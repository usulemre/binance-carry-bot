#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 463 — LONG MERDİVEN KÂR ALMA KOMŞULUĞU (madde 462'nin tek iyi sonucu).

Madde 462: MR40 (long'un yarısı +%40'ta, kalanı +%60'ta) yıllık +226,2 (taban +216,3), Sharpe 3,65
(3,44), −%5 altı gün 5 (7), eşit oynaklıkta +22,4; ama IS farkı yalnız +2,9 (ön kayıt +8 istiyordu).
Sharpe artışı = aynı riskte daha çok kâr → komşulukla sınanır.
KOLLAR (taban T60 + 24 sa stop): MR35, MR45, MR50 (pay 0,5) · MR40P33, MR40P67 (pay 1/3, 2/3) ·
MR40T70, MR40T80 (kalan +%70 / +%80).
ÖN KAYIT: MR35/MR40/MR45 üçünün de Sharpe'ı tabanı >= 0,10 geçer ve eşit oynaklıkta >= +10 ise
→ "MERDİVEN PLATO" → madde 464 (3.500 $ + protokol).
"""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m460_sinyal_toplulugu as S6

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
DEG = {"MR35": {"MERD_ESIK": "0.35"}, "MR45": {"MERD_ESIK": "0.45"}, "MR50": {"MERD_ESIK": "0.50"},
       "MR40P33": {"MERD_ESIK": "0.40", "MERD_PAY": "0.333"}, "MR40P67": {"MERD_ESIK": "0.40", "MERD_PAY": "0.667"},
       "MR40T70": {"MERD_ESIK": "0.40", "TPL": "0.70"}, "MR40T80": {"MERD_ESIK": "0.40", "TPL": "0.80"}}
A.KOLLAR = {f"X{a}": ({**T, "MERD_PAY": "0.5", **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    S6.A.KOLLAR = {**A.KOLLAR, "XMR30": None, "XMR40": None}
    S6.analiz()
    b = K.seri("KD24_45T2"); sb = b.mean() / b.std() * np.sqrt(365.25)
    ok = True
    for k in ("XMR35", "XMR40", "XMR45"):
        g = K.seri(k); sh = g.mean() / g.std() * np.sqrt(365.25); f = K.olc(g)["yil"] - K.YIL(b * (g.std() / b.std()))
        ok &= (sh - sb >= 0.10) and f >= 10
    print(f"\nHUKUM: merdiven plato {'VAR -> madde 464' if ok else 'YOK -> RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
