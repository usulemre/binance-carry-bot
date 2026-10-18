#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 305 — TREND SLEEVE 13x3'TE 15x5'TEKİNİN ÜÇ KATI DEĞERİNDE VE
EŞİĞİ 9.375 $ DEĞİL **3.250 $**: PROJENİN EN GÜÇLÜ ADAYI, VE YİNE YALNIZ
ŞART 4'TEN DÜŞÜYOR.

Madde 298 trend sleeve'ini bulmuştu ama yalnız **15x5** kontrolüne karşı
ölçmüştü: net +208,46 vs +200,85 (+7,61), P(Sh) %81,0, ve harman iki
kitap olduğu için **9.375 $** istiyordu. Kullanıcının yapılandırması
13x3 ve orada aynı harman daha düşük bakiyede koşabilirdi — ama sleeve
13x3 kontrolüne karşı HİÇ ölçülmemişti. Madde 304'ün sonunda bu, iki
açık adaydan "daha ucuz ve sermaye aralığına daha yakın" olanıydı.

Ölçüldü. Sonuç beklenenden iyi çıktı.

═══ 1. TAM EVREN: SLEEVE 13x3'TE ÜÇ KAT DEĞERLİ ═══

Sleeve `REZERV=0` ile koşuldu (madde 299: motor `REZ_ESIK`'i doğrudan
sinyalin BÜYÜKLÜĞÜYLE karşılaştırıyor ve momentum paneli funding birimi
olmadığı için o eşik anlamsız; kapanma ÇIKTIDAN doğrulandı,
`rez_kullanim/yil 0`).

    kitap                     CAGR      Sh   dusus    doz      net     rho
    KONTROL 13x3           +149,95   2,886   17,68  1,200x  +195,33   1,000
    mom1 13x3 (REZERV=0)   +126,98   2,655   18,27  1,141x  +151,68   0,703
    PLASEBO 13x3           + 57,89   1,918   23,06  1,207x  + 71,19   0,724

    mom1 vs PLASEBO tek basina: net +151,68 vs +71,19, **P(Sh) %99,4**

Sinyalin degeri 13x3'te **+0,74 Sharpe** (2,655 − 1,918); 15x5'te
**+0,54** idi (2,543 − 2,016). Ve harman:

    w      CAGR      Sh   dusus    Sh22    Sh25     doz      net    dnet   P(Sh)
    0,1  +148,27   2,942   17,12   2,742   3,213  1,247x  +204,78   + 9,45  %97,1
    0,2  +146,45   2,984   16,55   2,768   3,277  1,285x  +211,90   +16,57  %94,5
  **0,3**+144,48   3,010   16,00   2,780   3,321  1,315x  +216,40 **+21,07** %90,3

15x5'te en iyi +7,61 (P %81,0) idi; 13x3'te **+21,07 (P %90,3)** —
yaklaşık **üç kat**, ve kanıtı daha güçlü.

SEBEP tutarlı: 13x3 kontrolünün dozu daha düşük (1,200x vs 1,505x) ve
düşüşü daha yüksek (17,68 vs 14,54), yani bir çeşitlendiriciye DAHA ÇOK
YER var.

ÖNEMLİ FARK: 15x5'te şart 1 kıl payıydı (Sh22 +0,003 / Sh25 +0,100);
13x3'te **iki fazda da temiz** (+0,074 / +0,188).

PLASEBO HARMANI NEGATİF: −4,15 (w=0,1) · −9,36 (0,2) · −19,12 (0,3).
Yani madde 298'in 2. yasası burada da geçerli — düşüş azaltması
sleeve'e ait değil — ama momentumun GETİRİ katkısı harmanı kazandırıyor:
mom1 harmanı plasebo harmanını **P(Sh) %99,5** ile geçiyor
(+216,40 vs +176,21).

═══ 2. AMA TAM EVREN GERÇEK DEĞİL: SERMAYE EŞİĞİ ═══

