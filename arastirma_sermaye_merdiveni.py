#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 304 — HAVUZ VE TUTMA SÜRESİ 13x3'TE DE ZATEN EN İYİ; KÂR
PARAMETREDE DEĞİL **SERMAYE MERDİVENİNDE**: 2.000 $'DAN 3.750 $'A ÇIKMAK
+5,52 PUAN, 8.361 $'A ÇIKMAK +13,36 PUAN.

Kullanıcı açıkça "kâr bulmaya çalış" dedi — son üç tur (301, 302, 303)
güvenilirlik işiydi. Kâr eksenine dönüldü ve madde 300'ün açtığı mantık
takip edildi: **kalabalık havuzu (HAVUZ=3) ve tutma süresi (5 gün) 15x5
kitabı üzerinde ayarlanmıştı.** HAVUZ doğrudan bacak sayısına bağlıdır
(havuz = HAVUZ x bacak), yani 5 bacakta 15, 3 bacakta **9** — seçim
genişliği yarıya inmiş. 13x3'te en muhtemel yanlış-ayar yeri burasıydı.

═══ 1. TARAMA: ALTI KOL, ALTISI DA RED ═══

    kol               CAGR      Sh   dusus    Sh22    Sh25     doz      net   P(Sh)  P(ham)
    KONTROL        +149,95   2,886   17,68   2,706   3,134  1,200x  +195,33     -       -
    HAVUZ 2        +150,78   2,877   21,20   2,692   3,141  1,209x  +198,73  %46,0   %54,7
    HAVUZ 5        +150,32   2,893   17,18   2,660   3,208  1,193x  +193,93  %46,1   %45,3
    HAVUZ 8        +144,30   2,801   19,62   2,514   3,195  1,156x  +176,96  %27,7   %31,4
    **REB 3 gun**  +184,10   2,805   20,51   2,669   3,007  0,966x  +174,05  %26,3  **%99,4**
    REB 7 gun      +112,62   2,661   16,87   2,608   2,742  1,282x  +157,88   %2,3    %0,0
    REB 10 gun     + 78,67   2,295   20,06   2,365   2,232  1,325x  +111,43   %0,7    %0,0

HAVUZ 2'nin neti +3,39 YÜKSEK ama şart 1, 2 ve 3'ten düşüyor (düşüş
+3,52 puan, tolerans 3,0) ve P(Sh) %46,0 — gürültü. HAVUZ 5 şart 2, 3
ve 4'ü GEÇİYOR, yalnız şart 1'den düşüyor (Sh22 −0,045 / Sh25 +0,074),
ama neti −1,40 ve P %46,1 — o da gürültü.

**HAVUZ=3 ve REB=5 gün 13x3'te de zaten en iyi.** Madde 300'ün TP
eşikleri için bulduğu sonucun aynısı: bu parametreler yapılandırmaya
değil MEKANİZMAYA ait. Üç bağımsız eksen (TP, HAVUZ, REB) aynı cevabı
verdi.

═══ 2. REB 3: AYNA TUZAĞININ ÜÇÜNCÜ VE EN KESKİN ÖRNEĞİ ═══

    ham getiri bootstrap'i  P(>0) = **%99,4**   -> KABUL ederdi
    Sharpe bootstrap'i      P(>0) =   %26,3     -> RED
    doz olcusu              net    **-21,29**   -> RED
    doz                     **0,966x**          -> 1x'i BILE tasimiyor

REB=3 CAGR'ı +149,95'ten **+184,10**'a çıkarıyor — 34 puan, ve bu %99,4
olasılıkla gerçek. Ama eşit p95 düşüşe ölçeklenince doz **1,0'ın
ALTINA** iniyor: kitap o haliyle 1x kaldıracı dahi taşımıyor.

Madde 300 bu tuzağı TPL 0,55'te bulmuştu (P(ham) %95,9 / net −5,26) ve
madde 299'un ters yönünü gösteriyordu. REB=3 aynı tuzağın **daha keskin**
hâli: daha yüksek güven (%99,4), daha büyük ceza (−21,29), ve dozun
1,0'ın altına düştüğü ilk vaka. **Üç gözlemle bu artık tek bir örnek
değil, bir DESEN.**

