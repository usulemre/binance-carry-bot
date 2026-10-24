#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 482 — DİLİM BAŞINA EMİR vs TEK HESAP ORTALAMA GİRİŞ, PROTOKOL (iki seviye, iki hiza).

Madde 481: canlı bot (TP/kademe/stop Binance'in ortalama entryPrice'ından) motorun dilim başına girişine göre aynı
getiri, Sharpe −0,11, −%5 altı gün 3 → 6. KONTROL = THTG1 (canlının bugünkü davranışı), ADAY = ZSR15P67 (dilim
başına giriş — canlıda her dilim için ayrı reduceOnly TP/kademe emri demek).
KARAR (madde 375): dört şart + P >= %95 iki seviyede → AYAR (canlı bot dilim başına emre çevrilir).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0; A.SEVIYE = (2000, 3500)
A.KOLLAR = {"THTG1": ({**W.T, "TEK_GIRIS": "1"}, 4, {2000: M.D8, 3500: M.D2}),
            "ZSR15P67": (dict(W.T), 4, {2000: M.D8, 3500: M.D2})}


def analiz():
    gec = {}
    for sev in (2000, 3500):
        n = 0
        for h in (0, 1):
            gk = M.gunluk(f"M357_THTG1_{sev}_{h}"); ga = M.gunluk(f"M357_ZSR15P67_{sev}_{h}")
            Kc, Ad = M.olcum("K", gk), M.olcum("DILIM", ga)
            s = KK.gecer_mi(Kc, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
            p, _ = M.bootstrap(gk, ga, n=1000)
            isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
            print(f"DILIM {sev} {h} yillik {Ad.getiri-Kc.getiri:+6.1f} Sh22 {Ad.erken-Kc.erken:+.2f} Sh25 {Ad.gec-Kc.gec:+.2f} "
                  f"dusus {Ad.dusus-Kc.dusus:+.1f} esitR {s['esit_risk']-Kc.getiri:+6.1f} {isr} P {p:5.1f}", flush=True)
            n += int(s["gecer"] and p >= M.KANIT_BARI)
        gec[sev] = n == 2
    print(f"HUKUM DILIM BASINA EMIR: {'AYAR' if all(gec.values()) else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
