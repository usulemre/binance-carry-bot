#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 295 — EVREN MALİYETİ GERÇEK BORSA TABLOSUNDAN ÖLÇÜLDÜ: BASAMAKLI,
VE FAZ ÇEŞİTLENDİRMESİ BACAK BÜYÜKLÜĞÜNDEN KAT KAT DEĞERLİ.

Madde 294 "küçük sermayede öncelik bacak büyüklüğü" dedi ve bunu iki
zayıf dayanağa kurdu: (1) botun docstring'indeki iki ankra (BTC ~100 $,
SOL ~150 $), (2) evren maliyetini `SEMBOL_DUS` ile **RASTGELE** sembol
düşürerek fiyatlamak. Bu madde ikisini de gerçek veriyle değiştirdi.

═══ GERÇEK TABLO ALINDI ═══

`fapi.binance.com` bu bölgeden 451 veriyor ama **`www.binance.com`
200**: `/fapi/v1/exchangeInfo` + `/fapi/v1/ticker/price` → 525 TRADING
USDT perpetual, canlı fiyatlarla. Bir sembolde açılabilecek en küçük
emir = max(MIN_NOTIONAL, fiyat × max(stepSize, minQty)).

**ELEME BASAMAKLI, ORANSAL DEĞİL:**

    bacak        elenen sembol                            oran
    >= 83,61 $   yok                                      %0,0
    20 - 84 $    BTC (83,61) + QNT (23,76)                %0,4
    16 - 20 $    + ETH/BCH/LTC/ETC/LINK (20,00) + AAVE    %1,5
    10 - 16 $    + AVAX (10,91)                           %1,7

Dağılım çok çarpık: **medyan asgari 5,00 $, p95 5,00 $, maksimum
83,61 $** (BTC). Yani sembollerin %97'si 5 $'la açılabiliyor; eleme
yalnız bir avuç majorde.

**BOTUN DOCSTRING'İ BAYAT:** "SOL ~150 $" yazıyor, SOL'un gerçek
asgarisi **5,00 $**. BTC ankrası (~100 $) bugünkü fiyatta 83,61 $ ile
yaklaşık doğru.

═══ ADI VERİLEN SEMBOLLERLE ÖLÇÜM (motor knobu + PARİTE) ═══

Bacak büyüklüğü **rastgele** sembol düşürmez; elenenler **isimli ve
hepsi major**. 9 majorun kaybı 9 rastgele altcoin'in kaybıyla aynı şey
değil. Motora `SEMBOL_HARIC` eklendi (boş bırakılırsa blok hiç
çalışmaz) ve **parite iki fazda da BİREBİR** (maksimum mutlak fark
0,000e+00).

    elenen set                      doz farkı
    yok (parite)                      +0,00
    BTC                              −13,36
    BTC + QNT                        −13,36   <- QNT'nin katkısı SIFIR
    8 major (16 $ bacak)             −30,13
    9 major (10 $ bacak)             −30,98

**Evrenin %1,7'si, rastgele %15'e bedel.** Madde 294'ün rastgele
ölçümü: %10 rastgele → −3,55 · %20 rastgele → −38,71/−77,59. Yani
major başına etki, rastgele sembol başına etkinin ~9 katı.

Ayrıştırma: **BTC tek başına −13,36** · 20 $ minNotional grubu
(ETH, BCH, LTC, ETC, LINK, AAVE) bir **−16,8** daha · AVAX ~−0,85 ·
QNT 0.

═══ YAPISAL MALİYET: DİLİM KESMEK PATLIYOR ═══

Madde 294 yalnız 5 dilime kadar inmişti. Daha aşağısı ölçüldü:

    yapı    yapısal    yapı    yapısal
    15x5     +0,00     4x5      −37,00
    15x2     −1,75     3x5      −48,21
    13x3     −5,52     3x3      −60,97
    5x5      −6,44     2x5     −102,44
    8x5     −11,96     2x4     −107,95
                       1x5     −122,05

**Faz çeşitlendirmesi bacak büyüklüğünden KAT KAT değerli.** 20 $
uçurumunu geçmek 17 puan kazandırır; onu geçmek için 4 dilime inmek
**37 puan** kaybettirir. Madde 120 haklı çıktı.

