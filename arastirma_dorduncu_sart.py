#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 272 — 4. ŞARTIN ARKASINDAKİ ODA: likidasyon ölçüldüğü için açıldı.

AKIL YÜRÜTME (kullanıcı "daha akıllı olmaya çalış" dedi; haklıydı)
-----------------------------------------------------------------
50 turdur kitaba bir şey EKLEMEYE çalıştım. Madde 271 bunun neden
işlemediğini tek sayıyla söyledi: kolun Sharpe tabanı ~1,9 ve denenen
bütün kollar altında. Yani yeni kol arayışı aritmetik olarak kapalı.

Ama aynı hafta başka bir şey oldu: **madde 266 likidasyonu ÖLÇTÜ.** Ve
4. şartın gerekçesi tam olarak şuydu (madde 225): *"kitap şu an
kaldıraçsız ve motor likidasyonu hiç modellemiyor → kıyas, modellenen
getiriyi MODELLENMEYEN tehlikeye karşı fiyatlıyor."* O tehlike artık
modellenmiş. Madde 271'in kendi yasası gereği (*"bir red gerekçesi
geçersizleşirse eksen yeniden açılır"*) 4. şarta çarpmış adaylar
yeniden açılmak ZORUNDA.

4. şarta çarpanlar: rezerv 0,30 (1,13x) · rezerv 0,40 (1,30x) ·
merdiven %20 ×1/2 (1,08x) · %20 ×1/3 (1,05x) · %10 ×1/3 (1,13x).

MERDİVEN AÇILMADI — İKİ ŞARTTAN DÜŞÜYOR
---------------------------------------
Madde 235 merdiveni yalnız 4. şarttan değil, **şart 1'den de**
düşürmüştü (22-24 Sharpe düz, −0,000..−0,018) ve eşit riskteki
üstünlüğü **yazı-tura** (%58,5). Madde 266 yalnız 4. şartın gerekçesini
yanıtlıyor; diğer iki engel yerinde. Merdiven KAPALI kaldı.

REZERV AÇILDI — ÜÇ ŞARTI GEÇMİŞTİ, BOOTSTRAP DESTEKLİYORDU
----------------------------------------------------------
Madde 225: rezerv 0,30 ve 0,40 "eski ÜÇ şartın ÜÇÜNÜ DE geçti (projede
ilk kez)" ve bootstrap destekledi (Δeşit-risk +1,1 / +2,4 puan, P %83,6
/ %83,0). Tek engel 4. şarttı.

BUGÜNÜN YÜZEYİNDE YENİDEN ÖLÇÜM (motor, faz ortalaması)
-------------------------------------------------------
    rezerv   yıllık   Sharpe(motor)  düşüş    22-24   25-26
    0,20     +112,35     3,115       −14,7    2,980   3,315   (kontrol)
    0,30      +96,35     3,125       −13,0    2,985   3,335
    0,40      +81,20     3,135       −11,3    2,995   3,355
Madde 225'in tablosuyla birebir (0,1-0,2 puan içinde).

AMA BİR AYRIM ÇIKTI: MOTOR SHARPE'I ≠ GÜNLÜK SHARPE
---------------------------------------------------
Aynı seriler GÜNLÜK getiriye çevrilince:
    kontrol      Sharpe 2,941 · 22-24 2,463 · 25-26 3,384 · düşüş 14,54
    rezerv 0,40  Sharpe 2,939 · 22-24 2,458 · 25-26 3,379 · düşüş 11,28
Motor "rezerv daha iyi" diyor (3,135 > 3,115), günlük seri "EŞİT" diyor
(2,939 ≈ 2,941; iki dönemde de −0,004/−0,005). **Madde 225'in 1. şart
geçişi MOTOR Sharpe'ındandı.** Sebep mekanizmada: rezerv 4 saatlik
oynaklığı günlük oynaklıktan daha çok azaltıyor — madde 235'in merdiven
için yazdığı şeyin aynısı (*"oynaklığı düşüşten daha çok azaltıyor"*).
Bu, projenin üç kez düştüğü motor/günlük Sharpe tuzağının dördüncü hâli.

