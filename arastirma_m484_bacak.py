#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 484 — BACAK SAYISI merdivenli kitapta (3+3 / 5+5 / 6+6; taban 4+4).

Bacak sayısı en son merdivenden ÖNCE ölçüldü (madde 230/458: 4+4 plato, 3+3 kaldıraç). Merdiven tek coin
pompasının kârını kilitlediğine göre yoğunlaşmanın riski değişmiş olabilir: 3+3 artık daha güvenli, 5+5 daha az
seyreltici olabilir. Madde 480 taraması bacağı sabit tuttu. 2.000 $ seviyesinde (D8 evreni) — 5+5/6+6 bu sermayede
asgari emir sınırına yaklaşır, sonuç bilgi amaçlı da okunur.
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
A.KOLLAR = {f"BC{b}": (dict(W.T), b, {2000: M.D8}) for b in (3, 5, 6)}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
