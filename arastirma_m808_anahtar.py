#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 808 — ML anahtar: kalabalık filtresi açık / kapalı (kapı teşhisi). Ön kayıt KAR_HARITASI 808. KARAR VERMEZ."""
import pickle
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
import arastirma_m389_ml_tahmin as A, arastirma_m801_ml_rejim as RJ
C, Fd, uy, X = A.panel()
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; H4 = pickle.load(open("/tmp/hlo.pkl", "rb"))["H"].reindex_like(C4)
sec = C4.index.hour == 0
fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]
c5 = C.shift(-5) / C - 1; fon = Fd.rolling(5).sum().shift(-5)
pay = (pd.DataFrame(np.where(fmax.values >= C.values * 1.45, 0.45, c5.values), index=C.index, columns=C.columns) - fon).where(uy).clip(-0.9, 0.45)
LS = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))["count_long_short_ratio"].reindex_like(C4)[sec].reindex_like(C)
F3 = X["fon3"]; sat = []
for t in C.index[C.index >= "2021-01-01"]:
    f = F3.loc[t]; p = pay.loc[t]; ok = f.notna() & p.notna() & uy.loc[t]
    if ok.sum() < 40: continue
    hav = f[ok].nsmallest(16); l = LS.loc[t].reindex(hav.index).dropna()
    if len(l) < 8: continue
    sat.append((t, p[l.nsmallest(4).index].mean(), p[hav.nsmallest(4).index].mean(), p[hav.index].mean()))
D = pd.DataFrame(sat, columns=["t", "K", "F", "H"]).set_index("t")
f = RJ.ozellik().reindex(D.index)
fark = (D.K - D.F).shift(6); f["kf30"] = fark.rolling(30, min_periods=10).mean(); f["kf90"] = fark.rolling(90, min_periods=30).mean()
y = D.K - D.F; tah = pd.Series(np.nan, index=D.index)
for yil in range(2022, 2027):
    bas = pd.Timestamp(f"{yil}-01-01"); e = (D.index < bas - pd.Timedelta(days=6)) & y.notna()
    te = (D.index >= bas) & (D.index < pd.Timestamp(f"{yil + 1}-01-01"))
    fk = f.replace([np.inf, -np.inf], np.nan); kol = [c for c in fk.columns if fk.loc[e, c].notna().mean() > 0.5]
    m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=50, l2_regularization=1.0, random_state=808)
    m.fit(fk.loc[e, kol].values, y[e].values); tah[te] = m.predict(fk.loc[te, kol].values)
S = D[D.index >= "2022-01-01"].copy(); S["anahtar"] = np.where(tah.reindex(S.index) < 0, S.F, S.K); S["F_günü"] = (tah.reindex(S.index) < 0)
t2 = (S[["K", "F", "H", "anahtar"]] * 100).groupby(S.index.year).mean(); t2["F seçilen gün %"] = S.groupby(S.index.year)["F_günü"].mean() * 100
t2.loc["2022-26"] = list((S[["K", "F", "H", "anahtar"]] * 100).mean()) + [S.F_günü.mean() * 100]
e2 = S["2026-10-01":"2026-11-10"]; t2.loc["Eki-10Kas"] = list((e2[["K", "F", "H", "anahtar"]] * 100).mean()) + [e2.F_günü.mean() * 100]
print(t2.round(2).to_string())
fk_ = t2["anahtar"] - t2["K"]; n = sum(fk_.loc[[2024, 2025, 2026]] >= 0.3); gec = n >= 2 and fk_.loc["2022-26"] >= 0.3
print("anahtar − K:", " ".join(f"{i}:{v:+.2f}" for i, v in fk_.items()), f"→ 2024-26 {n}/3 · KAPI {'GEÇTİ' if gec else 'GEÇMEDİ'}")
