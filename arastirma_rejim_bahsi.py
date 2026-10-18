#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 284 — "ERKEN DÖNEM NEDEN VETO ETSİN?" SORUSU ÖLÇÜLDÜ: ŞART 1 BİR
TEKNİKLİK DEĞİL, BİR **REJİM BAHSİ DEDEKTÖRÜ**. VE BAHSİN FİYATI HESAPLANDI.

Kullanıcı madde 282'nin reddini sorguladı: getiri fırlıyor, **25-26 tarafı
bozulmuyor** (γ0,25'te 3,084 vs kontrol 3,076), yalnız 22-24 yıkılıyor.
Meşru soru: 22-24 bayat bir dönem mi, yoksa GERİ DÖNEBİLECEK bir rejim mi?

Ve kullanıcının sezgisi KISMEN DOĞRU çıktı: 25-26 rejiminde büyüklük
ağırlığı doz ölçütünde de KAZANIYOR. Red yine de ayakta — ama artık bir
şart ihlali olarak değil, **fiyatı ölçülmüş bir bahis** olarak.

BULGU 1 — DOZ ÖLÇÜTÜ HER DÖNEMDE AYRI
-------------------------------------
Karıştırma p95, −%30 tolerans, her pencere kendi içinde çözüldü:

    aday          TAM           22-24          25-26
    g0 (kontrol)  1,465x/+192   1,576x/+179    1,468x/**+248**
    γ0,25         1,257x/+184   1,376x/+151    1,221x/**+268**
    γ0,5 kırp2    1,118x/+174   1,237x/+135    1,078x/**+267**
    γ0,5          1,058x/+163   1,176x/+122    1,021x/+262
    γ1,0          0,862x/+138   0,962x/ +93    0,847x/+248
    γ2,0          0,766x/+128   0,830x/ +79    0,772x/+251

**(B) 25-26 rejimi SÜRERSE kazanç:** γ0,25 **+20,36** · γ0,5kırp2 +19,61
· γ0,5 +14,64 · γ1,0 +0,48 · γ2,0 +3,17 puan.
**(C) 22-24 rejimi GERİ DÖNERSE kayıp:** γ0,25 **−27,42** · γ0,5kırp2
−43,99 · γ0,5 −56,85 · γ1,0 −85,52 · γ2,0 −99,57 puan.

BULGU 2 — BAHSİN FİYATI: BAŞABAŞ REJİM OLASILIĞI
------------------------------------------------
    p* = |kayıp| / (kazanç + |kayıp|)

    aday         kazanç   kayıp     p* (rejimin SÜRME olasılığı gereken)
    **γ0,25**    +20,36   −27,42        **%57,4**
    γ0,5 kırp2   +19,61   −43,99          %69,2
    γ0,5         +14,64   −56,85          %79,5
    γ2,0          +3,17   −99,57          %96,9
    γ1,0          +0,48   −85,52          %99,4

En iyi aday (γ0,25) bile **yüksek prim rejiminin %57,4 olasılıkla
süreceğine** inanmayı gerektiriyor. Ve madde 231'in ölçümü tam bu
olasılığa karşı konuşuyor: değişim **TREND değil SEVİYE atlaması**
(2022Q3-2024Q4 ort −%0,493/gün vs 2025Q1+ −%1,855, 3,8 kat,
Mann-Whitney p=0,0005; model kıyası artık kareler 4,027 trend vs
**2,115 seviye**) ve o maddenin kendi hükmü: *"trend devam etmeyi,
rejim GERİ DÖNMEYİ düşündürür."*

BULGU 3 — ÜSTELİK 25-26 KAZANCININ KENDİSİ DE KANIT DEĞİL
---------------------------------------------------------
Madde 276'nın dersi (nokta değil ARALIK) 25-26 kazancına uygulandı
(blok bootstrap, blok 21, ~600 günlük pencere):

    aday         kazanç p5    medyan    p95       P(>0)
    γ0,25         −24,09      +17,95   +95,92    **%71,7**
    γ0,5 kırp2    −81,27      +28,74  +194,55    **%71,7**

**P(>0) = %71,7 → projenin %80 kanıt barının ALTINDA.** 20 aylık bir
pencere +20 puanı kurmak için yeterli değil; madde 231 bunu zaten
söylemişti (*"tek bir 6 ay az bilgi taşır"*, yarım yıllık Sharpe
yayılımı 0,494-4,802).

BİRLEŞİK HÜKÜM
--------------
γ0,25'i kabul etmek İKİ şeye birden inanmayı gerektiriyor:
  1. 25-26 kazancının gerçek olduğuna — ölçülen **%71,7** (bar %80)
  2. Rejimin sürdüğüne — gereken **%57,4**, ve madde 231 TERSİNE eğiliyor
Kabaca bağımsız sayılırsa birleşik olasılık **≈ %41**. Yani bu bir yazı
tura ve iki girdinin ikisi de projenin kendi barlarının yanlış tarafında.

**RED AYAKTA. Ayar DEĞİŞMEDİ.** Ama red artık "şart 1'den düştü" değil:
**fiyatı %57,4 olan, kanıtı %71,7 olan bir rejim bahsi** — ve bu, karar
verilebilir bir ifade.

DERS — YENİ VE YENİDEN KULLANILABİLİR YÖNTEM
--------------------------------------------
**Bir aday bir alt dönemde geçip diğerinde düşüyorsa şart 1'i ANMAKLA
yetinme: BAHSİ FİYATLA.** Üç sayı yeter:
  * kazanç (yeni rejim sürerse) ve kayıp (eski rejim dönerse) —
    her pencerede AYRI doz çözümüyle,
  * başabaş rejim olasılığı p* = |kayıp|/(kazanç+|kayıp|),
  * kazancın kendi örnekleme P(>0)'ı.
Böylece **şart 1'in ne İŞE yaradığı da görünüyor: o bir keyfî filtre
değil, adayın bir REJİM BAHSİ olduğunun dedektörü.** Geçememek "kötü"
demek değil; "bedeli şu" demek. Bedeli söylenebilen bir red, kullanıcının
kendi kararını verebileceği bir reddir.
"""
from __future__ import annotations

TOLERANS = 30.0

# aday -> {donem: (brut, net)}
DOZ = {
    "g0_k0": {"TAM": (1.465, 192.44), "22-24": (1.576, 178.54), "25-26": (1.468, 247.74)},
    "g0.25_k0": {"TAM": (1.257, 184.44), "22-24": (1.376, 151.12), "25-26": (1.221, 268.10)},
    "g0.5_k2.0": {"TAM": (1.118, 173.55), "22-24": (1.237, 134.55), "25-26": (1.078, 267.34)},
    "g0.5_k0": {"TAM": (1.058, 163.33), "22-24": (1.176, 121.69), "25-26": (1.021, 262.37)},
    "g1.0_k0": {"TAM": (0.862, 138.08), "22-24": (0.962, 93.02), "25-26": (0.847, 248.21)},
    "g2.0_k0": {"TAM": (0.766, 128.45), "22-24": (0.830, 78.97), "25-26": (0.772, 250.90)},
}
KONTROL = "g0_k0"

KAZANC = {"g0.25_k0": 20.36, "g0.5_k2.0": 19.61, "g0.5_k0": 14.64,
          "g1.0_k0": 0.48, "g2.0_k0": 3.17}
KAYIP = {"g0.25_k0": -27.42, "g0.5_k2.0": -43.99, "g0.5_k0": -56.85,
         "g1.0_k0": -85.52, "g2.0_k0": -99.57}

# aday -> (p5, medyan, p95, P(>0))  — 25-26 kazancinin ornekleme araligi
ORNEKLEME = {
    "g0.25_k0": (-24.09, 17.95, 95.92, 71.7),
    "g0.5_k2.0": (-81.27, 28.74, 194.55, 71.7),
}
KANIT_BARI = 80.0            # projenin P(>0) bari

MADDE_231 = {
    "dusuk_rejim_gunluk": -0.493, "yuksek_rejim_gunluk": -1.855, "kat": 3.8,
    "mann_whitney_p": 0.0005, "artik_trend": 4.027, "artik_seviye": 2.115,
    "hukum": "trend DEVAM etmeyi, rejim GERI DONMEYI dusundurur",
    "yarim_yil_sharpe_yayilim": (0.494, 4.802),
}


def kazanc(aday: str) -> float:
    return DOZ[aday]["25-26"][1] - DOZ[KONTROL]["25-26"][1]


def kayip(aday: str) -> float:
    return DOZ[aday]["22-24"][1] - DOZ[KONTROL]["22-24"][1]


def yeni_rejimde_kazaniyor_mu(aday: str = "g0.25_k0") -> bool:
    """Kullanicinin sezgisi: 25-26'da gercekten kazaniyor mu?"""
    return kazanc(aday) > 0


def kac_aday_yeni_rejimde_kazaniyor() -> int:
    return sum(1 for a in KAZANC if kazanc(a) > 0)


def basabas_rejim_olasiligi(aday: str) -> float:
    g, k = kazanc(aday), abs(kayip(aday))
    return 100.0 * k / (g + k) if (g + k) > 0 else 100.0


def en_ucuz_bahis() -> tuple:
    a = min(KAZANC, key=basabas_rejim_olasiligi)
    return a, basabas_rejim_olasiligi(a)


def bahis_elli_ustu_mu() -> bool:
    """En ucuz bahis bile rejimin SURMESINE mi bahis?"""
    return en_ucuz_bahis()[1] > 50.0


def rejim_mi_trend_mi() -> str:
    return ("seviye" if MADDE_231["artik_seviye"] < MADDE_231["artik_trend"]
            else "trend")


def madde231_tersine_mi_egiliyor() -> bool:
    """Seviye atlamasi -> geri donus; yani bahsin aleyhine."""
    return rejim_mi_trend_mi() == "seviye"


def kazanc_kaniti_yeterli_mi(aday: str = "g0.25_k0") -> bool:
    return ORNEKLEME[aday][3] >= KANIT_BARI


def kazanc_araligi_sifiri_kapsiyor_mu(aday: str = "g0.25_k0") -> bool:
    p5, _, p95, _ = ORNEKLEME[aday]
    return p5 < 0 < p95


def birlesik_olasilik(aday: str = "g0.25_k0") -> float:
    """Kabaca bagimsiz: P(kazanc gercek) x P(rejim surer)."""
    return ORNEKLEME[aday][3] / 100.0 * basabas_rejim_olasiligi(aday) / 100.0 * 100.0


def red_ayakta_mi() -> bool:
    return not (kazanc_kaniti_yeterli_mi() and not bahis_elli_ustu_mu())


def sart1_ne_ise_yarar() -> str:
    return ("sart 1 keyfi bir filtre DEGIL: adayin bir REJIM BAHSI "
            "oldugunun DEDEKTORU. Gecememek 'kotu' demek degil, "
            "'bedeli su' demek.")


def hukum() -> str:
    a, p = en_ucuz_bahis()
    return ("Kullanicinin sezgisi KISMEN DOGRU: 25-26 rejiminde %d adayin "
            "%d'i doz olcutunde KAZANIYOR (en iyisi %s, +%.2f puan). Ama "
            "red AYAKTA: en ucuz bahis bile rejimin **%%%.1f** olasilikla "
            "surmesini gerektiriyor ve madde 231 TERSINE egiliyor (SEVIYE "
            "atlamasi, 'rejim geri donmeyi dusundurur'); ustune 25-26 "
            "kazancinin kendi orneklemesi P(>0)=%%%.1f ile %%%.0f barinin "
            "ALTINDA (p5 %+.2f). Birlesik olasilik ~%%%.0f. Ayar DEGISMEDI."
            % (len(KAZANC), kac_aday_yeni_rejimde_kazaniyor(), a, kazanc(a),
               p, ORNEKLEME["g0.25_k0"][3], KANIT_BARI,
               ORNEKLEME["g0.25_k0"][0], birlesik_olasilik()))


def yaz() -> None:
    print("MADDE 284 — ŞART 1 BİR REJİM BAHSİ DEDEKTÖRÜ; BAHSİN FİYATI\n")
    print("DOZ ÖLÇÜTÜ HER DÖNEMDE AYRI (karıştırma p95, −%%%.0f):" % TOLERANS)
    print("  aday        | TAM          | 22-24        | 25-26")
    for a in DOZ:
        d = DOZ[a]
        print("  %-11s | %5.3fx/%+5.0f | %5.3fx/%+5.0f | %5.3fx/%+5.0f"
              % (a, d["TAM"][0], d["TAM"][1], d["22-24"][0], d["22-24"][1],
                 d["25-26"][0], d["25-26"][1]))
    print("\n(B) 25-26 SÜRERSE kazanç | (C) 22-24 DÖNERSE kayıp | BAHSİN FİYATI:")
    print("  aday        | kazanç  | kayıp   | p* (rejimin sürme olasılığı)")
    for a in sorted(KAZANC, key=basabas_rejim_olasiligi):
        print("  %-11s | %+7.2f | %+7.2f | **%%%.1f**"
              % (a, kazanc(a), kayip(a), basabas_rejim_olasiligi(a)))
    a, p = en_ucuz_bahis()
    print("  -> kullanıcının sezgisi doğru mu (25-26'da kazanıyor): %s (%d/%d aday)"
          % (yeni_rejimde_kazaniyor_mu(), kac_aday_yeni_rejimde_kazaniyor(),
             len(KAZANC)))
    print("  -> en ucuz bahis: %s, %%%.1f | yine de %%50 üstü mü: %s"
          % (a, p, bahis_elli_ustu_mu()))
    print("\nMADDE 231 NE DİYOR: değişim %s atlaması (artık kareler trend %.3f"
          " vs seviye %.3f, Mann-Whitney p=%.4f)"
          % (rejim_mi_trend_mi(), MADDE_231["artik_trend"],
             MADDE_231["artik_seviye"], MADDE_231["mann_whitney_p"]))
    print("  \"%s\" -> bahsin TERSİNE mi: %s"
          % (MADDE_231["hukum"], madde231_tersine_mi_egiliyor()))
    print("\n25-26 KAZANCININ ÖRNEKLEME ARALIĞI (madde 276'nın dersi):")
    print("  aday        | p5      | medyan  | p95     | P(>0)")
    for a, v in ORNEKLEME.items():
        print("  %-11s | %+7.2f | %+7.2f | %+7.2f | %%%.1f" % (a, v[0], v[1], v[2], v[3]))
    print("  -> kanıt barı (%%%.0f) geçiliyor mu: %s | aralık sıfırı kapsıyor mu: %s"
          % (KANIT_BARI, kazanc_kaniti_yeterli_mi(),
             kazanc_araligi_sifiri_kapsiyor_mu()))
    print("\nBİRLEŞİK OLASILIK (kazanç gerçek × rejim sürer): ~%%%.0f"
          % birlesik_olasilik())
    print("RED AYAKTA MI: %s" % red_ayakta_mi())
    print("\nŞART 1 NE İŞE YARAR: %s" % sart1_ne_ise_yarar())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
