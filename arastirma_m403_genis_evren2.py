#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 403 — GENİŞ EVRENİN SINIRI: GE2'nin ötesi.

GE2 (yaş 60, hacim 70M, UCELE 0): +32..+39 puan, P %58-77 (madde 402).
Evren genişletme nerede tepe yapar?
    GE3 = yaş 45 + hacim 50M + UCELE 0 + donuk filtresi kapalı
    GE4 = GE2 + donuk filtresi kapalı
KARAR (madde 375): iki seviye x iki hiza; dört şart + P >= %95 (kontrole karşı).
Ek, tanımlayıcı: GE2'ye karşı fark (tepe mi, devam mı).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"GE3": ({"HAVUZ": "4", "YAS_GUN": "45", "UCELE": "0", "HACIM_ESIK": "5e7", "DONUK_ESIK": "1.0"}, 4, _E),
            "GE4": ({"HAVUZ": "4", "YAS_GUN": "60", "UCELE": "0", "HACIM_ESIK": "7e7", "DONUK_ESIK": "1.0"}, 4, _E)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
