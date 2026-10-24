#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 506 — T3f (= T3 + kademe payı 0,80) ÜZERİNDE DEFANS/ÇIKIŞ EKSENLERİ, UZUN ZEMİN (önce ./zemin_sec.sh uzun).

24 sa düşüş stop'u (madde 449-453) ve long kademe seviyesi yalnız 2022-26'da ayarlandı; 2020-21'de 2021-05-19 gibi −%13,6
bir gün var. KOLLAR: S0 (24 sa stop KAPALI — kullanıcı "neden ekledin" diye sormuştu) · S35 (stop −%35) · M40 / M50
(long kademe +%40 / +%50).
ÖN KAYIT (madde 503 ile aynı, T3f'ye karşı): TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0,
dd en fazla 1 puan derin → aday. Ayrıca en kötü gün ve −%5 altı gün raporlanır.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T3F = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80"}
U.KOL = {"U_T1": TB.T1, "U_T3P80": T3F, "U_T3FS0": {**T3F, "SLL24": "0"}, "U_T3FS35": {**T3F, "SLL24": "0.35"},
         "U_T3FM40": {**T3F, "MERD_ESIK": "0.40"}, "U_T3FM50": {**T3F, "MERD_ESIK": "0.50"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3P80"]
    print("\n== T3f'ye karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T3FS0", "U_T3FS35", "U_T3FM40", "U_T3FM50"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
