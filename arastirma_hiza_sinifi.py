#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 332 — **HİZA İKİ SINIFTAN İBARET, ARALARINDAKİ 15 PUANLIK "NET"
FARKI BİR METRİK ARTEFAKTI, VE ÖN KAYITLI KURAL İKİ YÖNDE DE RED
VERİYOR. AYRICA MADDE 331'İN BAŞLIK DÜZELTMESİ YANLIŞTI.**

*** BU DOSYA 2026-10-19'DA TRANSKRİPTTEN YENİDEN YAZILDI (madde 335).
Özgün hâli konteyner kaybında gitti. ***

═══ 0. MADDE 331'İN HATASI (benim hatam) ═══

Madde 331'de "üç hiza ölçtüm, medyan +159,48, yayınlanan **9,35 puan
iyimser**" dedim. **Üç hiza değildi.** Motorun faz adımı
`adim = REB//FAZ = 30//15 = 2`; bu yüzden ofsetler **parite** sınıfına
ayrılır:

    faz kumesi (mod 30):  k CIFT -> {0,2,...,28}   k TEK -> {1,3,...,29}
    farkli faz kumesi sayisi: **2** (hepsi bu)
    k=0 ile ortak faz: k=2 -> 14/15 · k=4 -> 14/15 · k=1 -> **0/15**

Yani ofset 0 ve 2 **aynı sınıf**, ofset 1 **öteki sınıf**. Medyanını
aldığım üç ölçümün **ikisi aynı sınıftı** → "medyan" hiza medyanı değil
çift sınıfın değeriydi.

**ÖN KAYITLI TAHMİN VE DOĞRULAMA** (madde 324'te mekanizma tahminim
çürümüştü; bu kez tuttu): ofset 3 TEK ⇒ ≈+174, ofset 4 ÇİFT ⇒ ≈+159
dedim, sonra ölçtüm:

    ofset  sinif   CAGR     dusus    doz       net
      0    CIFT  +117,60   19,07   1,250x   +159,48
      2    CIFT  +117,50   19,07   1,249x   +159,23
      4    CIFT  +117,19   19,07   1,253x   **+159,43**  <- tahmin +159,4
      1    TEK   +121,65   20,92   1,293x   +174,00
      3    TEK   +122,04   20,92   1,294x   **+174,78**  <- tahmin +174,0
    ic yayilim: CIFT 0,25 puan · TEK 0,78 puan
    siniflar arasi: **~15,0 puan**

**DÜZELTME:** iki sınıf eşit olasılıklıysa hizaya göre **beklenen net
≈+166,9**; yayınlanan **+168,83** bunun **1,9 puan** üstünde, 9,35
değil.

═══ 1. ASIL BULGU — 15 PUAN BİR METRİK ARTEFAKTI ═══

Ön kayıtlı kural (`karar_kurali.gecer_mi`, KOD) **iki yönde de RED**:

    kontrol -> aday        sartlar  gecer   esit riskte getiri
    CIFT-0  -> TEK-1       YYRY     False   %+106,0 vs %+117,6 (**−11,6**) [0,90x]
    TEK-1   -> CIFT-0      RYYR     False   +13,6 ama **1,11x** kaldirac
    CIFT-2  -> TEK-3       YYRY     False   −11,2 [0,90x]
    CIFT-4  -> TEK-3       YYRY     False   −10,9 [0,90x]

TEK sınıf **iki dönemde de daha yüksek Sharpe** veriyor (22-24 2,617 vs
2,519 · 25-26 2,970 vs 2,912) ve düşüş toleransını da geçiyor (+1,86 <
3,0) — **ama eşit riskte 11 puan GERİDE.**

⇒ **Hiza bir tercih değil: hangi sınıf olursa olsun ön kayıtlı kural bir
üstünlük görmüyor.**

**NEDEN "NET" 15 PUAN DİYOR — ÖLÇÜLDÜ.** Madde 287'nin dozu,
**TAM KARIŞTIRMA** (i.i.d.) p95 düşüşünü −%30 yapan `k`dır. Tam
karıştırma **yolu yok eder**, yani kayıpların kümelenmesini görmez:

    sinif    gercek dd   TAM KARIS.   blok 21   blok 5
    CIFT-0     19,07       24,58       20,45     22,97
    TEK-1      **20,92**   **23,87**   20,28     22,50

- **Gerçekleşen** düşüş: ÇİFT **1,85 puan daha iyi**
- **Tam karıştırma** (dozun gördüğü): TEK **0,71 puan daha iyi**
- **Kümelenmeyi koruyan** blok bootstrap: fark **0,17-0,47 puan**

