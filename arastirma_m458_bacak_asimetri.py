#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 458 — BACAK ASİMETRİSİ 4 LONG / 3 SHORT (madde 457'nin tutarlı tek adayı) ve birleşimler.

Madde 457: N43 IS +7,8 / OOS +21,2 puan, Sharpe 3,44 → 3,50, BTC betası −0,026 (yön bahsi değil).
Long taraf carry motoru (madde 214: long kârının %73'ü funding), short taraf dönüş hasadı; daha az ama
aynı büyüklükte short bacak short'u daha seçici yapar. Buyukluk ağırlığı eşit oynaklıkta kaldıraçtan
KÖTÜ (−47/−101 puan) → elendi.
KOLLAR (taban T60 + 24 sa stop, 2.000 $): N33, N42, N43AK0 (+ akış 0), N43HL6 (+ long havuz 6) ·
N43 3.500 $ D2.
ÖN KAYIT: N43 3.500 $'da da tabanı geçer (yıllık >= +5, Sharpe >= taban) ve N42 ile N33'ten en az biri
de tabanı geçerse → "N43 CANLIYA ADAY" (madde 375 protokolüne).
"""
import sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
A.KOLLAR = {"EN33": ({**T, "N_L": "3", "N_S": "3"}, 4, {2000: M.D8}),
            "EN42": ({**T, "N_L": "4", "N_S": "2"}, 4, {2000: M.D8}),
            "EN43AK0": ({**T, "N_L": "4", "N_S": "3", "AKIS": "0"}, 4, {2000: M.D8}),
            "EN43HL6": ({**T, "N_L": "4", "N_S": "3", "HAVUZ_L": "6", "HAVUZ_S": "4"}, 4, {2000: M.D8}),
            "EN43": ({**T, "N_L": "4", "N_S": "3"}, 4, {3500: M.D2}),
            "KD24_45T2": (T, 4, {3500: M.D2})}
A.SEVIYE = (2000, 3500)
_o = A.tek
A.tek = lambda kol, sev, h: (f"M357_{kol}_{sev}_{h}", "atlandi") if sev not in A.KOLLAR[kol][2] else _o(kol, sev, h)


def seri(ad, sev=2000):
    return (M.gunluk(f"M357_{ad}_{sev}_0") + M.gunluk(f"M357_{ad}_{sev}_1")) / 2


def analiz():
    r = {}
    for sev, kollar in ((2000, ["KD24_45T2", "EN43", "EN33", "EN42", "EN43AK0", "EN43HL6"]), (3500, ["KD24_45T2", "EN43"])):
        print(f"\n=== {sev} $ ===")
        for kol in kollar:
            g = seri(kol, sev); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
            sh = g.mean() / g.std() * np.sqrt(365.25); r[(kol, sev)] = (o, sh)
            print(f"{kol:10s} yillik {o['yil']:+7.1f} IS {K.YIL(IS):+7.1f} OOS {K.YIL(OOS):+7.1f} Sh {sh:.2f} dd {o['dd']:6.1f} "
                  f"en kotu {o['enkotu']:6.2f} -%5 alti {o['g5']} Tem-Eyl26 {o['son']:+.1f}")
    b35, s35 = r[("KD24_45T2", 3500)]; n35, sn35 = r[("EN43", 3500)]
    ok35 = n35["yil"] - b35["yil"] >= 5 and sn35 >= s35
    b2, s2 = r[("KD24_45T2", 2000)]
    kom = any(r[(k, 2000)][0]["yil"] > b2["yil"] for k in ("EN42", "EN33"))
    print(f"\nHUKUM: 3.500 $ {'TUTUYOR' if ok35 else 'TUTMUYOR'}, komsu {'VAR' if kom else 'YOK'} -> {'N43 CANLIYA ADAY' if ok35 and kom else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
