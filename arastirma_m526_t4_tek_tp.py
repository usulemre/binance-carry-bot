#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 526 — T4'TE TEK TP (merdivensiz): seviye taraması, kaldıraçsız, uzun zemin (önce ./zemin_sec.sh uzun).

Madde 525: kademe payı 1,00'a kadar monoton → T4 yapısında merdiven yerine tek TP daha iyi. Botta eşdeğeri: CARRY_MERDIVEN=0,
CARRY_MERDIVEN_SHORT=0, CARRY_KAR_AL=x, CARRY_KAR_AL_SHORT=y. KOLLAR (T4 − merdiven): L45S15 (pay 1,00 eşdeğeri, kontrol) ·
L40S15 · L50S15 · L45S12 · L45S18.
ÖN KAYIT (madde 503 ile aynı) T4'e karşı; ayrıca L45S15'in madde 525'teki P100 kolu ile ~aynı çıkması beklenir (eşdeğerlik).
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m509_t4_uzun as B

T4 = B.T4
T = lambda l, s: {**T4, "MERD_ESIK": "0", "MERDS_ESIK": "0", "TPL": l, "TPS": s}
U.KOL = {"U_T1": U.KOL["U_T1"], "U_T3FN30": T4, "U_T4P100": {**T4, "MERD_PAY": "0.999"},
         "U_T4L45S15": T("0.45", "0.15"), "U_T4L40S15": T("0.40", "0.15"), "U_T4L50S15": T("0.50", "0.15"),
         "U_T4L45S12": T("0.45", "0.12"), "U_T4L45S18": T("0.45", "0.18")}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    import arastirma_m499_sreb_durdur as D
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3FN30"]
    print("\n== T4'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T4P100", "U_T4L45S15", "U_T4L40S15", "U_T4L50S15", "U_T4L45S12", "U_T4L45S18"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:11s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
