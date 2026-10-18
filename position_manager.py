"""
Açık pozisyonların meta verisini (giriş fiyatı, ATR, SL/TP, break-even,
kısmi kâr alma, trailing stop durumu) diskte tutar. Binance'in position
bilgisi bunları içermediği için (sadece anlık miktar/giriş/mark fiyatı
verir), bot kendi açtığı işlemlerin detayını burada saklar.

Kâr kilitleme mantığı 3 aşamalı:
  1) BREAKEVEN: Pozisyon `breakeven_trigger_atr` kadar kâra ulaşınca stop
     girişe çekilir -> işlem artık en kötü ihtimalle "sıfır" kapanır.
  2) KISMİ KÂR ALMA: Pozisyon `partial_tp_r_multiple` R'ye ulaşınca
     miktarın `partial_tp_fraction` kadarı GERÇEKTEN kapatılır (borsaya
     market emri gönderilir) -> bu kâr artık KESİNLEŞMİŞTİR, geri
     dönemez. Kalan miktar açık kalır.
  3) TRAILING STOP: Kalan miktar için, fiyat lehte yeni bir zirve/dip
     yaptıkça stop-loss da onu ATR mesafesiyle takip eder -> pozisyon
     hâlâ açıkken bile kazanılan kârın büyük kısmı "kilitlenir".
"""

import json
import logging
import os

logger = logging.getLogger("bot")

TRADES_FILE = "open_trades.json"


def load_trades() -> dict:
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE) as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"İşlem kayıt dosyası okunamadı ({e}) - boş başlanıyor. "
                           f"Açık pozisyonlar borsada duruyor ama bot onları "
                           f"kendi kaydında görmeyecek - MANUEL KONTROL EDİN.")
    return {}


def save_trades(trades: dict):
    """ATOMİK yazma - yarım kalan dosya botu bir daha başlatmaz."""
    tmp = TRADES_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(trades, f)
        os.replace(tmp, TRADES_FILE)
    except Exception as e:
        logger.warning(f"İşlem kayıtları kaydedilemedi: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def register_trade(symbol: str, direction: str, entry_price: float, atr_value: float,
                    stop_loss: float, take_profit: float, quantity: float):
    trades = load_trades()
    trades[symbol] = {
        "direction": direction,
        "entry_price": entry_price,
        "atr_value": atr_value,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "quantity": quantity,
        "original_quantity": quantity,
        "breakeven_done": False,
        "partial_tp_done": False,
        "best_price": entry_price,  # LONG icin en yuksek, SHORT icin en dusuk gorulen fiyat
    }
    save_trades(trades)


def remove_trade(symbol: str):
    trades = load_trades()
    if symbol in trades:
        del trades[symbol]
        save_trades(trades)


def _risk_per_unit(meta: dict) -> float:
    # Orijinal stop, kayıtta ilk açılıştaki stop_loss değil (breakeven/trailing
    # sonradan değiştirmiş olabilir) - o yüzden entry ile ilk ATR'den türetiyoruz.
    return meta["atr_value"] * 1.0  # ATR birimini risk birimine yaklaşık eşliyoruz


def _replace_protective_orders(exchange, symbol: str, exit_side: str,
                                new_sl: float, new_tp: float, quantity: float,
                                eski_sl: float = None):
    """Koruyucu emirleri (SL/TP) yenileriyle değiştirir.

    TEHLİKELİ AN: mevcut emirler iptal edildikten sonra, yeni SL konana
    kadar pozisyon KORUMASIZDIR. Yeni SL konulamazsa pozisyon açık ve
    stop'suz kalır - kayıp sınırsız olabilir.

    Bu yüzden SL kurulamazsa:
      1) ESKİ SL geri konmaya çalışılır (eski_sl verilmişse)
      2) O da olmazsa pozisyon KAPATILIR
      3) O da olmazsa ACİL uyarı basılır

    Hata yukarı fırlatılır ki çağıran taraf durumu "başarılı" sanmasın.
    """
    exchange.cancel_all_open_orders(symbol)

    try:
        exchange.place_stop_loss(symbol, exit_side, new_sl, quantity)
    except Exception as e:
        logger.error(f"{symbol}: YENİ STOP-LOSS KURULAMADI ({e}) - "
                     f"pozisyon şu an KORUMASIZ, kurtarma deneniyor...")
        # 1) Eski stop'u geri koymayı dene
        if eski_sl is not None:
            try:
                exchange.place_stop_loss(symbol, exit_side, eski_sl, quantity)
                logger.warning(f"{symbol}: eski stop-loss ({eski_sl:.6f}) geri konuldu. "
                               f"Güncelleme yapılamadı ama pozisyon korumalı.")
                raise
            except Exception:
                pass
        # 2) Pozisyonu kapat
        try:
            exchange.close_position(symbol, exit_side, quantity)
            logger.warning(f"{symbol}: korumasız kalmasın diye pozisyon KAPATILDI.")
        except Exception as kapat_hata:
            logger.error(
                f"{symbol}: POZİSYON KAPATILAMADI ({kapat_hata})! "
                f"AÇIK VE KORUMASIZ POZİSYON VAR - DERHAL MANUEL MÜDAHALE EDİN. "
                f"miktar={quantity}")
        raise

    # SL kuruldu - TP kurulamazsa pozisyon kapatılmaz, risk zaten sınırlı
    try:
        exchange.place_take_profit(symbol, exit_side, new_tp, quantity)
    except Exception as e:
        logger.warning(f"{symbol}: take-profit yenilenemedi ({e}). "
                       f"SL mevcut, risk sınırlı.")


