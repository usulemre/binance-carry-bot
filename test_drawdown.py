"""Devre kesici testi."""
import sys, os, json; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.INFO, format='%(message)s')
import pandas as pd
import crosssec_bot as B
B.STATE_FILE='/tmp/cs_state_test.json'  # gercek durumu bozmamak icin
if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)

class FakeEx:
    def __init__(self, bal, pos=None): self.balance=bal; self._pos=pos or []; self.closed=[]
    def get_account_balance_usdt(self): return self.balance
    def get_top_symbols(self,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(self,s,tf,l):
        i=int(s[1:].replace('USDT','')); n=max(l,B.LOOKBACK_BARS+5)
        return pd.DataFrame({'close':[100*(1+(i-7)*0.004)**k for k in range(n)]})
    def get_open_positions(self): return self._pos
    def get_symbol_precision(self,s): return {'quantity_precision':3}
    def open_market_position(self,*a): pass
    def close_position(self,s,side,q): self.closed.append(s)
    def cancel_all_open_orders(self,s): pass

print("=== 1) Bakiye 10000 -> tepe kaydedilir, devam ===")
ex=FakeEx(10000.0); B.rebalance(ex, dry_run=True)
print("state:", json.load(open(B.STATE_FILE)))

print("\n=== 2) Bakiye 8000 (-%20) -> limit altinda, devam etmeli ===")
ex=FakeEx(8000.0); B.rebalance(ex, dry_run=True)
print("-> devam etti (beklenen)")

print("\n=== 3) Bakiye 6000 (-%40) -> DEVRE KESICI tetiklenmeli ===")
ex=FakeEx(6000.0, pos=[{'symbol':'C0USDT','positionAmt':'5','markPrice':'100'}])
try:
    B.rebalance(ex, dry_run=False)
    print("HATA: devre kesici tetiklenmedi!")
except SystemExit:
    print(f"-> SystemExit ile durdu, kapatilanlar: {ex.closed}")
    assert 'C0USDT' in ex.closed, "pozisyonlar kapatilmadi!"
    print("OK")

os.remove(B.STATE_FILE)
print("\nDEVRE KESICI TESTLERI GECTI")
