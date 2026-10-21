#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 411 — LİTERATÜRDEKİ KESİTSEL ANOMALİLER (ön kayıtlı, örnek dışı).

Kaynaklar: Cryptocurrency as an Investable Asset Class (arXiv 2510.14435: CMOM 2 hafta
en tutarlı, CSIZE, CVALUE), Cryptocurrency anomalies and economic constraints (IRFA 2024),
Bali-Cakici-Whitelaw MAX (piyango), Ang ve diğ. IVOL — kriptoya uyarlanmış.
SİNYALLER (00 UTC günlük, haftalık yeniden kurma, beşte birlik L/S, eşit ağırlık, brüt 1):
  CMOM14  son 14 g getiri — yüksek LONG (literatür yönü)
  MAX30   son 30 günün en büyük günlük getirisi — yüksek SHORT (piyango)
  IVOL30  BTC'ye 30 g regresyon artığının oynaklığı — yüksek SHORT
  SIZE    log 30 g ort hacim (piyasa değeri vekili) — küçük LONG
Maliyet devir x %0,05, gerçek funding. Evren TradFi hariç, hacim >= 20M$, yaş >= 90 g.
KABUL (koşudan ÖNCE, sinyal başına): IS (2022-04..2024-12) ve OOS (2025-01..2026-08)
net Sharpe İKİSİ de >= 0,5, OOS Sharpe >= 1,0, OOS plasebo farkı >= 0,5, carry rho <= 0,30.
Dört sinyal — çoklu bakış küçük; geçen sinyal harman turuna (%95).
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m381_cok_ufuk as U
import arastirma_m346_prim as M

def main():
    C, Fd, uy = U.yukle()
    r1 = C / C.shift(1) - 1
    import pickle
    P = pickle.load(open("/tmp/panel.pkl", "rb")); HAC = P["HAC"].reindex_like(P["C"])[P["C"].index.hour == 0].reindex_like(C)
    b = r1["BTCUSDT"]
    beta = r1.rolling(30).cov(b).div(b.rolling(30).var(), axis=0)
    res = r1 - beta.mul(b, axis=0)
    S = {"CMOM14": (C / C.shift(14) - 1, +1), "MAX30": (r1.rolling(30).max(), -1),
         "IVOL30": (res.rolling(30).std(), -1), "SIZE": (np.log(HAC.rolling(30).mean()), -1)}
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    sh = lambda g: g.mean() / g.std() * np.sqrt(365.25) if g.std() > 0 else np.nan
    for ad, (sig, yon) in S.items():
        rk = sig.where(uy).rank(axis=1, pct=True)
        def kur(rk):
            W = (rk >= 0.8).astype(float) - (rk <= 0.2).astype(float)
            W = W * yon
            lo = W.clip(lower=0); so = (-W).clip(lower=0)
            W = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 0.5 - so.div(so.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 0.5
            return U.getiri(W, C, Fd, 7)
        g = kur(rk); g = g[g.index >= "2022-04-01"]
        v = rk.values.copy(); rng = np.random.default_rng(411)
        for i in range(v.shape[0]):
            m = np.isfinite(v[i]); v[i, m] = rng.permutation(v[i, m])
        gp = kur(pd.DataFrame(v, index=rk.index, columns=rk.columns)); gp = gp[gp.index >= "2022-04-01"]
        IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        e = (1 + g).cumprod(); dd = ((e / e.cummax()) - 1).min() * 100
        yil = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
        ix = g.index.intersection(carry.index); rho = np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1]
        pla = sh(gp[gp.index >= "2025-01-01"])
        k = sh(IS) >= 0.5 and sh(OOS) >= 1.0 and sh(OOS) - pla >= 0.5 and rho <= 0.30
        print(f"{ad:<7} IS Sh {sh(IS):+.2f} yil {yil(IS):+6.1f} | OOS Sh {sh(OOS):+.2f} yil {yil(OOS):+6.1f} | plasebo {pla:+.2f} | dusus {dd:.1f} | carry rho {rho:+.2f} -> {'HARMAN TURUNA' if k else 'RED'}", flush=True)

if __name__ == "__main__":
    main()
