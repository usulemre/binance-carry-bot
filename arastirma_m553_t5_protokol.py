#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 553 — T5 ADAYI PROTOKOLDE (düzeltilmiş model): T5 = T4 + short 40 sa (S_REB 10) + short sinyal penceresi 96 sa,
vs T4 (asıl bot). Bugünün iki kıl payı adayı (madde 545, 547) BİRLİKTE: tek tek kanıt yetmedi, birleşim kontrol ediliyor.
UZUN ZEMİN, canlı gibi giriş + 5 bp, iki seviye, iki hiza (önce ./zemin_sec.sh uzun).
Madde 544-545: 36-40 sa platosu; botta 40 sa = 5 tur (8 sa'lik tur).
KARAR (madde 375): dört şart + P >= %95 iki seviyede → AYAR."""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_tabanlar as TB
import karar_kurali as KK

A.CIKTI = "/tmp/m_uzun"; M.CIKTI = "/tmp/m_uzun"; M.KANIT_BARI = 95.0; A.SEVIYE = (2000, 3500)
B = {**TB.T1, "TEK_GIRIS": "1", "KOM": "0.0005", "MERD_SIRA": "1"}
T4 = {**B, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
A.KOLLAR = {"W4_TGK5": (T4, 4, {2000: M.D8, 3500: M.D2}),
            "W5_TGK5": ({**T4, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl"}, 4, {2000: M.D8, 3500: M.D2})}


def analiz():
    kol = "W5_TGK5"; gec = {}
    for sev in (2000, 3500):
        n = 0
        for h in (0, 1):
            gk = M.gunluk(f"M357_W4_TGK5_{sev}_{h}"); ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
            Kc, Ad = M.olcum("K", gk), M.olcum(kol, ga)
            s = KK.gecer_mi(Kc, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
            p, _ = M.bootstrap(gk, ga, n=1000)
            isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
            print(f"{kol} {sev} {h} yillik {Ad.getiri-Kc.getiri:+6.1f} Sh22 {Ad.erken-Kc.erken:+.2f} Sh25 {Ad.gec-Kc.gec:+.2f} "
                  f"dusus {Ad.dusus-Kc.dusus:+.1f} esitR {s['esit_risk']-Kc.getiri:+6.1f} {isr} P {p:5.1f}", flush=True)
            n += int(s["gecer"] and p >= M.KANIT_BARI)
        gec[sev] = n == 2
    print(f"HUKUM {kol}: {'AYAR' if all(gec.values()) else 'RED'}  {gec}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
