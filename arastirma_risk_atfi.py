"""MADDE 243: RISKIN KAYNAGI - hedge edilecek faktor YOK, ve YOL ZATEN IYI.

Parametre yuzeyi kapandiktan sonra (madde 240 tek tek, madde 242 ortak)
dokunulmamis tek yer kaldi: kitabin RISKININ KAYNAGI. Mantik su: esit-risk
getirisi = getiri / dusus. Butun maddeler GETIRIYI aradi; kimse DUSUSUN
neyden yapildigini sormadi. Eger dususun bir kismi hedge edilebilir bir
faktor maruziyetiyse, onu kaldirmak getiriye dokunmadan kari artirir.

================================================================
1) FAKTOR ATFI: HEDGE EDILECEK PIYASA RISKI YOK
================================================================
Gunluk regresyon (N=1.504):

  model                       R2       beta
  BTC                      0,0000   +0,0009 (t +0,1)   <- TAM NOTR
  ALT (esit agirlik evren) 0,0061   +0,0252 (t +3,0)
  BTC + (ALT-BTC)          0,0127   BTC -0,0138 (t -0,9)
                                    ALT-BTC +0,0533 (t +4,4)

**Varyansin %98,7'si idiyosinkratik.** Kitap gercekten piyasa-notr;
ortak bir faktor olmadigi icin hedge edilecek bir sey de yok.

Kosullu beta VAR ama kucuk: dusus > %5 oldugu 182 gunde BTC betasi
+0,0916 (t +2,4; R2 0,030), diger 1.322 gunde -0,0100 (t -0,7).

================================================================
2) BULUNAN TEK MARUZIYET BIR GELIR KAYNAGI, SIZINTI DEGIL
================================================================
ALT-BTC maruziyeti sabit beta ile hedge edildi:

  hedge                getiri   Sharpe   22-24   25-26   dusus   esit-risk
  YOK (kontrol)       +%112,5   2,942   2,794   3,147   -14,5    +%112,5
  beta 0,053 (olculen) +%96,8   2,671   2,585   2,797   -14,9     +%93,8
  beta 0,10            +%83,8   2,401   2,375   2,452   -17,4     +%66,5
  beta 0,25            +%46,9   1,466   1,626   1,292   -28,0     +%21,8

Hedge ettikce getiri gidiyor VE dusus KOTULESIYOR. Yani o maruziyet
riskin degil GELIRIN bir parcasi - long bacak yuksek funding odeyen
alt'lari tutuyor, maruziyet de oradan geliyor.

**MADDE 191'IN IKINCI ORNEGI:** orada long bacagin yillik -108,5 puan
fiyat kanamasinin bir SIZINTI degil +141,6 puanlik sikisma opsiyonunun
PRIMI oldugu bulunmustu. Burada ayni sey bir FAKTOR icin: olculen beta
bir kusur degil, kitabin kazandigi yerin imzasi.

================================================================
3) ASIL BULGU: YOL ZATEN IYI - YOL DUZEYINDE MUDAHALE EDILEMEZ
================================================================
Gunluk getiriler kumelenmiyor, hafifce GERI DONUYOR:

  otokorelasyon  lag1 -0,0514   lag2 -0,0186   lag3 -0,0645   lag5 +0,0468
  (beyaz gurultu 2-sigma bandi: +-0,052)
  varyans orani  k=2: 0,949  k=5: 0,873  k=10: 0,888  k=21: 0,899
  |getiri| lag1 +0,2257 (oynaklik kumelenmesi normal)

Hepsi 1'in ALTINDA: cok gunluk varyans, gunluk varyanin k katindan AZ.

GERCEK DUSUS vs AYNI GUNLERIN RASTGELE SIRALANMASI (20.000 ornek):

  gercek maks dusus                            -%14,54
  karistirilmis: ort -%18,13 · p50 -%17,52 · p5 -%25,38 · p95 -%13,09
  gercek dususun karistirilmis dagilimdaki yuzdeligi: **%84**

Yani ayni gunlerin %84'luk bir kismi, GERCEKLESEN siradan DAHA DERIN
bir dusus uretiyordu. **Yolda kaldirilacak olumsuz bir kumelenme yok -
tersine, gerceklesen sira sansli tarafta.**

BU, BIR AILENIN TAMAMINI MEKANIK OLARAK KAPATIR. Stop (191), takip eden
cikis (235), merdiven (235), prime gore nakde cekme (239), dusus
hedge'i (243) - hepsi YOLA mudahale etmeye calisiyor. Ama yol zaten
rastgeleden iyi; mudahale edilecek bir sey yok. Ampirik olarak hepsi
reddedilmisti; artik SEBEBI olculu.

================================================================
4) CANLI ICIN IKI YENI SAYI
================================================================
(a) ILERIYE DONUK DUSUS BEKLENTISI. 1 yillik pencerede:

  olcum                          ort      p50      p5       p1
  GERCEK kayan pencereler    -%10,89  -%10,73  -%14,54  -%14,54
  KARISTIRILMIS (ayni dagilim) -%12,94  -%12,25  -%20,55  -%25,30

Gerceklesen pencereler iyimser. **Ayni getiri dagiliminin durust 1 yil
p5'i -%20,55, p1'i -%25,30.** Madde 148.2 "canlida -%20..-%30 bekle"
diyordu; bu, o uyarinin kitabin KENDI dagilimindan cikarilmis hali.

(b) ALARM ESIKLERININ YANLIS TETIKLEME OLASILIGI (saglikli bot):

  esik              gercek pencerelerde   karistirilmista
  INCELE  -%18            %0,0                %11,1
  DURDUR  -%23            %0,0                 %2,2

Ikisi de kabul edilebilir: "incele" yilda ~%11 bosa cagirir (incelemek
durdurmak degil), "durdur" ~45 yilda bir bosa tetikler. Madde 231/233'un
esikleri BAGIMSIZ bir yontemle dogrulandi.

Kosum: python3 arastirma_risk_atfi.py
"""

