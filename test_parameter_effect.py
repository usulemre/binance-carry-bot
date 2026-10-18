"""KAPSAMLI PARAMETRE ETKİ DENETİMİ.

KULLANIM: python test_parameter_effect.py

Her backtest parametresini iki farklı değerle çalıştırıp sonucun
GERÇEKTEN değiştiğini doğrular. Aynı sonuç çıkıyorsa parametre
sessizce yok sayılıyor demektir.

Yeni bir parametre eklendiğinde bu teste de eklenmeli.

ORİJİNAL AÇIKLAMA:

Bu projede tekrar eden hata sinifi: bir parametre kabul ediliyor ama
SONUCU DEGISTIRMIYOR (sessiz no-op). Ornekler:
  madde 68: testnet parametresi hic kullanilmiyordu
  madde 94: dispersiyon filtresi backtestte yoktu
  madde 96: kademeli azaltma/max tutma backtestte yoktu
  madde 97: strategy_cfg sinyal uretimine gecmiyordu

Bu denetim HER parametreyi iki farkli degerle calistirip sonucun
gercekten degistigini dogrular.
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, config, inspect
from dataclasses import replace
from backtest_yearly import load_all_csvs
from indicators import compute_all_indicators
from portfolio_backtest import run_portfolio_backtest
from crosssec_backtest import build_price_panel, run_crosssectional
from data_quality import stale_orani

d=load_all_csvs('4h')
temiz={s:df for s,df in d.items() if stale_orani(df[df['date'].dt.year>=2022])<0.10}
P=build_price_panel(temiz); P=P[(P.index.year>=2023)&(P.index.year<=2024)]
H=[30,60,90]

sorunlar=[]
def kontrol(ad, a, b, aciklama=""):
    ayni = (a==b) if not isinstance(a,float) else abs(a-b)<1e-9
    if ayni:
        sorunlar.append(ad)
        print(f"  !!!! {ad:<34} ETKISIZ (ikisi de {a})")
    else:
        print(f"  OK   {ad:<34} {a} -> {b}")

print("="*64)
print("A) KESITSEL BACKTEST PARAMETRELERI")
print("="*64)
def cs(**kw):
    varsayilan=dict(horizons_bars=H,pos_tp=0.04,trail_scale=0.30,compound=True,
                    min_dispersion=None,pos_sl=None,exec_lag=1)
    varsayilan.update(kw)
    _,m=run_crosssectional(P,60,6,3,**varsayilan)
    return round(m['total_return_pct'],4)

kontrol("horizons_bars",  cs(horizons_bars=H), cs(horizons_bars=[60]))
kontrol("pos_tp",         cs(pos_tp=0.04), cs(pos_tp=0.15))
kontrol("pos_sl",         cs(pos_sl=None), cs(pos_sl=0.10))
kontrol("trail_scale",    cs(trail_scale=0.30), cs(trail_scale=None))
kontrol("min_dispersion", cs(min_dispersion=None), cs(min_dispersion=0.05))
kontrol("exec_lag",       cs(exec_lag=1), cs(exec_lag=0))
kontrol("compound",       cs(compound=True), cs(compound=False))
_,m1=run_crosssectional(P,60,6,3,horizons_bars=H,pos_tp=0.04,compound=True)
_,m2=run_crosssectional(P,60,6,5,horizons_bars=H,pos_tp=0.04,compound=True)
kontrol("n_legs", round(m1['total_return_pct'],4), round(m2['total_return_pct'],4))
_,m3=run_crosssectional(P,60,18,3,horizons_bars=H,pos_tp=0.04,compound=True)
kontrol("rebalance_bars", round(m1['total_return_pct'],4), round(m3['total_return_pct'],4))
_,m4=run_crosssectional(P,60,6,3,horizons_bars=H,pos_tp=0.04,compound=True,gross_exposure=2.0)
kontrol("gross_exposure", round(m1['total_return_pct'],4), round(m4['total_return_pct'],4))

print()
print("="*64)
print("B) SINYAL BOTU BACKTEST PARAMETRELERI")
print("="*64)
def sig_veri(cfg):
    out={}
    for s,df in temiz.items():
        sub=df[(df['date'].dt.year>=2023)&(df['date'].dt.year<=2024)].reset_index(drop=True)
        if len(sub)>300: out[s]=compute_all_indicators(sub,cfg)
    return out
base=config.STRATEGY
SD=sig_veri(base)
def sg(cfg=None, **kw):
    varsayilan=dict(max_concurrent=5,correlation_filter=True,correlation_threshold=0.7,
                    correlation_lookback=50,timeframe='4h',exec_lag=1,
                    drawdown_scale_r=30.0,max_hold_bars=60,strategy_cfg=cfg)
    varsayilan.update(kw)
    sd = sig_veri(cfg) if cfg is not None else SD
    r=run_portfolio_backtest(sd,'extreme_reversal',**varsayilan)
    return round(r['total_r'],4)

kontrol("exec_lag",          sg(exec_lag=1), sg(exec_lag=0))
kontrol("drawdown_scale_r",  sg(drawdown_scale_r=30.0), sg(drawdown_scale_r=None))
kontrol("max_hold_bars",     sg(max_hold_bars=60), sg(max_hold_bars=None))
kontrol("max_concurrent",    sg(max_concurrent=5), sg(max_concurrent=2))
kontrol("correlation_filter",sg(correlation_filter=True), sg(correlation_filter=False))
kontrol("correlation_threshold", sg(correlation_threshold=0.7), sg(correlation_threshold=0.2))
kontrol("entry_slippage_pct", sg(entry_slippage_pct=0.02), sg(entry_slippage_pct=0.5))
kontrol("sl_slippage_pct",    sg(sl_slippage_pct=0.05), sg(sl_slippage_pct=1.0))
kontrol("strategy_cfg: esik", sg(cfg=replace(base,extreme_threshold_pct=8.0)),
                              sg(cfg=replace(base,extreme_threshold_pct=20.0)))
kontrol("strategy_cfg: ATR",  sg(cfg=replace(base,atr_sl_multiplier=1.0)),
                              sg(cfg=replace(base,atr_sl_multiplier=3.0)))
kontrol("strategy_cfg: retrace", sg(cfg=replace(base,extreme_retrace_fraction=0.3)),
                                 sg(cfg=replace(base,extreme_retrace_fraction=0.7)))
kontrol("strategy_cfg: lookback", sg(cfg=replace(base,extreme_lookback=10)),
                                  sg(cfg=replace(base,extreme_lookback=50)))

print()
print("="*64)
if sorunlar:
    print(f"!!! {len(sorunlar)} ETKISIZ PARAMETRE BULUNDU:")
    for x in sorunlar: print(f"    - {x}")
else:
    print("TUM PARAMETRELER GERCEKTEN ETKI EDIYOR.")
print("="*64)


# Test cikis kodu
if sorunlar:
    sys.exit(1)
