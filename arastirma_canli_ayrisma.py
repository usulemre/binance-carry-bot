"""MADDE 247: CANLI-BACKTEST AYRISMASI - iki kural, 63 tur sonra yeniden olculdu.

Canli botta OLUP backtest kontrolunde OLMAYAN iki kural var:

  kural                   canli      backtest kontrolu
  DELIST_UFUK_GUN          30 gun     0 (modellenmiyor)
  ISLEM_TOLERANSI          %50        0 (her sapma duzeltilir)

Ikisi de son kez **madde 183.2'de** olculmustu: Sharpe 2,68'lik bir
yuzeyde, 12+12 bacakla, ve "kontrolle beraber" cikmisti. Aradan 184
(dilim 5->15), 189, 196, 209 (pencere), 222 (bacak 6->5), 224-246 gecti.
Madde 240'in defteri bu ikisini KAPALI_EKSEN'e "madde 183.2" gerekcesiyle
koymustu - yani gerekce 63 tur bayattı. Ve bahis buyudu: kitap artik
cok daha YOGUN (5+5 bacak, taraf basina 15 adaylik havuz), yogunluk
disŀamanın bedelini BUYUTUR (madde 226 tam bunu bulmustu).

Madde 182'nin dersi de tam bu sinifti: **canli bot, OLCULMEMIS bir
yapilandirmayla calisabilir.**

================================================================
OLCUM (guncel yuzey, iki faz ortalamasi)
================================================================
  yapilandirma            getiri   Sharpe   22-24   25-26   dusus  esit-risk
  KONTROL (ufuk 0, tol 0) +%112,5  2,942   2,794   3,147   -14,5   +%112,5
  delist ufku 15 gun      +%112,8  2,947   2,794   3,158   -14,5   +%112,8
  delist ufku 30 (CANLI)  +%113,0  2,949   2,797   3,160   -14,5   +%113,0
  delist ufku 60 gun      +%112,6  2,945   2,790   3,159   -14,5   +%112,6
  islem toleransi %25     +%112,6  2,942   2,784   3,161   -14,8   +%110,3
  islem tol. %50 (CANLI)  +%112,6  2,944   2,788   3,161   -14,8   +%110,3
  **CANLI: ufuk 30 + tol %50** +%113,1 2,951 2,791  3,173   -14,8   +%110,8

================================================================
SONUC: AYRISMA BEDAVA - VE ISARET BEKLENENIN TERSI
================================================================
1. **Delist ufku bir MALIYET DEGIL, hafif bir FAYDA.** 30 gun, kurali
   formen GECIYOR (+%113,0; Sharpe 2,949; iki donemde de yukari; dusus
   ayni). Kazanc +0,5 puan, yani gurultu icinde - ama ISARET onemli:
   delist edilecek coinleri dislamak zarar vermiyor. Beklenti tersiydi
   (delistlenen coinler genelde EN YUKSEK funding odeyenler).
   Mekanizma: o coinlerde funding sinyalinin yakalamadigi uzlasma/
   likidite riski var; kitap onlari kaybetmekle bir sey kaybetmiyor.

2. **Islem toleransi %50 pratikte notr:** getiri ayni, Sharpe +0,002,
   dusus 0,3 puan derin, esit-risk -2,2 puan. Madde 124/183.2'nin
   sonucu guncel yuzeyde de gecerli; operasyonel faydasi (daha az
   islem, limit emre daha cok sure) hala bedavaya geliyor.

3. **TAM CANLI YAPILANDIRMA kontrolden AYIRT EDILEMEZ:** +%113,1 vs
   +%112,5 getiri, Sharpe 2,951 vs 2,942, esit-risk +%110,8 vs +%112,5.
   **Yani yayinlanan +%112,5, canliya ozgu iki kural MODELLENDIGINDE de
   ayakta.** Bu, 63 tur sonra yapilmis bir canli-gerceklik dogrulamasi
   ve su an onemli olan tek eksen o (arastirma yuzeyi 240-246'da kapandi).

Defterdeki (madde 240) iki gerekce artik GUNCEL bir olcume isaret
ediyor: "madde 183.2 + madde 247".

Kosum: arastirma_canli_ayrisma_kos.sh, sonra bu dosya.
"""

OLCUM = {   # ad: (getiri, Sharpe, 22-24, 25-26, dusus, esit-risk, kaldirac)
    "KONTROL (ufuk 0, tol 0)": (112.5, 2.942, 2.794, 3.147, -14.5, 112.5, 1.00),
    "delist ufku 15 gun": (112.8, 2.947, 2.794, 3.158, -14.5, 112.8, 1.00),
    "delist ufku 30 (CANLI)": (113.0, 2.949, 2.797, 3.160, -14.5, 113.0, 1.00),
    "delist ufku 60 gun": (112.6, 2.945, 2.790, 3.159, -14.5, 112.6, 1.00),
    "islem toleransi %25": (112.6, 2.942, 2.784, 3.161, -14.8, 110.3, 0.98),
    "islem tol. %50 (CANLI)": (112.6, 2.944, 2.788, 3.161, -14.8, 110.3, 0.98),
    "CANLI: ufuk 30 + tol %50": (113.1, 2.951, 2.791, 3.173, -14.8, 110.8, 0.98),
}

CANLI = "CANLI: ufuk 30 + tol %50"
KONTROL = "KONTROL (ufuk 0, tol 0)"
ONCEKI_OLCUM_MADDE = 183        # son kez burada olculmustu
BU_MADDE = 247


def fark(ad=CANLI):
    """(d getiri, d Sharpe, d dusus, d esit-risk) - kontrole gore."""
    a, k = OLCUM[ad], OLCUM[KONTROL]
    return (a[0] - k[0], a[1] - k[1], a[4] - k[4], a[5] - k[5])


if __name__ == "__main__":
    print("MADDE 247 - CANLI-BACKTEST AYRISMASI (son olcum madde %d, %d tur once)\n"
          % (ONCEKI_OLCUM_MADDE, BU_MADDE - ONCEKI_OLCUM_MADDE))
    print("%-28s%9s%8s%8s%8s%8s%12s" % ("yapilandirma", "getiri", "Sharpe",
          "22-24", "25-26", "dusus", "esit-risk"))
    for ad, t in OLCUM.items():
        im = ("  <- KONTROL" if ad == KONTROL else
              "  <- TAM CANLI" if ad == CANLI else "")
        print("%-28s%+9.1f%8.3f%8.3f%8.3f%8.1f%+12.1f%s"
              % (ad, t[0], t[1], t[2], t[3], t[4], t[5], im))
    dg, ds, dd, de = fark()
    print("\nTAM CANLI - KONTROL:  getiri %+.1f puan · Sharpe %+.3f · "
          "dusus %+.1f puan · esit-risk %+.1f puan" % (dg, ds, dd, de))
    print("\n1) Delist ufku bir MALIYET DEGIL, hafif FAYDA (+0,5 puan, gurultu")
    print("   icinde) - ama ISARET beklenenin TERSI. Delistlenecek coinler")
    print("   genelde en yuksek funding odeyenler; onlari dislamak zarar")
    print("   vermiyor, cunku o coinlerde sinyalin yakalamadigi uzlasma riski var.")
    print("2) Islem toleransi %50 notr (madde 124/183.2 guncel yuzeyde gecerli).")
    print("3) TAM CANLI yapilandirma kontrolden AYIRT EDILEMEZ -> yayinlanan")
    print("   +%112,5, canliya ozgu iki kural MODELLENDIGINDE de ayakta.")
