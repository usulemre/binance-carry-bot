"""carry_rapor.py testleri (madde 171).

En kritik test: aracın KARAR verirken doğru eşikleri uygulaması.
Yanlış tarafa düşen bir eşik, aracı ya sürekli alarm veren (ve bu
yüzden kapatılan) ya da hiç alarm vermeyen (ve bu yüzden işe
yaramayan) bir şeye dönüştürür.
"""
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carry_rapor as cr
import carry_sapma as cs

gecen = basarisiz = 0


def kontrol(ad, kosul, ek=""):
    global gecen, basarisiz
    if kosul:
        gecen += 1
        print(f"  [OK]   {ad}")
    else:
        basarisiz += 1
        print(f"  [HATA] {ad} {ek}")


def b(gun=40, dusus=-0.05, ort=0.0013, yas=2.0):
    """Sahte bakiye özeti."""
    g = pd.Series([ort] * gun)
    return {"gun": gun, "getiri": ort * gun, "dusus": dusus, "gunluk_ort": ort,
            "seri": g, "bakiye": 10000.0, "ilk_bakiye": 10000.0,
            "son_kayit_saat": yas}


NORMAL = {"durum": "NORMAL", "yuzdelik": 50.0, "guc": 30.0}
ACIK = {"var": True, "acik": True}
YOK = {"var": False}

print("1) DÜŞÜŞ EŞİKLERİ")
d, s = cr.karar(b(dusus=-0.10), NORMAL, ACIK, YOK)
kontrol("−%10 düşüş DEVAM (backtest maksimumunun içinde)", d == "DEVAM", f"({d}, {s})")
d, s = cr.karar(b(dusus=-0.16), NORMAL, ACIK, YOK)
kontrol("−%16 düşüş DEVAM (normal yılın p5'i −%16,8 - madde 222)",
        d == "DEVAM", f"({d})")
# MADDE 233: esikler KODDAN turetilir. Bu test eskiden -%23'u "INCELE"
# diye sabit yaziyordu; o, madde 175'in curutulmus esiklerinden
# (-%20/-%25) geliyordu ve madde 233 esikleri -%18/-%23'e cektiginde
# kirildi. Sabit yazilan esik, esigin bayatligini GIZLER.
# MADDE 378: karar() esikleri ham DUSUS_INCELE/DURDUR'dan degil, KOSULAN
# kitaptan (ilk_bakiye -> kitap_anahtari -> dusus_incele/durdur) okur
# (madde 329/341). Test ham sabitleri kullandigi icin o maddelerden beri
# kirikti. Artik karar()'in kendi kuralindan turetiliyor.
_ANK = cr.kitap_anahtari(bakiye=10000.0)
_KI, _KD = cr.dusus_incele(_ANK, 10000.0), cr.dusus_durdur(_ANK, 10000.0)
_ara = (_KI + _KD) / 2       # iki esigin arasi
d, s = cr.karar(b(dusus=_ara), NORMAL, ACIK, YOK)
kontrol(f"iki eşik ARASI (%{_ara*100:.1f}) İNCELE", d == "İNCELE", f"({d})")
_asagi = _KD - 0.04
d, s = cr.karar(b(dusus=_asagi), NORMAL, ACIK, YOK)
kontrol(f"DURDUR eşiğinin ALTI (%{_asagi*100:.1f}) DURDUR", d == "DURDUR", f"({d})")
kontrol("DURDUR gerekçesinde gerçekleşen düşüş yazılı",
        any(f"{_asagi*100:.1f}" in x for x in s), f"({s})")
# esigin HEMEN ustu/alti: sinir davranisi
d, _ = cr.karar(b(dusus=_KI + 0.001), NORMAL, ACIK, YOK)
kontrol("İNCELE eşiğinin hemen ÜSTÜ DEVAM", d == "DEVAM", f"({d})")
d, _ = cr.karar(b(dusus=_KD - 0.001), NORMAL, ACIK, YOK)
kontrol("DURDUR eşiğinin hemen ALTI DURDUR", d == "DURDUR", f"({d})")

print("\n2) SAPMA DURUMU")
d, _ = cr.karar(b(), {"durum": "CİDDİ SAPMA", "yuzdelik": 1.0, "guc": 40}, ACIK, YOK)
kontrol("CİDDİ SAPMA -> DURDUR", d == "DURDUR", f"({d})")
_, s = cr.karar(b(), {"durum": "CİDDİ SAPMA", "yuzdelik": 1.0, "guc": 40}, ACIK, YOK)
kontrol("CİDDİ SAPMA gerekçesi KALDIRAÇ uyarısı içeriyor",
        any("KALDIRAÇ" in x for x in s), f"({s})")
