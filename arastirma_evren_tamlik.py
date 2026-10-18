#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 269 — EVREN TAMLIĞI: örnekleme değil, TÜKETEREK denetim. Ve bir
boşluk bulundu.

ÖNCE DÜRÜSTLÜK: BU TURU AÇARKEN YANILDIM
----------------------------------------
Madde 268'in dersini ("eksenleri BÜYÜKLÜK sırasına göre denetle")
uygulayıp kalan en büyük kaleme, ham fiyata (−108,0 puan) ve onun
dayandığı fiyat paneline baktım. README'de survivorship'in
**"SURVIVORSHIP CONFIDENCE: LOW"** ve "en ciddi açık" diye işaretli
olduğunu görüp "130 maddedir açık duran risk" diye tura başladım.

**Yanlıştı: madde 146 bu işi zaten yapmış.** Orada ölçülmüş olanlar:
  * Binance arşivi delist edilen sembolü SİLMİYOR, **donduruyor** —
    fiyat donuk, hacim sıfır barlar yazmaya devam ediyor (FTTUSDT'nin
    son gerçek işlemi 2022-11-14 ama dosya 2026-08-31'e kadar sürüyor).
  * Bu yüzden "28 delist" sayısı YANLIŞTI; son İŞLEM GÖREN bara göre
    sayınca **156 delist** (2022:14 · 2023:3 · 2024:30 · 2025:47 ·
    2026:62).
  * Güven LOW -> **MEDIUM-HIGH**.

Ve ben bu turda `last_valid_index()` ile sayıp yine **28** buldum — yani
madde 134'ün tam olarak düzeltilmiş hatasını yeniden üretmişim. Bu
modülün ilk işi bunu kayda geçirmek: **bir riski açmadan önce o riskin
en SON ele alındığı maddeyi oku, risk tablosunun satırını değil.** Risk
tablosu 136.13'ten kalmış LOW'u taşıyordu; düzeltme 10 madde sonra
geldiği için tabloya yansımamıştı. (Madde 256'nın "defteri değil
docstring'i oku" dersinin ikizi.)

YİNE DE BU TUR BİR ŞEY EKLEDİ: ÖRNEKLEME DEĞİL TÜKETME
------------------------------------------------------
Madde 146 kapsamı ÖRNEKLEYEREK denetledi: "bilinen 50 delist tek tek
arandı, 45'i arşivde." Bu, "aradığımız sembol var mı" sorusunu yanıtlar;
"arşivde olup bizde OLMAYAN sembol var mı" sorusunu yanıtlamaz.

Bu tur onu TÜKETEREK yanıtladı. `data.binance.vision`in S3 listelemesi
sayfalanarak çekildi:

    arşivdeki tüm USDⓈ-M sembol      1.057
      USDT paritesi                    901
      USDC                              40 | diğer                116
    bizim panel                        847
    arşivde VAR, bizde YOK              54      (847 + 54 = 901, tam)

54'ün tamamı tek tek sınıflandırıldı:
  * **39'u hisse/FX perp** (ACN, AMC, ANET, BYD, CVNA, DDOG, DJT, GPRO,
    GTLB, HK0625, HK0992, HUT, IONQ, MARA, MDB, MRK, MRNA, NKE, NVDL,
    OKLO, OURA, PATH, PDD, RUM, SECZ, TEAM, TEM, TSLL, TWST, UNH,
    USDBRL, XOM, ZS, ...) -> kitap TRADFI'yi kural gereği dışlıyor.
  * **3'ü örnek ÖNCESİ delist**: BZRXUSDT (2020-09..2021-12),
    LENDUSDT (2020-07..2020-11), DOTECOUSDT (2021-01..2021-02).
  * **7'si örnek SONRASI listeleme** (yalnız 2026-09): CYPHUSDT,
    MARSCOINUSDT, MOONSHOTUSDT, PONSUSDT, AGPUUSDT, BWETUSDT, 哈基米USDT.
  * **1'i arşivde dosyasız**: CTUSDT.
  * **3'ü hacim eşiğinin altında**: 我踏马来了USDT (9 ay, 24sa ciro
    medyanı 2,2M$), 龙虾USDT (7 ay, 7,3M$), ve 牛来USDT (2 ay, 97,6M$ —
    sınırda ve örneğin en sonunda).
  * **1 GERÇEK BOŞLUK**: **币安人生USDT** — 2025-10..2026-09, yani
    örneğin İÇİNDE 11 ay, 24sa ciro medyanı **128,1M$** -> 100M$
    eşiğinin ÜSTÜNDE. Panelde yok.

ARŞİV BUDANMAMIŞ — BAĞIMSIZ KANIT
---------------------------------
Madde 134'ün temel kaygısı "arşiv büyük olasılıkla budanmış"tı. Arşiv
bugün **2020'de delist edilmiş** BZRXUSDT ve LENDUSDT'yi hâlâ
taşıyor. Budanmış bir arşivde bunlar olmazdı.

