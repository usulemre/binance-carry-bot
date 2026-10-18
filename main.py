"""
Agentic Binance Futures Bot - Ana Döngü
=========================================
Akış:
  1. Piyasayı tara (en yüksek hacimli N coin)
  2. Her coin için strateji sinyali hesapla, puanla
  3. Açık pozisyonları kontrol et (yeni slot var mı, günlük limit uygun mu)
  4. En güçlü sinyalden başlayarak, boş slot doldukça pozisyon aç
  5. Her pozisyon açılışında otomatik SL/TP emirleri de gönderilir (borsa tarafında)
  6. Belirlenen aralıkla (scan_interval_seconds) tekrar et

ÖNEMLİ: Bu bot TESTNET için tasarlanmıştır. Gerçek paraya geçmeden önce
haftalarca gözlemleyin. Kripto vadeli işlemler yüksek risklidir, kaldıraçlı
işlemlerde sermayenin tamamını kaybetmek mümkündür. Bu yazılım yatırım
tavsiyesi değildir.
"""

import json
import os
import logging
import time
import sys

import config
from exchange_client import ExchangeClient
from risk_manager import RiskManager
from strategy import evaluate_symbol, Signal, STRATEGY_VARIANTS
import position_manager as pm
from macro_calendar import is_near_macro_event, is_configured as macro_configured, gecmis_olaylari_temizle
from correlation import is_too_correlated
from backtest import _timeframe_to_minutes
from market_regime import compute_market_regime, is_regime_tradeable

ACTIVE_SIGNAL_FN = STRATEGY_VARIANTS[config.ACTIVE_STRATEGY]

SIGNALS_FILE = "last_signals.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("bot")


def get_open_symbols(exchange: ExchangeClient) -> set:
    positions = exchange.get_open_positions()
    return {p["symbol"] for p in positions}


def scan_and_score(exchange: ExchangeClient) -> tuple:
    """(sinyaller, {sembol: kapanış serisi}) döner. Kapanış serileri korelasyon
    filtresi için saklanır - böylece ek API çağrısı yapmaya gerek kalmaz."""
    symbols = exchange.get_top_symbols(
        config.SCAN.quote_asset, config.SCAN.top_n_symbols, config.SCAN.excluded_symbols
    )
    signals = []
    closes_by_symbol = {}
    for symbol in symbols:
        try:
            df = exchange.get_klines(symbol, config.SCAN.timeframe, config.SCAN.kline_lookback)
            closes_by_symbol[symbol] = df["close"].values
            signal = evaluate_symbol(symbol, df, config.STRATEGY, signal_fn=ACTIVE_SIGNAL_FN)
            if signal:
                signals.append(signal)
        except Exception as e:
            logger.warning(f"{symbol} taranırken hata: {e}")
            continue
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals, closes_by_symbol


BOT_STATE_FILE = "bot_state.json"


