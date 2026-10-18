#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 330 — **CANLI ÖLÇÜM KATMANININ TAMAMI 15x5 TAM EVREN İÇİN
KALİBREYDİ.** Madde 329 devre kesicide tek bir anahtarı düzeltti; aynı
gözle canlıda karar verdiren **bütün** ölçülmüş sabitler tarandı ve
hepsinin **15 faz × 5 bacak, TAM evren** kitabına ait olduğu görüldü —
oysa 2.000 $'da bot **15x4 / D8** koşar.

*** BU DOSYA 2026-10-19'DA TRANSKRİPTTEN YENİDEN YAZILDI (madde 335).
Özgün hâli konteyner kaybında gitti. ***

İki ayak **ölçüldü** (hipotezimin biri **yanlış** çıktı):

  AYAK 1 — L1 FUNDING KAPISI: **GÜVENLİ** (hipotezim yanlıştı).
  AYAK 2 — SAPMA REFERANSI: **YANLIŞ KİTAP**, kuyrukta yanlış alarm
           ~İKİ KAT. Düzeltildi.

═══ 0. DENETİM KAPSAMI ═══

  sabit / dosya                       olculdugu kitap   canli rolu
  BEKLENEN_FUNDING_TABAN 0,000653     15x5 TAM (m.232)  L1 DURDUR (%100 guc)
  BEKLENEN_FUNDING_GUNLUK 0,001055    15x5 TAM          rejim gostergesi
  BEKLENEN_FUNDING_YUKSEK 0,001648    15x5 TAM          rejim gostergesi
  BEKLENEN_TP_LONG/SHORT 0,088/0,181  m.214             L2/L3 INCELE
  referans_getiri.csv (1.504 gun)     15x5 TAM          SAPMA DURDUR/INCELE
  DUSUS_ZARFI (m.260)                 15x5 TAM          L4 (m.329'da isaretlendi)
  KITAP_ESIK                          -> MADDE 329'DA DUZELTILDI

`referans_getiri.csv`'nin hangi kitap olduğu **kanıtla** saptandı: tam
dönem düşüşü **−%14,54**, yani `KITAP_DUSUS["15x5"]` ile **birebir**.

═══ 1. RAY PARİTESİ (önce bu) ═══

    ARM A (15x5 TAM): +112,28%  dd −14,51
    madde 320 PARITE: +112,27%  dd −14,54      -> GECTI

Motorun bastığı `dd` **bar seviyesindedir** (`carry_denetim.ozet`);
`KITAP_DUSUS` ise **günlük** seride ölçülmüş. İki yakınsadığı için
15x5'te ayrım görünmüyordu.

D8 kolum ise madde 320'nin **+119,71 / 19,91**'ini vermedi (+117,72 /
20,07). Sebep **başlangıç hizası** — üç ofset koşuldu:

    FAZ_KAY   CAGR     dusus
       0     +117,72   20,07
       1     +121,80   21,70
       2     +117,60   20,10
    yayilim  4,20 puan  1,63 puan

Kayıtlı **+119,71 bu aralığın İÇİNDE**; kayıtlı düşüş 19,91 ise en sığ
ölçümümden **0,16 puan daha sığ**. Madde 323'ün yasası gereği hizasız
bir kitap **tek hizanın** dağılımıyla yargılanır — yeni referans serisi
bu yüzden **tek ofsete (FAZ_KAY=0)** aittir.

**MADDE 329'A RAFİNERİ:** 329'un payı tek ofsetin düşüşüne (19,91)
göre **+3,09** idi; **en kötü ofsetle (21,70) pay +1,30** — hâlâ
pozitif, çift **ayakta**, ama pay sanıldığından incedir.

═══ 2. AYAK 1 — L1 FUNDING KAPISI: GÜVENLİ (hipotezim YANLIŞTI) ═══

Beklentim: daralmış evren daha az funding toplar, L1 sağlıklı botu
DURDURUR. **Ters çıktı.** Motorun `FON_OLC` koluyla, aynı ortamda:

    kitap            harman      dusuk prim(<2025)  yuksek prim(>=2025)
    15x5 TAM       0,001068         0,000676            0,001644
    **15x4 D8**    **0,001208**     **0,000762**        **0,001863**
    KAYITLI (m.232) 0,001055         0,000653            0,001648

Arm A, madde 232'nin üç sabitini **%0,2-3,5 içinde** yeniden üretti
(ray doğrulandı). Koşan kitap funding'i **%13 DAHA ÇOK** topluyor.

    L1 ORANI (saglikli KOSULAN kitap, kayitli tabana gore):
      dusuk prim rejimi   0,000762 / 0,000653 = **1,17**  TEMIZ
      harman              0,001208 / 0,000653 = 1,85      TEMIZ
      yuksek prim         0,001863 / 0,000653 = 2,85      TEMIZ

⇒ En kötü rejimde bile oran **1,17 > 0,80**: L1 yanlış alarm vermez.
**AYAR DEĞİŞMEZ.**

**MEKANİZMA:** elenen sekiz sembol (BTC, ETH, LINK, LTC, BCH, ETC,
AAVE, QNT) **büyük kapitalli ve DÜŞÜK funding'li** majorlardır; evreni
daraltmak funding/sermaye ortalamasını **yükseltir**.

**KÂR NOTU (madde 214 ile uyumlu):** daralmış kitap daha çok funding
topluyor ama net kazancı daha düşük ⇒ **evren kanalının +16,67'si bir
FUNDING kanalı değil** — düşüş/doz kanalıdır. Kâr çıkıştan gelir.

═══ 3. AYAK 2 — SAPMA REFERANSI: YANLIŞ KİTAP (ÖLÇÜLDÜ) ═══

    seri                   gunluk ort   std      yillik    dusus
    referans_getiri.csv      0,00216   0,01405  +112,46%  −14,54
    15x5 TAM (benim)         0,00216   0,01425  +112,17%  −14,27
    **KOSULAN 15x4 D8**      0,00226   0,01608  +117,60%  −19,07

**MERKEZDE SORUN YOK** (ikinci hipotezim de yanlıştı): sağlıklı koşan
kitabın medyanı 15x5 dağılımında **%49,5-55,3** yüzdeliğe düşüyor —
bütün ufuklarda NORMAL. Çünkü koşan kitap günlük olarak **daha çok**
kazanıyor.

**SORUN KUYRUKTA.** std'si %14 daha yüksek; sağlıklı bir kitap yanlış
dağılımda tasarlanandan **daha sık** alarm verir (B=20.000):

    ufuk   INCELE hedef  GERCEK   |  DURDUR hedef  GERCEK
     14        %5,0       %7,2    |     %1,0        %1,7
     30        %5,0       %6,9    |     %1,0        **%2,0**
     60        %5,0       %6,6    |     %1,0        %2,1
     90        %5,0       %7,0    |     %1,0        **%2,2**
    180        %5,0       %6,5    |     %1,0        %1,9
    365        %5,0       %6,4    |     %1,0        %1,8

    DOGRU referansla: 30g %5,0/%1,0 · 90g %5,1/%1,0 · 365g %4,4/%0,9

⇒ **DURDUR yanlış alarmı tasarlananın ~İKİ KATI.** Projenin kendi
aracıyla okunan bant (30 gün): yanlış referans p1 **−%9,25** / p5
−%5,22; doğru referans p1 **−%11,37** / p5 −%6,85 — DURDUR bandı
**2,12 puan fazla dardı.**

**KARŞI-OLGU, GERÇEK DİLİMLERLE (bootstrap değil).** Koşan kitabın
**200 gerçek 30-günlük dilimi** iki referansla değerlendirildi:

    referans            CIDDI SAPMA (DURDUR)   BEKLENENIN ALTINDA
    YANLIS (15x5)              **3**                  5
    DOGRU  (15x4)              **0**                  6

Dilimler örtüşüyor ve referans dilimin kendisini içeriyor — bağımsız
deney değil, ama gerçek veri. Kitabın **gerçek en kötü 30 günü**
(2024-02-04, **−%15,30**) her iki referansla da CİDDİ SAPMA veriyor:
düzeltme kapıyı **körleştirmiyor**, yalnız yanlış alarmı kaldırıyor.

═══ 4. DÜZELTME ═══

  referans_getiri_15x4.csv            YENI (1.504 gun, tek ofset)
  carry_sapma.KITAP_REFERANS          kitap -> dosya tablosu
  carry_sapma.referans_dosyasi(bak)   (yol, kitap, uyari) dondurur
  carry_sapma.referans_oku(.., bak)   KOSAN kitabin serisini okur
  carry_sapma --bakiye                yoksa carry_equity.csv'nin ILK bakiyesi
  dusme halinde UYARI basilir         sessiz yanlis dagilim YOK

`referans_getiri.csv` **silinmedi ve değiştirilmedi**: o, madde 262'nin
"bu tablonun tek kaynağı" dosyasıdır.

═══ 5. AÇIK EKSENLER (dürüst) ═══

A) **`CANLIYA_CIKIS.md`'nin beklenti tablosu da 15x5'tir** — madde
   331'de ele alındı.
