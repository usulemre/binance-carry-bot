#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 450 — SHORT SIKIŞMASI İÇİN 24 SA YÜKSELİŞ STOP'U (kötü günlerin diğer yarısı).

Madde 443: kötü günlerin yarısı yükselen piyasada büyük coin SHORT sıkışması (XRP +%76, 1000RATS +%54,
FIL +%35, AIOT +%173 tek günde). Sıkı girişten-stop (+%50) ZARARLIYDI. Bu madde girişten bağımsız:
coin son 24 sa'te +%X yükselirse short kapanır (SLS24, yeni düğme, parite korunur).
KOLLAR (T60 üzerine): S24_25 / S24_35 / S24_50 · S24_35L40 (+ long stop −%40).
ÖLÇÜT madde 447 ile aynı.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m447_pompa_filtresi as P

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = K.T60
DEG = {"S24_25": {"SLS24": "0.25"}, "S24_35": {"SLS24": "0.35"}, "S24_50": {"SLS24": "0.50"},
       "S24_35L40": {"SLS24": "0.35", "SLL": "0.40"}}
A.KOLLAR = {f"K{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
P.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": P.analiz}[sys.argv[1]]()
