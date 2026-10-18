"""MADDE 258: PRIM BRUTU BIR REJIM ARACI - ve sart 1 bunu YAPISAL OLARAK reddediyor.

Madde 257 projeye zorunlu bir test getirdi: getiriyi artiran her aday icin
kontrolu ADAYIN KENDI DUSUSUNE kaldiraclayip karsilastir. O test yazildigi
icin geriye donuk uygulanmasi gerekti - ve sicilin seklini degistirdi.

================================================================
1) KALDIRAC YASASI SICILE UYGULANDI: 9/19
================================================================
Getiriyi artirmis 19 aday icin kontrol, adayin kendi dususune
kaldiraclandi (gercek gunluk seriyle, interpolasyon YOK):

  aday                      yillik  dusus   kald.kontrol    FARK
  239 prim e1.0 ust2.0      +171,9  -15,2        +119,5   **+52,4**  GECER
  239 prim e1.0 alt0.5      +138,9  -13,6        +101,9     +37,0   GECER
  239 prim e0.5 ref180      +137,3  -13,3         +99,4     +37,9   GECER
  239 prim e1.0 ref180      +137,3  -13,6        +101,9     +35,4   GECER
  239 prim e1.5 ref180      +134,4  -13,9        +105,4     +29,0   GECER
  239 prim e1.0 ref365      +144,8  -15,0        +117,1     +27,7   GECER
  239 PLASEBO karis         +115,5  -13,5        +101,6     +13,9   (gecer!)
  239 prim e1.0 ref90       +133,3  -15,8        +126,1      +7,2   (plasebo alti)
  257 agirlik~(oyn+0,02)    +132,9  -15,8        +126,4      +6,5   (plasebo alti)
  255 harman w=0,25         +112,6  -14,6        +113,0      -0,4   kaldirac onde
  257 agirlik~oynaklik      +145,2  -19,0        +166,2     -21,0   kaldirac onde
  250 ort.dusurme (6 varyant)  ...             -34,7..-248,5  kaldirac onde

YASA GERCEKTEN AYIRIYOR: madde 250'nin tamami ve madde 257'nin ana adayi
kaldiracin ALTINDA kaliyor; madde 239'un ailesi USTUNDE. Ama plasebo da
+13,9 ile geciyor - yani yasa TEK BASINA yeterli degil: bir adayin
marji, kendi PLASEBOSUNUN marjini asmali. Bu olcute gore yalnizca
239'un ilk alti varyanti ayrisiyor; ref90 ve 257'nin taban 0,02'si
plasebonun altinda, yani gurultu.

================================================================
2) EN GUCLU ADAYIN HIC KOSULMAMIS KAPISI
================================================================
Madde 239'un en guclu varyanti (`ust2.0`) icin bootstrap HIC KOSULMAMISTI
(yalnizca `e0.5 ref180` icin kosulmus: +22,2 puan P %79,0). Kosumlari
diskte duruyordu; kosuldu:

  aday            yillik  Sharpe   22-24   25-26  dusus  esit-risk  bootstrap
  KONTROL         +112,3   2,939   2,789   3,147  -14,5     +112,3        -
  e1.0 ust2.0     +171,7   3,033   3,163   3,006  -15,2     +160,6  +25,3 P %69,3
  e0.5 ref180     +137,1   3,058   3,065   3,115  -13,3     +156,4  +21,6 P %79,1
  e1.0 ref365     +144,6   2,993   3,113   3,026  -15,0     +138,3  +19,4 P %67,4
  PLASEBO karis   +115,4   2,945   2,809   3,134  -13,5     +128,0   +0,5 P %53,6
  PLASEBO ters    +116,1   2,803   2,728   2,909  -18,3      +84,7  -14,1 P %18,8

BORU HATTI TEMIZ: plasebonun bootstrap'i +0,5 puan, P %53,6 - tam yazi
tura. Yani gercek adaylarin +19..+25 puani MEKANIK DEGIL.
AMA hicbiri %80 esigini gecmiyor; en iyisi %79,1 ile KIL PAYI altinda.

================================================================
3) DESEN: HEPSI AYNI ALT DONEMDE KAYBEDIYOR
================================================================
Yukaridaki tabloda gozden kacmayacak bir duzen var: UC varyantin da
22-24 Sharpe'i kontrolden BELIRGIN iyi (3,06-3,16 vs 2,789) ve 25-26
Sharpe'i HAFIF kotu (3,006-3,115 vs 3,147). Rastgele bir red boyle
duzenli olmaz. Madde 231'in rejim ayrimi (kirilma 2025-01-01) test
edildi - esli blok bootstrap, esit riskte, 3.000 ornek:

  aday            DUSUK PRIM (896 gun)      YUKSEK PRIM (608 gun)
  e1.0 ust2.0     **+69,3 puan  P %92,3**     -11,5 puan  P %34,9
  e0.5 ref180     **+34,3 puan  P %94,4**      -2,9 puan  P %43,9
  e1.0 ref365     **+53,9 puan  P %93,8**     -13,3 puan  P %20,0
  PLASEBO karis       +4,9 puan  P %68,1      -13,4 puan  P %26,8

**DUSUK PRIM REJIMINDE UCU DE %80 ESIGINI ACIK ARA GECIYOR; PLASEBO
%68,1'DE KALIYOR.** Yuksek prim rejiminde (SU AN BURADAYIZ) ucu de
negatif.

MEKANIZMA: prim-olcekli brut, kesitsel funding dagilimi genisken brutu
buyutur. Prim ZATEN yuksekken (2025Q1+) bu surekli kaldiracli olmak
demektir - oynaklik ekler, secim kalitesi eklemez. Prim INCEYKEN
(2022-24) ise dogru anlarda buyur, yani asil isini yapar.

================================================================
4) BUNUN ANLAMI: KABUL DEGIL, HAZIR CEVAP
================================================================
BUGUN: REDDEDILIR. Yuksek prim rejimindeyiz ve bu rejimde aday zarar
veriyor. Ayar DEGISMEDI.

AMA PROJE ARTIK EN BUYUK TESPIT EDILMIS RISKINE HAZIR BIR CEVABA SAHIP.
Madde 231 soyle demisti: "prim gerilerse risk 'kenar yok' degil 'getiri
+%95'." Madde 258 bunu tamamliyor: **o senaryo gerceklesirse, esit riskte
+34..+69 puan geri kazandiran OLCULMUS bir arac var.**

TETIK (somut): `arastirma_rejim.py`'nin rejim ayrimi DUSUK PRIM'i
gosterdiginde - yani en uc long adayinin gunluk funding medyani madde
231'in -%0,49/gun bandina dondugunde - bu aday YENIDEN OLCULUR ve
karar bootstrap'a birakilir. Once olcum, sonra karar; rejim tahminine
dayanarak simdiden acilmaz.

SINIRI DURUSTCE: dusuk prim rejimi TEK bir tarihsel epizottur (896 gun,
2022-07..2024-12). Etki o donemin kendine ozgu kosullarina bagli olabilir
ve plasebonun ayni pencerede %68,1 almasi tamamen ihmal edilebilir
degildir. Bu yuzden tetik "otomatik ac" degil, "yeniden olc"tur.

================================================================
5) KURALIN REFINE EDILMESI: SART 1'IN UCUNCU YUZU
================================================================
Madde 248 sart 1'in YANLIS RED oranini olctu (%77,8, null adaylar icin).
Madde 255 aynasini ekledi (cok bakis: k=8'de %86,6 yanlis kabul riski).
Madde 258 ucuncu yuzunu buluyor:

  **SART 1, REJIM ARACLARINI YAPISAL OLARAK REDDEDER.**
  Sart 1 iki alt donemde birden iyilesme ister. Ama o iki alt donem
  madde 231'e gore IKI AYRI REJIMDIR. Bir aday yalnizca bir rejimde
  calisiyorsa - ki bir rejim araci TANIM GEREGI oyledir - sart 1'i
  gecmesi IMKANSIZDIR. Bu bir kalibrasyon hatasi degil, kuralin
  tasariminin dogal sonucu.

  O yuzden kurala bir AYIRIM eklendi: bir aday sart 1'i yalnizca TEK
  alt donemde kaybediyor VE kaybettigi donemde isareti mekanizmayla
  aciklanabiliyorsa, "RED" degil **"REJIM ARACI - KOSULLU"** olarak
  siniflanir ve tetigi yazilir. Kabul edilmez, ama CÖPE DE ATILMAZ.

HATA KAYDI YOK. Ama bir ISLETME kusuru duzeltildi: `arastirma_rejim.py`
`/tmp/g19E_%d.pkl`'i okuyordu - yani SON kosumun dokumunu. Madde 252'de
bu beni bir kez yanlis yonlendirmisti (arac +%64,5 gosteriyordu).
Artik once sabitlenmis kontrol dokumunu (`/tmp/kontrol_E%d.pkl`) ariyor.

Kosum: python3 arastirma_rejim_araci.py
"""

