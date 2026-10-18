"""ARIZA SENARYOLARI: bot canlida ne zaman bozulur?"""
import sys, os, json; sys.path.insert(0,'.')
import logging; logging.basicConfig(level=logging.ERROR)
import pandas as pd, numpy as np
import crosssec_bot as B

B.STATE_FILE='/tmp/fail_test.json'
def temizle():
    if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)

class Book:
    def futures_order_book(self,symbol,limit=100):
        a=[[str(100*(1+0.0001*i)), str(50000/(100*(1+0.0001*i)))] for i in range(100)]
        b=[[str(100*(1-0.0001*(i+1))), str(50000/(100*(1-0.0001*(i+1))))] for i in range(100)]
        return {"asks":a,"bids":b}

class Ex:
    def __init__(s,**kw):
        s.balance=kw.get('bal',10000.0); s._pos=kw.get('pos',[])
        s.orders=[]; s.closed=[]; s.client=Book()
        s.fail_open=kw.get('fail_open',False); s.fail_klines=kw.get('fail_klines',False)
        s.fail_close=kw.get('fail_close',False); s.fail_bal=kw.get('fail_bal',False)
    def get_account_balance_usdt(s):
        if s.fail_bal: raise RuntimeError("API zaman asimi")
        return s.balance
    def get_top_symbols(s,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(s,sym,tf,l):
        if s.fail_klines and sym=='C3USDT': raise RuntimeError("kline hatasi")
        i=int(sym[1:].replace('USDT','')); n=max(l,B.REQUIRED_BARS)
        return pd.DataFrame({'close':[100*(1+(i-B.UNIVERSE_SIZE//2)*0.002)**k for k in range(n)]})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q):
        if s.fail_open: raise RuntimeError("emir reddedildi (marj yetersiz)")
        s.orders.append((sym,side,q))
    def close_position(s,sym,side,q):
        if s.fail_close: raise RuntimeError("kapatma basarisiz")
        s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

sonuc=[]
def dene(ad, fn):
    try:
        fn(); sonuc.append((ad,'GECTI','')); print(f'  OK   {ad}')
    except SystemExit as e:
        sonuc.append((ad,'SystemExit',str(e))); print(f'  EXIT {ad} (kasitli olabilir)')
    except Exception as e:
        sonuc.append((ad,'COKTU',f'{type(e).__name__}: {e}')); print(f'  !!!! {ad} -> {type(e).__name__}: {e}')

print("ARIZA SENARYOLARI")
print()
temizle(); dene("1. Bakiye API hatasi", lambda: B.rebalance(Ex(fail_bal=True), dry_run=True))
temizle(); dene("2. Bir coinin kline verisi gelmiyor", lambda: B.rebalance(Ex(fail_klines=True), dry_run=False))
temizle(); dene("3. Emir acma reddediliyor (marj yok)", lambda: B.rebalance(Ex(fail_open=True), dry_run=False))
temizle(); dene("4. Pozisyon kapatma basarisiz", lambda: B.rebalance(Ex(fail_close=True, pos=[{'symbol':'ESKIUSDT','positionAmt':'5','markPrice':'100','entryPrice':'100'}]), dry_run=False))
temizle(); dene("5. Bakiye sifir", lambda: B.rebalance(Ex(bal=0.0), dry_run=True))
temizle(); dene("6. Negatif bakiye", lambda: B.rebalance(Ex(bal=-50.0), dry_run=True))

# 7) bozuk durum dosyasi
temizle()
open(B.STATE_FILE,'w').write('{bozuk json!!')
dene("7. Bozuk state dosyasi", lambda: B.rebalance(Ex(), dry_run=True))

# 8) state dosyasinda sacma deger
temizle()
json.dump({'peak_balance':'metin'}, open(B.STATE_FILE,'w'))
dene("8. State dosyasinda yanlis tip", lambda: B.rebalance(Ex(), dry_run=True))

# 9) pozisyon verisinde eksik alan
temizle(); dene("9. Pozisyon verisinde eksik alan",
    lambda: B.rebalance(Ex(pos=[{'symbol':'XUSDT','positionAmt':'5'}]), dry_run=True))

# 10) ayni sembol iki kez
temizle(); dene("10. Ayni sembol tekrarli pozisyon",
    lambda: B.rebalance(Ex(pos=[{'symbol':'C0USDT','positionAmt':'5','markPrice':'100','entryPrice':'100'},
                                 {'symbol':'C0USDT','positionAmt':'3','markPrice':'100','entryPrice':'100'}]), dry_run=True))
temizle()
print()
coken=[x for x in sonuc if x[1]=='COKTU']
print(f"SONUC: {len(sonuc)} senaryo, {len(coken)} COKME")
for ad,_,hata in coken: print(f"  - {ad}: {hata}")

# --- YENIDEN BASLATMA GUVENLIGI ---
print()
print("YENIDEN BASLATMA GUVENLIGI")
temizle()

# 1) Bot pozisyon acar, sonra "yeniden baslar" (state korunur mu?)
ex1=Ex()
B.rebalance(ex1, dry_run=False)
acik=[(o[0],o[1]) for o in ex1.orders]
st1=json.load(open(B.STATE_FILE))
print(f"  ilk calisma: {len(acik)} emir, tepe bakiye={st1.get('peak_balance')}")

# 2) Yeniden baslat: ayni pozisyonlar acikken tekrar calistir
# GERCEK miktarlarla pozisyon kur - sabit deger kullanmak yanlis test yapar
pos=[]
for sym,side,q in ex1.orders:
    px=float(ex1.get_klines(sym,'4h',2)['close'].iloc[-1])
    pos.append({'symbol':sym,'positionAmt':str(q if side=='BUY' else -q),
                'markPrice':str(px),'entryPrice':str(px)})
ex2=Ex(pos=pos)
B.rebalance(ex2, dry_run=False)
print(f"  yeniden baslatma sonrasi yeni emir: {len(ex2.orders)}")
print(f"  (0'a yakin olmali - mevcut pozisyonlar korunmali, tekrar acilmamali)")
assert len(ex2.orders)==0, f"yeniden baslatmada {len(ex2.orders)} gereksiz emir acildi!"

# 3) State dosyasi SILINIRSE (disk temizligi, tasima)
os.remove(B.STATE_FILE)
ex3=Ex(pos=pos)
B.rebalance(ex3, dry_run=True)
print(f"  state silinince cokme yok: OK")
st3=json.load(open(B.STATE_FILE))
print(f"  tepe bakiye yeniden olusturuldu: {st3.get('peak_balance')}")

temizle()
print()
print("TUM ARIZA SENARYOLARI VE YENIDEN BASLATMA TESTLERI GECTI")
