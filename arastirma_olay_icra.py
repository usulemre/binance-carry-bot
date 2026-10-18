#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 277 — OLAY KOLU GERÇEK İCRAYLA ÖLÇÜLDÜ: RED, VE MADDE 166 DÜZELTİLDİ.
AYRICA GERÇEK BİR KUSUR: `CARRY_OLAY_PAY` VARSAYILANI 0,20'YDİ.

Kullanıcı "soket mantığıyla anlık karar verilemez mi?" diye sordu. Cevabı
yazarken projenin ZATEN dakika seviyesinde bir kolu olduğunu hatırladım
(`carry_olay.py`, madde 166) ve madde 275'te o kolu hiç kontrol
etmediğimi gördüm. Madde 263'te "kitap bunu zaten kullanıyor mu?" diye
sormuştum; 275'te sormadım. Bu madde o boşluğu kapatıyor.

KUSUR — BELGE İLE KOD AYNI AYAR HAKKINDA TERS ŞEY SÖYLÜYORDU
------------------------------------------------------------
`carry_olay.py` satır 50: `PAY = float(os.getenv("CARRY_OLAY_PAY", "0.20"))`
Aynı dosyanın `ESIK` belgesi, modülün kendi uyarısı ve `KAR_HARITASI.md`
ise **üç yerde** "kurulu, `CARRY_OLAY_PAY=0` ile kapalı" diyordu.
`python carry_olay.py` çevre değişkeni verilmeden çalıştırılırsa
sermayenin **%20'si** bu kola gidiyordu — modülün kendi belgesinin
"ana strateji +%52'den +%92'ye çıktığı için o karşılaştırma ARTIK
GEÇERSİZ; modül açılmadan önce yeniden ölçülmeli" dediği bir kola.
**Varsayılan 0,0'a çekildi** ve ön uçuş denetimi artık bunu kontrol
ediyor. Madde 217'nin sınıfı ama daha kötüsü: orada belge bayattı,
burada belge ile kod BİRBİRİNİ YALANLIYORDU.

