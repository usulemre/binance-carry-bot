#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 424 — DİLİM ARALIĞI: 8 sa (15 dilim) yerine 4 / 12 / 24 sa (gerçekçi ağırlık kayması).

Kullanıcı: "8 saatte bir mi dilimliyor, test et". REB 5 g = 30 bar, FAZ 15 → 2 bar (8 sa).
FAZ 30 = 4 sa, FAZ 10 = 12 sa, FAZ 5 = 24 sa (madde 184: 5 → 15 faz kumarını kapatmıştı).
Uyarı: dilim sayısı bacak büyüklüğünü değiştirir (bakiye / N_DILIM); evren listesi
(D8/D2) 15 dilimin bacağına göre — 30 dilimde 2.000 $ bacağı ~7 $, evren etkisi yaklaşık.
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
A.KOLLAR = {f"FZ{f}": ({"HAVUZ": "4", "FAZ": str(f), **_K}, 4, _E) for f in (30, 10, 5)}

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
