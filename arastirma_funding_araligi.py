"""MADDE 246: FUNDING ARALIGI DENETIMI - evren KARISIK, ve sinyal zaten en iyisi.

Farkli bir aci: arama degil DENETIM. Projede +puan kazandiran tek
kategori olcum zinciri denetimi (madde 182/209/212: dort hata, +3,8
puan). Hic incelenmemis bir sey vardi: **funding ARALIGI coin basina
degisiyor.**

================================================================
1) EVREN KARISIK - VE BU HIC INCELENMEMISTI
================================================================
847 sembolun odeme araliklari (zaman damgalarindan, medyan):

  aralik    sembol    pay
   1 saat        4    %0,5
   4 saat      482   %56,9   <- EVRENIN YARISINDAN FAZLASI
   8 saat      361   %42,6

Ayni kote oranla 4 saatlik odeyen coin, 8 saatliginin IKI KATI gunluk
taşima verir. Aralik degisimi gozlenmedi (0/847 sembolde gecis).

================================================================
2) OLCULEN SAPMA: SINYAL 4 SAATLIKLERI DUSUK SIRALIYOR
================================================================
Uretim sinyalinin (sk_bar48, canli tahminci) ayni ceyreginde,
GERCEKLESEN gunluk funding:

  sinyal ceyregi   4 saatlik    8 saatlik   fark
  Q1 (en uc)      -0,02164     -0,01390    %56
  Q2              -0,00468     -0,00317    %48
  Q3              -0,00033     -0,00019    %76

ODE/sinyal orani: 4sa 1,314 vs 8sa 1,080 -> **%22 sapma.** Yani kitap,
evrenin %57'sini sistematik olarak DUSUK siraliyor.

================================================================
3) UC DUZELTME DENENDI - UCU DE KONTROLDEN KOTU
================================================================
  sinyal                            getiri   Sharpe   dusus   esit-risk
  KONTROL (canli: medyan + 4sa taban) +%112,5  2,942   -14,5    +%112,5
  TOPLAM (medyan yok) + duzeltilmis   +%120,8  2,765   -16,8     +%98,7
  MEDYAN + aralik DUZELTILMIS         +%106,0  2,585   -16,9     +%86,3
  MEDYAN + hep 8 saat VARSAY           +%86,1  2,268   -19,6     +%58,2

Pencere taramasi da tek yonlu RED: ODE toplami 24sa +%85,0 · 48sa
+%98,7 · 72sa +%89,7 · 120sa +%71,0 (esit-risk).

**UC SONUC:**

(a) **Aralik islemenin bedeli OLCULDU ve BUYUK.** "Hep 8 saat varsay"
    esit riskte **+%58,2** veriyor, kontrol +%112,5 - yani araligi
    yok saymak **54 puan** goturuyor. Bu, projede olculmus EN BUYUK
    tek olcum-hatasi bedeli, ve madde 182/209'un duzeltmesinin degerini
    geriye donuk fiyatlandiriyor.

(b) **Ama sapma SOMURULEBILIR BIR HATA DEGIL.** Uc duzeltmenin ucu de
    kontrolden kotu. Uretim tahmincisi (medyan + 4 saat tabani) benim
    kurdugum her yeniden-insadan iyi; demek ki tabanin kendisi de yuk
    tasiyor (madde 209'da eklenmisti ve ben onu yeniden kurmadim).

(c) **MEKANIZMA:** 4 saatlik coinlerin fazla taşimasi BEDAVA DEGIL.
    Onlara yaslanan her varyantta dusus derinlesiyor (-16,8..-19,6 vs
    -14,5). Borsa kisa araligi daha oynak/uc coinlere veriyor; "ayni
    sinyalde daha cok kira" bir alfa degil TAZMINAT.

YENI AYRIM (madde 212'yi tamamlar): **coin ICINDE zamanda yumusatma
(medyan) RISK ISI yapar ve YARDIM EDER; coinler ARASINDA normalizasyon
geliri YOK EDER (madde 212).** Ikisi ayni islem degil.

HATA KAYDI: bu turu "uretim sinyalinde duzeltilmemis bir yanlilik var,
duzeltmek kar getirir" hipoteziyle actim. Olcum hipotezi CURUTTU: sapma
gercek ama duzeltmeleri kotu. Kullaniciya ilk mesajda hipotezi
"muhtemel mekanizma" diye yazdim; sonuc tersi cikti ve burada kayitli.

Kosum: python3 arastirma_funding_araligi.py
"""

