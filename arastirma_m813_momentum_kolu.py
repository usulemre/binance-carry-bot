#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 813 — carry + kesitsel momentum kolu harmanı. Ön kayıt KAR_HARITASI 813. KARAR VERMEZ."""
import numpy as np, pandas as pd
import arastirma_m389_ml_tahmin as A, arastirma_m346_prim as M
import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
C, Fd, uy, X = A.panel(); r1 = C / C.shift(1) - 1
def kol(k):
    g = (C / C.shift(k) - 1).where(uy); rk = g.rank(axis=1); n = g.notna().sum(axis=1)
    lo = rk.le(10, axis=0) & g.notna(); hi = rk.ge(n - 9, axis=0) & g.notna()
    w = (hi.astype(float) / 10 - lo.astype(float) / 10) * 0.5
    W = sum(w.shift(j) for j in range(1, 6)) / 5
    return (W * r1.fillna(0)).sum(axis=1) - (W * Fd.reindex_like(W).fillna(0)).sum(axis=1) - (W - W.shift(1)).abs().sum(axis=1) * 0.0010
Mom = (kol(3) + kol(7)) / 2
M.CIKTI = "/tmp/m783d"; P = sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2
Mom = Mom.reindex(P.index).fillna(0.0)
print(f"momentum kolu tek başına (2021+): Sh {Mom['2021':].mean() / Mom['2021':].std() * np.sqrt(365):.2f} · korelasyon carry {Mom['2021':].corr(P['2021':]):.2f}")
D = pd.read_pickle("/tmp/m810_D.pkl"); kotu = ((D.K - D.F).shift(6).rolling(60, min_periods=40).mean() < 0).reindex(P.index).fillna(False)
for ad, s0 in (("taban P3T2", P), ("w 0,20", 0.80 * P + 0.20 * Mom), ("w 0,35", 0.65 * P + 0.35 * Mom)):
    s = s0[:"2026-10-31"]; o = T.olc(s); kk, er = Z.esit(s.reindex(Z.P.index).dropna())
    yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100); ek = ((1 + s0["2026-10-01":"2026-11-16"] * 1.15).prod() - 1) * 100
    print(f"{ad:11s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} / 2025+ {Z.sh(s['2025-01-01':]):.2f} · "
          f"eşit risk {er:.1f} (doz {kk:.2f}) | " + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()) + f" | Eki-16Kas {ek:+.1f} | kötü rejim günü ort {s0[kotu].mean() * 115:+.3f}%")
