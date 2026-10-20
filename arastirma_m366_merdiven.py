#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 366 — KÂR ALMA MERDİVENİ (madde 235) HAVUZ 4'LÜK 15x4 KİTABINDA.

Madde 235 (5 bacak, HAVUZ 3): merdiven %20 x 1/2 Sharpe 3,128 -> 3,202,
düşüş −14,6 -> −14,2, getiri −6 puan; %20 x 1/3 3,183; %10 x 1/3 3,157.
Bütçe: +%20'ye değen bacak +%40'a değenin 2,6 katı. Kitap o günden beri
dört kez değişti (bacak 5->4, faz, HAVUZ 3->4); merdiven hiç yeniden
açılmadı (madde 222).

KOLLAR (motorun MERD_ESIK / MERD_PAY'ı; HAVUZ 4):
    M20_50   %20'de pozisyonun yarısı
    M20_33   %20'de üçte biri
    M10_33   %10'da üçte biri

ÖN KAYITLI KARAR: madde 357 ile aynı (iki hiza, dört şart + P >= %80;
ayar değişikliği iki seviyede de geçerse). Not: madde 235'te merdiven
Sharpe'ı yükseltip getiriyi düşürmüştü — şart 4 (kaldıraç gerektirmeme)
burada bağlayıcı olabilir; o durumda sonuç "KALDIRAÇ KARARI" sınıfıdır.
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {
    "M20_50": ({"HAVUZ": "4", "MERD_ESIK": "0.20", "MERD_PAY": "0.5"}, 4, _E),
    "M20_33": ({"HAVUZ": "4", "MERD_ESIK": "0.20", "MERD_PAY": "0.333"}, 4, _E),
    "M10_33": ({"HAVUZ": "4", "MERD_ESIK": "0.10", "MERD_PAY": "0.333"}, 4, _E),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
