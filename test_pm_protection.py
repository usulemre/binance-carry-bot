"""position_manager: koruyucu emir DEGISTIRIRKEN korumasiz kalma riski.

Tehlikeli an: eski emirler iptal edildi, yeni SL henuz konmadi.
Bu arada SL kurulamazsa pozisyon acik ve stop'suz kalir.
"""
import sys; sys.path.insert(0,'.')
import logging
logs=[]
class Y(logging.Handler):
    def emit(s,r): logs.append(r.getMessage())
lg=logging.getLogger('bot'); lg.addHandler(Y()); lg.setLevel(logging.DEBUG)

import position_manager as pm

class Ex:
    def __init__(s, sl_hata_sayisi=0, kapat_hata=False):
        s.sl_hata_sayisi=sl_hata_sayisi   # ilk N SL denemesi hata versin
        s.kapat_hata=kapat_hata
        s.sl_denemeleri=[]; s.tp_konan=[]; s.kapatilan=[]; s.iptal=[]
    def cancel_all_open_orders(s,sym): s.iptal.append(sym)
    def place_stop_loss(s,sym,side,px,q):
        s.sl_denemeleri.append(px)
        if len(s.sl_denemeleri)<=s.sl_hata_sayisi:
            raise RuntimeError("SL reddedildi")
    def place_take_profit(s,sym,side,px,q): s.tp_konan.append(px)
    def close_position(s,sym,side,q,**kw):
        if s.kapat_hata: raise RuntimeError("kapatma basarisiz")
        s.kapatilan.append(sym)

print("=== 1) NORMAL: SL ve TP yenileniyor ===")
logs.clear(); ex=Ex()
pm._replace_protective_orders(ex,'BTCUSDT','SELL',95.0,110.0,1.0,eski_sl=90.0)
print(f"   iptal={ex.iptal} SL={ex.sl_denemeleri} TP={ex.tp_konan}")
assert ex.sl_denemeleri==[95.0] and ex.tp_konan==[110.0]

print("\n=== 2) Yeni SL kurulamadi -> ESKI SL geri konmali ===")
logs.clear(); ex=Ex(sl_hata_sayisi=1)   # ilk deneme (yeni SL) hata, ikinci (eski SL) basarili
try:
    pm._replace_protective_orders(ex,'BTCUSDT','SELL',95.0,110.0,1.0,eski_sl=90.0)
    raise AssertionError("hata firlatilmaliydi (guncelleme basarisiz)")
except RuntimeError:
    pass
print(f"   SL denemeleri={ex.sl_denemeleri} (yeni 95.0 basarisiz -> eski 90.0 denendi)")
assert 90.0 in ex.sl_denemeleri, "eski SL geri konmadi - POZISYON KORUMASIZ!"
geri=[l for l in logs if 'geri konuldu' in l]
assert geri, "eski SL geri koyma loglanmadi"
print(f"   {geri[0][:70]}...")

print("\n=== 3) Hem yeni hem eski SL basarisiz -> pozisyon KAPATILMALI ===")
logs.clear(); ex=Ex(sl_hata_sayisi=99)   # tum SL denemeleri hata
try:
    pm._replace_protective_orders(ex,'BTCUSDT','SELL',95.0,110.0,1.0,eski_sl=90.0)
    raise AssertionError("hata firlatilmaliydi")
except RuntimeError:
    pass
print(f"   SL denemeleri={len(ex.sl_denemeleri)}, kapatilan={ex.kapatilan}")
assert ex.kapatilan==['BTCUSDT'], "korumasiz pozisyon kapatilmadi!"

print("\n=== 4) SL basarisiz VE kapatma da basarisiz -> ACIL UYARI ===")
logs.clear(); ex=Ex(sl_hata_sayisi=99, kapat_hata=True)
try:
    pm._replace_protective_orders(ex,'BTCUSDT','SELL',95.0,110.0,1.0,eski_sl=90.0)
except RuntimeError:
    pass
acil=[l for l in logs if 'MANUEL MÜDAHALE' in l]
print(f"   acil uyari={len(acil)}")
assert acil, "acil uyari yok!"
print(f"   {acil[0][:75]}...")

print("\n=== 5) TP kurulamadi -> pozisyon KAPATILMAMALI (SL var) ===")
logs.clear()
class ExTp(Ex):
    def place_take_profit(s,sym,side,px,q): raise RuntimeError("TP reddedildi")
ex=ExTp()
pm._replace_protective_orders(ex,'BTCUSDT','SELL',95.0,110.0,1.0,eski_sl=90.0)
print(f"   SL={ex.sl_denemeleri} kapatilan={ex.kapatilan} (kapatilmamali)")
assert ex.sl_denemeleri==[95.0] and not ex.kapatilan
uyari=[l for l in logs if 'take-profit yenilenemedi' in l]
assert uyari
print("   SL var, risk sinirli -> pozisyon acik: OK")

print("\nKORUYUCU EMIR DEGISTIRME TESTLERI GECTI")

print("\n=== 6) Koruyucu emirler reduceOnly mi? (kismi kar sonrasi guvenlik) ===")
import inspect, exchange_client as EC
for ad in ['place_stop_loss','place_take_profit','close_position']:
    kaynak=inspect.getsource(getattr(EC.ExchangeClient, ad))
    var='reduceOnly=True' in kaynak
    print(f"   {ad:<20} reduceOnly={var}")
    assert var, f"{ad} reduceOnly kullanmiyor - kismi kar sonrasi TERS POZISYON acabilir!"
print("   Kismi kar alindiktan sonra eski miktarli SL zararsiz: OK")
