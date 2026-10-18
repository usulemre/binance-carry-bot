"""MADDE 259: REJIM SINIFI BIR KACIS KAPISI DEGIL - sicil tarandi, yalniz 239 gecti.

Madde 258 "REJIM ARACI - KOSULLU" sinifini kurdu ve sart 1'in bu sinifi
YAPISAL olarak reddettigini gosterdi. Boyle bir sinif kurulunca akla hemen
bir risk gelir: **her reddedilmis aday icin "ama belki rejim aracidir"
denebilir mi?** Bu tur o riski kapatiyor: sicil makineyle tarandi ve sinif
bir ESIKLE sinirlandi.

================================================================
1) SICIL TARAMASI: TEK ALT DONEMDE KAYBEDENLER
================================================================
Bir aday rejim araci ADAYI olmak icin sart 1'i YALNIZCA TEK alt donemde
kaybetmis olmali (iki donemde de kaybediyorsa duz RED). On makine-okunur
tablo tarandi (63 aday):

  sart 1'i GECEN            :  9
  TEK DONEMDE kaybeden      : 16   <- rejim araci ADAYLARI
  iki donemde de kaybeden   : 38   <- duz RED, rejim tartismasi YOK

16 adayin dagilimi:
  madde 239 (prim-olcekli brut)        9 aday  -> madde 258'de olculdu
  madde 244 (ust trader kontrarian)    4 aday  -> BU TURDA olculdu
  madde 242 MERKEZ / 246 KONTROL       3 satir -> KONTROLUN KENDISI
                                                  (baska tablolarda kayitli,
                                                   aday degil - tarama artefakti)

Yani tartisilacak YENI aile TEK: madde 244'un kolu. Ve imzasi 239'un
aynisi - dort payda da 22-24 iyi, 25-26 kotu.

================================================================
2) KOL YENIDEN KURULDU VE DOGRULANDI
================================================================
Madde 244'un kol dokumleri ayri kaydedilmemisti, ama bir kol tanim geregi
sermaye karisimidir: w x (ust trader kitabi) + (1-w) x (kontrol). Ikisinin
gunluk serisi de diskte duruyordu, kol yeniden kuruldu ve madde 244'un
KENDI tablosuna karsi dogrulandi:

  pay    YENIDEN KURULAN                    KAYITLI (madde 244)
  0,00   +112,3  2,939  2,789  3,147  -14,5 | +112,5  2,942  2,794  3,147  -14,5
  0,10   +110,9  2,962  2,834  3,145  -13,2 | +111,0  2,965  2,838  3,145  -13,2
  0,20   +109,3  2,965  2,860  3,123  -13,0 | +109,5  2,967  2,865  3,123  -13,0
  0,30   +107,7  2,947  2,866  3,081  -13,1 | +107,9  2,949  2,870  3,081  -13,1
  0,50   +104,3  2,847  2,807  2,942  -13,7 | +104,4  2,849  2,810  2,942  -13,7

BIREBIR (her satir 0,2 puan ve 0,005 Sharpe icinde). Rekonstruksiyon
gecerli; uzerine olcum yapilabilir.
(Ust trader kontrarian TEK BASINA: +%94,2 / Sharpe 2,350 / dusus -%20,8.)

================================================================
3) REJIM AYRIMI: AYNI IMZA, AMA ESIGIN ALTINDA
================================================================
Madde 258'in protokolu aynen uygulandi (esli blok bootstrap, esit riskte,
3.000 ornek, kirilma 2025-01-01). PLASEBO olarak kolun ISARET CEVRILMIS
hali kullanildi (kontrarian yerine IZLEYEN - ayni veri, ters yon):

  kol                 TAM ORNEK        DUSUK PRIM        YUKSEK PRIM
  kontrarian %20   +8,7  P %65,1   +11,7  P **%76,8**   -6,1  P %36,3
  kontrarian %30   +8,7  P %58,2   +16,6  P   %72,9    -12,9  P %29,6
  PLASEBO izleyen  -1,0  P %48,1    -5,5  P   %36,0    +11,8  P %59,2

OKUNUSU:
(a) IMZA AYNI: dusuk primde pozitif, yuksek primde negatif - tipki 239.
(b) PLASEBO TEMIZ: isaret cevrilince dusuk primde -5,5 puan (P %36,0),
    yani YON gercek, mekanik degil.
(c) AMA ESIGE ULASMIYOR: en iyisi %76,8, madde 255'in %80 cubugunun
    ALTINDA. Kiyas icin madde 239'un ayni penceredeki degerleri:
    **%92,3 / %94,4 / %93,8**. Yani 244'un kolu ayni yonde ama kabaca
    DORTTE BIR gucte.

KARAR: madde 244 "REJIM ARACI - KOSULLU" sinifina GIRMEZ. Duz RED olarak
kalir. Tetik yazilmaz.

================================================================
4) ASIL BULGU: SINIF BIR KACIS KAPISI DEGIL
================================================================
Bu turun degeri 244'un sonucunda degil, SINIFIN SINANMASINDA:

  * sart 1'i tek donemde kaybetmek, rejim araci olmak icin YETMEZ -
    yalnizca ADAY olmak icin yeter (16 aday);
  * ADAYLIKTAN SINIFA gecmek icin o rejimde bootstrap %80'i gecmeli
    (239: evet; 244: hayir);
  * ve PLASEBO ayni pencerede esigin altinda kalmali (ikisinde de evet).

Uc kapidan gecen tek aile madde 239'dur. Yani madde 258'in actigi kapi
genis degil: 63 adayin 3'u (yalniz 239'un olculmus varyantlari).

**BUNUN ONEMI:** "rejim araci" etiketi, reddedilmis her adayi diri
tutmanin yolu olabilirdi - projenin 259 turluk disiplininin en kolay
asilacak yeri. Esik bunu engelliyor ve bu tur onu SINAYARAK gosterdi,
iddia ederek degil.

================================================================
5) BIR REFINE: MADDE 241'IN KOL ESITSIZLIGI GEREKLI, YETERLI DEGIL
================================================================
Madde 241 bir kol eleme esitsizligi kurmustu: Sh_kol > Sh_kitap x korelasyon.
Madde 244 bu esitsizligi projede OLCULEN EN GENIS MARJLA geciyordu
(+0,284). Ve yine reddediliyor - hem tam ornekte (P %64,5) hem rejim
ayriminda (P %76,8).

  **Kol esitsizligi GEREKLI kosuldur, YETERLI DEGILDIR.** Bir kol onu
  gecse bile esit riskte para getirmeyebilir; esitsizlik kolun kitaba
  "matematiksel olarak ekleyebilir olmasini" soyler, "ekledigini"
  soylemez. Karar yine bootstrap'in.

HATA KAYDI YOK. Tarama artefakti (242 MERKEZ / 246 KONTROL satirlari)
kontrolun baska tablolara kaydedilmis kopyalariydi; aday sanilmadi,
kaynagina bakilarak ayikladi.

Kosum: python3 arastirma_rejim_taramasi.py
"""