d, _ = cr.karar(b(), {"durum": "BEKLENENİN ALTINDA", "yuzdelik": 3.0, "guc": 40}, ACIK, YOK)
kontrol("BEKLENENİN ALTINDA -> İNCELE", d == "İNCELE", f"({d})")
d, _ = cr.karar(b(), {"durum": "BEKLENENİN ÇOK ÜSTÜNDE", "yuzdelik": 99.0, "guc": 40}, ACIK, YOK)
kontrol("çok iyi gitmek alarm ÜRETMİYOR", d == "DEVAM", f"({d})")

print("\n3) SAĞLIK KAPISI")
d, _ = cr.karar(b(), NORMAL, {"var": True, "acik": False}, YOK)
kontrol("kapı KAPALI -> İNCELE", d == "İNCELE", f"({d})")
d, _ = cr.karar(b(), NORMAL, {"var": False, "acik": True}, YOK)
kontrol("sağlık dosyası YOKSA alarm üretmiyor", d == "DEVAM", f"({d})")

print("\n4) FUNDING TAHSİLATI")
# MADDE 232: beklenen funding artik TURETILMIYOR, OLCULEN tabandan
# geliyor. Eski satir `BEKLENEN_GUNLUK * 0.94` kullaniyordu ve o 0,94
# madde 136'nin "funding gelirinin %94'u LONG bacaktan" cumlesinin
# yanlis etiketlenmis haliydi. Test de o yanlis formulu tasiyordu -
# yani yanlis beklentiyi DOGRULUYORDU. Artik koddan turetiliyor.
_bekl = cr.BEKLENEN_FUNDING_TABAN * 40 * 10000
# saglikli bir bot HER rejimde tabanin ustunde okur (madde 232)
for _ad, _v in (("dusuk prim", cr.BEKLENEN_FUNDING_TABAN),
                ("harman", cr.BEKLENEN_FUNDING_GUNLUK),
                ("yuksek prim", cr.BEKLENEN_FUNDING_YUKSEK)):
    _d, _ = cr.karar(b(), NORMAL, ACIK,
                     {"var": True, "funding": _v * 40 * 10000})
    kontrol(f"SAGLIKLI bot ({_ad}) alarm URETMIYOR", _d == "DEVAM", f"({_d})")
d, _ = cr.karar(b(), NORMAL, ACIK, {"var": True, "funding": _bekl * 0.95})
kontrol("beklentinin %95'i -> DEVAM", d == "DEVAM", f"({d})")
d, _ = cr.karar(b(), NORMAL, ACIK, {"var": True, "funding": _bekl * 0.70})
kontrol("beklentinin %70'i -> İNCELE", d == "İNCELE", f"({d})")
d, _ = cr.karar(b(), NORMAL, ACIK, {"var": True, "funding": _bekl * 0.30})
kontrol("beklentinin %30'u -> DURDUR", d == "DURDUR", f"({d})")
d, s = cr.karar(b(), NORMAL, ACIK, {"var": True, "funding": _bekl * 1.10})
kontrol("beklentinin üstü alarm üretmiyor, gerekçeye yazılıyor",
        d == "DEVAM" and any("funding" in x for x in s), f"({d}, {s})")

print("\n5) EN KÖTÜ SİNYAL KAZANIR")
d, _ = cr.karar(b(dusus=-0.23), {"durum": "CİDDİ SAPMA", "yuzdelik": 1.0, "guc": 40},
                ACIK, YOK)
kontrol("İNCELE + DURDUR -> DURDUR", d == "DURDUR", f"({d})")
d, s = cr.karar(b(dusus=_ara), NORMAL, {"var": True, "acik": False}, YOK)
kontrol("iki ayrı İNCELE -> İNCELE, iki gerekçe",
        d == "İNCELE" and len([x for x in s if "İNCELE" in x]) == 2, f"({d}, {s})")

print("\n6) İLK GÜNLER")
d, s = cr.karar(b(gun=3, dusus=-0.30), {"durum": "YETERSİZ"}, ACIK, YOK)
kontrol("ilk 5 günde düşüş alarmı ÜRETİLMİYOR (kitap kuruluyor)",
        d == "DEVAM", f"({d})")
kontrol("ilk 5 gün notu veriliyor", any("kurulum" in x for x in s), f"({s})")

print("\n6b) ÖLÜ BOT DEDEKTÖRÜ (en tehlikeli sessiz hâl)")
d, _ = cr.karar(b(yas=20), NORMAL, ACIK, YOK)
kontrol("20 saat önce tur atmış -> DEVAM (normal aralık)", d == "DEVAM", f"({d})")
d, s = cr.karar(b(yas=40), NORMAL, ACIK, YOK)
kontrol("40 saattir tur yok -> İNCELE", d == "İNCELE", f"({d})")
d, s = cr.karar(b(yas=100), NORMAL, ACIK, YOK)
kontrol("4 gündür tur yok -> DURDUR", d == "DURDUR", f"({d})")
kontrol("gerekçe pozisyonların YÖNETİLMEDİĞİNİ söylüyor",
        any("yönetilmiyor" in x for x in s), f"({s})")