BAR BOYUTU DA DENETLENDİ
------------------------
Sembol boyutu yeterli değil: panelin bir sembolü TAŞIYIP barlarını erken
KESMESİ de bir yanlılık olurdu. Sekiz sembolde (üçü canlı, beşi delist)
panelin son barı ile arşivin son ayı karşılaştırıldı; **sekizinde de
birebir uyumlu**: 1000BTTCUSDT 2022-04 · AKROUSDT 2022-05 · ANCUSDT
2022-05 · ANTUSDT 2024-05 · AERGOUSDT 2026-06.

BULUNAN BOŞLUĞUN BÜYÜKLÜĞÜ — ÖLÇÜLDÜ, TAHMİN EDİLMEDİ
-----------------------------------------------------
币安人生USDT'nin funding geçmişi arşivden çekildi (örnek içinde 1.892
ödeme): ortalama **+%0,01260/ödeme**, medyan +%0,00500, p95 +%0,05606
-> günlük eşdeğer **+%0,0378/gün**.

Bunu madde 230'un ölçtüğü seçilmiş bacak profiliyle kıyaslayın: LONG 1.
aday −%0,733/gün (uç), SHORT 1. +%0,056, **SHORT 2.-5. +%0,030**
(standart oran). Yani bu sembol funding ucunda DEĞİL; olsa olsa
**marjinal bir SHORT adayı** olurdu — ve madde 229 marjinal adayın
"nakitten kötü", madde 230 da sönümün 2. adaydan sonra başladığını
ölçmüştü. Kapsam da sınırlı: 56 aylık örneğin 11 ayı, ~20-39 sembollük
uygun havuzda bir sembol.

