#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 502 — SR12+CAP8 KOMŞULUĞU uzun zeminde (plato mu?) — önce ./zemin_sec.sh uzun.

Madde 501: dört şart 16/16, P %68-82. P'nin güç sınırını aşmanın diğer yolu madde 463/487 gibi PLATO: komşu ayarlar da
aynı yönde mi? KOMŞULAR (biri değişir): S_REB 9 / 18 bar (1,5 / 3 g) · tavan %7 / %10.
ÖN KAYIT (koşudan önce): dört komşunun DÖRDÜ de TÜM dönemde T1'e karşı yıllık ≥ +15, Sharpe ≥ +0,15, dd en fazla 1 puan
derin, VE üç dönemin her birinde yıllık > 0 → PLATO.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

C = lambda c: {"CAP_ORTAK": c, "CAP_TARAF": "short"}
U.KOL = {"U_T1": TB.T1, "U_SR12CAP8": {**TB.T1, "S_REB": "12", **C("0.08")},
         "U_SR9CAP8": {**TB.T1, "S_REB": "9", **C("0.08")}, "U_SR18CAP8": {**TB.T1, "S_REB": "18", **C("0.08")},
         "U_SR12CAP7": {**TB.T1, "S_REB": "12", **C("0.07")}, "U_SR12CAP10": {**TB.T1, "S_REB": "12", **C("0.10")}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}

if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": D.analiz}[sys.argv[1]]()
