"""MADDE 244: ALTI ALTERNATIF STRATEJI - ve IC TARAMASININ CEVABI TERS VERMESI.

Projenin elindeki ama strateji olarak hic kullanilmamis uc veri kumesi
denendi: prim endeksi (`data_premium`, 616 sembol), ust trader
konumlanmasi ve genel long/short orani (`metrik_panel`, tam 847
sembollük panel - madde 145 bunlari YALNIZCA 21 coinde ve eski yuzeyde
olcmustu). Hepsi BIRINCIL secici olarak kosuldu (motorun SK_DOSYA
paneli), tam yapilandirma, iki faz.

================================================================
1) BUTCE: IC TARAMASI (kesitsel Spearman, ileri 5 GUNLUK FIYAT getirisi)
================================================================
  sinyal                               IC        t
  ust trader oranini IZLE          +0,0573    +5,0   <- EN GUCLU
  kalabaligi IZLE                  +0,0527    +4,3
  geri donus (1 gunluk)            +0,0271    +2,1
  OI buyumesi TERS                 +0,0214    +1,7
  prim endeksi                     +0,0195    +1,6
  taker alis/satis orani           +0,0094    +0,9
  carry (KITABIN SINYALI)          -0,0058    -0,5   <- SIFIR

Ilk sonuc madde 214'un BAGIMSIZ dogrulanmasi: **kitabin kendi
sinyalinin fiyat ongorusu sifirdir.** Funding bir fiyat tahmincisi
degil; kârin tamami TP hasadi.

================================================================
2) ASIL BULGU: IC TARAMASI CEVABI TERS VERDI
================================================================
  strateji (birincil secici)      yillik   Sharpe   IC isareti
  ust trader IZLE (IC +0,057)     +%21,0   1,006    guclu POZITIF
  ust trader KONTRARIAN (-0,057)  +%94,2   2,350    guclu NEGATIF
  kalabalik IZLE (+0,053)         +%12,7   0,741    guclu POZITIF
  kalabalik KONTRARIAN (-0,053)   +%90,0   2,000    guclu NEGATIF

**IC'si NEGATIF olan yon, 1,3 Sharpe daha iyi kitap uretiyor.** Sebep
madde 214: kitap fiyattan kazanmiyor. IC fiyat ongorusunu olcer; kitabin
geliri ise TP hasadi + funding. Konumlanma ucundaki coinler (kalabalik
olanlar) funding oduyor ve geri doniyor - TP onu hasat ediyor.

> YENI TARAMA KURALI: bir aday seciciyi IC ile DEGIL, kitabin
> GERCEKLESEN P&L'i ile ele. IC bu kitapta yanlis hedefi olcer.

Bu, madde 203/209/232'nin etiket hatalari sinifinin yeni bir turu:
orada ETIKET yanlisti, burada OLCULEN HEDEF yanlis.

================================================================
3) EN IYI ADAY: UST TRADER KONTRARIAN - en guclu kol, yine de RED
================================================================
Tek basina: +%94,2 / Sharpe 2,350 / dusus -%20,8 · carry ile GETIRI
korelasyonu **+0,702**.

Madde 241'in eleme esitsizligi (Sh_kol > Sh_ana x kor): gereken 2,066,
kolun Sharpe'i 2,350 -> **+0,284 marjla GECER** (projenin olctugu en
geniş marj; madde 237'nin momentumu neredeyse ayni korelasyonda
-0,177 ile elenmisti).

  pay    getiri   Sharpe   22-24   25-26   dusus   esit-risk  kald.
  %0    +%112,5   2,942   2,794   3,147   -14,5    +%112,5   1,00
  %10   +%111,0   2,965   2,838   3,145   -13,2    +%127,8   1,11
  %20   +%109,5   2,967   2,865   3,123   -13,0    +%128,9   1,13
  %30   +%107,9   2,949   2,870   3,081   -13,1    +%125,4   1,12
  %50   +%104,4   2,849   2,810   2,942   -13,7    +%113,4   1,06

Sharpe TAM ORNEKTE ve 22-24'te YUKSELIYOR, dusus 1,5 puan SIGLASIYOR,
esit-risk %20'de **+16,4 puan**. **RED, iki sebeple:** sart 1 (25-26
-0,024; %10'da -0,002) ve sart 4 (1,11-1,13x kaldirac gerekiyor ve aday
kaldiracsiz USTUN degil - getirisi 3 puan DAHA AZ). Bootstrap:

  pay    dSharpe   P(dSh>0)   d esit-risk   P(>0)
  %10     +0,024     %70,6      +5,3 puan   %70,2
  %20     +0,027     %62,5      +8,5 puan   %64,5
  %30     +0,012     %55,0      +9,3 puan   %59,9

Tam ornekteki +16,4 puan +8,5'e dusuyor, P %64,5. Madde 227/235/239/241
ile ayni desen: en guclu aday bile ayirt edilemez.

================================================================
4) PRIM ENDEKSI: AYNI PRIMIN DAHA KOTU OLCUMU
================================================================
  secici              yillik   Sharpe   22-24   25-26   dusus    kor
  funding 48sa (ktrl) +%112,5   2,942   2,794   3,147   -14,5      -
  prim 48sa            +%92,8   2,676   2,592   2,801   -13,6   +0,946
  prim anlik           +%73,4   2,589   2,650   2,530    -9,4   +0,924
  prim 120sa           (bkz. araç çıktısı)
  harman %25 prim      +%84,3   2,742   2,775   2,707   -13,2   +0,956
  harman %50 prim      +%84,1   2,706   2,690   2,732   -12,8   +0,951
  harman %75 prim      +%87,9   2,748   2,627   2,915   -13,0   +0,946

Prim endeksi funding'i BELIRLEYEN seydir, o yuzden korelasyon 0,92-0,96:
ayni sinyalin baska olcumu. Ama her duzlestirmede ve her harman payinda
**daha kotu**, ve harman monoton kotuleşiyor - madde 237'nin yasasinin
UCUNCU dogrulanmasi.

HATA KAYDI: ilk okumada prim kitabinin MOTOR Sharpe'ini (2,84) kontrolun
GUNLUK Sharpe'i (2,942) ile karsilastirdim ve "neredeyse esit" sandim.
Motor 4 saatlik bar kullanir; ayni tabanda prim 2,676'dir. Proje bu
karisikligi madde 223 ve 237'de de yakalamisti - ucuncu tekrar.

Kosum: arastirma_alternatif_strateji_kos.sh, sonra bu dosya.
"""

