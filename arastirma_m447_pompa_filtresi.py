#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 447 — POMPA FİLTRESİ: aşırı yükselmiş coini long adayı yapmamak (madde 446 imzası).

Madde 446: T60 long felaketlerinin imzası çöküş ÖNCESİ aşırı yükseliş — 7 g getirisi üst %10'da
felaket riski 5,7x (IS) / 4,1x (OOS), 30 g'de 5,6x / 5,0x (POWER +%407, RAVE +%1.266, PIPPIN +%194).
Motorun UCELE düğmesi (madde 196) tam bu: "pompalanmış coin long adayı olmaz, çökmüş coin short
adayı olmaz"; şimdiye kadar yalnız 24 sa (UCGERI 6) penceresiyle denendi. Burada 7 g (42 bar) ve
30 g (180 bar). T60 (UCELE 0) üzerine; 2.000 $ D8, iki hiza, kaymalı.
KOLLAR: P7_50 / P7_100 (7 g +%50 / +%100) · P30_100 / P30_200 (30 g +%100 / +%200) ·
        P7_100L40 / P30_100L40 (+ long stop −%40)
ÖN KAYIT: madde 443 ölçütleri. Bir kol en kötü günü >= %20 iyileştirip yıllık maliyeti <= 10 puan
tutarsa "UCUZ KALKAN"; kâr da artırırsa (maliyet < 0) "KALKAN + KÂR" → iki seviye protokol.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = K.T60
DEG = {"P7_50": {"UCELE": "0.5", "UCGERI": "42"}, "P7_100": {"UCELE": "1.0", "UCGERI": "42"},
       "P30_100": {"UCELE": "1.0", "UCGERI": "180"}, "P30_200": {"UCELE": "2.0", "UCGERI": "180"},
       "P7_100L40": {"UCELE": "1.0", "UCGERI": "42", "SLL": "0.40"},
       "P30_100L40": {"UCELE": "1.0", "UCGERI": "180", "SLL": "0.40"}}
A.KOLLAR = {f"K{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    t = K.seri("T60"); b = K.olc(t)
    print(f"{'kol':10s} {'yillik':>7s} {'maliyet':>8s} {'dd':>6s} {'enkotu':>7s} {'iyilesme':>8s} {'p1':>6s} {'-5%alti':>7s} {'-4%alti':>7s} {'TemEyl26':>8s} {'IS yil':>7s} {'OOS yil':>7s}")
    satirlar = [("T60", t)] + [(k[1:], K.seri(k)) for k in ("KL40",) + tuple(A.KOLLAR)]
    for ad, g in satirlar:
        o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        print(f"{ad:10s} {o['yil']:+7.1f} {o['yil']-b['yil']:+8.1f} {o['dd']:6.1f} {o['enkotu']:7.2f} {(1-o['enkotu']/b['enkotu'])*100:7.0f}% "
              f"{o['p1']:6.2f} {o['g5']:7d} {o['g4']:7d} {o['son']:+8.1f} {K.YIL(IS):+7.1f} {K.YIL(OOS):+7.1f}")
    print()
    for k in A.KOLLAR:
        o = K.olc(K.seri(k)); iy = 1 - o["enkotu"] / b["enkotu"]; mal = b["yil"] - o["yil"]
        h = "KALKAN + KAR" if iy >= 0.20 and mal < 0 else "UCUZ KALKAN" if iy >= 0.20 and mal <= 10 else "RED"
        print(f"{k[1:]:10s} en kotu gun iyilesme %{iy*100:.0f}, maliyet {mal:+.1f} puan -> {h}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
