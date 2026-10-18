#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 262 — YAYINLANAN SAYILARIN TEK KAYNAĞI, ve KUYRUK BELİRSİZLİĞİNİN
GERÇEK KAYNAĞI.

Bu tur bir ADAY ARAMASI DEĞİL. 261 maddedir yayınlanan sayılar birbirine
atıfla taşınıyordu; bu modül onları TEK bir kaynaktan, kodla yeniden üretir
ve yayınlanan kuyrukların belirsizliğinin NEREDEN geldiğini ölçer.

NEDEN BU TUR
------------
Belgelerde "1 yıl getiri p5" ÜÇ farklı değerle geçiyordu: +%41,1
(CANLIYA_CIKIS rejim tablosu, madde 231) · +%41,4 (README doz tablosu,
madde 245) · +%41,5 (CANLIYA_CIKIS başlık tablosu). Üçü de AYNI kitabın
AYNI ölçüsü. Hangisi doğru sorusunun cevabı, beklenenden daha öğreticiydi.

BULGU 1 — TEK KAYNAK VAR, VE /tmp'DE DEĞİL
------------------------------------------
`referans_getiri.csv` (depoda, 1.504 gün) tek başına yayınlanan üç başlık
sayısını TAM olarak üretiyor:
    bileşik toplam  +%2.126,4
    yıllık (CAGR)   +%112,46   (yayınlanan +%112,5)
    günlük Sharpe     2,941    (yayınlanan 2,942)
    maks düşüş       −%14,54   (yayınlanan −%14,5)
Yani hiçbir yayınlanan sayı için motoru yeniden koşmak gerekmiyor.