IC = {   # sinyal: (IC, t)
    "ust trader IZLE": (+0.0573, +5.0), "kalabaligi IZLE": (+0.0527, +4.3),
    "geri donus 1g": (+0.0271, +2.1), "OI buyumesi TERS": (+0.0214, +1.7),
    "prim endeksi": (+0.0195, +1.6), "taker orani": (+0.0094, +0.9),
    "carry (kitabin sinyali)": (-0.0058, -0.5),
}

TEK_BASINA = {   # strateji: (yillik, Sharpe, 22-24, 25-26, dusus, korelasyon)
    "carry (KONTROL)": (112.5, 2.942, 2.794, 3.147, -14.5, None),
    "ust trader KONTRARIAN": (94.2, 2.350, 2.331, 2.424, -20.8, 0.702),
    "kalabalik KONTRARIAN": (90.0, 2.000, 1.791, 2.282, -26.9, 0.758),
    "prim 48sa": (92.8, 2.676, 2.592, 2.801, -13.6, 0.946),
    "prim TERS": (41.3, 1.500, 1.420, 1.614, -22.2, 0.566),
    "ust trader IZLE": (21.0, 1.006, 0.612, 1.482, -20.8, 0.253),
    "kalabalik IZLE": (12.7, 0.741, 0.432, 1.168, -19.5, 0.009),
}

