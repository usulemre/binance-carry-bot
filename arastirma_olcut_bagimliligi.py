#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 274 — REZERVİN ÜSTÜNLÜĞÜ ÖLÇÜTE BAĞLIYDI: 272 ve 273'ün iyimserliği
geri alınıyor.

Madde 272 rezerv 0,40'ı (+2,04 puan), madde 273 rezerv 0,60'ı (+5,80 puan)
"projenin en iyi ölçülmüş kazancı" olarak kaydetmişti. İkisi de eşit riski
**MAKSİMUM DÜŞÜŞ** ile tanımlıyordu. Ama maksimum düşüş TEK BİR uç nokta ve
madde 243 gerçekleşen yolun **şanslı** olduğunu (%84'lük yüzdelik) ölçmüştü.
Bu madde aynı kıyası dört ayrı risk ölçütüyle yaptı.

BULGU 1 — ÜSTÜNLÜK ÖLÇÜTE GÖRE DEĞİŞİYOR, HATTA İŞARET DEĞİŞTİRİYOR
-------------------------------------------------------------------
Net puan (eşit-risk getirisi − icra bedeli, kontrole göre):

    risk ölçütü         rezerv 0,50  rezerv 0,60  rezerv 0,70
    maks düşüş             +3,31       **+5,80**     +10,03
    **oynaklık**           **−0,55**   **−1,11**     **−2,51**
    ortalama düşüş         +0,72        +1,22         +1,93
    bootstrap p95 düşüş    +2,95        +4,38         +5,53

Hedefler: maks düşüş 14,54 · oynaklık 26,84 · ort düşüş 2,30 · boot p95 16,23.

Okuma: **nakit, kitabı OYNAKLIK başına iyileştirmiyor (eksi); KUYRUK
başına iyileştiriyor.** Sıralama mekanizmayı söylüyor — rezerv uç
episodu yastıklıyor, ortalama günü değil. Günlük Sharpe'ın hafifçe
gerilemesi (madde 272/273) bunun aynı ifadesi.

BULGU 2 — ASIL ÖLÇÜM: PROJENİN KENDİ DOZ ÖLÇÜTÜYLE KAZANÇ ~+1 PUAN
------------------------------------------------------------------
Doz kararının ön kayıtlı ölçütü madde 243/261'in **karıştırma** testidir
(gerçekleşen sıralama şanslı olduğu için sıralama TAMAMEN rastgeleleşir).
Aynı tolerans karşılığında net yıllık getiri (icra düşülmüş, B=8.000):

    1 yıl p95     KONTROL (rez 0,20)      REZERV 0,60          fark
    tolerans      brüt    net getiri      brüt    net getiri   puan
      −%15        0,702x    +%70,5        1,267x    +%70,9     +0,4
      −%20        0,955x   +%104,9        1,720x   +%105,5     +0,6
      −%25        1,219x   +%147,3        2,198x   +%148,4     +1,1
      −%30        1,495x   +%199,2        2,695x   +%201,1     +1,8
      −%35        1,786x   +%263,9        3,218x   +%266,5     +2,6
      −%40        2,095x   +%345,3        3,767x   +%347,8     +2,5

**Madde 273'ün +5,80 puanı, projenin kendi doz ölçütünde +1,1 puana
iniyor.** Fark yöntemde: 273 blok bootstrap'ın p95'ini eşitliyordu (blok
seri korelasyonunu KORUR), 274 karıştırmayı kullanıyor (korelasyonu
YOK EDER). Rezervin kazancının büyük kısmı **kümelenmiş** kötü dönemleri
yastıklamaktan geliyor ve doz ölçütü kasten kümelenme varsaymıyor.

BULGU 3 — VE TERSİ: REZERV DUVARI DAHA ERKEN TÜKETİYOR
------------------------------------------------------
Rezerv kuyruğu sıkıştırdığı için AYNI toleransı almak çok daha fazla
kaldıraç ister: −%30 toleransta kontrol 1,495x, rezerv 0,60 **2,695x**.
Madde 266/273'ün likidasyon duvarı **2,358x**:

    tolerans   rezerv 0,60 brüt   duvar (2,358x)
     −%25         2,198x          içinde
     −%30         2,695x          **AŞIYOR**
     −%35         3,218x          AŞIYOR
     −%40         3,767x          AŞIYOR

Kontrol −%40 toleransta bile 2,095x ile duvarın içinde. **Yani kontrol,
tolerans uzayının DAHA GENİŞ bir kısmında uygulanabilir.** Rezerv yolu
yalnız kazanmıyor değil, erişilebilir tolerans aralığını DARALTIYOR.

BULGU 4 — GERÇEK VE KULLANILABİLİR OLAN ŞEY: SAKİN SÜRÜŞ
--------------------------------------------------------
Rezerv 0,60, 1,00x'te p95 bir yıllık düşüşü **%20,9'dan %12,0'ye**
indiriyor (getiri +%112,5 → +%53,9). Bu bir kazanç değil bir TAKAS ve
madde 225'in söylediği şeyin aynısı: *"düşük riskli kitap isteniyorsa
rezervi büyütmek brütü kısmaktan iyidir."* Kaldıraçla geri almaya
çalışmak kazancı yok ediyor; kaldıraçsız bırakmak gerçek bir seçenek.

HÜKÜM
-----
**Rezerv 0,20 KALIYOR.** Madde 272 ve 273'ün "+2,04 / +5,80 puan"
kayıtları **ölçüt bağımlıydı** ve projenin kendi doz ölçütünde ~+1 puana
iniyor; üstüne rezerv yolu likidasyon duvarını daha erken tüketiyor.
Madde 273'ün "en iyi ölçülmüş kazanç" ifadesi bu madde ile DÜZELTİLDİ.

DERS
----
**Bir üstünlüğü kabul etmeden önce RİSK ÖLÇÜTÜNÜ değiştir.** Aynı aday
dört ölçütte +10,03 ile −2,51 arasında salınıyor. Ve kullanılacak ölçüt
keyfî değil: kararın ölçütü neyse (burada doz kararı -> madde 243'ün
karıştırma p95'i) kıyas onunla yapılmalı.
"""
from __future__ import annotations

OLCUT_CEPHESI = {   # olcut -> {rezerv: net_puan}
    "maks dusus": {0.50: 3.31, 0.60: 5.80, 0.70: 10.03},
    "oynaklik": {0.50: -0.55, 0.60: -1.11, 0.70: -2.51},
    "ort dusus": {0.50: 0.72, 0.60: 1.22, 0.70: 1.93},
    "boot p95 dusus": {0.50: 2.95, 0.60: 4.38, 0.70: 5.53},
}
HEDEFLER = {"maks dusus": 14.54, "oynaklik": 26.84,
            "ort dusus": 2.30, "boot p95 dusus": 16.23}

# tolerans -> (kontrol_brut, kontrol_net, rez60_brut, rez60_net)
DOZ = {
    15: (0.702, 70.5, 1.267, 70.9),
    20: (0.955, 104.9, 1.720, 105.5),
    25: (1.219, 147.3, 2.198, 148.4),
    30: (1.495, 199.2, 2.695, 201.1),
    35: (1.786, 263.9, 3.218, 266.5),
    40: (2.095, 345.3, 3.767, 347.8),
}
DUVAR = 2.358                 # madde 266/273, mmr %1
P95_1X = {"kontrol": 20.9, "rezerv60": 12.0}
GETIRI_1X = {"kontrol": 112.5, "rezerv60": 53.9}

MADDE_272_IDDIA = 2.04
MADDE_273_IDDIA = 5.80
DOZ_OLCUTUNDE_KAZANC = 1.1    # tolerans −%25'te


def isaret_degistiriyor_mu() -> bool:
    """Ayni aday farkli olcutlerde isaret degistiriyor mu?"""
    v = [OLCUT_CEPHESI[o][0.60] for o in OLCUT_CEPHESI]
    return max(v) > 0 > min(v)


def oynaklikta_negatif_mi() -> bool:
    return all(v < 0 for v in OLCUT_CEPHESI["oynaklik"].values())


def doz_olcutunde_kuculuyor_mu() -> bool:
    """Madde 273'un iddiasi doz olcutunde kuculuyor mu?"""
    return DOZ_OLCUTUNDE_KAZANC < MADDE_273_IDDIA / 2


def duvari_hangi_toleransta_asiyor(hangi: str = "rezerv60") -> int | None:
    for t in sorted(DOZ):
        brut = DOZ[t][2] if hangi == "rezerv60" else DOZ[t][0]
        if brut > DUVAR:
            return t
    return None


def kontrol_daha_genis_mi() -> bool:
    """Kontrol, tolerans uzayinin daha genis kisminda uygulanabilir mi?"""
    a = duvari_hangi_toleransta_asiyor("kontrol")
    b = duvari_hangi_toleransta_asiyor("rezerv60")
    return b is not None and (a is None or a > b)


def sakin_surus_takasi() -> dict:
    return {"p95_dusus": (P95_1X["kontrol"], P95_1X["rezerv60"]),
            "getiri": (GETIRI_1X["kontrol"], GETIRI_1X["rezerv60"])}


def hukum() -> str:
    return ("Rezerv 0,20 KALIYOR. Madde 272/273'un +%.2f/+%.2f puan kayitlari "
            "OLCUT BAGIMLIYDI; projenin kendi doz olcutunde (madde 243 "
            "karistirma p95) kazanc +%.1f puana iniyor ve rezerv yolu "
            "likidasyon duvarini tolerans −%%%d'te asiyor (kontrol −%%40'ta "
            "bile icinde). Madde 273'un 'en iyi olculmus kazanc' ifadesi "
            "DUZELTILDI."
            % (MADDE_272_IDDIA, MADDE_273_IDDIA, DOZ_OLCUTUNDE_KAZANC,
               duvari_hangi_toleransta_asiyor("rezerv60")))


def yaz() -> None:
    print("MADDE 274 — REZERVİN ÜSTÜNLÜĞÜ ÖLÇÜTE BAĞLIYDI\n")
    print("NET PUAN, risk ölçütüne göre (kontrole karşı):")
    print("  ölçüt              | 0,50   | 0,60   | 0,70   | hedef")
    for o, d in OLCUT_CEPHESI.items():
        print("  %-18s | %+6.2f | %+6.2f | %+6.2f | %.2f"
              % (o, d[0.50], d[0.60], d[0.70], HEDEFLER[o]))
    print("  -> işaret değiştiriyor mu: %s | oynaklıkta negatif mi: %s"
          % (isaret_degistiriyor_mu(), oynaklikta_negatif_mi()))
    print("\nDOZ ÇETVELİ (madde 243'ün karıştırma p95'i, icra düşülmüş):")
    print("  tolerans | kontrol brüt/net   | rezerv0,60 brüt/net | fark | duvar")
    for t in sorted(DOZ):
        ka, na, kr, nr = DOZ[t]
        print("   −%%%2d    | %5.3fx  %+8.1f   | %5.3fx  %+8.1f    | %+4.1f | %s"
              % (t, ka, na, kr, nr, nr - na,
                 "AŞIYOR" if kr > DUVAR else "içinde"))
    print("\n  madde 273'ün iddiası +%.2f -> doz ölçütünde +%.1f (küçülüyor: %s)"
          % (MADDE_273_IDDIA, DOZ_OLCUTUNDE_KAZANC, doz_olcutunde_kuculuyor_mu()))
    print("  rezerv0,60 duvarı −%%%s toleransta aşıyor; kontrol: %s"
          % (duvari_hangi_toleransta_asiyor("rezerv60"),
             duvari_hangi_toleransta_asiyor("kontrol") or "bu aralıkta aşmıyor"))
    print("  kontrol daha geniş tolerans aralığında uygulanabilir mi: %s"
          % kontrol_daha_genis_mi())
    t = sakin_surus_takasi()
    print("\nGERÇEK SEÇENEK (kaldıraçsız): rezerv 0,60 p95 düşüşü %%%.1f -> %%%.1f,"
          " getiri +%%%.1f -> +%%%.1f"
          % (t["p95_dusus"][0], t["p95_dusus"][1], t["getiri"][0], t["getiri"][1]))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
