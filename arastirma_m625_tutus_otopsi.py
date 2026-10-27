#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 625 — TUTUŞ OTOPSİSİ (madde 621'in devamı; yeni taban T7K 1,15x + koşullu stop, bot ritmi).
621 çıkışlara baktı. Bu tanı TUTULAN pozisyonlara bakar: coin 24 sa'te sert hareket edince (short'ta +X yükseliş = sıkışma, long'ta
−X düşüş = stop seviyesine gelmeden çöküş) pozisyonu TUTMAK mı KESMEK mi kazandırır, piyasa durumuna göre?
Olay = pozisyonun coin 24 sa getirisi eşiği İLK geçtiği bar (önceki bar altındaydı). Değer = ağırlık (dilimler ortalaması, POZ_CIKTI)
× yön × ileri getiri (1 / 3 / 7 g), kitap puanı / yıl, iki hiza ortalaması. Pozitif = tutmak doğru, negatif = kesmek kazandırırdı.
Kırılım: piyasa (evren medyan 24 sa) ≤ −%3 / sakin / ≥ +%3 ve dönem ≤2024 / 2025+. TANI; kural ayrı ön kayıtla.
"""
import pickle
import numpy as np
import pandas as pd

z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = z["C"]
uy = z["uy"]; uy = uy if isinstance(uy, pd.DataFrame) else pd.DataFrame(uy, index=C.index, columns=C.columns)
R24 = C / C.shift(6) - 1
piy = R24.where(uy.astype(bool)).median(axis=1)
yil = (C.index[-1] - pd.Timestamp("2020-07-19")).days / 365.25
cv = C.values; r24 = R24.values

olaylar = []
for h in (0, 1):
    P = pd.read_pickle(f"/tmp/m621/pozKS_{h}.pkl")
    ii = C.index.get_indexer(P.zaman); jj = C.columns.get_indexer(P.sembol); w = P.w.values
    for taraf, esikler in (("S", (0.20, 0.35, 0.50)), ("L", (-0.20, -0.30))):
        m = (w < 0) if taraf == "S" else (w > 0)
        for e in esikler:
            x = r24[ii, jj]; xo = r24[np.maximum(ii - 1, 0), jj]
            if taraf == "S": k = m & (x >= e) & ~(xo >= e)
            else: k = m & (x <= e) & ~(xo <= e)
            for a, b, ww in zip(ii[k], jj[k], w[k]):
                rec = dict(h=h, taraf=taraf, esik=e, zaman=C.index[a], w=ww, piy=piy.iloc[a])
                for ad, n in (("f1", 6), ("f3", 18), ("f7", 42)):
                    t = min(a + n, len(C) - 1); rec[ad] = cv[t, b] / cv[a, b] - 1
                olaylar.append(rec)
O = pd.DataFrame(olaylar)
for ad in ("f1", "f3", "f7"):
    O["p" + ad] = O.w * O[ad] / 2 * 100          # w işaretli → tutmanın değeri; iki hiza ortalaması
O["pk"] = pd.cut(O.piy, [-9, -0.03, 0.03, 9], labels=["piyasa≤−3", "sakin", "piyasa≥+3"])
O["donem"] = np.where(O.zaman < "2025-01-01", "≤2024", "2025+")


def tablo(g, b):
    t = g.agg(olay=("w", "size"), f1=("pf1", "sum"), f3=("pf3", "sum"), f7=("pf7", "sum"))
    t[["f1", "f3", "f7"]] /= yil
    print(f"\n{b} (yıllık kitap puanı; + = TUTMAK doğru, − = kesmek kazandırırdı)"); print(t.round(2).to_string())


tablo(O.groupby(["taraf", "esik"]), "TARAF × EŞİK")
tablo(O.groupby(["taraf", "esik", "pk"], observed=True), "× PİYASA")
tablo(O.groupby(["taraf", "esik", "donem"]), "× DÖNEM")
O.to_pickle("/tmp/m621/tutus_olay.pkl")
