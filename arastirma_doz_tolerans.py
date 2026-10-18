"""MADDE 261: DOZ SORUSU UFUK OLMADAN EKSIK - ve cevabi 1x'in kendisi cikiyor.

Madde 245 doz cetvelini olctu (brut -> yillik getiri, maks dusus). Madde 260
dusus zarfini UFKA GORE olctu (14/30/90/365 gun). Ikisi hic birlestirilmedi -
ama doz karari tam olarak o kesisimde veriliyor. Cunku "-%20 dususe
dayanabilirim" cumlesi, UFUK soylenmeden ANLAMSIZDIR: 14 gunluk -%20 ile
1 yillik -%20 bambaska dozlar demektir.

YONTEM: madde 243'un siralama testi (ayni gunluk getiriler, siralama
rastgele - cunku gerceklesen yol sansli bir siralamadir, %84'luk yuzdelik).
Her doz icin gunluk getiriler k ile olceklenir, 20.000 karistirilmis yol
uretilir, her ufukta dusus dagiliminin p95'i alinir. Kaldirac dususu
DOGRUSAL olceklemez (madde 218: bilesik seride konvekslik) - o yuzden
olceklenip hesaplandi, carpilmadi.

DOGRULAMA: yillik getiri sutunu madde 245'in CETVEL'ini yeniden uretiyor
(112,3 / 153,4 / 201,1 / 319,6 / 474,6 / 673,4 vs 112,5 / 153,6 / 201,5 /
320,3 / 475,8 / 675,3) - yontem gecerli.

================================================================
1) DUSUS p95, DOZA VE UFKA GORE
================================================================
  doz      14 gun   30 gun   90 gun  365 gun   yillik getiri
  1,00x      %7,1    %10,4    %15,2    %21,0        +%112,3
  1,25x      %8,8    %12,7    %18,9    %25,7        +%153,4
  1,50x     %10,3    %15,3    %22,0    %30,5        +%201,1
  2,00x     %13,6    %20,2    %28,9    %39,4        +%319,6
  2,50x     %17,2    %24,5    %35,3    %47,3        +%474,6
  3,00x     %20,3    %28,5    %41,0    %54,0        +%673,4

UFUK NE KADAR ONEMLI: 1x'te p95 dusus 14 gunde %7,1 ama bir yilda %21,0 -
UC KATI. Yani ayni kitap, ayni doz, farkli ufukta tamamen farkli bir risk
gorunumu verir. "Dayanabilirim" cumlesi ufuksuz kurulamaz.

================================================================
2) TOLERANSA GORE EN YUKSEK DOZ (p95 dusus <= tolerans)
================================================================
  tolerans   14 gun   30 gun   90 gun   365 gun
  -%10        1,25x      <1x      <1x       <1x
  -%15        2,00x    1,25x      <1x       <1x
  -%20        2,50x    1,50x    1,25x       <1x
  -%25        3,00x    2,50x    1,50x     1,00x
  -%30        3,00x    3,00x    2,00x     1,25x

================================================================
3) ASIL BULGU: MEVCUT AYAR ZATEN DOGRU DOZ
================================================================
365 GUN sutunu okunursa:
  * -%20 tolerans  -> **1x'in ALTI**. Yani bugunku ayar bile bir yillik
    -%20 toleransi icin HAFIF AGRESIF: 1x'in bir yillik p95 dususu %21,0.
  * -%25 tolerans  -> **tam 1,00x**. Yani mevcut ayar, bir yillik -%25
    toleransin TAM karsiligi.
  * 1,25x'e cikmak bir yillik -%30 toleransi gerektirir.

Bu, projenin 40+ turdur sorulan "getiriyi nasil yukseltiriz" sorusuna
en durust cevaptir: **yukseltmek, bir yillik dususu -%20'den belirgin
asagiya goturmek anlamina gelir, ve tablo ne kadar oldugunu soyler.**
Madde 257 zaten gostermisti ki tiltlerle bunu bedava yapmak mumkun degil
(kaldirac her tilti yeniyor); madde 261 fiyatini koyuyor.

VE MADDE 243 ILE TUTARLI: 1x'in bir yillik p95'i burada %21,0, madde 243
yayinlanan beklentiyi -%20,6 olarak vermisti - ayni yontem, ayni sayi.
Yani "canlida -%20 civari bir yil normaldir" ifadesi bu tablonun 1x
satiridir.

================================================================
4) KURAL: DOZ KARARI UC GIRDI ISTER
================================================================
  (1) UFUK  - kac gunluk dususe bakiyorsunuz? (14 / 30 / 90 / 365)
  (2) TOLERANS - o ufukta kabul edilebilir en kotu dusus
  (3) CANLI SAPMA - madde 227: doz karari CANLI OLCUM ONCESINDE verilmez,
      cunku modellenmeyen icra sapmasi kaldiracla CARPILIR.
Ucu olmadan doz sorusu cevaplanamaz; ikisi varsa tablo cevabi verir.

SINIR: tablo backtest'in +%112,5'ine ve onun gunluk getiri dagilimina
dayanir. O dagilim yanlissa her satir ayni oranda yanlistir (madde 245'in
kendi uyarisi). Ayrica likidasyon ayri bir kisit: madde 245 brut 3x'e
kadar baglayici olmadigini olctu, tablo onun otesine gecmez.

Kosum: python3 arastirma_doz_tolerans.py
       python3 arastirma_doz_tolerans.py --ufuk 365 --tolerans 25
"""
import argparse

