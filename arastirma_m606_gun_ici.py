#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 606 — KULLANICI: "günlük için başka kitap". GÜN İÇİ SAAT MEVSİMSELLİĞİ (hiç ölçülmedi; madde 353-C haftalık, 385 yalnız
00-04 UTC kesitsel). Her gün sabit bir UTC saat penceresinde piyasa sepetini (eşit ağırlık, 100 likit sembol) ya da BTC'yi LONG/SHORT
tut, pencere dışında düz → her gün kapanan, gece taşımayan bir "günlük kitap".
ÖN KAYIT: veri saat paneli (data_5m, 2024-01..2026-08). IS = 2024, OOS = 2025-01..2026-08. Aile: başlangıç 0..23 × uzunluk
{1,2,3,4,6,8,12} sa × yön ± × varlık {sepet, BTC} = 672 kol. Maliyet gidiş-dönüş/gün: 4 bp (maker, iyimser) ve 10 bp (taker).
Seçim YALNIZ IS'te (4 bp net Sharpe). ADAY: IS birincisi OOS'ta net Sharpe ≥ 1,0 (4 bp) VE > 0 (10 bp); ayrıca IS↔OOS Sharpe sıra
korelasyonu (672 kol) raporlanır — ~0 ise mevsimsellik kalıcı değil.
"""
import pickle
import numpy as np, pandas as pd

P = pickle.load(open("/tmp/saat_panel.pkl", "rb")); C = P["C"]
R = C.pct_change()
R = R.where(R.abs() < 0.5)                                   # bozuk barlar
sepet = R.mean(axis=1); btc = R["BTCUSDT"]
VAR = {"sepet": sepet, "BTC": btc}
UZ = (1, 2, 3, 4, 6, 8, 12)


def gunluk(r, bas, L, yon, mal):
    h = r.index.hour
    pen = ((h - bas) % 24) < L
    x = (r.where(pen, 0.0).fillna(0.0) * yon)
    d = (1 + x).groupby(r.index.date).prod() - 1 - mal
    d.index = pd.DatetimeIndex(d.index); return d


def sh(d): return d.mean() / d.std() * np.sqrt(365.25) if d.std() > 0 else np.nan
def yil(d): return ((1 + d).prod() ** (365.25 / len(d)) - 1) * 100


kayit = []
for va, r in VAR.items():
    for bas in range(24):
        for L in UZ:
            for yon in (1, -1):
                d4 = gunluk(r, bas, L, yon, 0.0004); d10 = gunluk(r, bas, L, yon, 0.0010)
                IS4, OOS4, OOS10 = d4[d4.index < "2025"], d4[d4.index >= "2025"], d10[d10.index >= "2025"]
                kayit.append(dict(va=va, bas=bas, L=L, yon=yon, IS=sh(IS4), ISy=yil(IS4), OOS=sh(OOS4), OOSy=yil(OOS4),
                                  OOS10=sh(OOS10), OOS10y=yil(OOS10)))
K = pd.DataFrame(kayit)
print(f"{len(K)} kol; IS↔OOS Sharpe sıra korelasyonu: {K.IS.rank().corr(K.OOS.rank()):+.3f}")
print("\nIS'te en iyi 8 (4 bp net):")
print(K.sort_values("IS", ascending=False).head(8).round(2).to_string(index=False))
b = K.sort_values("IS", ascending=False).iloc[0]
ok = b.OOS >= 1.0 and b.OOS10 > 0
print(f"\nIS birincisi: {b.va} {int(b.bas):02d}:00 UTC'den {int(b.L)} sa {'LONG' if b.yon>0 else 'SHORT'} → OOS Sh {b.OOS:.2f} (4 bp) / {b.OOS10:.2f} (10 bp), "
      f"OOS yıllık {b.OOSy:+.1f}% / {b.OOS10y:+.1f}% → {'ADAY' if ok else 'RED'}")
print(f"OOS'ta 4 bp net Sharpe ≥ 1 olan kol sayısı: {(K.OOS>=1).sum()} / {len(K)} (şansla beklenen ~{len(K)*0.5*0.16:.0f}+)")
