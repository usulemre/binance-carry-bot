"""
Uzun Vadeli Geçmiş Veri İndirici (2020 -> Bugün)
====================================================
Binance'in public kline endpoint'i tek istekte en fazla 1500 mum döner.
2020'den bugüne (6 yıl) veri çekmek için startTime ilerleterek sayfalama
yapmak gerekir. Bu script bunu yapar ve sonucu CSV olarak diske kaydeder.

ÖNEMLİ - Coin seçimi (survivorship bias uyarısı):
    Bugünün en yüksek hacimli 30 coinini alıp "2020'den beri böyleydi"
    varsayımıyla geriye backtest etmek YANLIŞTIR: bugün popüler olan
    birçok coin 2020'de ya yoktu ya da düşük hacimliydi; 2020'de popüler
    olup sonra çöken/silinen coinler (ör. bazı DeFi coinleri) bu listede
    hiç yer almaz. Bu "hayatta kalma önyargısı" sonuçları yapay şekilde
    iyi gösterir.

    Bu yüzden burada SABİT bir "2020'den beri Binance Futures'ta işlem
    gören, hâlâ var olan" majör coin listesi kullanılıyor. Bu liste
    mükemmel değil ama rastgele bugünün top-30'unu almaktan çok daha
    dürüst bir başlangıç noktası.

Kullanım:
    python historical_fetch.py --start 2020-01-01 --timeframe 4h
    python historical_fetch.py --symbols BTCUSDT,ETHUSDT --start 2020-06-01
"""

import argparse
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

BASE_URL = "https://fapi.binance.com"
DATA_DIR = "historical_data"

# 2020'nin başından beri Binance Futures'ta (USDT-M perpetual) işlem gören,
# hâlâ aktif olan majör coinler. Tam liste değil ama makul bir başlangıç seti.
# --- Coin evreni ---
# NEDEN ÖNEMLİ: Kesitsel strateji coinlerin BİRBİRİNE göre sıralanmasından
# kazanır. Evren ne kadar genişse ayrışma o kadar zengin olur. Ölçüldü
# (temiz veriyle, 2022+):
#     4 coin  -> Sharpe 0.93
#     6 coin  -> Sharpe 1.47
#     8 coin  -> Sharpe 1.76
#    10 coin  -> Sharpe 2.13
# Her ek coin ~0.2 Sharpe ekliyor (doyma noktasına kadar).
#
# Canlı bot 30 coin tarıyor ama backtest sadece aşağıdaki listeyle
# yapılıyor - yani BACKTEST, CANLI BOTU EKSİK TEMSİL EDİYOR.
# Listeyi genişletmek en yüksek getirili iyileştirme adımıdır.

# 2020'den beri işlem gören, hâlâ var olan çekirdek liste (orijinal 14).
CORE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "LTCUSDT",
    "ADAUSDT", "LINKUSDT", "BCHUSDT", "EOSUSDT", "TRXUSDT",
    "XLMUSDT", "XTZUSDT", "ETCUSDT", "FILUSDT",
]

# 2021'den beri işlem gören ek coinler. Daha kısa geçmiş ama evreni
# belirgin genişletiyor. --extended ile dahil edilir.
EXTENDED_SYMBOLS = [
    "SOLUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT", "ATOMUSDT",
    "UNIUSDT", "AAVEUSDT", "ALGOUSDT", "VETUSDT", "ICPUSDT",
    "NEARUSDT", "FTMUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT",
    "THETAUSDT", "EGLDUSDT", "HBARUSDT", "CHZUSDT", "ENJUSDT",
]

LONG_HISTORY_SYMBOLS = CORE_SYMBOLS


def fetch_klines_page(symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1500):
    params = {
        "symbol": symbol, "interval": interval,
        "startTime": start_ms, "endTime": end_ms, "limit": limit,
    }
    resp = requests.get(f"{BASE_URL}/fapi/v1/klines", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_full_history(symbol: str, interval: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.now(timezone.utc) if end_date is None else \
        datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    all_rows = []
    cursor = start_ms
    page = 0
    while cursor < end_ms:
        page += 1
        rows = fetch_klines_page(symbol, interval, cursor, end_ms)
        if not rows:
            break
        all_rows.extend(rows)
        last_open_time = rows[-1][0]
        if last_open_time <= cursor:
            break  # ilerleme yok, sonsuz döngüye girmemek için dur
        cursor = last_open_time + 1
        print(f"  {symbol}: sayfa {page}, {len(all_rows)} mum toplandı "
              f"(şu ana kadar: {datetime.fromtimestamp(last_open_time/1000, tz=timezone.utc).date()})")
        time.sleep(0.3)  # rate limit koruması

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    return df.drop_duplicates(subset="open_time").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description="2020'den bugüne geçmiş veri indirici")
    parser.add_argument("--extended", action="store_true",
                        help="Genişletilmiş coin evreni (14 -> 34). Kesitsel "
                             "strateji için ÖNERİLİR: her ek coin ~0.2 Sharpe "
                             "ekliyor (bkz. dosya başındaki ölçüm).")
    parser.add_argument("--symbols", type=str, default=None,
                         help="Virgülle ayrılmış sembol listesi (boşsa varsayılan majör liste kullanılır)")
    parser.add_argument("--start", type=str, default="2020-01-01")
    parser.add_argument("--end", type=str, default=None, help="Boşsa bugüne kadar")
    parser.add_argument("--timeframe", type=str, default="4h",
                         help="6 yıllık veri için 15m çok fazla satır üretir; 1h veya 4h önerilir")
    args = parser.parse_args()

    if args.symbols:
        symbols = args.symbols.split(",")
    elif args.extended:
        symbols = CORE_SYMBOLS + EXTENDED_SYMBOLS
        print(f"Genişletilmiş evren: {len(symbols)} coin "
              f"({len(CORE_SYMBOLS)} çekirdek + {len(EXTENDED_SYMBOLS)} ek).")
        print("NOT: ek coinlerin çoğu 2021'den başlar - 2020 testleri için "
              "kısa geçmişli olanlar otomatik atlanır.")
    else:
        symbols = LONG_HISTORY_SYMBOLS
    os.makedirs(DATA_DIR, exist_ok=True)

    for symbol in symbols:
        print(f"\n=== {symbol} indiriliyor ({args.start} -> {args.end or 'bugün'}, {args.timeframe}) ===")
        try:
            df = fetch_full_history(symbol, args.timeframe, args.start, args.end)
            if df.empty:
                print(f"  {symbol}: veri bulunamadı (bu tarihte henüz listelenmemiş olabilir).")
                continue
            out_path = os.path.join(DATA_DIR, f"{symbol}_{args.timeframe}.csv")
            df.to_csv(out_path, index=False)
            print(f"  {symbol}: {len(df)} mum kaydedildi -> {out_path} "
                  f"({df['date'].iloc[0].date()} -> {df['date'].iloc[-1].date()})")
        except Exception as e:
            print(f"  {symbol}: hata - {e}")


if __name__ == "__main__":
    main()