ÖN KAYIT
--------
Kol kuralı (üretim kodundan birebir): `|funding| >= 20bp` olan ödemede
T−60sn'de GTX limit (5bp lehte), dolmazsa piyasa; T+5dk'da çık; yön hep
ödemeyi ALAN taraf; en fazla 6+6 bacak; bacak = sermaye*0,20/12.
Üç eşik, hepsi geçmezse kol açılmaz:
  1. ödeme başına NET bp > 0
  2. kol Sharpe >= 1,9 (madde 271'in kol tabanı)
  3. şart 1: iki alt dönemde de pozitif

VERİ — MADDE 275'İN n=12'Lİk BOŞLUĞU n=23.609'A ÇIKTI
-----------------------------------------------------
Tüm evrende `|funding| >= 20bp` ödemeler sayıldı: **730 sembolde 23.666
olay** (2022-01 → 2026-08; 2025'te 9.198, 2026'da 10.767). Her olayın
±15 dakikası hedefli indirildi (3.279 sembol-ay, ham dosya saklanmadan).
Ölçüme giren: **23.609 olay, 730 sembol, 4,7 yıl.**

BENİM HATAM — VE İYİMSER YÖNE SAPTIRIYORDU
------------------------------------------
İlk koşumda GTX limitinin referansını T−1 dakikasının **KAPANIŞI** almıştım;
oysa emir T−1'in **BAŞINDA** konuyor → ileriye bakış. Referans açılışa
çevrildi. Etki: net **−26,08 → −49,85 bp** (24 bp iyimserlik). Hata
RED'i zayıflatıyordu, yani düzeltme hükmü güçlendirdi.

BULGU 1 — ASIL BULGU: FUNDING İLE FİYAT BİRBİRİNİ GÖTÜRÜYOR, YİNE
-----------------------------------------------------------------
    gelir (|funding|)     **+53,31 bp**
    fiyat hareketi        **−52,93 bp**
    ----------------------------------
    toplam                  **+0,38 bp**
    maliyet                 −50,23 bp
    **NET**                **−49,85 bp**   medyan −27,39 · net>0 %37,5

23.609 olayda funding geliri ile fiyat hareketi **0,38 bp içinde
birbirini götürüyor.** Bu, madde 214'ün ana kitapta bulduğu şeyin
AYNISI (funding +109,8 · ham fiyat −108,0 · kâr = TP hasadı +210,5) —
ama 5 günlük ufukta değil, **6 DAKİKALIK** ufukta.

**YENİ YASA: funding/fiyat götürmesi ÖLÇEKTEN BAĞIMSIZ.** Kitap
carry'den kazanmıyor, hiçbir ufukta; **hasattan** kazanıyor. Hasat
edecek kadar uzun tutmayan bir kolda gelir diye bir şey yok, yalnız
maliyet var. Olay kolu = ana kitap EKSİ hasat.

BULGU 2 — UÇ FUNDING ÜCRETİNDEN PAHALI, UCUZ DEĞİL
--------------------------------------------------
    gelir dilimi    n       gelir     fiyat       NET
     20-30 bp     8.866     +24,3    −19,68    −35,55
     30-50 bp     6.845     +38,3    −38,26    −47,11
     50-100 bp    5.178     +69,3    −66,72    −53,12
     **100+ bp**  2.720    +155,2  **−172,00** **−97,17**

Doz-tepki monoton ve en uçta **fiyat hareketi geliri AŞIYOR.** Yani
"çok yüksek funding varsa maliyeti karşılar" sezgisi tersine çalışıyor:
funding yükseldikçe onun fiyatı daha da hızlı yükseliyor. Madde 201'in
"funding, olayın FİYATIDIR" yasasının en keskin ölçümü.

BULGU 3 — MAKER DOLUMU TERS SEÇİLİMİN KENDİSİ
---------------------------------------------
    maker doldu     n=23.224 | fiyat **−53,96** | NET −50,25
    piyasaya düştü  n=   385 | fiyat **+9,15**  | NET −26,06

GTX limiti %98,3 oranında doluyor — ve **dolduğu için kötü.** Limit,
fiyat sana doğru geldiği için doluyor ve fiyat gelmeye devam ediyor.
Dolmayanlarda fiyat lehte (+9,15), çünkü fiyat limitten KAÇMIŞ. Bu,
madde 213'ün ters seçilim bulgusunun aynadaki görüntüsü.
Not: `PIYASA_YEDEK` belgesi "dolmayanlar taker'a düşse bile funding
ücretin kat kat üstünde (+57,1 / +32,2 bp)" diyordu — yön doğru
(dolmayanlar DAHA İYİ) ama işaret yanlış: ikisi de negatif. Düzeltildi.

KOL DÜZEYİ — ÜÇ EŞİĞİN ÜÇÜ DE RED
---------------------------------
    PAY=0,20 · MAKS=6 · bacak = sermayenin %1,67'si · 1.704 gün
    TAM        yıllık **−%34,13** | Sharpe **−9,297** | maks düşüş −%85,74
    2022-24    yıllık  −%6,07     | Sharpe −5,174    | −%17,13
    2025-26    yıllık **−%65,26** | Sharpe −17,500   | −%82,79

    1) ödeme başına NET > 0       : −49,85 bp -> **RED**
    2) kol Sharpe >= 1,9          : −9,297   -> **RED**
    3) iki alt dönemde de pozitif : −5,17 / −17,50 -> **RED**

MADDE 166 DÜZELTİLDİ
--------------------
Madde 166 bu kolu "+%21,7/yıl, Sharpe 1,18, korelasyon 0,19" ile şartlı
KABUL etmişti ve `carry_olay.py` o kararın ürünü. Bu ölçüm onu
çürütüyor: kol gerçek icrayla **−%34,13**. İki ek not:
* Madde 166'nın KENDİ Sharpe'i (1,18) bile madde 271'in 105 madde sonra
  koyduğu kol tabanının (1,9) altında. Yani kol, bugünkü kabul
  eşiğinden kendi iyimser rakamıyla da geçemiyordu.
