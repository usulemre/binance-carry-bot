#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 594 — YENİ EKSEN (ön eleme): HAFTANIN GÜNÜ. Kitabın getirisi / kötü günü haftanın gününe göre ayrışıyor mu?
(Madde 353-C bağımsız bir haftalık mevsimsellik STRATEJİSİNİ ölçtü; carry KİTABININ gün etkisi hiç ölçülmedi.)

ÖN KAYIT: kitap T4 (standart model, MERD_SIRA=1, 2.000 $ D8, iki hiza ort., uzun zemin; /tmp/m591 K_0/K_1).
Bir gün d "tilt adayı" sayılır, ancak IS (≤2024) ve OOS (2025+) İKİSİNDE de:
  (a) d'nin ortalama günlük getirisi, diğer günlerin ortalamasından en az 1 standart hata uzakta, AYNI yönde, ve
  (b) aynı yönde d'nin −%3 altı gün oranı diğerlerinin ≥ 1,5 katı (zayıf gün) ya da ≤ 0,67 katı (güçlü gün).
Aday yoksa eksen KAPANIR. Aday varsa motor kolu (o gün brüt ×0,5 / ×1,5) ayrı ön kayıtla ölçülür.
"""
import pickle, numpy as np, pandas as pd
def g(p):
    E = pickle.load(open(p, "rb")); r = E.pct_change().dropna(); d = (1 + r).groupby(r.index.date).prod() - 1
    d.index = pd.DatetimeIndex(d.index); return d
d = (g("/tmp/m591/K_0.pkl") + g("/tmp/m591/K_1.pkl")) / 2
GUN = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
aday = {}
for dn, m in (("IS", d.index < "2025-01-01"), ("OOS", d.index >= "2025-01-01")):
    x = d[m]; print(f"\n{dn} ({x.index[0].date()} → {x.index[-1].date()}, {len(x)} gün)")
    print(f"{'gün':4s} {'n':>4s} {'ort bp':>7s} {'fark/SE':>8s} {'−%3 %':>6s} {'oran':>5s}")
    for w in range(7):
        a, b = x[x.index.dayofweek == w], x[x.index.dayofweek != w]
        se = np.sqrt(a.var() / len(a) + b.var() / len(b)); z = (a.mean() - b.mean()) / se
        ka, kb = (a < -0.03).mean(), (b < -0.03).mean(); o = ka / kb if kb > 0 else np.nan
        print(f"{GUN[w]:4s} {len(a):4d} {a.mean()*1e4:+7.1f} {z:+8.2f} {ka*100:6.2f} {o:5.2f}")
        yon = 1 if z >= 1 else (-1 if z <= -1 else 0)
        kt = (yon == -1 and o >= 1.5) or (yon == 1 and o <= 0.67)
        aday.setdefault(w, []).append(yon if kt else 0)
sec = [GUN[w] for w, v in aday.items() if v[0] != 0 and v[0] == v[1]]
print("\nHÜKÜM:", ("ADAY: " + ", ".join(sec)) if sec else "KAPANDI (iki dönemde tutarlı gün yok)")
