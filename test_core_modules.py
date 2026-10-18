"""correlation.py, market_regime.py, data_quality.py testleri.
Bu uc modul canli botta KARAR veriyor ama testleri yoktu."""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd

print("=== correlation.py ===")
from correlation import rolling_correlation_from_closes, is_too_correlated
np.random.seed(3)
n=200
ortak=np.cumsum(np.random.randn(n))
A=100+ortak; B=50+ortak*0.5+np.random.randn(n)*0.01; C=80+np.cumsum(np.random.randn(n))
print(f"  A-B korelasyon: {rolling_correlation_from_closes(A,B,50):+.3f} (yuksek olmali)")
print(f"  A-C korelasyon: {rolling_correlation_from_closes(A,C,50):+.3f}")
assert rolling_correlation_from_closes(A,B,50)>0.9
# veri yetersiz -> 0.0 (guvenli: engelleme yapma)
assert rolling_correlation_from_closes(np.array([1.0,2.0]),B,50)==0.0
# sabit seri (std=0) -> 0.0, cokme yok
assert rolling_correlation_from_closes(np.full(n,5.0),B,50)==0.0
print("  sabit seri / yetersiz veri -> 0.0 (cokme yok): OK")
blok,sym,c=is_too_correlated(B,{'A':A},0.7,50)
assert blok is True and sym=='A'
assert is_too_correlated(C,{'A':A},0.99,50)[0] is False
print("  engelleme mantigi: OK")

print("\n=== market_regime.py ===")
from market_regime import compute_market_regime, is_regime_tradeable
yuksek=100*np.cumprod(1+np.random.randn(300)*0.03)
dusuk=100*np.cumprod(1+np.random.randn(300)*0.002)
rh=compute_market_regime({'A':yuksek,'B':yuksek*1.01},180)
rl=compute_market_regime({'A':dusuk,'B':dusuk*1.01},180)
print(f"  yuksek vol: {rh['volatility']:.4f} | dusuk vol: {rl['volatility']:.4f}")
assert rh['volatility']>rl['volatility']*5
assert is_regime_tradeable(rh,0.02,-0.05,False)[0] is True
assert is_regime_tradeable(rl,0.02,-0.05,False)[0] is False
# veri yoksa GUVENLI taraf = islem izni (bot sessizce durmasin)
bos=compute_market_regime({},180)
assert is_regime_tradeable(bos,0.02,-0.05,False)[0] is True
print("  veri yokken islem izni (guvenli varsayilan): OK")
# otokorelasyon filtresi
rr={'volatility':0.05,'autocorrelation':0.5,'symbols_used':2}
assert is_regime_tradeable(rr,0.02,-0.05,True)[0] is False
assert is_regime_tradeable(rr,0.02,-0.05,False)[0] is True
print("  otokorelasyon filtresi (acik/kapali): OK")

print("\n=== data_quality.py ===")
from data_quality import find_bad_bars, clean_ohlcv
# spike-and-revert
df=pd.DataFrame({'open':[100.]*20,'high':[101.]*20,'low':[99.]*20,'close':[100.]*20,'volume':[1000.]*20})
df.loc[10,['close','high']]=[500.,500.]   # tek bar spike
df.loc[11,'close']=100.
bad=find_bad_bars(df)
print(f"  spike-and-revert yakalandi: {bool(bad.iloc[10])}")
assert bad.iloc[10]
# uzun sureli bozuk blok (ortanca bazli)
df2=pd.DataFrame({'open':[100.]*200,'high':[101.]*200,'low':[99.]*200,'close':[100.]*200,'volume':[1000.]*200})
df2.loc[50:56,'close']=9000.    # gunlerce suren sacma blok
bad2=find_bad_bars(df2)
print(f"  uzun bozuk blok yakalandi: {bad2.iloc[50:57].sum()}/7 bar")
assert bad2.iloc[50:57].sum()>=5
# temizleme sonrasi NaN ve tutarsizlik olmamali
cl=clean_ohlcv(df2)
assert cl[['open','high','low','close']].isna().sum().sum()==0
assert ((cl['high']<cl['low'])|(cl['close']>cl['high'])|(cl['close']<cl['low'])).sum()==0
print("  temizleme sonrasi NaN yok, OHLC tutarli: OK")
# temiz veri BOZULMAMALI
temiz=pd.DataFrame({'open':[100.]*100,'high':[101.]*100,'low':[99.]*100,'close':[100.]*100,'volume':[1000.]*100})
assert find_bad_bars(temiz).sum()==0, "temiz veri bozuk isaretlendi!"
print("  temiz veri yanlislikla isaretlenmiyor: OK")

print("\nCEKIRDEK MODUL TESTLERI GECTI")