**HÜKÜM: evren tamlığı TÜKETEREK doğrulandı. Bir boşluk var, ölçüldü ve
etkisi küçük; yönü belirsiz ama büyük olasılıkla kitap LEHİNE (marjinal
bir short adayı eklemek madde 229'a göre getiri düşürür). Ayar
DEĞİŞMEDİ.** Yeniden açma şartı: panel yeniden indirildiğinde
币安人生USDT ve 牛来USDT dahil edilsin; dahil edilirse kontrol koşusu
yeniden alınmalı.
"""
from __future__ import annotations

ARSIV = {"tum": 1057, "usdt": 901, "usdc": 40, "diger": 116}
PANEL_SEMBOL = 847
EKSIK = 54

EKSIK_SINIF = {
    "tradfi_hisse_fx": 39,
    "ornek_oncesi_delist": 3,      # BZRX, LEND, DOTECO
    "ornek_sonrasi_listeleme": 7,  # yalnız 2026-09
    "arsivde_dosyasiz": 1,         # CTUSDT
    "hacim_esigi_altinda": 3,      # 我踏马来了, 龙虾, 牛来
    "gercek_bosluk": 1,            # 币安人生USDT
}

BOSLUK = {
    "sembol": "币安人生USDT",
    "ilk_ay": "2025-10", "son_ay": "2026-09",
    "ornek_ici_ay": 11,
    "ciro_medyan_musd": 128.1,
    "funding_ode_ort_pct": 0.01260,
    "funding_ode_medyan_pct": 0.00500,
    "funding_ode_p95_pct": 0.05606,
    "funding_gunluk_pct": 0.0378,
    "odeme_sayisi": 1892,
}
# madde 230'un seçilmiş bacak profili (günlük funding, %)
MADDE_230_PROFIL = {"long1": -0.733, "short1": 0.056, "short2_5": 0.030}

BUDANMAMIS_KANIT = ("arşiv 2020'de delist edilen BZRXUSDT (2020-09..2021-12) "
                    "ve LENDUSDT (2020-07..2020-11) dosyalarını hâlâ taşıyor")

BAR_DENETIMI = {
    "ornek": 8, "uyumlu": 8,
    "delist_ornekleri": {"1000BTTCUSDT": "2022-04", "AKROUSDT": "2022-05",
                         "ANCUSDT": "2022-05", "ANTUSDT": "2024-05",
                         "AERGOUSDT": "2026-06"},
}

# madde 146 zaten ölçmüştü — bu tur onu TEKRAR ETMEDİ, TÜKETEREK genişletti
MADDE_146 = {
    "arsiv_dondurur_silmez": True,
    "gercek_delist": 156,
    "yillara_gore": {2022: 14, 2023: 3, 2024: 30, 2025: 47, 2026: 62},
    "guven_eski": "LOW", "guven_yeni": "MEDIUM-HIGH",
    "yontem": "ÖRNEKLEME (bilinen 50 delist arandı, 45 bulundu)",
}
BU_TURUN_YONTEMI = "TÜKETME (S3 listelemesi sayfalanarak, 901 USDT sembol)"

ACILIS_HATASI = ("bu turu 'survivorship 130 maddedir LOW' diye açtım; oysa "
                 "madde 146 düzeltmişti. Risk TABLOSU 136.13'ten kalma LOW'u "
                 "taşıyordu, düzeltme 10 madde sonra geldiği için tabloya "
                 "yansımamıştı. Üstüne `last_valid_index()` ile sayıp yine "
                 "28 buldum — madde 134'ün tam olarak düzeltilmiş hatası.")


def aritmetik_kapaniyor_mu() -> bool:
    """Panel + eksik = arşivdeki USDT sembol sayısı?"""
    return PANEL_SEMBOL + EKSIK == ARSIV["usdt"]


def siniflandirma_tam_mi() -> bool:
    return sum(EKSIK_SINIF.values()) == EKSIK


def arsiv_budanmis_mi() -> bool:
    return False          # BZRX/LEND kanıtı


def bosluk_funding_ucunda_mi() -> bool:
    """Bulunan boşluk funding ucunda mı, yoksa sıradan mı?"""
    return BOSLUK["funding_gunluk_pct"] > abs(MADDE_230_PROFIL["short1"])


def bosluk_marjinal_mi() -> bool:
    """Boşluk olsa olsa marjinal bir SHORT adayı mı?"""
    return (not bosluk_funding_ucunda_mi()
            and BOSLUK["funding_gunluk_pct"] >= MADDE_230_PROFIL["short2_5"])


def bar_boyutu_temiz_mi() -> bool:
    return BAR_DENETIMI["uyumlu"] == BAR_DENETIMI["ornek"]


def dogrula() -> bool:
    return (aritmetik_kapaniyor_mu() and siniflandirma_tam_mi()
            and bar_boyutu_temiz_mi() and not arsiv_budanmis_mi())


def yeniden_acma_sarti() -> str:
    return ("panel yeniden indirildiğinde 币安人生USDT ve 牛来USDT dahil "
            "edilsin; dahil edilirse kontrol koşusu yeniden alınmalı")


def hukum() -> str:
    return ("Evren tamlığı TÜKETEREK doğrulandı; 1 boşluk bulundu, ölçüldü, "
            "etkisi küçük ve yönü büyük olasılıkla kitap LEHİNE. "
            "Ayar DEĞİŞMEDİ.")


def yaz() -> None:
    print("MADDE 269 — EVREN TAMLIĞI (tüketerek denetim)\n")
    print("AÇILIŞ HATASI: %s\n" % ACILIS_HATASI)
    print("madde 146 yöntemi : %s" % MADDE_146["yontem"])
    print("bu turun yöntemi  : %s" % BU_TURUN_YONTEMI)
    print("\nARŞİV: %d sembol (USDT %d · USDC %d · diğer %d)"
          % (ARSIV["tum"], ARSIV["usdt"], ARSIV["usdc"], ARSIV["diger"]))
    print("PANEL: %d | EKSİK: %d | aritmetik kapanıyor mu: %s"
          % (PANEL_SEMBOL, EKSIK, aritmetik_kapaniyor_mu()))
    print("\nEKSİĞİN SINIFLANDIRMASI (toplam %s):" % siniflandirma_tam_mi())
    for k, v in EKSIK_SINIF.items():
        print("  %-26s %2d" % (k, v))
    print("\nARŞİV BUDANMIŞ MI: %s" % arsiv_budanmis_mi())
    print("  kanıt: %s" % BUDANMAMIS_KANIT)
    print("\nBAR BOYUTU: %d/%d uyumlu -> temiz mi: %s"
          % (BAR_DENETIMI["uyumlu"], BAR_DENETIMI["ornek"], bar_boyutu_temiz_mi()))
    print("\nBULUNAN BOŞLUK: %s" % BOSLUK["sembol"])
    print("  %s..%s · örnek içinde %d ay · ciro medyanı %.1fM$"
          % (BOSLUK["ilk_ay"], BOSLUK["son_ay"], BOSLUK["ornek_ici_ay"],
             BOSLUK["ciro_medyan_musd"]))
    print("  funding %d ödeme · ortalama +%%%.5f/ödeme · günlük +%%%.4f"
          % (BOSLUK["odeme_sayisi"], BOSLUK["funding_ode_ort_pct"],
             BOSLUK["funding_gunluk_pct"]))
    print("  madde 230 profili: LONG1 %%%.3f · SHORT1 +%%%.3f · SHORT2-5 +%%%.3f"
          % (MADDE_230_PROFIL["long1"], MADDE_230_PROFIL["short1"],
             MADDE_230_PROFIL["short2_5"]))
    print("  funding ucunda mı: %s | marjinal short adayı mı: %s"
          % (bosluk_funding_ucunda_mi(), bosluk_marjinal_mi()))
    print("\nDOĞRULAMA: %s" % dogrula())
    print("YENİDEN AÇMA ŞARTI: %s" % yeniden_acma_sarti())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