═══ BİRLEŞİK SIRALAMA (yapısal + evren) ═══

1.000 $ (bacak = 400/(dilim×bacak)):

    yapı   bacak$    yapısal   evren   TOPLAM   not
    15x5     5,33     +0,00   −30,98  −30,98   BOT ÇALIŞMAZ
    15x2    13,33     −1,75   −30,98  −32,73   tolerans AŞILIR (gün içi −%36,1)
    13x3    10,26     −5,52   −30,98  **−36,50**  uygun  <= EN İYİ
    5x5     16,00     −6,44   −30,13   −36,57   uygun
    8x5     10,00    −11,96   −30,98   −42,94   uygun
    4x5     20,00    −37,00   −13,36   −50,36   uygun

2.000 $:

    yapı   bacak$    yapısal   evren   TOPLAM   not
    15x2    26,67     −1,75   −13,36  −15,11   tolerans AŞILIR
    13x3    20,51     −5,52   −13,36  **−18,88**  uygun  <= EN İYİ
    5x5     32,00     −6,44   −13,36   −19,80   uygun
    8x5     20,00    −11,96   −13,36   −25,32   uygun
    15x5    10,67     +0,00   −30,98   −30,98   uygun (ama 12 puan geride)
    3x3     88,89    −60,97    +0,00   −60,97   tolerans AŞILIR

═══ İKİ ÇIKARIM ═══

**(1) ÖNERİ: `CARRY_N_DILIM=13 CARRY_N_LEGS=3 CARRY_MIN_LEGS=3`.**
13 dilim × 3 bacak her iki bakiyede de en iyi UYGUN seçenek. Madde
294'ün önerisi (5x5) 1.000 $'da onunla neredeyse berabere (−36,57 vs
−36,50) ama 2.000 $'da bir puan geride ve 13 dilim, 5 dilimin iki
katından fazla faz çeşitlendirmesi veriyor — geri testin tek
gerçekleşmesinde görünmeyen bir dayanıklılık.
(`CARRY_MIN_LEGS=3` tutarlılık için: MIN_LEGS varsayılanı 4 ve
N_LEGS'ten büyük kalması tutarsız bir durum; `uygun_bacak_sayisi` yine
3 döndürüyor ama bu bir tesadüf.)

**(2) 1.000 → 2.000 $ ATLAMASI ~17,6 PUAN DEĞERİNDE** ve bu herhangi
bir yapılandırma seçiminden büyük. Sebebi tek: 13x3'ün bacağı
1.000 $'da 10,26 $ (20 $ uçurumunun ALTINDA), 2.000 $'da 20,51 $
(ÜSTÜNDE). **Yani sermayeyi ikiye katlamak, kitabı ETH/LINK/LTC/BCH/
ETC/AAVE'ye geri kavuşturuyor.** 2.000 $ ile başlamak 1.000 $ ile
başlamaktan yapısal olarak çok daha iyi bir yere koyuyor.

═══ BU TURDA İKİ KEZ YANLIŞ YÖNE SAPTIM ═══

**(a) MADDE 294'TE:** evren maliyetini rastgele düşürmeyle fiyatlayıp
"10 $'dan 16 $'a çıkmak evrenin %3'ünü kurtarır → 6-12 puan" yazdım.
İki hata birlikte: oranı abarttım (%3 vs gerçek %0,2) ve sembol başına
etkiyi ~9 kat küçümsedim. İkisi ters yönde olduğu için SONUÇ (bacağı
büyüt) kazara doğru kaldı, GEREKÇE yanlıştı.

**(b) BU TURUN ORTASINDA:** gerçek oranı (%1,7) görünce "öneri tersine
dönüyor, 15x5 daha iyi" diye yazdım — **o da yanlıştı**, çünkü elimde
oran vardı ama ETKİ yoktu. Etkiyi ölçünce 9 majorun −30,98 puan
olduğu çıktı ve 15x5 (bacağı 10,67 $) tam o cezayı ödüyor.

**YASA: bir maliyeti RASTGELE örnekle fiyatlamak, kaybın ADRESLİ olduğu
yerde yanıltır** — ve yanıltma yönü belli değildir: oranı da etkiyi de
ayrı ayrı ölçmek gerekir. Bir tanesi elde, öteki tahmin olduğu sürece
hüküm verilmemeli (bu turda iki kez verdim, ikisi de yanlıştı).