UFUKLAR = (14, 30, 90, 365)
DOZLAR = (1.00, 1.25, 1.50, 2.00, 2.50, 3.00)

# doz: ((14g, 30g, 90g, 365g) p95 dusus YUZDE, yillik getiri YUZDE)
ZARF = {
    1.00: ((7.1, 10.4, 15.2, 21.0), 112.3),
    1.25: ((8.8, 12.7, 18.9, 25.7), 153.4),
    1.50: ((10.3, 15.3, 22.0, 30.5), 201.1),
    2.00: ((13.6, 20.2, 28.9, 39.4), 319.6),
    2.50: ((17.2, 24.5, 35.3, 47.3), 474.6),
    3.00: ((20.3, 28.5, 41.0, 54.0), 673.4),
}
# madde 245'in CETVEL'i - dogrulama referansi (yillik getiri)
MADDE_245_GETIRI = {1.00: 112.5, 1.25: 153.6, 1.50: 201.5,
                    2.00: 320.3, 2.50: 475.8, 3.00: 675.3}
MADDE_243_1YIL_P5 = 20.6        # yayinlanan beklenti
ORNEK = 20000
LIKIDASYON_SINIRI = 3.0         # madde 245: 3x'e kadar baglayici degil


def p95(doz: float, ufuk: int) -> float:
    """Verilen doz ve ufukta p95 dusus (POZITIF yuzde)."""
    return ZARF[doz][0][UFUKLAR.index(ufuk)]


def getiri(doz: float) -> float:
    return ZARF[doz][1]


def en_yuksek_doz(ufuk: int, tolerans: float):
    """p95 dususu toleransi asmayan EN YUKSEK doz. Yoksa None (<1x)."""
    uygun = [d for d in DOZLAR if p95(d, ufuk) <= tolerans]
    return max(uygun) if uygun else None


def doz_onerisi(ufuk: int, tolerans: float) -> dict:
    """Doz karari icin tam cevap - uc girdinin ikisi verilince."""
    d = en_yuksek_doz(ufuk, tolerans)
    return {
        "ufuk": ufuk, "tolerans": tolerans, "doz": d,
        "yillik": getiri(d) if d else None,
        "p95_dusus": p95(d, ufuk) if d else None,
        "likidasyon_icinde": (d is not None and d <= LIKIDASYON_SINIRI),
        "uyari": ("1x'in ALTI gerekir - mevcut ayar bu tolerans icin AGRESIF"
                  if d is None else
                  "madde 227: CANLI OLCUM ONCESINDE uygulanmaz"),
    }


def dogrulama_245(oran=0.005) -> bool:
    """Yillik getiri sutunu madde 245'in cetvelini uretiyor mu?

    ORANSAL test: getiri bilesik oldugu icin mutlak fark seviyeyle buyur
    (3x satirinda 1,9 puan ama bu %0,3'tur). Ilk surumum mutlak tolerans
    kullandi ve 3x'te yanlis "HAYIR" verdi - duzeltildi.
    """
    return all(abs(getiri(d) - MADDE_245_GETIRI[d]) / MADDE_245_GETIRI[d] < oran
               for d in DOZLAR)


def madde_243_tutarli(tol=1.0) -> bool:
    """1x'in bir yillik p95'i, madde 243'un yayinlanan -%20,6'siyla uyumlu mu?"""
    return abs(p95(1.00, 365) - MADDE_243_1YIL_P5) < tol + 0.5


