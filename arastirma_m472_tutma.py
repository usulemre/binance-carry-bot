#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 472 — TARAF BAZLI MAKSİMUM TUTMA (YAS_L / YAS_S), iki taraflı merdiven üzerinde.

Tutma 6/7 g (tüm kitap) kötüydü (madde 457). Merdivenle kârın çoğu ilk günlerde kilitleniyor; kalan
⅓ pozisyonun 5 gün boyunca tutulması gerekli mi? KOLLAR (taban ZSR15P67): YL18 / YL24 (long en fazla
3 / 4 g) · YS24 (short en fazla 4 g) · YL24YS24.
ÖN KAYIT madde 470 ile aynı.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"YL18": {"YAS_L": "18"}, "YL24": {"YAS_L": "24"}, "YS24": {"YAS_S": "24"}, "YL24YS24": {"YAS_L": "24", "YAS_S": "24"}}
A.KOLLAR = {f"H{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