Bunun operasyonel değeri var: madde 258 kontrol serisini
`/tmp/kontrol_E%d.pkl` dosyasına SABİTLEMİŞTİ, çünkü `/tmp/g19E_*.pkl`
her koşuda üzerine yazılıyordu (madde 252'de beni yanıltan hata). Bugün
baktım: **o sabitlenmiş dosyalar YOK.** `/tmp` silinmiş. Yani madde
258'in çözümü doğru teşhisti ama KALICI DEĞİLDİ — kalıcı kaynak depodaki
CSV'dir. Bu modül bu yüzden `/tmp`'ye hiç bakmaz.

BULGU 2 — HANGİSİ DOĞRU: +%41,4
-------------------------------
Yayınlanan DÜŞÜŞ çifti (−%16,8 / −%20,7, madde 222/231) hangi yöntemden
çıktıysa, getiri p5'i de o yöntemden okunmalı. Yöntemleri tek tek
yeniden koştum:
    blok  5, B=20.000 -> getiri p5 +%41,4 | düşüş p5 −%19,1 p1 −%23,9
    blok 21, B= 2.000 -> getiri p5 +%39,5 | düşüş p5 −%17,1 p1 −%21,1
    blok 21, B=20.000 -> getiri p5 +%41,4 | düşüş p5 −%16,7 p1 −%20,7  <<<
Yayınlanan düşüş çiftini üreten koşu **blok 21 / B=20.000** (madde
`arastirma_rejim.yil_bootstrap`'ın blok uzunluğu). O koşunun getiri p5'i
**+%41,4**. Yani doz tablosundaki sayı doğru; başlık tablosundaki +%41,5
ve rejim tablosundaki +%41,1 başka koşulardan kalmış.

Tarihsel araştırma tabloları DEĞİŞTİRİLMEDİ — onlar o günün ölçümünün
kaydı; yalnızca "bugünkü beklenti" tablosu tek kaynağa bağlandı.

BULGU 3 — ASIL BULGU: KUYRUĞUN BELİRSİZLİĞİ TOHUMDAN DEĞİL, BLOK
UZUNLUĞUNDAN GELİYOR — VE İKİ KUYRUK TERS YÖNE GİDİYOR
----------------------------------------------------------------
261 maddede blok uzunluğunun duyarlılığı hiç ölçülmemişti. Tohum
gürültüsü ±0,2-0,4 puan (5 tohum). Blok uzunluğu ise:

    blok   5 -> getiri p5 +%41,4 | düşüş p5 −%19,1  p1 −%23,9
    blok  10 -> getiri p5 +%41,4 | düşüş p5 −%17,5  p1 −%21,2
    blok  21 -> getiri p5 +%41,4 | düşüş p5 −%16,7  p1 −%20,7
    blok  30 -> getiri p5 +%41,8 | düşüş p5 −%16,7  p1 −%20,2
    blok  45 -> getiri p5 +%39,8 | düşüş p5 −%16,4  p1 −%20,1
    blok  60 -> getiri p5 +%37,1 | düşüş p5 −%16,1  p1 −%19,5
    blok  90 -> getiri p5 +%34,8 | düşüş p5 −%15,4  p1 −%18,3
    blok 120 -> getiri p5 +%31,7 | düşüş p5 −%14,7  p1 −%17,3

**Blok uzadıkça getiri kuyruğu KÖTÜLEŞİYOR (41,4 -> 31,7) ama düşüş
kuyruğu İYİLEŞİYOR (−19,1 -> −14,7).** Mekanizma: kısa blok sıralamayı
yok eder; yollar çeşitlenir (getiri kuyruğu iyi görünür) ama gerçek
serinin lehte KÜMELENMESİ de kaybolur (düşüş kötüleşir). Uzun blok
gerçek serinin kötü dönemlerini BÜTÜN olarak taşır (getiri kuyruğu
kötüleşir) ve aynı zamanda gerçek sıralamanın şansını korur (düşüş
iyimser görünür).

**Sonuç: HİÇBİR blok seçimi iki eksende birden ihtiyatlı değildir.**
Tek bir blok seçip "yayınlanan kuyruk budur" demek, ölçülmemiş bir
yöntem seçimini sayının içine gizlemektir. Dürüst hâli ÇAPRAZ ZARF:
    düşüş  : en kısa konvansiyondan   (blok  5) -> p5 −%19,1 / p1 −%23,9
    getiri : en uzun konvansiyondan   (blok 90) -> p5 +%34,8

BULGU 4 — MADDE 243 AYNEN ÜRETİLDİ, VE İKİ AYRI ÖLÇÜ OLDUĞU DOĞRULANDI
----------------------------------------------------------------------
Madde 243'ün iki sayısı farklı ufuklardan geliyor ve ikisi de tuttu:
  * 1 yıllık (365 gün) tam karıştırma: düşüş p5 −%20,6 / p1 −%25,6
    (yayınlanan −%20,6 / −%25,3; p1 farkı tohum gürültüsü)
  * TÜM ÖRNEK (1.504 gün) permütasyonu: ortalama −%18,10, ve
    gerçekleşen −%14,54 payların **%84,1**'inden daha iyi
    (yayınlanan %84). "Yayınlanan düşüş şanslı bir sıralama" iddiası
    AYAKTA.
Not: bu ikisi karıştırılmaya müsait. 365 günlük karıştırmada ortalama
düşüş −%13,0'dır ve gerçekleşen −%14,54 bu dağılımın kötü %30'undadır —
ama o KIYAS GEÇERSİZ, çünkü 4,1 yıllık bir yolun maksimum düşüşü bir
yıllık yolun maksimumuyla kıyaslanamaz (ufuk uzadıkça maksimum derinleşir;
madde 261'in tam olarak ölçtüğü şey). Şans iddiası AYNI UFUKTA kurulmuş,
bu yüzden geçerli.

KARARA ETKİSİ — EŞİK DEĞİŞMEDİ, AMA GEREKÇESİ ÜÇE ÇIKTI
-------------------------------------------------------
`canli_karar.py`'nin düşüş zarfı −%18 İNCELE / −%23 DURDUR diyor. Üç
bağımsız yöntemin bir yıllık p1'i: blok 21 −%20,7 · blok 5 −%23,9 ·
madde 243 sıralama −%25,6. DURDUR eşiği (−23) ikisinin arasında,
İNCELE eşiği (−18) üçünün de p5'inin (−16,7 / −19,1 / −20,6) içinde.
Yani eşikler **tek bir yönteme bağlı değil**; değiştirilmesi için bir
gerekçe çıkmadı. AYAR DEĞİŞMEDİ.

KANUN
-----
**"Bir sayıyı yayınlamak, onu üreten YÖNTEM SEÇİMİNİ de yayınlamaktır."**
Tohum gürültüsünü rapor edip blok uzunluğunu sessiz bırakmak, belirsizliğin
büyük parçasını saklamaktır: burada tohum ±0,4 puan, blok ±9,7 puandı.

KULLANIM
--------
    python arastirma_yayinlanan_sayilar.py            # tablo + doğrulama
    python arastirma_yayinlanan_sayilar.py --zarf     # çapraz zarf
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

KOK = os.path.dirname(os.path.abspath(__file__))
SERI_DOSYA = os.path.join(KOK, "referans_getiri.csv")

# --- ÖN KAYIT: yayınlanan kuyruk hangi yöntemle üretilir -------------------
# Madde 222/231'in yayınlanan düşüş çiftini üreten koşu budur. Değiştirmek
# yayınlanan sayıyı değiştirir; bu yüzden burada SABİT.
KANONIK_BLOK = 21
KANONIK_TEKRAR = 20000
KANONIK_TOHUM = 11
UFUK_GUN = 365

# Belgelerde yayınlanan "bugünkü beklenti" sayıları. dogrula() bunları
# referans_getiri.csv'den yeniden üretip karşılaştırır.
YAYINLANAN = {
    "yillik_getiri": 112.5,   # CAGR, %
    "sharpe_gunluk": 2.942,
    "maks_dusus": -14.5,      # %
    "yil_getiri_p5": 41.4,    # %  <-- madde 262'de tek kaynağa bağlandı
    "yil_dusus_p5": -16.8,    # %
    "yil_dusus_p1": -20.7,    # %
}

# Ölçülen blok duyarlılığı (tohum 11, B=20.000):
# blok -> (getiri p5, düşüş p5, düşüş p1)
BLOK_DUYARLILIK = {
    5:   (41.4, -19.1, -23.9),
    10:  (41.4, -17.5, -21.2),
    21:  (41.4, -16.7, -20.7),
    30:  (41.8, -16.7, -20.2),
    45:  (39.8, -16.4, -20.1),
    60:  (37.1, -16.1, -19.5),
    90:  (34.8, -15.4, -18.3),
    120: (31.7, -14.7, -17.3),
}

# Zarf kurulurken blok üst sınırı. 365 günlük ufukta blok 120 yalnızca
# 4 bağımsız çekiliş bırakır (120'nin üstünde 3) — bootstrap orada
# yozlaşır, tahmin kuyruğu değil örneklem azlığını ölçer. Bu yüzden zarf
# blok <= 90 (en az 5 çekiliş) ile kurulur; blok 120 tabloda kalır ama
# zarfa girmez.
ZARF_BLOK_UST = 90

# Çapraz zarf: her ekseni KENDİ en kötümser konvansiyonundan al.
CAPRAZ_ZARF = {
    "getiri_p5": (34.8, 90),    # (değer, hangi blok)
    "dusus_p5": (-19.1, 5),
    "dusus_p1": (-23.9, 5),
}

# Madde 243'ün iki ölçüsü (bu modülde aynen üretildi)
MADDE_243 = {
    "yil_dusus_p5": -20.6,
    "yil_dusus_p1": -25.6,     # yayınlanan −25,3; fark tohum gürültüsü
    "tum_ornek_ortalama": -18.10,
    "gerceklesen_yuzdelik": 84.1,
}

TOHUM_GURULTUSU_PUAN = 0.4     # 5 tohum, getiri p5
BLOK_GURULTUSU_PUAN = 9.7      # blok 5 -> 120, getiri p5


def seri() -> np.ndarray:
    """Depodaki kanonik günlük getiri serisi. /tmp'ye BAKMAZ."""
    with open(SERI_DOSYA) as f:
        return np.array([float(r["getiri"]) for r in csv.DictReader(f)])


def ozet(g: np.ndarray | None = None) -> dict:
    """Serinin kendi başlık sayıları (bootstrap yok)."""
    if g is None:
        g = seri()
    yil = len(g) / 365.25
    tam = float(np.prod(1.0 + g))
    e = np.cumprod(1.0 + g)
    return {
        "gun": len(g),
        "bilesik_toplam": (tam - 1.0) * 100.0,
        "yillik_getiri": (tam ** (1.0 / yil) - 1.0) * 100.0,
        "sharpe_gunluk": float(g.mean() / g.std(ddof=1) * np.sqrt(365)),
        "maks_dusus": float((e / np.maximum.accumulate(e) - 1.0).min()) * 100.0,
    }


def _yollar(g: np.ndarray, blok: int, tohum: int, tekrar: int, ufuk: int):
    rng = np.random.default_rng(tohum)
    nb = int(np.ceil(ufuk / blok))
    st = rng.integers(0, len(g) - blok + 1, size=(tekrar, nb))
    idx = (st[:, :, None] + np.arange(blok)[None, None, :]).reshape(tekrar, -1)[:, :ufuk]
    e = np.cumprod(1.0 + g[idx], axis=1)
    getiri = e[:, -1] - 1.0
    dusus = (e / np.maximum.accumulate(e, axis=1) - 1.0).min(axis=1)
    return getiri, dusus


def kuyruk(blok: int = KANONIK_BLOK, tohum: int = KANONIK_TOHUM,
           tekrar: int = KANONIK_TEKRAR, ufuk: int = UFUK_GUN,
           g: np.ndarray | None = None) -> dict:
    """Blok bootstrap ile bir yıllık getiri/düşüş kuyrukları (%)."""
    if g is None:
        g = seri()
    r, d = _yollar(g, blok, tohum, tekrar, ufuk)
    return {
        "getiri_p5": float(np.percentile(r, 5)) * 100.0,
        "getiri_ort": float(r.mean()) * 100.0,
        "dusus_p5": float(np.percentile(d, 5)) * 100.0,
        "dusus_p1": float(np.percentile(d, 1)) * 100.0,
        "dusus_ort": float(d.mean()) * 100.0,
    }


def siralama_testi(ufuk: int = UFUK_GUN, tekrar: int = 20000,
                   tohum: int = 243, g: np.ndarray | None = None) -> dict:
    """Madde 243: blok YOK, tam karıştırma. ufuk=None -> tüm örnek."""
    if g is None:
        g = seri()
    n = len(g)
    h = n if ufuk is None else ufuk
    rng = np.random.default_rng(tohum)
    idx = np.argsort(rng.random((tekrar, n)), axis=1)[:, :h]
    e = np.cumprod(1.0 + g[idx], axis=1)
    d = (e / np.maximum.accumulate(e, axis=1) - 1.0).min(axis=1)
    ger = float((np.cumprod(1.0 + g) /
                 np.maximum.accumulate(np.cumprod(1.0 + g)) - 1.0).min())
    return {
        "dusus_p5": float(np.percentile(d, 5)) * 100.0,
        "dusus_p1": float(np.percentile(d, 1)) * 100.0,
        "dusus_ort": float(d.mean()) * 100.0,
        "gerceklesen": ger * 100.0,
        "gerceklesenden_kotu_pay": float((d < ger).mean()) * 100.0,
    }


def dogrula(tolerans: float = 0.15) -> bool:
    """Yayınlanan başlık sayıları depodaki seriden yeniden üretilebiliyor mu?

    Serinin kendi ölçüleri (getiri/Sharpe/düşüş) KESİN; kuyruk sayıları
    bootstrap olduğu için tolerans puan cinsindendir.
    """
    o = ozet()
    if abs(o["yillik_getiri"] - YAYINLANAN["yillik_getiri"]) > 0.1:
        return False
    if abs(o["sharpe_gunluk"] - YAYINLANAN["sharpe_gunluk"]) > 0.01:
        return False
    if abs(o["maks_dusus"] - YAYINLANAN["maks_dusus"]) > 0.1:
        return False
    k = kuyruk()
    for ad, anahtar in (("yil_getiri_p5", "getiri_p5"),
                        ("yil_dusus_p5", "dusus_p5"),
                        ("yil_dusus_p1", "dusus_p1")):
        if abs(k[anahtar] - YAYINLANAN[ad]) > tolerans:
            return False
    return True


def blok_ters_yonlu_mu() -> bool:
    """İki kuyruk blok uzunluğuyla TERS yöne mi gidiyor? (Bulgu 3)"""
    bloklar = sorted(BLOK_DUYARLILIK)
    getiri = [BLOK_DUYARLILIK[b][0] for b in bloklar]
    dusus = [BLOK_DUYARLILIK[b][1] for b in bloklar]
    return getiri[-1] < getiri[0] and dusus[-1] > dusus[0]


def zarf_bloklari() -> list[int]:
    """Zarfa giren blok uzunlukları (yozlaşmayanlar)."""
    return [b for b in sorted(BLOK_DUYARLILIK) if b <= ZARF_BLOK_UST]


def tek_blok_ihtiyatli_mi() -> bool:
    """İki eksende birden en kötümser olan BİR blok var mı? (yok -> False)"""
    bloklar = zarf_bloklari()
    en_kotu_getiri = min(BLOK_DUYARLILIK[b][0] for b in bloklar)
    en_kotu_dusus = min(BLOK_DUYARLILIK[b][1] for b in bloklar)
    return any(BLOK_DUYARLILIK[b][0] == en_kotu_getiri
               and BLOK_DUYARLILIK[b][1] == en_kotu_dusus for b in bloklar)


def gurultu_kaynagi() -> str:
    """Yayınlanan kuyruğun belirsizliği hangi seçimden geliyor?"""
    return "BLOK" if BLOK_GURULTUSU_PUAN > TOHUM_GURULTUSU_PUAN else "TOHUM"


def yaz() -> None:
    o = ozet()
    print("MADDE 262 — YAYINLANAN SAYILARIN TEK KAYNAĞI")
    print("kaynak: referans_getiri.csv (%d gün, depoda, /tmp DEĞİL)\n" % o["gun"])
    print("  bileşik toplam  +%%%.1f" % o["bilesik_toplam"])
    print("  yıllık (CAGR)   +%%%.2f   (yayınlanan +%%%.1f)"
          % (o["yillik_getiri"], YAYINLANAN["yillik_getiri"]))
    print("  günlük Sharpe     %.3f   (yayınlanan %.3f)"
          % (o["sharpe_gunluk"], YAYINLANAN["sharpe_gunluk"]))
    print("  maks düşüş       %%%.2f   (yayınlanan %%%.1f)"
          % (o["maks_dusus"], YAYINLANAN["maks_dusus"]))
    k = kuyruk()
    print("\nkanonik kuyruk (blok %d, B=%d, tohum %d):"
          % (KANONIK_BLOK, KANONIK_TEKRAR, KANONIK_TOHUM))
    print("  1 yıl getiri p5  +%%%.1f   (yayınlanan +%%%.1f)"
          % (k["getiri_p5"], YAYINLANAN["yil_getiri_p5"]))
    print("  1 yıl düşüş p5   %%%.1f   p1 %%%.1f" % (k["dusus_p5"], k["dusus_p1"]))
    print("\nBLOK DUYARLILIĞI (asıl bulgu):")
    print("  blok | getiri p5 | düşüş p5 | düşüş p1")
    for b in sorted(BLOK_DUYARLILIK):
        gp, dp, d1 = BLOK_DUYARLILIK[b]
        print("  %4d |    +%%%4.1f |   %%%5.1f |   %%%5.1f" % (b, gp, dp, d1))
    print("  -> iki kuyruk TERS yöne gidiyor: %s" % blok_ters_yonlu_mu())
    print("  -> iki eksende birden ihtiyatlı tek blok: %s" % tek_blok_ihtiyatli_mi())
    print("  -> belirsizliğin kaynağı: %s (tohum ±%.1f puan, blok ±%.1f puan)"
          % (gurultu_kaynagi(), TOHUM_GURULTUSU_PUAN, BLOK_GURULTUSU_PUAN))
    print("\nÇAPRAZ ZARF (her eksen kendi en kötümser konvansiyonundan):")
    print("  1 yıl getiri p5  +%%%.1f  (blok %d)" % CAPRAZ_ZARF["getiri_p5"])
    print("  1 yıl düşüş  p5   %%%.1f  (blok %d)" % CAPRAZ_ZARF["dusus_p5"])
    print("  1 yıl düşüş  p1   %%%.1f  (blok %d)" % CAPRAZ_ZARF["dusus_p1"])
    print("\nMADDE 243 (sıralama testi) — aynen üretildi:")
    print("  1 yıl  : düşüş p5 %%%.1f  p1 %%%.1f"
          % (MADDE_243["yil_dusus_p5"], MADDE_243["yil_dusus_p1"]))
    print("  tüm örnek: ortalama %%%.2f, gerçekleşen payların %%%.1f'inden iyi"
          % (MADDE_243["tum_ornek_ortalama"], MADDE_243["gerceklesen_yuzdelik"]))
    print("\nDOĞRULAMA: %s" % ("EVET" if dogrula() else "HAYIR"))
    print("\nKANUN: bir sayıyı yayınlamak, onu üreten YÖNTEM SEÇİMİNİ de")
    print("yayınlamaktır. AYAR DEĞİŞMEDİ.")


if __name__ == "__main__":
    if "--zarf" in sys.argv:
        for ad, (deger, blok) in CAPRAZ_ZARF.items():
            print("%-12s %+7.1f  (blok %d)" % (ad, deger, blok))
    else:
        yaz()
