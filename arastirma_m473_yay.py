#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 473 — SERBEST KALAN AGIRLIGI ACIK BACAKLARA YAYMA (MERD_YAY).

Merdivenle boşta sermaye %6,5 → %8,78. Yedek adayla doldurmak nakitten kötüydü (madde 229) — burada YENİ
coin yok: boşalan ağırlık aynı dilimde aynı taraftaki AÇIK bacaklara orantılı eklenir (brüt korunur,
giriş ağırlıklı ortalama). KOLLAR: Y1 (yalnız rung dolumu) · Y2 (rung + TP kapanışı).
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"Y1": {"MERD_YAY": "1"}, "Y2": {"MERD_YAY": "2"}}
A.KOLLAR = {f"YA{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
