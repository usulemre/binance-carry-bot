"""
Sabit Saatte Karar, Sabit Süre Tutma - Test Scripti (Anahtarsız)
=====================================================================

!!! UYARI - BU FİKİR REDDEDİLDİ (README madde 51) !!!
Sabit süre tutma test edildi ve AÇIKÇA ZARARLI çıktı:
    bekleme yok : OOS +93.7R (kazanma %57.3)
    2 gün bekle : OOS  -3.0R (kazanma %44.6)
    5 gün bekle : OOS -27.9R (kazanma %35.6)
Sebep: TP bastırılınca kazanan pozisyonlar kâr noktasından geri dönüp
SL'e gidiyor. Giriş saati filtresi de faydasız çıktı.

!!! AYRICA: PORTFÖY KISITI YOK (README madde 106) !!!
Bu araç simulate_range kullanıyor - her coin BAĞIMSIZ simüle ediliyor.
Slot limiti, uygulama gecikmesi ve korumalar yok. Sonuçlar 1.4-2.3 KAT
şişik çıkar; 2022'de işaret bile değişebilir.

Bu script referans olarak duruyor ama SONUÇLARINA GÜVENMEYİN.
Gerçek ölçüm için portfolio_backtest.py kullanın.
=====================================================================
"03:00'da karar ver, 3 gün sabit tut, sonra yeni karar" tarzı yürütmeyi
gerçek geçmiş veriyle test eder. historical_fetch.py ile indirilmiş
CSV'leri kullanır (bkz. README "Uzun Vadeli Tarihsel Analiz" bölümü).

Kullanım:
    python historical_fetch.py --start 2023-01-01 --timeframe 4h
    python time_based_backtest.py --timeframe 4h --decision-hour 3 --holding-days 3
"""

import argparse
import glob
import os

import pandas as pd

import config
from backtest import simulate_time_based_range, simulate_range, compute_metrics
from indicators import compute_all_indicators
from strategy import STRATEGY_VARIANTS
from backtest import _timeframe_to_minutes

DATA_DIR = "historical_data"


def load_all_csvs(timeframe: str) -> dict:
    pattern = os.path.join(DATA_DIR, f"*_{timeframe}.csv")
    data = {}
    for path in glob.glob(pattern):
        symbol = os.path.basename(path).replace(f"_{timeframe}.csv", "")
        data[symbol] = pd.read_csv(path, parse_dates=["date"])
    return data


def main():
    parser = argparse.ArgumentParser(description="Sabit saat/sabit süre tutma testi")
    parser.add_argument("--timeframe", type=str, default="4h")
    parser.add_argument("--strategy", type=str, default="trend_momentum", choices=list(STRATEGY_VARIANTS.keys()))
    parser.add_argument("--decision-hour", type=int, default=3, help="UTC saat (0-23)")
    parser.add_argument("--holding-days", type=float, default=3.0)
    args = parser.parse_args()

    data = load_all_csvs(args.timeframe)
    if not data:
        print(f"'{DATA_DIR}/' klasöründe veri yok. Önce: python historical_fetch.py --timeframe {args.timeframe}")
        return

    tf_minutes = _timeframe_to_minutes(args.timeframe)
    holding_bars = int(args.holding_days * 1440 / tf_minutes)
    signal_fn = STRATEGY_VARIANTS[args.strategy]
    cfg = config.STRATEGY

    print(f"{len(data)} coin yüklendi. Karar saati: {args.decision_hour}:00 UTC, "
          f"tutma süresi: {args.holding_days} gün ({holding_bars} bar)\n")

    time_trades, normal_trades = [], []
    for symbol, df in data.items():
        ind = compute_all_indicators(df, cfg)
        time_trades.extend(simulate_time_based_range(
            symbol, ind, signal_fn, cfg, args.decision_hour, holding_bars, timeframe=args.timeframe))
        normal_trades.extend(simulate_range(symbol, ind, signal_fn, cfg, 60, len(ind), timeframe=args.timeframe))

    m_time = compute_metrics(time_trades)
    m_normal = compute_metrics(normal_trades)

    print("=== SABİT SAAT / SABİT SÜRE ===")
    print(m_time or "İşlem yok")
    print("\n=== NORMAL (her an karar, SL/TP ile çıkış) ===")
    print(m_normal or "İşlem yok")

    print("\nNOT: Bu iki yaklaşım FARKLI sayıda işlem üretir (biri sadece belirli")
    print("saatte karar verir), doğrudan kıyaslama kaba bir fikir verir, kesin")
    print("kanıt değildir. Trend piyasasında sabit süre genelde kazananı daha")
    print("uzun taşır; yatay piyasada kaybedeni de daha uzun taşıyabilir -")
    print("bu yüzden ADX trend teyidiyle birlikte kullanılması önerilir.")


if __name__ == "__main__":
    main()
