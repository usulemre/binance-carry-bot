"""MADDE 256: KABUL DENETIMI - kitabin KENDI kabullerini bugunun kuraliyla sina.

Madde 255 cok bakis duzeltmesini kurala yazdi: bir turda k varyant
denenirse, hepsi ETKISIZ olsa bile en az birinin sart 1'i gecme olasiligi
1-(1-0,222)^k - k=8'de **%86,6**. O yasa yazildiktan sonra kacinilmaz bir
soru dogdu: **kitabin BUGUN canlida duran katmanlari hangi delille kabul
edildi?**

Kritik tarih: on kayitli karar kurali **madde 212**. Esli blok bootstrap
kapisi daha da sonra (222-248) olgunlasti. Yani kârin cogunu tasiyan
katmanlar - kalabalik havuzu (148), firsat rezervi (156), kar al (178),
uc hareket elemesi (196) - **kural VAR OLMADAN** kabul edildi.

Madde 238 bu katmanlarin EKLEMELI katkisini olcmustu, ama kendi yasasi
"katmanlar TOPLAMSAL DEGIL" diyor. Dogru denetim araci CIKARMA testidir:
tam kitaptan katmani tek tek cikar, ve kurali IKI YONDE kos -
"katman bugun onerilse gecer mi?" ve "cikarma onerilse gecer mi?".

================================================================
1) CIKARMA TABLOSU (GUNLUK baz, tam kitap = +%112,3 / 2,939 / -%14,5)
================================================================
  katman CIKARILINCA   kabul  yeniden   yillik  Sharpe   22-24  dusus  esit-risk
  kalabalik havuzu       148      224    +74,7   2,009   2,246  -20,9      +47,2
  emir akisi             117      228   +109,4   2,886   2,774  -14,5     +109,4
  uc hareket elemesi     196        -   +115,9   2,859   2,747  -14,1     +120,7
  firsat rezervi         156      225   +127,6   2,879   2,753  -16,9     +103,1
  kar al (TP)            178      227    +92,7   2,197   2,355  -19,8      +61,7

================================================================
2) IKI YONLU KARAR + BOOTSTRAP (4.000 ornek, esit riskte)
================================================================
  katman             KATMAN bugun onerilse       CIKARMA onerilse
  kalabalik havuzu   GECER   d+197,3  P %99,7    RED  d -69,4  P %0,4
  emir akisi         GECER   d  +1,2  P %57,7    RED  d  -0,0  P %41,9
  uc hareket elemesi RED(s3) d +12,5  P %66,8    RED  d  -7,8  P %33,6
  firsat rezervi     RED(s4) d +13,3  P %91,0    RED  d  -9,5  P  %9,4
  kar al (TP)        GECER   d +94,8  P %95,8    RED  d -46,8  P %3,8

MADDE 255'IN ESIGI (bootstrap P>%80) UYGULANINCA DORT SINIF CIKIYOR:

  (I) SAGLAM GEREKCELI - kalabalik havuzu (P %99,7) ve kar al (P %95,8).
      Ikisi de ezici. Havuz ayrica madde 253'te bagimsiz olarak dogrulandi:
      olcutunu OI ile degistirmek kitabi +%112,3'ten +%44,0'a dusuruyor.
      Kar al ise madde 214'un kâr motoru.

  (II) NOKTA TAHMINI UYARIYOR AMA BOOTSTRAP DESTEKLIYOR - firsat rezervi.
      Sart 4 (kaldirac) onerilse veto ederdi, ama bootstrap P **%91,0**
      ile esigin UZERINDE. Ve madde 225'te kural altinda yeniden acilip
      gecmisti. KALIR - ve bu, sart 4'un nokta tahminine fazla duyarli
      oldugunun ikinci kaniti (birincisi madde 248'in sicili).

  (III) OLCULEBILIR HICBIR SEY GETIRMIYOR, AMA BEDAVA - emir akisi.
      Bootstrap +1,2 puan P %57,7; cikarmanin bootstrap'i -0,0 puan
      P %41,9. Yani iki yon de YAZI TURA: katman olculebilir sifir.
      Madde 228 bunu zaten "+0,04 Sharpe" diye tespit etmisti.
      **BENIM ONERIM BURADA COKTU:** "o zaman kaldirip canliyi
      sadelestirelim" demek uzereydim; `carry_bot.py`'yi okudum ve madde
      228'in bu bagi KOPARDIGINI gordum - kline verisi
      `AKIS_AGIRLIK>0 VEYA DONUK_ESIK>0` ise toplaniyor ve donuk filtresi
      (0,10) ACIK. Yani akis agirligini kapatmak **SIFIR API cagrisi**
      tasarruf eder. Katman bedava; kaldirmanin hicbir faydasi yok.
      KALIR. (Madde 228'in oneminin olculmus hali: bir katmanin
      "degersiz" olmasi onu KALDIRMA gerekcesi degildir - maliyeti de
      sorulur.)

  (IV) IKINCI OLCULEBILIR SIFIR - UC HAREKET ELEMESI (madde 196).
      Bugun onerilse sart 3'ten RED (esit riskte +%120,7 elemesiz vs
      +%112,3 elemeli); cikarma onerilse sart 1'den RED (bootstrap
      P %33,6). Iki yon de %80 esiginin ALTINDA.

      **BENIM HATAM VE DUZELTMESI:** bu turu "projenin hic yeniden
      acilmamis tek katmani" diye kurmustum. YANLISTI. `carry_bot.py`'deki
      docstring'in ILK SATIRI "MADDE 236 - YENIDEN ACILDI" diyor ve
      kapali hâli orada OLCULMUS: +%116,2 / Sharpe 3,017 / esit-risk
      +%120,9 (motor basinda) ve REDDEDILMIS. Ben yeniden acma
      defterinin gosterdigi 241'e bakip (o madde kullanicinin ±%40
      KOLUNU olcmustu, katmani degil - madde 240'in belgeledigi yapisal
      sinirin tam ornegi) kendi sozlugume "yeniden acilmadi" yazmisim.
      Katmanin denetim gecmisi TAM.

      KATKIM YINE DE VAR: madde 236'nin bootstrap'i yoktu. Bu tur onu
      ekledi (kalma P %66,8 / cikarma P %33,6) ve 236'nin nokta tahminli
      reddini bagimsiz olarak teyit etti.

      GORUNUR CELISKI VE COZUMU: tablonun esit-risk sutunu elemesiz
      kitabi +%120,7 gosteriyor (tam kitap +%112,3), yani "cikarmak daha
      iyi"; bootstrap ise elemeli kitabi +12,5 puan onde gosteriyor.
      Ceviri: sutun TEK bir normalizasyon kullaniyor (tam kitabin
      -%14,5'i), bootstrap ise HER ornekte o ornegin KENDI kontrol
      dususune normalize ediyor. Madde 248/255'e gore karar mercii
      bootstraptir.

      VE 236 MEKANIZMAYI DA ACIKLAMIS: onceki hareket bir ZARAR secicisi
      degil, bir KUYRUK secicisi - oynaklik ve onceki hareket IKI
      KUYRUKTA DA yuksek (en kotu 250 bacakta +%2,12, en iyi 250'de
      +%0,76, tumunde +%0,08). Bu niteliklere dayanan her filtre zarari
      keserken kâri da kesiyor. Katman ne fayda ne zarar getiriyor cunku
      kestigi sey simetrik.

================================================================
3) DEGISEN / DEGISMEYEN
================================================================
DEGISMEYEN: ayar. Bes katmanin hicbiri degistirilmedi. Ikisi ezici
gerekceli, biri bootstrap destekli, biri bedava, biri zayif ama
cikarilmasi da gerekcesiz.

DEGISEN: SICIL. Uc hareket elemesi artik "projenin en zayif gerekceli
canli katmani" olarak kayitli ve YENIDEN ACMA KOSULU var (asagi).
Ayrica yeniden acma defterine girdi - orada "-" satiri kalmamali.

YENIDEN ACMA KOSULU (uc hareket elemesi): canli ilk ceyrek bittiginde,
VEYA kitabin yuzeyinde kabul edilen bir degisiklik oldugunda yeniden
olculur; ve o olcumde karar MERCII bootstrap olur, nokta tahmini degil.

Kosum: python3 arastirma_kabul_denetimi.py
"""

