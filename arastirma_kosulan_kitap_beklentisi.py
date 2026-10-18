#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 331 — **YAYINLANAN "BUGÜNKÜ BEKLENTİ" +%168,8 DEĞİL ≈+%159,5:
TEK VE ŞANSLI BİR BAŞLANGIÇ HİZASININ SAYISIYDI.**

*** BU DOSYA 2026-10-19'DA TRANSKRİPTTEN YENİDEN YAZILDI (madde 335).
Özgün hâli konteyner kaybında gitti. ***

*** VE MADDE 332 BU MADDENİN BAŞLIK DÜZELTMESİNİ ÇÜRÜTTÜ. *** Aşağıdaki
"medyan +159,48" hükmü YANLIŞTIR: ölçtüğüm üç hizanın İKİSİ aynı parite
sınıfıydı. Doğru hâli madde 332'de: iki sınıf (≈+159,4 / ≈+174,4),
hizaya göre beklenen ≈+166,9. Bu dosya o turun kaydı olarak duruyor,
hükmü madde 332 tarafından DÜZELTİLMİŞTİR.

Madde 330'un A ekseni kapatıldı: `CANLIYA_CIKIS.md`'nin beklenti
tablosu koşan kitap için kanonik yöntemle **birebir** yeniden üretildi
ve üretirken üç şey çıktı.

═══ 1. RAY PARİTESİ — DOZ METRİĞİ ═══

Madde 287'nin ölçüm kodu yayınlanan **tek kaynaktan** koşuldu:

    seri                      CAGR      Sh    dusus     doz       net
    referans_getiri.csv     +112,46  2,943   14,54   1,507x   **+201,69**
    KAYITLI (madde 320)     +112,27     -    14,54   1,505x   **+200,85**

⇒ **0,84 puan** — yöntem ve ray doğrulandı. Aynı kodu koşan kitabın
serisine uygulayınca **+159,48** çıktı, kayıtlı **+168,83** değil. Ray
doğrulanmış olduğu için fark **yöntemde değil SERİDE**.

