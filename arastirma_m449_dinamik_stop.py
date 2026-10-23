#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 449 — GİRİŞTEN BAĞIMSIZ STOP'LAR: 24 sa düşüş stop'u ve zirveden geri çekilme.

Madde 443/444: girişten −%40 long stop en kötü günü %31 kesiyor (~14 puan). Ama pompalanan coine
girişten SONRA yükselmişse çöküş girişe göre −%40'a varmadan kârı siler; tersine, girişten beri
yavaş düşen coin stop'a gürültüyle değer. İki girişten bağımsız tetik:
  SLL24 (yeni, g33): coin son 24 sa'teki kapanışından −%X düşerse long kapanır (çöküş hızı).
  TBAS/TGERI (var): kârdayken zirveden −%X geri çekilince kapan (iki taraf).
KOLLAR (T60 üzerine): D24_25/D24_35/D24_45 · Z50 (zirveden −%50) · Z40L40 · D24_35L40.
ÖLÇÜT madde 447 ile aynı (en kötü gün iyileşmesi vs yıllık maliyet).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m447_pompa_filtresi as P

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = K.T60
DEG = {"D24_25": {"SLL24": "0.25"}, "D24_35": {"SLL24": "0.35"}, "D24_45": {"SLL24": "0.45"},
       "Z50": {"TBAS": "0.0001", "TGERI": "0.50"}, "Z40L40": {"TBAS": "0.0001", "TGERI": "0.40", "SLL": "0.40"},
       "D24_35L40": {"SLL24": "0.35", "SLL": "0.40"}}
A.KOLLAR = {f"K{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
P.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": P.analiz}[sys.argv[1]]()
