"""
Yıl Yıl Performans Analizi (2020 -> 2026)
=============================================
historical_fetch.py ile indirilen CSV'leri kullanarak, stratejinin HER YIL
ayrı ayrı nasıl performans gösterdiğini raporlar. Bu, "genel ortalama iyi"
görünen ama aslında tek bir yıldan (ör. 2021 bull run) beslenen ve diğer
yıllarda zarar eden bir stratejiyi yakalamak için kritiktir.

Kullanım:
    python historical_fetch.py --start 2020-01-01 --timeframe 4h   # önce veriyi indir
    python backtest_yearly.py --timeframe 4h                        # sonra analiz et
"""

import argparse
import glob
import os

import pandas as pd

import config
from backtest import simulate_range, simulate_range_managed, compute_metrics
from indicators import compute_all_indicators
from strategy import STRATEGY_VARIANTS
from data_quality import clean_ohlcv, stale_orani

# Veri klasörü. HISTORICAL_DATA_DIR ortam değişkeniyle değiştirilebilir:
#   HISTORICAL_DATA_DIR=historical_data_wide python3 ...
# (madde 111: eski historical_data verisinde yapay gürültü tespit edildi,
#  historical_data_wide = Binance'in resmi arşivinden indirilen temiz veri)
DATA_DIR = os.getenv("HISTORICAL_DATA_DIR", "historical_data")


def load_all_csvs(timeframe: str, clean: bool = True) -> dict:
    """historical_data/ içindeki tüm *_<timeframe>.csv dosyalarını yükler.

    clean=True (varsayılan): bozuk barlar (spike-and-revert veri hataları)
    otomatik onarılır. 2020-2021 Binance Futures verisi bu tür hatalar
    içeriyor (ör. BTCUSDT 2020-07-13: 9.400 -> 65.000 -> 11.299) ve bunlar
    backtest'te SAHTE KÂR üretiyor. Ölçüldü: temizlemeden 2020+ testi
    +1021.69R (3152 işlem), temizleyince +800.05R (2529 işlem) - yani
    623 işlem ve 221R tamamen veri hatasından geliyormuş. 2022+ döneminde
    fark ~0 (+0.90R), çünkü o dönem verisi zaten temiz.
    Ham veriyle çalışmak için clean=False verin.
    """
    data = {}
    for path in sorted(glob.glob(os.path.join(DATA_DIR, f"*_{timeframe}.csv"))):
        symbol = os.path.basename(path).replace(f"_{timeframe}.csv", "")
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        if clean:
            df = clean_ohlcv(df, symbol=symbol)
        data[symbol] = df
    if clean:
        _uyar_kirli_donem(data)
        _uyar_donuk_veri(data)
    return data


_DONUK_UYARI_VERILDI = False


def _uyar_donuk_veri(data: dict, esik: float = 0.10):
    """İleri doldurulmuş (donuk) verisi olan coinleri uyarır.

    Donuk bir coin hiç hareket etmez, kesitsel sıralamada hep ortada
    kalır ve KAYBETTİRMEZ - ama gerçekte o coin işlem görmüyor bile.
    Bu, backtest sonucunu yapay olarak İYİLEŞTİRİR.

    ÖLÇÜLDÜ (2022+, kesitsel bot):
      14 coin (donuk dahil) : yıllık +137.4%, Sharpe 3.10
      10 coin (donuk hariç) : yıllık  +74.9%, Sharpe 1.99
      rastgele 10 coin      : Sharpe 2.31  <- kontrol
    Düşüşün bir kısmı coin sayısından ama kalanı gerçekten donuk
    veriden geliyor.

    En uç örnek: EOSUSDT 2025-05-21'den itibaren 2869 bar (16 ay)
    boyunca open=high=low=close=0.78 - muhtemelen delist edilmiş.
    """
    global _DONUK_UYARI_VERILDI
    if _DONUK_UYARI_VERILDI:
        return
    donuk = []
    for sym, df in data.items():
        sub = df[df["date"].dt.year >= 2022] if "date" in df.columns else df
        if len(sub) > 100 and stale_orani(sub) >= esik:
            donuk.append(f"{sym} (%{stale_orani(sub)*100:.0f})")
    if donuk:
        print(f"[uyarı] DONUK VERİ: {', '.join(donuk)} - bu coinlerde fiyat "
              f"uzun süre hiç değişmiyor (ileri doldurulmuş/delist). Backtest "
              f"sonucunu YAPAY OLARAK İYİLEŞTİRİRLER. Gerçekçi tahmin için "
              f"bunları hariç tutmayı düşünün.")
        _DONUK_UYARI_VERILDI = True


_KIRLI_UYARI_VERILDI = False


