#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 481 — TEK HESAP GİRİŞ PARİTESİ (gözden kaçmış olabilecek motor-canlı farkı).

Motor her dilimin TP/kademe/stop'unu O DİLİMİN kendi girişinden ölçer. Canlı bot 15 dilimi TEK hesapta tutar ve
emirleri Binance'in entryPrice'ından (coinin tüm dilimlerdeki AĞIRLIKLI ORTALAMA girişi) kurar: TP dolunca coin
bütün dilimlerde birden kapanır. Bu fark hiç ölçülmedi. Ölçüm hem gerçekçilik (canlı backtestten sapar mı) hem
kâr (fark büyükse canlıyı dilim başına emre çevirmek gerekir) sorusu.
KOLLAR: TG1 (TEK_GIRIS=1, lockstep) · KP (CAP_ORTAK=10 — bağlayıcı olmayan tavan, lockstep PARİTE kontrolü).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"TG1": {"TEK_GIRIS": "1"}, "KP": {"CAP_ORTAK": "10"}}
A.KOLLAR = {f"TH{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
