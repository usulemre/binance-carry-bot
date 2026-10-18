"""MADDE 241: "+%40 yukselene SHORT, -%40 dusene LONG" kolu - RED, her payda.

Kullanici bu fikri madde 197'de de sormustu (orada +%50 pump, 03:00
Istanbul). Orada OLCULUP RAFA KALDIRILMISTI. Madde 241 uc sey ekliyor:
(1) olayin KENDISINI kitap kurmadan olcuyor, (2) olcegi buyutulebilir
versiyonu (siralama bazli geri donus) olcuyor - madde 237'nin EKSIK
BIRAKTIGI satir, (3) kol ekleme kararini KAPALI FORMA baglayip sonra
o formun SINIRINI buluyor.

================================================================
1) OLAYIN KENDISI (kitap yok, ham islem dagilimi, uygun evren)
================================================================
+%40 gunluk hareket sonrasi, 3 gun:

  olay            N     ort %   medyan   kazanan   p1        en kotu
  pump -> SHORT  3999   +4,06   +12,07    %68,6   -145,7     -743
  dump -> LONG    752   +2,81   -10,33    %35,2    -81,7     -100

GOZLEM DOGRULANIYOR: pump'i short'lamak %68,6 kazaniyor ve MEDYANI
+%12,07. Ama ORTALAMA +%4,06 - fark kuyrukta: p1 = -%145,7, en kotu tek
islem **-%743**. Kazananlar kucuk, kaybedenler sinirsiz.

Bu, projenin kendi yasasinin TERS YUZU: kitabin LONG bacagi yillik
-108,5 puan fiyat kanamasi odeyip +141,6 puanlik SIKISMA OPSIYONUNU
satin aliyor (madde 191). Pump'i short'lamak **o opsiyonu SATMAK**tir -
primi toplar, kuyrugu yer.

DUMP -> LONG tarafi bu evrende NEGATIF (medyan -%10,33, kazanan %35,2)
ve ARZI YOK: gunlerin %87'sinde hic -%40 dump olmuyor (gunde 0,17
sembol; filtresiz evrende 0,33).

================================================================
2) SAAT: 03:00 POZITIF AMA ZAYIF KANAT (madde 197 bagimsiz dogrulandi)
================================================================
Pozisyon basina sabit %20, funding>0, 3 gun tutma:

  saat (UTC)          Istanbul   yillik   Sharpe   22-24   25-26   dusus
  04                   07:00     +%31,7   0,747   -0,565   1,475   -75,5
  ASYA (00/04/20)        -        +%6,3   0,607   -0,819   1,390   -91,7
  00                   03:00      +%3,6   0,482   -0,726   1,061   -81,3

Madde 197 de ayni siralamayi bulmustu (00 UTC Sharpe 0,25 vs 04 UTC
0,49). Iki bagimsiz olcum: **saat etkisi var ama 03:00 en iyisi degil.**

VE DAHA ONEMLISI: her varyant 2022-24'te NEGATIF, yalnizca 2025-26'da
pozitif. Madde 197 "iki donemde de pozitif" sonucuna ancak SONRADAN
secilmis bir funding filtresiyle ulasmis ve bunu kendisi kayda
gecmisti; bu yeniden kurulumda o sonuc TEKRARLAMIYOR.

================================================================
3) SERMAYE PAYI: HER PAYDA RED
================================================================
Kol = "+40% 3g, 04 UTC" (en iyi varyant), kontrol = tam kitap:

  pay    getiri   Sharpe   22-24   25-26   dusus   esit-risk  karar
  %0    +%112,5   2,942   2,794   3,147   -14,5    +%112,5   KONTROL
  %5    +%111,0   3,014   2,744   3,373   -14,6    +%110,5   RED
  %10   +%109,1   3,011   2,674   3,450   -16,7     +%89,3   RED
  %20   +%104,4   2,779   2,459   3,226   -21,1     +%62,4   RED

Olceklenebilir versiyon (siralama bazli GERI DONUS kitabi; madde 237'nin
eksik satiri) daha da net - her payda TEK YONLU kotu:

  pay    getiri   Sharpe   dusus   esit-risk      korelasyon
  %0    +%112,5   2,942   -14,5    +%112,5        (carry)
  %5    +%107,8   2,931   -14,3    +%110,0        +0,471
  %10   +%103,3   2,915   -14,1    +%107,4
  %25    +%89,9   2,818   -15,0     +%86,2
  %100   +%32,1   1,228   -24,4     +%18,0

================================================================
4) KAPALI FORM: KOL ELEME ESITSIZLIGI - VE SINIRI
================================================================
Bir kol ancak su kosulda portfoy SHARPE'ini yukseltir:

        Sh_kol  >  Sh_ana  x  korelasyon

Dort bagimsiz olcumde isaret DOGRU:

  kol                 Sh_kol    kor   gereken   gozlenen Sharpe etkisi
  pump modulu (197)    0,69   +0,043   0,127    YUKSELDI (2,942 -> 3,014)
  olay kolu (241)      0,747  +0,019   0,056    YUKSELDI
  momentum (237)       1,935  +0,718   2,112    DUSTU
  geri donus (241)     1,228  +0,471   1,387    DUSTU

AMA ESITSIZLIGIN SINIRI DA BURADA BULUNDU: **Sharpe'in yukselmesi karin
yukselmesi DEGILDIR.** Korelasyonu sifira yakin ama KUYRUKLU bir kol,
Sharpe'i yukseltirken maksimum DUSUSU derinlestiriyor (-14,5 -> -16,7
-> -21,1) ve projenin kar olcutu olan esit-risk getirisi COKUYOR
(+%112,5 -> +%89,3 -> +%62,4). Sharpe ortalama/oynaklik, dusus ise
YOLA bagli - madde 212'nin kuralda buldugu deligin aynisi, ilk kez bir
PARAMETRE degil bir KOL icin.

Pratik kural: esitsizlik bir ELEME aracidir (gecmezse kosmaya gerek
yok), bir KABUL gerekcesi DEGIL. Gecen bir kol icin ikinci soru:
**kuyrugu dususu ne kadar derinlestiriyor?**

Kosum: python3 arastirma_olay_kolu.py
"""