FAKTOR = {   # model: (R2, [(ad, beta, t)])
    "BTC": (0.0000, [("BTC", +0.0009, +0.1)]),
    "ALT": (0.0061, [("ALT", +0.0252, +3.0)]),
    "BTC + (ALT-BTC)": (0.0127, [("BTC", -0.0138, -0.9),
                                 ("ALT-BTC", +0.0533, +4.4)]),
}

KOSULLU_BETA = {"dususte (182 gun)": (+0.0916, +2.4, 0.030),
                "diger (1322 gun)": (-0.0100, -0.7, 0.0003)}

HEDGE = {   # beta: (getiri, Sharpe, 22-24, 25-26, dusus, esit-risk)
    0.000: (112.5, 2.942, 2.794, 3.147, -14.5, 112.5),
    0.053: (96.8, 2.671, 2.585, 2.797, -14.9, 93.8),
    0.100: (83.8, 2.401, 2.375, 2.452, -17.4, 66.5),
    0.250: (46.9, 1.466, 1.626, 1.292, -28.0, 21.8),
}

BAGIMSIZLIK = {"lag1": -0.0514, "lag2": -0.0186, "lag3": -0.0645,
               "lag5": +0.0468, "lag10": +0.0126}
VARYANS_ORANI = {2: 0.949, 5: 0.873, 10: 0.888, 21: 0.899}
ABS_OTOKOR = {"lag1": +0.2257, "lag5": +0.0837, "lag10": +0.0407}

KARISTIRMA = {   # tam ornek (4,6 yil)
    "gercek": -14.54, "ort": -18.13, "p50": -17.52, "p5": -25.38,
    "p95": -13.09, "yuzdelik": 84.0,
}

BIR_YIL = {   # (ort, p50, p5, p1)
    "gercek": (-10.89, -10.73, -14.54, -14.54),
    "karistirilmis": (-12.94, -12.25, -20.55, -25.30),
}

YANLIS_TETIK = {"INCELE -%18": (0.0, 11.1), "DURDUR -%23": (0.0, 2.2)}


if __name__ == "__main__":
    print("MADDE 243 - RISKIN KAYNAGI\n")
    print("1) FAKTOR ATFI")
    for ad, (r2, bs) in FAKTOR.items():
        print("  %-18s R2=%.4f" % (ad, r2), end="")
        for b_ad, b, t in bs:
            print("  | %s %+.4f (t %+.1f)" % (b_ad, b, t), end="")
        print()
    print("  -> varyansin %98,7'si IDIYOSINKRATIK; hedge edilecek faktor YOK")
    print("\n  kosullu beta:")
    for ad, (b, t, r2) in KOSULLU_BETA.items():
        print("    %-22s beta %+.4f (t %+.1f)  R2 %.4f" % (ad, b, t, r2))
    print("\n2) ALT-BTC HEDGE'I - her oranda KOTU")
    print("  %-10s%9s%8s%8s%8s%8s%12s" % ("beta", "getiri", "Sharpe", "22-24",
                                          "25-26", "dusus", "esit-risk"))
    for b, t in HEDGE.items():
        im = "  <- kontrol" if b == 0 else ""
        print("  %-10.3f%+9.1f%8.3f%8.3f%8.3f%8.1f%+12.1f%s" % (b, *t, im))
    print("  -> maruziyet SIZINTI degil GELIR kaynagi (madde 191'in 2. ornegi)")
    print("\n3) YOL ZATEN IYI")
    print("  otokorelasyon: " + "  ".join("%s %+.4f" % kv for kv in BAGIMSIZLIK.items()))
    print("  varyans orani: " + "  ".join("k=%d %.3f" % kv for kv in VARYANS_ORANI.items()))
    print("  gercek dusus %.2f · karistirilmis p50 %.2f · YUZDELIK %%%.0f"
          % (KARISTIRMA["gercek"], KARISTIRMA["p50"], KARISTIRMA["yuzdelik"]))
    print("  -> yolda kaldirilacak olumsuz kumelenme YOK; yol duzeyinde")
    print("     mudahale eden butun aile (stop/takip/merdiven/nakde cekme) KAPALI")
    print("\n4) CANLI ICIN")
    print("  %-16s%9s%9s%9s%9s" % ("1 yillik dusus", "ort", "p50", "p5", "p1"))
    for ad, t in BIR_YIL.items():
        print("  %-16s%9.2f%9.2f%9.2f%9.2f" % (ad, *t))
    print("\n  alarm yanlis tetikleme (saglikli bot):")
    for ad, (g, k) in YANLIS_TETIK.items():
        print("    %-14s gercek %%%.1f · karistirilmis %%%.1f" % (ad, g, k))