# --- 1) kaldirac yasasi sicile uygulandi ---
# aday: (madde, yillik, dusus, kaldiraclanmis kontrol getirisi, fark)
YASA_SICILI = {
    "239 prim e1.0 ust2.0": (239, 171.9, -15.2, 119.5, +52.4),
    "239 prim e1.0 alt0.5": (239, 138.9, -13.6, 101.9, +37.0),
    "239 prim e0.5 ref180": (239, 137.3, -13.3, 99.4, +37.9),
    "239 prim e1.0 ref180": (239, 137.3, -13.6, 101.9, +35.4),
    "239 prim e1.5 ref180": (239, 134.4, -13.9, 105.4, +29.0),
    "239 prim e1.0 ref365": (239, 144.8, -15.0, 117.1, +27.7),
    "239 PLASEBO karis": (239, 115.5, -13.5, 101.6, +13.9),
    "239 prim e1.0 ref90": (239, 133.3, -15.8, 126.1, +7.2),
    "257 agirlik~(oyn+0,02)": (257, 132.9, -15.8, 126.4, +6.5),
    "255 harman w=0,25": (255, 112.6, -14.6, 113.0, -0.4),
    "257 agirlik~oynaklik": (257, 145.2, -19.0, 166.2, -21.0),
    "250 ort.dusurme e30 p0.5": (250, 115.8, -17.8, 150.5, -34.7),
    "250 ort.dusurme e20 p0.5": (250, 117.6, -19.6, 174.4, -56.8),
    "250 ort.dusurme e15 p0.5": (250, 122.0, -20.5, 187.1, -65.1),
    "250 ort.dusurme e10 p0.5": (250, 130.1, -21.4, 200.4, -70.3),
    "250 ort.dusurme e15 p0.5x2": (250, 126.9, -25.3, 265.0, -138.1),
    "250 ort.dusurme e15 p1.0": (250, 131.6, -26.1, 279.8, -148.2),
    "250 ort.dusurme e20 p1.0x2": (250, 125.6, -30.6, 374.1, -248.5),
}
PLASEBO_MARJI = +13.9        # yasanin NULL referansi

