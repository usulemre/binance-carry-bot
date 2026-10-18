"""ÖN KAYITLI KARAR KURALI TESTLERİ (madde 212).

Kural prose'tan koda taşındı çünkü madde 212'de bir DELİĞİ bulundu:
`wins` varyantı iki dönemde de Sharpe'ı yükseltip düşüşü tolerans içinde
tutarak kuralı GEÇİYORDU, ama eşit riskte +94,7 → +78,3'e geriliyordu.

Buradaki testler (a) o deliğin kapandığını, (b) kuralın GEÇMİŞ kabul
kararlarını geriye dönük ÇÜRÜTMEDİĞİNİ doğrular. İkincisi kritik: yeni
bir şart eklediysem ve o şart eski kabulleri reddediyorsa, ya şart yanlış
ya eski kabul yanlış - ikisi de sessizce geçilemez.
"""
import sys

from karar_kurali import MADDE_212, Olcum, gecer_mi, yaz

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad} {detay}")
        basarisiz.append(ad)


K = MADDE_212["kontrol"]
A = {a.ad: a for a in MADDE_212["adaylar"]}

print("1) DÖRT ŞART AYRI AYRI ÇALIŞIYOR")
_hepsi = Olcum("her şeyi iyi", 110.0, 3.20, 3.00, 3.30, 14.0)
_r = gecer_mi(K, _hepsi)
kontrol("her şeyi iyileştiren aday GEÇER", _r["gecer"], f"({_r['gerekce']}")
kontrol("dört şart da raporlanıyor", len(_r["sartlar"]) == 4,
        f"({list(_r['sartlar'])})")
# MADDE 225: gunluk seri verilmeyince kaldirac NaN'dir -> 4. sart
# ELEMEZ (yaklasik moddaki eski cagrilar bozulmasin).
kontrol("günlük seri yokken 4. şart ELEMİYOR",
        _r["sartlar"]["kaldıraç gerektirmiyor"][0])
# sart 1: TEK donemde iyilesme yetmez (donem secmekten ayirt edilemez)
_tek = Olcum("tek dönem", 120.0, 3.10, 2.60, 3.60, 14.0)
kontrol("SADECE 25-26'da iyileşen aday RED",
        not gecer_mi(K, _tek)["gecer"])
kontrol("gerekçe 'iki dönemde Sharpe'ı gösteriyor",
        "iki dönemde Sharpe" in gecer_mi(K, _tek)["gerekce"])
_tek2 = Olcum("tek dönem 2", 120.0, 3.10, 3.20, 3.00, 14.0)
kontrol("SADECE 22-24'te iyileşen aday da RED",
        not gecer_mi(K, _tek2)["gecer"])
kontrol("BERABERLİK iyileşme sayılmıyor (kesin büyük olmalı)",
        not gecer_mi(K, Olcum("eşit", 120.0, 3.1, K.erken, 3.30, 14.0))["gecer"])
# sart 2: dusus toleransi
_derin = Olcum("derin düşüş", 200.0, 3.50, 3.00, 3.30, K.dusus + 3.01)
kontrol("düşüş 3 puandan fazla kötüleşirse RED",
        not gecer_mi(K, _derin)["gecer"])
kontrol("tam 3 puan kötüleşme GEÇER (sınır dahil)",
        gecer_mi(K, Olcum("sınırda", 200.0, 3.5, 3.0, 3.3,
                          K.dusus + 3.0))["gecer"])
kontrol("tolerans parametreyle değiştirilebiliyor",
        gecer_mi(K, _derin, tolerans=5.0)["gecer"])

print("\n2) MADDE 212'NİN DELİĞİ KAPANDI")
_w = gecer_mi(K, A["wins"])
kontrol("`wins` REDDEDİLİYOR", not _w["gecer"])
kontrol("`wins` şart 1'i (iki dönemde Sharpe) GEÇİYOR",
        _w["sartlar"]["iki dönemde Sharpe"][0],
        "kuralın eski hâli bu yüzden EVET diyordu")
