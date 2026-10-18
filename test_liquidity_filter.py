"""Likidite filtresi testleri."""
import sys, os; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.INFO, format='%(message)s')
import pandas as pd
import crosssec_bot as B
B.STATE_FILE='/tmp/liq_test_state.json'
if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)

def kalin_defter(mid=100.0, seviye=100, adet_usd=50000):
    """Her seviyede $50k -> cok likit"""
    asks=[[str(mid*(1+0.0001*i)), str(adet_usd/(mid*(1+0.0001*i)))] for i in range(seviye)]
    bids=[[str(mid*(1-0.0001*(i+1))), str(adet_usd/(mid*(1-0.0001*(i+1))))] for i in range(seviye)]
    return {"asks":asks,"bids":bids}

def ince_defter(mid=100.0, seviye=100, adet_usd=50):
    """Her seviyede sadece $50 -> cok sig"""
    asks=[[str(mid*(1+0.005*i)), str(adet_usd/(mid*(1+0.005*i)))] for i in range(seviye)]
    bids=[[str(mid*(1-0.005*(i+1))), str(adet_usd/(mid*(1-0.005*(i+1))))] for i in range(seviye)]
    return {"asks":asks,"bids":bids}

class FakeClient:
    def __init__(s, sig_semboller): s.sig=sig_semboller
    def futures_order_book(s, symbol, limit=100):
        return ince_defter() if symbol in s.sig else kalin_defter()

class FakeEx:
    def __init__(s, bal=10000.0, sig=(), pos=None):
        s.balance=bal; s._pos=pos or []; s.orders=[]; s.closed=[]
        s.client=FakeClient(set(sig))
    def get_account_balance_usdt(s): return s.balance
    def get_top_symbols(s,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(s,sym,tf,l):
        i=int(sym[1:].replace('USDT','')); n=max(l,B.REQUIRED_BARS)
        return pd.DataFrame({'close':[100*(1+(i-15)*0.002)**k for k in range(n)]})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q): s.orders.append((sym,side,q))
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

def _tmz():
    """Onbellegi temizle - testler birbirini etkilemesin."""
    B._liquidity_cache.clear()

_tmz()
print("=== 1) Kalin defter -> GECMELI ===")
ex=FakeEx()
ok,sebep=B.check_liquidity(ex,'C0USDT',1000.0)
print(f"  ok={ok} | {sebep}")
assert ok is True, "likit coin elendi!"

_tmz()
print("\n=== 2) Ince defter -> ELENMELI ===")
ex=FakeEx(sig=['C0USDT'])
ok,sebep=B.check_liquidity(ex,'C0USDT',1000.0)
print(f"  ok={ok} | {sebep}")
assert ok is False, "sig coin elenmedi!"

_tmz()
print("\n=== 3) Emir defteri alinamazsa -> GUVENLI tarafta, ELENMELI ===")
class HataliClient:
    def futures_order_book(s,symbol,limit=100): raise RuntimeError("ag hatasi")
ex=FakeEx(); ex.client=HataliClient()
ok,sebep=B.check_liquidity(ex,'C0USDT',1000.0)
print(f"  ok={ok} | {sebep}")
assert ok is False, "veri yokken coine girildi - GUVENSIZ!"

_tmz()
print("\n=== 4) Sig coinler evrenden cikarilmali, siralama kalanlar arasinda ===")
# C0 ve C1 en cok dusenler (LONG adayi) ama SIG -> elenmeli
ex=FakeEx(sig=['C0USDT','C1USDT'])
B.rebalance(ex, dry_run=False)
acilan={o[0] for o in ex.orders}
print(f"  acilan pozisyonlar: {sorted(acilan)}")
assert 'C0USDT' not in acilan and 'C1USDT' not in acilan, "sig coine pozisyon acildi!"
assert len(acilan)==B.N_LEGS*2, f"bacak sayisi eksik: {len(acilan)} (beklenen {B.N_LEGS*2})"
print(f"  -> {len(acilan)} pozisyon acildi (tam), sig coinler atlandi")

