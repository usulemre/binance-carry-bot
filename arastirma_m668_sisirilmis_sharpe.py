#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 668 — ÇOKLU DENEME DÜZELTMESİ (Deflated Sharpe, Bailey & López de Prado 2014). Soru: ~660 madde boyunca yüzlerce kol denendi;
önerilen ayarın Sharpe'ı (4,14) "en iyisini seçmenin" şansı mı? DSR = P(gerçek Sharpe > N denemenin şansla beklenen en büyüğü),
çarpıklık / basıklık düzeltmeli. N ∈ {100, 300, 700}, deneme Sharpe'larının sıfır etrafındaki yayılımı V ∈ {0,5; 1,0; 1,5} (yıllık).
Ek: örneğin iki yarısı ayrı Sharpe."""
import arastirma_m346_prim as M, numpy as np
from scipy.stats import norm, skew, kurtosis
M.CIKTI = "/tmp/m622"; d = sum(M.gunluk(f"M357_EK_P3T2_2000_{h}") for h in (0, 1)) / 2
n = len(d); sr = d.mean() / d.std(); g3 = skew(d); g4 = kurtosis(d, fisher=False)
psr = lambda s: norm.cdf((sr - s) * np.sqrt(n - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
print(f"gün {n} · yıllık Sharpe {sr*np.sqrt(365.25):.2f} · çarpıklık {g3:.2f} · basıklık {g4:.1f}")
for N in (100, 300, 700):
    for V in (0.5, 1.0, 1.5):
        e = np.euler_gamma; s = V / np.sqrt(365.25) * ((1 - e) * norm.ppf(1 - 1 / N) + e * norm.ppf(1 - 1 / (N * np.e)))
        print(f"N={N:4d} V={V:.1f}: şansla en iyi {s*np.sqrt(365.25):.2f} → DSR {psr(s):.4f}")
h = n // 2
print("yarılar:", round(d.iloc[:h].mean() / d.iloc[:h].std() * np.sqrt(365.25), 2), round(d.iloc[h:].mean() / d.iloc[h:].std() * np.sqrt(365.25), 2))
