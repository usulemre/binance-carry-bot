"""
Anahtarsız Tarayıcı (Scanner-Only Mode)
==========================================
API KEY / SECRET GEREKTİRMEZ. Sadece Binance Futures'ın herkese açık
(public) REST endpoint'lerini kullanır: ticker ve kline verisi.

Kullanım:
    pip install requests pandas
    python scanner_public.py

Ne yapar:
    1. En yüksek hacimli USDT-M futures coinlerini çeker
    2. Her biri için mum verisi çeker (public endpoint)
    3. Trend + Momentum + Hacim stratejisiyle puanlar
    4. Sonuçları terminale tablo halinde basar ve last_signals.json'a yazar
       (dashboard.py bunu okuyup gösterebilir)

NOT: Bu script SADECE analiz yapar, hiçbir emir göndermez, hiçbir
hesaba bağlanmaz. main.py (gerçek/test işlem açan bot) için hâlâ
Binance Futures Testnet API anahtarı gerekecek.
"""

import json
import time
import requests
import pandas as pd

import config
from strategy import evaluate_symbol, STRATEGY_VARIANTS

ACTIVE_SIGNAL_FN = STRATEGY_VARIANTS[config.ACTIVE_STRATEGY]

# Bazı ağ ortamlarında mainnet public endpoint'i coğrafi/yasal kısıtlama
# (HTTP 451) ile engellenebilir, testnet ise engellenmeyebilir (ya da tam
# tersi). Bu yüzden sabit tek bir BASE_URL yerine, önce mainnet'i dener,
# başarısız olursa (bağlantı hatası, 451, timeout) otomatik olarak
# testnet'e düşer ve bir daha mainnet'i denemez (gereksiz gecikme olmasın).
_BASE_URL_CANDIDATES = [
    "https://fapi.binance.com",              # mainnet (gerçek piyasa verisi, tercih edilen)
    "https://testnet.binancefuture.com",     # testnet fallback (veri gecikmeli/farklı olabilir)
]
_working_base_url = None  # ilk başarılı istekten sonra sabitlenir


def _get(path: str, params: dict = None, timeout: int = 10) -> requests.Response:
    """BASE_URL adaylarını sırayla dener, ilk çalışanı önbelleğe alır."""
    global _working_base_url
    candidates = [_working_base_url] if _working_base_url else _BASE_URL_CANDIDATES
    last_exc = None
    for base in candidates:
        try:
            resp = requests.get(f"{base}{path}", params=params, timeout=timeout)
            if resp.status_code == 200:
                if _working_base_url is None:
                    _working_base_url = base
                    if base != _BASE_URL_CANDIDATES[0]:
                        print(f"[uyarı] mainnet erişilemedi, public veri için {base} kullanılıyor "
                              f"(fiyat/hacim testnet verisi olabilir, gerçek piyasadan farklı olabilir).")
                return resp
            last_exc = requests.HTTPError(f"HTTP {resp.status_code} - {base}{path}")
        except requests.RequestException as e:
            last_exc = e
            continue
    raise last_exc or RuntimeError("Hiçbir base URL'e ulaşılamadı")


def get_top_symbols(quote_asset: str, top_n: int, excluded: list) -> list:
    resp = _get("/fapi/v1/ticker/24hr")
    tickers = resp.json()
    filtered = [
        t for t in tickers
        if t["symbol"].endswith(quote_asset) and t["symbol"] not in excluded
    ]
    filtered.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    return [t["symbol"] for t in filtered[:top_n]]


def get_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = _get("/fapi/v1/klines", params=params)
    raw = resp.json()
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
        df[col] = df[col].astype(float)
    return df


def run_scan():
    print(f"Taranıyor: en hacimli {config.SCAN.top_n_symbols} coin ({config.SCAN.timeframe})...\n")
    symbols = get_top_symbols(config.SCAN.quote_asset, config.SCAN.top_n_symbols, config.SCAN.excluded_symbols)

    signals = []
    for symbol in symbols:
        try:
            df = get_klines(symbol, config.SCAN.timeframe, config.SCAN.kline_lookback)
            signal = evaluate_symbol(symbol, df, config.STRATEGY, signal_fn=ACTIVE_SIGNAL_FN)
            if signal:
                signals.append(signal)
        except Exception as e:
            print(f"  {symbol}: hata - {e}")
            continue

    signals.sort(key=lambda s: s.score, reverse=True)

    if not signals:
        print("Şu an eşiği geçen sinyal yok (min_signal_score = "
              f"{config.STRATEGY.min_signal_score}).")
    else:
        print(f"{'Sembol':<12}{'Yön':<8}{'Skor':<6}{'Giriş':<14}{'Stop-Loss':<14}{'Take-Profit':<14}")
        print("-" * 68)
        for s in signals:
            print(f"{s.symbol:<12}{s.direction:<8}{s.score:<6}{s.entry_price:<14.6f}"
                  f"{s.stop_loss:<14.6f}{s.take_profit:<14.6f}")

    snapshot = {
        "timestamp": time.time(),
        "balance": None,  # anahtarsız modda bakiye bilgisi yok
        "signals": [
            {
                "symbol": s.symbol, "direction": s.direction, "score": float(s.score),
                "entry_price": s.entry_price, "stop_loss": s.stop_loss, "take_profit": s.take_profit,
            }
            for s in signals[:15]
        ],
    }
    with open("last_signals.json", "w") as f:
        json.dump(snapshot, f)

    print(f"\n{len(signals)} sinyal last_signals.json dosyasına kaydedildi.")


if __name__ == "__main__":
    run_scan()
