"""MADDE 239: PRIM-OLCEKLI BRUT yapisinin karar tablosu + plasebo + bootstrap.

YAPI: brut maruziyet, gozlenebilir prim seviyesine gore olceklenir.
  m[t] = clip( (prim_30g[t] / prim'in YEREL 180g medyani) ** e , alt, ust )
Hepsi nedensel, 1 bar gecikmeli. Motor flagleri (g33.py):
  BRUT_PRIM=e  BRUT_ALT  BRUT_UST  BRUT_REF  BRUT_OLC  BRUT_PLASEBO

ONCE BUTCE (madde 213/214 disiplini): bkz. `arastirma_prim_butce.py` -
gozlenebilir prim, kitabin ileriye donuk getirisini tek yonlu siraliyor
ve oynaklik ceyrekler arasinda DUZ.

SONUC: ON KAYITLI KURAL REDDEDIYOR, tek sebep SART 1 - ve o sart
2025-26'da -0,032 Sharpe'a dayaniyor. Alt donem bootstrap'i (4.000
ornek) o reddin tabanini soyle gosteriyor:
  22-24: dSharpe +0,269, P(dSh>0) = %95,6   <- gercek iyilesme
  25-26: dSharpe -0,008, P(dSh>0) = %48,2   <- YAZI-TURA, negatif degil
Yani yapi bir donemde %95,6 guvenle iyilestiriyor, otekinde SIFIRDAN
AYIRT EDILEMIYOR. Kural "her iki donemde de KESIN iyilesme" istedigi
icin bu RED'dir ve kural DEGISTIRILMEDI: aday elde tutularak kuralin
gevsetilmesi, madde 212'nin kapattigi deligin ta kendisidir.

PLASEBO AYIRIMI (ayni carpan DAGILIMI, yanlis zamanlar):
  gercek yapi   esit-risk +150,0   (kontrol +112,5)
  zamanda TERS  esit-risk  +92,5   <- yapiyi YOK EDIYOR
  KARISTIR      esit-risk +124,2   <- kismi (bkz. asagidaki not)
Dozu degil ZAMANLAMAYI tasiyor.

SADECE NAKDE CEKME (ust=1,0; hic kaldirac yok) NEREDEYSE HICBIR SEY
ODEMIYOR: +%93,6, Sharpe 2,985, dusus -12,49, ort brut 0,848 -> esit
riskte kontrolun 3,6 puan ustunde (gunluk seriyle dogrudan olcum
+%116,1; kural tablosunun yaklasik sutunu +%109,0 diyor - ikisi de
"kontrolun hemen yaninda") VE o kazanc icin 1,17x kaldirac gerekiyor. Kazanc tamamen primin GENIS oldugu
donemde brutu ARTIRMAKTAN geliyor. Yani bu yapi kismen bir KALDIRAC kararidir (madde 227'nin
bekleyen karari) ve motor likidasyonu modellemez.

HATA KAYDI: `BRUT_PLASEBO=2` (karistir) ilk kosumda `.values`
salt-okunur oldugu icin patladi; kabuk eski `/tmp/g19E_*.pkl`i yeni
sonuc sanip kopyaladi ve iki plasebo satiri BIREBIR AYNI cikti.
Esitlik fark edildigi icin yakalandi. Duzeltme: shuffle oncesi copy().

Kosum: python3 arastirma_prim_karar.py
"""
import sys

sys.path.insert(0, "/home/claude/binance_bot/binance_bot")
import karar_kurali as K  # noqa: E402

