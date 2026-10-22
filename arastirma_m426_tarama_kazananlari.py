#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 426 — RASTGELE TARAMANIN KAZANANLARI (R16, R19, R18) MADDE 375 PROTOKOLÜNDE.

Madde 425: 25 kombinasyon, IS (22-24) seçimi → OOS (25-26) genelleme Spearman 0,61;
IS'te en iyi 5'in 4'ü OOS'ta kontrolü Sharpe +0,36..+0,69, getiri +41..+172 puan geçti.
Ortak iz: hacim 70M (5/5), yaş 60 (4/5). R16 her yıl kontrolün önünde (2023 +366 vs
+201, 2025 +309 vs +103) ama Tem-Ağu 2026 geride. 25'ten seçim → bar %95.
KONTROL: bugünkü kitap gerçekçi modelde (M357_KAYMA), zemin 2026-09-30'a uzatılmış (/tmp/m412/M357_BUGUN_*).
KOLLAR: SL50 (long −%50) · SL60 (long −%60) · SL50S100 (long −%50, short +%100).
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza; dört şart + P >= %95 .
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
_K = {"AGIRLIK_KAYMA": "1"}
A.KOLLAR = {
    "R16": (dict(HAVUZ="3", REB_GUN="4", TPL="0.30", TPS="0.15", REZERV="0.10", UCELE="0", YAS_GUN="60", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", **_K), 3, _E),
    "R19": (dict(HAVUZ="4", REB_GUN="4", TPL="0.40", TPS="0.25", REZERV="0.10", UCELE="0", YAS_GUN="60", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar36.pkl", **_K), 5, _E),
    "R18": (dict(HAVUZ="5", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0.40", YAS_GUN="60", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", **_K), 4, _E)}

def analiz():
    for kol in A.KOLLAR:
        gec = {}
        for sev in (2000, 3500):
            n = 0
            for h in (0, 1):
                gk = M.gunluk(f"M357_KAYMA_{sev}_{h}"); ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
                K, Ad = M.olcum("K", gk), M.olcum(kol, ga)
                s = KK.gecer_mi(K, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, med = M.bootstrap(gk, ga, n=1000)
                isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                print(f"{kol} {sev} {h} yillik {Ad.getiri-K.getiri:+6.1f} Sh22 {Ad.erken-K.erken:+.2f} Sh25 {Ad.gec-K.gec:+.2f} "
                      f"dusus {Ad.dusus-K.dusus:+.1f} esitR {s['esit_risk']-K.getiri:+6.1f} {isr} P {p:5.1f}", flush=True)
                n += int(s["gecer"] and p >= M.KANIT_BARI)
            gec[sev] = n == 2
        print(f"HUKUM {kol}: {'AYAR' if all(gec.values()) else 'RED'}\n", flush=True)

if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
