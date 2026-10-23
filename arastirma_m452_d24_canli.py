#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 452 — 24 SA DÜŞÜŞ STOP'U CANLIDAKİ GİBİ: seviye 8 sa'te bir güncellenir (SLL24_TAZE=2).

Canlı bot 8 sa'te bir döner; borsada bekleyen STOP_MARKET'in seviyesi (24 sa önceki fiyat x 0,55) ancak
turda yenilenebilir. Motor her 4 sa bakıyordu. KOL: D24_45T2 (SLL24 0,45, TAZE 2). Ayrıca D24_45 +
long stop −%40 birleşimi (D24_45L40). Ölçüt madde 447 ile aynı.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m447_pompa_filtresi as P

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = K.T60
A.KOLLAR = {"KD24_45T2": ({**T, "SLL24": "0.45", "SLL24_TAZE": "2"}, 4, {2000: M.D8}),
            "KD24_45": ({**T, "SLL24": "0.45"}, 4, {2000: M.D8}),
            "KD24_45L40": ({**T, "SLL24": "0.45", "SLL": "0.40"}, 4, {2000: M.D8})}
P.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": P.analiz}[sys.argv[1]]()