ARALIK_DAGILIMI = {1: 4, 4: 482, 8: 361}
ARALIK_DEGISEN = 0          # 847 sembolde aralik gecisi gozlenmedi

SAPMA = {   # sinyal ceyregi: (4 saatlik gunluk ODE, 8 saatlik, fark %)
    "Q1": (-0.02164, -0.01390, 56), "Q2": (-0.00468, -0.00317, 48),
    "Q3": (-0.00033, -0.00019, 76),
}
ODE_SINYAL_ORANI = {4: 1.314, 8: 1.080}     # 4sa/8sa = 1,217 -> %22 sapma

VARYANT = {   # ad: (getiri, Sharpe, 22-24, 25-26, dusus, esit-risk)
    "KONTROL (medyan + 4sa taban)": (112.5, 2.942, 2.794, 3.147, -14.5, 112.5),
    "TOPLAM + aralik duzeltilmis": (120.8, 2.765, 2.631, 2.950, -16.8, 98.7),
    "MEDYAN + aralik duzeltilmis": (106.0, 2.585, 2.448, 2.773, -16.9, 86.3),
    "MEDYAN + hep 8 saat varsay": (86.1, 2.268, 2.265, 2.280, -19.6, 58.2),
}

PENCERE = {24: 85.0, 48: 98.7, 72: 89.7, 120: 71.0}   # ODE toplami, esit-risk

ARALIGI_YOKSAYMANIN_BEDELI = 112.5 - 58.2             # puan


if __name__ == "__main__":
    print("MADDE 246 - FUNDING ARALIGI DENETIMI\n")
    print("1) EVREN KARISIK (847 sembol)")
    tot = sum(ARALIK_DAGILIMI.values())
    for a, n in sorted(ARALIK_DAGILIMI.items()):
        print("  %2d saat: %4d sembol  (%%%.1f)" % (a, n, 100 * n / tot))
    print("  aralik DEGISEN sembol: %d / %d" % (ARALIK_DEGISEN, tot))
    print("\n2) OLCULEN SAPMA (ayni sinyal ceyreginde gerceklesen gunluk funding)")
    print("  %-6s%13s%13s%8s" % ("ceyrek", "4 saatlik", "8 saatlik", "fark"))
    for q, (a4, a8, f) in SAPMA.items():
        print("  %-6s%13.5f%13.5f%7d%%" % (q, a4, a8, f))
    print("  ODE/sinyal orani: 4sa %.3f vs 8sa %.3f -> %%%.0f sapma"
          % (ODE_SINYAL_ORANI[4], ODE_SINYAL_ORANI[8],
             (ODE_SINYAL_ORANI[4] / ODE_SINYAL_ORANI[8] - 1) * 100))
    print("\n3) UC DUZELTME - UCU DE KONTROLDEN KOTU")
    print("  %-32s%9s%8s%8s%12s" % ("sinyal", "getiri", "Sharpe", "dusus",
                                    "esit-risk"))
    for ad, t in VARYANT.items():
        im = "  <- kalan" if ad.startswith("KONTROL") else ""
        print("  %-32s%+9.1f%8.3f%8.1f%+12.1f%s" % (ad, t[0], t[1], t[4], t[5], im))
    print("\n  pencere taramasi (ODE toplami, esit-risk):")
    for w, e in PENCERE.items():
        print("    %3d saat: +%.1f%%" % (w, e))
    print("\n  (a) araligi YOKSAYMANIN bedeli: %.1f PUAN (projede olculmus en"
          % ARALIGI_YOKSAYMANIN_BEDELI)
    print("      buyuk tek olcum-hatasi bedeli; madde 182/209'u fiyatlandirir)")
    print("  (b) ama sapma SOMURULEBILIR DEGIL: uc duzeltmenin ucu de kotu")
    print("  (c) mekanizma: 4 saatliklerin fazla taşimasi TAZMINAT, alfa degil")
    print("      (onlara yaslanan her varyantta dusus derinlesiyor)")
    print("\n  YENI AYRIM: coin ICINDE zamanda yumusatma (medyan) RISK isi yapar")
    print("  ve YARDIM EDER; coinler ARASINDA normalizasyon geliri YOK EDER (212).")
