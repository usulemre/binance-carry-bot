#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 475 — TP SONRASI YENİDEN GİRİŞ (AYNI) ve TERSİNE ÇEVİRME (TERS), merdivenli T60 üzerinde.

Madde 474: pompalanmış coin hâlâ primi taşıyor. O zaman TP ile TAM kapanan koltuğu boş bırakmak yerine aynı
coine aynı yönde (funding hâlâ uçtaysa, |S| ≥ REZ_ESIK) yeniden girmek? KOLLAR: TAY1 (AYNI=1) · TAY2 (TERS=1:
TP sonrası ters yönde gir — pompa sonrası geri dönüşü hasat).
ÖN KAYIT madde 470 ile aynı.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"Y1": {"AYNI": "1"}, "Y2": {"TERS": "1"}}
A.KOLLAR = {f"TA{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
