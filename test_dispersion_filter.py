"""Dispersiyon filtresi: coinler ayrismiyorsa yeni pozisyon acma."""
import sys, os; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.INFO, format='%(message)s')
import numpy as np, pandas as pd
import crosssec_bot as B

B.STATE_FILE='/tmp/disp_test.json'
def temizle():
    if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)
    B._liquidity_cache.clear()

print("=== 1) Dispersiyon hesabi: AYRISAN vs AYRISMAYAN ===")
n=B.DISPERSION_WINDOW_BARS+50
rng=np.random.default_rng(2)
# ayrisan: her coin kendi yolunda
ayrisan={f'A{i}': 100*np.cumprod(1+rng.normal(0,0.03,n)) for i in range(8)}
# ayrismayan: hepsi ayni harekete yapisik
ortak=np.cumprod(1+rng.normal(0,0.03,n))
yapisik={f'B{i}': 100*ortak*(1+i*0.0001) for i in range(8)}
d1=B.hesapla_dispersiyon(ayrisan, B.DISPERSION_WINDOW_BARS)
d2=B.hesapla_dispersiyon(yapisik, B.DISPERSION_WINDOW_BARS)
print(f"   ayrisan coinler  : {d1:.5f}")
print(f"   yapisik coinler  : {d2:.5f}")
assert d1 > d2*10, "dispersiyon ayrimi calismiyor!"
print("   OK")

print("\n=== 2) Veri yetersizse NaN donmeli (cokme yok) ===")
az={f'C{i}': np.array([100.0]*10) for i in range(8)}
assert not np.isfinite(B.hesapla_dispersiyon(az, B.DISPERSION_WINDOW_BARS))
kisa={f'D{i}': 100*np.cumprod(1+rng.normal(0,0.03,n)) for i in range(2)}
assert not np.isfinite(B.hesapla_dispersiyon(kisa, B.DISPERSION_WINDOW_BARS))
print("   yetersiz veri -> NaN: OK")

# --- canli akis testi ---
class Book:
    def futures_order_book(s,symbol,limit=100):
        a=[[str(100*(1+0.0001*i)), str(50000/(100*(1+0.0001*i)))] for i in range(100)]
        b=[[str(100*(1-0.0001*(i+1))), str(50000/(100*(1-0.0001*(i+1))))] for i in range(100)]
        return {'asks':a,'bids':b}
    def futures_mark_price(s,symbol): return {'lastFundingRate':'0.0001'}

class Ex:
    def __init__(s, yapisik=False, pos=None):
        s.yapisik=yapisik; s.balance=10000.0; s._pos=pos or []
        s.orders=[]; s.closed=[]; s.client=Book()
        s._ortak=np.cumprod(1+np.random.default_rng(9).normal(0,0.03,B.REQUIRED_BARS+200))
    def get_account_balance_usdt(s): return s.balance
    def get_top_symbols(s,q,n2,e): return [f'C{i}USDT' for i in range(n2)]
    def get_klines(s,sym,tf,l):
        i=int(sym[1:].replace('USDT','')); n2=max(l,B.REQUIRED_BARS+B.DISPERSION_WINDOW_BARS)
        if s.yapisik:
            c=100*s._ortak[:n2]*(1+i*0.0001)   # hepsi ayni
        else:
            r=np.random.default_rng(i).normal(0,0.03,n2)
            c=100*np.cumprod(1+r)
        return pd.DataFrame({'close':c})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q): s.orders.append((sym,side,q))
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

print("\n=== 3) AYRISAN piyasa -> pozisyon acilmali ===")
temizle(); ex=Ex(yapisik=False)
B.rebalance(ex, dry_run=False)
print(f"   acilan emir: {len(ex.orders)} (>0 olmali)")
assert len(ex.orders)>0, "ayrisan piyasada islem yapilmadi!"

print("\n=== 4) YAPISIK piyasa -> pozisyon ACILMAMALI ===")
temizle(); ex=Ex(yapisik=True)
B.rebalance(ex, dry_run=False)
print(f"   acilan emir: {len(ex.orders)} (0 olmali)")
assert len(ex.orders)==0, "dispersiyon dusukken pozisyon acildi!"

print("\n=== 5) Filtre devredeyken KAR ALMA yine calismali ===")
temizle()
ex=Ex(yapisik=True, pos=[{'symbol':'C0USDT','positionAmt':'10',
                          'entryPrice':'100','markPrice':'110'}])
B.rebalance(ex, dry_run=False)
print(f"   kapatilan: {ex.closed} (kar alinmali)")
assert 'C0USDT' in ex.closed, "filtre devredeyken kar alinmadi - pozisyonlar yonetimsiz!"

print("\n=== 6) Filtre KAPALIYKEN yapisik piyasada da islem yapmali ===")
temizle(); B.USE_DISPERSION_FILTER=False
ex=Ex(yapisik=True)
B.rebalance(ex, dry_run=False)
B.USE_DISPERSION_FILTER=True
print(f"   acilan emir: {len(ex.orders)} (>0 olmali)")
assert len(ex.orders)>0

temizle()
print("\nDISPERSIYON FILTRESI TESTLERI GECTI")