# --- 1) tarama ---
TARAMA = {"sart1 gecen": 9, "tek donemde kaybeden": 16, "iki donemde kaybeden": 38}
TEK_DONEM_DAGILIM = {"239 prim-olcekli brut": 9, "244 ust trader kontrarian": 4,
                     "242/246 kontrolun kendisi (artefakt)": 3}

# --- 2) kol rekonstruksiyonu: pay -> (yeniden, kayitli) ---
# her biri (yillik, Sharpe, 22-24, 25-26, dusus)
REKONSTRUKSIYON = {
    0.00: ((112.3, 2.939, 2.789, 3.147, -14.5), (112.5, 2.942, 2.794, 3.147, -14.5)),
    0.10: ((110.9, 2.962, 2.834, 3.145, -13.2), (111.0, 2.965, 2.838, 3.145, -13.2)),
    0.20: ((109.3, 2.965, 2.860, 3.123, -13.0), (109.5, 2.967, 2.865, 3.123, -13.0)),
    0.30: ((107.7, 2.947, 2.866, 3.081, -13.1), (107.9, 2.949, 2.870, 3.081, -13.1)),
    0.50: ((104.3, 2.847, 2.807, 2.942, -13.7), (104.4, 2.849, 2.810, 2.942, -13.7)),
}
TT_TEK_BASINA = (94.2, 2.350, 2.331, 2.424, -20.8)

# --- 3) rejim ayrimi: kol -> {rejim: (d esit-risk, P(>0))} ---
REJIM = {
    "kontrarian %20": {"tam": (+8.7, 65.1), "dusuk": (+11.7, 76.8), "yuksek": (-6.1, 36.3)},
    "kontrarian %30": {"tam": (+8.7, 58.2), "dusuk": (+16.6, 72.9), "yuksek": (-12.9, 29.6)},
    "PLASEBO izleyen %20": {"tam": (-1.0, 48.1), "dusuk": (-5.5, 36.0), "yuksek": (+11.8, 59.2)},
}
BOOT_ESIK = 80.0
MADDE_239_DUSUK = {"e1.0 ust2.0": 92.3, "e0.5 ref180": 94.4, "e1.0 ref365": 93.8}

UC_KAPI = ("(1) sart 1'i YALNIZCA tek alt donemde kaybetmek -> ADAYLIK; "
           "(2) o rejimde bootstrap P>%80 -> SINIF; "
           "(3) PLASEBO ayni pencerede esigin ALTINDA -> dogrulama.")
SINIF_DAR = ("63 adaydan 3'u (yalniz madde 239'un olculmus varyantlari). "
             "Rejim etiketi reddedilmis her adayi diri tutmanin yolu DEGIL.")
