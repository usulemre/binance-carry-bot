"""MADDE 242: KOORDINAT OPTIMUMU MU, ORTAK OPTIMUM MU? - ikisi ayni yer.

NEDEN SORULDU: madde 238 katmanlarin TOPLAMSAL OLMADIGINI olctu (emir
akisi ve uc hareket elemesi merdivenin bir noktasinda negatif, tam
yapilandirmadan cikarilinca pozitif). Madde 240 her parametrenin TEK TEK
optimumda oldugunu dogruladi. Bu ikisi birlikte bir bosluk birakiyordu:
**etkilesimler guclu ise koordinat optimumu ortak optimumdan uzak
olabilir.** Proje 240 tur boyunca HEP tek-parametre taradi; ortak bir
tarama hic yapilmadi.

TASARIM: dort parametrenin de "beraberlik/red ama yakin" cikan komsusu
secildi - dordu de tek tek olculdugunde esit-riski YUKARI gosteriyordu:

  parametre   merkez   komsu   tek tek olculdugunde (esit-risk)
  TPL          0,40     0,50   +121,5 (madde 227; bootstrap reddetti)
  HAVUZ        3,0      4,0    +115,8 (madde 224; beraberlik, P %50,9)
  UCELE        0,40     0,60   +118,6 (madde 236)
  REZERV       0,20     0,30   +113,5 (madde 225; kaldirac 1,13x)

2^4 = 16 hucre, her biri iki faz ortalamasi (32 kosum).

================================================================
BULGU 1: ETKILESIMLER IHMAL EDILEBILIR -> KOORDINAT = ORTAK OPTIMUM
================================================================
  ANA ETKILER (+1 seviyeye gecis)      d Sharpe   d esit-risk   d getiri
  TP     0,40 -> 0,50                   -0,024       +10,8        +4,9
  HAVUZ  3,0  -> 4,0                    -0,020        +3,7        -0,6
  UCELE  0,40 -> 0,60                   -0,065        +6,4        -0,2
  REZERV 0,20 -> 0,30                   -0,002        +0,9       -16,4

  EN BUYUK IKILI ETKILESIM             +0,004        +1,05

Sharpe'ta en buyuk etkilesim **+0,004**, en buyuk ana etki -0,065 -
yani etkilesim ana etkinin **%6'si**. Esit-riskte 1,05 puana karsi 10,8
puan (**%10**). **Bu parametre blogu TOPLAMSALDIR.**

MADDE 238 ILE CELISMEZ, ONU TAMAMLAR - ve yeni bir yasa verir:

  > KATMAN AC/KAPA siframalari ETKILESIR (madde 238: isaret bile
  > degisir). YEREL PARAMETRE ADIMLARI ETKILESMEZ (madde 242).

Pratik sonucu buyuk: projenin 240 tur boyunca kullandigi TEK-PARAMETRE
tarama disiplini, optimumun YAKININDA **yeterlidir** - ve bu artik bir
varsayim degil, olculmus bir sonuc.

================================================================
BULGU 2: MERKEZ, SHARPE'TA 1/16 VE ESIT-RISKTE 16/16
================================================================
15 alternatif hucrenin **tamami**: esit-risk merkezin USTUNDE
(+113,5..+134,3), Sharpe merkezin ALTINDA (2,830..2,941), 22-24 Sharpe
merkezin ALTINDA, ve kaldirac >= 1,02x. Kaldiracsiz kalan tek hucre
MERKEZIN KENDISI (1/16).

Yani esit-risk metrigini TEK BASINA maksimize eden bir proje, kupun
**en uzak kosesine** yururdu (TP0,50 H4 U0,60 R0,30: esit-risk +%134,3)
- ve o kose kupteki **en dusuk Sharpe'a** sahip (2,830), 1,24x kaldirac
istiyor. Esli blok bootstrap o kazanci da yok ediyor:

  aday                   dSharpe   P(dSh>0)   d esit-risk   P(>0)
  en uzak kose (4 dgs)    -0,113     %15,2      -2,7 puan   %46,0
  TP0,50 tek (1 dgs)      -0,025     %35,9      +1,9 puan   %64,2
  UCELE0,60 tek (1 dgs)   -0,068      %8,5      -5,3 puan   %28,2

Tam ornekteki **+21,8 puan** bootstrap'ta **-2,7 puana** doner.
(TP0,50 satiri madde 227'nin +2,2 / P %64,1 olcumunu bagimsiz olarak
tekrarliyor - olcum zincirinin dogrulanmasi.)

BU, DORT SARTLI KURALIN EN NET GEREKCESI: sart 3 (esit-risk) bir VETO,
bir kabul gerekcesi degil (madde 223); sart 4 (kaldirac gerekmesin)
madde 225'te kondu. Madde 242 ikisinin de olmasa ne olurdu sorusunun
cevabini gosteriyor: kup boyunca yanlis yone, tek yonlu bir yurume.

Kosum: arastirma_faktoriyel_kos.sh, sonra python3 arastirma_faktoriyel.py
"""

