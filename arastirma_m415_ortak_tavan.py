#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 415 — DİLİMLER ARASI ORTAK COİN TAVANI (g33 CAP_ORTAK, lockstep simülasyon).

Madde 414: büyük kayıp günleri tek coin long çöküşü (LAB 3 Tem −126 $, H 8 Haz −106 $),
coin toplam ağırlığı dilimler üst üste binince %10-15. Ama aynı coinler en çok
kazandıranlar → yasak değil TAVAN. Kaba 2026 tahmini: tavan 0,08 → Sh 3,44→3,61.
Motor: `_bt2g` üreteci + `_ortak_kos` (15 dilim eşzamanlı); parite iki yolda 0,0.
KONTROL: bugünkü kitap, zemin 2026-09-30'a uzatılmış (/tmp/m412/M357_BUGUN_*).
KOLLAR: CAP_ORTAK 0,10 / 0,08 / 0,06, CAP_DAGIT=1 (brüt korunur).
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza; dört şart + P >= %95 VE
eşit-risk farkı tavanla monoton.
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {f"CAP{int(c*100):02d}": ({"HAVUZ": "4", "CAP_ORTAK": str(c), "CAP_DAGIT": "1"}, 4, _E) for c in (0.10, 0.08, 0.06)}

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
