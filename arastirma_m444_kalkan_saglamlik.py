#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 444 — KÖTÜ GÜN KALKANININ SAĞLAMLIĞI (madde 443'ün devamı).

Madde 443: long felaket stop'u −%40 (L40) T60'ın en kötü gününü −8,63 → −5,94 indirdi, −%5 altı gün
9 → 6, yıllık maliyet ~14 puan; L40 + coin tavanı %8 −%5 altı günü 1'e indirdi (~52 puan). Ölçüt
sonradan seçildi → komşuluk ve ikinci seviye ile sınanır.
KOLLAR: L35, L45 (2.000 $) · L40 3.500 $ D2 · L40C10, L40C09 (2.000 $) · L40K03 (rezerv coin payı
tavanı KAP 0,05 → 0,03: short yoğunlaşmasını rezervden kesmek).
ÖN KAYIT: L35/L40/L45 üçü de en kötü günü >= %25 iyileştirip yıllık maliyeti <= 20 puan tutarsa
"long felaket stop'u PLATO" (canlıya eklenebilir); 3.500 $'da da en kötü gün >= %20 iyileşmeli.
"""
import sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"
T = K.T60
A.KOLLAR = {"KL35": ({**T, "SLL": "0.35"}, 4, {2000: M.D8}), "KL45": ({**T, "SLL": "0.45"}, 4, {2000: M.D8}),
            "KL40C10": ({**T, "SLL": "0.40", "CAP_ORTAK": "0.10"}, 4, {2000: M.D8}),
            "KL40C09": ({**T, "SLL": "0.40", "CAP_ORTAK": "0.09"}, 4, {2000: M.D8}),
            "KL40K03": ({**T, "SLL": "0.40", "KAP": "0.03"}, 4, {2000: M.D8}),
            "KL40": ({**T, "SLL": "0.40"}, 4, {3500: M.D2})}
A.SEVIYE = (2000, 3500)
_orj_tek = A.tek
def _tek(kol, sev, h):
    if sev not in A.KOLLAR[kol][2]:
        return f"M357_{kol}_{sev}_{h}", "atlandi"
    return _orj_tek(kol, sev, h)
A.tek = _tek


def seri(ad, sev=2000):
    return (M.gunluk(f"M357_{ad}_{sev}_0") + M.gunluk(f"M357_{ad}_{sev}_1")) / 2


def analiz():
    for sev, kollar in ((2000, ["T60", "KL35", "KL40", "KL45", "KL40C10", "KL40C09", "KL40C08", "KL40K03"]), (3500, ["T60", "KL40"])):
        t = seri("T60", sev); b = K.olc(t)
        print(f"\n=== {sev} $ ===")
        for kol in kollar:
            g = seri(kol, sev); o = K.olc(g); k = o["enkotu"] / b["enkotu"]
            print(f"{kol:8s} yillik {o['yil']:+7.1f} (maliyet {o['yil']-b['yil']:+6.1f}) dd {o['dd']:6.1f} en kotu {o['enkotu']:6.2f} "
                  f"(iyilesme %{(1-o['enkotu']/b['enkotu'])*100:4.0f}) p1 {o['p1']:.2f} -%5 alti {o['g5']:2d} -%4 alti {o['g4']:2d} Tem-Eyl26 {o['son']:+.1f}")
    b = K.olc(seri("T60"))
    ok = all((1 - K.olc(seri(k))["enkotu"] / b["enkotu"]) >= 0.25 and (b["yil"] - K.olc(seri(k))["yil"]) <= 20 for k in ("KL35", "KL40", "KL45"))
    b35 = K.olc(seri("T60", 3500)); o35 = K.olc(seri("KL40", 3500))
    ok35 = (1 - o35["enkotu"] / b35["enkotu"]) >= 0.20
    print(f"\nHUKUM: plato {'VAR' if ok else 'YOK'}, 3.500 $ {'TUTUYOR' if ok35 else 'TUTMUYOR'} -> {'LONG FELAKET STOP CANLIYA ADAY' if ok and ok35 else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