⇒ **0,71 puanlık, yolu yok eden bir kuyruk farkı, kaldıraç çözümüyle
15 puanlık "net" farkına büyüyor (~21 kat)** — oysa botun gerçekten
yaşadığı düşüş ters yönde.

═══ 2. BU, YALNIZCA HİZA SORUNU DEĞİL ═══

Dozun bu körlüğü **her yayınlanan "net" için** geçerlidir (madde
287/288/304/313/316/320/325/326). Bu madde o sayıları **yeniden
yazmıyor** ama uyarıyı yasa olarak kaydediyor ve en yakın riski ölçüyor:

**MADDE 288 (`CARRY_PRIM_E=0.10`) net ile kabul edilmişti.**
Eşleştirilmiş iki kol (aynı ofset, aynı kitap, tek fark 288):

    kol                      22-24 ΔSh   25-26 ΔSh   esit risk  kaldirac  net
    madde 288 kaydi (15x5)     +0,082     **+0,012**    +8,6      1,019x  +8,24
    kosan kitap, ofset 9       +0,090     **−0,009**    +7,0      1,001x  +8,43
    kosan kitap, ofset 10      +0,088     **−0,009**    +6,1      0,996x  +8,41

İki **bağımsız** hiza sınıfında **birebir aynı −0,009** ⇒ **gürültü
değil, yeniden üretilebilir.** 288'in kabulü **+0,012** marjıyla
alınmıştı; koşan kitapta aynı ayar **−0,009** veriyor — 0,021 puanlık
salınım ve **tek değişken KİTAP**.

**Kazanç ARTEFAKT DEĞİL** (eşit riskte +6,1/+7,0, kaldıraçsız) ama
kural **RED** diyor. Karar **fiyatlandı, tek taraflı verilmedi**:
1. **Kural harfiyen:** 288 koşan kitapta **geri alınır**.
2. **Eşit-risk kanıtı:** ~**+6,5 puan** kaldıraçsız masada kalır;
   düşen şart 25-26'da −0,009, yani pratikte beraberlik.

═══ 3. AÇIK EKSEN (dürüst) ═══

Beş ofset ölçüldü (0-4); parite yapısı mod 30'da **iki sınıf** olduğu
için bu yeterli, ama mutlak başlangıç kayması yüzünden aynı sınıf içinde
14/15 örtüşme var — iç yayılım (0,25/0,78) bu yüzden **alt sınır**
olabilir. Dozun kümelenme körlüğü **nicelendi** ama projenin bütün net
tablosu yeniden üretilmedi.

