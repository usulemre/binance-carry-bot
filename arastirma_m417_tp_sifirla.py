#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 417 — KÂR HEDEFİ SIFIRLAMA (çöküş sonrası toparlanmayı eski dilimler de hasat etsin).

Madde 414/416: H 8 Haz −%90 çöktü; bot tuttu ve 8-14 Haz +51 $ kazandı, ama hasadı
yalnız DİPTE giren dilimler aldı — 0,70'ten girenlerin %40 hedefi 0,98'de kaldı.
TP_SIFIRLA=x: bacak girişten aleyhe x gidince TP referansı o anki kapanışa taşınır
(işlem yok). Stop değil: pozisyon tutulur, yalnız toparlanmada daha erken hasat edilir.
KONTROL: bugünkü kitap, zemin 2026-09-30'a uzatılmış (/tmp/m412/M357_BUGUN_*).
KOLLAR: R30 / R50 (iki taraf, %30 / %50) · R30L (yalnız long, %30). Doz monotonluğu raporlanır.
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza; dört şart + P >= %95 .
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"R30": ({"HAVUZ": "4", "TP_SIFIRLA": "0.30"}, 4, _E), "R50": ({"HAVUZ": "4", "TP_SIFIRLA": "0.50"}, 4, _E), "R30L": ({"HAVUZ": "4", "TP_SIFIRLA": "0.30", "TP_SIF_TARAF": "long"}, 4, _E)}

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