# hucre: (degisen sayisi, getiri, Sharpe, 22-24, 25-26, dusus, esit-risk, kaldirac)
HUCRE = {
    "MERKEZ":                (0, 112.5, 2.942, 2.794, 3.147, -14.5, 112.5, 1.00),
    "TP0.50 H4 U0.60 R0.30": (4, 100.2, 2.830, 2.720, 2.993, -11.8, 134.3, 1.24),
    "TP0.50 H4 U0.60 R0.20": (3, 117.1, 2.834, 2.721, 2.998, -13.2, 133.6, 1.10),
    "TP0.50 H3 U0.60 R0.30": (3, 100.4, 2.843, 2.704, 3.041, -12.0, 130.2, 1.21),
    "TP0.50 H3 U0.60 R0.20": (2, 117.1, 2.847, 2.709, 3.043, -13.6, 129.2, 1.07),
    "TP0.50 H4 U0.40 R0.30": (3, 100.0, 2.892, 2.763, 3.074, -12.2, 127.5, 1.20),
    "TP0.50 H4 U0.40 R0.20": (2, 117.0, 2.895, 2.764, 3.079, -13.7, 126.9, 1.06),
    "TP0.50 H3 U0.40 R0.30": (2, 100.6, 2.912, 2.757, 3.129, -12.6, 122.4, 1.16),
    "TP0.40 H4 U0.60 R0.30": (3,  95.6, 2.852, 2.740, 3.017, -12.2, 121.7, 1.20),
    "TP0.50 H3 U0.40 R0.20": (1, 117.6, 2.916, 2.762, 3.131, -14.2, 121.5, 1.02),
    "TP0.40 H4 U0.60 R0.20": (2, 111.5, 2.852, 2.741, 3.013, -13.7, 120.8, 1.06),
    "TP0.40 H3 U0.60 R0.30": (2,  96.2, 2.872, 2.737, 3.066, -12.4, 119.7, 1.18),
    "TP0.40 H3 U0.60 R0.20": (1, 112.0, 2.873, 2.743, 3.058, -14.0, 118.6, 1.04),
    "TP0.40 H4 U0.40 R0.30": (2,  95.5, 2.914, 2.780, 3.103, -12.6, 116.6, 1.16),
    "TP0.40 H4 U0.40 R0.20": (1, 111.5, 2.914, 2.780, 3.099, -14.1, 115.8, 1.03),
    "TP0.40 H3 U0.40 R0.30": (1,  96.5, 2.941, 2.788, 3.154, -12.9, 113.5, 1.13),
}

ANA_ETKI = {   # faktor: (d Sharpe, d esit-risk, d getiri, d dusus)
    "TP 0,40->0,50":     (-0.024, +10.8, +4.9, -0.39),
    "HAVUZ 3,0->4,0":    (-0.020, +3.7, -0.6, -0.34),
    "UCELE 0,40->0,60":  (-0.065, +6.4, -0.2, -0.51),
    "REZERV 0,20->0,30": (-0.002, +0.9, -16.4, -1.55),
}

