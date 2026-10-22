#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 434 — GÜVEN ÖLÇÜSÜNÜN DENETİMİ (P doğru mu hesaplanıyor?).

Protokolün P'si: eşli durağan blok bootstrap (20 g) yollarında "adayı kontrolün maks
düşüşüne kaldıraçla, yıllık getiri farkı > 0" oranı. Maks düşüş tek-olay istatistiği →
şüphe: ölçü gürültüyle ezilip GERÇEK bir üstünlüğü bile %95'e taşıyamıyor olabilir.
DENEY (bilinen cevaplı yapay adaylar, kontrol = M357_KAYMA_2000_0):
  PLASEBO  aday = kontrol x 1,25 kaldıraç       → gerçek fark 0  → doğru P ≈ %50
  EKn      aday = kontrol + n baz puan/gün        → gerçek fark > 0 (aynı risk) → doğru P → %100
Her yolda dört ölçü: ESIT_DD (bugünkü), HAM (yıllık getiri), SHARPE, ESIT_VOL (aday kontrol
oynaklığına ölçeklenmiş getiri farkı). Ardından gerçek adaylar aynı dört ölçüyle.
"""
import numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m346_prim as M
M.CIKTI = "/tmp/m412"


def yol_indeks(T, n, blok=20, tohum=346):
    rng = np.random.default_rng(tohum)
    for _ in range(n):
        idx = np.empty(T, int); t = 0
        while t < T:
            b = rng.integers(T); L = min(rng.geometric(1 / blok), T - t)
            idx[t:t + L] = (b + np.arange(L)) % T; t += L
        yield idx


yil = lambda r: (np.prod(1 + r) ** (365.25 / len(r)) - 1) * 100


def olc(rk, ra, n=500):
    s = {"ESIT_DD": [], "HAM": [], "SHARPE": [], "ESIT_VOL": []}
    for idx in yol_indeks(len(rk), n):
        k, a = rk[idx], ra[idx]
        s["ESIT_DD"].append(M._esit_risk_fark(k, a))
        s["HAM"].append(yil(a) - yil(k))
        s["SHARPE"].append(a.mean() / a.std() - k.mean() / k.std())
        s["ESIT_VOL"].append(yil(a * k.std() / a.std()) - yil(k))
    return {m: np.mean(np.array(v)[np.isfinite(v)] > 0) * 100 for m, v in s.items()}


def main():
    gk = M.gunluk("M357_KAYMA_2000_0"); rk = gk.values
    print("YAPAY ADAYLAR (dogru cevap bilinir)                ESIT_DD    HAM  SHARPE ESIT_VOL")
    yapay = {"PLASEBO 1,25x (dogru P ~50)": rk * 1.25}
    for bp in (2, 5, 10):
        a = rk + bp / 1e4
        yapay[f"EK{bp:2d} bp/gun (+{yil(a)-yil(rk):.0f} puan, dogru P ->100)"] = a
    for ad, ra in yapay.items():
        p = olc(rk, ra); print(f"{ad:48s} " + " ".join(f"{p[m]:6.1f}" for m in p), flush=True)
    print("\nGERCEK ADAYLAR (2000 $, hiza 0 / 1)")
    for ad in ("R30Y60S", "R18", "R16"):
        for h in (0, 1):
            k = M.gunluk(f"M357_KAYMA_2000_{h}"); a = M.gunluk(f"M357_{ad}_2000_{h}")
            i = k.index.intersection(a.index)
            p = olc(k[i].values, a[i].values)
            print(f"{ad:8s} h{h}{'':38s} " + " ".join(f"{p[m]:6.1f}" for m in p), flush=True)
    for h in (0, 1):
        k = M.gunluk(f"M357_KAYMA_2000_{h}")
        a = pd.concat([M.gunluk(f"M357_{u}_2000_{h}") for u in ("R16", "R19", "R13", "R18", "R22")], axis=1).dropna().mean(axis=1)
        i = k.index.intersection(a.index); p = olc(k[i].values, a[i].values)
        print(f"TOP5     h{h}{'':38s} " + " ".join(f"{p[m]:6.1f}" for m in p), flush=True)


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


def guc():
    """GERÇEKÇİ GÜRÜLTÜLÜ GÜÇ TESTİ: aday = kontrol + (gerçek R30Y60S farkının ortalaması
    sıfırlanmış hâli) + bilinen sabit üstünlük. Gürültü gerçek adayınki kadar, cevap bilinir."""
    k = M.gunluk("M357_KAYMA_2000_0"); a = M.gunluk("M357_R30Y60S_2000_0")
    i = k.index.intersection(a.index); rk, ra = k[i].values, a[i].values
    d0 = (ra - rk) - (ra - rk).mean()
    print("\nGUC TESTI (R30Y60S kadar gurultu, bilinen ustunluk)    ESIT_DD    HAM  SHARPE ESIT_VOL")
    for bp in (0, 2, 5, 8):
        x = rk + d0 + bp / 1e4
        p = olc(rk, x)
        print(f"ustunluk {bp} bp/gun (+{yil(x)-yil(rk):5.0f} puan ham){'':20s} " + " ".join(f"{p[m]:6.1f}" for m in p), flush=True)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "guc":
    guc()
