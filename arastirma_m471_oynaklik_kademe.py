#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 471 — OYNAKLIĞA ÖLÇEKLİ KADEME (MERD_KAT / MERDS_KAT, yeni g33 düğmeleri).

Sabit kademe (long +%45, short −%15) oynak coinde normal dalgalanma, sakin coinde büyük hareket. Kademe =
k x 5 g gerçekleşen oynaklık (%5-%100, son TP'nin %95'i ile kırpılır). Taban: canlı varsayılan ZSR15P67.
KOLLAR: VL3 / VL5 (long 3x / 5x) · VS1 / VS15 (short 1,0x / 1,5x) · VL4VS12 (long 4x + short 1,2x).
ÖN KAYIT madde 470 ile aynı.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"VL3": {"MERD_KAT": "3"}, "VL5": {"MERD_KAT": "5"}, "VS1": {"MERDS_KAT": "1.0"},
       "VS15": {"MERDS_KAT": "1.5"}, "VL4VS12": {"MERD_KAT": "4", "MERDS_KAT": "1.2"}}
A.KOLLAR = {f"V{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
