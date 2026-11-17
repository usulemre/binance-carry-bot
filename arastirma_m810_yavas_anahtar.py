#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 810 — yavaş rejim anahtarı (60 g gerçekleşmiş K − F < 0 → F). Ön kayıt KAR_HARITASI 810. KARAR VERMEZ."""
import pickle
import numpy as np, pandas as pd
import arastirma_m389_ml_tahmin as A
C, Fd, uy, X = A.panel()
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; H4 = pickle.load(open("/tmp/hlo.pkl", "rb"))["H"].reindex_like(C4)
sec = C4.index.hour == 0
fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]
c5 = C.shift(-5) / C - 1; fon = Fd.rolling(5).sum().shift(-5)
pay = (pd.DataFrame(np.where(fmax.values >= C.values * 1.45, 0.45, c5.values), index=C.index, columns=C.columns) - fon).where(uy).clip(-0.9, 0.45)
LS = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))["count_long_short_ratio"].reindex_like(C4)[sec].reindex_like(C)
F3 = X["fon3"]; sat = []
for t in C.index[C.index >= "2022-02-23"]:
    f = F3.loc[t]; p = pay.loc[t]; ok = f.notna() & p.notna() & uy.loc[t]
    if ok.sum() < 40: continue
    hav = f[ok].nsmallest(16); l = LS.loc[t].reindex(hav.index).dropna()
    if len(l) < 8: continue
    sat.append((t, p[l.nsmallest(4).index].mean(), p[hav.nsmallest(4).index].mean(), p[hav.index].mean()))
D = pd.DataFrame(sat, columns=["t", "K", "F", "H"]).set_index("t"); D.to_pickle("/tmp/m810_D.pkl")
g = (D.K - D.F).shift(6).rolling(60, min_periods=40).mean()
kap = g < 0; D["anahtar"] = np.where(kap, D.F, D.K); D["kapali"] = kap
t = (D[["K", "F", "H", "anahtar"]] * 100).groupby(D.index.year).mean(); t["kapalı gün %"] = D.groupby(D.index.year).kapali.mean() * 100
t.loc["tümü"] = list((D[["K", "F", "H", "anahtar"]] * 100).mean()) + [D.kapali.mean() * 100]
e = D["2026-10-01":]; t.loc["Eki-Kas 26"] = list((e[["K", "F", "H", "anahtar"]] * 100).mean()) + [e.kapali.mean() * 100]
print(t.round(2).to_string())
bas = D.index[kap & ~kap.shift(1, fill_value=False)]; print("kapalı dönem başlangıçları:", [d.strftime("%Y-%m-%d") for d in bas])
fk = t["anahtar"] - t["K"]; yil = fk.loc[[y for y in t.index if isinstance(y, (int, np.integer))]]
gec = fk.loc["tümü"] >= 0.2 and (yil > -0.3).all()
print("anahtar − K:", " ".join(f"{i}:{v:+.2f}" for i, v in fk.items()), "→ KAPI", "GEÇTİ" if gec else "GEÇMEDİ")