kontrol("`wins` şart 2'yi (düşüş toleransı) de GEÇİYOR",
        _w["sartlar"]["düşüş toleransı"][0])
kontrol("`wins` SADECE şart 3'te (eşit riskte getiri) düşüyor",
        not _w["sartlar"]["eşit riskte getiri"][0]
        and _w["gerekce"] == "geçmeyen şart: eşit riskte getiri",
        f"({_w['gerekce']})")
kontrol("eşit risk hesabı doğru (87.2 x 15.45/17.20 = 78.3)",
        abs(_w["esit_risk"] - 87.2 * 15.45 / 17.20) < 1e-9,
        f"({_w['esit_risk']:.2f})")
kontrol("eşit risk kontrolün getirisinin ALTINDA",
        _w["esit_risk"] < K.getiri, f"({_w['esit_risk']:.1f} vs {K.getiri})")

print("\n3) MADDE 212'NİN BÜTÜN ADAYLARI REDDEDİLİYOR")
for ad, a in A.items():
    kontrol(f"{ad} RED", not gecer_mi(K, a)["gecer"])
kontrol("kontrolün kendisi kendine karşı GEÇMEZ (beraberlik)",
        not gecer_mi(K, K)["gecer"],
        "aynı kitap iyileşme değildir")

print("\n4) GEÇMİŞ KABULLER GERİYE DÖNÜK ÇÜRÜTÜLMÜYOR")
# Madde 209: funding penceresi 8sa -> 48sa. Kontrol canlinin FIILI hali.
_k209 = Olcum("8 saat (canlının hâliydi)", 78.6, 2.710, 2.800, 2.625, 13.05)
_a209 = Olcum("48 saat", 96.8, 3.015, 2.965, 3.110, 13.70)
_r209 = gecer_mi(_k209, _a209)
kontrol("madde 209 (8sa -> 48sa) YENİ kuralla da KABUL", _r209["gecer"],
        f"({_r209['gerekce']})")
kontrol("madde 209 eşit riskte de KAZANIYOR",
        _r209["esit_risk"] > _k209.getiri,
        f"({_r209['esit_risk']:.1f} vs {_k209.getiri})")
# Madde 196: uc hareket elemesi. Getiriyi 3,8 puan DUSURDU ama riski
# iyilestirdi - esit riskte +102,1 (o zamanki rapor).
_k196 = Olcum("elemesiz", 96.8, 2.840, 2.700, 3.000, 18.0)
_a196 = Olcum("UCELE=0.40", 93.0, 2.908, 2.780, 3.060, 16.2)
_r196 = gecer_mi(_k196, _a196)
kontrol("madde 196 (uç hareket elemesi) YENİ kuralla da KABUL",
        _r196["gecer"], f"({_r196['gerekce']})")
kontrol("madde 196 GETİRİYİ düşürdüğü hâlde geçiyor - çünkü eşit riskte kazanıyor",
        _a196.getiri < _k196.getiri and _r196["esit_risk"] > _k196.getiri,
        f"(getiri {_a196.getiri} < {_k196.getiri}, "
        f"eşit risk {_r196['esit_risk']:.1f} > {_k196.getiri})")

print("\n5) SINIR DURUMLARI")
kontrol("düşüş sıfırsa eşit risk NaN, çökmüyor",
        gecer_mi(K, Olcum("sıfır düşüş", 100.0, 3.0, 3.0, 3.3, 0.0))
        is not None)
kontrol("sıfır düşüşlü aday GEÇEMEZ (ölçülemeyen risk kabul edilmez)",
        not gecer_mi(K, Olcum("sıfır düşüş", 100.0, 3.0, 3.0, 3.3, 0.0))["gecer"])