OLAY = {   # (N, ort %, medyan %, kazanan %, p1 %, en kotu %)
    "pump -> SHORT": (3999, 4.06, 12.07, 68.6, -145.7, -743.0),
    "dump -> LONG": (752, 2.81, -10.33, 35.2, -81.7, -100.0),
}

ARZ = {   # esik: (gunde pump, gunde dump, dumpsiz gun %)
    0.20: (2.47, 1.03, 62), 0.30: (1.30, 0.37, 78),
    0.40: (0.79, 0.17, 87), 0.50: (0.52, 0.09, 92),
}

SAAT = {   # etiket: (yillik, Sharpe, 22-24, 25-26, dusus)
    "04 UTC = 07:00 Ist.": (31.7, 0.747, -0.565, 1.475, -75.5),
    "ASYA 00/04/20 UTC": (6.3, 0.607, -0.819, 1.390, -91.7),
    "00 UTC = 03:00 Ist.": (3.6, 0.482, -0.726, 1.061, -81.3),
    "+50% funding>0": (0.7, 0.530, -0.378, 0.996, -86.5),
    "+40% filtresiz": (-10.1, 0.765, -0.142, 1.328, -98.9),
}

PAY_OLAY = {   # pay: (getiri, Sharpe, 22-24, 25-26, dusus, esit-risk)
    0.00: (112.5, 2.942, 2.794, 3.147, -14.5, 112.5),
    0.05: (111.0, 3.014, 2.744, 3.373, -14.6, 110.5),
    0.10: (109.1, 3.011, 2.674, 3.450, -16.7, 89.3),
    0.20: (104.4, 2.779, 2.459, 3.226, -21.1, 62.4),
}