KURAL_MADDESI = 212          # on kayitli kural bu maddede kuruldu
BOOT_ESIK = 80.0             # madde 255: delil esigi P(>0) > %80

TAM_KITAP = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)

# katman: (kabul maddesi, yeniden acilma maddesi veya None,
#          cikarilinca: yillik, Sharpe, 22-24, dusus, esit-risk)
CIKARMA = {
    "kalabalik havuzu": (148, 224, 74.7, 2.009, 2.246, -20.9, 47.2),
    "emir akisi": (117, 228, 109.4, 2.886, 2.774, -14.5, 109.4),
    "uc hareket elemesi": (196, 236, 115.9, 2.859, 2.747, -14.1, 120.7),
    "firsat rezervi": (156, 225, 127.6, 2.879, 2.753, -16.9, 103.1),
    "kar al (TP)": (178, 227, 92.7, 2.197, 2.355, -19.8, 61.7),
}
# katman: (katman_gecer, katman_boot_d, katman_boot_P,
#          cikarma_gecer, cikarma_boot_d, cikarma_boot_P, kirilan_sart)
KARAR = {
    "kalabalik havuzu": (True, +197.3, 99.7, False, -69.4, 0.4, None),
    "emir akisi": (True, +1.2, 57.7, False, -0.0, 41.9, None),
    "uc hareket elemesi": (False, +12.5, 66.8, False, -7.8, 33.6,
                           "esit riskte getiri"),
    "firsat rezervi": (False, +13.3, 91.0, False, -9.5, 9.4,
                       "kaldirac gerekmesin"),
    "kar al (TP)": (True, +94.8, 95.8, False, -46.8, 3.8, None),
}
SINIF = {
    "kalabalik havuzu": "I  saglam gerekceli",
    "kar al (TP)": "I  saglam gerekceli",
    "firsat rezervi": "II bootstrap destekli (nokta tahmini uyariyor)",
    "emir akisi": "III olculebilir sifir AMA bedava",
    "uc hareket elemesi": "III olculebilir sifir - ve madde 236 NEDENINI aciklamis",
}
# madde 228'in kopardigi bag: akis kapatilsa bile kline verisi toplanir
AKIS_BEDAVA_SEBEBI = ("carry_bot.py: veri `AKIS_AGIRLIK>0 VEYA DONUK_ESIK>0` "
                      "ise toplanir; DONUK_ESIK=0,10 acik -> akisi kapatmak "
                      "SIFIR API cagrisi tasarruf eder (madde 228 bu bagi "
                      "bilerek kopardi)")