def _uyar_kirli_donem(data: dict):
    """2020-2021 verisi temizleme SONRASI bile anormallikler içeriyor.

    Veri temizleyici (data_quality.py) tek bar spike'larını ve orta
    süreli bozuk blokları yakalıyor, ama 2020-21'de bozukluk o kadar
    yaygın ki ortanca penceresinin kendisi bozuluyor - bir kısmı
    kaçıyor. Ölçüldü (temizleme sonrası |bar getirisi| > %50):
        2020: 65 bar   2021: 120 bar
        2022: 0 bar    2023: 1    2024: 3    2025: 3    2026: 0

    Projedeki tüm ana backtest'ler 2022+ kullanıyor, bu yüzden
    sonuçlar etkilenmemiştir. Ama biri farkında olmadan 2020'den
    başlatırsa uyarılmalı.
    """
    global _KIRLI_UYARI_VERILDI
    if _KIRLI_UYARI_VERILDI:
        return
    for df in data.values():
        if (df["date"].dt.year < 2022).any():
            print("[uyarı] 2020-2021 verisi temizleme sonrası bile anormallikler "
                  "içeriyor (Binance Futures'ın ilk ayları). Güvenilir sonuç için "
                  "testleri 2022'den başlatın.")
            _KIRLI_UYARI_VERILDI = True
            return


def run_yearly_breakdown(variant_name: str, data: dict, timeframe: str, years: list,
                         portfolio_mode: bool = True,
                          use_management: bool = False):
    signal_fn = STRATEGY_VARIANTS[variant_name]
    cfg = config.STRATEGY
    mgmt = config.STRATEGY_MANAGEMENT.get(variant_name, config.STRATEGY_MANAGEMENT["breakout"])

    label = "KÂR KİLİTLEMELİ (özelleştirilmiş)" if use_management else "BASİT SL/TP"
    print(f"\n{'='*70}\n{variant_name.upper()} ({label}) - Yıl Yıl Sonuçlar\n{'='*70}")
    yearly_results = {}

    # ÖNEMLİ (düzeltme): İndikatörler TÜM veri üzerinde BİR KERE hesaplanır,
    # sonra sadece ilgili yılın bar ARALIĞI simüle edilir. Önceki versiyonda
    # veri önce yıllara bölünüp her yıl için indikatörler sıfırdan
    # hesaplanıyor ve simülasyon warmup=0'dan başlatılıyordu; bu iki hata
    # üretiyordu: (1) her yılın ilk ~60 barında ATR/EMA/return_n_pct henüz
    # "ısınmamış" olduğu halde işlem açılabiliyordu, (2) return_n_pct gibi
    # geriye bakan indikatörler 1 Ocak'ta sıfırlanıp önceki yılın verisini
    # göremiyordu. Ölçüldü: extreme_reversal'da ~%2 (-31R) sapma üretiyordu.
    WARMUP = 60
    full_ind = {sym: compute_all_indicators(df, cfg) for sym, df in data.items()}

    for year in years:
        year_trades = []
        yil_ind = {}
        for symbol, ind in full_ind.items():
            mask = ind["date"].dt.year == year
            if mask.sum() < 60:
                continue
            idx = ind.index[mask]
            start, end = max(int(idx[0]), WARMUP), int(idx[-1]) + 1
            if end - start < 10:
                continue
            if use_management:
                trades = simulate_range_managed(
                    symbol, ind, signal_fn, cfg, start, end,
                    breakeven_trigger_atr=mgmt["breakeven_trigger_atr"],
                    breakeven_buffer_pct=mgmt["breakeven_buffer_pct"],
                    partial_tp_r_multiple=mgmt["partial_tp_r_multiple"],
                    partial_tp_fraction=mgmt["partial_tp_fraction"],
                    trailing_atr_multiple=mgmt["trailing_atr_multiple"],
                    timeframe=timeframe,
                )
            else:
                trades = simulate_range(symbol, ind, signal_fn, cfg, start, end, timeframe=timeframe)
            year_trades.extend(trades)
            yil_ind[symbol] = ind.iloc[start:end].reset_index(drop=True)

        if portfolio_mode:
            # GERÇEK BOT KISITLARIYLA ölç: slot limiti, uygulama gecikmesi,
            # kademeli azaltma, max tutma. Bağımsız simülasyon (her coin
            # ayrı) 1.4-2.3 KAT şişik sonuç verir ve 2022'de İŞARET BİLE
            # DEĞİŞİR (+56.5R yerine gerçekte -11.1R).
            from portfolio_backtest import run_portfolio_backtest
            try:
                r = run_portfolio_backtest(
                    yil_ind, variant_name, config.RISK.max_concurrent_positions,
                    True, 0.7, 50, timeframe, exec_lag=1,
                    drawdown_scale_r=config.DRAWDOWN_SCALE_FULL_R,
                    max_hold_bars=int(config.MAX_HOLD_DAYS * 6),
                    strategy_cfg=cfg)
                m = {"trades": r["trades"], "win_rate": r["win_rate"],
                     "total_r": r["total_r"], "profit_factor": None,
                     "max_drawdown_r": r.get("max_drawdown_r")}
            except Exception:
                m = None
        else:
            m = compute_metrics(year_trades)
        yearly_results[year] = m
        if m:
            _pf = m.get("profit_factor")
            print(f"  {year}: {m['trades']:>4} işlem | kazanma=%{m['win_rate']:>5.1f} | "
                  f"toplamR={m['total_r']:>+7.2f}"
                  + (f" | PF={_pf:.2f}" if _pf else ""))
        else:
            print(f"  {year}: veri yok veya hiç işlem üretilmedi")

    valid = [m for m in yearly_results.values() if m]
    if valid:
        total_r_all = sum(m["total_r"] for m in valid)
        total_trades_all = sum(m["trades"] for m in valid)
        profitable_years = sum(1 for m in valid if m["total_r"] > 0)
        print(f"\n  ÖZET: {len(valid)} yılın {profitable_years} tanesinde net pozitif.")
        print(f"  Toplam R (tüm yıllar) = {total_r_all:+.2f} | Toplam işlem = {total_trades_all}")
        if profitable_years < len(valid) * 0.6:
            print("  UYARI: Yılların çoğunda kârlı değil -> strateji büyük olasılıkla")
            print("  belirli bir piyasa rejimine (ör. güçlü trend dönemine) bağımlı,")
            print("  her koşulda güvenilir değil.")

    return yearly_results


