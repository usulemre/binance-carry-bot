#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 621 — ÇIKIŞ OTOPSİSİ (kullanıcı: "nerede erken satıyor, nerede zarar ediyor — veriler var").
g33'e CIKIS_DEFTER eklendi (varsayılan boş = parite): her çıkış olayı (kâr al TP, kademe KAD, 24 sa stop S24, felaket SL, ...)
zaman, coin, yön, satılan ağırlık, çıkış fiyatı, giriş fiyatı. T7K gerçekçi, 2.000 $ D8, iki hiza, uzun zemin (/tmp/m621).
Soru: çıkılan pozisyon TUTULSAYDI sonraki 1 / 3 / 7 günde ne kazandırırdı (fiyat, yön işaretli; funding hariç)? Toplam kitap
puanı = Σ satılan ağırlık × yön × ileri getiri / dilim sayısı (15), yıllık. Pozitif = erken satış (para masada kaldı),
negatif = çıkış doğru. Kırılımlar: tür × yön, çıkıştaki funding uçluğu (sk60 yüzdeliği), piyasa durumu (evren 24 sa medyanı).
Bu bir TANI; kural yazılacaksa ayrı ön kayıtla (madde 622+).
"""
import pickle
import numpy as np
import pandas as pd

NF = 15
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = z["C"]
S = pickle.load(open("/tmp/sk_bar60.pkl", "rb")).reindex(index=C.index, columns=C.columns)
uy = z["uy"]; uy = uy if isinstance(uy, pd.DataFrame) else pd.DataFrame(uy, index=C.index, columns=C.columns)
Sq = S.where(uy.astype(bool)).rank(axis=1, pct=True)
piy = (C / C.shift(6) - 1).where(uy.astype(bool)).median(axis=1)
yil = (C.index[-1] - pd.Timestamp("2020-07-19")).days / 365.25

import os
E = pd.concat([pd.read_pickle(os.environ.get("CIKIS_KOK", "/tmp/m621/cikis") + f"_{h}.pkl").assign(h=h) for h in (0, 1)])
ci = C.index.get_indexer(E.zaman); cj = C.columns.get_indexer(E.sembol)
for ad, n in (("f1", 6), ("f3", 18), ("f7", 42)):
    ii = np.minimum(ci + n, len(C) - 1)
    E[ad] = C.values[ii, cj] / C.values[ci, cj] - 1
E["sq"] = Sq.values[ci, cj]; E["piy"] = piy.values[ci]
for ad in ("f1", "f3", "f7"):
    E["p" + ad] = E.w * E.yon * E[ad] / NF / 2 * 100          # iki hiza ortalaması, kitap puanı
E["kaz"] = E.yon * (E.fiyat / E.giris - 1)                   # çıkıştaki kâr (giriş referansına göre)


def tablo(g, baslik):
    t = g.agg(olay=("w", "size"), kaz=("kaz", "mean"), f1=("pf1", "sum"), f3=("pf3", "sum"), f7=("pf7", "sum"))
    t[["f1", "f3", "f7"]] /= yil; t["kaz"] *= 100
    print(f"\n{baslik} (yıllık kitap puanı; + = tutmak kazandırırdı)")
    print(t.round(2).to_string())


tablo(E.groupby(["tur", "yon"]), "TÜR × YÖN")
E["sqk"] = pd.cut(E.sq, [0, 0.1, 0.5, 0.9, 1.0], labels=["alt10", "10-50", "50-90", "üst10"])
tablo(E[E.tur.isin(["TP", "KAD"])].groupby(["tur", "yon", "sqk"], observed=True), "KÂR AL / KADEME × çıkıştaki funding yüzdeliği")
E["pk"] = pd.cut(E.piy, [-1, -0.05, 0.05, 10], labels=["piyasa↓5", "sakin", "piyasa↑5"])
tablo(E.groupby(["tur", "yon", "pk"], observed=True), "TÜR × YÖN × piyasa 24 sa")
E["donem"] = np.where(E.zaman < "2025-01-01", "≤2024", "2025+")
tablo(E.groupby(["tur", "yon", "donem"]), "TÜR × YÖN × dönem")
E.to_pickle(os.environ.get("CIKIS_KOK", "/tmp/m621/cikis") + "_analiz.pkl")
