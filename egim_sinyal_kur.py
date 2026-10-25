#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 556 panel: FUNDING EĞİMİ harmanı. B = sk60 + L · (sk36 − sk144): funding'i YENİ artan coin öne, sönmekte olan geriye.
Kaynak /tmp/zu/sk_bar{36,60,144}.pkl (uzun zemin). Kullanım: L=0.5 AD=eg50 python3 egim_sinyal_kur.py → /tmp/sk_eg50.pkl (+ /tmp/zu)."""
import os, pickle, shutil
import numpy as np, pandas as pd
L = float(os.environ.get("L", "0.5")); AD = os.environ.get("AD", "eg50")
a, b, c = (pickle.load(open(f"/tmp/zu/sk_bar{p}.pkl", "rb")) for p in (36, 60, 144))
B = (b + L * (a - c)).where(a.notna() & c.notna(), b)
pickle.dump(B, open(f"/tmp/sk_{AD}.pkl", "wb")); shutil.copy(f"/tmp/sk_{AD}.pkl", f"/tmp/zu/sk_{AD}.pkl")
k = [np.corrcoef(*[x.rank().values for x in (b.iloc[i].dropna(), B.iloc[i][b.iloc[i].notna()])])[0, 1] for i in range(500, len(b), 200)]
print(f"{AD}: L={L} sk60 ile sıra kor. {np.nanmean(k):.3f}")
