#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 627 — GİRİŞ OTOPSİSİ (621 çıkış, 625 tutuş; şimdi GİRİŞ). Taban T7K 1,15x + koşullu stop (P3T2). KATKI=1 bacak defteri
(madde 236: her dilim girişi; pnl = fiyat + funding, dilim ağırlığıyla; kapanış TP / DEVIR). Girişteki özelliklere göre bacak P&L'i:
taraf × beşte birlik, dönem ≤2024 / 2025+ AYRI (iki dönemde aynı yönde ve tekdüze olmayan desen elenir). Haritada sınanmış özellikler
(momentum 383, uç hareket 196/447, oynaklık 251, funding eğimi 556) bilgi için yeniden yazılır; YENİ olanlar: 30 g tepeden uzaklık,
taze giriş mi (coin önceki barda kitapta yok) yoksa yenileme mi, piyasa 7 g rejimi, coinin hacim sırası.
TANI; kural ayrı ön kayıtla. Birim: bacak başı ort. P&L (bp, dilim ağırlığına göre) ve toplam katkı (kitap puanı/yıl ≈ Σ pnl / 15 / 2 hiza).
"""
import pickle
import numpy as np
import pandas as pd

NF = 15
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = z["C"]
P = pickle.load(open("/tmp/zu/panel.pkl", "rb"))
uy = z["uy"]; uy = uy if isinstance(uy, pd.DataFrame) else pd.DataFrame(uy, index=C.index, columns=C.columns)
HAC = P["HAC"].reindex(index=C.index, columns=C.columns)
yil = (C.index[-1] - pd.Timestamp("2020-07-19")).days / 365.25

K = pd.concat([pd.read_pickle(f"/tmp/katki_{h}.pkl").assign(h=h) for h in (0, 1)], ignore_index=True)
K = K[K.w != 0].copy()
ii = C.index.get_indexer(K.t); jj = C.columns.get_indexer(K.sem)
cv = C.values


def ret(n):
    a = cv[ii, jj]; b = cv[np.maximum(ii - n, 0), jj]
    return a / b - 1


K["r1"] = ret(6); K["r7"] = ret(42); K["r30"] = ret(180)
hi30 = C.rolling(180, min_periods=60).max().values
K["tepe"] = cv[ii, jj] / hi30[ii, jj] - 1
piy7 = (C / C.shift(42) - 1).where(uy.astype(bool)).median(axis=1).values
K["piy7"] = piy7[ii]
K["hac_sira"] = HAC.where(uy.astype(bool)).rank(axis=1, pct=True).values[ii, jj]
# taze: aynı coin aynı yönde bir önceki 24 sa içinde başka bir dilimde açılmamış
K = K.sort_values("t"); K["taze"] = 1
son = {}
for idx, r in K[["t", "sem", "yon", "h"]].iterrows():
    key = (r.h, r.sem, r.yon)
    if key in son and (r.t - son[key]) <= pd.Timedelta(hours=24): K.at[idx, "taze"] = 0
    son[key] = r.t
K["donem"] = np.where(K.t < "2025-01-01", "≤2024", "2025+")
K["taraf"] = np.where(K.yon > 0, "L", "S")
K["bp"] = K.pnl / K.w.abs() * 1e4


def ozet(ozellik, q=5):
    print(f"\n=== {ozellik} ===")
    for taraf in ("L", "S"):
        x = K[K.taraf == taraf].copy()
        if ozellik == "taze":
            x["kova"] = x.taze.astype(str)
        else:
            x["kova"] = pd.qcut(x[ozellik].rank(method="first"), q, labels=[f"Q{i+1}" for i in range(q)])
        t = x.groupby(["kova", "donem"], observed=True).agg(n=("bp", "size"), bp=("bp", "mean"), top=("pnl", "sum"))
        t["top"] = t.top / NF / 2 * 100 / yil
        t = t.unstack("donem")
        lo = x.groupby("kova", observed=True)[ozellik].median() if ozellik != "taze" else None
        if lo is not None: t[("medyan", "")] = lo.round(3)
        print(f"-- {taraf} (bp: bacak başı ort. getiri, top: kaba kitap puanı/yıl)"); print(t.round(1).to_string())


for o in ("r1", "r7", "r30", "tepe", "piy7", "hac_sira", "vol", "sin", "taze"):
    ozet(o)
K.to_pickle("/tmp/m621/giris_bacak.pkl")
