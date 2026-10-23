#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 470 — İKİ TARAFLI MERDİVEN ÇEVRESİNDE İNCE TARAMA (taban: canlı varsayılan, madde 469).

Taban ZSR15P67: T60 + 24 sa stop + long ⅔ @ +%45 (kalan +%60) + short ⅔ @ −%15 (kalan −%20).
Eksenler birlikte çalışınca en iyi noktalar kaymış olabilir. Her kol TEK değişiklik:
  long kademe 0,40 / 0,50 · short kademe 0,12 / 0,17 · pay 0,75 / 0,80 · son short TP 0,25 ·
  son long TP 0,50 / 0,70.
ÖN KAYIT: IS >= +8, OOS >= 0, eşit oynaklıkta >= +8 → madde 471 protokol; yoksa taban tepede.
"""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2", "MERD_ESIK": "0.45", "MERD_PAY": "0.667", "MERDS_ESIK": "0.15"}
DEG = {"L40": {"MERD_ESIK": "0.40"}, "L50": {"MERD_ESIK": "0.50"}, "S12": {"MERDS_ESIK": "0.12"},
       "S17": {"MERDS_ESIK": "0.17"}, "P75": {"MERD_PAY": "0.75"}, "P80": {"MERD_PAY": "0.80"},
       "TS25": {"TPS": "0.25"}, "TL50": {"TPL": "0.50"}, "TL70": {"TPL": "0.70"}}
A.KOLLAR = {f"W{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
TABAN = "ZSR15P67"


def analiz():
    b = K.seri(TABAN); bIS, bOOS = b[b.index < "2025-01-01"], b[b.index >= "2025-01-01"]
    print(f"{'kol':10s} {'yillik':>7s} {'IS':>7s} {'OOS':>7s} {'Sh':>5s} {'dd':>6s} {'enkotu':>7s} {'-5%':>4s} {'TemEyl':>7s} {'esitVol':>8s}")
    for ad in [TABAN] + list(A.KOLLAR):
        g = K.seri(ad); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        f = o["yil"] - K.YIL(b * (g.std() / b.std()))
        dIS, dOOS = K.YIL(IS) - K.YIL(bIS), K.YIL(OOS) - K.YIL(bOOS)
        h = "ADAY" if ad != TABAN and dIS >= 8 and dOOS >= 0 and f >= 8 else ""
        print(f"{ad:10s} {o['yil']:+7.1f} {K.YIL(IS):+7.1f} {K.YIL(OOS):+7.1f} {g.mean()/g.std()*np.sqrt(365.25):5.2f} {o['dd']:6.1f} "
              f"{o['enkotu']:7.2f} {o['g5']:4d} {o['son']:+7.1f} {f:+8.1f} {h}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