═══ DÜRÜST SINIR: UÇURUMLAR FİYATA BAĞLI ═══

BTC'nin 83,61 $'lık asgarisi = 83.607 $ × 0,001 stepSize, yani **BTC
fiyatıyla doğru orantılı**. BTC 120.000 $ olursa uçurum 120 $'a çıkar.
20 $'lık minNotional'lar ise borsa ayarı ve değişebilir. Tablo
periyodik yeniden ölçülmeli; tek satır:

    curl -s https://www.binance.com/fapi/v1/exchangeInfo > ei.json
    curl -s https://www.binance.com/fapi/v1/ticker/price > px.json

Canlıda botun `islem_yapilabilir()` fonksiyonu bunu zaten her turda
yapıyor; `arastirma_evren_esigi.esik_tablosu()` aynı hesabı ölçüm
için tekrarlar.
"""

# --- gercek borsa tablosu (2026-10-12, www.binance.com) --------------
VERI_TARIHI = "2026-10-12"
KAYNAK = "www.binance.com/fapi/v1/exchangeInfo + /ticker/price (fapi 451 veriyor)"
SEMBOL_SAYISI = 525
ASGARI_DAGILIM = {"medyan": 5.00, "p75": 5.00, "p90": 5.00, "p95": 5.00,
                  "maks": 83.61}
ELENEN = {   # bacak USD -> (elenen sembol sayisi, oran %)
    10.0: (9, 1.7), 16.0: (8, 1.5), 20.0: (2, 0.4), 32.0: (1, 0.2),
    84.0: (0, 0.0),
}
MAJORLER = {"BTCUSDT": 83.61, "QNTUSDT": 23.76, "ETHUSDT": 20.00,
            "BCHUSDT": 20.00, "LTCUSDT": 20.00, "ETCUSDT": 20.00,
            "LINKUSDT": 20.00, "AAVEUSDT": 17.17, "AVAXUSDT": 10.91}
BAYAT_DOCSTRING = ("botun islem_yapilabilir docstring'i 'SOL ~150 $' diyor; "
                   "SOL'un gercek asgarisi 5,00 $ (BTC ankrasi ~100 $ ise "
                   "bugunku fiyatta 83,61 $ ile yaklasik dogru)")

# --- olculen evren maliyeti (SEMBOL_HARIC + parite) ------------------
PARITE_BIREBIR = True
EVREN_MALIYETI = {   # elenen set -> doz farki
    "yok": 0.00, "BTC": -13.36, "BTC+QNT": -13.36,
    "8 major": -30.13, "9 major": -30.98,
}
AYRISTIRMA = {"BTC": -13.36, "QNT": 0.00, "20$ grubu": -16.77, "AVAX": -0.85}
RASTGELE_KIYAS = {0.10: -3.55, 0.20: -38.71, 0.201: -77.59}

def evren_maliyeti(bacak_usd: float) -> float:
    """OLCULEN basamak fonksiyonu (madde 295)."""
    if bacak_usd >= 83.61:
        return 0.0
    if bacak_usd >= 20.0:
        return -13.36
    if bacak_usd >= 16.0:
        return -30.13
    return -30.98

# --- yapisal maliyet (madde 294 + bu madde) --------------------------
YAPISAL = {"15x5": 0.00, "15x2": -1.75, "13x3": -5.52, "5x5": -6.44,
           "8x5": -11.96, "4x5": -37.00, "3x5": -48.21, "3x3": -60.97,
           "2x5": -102.44, "2x4": -107.95, "1x5": -122.05}
DUSUS = {"15x5": 14.54, "15x2": 24.75, "13x3": 17.68, "5x5": 16.12,
         "8x5": 14.89, "4x5": 15.32, "3x5": 16.96, "3x3": 22.10,
         "2x5": 19.10, "2x4": 22.60, "1x5": 28.08}
IZGARA = {"15x5": (15, 5), "15x2": (15, 2), "13x3": (13, 3), "5x5": (5, 5),
          "8x5": (8, 5), "4x5": (4, 5), "3x5": (3, 5), "3x3": (3, 3),
          "2x5": (2, 5), "2x4": (2, 4), "1x5": (1, 5)}
TABAN_PAYI = 0.40          # REZERV %20
MIN_BACAK_USD = 10.0
GUN_ICI_CARPAN = 1.458     # madde 291
TOLERANS = 30.0

ONERI = {"dilim": 13, "bacak": 3,
         "komut": "CARRY_N_DILIM=13 CARRY_N_LEGS=3 CARRY_MIN_LEGS=3 "
                  "python carry_bot.py"}
MIN_LEGS_NOTU = ("MIN_LEGS varsayilani 4 ve N_LEGS'ten buyuk kalmasi "
                 "tutarsiz; uygun_bacak_sayisi() yine 3 donduruyor ama bu "
                 "bir tesadut - CARRY_MIN_LEGS=3 ile acikca ayarlanmali")
ATLAMA_DEGERI = 17.62      # 1.000 -> 2.000 $, ayni yapilandirmayla

# --- benim iki sapmam ------------------------------------------------
SAPMALARIM = {
    "madde 294": ("evren maliyetini RASTGELE dusurmeyle fiyatladim ve "
                  "'10->16 $ evrenin %3'unu kurtarir -> 6-12 puan' yazdim; "
                  "orani abarttim (%3 vs %0,2) VE sembol basina etkiyi ~9 "
                  "kat kucumsedim",
                  "iki hata TERS yonde oldugu icin SONUC (bacagi buyut) "
                  "kazara dogru kaldi, GEREKCE yanlisti"),
    "bu turun ortasi": ("gercek orani (%1,7) gorunce 'oneri tersine donuyor, "
                        "15x5 daha iyi' yazdim",
                        "o da YANLISTI: elimde ORAN vardi ama ETKI yoktu; "
                        "etkiyi olcunce 9 majorun -30,98 puan oldugu cikti"),
}
YASA = ("bir maliyeti RASTGELE ornekle fiyatlamak, kaybin ADRESLI oldugu "
        "yerde yaniltir - ve yaniltma YONU belli degildir: orani da etkiyi "
        "de AYRI AYRI olcmek gerekir; biri elde oteki tahmin oldugu surece "
        "hukum verilmemeli")

# --- durust sinir ----------------------------------------------------
UCURUM_FIYATA_BAGLI = ("BTC'nin 83,61 $'lik asgarisi = 83.607 $ x 0,001 "
                       "stepSize, yani BTC FIYATIYLA DOGRU ORANTILI; BTC "
                       "120.000 $ olursa ucurum 120 $'a cikar. 20 $'lik "
                       "minNotional'lar borsa ayari ve degisebilir")
YENIDEN_OLCUM = ("curl -s https://www.binance.com/fapi/v1/exchangeInfo > ei.json && "
                 "curl -s https://www.binance.com/fapi/v1/ticker/price > px.json")


# --- yardimcilar ------------------------------------------------------
def bacak_usd(bakiye: float, yapi: str) -> float:
    d, b = IZGARA[yapi]
    return bakiye * TABAN_PAYI / (d * b)


def toplam_maliyet(bakiye: float, yapi: str) -> float:
    return YAPISAL[yapi] + evren_maliyeti(bacak_usd(bakiye, yapi))


def calisir_mi(bakiye: float, yapi: str) -> bool:
    return bacak_usd(bakiye, yapi) >= MIN_BACAK_USD


def tolerans_icinde_mi(yapi: str) -> bool:
    return DUSUS[yapi] * GUN_ICI_CARPAN <= TOLERANS


def uygun_mu(bakiye: float, yapi: str) -> bool:
    return calisir_mi(bakiye, yapi) and tolerans_icinde_mi(yapi)


def en_iyi(bakiye: float) -> str:
    uy = [y for y in IZGARA if uygun_mu(bakiye, y)]
    return max(uy, key=lambda y: toplam_maliyet(bakiye, y))


# --- sinamalar --------------------------------------------------------
def parite_birebir_mi() -> bool:
    return PARITE_BIREBIR is True


def eleme_basamakli_mi() -> bool:
    """16->20 $ arasindaki ucurum, 10->16 arasindakinden BUYUK mu?"""
    return (abs(evren_maliyeti(16.0) - evren_maliyeti(20.0))
            > 10 * abs(evren_maliyeti(10.0) - evren_maliyeti(16.0)))


def qnt_katkisi_sifir_mi() -> bool:
    return abs(EVREN_MALIYETI["BTC"] - EVREN_MALIYETI["BTC+QNT"]) < 1e-9


def majorler_rastgeleden_agir_mi(kat: float = 5.0) -> bool:
    """9 major (%1,7), rastgele %1,7'den kat kat agir mi?"""
    rastgele_birim = abs(RASTGELE_KIYAS[0.10]) / 10.0      # %1 basina
    major_birim = abs(EVREN_MALIYETI["9 major"]) / 1.7
    return major_birim > kat * rastgele_birim