# (getiri, Sharpe, 22-24 Sh, 25-26 Sh, dusus POZITIF, esit-risk, ort brut)
KONTROL = (112.5, 2.942, 2.794, 3.147, 14.54, 112.5, 1.000)
ADAYLAR = {
    "e0.5 ref180":  (137.3, 3.061, 3.069, 3.115, 13.31, 150.0, 1.058),
    "e1.0 ref180":  (137.3, 3.067, 3.143, 3.065, 13.55, 147.4, 1.031),
    "e1.5 ref180":  (134.4, 3.052, 3.129, 3.062, 13.89, 140.7, 1.005),
    "e1.0 ref90":   (133.3, 2.970, 3.126, 2.867, 15.78, 122.8, 1.039),
    "e1.0 ref365":  (144.8, 2.996, 3.118, 3.026, 14.98, 140.5, 1.099),
    "e1.0 alt0.5":  (138.9, 3.080, 3.139, 3.098, 13.55, 149.0, 1.040),
    "e1.0 ust2.0":  (171.9, 3.035, 3.166, 3.007, 15.19, 164.5, 1.131),
    "PLASEBO ters": (116.4, 2.807, 2.735, 2.909, 18.29,  92.5, 1.036),
    "PLASEBO karis": (115.5, 2.946, 2.812, 3.134, 13.53, 124.2, 1.036),
    # yalnizca nakde cekme: brut HIC 1,00'in ustune cikmaz
    "ust1.0 (nakit)": (93.6, 2.985, 2.960, 3.050, 12.49, 109.0, 0.848),
}

# esli blok bootstrap (1.504 gun, 21 gunluk blok, 2.000 ornek)
BOOTSTRAP = {   # ad: (dSharpe, P(dSh>0)%, d esit-risk puan, P(>0)%)
    "e0.5 ref180":  (+0.117, 83.9, +22.2, 79.0),
    "e1.0 ref180":  (+0.120, 77.2, +24.3, 75.1),
    "e1.5 ref180":  (+0.113, 72.0, +25.7, 71.1),
    "e1.0 ust2.0":  (+0.102, 68.8, +27.4, 70.0),
    "PLASEBO ters": (-0.138, 16.4, -15.0, 19.2),
}

ALT_DONEM = {"22-24": (2.794, 3.069, +0.269, 95.6),
             "25-26": (3.147, 3.115, -0.008, 48.2)}

YIL_YIL = {2022: (11.9, 12.8), 2023: (142.5, 212.2), 2024: (101.6, 97.3),
           2025: (107.3, 153.8), 2026: (202.2, 210.9)}


def _olcum(ad, t):
    return K.Olcum(ad, getiri=t[0], sharpe=t[1], erken=t[2], gec=t[3], dusus=t[4])


if __name__ == "__main__":
    print(K.yaz(_olcum("5g kontrol", KONTROL),
                [_olcum(a, t) for a, t in ADAYLAR.items()]))
    print("\nFIILI ORTALAMA BRUT CARPAN (1,00 = kaldirac yok)")
    for a, t in ADAYLAR.items():
        print("  %-16s%7.3fx" % (a, t[6]))
    print("\nESLI BLOK BOOTSTRAP (1.504 gun, 21 gunluk blok, 2.000 ornek)")
    print("  %-16s%10s%11s%14s%9s" % ("aday", "dSharpe", "P(dSh>0)",
                                      "d esit-risk", "P(>0)"))
    for a, (ds, ps, de, pe) in BOOTSTRAP.items():
        print("  %-16s%+10.3f%10.1f%%%+14.1f%8.1f%%" % (a, ds, ps, de, pe))
    print("\nSART 1'IN REDDI NEYE DAYANIYOR (alt donem bootstrap, 4.000 ornek)")
    print("  %-8s%10s%9s%10s%11s" % ("donem", "kontrol", "aday", "dSharpe",
                                     "P(dSh>0)"))
    for d, (b, a, ds, p) in ALT_DONEM.items():
        print("  %-8s%10.3f%9.3f%+10.3f%10.1f%%" % (d, b, a, ds, p))
    print("\nYIL YIL yillik getiri (aday = e0.5 ref180)")
    print("  %-6s%10s%10s%9s" % ("yil", "kontrol", "aday", "fark"))
    for y, (b, a) in YIL_YIL.items():
        print("  %-6d%+10.1f%+10.1f%+9.1f" % (y, b, a, a - b))
    print("\nKARAR: RED (sart 1). Kural degistirilmedi. Yapi OLCULMUS bir")
    print("secenek olarak duruyor; kabulu icin ornek DISI kanit gerekir.")
