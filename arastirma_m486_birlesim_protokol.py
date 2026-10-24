#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 486 — BİRLEŞİM PROTOKOLÜ: P80+CAP+A43 ve P80+A43 vs canlı taban ZSR15P67 (iki seviye, iki hiza).
KARAR (madde 375): dört şart + P >= %95 iki seviyede → AYAR."""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W
import arastirma_m485_birlesik as B
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0; A.SEVIYE = (2000, 3500)
A.KOLLAR = {k: (B.A.KOLLAR[k][0], 4, {2000: M.D8, 3500: M.D2}) for k in ("BRP80_CAP_A43", "BRP80_A43")}
A.KOLLAR["ZSR15P67"] = (dict(W.T), 4, {2000: M.D8, 3500: M.D2})


def analiz():
    for kol in ("BRP80_CAP_A43", "BRP80_A43"):
        gec = {}
        for sev in (2000, 3500):
            n = 0
            for h in (0, 1):
                gk = M.gunluk(f"M357_ZSR15P67_{sev}_{h}"); ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
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
