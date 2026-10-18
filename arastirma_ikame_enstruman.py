#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 296 — ELENEN MAJORLERE İKAME ENSTRÜMAN: ÖDÜL +28,5 PUAN,
MEKANİZMA ÇÖKÜYOR. BİR ENSTRÜMANI DAYANAĞI İÇİN DEĞİL SİNYALİ İÇİN
ALIRSIN.

Madde 295'te küçük sermayenin tek büyük kaybı adresliydi: 10 $ bacakta
9 major eleniyor (−30,98 puan), 20 $ bacakta yalnız BTC (−13,36).
Doğal fikir: **aynı dayanağın daha küçük asgarili başka enstrümanı
var mı?**

VAR, ve bol:

    major   USDT asgari   en iyi varyant      varyant asgarisi
    BTC        83,61 $    **BTCU**                 8,36 $
    ETH        20,00 $    ETHU / ETHUSD1           5,00 $
    LINK       20,00 $    LINKUSDC                 5,00 $
    LTC        20,00 $    LTCUSDC                  5,00 $
    BCH        20,00 $    BCHUSDC                  5,00 $
    AVAX       10,91 $    AVAXUSDC                 5,00 $
    AAVE       17,17 $    AAVEUSDC                17,14 $  (yok)
    ETC        20,00 $    -                        -       (yok)
    QNT        23,76 $    -                        -       (yok, katkisi 0)

═══ ÖNCE ÖDÜL ÖLÇÜLDÜ (reddin kirilgan kalmamasi icin) ═══

`SEMBOL_HARIC` ile: ikameler HEPSI calissa elenen set {AAVE, ETC, QNT}'ye
iner ve maliyet **−30,98 → −2,50 puana** duser. Yani odul 1.000 $'da
**+28,5 puan**, 2.000 $'da **+10,9 puan**. Kucuk bir sey degil.

═══ SONRA MEKANIZMA: FUNDING AYNI SINYAL DEGIL ═══

Bu kitabin TUM sinyali funding'dir (madde 214'un ayakta kalan yarisi:
funding bir SECICIdir). 12 aylik funding gecmisi indirildi
(`data.binance.vision`, 1095 gozlem/cift) ve karsilastirildi:

    USDT cifti   ikame        funding rho   hacim USDT / ikame (4sa)
    ETHUSDT      **ETHU**        **0,021**   1,95 milyar / 1,03 milyon
    BTCUSDT      **BTCU**        **0,180**   2,11 milyar / 1,14 milyon
    ETHUSDT      ETHUSD1           0,304     -          / 1,55 milyon
    AAVEUSDT     AAVEUSDC          0,414     19,4M      / 1,09M
    LTCUSDT      LTCUSDC           0,436     23,7M      / 2,41M
    LINKUSDT     LINKUSDC          0,455     35,3M      / 3,23M
    AVAXUSDT     AVAXUSDC          0,725     37,8M      / 3,00M
    BCHUSDT      **BCHUSDC**     **0,871**   24,1M      / 2,76M

**En degerli iki kurtarma (BTC ve ETH) tam olarak ise yaramiyor.**
ETHU'nun funding'i ETHUSDT ile neredeyse KORELASYONSUZ (0,021); BTCU
0,180. Fiyat korelasyonlari ~1 ama **funding korelasyonlari sifira
yakin**: dayanagi paylasiyorlar, carry akisini paylasmiyorlar.

Ustune: ETHU/BTCU/ETHUSD1 yalniz **187 funding gozlemi** (~2 ay; USDC
ciftlerinde 1095) — yeni listelenmis enstrumanlar, dusuk rho'nun bir
kismi kucuk ornek olabilir. Ama 2 aylik bir enstrumani, dogrulayamadigin
bir sinyalle, ana ciftin **1/1850'i** likiditesinde ticarete sokmak
zaten aday degil.

═══ CIDDIYE ALINABILIR IKI IKAME, VE NEDEN YETMIYOR ═══

Yalniz BCHUSDC (rho 0,871) ve AVAXUSDC (0,725) tam gecmisli ve yakin.
Ikisi kurtarilsa (7 major elenmis kalir): **−20,57 puan**, yani 10 $
bacakta **+10,41 puan** kazanc.

AMA: 2.000 $'da 13x3'un bacagi 20,51 $ ve BCH ile AVAX **zaten
elenmiyor** — orada bu kurtarmanin degeri SIFIR. Deger yalniz 1.000 $'da
var, ve madde 295'in onerisi zaten "2.000 $ ile basla". Yani:

  - **2.000 $'da** kalan tek kayip BTC (−13,36) ve ikamesi (BTCU)
    KULLANILAMAZ -> kayip GERI ALINAMAZ.
  - **1.000 $'da** BCH+AVAX ikamesi +10,41 puan ederdi, ama botun
    USDC-quote cift desteklemesi (farkli teminat varligi, madde 141'in
    alani), sinyalin o ciftlerin KENDI funding'inden hesaplanmasi ve
    ayri bir evren paneli gerekir. 2.000 $'da sifir deger ettigi icin
    bu insaat **degmez**.