Harmanda İKİ kitap var ve bacakları FARKLI, yani eleme kümeleri de
farklı (madde 295: her majorün kendi asgarisi var). w=0,3'te sleeve
bakiyenin %30'unu alıyor, yani 3.250 $'da sleeve bacağı tam **10,00 $**
ve orada **9 major** eleniyor; carry bacağı 23,33 $ ve orada yalnız
**BTC+QNT**.

O yüzden her iki kitap da GERÇEK eleme kümeleriyle yeniden koşuldu
(`SEMBOL_HARIC`, eleme çıktıdan doğrulandı: 9/9 ve 2/2 sembol):

    kol        CAGR      Sh   dusus    Sh22    Sh25     doz      net
    KAR TAM  +149,95   2,886   17,68   2,706   3,134  1,200x  +195,33
    KAR D2   +146,30   2,830   18,65   2,668   3,052  1,181x  +185,50
    KAR D9   +147,56   2,814   22,87   2,571   3,142  1,162x  +182,61
    MOM TAM  +126,98   2,655   18,27   2,447   2,934  1,141x  +151,68
    MOM D2   +126,21   2,624   18,15   2,434   2,879  1,122x  +147,16
    MOM D9   +121,02   2,502   19,84   2,213   2,886  1,062x  +130,45

Ve bakiyeye göre harman (her kitap kendi kümesinde):

    bakiye   en iyi w   tek kitap   harman     fark   sleeve bacagi
    2.000 $      -       +185,50   KOSMUYOR      -     < 10 $
  **3.250 $**   0,3      +185,50   +198,19  **+12,69**  10,00 $
    4.875 $     0,3      +185,50   +198,19    +12,69   15,00 $
  **8.000 $**   0,3      +185,50   +205,67  **+20,16**  24,62 $
   13.000 $     0,3      +195,33   +213,36    +18,03   40,00 $

Tam evrendeki +21,07, gerçek evren kaybıyla 3.250 $'da **+12,69**'a
iniyor (sleeve 9 major kaybediyor), sleeve 20 $ eşiğini geçince
(8.000 $) **+20,16**'ya çıkıyor.

**EŞİK 9.375 $ DEĞİL 3.250 $** — kullanıcının 2.000 $'ının 1,6 katı.

═══ 3. DÖRT ŞART, GERÇEK KOLLARDA ═══

    bakiye    sart 1        sart 2        sart 3         sart 4      P(Sh)
    3.250 $  OK (+0,008/   OK (-1,61)   OK (+15,0)   RED (1,103x)   %82,9
              +0,187)
    8.000 $  OK (+0,079/   OK (-1,82)   OK (+20,1)   RED (1,118x)   %91,0
              +0,186)
   13.000 $  OK (+0,069/   OK (-2,14)   OK (+26,6)   RED (1,149x)   %88,0
              +0,170)

**Her bakiyede şart 1, 2 ve 3 GEÇİYOR ve kanıt barı (%80) GEÇİLİYOR.**
Yalnız şart 4 düşüyor — ve kuralın kendi metni onun "bir PARAMETRE
kararı değil KALDIRAÇ kararı" olduğunu, madde 149 tablosuna karşı AYRICA
verilmesi gerektiğini söylüyor (madde 225).

Bu, şart 4'ten tek başına düşen **DÖRDÜNCÜ** aday (288 prim-brüt, 290
SEC_volyuk, 298 trend sleeve 15x5, 305 trend sleeve 13x3) — ama ilk kez
(a) kazanç BÜYÜK (+12,69 .. +20,16), (b) kanıt barı GERÇEK sermayede
geçiliyor, (c) şart 1 iki fazda da TEMİZ, (d) eşik kullanıcının
bakiyesinin 1,6 katı.

═══ 4. YAN BULGU: EVREN MALİYETİ DE YAPILANDIRMAYA BAĞLI ═══

Madde 304'ün merdiveni 13x3'ü 2.000 $'da +181,97 diye hesaplıyordu:
tam evren neti +195,33 eksi madde 295'in `evren_maliyeti(20,51) = −13,36`
basamağı.