_neg = Olcum("zarar eden", -20.0, -0.5, -0.4, -0.6, 40.0)
kontrol("zarar eden aday RED", not gecer_mi(K, _neg)["gecer"])
kontrol("esit_risk_getiri ölçekleme doğru yönde",
        Olcum("x", 100.0, 3, 3, 3, 20.0).esit_risk_getiri(10.0) == 50.0)

print("\n6b) GERÇEK KALDIRAÇLI EŞİT RİSK (madde 218)")
# Madde 218: dogrusal olcekleme bir kararı TERSINE cevirdi. Bilesik getiri
# kaldiracta KONVEKS (%0,1/gun -> +%44/yil, %0,2/gun -> +%107/yil).
import numpy as _np
from karar_kurali import esit_risk_gercek, _stat
_r = _np.random.default_rng(1).normal(0.002, 0.012, 1500)
_y, _dd = _stat(_r)
_k, _ye, _dde = esit_risk_gercek(_r, _dd * 100.0)
kontrol("aynı hedef düşüşte kaldıraç TAM 1.0", abs(_k - 1.0) < 0.01,
        f"({_k:.4f})")
kontrol("aynı hedefte getiri de aynı", abs(_ye - _y * 100) < 0.5,
        f"({_ye:.2f} vs {_y*100:.2f})")
_k2, _ye2, _dde2 = esit_risk_gercek(_r, _dd * 100.0 / 2)
kontrol("hedef yarıya inince kaldıraç 1'in ALTINA iniyor", _k2 < 1.0,
        f"({_k2:.3f})")
kontrol("ulaşılan düşüş hedefi tutuyor", abs(_dde2 - _dd * 100 / 2) < 0.2,
        f"({_dde2:.2f} vs {_dd*100/2:.2f})")
# MADDE 218 BIRIM HATASI REGRESYONU: ilk surum hedefi KESIR ile
# karsilastirinca kaldirac ust sinira dayanip +%4.045 gibi sacma sonuc
# veriyordu. Kaldirac artik makul aralikta kalmali.
kontrol("kaldıraç üst sınıra DAYANMIYOR (birim hatası regresyonu)",
        _k < 7.9 and _k2 < 7.9, f"({_k:.2f}, {_k2:.2f})")
kontrol("getiri saçma büyüklükte DEĞİL (birim hatası regresyonu)",
        _ye < 1000.0, f"(%{_ye:.0f})")
# KONVEKSLIK: dogrusal yaklasim gercekten farkli mi
_dusuk = _np.random.default_rng(2).normal(0.0008, 0.004, 1500)
_yd, _ddd = _stat(_dusuk)
_kk, _yek, _ = esit_risk_gercek(_dusuk, _dd * 100.0)     # daha derin hedefe LEVER
_dogrusal = _yd * 100 * (_dd * 100) / (_ddd * 100)
kontrol("düşük oynaklıklı seride GERÇEK kaldıraç doğrusaldan YÜKSEK "
        "(konvekslik)", _yek > _dogrusal,
        f"(gerçek %{_yek:.1f} vs doğrusal %{_dogrusal:.1f})")
# gecer_mi gunluk seri verilince YAKLASIK olmadigini isaretlemeli
_ka = Olcum("kontrol", _y * 100, 2.0, 2.0, 2.0, _dd * 100)
_ad = Olcum("aday", _yd * 100, 2.5, 2.5, 2.5, _ddd * 100)
_r1 = gecer_mi(_ka, _ad)
_r2 = gecer_mi(_ka, _ad, gunluk_kontrol=_r, gunluk_aday=_dusuk)
kontrol("seri verilmezse yaklaşık işaretlenir", _r1["yaklasik"] is True)
kontrol("seri verilirse yaklaşık DEĞİL", _r2["yaklasik"] is False)
kontrol("gerekçede kaldıraç yazılı",
        "kaldıraç" in _r2["sartlar"]["eşit riskte getiri"][1])
