#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 467 — SHORT MERDİVENİ SR15 PROTOKOL + birleşim (P67).

Madde 466: short merdiveni (short'un yarısı −%10/−%12/−%15'te, kalanı −%20'de) üçü de Sharpe 3,72-3,74
(taban 3,66), dd −20,6 → −15,3..−18,3; SR15 ön kaydı geçti (IS +10, OOS +2, eşit oynaklık +8,4).
P67 (long'un 2/3'ü +%45'te) eşit oynaklık +8,2.
KOLLAR: SR15 iki seviye (protokol, kontrol XMR45) · SR15P67 · SR12P67 (2.000 $, bilgi).
KARAR (madde 375): dört şart + P >= %95 iki seviyede → AYAR.
"""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import arastirma_m466_cikis2 as Z
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0; A.SEVIYE = (2000, 3500)
T = Z.T
A.KOLLAR = {"ZSR15": ({**T, "MERDS_ESIK": "0.15"}, 4, {2000: M.D8, 3500: M.D2}),
            "ZSR15P67": ({**T, "MERDS_ESIK": "0.15", "MERD_PAY": "0.667"}, 4, {2000: M.D8}),
            "ZSR12P67": ({**T, "MERDS_ESIK": "0.12", "MERD_PAY": "0.667"}, 4, {2000: M.D8})}
_o = A.tek
A.tek = lambda kol, sev, h: (f"M357_{kol}_{sev}_{h}", "atlandi") if sev not in A.KOLLAR[kol][2] else _o(kol, sev, h)


def analiz():
    Z.A.KOLLAR = {k: v for k, v in A.KOLLAR.items() if k != "ZSR15"}
    Z.analiz()
    print()
    gec = {}
    for sev in (2000, 3500):
        n = 0
        for h in (0, 1):
            gk = M.gunluk(f"M357_XMR45_{sev}_{h}"); ga = M.gunluk(f"M357_ZSR15_{sev}_{h}")
            Kc, Ad = M.olcum("K", gk), M.olcum("SR15", ga)
            s = KK.gecer_mi(Kc, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
            p, _ = M.bootstrap(gk, ga, n=1000)
            isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
            print(f"SR15 {sev} {h} yillik {Ad.getiri-Kc.getiri:+6.1f} Sh22 {Ad.erken-Kc.erken:+.2f} Sh25 {Ad.gec-Kc.gec:+.2f} "
                  f"dusus {Ad.dusus-Kc.dusus:+.1f} esitR {s['esit_risk']-Kc.getiri:+6.1f} {isr} P {p:5.1f}", flush=True)
            n += int(s["gecer"] and p >= M.KANIT_BARI)
        gec[sev] = n == 2
    print(f"HUKUM SR15: {'AYAR' if all(gec.values()) else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
