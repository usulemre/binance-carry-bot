#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 805 — ML koşullu uzatma, KAPI teşhisi. Ön kayıt KAR_HARITASI 805. KARAR VERMEZ."""
import pickle
import numpy as np, pandas as pd
import arastirma_m389_ml_tahmin as A
C, Fd, uy, X = A.panel()
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; H4 = pickle.load(open("/tmp/hlo.pkl", "rb"))["H"].reindex_like(C4)
sec = C4.index.hour == 0
fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]
c5 = C.shift(-5) / C - 1; fon = Fd.rolling(5).sum().shift(-5)
pay = (pd.DataFrame(np.where(fmax.values >= C.values * 1.45, 0.45, c5.values), index=C.index, columns=C.columns) - fon).where(uy).clip(-0.9, 0.45)
V4 = pickle.load(open("/tmp/m804/veto.pkl", "rb")); V = V4[sec].reindex_like(C)          # V yüksek = asimetri lehte
F3 = X["fon3"]
dolan = (F3.shift(5) <= 0.10) & (C < C.shift(5)) & uy & pay.notna() & V.notna()
yeni = (F3 <= 0.10) & uy & pay.notna()
gec = 0
for yil in range(2022, 2027):
    ix = C.index.year == yil
    Vd = V[ix].where(dolan[ix]); esik = Vd.quantile(0.80, axis=1)
    sec_ = Vd.ge(esik, axis=0) & dolan[ix]
    a = pay[ix][sec_].stack(); b = pay[ix][yeni[ix]].stack(); hep = pay[ix][dolan[ix]].stack()
    f = (a.mean() - b.mean()) * 100; ok = f >= 1.0; gec += ok
    print(f"{yil}: uzatılacak (ML en iyi %20, n {len(a)}) {a.mean() * 100:+.2f}% · tüm dolan zarardaki (n {len(hep)}) {hep.mean() * 100:+.2f}% · yeni aday (n {len(b)}) {b.mean() * 100:+.2f}% · fark {f:+.2f} {'✓' if ok else '✗'}")
print(f"KAPI: {gec}/5 → " + ("GEÇTİ → 806 motor ön kaydı" if gec >= 4 else "GEÇMEDİ → eksen kapanır"))