_tmz()
print("\n=== 5) Cok fazla coin elenirse islem YAPILMAMALI ===")
# 30 coinin 25'i sig -> 5 kalir, 10 gerekli
ex=FakeEx(sig=[f'C{i}USDT' for i in range(25)])
B.rebalance(ex, dry_run=False)
print(f"  acilan emir: {len(ex.orders)} (0 olmali)")
assert len(ex.orders)==0, "yetersiz coinle islem yapildi!"

_tmz()
print("\n=== 6) Filtre kapaliyken her sey gecmeli ===")
B.USE_LIQUIDITY_FILTER=False
ex=FakeEx(sig=['C0USDT'])
ok,_=B.check_liquidity(ex,'C0USDT',1000.0)
assert ok is True, "filtre kapaliyken elendi!"
B.USE_LIQUIDITY_FILTER=True
print("  OK")

os.remove(B.STATE_FILE)
print("\nLIKIDITE FILTRESI TESTLERI GECTI")

print("\n=== 7) ONBELLEK: ikinci cagri API'ye gitmemeli ===")
B._liquidity_cache.clear()
class Sayac:
    def __init__(s): s.n=0
    def futures_order_book(s,symbol,limit=100):
        s.n+=1
        return kalin_defter()
ex=FakeEx(); ex.client=Sayac()
B.check_liquidity(ex,'C0USDT',1000.0)
ilk=ex.client.n
B.check_liquidity(ex,'C0USDT',1000.0)
B.check_liquidity(ex,'C0USDT',1000.0)
print(f"  3 cagri sonrasi API istegi: {ex.client.n} (1 olmali)")
assert ex.client.n==1, "onbellek calismadi!"

print("\n=== 8) Farkli sembol -> ayri onbellek ===")
B.check_liquidity(ex,'C1USDT',1000.0)
print(f"  yeni sembol sonrasi: {ex.client.n} (2 olmali)")
assert ex.client.n==2

print("\n=== 9) AG HATASI onbellege alinmamali (gecici olabilir) ===")
B._liquidity_cache.clear()
class Hatali:
    def __init__(s): s.n=0
    def futures_order_book(s,symbol,limit=100):
        s.n+=1
        if s.n<=2: raise RuntimeError("gecici ag hatasi")
        return kalin_defter()
ex2=FakeEx(); ex2.client=Hatali()
ok1,_=B.check_liquidity(ex2,'C0USDT',1000.0)
ok2,_=B.check_liquidity(ex2,'C0USDT',1000.0)
ok3,_=B.check_liquidity(ex2,'C0USDT',1000.0)
print(f"  hata sonrasi toparlanma: {ok1} -> {ok2} -> {ok3} (son True olmali)")
assert ok1 is False and ok3 is True, "gecici hata kalici onbelleklendi!"

print("\n=== 10) Onbellek suresi dolunca yenilenmeli ===")
import time as _t
B._liquidity_cache.clear()
ex3=FakeEx(); ex3.client=Sayac()
B.check_liquidity(ex3,'C0USDT',1000.0)
# zamani geriye al
z,ok,sb=B._liquidity_cache['C0USDT']
B._liquidity_cache['C0USDT']=(z-B.LIQUIDITY_CACHE_HOURS*3600-10, ok, sb)
B.check_liquidity(ex3,'C0USDT',1000.0)
print(f"  sure dolunca API istegi: {ex3.client.n} (2 olmali)")
assert ex3.client.n==2, "onbellek suresi dolmadi!"
B._liquidity_cache.clear()
print("\nONBELLEK TESTLERI GECTI")

print("\n=== 11) ONBELLEK SURESI rebalance ile tutarli mi? ===")
rebalance_saat = B.REBALANCE_DAYS * 24
print(f"  rebalance: {rebalance_saat:.0f}sa | onbellek: {B.LIQUIDITY_CACHE_HOURS:.0f}sa")
assert B.LIQUIDITY_CACHE_HOURS > rebalance_saat, (
    f"Onbellek suresi ({B.LIQUIDITY_CACHE_HOURS}sa) rebalance araligindan "
    f"({rebalance_saat}sa) KISA - onbellek her turda dolar, hic ise yaramaz!")
print(f"  {B.LIQUIDITY_CACHE_HOURS/rebalance_saat:.1f} turda bir yenilenir: OK")
print("\nTUTARLILIK TESTI GECTI")
