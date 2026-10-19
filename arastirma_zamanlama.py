#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 264 — "DOĞRU YERDE GİR, DOĞRU YERDE ÇIK, HAFTALIK KÂR".

Kullanıcının üç isteği, üçü de ölçüldü. İkisi KAPALI çıktı, biri ZATEN
VAR ve sayıları burada.

1) GİRİŞ SAATİ — ana kitap için İLK KEZ ölçüldü, FARK YOK
--------------------------------------------------------
Saat etkisi daha önce iki kez ölçülmüştü (madde 197 ve 241) ama ikisi de
kullanıcının AYRI pump kolu içindi; ana kitabın giriş saati hiç
optimize edilmemişti. Motorda bu eksen `FAZ_KAY` ve bugüne dek şansı
ORTALAMAK için kullanıldı, en iyisini SEÇMEK için değil.

Önemli yapısal gerçek: dilimler `REB//FAZ = 2` bar aralıkla açılıyor,
yani 8 saatte bir. 8 saatlik ızgarada 4 saatlik bir kaydırma iki ayrı
hizalama üretir, üçüncüsü yoktur — yani **ana kitabın "giriş saati"
ekseninde seçilebilecek sadece İKİ nokta var** ve ikisi de ölçüldü:

    FAZ_KAY=0 -> tam +%112,3  Sh 3,10  dd −%14,5 | 22-24 +%95,8 | 25-26 +%140,0
    FAZ_KAY=1 -> tam +%112,4  Sh 3,13  dd −%14,9 | 22-24 +%94,0 | 25-26 +%143,6

Fark: **0,1 puan getiri, 0,03 Sharpe.** Yayınlanan sayı ikisinin
harmanı, yani zaten "saat kumarı"ndan arındırılmış. **Seçilecek bir saat
yok** — ve madde 223'ün dersiyle tutarlı: `N_DILIM` bir getiri değil
BELİRLİLİK parametresidir, 15 dilim faz yayılımını 22,6 puandan 2,5
puana indirmişti; bu ölçüm o indirimin bugünkü hâli.

Pump kolundaki saat etkisi ise gerçekti ama kabul edilemedi: madde
241'de 04 UTC (07:00 İstanbul) +%31,7 / Sharpe 0,747 ama **her varyant
2022-24'te NEGATİF** ve tek başına düşüş −%75 ile −%99 arası.

2) ÇIKIŞ / DAHA KISA DÖNGÜ — madde 223 bunu bir KALDIRAÇ KOLU olarak
   ölçmüştü, yani "haftalık kâr" diye kısaltmak bedava değil
--------------------------------------------------------------------
    3 gün tutma -> +%131,8  Sh 3,06  dd −%17,8
    5 gün (şu an) -> +%112,4  Sh 3,10  dd −%14,5
    6 gün tutma -> +%99,8   Sh 3,04  dd −%14,4

Tutma süresi kısaldıkça getiri VE düşüş birlikte büyüyor, **Sharpe
sabit** → bu bir kenar değil doz. Daha fazla getiri isteyen `CARRY_GROSS`
kullanmalı (orada ölçülmüş ve fiyatı yazılı); tutma süresini kısaltmak
aynı riski daha kötü Sharpe'la satın alır.

Ayrıca kârı daha erken realize etmek kitabın mekanizmasına AYKIRI:
madde 236 bacakların %90'ının net −65 puanlık yük, %10'unun (TP ile
kapananların) +114,5 kazandırıp hepsini ödediğini ölçtü. Kazananı erken
kesmek, parayı yapan azınlığı kesmektir.

3) HAFTALIK KÂR — ZATEN VAR, çünkü 15 dilim × 5 gün tutma
---------------------------------------------------------
Dilimler 8 saatte bir açılıp 5 gün sonra kapandığı için **her 8 saatte
bir dilim kapanıyor**; nakit yılda bir değil sürekli realize oluyor.
Kontrol serisinin (1.504 gün) haftalık dağılımı:

    pozitif hafta oranı            %60,6
    medyan hafta                   +%1,06
    ortalama hafta                 +%1,51
    en kötü hafta                  −%8,54      (p5 −%3,01)
    en iyi hafta                   +%14,77     (p95 +%7,90)
    üst üste negatif en uzun seri  6 hafta
    pozitif AY oranı               %86,0  (50 ay)

**Dürüst okuma: haftanın %39'u eksi, ve 6 hafta üst üste eksi gören bir
dönem var.** "Haftalık kâr" bir GARANTİ değil, bir nakit akışı ritmi.