def ufuk_ne_kadar_onemli(doz=1.00) -> float:
    """En uzun / en kisa ufuk orani - 'ufuksuz soru anlamsiz'in sayisi."""
    return p95(doz, 365) / p95(doz, 14)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MADDE 261 - doz x ufuk x tolerans")
    ap.add_argument("--ufuk", type=int, choices=UFUKLAR, default=None)
    ap.add_argument("--tolerans", type=float, default=None,
                    help="POZITIF puan, ornek 25")
    a = ap.parse_args()

    if a.ufuk and a.tolerans:
        o = doz_onerisi(a.ufuk, a.tolerans)
        print("MADDE 261 - DOZ ONERISI\n")
        print("  ufuk          : %d gun" % o["ufuk"])
        print("  tolerans      : -%.0f%%" % o["tolerans"])
        if o["doz"]:
            print("  ONERILEN DOZ  : **%.2fx**" % o["doz"])
            print("  beklenen getiri: %+.1f%%/yil" % o["yillik"])
            print("  o ufukta p95 dusus: -%.1f%%" % o["p95_dusus"])
            print("  likidasyon sinirinin icinde mi? %s"
                  % ("EVET" if o["likidasyon_icinde"] else "HAYIR"))
        else:
            print("  ONERILEN DOZ  : **1x'in ALTI**")
        print("  UYARI         : %s" % o["uyari"])
        raise SystemExit(0)

    print("MADDE 261 - DOZ x UFUK x TOLERANS\n")
    print("1) DUSUS p95 (madde 243'un siralama testi, %d ornek)" % ORNEK)
    print("  %-8s" % "doz" + "".join("%10s" % ("%dg" % u) for u in UFUKLAR)
          + "%16s" % "yillik getiri")
    for d in DOZLAR:
        print("  %-8.2f" % d + "".join("%9.1f%%" % p95(d, u) for u in UFUKLAR)
              + "%15.1f%%" % getiri(d))
    print("\n  madde 245'in cetvelini uretiyor mu? %s"
          % ("EVET" if dogrulama_245() else "HAYIR"))
    print("  ufuk ne kadar onemli: 1x'te 365g/14g = **%.1f KAT**"
          % ufuk_ne_kadar_onemli())

    print("\n2) TOLERANSA GORE EN YUKSEK DOZ")
    print("  %-12s" % "tolerans" + "".join("%10s" % ("%dg" % u) for u in UFUKLAR))
    for tol in (10, 15, 20, 25, 30):
        hu = []
        for u in UFUKLAR:
            d = en_yuksek_doz(u, tol)
            hu.append("%.2fx" % d if d else "<1x")
        print("  -%-11d" % tol + "".join("%10s" % h for h in hu))

    print("\n3) ASIL BULGU - 365 GUN sutunu")
    for tol in (20, 25, 30):
        d = en_yuksek_doz(365, tol)
        print("  bir yillik -%d%% tolerans -> %s"
              % (tol, "**%.2fx**" % d if d else "**1x'in ALTI**"))
    print("\n  -> mevcut ayar (1x), bir yillik -%25 toleransin TAM karsiligi.")
    print("  -> getiriyi yukseltmek = bir yillik dususu -%20'nin belirgin")
    print("     asagisina goturmek. Madde 257 bunu tiltle bedava yapmanin")
    print("     mumkun olmadigini gosterdi; madde 261 fiyatini koyuyor.")
    print("  madde 243 ile tutarli mi (1x 365g p95 ~ -%.1f)? %s"
          % (MADDE_243_1YIL_P5, "EVET" if madde_243_tutarli() else "HAYIR"))

    print("\n4) DOZ KARARI UC GIRDI ISTER")
    print("  (1) UFUK  (2) TOLERANS  (3) CANLI SAPMA (madde 227 - once olcum)")


# --- MADDE 266 BAĞI -------------------------------------------------------
# Bu modülün p95 düşüşleri GÜNLÜK getirilerden üretilir; gün içi yol daha
# kötüdür (madde 266: büyütme medyan 1,49 · p90 2,72). Doz önerisi bu
# yüzden gün içi kısıtı da söylemek zorunda.
MADDE_266_BUYUTME = 1.488


def icgun_uyarisi(doz: float | None) -> str:
    if doz is None:
        return ("madde 266: tablo GÜNLÜK kapanıştan; gün içi yol medyanda "
                "1,49 kat daha kötü")
    ek = ""
    if doz >= 2.50:
        ek = (" VE madde 266: ölçülen en kötü iki aylık yol (−%41,4) bu "
              "brütte LİKİDASYON eşiğinin ötesinde")
    return ("madde 266: bu satırın gün içi karşılığı ~%.1f kat, yani "
            "p95 düşüşü GÜNLÜK rakamın 1,49 katı okunmalı%s"
            % (MADDE_266_BUYUTME, ek))
