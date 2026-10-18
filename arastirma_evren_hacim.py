#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 297 — "BAŞKA COİNLER BUL": HACİM EŞİĞİ İKİ YÖNDE DE EN İYİ.
SABİT BACAK SAYISINDA EVRENİ GENİŞLETMEK SİNYAL EKLEMEZ, SLOT DAĞITIR.

Soru kullanıcıdan geldi ve somuttu: *"Başka coinler bul o zaman mesela
ususdtden shortta çok kazandım bu gün"* (12 Ekim 2026).

═══ 1. USUSDT KİTABIN EVRENİNDE Mİ? ═══

Evet, panelde VAR; eleyen şart HACİM:

    USUSDT: listeleme 2025-12-12, PERPETUAL, TRADING
            1.576 fiyat gözlemi, bunun yalnız **21'i uygun** (%1,3)
            medyan günlük hacim **4,2 M$**, eşik **100 M$** (24 kat altı)
            funding ortalama **+%31,5/yıl** (BTC +%6,6 — 5 katı)

Yani sinyal onu istiyor, filtre atıyor. Eşik düşürülürse kaç bar
uygun olur: 5e7 -> 87, 2e7 -> 223, 1e7 -> 359, 5e6 -> 528.

BİRİM DÜZELTMESİ (bu turda bulundu): `carry_denetim.py`'nin `SINYAL`
docstring'i "yıllıklaştırılmış oran" diyor ama kod `* (24/ARALIK)` ile
**GÜNLÜK** orana çeviriyor. Strateji için fark etmez (monoton dönüşüm),
RAPOR için eder: ilk hesabımda USUSDT'nin funding'ini %0,09 diye
yazacaktım, gerçek %31,5/yıl. Docstring madde 297'de düzeltildi.

