#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 564 — SHORT TAVANI GERÇEKÇİ KOŞULDA (madde 563) — ayrıca madde 561: HAM KÂR KOLLARI GERÇEKÇİ KOŞULDA (canlı gibi tek hesap girişi + 5 bp, MERD_SIRA=1, uzun zemin, 2.000 $ D8 ve 3.500 $ D2,
iki hiza ortalaması). Kullanıcı hedefi: yalnız ham kâr, kaldıraçsız (madde 560). T4 = W4_TGK5 (madde 530 önbelleği)."""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_tabanlar as TB
import arastirma_m497_uzun_gecmis as U

A.CIKTI = "/tmp/m_uzun"; M.CIKTI = "/tmp/m_uzun"; A.SEVIYE = (2000, 3500)
B = {**TB.T1, "TEK_GIRIS": "1", "KOM": "0.0005", "MERD_SIRA": "1"}
T4 = {**B, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
NL = {**T4, "MERD_ESIK": "0", "MERDS_ESIK": "0"}
K1 = {**NL, "REZERV": "0"}; K2 = {**K1, "TPL": "1.00"}; K3 = {**K2, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl"}
EV = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"W4_TGK5": (T4, 4, EV), "WK3_TGK5": (K3, 4, EV), "WK3C100_TGK5": ({**K3, "CAP_ORTAK": "1.0"}, 4, EV),
            "WK3C12_TGK5": ({**K3, "CAP_ORTAK": "0.12"}, 4, EV), "W4C100_TGK5": ({**T4, "CAP_ORTAK": "1.0"}, 4, EV),
            "W4C12_TGK5": ({**T4, "CAP_ORTAK": "0.12"}, 4, EV)}


def ham():
    for sev in (2000, 3500):
        print(f"\n== {sev} $ (iki hiza ortalaması)")
        b = None
        for k in A.KOLLAR:
            x = (M.gunluk(f"M357_{k}_{sev}_0") + M.gunluk(f"M357_{k}_{sev}_1")) / 2
            if b is None: b = x
            o = U.olc(x); yy = " ".join(f"{(1+x[str(y)]).prod()*100-100:+5.0f}" for y in range(2020, 2027))
            print(f"{k:9s} {o[0]:+7.1f} Sh {o[1]:4.2f} dd {o[2]:6.1f} enk {o[3]:6.2f} −%5 {o[4]:2d} −%3 {int((x<-0.03).sum()):3d} | {yy}")
        v = x.std() / b.std(); print(f"T4 × {v:.2f} (K3 oynaklığında): yıllık {U.olc(b*v)[0]:+.1f}, −%5 {U.olc(b*v)[4]}")


if __name__ == "__main__":
    {"kos": A.kos, "ham": ham}[sys.argv[1]]()
