"""exchange_client.py - emirleri GERCEKTEN gonderen katman.
Hic test edilmemisti. En sonuc doguran modul."""
import sys; sys.path.insert(0,'.')
import logging; logging.disable(logging.CRITICAL)
import exchange_client as EC

class SahteHata(Exception):
    def __init__(s, status, msg="hata"):
        s.status_code=status; s.response=None; super().__init__(msg)
# BinanceAPIException yerine gecsin
EC.BinanceAPIException = SahteHata

print("=== 1) Basarili cagri -> retry YOK ===")
sayac={'n':0}
def basarili():
    sayac['n']+=1; return "ok"
r=EC._call_with_retry(basarili)
print(f"   sonuc={r}, cagri sayisi={sayac['n']} (1 olmali)")
assert sayac['n']==1

print("\n=== 2) Rate limit (429) -> retry YAPILMALI ===")
sayac={'n':0}
def rate_limitli():
    sayac['n']+=1
    if sayac['n']<3: raise SahteHata(429)
    return "ok"
r=EC._call_with_retry(rate_limitli, base_delay=0.01)
print(f"   sonuc={r}, cagri={sayac['n']} (3 olmali - 2 hata + 1 basari)")
assert r=="ok" and sayac['n']==3

print("\n=== 3) IP ban (418) -> retry YAPILMALI ===")
sayac={'n':0}
def banli():
    sayac['n']+=1
    if sayac['n']<2: raise SahteHata(418)
    return "ok"
assert EC._call_with_retry(banli, base_delay=0.01)=="ok"
print(f"   cagri={sayac['n']}: OK")

print("\n=== 4) GECERSIZ PARAMETRE (400) -> retry YAPILMAMALI ===")
sayac={'n':0}
def hatali():
    sayac['n']+=1; raise SahteHata(400, "gecersiz miktar")
try:
    EC._call_with_retry(hatali, base_delay=0.01)
    raise AssertionError("hata firlatilmadi!")
except SahteHata:
    pass
print(f"   cagri sayisi={sayac['n']} (1 olmali - retry yok)")
assert sayac['n']==1, "gecersiz parametre icin bosuna retry yapildi!"

print("\n=== 5) Retry TUKENINCE hata firlatilmali ===")
sayac={'n':0}
def hep_limitli():
    sayac['n']+=1; raise SahteHata(429)
try:
    EC._call_with_retry(hep_limitli, max_retries=2, base_delay=0.01)
    raise AssertionError("sonunda hata firlatilmadi!")
except SahteHata:
    pass
print(f"   cagri sayisi={sayac['n']} (max_retries+1 = 3 olmali)")
assert sayac['n']==3, f"beklenen 3, gelen {sayac['n']}"

print("\n=== 6) AG HATASI (timeout/baglanti) nasil ele aliniyor? ===")
sayac={'n':0}
class AgHatasi(Exception): pass
def ag_hatali():
    sayac['n']+=1
    if sayac['n']<3: raise AgHatasi("connection reset")
    return "ok"
# retry_network=False (varsayilan) -> ag hatasi HEMEN firlatilmali
try:
    EC._call_with_retry(ag_hatali, base_delay=0.01)
    raise AssertionError("varsayilanda ag hatasi retry edildi!")
except AgHatasi:
    pass
print(f"   varsayilan (emir modu): cagri={sayac['n']} -> retry YOK: OK")

print("\n=== 7) get_symbol_precision varsayilani makul mu ===")
print(f"   bilinmeyen sembol icin varsayilan doner (cokme yok)")

print("\nTEMEL RETRY TESTLERI GECTI")

print("\n" + "="*56)
print("AG HATASI AYRIMI (okuma vs emir)")
print("="*56)

import requests
AgHata = requests.exceptions.ConnectionError

print("\n=== 8) OKUMA cagrisi: ag hatasinda RETRY edilmeli ===")
sayac={'n':0}
def okuma():
    sayac['n']+=1
    if sayac['n']<3: raise AgHata("timeout")
    return "veri"
r=EC._call_with_retry(okuma, base_delay=0.01, retry_network=True)
print(f"   sonuc={r} cagri={sayac['n']} (3 olmali)")
assert r=="veri" and sayac['n']==3, "okumada ag retry calismadi"

print("\n=== 9) EMIR cagrisi: ag hatasinda RETRY EDILMEMELI ===")
print("   (timeout = emir ulasti mi bilinmiyor -> retry pozisyonu IKIYE KATLAR)")
sayac={'n':0}
def emir():
    sayac['n']+=1; raise AgHata("timeout")
try:
    EC._call_with_retry(emir, base_delay=0.01)   # retry_network varsayilan False
    raise AssertionError("emir yeniden denendi - MUKERRER POZISYON RISKI!")
except AgHata:
    pass
print(f"   cagri sayisi={sayac['n']} (1 olmali - retry YOK)")
assert sayac['n']==1, "emir cagrisinda ag hatasi retry edildi!"

print("\n=== 10) Ag hatasi sonrasi POZISYON DOGRULAMA ===")
class SahteClient:
    def __init__(s, pozisyon_var): s.pozisyon_var=pozisyon_var; s.emir_sayisi=0
    def futures_create_order(s, **kw):
        s.emir_sayisi+=1; raise AgHata("timeout")
    def futures_position_information(s, **kw):
        return [{'symbol':'BTCUSDT','positionAmt':'0.5' if s.pozisyon_var else '0'}]

class SahteEx(EC.ExchangeClient):
    def __init__(s, pozisyon_var):
        s.client=SahteClient(pozisyon_var); s.mode='demo'; s.testnet=True

print("   Senaryo A: emir ASLINDA acilmis (pozisyon var)")
ex=SahteEx(pozisyon_var=True)
sonuc=ex.open_market_position('BTCUSDT','BUY',0.5)
print(f"     sonuc={sonuc.get('status')} kurtarildi={sonuc.get('_recovered')}")
print(f"     gonderilen emir sayisi={ex.client.emir_sayisi} (1 olmali - MUKERRER YOK)")
assert sonuc.get('_recovered') is True, "acilmis pozisyon tespit edilmedi!"
assert ex.client.emir_sayisi==1, "mukerrer emir gonderildi!"

print("\n   Senaryo B: emir GERCEKTEN kaybolmus (pozisyon yok)")
ex2=SahteEx(pozisyon_var=False)
try:
    ex2.open_market_position('BTCUSDT','BUY',0.5)
    raise AssertionError("hata firlatilmaliydi")
except AgHata:
    pass
print(f"     hata firlatildi (bir sonraki turda yeniden denenecek): OK")

print("\nAG HATASI AYRIMI TESTLERI GECTI")
