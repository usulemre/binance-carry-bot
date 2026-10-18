import sys, os, json; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.INFO, format='%(message)s')
import pandas as pd
import crosssec_bot as B

class FakeBook:
    """Kalin emir defteri - likidite filtresi tum coinleri gecirsin."""
    def futures_order_book(self, symbol, limit=100):
        asks=[[str(100*(1+0.0001*i)), str(50000/(100*(1+0.0001*i)))] for i in range(100)]
        bids=[[str(100*(1-0.0001*(i+1))), str(50000/(100*(1-0.0001*(i+1))))] for i in range(100)]
        return {"asks":asks,"bids":bids}
B.STATE_FILE='/tmp/scale_test.json'

print("=== compute_exposure_scale mantigi ===")
for dd in [0,5,10,15,20,25,30,40]:
    print(f"  dusus %{dd:>2} -> exposure %{B.compute_exposure_scale(dd)*100:>5.1f}")
assert B.compute_exposure_scale(0)==1.0
assert B.compute_exposure_scale(15)==0.5
assert B.compute_exposure_scale(30)==0.0
assert B.compute_exposure_scale(40)==0.0
print("OK\n")

class FakeEx:
    def __init__(s,bal,pos=None): s.balance=bal; s._pos=pos or []; s.orders=[]; s.closed=[]; s.client=FakeBook()
    def get_account_balance_usdt(s): return s.balance
    def get_top_symbols(s,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(s,sym,tf,l):
        i=int(sym[1:].replace('USDT','')); n=max(l,B.REQUIRED_BARS)
        return pd.DataFrame({'close':[100*(1+(i-7)*0.004)**k for k in range(n)]})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q): s.orders.append((sym,side,q))
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)
print("=== 1) tepe 10000 kaydet ===")
B.rebalance(FakeEx(10000.0), dry_run=True)

print("\n=== 2) bakiye 8500 (-%15) -> exposure yarilanmali ===")
ex=FakeEx(8500.0)
# gercek nominal: her emir icin o coinin kendi fiyatini kullan
B.rebalance(ex, dry_run=False)
tot=0
for sym,side,q in ex.orders:
    px=float(ex.get_klines(sym,'4h',2)['close'].iloc[-1])
    tot+=abs(q)*px
print(f"-> toplam nominal ~{tot:.0f} USDT (olceksiz ~8500 olurdu, %50 olcekle ~4250)")
assert 3400 < tot < 5100, f"olcekleme yanlis: {tot}"
print("OK: exposure yarilandi")

print("\n=== 3) bakiye 7000 (-%30) -> exposure sifir, pozisyonlar kapanmali ===")
ex=FakeEx(7000.0, pos=[{'symbol':'C0USDT','positionAmt':'10','markPrice':'100'}])
B.rebalance(ex, dry_run=False)
print(f"-> acilan emir: {len(ex.orders)}, kapatilan: {ex.closed}")
assert len(ex.orders)==0, "sifir exposure'da emir acildi!"
os.remove(B.STATE_FILE)
print("\nOLCEKLEME TESTLERI GECTI")