Bu turda o kayıp DOĞRUDAN ölçüldü: 13x3 + BTC/QNT elemesi = **+185,50**,
yani kayıp **−9,83**, −13,36 değil.

Sebep: madde 295'in −13,36'sı **15x5** kitabında ölçülmüştü. 13x3 daha
az pozisyon tuttuğu için BTC'nin kaybı ona daha az zarar veriyor. Yani
**evren maliyeti de yapılandırmaya bağlıdır** ve madde 304'ün merdiveni
13x3 için kitabı olduğundan 3,53 puan KÖTÜ gösteriyor.

Merdiven bu maddede DÜZELTİLMEDİ: düzeltmek için her yapılandırma x her
eleme kümesi ölçülmeli (bu turda yalnız 13x3 ölçüldü). Açık eksen olarak
geçti ve madde 304'ün dosyasına ileri işaret konuldu.

═══ 5. KULLANICI İÇİN ═══

2.000 $'da harman KOŞMUYOR; öneri aynen **13 dilim x 3 bacak, 2.000 $,
1x**. Ama artık ölçülmüş bir hedef var: **3.250 $'da +12,69 puan,
8.000 $'da +20,16 puan** — ve bu, madde 304'ün sermaye merdivenindeki
tek-kitap kazançlarından (3.750 $'da +5,52) KAT KAT büyük.

Yani madde 304'ün "kâr sermayededir" sonucu güncellendi: kâr sermayede
AMA yapılandırma değiştirerek değil, **ikinci bir kitap ekleyerek**.

AYAR DEĞİŞMEDİ.
"""

# ---------------------------------------------------------------- SABİTLER

KAYNAK = ("Madde 298 trend sleeve'ini yalniz 15x5 kontrolune karsi olcmustu "
          "(+7,61, P %81,0, esik 9.375 $). Madde 304'un sonunda iki acik "
          "adaydan 'daha ucuz ve sermaye araligina daha yakin' olani buydu.")
SLEEVE_REZERV = 0
SLEEVE_REZERV_GEREKCE = ("madde 299: motor REZ_ESIK'i sinyalin BUYUKLUGUYLE "
                         "karsilastirir ve momentum paneli funding birimi "
                         "degil; kapanma CIKTIDAN dogrulandi (rez_kullanim 0)")

# --- 1. tam evren ---
TAM_EVREN = {
    #  kitap  : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net,    rho)
    "KONTROL 13x3": (149.95, 2.886, 17.68, 2.706, 3.134, 1.200, 195.33, 1.000),
    "mom1 13x3":    (126.98, 2.655, 18.27, 2.447, 2.934, 1.141, 151.68, 0.703),
    "PLASEBO 13x3": ( 57.89, 1.918, 23.06, 1.785, 2.097, 1.207,  71.19, 0.724),
}
MOM_VS_PLASEBO_P = 99.4
SINYAL_DEGERI = {"13x3": 2.655 - 1.918, "15x5": 2.543 - 2.016}
HARMAN_TAM = {
    #  w  : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net,    dnet,  P(Sh)%)
    0.1: (148.27, 2.942, 17.12, 2.742, 3.213, 1.247, 204.78,  9.45, 97.1),
    0.2: (146.45, 2.984, 16.55, 2.768, 3.277, 1.285, 211.90, 16.57, 94.5),
    0.3: (144.48, 3.010, 16.00, 2.780, 3.321, 1.315, 216.40, 21.07, 90.3),
}
MADDE298_15X5 = {"dnet": 7.61, "P": 81.0, "esik_usd": 9375.0,
                 "sart1": (0.003, 0.100)}
NEDEN_DAHA_DEGERLI = ("13x3 kontrolunun dozu daha DUSUK (1,200x vs 1,505x) ve "
                      "dususu daha YUKSEK (17,68 vs 14,54), yani bir "
                      "cesitlendiriciye DAHA COK YER var.")
PLASEBO_HARMAN = {0.1: -4.15, 0.2: -9.36, 0.3: -19.12}
HARMAN_VS_PLASEBO = {"aday": 216.40, "plasebo": 176.21, "P": 99.5}

# --- 2. gercek evren kaybi ---
KOLLAR = {
    #  kol      : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net)
    "KAR TAM": (149.95, 2.886, 17.68, 2.706, 3.134, 1.200, 195.33),
    "KAR D2":  (146.30, 2.830, 18.65, 2.668, 3.052, 1.181, 185.50),
    "KAR D9":  (147.56, 2.814, 22.87, 2.571, 3.142, 1.162, 182.61),
    "MOM TAM": (126.98, 2.655, 18.27, 2.447, 2.934, 1.141, 151.68),
    "MOM D2":  (126.21, 2.624, 18.15, 2.434, 2.879, 1.122, 147.16),
    "MOM D9":  (121.02, 2.502, 19.84, 2.213, 2.886, 1.062, 130.45),
}
ELEME_DOGRULANDI = ("SEMBOL_HARIC cikti ile dogrulandi: D9 -> 9/9 sembol, "
                    "D2 -> 2/2 sembol")
MERDIVEN = [
    #  (bakiye, en_iyi_w, tek_net, harman_net, fark, sleeve_bacak, kume_c, kume_s)
    (2000.0,  None,  185.50, None,   None,  6.15,  "D2",  "-"),
    (3250.0,  0.3,   185.50, 198.19, 12.69, 10.00, "D2",  "D9"),
    (4875.0,  0.3,   185.50, 198.19, 12.69, 15.00, "D2",  "D9"),
    (8000.0,  0.3,   185.50, 205.67, 20.16, 24.62, "D2",  "D2"),
    (13000.0, 0.3,   195.33, 213.36, 18.03, 40.00, "TAM", "D2"),
]
ESIK_USD = 3250.0
KULLANICI_BAKIYE = 2000.0
ASGARI_BACAK = 10.0

# --- 3. dort sart gercek kollarda ---
SARTLAR = {
    #  bakiye : (sart1 (sh22,sh25), sart2, sart3, sart4 kaldirac, P(Sh)%)
    3250.0:  ((0.008, 0.187), -1.61, 15.0, 1.103, 82.9),
    8000.0:  ((0.079, 0.186), -1.82, 20.1, 1.118, 91.0),
    13000.0: ((0.069, 0.170), -2.14, 26.6, 1.149, 88.0),
}
BAR_P = 80.0
SART4_SICIL = (288, 290, 298, 305)
SART4_METNI = ("kuralin kendi metni: 'bu bir PARAMETRE karari degil KALDIRAC "
               "kararidir (madde 225); madde 149 tablosuna karsi ayrica "
               "verilmeli'")
ILK_KEZ = ("ilk kez (a) kazanc BUYUK (+12,69..+20,16), (b) kanit bari GERCEK "
           "sermayede gecilyor, (c) sart 1 iki fazda da TEMIZ, (d) esik "
           "kullanicinin bakiyesinin 1,6 kati")

# --- 4. yan bulgu: evren maliyeti yapilandirmaya bagli ---
MADDE295_BASAMAK = -13.36
"""evren_maliyeti(20,51); 15x5 kitabinda olculdu."""
OLCULEN_13X3 = -9.83
"""195,33 - 185,50. 13x3 daha az pozisyon tuttugu icin BTC kaybi ona daha
az zarar veriyor."""
MADDE304_SAPMASI = 3.53
"""Madde 304'un merdiveni 13x3'u 2.000 $'da +181,97 diyordu; olculen
+185,50. Yani kitabi oldugundan 3,53 puan KOTU gosteriyor."""
MERDIVEN_DUZELTILMEDI = ("Duzeltmek icin her yapilandirma x her eleme kumesi "
                         "olculmeli; bu turda yalniz 13x3 olculdu. Acik eksen "
                         "olarak gecti, madde 304'un dosyasina ileri isaret "
                         "konuldu.")

AYAR_DEGISTI = False
ONERI = "13 dilim x 3 bacak, 2.000 $, 1x (DEGISMEDI)"
HEDEF = ("3.250 $'da +12,69 puan, 8.000 $'da +20,16 puan - madde 304'un "
         "tek-kitap kazanclarindan (3.750 $'da +5,52) KAT KAT buyuk")

YASA1 = ("Bir cesitlendiricinin degeri, ANA KITABIN dozuna baglidir: ayni "
         "sleeve 15x5'te +7,61, 13x3'te +21,07 getirdi - cunku 13x3'un dozu "
         "daha dusuk ve dususu daha yuksek, yani cesitlendiriciye daha cok "
         "YER var. Bir adayi tek bir kontrole karsi olcup 'degeri bu' demek, "
         "degerin KONTROLE AIT oldugunu kacirir.")
YASA2 = ("Harmanda IKI kitap vardir ve bacaklari FARKLI, yani evren kayiplari "
         "da farklidir: tam evrendeki +21,07, sleeve'in 10 $ bacaginda "
         "+12,69'a iner. Bir harmani tam evrende olcup sermaye esigini ayri "
         "hesaplamak, iki hatayi birbirine EKLER.")
YASA3 = ("Bir basamak fonksiyonu da yapilandirmaya bagli olabilir: madde "
         "295'in -13,36'si 15x5'te olculmustu, 13x3'te gercek kayip -9,83. "
         "Olculmus bir sabiti BASKA bir yapilandirmaya tasimak, onu "
         "olculmemis bir tahmine cevirir.")


# ---------------------------------------------------------------- HÜKÜM

def sinyal_13x3_te_daha_mi_degerli() -> bool:
    return SINYAL_DEGERI["13x3"] > SINYAL_DEGERI["15x5"]


def tam_evren_ucu_kat_mi(kat: float = 2.5) -> bool:
    return HARMAN_TAM[0.3][7] > kat * MADDE298_15X5["dnet"]


def sart1_temiz_mi() -> bool:
    """13x3'te sart 1 iki fazda da 15x5'ten BELIRGIN daha iyi mi?"""
    return (HARMAN_TAM[0.3][3] - TAM_EVREN["KONTROL 13x3"][3]
            > MADDE298_15X5["sart1"][0] * 5)


def plasebo_harmani_negatif_mi() -> bool:
    return all(v < 0 for v in PLASEBO_HARMAN.values())


def momentum_plaseboyu_gecti_mi() -> bool:
    return (MOM_VS_PLASEBO_P >= 95.0
            and HARMAN_VS_PLASEBO["P"] >= 95.0)


def esik_dustu_mu() -> bool:
    return ESIK_USD < MADDE298_15X5["esik_usd"]


def esik_kati() -> float:
    return round(ESIK_USD / KULLANICI_BAKIYE, 2)


def kullanici_bakiyesinde_kosar_mi() -> bool:
    return KULLANICI_BAKIYE >= ESIK_USD


def tam_evren_gercekten_fazla_mi() -> bool:
    """Tam evren +21,07, gercek 3.250 $'da +12,69 -> fark anlamli mi?"""
    return HARMAN_TAM[0.3][7] > MERDIVEN[1][4]


def her_bakiyede_sart123_geciyor_mu() -> bool:
    return all(s[0][0] > 0 and s[0][1] > 0 and s[1] < 0 and s[2] > 0
               for s in SARTLAR.values())


def her_bakiyede_bar_geciliyor_mu() -> bool:
    return all(s[4] >= BAR_P for s in SARTLAR.values())


def yalniz_sart4_mu_dusuyor() -> bool:
    return (her_bakiyede_sart123_geciyor_mu()
            and all(s[3] > 1.005 for s in SARTLAR.values()))


def sart4_kacinci_aday() -> int:
    return len(SART4_SICIL)


def evren_maliyeti_yapilandirmaya_bagli_mi(tol: float = 1.0) -> bool:
    return abs(abs(MADDE295_BASAMAK) - abs(OLCULEN_13X3)) > tol


def madde304_kitabi_kotu_mu_gosteriyor() -> bool:
    return MADDE304_SAPMASI > 0


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    return ("ACIK VE EN GUCLU: trend sleeve 13x3'te tam evrende +21,07 puan "
            "(P %90,3) - 15x5'teki +7,61'in (P %81,0) yaklasik UC KATI, cunku "
            "13x3'un dozu daha dusuk ve dususu daha yuksek. GERCEK evren "
            "kaybiyla (iki kitabin bacaklari FARKLI, eleme kumeleri de) "
            "3.250 $'da **+12,69**, 8.000 $'da **+20,16** puan. Her bakiyede "
            "sart 1, 2 ve 3 GECIYOR ve kanit bari (%80) GECILIYOR (P %82,9 / "
            "%91,0 / %88,0); yalniz sart 4 dusuyor (kaldirac 1,10-1,15x) ki "
            "kural onu AYRI bir kaldirac karari sayiyor. Sart 4'ten tek "
            "basina dusen DORDUNCU aday, ama ilk kez kazanc buyuk, kanit "
            "gercek sermayede ve esik kullanicinin bakiyesinin 1,6 kati "
            "(9.375 $ degil **3.250 $**). 2.000 $'da KOSMUYOR; ayar "
            "DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("KAYNAK: %s\n" % KAYNAK)

    print("1) TAM EVREN (sleeve REZERV=%d; %s):"
          % (SLEEVE_REZERV, SLEEVE_REZERV_GEREKCE))
    print("   %-16s %8s %7s %7s %7s %7s %8s %9s %7s"
          % ("kitap", "CAGR", "Sh", "dusus", "Sh22", "Sh25", "doz", "net", "rho"))
    for ad, v in TAM_EVREN.items():
        print("   %-16s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %7.3f"
              % (ad, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]))
    print("   mom1 vs PLASEBO tek basina: P(Sh) %%%.1f" % MOM_VS_PLASEBO_P)
    print("   sinyalin degeri: 13x3 %+.3f vs 15x5 %+.3f -> 13x3'te daha mi "
          "degerli: %s" % (SINYAL_DEGERI["13x3"], SINYAL_DEGERI["15x5"],
                           sinyal_13x3_te_daha_mi_degerli()))
    print("   %-5s %8s %7s %7s %7s %7s %8s %9s %8s %7s"
          % ("w", "CAGR", "Sh", "dusus", "Sh22", "Sh25", "doz", "net",
             "dnet", "P(Sh)"))
    for w in sorted(HARMAN_TAM):
        v = HARMAN_TAM[w]
        print("   %-5.1f %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %+8.2f %6.1f%%"
              % (w, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8]))
    print("   madde 298 (15x5): dnet %+.2f, P %%%.1f -> uc kat mi: %s"
          % (MADDE298_15X5["dnet"], MADDE298_15X5["P"], tam_evren_ucu_kat_mi()))
    print("   SEBEP: %s" % NEDEN_DAHA_DEGERLI)
    print("   sart 1 temiz mi (15x5'te kil payiydi): %s" % sart1_temiz_mi())
    print("   PLASEBO harmani: %s -> hepsi negatif mi: %s"
          % (PLASEBO_HARMAN, plasebo_harmani_negatif_mi()))
    print("   mom1 harmani vs plasebo harmani: %+.2f vs %+.2f, P %%%.1f -> "
          "gecti mi: %s" % (HARMAN_VS_PLASEBO["aday"],
                            HARMAN_VS_PLASEBO["plasebo"],
                            HARMAN_VS_PLASEBO["P"], momentum_plaseboyu_gecti_mi()))

    print("\n2) GERCEK EVREN KAYBI (%s):" % ELEME_DOGRULANDI)
    print("   %-9s %8s %7s %7s %7s %7s %8s %9s"
          % ("kol", "CAGR", "Sh", "dusus", "Sh22", "Sh25", "doz", "net"))
    for ad, v in KOLLAR.items():
        print("   %-9s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f"
              % (ad, v[0], v[1], v[2], v[3], v[4], v[5], v[6]))
    print("   %10s %8s %10s %10s %9s %10s %7s %7s"
          % ("bakiye", "en iyi w", "tek net", "harman", "fark", "sleeve bck",
             "kume_c", "kume_s"))
    for b, w, tn, hn, f, ls, kc, ks in MERDIVEN:
        if hn is None:
            print("   %9.0f$ %8s %+10.2f %10s %9s %9.2f$ %7s %7s  (sleeve < %.0f$)"
                  % (b, "-", tn, "KOSMUYOR", "-", ls, kc, ks, ASGARI_BACAK))
        else:
            print("   %9.0f$ %8.1f %+10.2f %+10.2f %+9.2f %9.2f$ %7s %7s"
                  % (b, w, tn, hn, f, ls, kc, ks))
    print("   tam evren FAZLA mi gosteriyordu: %s (+%.2f -> +%.2f)"
          % (tam_evren_gercekten_fazla_mi(), HARMAN_TAM[0.3][7], MERDIVEN[1][4]))
    print("   ESIK: %.0f $ (madde 298'de %.0f $) -> dustu mu: %s | "
          "kullanicinin bakiyesinin %.2f kati"
          % (ESIK_USD, MADDE298_15X5["esik_usd"], esik_dustu_mu(), esik_kati()))
    print("   kullanici bakiyesinde kosar mi: %s" % kullanici_bakiyesinde_kosar_mi())

    print("\n3) DORT SART, GERCEK KOLLARDA:")
    print("   %10s %22s %10s %10s %14s %8s"
          % ("bakiye", "sart 1 (Sh22/Sh25)", "sart 2", "sart 3", "sart 4", "P(Sh)"))
    for b, (s1, s2, s3, s4, p) in sorted(SARTLAR.items()):
        print("   %9.0f$   OK (%+.3f/%+.3f)  OK (%+.2f)  OK (%+.1f)  RED (%.3fx) %7.1f%%"
              % (b, s1[0], s1[1], s2, s3, s4, p))
    print("   her bakiyede sart 1-2-3 geciyor mu: %s"
          % her_bakiyede_sart123_geciyor_mu())
    print("   her bakiyede kanit bari (>=%%%.0f) geciliyor mu: %s"
          % (BAR_P, her_bakiyede_bar_geciliyor_mu()))
    print("   yalniz sart 4 mu dusuyor: %s" % yalniz_sart4_mu_dusuyor())
    print("   %s" % SART4_METNI)
    print("   sart 4'ten tek basina dusen %d. aday (sicil %s)"
          % (sart4_kacinci_aday(), list(SART4_SICIL)))
    print("   ILK KEZ: %s" % ILK_KEZ)

    print("\n4) YAN BULGU - EVREN MALIYETI DE YAPILANDIRMAYA BAGLI:")
    print("   madde 295'in basamagi %+.2f (15x5'te olculdu)" % MADDE295_BASAMAK)
    print("   13x3'te OLCULEN kayip %+.2f (195,33 - 185,50)" % OLCULEN_13X3)
    print("   -> yapilandirmaya bagli mi: %s"
          % evren_maliyeti_yapilandirmaya_bagli_mi())
    print("   madde 304'un merdiveni 13x3'u %.2f puan KOTU gosteriyor: %s"
          % (MADDE304_SAPMASI, madde304_kitabi_kotu_mu_gosteriyor()))
    print("   %s" % MERDIVEN_DUZELTILMEDI)

    print("\n5) KULLANICI ICIN: %s" % ONERI)
    print("   HEDEF: %s" % HEDEF)
    print("   ayar degisti mi: %s" % ayar_degisti_mi())

    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