HÜKÜM: giriş saati RED (fark yok) · kısa döngü RED (kaldıraç kolu,
Sharpe sabit) · haftalık nakit akışı ZATEN VAR. AYAR DEĞİŞMEDİ.
"""
from __future__ import annotations

import csv
import os

import numpy as np

KOK = os.path.dirname(os.path.abspath(__file__))

# (1) giriş saati: ana kitabın İKİ hizalaması
FAZ_OLCUM = {
    0: {"getiri": 112.3, "sharpe": 3.10, "dusus": -14.5, "e1": 95.8, "e2": 140.0},
    1: {"getiri": 112.4, "sharpe": 3.13, "dusus": -14.9, "e1": 94.0, "e2": 143.6},
}
# 8 saatlik dilim ızgarasında 4 saatlik kaydırma -> yalnızca 2 hizalama
HIZALAMA_SAYISI = 2
BAR_SAAT = 4
DILIM_ARALIK_SAAT = 8

# (2) tutma süresi (madde 223'ün ölçümü)
TUTMA = {
    3: {"getiri": 131.8, "sharpe": 3.06, "dusus": -17.8},
    5: {"getiri": 112.4, "sharpe": 3.10, "dusus": -14.5},
    6: {"getiri": 99.8, "sharpe": 3.04, "dusus": -14.4},
}

# (3) haftalık nakit akışı
# MADDE 336: zemin yeniden kurulduktan sonra (madde 335) tablo seriden
# yeniden türetildi. Eski kayıt HAFTALIK_KAYIP_ZEMIN'de duruyor.
# Yapısal değişmezler AYAKTA: üst üste en uzun 6 negatif hafta, 50 ay.
# Tek dikkat çeken kayma POZİTİF AY ORANI: %86,0 -> %82,0, yani 50 ayın
# 43'ü değil 41'i artı. Bu 4 puan yapısal bir bozulma DEĞİL; küçük bir
# getiri kayması sınıra yakın iki ayı öbür tarafa atıyor (ay örneklemi
# 50, bir ay = 2 puan). Yine de "ayların %86'sı artı" diye yayınlanan
# başlık artık %82'dir ve belgelerde öyle yazılmalıdır.
HAFTALIK_KAYIP_ZEMIN = {
    "pozitif_oran": 60.6, "medyan": 1.06, "ortalama": 1.51,
    "en_kotu": -8.54, "p5": -3.01, "en_iyi": 14.77, "p95": 7.90,
    "en_uzun_negatif_hafta": 6, "pozitif_ay_oran": 86.0, "ay": 50,
}
HAFTALIK = {
    "pozitif_oran": 60.2, "medyan": 1.01, "ortalama": 1.50,
    "en_kotu": -8.24, "p5": -3.03, "en_iyi": 14.98, "p95": 8.19,
    "en_uzun_negatif_hafta": 6, "pozitif_ay_oran": 82.0, "ay": 50,
}
# MADDE 336: ölçülen fark (yeni − kayıp), puan.
ZEMIN_FARK_HAFTALIK = {
    "pozitif_oran": -0.42, "medyan": -0.05, "ortalama": -0.01,
    "en_kotu": +0.30, "p5": -0.02, "en_iyi": +0.21, "p95": +0.29,
    "en_uzun_negatif_hafta": 0, "pozitif_ay_oran": -4.0, "ay": 0,
}


def _seri():
    yol = os.path.join(KOK, "referans_getiri.csv")
    with open(yol) as f:
        d = list(csv.DictReader(f))
    import pandas as pd
    return pd.Series([float(r["getiri"]) for r in d],
                     index=pd.to_datetime([r["tarih"] for r in d]))


def haftalik_olc() -> dict:
    """HAFTALIK tablosunu seriden yeniden üretir (tek kaynak: madde 262)."""
    import itertools
    g = _seri()
    h = (1.0 + g).resample("W").prod() - 1.0
    a = (1.0 + g).resample("ME").prod() - 1.0
    return {
        "pozitif_oran": float((h > 0).mean()) * 100.0,
        "medyan": float(h.median()) * 100.0,
        "ortalama": float(h.mean()) * 100.0,
        "en_kotu": float(h.min()) * 100.0,
        "p5": float(np.percentile(h, 5)) * 100.0,
        "en_iyi": float(h.max()) * 100.0,
        "p95": float(np.percentile(h, 95)) * 100.0,
        "en_uzun_negatif_hafta": max(
            (len(list(v)) for k, v in itertools.groupby(h <= 0) if k), default=0),
        "pozitif_ay_oran": float((a > 0).mean()) * 100.0,
        "ay": int(len(a)),
    }


def giris_saati_fark_eder_mi(esik_puan: float = 2.0) -> bool:
    """İki hizalama arasındaki fark anlamlı mı? (madde 230'un gürültü bandı)"""
    f = abs(FAZ_OLCUM[0]["getiri"] - FAZ_OLCUM[1]["getiri"])
    return f > esik_puan


def tutma_kaldirac_kolu_mu() -> bool:
    """Tutma süresi bir kenar mı, doz mu? Sharpe sabit kalıyorsa DOZ."""
    sh = [TUTMA[k]["sharpe"] for k in sorted(TUTMA)]
    gt = [TUTMA[k]["getiri"] for k in sorted(TUTMA)]
    dd = [TUTMA[k]["dusus"] for k in sorted(TUTMA)]
    return (max(sh) - min(sh) < 0.10          # Sharpe sabit
            and gt[0] > gt[-1] and dd[0] < dd[-1])   # getiri ve düşüş birlikte


def haftalik_kar_garanti_mi() -> bool:
    """Haftalık kâr bir garanti mi? HAYIR - haftanın %39'u eksi."""
    return HAFTALIK["pozitif_oran"] >= 100.0


def dogrula(tol: float = 0.2) -> bool:
    o = haftalik_olc()
    return all(abs(o[k] - HAFTALIK[k]) < tol for k in
               ("pozitif_oran", "medyan", "ortalama", "en_kotu", "p5",
                "en_iyi", "p95", "pozitif_ay_oran")) \
        and o["en_uzun_negatif_hafta"] == HAFTALIK["en_uzun_negatif_hafta"]


def hukum() -> dict:
    return {"giris_saati": "RED", "kisa_dongu": "RED",
            "haftalik_nakit": "ZATEN VAR"}


def yaz() -> None:
    print("MADDE 264 — GİRİŞ SAATİ / ÇIKIŞ DÖNGÜSÜ / HAFTALIK KÂR\n")
    print("1) GİRİŞ SAATİ (ana kitap, ilk kez ölçüldü)")
    print("   dilimler %d saatte bir açılıyor -> %d saatlik kaydırma yalnız"
          " %d hizalama üretir" % (DILIM_ARALIK_SAAT, BAR_SAAT, HIZALAMA_SAYISI))
    for k in sorted(FAZ_OLCUM):
        v = FAZ_OLCUM[k]
        print("   FAZ_KAY=%d -> +%%%.1f  Sh %.2f  dd %%%.1f | 22-24 +%%%.1f | 25-26 +%%%.1f"
              % (k, v["getiri"], v["sharpe"], v["dusus"], v["e1"], v["e2"]))
    print("   -> fark anlamlı mı: %s (%.1f puan)"
          % (giris_saati_fark_eder_mi(),
             abs(FAZ_OLCUM[0]["getiri"] - FAZ_OLCUM[1]["getiri"])))
    print("\n2) TUTMA SÜRESİ (madde 223)")
    for k in sorted(TUTMA):
        v = TUTMA[k]
        print("   %d gün -> +%%%.1f  Sh %.2f  dd %%%.1f" % (k, v["getiri"],
                                                           v["sharpe"], v["dusus"]))
    print("   -> kaldıraç kolu mu (Sharpe sabit, getiri+düşüş birlikte): %s"
          % tutma_kaldirac_kolu_mu())
    print("\n3) HAFTALIK NAKİT AKIŞI")
    o = haftalik_olc()
    print("   pozitif hafta %%%.1f · medyan +%%%.2f · ortalama +%%%.2f"
          % (o["pozitif_oran"], o["medyan"], o["ortalama"]))
    print("   en kötü hafta %%%.2f (p5 %%%.2f) · en iyi +%%%.2f (p95 +%%%.2f)"
          % (o["en_kotu"], o["p5"], o["en_iyi"], o["p95"]))
    print("   üst üste negatif en uzun: %d hafta · pozitif ay %%%.1f (%d ay)"
          % (o["en_uzun_negatif_hafta"], o["pozitif_ay_oran"], o["ay"]))
    print("   -> garanti mi: %s" % haftalik_kar_garanti_mi())
    print("\nDOĞRULAMA: %s" % ("EVET" if dogrula() else "HAYIR"))
    print("HÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