YENIDEN_ACMA_KOSULU = {
    "uc hareket elemesi": ("madde 236 + 256'da iki kez olculdu; bir sonraki "
                           "olcum ancak canli ilk ceyrek bittiginde anlamli "
                           "olur - karar mercii BOOTSTRAP"),
    "emir akisi": ("madde 228 + 256; bedava oldugu icin kaldirma gerekcesi "
                   "yok, DONUK_ESIK kapatilirsa yeniden sorulur"),
}
DERS = ("Iki ders. (1) Bir katmanin 'olculebilir degeri yok' olmasi onu "
        "KALDIRMA gerekcesi degildir - MALIYETI de sorulur; emir akisi sifir "
        "getiri sagliyor ama sifir maliyetle, cunku verisi baska bir filtre "
        "icin zaten toplaniyor. (2) Bir katmanin denetim gecmisini YENIDEN "
        "ACMA DEFTERINDEN okumak yetmez - defter birlikte taranan "
        "parametrelerde yanlis madde gosterebilir (madde 240'in belgeledigi "
        "sinir); DOCSTRING'IN KENDISI okunur.")


def kuraldan_once_kabul():
    """Kural (madde 212) yoktan once kabul edilmis katmanlar."""
    return sorted(a for a, v in CIKARMA.items() if v[0] < KURAL_MADDESI)


