#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 423 — LONG KALABALIK VETOSU (tam dönem katkı atfından; gerçekçi ağırlık kayması).

Tam dönem coin-gün katkı atfı (gerçekçi model, 2.000 $, iki hiza): 9 özellik x 5 kova x
iki taraf içinde İKİ DÖNEMDE DE zarar eden TEK kova: long bacak, log(long/short hesap
oranı) üst beşte bir (0,64..2,15) — 22-24 −150 $/yıl (−30 bp/gün), 25-26 −127 $/yıl
(−132 bp/gün). Karşıtı (oran en düşük long) en çok kazandıran kova (+928 / +1.221 $/yıl).
Mekanizma: funding negatif ama hesaplar long kalabalık → kalabalık AYNI tarafta.
Seçim tam dönem verisine bakılarak yapıldı → bar %95, doz monotonluğu şart.
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
A.KOLLAR = {f"LSL{int(v*100):02d}": ({"HAVUZ": "4", "LS_L_MAKS": str(v), **_K}, 4, _E) for v in (0.80, 0.64, 0.50)}

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