def main():
    parser = argparse.ArgumentParser(description="Yıl yıl geçmiş performans analizi")
    parser.add_argument("--fast", action="store_true",

                        help="Her coin BAĞIMSIZ simüle edilir (portföy kısıtı yok). "

                             "1.4-2.3 KAT şişik sonuç verir, 2022'de işaret bile "

                             "değişir. Sadece kaba karşılaştırma için.")

    parser.add_argument("--timeframe", type=str, default="4h")
    parser.add_argument("--years", type=str, default="2020,2021,2022,2023,2024,2025,2026")
    parser.add_argument("--compare-management", action="store_true",
                         help="Basit SL/TP ile 3-aşamalı kâr kilitlemeyi karşılaştır")
    args = parser.parse_args()
    years = [int(y) for y in args.years.split(",")]

    data = load_all_csvs(args.timeframe)
    if not data:
        print(f"'{DATA_DIR}/' klasöründe {args.timeframe} periyoduna ait veri bulunamadı.")
        print(f"Önce çalıştırın: python historical_fetch.py --timeframe {args.timeframe}")
        return

    print(f"{len(data)} coin için veri yüklendi: {', '.join(sorted(data.keys()))}")

    if not args.compare_management:
        all_results = {}
        for variant_name in STRATEGY_VARIANTS:
            all_results[variant_name] = run_yearly_breakdown(variant_name, data, args.timeframe, years, portfolio_mode=not args.fast)

        print(f"\n{'='*70}\nSTRATEJİLER ARASI KARŞILAŞTIRMA (yıl bazlı toplam R)\n{'='*70}")
        header = "Strateji".ljust(18) + "".join(str(y).rjust(10) for y in years)
        print(header)
        for variant_name, results in all_results.items():
            row = variant_name.ljust(18)
            for year in years:
                m = results.get(year)
                row += (f"{m['total_r']:+.1f}".rjust(10) if m else "-".rjust(10))
            print(row)
        return

    # --compare-management: basit vs kâr-kilitlemeli karşılaştırma
    print("\n### KÂR KİLİTLEME KARŞILAŞTIRMASI ###")
    comparison = {}
    for variant_name in STRATEGY_VARIANTS:
        simple = run_yearly_breakdown(variant_name, data, args.timeframe, years, use_management=False, portfolio_mode=not args.fast)
        managed = run_yearly_breakdown(variant_name, data, args.timeframe, years, use_management=True, portfolio_mode=not args.fast)
        comparison[variant_name] = (simple, managed)

    print(f"\n{'='*70}\nÖZET: KÂR KİLİTLEME NET ETKİSİ (toplam R, tüm yıllar)\n{'='*70}")
    print(f"{'Strateji':<18}{'Basit SL/TP':>14}{'Kâr Kilitleme':>16}{'Fark':>10}")
    for variant_name, (simple, managed) in comparison.items():
        simple_total = sum(m["total_r"] for m in simple.values() if m)
        managed_total = sum(m["total_r"] for m in managed.values() if m)
        diff = managed_total - simple_total
        verdict = "İYİLEŞTİ" if diff > 0 else ("KÖTÜLEŞTİ" if diff < 0 else "AYNI")
        print(f"{variant_name:<18}{simple_total:>+14.2f}{managed_total:>+16.2f}{diff:>+10.2f}  ({verdict})")

    print("\nNOT: Bu KARŞILAŞTIRMALI sonuç bile hâlâ VARSAYIM İÇERİR - kâr kilitleme")
    print("parametreleri (breakeven_trigger_atr, partial_tp_r_multiple, vb.) hiç")
    print("optimize edilmedi, config.py'daki ilk tahmini değerler kullanıldı.")
    print("'İYİLEŞTİ' çıkması bile kesin kanıt değildir - sadece bu parametrelerle,")
    print("bu veri setinde böyle çıktığı anlamına gelir.")


if __name__ == "__main__":
    main()