═══ 2. ÖNCE ÖDÜL ÖLÇÜLDÜ (madde 296'nın yasası) ═══

`HACIM_ESIK` motorda zaten dışarı veriliyordu (madde 228). Eşik HER İKİ
YÖNDE tarandı, iki faz, madde 287'nin kanon doz ölçümü:

    esik      CAGR     Sh22    Sh25   dusus    doz      net    P(>0)
    1e7     + 83,05   2,952   1,616   20,55  1,104x   + 93,05   10,9%
    2e7     + 95,50   2,904   2,111   21,32  1,222x   +123,40   25,6%
    5e7     +107,48   2,727   2,899   15,88  1,402x   +171,26   43,6%
  **1e8**   +112,27   2,789   3,147   14,54  1,505x  **+200,85**   -
    1,5e8   + 89,00   2,439   2,685   14,53  1,426x   +141,62    0,0%
    2e8     + 74,47   2,527   2,138   18,08  1,403x   +113,36    0,0%
    2,5e8   + 62,13   2,477   1,807   20,68  1,429x   + 94,97    0,0%

    7,5e7   +111,15   2,690   3,192   15,63  1,478x   +193,10   52,4%  <-- en yakın
    1,25e8  + 93,90   2,545   2,704   15,60  1,419x   +149,45    0,0%

Mevcut eşik **tam bir iç optimum**: her iki yönde tek yönlü düşüş.
Dört şart **dokuz adayın dokuzunu** da reddetti. En yakın rakip 7,5e7:
net farkı yalnız −7,75 puan, Sh25 +0,045 İYİLEŞİYOR ama Sh22 −0,099
düşüyor, yani şart 1'den dalıyor.

DÜRÜST NOT: bu eşik madde 133'te zaten taranmıştı. "İki yön de
kaybediyor" bir DOĞRULAMA, keşif değil. Bu turun keşfi MEKANİZMA ve
cezanın büyüklüğü — ve USUSDT'nin kendi hesabı.

ASİMETRİ: yarıya indirmek −29,6 puan, 1,5 katına çıkarmak −59,2 puan.
Optimum 1e8'in hafifçe altında olabilir diye 7,5e7 ve 1,25e8 de koşuldu
(yukarıda). "1e8 en iyi" iddiası bu veri kümesine KOŞULLU — madde
133'ün taraması da aynı veriydi — ama RED yönü dört şart VE P(>0) ile
iki kez teyitli.

═══ 3. BULUNAN VE ELENEN KARIŞIM ═══

`HACIM_ESIK != 1e8` motorda yeniden-hesap dalını tetikliyor ve o dal
AYRICA 150 TRADFI sembolünü uygunluktan siliyor (5.114 hücre). Yani
düşük eşik koşuları kontrolden İKİ yönden ayrılıyordu.

REFERANS KOL kuruldu: `HACIM_ESIK=99999999` (eşiği değiştirmeden dalı
tetikler). Sonuç kontrolle **BİREBİR AYNI** (fark 0,000; CAGR +112,27,
Sh22 2,789, Sh25 3,147, doz 1,505x). Karışım elendi: bütün etki eşiğin
kendisi.

═══ 4. MEKANİZMA: SEYRELTME DEĞİL, SLOT YERİNDEN ETME ═══

Bacak bazında katkı defteri (KATKI=1, iki faz, ~90.000 bacak) kontrol
ile eşik 2e7 arasında karşılaştırıldı. Bacağın AÇILIŞ barındaki hacmine
göre katmanlandı:

    KONTROL (1e8)          bacak  pay%   pnl/bacak   funding    fiyat
    >1e8                   86320  96,0   +11,04 bp   +5,29     +5,75

    ESIK 2e7               bacak  pay%   pnl/bacak   funding    fiyat
    >1e8                   34240  38,1   +19,91 bp   +9,93     +9,98
    5e7-1e8                19564  21,8   + 7,48 bp   +5,31     +2,16
    **2e7-5e7**            33206  36,9   **+ 2,25 bp**  +4,71   **−2,45**
    1e7-2e7                 2880   3,2   − 0,49 bp   +4,24     −4,73
    <1e7                      60   0,1   −21,54 bp   +2,70    −24,24

Kitap ince coinleri GERÇEKTEN seçiyor — bacakların **%40'ı** 50 M$'ın
altına kayıyor. Sebep seyreltme değil (zayıf funding'li sembol seçilmez
zaten); sebep şu: ince coin funding SIRALAMASINI kazanıyor, ama
topladığı carry yarısı kadar (4,71 vs 9,93 bp) ve **fiyat bacağı
NEGATİF** (−2,45 vs +9,98 bp).

Ve asıl maliyet orada bile değil: bacak sayısı SABİT. İnce coine
verilen her slot, +19,91 bp'lik bir bacaktan alınıyor. 2025-26'da fark
uçuyor: >1e8 **+26,07 bp**, 2e7-5e7 **−0,37 bp**.

FAZ ASİMETRİSİ: eşik düşerken Sh22 İYİLEŞİYOR (+0,115, +0,163) ama
Sh25 ÇÖKÜYOR (−1,036, −1,531). İnce coinler 2022-24'te yardım etmiş,
2025-26'da yıkmış. Yalnız eski veride test eden biri bunu KABUL ederdi.

═══ 5. USUSDT'NİN KENDİ HESABI ═══

Eşik 2e7 olsaydı kitap USUSDT'yi gerçekten alırdı — ve **33 bacağın
33'ü de SHORT**. Yani sinyal kullanıcıyla aynı fikirde. Sonuç:

    ortalama **−105,05 bp/bacak**  =  funding **+3,08** + fiyat **−108,13**
    kazanan bacak payı %36, tutulan dönem 2026-05-11 .. 2026-08-05

Neden: funding baştan sona pozitifti (+%26 ile +%44/yıl arası, hiç
dönmedi), yani sinyal HEP short dedi. Fiyat ise

    2026-05-11 -> 2026-08-05:  0,00642 -> 0,05270   **+%721**
    2026-08-01 -> 2026-08-31:  0,04866 -> 0,01675   **−%65,6**

Kitap Mayıs'ta +%43 funding'e short girdi ve 7 katlık bir ralliye
yakalandı. Topladığı carry 3 bp, fiyatta ödediği 108 bp — **35 katı**.

Kullanıcının Ekim'deki shortu ise çöküşten SONRA. Aynı yön, ters
zamanlama. Kullandığı sinyal funding değil, **trend**. Kitapta trend
girdisi yok; bu kazancı taklit edemez. (Açık eksen, madde 297.6.)

═══ 6. İNCE COİNİN GERÇEK İŞLEM MALİYETİ — VE NİÇİN BURADA ÖNEMSİZ ═══

Motorun TEK işlem maliyeti `KOM=0.0002`, HER SEMBOL İÇİN AYNI: hacme
duyarlı kayma yok, spread yok. Yani yukarıdaki ölçüm ince coini BTC
maliyetiyle fiyatlıyor — ADAYIN LEHİNE sapan bir varsayım.

Gerçek spread ölçüldü (Corwin-Schultz, 1dk barlar, 2026-06..08, 41
sembol, `data.binance.vision`):

    >1e8        2,31 bp        1e7-2e7     7,36 bp
    5e7-1e8     3,65 bp        3e6-1e7     4,41 bp  (ALT TAHMİN *)
    2e7-5e7     5,66 bp        USUSDT     11,08 bp

(*) Corwin-Schultz işlemsiz barlarda negatifi sıfıra kırpar; en ince
katmanda bu AŞAĞI sapma yapar — VANRYUSDT %26,8 boş barla 5,43 bp
veriyor. Yorumlanmadı, işaretlendi.

AMA bu maliyet BURADA karara girmiyor, iki sebepten:
  (a) Ödül negatif. Maliyeti sıfır sayarken bile aday reddediliyor;
      maliyet eklemek reddi yalnız güçlendirir.
  (b) `KOM=0,0002` tam olarak Binance **maker** ücreti ve canlı kitap
      GTX post-only giriyor (madde 198). Maker spread'i ÖDEMEZ, kazanır.
      İnce coinin maker için maliyeti spread değil **dolum kalitesi** —
      bu motor onu sembol bazında modellemiyor. Reddi o eksen üzerine
      kurmak yanlış olurdu.

═══ 7. SONUÇ ═══

"Başka coin" eklemek bu kitabı iyileştirmiyor; eşiği hangi yöne
oynatırsanız kaybediyorsunuz. Kullanıcının USUSDT kazancı gerçek ama
BU kitabın mekanizmasıyla yakalanamaz — o bir trend işlemi.

AYAR DEĞİŞMEDİ: `CARRY_MIN_VOLUME=100000000` aynen kalıyor.
"""

import os

# ---------------------------------------------------------------- SABİTLER

SORU = ("Başka coinler bul o zaman mesela ususdtden shortta çok "
        "kazandım bu gün")
SORU_TARIHI = "2026-10-12"

ESIK_SIMDI = 1e8
"""Yürürlükteki hacim eşiği: carry_bot.MIN_DAILY_VOLUME_USD (madde 133)."""

# --- USUSDT'nin evren durumu (panel 2022-01-01 .. 2026-08-31) ---
USUSDT = {
    "listeleme": "2025-12-12",
    "fiyat_gozlem": 1576,
    "uygun_bar": 21,
    "medyan_hacim": 4.22e6,
    "funding_yillik": 31.5,      # ortalama, %/yıl
    "fiyat_tam_donem": -25.2,    # %
}

BTC_FUNDING_YILLIK = 6.6
"""Karşılaştırma: BTCUSDT ortalama funding, %/yıl (aynı panel)."""

USUSDT_UYGUN_BAR = {1e8: 21, 5e7: 87, 2e7: 223, 1e7: 359, 5e6: 528}
"""Eşik düşürülürse USUSDT kaç barda uygun olur (1.576 gözlemin içinden)."""

# --- MADDE 297 BULGUSU: SINYAL PANELI GUNLUK, YILLIK DEGIL ---
SINYAL_BIRIMI = "gunluk"
SINYAL_DOCSTRING_HATASI = (
    "carry_denetim.py SINYAL docstring'i 'yıllıklaştırılmış' diyordu; kod "
    "* (24/ARALIK) ile GÜNLÜK orana çeviriyor. Strateji monoton dönüşüme "
    "duyarsız, RAPOR değil: USUSDT %0,09 yerine %31,5/yıl. Düzeltildi.")

# --- DOZ TARAMASI (madde 287 kanon ölçümü, iki faz ortalaması) ---
KONTROL = {"cagr": 112.27, "sh": 2.939, "sh22": 2.789, "sh25": 3.147,
           "dusus": 14.54, "doz": 1.505, "net": 200.85}

TARAMA = {
    #  esik : (cagr,   sh22,  sh25,  dusus,  doz,   net,    P(>0)%)
    1e7:    (83.05, 2.952, 1.616, 20.55, 1.104,  93.05, 10.9),
    2e7:    (95.50, 2.904, 2.111, 21.32, 1.222, 123.40, 25.6),
    5e7:   (107.48, 2.727, 2.899, 15.88, 1.402, 171.26, 43.6),
    1e8:   (112.27, 2.789, 3.147, 14.54, 1.505, 200.85, None),
    1.5e8:  (89.00, 2.439, 2.685, 14.53, 1.426, 141.62, 0.0),
    2e8:    (74.47, 2.527, 2.138, 18.08, 1.403, 113.36, 0.0),
    2.5e8:  (62.13, 2.477, 1.807, 20.68, 1.429,  94.97, 0.0),
}

INCE_TARAMA = {
    #  esik  : (cagr,   sh22,  sh25,  dusus,  doz,   net,    P(>0)%)
    7.5e7:  (111.15, 2.690, 3.192, 15.63, 1.478, 193.10, 52.4),
    1.25e8: ( 93.90, 2.545, 2.704, 15.60, 1.419, 149.45,  0.0),
}
"""Asimetri (−29,6 vs −59,2 puan) optimumun 1e8 ALTINDA olabileceğini
söyledi; iki ara nokta koşuldu. 7,5e7 EN YAKIN RAKİP: net +193,10
(−7,75), P(>0) %52,4. Sh25 +0,045 İYİLEŞİYOR ama Sh22 −0,099 düşüyor,
yani şart 1'den dalıyor. Dokuz kolun dokuzu da reddedildi."""

EN_YAKIN_RAKIP = 7.5e7
"""net farkı yalnız −7,75 puan. Optimumun 1e8 olduğu bu komşulukta
TEK BİR VERİ KÜMESİNDE ölçüldü; madde 133'ün taraması da aynı veriydi.
Yani "1e8 en iyi" iddiası bu kümeye KOŞULLU - ama red yönü dört şart
VE P(>0) ile iki kez teyitli."""

BAR_P = 80.0
"""Kanıt eşiği: P(>0) >= %80 (proje standardı)."""

# --- BULUNAN KARIŞIM VE REFERANS KOL ---
KARISIM = (
    "HACIM_ESIK != 1e8 motorda yeniden-hesap dalini tetikler ve o dal "
    "AYRICA 150 TRADFI sembolunu uygunluktan siler (5.114 hucre). Dusuk "
    "esik kosulari kontrolden IKI yonden ayriliyordu.")
REFERANS_KOL = "HACIM_ESIK=99999999"
REFERANS_FARK = 0.0
"""Referans kol kontrolle birebir aynı çıktı: bütün etki eşiğin kendisi."""

# --- MEKANİZMA: bacak bazında katkı defteri (KATKI=1, ~90.000 bacak) ---
KATMAN_KONTROL = {
    #  katman  : (bacak, pay%,  pnl_bp, funding_bp, fiyat_bp)
    ">1e8":     (86320, 96.0,  11.04,  5.29,  5.75),
    "5e7-1e8":  ( 3567,  4.0,   9.56,  4.71,  4.85),
}
KATMAN_2E7 = {
    ">1e8":     (34240, 38.1,  19.91,  9.93,  9.98),
    "5e7-1e8":  (19564, 21.8,   7.48,  5.31,  2.16),
    "2e7-5e7":  (33206, 36.9,   2.25,  4.71, -2.45),
    "1e7-2e7":  ( 2880,  3.2,  -0.49,  4.24, -4.73),
    "<1e7":     (   60,  0.1, -21.54,  2.70,-24.24),
}
KATMAN_2E7_FAZ = {
    #  katman  : (22-24 pnl_bp, 25-26 pnl_bp)
    ">1e8":     (16.58, 26.07),
    "5e7-1e8":  ( 5.98,  9.63),
    "2e7-5e7":  ( 4.29, -0.37),
    "1e7-2e7":  (-1.20,  0.07),
    "<1e7":     (-14.70, -22.75),
}

# --- USUSDT'nin bacak bazında hesabı (esik 2e7, iki faz) ---
USUSDT_BACAK = {
    "n": 33, "hepsi_short": True,
    "pnl_bp": -105.05, "funding_bp": 3.08, "fiyat_bp": -108.13,
    "kazanan_pay": 36.0,
    "ilk": "2026-05-11", "son": "2026-08-05",
}
USUSDT_FIYAT_YOLU = {
    "2026-05-11..2026-08-05": +721.0,
    "2026-08-01..2026-08-31": -65.6,
}
USUSDT_FUNDING_AYLIK = {
    "2025-12": 26.1, "2026-01": 25.5, "2026-02": 11.5, "2026-03": 22.5,
    "2026-04": 41.7, "2026-05": 43.1, "2026-06": 27.3, "2026-07": 43.8,
    "2026-08": 38.3,
}
"""%/yıl. Hiç negatife dönmedi: sinyal HEP short dedi."""

# --- GERÇEK SPREAD (Corwin-Schultz, 1dk, 2026-06..08, 41 sembol) ---
SPREAD_BP = {
    ">1e8": 2.31, "5e7-1e8": 3.65, "2e7-5e7": 5.66, "1e7-2e7": 7.36,
    "3e6-1e7": 4.41, "USUSDT": 11.08,
}
SPREAD_ALT_TAHMIN = "3e6-1e7"
SPREAD_SAPMA = (
    "Corwin-Schultz islemsiz barlarda negatifi sifira kirpar; en ince "
    "katmanda AŞAĞI sapar (VANRYUSDT %26,8 bos barla 5,43 bp). "
    "Yorumlanmadi, isaretlendi.")

MOTOR_KOM = 0.0002
"""Motorun TEK işlem maliyeti; her sembol için AYNI. Tam olarak Binance
maker ücreti — ve canlı kitap GTX post-only giriyor (madde 198), yani
spread'i ödemez, kazanır. İnce coinin maker maliyeti spread değil
DOLUM KALİTESİ; bu motor onu sembol bazında modellemiyor."""

MALIYET_KARARA_GIRMEDI = (
    "(a) Odul zaten NEGATIF: maliyet sifir sayilirken bile red. "
    "(b) KOM maker ucretidir, kitap maker girer: spread bir maliyet "
    "degil. Reddi olculmemis bir eksen uzerine kurmak yanlis olurdu.")

AYAR = {"CARRY_MIN_VOLUME": 100000000}
"""DEĞİŞMEDİ."""

ACIK_EKSEN = (
    "Kullanicinin USUSDT kazanci bir TREND islemi: funding Mayis'tan beri "
    "hep short diyordu ve fiyat +%721 yapti; o kazanc Agustos'taki "
    "−%65,6 cokusunden SONRA alindi. Kitapta trend girdisi YOK. Ayri bir "
    "kitap olarak madde 289'un sartnamesine tabi: tek basina Sharpe >= 2,5.")

YASA1 = ("Sabit bacak sayisinda evreni genisletmek sinyal EKLEMEZ, SLOT "
         "dagitir: ince coine verilen her slot +19,91 bp'lik bir bacaktan "
         "alinir ve bu firsat maliyeti HICBIR sembol istatistiginde "
         "gorunmez.")
YASA2 = ("Ince bir coinde yuksek funding bedava carry degil RISKIN "
         "FIYATIDIR: USUSDT 3 bp carry odedi, fiyatta 108 bp aldi.")
YASA3 = ("Ayni yonde kazanmak ayni sinyali kullanmak degildir - yon "
         "cakismasi bir DOGRULAMA DEGIL. Kitap da USUSDT'de short'tu ve "
         "bacak basina −105 bp kaybetti.")

# ---------------------------------------------------------------- HÜKÜM


def esik_ic_optimum_mu() -> bool:
    """1e8 her iki yönde de en yüksek net'i veriyor mu?"""
    en = max(TARAMA.items(), key=lambda kv: kv[1][5])
    return abs(en[0] - ESIK_SIMDI) < 1.0


def tek_yonlu_dusus_mu() -> bool:
    """1e8'den uzaklaştıkça net tek yönlü düşüyor mu (doz-tepki)?"""
    alt = [TARAMA[e][5] for e in sorted(e for e in TARAMA if e <= ESIK_SIMDI)]
    ust = [TARAMA[e][5] for e in sorted(
        (e for e in TARAMA if e >= ESIK_SIMDI), reverse=True)]
    return (all(a < b for a, b in zip(alt, alt[1:]))
            and all(a < b for a, b in zip(ust, ust[1:])))


def gecen_aday_var_mi() -> bool:
    """Kanıt eşiğini (P>=%80) geçen bir eşik adayı var mı?"""
    return any(v[6] is not None and v[6] >= BAR_P
               for v in list(TARAMA.values()) + list(INCE_TARAMA.values()))


def karisim_elendi_mi() -> bool:
    return REFERANS_FARK == 0.0


def ince_coin_slot_payi() -> float:
    """Eşik 2e7'de bacakların yüzde kaçı 50 M$'ın altına kayıyor?"""
    return KATMAN_2E7["2e7-5e7"][1] + KATMAN_2E7["1e7-2e7"][1] \
        + KATMAN_2E7["<1e7"][1]


def firsat_maliyeti_bp() -> float:
    """Bir slotu ince coine vermenin bacak başına maliyeti (bp)."""
    return KATMAN_2E7[">1e8"][2] - KATMAN_2E7["2e7-5e7"][2]


def ince_coin_fiyat_bacagi_negatif_mi() -> bool:
    return all(KATMAN_2E7[k][4] < 0 for k in ("2e7-5e7", "1e7-2e7", "<1e7"))


def faz_asimetrisi_var_mi() -> bool:
    """Eşik düşerken Sh22 iyileşip Sh25 çöküyor mu?"""
    dus = sorted(e for e in TARAMA if e < ESIK_SIMDI)
    return (all(TARAMA[e][1] > KONTROL["sh22"] for e in dus if e <= 2e7)
            and all(TARAMA[e][2] < KONTROL["sh25"] for e in dus))


def ususdt_sinyali_kullaniciyla_ayni_mi() -> bool:
    return USUSDT_BACAK["hepsi_short"] is True


def ususdt_kitapta_kaybetti_mi() -> bool:
    return USUSDT_BACAK["pnl_bp"] < 0


def ususdt_carry_fiyati_karsilamiyor_mu() -> tuple[bool, float]:
    """Fiyatta ödenen, toplanan carry'nin kaç katı?"""
    kat = abs(USUSDT_BACAK["fiyat_bp"]) / USUSDT_BACAK["funding_bp"]
    return kat > 1.0, kat


def spread_hacimle_artiyor_mu() -> bool:
    """Alt tahmin işaretli katman hariç, spread hacim düştükçe artıyor mu?"""
    s = [SPREAD_BP[k] for k in (">1e8", "5e7-1e8", "2e7-5e7", "1e7-2e7")]
    return all(a < b for a, b in zip(s, s[1:]))


def maliyet_karara_girdi_mi() -> bool:
    """Red, ölçülmemiş bir maliyet eksenine DAYANMIYOR."""
    return False


def ince_tarama_sonucu(esik: float, satir: tuple[float, ...]) -> None:
    """7,5e7 / 1,25e8 koşuları bittiğinde doldurulur."""
    INCE_TARAMA[esik] = satir


def ayar_degisti_mi() -> bool:
    return AYAR != {"CARRY_MIN_VOLUME": 100000000}


def acik_eksen_kayitli_mi() -> bool:
    return "TREND" in ACIK_EKSEN and "289" in ACIK_EKSEN


def hukum() -> str:
    if gecen_aday_var_mi():
        return "ACIK: kanit esigini gecen bir esik adayi var."
    return ("RED: hacim esigi IKI YONDE de en iyi (1e8, net +200,85). "
            "Yedi adayin yedisi de dort sarttan dustu; en iyi aday "
            "5e7 P(>0) %43,6. Kullanicinin USUSDT kazanci GERCEK ama "
            "bu kitabin mekanizmasiyla yakalanamaz: kitap da short'tu "
            "ve bacak basina −105 bp kaybetti. Ayar DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("SORU (%s): %s\n" % (SORU_TARIHI, SORU))

    print("1) USUSDT EVRENDE Mİ:")
    print("   listeleme %s | fiyat gozlem %d | **uygun bar %d** (%%%.1f)"
          % (USUSDT["listeleme"], USUSDT["fiyat_gozlem"],
             USUSDT["uygun_bar"],
             100.0 * USUSDT["uygun_bar"] / USUSDT["fiyat_gozlem"]))
    print("   medyan hacim %.3g $ vs esik %.3g $ (%.0f kat alti)"
          % (USUSDT["medyan_hacim"], ESIK_SIMDI,
             ESIK_SIMDI / USUSDT["medyan_hacim"]))
    print("   funding +%%%.1f/yil (BTC +%%%.1f - %.1f kati)"
          % (USUSDT["funding_yillik"], BTC_FUNDING_YILLIK,
             USUSDT["funding_yillik"] / BTC_FUNDING_YILLIK))
    print("   esik dusurulurse uygun bar: %s"
          % ", ".join("%.0e->%d" % (k, v)
                      for k, v in sorted(USUSDT_UYGUN_BAR.items())))
    print("   BIRIM DUZELTMESI: %s" % SINYAL_DOCSTRING_HATASI)

    print("\n2) DOZ TARAMASI (madde 287 kanon, iki faz):")
    print("   %-8s %8s %7s %7s %7s %7s %9s %7s"
          % ("esik", "CAGR", "Sh22", "Sh25", "dusus", "doz", "net", "P(>0)"))
    for e in sorted(TARAMA):
        c, s2, s5, d, k, n, p = TARAMA[e]
        yil = "  <== YURURLUKTE" if abs(e - ESIK_SIMDI) < 1 else ""
        print("   %-8.2e %+8.2f %7.3f %7.3f %7.2f %6.3fx %+9.2f %6s%s"
              % (e, c, s2, s5, d, k, n,
                 "-" if p is None else "%.1f%%" % p, yil))
    print("   ic optimum mu: %s | tek yonlu dusus mu: %s"
          % (esik_ic_optimum_mu(), tek_yonlu_dusus_mu()))
    print("   kanit esigini (>=%%%.0f) gecen aday: %s"
          % (BAR_P, gecen_aday_var_mi()))
    print("   INCE TARAMA (en yakin komsuluk):")
    for e in sorted(INCE_TARAMA):
        c, s2, s5, d, k, n, p_ = INCE_TARAMA[e]
        print("   %-8.2e %+8.2f %7.3f %7.3f %7.2f %6.3fx %+9.2f %5.1f%%%s"
              % (e, c, s2, s5, d, k, n, p_,
                 "  <== EN YAKIN RAKIP" if abs(e - EN_YAKIN_RAKIP) < 1 else ""))
    print("   dokuz kolun kaci gecti: %d"
          % sum(1 for v in list(TARAMA.values()) + list(INCE_TARAMA.values())
                if v[6] is not None and v[6] >= BAR_P))

    print("\n3) BULUNAN KARISIM:")
    print("   %s" % KARISIM)
    print("   referans kol %s -> fark %.3f | karisim elendi mi: %s"
          % (REFERANS_KOL, REFERANS_FARK, karisim_elendi_mi()))

    print("\n4) MEKANIZMA (katki defteri, ~90.000 bacak):")
    print("   %-10s %8s %6s %10s %9s %9s"
          % ("katman", "bacak", "pay%", "pnl/bacak", "funding", "fiyat"))
    print("   -- KONTROL (1e8) --")
    for k, (n, p, pl, f, fi) in KATMAN_KONTROL.items():
        print("   %-10s %8d %6.1f %+9.2f %+9.2f %+9.2f" % (k, n, p, pl, f, fi))
    print("   -- ESIK 2e7 --")
    for k, (n, p, pl, f, fi) in KATMAN_2E7.items():
        print("   %-10s %8d %6.1f %+9.2f %+9.2f %+9.2f" % (k, n, p, pl, f, fi))
    print("   ince coine kayan slot payi: %%%.1f" % ince_coin_slot_payi())
    print("   bir slotun firsat maliyeti: %.2f bp/bacak" % firsat_maliyeti_bp())
    print("   ince coinin fiyat bacagi negatif mi: %s"
          % ince_coin_fiyat_bacagi_negatif_mi())
    print("   -- faz x katman (pnl bp) --")
    for k, (a, b) in KATMAN_2E7_FAZ.items():
        print("   %-10s 22-24 %+7.2f   25-26 %+7.2f" % (k, a, b))
    print("   faz asimetrisi var mi: %s (yalniz eski veride test eden "
          "KABUL ederdi)" % faz_asimetrisi_var_mi())

    print("\n5) USUSDT'NIN KENDI HESABI (esik 2e7):")
    print("   %d bacak, hepsi SHORT mu: %s (sinyal kullaniciyla AYNI FIKIRDE)"
          % (USUSDT_BACAK["n"], ususdt_sinyali_kullaniciyla_ayni_mi()))
    print("   ortalama %+.2f bp/bacak = funding %+.2f + fiyat %+.2f"
          % (USUSDT_BACAK["pnl_bp"], USUSDT_BACAK["funding_bp"],
             USUSDT_BACAK["fiyat_bp"]))
    ok, kat = ususdt_carry_fiyati_karsilamiyor_mu()
    print("   fiyatta odenen, carry'nin %.0f kati (karsilamiyor mu: %s)"
          % (kat, ok))
    print("   funding hic negatife dondu mu: %s (en dusuk +%%%.1f/yil)"
          % (any(v < 0 for v in USUSDT_FUNDING_AYLIK.values()),
             min(USUSDT_FUNDING_AYLIK.values())))
    for ad, v in USUSDT_FIYAT_YOLU.items():
        print("   fiyat %s: %+.1f%%" % (ad, v))
    print("   kitapta kaybetti mi: %s" % ususdt_kitapta_kaybetti_mi())

    print("\n6) GERCEK SPREAD (Corwin-Schultz, 1dk, 41 sembol):")
    for k, v in SPREAD_BP.items():
        print("   %-10s %6.2f bp%s"
              % (k, v, "   (ALT TAHMIN)" if k == SPREAD_ALT_TAHMIN else ""))
    print("   hacimle artiyor mu: %s" % spread_hacimle_artiyor_mu())
    print("   sapma: %s" % SPREAD_SAPMA)
    print("   motor kom %.4f (her sembol AYNI; maker ucreti)" % MOTOR_KOM)
    print("   maliyet karara girdi mi: %s" % maliyet_karara_girdi_mi())
    print("   neden: %s" % MALIYET_KARARA_GIRMEDI)

    print("\n7) AYAR: %s (degisti mi: %s)" % (AYAR, ayar_degisti_mi()))
    print("   ACIK EKSEN: %s" % ACIK_EKSEN)
    print("   kayitli mi: %s" % acik_eksen_kayitli_mi())

    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
