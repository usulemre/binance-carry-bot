"""MADDE 240: DEFTERIN ACTIGI DORT PARAMETRE - dordu de yerinde kaldi.

Madde 222 bir kural koydu, madde 227 o kuralin uygulamasinda bir delik
buldu (**listenin kendisi eksikti**). Madde 240 listeyi elden cikardi:
`arastirma_yeniden_acma_defteri.py` listeyi `carry_bot.py`
docstring'lerinden OKUYOR. Defterin actigi dort parametre taranmistir.

Kontrol: HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40
TPS=0.20 UCELE=0.40 DONUK_ESIK=0.10 SK_DOSYA=sk_bar48 REB_GUN=5 FAZ=15,
iki faz ortalamasi -> +%112,5 / Sharpe 2,942 (gunluk) / dusus -%14,54.

SONUC: 0 degisiklik / 4 parametre. Ama her biri YENI bilgi verdi.
"""

# (getiri, Sharpe, 22-24, 25-26, dusus POZITIF, esit-risk, kaldirac)
KONTROL = (112.5, 2.942, 2.794, 3.147, 14.54, 112.5, 1.00)

PENCERE = {   # funding sinyal penceresi (saat) - son tarama madde 209
    "8 saat":  (90.5, 2.629, 2.720, 2.540, 12.98, 105.3, 1.12),
    "24 saat": (100.6, 2.773, 2.787, 2.777, 13.48, 111.5, 1.08),
    "36 saat": (104.3, 2.821, 2.697, 2.995, 14.12, 108.6, 1.03),
    "48 saat": KONTROL,
    "60 saat": (109.6, 2.873, 2.682, 3.134, 14.48, 110.2, 1.00),
    "72 saat": (105.7, 2.798, 2.623, 3.035, 15.04, 100.8, 0.97),
}

REZERV_ESIK = {   # gunluk funding esigi - docstring'inde madde ATFI YOKTU
    "%1,0": (115.3, 2.915, 2.762, 3.129, 15.03, 110.0, 0.97),
    "%1,2": (114.3, 2.932, 2.780, 3.144, 14.82, 111.2, 0.98),
    "%1,5": KONTROL,
    "%1,8": (111.3, 2.966, 2.823, 3.165, 14.40, 112.8, 1.01),
    "%2,0": (110.2, 2.977, 2.831, 3.180, 14.30, 112.8, 1.02),
    "%2,2": (109.1, 2.979, 2.836, 3.177, 14.20, 112.8, 1.02),
    "%2,5": (105.5, 2.955, 2.823, 3.139, 13.96, 111.7, 1.04),
    "%3,0": (103.8, 2.968, 2.835, 3.153, 13.73, 112.4, 1.06),
}

REZERV_KAP = {   # coin basina EK pay ust siniri - docstring'inde ATIF YOKTU
    "%3": (105.3, 2.925, 2.781, 3.124, 14.21, 108.6, 1.02),
    "%5": KONTROL,
    "%8": (118.0, 2.932, 2.764, 3.166, 15.02, 112.7, 0.97),
    "%15": (121.8, 2.922, 2.743, 3.171, 15.34, 112.8, 0.95),
}

DONUK = {   # donuk seri esigi - son tarama madde 183 (57 tur once)
    "0,05": (112.0, 2.951, 2.784, 3.181, 14.54, 112.0, 1.00),
    "0,10": KONTROL,
    "0,20": (108.5, 2.857, 2.765, 2.995, 14.54, 108.5, 1.00),
    "0,30": (109.1, 2.872, 2.768, 3.024, 15.13, 103.1, 0.96),
}

BULGULAR = """
1) PENCERE: 48 saat kaldi - VE TEPE SIVRILESTI. Madde 209'da 36/48/60
   "0,03 Sharpe icinde YAYLA" diye kaydedilmisti; bugun 48, 60'i 0,069
   ve 36'yi 0,121 Sharpe geciyor. Kitabin geri kalani iyilestikce
   optimum BELIRSIZLESMEDI, TERSINE keskinlesti. Her bes alternatif de
   iki donemde de Sharpe kaybediyor (tek yonlu: 8<24<36<48>60>72).

2) REZERV ESIGI: eksen ESIT RISKTE DUZ. %1,0'dan %3,0'a kadar esit-risk
   +%110,0 ile +%112,8 arasinda; getiri tek yonlu DUSUYOR (+115,3 ->
   +103,8) ve dusus tek yonlu SIGLASIYOR (-15,03 -> -13,73). Yani bu bir
   KAR dial'i degil, bir PURUZSUZLUK dial'i. %1,8-%2,2 iki donemde de
   Sharpe'i yukseltiyor (tepe %2,2: 2,979) ve dususu sigaltiyor, ama
   esit riskte kazanc +0,3 puan ve 1,02x kaldirac istiyor -> sart 4
   reddediyor. OLCULMUS SECENEK olarak duruyor: daha puruzsuz bir binis
   icin ~2,3 puan getiri odemeye razi olan %2,0'a cekebilir.

3) REZERV COIN KAPI: %5 esit-risk yaylasinda. Kapi acildikca ham getiri
   artiyor (+105,3 -> +121,8) AMA dusus ayni oranda derinlesiyor
   (-14,21 -> -15,34); esit-risk %5'in uzerinde +112,7/+112,8'de SABIT.
   **Kapi bir DOZ dial'idir, alfa dial'i degil** - projenin kendi yasasi
   (madde 225/229: yogunlasma doz demektir) bir kez daha.

4) DONUK ESIGI: 0,10 tepede. Siklastirmak 4 ila 9 puan yakiyor
   (0,20 -> +%108,5; 0,30 -> +%103,1), gevsetmek notr (0,05 -> +%112,0).
   Son olcumden 57 tur gecmisti.

META: madde 223'ten 240'a kadar YENIDEN ACILAN 12 parametrenin HICBIRI
degismedi. O araliktaki gercek kazanclar parametrelerden degil,
(a) gizli baglantilari duzeltmekten (223'un bayat sermayesi, 228'in
gizli kuplaji) ve (b) izleme/alarm katmanindan (231-234) geldi.
Defter artik bunu MEKANIK olarak soyluyor: canli strateji yuzeyinde
madde 222'nin kuralindan once olculmus parametre KALMADI (kapali
eksenlerdekiler haric: icra 3,3 puan, oynaklik hedefleme, solma).
"""


def _yaz(ad, tablo, secili):
    print("\n" + ad)
    print("  %-10s%9s%9s%8s%8s%8s%11s%8s" % ("deger", "yillik", "Sharpe",
          "22-24", "25-26", "dusus", "esit-risk", "kald."))
    for k, t in tablo.items():
        im = "  <- kalan" if k == secili else ""
        print("  %-10s%+9.1f%9.3f%8.3f%8.3f%8.2f%+11.1f%8.2f%s" % (
            k, t[0], t[1], t[2], t[3], -t[4], t[5], t[6], im))


if __name__ == "__main__":
    print("MADDE 240 - YENIDEN ACMA TURU: 4 parametre, 0 degisiklik")
    _yaz("A) FUNDING SINYAL PENCERESI (son tarama madde 209)", PENCERE, "48 saat")
    _yaz("B) FIRSAT REZERVI ESIGI (docstring'inde madde ATFI YOKTU)",
         REZERV_ESIK, "%1,5")
    _yaz("C) REZERV COIN KAPI (docstring'inde madde ATFI YOKTU)",
         REZERV_KAP, "%5")
    _yaz("D) DONUK SERI ESIGI (son tarama madde 183)", DONUK, "0,10")
    print(BULGULAR)