ETKILESIM = {   # cift: (d Sharpe, d esit-risk)
    "TP x HAVUZ": (+0.004, +1.0), "TP x UCELE": (-0.000, +0.8),
    "TP x REZERV": (-0.002, -0.1), "HAVUZ x UCELE": (+0.004, -0.5),
    "HAVUZ x REZERV": (+0.001, -0.1), "UCELE x REZERV": (-0.000, +0.0),
}

BOOTSTRAP = {   # aday: (dSharpe, P(dSh>0)%, d esit-risk, P(>0)%)
    "en uzak kose (4 dgs)": (-0.113, 15.2, -2.7, 46.0),
    "TP0,50 tek (1 dgs)": (-0.025, 35.9, +1.9, 64.2),
    "UCELE0,60 tek (1 dgs)": (-0.068, 8.5, -5.3, 28.2),
}


def siralama(olcut):
    """Merkezin 16 hucre icindeki sirasi (1 = en iyi)."""
    i = 6 if olcut == "esit" else 2          # esit-risk / Sharpe alan indeksi
    d = sorted(HUCRE.items(), key=lambda t: -t[1][i])
    return 1 + [a for a, _ in d].index("MERKEZ")


if __name__ == "__main__":
    print("MADDE 242 - 2^4 FAKTORIYEL (TPL x HAVUZ x UCELE x REZERV)\n")
    print("%-24s%5s%9s%8s%7s%7s%8s%11s%7s" % ("hucre", "dgs", "getiri", "Sharpe",
          "22-24", "25-26", "dusus", "esit-risk", "kald."))
    for ad, t in sorted(HUCRE.items(), key=lambda x: -x[1][6]):
        im = "  <- MERKEZ" if ad == "MERKEZ" else ""
        print("%-24s%5d%+9.1f%8.3f%7.3f%7.3f%8.1f%+11.1f%7.2f%s"
              % (ad, t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], im))
    print("\nANA ETKILER")
    print("  %-20s%11s%13s%11s%10s" % ("faktor", "d Sharpe", "d esit-risk",
                                       "d getiri", "d dusus"))
    for ad, t in ANA_ETKI.items():
        print("  %-20s%+11.3f%+13.1f%+11.1f%+10.2f" % (ad, *t))
    print("\nIKILI ETKILESIMLER")
    print("  %-18s%11s%13s" % ("cift", "d Sharpe", "d esit-risk"))
    for ad, t in ETKILESIM.items():
        print("  %-18s%+11.3f%+13.1f" % (ad, *t))
    es = max(abs(v[0]) for v in ETKILESIM.values())
    ae = max(abs(v[0]) for v in ANA_ETKI.values())
    print("\n  en buyuk etkilesim / en buyuk ana etki (Sharpe) = "
          "%.3f / %.3f = %%%.0f" % (es, ae, 100 * es / ae))
    print("  -> YEREL PARAMETRE ADIMLARI TOPLAMSALDIR; tek-parametre tarama YETERLI")
    print("\nMERKEZIN SIRASI: Sharpe %d/16  ·  esit-risk %d/16"
          % (siralama("sharpe"), siralama("esit")))
    print("kaldiracsiz (<=1,005x) kalan hucre: 1/16 (merkezin kendisi)")
    print("\nESLI BLOK BOOTSTRAP (kontrol = MERKEZ)")
    print("  %-24s%10s%11s%14s%9s" % ("aday", "dSharpe", "P(dSh>0)",
                                      "d esit-risk", "P(>0)"))
    for ad, (ds, ps, de, pe) in BOOTSTRAP.items():
        print("  %-24s%+10.3f%10.1f%%%+14.1f%8.1f%%" % (ad, ds, ps, de, pe))
    print("\nKARAR: hicbir hucre kabul edilmedi. Merkez ORTAK optimumdur.")