# --- 2) tam ornek bootstrap (hic kosulmamisti) ---
KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)
TAM_ORNEK = {   # aday: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk, boot_d, boot_P)
    "e1.0 ust2.0": (171.7, 3.033, 3.163, 3.006, -15.2, 160.6, +25.3, 69.3),
    "e0.5 ref180": (137.1, 3.058, 3.065, 3.115, -13.3, 156.4, +21.6, 79.1),
    "e1.0 ref365": (144.6, 2.993, 3.113, 3.026, -15.0, 138.3, +19.4, 67.4),
    "PLASEBO karis": (115.4, 2.945, 2.809, 3.134, -13.5, 128.0, +0.5, 53.6),
    "PLASEBO ters": (116.1, 2.803, 2.728, 2.909, -18.3, 84.7, -14.1, 18.8),
}

# --- 3) rejim ayrimi (madde 231'in kirilmasi) ---
REJIM_KIRILMA = "2025-01-01"
REJIM_BOOT = {   # aday: {rejim: (d esit-risk, P(>0), gun)}
    "e1.0 ust2.0": {"dusuk": (+69.3, 92.3, 896), "yuksek": (-11.5, 34.9, 608)},
    "e0.5 ref180": {"dusuk": (+34.3, 94.4, 896), "yuksek": (-2.9, 43.9, 608)},
    "e1.0 ref365": {"dusuk": (+53.9, 93.8, 896), "yuksek": (-13.3, 20.0, 608)},
    "PLASEBO karis": {"dusuk": (+4.9, 68.1, 896), "yuksek": (-13.4, 26.8, 608)},
}
BOOT_ESIK = 80.0             # madde 255

