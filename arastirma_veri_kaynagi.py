"""MADDE 253: API ERISIMI COZULDU - ve madde 252'nin KAPSAM GEREKCESI YANLISTI.

Kullanicinin istegi: "API erisimini sen yap". Yapildi - ama is bitmeden
once kendi onceki turumda bir hata buldum ve bu madde once onu duzeltiyor.

================================================================
1) ERISIM: fapi KAPALI, ARSIV ACIK
================================================================
  https://fapi.binance.com/fapi/v1/ping          -> **451**
  https://data-api.binance.vision/api/v3/ping    -> 200
  https://data.binance.vision/...                -> 200
  https://s3-ap-northeast-1.amazonaws.com/data.binance.vision  -> 200 (listeleme)

451 cografi bir kisit, proxy reddi DEGIL. Binance'in resmi halka acik veri
arsivi (`data.binance.vision`) ayri altyapida ve ERISILEBILIR. Listeleme
HTML donduruyor; dizin dokumu icin S3 ucu kullanilmali.

ARSIVDE NE VAR (futures/um):
  gunluk : aggTrades, bookDepth, bookTicker, indexPriceKlines, klines,
           markPriceKlines, **metrics**, premiumIndexKlines, trades
  aylik  : ayni liste AMA metrics YOK ve bookDepth YOK; buna karsilik
           **fundingRate** aylik var
  metrics dosyasi: 5 DAKIKALIK (289 satir/gun), 2020-09'dan beri, kolonlar:
    sum_open_interest · sum_open_interest_value · count_long_short_ratio
    count_toptrader_long_short_ratio · sum_toptrader_long_short_ratio
    sum_taker_long_short_vol_ratio

YOL KALIBI:
  .../data/futures/um/daily/metrics/<SEM>/<SEM>-metrics-<YYYY-MM-DD>.zip
  .../data/futures/um/monthly/fundingRate/<SEM>/<SEM>-fundingRate-<YYYY-MM>.zip

OLCULEN HIZ: 24 es zamanli baglantiyla ~63 dosya/saniye, sifir hata.
Yani 124.712 gunluk metrics dosyasi ~33 dakika. Ham dosya saklanmamali;
bellekte acilip 4 saatlik bara indirgenmeli (zip 11 KB, CSV ~10 kat).

================================================================
2) HATA KAYDI: MADDE 252 YANLIS KAYNAKTAN OLCTU
================================================================
Madde 252 acik pozisyonu `data_oi/` klasorunden olctu: 60 sembol, GUNLUK,
ve uygun evrenin **%51'i**. O yuzden turu su cumleyle sinirladim:
"olcum kitabin en zayif ucte biri uzerinde" - ve yeniden acma kosulunu
"kapsam %85'e cikinca" diye yazdim.

**IKISI DE YANLISTI.** Uretim backtest'inin HER KOSUMDA kullandigi panel
`/tmp/metrik_panel.pkl` `sum_open_interest_value` sutununu **zaten
tasiyor**: 619 sembol, 2022-07-18 -> 2026-08-31, uygun evren kapsami
**%97,7** (2023 %100,0 · 2024 %98,3 · 2025 %99,9 · 2026 %89,2 - en yeni
listelemeler geriden geliyor). Ustelik motorda `g33.py oi 5` modu zaten
o sutuna bagli duruyordu (madde 117'nin biraktigi kanca).

Yani `data_oi/` eski, ayri ve KISMI bir indirmeydi; ben projenin kendi
tam verisini gormeden yanindaki yarim dosyayi olctum. Yeniden acma
kosulu zaten KARSILANMISTI - emekli edildi.

NASIL YAKALANDI: kullanicinin "API erisimini sen yap" istegi uzerine
indirmeyi planlarken motorun hangi paneli okudugunu inceledim ve `oi`
modunu gordum. Yani hatayi, ihtiyaci olmayan bir isi yapmaya hazirlanirken
buldum. **Ders: yeni veri indirmeden once projenin ELINDE olani denetle.**
`data_oi/` artik KULLANILMAMALI (ikinci, yaniltici kaynak).

================================================================
3) DOGRU OLCUM: TAM EVREN, HAVUZ ACIK, URETIM KONTROLU
================================================================
Kontrol: +%112,3 · Sharpe 2,939 · 22-24 2,789 · 25-26 3,147 · -%14,5

  aday                              yillik  Sharpe   22-24   25-26  dusus  esit-risk
  OI degisimi = KALABALIK olcutu     +44,0   1,963   1,977   1,954  -16,6      +37,6
  funding x OI yuksekligi           +103,7   2,807   2,608   3,077  -18,8      +72,7
  funding x OI degisimi (24sa)      +108,2   2,875   2,735   3,069  -14,9     +104,6

UCU DE SART 1'DEN RED. En iyi aday icin esli blok bootstrap (4.000 ornek,
20 gunluk blok, esit riskte): ort **-9,5 puan**  std 12,4  **P(>0) %19,7**.

EN OGRETICI SATIR BIRINCISI: kalabalik olcutunu (globalLongShortAccount-
Ratio) OI degisimiyle DEGISTIRMEK kitabi +%112,3'ten **+%44,0**'a
dusuruyor. Yani havuz secimi gercek is yapiyor ve OI onun yerine KOTU bir
vekil. Madde 252'nin "OI, funding'in gurultulu esi" dersi tam evrende de
ayakta - ama artik kapsam mazereti olmadan.

MADDE 252'NIN SONUCU AYAKTA, GEREKCESI DEGISTI: acik pozisyon kitaba bir
sey eklemiyor; bu bir veri eksikligi sonucu DEGIL, olculmus bir sonuc.

================================================================
4) BUNUN KALICI DEGERI: /tmp KIRILGANLIGI
================================================================
Bu tur bir isletme riski de ortaya cikardi: uretim backtest'i
`/tmp/sk_bar48.pkl` ve `/tmp/metrik_panel.pkl` dosyalarina bagli. Bunlar
GECICI dizinde; silinirse kontrol kosumu (+%112,3) yeniden uretilemez ve
kalabalik secimi calismaz. Bugune kadar bunun yedegi YOKTU.

Artik var: arsiv erisimi dogrulandi, yol kaliplari ve hiz olculdu, yeniden
kurma receti asagida (`YENIDEN_KURMA`). Bir kayip durumunda metrics paneli
~33 dakikada, funding paneli aylik dosyalardan ~2 dakikada yeniden kurulur.

Kosum: python3 arastirma_veri_kaynagi.py
"""

