#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 402 — "GENİŞ EVREN" BİRLEŞİMİ: yaş 60 g + (hacim 70M) + pump-long yasağı kapalı.

Madde 396/397 (yaş 60: +15..+26, P %67-86), 401 (hacim 70M: +3..+7, P %52-71),
376 (UCELE kapalı: +3..+9) aynı yönde — evreni genişletmek. Birleşim:
    GE1 = YAS_GUN 60 + UCELE 0
    GE2 = YAS_GUN 60 + UCELE 0 + HACIM_ESIK 7e7
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza; dört şart + P >= %95.
Birleşimler bileşenleri görerek kuruldu (seçim yanlılığı) → bar düşürülmez.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"GE1": ({"HAVUZ": "4", "YAS_GUN": "60", "UCELE": "0"}, 4, _E),
            "GE2": ({"HAVUZ": "4", "YAS_GUN": "60", "UCELE": "0", "HACIM_ESIK": "7e7"}, 4, _E)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
