#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 416 — FELAKET STOP'U (geniş, yalnız çöküşte tetiklenen).

Madde 414: kayıp günleri tek coin çöküşü — H 8 Haz 8 saatte −%90 (0,625 → 0,075),
long bacak kitabın ~%5,4'ünü götürdü. Madde 191'in stop'ları dar (%15-35) ve TP
hasadını kesiyordu; %50-60 stop normal dalgalanmada neredeyse hiç tetiklenmez,
yalnız çöküşü −%90'dan ~−%50'ye çeker. Dolum muhafazakâr (açılış seviyenin
ötesindeyse açılıştan).
KONTROL: bugünkü kitap, zemin 2026-09-30'a uzatılmış (/tmp/m412/M357_BUGUN_*).
KOLLAR: SL50 (long −%50) · SL60 (long −%60) · SL50S100 (long −%50, short +%100).
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza; dört şart + P >= %95 .
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"SL50": ({"HAVUZ": "4", "SLL": "0.50"}, 4, _E), "SL60": ({"HAVUZ": "4", "SLL": "0.60"}, 4, _E), "SL50S100": ({"HAVUZ": "4", "SLL": "0.50", "SLS": "1.0"}, 4, _E)}

def analiz():
    for kol in A.KOLLAR:
        gec = {}
        for sev in (2000, 3500):
            n = 0
            for h in (0, 1):
                gk = M.gunluk(f"M357_BUGUN_{sev}_{h}"); ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
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