═══ YAN BULGU: INCE QUOTE CIFTLERI DAHA COK CARRY ODUYOR ═══

Ikame ciftlerin ortalama funding'i USDT ciftlerinden SISTEMATIK olarak
yuksek: LINKUSDC **+%0,50/yil** · LTCUSDC **+%1,10** · AVAXUSDC
**+%1,41** · BCHUSDC **+%1,88** · AAVEUSDC **+%2,33**.

Bu bir IKAME bulgusu degil, bir **YENI EVREN** adayi: rho ~0,4 ile
bagimsiz bir funding akisi ve sistematik bir fazla. Ama madde 289'un
sartnamesi gecerli: yeni bir kitap TEK BASINA Sharpe >= 2,5 ister ve
bunu bilmek o evreni bastan kurmayi gerektirir (USDC panelini indirip
motoru o evrende kosmak). Bu maddede YAPILMADI; sicile acik bir
eksen olarak gecti.

═══ YASALAR ═══

**BIR ENSTRUMANI DAYANAGI ICIN DEGIL SINYALI ICIN ALIRSIN.** "Ayni
dayanak, daha kucuk asgari" bir ikame gibi gorunur; strateji funding
uzerine kuruluysa farkli funding = **farkli islem**. ETHU'nun ETH ile
fiyat korelasyonu ~1, funding korelasyonu 0,021.

