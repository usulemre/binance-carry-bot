#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 550 — PRİM TANISI (uzun zemin, /tmp/zu; prim /tmp/premium/prim_4h.pkl).
Her gün (6 barda bir) evren içinde kesitsel Spearman IC:
  hedefler: sonraki 60 sa gerçekleşen funding (fv toplamı), sonraki 5 g fiyat getirisi
  öngörücüler: sk60 (botun sinyali), prim son (bar kapanışı), prim 24 sa ort., prim − sk60 (artık)
Asıl soru: prim, sk60 SABİT tutulunca (kısmi IC) gelecek funding / fiyatı açıklıyor mu? Ayrıca botun seçtiği uçlarda (sk60 üst/alt %10)."""
import pickle, numpy as np, pandas as pd

Z = pickle.load(open("/tmp/zu/zemin.pkl", "rb"))
C = Z["C"]; cv = C.values; fv = Z["ODE"].values; U = Z["uy"].values
S = pickle.load(open("/tmp/zu/sk_bar60.pkl", "rb")).reindex(index=C.index, columns=C.columns).values
p = pd.read_pickle("/tmp/premium/prim_4h.pkl")
PL = p.pivot_table(index="bar", columns="sembol", values="last").reindex(index=C.index, columns=C.columns)
PM = p.pivot_table(index="bar", columns="sembol", values="mean").reindex(index=C.index, columns=C.columns)
P24 = PM.rolling(6, min_periods=4).mean().values; PL = PL.values
print("prim kapsama (evren hücrelerinde):", float(np.isfinite(PL)[U].mean()))


def rk(x): return pd.Series(x).rank(pct=True).values


def kisi(y, x, z):
    """y ile x'in z kontrol edilerek kısmi rank korelasyonu."""
    ry, rx, rz = rk(y), rk(x), rk(z)
    def res(a): b = np.polyfit(rz, a, 1); return a - np.polyval(b, rz)
    return np.corrcoef(res(ry), res(rx))[0, 1]


sat = []
for i in range(200, len(C) - 31, 6):
    m = U[i] & np.isfinite(S[i]) & np.isfinite(PL[i]) & np.isfinite(P24[i]) & np.isfinite(cv[i]) & np.isfinite(cv[i + 30])
    if m.sum() < 30: continue
    ff = np.nansum(fv[i + 1:i + 16][:, m], axis=0); rr = cv[i + 30][m] / cv[i][m] - 1
    s, pl, p24 = S[i][m], PL[i][m], P24[i][m]
    d = dict(t=C.index[i], n=int(m.sum()))
    for ad, x in (("sk", s), ("pl", pl), ("p24", p24)):
        d[f"F_{ad}"] = np.corrcoef(rk(ff), rk(x))[0, 1]; d[f"R_{ad}"] = np.corrcoef(rk(rr), rk(x))[0, 1]
    d["F_p24|sk"] = kisi(ff, p24, s); d["R_p24|sk"] = kisi(rr, p24, s)
    d["F_pl|sk"] = kisi(ff, pl, s); d["R_pl|sk"] = kisi(rr, pl, s)
    # botun short ucu (sk üst %10): prim yüksek mi düşük mü daha iyi?
    ust = s >= np.quantile(s, 0.9)
    if ust.sum() >= 6:
        h = p24[ust] >= np.median(p24[ust])
        d["Sust_F_fark"] = (ff[ust][h].mean() - ff[ust][~h].mean()) * 1e4      # bp, 60 sa
        d["Sust_R_fark"] = (rr[ust][h].mean() - rr[ust][~h].mean()) * 100      # %, 5 g
    alt = s <= np.quantile(s, 0.1)
    if alt.sum() >= 6:
        h = p24[alt] <= np.median(p24[alt])
        d["Lalt_F_fark"] = (ff[alt][h].mean() - ff[alt][~h].mean()) * 1e4
        d["Lalt_R_fark"] = (rr[alt][h].mean() - rr[alt][~h].mean()) * 100
    sat.append(d)
D = pd.DataFrame(sat).set_index("t"); D.to_pickle("/tmp/premium/tani.pkl")
pd.set_option("display.width", 200)
for ad, a, b in (("TÜM", "2020", "2027"), ("2020-21", "2020", "2022"), ("2022-24", "2022", "2025"), ("2025-26", "2025", "2027")):
    x = D.loc[a:b]
    m = x.mean(); t = m / (x.std() / np.sqrt(len(x)))
    print(f"\n== {ad} (gün {len(x)})")
    print(pd.DataFrame({"ort": m, "t": t}).drop("n").round(3).T.to_string())
