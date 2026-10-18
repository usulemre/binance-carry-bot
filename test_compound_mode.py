"""BILESIK MOD testleri.

Bulunan hata: kademeli azaltma korumasi dususu PUAN cinsinden olcuyordu.
Bilesik modda sermaye buyudukce ayni YUZDE dusus cok daha fazla puan
eder -> koruma kalici olarak sifirda kilitlenir ve bot tamamen durur.
(Kanit: sermaye 2024'te 11.650'ye cikip 2025-2026 boyunca HIC degismemisti.)
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd
from backtest_yearly import load_all_csvs
from crosssec_backtest import build_price_panel, run_crosssectional
from data_quality import stale_orani

d=load_all_csvs('4h')
temiz={s:df for s,df in d.items() if stale_orani(df[df['date'].dt.year>=2022])<0.10}
P=build_price_panel(temiz); P=P[P.index.year>=2022]
H=[30,60,90]

print("=== 1) Bilesik modda bot DURMUYOR mu? ===")
eq,m=run_crosssectional(P,60,6,3,horizons_bars=H,pos_tp=0.04,trail_scale=0.30,compound=True)
# son yilda equity degisiyor mu?
son_yil=eq[eq.index.year==eq.index.year.max()]
degisim=son_yil.nunique()
print(f"   son yilda benzersiz equity degeri: {degisim} (>10 olmali)")
assert degisim>10, "BILESIK MODDA BOT DURMUS - koruma kilitlenmis!"

print("\n=== 2) Bilesik vs sabit: Sharpe benzer olmali ===")
_,ms=run_crosssectional(P,60,6,3,horizons_bars=H,pos_tp=0.04,trail_scale=0.30,compound=False)
print(f"   sabit  : Sharpe={ms['sharpe']:.2f} maxDusus={ms['max_drawdown_pct']:.1f}%")
print(f"   bilesik: Sharpe={m['sharpe']:.2f} maxDusus={m['max_drawdown_pct']:.1f}%")
assert abs(m['sharpe']-ms['sharpe'])<0.5, (
    "Bilesik ve sabit Sharpe cok farkli - koruma mekanizmasi modlar "
    "arasinda tutarsiz calisiyor olabilir.")
print("   tutarli (bilesik bedava kazanc degil, sadece kar yeniden yatirimi)")

print("\n=== 3) Bilesik getiri sabitten YUKSEK olmali ===")
print(f"   sabit  : yillik {ms['cagr_pct']:+.1f}%")
print(f"   bilesik: yillik {m['cagr_pct']:+.1f}%")
assert m['cagr_pct']>ms['cagr_pct'], "bilesik daha dusuk - mantik hatasi!"

print("\n=== 4) Dusus ORANSAL mi olculuyor? (kod kontrolu) ===")
import inspect, crosssec_backtest as cb
src=inspect.getsource(cb.run_crosssectional)
assert 'if compound:' in src and '/ peak' in src, (
    "Dusus hesabi compound moda gore ayrilmamis - puan cinsinden olcum "
    "bilesik modda korumayi kilitler!")
print("   compound modda oransal, sabit modda puan: OK")

print("\n=== 5) Kucuk sermayede likidite kisiti yok mu? ===")
import crosssec_bot as B
for sermaye in [2000, 10000, 100000]:
    poz = sermaye*(B.GROSS_EXPOSURE/2)/B.N_LEGS
    print(f"   {sermaye:>7,} USDT -> pozisyon {poz:>8,.0f} USDT "
          f"(likidite esigi {B.MIN_DEPTH_USDT:,.0f})")
    assert poz < B.MIN_DEPTH_USDT, f"{sermaye} USDT'de pozisyon likidite esigini asiyor"
print("   bu sermaye araliginda bilesik gercekci: OK")

print("\nBILESIK MOD TESTLERI GECTI")
