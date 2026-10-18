"""MADDE 254: GRAFIK OGRENIP ILERIYE TAHMIN - model CALISTI, kitap COKTU.

Kullanicinin sorusu: "grafik ogrense, grafik formullerinden ileriye donuk
tahminleme yapsa". Madde 152 bunu denemis ve reddetmisti; kendi kaydindaki
sebep: "5 gunluk getiri fiyat gurultusune gomulu". Ama madde 152, madde
**214'ten 62 tur ONCEYDI** - ve 214 karin TAMAMININ TP HASADI oldugunu,
funding (+109,8) ile ham fiyatin (-108,0) birbirini goturdugunu gosterdi.

Yani 152'nin reddi HEDEFIN yanlis olmasiyla da aciklanabilirdi. Bu tur
hedefi degistirdi:
  152'nin hedefi : 5 gunluk toplam getiri (fiyat + funding)
  254'un hedefi  : "bu bacagin KAR AL seviyesi tutma suresi icinde DOLAR mi?"
                   long  = onumuzdeki 30 barda max(H) >= giris x 1,40
                   short = onumuzdeki 30 barda min(L) <= giris x 0,80

OZELLIKLER: 14 tane, YALNIZCA grafik (fiyat/hacim) - "grafik formulleri".
1/6/30/90 bar getiri · 30 bar oynaklik · oynaklik orani (30/180) · yukselen
bar payi (RSI benzeri) · 6/30/180 ortalamaya uzaklik · 30/180 menzil
konumu · hacim orani (30/180) · donukluk. Funding, kalabalik, OI, akis
KULLANILMADI - sorulan sey grafigin KENDI BASINA ne ogrettigi.

SIZINTI ENGELI: HistGradientBoosting, 90 gunde bir yeniden egitim, yalnizca
o ana kadarki veri, VE etiket 30 bar ileri baktigi icin egitim verisinin
son 30 bari atilir. Olasiliklar yalnizca egitim penceresinin DISINA yazilir.
351.734 ORNEK DISI gozlem.

================================================================
1) MODEL CALISTI - VE AZ DEGIL
================================================================
                  ORNEK DISI AUC
  taraf        gercek    plasebo (etiketler karistirilmis)
  long         0,7918     0,5542
  short        0,7122     0,4699

Madde 152'nin en guclu TEK siralama korelasyonu -0,087'ydi. Bu baska bir
lig: grafik, TP'nin dolup dolmayacagini ciddi sekilde BILIYOR. Plasebonun
~0,5'te kalmasi boru hattinda sizinti olmadigini gosterir.
(Plasebo long'un 0,554'u tam 0,5 degil; etiket karistirmasi taban orani
korudugu icin modelin zaman-degisken bir kesisim ogrenmesinden geliyor -
kucuk ve sonucu etkilemiyor.)

================================================================
2) KITAP COKTU - AMA GURULTUYU YENDI
================================================================
Olasilik, havuz olcutu olarak kullanildi (kitap funding ile taraf basina
15 aday seciyor, havuz onlardan 5'ini bir olcute gore aliyor).

  aday                       yillik  Sharpe   22-24   25-26  dusus  esit-risk
  KONTROL (kalabalik olcutu) +112,3   2,939   2,789   3,147  -14,5     +112,3
  grafik modeli (AUC 0,79)    +63,4   1,732   1,821   1,711  -22,6      +37,1
  plasebo (AUC 0,55)          +28,5   1,364   1,242   1,529  -23,2      +16,7

Uc satir birlikte okunmali:
  * model plaseboyu **35 puan** geciyor -> grafik GERCEK bilgi tasiyor,
    bu bir "ise yaramadi" vakasi DEGIL;
  * ama kitabin mevcut olcutunun **49 puan** gerisinde.
Bootstrap (4.000 ornek, esli blok, esit riskte): ort **-79,0 puan**,
std 24,5, **P(>0) %0,0** - projenin sicilindeki EN KESIN ret.

================================================================
3) NEDEN: TP'NIN DOLMASINI ONGORMEK, HASADI ONGORMEK DEGILDIR
================================================================
Tahmin ondaligina gore gerceklesenler (351.719 gozlem):

  LONG tarafi
  ondalik  ort tahmin   TP dolma    bacak getirisi
     1        0,002        0,6%          +0,30%
     5        0,016        2,2%          -0,36%
     9        0,076        9,9%          +0,92%
    10        0,196       20,0%          **-1,53%**   <- ON ONDALIGIN EN KOTUSU
  en ust/en alt: TP dolma **31,5 KAT**, bacak getirisi **-1,83 puan**

  SHORT tarafi
     1        0,015        2,9%          -0,79%
    10        0,454       38,2%          +0,93%
  en ust/en alt: TP dolma **13,3 KAT**, bacak getirisi **+1,72 puan**

LONG TARAFTA TABLO TAM TERSINE DONUYOR: model TP dolumunu 31,5 kat daha
iyi seciyor ve en yuksek tahminli ondalik, PARAYI EN COK KAYBEDEN
ondalik. Bu madde 191'in gorunur hali: long bacagin kanamasi sizinti
degil OPSIYON PRIMI. +%40'i 5 gunde vurma olasiligi yuksek olan coin,
ayni zamanda cokme olasiligi yuksek olan coindir. **Opsiyon DOGRU
FIYATLANMIS**: dolma olasiligi yukseldikce primi de yukseliyor.

SHORT tarafta kismen DONUSUYOR (+1,72 puan) - madde 189/190'in "short
bacak hedge degil, kendi alfasi var" bulgusuyla tutarli. Yani grafik
bilgisi degersiz degil; yanlis tarafta ve yanlis hedefte.

================================================================
4) YENI YASA
================================================================
  **BIR SEYI IYI ONGORMEK, ONDAN PARA KAZANMAK DEGILDIR - ve hangi SEYI
  ongordugunuz, NE KADAR IYI ongordugunuzden onemlidir.**

Madde 251 bunun bir yuzunu gostermisti (Sharpe artar, para artmaz).
Madde 254 daha serti: tahmin gucu 0,79 AUC'ye cikti, kitap yariya indi,
ve long tarafta tahmin ile para TERS yonlu cikti. Yeni bir model
onerisi artik su iki soruyu gecmek zorunda:
  (a) hangi hedefi ongoruyor - ve o hedef PARAYI tasiyan sey mi?
  (b) ongorduğu sey, piyasada zaten FIYATLANMIS bir sey mi?
(b) bu turda "evet" cikti: TP dolma olasiligi opsiyonun priminde zaten var.

HATA KAYDI YOK (bu tur temiz gecti). Madde 250'nin dersi uygulandi:
motora eklenen `tpmdl` modunun girintisi elle dogrulandi, `ast.parse`
yeterli sayilmadi.

Kosum: python3 arastirma_grafik_modeli.py
"""