**ODULU OLCMEDEN REDDETMEK, REDDI KIRILGAN BIRAKIR.** +28,5 puanlik bir
odulun orada oldugunu bilmek, mekanizmanin NEREDE coktugunu olcmeyi
zorunlu kilar - yoksa fikir alti ay sonra geri gelir ve yeniden
tartisilir. Bu maddede once odul, sonra mekanizma olculdu.
"""

# --- ikame tablosu: major -> (USDT asgari, varyant, varyant asgarisi) -
IKAME = {
    "BTC": (83.61, "BTCU", 8.36), "ETH": (20.00, "ETHU / ETHUSD1", 5.00),
    "LINK": (20.00, "LINKUSDC", 5.00), "LTC": (20.00, "LTCUSDC", 5.00),
    "BCH": (20.00, "BCHUSDC", 5.00), "AVAX": (10.91, "AVAXUSDC", 5.00),
    "AAVE": (17.17, "AAVEUSDC", 17.14), "ETC": (20.00, None, None),
    "QNT": (23.76, None, None),
}

# --- odul (SEMBOL_HARIC ile olculdu) ---------------------------------
ODUL = {
    "hic eleme yok": 0.00,
    "ikameler HEPSI calissa (AAVE+ETC+QNT yok)": -2.50,
    "yalniz BCH+AVAX kurtarilsa (7 major yok)": -20.57,
    "9 major yok (10 $ bacak, GERCEK)": -30.98,
    "BTC yok (20 $ bacak, GERCEK)": -13.36,
}

# --- funding karsilastirmasi: (USDT, ikame) -> (n, rho, hacim_usdt, hacim_ikame)
FUNDING = {
    ("ETHUSDT", "ETHU"): (187, 0.0207, 1.95e9, 1.03e6),
    ("ETHUSDT", "ETHUSD1"): (181, 0.3042, 1.95e9, 1.55e6),
    ("BTCUSDT", "BTCU"): (187, 0.1795, 2.11e9, 1.14e6),
    ("AAVEUSDT", "AAVEUSDC"): (1095, 0.4141, 1.94e7, 1.09e6),
    ("LTCUSDT", "LTCUSDC"): (1095, 0.4359, 2.37e7, 2.41e6),
    ("LINKUSDT", "LINKUSDC"): (1095, 0.4547, 3.53e7, 3.23e6),
    ("AVAXUSDT", "AVAXUSDC"): (1095, 0.7254, 3.78e7, 3.00e6),
    ("BCHUSDT", "BCHUSDC"): (1095, 0.8712, 2.41e7, 2.76e6),
}
RHO_ESIGI = 0.70          # "ciddiye alinabilir" esigi
YENI_LISTE_N = 200        # bunun altinda gozlem = yeni enstruman

# --- ince quote ciftlerinin funding FAZLASI (yillik %) ---------------
FAZLA = {"LINKUSDC": 0.50, "LTCUSDC": 1.10, "AVAXUSDC": 1.41,
         "BCHUSDC": 1.88, "AAVEUSDC": 2.33}

# --- 2.000 $ ve 1.000 $ sonuclari ------------------------------------
BACAK_2000 = 20.51        # 13x3
BACAK_1000 = 10.26        # 13x3
SONUC_2000 = ("kalan tek kayip BTC (-13,36) ve ikamesi BTCU KULLANILAMAZ "
              "(rho 0,180, 2 aylik, 1/1850 likidite) -> GERI ALINAMAZ")
SONUC_1000 = ("BCH+AVAX ikamesi +10,41 puan ederdi ama USDC-quote cift "
              "destegi + ayri evren paneli gerekir ve 2.000 $'da SIFIR "
              "deger ettigi icin insaat DEGMEZ")
INSAAT_GEREKENLER = ("USDC-quote cift destegi (farkli teminat varligi, "
                     "madde 141'in alani), sinyalin o ciftlerin KENDI "
                     "funding'inden hesaplanmasi, ayri evren paneli")

YASA1 = ("bir enstrumani DAYANAGI icin degil SINYALI icin alirsin: "
         "strateji funding uzerine kuruluysa farkli funding = FARKLI "
         "ISLEM; ETHU'nun ETH ile fiyat korelasyonu ~1, funding "
         "korelasyonu 0,021")
YASA2 = ("odulu olcmeden reddetmek, reddi KIRILGAN birakir: +28,5 puanlik "
         "bir odulun orada oldugunu bilmek mekanizmanin NEREDE coktugunu "
         "olcmeyi zorunlu kilar, yoksa fikir geri gelir")
ACIK_EKSEN = ("ince quote ciftleri (USDC) rho ~0,4 ile BAGIMSIZ bir "
              "funding akisi ve sistematik +%0,5..+%2,3/yil fazla "
              "sunuyor - bir IKAME degil YENI EVREN adayi; madde 289'un "
              "sartnamesi (tek basina Sharpe >= 2,5) gecerli ve bu "
              "maddede OLCULMEDI")
AYAR_DEGISTI = False


# --- sinamalar --------------------------------------------------------
def odul_buyuk_mu(esik: float = 20.0) -> bool:
    return (ODUL["9 major yok (10 $ bacak, GERCEK)"]
            - ODUL["ikameler HEPSI calissa (AAVE+ETC+QNT yok)"]) < -esik


def odul_puani() -> float:
    return (ODUL["ikameler HEPSI calissa (AAVE+ETC+QNT yok)"]
            - ODUL["9 major yok (10 $ bacak, GERCEK)"])


def en_degerli_ikameler_calisiyor_mu() -> bool:
    """BTC ve ETH ikameleri rho esigini geciyor mu? (Hayir.)"""
    return all(FUNDING[k][1] >= RHO_ESIGI
               for k in (("BTCUSDT", "BTCU"), ("ETHUSDT", "ETHU")))


def ciddiye_alinabilir_ikameler() -> list:
    return sorted(b for (a, b), v in FUNDING.items()
                  if v[1] >= RHO_ESIGI and v[0] > YENI_LISTE_N)


def yeni_listelenmisler() -> list:
    return sorted(b for (a, b), v in FUNDING.items() if v[0] <= YENI_LISTE_N)


def likidite_kat_farki(ikame: str) -> float:
    for (a, b), v in FUNDING.items():
        if b == ikame:
            return v[2] / v[3]
    return float("nan")


def btcu_likiditesi_asiri_ince_mi(kat: float = 1000.0) -> bool:
    return likidite_kat_farki("BTCU") > kat


def iki_ikame_ne_kurtarir() -> float:
    return (ODUL["yalniz BCH+AVAX kurtarilsa (7 major yok)"]
            - ODUL["9 major yok (10 $ bacak, GERCEK)"])


def ikibin_dolarda_degeri_sifir_mi() -> bool:
    """2.000 $'da BCH ve AVAX zaten elenmiyor mu?"""
    return BACAK_2000 >= 20.00 > BACAK_1000


def ince_ciftler_daha_cok_mu_oduyor() -> bool:
    return all(v > 0 for v in FAZLA.values())


def ortalama_fazla() -> float:
    return sum(FAZLA.values()) / len(FAZLA)


