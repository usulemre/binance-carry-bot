#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 278 — "ÇOKLU DİNAMİK ÖĞRENME" ÖLÇÜLDÜ: KÂHİN TAVANI BÜYÜK (+22,5 PUAN)
AMA GEÇMİŞTEN ULAŞILAMAZ. RED — VE YENİ BİR YASA.

Kullanıcı sordu: "çoklu dinamik öğrenme mantığında kâr oluşur mu?" Yani
parametreleri sabitlemek yerine her dönem yeniden seçen bir sistem.
Projenin kendi disiplini uygulandı (madde 214): **önce kâhini koş.**
Mükemmel öngörüyle her dönem en iyi parametreyi seçsen ne kazanırdın?
Tavan küçükse hiçbir öğrenici o aileden para çıkaramaz.

YÖNTEM
------
13 motor koşumu (hepsi kontrolün aynısı, tek parametre değişik,
FAZ_KAY=0 sabit). Kontrol birebir yeniden üretildi: +%112,3 / Sh 3,10 /
dd −%14,5. Beş aile: tutma süresi (REB_GUN 3/4/5/6/7) · long kâr-al
(TPL 0,30/0,40/0,50) · kalabalık havuzu (HAVUZ 2/3/4) · uç hareket
elemesi (UCELE 0,30/0,40/0,50) · fırsat rezervi (REZERV 0,10/0,20/0,30).

Dönem = yarım yıl (**9 dönem**, kasten cömert: ne kadar sık yeniden
seçim, o kadar çok uyarlanma şansı). Üç seri:
  A) KONTROL   : parametre sabit
  B) KÂHİN     : her dönem O DÖNEMDE en iyi olanı seç (ileriye bakış)
  C) GERÇEKÇİ  : her dönem ÖNCEKİ dönemde en iyi olanı seç (öğrenici)

BULGU 1 — KÂHİN TAVANI GERÇEK VE BÜYÜK (eşit riskte)
----------------------------------------------------
    aile        kontrol dd   kâhin dd   kâhin getiri   EŞİT RİSK   kenar
    **tutma**     −14,51      −13,79      +%125,5      **+%134,7**  **+22,50**
    long TP       −14,51      −14,99      +%121,2        +%115,9     +3,69
    havuz         −14,51      −14,43      +%116,5        +%117,4     +5,17
    uç eleme      −14,51      −14,31      +%112,3        +%114,4     +2,21
    rezerv        −14,51      −16,10      +%109,7         +%95,5    −16,72

Tutma süresi ekseninde kâhin **eşit riskte +22,5 puan** — ve düşüşü
İYİLEŞTİRİYOR (−13,79 vs −14,51), yani bu bir doz etkisi değil gerçek
kenar. Madde 223/264 "tutma süresi bir kaldıraç koludur" demişti;
**dönem dönem doğru tutma süresini bilmek kaldıraçtan FAZLASI.**
Çok parametreli kâhin ÜST SINIRI (aile başına fazlaların toplamı,
bağımsızlık varsayar → abartır): kontrol +%112,2 → **+%136,4 (+24,2 puan)**.

BULGU 2 — AMA O SEÇİM GEÇMİŞTEN TAHMİN EDİLEMİYOR
--------------------------------------------------
Üç ayrı test, hepsi aynı cevabı veriyor:

* **Sıralama otokorelasyonu** (dönem t ile t+1 arası Spearman, 40 çift):
  reb −0,200 · tpl +0,000 · havuz +0,062 · uç eleme +0,250 · rezerv
  +0,125 → **toplam +0,048, p = 0,707.** Hangi değerin iyi olduğu bir
  dönemden diğerine TAŞINMIYOR.
* **Argmax isabeti:** önceki dönemin en iyisi = bu dönemin en iyisi
  **13/40 = %32,5**, şans %30,7 → binom p = 0,459.
* **Gerçekçi öğrenici:** 5 ailenin 3'ünde KONTROLDEN KÖTÜ; toplam
  **−4,6 puan** (tpl −4,75 · havuz −4,01 · uç eleme −3,11 · reb +3,48
  · rezerv +3,77).