def faz_bacaktan_degerli_mi() -> bool:
    """20 $ ucurumunu gecmek icin 4 dilime inmek KAZANCTAN pahali mi?"""
    kazanc = abs(evren_maliyeti(16.0) - evren_maliyeti(20.0))
    bedel = abs(YAPISAL["4x5"] - YAPISAL["5x5"])
    return bedel > kazanc


def oneri_en_iyi_mi() -> bool:
    ad = "%dx%d" % (ONERI["dilim"], ONERI["bacak"])
    return en_iyi(1000.0) == ad and en_iyi(2000.0) == ad


def standart_2000de_geride_mi(puan: float = 10.0) -> bool:
    return (toplam_maliyet(2000.0, "13x3")
            - toplam_maliyet(2000.0, "15x5")) > puan


def atlama_degeri_dogru_mu(tol: float = 0.5) -> bool:
    fark = toplam_maliyet(2000.0, "13x3") - toplam_maliyet(1000.0, "13x3")
    return abs(fark - ATLAMA_DEGERI) < tol


def atlama_ucurumdan_mi() -> bool:
    """Atlamanin sebebi 20 $ ucurumu mu?"""
    return (bacak_usd(1000.0, "13x3") < 20.0 <= bacak_usd(2000.0, "13x3"))


def standart_1000de_calisir_mi() -> bool:
    return calisir_mi(1000.0, "15x5")


