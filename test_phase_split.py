"""FAZ DILIMLEME testleri.

NOT: Bu ozellik VARSAYILAN OLARAK KAPALI (madde 104 - netlesme
yuzunden zararli cikti). Kod duruyor cunku ayri alt hesaplarda
kullanilabilir. Testler ozelligi GECICI ACARAK mantigin dogru
calistigini dogrular.

Her turda sadece SIRADAKI dilim yenilenmeli, digerleri korunmali.
Toplam hedef tum dilimlerin birlesimi olmali.
"""
import sys, os, json; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.WARNING)
import numpy as np, pandas as pd
import crosssec_bot as B

B.STATE_FILE='/tmp/faz_test.json'
def temizle():
    if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)
    B._liquidity_cache.clear()

class Book:
    def futures_order_book(s,symbol,limit=100):
        a=[[str(100*(1+0.0001*i)), str(50000/(100*(1+0.0001*i)))] for i in range(100)]
        b=[[str(100*(1-0.0001*(i+1))), str(50000/(100*(1-0.0001*(i+1))))] for i in range(100)]
        return {'asks':a,'bids':b}
    def futures_mark_price(s,symbol): return {'lastFundingRate':'0.0001'}

class Ex:
    def __init__(s, tohum=0):
        s.balance=10000.0; s._pos=[]; s.orders=[]; s.closed=[]; s.client=Book(); s.tohum=tohum
    def get_account_balance_usdt(s): return s.balance
    def get_top_symbols(s,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(s,sym,tf,l):
        i=int(sym[1:].replace('USDT',''))
        n=max(l,B.REQUIRED_BARS+B.DISPERSION_WINDOW_BARS)
        rng=np.random.default_rng(i*100+s.tohum)
        return pd.DataFrame({'close':100*np.cumprod(1+rng.normal(0,0.03,n))})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q): s.orders.append((sym,side,q))
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

# Ozellik varsayilan kapali - testler icin gecici ac
_ESKI_AYAR = B.USE_PHASE_SPLIT
B.USE_PHASE_SPLIT = True

print("=== 1) Ilk turda SADECE dilim 0 dolmali ===")
temizle()
B.rebalance(Ex(tohum=0), dry_run=True)
st=json.load(open(B.STATE_FILE))
pt=st.get('phase_targets',{})
print(f"   dolu dilim: {sorted(pt.keys())}  sonraki: {st.get('next_phase')}")
assert list(pt.keys())==['0'], f"ilk turda sadece dilim 0 olmali: {list(pt)}"
assert st['next_phase']==1

print("\n=== 2) Ikinci tur dilim 1'i eklemeli, dilim 0'i KORUMALI ===")
dilim0_once=dict(pt['0'])
B.rebalance(Ex(tohum=1), dry_run=True)
st=json.load(open(B.STATE_FILE))
pt=st['phase_targets']
print(f"   dolu dilim: {sorted(pt.keys())}  sonraki: {st.get('next_phase')}")
assert sorted(pt.keys())==['0','1'], f"dilim 1 eklenmedi: {list(pt)}"
assert pt['0']==dilim0_once, "dilim 0 DEGISTI - korunmasi gerekiyordu!"
print("   dilim 0 korundu: OK")

print("\n=== 3) Ucuncu tur sonrasi sira BASA donmeli ===")
B.rebalance(Ex(tohum=2), dry_run=True)
st=json.load(open(B.STATE_FILE))
print(f"   dolu dilim: {sorted(st['phase_targets'].keys())}  sonraki: {st['next_phase']}")
assert st['next_phase']==0, "sira basa donmedi"
assert len(st['phase_targets'])==B.PHASE_COUNT

print("\n=== 4) Dilim 0 dorduncu turda YENILENMELI ===")
d0_eski=dict(st['phase_targets']['0'])
B.rebalance(Ex(tohum=99), dry_run=True)
st=json.load(open(B.STATE_FILE))
d0_yeni=st['phase_targets']['0']
print(f"   dilim 0 degisti mi: {d0_eski!=d0_yeni}")
assert d0_eski!=d0_yeni, "dilim 0 yenilenmedi!"

print("\n=== 5) Her dilim sermayenin 1/PHASE_COUNT'i kadar olmali ===")
for k,v in st['phase_targets'].items():
    brut=sum(abs(w) for w in v.values())
    beklenen=B.GROSS_EXPOSURE/B.PHASE_COUNT
    print(f"   dilim {k}: brut={brut:.4f} (beklenen {beklenen:.4f})")
    assert abs(brut-beklenen)<0.01, f"dilim {k} yanlis buyuklukte"

print("\n=== 6) Dilimleme KAPALIYKEN eski davranis ===")
temizle()
B.USE_PHASE_SPLIT=False
B.rebalance(Ex(tohum=0), dry_run=True)
st=json.load(open(B.STATE_FILE))
B.USE_PHASE_SPLIT=True
print(f"   phase_targets var mi: {'phase_targets' in st} (olmamali)")
assert 'phase_targets' not in st

temizle()
B.USE_PHASE_SPLIT = _ESKI_AYAR
print(f"\n(ozellik varsayilan durumu: {_ESKI_AYAR} - madde 104)")
print("FAZ DILIMLEME TESTLERI GECTI")
