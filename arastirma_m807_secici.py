#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 807 — ML seçici vs kalabalık filtresi, aynı havuzda (kapı teşhisi). Ön kayıt KAR_HARITASI 807. KARAR VERMEZ."""
import pickle
import numpy as np, pandas as pd
import arastirma_m389_ml_tahmin as A
C, Fd, uy, X = A.panel()
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; H4 = pickle.load(open("/tmp/hlo.pkl", "rb"))["H"].reindex_like(C4)
sec = C4.index.hour == 0
fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]
c5 = C.shift(-5) / C - 1; fon = Fd.rolling(5).sum().shift(-5)
pay = (pd.DataFrame(np.where(fmax.values >= C.values * 1.45, 0.45, c5.values), index=C.index, columns=C.columns) - fon).where(uy).clip(-0.9, 0.45)
Mt = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))
LS = Mt["count_long_short_ratio"].reindex_like(C4)[sec].reindex_like(C)
S802 = pickle.load(open("/tmp/m802/veto.pkl", "rb"))[sec].reindex_like(C)      # 0,5 × sıra(P sıçrama) → yüksek = iyi
A804 = pickle.load(open("/tmp/m804/veto.pkl", "rb"))[sec].reindex_like(C)      # 0,5 × (1 − sıra(skor)) → yüksek = iyi
F3 = X["fon3"]; rng = np.random.default_rng(807)
sat = []
for t in C.index[C.index >= "2022-01-01"]:
    f = F3.loc[t]; p = pay.loc[t]; ok = f.notna() & p.notna() & uy.loc[t]
    if ok.sum() < 40: continue
    hav = f[ok].nsmallest(16).index
    def ort(s, en_yuksek):
        s = s.reindex(hav).dropna()
        if len(s) < 8: return np.nan
        k = (s.nlargest(4) if en_yuksek else s.nsmallest(4)).index; return p[k].mean()
    sat.append((t, ort(LS.loc[t], False), ort(S802.loc[t], True), ort(A804.loc[t], True), p[rng.choice(hav, 4, replace=False)].mean(), p[hav].mean()))
D = pd.DataFrame(sat, columns=["t", "K kalabalık", "S sıçrama", "A asimetri", "R rastgele", "havuz"]).set_index("t") * 100
y = D.groupby(D.index.year).mean(); y.loc["2022-26"] = D.mean(); y.loc["Eki-10Kas 26"] = D["2026-10-01":"2026-11-10"].mean()
y.loc["n gün"] = D.groupby(D.index.year).size().reindex(y.index[:-2]).tolist() + [len(D), len(D["2026-10-01":"2026-11-10"])]
print(y.round(2).to_string())
for c in ("S sıçrama", "A asimetri"):
    fark = y[c] - y["K kalabalık"]; n = sum(fark.loc[[2024, 2025, 2026]] >= 0.5); gec = n >= 2 and fark.loc["2022-26"] >= 0.5
    print(f"{c}: fark K'ya göre " + " ".join(f"{i}:{v:+.2f}" for i, v in fark.items() if i != 'n gün') + f" → 2024-26 {n}/3 · KAPI {'GEÇTİ' if gec else 'GEÇMEDİ'}")
