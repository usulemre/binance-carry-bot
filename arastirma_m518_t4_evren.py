#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 518 — T4 ÜZERİNDE EVREN PARAMETRELERİ 6 YILDA (kaldıraçsız, uzun zemin; önce ./zemin_sec.sh uzun).

Hacim eşiği 70M, yaş 60 g ve pompa filtresi kapalı — üçü de 2022-26'da seçildi (madde 429/433/447). Evren tabanıyla
birlikte 6 yılda: H50 / H100 (hacim 50M / 100M) · Y90 (yaş 90 g) · UC40 (pompa filtresi 0,40).
ÖN KAYIT (madde 503 ile aynı, T4'e karşı): TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0, dd en
fazla 1 puan derin → aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T4 = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
U.KOL = {"U_T1": TB.T1, "U_T3FN30": T4, "U_T4H50": {**T4, "HACIM_ESIK": "5e7"}, "U_T4H100": {**T4, "HACIM_ESIK": "1e8"},
         "U_T4Y90": {**T4, "YAS_GUN": "90"}, "U_T4UC40": {**T4, "UCELE": "0.40"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3FN30"]
    print("\n== T4'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T4H50", "U_T4H100", "U_T4Y90", "U_T4UC40"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