ERISIM = {
    "fapi.binance.com/fapi/v1/ping": 451,
    "data-api.binance.vision/api/v3/ping": 200,
    "data.binance.vision (indirme)": 200,
    "s3-ap-northeast-1.amazonaws.com/data.binance.vision (listeleme)": 200,
}
ARSIV_GUNLUK = ["aggTrades", "bookDepth", "bookTicker", "indexPriceKlines",
                "klines", "markPriceKlines", "metrics", "premiumIndexKlines",
                "trades"]
ARSIV_AYLIK = ["aggTrades", "bookTicker", "fundingRate", "indexPriceKlines",
               "klines", "markPriceKlines", "premiumIndexKlines", "trades"]
METRIK_KOLON = ["sum_open_interest", "sum_open_interest_value",
                "count_long_short_ratio", "count_toptrader_long_short_ratio",
                "sum_toptrader_long_short_ratio", "sum_taker_long_short_vol_ratio"]
YOL = {
    "metrics": ("https://data.binance.vision/data/futures/um/daily/metrics/"
                "{SEM}/{SEM}-metrics-{YYYY-MM-DD}.zip"),
    "fundingRate": ("https://data.binance.vision/data/futures/um/monthly/"
                    "fundingRate/{SEM}/{SEM}-fundingRate-{YYYY-MM}.zip"),
    "listeleme": ("https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
                  "?delimiter=/&prefix=data/futures/um/daily/metrics/"),
}
HIZ = dict(es_zamanli=24, dosya_saniye=63, hata=0, zip_kb=11, cozunurluk_dk=5)

# --- madde 252'nin duzeltilmesi ---
MADDE_252_IDDIA = dict(kaynak="data_oi/", sembol=60, cozunurluk="gunluk", kapsam=51)
GERCEK = dict(kaynak="/tmp/metrik_panel.pkl", sembol=619, cozunurluk="4 saatlik",
              kapsam=97.7, bas="2022-07-18", son="2026-08-31")
KAPSAM_YILLARA = {2022: 99.6, 2023: 100.0, 2024: 98.3, 2025: 99.9, 2026: 89.2}
EMEKLI_KOSUL = ("madde 252'nin 'kapsam %85 olunca yeniden ac' kosulu - zaten "
                "karsilanmisti (%97,7), EMEKLI EDILDI")
KULLANILMAZ = "data_oi/  (eski, kismi, yaniltici - madde 253'te emekli)"

# --- dogru olcum ---
KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)
VARYANT = {   # (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk)
    "OI degisimi = KALABALIK olcutu": (44.0, 1.963, 1.977, 1.954, -16.6, 37.6),
    "funding x OI yuksekligi": (103.7, 2.807, 2.608, 3.077, -18.8, 72.7),
    "funding x OI degisimi (24sa)": (108.2, 2.875, 2.735, 3.069, -14.9, 104.6),
}
BOOTSTRAP = dict(aday="funding x OI degisimi (24sa)", ort=-9.5, std=12.4,
                 p_pozitif=19.7, ornek=4000)