PAY_GERIDONUS = {   # pay: (getiri, Sharpe, dusus, esit-risk)
    0.00: (112.5, 2.942, -14.5, 112.5), 0.05: (107.8, 2.931, -14.3, 110.0),
    0.10: (103.3, 2.915, -14.1, 107.4), 0.15: (98.7, 2.891, -14.0, 104.7),
    0.25: (89.9, 2.818, -15.0, 86.2), 0.50: (69.0, 2.461, -17.6, 53.9),
    1.00: (32.1, 1.228, -24.4, 18.0),
}

ESITSIZLIK = {   # kol: (Sh_kol, korelasyon, gozlenen Sharpe etkisi)
    "pump modulu (197)": (0.69, 0.043, "YUKSELDI"),
    "olay kolu (241)": (0.747, 0.019, "YUKSELDI"),
    "momentum (237)": (1.935, 0.718, "DUSTU"),
    "geri donus (241)": (1.228, 0.471, "DUSTU"),
}
SH_ANA = 2.942


def gereken(kor):
    """Kolun portfoy Sharpe'ini yukseltmesi icin gereken en az Sharpe."""
    return SH_ANA * kor


if __name__ == "__main__":
    print("MADDE 241 - OLAY KOLU: olcum ozeti\n")
    print("1) OLAYIN KENDISI (+-%40, 3 gun, uygun evren)")
    print("  %-16s%7s%9s%9s%10s%9s%9s" % ("olay", "N", "ort %", "medyan",
                                          "kazanan", "p1", "en kotu"))
    for ad, t in OLAY.items():
        print("  %-16s%7d%+9.2f%+9.2f%9.1f%%%+9.1f%+9.0f" % (ad, *t))
    print("\n   ARZ (gunde kac sembol esigi asiyor)")
    for e, (p, d, y) in ARZ.items():
        print("   +-%2d%%: pump %.2f / dump %.2f  (dumpsiz gun %%%d)"
              % (e * 100, p, d, y))
    print("\n2) SAAT (pozisyon basina sabit %20)")
    print("  %-22s%9s%9s%9s%9s%9s" % ("varyant", "yillik", "Sharpe",
                                      "22-24", "25-26", "dusus"))
    for ad, t in SAAT.items():
        print("  %-22s%+9.1f%9.3f%9.3f%9.3f%9.1f" % (ad, *t))
    print("  -> HER varyant 2022-24'te NEGATIF; 03:00 en iyisi DEGIL")
    print("\n3) SERMAYE PAYI - olay kolu")
    print("  %-8s%9s%9s%9s%9s%9s%12s" % ("pay", "getiri", "Sharpe", "22-24",
                                         "25-26", "dusus", "esit-risk"))
    for w, t in PAY_OLAY.items():
        print("  %-8s%+9.1f%9.3f%9.3f%9.3f%9.1f%+12.1f" % ("%%%d" % (w * 100), *t))
    print("\n   SERMAYE PAYI - olceklenebilir geri donus kitabi")
    print("  %-8s%9s%9s%9s%12s" % ("pay", "getiri", "Sharpe", "dusus", "esit-risk"))
    for w, t in PAY_GERIDONUS.items():
        print("  %-8s%+9.1f%9.3f%9.1f%+12.1f" % ("%%%d" % (w * 100), *t))
    print("\n4) ELEME ESITSIZLIGI:  Sh_kol > Sh_ana (%.3f) x korelasyon" % SH_ANA)
    print("  %-22s%9s%8s%10s%12s" % ("kol", "Sh_kol", "kor", "gereken", "gozlem"))
    for ad, (s, k, g) in ESITSIZLIK.items():
        print("  %-22s%9.3f%8.3f%10.3f%12s" % (ad, s, k, gereken(k), g))
    print("\n  SINIR: Sharpe'in yukselmesi KAR'in yukselmesi degildir -")
    print("  kuyruklu kol dususu derinlestirir, esit-risk getirisi coker.")
    print("  Esitsizlik bir ELEME aracidir, KABUL gerekcesi degil.")
