#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 514 — T4 ÜZERİNDE TARAF BAZLI FUNDING BÜYÜKLÜĞÜ AĞIRLIĞI, UZUN ZEMİN (önce ./zemin_sec.sh uzun).

Funding büyüklüğüyle ağırlık iki tarafta gizli kaldıraçtı (madde 457: long pompa coinlerine yığılıyor). Short tarafı
hiç ayrı ölçülmedi: T4'te short tarafı tavanlı (%8) ve sık yenileniyor → ağırlık yalnız orada. KOLLAR: SG05 / SG10
(short |funding|^0,5 / ^1,0) · LG05 (yalnız long ^0,5, kontrol).
ÖN KAYIT (madde 503 ile aynı, T4'e karşı): TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0, dd en
fazla 1 puan derin → aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T4 = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
W = lambda g, t: {"AGIRLIK": "buyukluk", "SK_GAMMA": g, "SK_TARAF": t}
U.KOL = {"U_T1": TB.T1, "U_T3FN30": T4, "U_T4SG05": {**T4, **W("0.5", "short")}, "U_T4SG10": {**T4, **W("1.0", "short")},
         "U_T4LG05": {**T4, **W("0.5", "long")}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3FN30"]
    print("\n== T4'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T4SG05", "U_T4SG10", "U_T4LG05"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        # eşit oynaklık (gizli kaldıraç denetimi): TÜM dönem
        x = S[k]; g = U.olc(b * (x.std() / b.std()))[0]; print(f"    {k} eşit oynaklıkta T4: {U.olc(x)[0]-g:+.1f}")
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
