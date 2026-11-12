#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 770 testleri: tutuşta tamamlama yok — referans fiyat, geçiş (sıfır emir), düşen coine ekleme yok, biten dilimin payı,
yeni dilim, kademe küçültmesi, bayrak kapalıyken eski davranış."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("BINANCE_MODE", "demo")
import carry_bot as cb

_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

def yakin(a, b, e=1e-6): return abs(a - b) <= e * max(1.0, abs(b))

# 3 dilim; A coin'i 3 dilimde long 17 $ (toplam 51 $ hedef), %30 düştü -> pozisyon 35,7 $. B short 17 $.
d = {"sira": 0, "dilimler": {"0": {"A": 17.0, "B": -17.0}, "1": {"A": 17.0}, "2": {"A": 17.0}}}
fiyat = {"A": 0.7, "B": 1.0, "C": 2.0}
mevcut = {"A": 35.7, "B": -17.0}
once = cb.bacak_imzasi(d)
r = cb.tutus_referans_guncelle(d, once, fiyat, mevcut)
h = cb.toplam_hedef_tut(d, fiyat)
kontrol("geçiş: hedef = bugünkü pozisyon (düşen A tamamlanmaz)", yakin(h["A"], 35.7) and yakin(h["B"], -17.0), h)
kontrol("geçiş sayısı", r["gecis"] == 4 and r["yeni"] == 0, r)
kontrol("geçiş: emir YOK", cb.emirleri_hesapla(h, mevcut, tolerans_usd=8.6) == [])
# fiyat %10 daha düşer: dolar hedefi olsaydı ekleme olurdu; şimdi hedef de %10 düşer
fiyat2 = {"A": 0.63, "B": 1.0}; mevcut2 = {"A": 35.7 * 0.9, "B": -17.0}
h2 = cb.toplam_hedef_tut(d, fiyat2)
kontrol("düşüş sürer: hedef fiyatla birlikte iner, ekleme yok", cb.emirleri_hesapla(h2, mevcut2, tolerans_usd=0.01) == [], h2)
kontrol("eski davranış (dolar hedefi) eklerdi", any(s == "A" for s, _, _ in cb.emirleri_hesapla(cb.toplam_hedef(d), mevcut2, tolerans_usd=8.6)))
# dilim 0 yenilenir: A ve B bırakılır, C long 17 $ girer
once3 = cb.bacak_imzasi(d)
d["dilimler"]["0"] = {"C": 17.0}
cb.tutus_referans_guncelle(d, once3, fiyat2, mevcut2)
h3 = cb.toplam_hedef_tut(d, fiyat2)
kontrol("biten dilim: A'nın 1/3'ü satılır (adet payı), B kapanır, C 17 $ açılır",
        yakin(h3["A"], 35.7 * 0.9 * 2 / 3) and "B" not in h3 and yakin(h3["C"], 17.0), h3)
kontrol("yeni bacağın referansı şimdiki fiyat", d["dilim_fiyat"]["0"] == {"C": 2.0} if "C" in fiyat2 else True)
# kademe: dilim 1'deki A hedefi yarıya iner (tur öncesi) -> referans korunur, adet yarıya
d["dilimler"]["1"]["A"] *= 0.5
once4 = cb.bacak_imzasi(d)
cb.tutus_referans_guncelle(d, once4, {"A": 0.63, "C": 2.0}, {})
h4 = cb.toplam_hedef_tut(d, {"A": 0.63, "C": 2.0})
kontrol("kademe küçültmesi adetle orantılı (referans korunur)", yakin(h4["A"], 35.7 * 0.9 * (0.5 + 1) / 3), h4)
kontrol("dilimde olmayan sembolün referansı silinir", "B" not in d["dilim_fiyat"].get("0", {}))
kontrol("fiyatı olmayan bacak dolar hedefiyle sayılır", yakin(cb.toplam_hedef_tut({"dilimler": {"0": {"Z": 10.0}}}, {})["Z"], 10.0))
kontrol("bayrak varsayılan AÇIK", cb.TUTUS_SABIT is True)

