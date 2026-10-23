#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 466 — ÇIKIŞ MEKANİĞİ 2: short merdiveni, merdiven sonrası başabaş stop, pay 2/3.

Madde 462-465: long merdiveni (½ @ +%45) Sharpe 3,44 → 3,66, protokolde AYAR. Çıkış mekaniği verimli bir
eksen çıktı. Taban: CANLI varsayılan (T60 + 24 sa stop + merdiven 0,45/0,5) = XMR45.
KOLLAR: SR10 / SR12 / SR15 (short'un yarısı −%10/−%12/−%15'te, kalanı −%20'de; yeni MERDS_ESIK) ·
BE (merdiven dolduktan sonra fiyat girişe dönerse kalan kapanır; yeni MERD_BE) · BESR12 · P67 (pay 2/3).
ÖN KAYIT madde 460 ile aynı (IS >= +8, OOS >= 0, eşit oynaklıkta >= +8) — taban XMR45.
"""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2", "MERD_ESIK": "0.45", "MERD_PAY": "0.5"}
DEG = {"SR10": {"MERDS_ESIK": "0.10"}, "SR12": {"MERDS_ESIK": "0.12"}, "SR15": {"MERDS_ESIK": "0.15"},
       "BE": {"MERD_BE": "1"}, "BESR12": {"MERD_BE": "1", "MERDS_ESIK": "0.12"}, "P67": {"MERD_PAY": "0.667"}}
A.KOLLAR = {f"Z{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    b = K.seri("XMR45"); bIS, bOOS = b[b.index < "2025-01-01"], b[b.index >= "2025-01-01"]
    print(f"{'kol':10s} {'yillik':>7s} {'IS':>7s} {'OOS':>7s} {'Sh':>5s} {'dd':>6s} {'enkotu':>7s} {'-5%':>4s} {'TemEyl':>7s} {'esitVol':>8s}")
    for ad in ["XMR45"] + list(A.KOLLAR):
        g = K.seri(ad); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        f = o["yil"] - K.YIL(b * (g.std() / b.std()))
        dIS, dOOS = K.YIL(IS) - K.YIL(bIS), K.YIL(OOS) - K.YIL(bOOS)
        h = "ADAY" if ad != "XMR45" and dIS >= 8 and dOOS >= 0 and f >= 8 else ""
        print(f"{ad:10s} {o['yil']:+7.1f} {K.YIL(IS):+7.1f} {K.YIL(OOS):+7.1f} {g.mean()/g.std()*np.sqrt(365.25):5.2f} {o['dd']:6.1f} "
              f"{o['enkotu']:7.2f} {o['g5']:4d} {o['son']:+7.1f} {f:+8.1f} {h}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