MEKANIZMA = ("Prim-olcekli brut, kesitsel funding dagilimi GENISKEN brutu "
             "buyutur. Prim ZATEN yuksekken (2025Q1+) bu surekli kaldiracli "
             "olmak demektir - oynaklik ekler, secim kalitesi eklemez. Prim "
             "INCEYKEN dogru anlarda buyur, yani asil isini yapar.")
TETIK = ("arastirma_rejim.py'nin ayrimi DUSUK PRIM'i gosterdiginde (en uc long "
         "adayinin gunluk funding medyani madde 231'in -%0,49/gun bandina "
         "dondugunde) aday YENIDEN OLCULUR; karar bootstrap'a birakilir. "
         "Rejim TAHMINIYLE simdiden acilmaz.")
SINIR = ("Dusuk prim rejimi TEK bir tarihsel epizot (896 gun, 2022-07..2024-12); "
         "etki o donemin kosullarina bagli olabilir ve plasebonun ayni pencerede "
         "%68,1 almasi ihmal edilebilir degil. Tetik 'otomatik ac' DEGIL, "
         "'yeniden olc'.")
SART1_UCUNCU_YUZ = ("SART 1, REJIM ARACLARINI YAPISAL OLARAK REDDEDER: iki alt "
                    "donem madde 231'e gore IKI AYRI REJIM oldugu icin, yalnizca "
                    "bir rejimde calisan bir adayin sart 1'i gecmesi imkansizdir. "
                    "Kalibrasyon hatasi degil, tasarimin dogal sonucu.")
YENI_SINIF = ("Bir aday sart 1'i YALNIZCA TEK alt donemde kaybediyor VE o donemde "
              "isareti mekanizmayla aciklanabiliyorsa: 'RED' degil 'REJIM ARACI - "
              "KOSULLU'. Kabul edilmez, ama cope de atilmaz; tetigi yazilir.")


def yasayi_gecen():
    """257'nin kaldirac yasasini gecen adaylar (fark > 0)."""
    return sorted((a for a, v in YASA_SICILI.items() if v[4] > 0),
                  key=lambda a: -YASA_SICILI[a][4])


def plaseboyu_asan():
    """Marji, 239'un karistirilmis plasebosunun marjini ASAN adaylar."""
    return sorted((a for a, v in YASA_SICILI.items()
                   if v[4] > PLASEBO_MARJI and "PLASEBO" not in a),
                  key=lambda a: -YASA_SICILI[a][4])


def tam_ornekte_gecen():
    """Tam ornekte %80 bootstrap esigini gecen aday var mi?"""
    return [a for a, v in TAM_ORNEK.items()
            if "PLASEBO" not in a and v[7] > BOOT_ESIK]


def dusuk_primde_gecen():
    """DUSUK PRIM rejiminde esigi gecen gercek adaylar."""
    return sorted(a for a, r in REJIM_BOOT.items()
                  if "PLASEBO" not in a and r["dusuk"][1] > BOOT_ESIK)


