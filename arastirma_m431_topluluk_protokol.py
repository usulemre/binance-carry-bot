#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 431 — AYAR TOPLULUĞU (madde 430 B) MADDE 375 PROTOKOLÜNDE.

Madde 430: madde 425 taramasında IS Sharpe'ına göre ilk 5 ayarın (R16 R19 R13 R18 R22)
eşit sermaye topluluğu OOS Sharpe 3,83 (en iyi tek ayar 3,58, kontrol 3,21), eşit
oynaklıkta +25,6 puan. Ama Tem-Eyl 2026'da kontrolün gerisinde (+13,7% vs +30,8%).
Bu betik eksik üyeleri (R13, R22) iki seviyede koşar, topluluğu (günlük getirilerin
ortalaması = sermaye 5 alt hesaba eşit bölünmüş, günlük dengeli) kontrolle kıyaslar.
KONTROL: M357_KAYMA. KARAR (koşudan ÖNCE): iki seviye x iki hiza, dört şart + P >= %95.
UYARI: REB 4 üyeler 24 dilim (madde 426) → D8/D2 dışlama listeleri onlar için iyimser.
"""
import os, sys
import pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
_K = {"AGIRLIK_KAYMA": "1"}
A.KOLLAR = {
    "R13": (dict(HAVUZ="3", REB_GUN="4", TPL="0.50", TPS="0.20", REZERV="0.30", UCELE="0.40", YAS_GUN="90", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar36.pkl", **_K), 3, _E),
    "R22": (dict(HAVUZ="4", REB_GUN="5", TPL="0.50", TPS="0.25", REZERV="0.30", UCELE="0.40", YAS_GUN="60", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar36.pkl", **_K), 4, _E)}
UYELER = ["R16", "R19", "R13", "R18", "R22"]


def analiz():
    for ad, uy in (("TOP5", UYELER), ("TOP3", UYELER[:3])):
        gec = {}
        for sev in (2000, 3500):
            n = 0
            for h in (0, 1):
                gk = M.gunluk(f"M357_KAYMA_{sev}_{h}")
                ga = pd.concat([M.gunluk(f"M357_{u}_{sev}_{h}") for u in uy], axis=1).dropna().mean(axis=1)
                gk = gk.loc[ga.index]
                K, Ad = M.olcum("K", gk), M.olcum(ad, ga)
                s = KK.gecer_mi(K, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, med = M.bootstrap(gk, ga, n=1000)
                isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                son = lambda x: ((1 + x[x.index >= "2026-07-01"]).prod() - 1) * 100
                print(f"{ad} {sev} {h} yillik {Ad.getiri-K.getiri:+6.1f} Sh22 {Ad.erken-K.erken:+.2f} Sh25 {Ad.gec-K.gec:+.2f} "
                      f"dusus {Ad.dusus-K.dusus:+.1f} esitR {s['esit_risk']-K.getiri:+6.1f} {isr} P {p:5.1f} "
                      f"| Tem-Eyl26 {son(ga):+.1f}% vs {son(gk):+.1f}%", flush=True)
                n += int(s["gecer"] and p >= M.KANIT_BARI)
            gec[sev] = n == 2
        print(f"HUKUM {ad}: {'AYAR' if all(gec.values()) else 'RED'}\n", flush=True)


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
