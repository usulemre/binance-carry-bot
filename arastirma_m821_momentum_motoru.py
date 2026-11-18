#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 821 — momentum motoru: 27 varyant, tasarım 2021-24 / doğrulama 2025-26. Ön kayıt KAR_HARITASI 821. KARAR VERMEZ."""
import itertools
import numpy as np, pandas as pd
import arastirma_m389_ml_tahmin as A, arastirma_m346_prim as M
C, Fd, uy, X = A.panel(); r1 = (C / C.shift(1) - 1).fillna(0); Fz = Fd.reindex_like(C).fillna(0)
def kol(k, tut, n_):
    g = (C / C.shift(k) - 1).where(uy); rk = g.rank(axis=1); n = g.notna().sum(axis=1)
    lo = rk.le(n_, axis=0) & g.notna(); hi = rk.ge(n - n_ + 1, axis=0) & g.notna()
    w = (hi.astype(float) / n_ - lo.astype(float) / n_) * 0.5; W = sum(w.shift(j) for j in range(1, tut + 1)) / tut
    return (W * r1).sum(axis=1) - (W * Fz).sum(axis=1) - (W - W.shift(1)).abs().sum(axis=1) * 0.0010
sh = lambda x: x.mean() / x.std() * np.sqrt(365)
T = slice("2021-01-01", "2024-12-31"); V = slice("2025-01-01", "2026-11-16")
sonuc = {}
for k, tut, n_ in itertools.product((3, 7, 14), (3, 5, 10), (5, 10, 20)):
    s = kol(k, tut, n_); sonuc[(k, tut, n_)] = s
    print(f"k {k:2d} tut {tut:2d} n {n_:2d}: tasarım Sh {sh(s[T]):+.2f} · doğrulama Sh {sh(s[V]):+.2f}", flush=True)
en = max(sonuc, key=lambda a: sh(sonuc[a][T])); m = sonuc[en]
print(f"\nSEÇİLEN (yalnız tasarımla): k {en[0]} tut {en[1]} n {en[2]} — tasarım Sh {sh(m[T]):.2f} · doğrulama Sh {sh(m[V]):.2f} · Eki-16Kas {((1 + m['2026-10-01':]).prod() - 1) * 100:+.1f}%")
dv = pd.Series({a: sh(s[V]) for a, s in sonuc.items()}); print(f"doğrulama Sh dağılımı (27 varyant): medyan {dv.median():.2f} · seçilenin sırası {int((dv > dv[en]).sum()) + 1}/27")
M.CIKTI = "/tmp/m783d"; P = sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2
mm = m.reindex(P.index).fillna(0); H = 0.8 * P + 0.2 * mm
for ad, x in (("P3T2", P[V]), ("harman w 0,20", H[V])):
    e = (1 + x * 1.15).cumprod(); dd = (e / e.cummax() - 1).min() * 100
    print(f"doğrulama {ad:14s} Sh {sh(x):.2f} · maks dd (×1,15) {dd:.1f} · getiri (×1,15) {(e.iloc[-1] - 1) * 100:+.0f}% · Eki-16Kas {((1 + x['2026-10-01':] * 1.15).prod() - 1) * 100:+.1f}%")
a = sh(m[V]) >= 0.8; b = (sh(H[V]) - sh(P[V]) >= 0.2)
e1 = (1 + P[V] * 1.15).cumprod(); e2 = (1 + H[V] * 1.15).cumprod(); b = b and (e2 / e2.cummax() - 1).min() > (e1 / e1.cummax() - 1).min()
print("ÖLÇÜT:", "İKİNCİ MOTOR ADAYI" if (a and b) else "RED", f"(a {a}, b {b})")