def acik_eksen_kayitli_mi() -> bool:
    return "YENI EVREN" in ACIK_EKSEN and "OLCULMEDI" in ACIK_EKSEN


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    return (
        "ODUL +28,5 PUAN, MEKANIZMA COKUYOR. Elenen majorlerin cogunun "
        "cok kucuk asgarili varyanti var (BTCU 8,36 $ vs BTCUSDT 83,61 $; "
        "ETHU/LINKUSDC/LTCUSDC/BCHUSDC/AVAXUSDC 5,00 $) ve ikameler HEPSI "
        "calissa maliyet -30,98'den -2,50'ye duserdi. AMA bu kitabin TUM "
        "sinyali funding'dir ve 12 aylik gecmiste ikame ciftlerin funding "
        "korelasyonu: ETHU **0,021**, BTCU **0,180** - en degerli iki "
        "kurtarma ise YARAMIYOR; fiyat korelasyonlari ~1 ama carry "
        "akislarini PAYLASMIYORLAR. Ustune ETHU/BTCU ~2 aylik (187 "
        "gozlem) ve ana ciftin 1/1850'i likiditede. Ciddiye alinabilir "
        "yalniz BCHUSDC (0,871) ve AVAXUSDC (0,725): ikisi +10,41 puan "
        "kurtarir AMA yalniz 1.000 $'da - 2.000 $'da (madde 295'in "
        "onerisi) bacak 20,51 $ ve ikisi ZATEN elenmiyor, degeri SIFIR. "
        "2.000 $'da kalan tek kayip BTC (-13,36) ve GERI ALINAMAZ. "
        "YASA: bir enstrumani DAYANAGI icin degil SINYALI icin alirsin. "
        "ACIK EKSEN: ince quote ciftleri +%0,5..+%2,3/yil fazla funding "
        "oduyor ve rho ~0,4 ile bagimsiz - bir IKAME degil YENI EVREN "
        "adayi, madde 289'un sartnamesiyle olculmedi. AYAR DEGISMEDI."
    )


def yaz() -> None:
    print(__doc__)
    print("IKAME TABLOSU:")
    print("  %-6s %12s %-20s %12s"
          % ("major", "USDT asgari", "varyant", "varyant asg."))
    for m, (a, v, b) in IKAME.items():
        print("  %-6s %12.2f %-20s %12s"
              % (m, a, v or "-", "-" if b is None else "%.2f" % b))
    print("\nODUL (SEMBOL_HARIC ile OLCULDU):")
    for ad, v in ODUL.items():
        print("  %-44s %+8.2f" % (ad, v))
    print("  odul buyuk mu: %s (%+.2f puan)" % (odul_buyuk_mu(), odul_puani()))
    print("\nFUNDING KARSILASTIRMASI (12 ay, rho esigi %.2f):" % RHO_ESIGI)
    print("  %-10s %-11s %6s %9s %12s" % ("USDT", "ikame", "n", "rho", "likidite kat"))
    for (a, b), (n, r, ha, hb) in sorted(FUNDING.items(), key=lambda kv: kv[1][1]):
        print("  %-10s %-11s %6d %9.4f %11.0fx%s"
              % (a, b, n, r, ha / hb, "  <= CIDDIYE ALINABILIR"
                 if r >= RHO_ESIGI and n > YENI_LISTE_N else ""))
    print("  en degerli iki ikame (BTC, ETH) calisiyor mu: %s"
          % en_degerli_ikameler_calisiyor_mu())
    print("  ciddiye alinabilir: %s" % ciddiye_alinabilir_ikameler())
    print("  yeni listelenmis (n<=%d, dogrulanamaz): %s"
          % (YENI_LISTE_N, yeni_listelenmisler()))
    print("  BTCU likiditesi asiri ince mi: %s (%.0f kat)"
          % (btcu_likiditesi_asiri_ince_mi(), likidite_kat_farki("BTCU")))
    print("\nIKI CIDDI IKAME NE KURTARIR: %+.2f puan (10 $ bacakta)"
          % iki_ikame_ne_kurtarir())
    print("  2.000 $'da degeri SIFIR mi: %s (bacak %.2f $ >= 20 $)"
          % (ikibin_dolarda_degeri_sifir_mi(), BACAK_2000))
    print("  2.000 $: %s" % SONUC_2000)
    print("  1.000 $: %s" % SONUC_1000)
    print("  gereken insaat: %s" % INSAAT_GEREKENLER)
    print("\nYAN BULGU - INCE QUOTE CIFTLERI DAHA COK CARRY ODUYOR:")
    for ad, v in sorted(FAZLA.items(), key=lambda kv: kv[1]):
        print("  %-10s +%%%.2f/yil" % (ad, v))
    print("  hepsi pozitif mi: %s | ortalama +%%%.2f/yil"
          % (ince_ciftler_daha_cok_mu_oduyor(), ortalama_fazla()))
    print("  ACIK EKSEN: %s" % ACIK_EKSEN)
    print("  kayitli mi: %s" % acik_eksen_kayitli_mi())
    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