YENIDEN_KURMA = """
1) SEMBOL LISTESI: S3 listelemesi (YOL['listeleme']), CommonPrefixes.
2) METRICS PANELI (/tmp/metrik_panel.pkl):
   her sembol-gun icin metrics zip'i cek, bellekte ac, 4 saatlik bara
   indirge (OI icin 'last', oranlar icin 'mean'), ham dosyayi ATMA.
   24 es zamanli baglanti, ~63 dosya/sn. Yalnizca UYGUN gunler + 35 gun
   isinma indirilir (tam gecmis DEGIL) -> ~125 bin dosya, ~33 dk.
3) FUNDING PANELI: monthly/fundingRate cok daha kucuk (~50 dosya/sembol).
4) SK_BAR48 (/tmp/sk_bar48.pkl): funding panelinden 48 saatlik pencere;
   tanimi g33.py'nin bekledigi olcekte olmali (madde 209/210 paritesi!).
   Yeniden kurulduktan sonra MUTLAKA kontrol kosumu ile parite alinir:
   +%112,3 / Sharpe 3,10 / dusus -14,5 (FAZ_KAY=0).
"""


def arsiv_erisilebilir():
    """fapi kapali ama arsiv acik mi?"""
    return (ERISIM["fapi.binance.com/fapi/v1/ping"] == 451
            and ERISIM["data.binance.vision (indirme)"] == 200)


def madde252_kapsam_iddiasi_yanlis():
    """252'nin kapsam gerekcesi gercekten yanlis miydi?"""
    return GERCEK["kapsam"] > 90 > MADDE_252_IDDIA["kapsam"]


def ucu_de_red():
    """Sart 1'i gecen OI varyanti var mi? (tam evren, havuz acik)"""
    return [a for a, v in VARYANT.items()
            if v[2] > KONTROL["erken"] and v[3] > KONTROL["gec"]]


def havuz_olcutu_is_yapiyor():
    """Kalabalik olcutunu OI ile degistirmek kitabi yariya mi indiriyor?"""
    return VARYANT["OI degisimi = KALABALIK olcutu"][0] < KONTROL["yillik"] / 2


if __name__ == "__main__":
    print("MADDE 253 - API ERISIMI + MADDE 252'NIN DUZELTILMESI\n")
    print("1) ERISIM")
    for u, c in ERISIM.items():
        print("  %-62s%4d" % (u, c))
    print("  arsiv erisilebilir mi? %s" % ("EVET" if arsiv_erisilebilir() else "HAYIR"))
    print("  gunluk veri setleri : %s" % ", ".join(ARSIV_GUNLUK))
    print("  aylik veri setleri  : %s" % ", ".join(ARSIV_AYLIK))
    print("  olculen hiz: %d es zamanli, %d dosya/sn, %d hata, cozunurluk %d dk"
          % (HIZ["es_zamanli"], HIZ["dosya_saniye"], HIZ["hata"], HIZ["cozunurluk_dk"]))

    print("\n2) HATA KAYDI - MADDE 252 YANLIS KAYNAKTAN OLCTU")
    print("  252'nin kullandigi : %-24s %3d sembol, %-9s kapsam %%%d"
          % (MADDE_252_IDDIA["kaynak"], MADDE_252_IDDIA["sembol"],
             MADDE_252_IDDIA["cozunurluk"], MADDE_252_IDDIA["kapsam"]))
    print("  GERCEK panel       : %-24s %3d sembol, %-9s kapsam %%%.1f"
          % (GERCEK["kaynak"], GERCEK["sembol"], GERCEK["cozunurluk"],
             GERCEK["kapsam"]))
    print("  yillara gore kapsam: %s"
          % "  ".join("%d %%%.1f" % (y, k) for y, k in KAPSAM_YILLARA.items()))
    print("  kapsam iddiasi yanlis miydi? %s"
          % ("EVET" if madde252_kapsam_iddiasi_yanlis() else "HAYIR"))
    print("  %s" % EMEKLI_KOSUL)
    print("  KULLANILMAZ: %s" % KULLANILMAZ)

    print("\n3) DOGRU OLCUM (tam evren, havuz acik)")
    print("  %-34s%8s%8s%8s%8s%8s%10s"
          % ("", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk"))
    print("  %-34s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f"
          % ("KONTROL", KONTROL["yillik"], KONTROL["sharpe"], KONTROL["erken"],
             KONTROL["gec"], KONTROL["dusus"], KONTROL["yillik"]))
    for a, v in VARYANT.items():
        print("  %-34s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("\n  sart 1'i gecen: %s" % (ucu_de_red() or "YOK (3/3 RED)"))
    print("  bootstrap (%s): ort %+.1f puan  P(>0) %%%.1f"
          % (BOOTSTRAP["aday"], BOOTSTRAP["ort"], BOOTSTRAP["p_pozitif"]))
    print("  kalabalik olcutu gercek is yapiyor mu? %s"
          % ("EVET - OI ile degistirmek kitabi yariya indiriyor"
             if havuz_olcutu_is_yapiyor() else "HAYIR"))

    print("\n4) /tmp KIRILGANLIGI - YENIDEN KURMA RECETESI")
    print(YENIDEN_KURMA)
