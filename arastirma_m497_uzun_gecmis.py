#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 497 — UZUN GEÇMİŞ SINAVI: 2020-07 → 2021-12 (hiç görülmemiş 18 ay) + 2022-26.

Zemin `VERI_EK=uzun BAS_YIL=2020 python3 yeniden_kur.py` + `VERI_EK=uzun PEN=60 AD=bar60 python3 canli_sinyal_kur.py`
ile kuruldu (yedek: /tmp/zu; 2022+ zemini /tmp/z22 — 2022+ fiyat paneli birebir aynı). Kalabalık (ls) oranı Binance'te
2021-12 öncesi yok → o dönemde long/short seçimi funding sırasıyla (her kolda aynı, karşılaştırma adil).
KOLLAR: T1 (şu anki bot) · T2 (2. aday) · T1+SR6 / T1+SR12 (short ara dengelemesi) · T2+SR6 · M0 (merdivensiz:
T60 + 24 sa stop, merdivenin kendisinin kontrolü).
ÖN KAYIT (koşudan önce): YENİ dönemde (2020-07..2021-12) aday, tabanını yıllıkta ve eşit oynaklıkta geçerse "YENİ
DÖNEMDE TUTTU"; geçemezse "2022-26'ya özel". Merdiven (M0'a karşı T1) aynı şekilde.
KULLANIM: önce zemini seç (`zemin_sec.sh uzun`), sonra kos/analiz; bitince `zemin_sec.sh 22`.
"""
import sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_tabanlar as TB

CIKTI = "/tmp/m_uzun"
import os; os.makedirs(CIKTI, exist_ok=True)
A.CIKTI = CIKTI; M.CIKTI = CIKTI; A.SEVIYE = (2000,)
M0 = {k: v for k, v in TB.T1.items() if k not in ("MERD_ESIK", "MERD_PAY", "MERDS_ESIK")}
KOL = {"U_T1": TB.T1, "U_T2": TB.T2, "U_T1SR6": {**TB.T1, "S_REB": "6"}, "U_T1SR12": {**TB.T1, "S_REB": "12"},
       "U_T2SR6": {**TB.T2, "S_REB": "6"}, "U_M0": M0}
A.KOLLAR = {k: (v, 4, {2000: M.D8}) for k, v in KOL.items()}


def seri(ad):
    return (M.gunluk(f"M357_{ad}_2000_0") + M.gunluk(f"M357_{ad}_2000_1")) / 2


def olc(g):
    yil = ((1 + g).prod() ** (365.25 / len(g)) - 1) * 100
    e = (1 + g).cumprod(); dd = ((e / e.cummax()) - 1).min() * 100
    return yil, g.mean() / g.std() * np.sqrt(365.25), dd, g.min() * 100, int((g < -0.05).sum())


def analiz():
    DON = [("YENİ 2020-07..2021-12", "2020-01-01", "2022-01-01"), ("2022-07..2024", "2022-07-20", "2025-01-01"),
           ("2025-26", "2025-01-01", "2027-01-01")]
    S = {k: seri(k) for k in KOL}
    print("ilk gün:", S["U_T1"].index[0].date())
    for ad, a, b in DON:
        print(f"\n== {ad}")
        print(f"  {'kol':10s} {'yıllık':>8s} {'Sh':>5s} {'dd':>6s} {'enkötü':>7s} {'-5%':>4s} | vs taban: {'yıl':>7s} {'eşitVol':>8s}")
        for k, g in S.items():
            x = g[(g.index >= a) & (g.index < b)]
            tb = {"U_T1": "U_M0", "U_T2": "U_T1", "U_T1SR6": "U_T1", "U_T1SR12": "U_T1", "U_T2SR6": "U_T2", "U_M0": None}[k]
            y, sh, dd, mn, g5 = olc(x)
            s = f"  {k:10s} {y:+8.1f} {sh:5.2f} {dd:6.1f} {mn:7.2f} {g5:4d}"
            if tb:
                bx = S[tb][(S[tb].index >= a) & (S[tb].index < b)]
                yb = olc(bx)[0]; e = y - olc(bx * (x.std() / bx.std()))[0]
                s += f" | {tb[2:]:>5s} {y-yb:+7.1f} {e:+8.1f}"
            print(s)


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
