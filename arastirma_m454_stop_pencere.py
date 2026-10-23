#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 454 — DÜŞÜŞ STOP'UNU İYİLEŞTİRME: pencere uzunluğu ve iki kademe (canlı hızında, TAZE 2).

Madde 451-453: 24 sa −%45 (D24_45T2) en kötü günü −8,63 → −5,49, maliyet 5,7 puan. Soru: daha kısa
pencere çöküşü başında yakalayıp daha az kayıpla çıkar mı; iki kademe (hızlı çöküşe kısa, yavaşa uzun
pencere) ikisinin iyisini alır mı?
KOLLAR (T60 + SLL24_TAZE 2): W12_30 / W12_35 (12 sa −%30/−%35) · W8_25 (8 sa −%25) ·
  W48_55 (48 sa −%55) · D45K30 / D45K35 (24 sa −%45 + 12 sa −%30/−%35).
ÖN KAYIT: D24_45T2'yi en kötü günde ve −%5 altı günde geçip maliyeti <= 8 puan tutan kol → madde 455
komşuluk testine. Hiçbiri geçmezse D24_45 kalır.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24_TAZE": "2"}
DEG = {"W12_30": {"SLL24": "0.30", "SLL24_PEN": "2"}, "W12_35": {"SLL24": "0.35", "SLL24_PEN": "2"},
       "W8_25": {"SLL24": "0.25", "SLL24_PEN": "1"}, "W48_55": {"SLL24": "0.55", "SLL24_PEN": "11"},
       "D45K30": {"SLL24": "0.45", "SLLK": "0.30", "SLLK_PEN": "2"},
       "D45K35": {"SLL24": "0.45", "SLLK": "0.35", "SLLK_PEN": "2"}}
A.KOLLAR = {f"K{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    t = K.seri("T60"); b = K.olc(t); ref = K.olc(K.seri("KD24_45T2"))
    print(f"{'kol':10s} {'yillik':>7s} {'maliyet':>8s} {'dd':>6s} {'enkotu':>7s} {'-5%':>4s} {'-4%':>4s} {'p1':>6s} {'TemEyl':>7s} {'IS':>7s} {'OOS':>7s}")
    for ad in ["T60", "KD24_45T2"] + list(A.KOLLAR):
        g = K.seri(ad); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        h = ""
        if ad in A.KOLLAR:
            h = "ADAY" if (o["enkotu"] > ref["enkotu"] and o["g5"] <= ref["g5"] and b["yil"] - o["yil"] <= 8) else "-"
        print(f"{ad:10s} {o['yil']:+7.1f} {o['yil']-b['yil']:+8.1f} {o['dd']:6.1f} {o['enkotu']:7.2f} {o['g5']:4d} {o['g4']:4d} {o['p1']:6.2f} "
              f"{o['son']:+7.1f} {K.YIL(IS):+7.1f} {K.YIL(OOS):+7.1f} {h}")
    # kalan en kötü 8 gün (D24_45T2)
    g = K.seri("KD24_45T2")
    print("\nD24_45T2 ile kalan en kotu 8 gun:", ", ".join(f"{d.date()} {v*100:+.2f}%" for d, v in g.sort_values().head(8).items()))


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
