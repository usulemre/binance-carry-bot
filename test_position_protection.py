"""KORUMASIZ POZISYON testi.

Canlidaki en tehlikeli senaryo: pozisyon acildi ama stop-loss
kurulamadi. Bot eskiden sadece log basip pozisyonu KORUMASIZ
birakiyordu - kayip sinirsiz olabilirdi.
"""
import sys; sys.path.insert(0,'.')
import logging
logs=[]
class Yakala(logging.Handler):
    def emit(s,r): logs.append(r.getMessage())
lg=logging.getLogger('bot'); lg.addHandler(Yakala()); lg.setLevel(logging.DEBUG)

import config, main as M
from strategy import Signal
import position_manager as pm

class Ex:
    def __init__(s, sl_hata=False, tp_hata=False, kapat_hata=False):
        s.sl_hata=sl_hata; s.tp_hata=tp_hata; s.kapat_hata=kapat_hata
        s.acilan=[]; s.kapatilan=[]; s.sl_konan=[]; s.tp_konan=[]
    def get_symbol_precision(s,x): return {'quantity_precision':3,'price_precision':2}
    def set_leverage(s,a,b): pass
    def open_market_position(s,sym,side,q,**kw):
        s.acilan.append(sym); return {'status':'FILLED','executedQty':q,'orderId':1}
    def place_stop_loss(s,sym,side,px,q):
        if s.sl_hata: raise RuntimeError("SL emri reddedildi")
        s.sl_konan.append(sym)
    def place_take_profit(s,sym,side,px,q):
        if s.tp_hata: raise RuntimeError("TP emri reddedildi")
        s.tp_konan.append(sym)
    def close_position(s,sym,side,q,**kw):
        if s.kapat_hata: raise RuntimeError("kapatma basarisiz")
        s.kapatilan.append(sym)

class RM:
    def calculate_position_size(s,b,e,sl,sc=1.0): return 1.0

sig=Signal(symbol='BTCUSDT',direction='LONG',score=4.0,entry_price=100.0,
           stop_loss=95.0,take_profit=110.0,atr_value=2.0)

print("=== 1) NORMAL: SL ve TP kuruluyor ===")
logs.clear(); ex=Ex()
M.open_position_with_protection(ex, RM(), sig, 10000)
print(f"   acilan={ex.acilan} SL={ex.sl_konan} TP={ex.tp_konan} kapatilan={ex.kapatilan}")
assert ex.sl_konan and ex.tp_konan and not ex.kapatilan

print("\n=== 2) SL KURULAMADI -> pozisyon KAPATILMALI ===")
logs.clear(); ex=Ex(sl_hata=True)
M.open_position_with_protection(ex, RM(), sig, 10000)
print(f"   acilan={ex.acilan} SL={ex.sl_konan} kapatilan={ex.kapatilan}")
assert ex.kapatilan==['BTCUSDT'], "KORUMASIZ POZISYON BIRAKILDI!"
assert not ex.tp_konan, "SL yokken TP kurulmus"
print("   korumasiz pozisyon kapatildi: OK")

print("\n=== 3) SL kurulamadi VE kapatma da basarisiz -> ACIL UYARI ===")
logs.clear(); ex=Ex(sl_hata=True, kapat_hata=True)
M.open_position_with_protection(ex, RM(), sig, 10000)
acil=[l for l in logs if 'MANUEL MÜDAHALE' in l]
print(f"   acil uyari sayisi={len(acil)}")
assert acil, "kapatilamayan korumasiz pozisyon icin acil uyari yok!"
print(f"   uyari: {acil[0][:80]}...")

print("\n=== 4) TP kurulamadi -> pozisyon KAPATILMAMALI (SL var, risk sinirli) ===")
logs.clear(); ex=Ex(tp_hata=True)
M.open_position_with_protection(ex, RM(), sig, 10000)
print(f"   SL={ex.sl_konan} TP={ex.tp_konan} kapatilan={ex.kapatilan}")
assert ex.sl_konan and not ex.kapatilan, "TP hatasinda pozisyon gereksiz kapatildi!"
uyari=[l for l in logs if 'take-profit kurulamadı' in l]
assert uyari, "TP hatasi loglanmadi"
print("   pozisyon acik birakildi (dogru - SL var): OK")

print("\n=== 5) Emir DOLMADI -> SL/TP kurulmamali ===")
logs.clear()
class ExDolmaz(Ex):
    def open_market_position(s,sym,side,q,**kw):
        return {'status':'NEW','executedQty':0,'orderId':1}
ex=ExDolmaz()
M.open_position_with_protection(ex, RM(), sig, 10000)
print(f"   SL={ex.sl_konan} TP={ex.tp_konan} (ikisi de bos olmali)")
assert not ex.sl_konan and not ex.tp_konan

print("\nKORUMASIZ POZISYON TESTLERI GECTI")