* Modülün kendi belgesi zaten "yeniden ölçülmeli" diyordu; eksik olan
  ölçümdü, uyarı değil. **Uyarı yazmak ölçüm yapmak değildir.**

HÜKÜM
-----
**Olay kolu ÖLÜ.** `CARRY_OLAY_PAY` varsayılanı 0,0 (kusur düzeltildi);
modülün tesisatı `carry_bot.py`'de duruyor (PAY=0 iken zararsız: kilit
ve emir koruma yolları). Madde 201'in "olay stratejileri ailesi kapandı"
hükmü, madde 166'nın açtığı istisnayla birlikte **tamamen kapandı**.
Ana ayar DEĞİŞMEDİ.

DERS
----
**Funding ile fiyatın birbirini götürmesi ölçekten bağımsızdır; kâr
hasattan gelir, taşımadan değil.** Bir kol hasat edecek kadar uzun
tutmuyorsa geliri yoktur — ne kadar yüksek funding seçerse seçsin,
çünkü seçtiği funding'in fiyatı da o kadar yüksektir. Ve ikinci ders:
**bir modülün belgesine "açılmadan önce ölçülmeli" yazmak, o modülü
güvenli kılmaz** — varsayılanı 0,20'de bırakmıştım.
"""
from __future__ import annotations

# --- kusur -------------------------------------------------------------
KUSUR = {
    "dosya": "carry_olay.py",
    "ayar": "CARRY_OLAY_PAY",
    "eski_varsayilan": 0.20,
    "yeni_varsayilan": 0.0,
    "belgenin_dedigi": "kurulu, CARRY_OLAY_PAY=0 ile kapalı",
    "kac_yerde_ters": 3,
    "sinif": "madde 217 (ayarın yanındaki bayat talimat) ama belge ile kod"
             " AYNI ayar hakkında ters sey soyluyordu",
}

# --- veri --------------------------------------------------------------
ESIK_BP = 20.0                 # carry_olay.ESIK = 0.0020
ARZ_OLAY = 23666               # tum evrende |funding| >= 20bp odeme
ARZ_SEMBOL = 730
OLCULEN_OLAY = 23609
SEMBOL_AY = 3279
MADDE_275_BOSLUK_N = 12        # 275'te 20-40bp diliminde kalan ornek

# --- benim hatam -------------------------------------------------------
HATAM = {
    "ne": "GTX limitinin referansi T-1 KAPANISI aliniyordu; emir T-1'in"
          " BASINDA konuyor -> ileriye bakis",
    "hatali_net": -26.08,
    "duzeltilmis_net": -49.85,
    "yonu": "IYIMSER (RED'i zayiflatiyordu)",
}

# --- olcum (bp/odeme) --------------------------------------------------
OLCUM = {
    "gelir": 53.31, "fiyat": -52.93, "maliyet": -50.23,
    "net": -49.85, "net_medyan": -27.39, "net_pozitif_pct": 37.5,
    "maker_dolum_pct": 98.3,
}
GOTURME = OLCUM["gelir"] + OLCUM["fiyat"]          # +0.38 bp
MADDE_214_GOTURME = (109.8, -108.0, 210.5)         # funding, fiyat, TP hasadi

DILIM = {   # (alt, ust) -> (n, gelir, fiyat, net, net_pozitif_pct)
    (20, 30): (8866, 24.3, -19.68, -35.55, 37.5),
    (30, 50): (6845, 38.3, -38.26, -47.11, 37.4),
    (50, 100): (5178, 69.3, -66.72, -53.12, 38.5),
    (100, None): (2720, 155.2, -172.00, -97.17, 36.4),
}

DOLUM = {   # tur -> (n, fiyat_bp, net_bp)
    "maker_doldu": (23224, -53.96, -50.25),
    "piyasaya_dustu": (385, 9.15, -26.06),
}

YILLAR = {2022: -42.13, 2023: -21.46, 2024: -31.93, 2025: -57.94, 2026: -49.40}

# --- kol duzeyi --------------------------------------------------------
PAY, MAKS = 0.20, 6
KOL = {   # donem -> (yillik, sharpe, maks_dusus)
    "tam": (-34.13, -9.297, -85.74),
    "2022-24": (-6.07, -5.174, -17.13),
    "2025-26": (-65.26, -17.500, -82.79),
}
KOL_TABANI = 1.9              # madde 271
MADDE_166 = {"yillik": 21.7, "sharpe": 1.18, "korelasyon": 0.19}


def kusur_duzeltildi_mi() -> bool:
    return KUSUR["yeni_varsayilan"] == 0.0


def hatam_iyimser_miydi() -> bool:
    """Kendi hatam hukmu hangi yone saptiriyordu?"""
    return HATAM["hatali_net"] > HATAM["duzeltilmis_net"]


def funding_fiyati_goturuyor_mu(tol: float = 2.0) -> bool:
    """Gelir ile fiyat hareketi birbirini goturuyor mu?"""
    return abs(GOTURME) < tol


def goturme_olcekten_bagimsiz_mi(tol: float = 3.0) -> bool:
    """Madde 214'un 5 GUNLUK goturmesi ile buranin 6 DAKIKALIK goturmesi
    ayni yapida mi?"""
    m214 = MADDE_214_GOTURME[0] + MADDE_214_GOTURME[1]
    return abs(m214) < tol and abs(GOTURME) < tol


def uc_funding_pahali_mi() -> bool:
    """En uc dilimde fiyat hareketi geliri ASIYOR mu?"""
    n, gelir, fiyat, net, _ = DILIM[(100, None)]
    return abs(fiyat) > gelir


def doz_tepki_monoton_mu() -> bool:
    """Gelir buyudukce aleyhte fiyat da buyuyor mu?"""
    d = [DILIM[k] for k in sorted(DILIM, key=lambda x: x[0])]
    return all(abs(d[i + 1][2]) > abs(d[i][2]) for i in range(len(d) - 1))


def maker_dolumu_ters_secilim_mi() -> bool:
    """Dolanlarda fiyat aleyhte, dolmayanlarda lehte mi?"""
    return DOLUM["maker_doldu"][1] < 0 < DOLUM["piyasaya_dustu"][1]


def esik_1_net() -> bool:
    return OLCUM["net"] > 0


def esik_2_sharpe() -> bool:
    return KOL["tam"][1] >= KOL_TABANI


def esik_3_iki_donem() -> bool:
    return min(KOL["2022-24"][1], KOL["2025-26"][1]) > 0


def kol_acilir_mi() -> bool:
    return esik_1_net() and esik_2_sharpe() and esik_3_iki_donem()


def madde_166_kendi_rakamiyla_gecer_miydi() -> bool:
    """166'nin KENDI Sharpe'i madde 271'in kol tabanini gecer miydi?"""
    return MADDE_166["sharpe"] >= KOL_TABANI