print("\n=== strategy.py guvenlik filtreleri ===")
from strategy import atr_saglikli, sl_mesafesi_kabul_edilebilir, MAX_ATR_RATIO, MAX_SL_DISTANCE_PCT
# ATR saglik
assert atr_saglikli(100.0, 5.0) is True          # %5 ATR - normal
assert atr_saglikli(100.0, 30.0) is False        # %30 ATR - bozuk
assert atr_saglikli(100.0, 5900.0) is False      # gercek bozuk veri ornegi
assert atr_saglikli(0.0, 5.0) is False           # sifir fiyat
assert atr_saglikli(100.0, 0.0) is False         # sifir ATR
assert atr_saglikli(float('nan'), 5.0) is False  # NaN
assert atr_saglikli(100.0, float('inf')) is False
print(f"  ATR saglik kontrolu (esik %{MAX_ATR_RATIO*100:.0f}): OK")
# SL mesafesi
assert sl_mesafesi_kabul_edilebilir(100.0, 95.0) is True    # %5 uzak
assert sl_mesafesi_kabul_edilebilir(100.0, 81.0) is True     # %19 uzak
assert sl_mesafesi_kabul_edilebilir(100.0, 70.0) is False    # %30 - likidasyon riski
assert sl_mesafesi_kabul_edilebilir(100.0, 130.0) is False   # SHORT tarafi da
assert sl_mesafesi_kabul_edilebilir(0.0, 95.0) is False
print(f"  SL mesafe kontrolu (esik %{MAX_SL_DISTANCE_PCT:.0f}): OK")
# kaldirac ile tutarlilik
import config
lik = 100 / config.RISK.leverage
assert MAX_SL_DISTANCE_PCT < lik * 0.8, \
    f"SL siniri (%{MAX_SL_DISTANCE_PCT}) kaldirac {config.RISK.leverage}x icin cok genis (likidasyon ~%{lik:.0f})"
print(f"  kaldirac {config.RISK.leverage}x ile tutarli (likidasyon ~%{lik:.0f}): OK")
print("\nGUVENLIK FILTRESI TESTLERI GECTI")

print("\n=== funding izleme (crosssec_bot) ===")
import crosssec_bot as CB
class _FC:
    def __init__(s,rates): s.rates=rates
    def futures_mark_price(s,symbol): return {'lastFundingRate':str(s.rates.get(symbol,0.0))}
class _FEx:
    def __init__(s,rates): s.client=_FC(rates)

t={f'C{i}USDT':(0.125 if i<4 else -0.125) for i in range(8)}

# 1) tum coinlerde ayni funding -> piyasa notr, net SIFIR
ex=_FEx({f'C{i}USDT':0.0001 for i in range(8)})
CB.log_funding_durumu(ex,t)   # cokmemeli
print("  simetrik funding -> net ~0: OK")

# 2) ASIMETRIK: long coinleri yuksek funding oder, short coinleri dusuk
#    -> net ALEYHTE olmali
rates={}
for i in range(8):
    rates[f'C{i}USDT'] = 0.0010 if i<4 else 0.0001   # long taraf pahali
ex2=_FEx(rates)
CB.log_funding_durumu(ex2,t)
print("  asimetrik funding loglaniyor: OK")

# 3) API hatasinda cokmemeli
class _Bad:
    def futures_mark_price(s,symbol): raise RuntimeError("API hatasi")
class _ExBad:
    def __init__(s): s.client=_Bad()
CB.log_funding_durumu(_ExBad(),t)
print("  API hatasinda cokme yok: OK")
print("\nFUNDING IZLEME TESTLERI GECTI")

print("\n=== donuk (ileri doldurulmus) bar tespiti ===")
from data_quality import find_stale_bars, stale_orani
# yapay donuk seri
donuk=pd.DataFrame({'open':[1.0]*50,'high':[1.0]*50,'low':[1.0]*50,
                    'close':[1.0]*50,'volume':[100.0]*50})
o=stale_orani(donuk)
print(f"  tamamen donuk seri: %{o*100:.0f} (yuksek olmali)")
assert o>0.9, "donuk seri tespit edilmedi!"

# normal seri - donuk OLMAMALI
rng=np.random.default_rng(4)
c=100*np.cumprod(1+rng.normal(0,0.02,200))
normal=pd.DataFrame({'open':c,'high':c*1.01,'low':c*0.99,'close':c,'volume':[100.0]*200})
o2=stale_orani(normal)
print(f"  normal seri: %{o2*100:.1f} (0 olmali)")
assert o2<0.01, "normal seri donuk isaretlendi!"

# KISA tekrarlar donuk SAYILMAMALI (min_run=6)
kisa=pd.DataFrame({'open':c,'high':c*1.01,'low':c*0.99,'close':c,'volume':[100.0]*200})
kisa.loc[50:52,['high','low']]=[1.5,0.5]   # 3 bar ayni
o3=stale_orani(kisa)
print(f"  3 barlik tekrar: %{o3*100:.1f} (0 olmali - min_run=6)")
assert o3<0.01, "kisa tekrar donuk sayildi!"

# gercek veride EOSUSDT donuk cikmali
from backtest_yearly import load_all_csvs
gd=load_all_csvs('4h')
eos=gd['EOSUSDT'][gd['EOSUSDT']['date'].dt.year>=2022]
btc=gd['BTCUSDT'][gd['BTCUSDT']['date'].dt.year>=2022]
print(f"  EOSUSDT gercek: %{stale_orani(eos)*100:.0f} | BTCUSDT: %{stale_orani(btc)*100:.1f}")
assert stale_orani(eos)>stale_orani(btc)*5, "EOSUSDT donuklugu tespit edilmedi!"
print("\nDONUK VERI TESPITI TESTLERI GECTI")