HEDEF_152 = "5 gunluk toplam getiri (fiyat + funding)"
HEDEF_254 = "TP tutma suresi icinde dolar mi (long +%40 / short -%20)"
OZELLIK_SAYISI = 14
ORNEK_DISI = 351734
EGITIM = "HistGradientBoosting, 90 gunde yeniden, etiket icin 30 bar atlama"

AUC = {"long": (0.7918, 0.5542), "short": (0.7122, 0.4699)}   # (gercek, plasebo)
MADDE_152_EN_GUCLU_KORELASYON = -0.087

KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)
KITAP = {   # (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk)
    "grafik modeli (AUC 0,79)": (63.4, 1.732, 1.821, 1.711, -22.6, 37.1),
    "plasebo (AUC 0,55)": (28.5, 1.364, 1.242, 1.529, -23.2, 16.7),
}
BOOTSTRAP = dict(ort=-79.0, std=24.5, p_pozitif=0.0, ornek=4000)

# ondalik: (ort tahmin, TP dolma %, bacak getirisi %)
ONDALIK_LONG = {1: (0.002, 0.6, +0.30), 5: (0.016, 2.2, -0.36),
                9: (0.076, 9.9, +0.92), 10: (0.196, 20.0, -1.53)}
ONDALIK_SHORT = {1: (0.015, 2.9, -0.79), 10: (0.454, 38.2, +0.93)}
UST_ALT = {"long": dict(tp_kat=31.5, getiri_fark=-1.83),
           "short": dict(tp_kat=13.3, getiri_fark=+1.72)}

YASA = ("Bir seyi iyi ongormek, ondan para kazanmak degildir - ve HANGI seyi "
        "ongordugunuz, NE KADAR IYI ongordugunuzden onemlidir. Yeni bir model "
        "iki soruyu gecmek zorunda: (a) ongordugu hedef PARAYI tasiyan sey mi? "
        "(b) ongordugu sey piyasada zaten FIYATLANMIS mi?")


