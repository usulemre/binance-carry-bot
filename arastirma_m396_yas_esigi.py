#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 396 — YAŞ EŞİĞİNİN KOMŞULARI BUGÜNÜN KİTABINDA (15x4, HAVUZ 4).

Madde 376 ablasyonu: yaş filtresi (90 g) kitabın en büyük tek bileşeni
(kaldırınca −97..−104 puan). Eşik madde 228'de ESKİ kitapta seçildi; bu
kitapta komşuları hiç ölçülmedi. Mekanizma: genç coinin funding'i kalabalık
değil keşif (fiyat bulma) ölçüyor; eşik bu geçişin nerede bittiğini söyler.
KOLLAR (g33 YAS_GUN): 60 / 120 / 180 gün.
KARAR (madde 375, koşudan ÖNCE): iki seviye (2.000 D8 / 3.500 D2) x iki hiza;
dört şart + eşli bootstrap P >= %95. Bir yön (uzatma ya da kısaltma) ancak
o yöndeki iki adım tutarlıysa (120 ve 180 aynı işaret) kabul edilir.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {f"YAS{g}": ({"HAVUZ": "4", "YAS_GUN": str(g)}, 4, _E) for g in (60, 120, 180)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
