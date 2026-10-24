#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 503 — T3 (= T1 + short 2 g'de bir + short tavan %8) ÜZERİNDE KIL PAYI EKSENLER, UZUN ZEMİN (önce ./zemin_sec.sh uzun).

T3 en güçlü aday (madde 500-502). Daha önce 2022-26'da kıl payı kalan eksenler bu kez 6 yılda ve T3 üzerinde:
P80 (kademe payı 0,80; T2'nin parçası) · A43 (4L/3S; T2'nin parçası — T2 2020-21'de tutmadı, hangi parçası?) ·
MS18 (short kademe −%18) · GS (short kademe geri alımı).
ÖN KAYIT: T3'e karşı TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0, dd en fazla 1 puan derin
→ T3 üzerine aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T3 = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short"}
U.KOL = {"U_T1": TB.T1, "U_SR12CAP8": T3, "U_T3P80": {**T3, "MERD_PAY": "0.80"}, "U_T3A43": {**T3, "N_L": "4", "N_S": "3"},
         "U_T3MS18": {**T3, "MERDS_ESIK": "0.18"}, "U_T3GS": {**T3, "MERD_GERI": "1", "MERD_GERI_TARAF": "short"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_SR12CAP8"]
    print("\n== T3'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T3P80", "U_T3A43", "U_T3MS18", "U_T3GS"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
