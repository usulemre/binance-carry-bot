#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 462 — ÇIKIŞ ŞEKLİ VE SHORT SEÇİMİ (T60 üzerinde denenmemiş).

KOLLAR (taban T60 + 24 sa stop, 2.000 $): MR30 / MR40 (merdiven: long'un yarısı +%30/+%40'ta, kalanı
+%60'ta; short'ta TP %20 önce vurur) · TKS1 / TKS15 (short TP = 1,0 / 1,5 x 5 g oynaklık, %5-%150 arası)
· SVY / SVD (short tarafı funding yerine en YÜKSEK / en DÜŞÜK oynaklıklı adaylardan).
ÖN KAYIT madde 460 ile aynı (IS >= +8, OOS >= 0, eşit oynaklıkta >= +8).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m460_sinyal_toplulugu as S6

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
DEG = {"MR30": {"MERD_ESIK": "0.30", "MERD_PAY": "0.5"}, "MR40": {"MERD_ESIK": "0.40", "MERD_PAY": "0.5"},
       "TKS1": {"TPKATS": "1.0"}, "TKS15": {"TPKATS": "1.5"},
       "SVY": {"SSEC": "volyuk"}, "SVD": {"SSEC": "voldus"}}
A.KOLLAR = {f"X{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
S6.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": S6.analiz}[sys.argv[1]]()