def reconcile_on_startup(exchange) -> list:
    """Bot her başladığında (yeniden başlatma dahil) çağrılır. Borsada açık
    olan ama open_trades.json'da meta verisi (giriş fiyatı, ATR, vb.) OLMAYAN
    pozisyonları tespit eder. Bu, bot çökme/yeniden başlatma sırasında
    dosyanın kaybolması gibi durumlarda oluşabilir. Bu pozisyonların SL/TP
    emirleri borsada zaten mevcuttur (o yüzden 'çıplak' değildir), ama
    breakeven/kısmi kâr alma/trailing stop gibi akıllı yönetim ÇALIŞMAZ -
    bu fonksiyon bunu tespit edip açıkça UYARIR, sessizce görmezden gelmez."""
    trades = load_trades()
    open_positions = exchange.get_open_positions()
    orphaned = [p["symbol"] for p in open_positions if p["symbol"] not in trades]

    if orphaned:
        logger.warning(
            f"UYARI: {len(orphaned)} pozisyon borsada açık ama takip kaydında yok: "
            f"{orphaned}. Bu pozisyonlar için breakeven/kısmi kâr alma/trailing stop "
            f"ÇALIŞMAYACAK (sadece ilk açılıştaki SL/TP emirleri geçerli kalacak). "
            f"Muhtemel sebep: bot önceki çalışmada beklenmedik şekilde durdu ve "
            f"open_trades.json güncellenemeden kapandı, ya da pozisyon botun "
            f"dışında (manuel) açıldı. Gerekirse bu pozisyonları manuel kapatıp "
            f"botun yeniden açmasına izin verebilirsiniz."
        )
    return orphaned


def close_all_positions(exchange, reason: str = "") -> list:
    """Günlük zarar limiti gibi acil bir durumda TÜM açık pozisyonları
    güvenli şekilde kapatır: önce koruyucu emirleri iptal eder (aksi halde
    pozisyon kapandıktan sonra 'sahipsiz' reduceOnly SL/TP emirleri borsada
    asılı kalır), sonra market emriyle kapatır, sonra takip kaydını temizler.
    Hangi pozisyon kapatılamazsa (ör. geçici API hatası) AÇIKÇA loglanır -
    sessizce atlanmaz, çünkü bu durumda pozisyon hem korumasız hem de
    botun bilgisi dışında kalmış olur."""
    open_positions = exchange.get_open_positions()
    if not open_positions:
        logger.info("Kapatılacak açık pozisyon yok.")
        return []

    logger.warning(f"TÜM POZİSYONLAR KAPATILIYOR (sebep: {reason}). "
                   f"Kapatılacak pozisyon sayısı: {len(open_positions)}")

    failed = []
    for p in open_positions:
        symbol = p["symbol"]
        amt = float(p["positionAmt"])
        side = "SELL" if amt > 0 else "BUY"
        quantity = abs(amt)
        try:
            exchange.cancel_all_open_orders(symbol)
            order = exchange.close_position(symbol, side, quantity)
            if order.get("status") == "FILLED":
                logger.warning(f"{symbol}: pozisyon kapatıldı (miktar={quantity}).")
                remove_trade(symbol)
            else:
                logger.error(f"{symbol}: kapatma emri FILLED olarak doğrulanamadı "
                             f"(durum: {order.get('status')}). MANUEL KONTROL EDİN.")
                failed.append(symbol)
        except Exception as e:
            logger.error(f"{symbol}: pozisyon kapatılamadı: {e}. MANUEL KONTROL EDİN.")
            failed.append(symbol)

    if failed:
        logger.error(f"UYARI: {len(failed)} pozisyon kapatılamadı: {failed}. "
                     f"Bunları borsadan MANUEL kontrol edip kapatmanız gerekebilir.")
    return failed