def model_gercekten_ogrendi():
    """Gercek AUC plaseboyu belirgin geciyor mu? (boru hatti saglam mi)"""
    return all(g - p > 0.15 for g, p in AUC.values())


def gurultuyu_yendi():
    """Model, plasebo kitabini geciyor mu? (grafik gercek bilgi tasiyor)"""
    return (KITAP["grafik modeli (AUC 0,79)"][0]
            - KITAP["plasebo (AUC 0,55)"][0] > 25.0)


def kontrole_yenildi():
    """Ama kontrolun gerisinde mi, ve bootstrap bunu dogruluyor mu?"""
    return (KITAP["grafik modeli (AUC 0,79)"][0] < KONTROL["yillik"] - 40
            and BOOTSTRAP["p_pozitif"] < 1.0)


def long_tahmin_parayla_ters():
    """Long tarafta TP dolumu artarken bacak getirisi DUSUYOR mu?"""
    return (UST_ALT["long"]["tp_kat"] > 10 and UST_ALT["long"]["getiri_fark"] < 0
            and ONDALIK_LONG[10][2] == min(v[2] for v in ONDALIK_LONG.values()))


if __name__ == "__main__":
    print("MADDE 254 - GRAFIK OGRENIP ILERIYE TAHMIN\n")
    print("hedef degisikligi:")
    print("  madde 152 : %s" % HEDEF_152)
    print("  madde 254 : %s" % HEDEF_254)
    print("  (152, madde 214'ten 62 tur ONCEYDI - 214 karin TP hasadi "
          "oldugunu gosterdi)")
    print("\n1) MODEL CALISTI  (%d ozellik, %d ornek disi gozlem)"
          % (OZELLIK_SAYISI, ORNEK_DISI))
    print("  %-8s%10s%10s" % ("taraf", "gercek", "plasebo"))
    for t, (g, p) in AUC.items():
        print("  %-8s%10.4f%10.4f" % (t, g, p))
    print("  madde 152'nin en guclu tek korelasyonu: %.3f"
          % MADDE_152_EN_GUCLU_KORELASYON)
    print("  boru hatti saglam mi? %s"
          % ("EVET" if model_gercekten_ogrendi() else "HAYIR"))

    print("\n2) KITAP (olasilik = havuz olcutu)")
    print("  %-28s%8s%8s%8s%8s%8s%10s"
          % ("", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk"))
    print("  %-28s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f"
          % ("KONTROL (kalabalik)", KONTROL["yillik"], KONTROL["sharpe"],
             KONTROL["erken"], KONTROL["gec"], KONTROL["dusus"], KONTROL["yillik"]))
    for a, v in KITAP.items():
        print("  %-28s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("  gurultuyu yendi mi? %s   kontrole yenildi mi? %s"
          % ("EVET" if gurultuyu_yendi() else "HAYIR",
             "EVET" if kontrole_yenildi() else "HAYIR"))
    print("  bootstrap: ort %+.1f puan  std %.1f  P(>0) %%%.1f"
          % (BOOTSTRAP["ort"], BOOTSTRAP["std"], BOOTSTRAP["p_pozitif"]))

    print("\n3) NEDEN - tahmin ondaligina gore gerceklesenler")
    for ad, tab in (("LONG", ONDALIK_LONG), ("SHORT", ONDALIK_SHORT)):
        print("  %s" % ad)
        print("    %-9s%12s%12s%18s"
              % ("ondalik", "ort tahmin", "TP dolma", "bacak getirisi"))
        for k, v in tab.items():
            print("    %-9d%12.3f%11.1f%%%17.2f%%" % (k, v[0], v[1], v[2]))
        u = UST_ALT[ad.lower()]
        print("    en ust/en alt: TP dolma %.1f KAT, getiri %+.2f puan"
              % (u["tp_kat"], u["getiri_fark"]))
    print("\n  LONG tarafta tahmin PARAYLA TERS mi? %s"
          % ("EVET - en yuksek tahminli ondalik en cok kaybeden"
             if long_tahmin_parayla_ters() else "HAYIR"))
    print("  -> madde 191'in gorunur hali: opsiyon DOGRU FIYATLANMIS")

    print("\n4) YENI YASA\n  %s" % YASA)