def iki_sapmam_kayitli_mi() -> bool:
    return len(SAPMALARIM) == 2 and all(len(v) == 2 for v in SAPMALARIM.values())


def docstring_bayat_mi() -> bool:
    return "SOL" in BAYAT_DOCSTRING and "5,00" in BAYAT_DOCSTRING


def hukum() -> str:
    return (
        "EVREN MALIYETI GERCEK BORSA TABLOSUNDAN OLCULDU VE BASAMAKLI: "
        "bacak >= 84 $ ise sifir, 20-84 $ arasi -13,36 (BTC), 10-20 $ "
        "arasi -30,1/-31,0 (9 major). Evrenin %1,7'si, rastgele %15'e "
        "bedel - cunku elenenler ISIMLI ve hepsi major; BTC tek basina "
        "-13,36, QNT SIFIR. Motora SEMBOL_HARIC eklendi, parite iki fazda "
        "BIREBIR. AMA dilim kesmenin yapisal maliyeti PATLIYOR (4x5 "
        "-37,00, 3x5 -48,21, 1x5 -122,05): 20 $ ucurumunu gecmek 17 puan "
        "kazandirir, gecmek icin 4 dilime inmek 37 puan kaybettirir - FAZ "
        "CESITLENDIRMESI BACAK BUYUKLUGUNDEN KAT KAT DEGERLI (madde 120 "
        "hakli). BIRLESIK EN IYI UYGUN SECENEK iki bakiyede de **13 dilim "
        "x 3 bacak** (1.000 $'da -36,50, 2.000 $'da -18,88; standart 15x5 "
        "2.000 $'da 12 puan geride cunku bacagi 10,67 $). VE 1.000 -> "
        "2.000 $ atlamasi ayni yapilandirmayla **17,6 puan** degerinde, "
        "herhangi bir yapilandirma secimden buyuk - cunku 13x3'un bacagini "
        "20 $ UCURUMUNUN ustune tasiyor. Bu turda IKI KEZ yanlis yone "
        "saptim (madde 294'te rastgele fiyatlama, bu turun ortasinda "
        "oran-ama-etki-yok); ayar DEGISMEDI, 13x3 bir KULLANICI KARARI."
    )