B) **L2/L3 (TP oranları 0,088 / 0,181) bu maddede ÖLÇÜLMEDİ.**
C) **`DUSUS_ZARFI` (madde 260) hâlâ 15x5'tir.**
D) Yeni seri **2.000 $ / D8**'e aittir.

AYAR DEĞİŞTİ: sapma kapısının referansı koşan kitaba bağlandı. L1
funding kapısı **ölçüldü ve dokunulmadı**.
"""

from __future__ import annotations

YENIDEN_YAZILDI = True

# ───────────────────────── 0. DENETİM KAPSAMI
SINIF = ("madde 322 -> 328 -> 329 ile ayni sinif: arkasinda uretim "
         "olmayan ya da BASKA BIR KITABA ait kayitli sayi")
CANLI_SABITLER = {
    "BEKLENEN_FUNDING_TABAN": ("15x5 TAM", "L1 DURDUR (%100 guc)", "OLCULDU: guvenli"),
    "BEKLENEN_FUNDING_GUNLUK": ("15x5 TAM", "rejim gostergesi", "OLCULDU: guvenli"),
    "BEKLENEN_FUNDING_YUKSEK": ("15x5 TAM", "rejim gostergesi", "OLCULDU: guvenli"),
    "BEKLENEN_TP_LONG/SHORT": ("madde 214", "L2/L3 INCELE", "OLCULMEDI - acik eksen B"),
    "referans_getiri.csv": ("15x5 TAM", "SAPMA DURDUR/INCELE", "YANLIS - DUZELTILDI"),
    "DUSUS_ZARFI": ("15x5 TAM", "L4 olasilik", "acik eksen C"),
    "KITAP_ESIK": ("15x5", "devre kesici", "MADDE 329'DA DUZELTILDI"),
}
REFERANS_KANITI = ("referans_getiri.csv tam donem dususu -14,54 = "
                   "KITAP_DUSUS['15x5'] ile BIREBIR")

# ───────────────────────── 1. RAY PARİTESİ
PARITE = {"benim": (112.28, -14.51), "madde_320": (112.27, -14.54)}
DUSUS_SOZLESMESI = ("motorun bastigi dd BAR seviyesi (carry_denetim.ozet); "
                    "KITAP_DUSUS ise GUNLUK seride olculmus - 15x5'te "
                    "ikisi yakinsadigi icin ayrim gorunmuyordu")
OFSET = {0: (117.72, 20.07), 1: (121.80, 21.70), 2: (117.60, 20.10)}
OFSET_YAYILIM = (4.20, 1.63)
MADDE320_D8 = (119.71, 19.91)
PAY_TEK_OFSET = 23.0 - 19.91       # +3.09
PAY_EN_KOTU_OFSET = 23.0 - 21.70   # +1.30
TEK_HIZA_MI = True

# ───────────────────────── 2. AYAK 1: L1
FUNDING = {   # kitap -> (harman, dusuk prim, yuksek prim) gun/sermaye
    "15x5 TAM": (0.001068, 0.000676, 0.001644),
    "15x4 D8":  (0.001208, 0.000762, 0.001863),
    "KAYITLI":  (0.001055, 0.000653, 0.001648),
}
L1_ORAN = {"dusuk prim": 1.17, "harman": 1.85, "yuksek prim": 2.85}
L1_ESIK = {"DURDUR": 0.50, "INCELE": 0.80}
L1_HUKUM = "AYAR DEGISMEZ"
HIPOTEZIM_YANLISTI = True
MEKANIZMA = ("elenen sekiz sembol (BTC, ETH, LINK, LTC, BCH, ETC, AAVE, "
             "QNT) buyuk kapitalli ve DUSUK funding'li majorlardir; "
             "evreni daraltmak funding/sermaye ortalamasini YUKSELTIR")
KAR_NOTU = ("daralmis kitap daha COK funding topluyor ama neti DAHA "
            "DUSUK => evren kanalinin +16,67'si bir FUNDING kanali "
            "DEGIL, dusus/doz kanalidir (madde 214)")

# ───────────────────────── 3. AYAK 2: SAPMA
SERILER = {   # ad -> (gunluk ort, std, yillik %, gunluk dusus %)
    "referans_getiri.csv": (0.00216, 0.01405, 112.46, -14.54),
    "15x5 TAM (benim)":    (0.00216, 0.01425, 112.17, -14.27),
    "KOSULAN 15x4 D8":     (0.00226, 0.01608, 117.60, -19.07),
}
MERKEZ_YUZDELIK = {14: 51.0, 30: 49.5, 60: 51.2, 90: 53.0, 180: 53.2, 365: 55.3}
YANLIS_ALARM = {   # ufuk -> (INCELE gercek %, DURDUR gercek %)
    14: (7.2, 1.7), 30: (6.9, 2.0), 60: (6.6, 2.1),
    90: (7.0, 2.2), 180: (6.5, 1.9), 365: (6.4, 1.8),
}
HEDEF_ALARM = (5.0, 1.0)
DOGRU_REFERANSLA = {30: (5.0, 1.0), 90: (5.1, 1.0), 365: (4.4, 0.9)}
BANT_30G = {"yanlis": (-9.25, -5.22), "dogru": (-11.37, -6.85)}
BANT_FARKI_PUAN = 11.37 - 9.25      # 2.12
KARSI_OLGU = {"yanlis 15x5": (3, 5), "dogru 15x4": (0, 6)}
KARSI_OLGU_N = 200
KARSI_OLGU_UYARISI = ("dilimler ORTUSUYOR ve referans dilimin kendisini "
                      "iceriyor - bagimsiz deney DEGIL, ama GERCEK veri")
EN_KOTU_30G = (-15.30, "2024-02-04")
KORLESTIRMEDI_MI = True
BENZER_MADDELER = ("madde 177 (surekli oten alarm tek guclu kontrolu "
                   "ise yaramaz kilar) ve madde 234 (saglikli kitabi "
                   "kapatma) - ayni ariza, bu kez sapma kapisinda")

# ───────────────────────── 4. DÜZELTME
DUZELTME = {
    "referans_getiri_15x4.csv": "YENI (1.504 gun, 15x4/D8, dusus -19,07)",
    "carry_sapma.KITAP_REFERANS": "kitap -> dosya tablosu",
    "carry_sapma.referans_dosyasi": "(yol, kitap, uyari)",
    "carry_sapma.referans_oku(bakiye=)": "KOSAN kitabin serisi",
    "carry_sapma --bakiye": "yoksa carry_equity.csv'nin ILK bakiyesi",
}
ESKI_DOSYA_KORUNDU = True
DUSME_UYARISI_VAR_MI = True

# ───────────────────────── 5. AÇIK EKSENLER
ACIK_EKSENLER = {
    "A": "CANLIYA_CIKIS.md beklenti tablosu da 15x5'tir - madde 331",
    "B": "L2/L3 TP oranlari (0,088/0,181) bu maddede OLCULMEDI",
    "C": "DUSUS_ZARFI (madde 260) hala 15x5",
    "D": "yeni seri 2.000 $/D8'e aittir - her kademe kendi serisini ister",
}
AYAR_DEGISTI = True
NE_DEGISTI = "sapma kapisinin referansi KOSAN kitaba baglandi"
NE_DEGISMEDI = "L1 funding kapisi OLCULDU ve DOKUNULMADI"

YASA1 = ("Canli bir kapinin esigi degil, KARSILASTIRMA DAGILIMI da "
         "kitaba baglidir: ayni esik, yanlis dagilimla tasarlananin IKI "
         "KATI yanlis alarm uretir.")
YASA2 = ("Bir referans serisinin hangi kitaba ait oldugu TAHMIN "
         "EDILMEZ, KIMLIKLE saptanir: tam donem dususu hangi "
         "KITAP_DUSUS girdisiyle birebir tutuyorsa o kitaptir.")
YASA3 = ("Yanlis kalibrasyonun YONU olculmeden bilinmez: iki hipotezim "
         "de (L1 az toplar; sapma merkezde duser) YANLIS cikti, gercek "
         "ariza yalnizca KUYRUKTAYDI.")
YASA4 = ("Bir motor sayisini kayitli bir sayiyla kiyaslamadan once "
         "DUSUS SOZLESMESI kontrol edilir: bar seviyesi mi, gunluk mu.")


# ───────────────────────── DOĞRULAMA
def ray_paritesi_gecti_mi():
    a, b = PARITE["benim"], PARITE["madde_320"]
    return abs(a[0] - b[0]) < 0.05 and abs(a[1] - b[1]) < 0.05


def arm_a_madde232yi_uretti_mi(tol=0.04):
    k, a = FUNDING["KAYITLI"], FUNDING["15x5 TAM"]
    return all(abs(x - y) / y < tol for x, y in zip(a, k))


def kosan_kitap_daha_cok_mu_topluyor():
    return FUNDING["15x4 D8"][0] > FUNDING["15x5 TAM"][0]


def l1_guvenli_mi():
    return min(L1_ORAN.values()) > L1_ESIK["INCELE"]


def l1_ayari_degismedi_mi():
    return L1_HUKUM == "AYAR DEGISMEZ"


def merkezde_sorun_var_mi():
    return not all(5.0 <= y <= 95.0 for y in MERKEZ_YUZDELIK.values())


def durdur_yanlis_alarmi_iki_kat_mi():
    return min(d for _, d in YANLIS_ALARM.values()) >= 1.5 * HEDEF_ALARM[1]


def incele_yanlis_alarmi_yuksek_mi():
    return all(i > HEDEF_ALARM[0] for i, _ in YANLIS_ALARM.values())


def dogru_referans_hedefi_tutuyor_mu(tol=0.6):
    return all(abs(i - HEDEF_ALARM[0]) < tol and abs(d - HEDEF_ALARM[1]) < 0.2
               for i, d in DOGRU_REFERANSLA.values())


def bant_dar_miydi():
    return BANT_FARKI_PUAN > 2.0


def karsi_olgu_yanlis_durdur_verdi_mi():
    return KARSI_OLGU["yanlis 15x5"][0] > 0 and KARSI_OLGU["dogru 15x4"][0] == 0


def kapi_korlesmedi_mi():
    return KORLESTIRMEDI_MI and EN_KOTU_30G[0] < -15.0


def madde320_ofset_araliginda_mi():
    c = [x[0] for x in OFSET.values()]
    return min(c) <= MADDE320_D8[0] <= max(c)


def pay_en_kotu_ofsette_hala_pozitif_mi():
    return 0 < PAY_EN_KOTU_OFSET < PAY_TEK_OFSET


def eski_dosya_korundu_mu():
    return ESKI_DOSYA_KORUNDU is True


def hipotezlerim_yanlis_mi_cikti():
    return HIPOTEZIM_YANLISTI and not merkezde_sorun_var_mi()


def hukum():
    return {
        "ayak1_L1": "GUVENLI (oran 1,17 en kotu rejimde) - AYAR DEGISMEZ",
        "ayak2_sapma": "YANLIS KITAP - DUZELTILDI",
        "durdur_yanlis_alarm": "%1,7-2,2 (hedef %1,0)",
        "incele_yanlis_alarm": "%6,4-7,2 (hedef %5,0)",
        "dogru_referansla": "%5,0 / %1,0",
        "karsi_olgu": "200 gercek dilimde 3 yanlis DURDUR -> 0",
        "hipotezlerim": "IKISI DE YANLIS cikti",
        "ayar_degisti_mi": True,
    }


def yaz():
    print(__doc__)
    print("CANLI SABITLERIN KITABI")
    for k, (kit, rol, son) in CANLI_SABITLER.items():
        print("  %-26s %-10s %-24s %s" % (k, kit, rol, son))
    print("\nHUKUM")
    for k, v in hukum().items():
        print("  %-22s %s" % (k, v))


if __name__ == "__main__":
    yaz()
