#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 500 — S_REB + COIN BAZLI SIKIŞMA KORUMASI (uzun zemin; önce ./zemin_sec.sh uzun).

Madde 499: S_REB'in kuyruk maliyeti tek olay — 2020-11 dar evrende coin özelinde short sıkışması. Piyasa medyanı yakalamıyor.
Coin bazlı iki koruma (ikisi de daha önce S_REB'siz ölçüldü): SLS24 (short, 24 sa'te +x yükselirse kapat; madde 450) ve
short coin tavanı %8 (CAP_TARAF=short; madde 455-456 — dar evrende aynı coinin birçok dilimde birikmesini keser).
KOLLAR (T1 + S_REB 12): Z40 / Z60 (SLS24 0,40 / 0,60) · CAP8 · ayrıca T1+CAP8 (korumanın S_REB'siz kontrolü).
ÖN KAYIT madde 499 ile aynı: S_REB kazancının ≥ yarısı korunur VE tüm dönem dd T1'den en fazla 1 puan derin.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

B = {**TB.T1, "S_REB": "12"}; CAP = {"CAP_ORTAK": "0.08", "CAP_TARAF": "short"}
U.KOL = {"U_T1": TB.T1, "U_T1SR12": B, "U_SR12Z40": {**B, "SLS24": "0.40"}, "U_SR12Z60": {**B, "SLS24": "0.60"},
         "U_SR12CAP8": {**B, **CAP}, "U_T1CAP8": {**TB.T1, **CAP}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}

if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": D.analiz}[sys.argv[1]]()