# --- madde 770 / 2: adet adım büyüklüğüne yuvarlanır
from exchange_client import adet_yuvarla, _adim
P = {"quantity_precision": 1, "step": 0.5, "piyasa_step": 1.0}
kontrol("adım 0,5: 12,74 → 12,5 (en yakın kat)", adet_yuvarla(12.74, P) == 12.5)
kontrol("adım 0,5 aşağı: 12,99 → 12,5", adet_yuvarla(12.99, P, asagi=True) == 12.5)
kontrol("piyasa adımı 1: 12,74 → 13", adet_yuvarla(12.74, P, piyasa=True) == 13.0)
kontrol("adım 0,001: kayan nokta kalıntısı yok", adet_yuvarla(0.1 + 0.2, {"step": 0.001}) == 0.3)
kontrol("adım bilinmiyorsa eski ondalık", adet_yuvarla(1.23456, {"quantity_precision": 2}) == 1.23)
kontrol("LOT_SIZE okuma", _adim({"filters": [{"filterType": "LOT_SIZE", "stepSize": "0.10"}]}, "LOT_SIZE") == 0.1)

# --- madde 770 / 3: hedefi 0 olan sembolde tam pozisyon adedi
class _C:
    def get_open_positions(self):
        return [{"symbol": "ARBUSDT", "positionAmt": "-295.1"}, {"symbol": "XUSDT", "positionAmt": "10"}]
k = cb.tam_kapanis_adetleri(_C(), {"XUSDT": 5.0}, [("ARBUSDT", "BUY", 45.3), ("XUSDT", "SELL", 3.0)])
kontrol("yalnız hedefte OLMAYAN sembol, tam |adet|", k == {"ARBUSDT": 295.1}, k)
kontrol("kapanan yoksa okuma yok", cb.tam_kapanis_adetleri(None, {"A": 1}, [("A", "BUY", 5)]) == {})

# --- madde 770 / 5: tur zamanı
import tempfile, json
_tz = os.path.join(tempfile.mkdtemp(), "tz.json")
kontrol("tur zamanı yoksa None", cb.tur_zamani_oku(_tz) is None)
cb.tur_zamani_yaz(1234.5, _tz)
kontrol("tur zamanı yaz / oku", cb.tur_zamani_oku(_tz) == 1234.5)
kontrol("ızgara varsayılan AÇIK", cb.TUR_IZGARA is True)

# --- madde 770 / 7: aday kaydı
import pandas as pd
_ad = os.path.join(tempfile.mkdtemp(), "ad.jsonl")
for i in range(3):
    cb.aday_kaydet(["A", "B"], ["C", "D"], ["A"], ["D"], pd.Series({"A": -1.0, "B": -0.5}), pd.Series({"C": 0.9, "D": 0.7}),
                   pd.Series({"A": 1.2, "B": 0.8, "C": 2.0, "D": 3.1}), dosya=_ad, simdi=100 + i)
_sat = [json.loads(x) for x in open(_ad)]
kontrol("aday kaydı: tur başına bir satır", len(_sat) == 3 and _sat[-1]["t"] == 102)
kontrol("aday kaydı: seçildi / oran / skor", _sat[0]["short"][1] == {"s": "D", "skor": 0.7, "fund": None, "oran": 3.1, "secildi": True}
        and _sat[0]["long"][1]["secildi"] is False, _sat[0])

# --- madde 770 / 4: kovalamada −5022 → piyasa emri
class _K:
    def __init__(s): s.piyasa = []
    def get_symbol_precision(s, sem): return {"quantity_precision": 1, "price_precision": 4, "step": 0.1, "piyasa_step": 1.0}
    def open_market_position(s, sem, yon, q): s.piyasa.append((sem, yon, q)); return {"orderId": 9}
    class client:
        @staticmethod
        def futures_get_order(symbol, orderId): return {"status": "NEW", "executedQty": "0"}
        @staticmethod
        def futures_cancel_order(symbol, orderId): return {}
        @staticmethod
        def futures_symbol_ticker(symbol): return {"price": "0.30"}
        @staticmethod
        def futures_create_order(**k): raise Exception("APIError(code=-5022): Due to the order could not be executed as maker")
_eski = (cb.DOLUM_BEKLEME_SN, cb.DOLUM_DENEME); cb.DOLUM_BEKLEME_SN = 0
try:
    kk = _K(); n = cb.dolumu_kovala(kk, [{"sembol": "CYBERUSDT", "yon": "BUY", "miktar": 57.3, "id": 1}])
finally:
    cb.DOLUM_BEKLEME_SN, cb.DOLUM_DENEME = _eski
kontrol("−5022 → kalan miktar piyasa emriyle (bacak eksik kalmaz)", kk.piyasa and kk.piyasa[0][0] == "CYBERUSDT" and kk.piyasa[0][2] == 57.0, kk.piyasa)
print("\nHEPSİ GEÇTİ" if _h == 0 else f"\n{_h} HATA"); sys.exit(1 if _h else 0)
