#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 401 — HACİM EŞİĞİNİN KOMŞULARI BUGÜNÜN KİTABINDA (madde 396'nın dersi).

Madde 396-397: yaş eşiği eski kitapta seçilmişti, bugünkü kitapta 30-60 g
platosu çıktı. Hacim eşiği (100M$/gün) de madde 226'da ESKİ kitapta
seçildi; 15x4 HAVUZ 4'te komşuları ölçülmedi.
KOLLAR (g33 HACIM_ESIK): 50M · 70M · 150M.
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza; dört şart + P >= %95;
yön ancak o yönde iki adım (50 ve 70 ya da yalnız 150 tek adım) aynı işaretliyse.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {f"HAC{int(h/1e6)}": ({"HAVUZ": "4", "HACIM_ESIK": str(h)}, 4, _E) for h in (5e7, 7e7, 1.5e8)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
