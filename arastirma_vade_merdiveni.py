"""MADDE 239: VADE MERDIVENI - kuraldan GECTI, bootstrap REDDETTI.

YAPI: tek bir tutma suresi yerine IKI kitabi ayni anda tutmak (2 gun
ve 5 gun), her biri kendi icinde piyasa-notr. Madde 215 taraf bazli
ZAMANLAMA asimetrisini kapatmisti; bu farkli bir sey - her kitap
simetrik, asimetri kitaplar ARASINDA.

ONCE BUTCE: ufuk merdiveni, iki faz ortalamasi.

  tek ufuk     yillik   Sharpe   dusus   esit-risk
  2 gun       +148.4%   2.810   -16.9     +116.4%
  3 gun       +131.7%   2.861   -15.8     +113.2%
  5 gun (ktrl)+112.2%   2.900   -14.3     +112.2%
  10 gun       +64.2%   2.389   -13.4      +69.5%
  15 gun       +40.0%   1.798   -17.3      +31.9%   (yalniz faz 0)

Esit riskte HICBIR tek ufuk 5 gunu anlamli gecmiyor (2 gun +4,2 puan).
Madde 222'nin 5 gun secimi dogrulandi.

HARMAN tam ornekte DORT SARTI DA GECIYOR ve kaldiracsiz USTUN:

  harman        yillik   Sharpe   22-24   25-26   dusus   esit-risk
  %25 2g+%75 5g +121.5%  2.980   2.829   3.194  -13.55    +130.4%
  %33 2g+%67 5g +124.5%  2.978   2.832   3.189  -13.77    +131.4%
  %50 2g+%50 5g +130.6%  2.958   2.827   3.157  -14.23    +133.4%

AMA ESLI BLOK BOOTSTRAP COKERTIYOR (1.504 gun, 21 gunluk blok, 2.000):

  aday            dSharpe   P(dSh>0)   d esit-risk   P(>0)
  %25 2g           +0,032     %70,2       +3,9 puan   %59,7
  %33 2g           +0,030     %64,3       +2,3 puan   %52,6
  %50 2g           +0,007     %53,5       +0,2 puan   %45,5
  %100 2g (tek)    -0,137     %28,1      -14,6 puan   %27,0

Tam ornekteki +22,5 puan bootstrap'ta +3,9'a dusuyor ve P %60. Doz-yanit
TERS yonlu: 2 gun payi arttikca guven AZALIYOR. **RED.**

NEDEN ONEMLI: bu, madde 227'nin AYNASI. Orada aday kurali gecip
bootstrap'ta cokmustu (0,50/0,20 kar al); burada ayni sey bir YAPI icin
oldu. Ve madde 237'nin yasasini RAFINE ediyor: gunluk getiri
korelasyonu 2g-5g arasinda **+0,875** - momentumun +0,718'inden DAHA
YUKSEK - ama yine de ise yaramiyor. Yani korelasyonun kendisi tek
basina ne kabul ne red gerekcesi; "ayni piyasa duvari" korelasyon
esiginden daha derin bir sey.

  ufuk kitaplarinin gunluk getiri korelasyonu
        2      3      5     10     15
   2  1.000  0.969  0.875  0.721  0.632
   3  0.969  1.000  0.939  0.798  0.699
   5  0.875  0.939  1.000  0.891  0.804
  10  0.721  0.798  0.891  1.000  0.934
  15  0.632  0.699  0.804  0.934  1.000

Kosum: python3 arastirma_vade_merdiveni.py
"""
TEK_UFUK = {   # gun: (yillik, Sharpe, dusus, esit-risk)
    2: (148.4, 2.810, -16.9, 116.4), 3: (131.7, 2.861, -15.8, 113.2),
    5: (112.2, 2.900, -14.3, 112.2), 10: (64.2, 2.389, -13.4, 69.5),
    15: (40.0, 1.798, -17.3, 31.9)}

HARMAN = {   # 2g payi: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk)
    0.25: (121.5, 2.980, 2.829, 3.194, -13.55, 130.4),
    1 / 3: (124.5, 2.978, 2.832, 3.189, -13.77, 131.4),
    0.50: (130.6, 2.958, 2.827, 3.157, -14.23, 133.4)}

BOOTSTRAP = {   # 2g payi: (dSharpe, P(dSh>0)%, d esit-risk, P(>0)%)
    0.25: (+0.032, 70.2, +3.9, 59.7), 1 / 3: (+0.030, 64.3, +2.3, 52.6),
    0.50: (+0.007, 53.5, +0.2, 45.5), 1.00: (-0.137, 28.1, -14.6, 27.0)}

KORELASYON = {   # gunluk getiri korelasyonu
    (2, 5): 0.875, (3, 5): 0.939, (5, 10): 0.891, (2, 10): 0.721,
    (2, 15): 0.632, (5, 15): 0.804}

if __name__ == "__main__":
    print("TEK UFUK (iki faz ortalamasi)")
    print("  %-12s%10s%9s%8s%12s" % ("ufuk", "yillik", "Sharpe", "dusus",
                                     "esit-risk"))
    for g, (y, s, d, e) in TEK_UFUK.items():
        print("  %-12s%+10.1f%9.3f%8.1f%+12.1f" % (f"{g} gun", y, s, d, e))
    print("\nHARMAN - kural GECER, bootstrap REDDEDER")
    print("  %-12s%10s%9s%8s%8s%8s%12s%10s%9s" % (
        "2g payi", "yillik", "Sharpe", "22-24", "25-26", "dusus",
        "esit-risk", "P(dSh>0)", "P(dER>0)"))
    for w, t in HARMAN.items():
        b = BOOTSTRAP[w]
        print("  %-12s%+10.1f%9.3f%8.3f%8.3f%8.1f%+12.1f%9.1f%%%8.1f%%" % (
            f"%{w * 100:.0f}", *t, b[1], b[3]))
    print("\nKARAR: RED. Tam ornekteki +22,5 puan bootstrap'ta +3,9'a "
          "cokuyor (P %59,7).")
    print("2 gun TEK basina da kotu (P %27) - madde 222'nin 5 gunu duruyor.")
