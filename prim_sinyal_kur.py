#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 551: PRİM HARMANLI SİNYAL PANELİ. sk60 (günlük funding oranı) ile primden tahmin edilen günlük funding harmanlanır:
  pf = 3 · (p24 + clip(0,0001 − p24, −0,0005, 0,0005))   (Binance formülü, 8 sa'lik ödeme, faiz %0,01)
  B  = (1 − W) · sk60 + W · pf
p24 = son 24 sa'lik saatlik prim ortalaması; NEDENSELLİK için 1 bar GECİKMELİ (bar i kararında en geç bar i−1 sonu).
Prim yoksa B = sk60. Kullanım (uzun zemin): W=0.3 AD=pb30 python3 prim_sinyal_kur.py → /tmp/sk_pb30.pkl ve /tmp/zu/."""
import os, pickle, shutil
import numpy as np, pandas as pd
W = float(os.environ.get("W", "0.5")); AD = os.environ.get("AD", "pb50")
S = pickle.load(open("/tmp/zu/sk_bar60.pkl", "rb"))
p = pd.read_pickle("/tmp/premium/prim_4h.pkl")
PM = p.pivot_table(index="bar", columns="sembol", values="mean").reindex(index=S.index, columns=S.columns)
p24 = PM.rolling(6, min_periods=4).mean().shift(1)
pf = 3 * (p24 + (0.0001 - p24).clip(-0.0005, 0.0005))
B = ((1 - W) * S + W * pf).where(pf.notna(), S).where(S.notna())
pickle.dump(B, open(f"/tmp/sk_{AD}.pkl", "wb")); shutil.copy(f"/tmp/sk_{AD}.pkl", f"/tmp/zu/sk_{AD}.pkl")
k = [np.corrcoef(*[pd.Series(v).rank().values for v in (S.iloc[i].dropna(), B.iloc[i][S.iloc[i].notna()])])[0, 1]
     for i in range(500, len(S), 200)]
print(f"{AD}: W={W} hücre {int(B.notna().sum().sum())} · sk60 ile kesitsel sıra kor. ort {np.nanmean(k):.3f}")
