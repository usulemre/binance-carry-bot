#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 387 — AYNI COİNİN USDT ve USDC PERP'İ ARASINDA FUNDING FARKI (madde 296'nın açık ekseni).

MEKANİZMA: aynı dayanak, iki ayrı perp; fiyat korelasyonu ~1, funding
korelasyonu ~0,4 (madde 296). Funding'i yüksek olanı short, düşük olanı long
tutmak fiyat riskini ~sıfırlar, farkı toplar. Fiyat riski düşük olduğu için
kaldıraç kaldırabilir (çapraz teminat, aynı hesap).

VERİ: data.binance.vision USDC perp funding + 4 sa kline (`indir_usdc.sh`,
40 sembol, çoğu 2024-01'den); USDT tarafı mevcut zemin (C, ODE).
DÖNEM: IS 2024 (seçim), OOS 2025-01..2026-08 (sınav).

KURAL (nedensel, 4 sa bar): d = son 3 günde (USDT ödemeleri − USDC ödemeleri)
toplamının 8 saatlik eşdeğeri. d > T -> USDT short + USDC long; d < −T ->
tersi; |d| < T/2 olunca çık. Çift başı brüt 1 (0,5 + 0,5); portföy açık
çiftlere eşit pay, brüt 1. Getiri = yön x 0,5 x (fon_USDT − fon_USDC)
+ yön x 0,5 x (r_USDC − r_USDT) − devir x 5 bp.
IZGARA: T {0,005% · 0,01% · 0,02% · 0,05%} (8 sa başına).
KABUL (koşudan ÖNCE): IS'te seçilen T'nin OOS net Sharpe >= 1,5 VE
3x brütte OOS yıllık >= +%15 VE carry ile rho <= 0,30.
"""
import glob
import io
import os
import pickle
import sys
import zipfile

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
KOM = 0.0005


def oku_usdc():
    fon, kap = {}, {}
    for s in open(os.path.join(KOK, "data_usdc/semboller.txt")).read().split():
        fs = []
        for f in sorted(glob.glob(os.path.join(KOK, f"data_usdc/fon/{s}-*.zip"))):
            z = zipfile.ZipFile(f); d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
            fs.append(d)
        ks = []
        for f in sorted(glob.glob(os.path.join(KOK, f"data_usdc/k4/{s}-*.zip"))):
            z = zipfile.ZipFile(f); raw = z.read(z.namelist()[0])
            d = pd.read_csv(io.BytesIO(raw), header=None)
            if not str(d.iloc[0, 0]).isdigit():
                d = d.iloc[1:]
            ks.append(d)
        if not fs or not ks:
            continue
        F = pd.concat(fs)
        F.index = pd.to_datetime(F["calc_time"].astype("int64"), unit="ms").dt.floor("h")
        fon[s] = F["last_funding_rate"].astype(float).groupby(level=0).sum()
        K = pd.concat(ks)
        K.index = pd.to_datetime(K[0].astype("int64"), unit="ms")
        kap[s] = K[4].astype(float).groupby(level=0).last()
    return fon, kap


def bar_topla(seri, idx):
    """Ödemeleri 4 sa barlara: bar t, [t, t+4s) içinde ödeneni taşır (zeminle aynı)."""
    k = pd.Series(idx.searchsorted(seri.index, side="right") - 1, index=seri.index)
    s = seri.groupby(k.values).sum()
    s = s[s.index >= 0]
    out = pd.Series(0.0, index=idx); out.iloc[s.index.values] = s.values
    return out


def main():
    z = pickle.load(open("/tmp/zemin.pkl", "rb"))
    C, ODE = z["C"], z["ODE"].reindex_like(z["C"]).fillna(0.0)
    fon, kap = oku_usdc()
    idx = C.index[C.index >= "2024-01-01"]
    cift = {}
    for s in fon:
        u = s[:-4] + "USDT"
        if u not in C.columns:
            continue
        fc = bar_topla(fon[s], idx)
        cc = kap[s].reindex(idx)
        cu = C[u].reindex(idx)
        fu = ODE[u].reindex(idx).fillna(0.0)
        ok = cc.notna() & cu.notna()
        if ok.sum() < 600:
            continue
        cift[s[:-4]] = pd.DataFrame(dict(fu=fu, fc=fc, ru=(cu / cu.shift(1) - 1), rc=(cc / cc.shift(1) - 1), ok=ok))
    print(f"{len(cift)} cift: {' '.join(sorted(cift))}")
    # teşhis: ortalama fark ve fiyat ayrışması
    ff = pd.DataFrame({k: (v.fu - v.fc).where(v.ok) for k, v in cift.items()})
    bz = pd.DataFrame({k: (v.ru - v.rc).where(v.ok) for k, v in cift.items()})
    print(f"ortalama fon farki (USDT-USDC) yillik %{ff.mean().mean()*6*365*100:.2f} | "
          f"4s fiyat farki sd %{bz.stack().std()*100:.3f}")

    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    d3 = ff.rolling(18, min_periods=12).sum() / 9          # 3 gün = 9 ödeme (8 sa eşdeğeri)
    sat = []
    for T in (0.00005, 0.0001, 0.0002, 0.0005):
        yon = pd.DataFrame(0.0, index=ff.index, columns=ff.columns)
        v = np.zeros(ff.shape[1]); D = d3.values; Y = np.zeros_like(D)
        for i in range(len(D)):
            di = D[i]
            v = np.where(np.isfinite(di) & (di > T), 1.0,
                np.where(np.isfinite(di) & (di < -T), -1.0,
                np.where(np.isfinite(di) & (np.abs(di) >= T / 2), v, 0.0)))
            Y[i] = v
        yon = pd.DataFrame(Y, index=ff.index, columns=ff.columns)
        Yl = yon.shift(1).fillna(0.0)                       # bar t'de kurulan, t+1'de kazanır
        n = (Yl != 0).sum(axis=1).replace(0, np.nan)
        pay = 1.0 / n
        brut = (Yl * 0.5 * (ff.fillna(0) - bz.fillna(0))).sum(axis=1) * pay
        dev = (yon.diff().abs().sum(axis=1) * pay.shift(-1).fillna(0)).fillna(0) * KOM
        g4 = (brut.fillna(0) - dev)
        g = (1 + g4).groupby(g4.index.floor("D")).prod() - 1
        IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        sh = lambda x: x.mean() / x.std() * np.sqrt(365.25) if x.std() > 0 else np.nan
        yil = lambda x, k=1: ((1 + k * x).prod() ** (365.25 / len(x)) - 1) * 100
        e = (1 + 3 * OOS).cumprod(); dd = ((e / e.cummax()) - 1).min() * 100
        ix = g.index.intersection(carry.index)
        rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
        acik = float((Yl != 0).sum(axis=1)[Yl.index >= "2025-01-01"].mean())
        sat.append(dict(T=T, IS=sh(IS), OOS=sh(OOS), y1=yil(OOS), y3=yil(OOS, 3), dd3=dd, rho=rho, acik=acik))
        r = sat[-1]
        print(f"T {T*100:.3f}%  IS Sh {r['IS']:5.2f}  OOS Sh {r['OOS']:5.2f}  OOS yil 1x %{r['y1']:+6.1f} "
              f"3x %{r['y3']:+6.1f} (dusus 3x {dd:.1f})  rho {rho:+.2f}  acik cift {acik:.1f}", flush=True)
    en = max(sat, key=lambda x: x["IS"] if np.isfinite(x["IS"]) else -9)
    kabul = en["OOS"] >= 1.5 and en["y3"] >= 15 and en["rho"] <= 0.30
    print(f"\nIS'TE SECILEN T {en['T']*100:.3f}% -> OOS Sh {en['OOS']:.2f}, 3x yil %{en['y3']:+.1f} -> "
          f"{'SONRAKI TURA' if kabul else 'RED'}")


if __name__ == "__main__":
    main()