AYAR DEĞİŞMEDİ. Bu madde bir **metrik denetimi** ve madde 331'in
**düzeltmesinin düzeltmesi**.
"""

from __future__ import annotations

YENIDEN_YAZILDI = True

# ───────── 0. MADDE 331'İN HATASI
MADDE331_HATASI = ("madde 331 'uc hiza olctum, medyan +159,48' dedi; "
                   "UC HIZA DEGILDI - ucun IKISI ayni parite sinifiydi "
                   "(ofset 0 ve 2, 15 fazin 14'u ortak)")
ADIM = 30 // 15          # 2
FARKLI_FAZ_KUMESI = 2
ORTAK_FAZ = {2: 14, 4: 14, 1: 0}
TAHMIN = {3: 174.0, 4: 159.4}
OLCUM = {   # ofset -> (sinif, CAGR, dusus, doz, net)
    0: ("CIFT", 117.60, 19.07, 1.250, 159.48),
    2: ("CIFT", 117.50, 19.07, 1.249, 159.23),
    4: ("CIFT", 117.19, 19.07, 1.253, 159.43),
    1: ("TEK", 121.65, 20.92, 1.293, 174.00),
    3: ("TEK", 122.04, 20.92, 1.294, 174.78),
}
IC_YAYILIM = {"CIFT": 0.25, "TEK": 0.78}
SINIFLAR_ARASI = 15.0
BEKLENEN_NET = 166.9
KAYITLI_NET = 168.83
MADDE331_DUZELTMESI = ("yayinlanan +168,83, hizaya gore BEKLENEN "
                       "+166,9'un 1,9 puan ustunde - madde 331'in "
                       "'9,35 puan iyimser' sayisi YANLISTI")

# ───────── 1. ÖN KAYITLI KURAL
KURAL = {   # "kontrol -> aday" -> (sartlar, gecer, esit risk puan, kaldirac)
    "CIFT-0 -> TEK-1": ("YYRY", False, -11.6, 0.90),
    "TEK-1 -> CIFT-0": ("RYYR", False, +13.6, 1.11),
    "CIFT-2 -> TEK-3": ("YYRY", False, -11.2, 0.90),
    "CIFT-4 -> TEK-3": ("YYRY", False, -10.9, 0.90),
}
SHARPE_ALT_DONEM = {"CIFT": (2.519, 2.912), "TEK": (2.617, 2.970)}
DUSUS_FARKI_PUAN = 20.92 - 19.07      # 1.85 (tolerans 3,0)

# ───────── 1b. METRİK ARTEFAKTI
P95_DUSUS = {   # sinif -> (gercek dd, tam karistirma, blok 21, blok 5)
    "CIFT-0": (19.07, 24.58, 20.45, 22.97),
    "TEK-1":  (20.92, 23.87, 20.28, 22.50),
}
TAM_KARISTIRMA_FARKI = 24.58 - 23.87    # 0.71 (TEK daha iyi)
GERCEK_DUSUS_FARKI = 20.92 - 19.07      # 1.85 (CIFT daha iyi)
BLOK_FARKI = (20.45 - 20.28, 22.97 - 22.50)
BUYUTME = SINIFLAR_ARASI / TAM_KARISTIRMA_FARKI   # ~21x
MEKANIZMA = ("madde 287'nin dozu TAM KARISTIRMA p95 dususunu -%30 yapan "
             "k'dir; tam karistirma YOLU YOK EDER, kayiplarin "
             "KUMELENMESINI gormez")

# ───────── 2. KAPSAM + MADDE 288
ETKILENEN_MADDELER = (287, 288, 304, 313, 316, 320, 325, 326)
YENIDEN_YAZILDI_MI = False
KAPSAM_NOTU = ("bu madde o sayilari yeniden YAZMIYOR ama uyariyi YASA "
               "olarak kaydediyor ve en yakin riski (madde 288) "
               "ESLESTIRILMIS kontrolle siniyor")
MADDE288 = {
    "kontrol": dict(getiri=120.39, sharpe=2.747, erken=2.585, gec=2.970,
                    dusus=20.92, doz=1.301, net=173.58),
    "aday":    dict(getiri=127.18, sharpe=2.792, erken=2.675, gec=2.960,
                    dusus=20.90, doz=1.290, net=182.01),
    "net_farki": 182.01 - 173.58,
    "esit_risk_puan": 7.0, "kaldirac": 1.001,
    "sartlar": "RYYY", "gecer": False,
    "dusen_sart": ("iki donemde Sharpe (25-26 -0,009; modulde Sharpe'lar "
                   "UC HANEYE yuvarli, yuvarli fark -0,010)"),
}
MADDE288_IKINCI = {
    "kontrol": dict(getiri=117.45, sharpe=2.682, erken=2.512, gec=2.912,
                    dusus=19.07, doz=1.240, net=157.32),
    "aday":    dict(getiri=124.19, sharpe=2.727, erken=2.600, gec=2.903,
                    dusus=19.13, doz=1.232, net=165.73),
    "net_farki": 165.73 - 157.32,
    "esit_risk_puan": 6.1, "kaldirac": 0.996,
    "sartlar": "RYYY", "gecer": False,
    "dusen_sart": "iki donemde Sharpe (25-26 -0,009)",
}
MADDE288_KAYIT = {"erken": 0.082, "gec": 0.012, "esit_risk": 8.6,
                  "kaldirac": 1.019, "net": 8.24}
MADDE288_YENI_HUKUM = ("IKI BAGIMSIZ HIZA SINIFINDA AYNI SONUC: 22-24 "
    "+0,090 / +0,088 · 25-26 **-0,009 / -0,009** · esit riskte +7,0 / "
    "+6,1 puan, kaldirac 1,00x · net +8,43 / +8,41. -0,009 GURULTU "
    "DEGIL, YENIDEN URETILEBILIR. Madde 288'in kabulu 15x5 TAM evren "
    "kitabinda **+0,012** marjiyla alinmisti; KOSAN kitapta ayni ayar "
    "-0,009 veriyor, yani 0,021 puanlik salinim ve TEK degisken KITAP. "
    "Kural KODDUR: kosan kitapta gecer_mi() = **RED**. Ama kazanc "
    "ARTEFAKT DEGIL (esit riskte +6,1/+7,0, kaldiracsiz) - bu yuzden "
    "karar FIYATLANIR, tek tarafli verilmez.")
MADDE288_KARAR_KULLANICININ = True

# ───────── 3. AÇIK EKSEN
ACIK_EKSEN = ("bes ofset olculdu (0-4); parite yapisi mod 30'da IKI "
              "sinif oldugu icin yeterli, ama ayni sinif icinde 14/15 "
              "ortusme var - ic yayilim ALT SINIR olabilir")
PARITE_SECILEBILIR_MI = True
PARITE_NASIL = ("gun bazinda kayma pariteyi KORUR (6 bar), 4 saatlik "
                "kayma CEVIRIR - yani secilebilir, AMA kural reddetti")
AYAR_DEGISTI = False

YASA1 = ("Bir 'hiza taramasi' once YAPISAL olarak cozulur: faz adimi "
         "REB//FAZ ise ofsetler PARITE sinifina ayrilir ve mod 30'da "
         "yalnizca IKI farkli faz kumesi vardir.")
YASA2 = ("Yolu yok eden bir risk olcutu uzerine kurulmus bir kaldirac "
         "metrigi kumelenen kayiplari GORMEZ: 0,71 puanlik kuyruk farki "
         "15 puanlik 'net' farkina buyuyebilir.")
YASA3 = ("Iki olcut bir siralamayi TERS ceviriyorsa hakem ON KAYITLI "
         "KURALDIR.")
YASA4 = ("Bir ON KAYITLI TAHMIN tutarsa yazilir, tutmazsa da yazilir.")
YASA5 = ("Bir kazancin GERCEK olmasi, KURALDAN GECMESI demek degildir; "
         "gurultu icindeki bir farkta TEK KOL karar vermez.")


# ───────── DOĞRULAMA
def iki_sinif_mi():
    return FARKLI_FAZ_KUMESI == 2 and ADIM == 2


def madde331in_ucu_ikisi_ayni_sinif_miydi():
    return ORTAK_FAZ[2] == 14 and ORTAK_FAZ[1] == 0


def tahminler_tuttu_mu(tol=1.0):
    return all(abs(OLCUM[k][4] - v) < tol for k, v in TAHMIN.items())


def ic_yayilim_siniflar_arasindan_kucuk_mu():
    return max(IC_YAYILIM.values()) < SINIFLAR_ARASI / 10


def kural_iki_yonde_de_red_mi():
    return all(not v[1] for v in KURAL.values())


def tek_sinif_iki_donemde_de_ustun_mu():
    c, t = SHARPE_ALT_DONEM["CIFT"], SHARPE_ALT_DONEM["TEK"]
    return t[0] > c[0] and t[1] > c[1]


def esit_riskte_tersine_mi_donuyor():
    return KURAL["CIFT-0 -> TEK-1"][2] < 0 < SINIFLAR_ARASI


def gercek_dusus_ters_yonde_mi():
    return GERCEK_DUSUS_FARKI > 0 and TAM_KARISTIRMA_FARKI > 0


def blok_fark_gormuyor_mu(esik=0.5):
    return all(abs(x) < esik for x in BLOK_FARKI)


def buyutme_yirmi_kattan_fazla_mi():
    return BUYUTME > 20.0


def madde331_duzeltildi_mi():
    return abs(KAYITLI_NET - BEKLENEN_NET - 1.93) < 0.1


def kapsam_durust_mu():
    return YENIDEN_YAZILDI_MI is False and "YASA" in KAPSAM_NOTU


def madde288_iki_kolda_da_ayni_mi():
    return (MADDE288["sartlar"] == MADDE288_IKINCI["sartlar"] == "RYYY"
            and not MADDE288["gecer"] and not MADDE288_IKINCI["gecer"])


def madde288_gec_farki_yeniden_uretilebilir_mi():
    return all(-0.0115 < (A["aday"]["gec"] - A["kontrol"]["gec"]) < -0.0075
               for A in (MADDE288, MADDE288_IKINCI))


def madde288_artefakt_degil_mi():
    return (MADDE288["esit_risk_puan"] > 5.0
            and MADDE288_IKINCI["esit_risk_puan"] > 5.0
            and abs(MADDE288["kaldirac"] - 1.0) < 0.01)


def hukum():
    return {
        "hiza_sinif_sayisi": 2,
        "siniflar_arasi_net": "+15,0 puan",
        "on_kayitli_kural": "IKI YONDE DE RED",
        "esit_riskte": "CIFT 11 puan ONDE (net'in TERSI)",
        "metrik_artefakti": "0,71 puan tam-karistirma farki -> 15 puan net",
        "madde331": "BASLIK DUZELTMESI YANLISTI, duzeltildi (+166,9)",
        "madde288": "iki kolda da RED (25-26 -0,009) ama kazanc GERCEK",
        "ayar_degisti_mi": False,
    }


def yaz():
    print(__doc__)
    print("OLCUM")
    for k, v in sorted(OLCUM.items()):
        print("  ofset %d  %-5s CAGR %+7.2f  dusus %5.2f  doz %.3fx  net %+7.2f"
              % (k, *v))
    print("\nHUKUM")
    for k, v in hukum().items():
        print("  %-20s %s" % (k, v))


if __name__ == "__main__":
    yaz()
