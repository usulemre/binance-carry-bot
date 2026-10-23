#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 448 — POMPA FİLTRESİ YALNIZ LONG TARAFINDA (madde 447'nin maliyet ayrıştırması).

Madde 447: UCELE 7 g / 30 g pompa filtresi en kötü günü yalnız %10-14 iyileştirdi, maliyeti 27-83 puan.
UCELE simetrik: çökmüş coini SHORT adayı da yapmıyor — maliyetin bir kısmı oradan olabilir. Yeni düğme
UCELE_TARAF=long (g33, parite korunur). KOLLAR: PL7_100, PL7_200 (7 g +%100/+%200, yalnız long),
PL30_300 (30 g +%300), PL7_100L40. Ölçüt madde 447 ile aynı.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m447_pompa_filtresi as P

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = K.T60
DEG = {"PL7_100": {"UCELE": "1.0", "UCGERI": "42", "UCELE_TARAF": "long"},
       "PL7_200": {"UCELE": "2.0", "UCGERI": "42", "UCELE_TARAF": "long"},
       "PL30_300": {"UCELE": "3.0", "UCGERI": "180", "UCELE_TARAF": "long"},
       "PL7_100L40": {"UCELE": "1.0", "UCGERI": "42", "UCELE_TARAF": "long", "SLL": "0.40"}}
A.KOLLAR = {f"K{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
P.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": P.analiz}[sys.argv[1]]()