def her_yil_negatif_mi() -> bool:
    return all(v < 0 for v in YILLAR.values())


def ornek_madde_275ten_buyuk_mu() -> bool:
    return OLCULEN_OLAY > 100 * MADDE_275_BOSLUK_N


def hukum() -> str:
    return ("Olay kolu OLU: gercek icrayla yillik %+.2f%%, Sharpe %+.3f, "
            "maks dusus %+.2f%%; uc on kayitli esigin UCU DE RED. "
            "Gelir %+.2f bp ile fiyat %+.2f bp birbirini %+.2f bp icinde "
            "goturuyor (madde 214'un 6 DAKIKALIK hali), kalan sey saf "
            "maliyet. CARRY_OLAY_PAY varsayilani 0,20'den 0,0'a cekildi. "
            "Madde 166 DUZELTILDI. Ana ayar DEGISMEDI."
            % (KOL["tam"][0], KOL["tam"][1], KOL["tam"][2],
               OLCUM["gelir"], OLCUM["fiyat"], GOTURME))


def yaz() -> None:
    print("MADDE 277 — OLAY KOLU GERÇEK İCRAYLA ÖLÇÜLDÜ\n")
    print("KUSUR: %s/%s varsayılanı %.2f -> %.1f (belge %d yerde '%s' diyordu)"
          % (KUSUR["dosya"], KUSUR["ayar"], KUSUR["eski_varsayilan"],
             KUSUR["yeni_varsayilan"], KUSUR["kac_yerde_ters"],
             KUSUR["belgenin_dedigi"]))
    print("\nVERİ: |funding| >= %.0f bp -> %d olay / %d sembol; ölçülen %d"
          " (madde 275'in boşluğu n=%d idi, %s)"
          % (ESIK_BP, ARZ_OLAY, ARZ_SEMBOL, OLCULEN_OLAY,
             MADDE_275_BOSLUK_N, ornek_madde_275ten_buyuk_mu()))
    print("\nBENİM HATAM: %s\n  net %+.2f -> %+.2f bp (%s)"
          % (HATAM["ne"], HATAM["hatali_net"], HATAM["duzeltilmis_net"],
             HATAM["yonu"]))
    print("\nORTALAMALAR (bp/ödeme):")
    print("  gelir  %+8.2f\n  fiyat  %+8.2f\n  %s\n  TOPLAM %+8.2f"
          % (OLCUM["gelir"], OLCUM["fiyat"], "-" * 18, GOTURME))
    print("  maliyet%+8.2f\n  NET    %+8.2f  medyan %+.2f  net>0 %%%.1f"
          % (OLCUM["maliyet"], OLCUM["net"], OLCUM["net_medyan"],
             OLCUM["net_pozitif_pct"]))
    print("  -> götürüyor mu: %s | ölçekten bağımsız mı (madde 214 ile): %s"
          % (funding_fiyati_goturuyor_mu(), goturme_olcekten_bagimsiz_mi()))
    print("\nGELİR DİLİMLERİ:")
    print("  dilim      |     n | gelir  | fiyat   | NET")
    for a, u in sorted(DILIM, key=lambda x: x[0]):
        n, g, f, net, _ = DILIM[(a, u)]
        print("  %4.0f-%-5s | %5d | %+6.1f | %+7.2f | %+7.2f"
              % (a, u if u else "+", n, g, f, net))
    print("  -> doz-tepki monoton mu: %s | uçta fiyat geliri AŞIYOR mu: %s"
          % (doz_tepki_monoton_mu(), uc_funding_pahali_mi()))
    print("\nDOLUM TÜRÜ (maker dolum oranı %%%.1f):" % OLCUM["maker_dolum_pct"])
    for t, (n, f, net) in DOLUM.items():
        print("  %-16s n=%6d | fiyat %+7.2f | NET %+7.2f" % (t, n, f, net))
    print("  -> maker dolumu TERS SEÇİLİMİN kendisi mi: %s"
          % maker_dolumu_ters_secilim_mi())
    print("\nKOL DÜZEYİ (PAY=%.2f, MAKS=%d):" % (PAY, MAKS))
    for d, (y, s, dd) in KOL.items():
        print("  %-9s yıllık %+8.2f%% | Sharpe %+7.3f | maks düşüş %+7.2f%%"
              % (d, y, s, dd))
    print("\nÜÇ ÖN KAYITLI EŞİK:")
    print("  1) ödeme başına NET > 0        : %+.2f bp -> %s"
          % (OLCUM["net"], "GEÇTİ" if esik_1_net() else "RED"))
    print("  2) kol Sharpe >= %.1f (madde 271): %+.3f -> %s"
          % (KOL_TABANI, KOL["tam"][1], "GEÇTİ" if esik_2_sharpe() else "RED"))
    print("  3) iki alt dönemde de pozitif  : %+.3f / %+.3f -> %s"
          % (KOL["2022-24"][1], KOL["2025-26"][1],
             "GEÇTİ" if esik_3_iki_donem() else "RED"))
    print("  -> kol açılır mı: %s | her yıl negatif mi: %s"
          % (kol_acilir_mi(), her_yil_negatif_mi()))
    print("\nMADDE 166 (+%%%.1f/yıl, Sharpe %.2f): kendi rakamıyla madde 271'in"
          " tabanını geçer miydi: %s"
          % (MADDE_166["yillik"], MADDE_166["sharpe"],
             madde_166_kendi_rakamiyla_gecer_miydi()))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