kontrol("yaklaşık hâlde bu UYARILIYOR",
        "YAKLAŞIK" in _r1["sartlar"]["eşit riskte getiri"][1])
kontrol("gerçek hesap yaklaşıktan DAHA YÜKSEK eşit-risk veriyor",
        _r2["esit_risk"] > _r1["esit_risk"],
        f"(gerçek {_r2['esit_risk']:.1f}, yaklaşık {_r1['esit_risk']:.1f})")
# MADDE 218'IN GERCEK VAKASI: capraz kitap harmani. Dogrusal hesap RED
# (+%91,1 < +%96,8) verirken gercek kaldiracla KABUL (+%103,4).
_kon218 = Olcum("ana kitap", 96.8, 2.837, 2.786, 2.922, 13.70)
_ad218 = Olcum("harman %50 çapraz", 44.0, 2.923, 2.892, 2.995, 6.99)
_y218 = gecer_mi(_kon218, _ad218)                       # yaklaşık
kontrol("madde 218 vakası: YAKLAŞIK hesap RED veriyordu",
        not _y218["gecer"]
        and not _y218["sartlar"]["eşit riskte getiri"][0],
        f"(yaklaşık %{_y218['esit_risk']:.1f})")
kontrol("madde 218 vakası: iki dönemde Sharpe ZATEN geçiyordu",
        _y218["sartlar"]["iki dönemde Sharpe"][0]
        and _y218["sartlar"]["düşüş toleransı"][0],
        "yani karar SADECE eşit-risk şartında dönüyordu")
kontrol("madde 218 vakası: ölçülen gerçek eşit-risk kontrolü GEÇİYOR",
        103.4 > _kon218.getiri, "(+%103,4 vs +%96,8 - ölçüm harman4/5'te)")

print("\n6) TABLO METNİ")
_m = yaz(K, MADDE_212["adaylar"])
kontrol("tabloda KONTROL satırı var", "KONTROL" in _m)
kontrol("tabloda eşit-risk kolonu var", "eşit-risk" in _m)
kontrol("her aday için karar yazılı",
        all(a.ad in _m for a in MADDE_212["adaylar"]))
kontrol("reddedilen adayın geçmeyen şartı GEREKÇELENDİRİLİYOR",
        "geçmeyen şart" in _m)
kontrol("`wins` satırında RED yazıyor",
        any("wins" in l and "RED" in l for l in _m.splitlines()))


print("\n7) MADDE 225 - DORDUNCU SART: KALDIRAC GEREKTIRMEYECEK")
# Aday SADECE nakit tutarak daha sig dusuyorsa (Sharpe ayni, getiri ve
# dusus birlikte kuculmus), esit-risk kiyasi onu kaldiracla geri sisirir
# ve "daha iyi" gosterir. Motor likidasyonu modellemez; bu bir PARAMETRE
# karari degil KALDIRAC kararidir. Madde 225'te rezerv 0,30 ve 0,40 tam
# bunu yapti: uc sartin ucunu de geciyorlardi.
import numpy as _np
_rng = _np.random.default_rng(3)
_taban = _rng.normal(0.002, 0.02, 1500)
_kontrol_g = _taban
_aday_g = _taban * 0.7           # SADECE nakde cekilmis hali
_k = Olcum("kontrol", 100.0, 3.00, 2.90, 3.10, 15.0)
_a = Olcum("nakit", 60.0, 3.00, 2.91, 3.11, 10.5)
_s = gecer_mi(_k, _a, gunluk_kontrol=_kontrol_g, gunluk_aday=_aday_g)
kontrol("saf nakit adayin esit-risk kaldiraci 1'in USTUNDE",
        _s["kaldirac"] > 1.0, f"({_s['kaldirac']:.3f})")
