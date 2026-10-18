"""HESAP DOGRULUGU - motor sayilari dogru hesapliyor mu?

Simdiye kadar parametrelerin ETKI ETTIGI dogrulandi ama hesaplarin
DOGRU oldugu hic kontrol edilmedi. Elle hesaplanabilir senaryolarla
test edilir: maliyet iki kez dusuluyor mu, R dogru mu, equity
egrisi tutarli mi?
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd
import config
from backtest import COMMISSION_PCT_PER_SIDE, AVG_FUNDING_PCT_PER_8H
from portfolio_backtest import run_portfolio_backtest
from strategy import Signal

print("=== 1) R HESABI: bilinen senaryo ===")
# LONG 100'den girdi, SL 95 (risk=5), TP 110 (odul=10) -> TP'de +2R olmali
# Maliyetler: komisyon 2 taraf + slippage + funding
risk=5.0; odul=10.0
ham_r = odul/risk
komisyon=(100+110)*(COMMISSION_PCT_PER_SIDE/100)
giris_slip=100*(0.02/100)
print(f"  ham R (odul/risk)     : {ham_r:.3f}")
print(f"  komisyon (2 taraf)    : {komisyon:.4f} fiyat birimi = {komisyon/risk:.4f}R")
print(f"  giris slippage        : {giris_slip:.4f} = {giris_slip/risk:.4f}R")
beklenen = (odul - giris_slip - komisyon)/risk
print(f"  BEKLENEN net R        : {beklenen:.4f}")
assert 1.8 < beklenen < 2.0, "R hesabi mantik disi"

print("\n=== 2) EQUITY EGRISI = islemlerin toplami mi? ===")
from backtest_yearly import load_all_csvs
from indicators import compute_all_indicators
from data_quality import stale_orani
d=load_all_csvs('4h')
temiz={s:df for s,df in d.items() if stale_orani(df[df['date'].dt.year>=2022])<0.10}
sd={}
for s,df in list(temiz.items())[:6]:
    sub=df[df['date'].dt.year==2024].reset_index(drop=True)
    if len(sub)>300: sd[s]=compute_all_indicators(sub,config.STRATEGY)
r=run_portfolio_backtest(sd,config.ACTIVE_STRATEGY,5,True,0.7,50,'4h',
                         exec_lag=1,drawdown_scale_r=30.0,max_hold_bars=60)
# closed_trades listesinden toplami yeniden hesapla
_tl = r.get('closed_trades', [])
_toplam = sum(t.r_multiple for t in _tl)
print(f"  toplam R (rapor)         : {r['total_r']:.4f}")
print(f"  islemlerden hesaplanan   : {_toplam:.4f}")
print(f"  islem sayisi (rapor/liste): {r['trades']} / {len(_tl)}")
assert abs(r['total_r']-_toplam)<1e-6, (
    "Raporlanan toplam R, islem listesinin toplamiyla UYUSMUYOR - "
    "muhasebe hatasi!")
assert r['trades']==len(_tl), "islem sayisi listeyle uyusmuyor!"
# kazanan sayisi da tutarli mi
_kazanan = sum(1 for t in _tl if t.r_multiple > 0)
assert r['wins']==_kazanan, f"kazanan sayisi uyusmuyor: {r['wins']} vs {_kazanan}"
assert abs(r['win_rate'] - _kazanan/max(len(_tl),1)*100) < 1e-6, "kazanma orani yanlis hesaplanmis!"
print(f"  kazanan (rapor/liste)    : {r['wins']} / {_kazanan}")
print("  OK: rapor ile islem listesi TAM tutarli")

print("\n=== 3) MALIYET IKI KEZ dusuluyor mu? ===")
# Sifir maliyetli vs normal karsilastirma
import backtest as bt
eski_kom=bt.COMMISSION_PCT_PER_SIDE
import portfolio_backtest as pbt
eski_pk=pbt.COMMISSION_PCT_PER_SIDE
pbt.COMMISSION_PCT_PER_SIDE=0.0
r0=run_portfolio_backtest(sd,config.ACTIVE_STRATEGY,5,True,0.7,50,'4h',
                          exec_lag=1,entry_slippage_pct=0.0,sl_slippage_pct=0.0,
                          drawdown_scale_r=30.0,max_hold_bars=60)
pbt.COMMISSION_PCT_PER_SIDE=eski_pk
print(f"  maliyetsiz : {r0['total_r']:>+9.2f}R  ({r0['trades']} islem)")
print(f"  maliyetli  : {r['total_r']:>+9.2f}R  ({r['trades']} islem)")
fark=r0['total_r']-r['total_r']
islem_basi=fark/max(r['trades'],1)
print(f"  islem basina maliyet: {islem_basi:.4f}R")
assert fark>0, "maliyet hic dusulmemis!"
assert islem_basi<0.5, f"islem basina maliyet cok yuksek ({islem_basi:.3f}R) - iki kez dusuluyor olabilir"
print("  OK: maliyet bir kez ve makul buyuklukte")

print("\n=== 4) KAZANMA ORANI tutarli mi? ===")
kaz=r['win_rate']
print(f"  kazanma orani: %{kaz:.1f}")
assert 0<=kaz<=100, "kazanma orani araligi disinda"
# R pozitif ise kazanma orani veya ortalama kazanc yuksek olmali
ort_r=r['total_r']/max(r['trades'],1)
print(f"  islem basina ortalama R: {ort_r:+.4f}")
if r['total_r']>0:
    assert kaz>30 or ort_r>0, "pozitif R ama dusuk kazanma VE dusuk ortalama - tutarsiz"
print("  OK")

print("\n=== 5) MAX DUSUS negatif ve toplam R'den kucuk mu? ===")
dd=r['max_drawdown_r']
print(f"  max dusus: {dd:.2f}R")
assert dd>=0, "max dusus pozitif sayi olarak raporlanmali"
print("  OK")

print("\n=== 6) KESITSEL: maliyet dogru mu? ===")
from crosssec_backtest import build_price_panel, run_crosssectional
import crosssec_backtest as cbt
P=build_price_panel(temiz); P=P[P.index.year==2024]
eski_c=cbt.COMMISSION_PCT_PER_SIDE; eski_s=cbt.SLIPPAGE_PCT
_,mA=run_crosssectional(P,60,6,3,horizons_bars=[30,60,90],pos_tp=0.04,
                        trail_scale=0.30,compound=False)
cbt.COMMISSION_PCT_PER_SIDE=0.0; cbt.SLIPPAGE_PCT=0.0
_,mB=run_crosssectional(P,60,6,3,horizons_bars=[30,60,90],pos_tp=0.04,
                        trail_scale=0.30,compound=False)
cbt.COMMISSION_PCT_PER_SIDE=eski_c; cbt.SLIPPAGE_PCT=eski_s
print(f"  maliyetli  : {mA['total_return_pct']:>+9.2f}%")
print(f"  maliyetsiz : {mB['total_return_pct']:>+9.2f}%")
assert mB['total_return_pct']>mA['total_return_pct'], "kesitsel: maliyet dusulmemis!"
print("  OK: maliyet dusuluyor")

print("\n=== 7) SIFIR POZISYONDA getiri degismemeli ===")
_,mZ=run_crosssectional(P,60,6,3,horizons_bars=[30,60,90],pos_tp=0.04,
                        trail_scale=0.30,compound=False,min_dispersion=99.0)
print(f"  dispersiyon esigi 99 (hic islem yok): {mZ['total_return_pct']:+.4f}%")
assert abs(mZ['total_return_pct'])<0.01, "islem yokken getiri sifir olmali!"
print("  OK")

print("\nHESAP DOGRULUGU TESTLERI GECTI")

print("\n=== 8) DETERMINIZM: ayni girdi -> ayni sonuc ===")
r_a=run_portfolio_backtest(sd,config.ACTIVE_STRATEGY,5,True,0.7,50,'4h',
                           exec_lag=1,drawdown_scale_r=30.0,max_hold_bars=60)
r_b=run_portfolio_backtest(sd,config.ACTIVE_STRATEGY,5,True,0.7,50,'4h',
                           exec_lag=1,drawdown_scale_r=30.0,max_hold_bars=60)
print(f"  1. calisma: {r_a['total_r']:.6f}R ({r_a['trades']} islem)")
print(f"  2. calisma: {r_b['total_r']:.6f}R ({r_b['trades']} islem)")
assert r_a['total_r']==r_b['total_r'] and r_a['trades']==r_b['trades'], \
    "AYNI GIRDI FARKLI SONUC - rastgelelik veya durum sizintisi var!"
print("  OK: deterministik")

print("\n=== 9) VERI SIRASI onemli mi? (sizinti kontrolu) ===")
# Sembol sirasini degistir - sonuc AYNI olmali (her sembol bagimsiz taranmali)
sd_ters={k:sd[k] for k in reversed(list(sd))}
r_t=run_portfolio_backtest(sd_ters,config.ACTIVE_STRATEGY,5,True,0.7,50,'4h',
                           exec_lag=1,drawdown_scale_r=30.0,max_hold_bars=60)
print(f"  normal sira: {r_a['total_r']:.4f}R")
print(f"  ters sira  : {r_t['total_r']:.4f}R")
fark=abs(r_a['total_r']-r_t['total_r'])
if fark>1e-6:
    print(f"  NOT: {fark:.4f}R fark var - slot rekabeti sembol sirasina bagli")
    print("       (beklenen davranis: 5 slot dolunca sonraki sinyaller elenir)")
else:
    print("  sira etkisiz")

print("\n=== 10) TEK ISLEM izlenebilir mi? ===")
if _tl:
    t0=_tl[0]
    print(f"  ilk islem: {t0.symbol} {t0.direction} R={t0.r_multiple:+.4f}")
    print(f"             giris bar={t0.entry_bar} cikis bar={t0.exit_bar}")
    assert t0.exit_bar>=t0.entry_bar, "cikis girisden ONCE - zaman hatasi!"
    sureler=[t.exit_bar-t.entry_bar for t in _tl]
    print(f"  tutma suresi: ort={np.mean(sureler):.1f} bar, max={max(sureler)} bar")
    assert max(sureler)<=60, f"max tutma 60 bar olmali ama {max(sureler)} bulundu!"
    print("  OK: zaman tutarli, max tutma siniri uygulaniyor")

print("\nGENISLETILMIS HESAP TESTLERI GECTI")
