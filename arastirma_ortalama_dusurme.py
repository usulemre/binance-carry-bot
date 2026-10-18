"""MADDE 250: ORTALAMA DUSURME (kullanicinin onerisi) - REDDEDILDI, ve bu
kez bootstrap "ayirt edilemez" demedi, **DAHA KOTU** dedi.

Kullanicinin onerisi: "parcali alim yapip ortalama dusurme taktigi nasil
olur - dusecek diye girdi, yukseldi; yukseldigi icin yukseldigi noktadan
tekrar dusecek diye girse zarari kapatmaya calissa".

Mekanizma motora bayrak olarak eklendi (`g33.py`: EK_ESIK / EK_PAY /
EK_SAYI): bir bacak aleyhte EK_ESIK kadar giderse ozgun bacak
agirliginin EK_PAY kati EKLENIR ve giris AGIRLIKLI ORTALAMAYA cekilir -
yani TP seviyesi fiyata YAKINLASIR, kullanicinin tarif ettigi "zarari
kapatma" tam olarak bu. Ekleme bar kapanisinda yapilir (motorun
AYNI/TERS/DOLDUR bloklariyla ayni konvansiyon, look-ahead yok).
PARITE: EK_ESIK=0 ile kontrol birebir tekrar etti (+%112,3 / Sh 3,10 /
dusus -14,5).

================================================================
1) DOZ MERDIVENI - GETIRI ARTIYOR, AMA BU KALDIRAC
================================================================
Kontrol: +%112,3 · Sharpe 2,939 · 22-24 2,789 · 25-26 3,147 · -%14,5

  aday                        yillik  Sharpe   22-24   25-26   dusus  esit-risk  kald.
  esik %10 pay 0,5 ekleme 1  +130,1   2,672   2,410   3,023  -21,4     +76,3   0,666
  esik %15 pay 0,5 ekleme 1  +122,0   2,650   2,416   2,965  -20,5     +76,5   0,699
  esik %20 pay 0,5 ekleme 1  +117,6   2,644   2,431   2,931  -19,6     +78,2   0,731
  esik %30 pay 0,5 ekleme 1  +115,8   2,705   2,520   2,956  -17,8     +88,0   0,812
  esik %15 pay 1,0 ekleme 1  +131,6   2,401   2,117   2,777  -26,1     +60,2   0,540
  esik %15 pay 0,5 ekleme 2  +126,9   2,419   2,158   2,768  -25,3     +60,6   0,559
  esik %20 pay 1,0 ekleme 2  +125,6   2,050   1,805   2,375  -30,6     +48,1   0,455

**YEDI YAPILANDIRMANIN HEPSI SART 1'DEN DUSTU** (iki donemde Sharpe).
Merdiven KUSURSUZ MONOTON: her agresiflestirme (esigi dusurmek, payi
buyutmek, ekleme sayisini artirmak) getiriyi DE dususu DE artirdi ve
Sharpe'i DUSURDU. Bu, bir kenarin degil KALDIRACIN imzasidir.

ASIL SAYI ESIT-RISK SUTUNU: kontrolun kendi dususune (-%14,5)
olceklenince adaylar +%48 ile +%88 arasi veriyor - yani **ayni riskte
24 ile 64 puan DAHA AZ**. Kaldirac sutunu 1'in ALTINDA (0,455-0,812):
aday kitaplar o kadar daha riskli ki esitlemek icin KALDIRAC INDIRMEK
gerekiyor. Sart 4 burada bile belirleyici degil - sart 1 onden dusuruyor.

================================================================
2) BOOTSTRAP: BU KEZ "AYIRT EDILEMEZ" DEGIL, "DAHA KOTU"
================================================================
En YUMUSAK aday (esik %30, pay 0,5, tek ekleme) kontrole karsi, esli
blok bootstrap (4.000 ornek, 20 gunluk bloklar, esit riskte):

  ort fark **-19,5 puan**  std 11,6  **P(>0) %5,3**
  p5 -38,5 · p25 -26,8 · p50 -19,7 · p75 -12,2 · p95 +0,3

BU, PROJENIN SICILINDE YENI BIR TUR SONUC. Madde 248'in sicili
reddedilen adaylarin bootstrap'ta "ayirt edilemez" ciktigini
gostermisti (239: +22,2 puan P %79,0 · 244: +8,5 P %64,5 · 242: -2,7
P %46,0). Ortalama dusurme ise **pozitif olarak kotu**: P(>0) yalnizca
%5,3. Yani "gosterilemedi" degil, "gosterildi - zarari".

================================================================
3) NEDEN: VARSAYIM YANLIS. ALEYHTE GIDEN GERI DONMUYOR.
================================================================
Onerinin kalbinde bir ortalamaya donus varsayimi var: "yukseldigi icin
tekrar dusecek". Bunu dogrudan olctum - kitabin TUTTUGU bacaklarda,
bacak aleyhte X% gittikten SONRA onumuzdeki 5 gunde bacak yonunde ne
oluyor (86.940 gozlem):

  durum                     ort      medyan        n
  KOSULSUZ (tum barlar)   -%0,25     -%0,50   86.940
  aleyhte >=%10 sonrasi   -%1,09     -%0,76   12.814
  aleyhte >=%15 sonrasi   -%1,74     -%0,55    7.403
  aleyhte >=%20 sonrasi   -%3,07     -%1,11    4.607
  aleyhte >=%30 sonrasi   -%6,18     -%2,42    2.063

**MONOTON VE TEK YONLU: bacak ne kadar derin aleyhteyse onumuzdeki 5
gun o kadar KOTU.** Ortalamaya donus olsaydi bu satirlar kosulsuzun
USTUNE cikardi; tersi oluyor. Yani ortalama dusurme, ileri getirinin EN
KOTU oldugu yere EN COK sermayeyi koyuyor. Doz merdivenindeki her sayi
bunun aritmetik sonucu.

================================================================
4) MADDE 191 ILE BIRLESEN YENI YASA
================================================================
Ilk bakista bu bulgu STOP'u destekler gorunur (aleyhte giden daha da
kotuye gidiyorsa kes). Ama madde 191 stopu olcmus ve REDDETMISTI:
kesilen sey maliyet degil, **odemenin bileti** - TP hasadinin primi.
Celiski yok; ikisi birlesince kesin bir yasa veriyor:

  **ALEYHTE GIDEN BACAGIN BOYUTUNA DOKUNULMAZ.**
  kesilmez (madde 191: kesilen sey TP hasadinin bileti)
  eklenmez (madde 250: ileri getiri aleyhlik derinligiyle kotulesir)

Iki yon de olculdu, iki yon de reddedildi - ve FARKLI sebeplerle. Pozisyon
boyutu kararinin verilecegi tek yer GIRIS ani; tutma suresince boyut
sabittir. Madde 243'un "yol duzeyinde mudahale imkansiz" bulgusunun
boyut eksenindeki karsiligi budur.

HATA KAYDI: bayragin ilk yamasi `g33.py`'de YANLIS GIRINTIYE oturdu -
DOLDUR blogu benim `if EK_ESIK>0:` blogunun ICINE girdi, yani DOLDUR
yalnizca ortalama-dusurme acikken calisacakti ve `yon` tanimsiz
kalabilirdi. `ast.parse` gectigi icin sessizdi; kontrolde DOLDUR=0
oldugu icin PARITE TESTI DE YAKALAMAZDI. Girintiyi elle okuyarak
bulundu ve blok `cik` blogunun DISINA tasindi.

Kosum: python3 arastirma_ortalama_dusurme.py
"""

KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)

# aday: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk getiri, kaldirac, kirilan sart)
MERDIVEN = {
    "esik %10 pay 0,5 ekleme 1": (130.1, 2.672, 2.410, 3.023, -21.4, 76.3, 0.666),
    "esik %15 pay 0,5 ekleme 1": (122.0, 2.650, 2.416, 2.965, -20.5, 76.5, 0.699),
    "esik %20 pay 0,5 ekleme 1": (117.6, 2.644, 2.431, 2.931, -19.6, 78.2, 0.731),
    "esik %30 pay 0,5 ekleme 1": (115.8, 2.705, 2.520, 2.956, -17.8, 88.0, 0.812),
    "esik %15 pay 1,0 ekleme 1": (131.6, 2.401, 2.117, 2.777, -26.1, 60.2, 0.540),
    "esik %15 pay 0,5 ekleme 2": (126.9, 2.419, 2.158, 2.768, -25.3, 60.6, 0.559),
    "esik %20 pay 1,0 ekleme 2": (125.6, 2.050, 1.805, 2.375, -30.6, 48.1, 0.455),
}
KIRILAN_SART = "iki donemde Sharpe"      # YEDISININ HEPSI

BOOTSTRAP = dict(aday="esik %30 pay 0,5 ekleme 1", ort=-19.5, std=11.6, p_pozitif=5.3,
                 p5=-38.5, p25=-26.8, p50=-19.7, p75=-12.2, p95=0.3, ornek=4000)
# karsilastirma: madde 248'in sicilinde reddedilen adaylar "ayirt edilemez"di
ONCEKI_REDLER = {"239 prim brutu e0,5": 79.0, "244 ust trader kolu %20": 64.5,
                 "235 merdiven %20x1/2": 58.5, "242 en uzak kose": 46.0}

