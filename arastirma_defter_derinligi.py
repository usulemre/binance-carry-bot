#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 279 — EMİR DEFTERİ DERİNLİĞİ İLK KEZ SEÇİCİ OLARAK KULLANILDI:
KALABALIK PRİMİ DEFTERDE GÖRÜNÜYOR, AMA AYNI PRİMİN DÖRDÜNCÜ YÜZÜ. RED.

Kullanıcı "alfa bulmaya çalış" dedi. Arşivde seçici olarak hiç
kullanılmamış iki veri kümesi vardı (bookDepth ve aggTrades); aggTrades
15 MB/sembol-gün ile ölçeklenemez, **bookDepth 449 KB** ile ölçeklenir.

NEDEN BU EKSEN: madde 253 kalabalık ölçütünü OI ile değiştirmenin kitabı
+%112,3 → **+%44,0**'a düşürdüğünü ölçtü — yani kalabalık seçimi gerçek
iş yapıyor. Kalabalık bugün funding + akış harmanından ölçülüyor. Emir
defteri derinliği aynı mekanizmanın **doğrudan ve hiç kullanılmamış**
ölçeği: kalabalık bir tarafın çıkış emirleri defterde durur. Madde 169
bookTicker kullanmıştı ama yalnız SPREAD denetimi için (veri 2024-03'te
bitiyor), seçici olarak değil.

