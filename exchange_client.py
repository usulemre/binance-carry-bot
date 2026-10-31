"""Binance Futures (Testnet) için ince bir wrapper (python-binance kullanır)."""

import logging
import os
import time
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger("bot")

# Binance'in rate-limit (429) ve IP ban (418) durumlarında dönebileceği kodlar.
# Bu durumlarda hemen pes etmek yerine, borsanın istediği süre kadar bekleyip
# yeniden denemek gerekir - aksi halde geçici bir yoğunluk, botun tamamen
# durmasına (ya da daha kötüsü, IP'nin uzun süreliğine banlanmasına) yol açar.
RATE_LIMIT_STATUS_CODES = (429, 418)

# Ağ katmanı hataları - API'ye ulaşılamadığını gösterir. Okuma
# çağrılarında yeniden denenebilir, emir çağrılarında DENENMEMELİDİR
# (bkz. _call_with_retry docstring).
try:
    import requests as _requests
    _NETWORK_ERRORS = (_requests.exceptions.RequestException, ConnectionError, TimeoutError)
except ImportError:
    _NETWORK_ERRORS = (ConnectionError, TimeoutError)


def _call_with_retry(func, *args, max_retries: int = 3, base_delay: float = 2.0,
                     retry_network: bool = False, **kwargs):
    """Binance API çağrısını rate-limit/ban durumuna karşı dayanıklı hale
    getirir. Retry-After header'ı varsa onu, yoksa üstel geri çekilmeyi
    kullanır. Rate-limit DIŞINDAKİ API hataları (ör. geçersiz parametre)
    hemen fırlatılır - onları yeniden denemenin anlamı yok.

    retry_network: AĞ hatalarında (timeout, bağlantı kopması) da yeniden
    dene. VARSAYILAN FALSE ve bu bilinçli bir karar:

      - OKUMA çağrılarında (bakiye, kline, pozisyon) ağ hatasını yeniden
        denemek güvenli ve faydalı -> retry_network=True verilir.

      - EMİR çağrılarında TEHLİKELİ. Ağ timeout'u, emrin borsaya
        ULAŞMADIĞI anlamına GELMEZ - emir işlenmiş ama cevap kaybolmuş
        olabilir. Yeniden denemek POZİSYONU İKİYE KATLAR.
        Bu yüzden emir gönderen çağrılarda retry_network=False kalır;
        hata yukarı fırlatılır ve çağıran taraf pozisyonu SORGULAYARAK
        durumu netleştirmelidir (bkz. open_market_position).

    Rate-limit (429/418) her iki durumda da güvenle yeniden denenir,
    çünkü bu kodlar isteğin borsa tarafından HİÇ İŞLENMEDİĞİNİ garanti eder.
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except _NETWORK_ERRORS as e:
            if retry_network and attempt < max_retries:
                wait = base_delay * (2 ** attempt)
                logger.warning(f"Ağ hatası ({type(e).__name__}: {e}), "
                               f"{wait:.0f}sn sonra yeniden denenecek "
                               f"(deneme {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            raise
        except BinanceAPIException as e:
            status = getattr(e, "status_code", None)
            if status in RATE_LIMIT_STATUS_CODES and attempt < max_retries:
                retry_after = getattr(e, "response", None)
                wait = base_delay * (2 ** attempt)
                if retry_after is not None:
                    header_val = retry_after.headers.get("Retry-After")
                    if header_val:
                        try:
                            wait = max(wait, float(header_val))
                        except ValueError:
                            pass
                logger.warning(f"Rate limit/ban (HTTP {status}), {wait:.0f}sn bekleniyor "
                               f"(deneme {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            raise
    return func(*args, **kwargs)  # son deneme, hata varsa doğrudan yukarı fırlatılır


def ozel_anahtar_oku():
    """MADDE 680: BINANCE_PRIVATE_KEY_PATH (PEM, Ed25519) -> (metin, parola) ya da None. Dosya yoksa / okunamıyorsa HATA verir
    (sessizce HMAC'a düşmek yanlış anahtarla çalışmak demektir)."""
    yol = os.getenv("BINANCE_PRIVATE_KEY_PATH", "").strip()
    if not yol:
        return None
    with open(os.path.expanduser(yol), encoding="utf-8") as f:
        metin = f.read()
    if "PRIVATE KEY" not in metin:
        raise ValueError(f"BINANCE_PRIVATE_KEY_PATH bir PEM özel anahtarı değil: {yol}")
    return metin, (os.getenv("BINANCE_PRIVATE_KEY_PASS") or None)


class ExchangeClient:
    def __init__(self, api_key: str, api_secret: str, mode: str = "demo"):
        """
        mode:
          - "demo"    : YENİ Binance Futures Demo Trading (demo-fapi.binance.com).
                        API key'i artık ana Binance hesabından, "Demo Trading"
                        sayfasından oluşturuluyor (eski ayrı testnet sitesi
                        2026'da demo.binance.com'a yönlendirilmeye başladı,
                        API tarafı demo-fapi.binance.com'a taşındı). Bu,
                        Ocak 2026 sonrası Binance'in önerdiği YENİ yöntemdir.
          - "legacy_testnet" : Eski ayrı testnet.binancefuture.com sitesi.
                        Site artık demo.binance.com'a yönlendiriyor; bu mod
                        sadece eskiden oluşturulmuş anahtarları olanlar için
                        geriye dönük uyumluluk amaçlıdır, YENİ anahtarlar
                        genelde bu sistemde çalışmaz (hesap eşleşmez).
          - "live"    : Gerçek para, gerçek mainnet. DİKKATLİ KULLANIN.

        NOT: Eskiden bir `testnet: bool` parametresi vardı ama `mode`
        eklendikten sonra HİÇ KULLANILMIYORDU - `testnet=True` geçilse
        bile `mode` varsayılanı devreye giriyordu. Sessiz bir tuzaktı
        (çağıran "testnet'teyim" sanıyordu), kaldırıldı.
        # ping=False: python-binance varsayılan olarak Client oluşturulurken
        # SPOT (mainnet) ping endpoint'ine istek atar - bu, testnet/demo
        # modunda da çalışır ve bazı ağ ortamlarında (mainnet coğrafi/yasal
        # kısıtlamaya takılan) bağlantıyı gereksiz yere başarısız kılar.
        # Bizim ilgilendiğimiz tek şey futures endpoint'leri.
        """
        self.mode = mode
        # MADDE 680: Ed25519 anahtarı (önerilen). BINANCE_PRIVATE_KEY_PATH verilirse istekler sunucuda üretilmiş özel anahtarla
        # imzalanır; Binance'e yalnız AÇIK anahtar verilir (gizli anahtar hiçbir zaman Binance'te / ekranda görünmez). O zaman
        # BINANCE_API_SECRET gerekmez. Yoksa eski HMAC (API_KEY + API_SECRET) yolu, değişmeden.
        ozel = ozel_anahtar_oku()
        kw = {"private_key": ozel[0], "private_key_pass": ozel[1]} if ozel else {}
        if ozel:
            api_secret = None
        self.imza = "ed25519" if ozel else "hmac"
        if mode == "demo":
            self.client = Client(api_key, api_secret, demo=True, ping=False, **kw)
        elif mode == "legacy_testnet":
            self.client = Client(api_key, api_secret, testnet=True, ping=False, **kw)
        else:
            self.client = Client(api_key, api_secret, ping=False, **kw)
        self.testnet = mode in ("demo", "legacy_testnet")

    # ---------------------------------------------------------------- market data
    def get_top_symbols(self, quote_asset: str, top_n: int, excluded: list) -> list:
        """24 saatlik hacme göre en yüksek işlem gören USDT-M perpetual sözleşmeleri döner."""
        tickers = _call_with_retry(self.client.futures_ticker, retry_network=True)
        filtered = [
            t for t in tickers
            if t["symbol"].endswith(quote_asset) and t["symbol"] not in excluded
        ]
        filtered.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
        return [t["symbol"] for t in filtered[:top_n]]

    def get_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        raw = _call_with_retry(self.client.futures_klines, symbol=symbol, interval=interval, limit=limit, retry_network=True)
        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        for col in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
            df[col] = df[col].astype(float)
        return df

    # ---------------------------------------------------------------- account
    def get_account_balance_usdt(self) -> float:
        balances = _call_with_retry(self.client.futures_account_balance, retry_network=True)
        for b in balances:
            if b["asset"] == "USDT":
                return float(b["balance"])
        return 0.0

    def get_account_equity_usd(self) -> float:
        """Futures hesabının TOPLAM teminat değeri (USD).

        Çoklu varlık modunda (BFUSD, LDUSDT, USDC vb. teminat) USDT
        satırı gerçek sermayeyi göstermez. `totalMarginBalance` tüm
        teminatları (Binance'in teminat oranı uygulanmış olarak) ve
        gerçekleşmemiş K/Z'yi içerir. Alan yoksa USDT bakiyesine düşer.
        """
        try:
            hesap = _call_with_retry(self.client.futures_account, retry_network=True)
            deger = float(hesap.get("totalMarginBalance", "nan"))
            if deger == deger:        # NaN değil
                return deger
        except Exception:
            pass
        return self.get_account_balance_usdt()

    def get_open_positions(self) -> list:
        positions = _call_with_retry(self.client.futures_position_information, retry_network=True)
        return [p for p in positions if float(p["positionAmt"]) != 0]

    def get_today_realized_pnl(self) -> float:
        """Bugünkü (00:00 UTC'den itibaren) gerçekleşmiş kâr/zarar toplamı.
        Binance'in gelir geçmişi (income history) endpoint'inden gerçek veriyle,
        tahmine dayalı takip yerine doğru rakam verir."""
        from datetime import datetime, timezone
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_ms = int(start_of_day.timestamp() * 1000)
        try:
            income = self.client.futures_income_history(
                incomeType="REALIZED_PNL", startTime=start_ms, limit=1000
            )
            return sum(float(i["income"]) for i in income)
        except BinanceAPIException as e:
            logger.warning(f"Günlük PnL çekilemedi: {e}")
            return 0.0

    def set_leverage(self, symbol: str, leverage: int):
        try:
            _call_with_retry(self.client.futures_change_leverage, symbol=symbol, leverage=leverage)
        except BinanceAPIException as e:
            logger.warning(f"Kaldıraç ayarlanamadı {symbol}: {e}")

    def get_symbol_precision(self, symbol: str) -> dict:
        info = _call_with_retry(self.client.futures_exchange_info, retry_network=True)
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                return {
                    "quantity_precision": s["quantityPrecision"],
                    "price_precision": s["pricePrecision"],
                }
        return {"quantity_precision": 3, "price_precision": 2}

    # ---------------------------------------------------------------- orders
    # NOT: Emir gönderen çağrılar rate-limit (429/418) durumunda güvenle
    # yeniden denenebilir, çünkü bu durum kodları isteğin borsa tarafından
    # HİÇ İŞLENMEDİĞİ (yani emrin açılmadığı) anlamına gelir - retry, aynı
    # emrin iki kez açılması riski taşımaz.
    def _verify_order_filled(self, symbol: str, order_id, max_wait_seconds: float = 10.0,
                              poll_interval: float = 1.0) -> dict:
        """MARKET emri gönderildikten sonra API'nin 'başarılı' cevap vermesi,
        emrin GERÇEKTEN dolduğu (FILLED) anlamına gelmez - eşleşme asenkron
        olabilir, kısmi dolabilir, ya da (nadiren) iptal/reddedilebilir. Bu
        fonksiyon, emrin son durumunu borsadan POLL ederek doğrular. Bot bu
        doğrulama olmadan "pozisyon açıldı" varsayıp SL/TP kurarsa, emir
        aslında dolmamışken korumasız bir SL/TP emri göndermiş olabilir."""
        import time as _time
        waited = 0.0
        last_status = None
        while waited < max_wait_seconds:
            order = _call_with_retry(self.client.futures_get_order, symbol=symbol, orderId=order_id, retry_network=True)
            last_status = order.get("status")
            if last_status == "FILLED":
                return order
            if last_status in ("CANCELED", "EXPIRED", "REJECTED"):
                logger.error(f"{symbol}: emir {order_id} dolmadı, durum: {last_status}")
                return order
            _time.sleep(poll_interval)
            waited += poll_interval

        logger.warning(f"{symbol}: emir {order_id} {max_wait_seconds}sn içinde FILLED "
                       f"olarak doğrulanamadı (son durum: {last_status}). Manuel kontrol edin.")
        return {"status": last_status or "UNKNOWN", "orderId": order_id}

    def _pozisyon_miktari(self, symbol: str) -> float:
        """Sembolün açık pozisyon miktarını döner (yoksa 0).
        Ağ hatası sonrası "emir gerçekten açıldı mı?" sorusunu yanıtlar."""
        try:
            for p in self.get_open_positions():
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0))
        except Exception as e:
            logger.error(f"{symbol}: pozisyon sorgulanamadı: {e}")
        return 0.0

    def open_market_position(self, symbol: str, side: str, quantity: float, verify_fill: bool = True):
        """side: 'BUY' (long aç) veya 'SELL' (short aç). verify_fill=True ise
        emrin gerçekten dolduğu borsadan teyit edilir (önerilen).

        AĞ HATASI DURUMU: Emir gönderilirken timeout/bağlantı kopması
        olursa emrin borsaya ulaşıp ulaşmadığı BİLİNMEZ. Bu durumda
        yeniden denemek pozisyonu ikiye katlayabilir. Bunun yerine
        pozisyon SORGULANIR: emir gerçekten açılmışsa bu tespit edilir
        ve mükerrer emir gönderilmez.
        """
        try:
            order = _call_with_retry(
                self.client.futures_create_order,
                symbol=symbol, side=side, type="MARKET", quantity=quantity,
            )
        except _NETWORK_ERRORS as e:
            logger.error(
                f"{symbol}: emir gönderilirken AĞ HATASI ({e}). Emrin borsaya "
                f"ulaşıp ulaşmadığı bilinmiyor - pozisyon sorgulanıyor...")
            mevcut = self._pozisyon_miktari(symbol)
            if abs(mevcut) > 0:
                logger.warning(
                    f"{symbol}: pozisyon AÇILMIŞ ({mevcut}) - emir aslında "
                    f"işlenmiş. Mükerrer emir GÖNDERİLMİYOR.")
                return {"status": "FILLED", "orderId": None,
                        "executedQty": abs(mevcut), "_recovered": True}
            logger.error(f"{symbol}: pozisyon açılmamış - emir kaybolmuş. "
                         f"Bir sonraki turda yeniden denenecek.")
            raise
        if verify_fill and order.get("status") != "FILLED":
            order = self._verify_order_filled(symbol, order["orderId"])
        return order

    def close_position(self, symbol: str, side: str, quantity: float, verify_fill: bool = True):
        """Pozisyonu kapatmak için ters yönde MARKET order, reduceOnly=True."""
        order = _call_with_retry(
            self.client.futures_create_order,
            symbol=symbol, side=side, type="MARKET", quantity=quantity, reduceOnly=True,
        )
        if verify_fill and order.get("status") != "FILLED":
            order = self._verify_order_filled(symbol, order["orderId"])
        return order

    def place_stop_loss(self, symbol: str, side: str, stop_price: float, quantity: float):
        return _call_with_retry(
            self.client.futures_create_order,
            symbol=symbol, side=side, type="STOP_MARKET",
            stopPrice=round(stop_price, 4), quantity=quantity, reduceOnly=True,
        )

    def place_take_profit(self, symbol: str, side: str, stop_price: float, quantity: float):
        return _call_with_retry(
            self.client.futures_create_order,
            symbol=symbol, side=side, type="TAKE_PROFIT_MARKET",
            stopPrice=round(stop_price, 4), quantity=quantity, reduceOnly=True,
        )

    def cancel_all_open_orders(self, symbol: str):
        try:
            _call_with_retry(self.client.futures_cancel_all_open_orders, symbol=symbol)
        except BinanceAPIException as e:
            logger.warning(f"Emirler iptal edilemedi {symbol}: {e}")
