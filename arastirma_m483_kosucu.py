#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 483 — KOŞUCU: kademe sonrası kalan payı sabit TP yerine İZ SÜREN çıkışla taşı.

Kâr kaynağı pompa coinleri (madde 414/446). Merdiven ⅔'ü +%45'te kilitliyor; kalan ⅓ +%60'ta sabit kapanıyor —
pompa +%150 giderse ⅓'ün üst kısmı kaçıyor. Eski kitapta "takip eden kâr al" REDdi (madde 1. tur) ama orada
TÜM pozisyon riskteydi; burada ⅔ zaten kilitli, yalnız ⅓ koşuyor. Kalan pay zirveden G kadar geri çekilince kapanır.
KOLLAR: KL15/KL25/KL35 (long G 0,15/0,25/0,35) · KS10 (short, dipten +%10) · KL25KS10.
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"KL15": {"KOSUCU": "0.15"}, "KL25": {"KOSUCU": "0.25"}, "KL35": {"KOSUCU": "0.35"},
       "KS10": {"KOSUCU_S": "0.10"}, "KL25KS10": {"KOSUCU": "0.25", "KOSUCU_S": "0.10"}}
A.KOLLAR = {f"KO{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
