#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 517 — T4 ÜZERİNDE SON TP SEVİYELERİ 6 YILDA (kaldıraçsız, uzun zemin; önce ./zemin_sec.sh uzun).

Son kâr al seviyeleri (long +%60, short −%20) 2022-26'da seçildi ve kademe payı 0,80 ile kalan pay artık ⅕.
KOLLAR: TPL70 / TPL50 (long son TP) · TPS25 / TPS17 (short son TP; short kademesi −%15'in üstünde kalmalı).
ÖN KAYIT (madde 503 ile aynı, T4'e karşı): TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0, dd en
fazla 1 puan derin → aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T4 = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
U.KOL = {"U_T1": TB.T1, "U_T3FN30": T4, "U_T4TPL70": {**T4, "TPL": "0.70"}, "U_T4TPL50": {**T4, "TPL": "0.50"},
         "U_T4TPS25": {**T4, "TPS": "0.25"}, "U_T4TPS17": {**T4, "TPS": "0.17"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3FN30"]
    print("\n== T4'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T4TPL70", "U_T4TPL50", "U_T4TPS25", "U_T4TPS17"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
