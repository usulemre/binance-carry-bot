#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 507 — GÖRELİ EVREN (hacimde ilk K, HACIM_SIRA) T3f üzerinde, UZUN ZEMİN (önce ./zemin_sec.sh uzun).

70M mutlak hacim eşiği piyasa büyüklüğüne uyarlanmıyor: uygun coin ortalaması 2020 5,3 · 2021 50,9 · 2024 66,2 · 2026 38,0
(2020'de kitap neredeyse hiç işlem yapamadı). Evren = yaş/donuk/tradfi şartını geçenler arasında hacimde ilk K
(taban 20M). KOLLAR: K40 / K60 / K80.
ÖN KAYIT (madde 503 ile aynı, T3f'ye karşı): TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0,
dd en fazla 1 puan derin → aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T3F = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80"}
U.KOL = {"U_T1": TB.T1, "U_T3P80": T3F, "U_T3FK40": {**T3F, "HACIM_SIRA": "40"}, "U_T3FK60": {**T3F, "HACIM_SIRA": "60"},
         "U_T3FK80": {**T3F, "HACIM_SIRA": "80"},
         "U_T3FN30": {**T3F, "HACIM_MIN_EVREN": "30"}, "U_T3FN40": {**T3F, "HACIM_MIN_EVREN": "40"}}   # madde 508
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3P80"]
    print("\n== T3f'ye karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T3FK40", "U_T3FK60", "U_T3FK80", "U_T3FN30", "U_T3FN40"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
