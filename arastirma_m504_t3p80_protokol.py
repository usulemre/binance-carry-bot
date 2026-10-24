#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 504 — T3 + kademe payı 0,80 vs T3, UZUN ZEMİN PROTOKOLÜ (canlı gibi giriş + 5 bp; önce ./zemin_sec.sh uzun).
KARAR (madde 375): dört şart + P >= %95 iki seviyede → AYAR (T3 üzerine)."""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_tabanlar as TB
import karar_kurali as KK

A.CIKTI = "/tmp/m_uzun"; M.CIKTI = "/tmp/m_uzun"; M.KANIT_BARI = 95.0; A.SEVIYE = (2000, 3500)
B = {**TB.T1, "TEK_GIRIS": "1", "KOM": "0.0005", "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short"}
A.KOLLAR = {"V1_SR12CAP8_TGK5": (B, 4, {2000: M.D8, 3500: M.D2}),
            "V3_P80_TGK5": ({**B, "MERD_PAY": "0.80"}, 4, {2000: M.D8, 3500: M.D2})}


def analiz():
    kol = "V3_P80_TGK5"; gec = {}
    for sev in (2000, 3500):
        n = 0
        for h in (0, 1):
            gk = M.gunluk(f"M357_V1_SR12CAP8_TGK5_{sev}_{h}"); ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
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