═══ 2. BAŞLIK (madde 332'de DÜZELTİLDİ) ═══

    ofset    CAGR      Sh     dusus      doz        net
      0    +117,60   2,686    19,07    1,250x    +159,48
      1    +121,65   2,766    20,92    1,293x    **+174,00**
      2    +117,50   2,684    19,07    1,249x    +159,23
    yayilim                                       **14,78 puan**

O turda "medyan +159,48" dedim. **Madde 332: ofset 0 ve 2 AYNI parite
sınıfı** (15 fazın 14'ü ortak), yani medyan hiza medyanı değildi.
Doğrusu: iki sınıf eşit olasılıklıysa **beklenen ≈+166,9** ve yayınlanan
+168,83 bunun **1,9 puan** üstünde.

**DEĞİŞMEYEN KISIM:** hiza yayılımı (14,78) kabul edilmiş tek
iyileştirmeden (madde 288, +8,24) **büyüktür** ve hiza **seçilebilir
bir şey değildir** — botun başlama anı belirler.

═══ 3. YAYINLANAN TABLO, KOŞAN KİTAP İÇİN (kanonik yöntem birebir) ═══

Yöntem `arastirma_yayinlanan_sayilar.py` ile aynı: blok 21, B=20.000,
tohum 11, ufuk 365; madde 243 sıralama testi tohum 243, B=20.000.

    olcu                              15x5 TAM    **15x4 D8 (kosan)**
    yillik getiri (gunluk seri)       +112,46%    **+117,60%**
    Sharpe (gunluk, tek kaynak)         2,943     **2,686**
    Sharpe (motor, bar) - AYRI sozlesme  3,10      2,87
    maks dusus                          −14,54    **−19,07**
    1y getiri p5 (blok 21)              +41,4%    **+36,4%**
    1y dusus p5 / p1 (blok 21)      −16,7/−20,7   **−20,7/−25,4**
    1y dusus p5 / p1 (madde 243)    −20,6/−25,6   **−24,5/−30,1**
    dozda yillik net                   +201,69    +159,48 (CIFT hiza)

Blok duyarlılığı (koşan kitap) — madde 262'nin "kuyruğun belirsizliği
blok uzunluğundan gelir" bulgusu **aynı yönde** tekrar ediyor:

    blok   getiri p5   dusus p5   dusus p1
      5      +35,9      −23,3      −28,8
     10      +35,8      −21,6      −26,3
     21      +36,4      −20,7      −25,4
     30      +36,7      −20,5      −25,0
     45      +34,6      −20,5      −25,2
     60      +32,5      −20,8      −25,3
     90      +30,1      −20,0      −23,8
    120      +27,6      −19,3      −22,8

Çapraz zarf (her eksen kendi en kötümser bloğundan, blok ≤ 90):
**getiri p5 +%30,1** (blok 90) · **düşüş p5 −%23,3 / p1 −%28,8**
(blok 5).

**SHARPE SÖZLEŞMESİ:** tablodaki **3,12**, madde 222'nin **motor (bar
seviyesi, 2 faz)** Sharpe'ı; aynı tablonun tek kaynağının **günlük**
Sharpe'ı **2,942** ve diğer bütün satırlar günlük seriden ⇒ tablo **tek
kaynaklı değildi.** Belgede ikisi de **etiketle** yazıldı.

**BELGEDEKİ BAYAT EŞİK:** "devre kesici eşikleri madde 302/303'te
türetildi (**−%23/−%29**)" satırı **13x3**'ün çiftiydi; koşan kitabın
çifti madde 329'da **−%23/−%30** → düzeltildi.

═══ 4. MADDE 329'UN EŞİK ÇİFTİ ÜÇ YÖNTEMİN ARASINDA MI? ═══

    yontem                         1y dusus p1
    blok 21 bootstrap                 −25,4
    blok 5 bootstrap                  −28,8
    rejim ayrimi (madde 329)          −29,2
    madde 243 siralama                −30,1
    ---
    YURURLUKTEKI DURDUR               **−30**     <- en kotumser ucta
    YURURLUKTEKI INCELE               **−23**     <- [−20,7 … −24,5] icinde

İNCELE **ortada**; DURDUR ise en kötümser iki yöntemin **tam üstünde**.
15x5'te yayınlanan −23 üç yöntemin **arasında** kalıyordu; koşan kitapta
−30 **uçta**: çift ayakta ama **tavanda.**

═══ 5. AÇIK EKSEN (dürüst) ═══

Madde 330'un **B** ve **C** eksenleri bu maddede de ölçülmedi. Yeni
tablo **2.000 $ / D8**'e aittir. Üç hiza ölçüldü, 15'in hepsi değil —
ve madde 332 bu üçün ikisinin aynı sınıf olduğunu gösterdi.

AYAR DEĞİŞMEDİ: bu madde bir **beklenti düzeltmesi**.
"""

from __future__ import annotations

YENIDEN_YAZILDI = True
MADDE332_DUZELTTI = True
DUZELTME_NOTU = ("bu maddenin 'medyan +159,48, yayinlanan 9,35 puan "
                 "iyimser' hukmu YANLIS; madde 332 olctugum uc hizanin "
                 "IKISININ ayni parite sinifi oldugunu gosterdi. Dogru "
                 "hali: iki sinif (~+159,4 / ~+174,4), hizaya gore "
                 "BEKLENEN ~+166,9, yayinlanan +168,83 bunun 1,9 puan "
                 "ustunde.")

# ─────────────────── 1. RAY PARİTESİ (doz metriği)
DOZ_PARITE = {
    "referans_getiri.csv (uretilen)": (112.46, 14.54, 1.507, 201.69),
    "madde 320 KAYITLI":              (112.27, 14.54, 1.505, 200.85),
}
PARITE_FARKI_PUAN = 201.69 - 200.85      # 0.84
RAY_DOGRULANDI = True

# ─────────────────── 2. HİZA
HIZA = {   # ofset -> (CAGR, Sharpe gunluk, dusus, doz, net)
    0: (117.60, 2.686, 19.07, 1.250, 159.48),
    1: (121.65, 2.766, 20.92, 1.293, 174.00),
    2: (117.50, 2.684, 19.07, 1.249, 159.23),
}
NET_YAYILIM = 174.00 - 159.23            # 14.78
KAYITLI_NET = 168.83
BASLIK_O_TURDA = 159.48                  # YANLIS - madde 332 duzeltti
BASLIK_DOGRU = 166.9                     # madde 332
MADDE288_KAZANCI = 8.24

# ─────────────────── 3. YAYINLANAN TABLO
YONTEM = ("arastirma_yayinlanan_sayilar.py ile ayni: blok 21, B=20.000, "
          "tohum 11, ufuk 365; madde 243 siralama tohum 243, B=20.000")
TABLO = {   # olcu -> (15x5 TAM, 15x4 D8)
    "yillik_getiri":        (112.46, 117.60),
    "sharpe_gunluk":        (2.943, 2.686),
    "sharpe_motor_bar":     (3.10, 2.87),
    "maks_dusus":           (-14.54, -19.07),
    "yil_getiri_p5":        (41.4, 36.4),
    "yil_dusus_p5":         (-16.7, -20.7),
    "yil_dusus_p1":         (-20.7, -25.4),
    "m243_dusus_p5":        (-20.6, -24.5),
    "m243_dusus_p1":        (-25.6, -30.1),
    "doz_net":              (201.69, 159.48),
}
BLOK_DUYARLILIK_15X4 = {
    5: (35.9, -23.3, -28.8), 10: (35.8, -21.6, -26.3),
    21: (36.4, -20.7, -25.4), 30: (36.7, -20.5, -25.0),
    45: (34.6, -20.5, -25.2), 60: (32.5, -20.8, -25.3),
    90: (30.1, -20.0, -23.8), 120: (27.6, -19.3, -22.8),
}
CAPRAZ_ZARF_15X4 = {"getiri_p5": (30.1, 90), "dusus_p5": (-23.3, 5),
                    "dusus_p1": (-28.8, 5)}
ZARF_BLOK_UST = 90
SHARPE_BELGEDE = 3.12
SHARPE_TEK_KAYNAK = 2.942
SHARPE_MOTOR_BAR = 3.102
SHARPE_SOZLESMESI = ("tablodaki 3,12 madde 222'nin MOTOR (bar seviyesi, "
                     "2 faz) Sharpe'i; tek kaynagin GUNLUK Sharpe'i "
                     "2,942 ve diger butun satirlar gunluk seriden")

# ─────────────────── 4. EŞİK ÇAPRAZ KONTROLÜ
ESIK_YONTEMLERI = {
    "blok 21 bootstrap": -25.4,
    "blok 5 bootstrap": -28.8,
    "rejim ayrimi (madde 329)": -29.2,
    "madde 243 siralama": -30.1,
}
YURURLUKTEKI = {"INCELE": -23.0, "DURDUR": -30.0}
INCELE_ARALIGI = (-24.5, -20.7)

# ─────────────────── 5. BELGE DÜZELTMELERİ
BELGE_BAYAT_ESIK = {"eskiydi": (-23, -29), "dogrusu": (-23, -30),
                    "neden": "(-23/-29) 13x3'un cifti; kosan kitap 15x4"}
ACIK_EKSENLER = ("madde 330'un B (L2/L3 TP oranlari) ve C (DUSUS_ZARFI) "
                 "eksenleri bu maddede de OLCULMEDI; tablo 2.000 $/D8'e "
                 "aittir; UC hiza olculdu ve madde 332 bunun IKISININ "
                 "ayni sinif oldugunu gosterdi")
AYAR_DEGISTI = False

YASA1 = ("Tek bir baslangic hizasinin neti, O KITABIN neti degildir.")
YASA2 = ("Bir hiza yayilimi, kabul edilmis bir iyilestirmeden buyukse "
         "(14,78 > madde 288'in 8,24'u) o bir GURULTU degil, "
         "raporlanmasi gereken BELIRSIZLIKTIR.")
YASA3 = ("Bir tabloda tek bir satir baska sozlesmeden geliyorsa tablo "
         "tek kaynakli DEGILDIR.")
YASA4 = ("Bir esik ciftinin uc yontemin ARASINDA mi UCUNDA mi durdugu "
         "yazilir.")


# ─────────────────── DOĞRULAMA
def doz_rayi_parite_gecti_mi():
    return RAY_DOGRULANDI and abs(PARITE_FARKI_PUAN) < 1.0


def kayitli_net_hiza_araliginda_mi():
    n = [v[4] for v in HIZA.values()]
    return min(n) <= KAYITLI_NET <= max(n)


def baslik_madde332de_duzeltildi_mi():
    return MADDE332_DUZELTTI and "YANLIS" in DUZELTME_NOTU


def yayilim_madde288den_buyuk_mu():
    return NET_YAYILIM > MADDE288_KAZANCI


def kosan_kitap_daha_derin_mi_dusuyor():
    return TABLO["maks_dusus"][1] < TABLO["maks_dusus"][0]


def kosan_kitap_getiri_kuyrugu_daha_mi_kotu():
    return TABLO["yil_getiri_p5"][1] < TABLO["yil_getiri_p5"][0]


def blok_ters_yonlu_mu():
    b = sorted(BLOK_DUYARLILIK_15X4)
    g = [BLOK_DUYARLILIK_15X4[x][0] for x in b]
    d = [BLOK_DUYARLILIK_15X4[x][1] for x in b]
    return g[-1] < g[0] and d[-1] > d[0]


def sharpe_sozlesmesi_karisik_miydi():
    return (abs(SHARPE_BELGEDE - SHARPE_TEK_KAYNAK) > 0.1
            and abs(SHARPE_BELGEDE - SHARPE_MOTOR_BAR) < 0.05)


def durdur_ucta_mi():
    return YURURLUKTEKI["DURDUR"] <= min(ESIK_YONTEMLERI.values()) + 0.2


def incele_arada_mi():
    return INCELE_ARALIGI[0] < YURURLUKTEKI["INCELE"] < INCELE_ARALIGI[1]


def hukum():
    return {
        "doz_rayi": "PARITE GECTI (0,84 puan)",
        "kayitli_baslik": "+168,83 (tek hiza)",
        "o_turda_dedigim": "+159,48 medyan - YANLIS",
        "madde_332_dogrusu": "~+166,9 (iki sinif, esit olasilikli)",
        "hiza_yayilimi": "14,78 puan (madde 288'in 8,24'unden BUYUK)",
        "esik_cifti": "INCELE arada, DURDUR en kotumser ucta",
        "sharpe_satiri": "motor/bar sozlesmesi (3,12), tek kaynak 2,942",
        "ayar_degisti_mi": False,
    }


def yaz():
    print(__doc__)
    print("HIZA TABLOSU")
    for k, v in HIZA.items():
        print("  ofset %d  CAGR %+7.2f  Sh %.3f  dusus %5.2f  doz %.3fx  net %+7.2f"
              % (k, *v))
    print("\nHUKUM")
    for k, v in hukum().items():
        print("  %-20s %s" % (k, v))


if __name__ == "__main__":
    yaz()
