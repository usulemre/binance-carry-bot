#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 433 — R30Y60S'İN KOMŞULUK (PLATO) TESTİ.

Madde 429: R30Y60S protokolde +66..+72 puan, P %78-89 (bar altı). P tek noktayı ölçer;
bir ayar şanssa komşuları çöker, yapısal ise komşuları da kontrolün önündedir.
Her komşu R30Y60S'ten TEK bir ayarı bir adım değiştirir (2.000 $ D8, iki hiza, kaymalı).
ÖN KAYIT: komşuların >= %80'i kontrolü yıllık >= +20 puan geçer VE hiçbiri dd'de 5 puandan
fazla kötü değilse → "PLATO" (R30Y60S izleme adayı olarak sabitlenir); değilse "TEPE" (şans).
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"
B = dict(HAVUZ="4", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60",
         HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", AGIRLIK_KAYMA="1")
DEG = {"H3": {"HAVUZ": "3"}, "H5": {"HAVUZ": "5"}, "TL30": {"TPL": "0.30"}, "TL50": {"TPL": "0.50"},
       "TS15": {"TPS": "0.15"}, "TS25": {"TPS": "0.25"}, "RZ05": {"REZERV": "0.05"}, "RZ20": {"REZERV": "0.20"},
       "UC40": {"UCELE": "0.40"}, "Y75": {"YAS_GUN": "75"}, "Y90": {"YAS_GUN": "90"},
       "V50": {"HACIM_ESIK": "5e7"}, "V100": {"HACIM_ESIK": "1e8"}, "P48": {"SK_DOSYA": "/tmp/sk_bar48.pkl"}}
A.SEVIYE = (2000,)
A.KOLLAR = {f"N{a}": ({**B, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    yil = lambda g: ((1 + g).prod() ** (365.25 / len(g)) - 1) * 100
    dd = lambda g: (((1 + g).cumprod() / (1 + g).cumprod().cummax()) - 1).min() * 100
    gk = (M.gunluk("M357_KAYMA_2000_0") + M.gunluk("M357_KAYMA_2000_1")) / 2
    g0 = (M.gunluk("M357_R30Y60S_2000_0") + M.gunluk("M357_R30Y60S_2000_1")) / 2
    print(f"KONTROL  yil {yil(gk):+7.1f} dd {dd(gk):6.1f}\nR30Y60S  yil {yil(g0):+7.1f} dd {dd(g0):6.1f}")
    iyi = kotu_dd = 0
    for kol in A.KOLLAR:
        g = (M.gunluk(f"M357_{kol}_2000_0") + M.gunluk(f"M357_{kol}_2000_1")) / 2
        f, d = yil(g) - yil(gk), dd(g) - dd(gk)
        s26 = ((1 + g[g.index >= "2026-07-01"]).prod() - 1) * 100
        print(f"{kol:7s} yil {yil(g):+7.1f} (kontrol {f:+6.1f}) dd {dd(g):6.1f} ({d:+5.1f}) Tem-Eyl26 {s26:+5.1f}%")
        iyi += f >= 20; kotu_dd += d < -5
    n = len(A.KOLLAR)
    print(f"\n{iyi}/{n} komsu kontrolu >= +20 puan geciyor, {kotu_dd} komsu dd'de 5 puandan kotu -> "
          f"{'PLATO' if iyi >= 0.8 * n and kotu_dd == 0 else 'TEPE'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