GÜÇ SINIRI (dürüstlük gereği): 8 geçişle gerçek isabet %50 olsaydı
%78,6, %60 olsaydı %98,0 olasılıkla yakalardım — yani **güçlü bir
tahmin gücü ELENDİ.** Gerçek isabet %40 olsaydı yakalama gücü yalnız
%30,7 → **ılımlı bir tahmin gücü elenemedi.** Söylenen şey "tahmin
imkânsız" değil, "tahmin gücüne dair KANIT YOK ve güçlü olanı yok".

BULGU 3 — MADDE 231 BUNU ZATEN SÖYLEMİŞTİ
-----------------------------------------
Madde 231 primdeki değişimin **TREND değil REJİM** olduğunu ölçmüştü
(2022Q3-2024Q4 ort −%0,493/gün vs 2025Q1+ −%1,855, 3,8 kat,
Mann-Whitney p=0,0005; model kıyası SEVİYE atlamasını seçiyor — artık
kareler 4,027 trend vs **2,115 seviye**). **Seviye atlaması, tanımı
gereği olduktan SONRA bilinir.** Uyarlanabilir bir öğrenici bu yüzden
yapısal olarak **her zaman bir rejim geride** olur. Bu madde o bulgunun
parametre düzeyinde bağımsız doğrulanması.

TASARIMIMIN SINIRI (kendi hatam sayılmaz ama kaydedilmeli)
----------------------------------------------------------
Kâhin her dönem **o dönemin Sharpe'ına** göre seçiyor, rapor edilen
ölçüt ise YILLIK GETİRİ. Bu iki amaç aynı değil ve rezerv satırı bunu
kanıtlıyor: "mükemmel öngörü" eşit riskte **−16,72 puan** KAYBEDİYOR.
Bu rezerv hakkında bir bulgu DEĞİL, açgözlü dönem-bazlı seçimin
birleştirilmiş sonucu maksimize etmediğinin kanıtı. Doğru okuma: kâhin
tavanı aileye göre +22,5 ile −16,7 arasında salınıyor ve en yüksek
satır (tutma) tavanın kendisidir.

HÜKÜM
-----
**RED — ama "para yok" diye değil, "para var ve geçmişten ulaşılamıyor"
diye.** Tutma süresi ekseninde dönem dönem doğru seçim eşit riskte
+22,5 puan ediyor; o seçimi önceden bilmenin hiçbir yolu ölçülemedi
(rho +0,048, p=0,707; isabet %32,5 vs şans %30,7) ve gerçekçi öğrenici
kontrolden −4,6 puan geride. Ayar DEĞİŞMEDİ.

