#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 400 — OLAY MOTORU IZGARASI (olay_motoru.py), ÖN KAYITLI.

Izgara (96 kol): saat {03, 07 TRT} x X {%30, %50} x H {1, 3, 7} x stop {%25, yok}
x NMAX {10, 20} x yön {iki, short}; filtre FON sabit.
SEÇİM yalnız IS (2022-04..2024-12) portföy Sharpe'ıyla; IS'te en iyi 3 kol OOS'ta
(2025-01..2026-08) raporlanır. KABUL (harman turuna): OOS Sh >= 1,0, OOS gün-t >= 2,
tam düşüş >= −%30, carry ile rho <= 0,30.
ŞEFFAFLIK: geriye dönük (tüm dönem) en iyi kol da yazılır — seçim yanlılıklı,
karar için kullanılmaz.
"""
import itertools
import sys
import numpy as np
import olay_motoru as OM
import arastirma_m346_prim as M

def main():
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    S = []
    for sa, X, H, st, n, yon in itertools.product((0, 4), (0.30, 0.50), (1, 3, 7), (0.25, 0.0), (10, 20), ("iki", "short")):
        r = OM.olc(OM.Ayar(sa, X, H, st, n, yon, "FON"))
        ix = r["g"].index.intersection(carry.index)
        r["rho"] = float(np.corrcoef(r["g"].loc[ix], carry.loc[ix])[0, 1])
        S.append(r)
        print(f"{r['ad']:<34} n {r['n']:>4} ort {r['ort']:+5.2f} med {r['med']:+5.2f} | IS Sh {r['shIS']:+5.2f} yil {r['yilIS']:+6.1f} | "
              f"OOS Sh {r['shOOS']:+5.2f} yil {r['yilOOS']:+6.1f} gun-t {r['tgunOOS']:+5.2f} | dusus {r['dd']:6.1f} rho {r['rho']:+.2f}", flush=True)
    print("\nIS'TE SECILEN 3 KOL:")
    for r in sorted(S, key=lambda x: -(x["shIS"] if np.isfinite(x["shIS"]) else -9))[:3]:
        k = r["shOOS"] >= 1.0 and r["tgunOOS"] >= 2 and r["dd"] >= -30 and r["rho"] <= 0.30
        print(f"  {r['ad']:<34} IS Sh {r['shIS']:+.2f} -> OOS Sh {r['shOOS']:+.2f} yil {r['yilOOS']:+.1f} gun-t {r['tgunOOS']:+.2f} dusus {r['dd']:.1f} -> {'HARMAN TURUNA' if k else 'RED'}")
    print("\nSEFFAFLIK - tum donemde en iyi 3 (secim yanlilikli, karar icin DEGIL):")
    for r in sorted(S, key=lambda x: -(x["yil"] if np.isfinite(x["yil"]) else -999))[:3]:
        print(f"  {r['ad']:<34} yillik {r['yil']:+.1f} IS {r['yilIS']:+.1f} OOS {r['yilOOS']:+.1f} dusus {r['dd']:.1f}")

if __name__ == "__main__":
    main()