# aleyhte X% gittikten SONRA bacak yonunde ileri 5 gun: (ort, medyan, n)
ILERI_GETIRI = {
    "kosulsuz": (-0.25, -0.50, 86940),
    "aleyhte >=%10": (-1.09, -0.76, 12814),
    "aleyhte >=%15": (-1.74, -0.55, 7403),
    "aleyhte >=%20": (-3.07, -1.11, 4607),
    "aleyhte >=%30": (-6.18, -2.42, 2063),
}

YASA = ("ALEYHTE GIDEN BACAGIN BOYUTUNA DOKUNULMAZ: kesilmez (madde 191 - "
        "kesilen sey TP hasadinin bileti), eklenmez (madde 250 - ileri getiri "
        "aleyhlik derinligiyle monoton kotulesir). Boyut karari yalnizca GIRISTE.")


def monoton_kotulesme():
    """Ileri getiri aleyhlik derinligiyle gercekten monoton mu kotulesiyor?"""
    sira = ["kosulsuz", "aleyhte >=%10", "aleyhte >=%15", "aleyhte >=%20",
            "aleyhte >=%30"]
    o = [ILERI_GETIRI[a][0] for a in sira]
    return all(o[i] > o[i + 1] for i in range(len(o) - 1))


def hicbiri_gecmedi():
    """Merdivende sart 1'i gecen aday var mi? (Sharpe iki donemde de artmali)"""
    return [a for a, v in MERDIVEN.items()
            if v[2] > KONTROL["erken"] and v[3] > KONTROL["gec"]]


def esit_riskte_hepsi_kotu():
    """Esit riskte adaylarin hepsi kontrolden kotu mu?"""
    return all(v[5] < KONTROL["yillik"] for v in MERDIVEN.values())


if __name__ == "__main__":
    print("MADDE 250 - ORTALAMA DUSURME (parcali ekleme)\n")
    print("KONTROL: %+.1f%%  Sh %.3f  (22-24 %.3f / 25-26 %.3f)  dusus %.1f%%\n"
          % (KONTROL["yillik"], KONTROL["sharpe"], KONTROL["erken"],
             KONTROL["gec"], KONTROL["dusus"]))
    print("1) DOZ MERDIVENI")
    print("  %-28s%8s%8s%8s%8s%8s%11s%8s"
          % ("aday", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk", "kald."))
    for a, v in MERDIVEN.items():
        print("  %-28s%+8.1f%8.3f%8.3f%8.3f%8.1f%+11.1f%8.3f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5], v[6]))
    print("\n  sart 1'i gecen aday: %s" % (hicbiri_gecmedi() or "YOK (7/7 RED)"))
    print("  esit riskte hepsi kontrolden kotu mu? %s"
          % ("EVET" if esit_riskte_hepsi_kotu() else "HAYIR"))
    print("  -> getiri artisi KENAR degil KALDIRAC (kald. sutunu 1'in ALTINDA)")

    print("\n2) ESLI BLOK BOOTSTRAP (%s, %d ornek)"
          % (BOOTSTRAP["aday"], BOOTSTRAP["ornek"]))
    print("  esit riskte fark: ort %+.1f puan  std %.1f  **P(>0) %%%.1f**"
          % (BOOTSTRAP["ort"], BOOTSTRAP["std"], BOOTSTRAP["p_pozitif"]))
    print("  p5 %+.1f · p50 %+.1f · p95 %+.1f"
          % (BOOTSTRAP["p5"], BOOTSTRAP["p50"], BOOTSTRAP["p95"]))
    print("\n  KARSILASTIRMA - madde 248'in reddettikleri AYIRT EDILEMEZDI:")
    for a, p in ONCEKI_REDLER.items():
        print("    %-28s P(>0) %%%.1f" % (a, p))
    print("    %-28s P(>0) %%%.1f  <- POZITIF OLARAK KOTU"
          % ("250 ortalama dusurme", BOOTSTRAP["p_pozitif"]))

    print("\n3) NEDEN: 'aleyhte giden geri doner' VARSAYIMI YANLIS")
    print("  bacak yonunde ileri 5 gun (%):")
    print("  %-20s%9s%9s%10s" % ("durum", "ort", "medyan", "n"))
    for a, v in ILERI_GETIRI.items():
        print("  %-20s%+9.2f%+9.2f%10d" % (a, v[0], v[1], v[2]))
    print("  monoton kotulesme dogrulandi mi? %s"
          % ("EVET" if monoton_kotulesme() else "HAYIR"))

    print("\n4) YENI YASA\n  %s" % YASA)
