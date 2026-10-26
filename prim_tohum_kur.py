#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 585: T7K prim çarpanı için TOHUM geçmişi. Bot çarpanı ancak ~90 günlük kendi geçmişi birikince uygular (öncesinde 1,0).
Bu betik araştırma zemininden (uzun zemin, sk_bar60, evren U) son 180 günün kesitsel primini (p90 − p10, YILLIK birim = günlük × 365,
botun prim_olc'u ile aynı birim) bot biçiminde yazar: carry_prim_tohum.csv (zaman,değer; 4 sa'te bir). Sunucuda:
  cp carry_prim_tohum.csv carry_prim.csv   (yalnız carry_prim.csv YOKSA)
Böylece çarpan ilk turdan itibaren motordaki gibi çalışır. Kullanım: ./zemin_sec.sh uzun && python3 prim_tohum_kur.py"""
import pickle, numpy as np, pandas as pd
Z = pickle.load(open("/tmp/zu/zemin.pkl", "rb")); U = Z["uy"]
S = pickle.load(open("/tmp/zu/sk_bar60.pkl", "rb")).reindex(index=U.index, columns=U.columns)
Sd = S.where(U)
pr = (Sd.quantile(0.9, axis=1) - Sd.quantile(0.1, axis=1)) * 365.0
pr = pr[pr.index >= pr.index[-1] - pd.Timedelta(days=180)].dropna()
with open("carry_prim_tohum.csv", "w") as f:
    for t, v in pr.items():
        f.write("%.0f,%.8f\n" % (t.timestamp(), v))
print(f"carry_prim_tohum.csv: {len(pr)} satır, {pr.index[0]} .. {pr.index[-1]}, medyan {pr.median():.4f}, son 30 g ort {pr.iloc[-180:].mean():.4f}")
