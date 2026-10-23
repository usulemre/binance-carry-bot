#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 455 — SHORT TARAFINDA TEK COİN TAVANI (24 sa stop'tan sonra kalan kötü günler).

Madde 454: 24 sa −%45 stop'tan sonra kalan en kötü günler ~−%5,5 ve çoğu SHORT sıkışması (ONDO, FIL,
DOGE, 1000SATS; madde 443: short coin payı %13-16, long'dan büyük). Short stop'ları zararlıydı (madde
443/450). Burada sıkışmayı kesmek yerine tek coine BİRİKEN short payı sınırlanır (CAP_TARAF=short,
yeni düğme; dilimler arası lockstep). Taban: T60 + SLL24 0,45 (TAZE 2).
KOLLAR: CS10 / CS08 / CS06 (short coin tavanı %10 / %8 / %6).
ÖN KAYIT: D24_45T2'ye göre en kötü günü ve −%5 altı günü iyileştirip ek maliyeti <= 6 puan → ADAY.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
DEG = {"CS10": {"CAP_ORTAK": "0.10", "CAP_TARAF": "short"}, "CS08": {"CAP_ORTAK": "0.08", "CAP_TARAF": "short"},
       "CS06": {"CAP_ORTAK": "0.06", "CAP_TARAF": "short"}}
A.KOLLAR = {f"K{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    ref = K.olc(K.seri("KD24_45T2"))
    for ad in ["T60", "KD24_45T2"] + list(A.KOLLAR):
        g = K.seri(ad); o = K.olc(g)
        h = ""
        if ad in A.KOLLAR:
            h = "ADAY" if o["enkotu"] > ref["enkotu"] and o["g5"] < ref["g5"] and ref["yil"] - o["yil"] <= 6 else "RED"
        print(f"{ad:10s} yillik {o['yil']:+7.1f} dd {o['dd']:6.1f} en kotu {o['enkotu']:6.2f} -%5 alti {o['g5']} -%4 alti {o['g4']} "
              f"p1 {o['p1']:.2f} Tem-Eyl26 {o['son']:+.1f} {h}")
    g = K.seri("KCS08")
    print("CS08 ile kalan en kotu 6 gun:", ", ".join(f"{d.date()} {v*100:+.2f}%" for d, v in g.sort_values().head(6).items()))


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
