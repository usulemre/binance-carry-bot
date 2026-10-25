#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 555 — KİTAP DÜZEYİNDE RİSK ÖLÇEĞİ (yalnız AZALTIR, kaldıraç yok), T4 günlük serisi üzerinde (Q_T4, düzeltilmiş model, uzun zemin).
Ölçek dün akşama kadar bilinenle kurulur (nedensel), bugünün getirisine uygulanır; ölçek değişimi maliyeti |Δölçek| × 2 taraf × 5 bp.
A) oynaklık hedefi: ölçek = min(1, hedef / son N gün gerçekleşen oynaklık)
B) düşüş freni: kitap tepeden D'den fazla aşağıdaysa ölçek k
C) kötü gün sonrası: dün ≤ −%X ise bugün ölçek k (madde 538-539: çöküş sonrası dönüş → beklenti negatif)
Ön kayıt madde 503 kuralı (Q_T4'e karşı)."""
import numpy as np, pandas as pd
import arastirma_m497_uzun_gecmis as U

b = U.seri("Q_T4")
DON = [("TÜM", "2020", "2027"), ("YENİ", "2020", "2022"), ("22-24", "2022-07-20", "2025"), ("25-26", "2025", "2027")]


def uygula(olc):
    olc = olc.clip(0, 1).fillna(1.0)
    mal = olc.diff().abs().fillna(0) * 2 * 0.0005
    return olc * b - mal


def rapor(ad, g):
    r = []
    for _, a, z in DON:
        x, y = g.loc[a:z], b.loc[a:z]; ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
    ev = U.olc(g)[0] - U.olc(b * (g.std() / b.std()))[0]
    ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
    print(f"  {ad:14s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) +
          f" · {ev:+6.1f} · −%5 {U.olc(g)[4]} · en kötü {g.min()*100:5.1f} · ort ölçek" + ("  ADAY" if ok else ""))


print("Q_T4:", U.olc(b))
vol = b.rolling(20).std().shift(1) * np.sqrt(365)
hv = float(b.std() * np.sqrt(365))
print(f"T4 yıllık oynaklık {hv:.2f}")
for h in (0.8, 1.0, 1.2):
    for n in (10, 20, 60):
        v = b.rolling(n).std().shift(1) * np.sqrt(365)
        rapor(f"A hedef{h:.1f}·{n}g", uygula((h * hv) / v))
eq = (1 + b).cumprod()
for D in (0.08, 0.12):
    for k in (0.5, 0.75):
        dd = (eq / eq.cummax() - 1).shift(1)
        rapor(f"B dd{int(D*100)}·{k}", uygula(pd.Series(np.where(dd < -D, k, 1.0), index=b.index)))
for X in (0.03, 0.05):
    for k in (0.5, 1.0):
        pass
for X in (0.03, 0.05):
    for k in (0.5, 0.0):
        rapor(f"C dün≤−{int(X*100)}·{k}", uygula(pd.Series(np.where(b.shift(1) <= -X, k, 1.0), index=b.index)))
