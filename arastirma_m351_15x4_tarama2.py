#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 351 — 15x4 KİTABINDA HİÇ TARANMAMIŞ ÜÇ AYAR DAHA: REZERV EŞİĞİ,
COİN BAŞINA REZERV SINIRI, FUNDING PENCERESİ.

Madde 350 ile aynı gerekçe (madde 222'nin yasası) ve aynı karar kuralı.
    REZ_ESIK 0,015   madde 156 (eski kitap)          -> 0,010 / 0,020
    KAP 0,05         madde 156                       -> 0,03 / 0,08
    pencere 48 sa    madde 209 (5 bacak; plato 36-60) -> 36 / 60 sa
Pencere kolları için sinyal canli_sinyal_kur.py ile kuruldu
(/tmp/sk_bar36.pkl, /tmp/sk_bar60.pkl) — canlı botun tahmincisiyle aynı.

ÖN KAYITLI KARAR: madde 350'nin kuralının aynısı (iki hizada dört şart +
bootstrap P >= %80; ayar değişikliği yalnız iki seviyede de geçerse).
"""
import sys

import arastirma_m350_15x4_tarama as T

T.KOLLAR = {
    "REZ10": {"REZ_ESIK": "0.010"}, "REZ20": {"REZ_ESIK": "0.020"},
    "KAP03": {"KAP": "0.03"}, "KAP08": {"KAP": "0.08"},
    "PEN36": {"SK_DOSYA": "/tmp/sk_bar36.pkl"},
    "PEN60": {"SK_DOSYA": "/tmp/sk_bar60.pkl"},
}

if __name__ == "__main__":
    {"kos": T.kos, "analiz": T.analiz}[sys.argv[1]]()
