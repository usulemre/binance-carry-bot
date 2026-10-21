#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 405 — GE2 KİTABINDA KÂR ALMA SEVİYELERİ (etkileşim).

GE2 evreni genişletti (daha genç, daha oynak coinler); TPL 0,40 / TPS 0,20 dar evrende
seçildi. Oynak evrende kâr alma eşiği kayabilir.
KONTROL: M357_GE2 (aynı zemin). KOLLAR: GE2 + TPL 0,50 · GE2 + TPS 0,25 · GE2 + TPL 0,30 · GE2 + TPS 0,15.
KARAR (madde 375, koşudan ÖNCE): iki seviye x iki hiza, dört şart + P >= %95
GE2'ye karşı. Tanımlayıcı: bugünkü kitaba (T350_HAVUZ4) karşı da yazılır.
"""
import os, sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
_G = {"YAS_GUN": "60", "UCELE": "0", "HACIM_ESIK": "7e7"}
A.KOLLAR = {"G2L50": (dict(_G, HAVUZ="4", TPL="0.50"), 4, _E), "G2S25": (dict(_G, HAVUZ="4", TPS="0.25"), 4, _E), "G2L30": (dict(_G, HAVUZ="4", TPL="0.30"), 4, _E), "G2S15": (dict(_G, HAVUZ="4", TPS="0.15"), 4, _E)}

def analiz():
    for kol in A.KOLLAR:
        gec = {}
        for sev in A.SEVIYE:
            n = 0
            for h in M.HIZA:
                gk = M.gunluk(f"M357_GE2_{sev}_{h}"); ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
                K, Ad = M.olcum("K", gk), M.olcum(kol, ga)
                s = KK.gecer_mi(K, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, med = M.bootstrap(gk, ga, n=1000)
                isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                t0 = M.olcum("T", M.gunluk(f"T350_HAVUZ4_{sev}_{h}"))
                print(f"{kol:<5} {sev} {h}  GE2'ye fark yillik {Ad.getiri-K.getiri:+6.1f} Sh22 {Ad.erken-K.erken:+.2f} Sh25 {Ad.gec-K.gec:+.2f} "
                      f"dusus {Ad.dusus-K.dusus:+.1f} {isr} P {p:5.1f} | bugune fark {Ad.getiri-t0.getiri:+.1f}", flush=True)
                n += int(s["gecer"] and p >= M.KANIT_BARI)
            gec[sev] = n == len(M.HIZA)
        print(f"HUKUM {kol}: {'AYAR (GE2 icinde)' if all(gec.values()) else 'RED'}\n")

if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