# KRİTİK: ilk 5 gün kısa devresi ölü bot alarmını EZMEMELİ
d, s = cr.karar(b(gun=3, yas=100), {"durum": "YETERSİZ"}, ACIK, YOK)
kontrol("ilk 5 günde bile ÖLÜ BOT alarmı geçerli", d == "DURDUR", f"({d}, {s})")
# donmus dosya: getiri iyi gorunurken bot olmus olabilir
d, _ = cr.karar(b(dusus=-0.01, ort=0.002, yas=120), NORMAL, ACIK, YOK)
kontrol("getiri İYİ görünse bile ölü bot DURDUR", d == "DURDUR", f"({d})")

print("\n7) BAKİYE ÖZETİ VE RAPOR METNİ")
yol = tempfile.mktemp(suffix=".csv")
bas = time.time() - 86400 * 40   # son kayit SIMDI olsun
with open(yol, "w", encoding="utf-8") as fh:
    v = 10000.0
    fh.write(f"{bas:.0f},{v:.4f},1.000000\n")
    for i in range(40):
        v *= 1 + 0.0013
        fh.write(f"{bas + 86400*(i+1):.0f},{v:.4f},1.000000\n")
o = cr.bakiye_ozet(yol)
kontrol("bakiye özeti 40 gün okuyor", o["gun"] == 40, f"({o['gun']})")
kontrol("getiri doğru (~%5.3)", abs(o["getiri"] - (1.0013**40 - 1)) < 1e-6,
        f"({o['getiri']:.4f})")
kontrol("sürekli artan seride düşüş ~0", abs(o["dusus"]) < 1e-9, f"({o['dusus']})")
kontrol("dosya yoksa gun=0 döner, çökmüyor",
        cr.bakiye_ozet("/tmp/olmayan_xyz.csv").get("gun") == 0)
kontrol("son kayıt yaşı ölçülüyor (taze dosyada ~0 saat)",
        o.get("son_kayit_saat", 999) < 1.0, f"({o.get('son_kayit_saat')})")

m = cr.yaz(7, api=False, dosya=yol)
kontrol("rapor KARAR satırı içeriyor", "KARAR:" in m, "(yok)")
kontrol("rapor eşikleri gösteriyor", "incele" in m and "durdur" in m)
kontrol("rapor normal zarar istatistiklerini hatırlatıyor",
        "zararlı ay" in m and "118 gün" in m)
kontrol("rapor son tur zamanını gösteriyor", "son tur" in m, "(yok)")
kontrol("30 günden kısa uyarısı KOŞULLU (40 günde yok)",
        "ölü stratejiyi yakalama gücü" not in m or o["gun"] < 30)

print("\n8) SİNYAL TANIMI PARİTESİ RAPORA BAĞLI (madde 210)")
# Madde 209'da canli bot backtest'ten FARKLI bir funding penceresi
# kullaniyordu; beklenti (%0.194/gun) o ayarla olculmemisti ve raporun
# butun kiyaslari yanlis olcute bakiyordu. Artik rapor DURDUR diyor.
import carry_bot as _cb
kontrol("doğru ayarda parite raporu BOZMUYOR", "DURDUR" not in m.splitlines()[1],
        f"({m.splitlines()[1]})")
_eski_pen = _cb.FUNDING_WINDOW_HOURS
_cb.FUNDING_WINDOW_HOURS = 8.0
_mb = cr.yaz(7, api=False, dosya=yol)
kontrol("pencere ayrışınca rapor DURDUR diyor", "DURDUR" in _mb)
kontrol("gerekçe PARİTE'yi adıyla söylüyor", "PARİTE" in _mb)
kontrol("gerekçe beklentinin geçersiz olduğunu söylüyor",
        "ÖLÇÜLMEDİ" in _mb or "GEÇERSİZ" in _mb)
# Parite bir AYAR hatasi: ilk turdan itibaren gecerli, "ilk 5 gun"
# muafiyeti onu susturmamali.
_yol3 = tempfile.mktemp(suffix=".csv")
_b3 = time.time() - 86400 * 3
with open(_yol3, "w", encoding="utf-8") as fh:
    for i in range(4):
        fh.write(f"{_b3 + 86400*i:.0f},{10000*(1.001**i):.4f},1.000000\n")
kontrol("parite hatası ilk 5 gün kuralından ÖNCE kontrol ediliyor",
        "DURDUR" in cr.yaz(7, api=False, dosya=_yol3))
_cb.FUNDING_WINDOW_HOURS = _eski_pen
kontrol("ayar geri gelince rapor yine DEVAM",
        "DURDUR" not in cr.yaz(7, api=False, dosya=yol).splitlines()[1])

print("\n" + "=" * 56)
print(f"GEÇEN: {gecen}   BAŞARISIZ: {basarisiz}")
if basarisiz:
    sys.exit(1)
print("Tum rapor testleri gecti.")
