#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 300 — TP EŞİKLERİ 13x3 KİTABINDA DA ZATEN EN İYİ. VE YANLIŞ
NİCELİK, MADDE 299'UN TERSİ YÖNDE DE HATA YAPAR: HAM GETİRİ BOOTSTRAP'I
TPL 0,55'İ %95,9 İLE **KABUL EDERDİ**.

Üç tur (297, 298, 299) "ayar değişmedi" ile kapandı. Ama hiç
sorulmamış bir şey vardı: **TP eşikleri 15x5 kitabı üzerinde
ayarlanmıştı**, kullanıcının koşacağı yapılandırma ise 13x3 (madde 295).
Üç bacaklı bir taraf daha yoğun, ve madde 298 hasadın yoğun kitapta
daha değerli olduğunu ölçtü (momentum kitabında hasat +0,91 Sharpe,
carry'de +0,74). Yani eşiklerin 13x3'te kaymış olması bekleneblirdi.

Bu eksen doğrudan kullanıcının 2.000 $'ına ait ve hiç taranmamıştı.

═══ 1. KONTROL: 13x3 ═══

    FAZ=13, 3+3 bacak, TPL=0,40 TPS=0,20, kalan ayar aynen kontrol
    CAGR +149,95 · Sharpe 2,886 · düşüş **17,68** · doz 1,200x · net +195,33

ÇAPRAZ DOĞRULAMA: düşüş 17,68, madde 295'in `DUSUS["13x3"]=17,68`
kaydıyla **birebir aynı**. Yani bu kontrol, madde 295'in ölçtüğü kitabın
kendisi.

(15x5 kontrolünden farkı: CAGR +149,95 vs +112,27 ama düşüş 17,68 vs
14,54 ve doz 1,200x vs 1,505x ⇒ net +195,33 vs +200,85. Madde 295'in
"13x3 yapısal maliyeti −5,52 puan" kaydıyla tutarlı: üç bacak daha
yoğun, hem getiriyi hem riski yükseltir, eşit riskte geride kalır.)

═══ 2. TARAMA: ALTI KOL, ALTISI DA RED ═══

    kol                CAGR      Sh   dusus    Sh22    Sh25     doz      net   P(Sh)  P(ham)
    KONTROL         +149,95   2,886   17,68   2,706   3,134  1,200x  +195,33     -       -
    TPL 0,25        +109,26   2,612   18,51   2,536   2,722  1,230x  +143,86  %0,5    %0,0
    **TPL 0,55**    +162,46   2,851   17,96   2,669   3,101  1,115x  +190,07 %34,9  **%95,9**
    TPL 0,70        +163,02   2,737   19,02   2,630   2,898  1,042x  +172,33 %10,2   %92,6
    TPS 0,12        +135,98   2,705   20,53   2,645   2,796  1,155x  +165,92  %5,5    %5,4
    TPS 0,28        +149,00   2,884   19,50   2,726   3,104  1,210x  +196,38 %44,2   %41,2
    TPS 0,40        +143,09   2,852   20,23   2,691   3,091  1,236x  +194,03 %36,0   %22,0

═══ 3. ASIL BULGU: YANLIŞ NİCELİK TERS YÖNDE DE YANILIR ═══

Madde 299'un 3. yasası şöyleydi: *bir çeşitlendiriciyi ham getiri
ortalamasıyla bootstraplamak onu REDDEDER (P %15,2) çünkü kazancı
riskte.* O yasa tek yönlüydü.

TPL 0,55 ters yönü gösteriyor:

    ham getiri bootstrap'i  P(>0) = **%95,9**  -> KABUL ederdi
    Sharpe bootstrap'i      P(>0) =   %34,9    -> kararsiz
    doz olcusu              net  **-5,26**     -> RED
    dort sart               sart 1'den duser (-0,037 ve -0,032)

Sebep açık: TPL 0,55 getiriyi **gerçekten** yükseltiyor (+162,46 vs
+149,95, ve bu %95,9 olasılıkla gerçek) ama riski de yükseltiyor
(doz 1,200x -> 1,115x), yani eşit riske ölçeklenince kazanç siliniyor.

**YASA: nicelik seçimi İKİ YÖNDE de hata yapar.** Ham getiri ölçüsü
çeşitlendiriciyi haksız REDDEDER (madde 299) ve getiriyi-ve-riski
birlikte yükselteni haksız KABUL EDER (madde 300). İkisi de aynı
hatanın iki yüzü: ölçü, kararın sorduğu soruyla aynı olmak zorunda.

═══ 4. EŞİKLERİN ŞEKLİ (operasyonel bilgi) ═══

**TPL'nin ALT KENARI SERT.** 0,25'e inmek net'ten **−51,47 puan**
alıyor (P %0,5). Mevcut 0,40 bu uçurumun güvenli tarafında.
Üst taraf ise düz-hafif kötü: 0,55 → −5,26, 0,70 → −23,00.

**TPS BİR PLATO.** 0,20 / 0,28 / 0,40 netleri: +195,33 / +196,38 /
+194,03 — birbirinden ayrışmıyor (P %44,2 ve %36,0). Ama 0,12 **−29,41**
puan. Yani short eşiği 0,20'nin ÜSTÜNDE hassas değil, ALTINDA sert.

Pratik sonuç: canlıda TPS'yi tam tutturma kaygısı gereksiz; TPL'yi
0,40'ın altına indirmek ise pahalı.

ÇÖZÜNÜRLÜK ÇEKİNCESİ: her eksende eşiğin altında bir, üstünde iki nokta
var. "Plato" ve "uçurum" bu çözünürlükte doğru, ama kenarların tam yeri
ölçülmedi. Daha ince bir tarama bu turun hükmünü değiştirmez (hiçbir kol
geçmedi), yalnız kenarları netleştirir.

═══ 5. ASİMETRİ 13x3'TE DE AYAKTA ═══

Kitap long'ta +%40, short'ta %20'de hasat ediyor. Tarama bu asimetriyi
13x3'te de doğruluyor: long tarafı aşağı doğru uçurumlu (0,25 → −51,47),
short tarafı yukarı doğru düz (0,28/0,40 → ±1 puan). Yani eşiklerin
15x5'te bulunan asimetrik şekli yapılandırmaya özgü DEĞİL.

═══ 6. SONUÇ ═══

TP eşikleri 13x3'te de zaten en iyi: **TPL=0,40 TPS=0,20 değişmiyor.**
Altı kolun hiçbiri kanıt barını geçmedi; en yakını TPS 0,28 (net +1,05,
P %44,2) ki bu gürültü.

Kullanıcı için: öneri aynen **13 dilim x 3 bacak, 2.000 $, 1x**.

AYAR DEĞİŞMEDİ.
"""

# ---------------------------------------------------------------- SABİTLER

SORU = ("TP esikleri (TPL=0,40 TPS=0,20) 15x5 kitabi uzerinde ayarlanmisti. "
        "Kullanicinin kosacagi yapilandirma 13x3 (madde 295) ve uc bacakli "
        "taraf daha yogun. Esikler kaymis mi?")

NEDEN_BEKLENIRDI = (
    "Madde 298 hasadin YOGUN kitapta daha degerli oldugunu olctu: hasat "
    "momentum kitabina +0,91 Sharpe, carry'ye +0,74. 13x3'te taraf basina "
    "3 bacak var (15x5'te 5), yani kitap daha yogun.")

# --- 1. kontrol ---
KONTROL = {"ad": "13x3 TPL0,40/TPS0,20", "cagr": 149.95, "sh": 2.886,
           "dd": 17.68, "sh22": 2.706, "sh25": 3.134, "doz": 1.200,
           "net": 195.33}
KONTROL_15X5 = {"cagr": 112.27, "sh": 2.939, "dd": 14.54, "doz": 1.505,
                "net": 200.85}
MADDE295_DUSUS_13X3 = 17.68
"""arastirma_evren_esigi.DUSUS["13x3"]. Bu turun kontrolu birebir ayni
dususu verdi -> capraz dogrulama."""
MADDE295_YAPISAL_13X3 = -5.52
"""13x3'un 15x5'e gore yapisal maliyeti (madde 295). Bu turda da tutarli:
net +195,33 vs +200,85 = -5,52."""

# --- 2. tarama ---
TARAMA = {
    #  kol        : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net,    P(Sh)%, P(ham)%)
    "TPL 0,25": (109.26, 2.612, 18.51, 2.536, 2.722, 1.230, 143.86,  0.5,  0.0),
    "TPL 0,55": (162.46, 2.851, 17.96, 2.669, 3.101, 1.115, 190.07, 34.9, 95.9),
    "TPL 0,70": (163.02, 2.737, 19.02, 2.630, 2.898, 1.042, 172.33, 10.2, 92.6),
    "TPS 0,12": (135.98, 2.705, 20.53, 2.645, 2.796, 1.155, 165.92,  5.5,  5.4),
    "TPS 0,28": (149.00, 2.884, 19.50, 2.726, 3.104, 1.210, 196.38, 44.2, 41.2),
    "TPS 0,40": (143.09, 2.852, 20.23, 2.691, 3.091, 1.236, 194.03, 36.0, 22.0),
}
BAR_P = 80.0

# --- 3. asil bulgu: iki yonlu nicelik hatasi ---
AYNA_ADAY = "TPL 0,55"
AYNA = {
    "ham getiri P": 95.9,     # KABUL ederdi
    "Sharpe P": 34.9,         # kararsiz
    "doz net farki": -5.26,   # RED
    "sart1 Sh22 farki": -0.037,
    "sart1 Sh25 farki": -0.032,
}
AYNA_SEBEBI = (
    "TPL 0,55 getiriyi GERCEKTEN yukseltiyor (+162,46 vs +149,95, ve bu "
    "%95,9 olasilikla gercek) ama riski de yukseltiyor (doz 1,200x -> "
    "1,115x), yani esit riske olceklenince kazanc siliniyor.")
MADDE299_YASA3 = ("Bir cesitlendiriciyi ham getiri ortalamasiyla "
                  "bootstraplamak onu REDDEDER (P %15,2) cunku kazanci "
                  "riskte.")

# --- 4. esiklerin sekli ---
TPL_ALT_UCURUM = {"esik": 0.25, "net_farki": -51.47, "P": 0.5}
TPL_UST = {0.55: -5.26, 0.70: -23.00}
TPS_PLATO = {0.20: 195.33, 0.28: 196.38, 0.40: 194.03}
TPS_ALT_UCURUM = {"esik": 0.12, "net_farki": -29.41, "P": 5.5}
COZUNURLUK_CEKINCESI = (
    "Her eksende esigin ALTINDA bir, USTUNDE iki nokta var. 'Plato' ve "
    "'ucurum' bu cozunurlukte dogru, ama kenarlarin TAM YERI olculmedi. "
    "Daha ince bir tarama bu turun hukmunu degistirmez (hicbir kol "
    "gecmedi), yalniz kenarlari netlestirir.")
OPERASYONEL = ("Canlida TPS'yi tam tutturma kaygisi gereksiz (0,20-0,40 "
               "arasi ayrismiyor); TPL'yi 0,40'in ALTINA indirmek pahali.")

# --- 5. asimetri ---
ASIMETRI_13X3_DE_AYAKTA = True
ASIMETRI_NOTU = ("Long tarafi asagi dogru ucurumlu (0,25 -> -51,47), short "
                 "tarafi yukari dogru duz (0,28/0,40 -> ±1 puan). Esiklerin "
                 "15x5'te bulunan asimetrik sekli YAPILANDIRMAYA OZGU DEGIL.")

AYAR = {"TPL": 0.40, "TPS": 0.20}
AYAR_DEGISTI = False
ONERI = "13 dilim x 3 bacak, 2.000 $, 1x (DEGISMEDI)"

YASA1 = ("Nicelik secimi IKI YONDE de hata yapar: ham getiri olcusu bir "
         "cesitlendiriciyi haksiz REDDEDER (madde 299, P %15,2) ve "
         "getiriyi-ve-riski birlikte yukselten bir adayi haksiz KABUL EDER "
         "(madde 300, P %95,9). Ikisi ayni hatanin iki yuzu: olcu, kararin "
         "SORDUGU SORUYLA ayni olmak zorunda.")
YASA2 = ("Bir esik iki yonde ayni sekle sahip olmayabilir: TPL'nin ALT "
         "kenari sert (-51,47 puan), UST tarafi duz-hafif kotu; TPS 0,20'nin "
         "USTUNDE plato, ALTINDA sert. 'Optimum' demek yetmez - kenarin "
         "HANGI YONDE sert oldugu operasyonel bir bilgidir.")
YASA3 = ("Bir yapilandirma degisirse ona gore ayarlanmis SANILAN parametreler "
         "yeniden sinanmali - ama sonuc 'degismedi' de olabilir: TP esikleri "
         "15x5'te bulunmustu ve 13x3'te de en iyi cikti, yani bu esikler "
         "yapilandirmaya degil MEKANIZMAYA ait.")


# ---------------------------------------------------------------- HÜKÜM

def kontrol_madde295_ile_tutuyor_mu(tol: float = 0.01) -> bool:
    """13x3 kontrolunun dususu madde 295'in kaydiyla ayni mi?"""
    return abs(KONTROL["dd"] - MADDE295_DUSUS_13X3) <= tol


def yapisal_maliyet_tutuyor_mu(tol: float = 0.05) -> bool:
    """net farki madde 295'in -5,52 kaydiyla tutuyor mu?"""
    return abs((KONTROL["net"] - KONTROL_15X5["net"])
               - MADDE295_YAPISAL_13X3) <= tol


def gecen_kol_var_mi() -> bool:
    return any(v[7] >= BAR_P for v in TARAMA.values())


def en_yakin_kol() -> str:
    return max(TARAMA, key=lambda a: TARAMA[a][7])


def ham_olcu_yanlis_kabul_eder_mi() -> bool:
    """TPL 0,55'i ham getiri olcusu kabul, doz olcusu red mi ediyor?"""
    return AYNA["ham getiri P"] >= 95.0 and AYNA["doz net farki"] < 0


def nicelik_hatasi_iki_yonlu_mu() -> bool:
    """Madde 299 (haksiz red) ve madde 300 (haksiz kabul) birlikte mi?"""
    return ham_olcu_yanlis_kabul_eder_mi() and "REDDEDER" in MADDE299_YASA3


def tpl_alt_kenari_sert_mi(esik: float = 25.0) -> bool:
    return abs(TPL_ALT_UCURUM["net_farki"]) >= esik


def tps_plato_mu(tol: float = 3.0) -> bool:
    v = list(TPS_PLATO.values())
    return max(v) - min(v) < tol


def tps_alt_kenari_sert_mi(esik: float = 20.0) -> bool:
    return abs(TPS_ALT_UCURUM["net_farki"]) >= esik


def esik_sekli_asimetrik_mi() -> bool:
    """TPL asagi sert / yukari duz, TPS yukari duz / asagi sert?"""
    return (tpl_alt_kenari_sert_mi() and abs(TPL_UST[0.55]) < 10.0
            and tps_plato_mu() and tps_alt_kenari_sert_mi())


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    if gecen_kol_var_mi():
        return "ACIK: kanit esigini gecen bir TP esigi var."
    return ("RED: TP esikleri 13x3 kitabinda da ZATEN EN IYI - TPL=0,40 "
            "TPS=0,20 degismiyor. Alti kolun hicbiri kanit barini gecmedi; "
            "en yakini TPS 0,28 (net +1,05, P %44,2) ki gurultu. BU TURUN "
            "ASIL BULGUSU AYRI: TPL 0,55'i HAM GETIRI bootstrap'i %95,9 ile "
            "KABUL ederdi, doz olcusu reddediyor (net -5,26) - madde "
            "299'un yanlis-nicelik yasasinin TERS yonu. Oneri ve ayar "
            "DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("SORU: %s" % SORU)
    print("NEDEN BEKLENIRDI: %s\n" % NEDEN_BEKLENIRDI)

    print("1) KONTROL (13x3):")
    print("   CAGR %+.2f · Sharpe %.3f · dusus %.2f · doz %.3fx · net %+.2f"
          % (KONTROL["cagr"], KONTROL["sh"], KONTROL["dd"], KONTROL["doz"],
             KONTROL["net"]))
    print("   madde 295'in DUSUS['13x3']=%.2f kaydiyla tutuyor mu: %s"
          % (MADDE295_DUSUS_13X3, kontrol_madde295_ile_tutuyor_mu()))
    print("   15x5 ile fark: net %+.2f vs %+.2f = %+.2f "
          "(madde 295 yapisal kaydi %+.2f, tutuyor mu: %s)"
          % (KONTROL["net"], KONTROL_15X5["net"],
             KONTROL["net"] - KONTROL_15X5["net"], MADDE295_YAPISAL_13X3,
             yapisal_maliyet_tutuyor_mu()))

    print("\n2) TARAMA:")
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

    print("\n3) ASIL BULGU - YANLIS NICELIK TERS YONDE DE YANILIR:")
    print("   madde 299 yasa 3: %s" % MADDE299_YASA3)
    print("   %s icin:" % AYNA_ADAY)
    print("     ham getiri bootstrap'i P(>0) = %%%.1f  -> KABUL ederdi"
          % AYNA["ham getiri P"])
    print("     Sharpe bootstrap'i     P(>0) = %%%.1f  -> kararsiz"
          % AYNA["Sharpe P"])
    print("     doz olcusu             net   = %+.2f   -> RED"
          % AYNA["doz net farki"])
    print("     dort sart: sart 1'den duser (%+.3f ve %+.3f)"
          % (AYNA["sart1 Sh22 farki"], AYNA["sart1 Sh25 farki"]))
    print("   SEBEP: %s" % AYNA_SEBEBI)
    print("   ham olcu yanlis KABUL eder mi: %s | hata iki yonlu mu: %s"
          % (ham_olcu_yanlis_kabul_eder_mi(), nicelik_hatasi_iki_yonlu_mu()))

    print("\n4) ESIKLERIN SEKLI:")
    print("   TPL alt ucurumu: %.2f -> net %+.2f (P %%%.1f) | sert mi: %s"
          % (TPL_ALT_UCURUM["esik"], TPL_ALT_UCURUM["net_farki"],
             TPL_ALT_UCURUM["P"], tpl_alt_kenari_sert_mi()))
    print("   TPL ust tarafi: %s (duz-hafif kotu)" % TPL_UST)
    print("   TPS platosu: %s | plato mu: %s" % (TPS_PLATO, tps_plato_mu()))
    print("   TPS alt ucurumu: %.2f -> net %+.2f | sert mi: %s"
          % (TPS_ALT_UCURUM["esik"], TPS_ALT_UCURUM["net_farki"],
             tps_alt_kenari_sert_mi()))
    print("   esik sekli asimetrik mi: %s" % esik_sekli_asimetrik_mi())
    print("   OPERASYONEL: %s" % OPERASYONEL)
    print("   CEKINCE: %s" % COZUNURLUK_CEKINCESI)

    print("\n5) ASIMETRI: %s" % ASIMETRI_NOTU)
    print("   13x3'te de ayakta mi: %s" % ASIMETRI_13X3_DE_AYAKTA)

    print("\n6) AYAR: %s (degisti mi: %s) | oneri: %s"
          % (AYAR, ayar_degisti_mi(), ONERI))

    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