def rejim_araci_mi(aday):
    """Bir rejimde esigi geciyor, otekinde negatif mi?"""
    r = REJIM_BOOT.get(aday)
    return bool(r and r["dusuk"][1] > BOOT_ESIK and r["yuksek"][0] < 0)


def plasebo_ayrisiyor_mu():
    """Dusuk primde plasebo esigin ALTINDA mi? (boru hatti temiz mi)"""
    return REJIM_BOOT["PLASEBO karis"]["dusuk"][1] < BOOT_ESIK


if __name__ == "__main__":
    print("MADDE 258 - PRIM BRUTU BIR REJIM ARACI\n")
    print("1) MADDE 257'NIN KALDIRAC YASASI SICILE UYGULANDI")
    print("  %-28s%5s%8s%8s%14s%9s"
          % ("aday", "mad", "yillik", "dusus", "kald.kontrol", "FARK"))
    for a, v in YASA_SICILI.items():
        print("  %-28s%5d%+8.1f%8.1f%+14.1f%+9.1f"
              % (a, v[0], v[1], v[2], v[3], v[4]))
    print("\n  yasayi gecen: %d / %d" % (len(yasayi_gecen()), len(YASA_SICILI)))
    print("  PLASEBO marji: %+.1f puan -> bu esigi ASAN gercek adaylar:"
          % PLASEBO_MARJI)
    for a in plaseboyu_asan():
        print("    %-28s%+8.1f" % (a, YASA_SICILI[a][4]))

    print("\n2) TAM ORNEK BOOTSTRAP (en guclu aday icin HIC kosulmamisti)")
    print("  %-16s%8s%8s%8s%8s%8s%10s%9s%8s"
          % ("aday", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk",
             "boot d", "P(>0)"))
    print("  %-16s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f%9s%8s"
          % ("KONTROL", KONTROL["yillik"], KONTROL["sharpe"], KONTROL["erken"],
             KONTROL["gec"], KONTROL["dusus"], KONTROL["yillik"], "-", "-"))
    for a, v in TAM_ORNEK.items():
        print("  %-16s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f%+9.1f%7.1f%%"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]))
    print("\n  tam ornekte %%%.0f esigini gecen: %s"
          % (BOOT_ESIK, tam_ornekte_gecen() or "YOK (en iyi %79,1 - kil payi alti)"))

    print("\n3) REJIM AYRIMI (kirilma %s, 3.000 ornek, esit riskte)" % REJIM_KIRILMA)
    print("  %-16s%26s%26s" % ("aday", "DUSUK PRIM (896 gun)", "YUKSEK PRIM (608 gun)"))
    for a, r in REJIM_BOOT.items():
        print("  %-16s%+16.1f  P%%%5.1f%+16.1f  P%%%5.1f"
              % (a, r["dusuk"][0], r["dusuk"][1], r["yuksek"][0], r["yuksek"][1]))
    print("\n  dusuk primde esigi gecen: %s" % ", ".join(dusuk_primde_gecen()))
    print("  plasebo ayrisiyor mu (boru hatti temiz)? %s"
          % ("EVET" if plasebo_ayrisiyor_mu() else "HAYIR"))
    print("  en guclu aday REJIM ARACI mi? %s"
          % ("EVET" if rejim_araci_mi("e1.0 ust2.0") else "HAYIR"))
    print("\n  MEKANIZMA: %s" % MEKANIZMA)

    print("\n4) KABUL DEGIL, HAZIR CEVAP")
    print("  BUGUN: REDDEDILIR (yuksek prim rejimindeyiz). AYAR DEGISMEDI.")
    print("  TETIK: %s" % TETIK)
    print("  SINIR: %s" % SINIR)

    print("\n5) SART 1'IN UCUNCU YUZU\n  %s" % SART1_UCUNCU_YUZ)
    print("\n  YENI SINIF: %s" % YENI_SINIF)
