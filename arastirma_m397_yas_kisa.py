#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 397 — YAŞ EŞİĞİ KISALTMA YÖNÜNÜN İKİNCİ VE ÜÇÜNCÜ ADIMI (45 / 30 gün).

Madde 396: 60 g dört hücrede +15..+26 puan, P %67-86 (bar %95 altı);
120 / 180 g monoton kötü; kapalı (0) −21..−29 puan ve düşüş −%47.
Ön kayıt (koşudan ÖNCE): eğri 90 → 60 → 45 → 30 boyunca ölçülür.
KABUL: bir eşik ancak (1) dört hücrede dört şart + P >= %95 VE
(2) komşusu (bir adım kısa ve bir adım uzun) aynı işaretli; ya da
60 ile 45 birlikte P >= %95 değilse RED, eğri kayda geçer.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {f"YAS{g}": ({"HAVUZ": "4", "YAS_GUN": str(g)}, 4, _E) for g in (45, 30)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