DERS
----
**Bir eksenin KÂHİN tavanı büyük olabilir ve yine ulaşılamaz olabilir;
tavanı ölçmek yetmez, o tavanın TAHMİN EDİLEBİLİRLİĞİ de ölçülmeli.**
Madde 214 "yeni bir eksene girmeden önce kâhini koş" demişti; bu madde
o disipline İKİNCİ adımı ekliyor: kâhin tavanı pozitifse hemen inşaata
başlama — **kâhinin SEÇİMİNİN kalıcılığını ölç.** Tavan +22,5 puan ve
kalıcılık sıfırsa inşa edilecek bir şey yok. Ve bu, modelin kalitesiyle
ilgili değil: aynı sonuç ridge için, gradient boosting için (madde 152:
Sharpe 1,51 / 1,04 vs elle kural 2,10) ve bir sinir ağı için de geçerli.
"""
from __future__ import annotations

KONTROL_PARITE = {"yillik": 112.3, "sharpe": 3.10, "dusus": -14.5}
KOSUM = 13
DONEM_SAYISI = 9
DONEM = "yarim yil"

AILELER = {   # ad -> (deger sayisi, taranan degerler)
    "reb": (5, (3, 4, 5, 6, 7)),
    "tpl": (3, (0.30, 0.40, 0.50)),
    "havuz": (3, (2, 3, 4)),
    "ucele": (3, (0.30, 0.40, 0.50)),
    "rezerv": (3, (0.10, 0.20, 0.30)),
}

# aile -> (kontrol_dd, kahin_dd, kahin_getiri, esit_risk_getiri, kenar_puan)
KAHIN = {
    "reb": (-14.51, -13.79, 125.46, 134.71, 22.50),
    "tpl": (-14.51, -14.99, 121.22, 115.90, 3.69),
    "havuz": (-14.51, -14.43, 116.51, 117.38, 5.17),
    "ucele": (-14.51, -14.31, 112.33, 114.42, 2.21),
    "rezerv": (-14.51, -16.10, 109.73, 95.49, -16.72),
}
KONTROL_GETIRI = 112.21
COKLU_UST_SINIR = 136.41          # OLCUM DEGIL: fazlalarin toplami
COKLU_UST_SINIR_PUAN = 24.2

# aile -> gercekci ogrenicinin kontrole gore puani
GERCEKCI = {"reb": 3.48, "tpl": -4.75, "havuz": -4.01,
            "ucele": -3.11, "rezerv": 3.77}
GERCEKCI_TOPLAM = -4.6

# tahmin edilebilirlik
RHO = {"reb": -0.200, "tpl": 0.000, "havuz": 0.062,
       "ucele": 0.250, "rezerv": 0.125}
RHO_TOPLAM = 0.048
RHO_P = 0.707
ISABET = (13, 40)
ISABET_SANS_PCT = 30.7
ISABET_P = 0.459
GUC = {0.40: 30.7, 0.50: 78.6, 0.60: 98.0, 0.75: 100.0}

MADDE_231 = {"dusuk_rejim": -0.493, "yuksek_rejim": -1.855, "kat": 3.8,
             "mann_whitney_p": 0.0005,
             "artik_trend": 4.027, "artik_seviye": 2.115}
MADDE_152 = {"ridge": 1.51, "gbm": 1.04, "elle_kural": 2.10}

TASARIM_SINIRI = (
    "kahin her donem o donemin SHARPE'ina gore seciyor, rapor edilen "
    "olcut YILLIK GETIRI; iki amac ayni degil. Rezerv satirinin esit "
    "riskte -16,72 puan KAYBETMESI bunun kaniti - rezerv hakkinda bir "
    "bulgu DEGIL, acgozlu donem-bazli secimin birlestirilmis sonucu "
    "maksimize etmediginin kaniti."
)


def kahin_tavani_buyuk_mu(esik: float = 10.0) -> bool:
    """En yuksek aile tavani anlamli mi?"""
    return max(v[4] for v in KAHIN.values()) > esik


def en_yuksek_tavan() -> tuple:
    ad = max(KAHIN, key=lambda a: KAHIN[a][4])
    return ad, KAHIN[ad][4]


def tavan_doz_mu(aile: str = "reb") -> bool:
    """Kahin kazanci DOZ etkisi mi? (dusus kotuleserek mi geliyor)"""
    kdd, hdd = KAHIN[aile][0], KAHIN[aile][1]
    return abs(hdd) > abs(kdd)


def tahmin_edilebilir_mi(p_esik: float = 0.05) -> bool:
    """Donem optimumu gecmisten tahmin edilebiliyor mu?"""
    return RHO_P < p_esik or ISABET_P < p_esik


def guclu_tahmin_elendi_mi(guc_esik: float = 75.0) -> bool:
    """Guclu bir tahmin gucu (>=%50 isabet) yakalanabilir miydi?"""
    return GUC[0.50] >= guc_esik


def ilimli_tahmin_elendi_mi(guc_esik: float = 75.0) -> bool:
    """Ilimli bir tahmin gucu (%40 isabet) elendi mi? (HAYIR beklenir)"""
    return GUC[0.40] >= guc_esik


def ogrenici_kaybediyor_mu() -> bool:
    return GERCEKCI_TOPLAM < 0


def kac_ailede_kaybediyor() -> int:
    return sum(1 for v in GERCEKCI.values() if v < 0)


def rejim_mi_trend_mi() -> str:
    """Madde 231'in model kiyasi hangisini seciyor?"""
    return ("seviye" if MADDE_231["artik_seviye"] < MADDE_231["artik_trend"]
            else "trend")


def ogrenici_yapisal_olarak_geride_mi() -> bool:
    """Degisim SEVIYE atlamasiysa ogrenici bir rejim geride kalir."""
    return rejim_mi_trend_mi() == "seviye"