def manage_open_positions(exchange, breakeven_trigger_atr: float = 1.0,
                           breakeven_buffer_pct: float = 0.05,
                           partial_tp_r_multiple: float = 1.5,
                           partial_tp_fraction: float = 0.5,
                           trailing_atr_multiple: float = 2.0):
    """Her döngüde çağrılır. 3 aşamalı kâr kilitleme mantığını uygular ve
    artık borsada açık olmayan işlemleri (kapanmış) kayıttan temizler."""
    trades = load_trades()
    if not trades:
        return

    open_positions = {p["symbol"]: p for p in exchange.get_open_positions()}

    for symbol in list(trades.keys()):
        if symbol not in open_positions:
            logger.info(f"{symbol}: pozisyon artık açık değil, takip kaydı temizleniyor.")
            remove_trade(symbol)
            continue

        meta = trades[symbol]
        mark_price = float(open_positions[symbol]["markPrice"])
        entry = meta["entry_price"]
        atr = meta["atr_value"]
        direction = meta["direction"]
        exit_side = "SELL" if direction == "LONG" else "BUY"
        risk_per_unit = _risk_per_unit(meta)

        # En iyi görülen fiyatı güncelle (trailing stop için gerekli)
        if direction == "LONG":
            meta["best_price"] = max(meta["best_price"], mark_price)
            profit_in_atr = (mark_price - entry) / atr if atr > 0 else 0
            profit_in_r = (mark_price - entry) / risk_per_unit if risk_per_unit > 0 else 0
        else:
            meta["best_price"] = min(meta["best_price"], mark_price)
            profit_in_atr = (entry - mark_price) / atr if atr > 0 else 0
            profit_in_r = (entry - mark_price) / risk_per_unit if risk_per_unit > 0 else 0

        changed = False

        # --- AŞAMA 2: Kısmi kâr alma (henüz yapılmadıysa) ---
        if not meta["partial_tp_done"] and profit_in_r >= partial_tp_r_multiple:
            try:
                close_qty = round(meta["quantity"] * partial_tp_fraction, 6)
                if close_qty > 0:
                    exchange.close_position(symbol, exit_side, close_qty)
                    meta["quantity"] = round(meta["quantity"] - close_qty, 6)
                    meta["partial_tp_done"] = True
                    changed = True
                    logger.info(f"{symbol}: {profit_in_r:.2f}R kâra ulaştı, pozisyonun "
                                f"%{partial_tp_fraction*100:.0f}'i ({close_qty}) kapatıldı. "
                                f"Kalan miktar: {meta['quantity']}")
                    # NOT: Borsadaki SL/TP emirleri hâlâ ESKİ (tam) miktar için
                    # duruyor. Bu ZARARSIZDIR çünkü tüm koruyucu emirler
                    # reduceOnly=True ile konuyor - pozisyondan fazlasını
                    # kapatamazlar, sadece mevcut miktarı kapatırlar.
                    # Emirler bir sonraki breakeven/trailing güncellemesinde
                    # zaten doğru miktarla yenilenecek.
            except Exception as e:
                logger.error(f"{symbol}: kısmi kâr alma başarısız: {e}")

        # --- AŞAMA 1: Breakeven (henüz yapılmadıysa) ---
        if not meta["breakeven_done"] and profit_in_atr >= breakeven_trigger_atr:
            buffer = entry * (breakeven_buffer_pct / 100)
            new_sl = entry + buffer if direction == "LONG" else entry - buffer
            try:
                _replace_protective_orders(exchange, symbol, exit_side, new_sl,
                                           meta["take_profit"], meta["quantity"],
                                           eski_sl=meta["stop_loss"])
                meta["breakeven_done"] = True
                meta["stop_loss"] = new_sl
                changed = True
                logger.info(f"{symbol}: {profit_in_atr:.2f}xATR kâra ulaştı, stop-loss girişe (breakeven) çekildi -> {new_sl:.6f}")
            except Exception as e:
                logger.error(f"{symbol}: breakeven stop ayarlanamadı: {e}")

        # --- AŞAMA 3: Trailing stop (breakeven yapıldıktan SONRA devreye girer) ---
        elif meta["breakeven_done"]:
            if direction == "LONG":
                trail_sl = meta["best_price"] - trailing_atr_multiple * atr
                should_update = trail_sl > meta["stop_loss"]  # sadece LEHTE ilerlet, asla gevşetme
            else:
                trail_sl = meta["best_price"] + trailing_atr_multiple * atr
                should_update = trail_sl < meta["stop_loss"]

            if should_update:
                try:
                    _replace_protective_orders(exchange, symbol, exit_side, trail_sl,
                                               meta["take_profit"], meta["quantity"],
                                               eski_sl=meta["stop_loss"])
                    meta["stop_loss"] = trail_sl
                    changed = True
                    logger.info(f"{symbol}: trailing stop güncellendi -> {trail_sl:.6f} "
                                f"(en iyi fiyat: {meta['best_price']:.6f})")
                except Exception as e:
                    logger.error(f"{symbol}: trailing stop güncellenemedi: {e}")

        if changed or meta["best_price"] != trades[symbol].get("best_price"):
            trades[symbol] = meta
            save_trades(trades)
