#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 764 — long zarar otopsisi (betimsel, motor koşusu YOK). Backtest defteri (711, P3T2, iki hiza ortalaması, ×1,15):
long tarafının 5 günlük fiyat katkısı kitabın ≤ −%7,5'i olan dönemlerde kayıp kaç coinden geliyor, sonra ne oluyor."""
import pickle, numpy as np, pandas as pd
import arastirma_m346_prim as M

G = pd.concat([pickle.load(open(f"/tmp/m711/gk_{h}.pkl", "rb")).assign(h=h) for h in (0, 1)])
G["gun"] = pd.to_datetime(G["gun"]); G = G[G["gun"] <= "2026-10-31"]
L = G.groupby(["gun", "sembol"])["fiyat_long_top"].sum() / 2 * 1.15 * 100          # % kitap, coin-gün
Lg = L.groupby(level=0).sum()
M.CIKTI = "/tmp/m_ekim"; r = (sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2)[:"2026-10-31"] * 1.15
L5 = Lg.rolling(5).sum()
m = L5 <= -7.5; ilk = m & ~m.shift(1, fill_value=False)
rows = []
for t in L5.index[ilk]:
    p = L.loc[t - pd.Timedelta(days=4):t].groupby(level=1).sum().sort_values()
    kay = p[p < 0]; top = -kay.sum()
    i = r.index.get_loc(t) if t in r.index else None
    if i is None or i + 15 >= len(r):
        continue
    rows.append({"gün": t.date(), "long 5g %": round(L5[t], 1), "zarar eden coin": len(kay),
                 "ilk coin payı %": round(-kay.iloc[0] / top * 100), "ilk 3 payı %": round(-kay.iloc[:3].sum() / top * 100),
                 "ilk coin": kay.index[0].replace("USDT", ""),
                 "aynı 5g toplam %": round(((1 + r.iloc[i - 4:i + 1]).prod() - 1) * 100, 1),
                 "sonraki 15g toplam %": round(((1 + r.iloc[i + 1:i + 16]).prod() - 1) * 100, 1),
                 "sonraki 15g long %": round(Lg.loc[t + pd.Timedelta(days=1):t + pd.Timedelta(days=15)].sum(), 1)})
T = pd.DataFrame(rows)
pd.set_option("display.width", 250); print(T.to_string(index=False))
print("\nmedyan:", T.drop(columns=["gün", "ilk coin"]).median().round(1).to_dict())
yog = T["ilk 3 payı %"] >= 60
for ad, s in (("yoğun (ilk 3 ≥ %60)", T[yog]), ("dağınık", T[~yog])):
    print(f"{ad}: n {len(s)} · sonraki 15g toplam medyan {s['sonraki 15g toplam %'].median():+.1f}% · artı %{(s['sonraki 15g toplam %'] > 0).mean() * 100:.0f} · "
          f"sonraki 15g long medyan {s['sonraki 15g long %'].median():+.1f}%")