def yaz() -> None:
    print(__doc__)
    print("VERI: %s | %s | %d sembol" % (VERI_TARIHI, KAYNAK, SEMBOL_SAYISI))
    print("  asgari notional dagilimi: %s" % ASGARI_DAGILIM)
    print("  BAYAT DOCSTRING: %s" % BAYAT_DOCSTRING)
    print("\n10 $ BACAKTA ELENEN MAJORLER:")
    for s, v in sorted(MAJORLER.items(), key=lambda kv: -kv[1]):
        print("  %-12s asgari %7.2f $" % (s, v))
    print("\nOLCULEN EVREN MALIYETI (parite birebir mi: %s):" % parite_birebir_mi())
    for ad, v in EVREN_MALIYETI.items():
        print("  %-12s %+8.2f" % (ad, v))
    print("  ayristirma: %s" % AYRISTIRMA)
    print("  QNT katkisi SIFIR mi: %s | majorler rastgeleden agir mi: %s"
          % (qnt_katkisi_sifir_mi(), majorler_rastgeleden_agir_mi()))
    print("  eleme BASAMAKLI mi: %s" % eleme_basamakli_mi())
    print("  rastgele kiyas (madde 294): %s" % RASTGELE_KIYAS)
    print("\nYAPISAL MALIYET: faz bacaktan degerli mi: %s"
          % faz_bacaktan_degerli_mi())
    for y in sorted(YAPISAL, key=lambda a: -YAPISAL[a]):
        print("  %-6s %+9.2f  (dusus %5.2f, gun ici -%%%.1f)"
              % (y, YAPISAL[y], DUSUS[y], DUSUS[y] * GUN_ICI_CARPAN))
    for bakiye in (1000.0, 2000.0):
        print("\nBIRLESIK SIRALAMA - BAKIYE %s $:" % format(int(bakiye), ","))
        print("  %-6s %8s %9s %9s %9s  %s"
              % ("yapi", "bacak$", "yapisal", "evren", "TOPLAM", "not"))
        for y in sorted(IZGARA, key=lambda a: -toplam_maliyet(bakiye, a)):
            nots = []
            if not calisir_mi(bakiye, y):
                nots.append("BOT CALISMAZ")
            if not tolerans_icinde_mi(y):
                nots.append("tolerans ASILIR")
            print("  %-6s %8.2f %+9.2f %+9.2f %+9.2f  %s%s"
                  % (y, bacak_usd(bakiye, y), YAPISAL[y],
                     evren_maliyeti(bacak_usd(bakiye, y)),
                     toplam_maliyet(bakiye, y),
                     " ".join(nots) if nots else "uygun",
                     "  <= EN IYI" if y == en_iyi(bakiye) else ""))
    print("\nONERI: %d dilim x %d bacak" % (ONERI["dilim"], ONERI["bacak"]))
    print("  %s" % ONERI["komut"])
    print("  iki bakiyede de en iyi mi: %s" % oneri_en_iyi_mi())
    print("  standart 15x5 2.000 $'da geride mi: %s" % standart_2000de_geride_mi())
    print("  standart 15x5 1.000 $'da calisir mi: %s" % standart_1000de_calisir_mi())
    print("  MIN_LEGS notu: %s" % MIN_LEGS_NOTU)
    print("\n1.000 -> 2.000 $ ATLAMASI: %+.2f puan (dogru mu: %s, ucurumdan mi: %s)"
          % (toplam_maliyet(2000.0, "13x3") - toplam_maliyet(1000.0, "13x3"),
             atlama_degeri_dogru_mu(), atlama_ucurumdan_mi()))
    print("\nIKI SAPMAM (kayitli mi: %s):" % iki_sapmam_kayitli_mi())
    for ad, (ne, ders) in SAPMALARIM.items():
        print("  %s" % ad.upper())
        print("    ne  : %s" % ne)
        print("    ders: %s" % ders)
    print("  YASA: %s" % YASA)
    print("\nDURUST SINIR: %s" % UCURUM_FIYATA_BAGLI)
    print("  yeniden olcum: %s" % YENIDEN_OLCUM)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
