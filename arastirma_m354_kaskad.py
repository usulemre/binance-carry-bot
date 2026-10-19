#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 354 — PİYASA ÇAPINDA ÇÖKÜŞ SONRASI DİP ALIMI (ve aynası).

Olay: likit (hacim >= 100M) coinlerin eşit ağırlıklı endeksi bir 4 sa
barda ESIK kadar düşer (likidasyon kaskadı). Karar o barın kapanışında,
giriş sonraki bar; endeksi long'la, H gün tut. Ayna kolu: endeks bir
barda +ESIK yükselince short. Çakışan olaylarda pozisyon uzatılır
(brüt <= 1). Maliyet ve elek madde 353 ile AYNI (koşudan önce yazıldı);
plasebo = aynı sayıda olay, rastgele barlarda.
"""
import sys

import numpy as np
import pandas as pd

import arastirma_m353_yeni_strateji as S

RNG = np.random.default_rng(354)


def kaskad(C, R, ODE, HAC, ESIK=0.05, H=2, yon=+1, plasebo=False, hacim_min=1e8):
    likit = HAC >= hacim_min
    m = R.where(likit).mean(axis=1)
    f = ODE.where(likit).mean(axis=1)
    olay = (m <= -ESIK) if yon > 0 else (m >= ESIK)
    ix = np.flatnonzero(olay.values)
    if plasebo:
        ix = np.sort(RNG.choice(np.arange(200, len(m) - 1), size=len(ix), replace=False))
    w = np.zeros(len(m))
    for i in ix:
        w[i + 1:min(i + 1 + int(H * 6), len(m))] = yon
    w = pd.Series(w, index=m.index)        # i barında karar, i+1'den itibaren tutulur
    fiyat = w * m
    fund = -w * f
    maliyet = w.diff().abs().fillna(0.0) * S.KOM
    return fiyat + fund - maliyet, len(ix)


def main():
    C, R, ODE, HAC = S.yukle()
    import arastirma_m346_prim as M
    carry = M.gunluk("K_2000_0")
    print(f"{'aday':<26} {'olay':>5} {'yillik':>8} {'Sh':>6} {'Sh22':>6} {'Sh25':>6} "
          f"{'dusus':>7} {'rho':>6} | {'PLA Sh':>6} | elek")
    gecen = []
    for yon, etk in ((+1, "dip al"), (-1, "tepe sat")):
        for ESIK in (0.04, 0.06, 0.08):
            for H in (1, 2, 3):
                r, n = kaskad(C, R, ODE, HAC, ESIK, H, yon)
                rp, _ = kaskad(C, R, ODE, HAC, ESIK, H, yon, plasebo=True)
                a = S.ozet(S.gunluk(r), f"{etk} {ESIK:.0%} H={H}g", carry)
                p = S.ozet(S.gunluk(rp), "PLA", carry)
                e = [a["sh22"] >= 1.0 and a["sh25"] >= 1.0, a["sh"] >= 1.5,
                     a["sh"] - p["sh"] >= 0.5, a["rho"] <= 0.30]
                print(f"{a['ad']:<26} {n:>5} {a['yil']:>+8.1f} {a['sh']:>6.2f} {a['sh22']:>6.2f} "
                      f"{a['sh25']:>6.2f} {a['dd']:>7.1f} {a['rho']:>+6.2f} | {p['sh']:>6.2f} | "
                      + "".join("Y" if x else "X" for x in e))
                if all(e):
                    gecen.append(a["ad"])
    print("\nELEKTEN GECEN:", gecen or "YOK")


if __name__ == "__main__":
    main()
