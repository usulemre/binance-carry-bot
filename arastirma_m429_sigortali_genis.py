#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 429 — SİGORTALI GENİŞ EVREN (short +%200 felaket stop'u) MADDE 375 PROTOKOLÜNDE.

Madde 428: sigortalı R30 (yaş 45, hacim 70M, UCELE 0, REZ 0,10, 60 sa) 4,2 yılda ~61x
(kontrol ~29x), tam düşüş −%21,7. Ama R30 madde 427'de 4 yılın tamamına bakılarak
seçildi → iyimser. Burada protokol: iki seviye x iki hiza, dört şart + P >= %95.
KOLLAR: R30S (R30 + SLS 2,0) · R30Y60S (aynı, yaş 60) · R18S (R18 + SLS 2,0).
KONTROL: M357_KAYMA (bugünkü kitap, kaymalı model). Bar %95 (çoklu seçim).
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
_K = {"AGIRLIK_KAYMA": "1"}
A.KOLLAR = {
    "R30S": (dict(HAVUZ="4", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="45", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", **_K), 4, _E),
    "R30Y60S": (dict(HAVUZ="4", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", **_K), 4, _E),
    "R18S": (dict(HAVUZ="5", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0.40", YAS_GUN="60", HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", **_K), 4, _E)}

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
