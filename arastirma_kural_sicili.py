"""MADDE 248: KURALIN KENDI SICILI - sart 1 her seyi engelliyor, sart 4 hicbir sey.

Madde 245 sart 4'un gerekcesini (likidasyon, "modellenmeyen tehlike")
OLCMUSTU ve ben turun sonunda sunu yazdim: "sart 4 revizyonu madde
239'un prim brutunu ve madde 244'un kolunu yeniden degerlendirmeye
acar." **BU YANLISTI.** Madde 248 kuralin kendi sicilini makineyle
cikardi; ikisi de sart 1'den dusuyor, sart 4 revizyonu onlara
dokunmuyor.

================================================================
1) ADAY SICILI: HANGI SART ENGELLEDI?
================================================================
Araclar veri olarak yazildigi icin sicil makineyle okunabilir:

  aday                          kald.   kirilan sart
  239 prim brutu e0,5           1,058   iki donemde Sharpe
  239 prim brutu e1,0           1,031   iki donemde Sharpe
  239 prim brutu ust2,0         1,131   iki donemde Sharpe
  240 rezerv esigi %1,8         1,010   esit riskte getiri
  240 rezerv esigi %2,0         1,020   esit riskte getiri
  240 rezerv esigi %2,2         1,020   esit riskte getiri
  242 en uzak kose              1,240   iki donemde Sharpe
  244 ust trader kolu %10       1,110   iki donemde Sharpe
  244 ust trader kolu %20       1,130   iki donemde Sharpe
  244 ust trader kolu %30       1,120   iki donemde Sharpe
  247 delist ufku 30 (canli)    1,000   YOK (kurali gecer)

**SART 4 HICBIR ADAYDA BELIRLEYICI OY OLMADI.** Onu kiran her aday
sart 1'i de (ya da sart 3'u) kiriyordu. Yalnizca sart 3/4'ten dusen tek
grup madde 240'in rezerv esikleri ve onlarin esit-risk kazanci **+0,3
puan** - yani hic. Sart 4'u gevsetmenin olculmus odulu: SIFIRA YAKIN.

================================================================
2) O ZAMAN ASIL SORU: SART 1 IYI KALIBRE MI?
================================================================
Sart 1 iki alt donemde de Sharpe'in KESIN iyilesmesini ister. Bir
adayin gercek farki SIFIR ise bu sart ne siklikta gecer?

ESLI BLOK BOOTSTRAP ILE (4.000 ornek, kontrolun kendi gunleri yeniden
orneklenerek "ayni dagilimdan yeni bir gerceklesme" uretildi):

  alt donem   ort fark   std      P(>0)
  22-24        +0,134   0,602     %58,6
  25-26        -0,211   0,725     %37,8
  iki fark arasi korelasyon: **-0,003** (bagimsiz)

  SART 1'I GECME OLASILIGI (ikisi de >0): **%22,2**
  -> YANLIS RED ORANI: **%77,8**
  (bagimsiz yazi-tura olsa 0,5^2 = %25 gecer / %75 red olurdu)

BAGIMSIZ AMPIRIK TEYIT - %5 rastgele sembol dusurmeyle kurulmus sekiz
ESDEGER kitap (farkli tohumlar):

  tohum   getiri   Sharpe   22-24   25-26   sart 1
  1      +%111,2   2,931   2,693   3,251    RED
  2      +%112,1   2,920   2,850   3,031    RED
  3       +%94,7   2,722   2,655   2,817    RED
  4      +%109,2   2,864   2,805   2,958    RED
  5      +%109,9   2,909   2,824   3,034    RED
  6      +%108,5   2,871   2,804   2,975    RED
  7      +%114,1   2,990   2,769   3,289    RED
  8      +%102,1   2,774   2,672   2,918    RED

  **8/8 RED.** (Bu plasebo hafif KOTUMSER: %5 sembol dusurmek bazen iyi
  coinleri de atiyor - tohum 3'te 18 puan. Yani gercek yanlis-red orani
  %77,8 civari, 8/8 ise sansin kotu tarafi.)

================================================================
3) BU NEYI DEGISTIRIR, NEYI DEGISTIRMEZ
================================================================
DEGISTIRMEZ - kural gevsetilmez. Cunku reddedilen adaylari BOOTSTRAP da
bagimsiz olarak "ayirt edilemez" buldu:

  aday                       bootstrap d esit-risk   P(>0)
  239 prim brutu e0,5            +22,2 puan          %79,0
  244 ust trader kolu %20         +8,5 puan          %64,5
  235 merdiven %20x1/2            +3,3 puan          %58,5
  242 en uzak kose                -2,7 puan          %46,0

Yani sart 1'in sertligi OLCULEBILIR bir sey maliyet etmedi: her vakada
ikinci, bagimsiz kapi da ayni cevabi verdi. **Asil kapi bootstrap.**

DEGISTIRIR - rapor dili. "RED" demek "daha kotu" demek DEGIL; "iki
donemde birden GOSTERILEMEDI" demek. Proje artik bunun sayisini
biliyor: esdeger bir aday bes denemeden yalnizca birinde gecer.

HATA KAYDI (iki tane): (1) gecen tur sart 4 icin yazdigim yeniden
degerlendirme onerisi yanlisti - duzeltildi. (2) Bu turun ilk plasebo
tasarimi da gecersizdi: `FAZ_KAY` tum takvimi kaydiriyor ama kosum
zaten 15 dilim kaymasini (0,2,...,28 bar) ortaladigi icin FAZ_KAY=2'nin
dilim kumesi FAZ_KAY=0'inkiyle MODULO AYNI - yani 10 bagimsiz aday
degil 2 kitap uretmisim. Alt donem Sharpe'inin alti ciftte birebir
3,147 cikmasi bunu ele verdi; oran yayinlanmadan once yakalandi.

Kosum: python3 arastirma_kural_sicili.py
"""

