#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 476 — ERKEN (İKİNCİ) KADEME: üç basamaklı merdiven.

Merdiven T60'tan sonraki tek gerçek yapısal kazançtı (madde 464/468) ve madde 470'te tek eğilim "daha çok
erken kilitle" idi (pay 0,75/0,80 +5/+9, ön kayıt altı). Pay'ı artırmak yerine ana kademenin ALTINA bir basamak
daha: pozisyonun ⅓'ü erken seviyede, kalanın ⅔'ü +%45 / −%15'te, son kısım +%60 / −%20'de.
KOLLAR (taban ZSR15P67): L25 / L30 (long ⅓ @ +%25 / +%30) · S08 (short ⅓ @ −%8) · L30S08.
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"L25": {"MERD0_ESIK": "0.25"}, "L30": {"MERD0_ESIK": "0.30"}, "S08": {"MERDS0_ESIK": "0.08"},
       "L30S08": {"MERD0_ESIK": "0.30", "MERDS0_ESIK": "0.08"}}
A.KOLLAR = {f"EK{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
