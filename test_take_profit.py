"""Pozisyon bazli kar alma (take-profit) testleri."""
import sys, os; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.INFO, format='%(message)s')
import pandas as pd
import crosssec_bot as B
B.STATE_FILE='/tmp/tp_test_state.json'
if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)

class FakeEx:
    def __init__(s,bal=10000.0,pos=None): s.balance=bal; s._pos=pos or []; s.orders=[]; s.closed=[]
    def get_account_balance_usdt(s): return s.balance
    def get_top_symbols(s,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(s,sym,tf,l):
        i=int(sym[1:].replace('USDT','')) if sym.startswith('C') else 0
        n=max(l,B.REQUIRED_BARS)
        return pd.DataFrame({'close':[100*(1+(i-7)*0.004)**k for k in range(n)]})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q): s.orders.append((sym,side,q))
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

print("=== 1) LONG pozisyon +%10 kar -> kapatilmali (hedef %8) ===")
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'110'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c}")
assert 'C0USDT' in c, "LONG kar alinmadi!"

print("\n=== 2) LONG +%3 kar -> kapatilMAmali ===")
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'103'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c} (bos olmali)")
assert c==[], "esik altinda kar alindi!"

print("\n=== 3) SHORT pozisyon, fiyat DUSMUS (-%10) -> kar, kapatilmali ===")
ex=FakeEx(pos=[{'symbol':'C1USDT','positionAmt':'-10','entryPrice':'100','markPrice':'90'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c}")
assert 'C1USDT' in c, "SHORT kar alinmadi!"

print("\n=== 4) SHORT pozisyon, fiyat YUKSELMIS (+%10) -> ZARAR, kapatilMAmali ===")
ex=FakeEx(pos=[{'symbol':'C1USDT','positionAmt':'-10','entryPrice':'100','markPrice':'110'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c} (bos olmali - bu zarar, kar degil!)")
assert c==[], "SHORT zararda kapatildi - YON HATASI!"

print("\n=== 5) dry-run: kapatma emri gitmemeli ===")
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'110'}])
c=B.take_profits(ex, dry_run=True)
print(f"  bildirilen: {c}, gercek kapatma: {ex.closed}")
assert c==['C0USDT'] and ex.closed==[], "dry-run emir gonderdi!"

print("\n=== 6) kar alinan sembol ayni turda YENIDEN ACILMAMALI ===")
# C0 en cok dusen -> hedefte LONG olmali, ama kar alindiysa acilmamali
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'110'}])
B.rebalance(ex, dry_run=False)
c0_orders=[o for o in ex.orders if o[0]=='C0USDT']
print(f"  C0USDT kapatildi mi: {'C0USDT' in ex.closed}")
print(f"  C0USDT yeniden acildi mi: {len(c0_orders)>0} (False olmali)")
assert 'C0USDT' in ex.closed, "kar alinmadi!"
assert len(c0_orders)==0, "kar alinan pozisyon ayni turda yeniden acildi!"

os.remove(B.STATE_FILE)
print("\nKAR ALMA TESTLERI GECTI")

print("\n=== 7) ACIL STOP: LONG -%30 zararda -> kapatilmali ===")
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'70'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c}")
assert 'C0USDT' in c, "acil stop tetiklenmedi!"

print("\n=== 8) ACIL STOP: SHORT fiyat yukselmis (-%30 zarar) -> kapatilmali ===")
ex=FakeEx(pos=[{'symbol':'C1USDT','positionAmt':'-10','entryPrice':'100','markPrice':'130'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c}")
assert 'C1USDT' in c, "SHORT acil stop tetiklenmedi!"

print("\n=== 9) ARADAKI BOLGE: -%10 zarar -> DOKUNULMAMALI ===")
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'90'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c} (bos olmali - ne TP ne acil stop)")
assert c==[], "normal dalgalanmada pozisyon kapatildi!"

print("\n=== 10) XLM senaryosu: SHORT %184 zarar ===")
ex=FakeEx(pos=[{'symbol':'C1USDT','positionAmt':'-10','entryPrice':'0.186','markPrice':'0.528'}])
c=B.take_profits(ex, dry_run=False)
print(f"  kapatilan: {c} (gercek 2024-11 XLM olayi)")
assert 'C1USDT' in c

print("\n=== 11) acil stop KAPALIYKEN tetiklenmemeli ===")
B.USE_EMERGENCY_STOP=False
ex=FakeEx(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'50'}])
c=B.take_profits(ex, dry_run=False)
B.USE_EMERGENCY_STOP=True
print(f"  kapatilan: {c} (bos olmali)")
assert c==[]
print("\nACIL STOP TESTLERI GECTI")
