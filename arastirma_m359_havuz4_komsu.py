#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 359 — MADDE 350'NİN SINIRDA KALAN İKİ KOLU, YENİ KONTROLE (HAVUZ 4) KARŞI.

Madde 350 (kontrol HAVUZ 3): TPL 0,50 ham +6..+7 puan ama şart 1
(22-24 −0,01..−0,06), P %59-77; REB 4 gün ham +3..+11 ama Sharpe düşük.
Kontrol HAVUZ 4 olunca ikisi de yeniden açılır (madde 222).
Kollar HAVUZ 4 + tek değişiklik; kontrol T350_HAVUZ4_*.

ÖN KAYITLI KARAR: madde 357 ile aynı (iki hiza, dört şart + P >= %80;
ayar değişikliği iki seviyede de geçerse).
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

A.KOLLAR = {
    "TPL50": ({"HAVUZ": "4", "TPL": "0.50"}, 4, {2000: M.D8, 3500: M.D2}),
    "REB4":  ({"HAVUZ": "4", "REB_GUN": "4"}, 4, {2000: M.D8, 3500: M.D2}),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