KOL_ESITSIZLIGI = ("Madde 241'in kol esitsizligi (Sh_kol > Sh_kitap x korelasyon) "
                   "GEREKLI kosuldur, YETERLI DEGILDIR: madde 244 onu projede "
                   "olculen EN GENIS marjla (+0,284) geciyor ve yine reddediliyor "
                   "- hem tam ornekte (P %64,5) hem rejim ayriminda (P %76,8).")


def rekonstruksiyon_dogrulandi(tol_getiri=0.5, tol_sharpe=0.01):
    """Yeniden kurulan kol, madde 244'un kaydiyla ortusuyor mu?"""
    return all(abs(y[0] - k[0]) < tol_getiri and abs(y[1] - k[1]) < tol_sharpe
               for y, k in REKONSTRUKSIYON.values())


def ayni_imza_mi(kol="kontrarian %20"):
    """Dusuk primde pozitif, yuksek primde negatif mi? (239'un imzasi)"""
    r = REJIM[kol]
    return r["dusuk"][0] > 0 and r["yuksek"][0] < 0


def esige_ulasiyor_mu(kol="kontrarian %20"):
    """Dusuk primde %80 cubugunu geciyor mu?"""
    return REJIM[kol]["dusuk"][1] > BOOT_ESIK


def plasebo_temiz_mi():
    """Isaret cevrilince dusuk primde esigin ALTINDA mi?"""
    return REJIM["PLASEBO izleyen %20"]["dusuk"][1] < BOOT_ESIK


def sinifa_giren():
    """Uc kapidan gecen aileler."""
    g = [a for a, p in MADDE_239_DUSUK.items() if p > BOOT_ESIK]
    if esige_ulasiyor_mu():
        g.append("244 kontrarian")
    return sorted(g)


if __name__ == "__main__":
    print("MADDE 259 - REJIM SINIFININ SINANMASI\n")
    print("1) SICIL TARAMASI (10 makine-okunur tablo, 63 aday)")
    for a, n in TARAMA.items():
        print("  %-26s%4d" % (a, n))
    print("\n  TEK DONEMDE kaybedenlerin dagilimi:")
    for a, n in TEK_DONEM_DAGILIM.items():
        print("    %-40s%3d" % (a, n))
    print("  -> tartisilacak YENI aile: madde 244'un kolu")

    print("\n2) KOL YENIDEN KURULDU (w x ust trader + (1-w) x kontrol)")
    print("  %-6s%-38s%s" % ("pay", "YENIDEN KURULAN", "KAYITLI (madde 244)"))
    for w, (y, k) in REKONSTRUKSIYON.items():
        print("  %-6.2f%+8.1f%7.3f%7.3f%7.3f%7.1f   |%+8.1f%7.3f%7.3f%7.3f%7.1f"
              % (w, y[0], y[1], y[2], y[3], y[4], k[0], k[1], k[2], k[3], k[4]))
    print("  dogrulandi mi? %s"
          % ("EVET - birebir" if rekonstruksiyon_dogrulandi() else "HAYIR"))
    print("  (ust trader kontrarian TEK BASINA: %+.1f%% / Sh %.3f / dusus %.1f%%)"
          % (TT_TEK_BASINA[0], TT_TEK_BASINA[1], TT_TEK_BASINA[4]))

    print("\n3) REJIM AYRIMI (3.000 ornek, esit riskte, kirilma 2025-01-01)")
    print("  %-22s%18s%18s%18s" % ("kol", "TAM ORNEK", "DUSUK PRIM", "YUKSEK PRIM"))
    for a, r in REJIM.items():
        print("  %-22s%+10.1f P%%%4.1f%+10.1f P%%%4.1f%+10.1f P%%%4.1f"
              % (a, r["tam"][0], r["tam"][1], r["dusuk"][0], r["dusuk"][1],
                 r["yuksek"][0], r["yuksek"][1]))
    print("\n  ayni imza mi? %s" % ("EVET" if ayni_imza_mi() else "HAYIR"))
    print("  plasebo temiz mi? %s" % ("EVET" if plasebo_temiz_mi() else "HAYIR"))
    print("  %%%.0f esigine ulasiyor mu? %s"
          % (BOOT_ESIK, "EVET" if esige_ulasiyor_mu() else "HAYIR - en iyisi %76,8"))
    print("  kiyas, madde 239 ayni pencerede: %s"
          % ", ".join("%s %%%.1f" % (a, p) for a, p in MADDE_239_DUSUK.items()))
    print("\n  KARAR: madde 244 sinifa GIRMEZ, duz RED olarak kalir.")

    print("\n4) SINIF BIR KACIS KAPISI DEGIL")
    print("  UC KAPI: %s" % UC_KAPI)
    print("  sinifa giren: %s" % ", ".join(sinifa_giren()))
    print("  %s" % SINIF_DAR)

    print("\n5) REFINE: %s" % KOL_ESITSIZLIGI)
    print("\nAYAR DEGISMEDI.")
