"""DOKÜMAN DOĞRULUĞU: BASLANGIC.md'deki rakamlar üretilebiliyor mu?

KULLANIM: python test_doc_accuracy.py

Bu proje boyunca ayarlar defalarca değişti ve dokümanlar birkaç kez
eskidi (madde 100'de BASLANGIC.md 3-4 tur geriden geliyordu).

Bu test, BASLANGIC.md'deki manşet rakamların GÜNCEL KODLA
üretilebildiğini doğrular. Ayar değiştirip dokümanı güncellemezseniz
test hata verir.

Rakamları değiştirdiyseniz aşağıdaki 'iddia' sözlüğünü ve
BASLANGIC.md'yi BİRLİKTE güncelleyin.
"""
import sys; sys.path.insert(0,'.')
import numpy as np, config
from backtest_yearly import load_all_csvs
from indicators import compute_all_indicators
from crosssec_backtest import build_price_panel, run_crosssectional
from portfolio_backtest import run_portfolio_backtest
from data_quality import stale_orani
import crosssec_bot as cb

d=load_all_csvs('4h')
temiz={s:df for s,df in d.items() if stale_orani(df[df['date'].dt.year>=2022])<0.10}
print(f"temiz evren: {len(temiz)} coin (dokuman: 10)")
iddia={'coin':10,'cs_yillik':65.9,'cs_sharpe':1.54,'cs_dusus':-26.1,
       'sig_r':954.5,'sig_dusus':-28.6,'sig_kaz':67.0}
sonuc={'coin':len(temiz)}

# kesitsel - tum fazlar
P=build_price_panel(temiz); P=P[P.index.year>=2022]
H=[int(h*6) for h in cb.HORIZON_DAYS]
s=[]
for off in range(6):
    _,m=run_crosssectional(P.iloc[off:],60,6,cb.N_LEGS,horizons_bars=H,
                           pos_tp=cb.POSITION_TP_PCT/100,
                           trail_scale=cb.DRAWDOWN_SCALE_FULL_PCT/100,
                           compound=True,min_dispersion=cb.MIN_DISPERSION,
                           pos_sl=cb.EMERGENCY_STOP_PCT/100)
    s.append(m)
sonuc['cs_yillik']=float(np.mean([x['cagr_pct'] for x in s]))
sonuc['cs_sharpe']=float(np.mean([x['sharpe'] for x in s]))
sonuc['cs_dusus']=float(np.mean([x['max_drawdown_pct'] for x in s]))

# sinyal
sd={}
for sym,df in temiz.items():
    sub=df[df['date'].dt.year>=2022].reset_index(drop=True)
    if len(sub)>300: sd[sym]=compute_all_indicators(sub,config.STRATEGY)
r=run_portfolio_backtest(sd,config.ACTIVE_STRATEGY,config.RISK.max_concurrent_positions,
                         True,0.7,50,'4h',exec_lag=1,
                         drawdown_scale_r=config.DRAWDOWN_SCALE_FULL_R,
                         max_hold_bars=int(config.MAX_HOLD_DAYS*6))
sonuc['sig_r']=r['total_r']; sonuc['sig_dusus']=-r['max_drawdown_r']
sonuc['sig_kaz']=r['win_rate']

print()
print(f"{'olcut':<16} {'dokuman':>10} {'gercek':>10} {'fark':>9} {'durum':>8}")
print('-'*58)
hata=0
for k in iddia:
    a=iddia[k]; b=sonuc[k]
    fark=abs(b-a)/max(abs(a),1e-9)*100
    ok = fark<3.0
    if not ok: hata+=1
    print(f'{k:<16} {a:>10.1f} {b:>10.1f} {fark:>8.1f}% {"OK" if ok else "SAPMA":>8}')
print()
if hata:
    print(f"!!! {hata} rakam dokumanla UYUSMUYOR")
    print("    BASLANGIC.md ve bu testteki 'iddia' sozlugunu guncelleyin.")
    sys.exit(1)
print("TUM RAKAMLAR DOGRULANDI (%3 tolerans)")
print("DOKUMAN DOGRULUK TESTI GECTI")