def hic_yeniden_acilmamis():
    """Kabul edildiginden beri hic yeniden olculmemis katmanlar."""
    return sorted(a for a, v in CIKARMA.items() if v[1] is None)


def bootstrap_destekli():
    """madde 255'in esigini (P>%80) gecen katmanlar."""
    return sorted(a for a, v in KARAR.items() if v[2] > BOOT_ESIK)


def gerekcesiz():
    """Iki yonu de esigin ALTINDA kalan katmanlar."""
    return sorted(a for a, v in KARAR.items()
                  if v[2] <= BOOT_ESIK and v[5] <= BOOT_ESIK)


if __name__ == "__main__":
    print("MADDE 256 - KABUL DENETIMI\n")
    print("on kayitli kural: madde %d · bootstrap delil esigi: P>%%%.0f\n"
          % (KURAL_MADDESI, BOOT_ESIK))
    print("TAM KITAP: %+.1f%%  Sh %.3f  dusus %.1f%%\n"
          % (TAM_KITAP["yillik"], TAM_KITAP["sharpe"], TAM_KITAP["dusus"]))
    print("1) CIKARMA TABLOSU")
    print("  %-20s%7s%9s%9s%8s%8s%8s%10s"
          % ("katman CIKARILINCA", "kabul", "yeniden", "yillik", "Sharpe",
             "22-24", "dusus", "esit-risk"))
    for a, v in CIKARMA.items():
        print("  %-20s%7d%9s%+9.1f%8.3f%8.3f%8.1f%+10.1f"
              % (a, v[0], str(v[1] or "-"), v[2], v[3], v[4], v[5], v[6]))

    print("\n2) IKI YONLU KARAR + BOOTSTRAP")
    print("  %-20s%-28s%s" % ("katman", "KATMAN bugun onerilse", "CIKARMA onerilse"))
    for a, v in KARAR.items():
        k1 = "GECER" if v[0] else "RED(%s)" % (v[6] or "")[:14]
        k2 = "GECER" if v[3] else "RED"
        print("  %-20s%-16s d%+7.1f P%%%4.1f   %-5s d%+7.1f P%%%4.1f"
              % (a, k1, v[1], v[2], k2, v[4], v[5]))

    print("\n3) SINIFLAR (madde 255'in %.0f%% esigi uygulanarak)" % BOOT_ESIK)
    for a, s in SINIF.items():
        print("  %-20s%s" % (a, s))
    print("\n  kuraldan (madde %d) ONCE kabul edilmis: %s"
          % (KURAL_MADDESI, ", ".join(kuraldan_once_kabul())))
    print("  hic yeniden acilmamis            : %s"
          % (", ".join(hic_yeniden_acilmamis()) or "YOK"))
    print("  bootstrap DESTEKLI (P>%%%.0f)      : %s"
          % (BOOT_ESIK, ", ".join(bootstrap_destekli())))
    print("  GEREKCESIZ (iki yon de esik alti): %s"
          % (", ".join(gerekcesiz()) or "YOK"))

    print("\n  emir akisi neden KALIR:\n    %s" % AKIS_BEDAVA_SEBEBI)
    print("\n  YENIDEN ACMA KOSULU:")
    for a, k in YENIDEN_ACMA_KOSULU.items():
        print("    %s: %s" % (a, k))
    print("\nDERS\n  %s" % DERS)
    print("\nAYAR DEGISMEDI - bes katmanin hicbiri degistirilmedi.")
