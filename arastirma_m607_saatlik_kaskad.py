#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 607 — "GÜNLÜK KİTAP" 2: SAATLİK piyasa kaskadı sonrası tepki (madde 354/418 GÜNLÜK ölçekte RED; saatlik hiç ölçülmedi).
Olay: eşit ağırlıklı sepetin (100 likit sembol) 1 saatlik getirisi ≤ −X (çöküş) ya da ≥ +X (sıçrama). Tepki: sonraki H saat sepeti
ters yönde (çöküşte long / sıçramada short) ya da aynı yönde (devam) tut. Maliyet 10 bp gidiş-dönüş. Kümelenme: aynı olay H saat içinde
tekrar tetiklenmez. t gün kümesinde (madde 395'in yasası).
ÖN KAYIT: X ∈ {%2, %3, %4}, H ∈ {1, 4, 12, 24}, 2 yön × 2 olay türü = 48 kol. IS 2024, OOS 2025-01..2026-08. ADAY: IS'te seçilen birinci
kol OOS'ta işlem başı ortalama > 0 ve gün kümesi t ≥ 2 ve OOS olay sayısı ≥ 20; ayrıca IS↔OOS ortalama sırası korelasyonu raporlanır.
"""
import pickle
import numpy as np, pandas as pd
P = pickle.load(open("/tmp/saat_panel.pkl", "rb")); C = P["C"]
R = C.pct_change(); R = R.where(R.abs() < 0.5); s = R.mean(axis=1).fillna(0.0)
MAL = 0.0010
kayit = []
for olay in ("cokus", "sicrama"):
    for X in (0.02, 0.03, 0.04):
        tet = (s <= -X) if olay == "cokus" else (s >= X)
        for H in (1, 4, 12, 24):
            for tepki in ("ters", "devam"):
                yon = (1 if olay == "cokus" else -1) * (1 if tepki == "ters" else -1)
                islem = []; son = -10**9
                idx = np.flatnonzero(tet.values)
                for i in idx:
                    if i <= son or i + H >= len(s): continue
                    g = (1 + s.values[i + 1:i + 1 + H]).prod() - 1
                    islem.append((s.index[i], yon * g - MAL)); son = i + H
                if not islem: continue
                d = pd.DataFrame(islem, columns=["t", "r"]).set_index("t")["r"]
                for dn, m in (("IS", d.index < "2025"), ("OOS", d.index >= "2025")):
                    x = d[m]
                    if len(x) == 0: continue
                    gk = x.groupby(x.index.date).mean()
                    t = gk.mean() / (gk.std() / np.sqrt(len(gk))) if len(gk) > 2 and gk.std() > 0 else np.nan
                    kayit.append(dict(olay=olay, X=X, H=H, tepki=tepki, donem=dn, n=len(x), ort=x.mean() * 100, t=t))
K = pd.DataFrame(kayit)
W = K.pivot_table(index=["olay", "X", "H", "tepki"], columns="donem", values=["n", "ort", "t"])
W.columns = [f"{a}_{b}" for a, b in W.columns]; W = W.dropna(subset=["ort_IS"])
print(f"{len(W)} kol · IS↔OOS ortalama sıra korelasyonu {W.ort_IS.rank().corr(W.ort_OOS.rank()):+.2f}")
print(W.sort_values("ort_IS", ascending=False).head(10).round(2).to_string())
b = W.sort_values("ort_IS", ascending=False).iloc[0]; ad = W.sort_values("ort_IS", ascending=False).index[0]
ok = b.ort_OOS > 0 and b.t_OOS >= 2 and b.n_OOS >= 20
print(f"\nIS birincisi {ad}: OOS n {b.n_OOS:.0f}, ort {b.ort_OOS:+.2f}%, gün-t {b.t_OOS:+.2f} → {'ADAY' if ok else 'RED'}")