def _load_bot_state() -> dict:
    """Bot durumunu (tepe bakiye vb.) diskten okur."""
    try:
        with open(BOT_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_bot_state(state: dict):
    """ATOMİK yazma - bkz. risk_manager._save_state açıklaması."""
    tmp = BOT_STATE_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, BOT_STATE_FILE)
    except Exception as e:
        logger.warning(f"Bot durumu kaydedilemedi: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass

def close_stale_positions(exchange: ExchangeClient, dry_run: bool = False):
    """MAX_HOLD_DAYS gününden uzun süredir açık olan pozisyonları kapatır.

    mean_reversion hızlı geri dönüş bekler; pozisyon günlerce açıksa tez
    muhtemelen yanlıştır ve sermaye boşa bağlanmıştır. Ölçüldü: 10 günlük
    üst sınır hem IS hem OOS getirisini artırıyor (config.py MAX_HOLD_DAYS).

    Giriş zamanı, bot durumundan (bot_state.json) okunur. Kayıt yoksa
    pozisyon ilk görüldüğü anda kaydedilir - yani bot yeniden başlarsa
    süre sıfırdan sayılır (muhafazakâr: erken kapatmaktansa geç kapatır).
    """
    if not config.USE_MAX_HOLD:
        return
    import time as _time
    max_seconds = config.MAX_HOLD_DAYS * 86400

    state = _load_bot_state()
    seen = state.setdefault("position_opened_at", {})
    now = _time.time()
    changed = False

    open_syms = set()
    for p in exchange.get_open_positions():
        amt = float(p.get("positionAmt", 0))
        if amt == 0:
            continue
        sym = p["symbol"]
        open_syms.add(sym)
        if sym not in seen:
            seen[sym] = now
            changed = True
            continue
        held = now - float(seen[sym])
        if held >= max_seconds:
            gun = held / 86400
            logger.info(f"SÜRE DOLDU {sym}: {gun:.1f} gündür açık "
                        f"(limit {config.MAX_HOLD_DAYS:.0f} gün) - kapatılıyor")
            if not dry_run:
                try:
                    exchange.cancel_all_open_orders(sym)
                    side = "SELL" if amt > 0 else "BUY"
                    exchange.close_position(sym, side, abs(amt))
                    pm.remove_trade(sym)
                    seen.pop(sym, None)
                    changed = True
                except Exception as e:
                    logger.error(f"  {sym} kapatılamadı: {e}")

    # artık açık olmayan sembolleri kayıttan temizle
    for sym in list(seen):
        if sym not in open_syms:
            seen.pop(sym, None)
            changed = True

    if changed:
        _save_bot_state(state)

def open_position_with_protection(exchange: ExchangeClient, risk_mgr: RiskManager,
                                   signal: Signal, balance: float, scale: float = 1.0):
    precision = exchange.get_symbol_precision(signal.symbol)
    qty_precision = precision["quantity_precision"]

    quantity = risk_mgr.calculate_position_size(balance, signal.entry_price, signal.stop_loss, scale)
    quantity = round(quantity, qty_precision)

    if quantity <= 0:
        logger.info(f"{signal.symbol}: hesaplanan miktar 0, atlanıyor.")
        return

    exchange.set_leverage(signal.symbol, config.RISK.leverage)

    entry_side = "BUY" if signal.direction == "LONG" else "SELL"
    exit_side = "SELL" if signal.direction == "LONG" else "BUY"

    try:
        order = exchange.open_market_position(signal.symbol, entry_side, quantity)

        if order.get("status") != "FILLED":
            logger.error(f"{signal.symbol}: emir DOLMADI (durum: {order.get('status')}), "
                         f"SL/TP kurulmayacak, pozisyon takibe alınmayacak. Manuel kontrol edin.")
            return

        # Gerçekten dolan miktarı kullan (talep edilen miktar değil) - MARKET
        # emirlerinde genelde aynıdır, ama kısmi dolma ihtimaline karşı güvenli taraf.
        filled_qty = float(order.get("executedQty", quantity)) or quantity

        logger.info(f"POZİSYON AÇILDI (doğrulandı): {signal.symbol} {signal.direction} "
                     f"miktar={filled_qty} giriş~{signal.entry_price} skor={signal.score}")

        # STOP-LOSS KURULAMAZSA POZİSYON KAPATILIR.
        # Bu, canlıdaki en tehlikeli senaryodur: pozisyon açık ama koruması
        # yok - kayıp sınırsız olabilir. Eskiden burada sadece log basılıyor,
        # pozisyon KORUMASIZ bırakılıyordu. Artık SL kurulamazsa pozisyon
        # derhal kapatılıyor: küçük bir komisyon kaybı, korumasız pozisyondan
        # kat kat iyidir.
        try:
            exchange.place_stop_loss(signal.symbol, exit_side, signal.stop_loss, filled_qty)
        except Exception as sl_hata:
            logger.error(f"{signal.symbol}: STOP-LOSS KURULAMADI ({sl_hata}) - "
                         f"pozisyon korumasız kalmasın diye KAPATILIYOR.")
            try:
                exchange.close_position(signal.symbol, exit_side, filled_qty)
                logger.warning(f"{signal.symbol}: korumasız pozisyon kapatıldı.")
            except Exception as kapat_hata:
                logger.error(
                    f"{signal.symbol}: POZİSYON KAPATILAMADI ({kapat_hata})! "
                    f"AÇIK VE KORUMASIZ POZİSYON VAR - DERHAL MANUEL MÜDAHALE EDİN. "
                    f"Yön={signal.direction} miktar={filled_qty}")
            return

        # TP kurulamazsa pozisyon KAPATILMAZ - SL zaten var, yani risk
        # sınırlı. Sadece uyarı verilir; pozisyon SL'e veya bir sonraki
        # döngüdeki yönetime bırakılır.
        try:
            exchange.place_take_profit(signal.symbol, exit_side, signal.take_profit, filled_qty)
            logger.info(f"{signal.symbol}: SL={signal.stop_loss:.6f} TP={signal.take_profit:.6f} ayarlandı.")
        except Exception as tp_hata:
            logger.warning(f"{signal.symbol}: take-profit kurulamadı ({tp_hata}). "
                           f"SL mevcut, risk sınırlı - pozisyon açık bırakılıyor.")

        pm.register_trade(signal.symbol, signal.direction, signal.entry_price,
                           signal.atr_value, signal.stop_loss, signal.take_profit, filled_qty)
    except Exception as e:
        logger.error(f"{signal.symbol} işlemi açılamadı: {e}")


def run_cycle(exchange: ExchangeClient, risk_mgr: RiskManager):
    balance = exchange.get_account_balance_usdt()
    daily_pnl = exchange.get_today_realized_pnl()
    logger.info(f"--- Yeni tarama döngüsü | Bakiye: {balance:.2f} USDT | Günlük PnL: {daily_pnl:+.2f} USDT ---")

    # Kademeli exposure azaltma: tepe bakiyeden uzaklaştıkça pozisyon
    # büyüklüğünü küçült, toparlandıkça büyüt. Ölçüldü: getiriyi artırırken
    # max düşüşü yarıdan fazla azaltıyor (config.py USE_DRAWDOWN_SCALING).
    position_scale = 1.0
    if config.USE_DRAWDOWN_SCALING:
        state = _load_bot_state()
        peak = max(float(state.get("peak_balance", 0.0)), balance)
        if peak != state.get("peak_balance"):
            state["peak_balance"] = peak
            _save_bot_state(state)
        if peak > 0:
            # Düşüşü R cinsine çevir: 1R = sermayenin risk_per_trade_pct'i
            r_unit = peak * (config.RISK.risk_per_trade_pct / 100)
            dd_r = (peak - balance) / r_unit if r_unit > 0 else 0.0
            position_scale = max(0.0, min(1.0, 1.0 - dd_r / config.DRAWDOWN_SCALE_FULL_R))
            if position_scale < 1.0:
                logger.info(f"Düşüş {dd_r:.1f}R -> pozisyon büyüklüğü "
                            f"%{position_scale*100:.0f}'e ölçekleniyor")
            if position_scale <= 0.01:
                logger.warning(f"Düşüş {dd_r:.1f}R, limit {config.DRAWDOWN_SCALE_FULL_R}R - "
                               f"yeni pozisyon açılmayacak, toparlanma bekleniyor.")

    # Kâr kilitleme yönetimi strateji bazında açılır/kapanır. mean_reversion
    # için ölçüldü ve ZARARLI çıktı (bkz. config.py STRATEGY_MANAGEMENT notu),
    # bu yüzden USE_POSITION_MANAGEMENT'te kapalı. Yönetim kapalıysa
    # pozisyonlar borsadaki SL/TP emirleriyle kendi başına kapanır.
    if config.USE_POSITION_MANAGEMENT.get(config.ACTIVE_STRATEGY, True):
        mgmt = config.STRATEGY_MANAGEMENT.get(config.ACTIVE_STRATEGY,
                                              config.STRATEGY_MANAGEMENT["breakout"])
        pm.manage_open_positions(
            exchange,
            breakeven_trigger_atr=mgmt["breakeven_trigger_atr"],
            breakeven_buffer_pct=mgmt["breakeven_buffer_pct"],
            partial_tp_r_multiple=mgmt["partial_tp_r_multiple"],
            partial_tp_fraction=mgmt["partial_tp_fraction"],
            trailing_atr_multiple=mgmt["trailing_atr_multiple"],
        )

    close_stale_positions(exchange)

    if risk_mgr.is_daily_loss_limit_hit(balance, daily_pnl):
        logger.warning("Günlük zarar limiti nedeniyle yeni işlem açılmayacak.")
        if config.RISK.close_positions_on_daily_limit:
            pm.close_all_positions(exchange, reason=f"günlük zarar limiti (%{config.RISK.max_daily_loss_pct})")
        return

    near_macro, macro_reason = is_near_macro_event()
    if near_macro:
        logger.info(f"Makro haber saatine yakın, yeni işlem açılmayacak: {macro_reason}")
        return

    open_symbols = get_open_symbols(exchange)
    open_count = len(open_symbols)
    logger.info(f"Açık pozisyon sayısı: {open_count}/{config.RISK.max_concurrent_positions}")

    if not risk_mgr.can_open_new_position(open_count):
        logger.info("Maksimum eşzamanlı pozisyon sayısına ulaşıldı, tarama sonucu değerlendirilmeyecek.")
        return

    signals, closes_by_symbol = scan_and_score(exchange)
    logger.info(f"{len(signals)} aday sinyal bulundu.")
    _save_signals_snapshot(signals, balance)

    # Piyasa rejimi kontrolü: strateji her rejimde çalışmaz. Düşük volatilite
    # döneminde mean_reversion para kaybediyor (hareket yoksa TP'ye ulaşılmaz
    # ama komisyon+funding yine ödenir). Bu kontrol AÇIK pozisyonları
    # etkilemez - onlar normal şekilde yönetilmeye devam eder, sadece YENİ
    # pozisyon açılmaz.
    # Rejim filtresi strateji bazında: extreme_reversal için zararlı
    # (bkz. config.USE_REGIME_FILTER_BY_STRATEGY)
    rejim_aktif = config.USE_REGIME_FILTER_BY_STRATEGY.get(
        config.ACTIVE_STRATEGY, config.RISK.use_regime_filter)
    if rejim_aktif and closes_by_symbol:
        regime = compute_market_regime(closes_by_symbol, config.RISK.regime_lookback_bars)
        tradeable, reason = is_regime_tradeable(
            regime, config.RISK.regime_min_volatility,
            config.RISK.regime_max_autocorrelation,
            config.RISK.use_autocorr_filter,
        )
        if not tradeable:
            logger.info(f"Piyasa rejimi uygun değil, yeni pozisyon açılmayacak: {reason}")
            return
        logger.info(f"Piyasa rejimi kontrolü: {reason}")

    for signal in signals:
        open_symbols = get_open_symbols(exchange)
        if signal.symbol in open_symbols:
            continue
        if not risk_mgr.can_open_new_position(len(open_symbols)):
            logger.info("Slot doldu, döngü sonlandırılıyor.")
            break

        # Korelasyon filtresi: bu sinyal, zaten açık bir pozisyonla aynı
        # bahsin tekrarı mı? Kripto altcoinleri birbirine yüksek
        # korelasyonludur - filtresiz halde piyasa aleyhe tek bir hareket
        # yaptığında tüm pozisyonlar aynı anda kaybeder.
        if config.RISK.use_correlation_filter and signal.symbol in closes_by_symbol:
            open_closes = {
                s: closes_by_symbol[s] for s in open_symbols if s in closes_by_symbol
            }
            if open_closes:
                too_corr, corr_sym, corr_val = is_too_correlated(
                    closes_by_symbol[signal.symbol], open_closes,
                    config.RISK.correlation_threshold, config.RISK.correlation_lookback,
                )
                if too_corr:
                    logger.info(
                        f"{signal.symbol} atlandı: açık pozisyon {corr_sym} ile "
                        f"korelasyon {corr_val:+.2f} (eşik {config.RISK.correlation_threshold}). "
                        f"Aynı riskin tekrarı olurdu."
                    )
                    continue

        open_position_with_protection(exchange, risk_mgr, signal, balance, position_scale)
        time.sleep(1)  # rate limit koruması


def _save_signals_snapshot(signals: list, balance: float):
    try:
        data = {
            "timestamp": time.time(),
            "balance": balance,
            "signals": [
                {
                    "symbol": s.symbol, "direction": s.direction, "score": float(s.score),
                    "entry_price": s.entry_price, "stop_loss": s.stop_loss, "take_profit": s.take_profit,
                }
                for s in signals[:15]
            ],
        }
        with open(SIGNALS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Sinyal snapshot kaydedilemedi: {e}")


def main():
    if not config.API_KEY or not config.API_SECRET:
        logger.error("BINANCE_API_KEY / BINANCE_API_SECRET ayarlanmamış. .env dosyanızı kontrol edin.")
        sys.exit(1)

    logger.info(f"Bot başlatılıyor. Mod: {config.BINANCE_MODE}")

    # Makro takvim boşsa filtre sessizce hiçbir şey yapmaz - bu durumu
    # görünür kıl. Bot "makro korumam var" sanmasın.
    silinen = gecmis_olaylari_temizle()
    if silinen:
        logger.info(f"Makro takvimden {silinen} geçmiş olay temizlendi.")
    if not macro_configured():
        logger.warning(
            "Makro haber takvimi BOŞ - bu filtre hiçbir şey yapmayacak. "
            "FOMC/CPI/NFP gibi yüksek etkili haber saatlerinde işlem "
            "açılmasını engellemek için macro_calendar.py içindeki "
            "MACRO_EVENTS listesini doldurun (kaynak: forexfactory.com/calendar).")
    exchange = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    risk_mgr = RiskManager(config.RISK, config.STATE_FILE)

    pm.reconcile_on_startup(exchange)

    while True:
        try:
            run_cycle(exchange, risk_mgr)
        except Exception as e:
            logger.exception(f"Döngüde beklenmeyen hata: {e}")
        logger.info(f"{config.SCAN.scan_interval_seconds} saniye bekleniyor...\n")
        time.sleep(config.SCAN.scan_interval_seconds)


if __name__ == "__main__":
    main()