SICIL = {   # aday: (kaldirac, kirilan sart)
    "239 prim brutu e0,5": (1.058, "iki donemde Sharpe"),
    "239 prim brutu e1,0": (1.031, "iki donemde Sharpe"),
    "239 prim brutu ust2,0": (1.131, "iki donemde Sharpe"),
    "240 rezerv esigi %1,8": (1.010, "esit riskte getiri"),
    "240 rezerv esigi %2,0": (1.020, "esit riskte getiri"),
    "240 rezerv esigi %2,2": (1.020, "esit riskte getiri"),
    "242 en uzak kose": (1.240, "iki donemde Sharpe"),
    "244 ust trader kolu %10": (1.110, "iki donemde Sharpe"),
    "244 ust trader kolu %20": (1.130, "iki donemde Sharpe"),
    "244 ust trader kolu %30": (1.120, "iki donemde Sharpe"),
    "247 delist ufku 30 (canli)": (1.000, "YOK (gecer)"),
}

ALT_DONEM_BOOT = {   # donem: (ort fark, std, P(>0) %)
    "22-24": (+0.134, 0.602, 58.6), "25-26": (-0.211, 0.725, 37.8),
}
KORELASYON = -0.003
SART1_GECME = 22.2          # %
YANLIS_RED = 100 - SART1_GECME

PLASEBO = {   # tohum: (getiri, Sharpe, 22-24, 25-26, sart1 gecti mi)
    1: (111.2, 2.931, 2.693, 3.251, False), 2: (112.1, 2.920, 2.850, 3.031, False),
    3: (94.7, 2.722, 2.655, 2.817, False), 4: (109.2, 2.864, 2.805, 2.958, False),
    5: (109.9, 2.909, 2.824, 3.034, False), 6: (108.5, 2.871, 2.804, 2.975, False),
    7: (114.1, 2.990, 2.769, 3.289, False), 8: (102.1, 2.774, 2.672, 2.918, False),
}

BOOTSTRAP_SICILI = {   # aday: (d esit-risk puan, P(>0) %)
    "239 prim brutu e0,5": (+22.2, 79.0), "244 ust trader kolu %20": (+8.5, 64.5),
    "235 merdiven %20x1/2": (+3.3, 58.5), "242 en uzak kose": (-2.7, 46.0),
}


def sart4_belirleyici_mi():
    """Sart 4'un TEK BASINA engelledigi aday var mi?"""
    return [a for a, (_, s) in SICIL.items() if s == "kaldiraç gerektirmiyor"]


if __name__ == "__main__":
    print("MADDE 248 - KURALIN KENDI SICILI\n")
    print("1) HANGI SART ENGELLEDI?")
    print("  %-30s%8s  %s" % ("aday", "kald.", "kirilan sart"))
    for a, (k, s) in SICIL.items():
        print("  %-30s%8.3f  %s" % (a, k, s))
    print("\n  sart 4'un TEK BASINA engelledigi aday: %s"
          % (sart4_belirleyici_mi() or "YOK"))
    print("  -> sart 4'u gevsetmenin olculmus odulu SIFIRA YAKIN")
    print("     (yalniz sart 3/4'ten dusen grup: madde 240 rezerv esigi, +0,3 puan)")
    print("\n2) SART 1 IYI KALIBRE MI? (gercek farki SIFIR olan aday)")
    print("  %-10s%11s%8s%9s" % ("alt donem", "ort fark", "std", "P(>0)"))
    for d, (m, s, p) in ALT_DONEM_BOOT.items():
        print("  %-10s%+11.3f%8.3f%8.1f%%" % (d, m, s, p))
    print("  iki fark arasi korelasyon: %+.3f (bagimsiz)" % KORELASYON)
    print("  SART 1'I GECME: %%%.1f  ->  YANLIS RED: %%%.1f"
          % (SART1_GECME, YANLIS_RED))
    print("  (analitik: 0,5^2 = %25 gecer / %75 red)")
    print("\n  AMPIRIK TEYIT - %5 sembol dusurmeyle 8 ESDEGER kitap")
    gecen = sum(1 for t in PLASEBO.values() if t[4])
    print("  %-8s%9s%8s%8s%8s  %s" % ("tohum", "getiri", "Sharpe", "22-24",
                                      "25-26", "sart1"))
    for t, v in PLASEBO.items():
        print("  %-8d%+9.1f%8.3f%8.3f%8.3f  %s"
              % (t, v[0], v[1], v[2], v[3], "OK" if v[4] else "RED"))
    print("  -> %d/%d gecti" % (gecen, len(PLASEBO)))
    print("\n3) BU KURALI GEVSETMEYI HAKLI KILMAZ: bootstrap da ayni dedi")
    print("  %-28s%14s%9s" % ("aday", "d esit-risk", "P(>0)"))
    for a, (de, p) in BOOTSTRAP_SICILI.items():
        print("  %-28s%+14.1f%8.1f%%" % (a, de, p))
    print("\n  DEGISEN: rapor dili. 'RED' = 'daha kotu' DEGIL,")
    print("  'iki donemde birden GOSTERILEMEDI'. Sayisi artik biliniyor.")