def hukum() -> str:
    ad, puan = en_yuksek_tavan()
    return ("RED - ama 'para yok' diye degil, 'para VAR ve gecmisten "
            "ULASILAMIYOR' diye. En yuksek kahin tavani %s ekseninde "
            "esit riskte +%.2f puan (dusus de IYILESIYOR, yani doz degil "
            "kenar); ama o secimin kaliciligi olculemedi (rho %+.3f "
            "p=%.3f; isabet %d/%d = %%%.1f vs sans %%%.1f) ve gercekci "
            "ogrenici kontrolden %.1f puan geride, 5 ailenin %d'inde "
            "kaybediyor. Ayar DEGISMEDI."
            % (ad, puan, RHO_TOPLAM, RHO_P, ISABET[0], ISABET[1],
               ISABET[0] / ISABET[1] * 100, ISABET_SANS_PCT,
               GERCEKCI_TOPLAM, kac_ailede_kaybediyor()))


def yaz() -> None:
    print("MADDE 278 — ÇOKLU DİNAMİK ÖĞRENME ÖLÇÜLDÜ\n")
    print("YÖNTEM: %d motor koşumu, %d aile, dönem = %s (%d dönem)"
          % (KOSUM, len(AILELER), DONEM, DONEM_SAYISI))
    print("  kontrol paritesi: +%%%.1f / Sh %.2f / dd %.1f"
          % (KONTROL_PARITE["yillik"], KONTROL_PARITE["sharpe"],
             KONTROL_PARITE["dusus"]))
    print("\nKÂHİN (mükemmel öngörü, EŞİT RİSK):")
    print("  aile     | kontrol dd | kâhin dd | kâhin getiri | eşit risk | KENAR")
    for a in KAHIN:
        kdd, hdd, hg, er, kn = KAHIN[a]
        print("  %-8s | %10.2f | %8.2f | %+12.1f | %+9.1f | %+6.2f"
              % (a, kdd, hdd, hg, er, kn))
    ad, puan = en_yuksek_tavan()
    print("  -> en yüksek tavan: %s, +%.2f puan | doz etkisi mi: %s"
          % (ad, puan, tavan_doz_mu(ad)))
    print("  -> ÇOKLU kâhin ÜST SINIRI (ölçüm DEĞİL): +%%%.1f -> +%%%.1f (+%.1f puan)"
          % (KONTROL_GETIRI, COKLU_UST_SINIR, COKLU_UST_SINIR_PUAN))
    print("\nTAHMİN EDİLEBİLİRLİK (üç test):")
    print("  sıralama otokorelasyonu: " + " · ".join(
        "%s %+.3f" % (a, r) for a, r in RHO.items()))
    print("    toplam %+.3f, p = %.3f" % (RHO_TOPLAM, RHO_P))
    print("  argmax isabeti: %d/%d = %%%.1f | şans %%%.1f | p = %.3f"
          % (ISABET[0], ISABET[1], ISABET[0] / ISABET[1] * 100,
             ISABET_SANS_PCT, ISABET_P))
    print("  -> tahmin edilebilir mi: %s" % tahmin_edilebilir_mi())
    print("  GÜÇ: " + " · ".join("gerçek %%%.0f -> güç %%%.1f" % (k * 100, v)
                                 for k, v in GUC.items()))
    print("    güçlü tahmin ELENDİ mi: %s | ılımlı tahmin elendi mi: %s"
          % (guclu_tahmin_elendi_mi(), ilimli_tahmin_elendi_mi()))
    print("\nGERÇEKÇİ ÖĞRENİCİ (önceki dönemin en iyisi):")
    for a, v in GERCEKCI.items():
        print("  %-8s %+6.2f puan" % (a, v))
    print("  TOPLAM %+.1f puan | %d/%d ailede KONTROLDEN KÖTÜ"
          % (GERCEKCI_TOPLAM, kac_ailede_kaybediyor(), len(GERCEKCI)))
    print("\nMADDE 231 İLE BAĞ: değişim %s atlaması (artık kareler trend "
          "%.3f vs seviye %.3f)" % (rejim_mi_trend_mi(),
                                    MADDE_231["artik_trend"],
                                    MADDE_231["artik_seviye"]))
    print("  -> öğrenici yapısal olarak BİR REJİM GERİDE mi: %s"
          % ogrenici_yapisal_olarak_geride_mi())
    print("\nTASARIMIMIN SINIRI: %s" % TASARIM_SINIRI)
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
