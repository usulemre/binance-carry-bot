#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 461 — GENÇ COİNLER YARIM AĞIRLIKLA (korumalar artık var).

Yeni listelenen coinlerin funding'i en uç olanlar; madde 427'de yaş 45 MYX/AIA short sıkışmalarıyla
hesabı sıfırlamıştı (o zaman short +%200 ve 24 sa düşüş stop'u YOKTU). Şimdi ikisi de açık. Yeni g33
düğmesi: GENC_GUN (evren yaşı bu güne iner) + GENC_PAY (YAS_GUN=60'tan genç coinin hedef ağırlığı x).
KOLLAR (taban T60 + 24 sa stop + short +%200, 2.000 $): G30H (30 g, x0,5) · G45H (45 g, x0,5) ·
G30Q (30 g, x0,25) · G45F (45 g, x1,0).
ÖN KAYIT: IS'te >= +8, OOS'ta >= 0, eşit oynaklıkta >= +8 puan ve en kötü gün tabanın 1 puandan fazla
altına inmiyorsa → madde 462 sağlamlık.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m460_sinyal_toplulugu as S6

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
DEG = {"G30H": {"GENC_GUN": "30", "GENC_PAY": "0.5"}, "G45H": {"GENC_GUN": "45", "GENC_PAY": "0.5"},
       "G30Q": {"GENC_GUN": "30", "GENC_PAY": "0.25"}, "G45F": {"GENC_GUN": "45", "GENC_PAY": "1.0"}}
A.KOLLAR = {f"Y{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
S6.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": S6.analiz}[sys.argv[1]]()