ÖN KAYIT (indirmeden önce yazıldı, `m279_indir.py` docstring'inde)
-----------------------------------------------------------------
Özellikler (sembol-gün, ~2.743 anlık görüntü üzerinden ortalama):
`dd1` = (alış−satış) notional @%1 / toplam · `dd5` = aynısı @%5 ·
`egim` = toplam@%5 / toplam@%1 · `seviye` = toplam notional @%1 ·
`dd1_std` = dd1'in gün içi oynaklığı.
**İşaret teorik olarak belirsiz** (kalabalık long'un kâr-al satışları
satış tarafını kalınlaştırır ama stopları alış tarafını zayıflatır) →
**her iki işaret de denendi. ÇOKLUK AÇIKÇA BEYAN EDİLDİ: 5×2 = 10 aday.**
Tarama ölçütü madde 244'ün yasası: IC değil **kitabın gerçekleşen P&L'i**.

VERİ
----
Motorun UYGUN evreni, 2023 (22-24 tarafı) + 2025 (25-26 tarafı) =
33.083 sembol-gün istendi, **32.751'i alındı (%99,0)**; 462 sembol, 724
gün. Ham dosya saklanmadı (madde 253'ün yöntemi). **Kapsama: uygun
hücrelerin %95,0'ı** (2023 %95,1 · 2025 %94,9). Sızıntı önlemi: günlük
özellik BİR GÜN kaydırıldı (gün kapanmadan gün içi ortalama bilinemez).
Kontrol AYNI tarihlere kısıtlandı: +%72,2 / Sharpe 2,760 / 2023 3,947 /
2025 2,903 / düşüş 11,45 (1.096 gün).

BULGU 1 — GERÇEK BULGU: DEFTER TEK BAŞINA ÇALIŞAN KİTAP ÜRETİYOR
----------------------------------------------------------------
    aday           getiri   Sharpe   2023    2025   düşüş   eşit-risk
    **dd5**        +%82,7   **2,947** 3,215  4,021   13,22    +%71,7
    **dd1**        +%76,9   **2,852** 4,000  3,161   15,81    +%55,7
    dd1_std_ters   +%79,9    2,429   3,084  2,908   20,54    +%44,6
    egim_ters      +%67,2    2,132   2,698  2,555   24,31    +%31,6
    seviye         +%50,6    1,970   2,681  2,191   22,89    +%25,3
    seviye_ters    +%35,3    1,600   1,204  2,551   14,57    +%27,7
    egim           +%18,1    1,286   2,277  1,049   12,56    +%16,5
    dd1_ters       +%18,8    1,015   0,861  1,626   23,22     +%9,3
    dd5_ters       +%16,4    0,873   2,275  0,217   16,57    +%11,4
    dd1_std         +%8,3    0,723   1,931  0,082   17,02     +%5,6
    (kontrol        +%72,2   2,760   3,947  2,903   11,45    +%72,2)

**Hiç funding girdisi olmadan**, yalnız emir defteri dengesizliğiyle
seçim yapan bir kitap kontrolden YÜKSEK Sharpe veriyor (dd5 2,947 vs
2,760). Kalabalık primi defterde gerçekten görünüyor. İşaret de
belirsiz değilmiş: **alış tarafı ince olanı LONG almak** çalışıyor,
tersi çökiyor (dd5 2,947 vs dd5_ters 0,873).

BULGU 2 — AMA AYNI PRİM: KORELASYON +0,74 / +0,77
-------------------------------------------------
Kontrol kitabıyla günlük getiri korelasyonu: **dd1 +0,765 · dd5 +0,741**
(diğerleri +0,20 … +0,81). Madde 200'ün korelasyon kapısı (<0,10)
yakınından geçilmiyor. Harman doz-tepkisi, **eşit riskte**:

    pay    dd1 Sharpe / eşit-risk      dd5 Sharpe / eşit-risk
    0,00     2,760 / +%72,2              2,760 / +%72,2
    0,10     2,830 / +%72,9              2,848 / +%72,5
    0,20     2,890 / +%73,6              2,925 / +%72,8
    0,30     2,937 / **+%74,2**          2,987 / +%73,0
    0,50     2,987 / +%72,7              3,060 / +%73,2

Sharpe yükseliyor (2,760 → 2,937) ama **eşit-risk getirisi en fazla
+2,0 puan** oynuyor — madde 230'un ±5 puanlık gürültü bandının içinde
ve kanıt barının çok altında. Madde 251'in yasası birebir: *"Sharpe ile
PARA'yı ayıran kapı şart 3'tür."*

BULGU 3 — DÖRT ŞART VE ÇOKLUK
-----------------------------
Yerine koyma (seçiciyi değiştirme) olarak:
* **dd1 şart 1'i İKİ alt dönemde de geçiyor** (2023 4,000 > 3,947 ·
  2025 3,161 > 2,903) — ama **şart 2 RED** (düşüş 15,81 vs 11,45, +4,4
  puan > 3 toleransı) ve **şart 3 RED, VETO** (eşit-risk +%55,7 vs
  +%72,2 = **−16,5 puan**).
* dd5 tam örnekte daha yüksek Sharpe veriyor ama **şart 1'den RED**
  (2023'te 3,215 < 3,947) — kuralın yakalamak için var olduğu dönem
  seçme imzası.
* **ÇOKLUK: 10 aday denendi → hepsi etkisizken en az birinin şart 1'i
  geçme olasılığı %91,9.** dd1'in şart 1'i geçmesi tam olarak gürültünün
  öngördüğü şey. Tek bir geçiş DELİL DEĞİL.

Kol olarak: korelasyon +0,74/+0,77 madde 200'ün kapısını geçmiyor;
madde 271'in tabanı (korelasyon 0,07'de Sharpe 1,91) bu korelasyonda
hesaplanamaz bile — `kol_gecer_mi()` üç uyarı birden döndürüyor.

HÜKÜM
-----
**RED.** Üç bağımsız sebep: (1) dd1 şart 2 ve şart 3'ten (veto) düşüyor,
(2) dd5 şart 1'den düşüyor, (3) tek geçiş çoklukla açıklanıyor (%91,9).
Kol olarak da korelasyon kapısı kapalı ve eşit-risk kazancı +2,0 puanla
gürültü içinde. **Ayar DEĞİŞMEDİ.**

Ama bu RED bir şey ÖĞRETİYOR: madde 220 *"bu piyasadaki her carry primi
aynı primin bir yüzü"* demişti ve funding · baz · borsalar arası fark ·
olay primi diye dört yüz saymıştı. **Emir defteri dengesizliği beşinci
yüz** — ve ilk kez tamamen bağımsız bir veri kümesinden ölçüldü.
Yasanın en güçlü doğrulanması: aynı prim, tamamen farklı bir enstrüman,
korelasyon +0,74.

SINIR (dürüstlük gereği)
-----------------------
Yalnız 2023 ve 2025 ölçüldü (4,7 yılın 2'si), kasten iki rejimi de
kapsayacak şekilde. Şart 1 bu iki yılla sınandı, projenin standart
22-24/25-26 bölmesiyle değil. Tam tarihe genişletmek ~35 GB daha indirme
demek; hiçbir aday hayatta kalmadığı için yapılmadı. Bir aday şart 2 ve
3'ü geçseydi gerekli olurdu.

DERS
----
**Tek başına çalışan bir kitap üretmek, EKLEMEK demek değildir.** dd5
kontrolden YÜKSEK Sharpe veriyor (2,947 vs 2,760) ve yine hiçbir şey
eklemiyor; karar veren sayı adayın kendi Sharpe'ı değil **korelasyonu**.
Yeni bir veri kümesi bulduğunda ilk hesaplanacak şey o kümenin ürettiği
kitabın performansı değil, o kitabın mevcut kitapla **korelasyonudur** —
çünkü +0,74 korelasyonda Sharpe ne olursa olsun eşit-risk kazancı
gürültüye gömülür.
"""
from __future__ import annotations

# --- veri -------------------------------------------------------------
VERI = {
    "kume": "data.binance.vision futures/um/daily/bookDepth",
    "dosya_boyut_kb": 449, "anlik_goruntu_gun": 2743,
    "istenen_cift": 33083, "alinan_cift": 32751,
    "sembol": 462, "gun": 724, "yillar": (2023, 2025),
    "kapsama_pct": 95.0, "kapsama_2023": 95.1, "kapsama_2025": 94.9,
    "sizinti_onlemi": "gunluk ozellik BIR GUN kaydirildi",
}
AGGTRADES_MB = 15.2        # neden olceklenemez

KONTROL = {"getiri": 72.2, "sharpe": 2.760, "y2023": 3.947,
           "y2025": 2.903, "dusus": 11.45, "gun": 1096}

# aday -> (getiri, sharpe, 2023, 2025, dusus, esit_risk, korelasyon)
ADAY = {
    "dd5": (82.7, 2.947, 3.215, 4.021, 13.22, 71.7, 0.741),
    "dd1": (76.9, 2.852, 4.000, 3.161, 15.81, 55.7, 0.765),
    "dd1_std_ters": (79.9, 2.429, 3.084, 2.908, 20.54, 44.6, 0.806),
    "egim_ters": (67.2, 2.132, 2.698, 2.555, 24.31, 31.6, 0.798),
    "seviye": (50.6, 1.970, 2.681, 2.191, 22.89, 25.3, 0.737),
    "seviye_ters": (35.3, 1.600, 1.204, 2.551, 14.57, 27.7, 0.286),
    "egim": (18.1, 1.286, 2.277, 1.049, 12.56, 16.5, 0.330),
    "dd1_ters": (18.8, 1.015, 0.861, 1.626, 23.22, 9.3, 0.577),
    "dd5_ters": (16.4, 0.873, 2.275, 0.217, 16.57, 11.4, 0.558),
    "dd1_std": (8.3, 0.723, 1.931, 0.082, 17.02, 5.6, 0.204),
}
BAKIS = len(ADAY)
COK_BAKIS_RISKI = 91.9          # karar_kurali.cok_bakis_riski(10)

# pay -> (dd1 sharpe, dd1 esit-risk, dd5 sharpe, dd5 esit-risk)
HARMAN = {
    0.00: (2.760, 72.2, 2.760, 72.2),
    0.10: (2.830, 72.9, 2.848, 72.5),
    0.20: (2.890, 73.6, 2.925, 72.8),
    0.30: (2.937, 74.2, 2.987, 73.0),
    0.50: (2.987, 72.7, 3.060, 73.2),
}
EN_IYI_HARMAN_KAZANC = 2.0      # puan, esit riskte
GURULTU_BANDI = 5.0             # madde 230
KORELASYON_KAPISI = 0.10        # madde 200
DUSUS_TOLERANS = 3.0            # karar_kurali
MADDE_253_OI = (112.3, 44.0)    # kalabalik olcutu degistirilince
MADDE_220_YUZLER = ("funding", "baz", "borsalar arasi fark", "olay primi")


def aggtrades_olceklenir_mi() -> bool:
    return AGGTRADES_MB < VERI["dosya_boyut_kb"] / 1000.0


def kapsama_yeterli_mi(esik: float = 90.0) -> bool:
    return VERI["kapsama_pct"] >= esik


def defter_tek_basina_calisiyor_mu() -> bool:
    """Funding girdisi OLMADAN kontrolden yuksek Sharpe veren aday var mi?"""
    return any(v[1] > KONTROL["sharpe"] for v in ADAY.values())


def tek_basina_calisanlar() -> list:
    return [a for a, v in ADAY.items() if v[1] > KONTROL["sharpe"]]


def isaret_belirsiz_miydi() -> bool:
    """Her iki isaret denendi; biri calisip digeri cokuyor mu?"""
    return ADAY["dd5"][1] > 2.5 and ADAY["dd5_ters"][1] < 1.0


def ayni_prim_mi(esik: float = 0.50) -> bool:
    """En iyi adaylarin korelasyonu yuksek mi (= ayni prim)?"""
    return min(ADAY["dd1"][6], ADAY["dd5"][6]) > esik


def korelasyon_kapisini_geciyor_mu(aday: str = "dd5") -> bool:
    return ADAY[aday][6] < KORELASYON_KAPISI


def sart1_gecen() -> list:
    return [a for a, v in ADAY.items()
            if v[2] > KONTROL["y2023"] and v[3] > KONTROL["y2025"]]


def sart2_gecer_mi(aday: str) -> bool:
    return ADAY[aday][4] - KONTROL["dusus"] <= DUSUS_TOLERANS


def sart3_gecer_mi(aday: str) -> bool:
    """Esit riskte getiri DUSMESIN (VETO)."""
    return ADAY[aday][5] >= KONTROL["getiri"]


def dort_sart_gecen() -> list:
    return [a for a in sart1_gecen() if sart2_gecer_mi(a) and sart3_gecer_mi(a)]


def tek_gecis_delil_mi() -> bool:
    """Tek bir sart-1 gecisi, 10 bakista DELIL mi?"""
    return COK_BAKIS_RISKI < 30.0


def harman_gurultunun_icinde_mi() -> bool:
    return EN_IYI_HARMAN_KAZANC < GURULTU_BANDI


def sharpe_yukselirken_para_sabit_mi() -> bool:
    """Harmanda Sharpe yukseliyor ama esit-risk getirisi sabit mi?"""
    s0, e0 = HARMAN[0.00][0], HARMAN[0.00][1]
    s3, e3 = HARMAN[0.30][0], HARMAN[0.30][1]
    return (s3 - s0) > 0.15 and (e3 - e0) < GURULTU_BANDI


def kacinci_yuz() -> int:
    """Madde 220 dort yuz saymisti; defter kacinci?"""
    return len(MADDE_220_YUZLER) + 1


def hukum() -> str:
    return ("RED. Defter dengesizligi tek basina CALISAN kitap uretiyor "
            "(dd5 Sharpe %.3f > kontrol %.3f, funding girdisi YOK) ama "
            "korelasyon +%.3f -> AYNI PRIM (madde 220'nin %d. yuzu). "
            "Yerine koyma: dd1 sart 1'i gecip sart 2 (dusus +%.2f puan) "
            "ve sart 3'ten (esit-risk %+.1f vs %+.1f, VETO) dusuyor; dd5 "
            "sart 1'den dusuyor; ve tek gecis %d bakista cokluğun "
            "ongordugu sey (%%%.1f). Kol: korelasyon kapisi kapali, "
            "harman kazanci +%.1f puan = gurultu. Ayar DEGISMEDI."
            % (ADAY["dd5"][1], KONTROL["sharpe"], ADAY["dd5"][6],
               kacinci_yuz(), ADAY["dd1"][4] - KONTROL["dusus"],
               ADAY["dd1"][5], KONTROL["getiri"], BAKIS, COK_BAKIS_RISKI,
               EN_IYI_HARMAN_KAZANC))


def yaz() -> None:
    print("MADDE 279 — EMİR DEFTERİ DERİNLİĞİ SEÇİCİ OLARAK\n")
    print("VERİ: %s" % VERI["kume"])
    print("  %d/%d sembol-gün (%%%.1f) · %d sembol · %d gün · yıllar %s"
          % (VERI["alinan_cift"], VERI["istenen_cift"],
             VERI["alinan_cift"] / VERI["istenen_cift"] * 100,
             VERI["sembol"], VERI["gun"], VERI["yillar"]))
    print("  kapsama: uygun hücrelerin %%%.1f'i (2023 %%%.1f · 2025 %%%.1f)"
          % (VERI["kapsama_pct"], VERI["kapsama_2023"], VERI["kapsama_2025"]))
    print("  sızıntı önlemi: %s" % VERI["sizinti_onlemi"])
    print("  (aggTrades %.1f MB/sembol-gün ile ölçeklenemezdi: %s)"
          % (AGGTRADES_MB, aggtrades_olceklenir_mi()))
    print("\nKONTROL (aynı tarihler): getiri +%%%.1f | Sharpe %.3f | 2023 %.3f"
          " | 2025 %.3f | düşüş %.2f"
          % (KONTROL["getiri"], KONTROL["sharpe"], KONTROL["y2023"],
             KONTROL["y2025"], KONTROL["dusus"]))
    print("\nADAYLAR (%d = 5 özellik × 2 işaret, ÖN KAYITTA beyan edildi):" % BAKIS)
    print("  aday          | getiri | Sharpe | 2023  | 2025  | düşüş | eşit-risk | kor")
    for a, v in sorted(ADAY.items(), key=lambda x: -x[1][1]):
        print("  %-13s | %+6.1f | %6.3f | %5.3f | %5.3f | %5.2f | %+9.1f | %+.3f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5], v[6]))
    print("  -> defter TEK BAŞINA çalışıyor mu: %s %s"
          % (defter_tek_basina_calisiyor_mu(), tek_basina_calisanlar()))
    print("  -> işaret belirsiz miydi (biri çalışıp diğeri çöküyor): %s"
          % isaret_belirsiz_miydi())
    print("\nAMA AYNI PRİM: korelasyon dd1 +%.3f · dd5 +%.3f (madde 200 kapısı %.2f)"
          % (ADAY["dd1"][6], ADAY["dd5"][6], KORELASYON_KAPISI))
    print("  -> korelasyon kapısını geçiyor mu: %s | aynı prim mi: %s"
          % (korelasyon_kapisini_geciyor_mu(), ayni_prim_mi()))
    print("\nHARMAN DOZ-TEPKİSİ (eşit riskte):")
    print("  pay  | dd1 Sharpe / eşit-risk | dd5 Sharpe / eşit-risk")
    for p in sorted(HARMAN):
        s1, e1, s5, e5 = HARMAN[p]
        print("  %.2f | %6.3f / %+9.1f     | %6.3f / %+9.1f" % (p, s1, e1, s5, e5))
    print("  -> Sharpe yükselirken PARA sabit mi: %s | kazanç gürültünün içinde mi: %s"
          % (sharpe_yukselirken_para_sabit_mi(), harman_gurultunun_icinde_mi()))
    print("\nDÖRT ŞART:")
    print("  şart 1'i geçen: %s" % sart1_gecen())
    for a in sart1_gecen():
        print("    %s -> şart 2 %s (düşüş %+.2f puan) | şart 3 (VETO) %s"
              " (eşit-risk %+.1f vs %+.1f)"
              % (a, "GEÇTİ" if sart2_gecer_mi(a) else "RED",
                 ADAY[a][4] - KONTROL["dusus"],
                 "GEÇTİ" if sart3_gecer_mi(a) else "RED",
                 ADAY[a][5], KONTROL["getiri"]))
    print("  dört şartı geçen: %s" % (dort_sart_gecen() or "YOK"))
    print("  ÇOKLUK: %d bakış -> %%%.1f | tek geçiş DELİL mi: %s"
          % (BAKIS, COK_BAKIS_RISKI, tek_gecis_delil_mi()))
    print("\nMADDE 220'NİN YÜZLERİ: %s + **emir defteri dengesizliği** = %d."
          % (", ".join(MADDE_220_YUZLER), kacinci_yuz()))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