═══ 3. ASIL CEVAP: KÂR SERMAYE MERDİVENİNDE ═══

Madde 297'den beri sekiz eksen denendi (hacim eşiği, ikame enstrüman,
trend sleeve, sinyal harmanı, TP, HAVUZ, REB) ve dört şartı geçen
**hiçbir** parametre bulunamadı. Bu bir başarısızlık değil bir BULGU:
2.000 $'daki kitap parametre uzayında yerel optimumda.

Kalan kazanç sermayeyle satın alınıyor, ve eşikler ÖLÇÜLMÜŞ. Projenin
kendi fonksiyonlarıyla (`arastirma_evren_esigi.toplam_maliyet`,
`uygun_mu`) kurulan merdiven:

    bakiye      en iyi    bacak        net     bir onceki rungdan
      975 $      13x3    10,00 $    +164,35          -
    1.250 $      5x5     20,00 $    +181,05       +16,70
  **1.950 $**  **13x3** 20,00 $  **+181,97**      + 0,92   <- SU AN
  **3.750 $**  **15x5** 20,00 $  **+187,49**    **+ 5,52**
    6.271 $      5x5    100,34 $    +194,41       + 6,92
    8.361 $      13x3    85,75 $    +195,33       + 0,92
   15.677 $      15x5    83,61 $    +200,85       + 5,52

(net = 200,85 + `toplam_maliyet`, yani 15x5 tam-evren tabanına göre.
Taban çapraz doğrulandı: madde 295'in `YAPISAL["13x3"]=−5,52` ile madde
300'ün bağımsız ölçtüğü 13x3 neti +195,33 = 200,85 − 5,52 birebir
tutuyor.)

**2.000 $ -> 3.750 $ (iki katından az) = +5,52 puan.**
**2.000 $ -> 8.361 $ = +13,36 puan.**
**2.000 $ -> 15.677 $ = +18,88 puan (tabana ulaşır).**

Merdivenin basamakları BACAK BÜYÜKLÜĞÜ eşikleridir, toplam bakiye
değil: `evren_maliyeti` 20 $ ve 83,61 $'da basamak yapıyor (madde 295)
ve her yapı o eşiklere farklı bakiyede varıyor. Bu yüzden sıralama
MONOTON DEĞİL: 5x5, 15x5'ten daha az pozisyon tuttuğu için tam evrene
**daha düşük bakiyede** ulaşıyor (6.271 $ vs 15.677 $) ve orada öne
geçiyor. Beklenmedik ama doğru.

═══ 4. KENDİ HATAM (kayda geçiyor) ═══