kontrol("4. sart bu adayi ELIYOR", not _s["sartlar"]["kaldıraç gerektirmiyor"][0])
kontrol("gerekce KALDIRAC kararindan bahsediyor",
        "KALDIRAÇ kararıdır" in _s["sartlar"]["kaldıraç gerektirmiyor"][1])
# ters yon: aday DAHA riskliyse kaldirac 1'in altinda, 4. sart elemez
_a2 = Olcum("riskli", 150.0, 3.00, 2.91, 3.11, 22.0)
_s2 = gecer_mi(_k, _a2, gunluk_kontrol=_kontrol_g, gunluk_aday=_taban * 1.5)
kontrol("daha RISKLI aday (kaldirac<1) 4. sarttan ELENMIYOR",
        _s2["sartlar"]["kaldıraç gerektirmiyor"][0], f"({_s2['kaldirac']:.3f})")
# madde 222'nin KABUL edilen adayi 0,94x ile gecmisti - geriye donuk kirilmamali
kontrol("madde 222 vakasi (kaldirac 0,94) 4. sarttan gecerdi", 0.94 <= 1.0)


# MADDE 226: ikili aramanin 1.0 artigi YANLIS RED vermemeli
from karar_kurali import KALDIRAC_TOLERANS
kontrol("kaldirac toleransi iki haneye yuvarlaninca 1.00",
        abs(round(KALDIRAC_TOLERANS, 2) - 1.00) < 1e-9)
_s3 = gecer_mi(_k, _a, gunluk_kontrol=_kontrol_g, gunluk_aday=_taban * 0.9995)
kontrol("1.0005x gibi arama artigi 4. sarttan ELENMIYOR (madde 226)",
        _s3["sartlar"]["kaldıraç gerektirmiyor"][0], f"({_s3['kaldirac']:.4f})")
_s4 = gecer_mi(_k, _a, gunluk_kontrol=_kontrol_g, gunluk_aday=_taban * 0.85)
kontrol("gercek kaldirac (1.1x civari) HALA ELENIYOR",
        not _s4["sartlar"]["kaldıraç gerektirmiyor"][0], f"({_s4['kaldirac']:.4f})")


# MADDE 227: aday KALDIRACSIZ zaten ustunse 4. sart ELEMEMELI.
# Madde 225'te sart TEK ornekten (nakit kadrani) yazildi ve fazla
# genellendi; TPL 0,60 kontrolu hem getiride hem dususte geciyordu ama
# 1,031x yuzunden RED aliyordu.
_ust = Olcum("ustun", 121.0, 2.95, 2.95, 3.28, 14.1)   # getiri YUKSEK, dusus SIG
_s5 = gecer_mi(_k, _ust, gunluk_kontrol=_kontrol_g, gunluk_aday=_taban * 1.03)
kontrol("kaldiracsiz USTUN aday 4. sarttan ELENMIYOR (madde 227)",
        _s5["sartlar"]["kaldıraç gerektirmiyor"][0])
kontrol("gerekce kaldiracin KOZMETIK oldugunu soyluyor",
        "kozmetik" in _s5["sartlar"]["kaldıraç gerektirmiyor"][1]
        or _s5["kaldirac"] <= 1.005)
# nakit kadrani (getiri DUSUK) hala elenmeli - madde 225 korunuyor
kontrol("nakit kadrani (getirisi DUSUK aday) HALA eleniyor",
        not _s["sartlar"]["kaldıraç gerektirmiyor"][0])

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum karar kurali testleri gecti.")
print("""
NE DOGRULANDI: kuralin UC sarti, madde 212'de bulunan deligin kapandigi,
ve yeni sartin GECMIS kabulleri (196, 209) geriye donuk curutmedigi.

NE DOGRULANMADI: sartlarin DOGRU sartlar oldugu. Kural bir SECIM;
gerekcesi karar_kurali.py'nin docstring'inde yazili. Tolerans 3 puan ve
"iki donemde de iyilesme" birer esik, olculmus optimum degil.
""")
