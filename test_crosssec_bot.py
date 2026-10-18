"""crosssec_bot mantiginin sahte borsa ile uctan uca testi."""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
import crosssec_bot as B

class FakeBook:
    """Kalin emir defteri - likidite filtresi tum coinleri gecirsin."""
    def futures_order_book(self, symbol, limit=100):
        asks=[[str(100*(1+0.0001*i)), str(50000/(100*(1+0.0001*i)))] for i in range(100)]
        bids=[[str(100*(1-0.0001*(i+1))), str(50000/(100*(1-0.0001*(i+1))))] for i in range(100)]
        return {"asks":asks,"bids":bids}

# --- Sahte borsa ---
class FakeEx:
    def __init__(self, positions=None, balance=10000.0):
        self.balance=balance; self._pos=positions or []; self.orders=[]; self.closed=[]; self.client=FakeBook()
    def get_account_balance_usdt(self): return self.balance
    def get_top_symbols(self,q,n,ex): return [f'C{i}USDT' for i in range(n)]
    def get_klines(self,sym,tf,limit):
        # her coine farkli trend ver -> siralama belirgin olsun
        i=int(sym[1:].replace('USDT',''))
        base=100.0
        drift=(i-B.UNIVERSE_SIZE//2)*0.004   # C0 en cok duser, C13 en cok yukselir
        n=max(limit,B.LOOKBACK_BARS+5)
        closes=[base*(1+drift)**k for k in range(n)]
        return pd.DataFrame({'close':closes})
    def get_open_positions(self): return self._pos
    def get_symbol_precision(self,s): return {'quantity_precision':3,'price_precision':2}
    def open_market_position(self,s,side,q): self.orders.append((s,side,q))
    def close_position(self,s,side,q): self.closed.append((s,side,q))
    def cancel_all_open_orders(self,s): pass

print("=== TEST 1: bos portfoy, ilk dengeleme ===")
ex=FakeEx()
B.rebalance(ex, dry_run=False)
longs=[o for o in ex.orders if o[1]=='BUY']; shorts=[o for o in ex.orders if o[1]=='SELL']
print(f"\n-> {len(longs)} BUY, {len(shorts)} SHORT emri")
assert len(longs)==B.N_LEGS and len(shorts)==B.N_LEGS, "bacak sayisi yanlis!"

# En cok DUSENLER long olmali (C0,C1,C2,C3), en cok YUKSELENLER short (C10..C13)
long_syms={o[0] for o in longs}; short_syms={o[0] for o in shorts}
print("LONG :", sorted(long_syms))
print("SHORT:", sorted(short_syms))
expected_long={f'C{i}USDT' for i in range(B.N_LEGS)}
assert long_syms==expected_long, f"yanlis long: {long_syms}"
expected_short={f'C{i}USDT' for i in range(B.UNIVERSE_SIZE-B.N_LEGS,B.UNIVERSE_SIZE)}
assert short_syms==expected_short, f"yanlis short: {short_syms}"
print("OK: dusenler long, yukselenler short\n")

print("=== TEST 2: piyasa notr mu? ===")
w=B.compute_target_weights({f'C{i}USDT':FakeEx().get_klines(f'C{i}USDT','4h',100)['close'].values for i in range(B.UNIVERSE_SIZE)}, B.N_LEGS, 1.0)
net=sum(w.values()); gross=sum(abs(v) for v in w.values())
print(f"net={net:+.6f} (0 olmali), gross={gross:.3f} (1.0 olmali)")
assert abs(net)<1e-9, "piyasa notr degil!"
assert abs(gross-1.0)<1e-9, "gross exposure yanlis!"
print("OK: piyasa notr, kaldiracsiz\n")

print("=== TEST 3: hedefte olmayan pozisyon kapatiliyor mu? ===")
ex2=FakeEx(positions=[{'symbol':'ESKIUSDT','positionAmt':'5.0','markPrice':'100'}])
B.rebalance(ex2, dry_run=False)
print(f"-> kapatilanlar: {ex2.closed}")
assert any(c[0]=='ESKIUSDT' for c in ex2.closed), "eski pozisyon kapatilmadi!"
print("OK\n")

print("=== TEST 4: dry-run hicbir emir gondermiyor mu? ===")
ex3=FakeEx()
B.rebalance(ex3, dry_run=True)
assert len(ex3.orders)==0 and len(ex3.closed)==0, "dry-run emir gonderdi!"
print(f"-> emir sayisi: {len(ex3.orders)} (0 olmali)  OK\n")

print("=== TEST 5: kucuk sapmada islem yapilmiyor mu? ===")
# hedefe zaten cok yakin pozisyonlar
w=(1.0/2)/B.N_LEGS
pos=[{'symbol':'C0USDT','positionAmt':str(w*10000/100),'markPrice':'100'}]
ex4=FakeEx(positions=pos)
B.rebalance(ex4, dry_run=False)
c0=[o for o in ex4.orders if o[0]=='C0USDT']
print(f"-> C0USDT icin emir: {c0} (bos olmali, zaten hedefte)")
assert len(c0)==0, "gereksiz islem yapildi!"
print("OK\n")

print("TUM TESTLER GECTI")

print("\n=== 6) COK UFUKLU SIRALAMA ===")
import numpy as np
np.random.seed(11)
n=B.REQUIRED_BARS+10

# Senaryo: A coini SON 5 GUNDE cok dustu ama 15 gunde yatay
#          B coini 15 GUNDE surekli dustu
# Tek ufuk (10g) ile coklu ufuk FARKLI siralama vermeli
def seri(gun5, gun15):
    """son 5 gunde gun5 kadar, onceki donemde (gun15-gun5) kadar degisim.

    NOT: uzun pencere HORIZON_DAYS'e gore belirlenir - ufuk ayari
    degisince test kirilmasin (5/10/15g -> 5/10g gecisinde yasandi)."""
    b5=int(5*B.BARS_PER_DAY)
    b15=min(int(max(B.HORIZON_DAYS)*B.BARS_PER_DAY), n-10)
    b15=max(b15, b5+6)
    p=[100.0]*max(n-b15, 1)
    # 15g -> 5g arasi
    ara=(gun15-gun5)
    for k in range(b15-b5): p.append(p[-1]*(1+ara/(b15-b5)))
    for k in range(b5): p.append(p[-1]*(1+gun5/b5))
    return np.array(p[:n]) if len(p)>=n else np.array(p+[p[-1]]*(n-len(p)))

closes={
 'AUSDT': seri(-0.30, -0.30),   # sadece son 5 gunde dustu
 'BUSDT': seri(-0.05, -0.30),   # 15 gun boyunca yavas dustu
 'CUSDT': seri(+0.30, +0.30),   # son 5 gunde ciktii
 'DUSDT': seri(+0.05, +0.30),   # 15 gun boyunca yavas cikti
 'EUSDT': seri(0.0, 0.0),
 'FUSDT': seri(0.01, 0.01),
}
w=B.compute_target_weights(closes, 2, 1.0)
longs={k for k,v in w.items() if v>0}; shorts={k for k,v in w.items() if v<0}
print(f"  LONG : {sorted(longs)}  (dusenler olmali: A,B)")
print(f"  SHORT: {sorted(shorts)} (cikanlar olmali: C,D)")
assert longs=={'AUSDT','BUSDT'}, f"yanlis long: {longs}"
assert shorts=={'CUSDT','DUSDT'}, f"yanlis short: {shorts}"
assert abs(sum(w.values()))<1e-9, "piyasa notr degil!"
print("  OK: coklu ufuk dogru yonde siraliyor, piyasa notr")

print("\n=== 7) yetersiz veri -> bos donmeli (cokme yok) ===")
kisa={f'X{i}USDT': np.array([100.0]*10) for i in range(6)}
w2=B.compute_target_weights(kisa, 2, 1.0)
print(f"  sonuc: {w2} (bos olmali)")
assert w2=={}, "yetersiz veriyle agirlik uretildi!"
print("  OK")