KARAR KURALI, GÜNLÜK SERİYLE
----------------------------
    [RED] iki dönemde Sharpe   22-24 −0,004 · 25-26 −0,005  (DÜZ, gürültü)
    [OK ] düşüş toleransı      −11,28 vs −14,54 (3,26 puan İYİ)
    [OK ] eşit riskte getiri   +%114,4 vs +%112,5 (**+2,0 puan**) [1,298x]
    [RED] kaldıraç             1,298x -> madde 149 tablosuna karşı karar

BOOTSTRAP (bugünün günlük serisi, 20 günlük blok, B=4.000)
----------------------------------------------------------
    Δeşit-risk getiri  ort **+2,28 puan**  **P(>0) %81,1**   <- çıtanın üstünde
    ΔSharpe            ort +0,0021  P(>0) %54,5              <- sıfırdan ayırt edilemez
    gereken kaldıraç   ort 1,298x  p95 1,331x

LİKİDASYON PAYI (madde 266'nın formülü, mmr %1)
-----------------------------------------------
1,298x'te likidasyon eşiği **−%76,0** kaldıraçsız hareket. Rezerv 0,40'ın
o kaldıraçta gerçekleşen maksimum düşüşü %14,53, gün içi karşılığı
~%21,6 (madde 266'nın 1,49 büyütmesi). Madde 266'nın ölçtüğü EN KÖTÜ iki
aylık yol (−%41,41) bile **likide etmiyor.** Yani 4. şartın gerekçesi bu
kaldıraç seviyesinde ÖLÇÜMLE karşılanıyor.

KALDIRACIN KENDİ İCRA BEDELİ — KAZANCIN BİR KISMINI YİYOR
---------------------------------------------------------
Madde 265: icra sapması 1x'te **0,79 puan/yıl**. Devir brütle
ölçeklendiği için 1,298x'te **1,03 puan** olur -> ek maliyet 0,24 puan.

    eşit-riskte brüt kazanç   +2,28 puan   (P %81,1)
    kaldıracın icra bedeli    −0,24 puan
    **NET                     +2,04 puan**

Yani dürüst okuma: **+%111,7 -> +%113,7.**

HÜKÜM
-----
Bu, projenin en güçlü adayı ve artık ESASLI bir engeli yok: şart 2 ve 3
geçiyor, bootstrap çıtanın üstünde (%81,1), likidasyon ölçülüp
bağlayıcı olmadığı görüldü. Şart 1 "düz" (−0,004) — katı eşitsizlik
olarak RED ama fark gürültü. **AMA KAZANDIRDIĞI ŞEY +2,0 PUAN**, yani
madde 230'un tarif ettiği platonun genişliği kadar.

**Bu bir PARAMETRE kararı değil, bir KALDIRAÇ kararıdır** ve kullanıcıya
aittir: kitabı 1,30x brütle çalıştırmayı kabul etmek, ölçülmemiş her
riski de 1,3 ile çarpmak demektir. AYAR DEĞİŞTİRİLMEDİ; ölçülmüş bir
SEÇENEK olarak kayda geçti.
"""
from __future__ import annotations

# 4. şarta çarpmış adaylar ve durumları
DORDUNCU_SARTA_CARPANLAR = {
    "rezerv 0,30": {"kaldirac": 1.13, "diger_engel": None},
    "rezerv 0,40": {"kaldirac": 1.30, "diger_engel": None},
    "merdiven %20 x1/2": {"kaldirac": 1.08,
                          "diger_engel": "sart 1 (22-24 duz) + esit-risk yazi-tura %58,5"},
    "merdiven %20 x1/3": {"kaldirac": 1.05, "diger_engel": "ayni"},
    "merdiven %10 x1/3": {"kaldirac": 1.13, "diger_engel": "ayni"},
}

MOTOR = {   # rezerv -> (yillik, sharpe_motor, dusus, erken, gec)
    0.20: (112.35, 3.115, -14.7, 2.980, 3.315),
    0.30: (96.35, 3.125, -13.0, 2.985, 3.335),
    0.40: (81.20, 3.135, -11.3, 2.995, 3.355),
}
GUNLUK = {  # ayni seriler GUNLUK getiriye cevrilince
    "kontrol": {"getiri": 112.46, "sharpe": 2.941, "erken": 2.463,
                "gec": 3.384, "dusus": 14.54},
    "rezerv40": {"getiri": 81.15, "sharpe": 2.939, "erken": 2.458,
                 "gec": 3.379, "dusus": 11.28},
}
ESIT_RISK = {"kaldirac": 1.298, "getiri": 114.45, "fark_puan": 1.99}
BOOTSTRAP = {"d_esitrisk_ort": 2.28, "d_esitrisk_P": 81.1,
             "d_sharpe_ort": 0.0021, "d_sharpe_P": 54.5,
             "kaldirac_ort": 1.298, "kaldirac_p95": 1.331}
MADDE_225_BOOTSTRAP = {0.30: (1.1, 83.6), 0.40: (2.4, 83.0)}

LIKIDASYON = {"g": 1.298, "esik_mmr1_pct": -76.0,
              "gerceklesen_dusus_pct": 14.53, "gun_ici_pct": 21.63,
              "madde266_en_kotu_kuyruk_pct": -41.41, "likide_eder": False}

ICRA = {"sapma_1x_puan": 0.79, "sapma_130x_puan": 1.03, "ek_maliyet_puan": 0.24}
NET_KAZANC_PUAN = BOOTSTRAP["d_esitrisk_ort"] - ICRA["ek_maliyet_puan"]
DURUST_OKUMA = {"kontrol": 111.7, "aday": 113.7}
GUC_CITASI = 80.0


def merdiven_acildi_mi() -> bool:
    """Madde 266 merdivenin engelini kaldırdı mı? HAYIR - iki şart daha var."""
    return DORDUNCU_SARTA_CARPANLAR["merdiven %20 x1/2"]["diger_engel"] is None


def rezerv_tek_engeli_kaldirac_miydi() -> bool:
    return DORDUNCU_SARTA_CARPANLAR["rezerv 0,40"]["diger_engel"] is None


def motor_gunluk_celiskisi() -> dict:
    """Motor Sharpe'ı rezervi iyi, günlük Sharpe'ı EŞİT gösteriyor."""
    return {
        "motor_fark": round(MOTOR[0.40][1] - MOTOR[0.20][1], 4),
        "gunluk_fark": round(GUNLUK["rezerv40"]["sharpe"]
                             - GUNLUK["kontrol"]["sharpe"], 4),
        "celiski": (MOTOR[0.40][1] > MOTOR[0.20][1]
                    and GUNLUK["rezerv40"]["sharpe"] <= GUNLUK["kontrol"]["sharpe"]),
    }


def esit_risk_saglam_mi() -> bool:
    return BOOTSTRAP["d_esitrisk_P"] >= GUC_CITASI


def sharpe_farki_gurultu_mu() -> bool:
    return BOOTSTRAP["d_sharpe_P"] < 60.0


def likidasyon_baglayici_mi() -> bool:
    return LIKIDASYON["likide_eder"]


def net_kazanc() -> float:
    return round(NET_KAZANC_PUAN, 2)


def plato_icinde_mi(plato_puan: float = 5.0) -> bool:
    """Kazanç madde 230'un plato genişliğinin içinde mi?"""
    return net_kazanc() < plato_puan


def hukum() -> str:
    return ("Rezerv 0,40 @%.3fx: esit-riskte +%.2f puan (P %%%.1f, citanin "
            "ustunde), likidasyon BAGLAYICI DEGIL (esik %%%.1f), icra bedeli "
            "-%.2f puan -> NET +%.2f puan. Sart 1 DUZ (-0,004, gurultu). "
            "Bu bir KALDIRAC kararidir, kullaniciya ait. AYAR DEGISTIRILMEDI."
            % (ESIT_RISK["kaldirac"], BOOTSTRAP["d_esitrisk_ort"],
               BOOTSTRAP["d_esitrisk_P"], LIKIDASYON["esik_mmr1_pct"],
               ICRA["ek_maliyet_puan"], net_kazanc()))


def yaz() -> None:
    print("MADDE 272 — 4. ŞARTIN ARKASINDAKİ ODA\n")
    print("4. şarta çarpmış adaylar:")
    for ad, d in DORDUNCU_SARTA_CARPANLAR.items():
        print("  %-20s %.2fx  %s" % (ad, d["kaldirac"],
                                     d["diger_engel"] or "(tek engeli kaldıraçtı)"))
    print("\n  merdiven açıldı mı: %s" % merdiven_acildi_mi())
    print("  rezervin tek engeli kaldıraç mıydı: %s"
          % rezerv_tek_engeli_kaldirac_miydi())
    print("\nMOTOR SHARPE (faz ortalaması):")
    for r in sorted(MOTOR):
        v = MOTOR[r]
        print("  rezerv %.2f  yıllık %+7.2f  Sh %.3f  düşüş %+6.1f" % (r, v[0], v[1], v[2]))
    c = motor_gunluk_celiskisi()
    print("\nMOTOR vs GÜNLÜK: motor farkı %+.4f · günlük farkı %+.4f · çelişki: %s"
          % (c["motor_fark"], c["gunluk_fark"], c["celiski"]))
    print("\nEŞİT RİSK: %.3fx -> +%%%.2f (kontrol +%%%.2f) fark %+.2f puan"
          % (ESIT_RISK["kaldirac"], ESIT_RISK["getiri"],
             GUNLUK["kontrol"]["getiri"], ESIT_RISK["fark_puan"]))
    print("BOOTSTRAP: Δeşit-risk %+.2f puan P %%%.1f (sağlam: %s) · ΔSharpe "
          "%+.4f P %%%.1f (gürültü: %s)"
          % (BOOTSTRAP["d_esitrisk_ort"], BOOTSTRAP["d_esitrisk_P"],
             esit_risk_saglam_mi(), BOOTSTRAP["d_sharpe_ort"],
             BOOTSTRAP["d_sharpe_P"], sharpe_farki_gurultu_mu()))
    print("\nLİKİDASYON @%.3fx: eşik %%%.1f · gerçekleşen düşüş %%%.2f · gün içi "
          "~%%%.2f · madde 266'nın en kötü kuyruğu (%%%.2f) likide eder mi: %s"
          % (LIKIDASYON["g"], LIKIDASYON["esik_mmr1_pct"],
             LIKIDASYON["gerceklesen_dusus_pct"], LIKIDASYON["gun_ici_pct"],
             LIKIDASYON["madde266_en_kotu_kuyruk_pct"],
             "EVET" if likidasyon_baglayici_mi() else "HAYIR"))
    print("\nİCRA BEDELİ: 1x %.2f puan -> %.3fx %.2f puan (ek %.2f)"
          % (ICRA["sapma_1x_puan"], LIKIDASYON["g"],
             ICRA["sapma_130x_puan"], ICRA["ek_maliyet_puan"]))
    print("NET KAZANÇ: %+.2f puan -> dürüst okuma +%%%.1f'ten +%%%.1f'e"
          % (net_kazanc(), DURUST_OKUMA["kontrol"], DURUST_OKUMA["aday"]))
    print("  madde 230'un platosu içinde mi: %s" % plato_icinde_mi())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