PAY = {   # ust trader kontrarian kolu - pay: (getiri,Sharpe,22-24,25-26,dusus,esit-risk,kald)
    0.00: (112.5, 2.942, 2.794, 3.147, -14.5, 112.5, 1.00),
    0.10: (111.0, 2.965, 2.838, 3.145, -13.2, 127.8, 1.11),
    0.20: (109.5, 2.967, 2.865, 3.123, -13.0, 128.9, 1.13),
    0.30: (107.9, 2.949, 2.870, 3.081, -13.1, 125.4, 1.12),
    0.50: (104.4, 2.849, 2.810, 2.942, -13.7, 113.4, 1.06),
}

BOOTSTRAP = {0.10: (+0.024, 70.6, +5.3, 70.2), 0.20: (+0.027, 62.5, +8.5, 64.5),
             0.30: (+0.012, 55.0, +9.3, 59.9)}

HARMAN_PRIM = {0.25: (84.3, 2.742, 2.775, 2.707, -13.2, 0.956),
               0.50: (84.1, 2.706, 2.690, 2.732, -12.8, 0.951),
               0.75: (87.9, 2.748, 2.627, 2.915, -13.0, 0.946)}

SH_ANA = 2.942


def esitsizlik(ad):
    """Madde 241'in eleme esitsizligi: (gereken esik, gecer mi)."""
    t = TEK_BASINA[ad]
    if t[5] is None:
        return None, None
    ger = SH_ANA * t[5]
    return ger, t[1] > ger


if __name__ == "__main__":
    print("MADDE 244 - ALTERNATIF STRATEJILER\n")
    print("1) IC TARAMASI (ileri 5 gunluk FIYAT getirisi)")
    print("  %-26s%10s%8s" % ("sinyal", "IC", "t"))
    for ad, (ic, t) in IC.items():
        print("  %-26s%+10.4f%+8.1f" % (ad, ic, t))
    print("\n2) TEK BASINA (gunluk Sharpe tabani) + madde 241 esitsizligi")
    print("  %-24s%9s%8s%8s%8s%8s%8s%9s%9s" % ("strateji", "yillik", "Sharpe",
          "22-24", "25-26", "dusus", "kor", "gereken", "esitsiz."))
    for ad, t in TEK_BASINA.items():
        ger, gec = esitsizlik(ad)
        print("  %-24s%+9.1f%8.3f%8.3f%8.3f%8.1f%8s%9s%9s" % (
            ad, t[0], t[1], t[2], t[3], t[4],
            "-" if t[5] is None else "%+.3f" % t[5],
            "-" if ger is None else "%.3f" % ger,
            "-" if gec is None else ("GECER" if gec else "elenir")))
    print("\n  -> IC'si NEGATIF olan yon 1,3 Sharpe DAHA IYI kitap veriyor")
    print("     (IC fiyat ongorusunu olcer; kitap fiyattan kazanmaz - madde 214)")
    print("\n3) EN IYI KOL: ust trader KONTRARIAN - sermaye payi")
    print("  %-8s%9s%8s%8s%8s%8s%12s%7s%11s%9s" % ("pay", "getiri", "Sharpe",
          "22-24", "25-26", "dusus", "esit-risk", "kald.", "boot d-ER", "P(>0)"))
    for w, t in PAY.items():
        b = BOOTSTRAP.get(w)
        print("  %-8s%+9.1f%8.3f%8.3f%8.3f%8.1f%+12.1f%7.2f%11s%9s" % (
            "%%%d" % (w * 100), *t,
            "-" if not b else "%+.1f" % b[2], "-" if not b else "%.1f%%" % b[3]))
    print("\n  RED: sart 1 (25-26 duşuyor) + sart 4 (1,11-1,13x kaldirac,")
    print("  kaldiracsiz USTUNLUK yok). Tam ornek +16,4 puan -> bootstrap +8,5 (P %64,5).")
    print("\n4) PRIM HARMANI monoton kotu (madde 237'nin yasasi, 3. dogrulama)")
    for w, t in HARMAN_PRIM.items():
        print("  harman %%%d prim: Sharpe %.3f  (kontrol %.3f)  kor %+.3f"
              % (w * 100, t[1], SH_ANA, t[5]))