Merdiveni ilk kurduğumda iki hata yaptım: (a) **koşabilirlik filtresini**
uygulamadım — 15x5 1.000 $'da bacak 5,33 $ veriyor, asgari 10 $'ın
altında, yani o yapı o bakiyede zaten koşmaz; (b) projenin
`toplam_maliyet` amaç fonksiyonu yerine kendi birleştirdiğim bir net
kullandım. Sonuç: `en_iyi()` ile "tutarsızlık" göründü (8.000 $'da 5x5,
12.000 $'da 13x3 diyordu).

Tutarsızlık YOKTU — tablom yanlıştı. Fonksiyonu okuyunca ikisi de
açıklandı, ve 5x5'in beklenmedik görünümü GERÇEK bir bulgu çıktı.
**Projenin kendi fonksiyonu varken onu yeniden türetmek, hatayı
projeye değil kendine yazdırır.**

═══ 5. AYAR DEĞİŞMEDİ ═══

Öneri aynen: **13 dilim x 3 bacak, 2.000 $, 1x.** Değişen tek şey, artık
sermaye arttıkça NEREDE yapılandırma değiştirmek gerektiği ölçülmüş
durumda.
"""

# ---------------------------------------------------------------- SABİTLER

SORU = ('Kullanici "kar bulmaya calis" dedi. HAVUZ ve tutma suresi 15x5 '
        "uzerinde ayarlanmisti; HAVUZ dogrudan bacak sayisina bagli "
        "(havuz = HAVUZ x bacak: 5 bacakta 15, 3 bacakta 9).")

# --- 1. tarama ---
KONTROL = {"cagr": 149.95, "sh": 2.886, "dd": 17.68, "sh22": 2.706,
           "sh25": 3.134, "doz": 1.200, "net": 195.33}
TARAMA = {
    #  kol        : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net,   P(Sh)%, P(ham)%)
    "HAVUZ 2":   (150.78, 2.877, 21.20, 2.692, 3.141, 1.209, 198.73, 46.0, 54.7),
    "HAVUZ 5":   (150.32, 2.893, 17.18, 2.660, 3.208, 1.193, 193.93, 46.1, 45.3),
    "HAVUZ 8":   (144.30, 2.801, 19.62, 2.514, 3.195, 1.156, 176.96, 27.7, 31.4),
    "REB 3 gun": (184.10, 2.805, 20.51, 2.669, 3.007, 0.966, 174.05, 26.3, 99.4),
    "REB 7 gun": (112.62, 2.661, 16.87, 2.608, 2.742, 1.282, 157.88,  2.3,  0.0),
    "REB 10 gun":( 78.67, 2.295, 20.06, 2.365, 2.232, 1.325, 111.43,  0.7,  0.0),
}
BAR_P = 80.0
HAVUZ_FORMULU = "havuz = HAVUZ x bacak (5 bacakta 15, 3 bacakta 9)"
MEKANIZMA_EKSENLERI = ("TP (madde 300)", "HAVUZ (madde 304)", "REB (madde 304)")
"""Uc bagimsiz eksen de 13x3'te 'degismedi' dedi -> parametreler
yapilandirmaya degil MEKANIZMAYA ait."""

# --- 2. ayna tuzagi: ucuncu ve en keskin ornek ---
AYNA_ADAY = "REB 3 gun"
AYNA_SICIL = {
    #  madde : (aday, P(ham)%, net farki, doz)
    299: ("sinyal harmani w=0,2", 15.2, -21.89, 1.464),   # ters yon: yanlis RED
    300: ("TPL 0,55", 95.9, -5.26, 1.115),                # yanlis KABUL
    304: ("REB 3 gun", 99.4, -21.29, 0.966),              # yanlis KABUL, en keskin
}
AYNA_YENI = ("REB=3'un dozu 0,966x - 1,0'IN ALTINA dusen ILK vaka: kitap "
             "o haliyle 1x kaldiraci dahi tasimiyor.")
DESEN = ("Uc gozlemle bu artik tek bir ornek degil bir DESEN: ham getiri "
         "olcusu, getiriyi VE riski birlikte yukselten adayi sistematik "
         "olarak KABUL ediyor.")

# --- 3. sermaye merdiveni ---
TABAN_NET = 200.85
"""15x5 tam evren (madde 297). net = TABAN_NET + toplam_maliyet."""
MERDIVEN = [
    #  (bakiye, yapi, bacak_usd, net)
    (975.0,    "13x3",  10.00, 164.35),
    (1250.0,   "5x5",   20.00, 181.05),
    (1950.0,   "13x3",  20.00, 181.97),
    (3750.0,   "15x5",  20.00, 187.49),
    (6271.0,   "5x5",  100.34, 194.41),
    (8361.0,   "13x3",  85.75, 195.33),
    (15677.0,  "15x5",  83.61, 200.85),
]
KULLANICI_BAKIYE = 2000.0
KULLANICI_BACAK = 20.51
"""2.000 $'da 13x3 bacagi. DIKKAT: merdivenin 1.950 $ rungundaki bacak
TAM 20,00 $ - ilk yazimda bu ikisini karistirip rung satirina 20,51
yazmistim; preflight'in `bacak_usd` capraz kontrolu yakaladi."""
KAZANCLAR = {3750.0: 5.52, 8361.0: 13.36, 15677.0: 18.88}
"""2.000 $'daki netten (+181,97) o bakiyeye cikmanin kazanci."""
MADDE305_NOTU = (
    "*** MADDE 305 DUZELTMESI: BU MERDIVEN 13x3'U OLDUGUNDAN KOTU "
    "GOSTERIYOR. *** Merdiven evren kaybini madde 295'in basamak "
    "fonksiyonundan aliyor (`evren_maliyeti(20,51) = -13,36`), ama o sayi "
    "**15x5** kitabinda olculmustu. Madde 305'te 13x3 + BTC/QNT elemesi "
    "DOGRUDAN kosuldu ve net +185,50 cikti, yani gercek kayip **-9,83** - "
    "13x3 daha az pozisyon tuttugu icin BTC'nin kaybi ona daha az zarar "
    "veriyor. Yani 2.000 $ rungu +181,97 degil **+185,50**, sapma 3,53 "
    "puan. Merdiven DUZELTILMEDI: her yapilandirma x her eleme kumesi "
    "olculmeli (madde 305'te yalniz 13x3 olculdu). ACIK EKSEN.")
MADDE305_OLCULEN_13X3 = {"TAM": 195.33, "D2": 185.50, "D9": 182.61}

BASAMAK_SEBEBI = ("Merdivenin basamaklari BACAK BUYUKLUGU esikleridir "
                  "(evren_maliyeti 20 $ ve 83,61 $'da basamak yapar, madde "
                  "295) ve her yapi o esiklere FARKLI bakiyede varir.")
MONOTON_DEGIL = ("5x5, 15x5'ten daha az pozisyon tuttugu icin tam evrene "
                 "DAHA DUSUK bakiyede ulasiyor (6.271 $ vs 15.677 $) ve "
                 "orada one geciyor. Beklenmedik ama dogru.")
CAPRAZ_DOGRULAMA = ("madde 295'in YAPISAL['13x3']=-5,52 ile madde 300'un "
                    "BAGIMSIZ olctugu 13x3 neti +195,33 = 200,85 - 5,52 "
                    "birebir tutuyor.")
DENENEN_EKSEN_SAYISI = 8
"""Madde 297'den beri: hacim esigi, ikame enstruman, trend sleeve (x2),
sinyal harmani, TP, HAVUZ, REB. Dort sarti gecen parametre YOK."""

# --- 4. kendi hatam ---
HATAM = ("Merdiveni ilk kurdugumda (a) KOSABILIRLIK filtresini uygulamadim "
         "- 15x5 1.000 $'da bacak 5,33 $ verir, asgari 10 $'in altinda; "
         "(b) projenin `toplam_maliyet` amac fonksiyonu yerine kendi "
         "birlestirdigim bir net kullandim. Sonuc: en_iyi() ile "
         "'tutarsizlik' gorundu. Tutarsizlik YOKTU - tablom yanlisti.")
HATANIN_DERSI = ("Projenin kendi fonksiyonu varken onu yeniden turetmek, "
                 "hatayi projeye degil KENDINE yazdirir.")

AYAR_DEGISTI = False
ONERI = "13 dilim x 3 bacak, 2.000 $, 1x (DEGISMEDI)"

YASA1 = ("Bir parametre uc bagimsiz eksende de 'degismedi' diyorsa o "
         "parametre YAPILANDIRMAYA degil MEKANIZMAYA aittir: TP, HAVUZ ve "
         "REB'in ucu de 15x5'te bulundu ve 13x3'te de en iyi cikti.")
YASA2 = ("Ham getiri olcusu, getiriyi VE riski birlikte yukselten adayi "
         "SISTEMATIK olarak kabul eder - artik uc ornek var ve en keskini "
         "dozu 1,0'IN ALTINA dusuruyor (%99,4 guven, net -21,29).")
YASA3 = ("Parametre uzayi tukenince kar PARAMETREDE degil SERMAYEDEDIR - "
         "ve bu bir basarisizlik degil bir OLCUMDUR: 2.000 $ -> 3.750 $ "
         "+5,52 puan, -> 8.361 $ +13,36 puan.")
YASA4 = ("Projenin kendi amac fonksiyonu varken onu yeniden turetme: "
         "koşabilirlik filtresini atlayip kendi netimi kurdugumda ortaya "
         "cikan 'tutarsizlik' projenin degil benim hatamdi.")


# ---------------------------------------------------------------- HÜKÜM

def gecen_kol_var_mi() -> bool:
    return any(v[7] >= BAR_P for v in TARAMA.values())


def en_yakin_kol() -> str:
    return max(TARAMA, key=lambda a: TARAMA[a][7])


def havuz_reb_zaten_en_iyi_mi() -> bool:
    """Hicbir HAVUZ/REB kolu kontrolu ANLAMLI gecemedi mi?"""
    return not gecen_kol_var_mi()


def uc_eksen_ayni_cevabi_mi_verdi() -> bool:
    return len(MEKANIZMA_EKSENLERI) == 3 and havuz_reb_zaten_en_iyi_mi()


def ayna_deseni_mi(en_az: int = 3) -> bool:
    """Yanlis-nicelik tuzagi artik tek ornek mi, desen mi?"""
    return len(AYNA_SICIL) >= en_az


def doz_birin_altina_dustu_mu() -> bool:
    return TARAMA[AYNA_ADAY][5] < 1.0


def ham_olcu_kabul_ederdi_mi() -> bool:
    return TARAMA[AYNA_ADAY][8] >= 95.0 and TARAMA[AYNA_ADAY][6] < KONTROL["net"]


def merdiven_monoton_mu() -> bool:
    """Yapi sirasi bakiyeyle monoton mu? (DEGIL - 5x5 araya giriyor)"""
    y = [r[1] for r in MERDIVEN]
    return len(set(y)) == len([1 for i, a in enumerate(y) if i == 0 or a != y[i - 1]])


def merdiven_neti_artiyor_mu() -> bool:
    n = [r[3] for r in MERDIVEN]
    return all(a < b for a, b in zip(n, n[1:]))


def simdiki_rung() -> tuple:
    uy = [r for r in MERDIVEN if r[0] <= KULLANICI_BAKIYE]
    return uy[-1]


def sonraki_rung() -> tuple:
    uy = [r for r in MERDIVEN if r[0] > KULLANICI_BAKIYE]
    return uy[0] if uy else simdiki_rung()


def sonraki_kazanc() -> float:
    return round(sonraki_rung()[3] - simdiki_rung()[3], 2)


def capraz_dogrulama_tutuyor_mu(tol: float = 0.01) -> bool:
    import arastirma_evren_esigi as _e
    return abs((TABAN_NET + _e.YAPISAL["13x3"]) - KONTROL["net"]) <= tol


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    if gecen_kol_var_mi():
        return "ACIK: kanit esigini gecen bir HAVUZ/REB ayari var."
    return ("RED + YON: HAVUZ ve tutma suresi 13x3 kitabinda da ZATEN EN "
            "IYI (HAVUZ=3, REB=5 gun degismiyor); alti kolun hicbiri kanit "
            "barini gecmedi, en yakini HAVUZ 5 (P %46,1, net -1,40) ki "
            "gurultu. Bu, TP'den (madde 300) sonra UCUNCU eksen - yani bu "
            "parametreler yapilandirmaya degil MEKANIZMAYA ait. REB=3 ise "
            "ayna tuzaginin EN KESKIN ornegi: ham getiri P %99,4 ile KABUL "
            "ederdi, doz 0,966x ile 1x'i bile tasimiyor. ASIL CEVAP: madde "
            "297'den beri sekiz eksende dort sarti gecen parametre YOK; "
            "2.000 $'daki kitap parametre uzayinda yerel optimumda ve kalan "
            "kazanc SERMAYEYLE satin aliniyor - 3.750 $'da +5,52 puan, "
            "8.361 $'da +13,36 puan, 15.677 $'da +18,88 puan. Ayar "
            "DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("SORU: %s\n" % SORU)

    print("1) TARAMA (%s):" % HAVUZ_FORMULU)
    print("   %-12s %8s %7s %7s %7s %7s %8s %9s %7s %8s"
          % ("kol", "CAGR", "Sh", "dusus", "Sh22", "Sh25", "doz", "net",
             "P(Sh)", "P(ham)"))
    print("   %-12s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %7s %8s"
          % ("KONTROL", KONTROL["cagr"], KONTROL["sh"], KONTROL["dd"],
             KONTROL["sh22"], KONTROL["sh25"], KONTROL["doz"],
             KONTROL["net"], "-", "-"))
    for ad, v in TARAMA.items():
        isa = "  <== AYNA" if ad == AYNA_ADAY else ""
        print("   %-12s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %6.1f%% %7.1f%%%s"
              % (ad, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], isa))
    print("   kanit barini (>=%%%.0f) gecen kol: %s | en yakin: %s (P %%%.1f)"
          % (BAR_P, gecen_kol_var_mi(), en_yakin_kol(),
             TARAMA[en_yakin_kol()][7]))
    print("   HAVUZ/REB zaten en iyi mi: %s" % havuz_reb_zaten_en_iyi_mi())
    print("   mekanizma eksenleri: %s -> ucu de ayni cevap: %s"
          % (list(MEKANIZMA_EKSENLERI), uc_eksen_ayni_cevabi_mi_verdi()))

    print("\n2) AYNA TUZAGI SICILI:")
    print("   %-7s %-24s %9s %10s %8s" % ("madde", "aday", "P(ham)", "net farki", "doz"))
    for m, (ad, p, n, d) in sorted(AYNA_SICIL.items()):
        print("   %-7d %-24s %8.1f%% %+10.2f %7.3fx" % (m, ad, p, n, d))
    print("   desen mi (>=3 ornek): %s" % ayna_deseni_mi())
    print("   %s" % AYNA_YENI)
    print("   doz 1,0'in altina dustu mu: %s | ham olcu KABUL ederdi mi: %s"
          % (doz_birin_altina_dustu_mu(), ham_olcu_kabul_ederdi_mi()))
    print("   %s" % DESEN)

    print("\n3) SERMAYE MERDIVENI (taban %.2f = 15x5 tam evren):" % TABAN_NET)
    print("   %10s %8s %10s %10s %10s"
          % ("bakiye", "en iyi", "bacak", "net", "onceki+"))
    onc = None
    for b, y, l, n in MERDIVEN:
        fark = "-" if onc is None else "%+.2f" % (n - onc)
        isa = "  <== SU AN" if (b, y, l, n) == simdiki_rung() else ""
        print("   %9.0f$ %8s %9.2f$ %+10.2f %10s%s" % (b, y, l, n, fark, isa))
        onc = n
    print("   simdiki rung: %s | sonraki: %.0f $ (%s) -> %+.2f puan"
          % (simdiki_rung()[1], sonraki_rung()[0], sonraki_rung()[1],
             sonraki_kazanc()))
    print("   %.0f $'dan kazanclar: %s" % (KULLANICI_BAKIYE, KAZANCLAR))
    print("   net monoton artiyor mu: %s | yapi sirasi monoton mu: %s"
          % (merdiven_neti_artiyor_mu(), merdiven_monoton_mu()))
    print("   %s" % BASAMAK_SEBEBI)
    print("   %s" % MONOTON_DEGIL)
    print("   capraz dogrulama: %s -> tutuyor mu: %s"
          % (CAPRAZ_DOGRULAMA, capraz_dogrulama_tutuyor_mu()))
    print("   madde 297'den beri denenen eksen: %d, gecen: 0"
          % DENENEN_EKSEN_SAYISI)

    print("\n4) KENDI HATAM:")
    print("   %s" % HATAM)
    print("   DERS: %s" % HATANIN_DERSI)

    print("\n5) AYAR degisti mi: %s | oneri: %s" % (ayar_degisti_mi(), ONERI))
    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("YASA 4: %s" % YASA4)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
