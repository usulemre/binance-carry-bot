#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 389 — MAKİNE ÖĞRENMESİYLE KESİTSEL FİYAT TAHMİNİ (madde 152'nin bugünkü zeminde tekrarı).

SORU: geniş bir özellik setiyle eğitilmiş bir öğrenici, coinlerin ERTESİ GÜN
(ve 5 gün) getirisini sıralayabilir mi, ve bu maliyet sonrası para eder mi?

VERİ: 00 UTC günlük panel (TradFi hariç, hacim >= 20M$, yaş >= 30 gün).
ÖZELLİKLER (hepsi t anında bilinen, kesitsel yüzdelik sıra):
  getiri 1/3/7/14/30/90 gün · 7 ve 30 gün oynaklık · 24 sa ve 3 gün funding ·
  hacim oranı (7g/30g) · 20 gün aralık konumu · kalabalık oranı (ls) ·
  OI 1g ve 7g değişimi · taker al/sat oranı · BTC'ye 30g beta · coin yaşı
HEDEF: sonraki H gün getirisinin kesitsel yüzdelik sırası (H = 1, 5);
  getiri funding'i de içerir (long'un ödediği).
MODELLER: ridge (doğrusal taban) ve HistGradientBoosting (ağaç).
YÜRÜYEN DOĞRULAMA: 2023, 2024, 2025, 2026 her biri için model yalnız O YILDAN
  ÖNCEKİ veriyle eğitilir (H gün boşluk bırakılarak), o yıl tahmin edilir.
  Hiperparametre seçimi YOK (sabit, makul değerler) — çoklu bakış sıfır.
PORTFÖY: tahmin üst %10 long / alt %10 short, eşit ağırlık, brüt 1;
  H=1 her gün, H=5 her 5 günde bir yeniden kur. Maliyet devir x 6 bp.
KABUL (koşudan ÖNCE): ağaç modelinin örnek dışı (2023-26) net Sharpe >= 1,0,
  her yıl rank IC > 0, ve carry ile rho <= 0,30 → harman turuna.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
MAL = 0.0006


def panel():
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); P = pickle.load(open("/tmp/panel.pkl", "rb"))
    hlo = pickle.load(open("/tmp/hlo.pkl", "rb")); Mt = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))
    C4 = z["C"]; F4 = z["ODE"].reindex_like(C4).fillna(0.0)
    sec = C4.index.hour == 0
    C = C4[sec]
    Fd = F4.groupby(F4.index.floor("D")).sum().reindex(C.index.floor("D") - pd.Timedelta(days=1)).fillna(0.0)
    Fd.index = C.index
    H4, L4 = hlo["H"].reindex_like(C4), hlo["L"].reindex_like(C4)
    from tradfi_liste import TRADFI
    HAC = P["HAC"].reindex_like(C4)[sec]; YAS = P["YAS"].reindex_like(C4)[sec]
    uy = (HAC >= 2e7) & (YAS >= 30 * 6) & C.notna()
    uy = uy & ~uy.columns.isin(list(TRADFI))
    r1 = C / C.shift(1) - 1
    f = {}
    for h in (1, 3, 7, 14, 30, 90):
        f[f"r{h}"] = C / C.shift(h) - 1
    f["vol7"] = r1.rolling(7).std(); f["vol30"] = r1.rolling(30).std()
    f["fon1"] = Fd; f["fon3"] = Fd.rolling(3).sum()
    f["hacim"] = HAC.rolling(7).mean() / HAC.rolling(30).mean()
    hi = H4.rolling(120).max()[sec]; lo = L4.rolling(120).min()[sec]
    f["konum"] = (C - lo) / (hi - lo)
    for k, ad in (("count_long_short_ratio", "ls"), ("sum_taker_long_short_vol_ratio", "taker")):
        f[ad] = Mt[k].reindex_like(C4)[sec]
    oi = Mt["sum_open_interest_value"].reindex_like(C4)[sec]
    f["oi1"] = oi / oi.shift(1) - 1; f["oi7"] = oi / oi.shift(7) - 1
    b = r1["BTCUSDT"]
    f["beta"] = r1.rolling(30).cov(b).div(b.rolling(30).var(), axis=0)
    f["yas"] = YAS
    X = {k: v.where(uy).rank(axis=1, pct=True) for k, v in f.items()}
    return C, Fd, uy, X


def hedef(C, Fd, uy, H):
    fwd = C.shift(-H) / C - 1 - Fd.rolling(H).sum().shift(-H)   # Fd[t+1..t+H]: long'un ödediği
    return fwd.where(uy).clip(-0.9, 3), fwd.where(uy).rank(axis=1, pct=True)


def uzun(X, y=None):
    d = pd.concat({k: v.stack(future_stack=True) for k, v in X.items()}, axis=1)
    if y is not None:
        d["y"] = y.stack(future_stack=True)
    return d


def main():
    C, Fd, uy, X = panel()
    D = uzun(X)
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    kols = list(X)
    for H in (1, 5):
        ham, yr = hedef(C, Fd, uy, H)
        D["y"] = yr.stack(future_stack=True)
        D["ham"] = ham.stack(future_stack=True)
        tah = {"ridge": pd.Series(np.nan, index=D.index), "agac": pd.Series(np.nan, index=D.index)}
        t = D.index.get_level_values(0)
        for yil in (2023, 2024, 2025, 2026):
            bas = pd.Timestamp(f"{yil}-01-01")
            egit = D[(t < bas - pd.Timedelta(days=H + 1))].dropna(subset=["y"])
            egit = egit[egit[kols].notna().sum(axis=1) >= len(kols) * 0.7]
            test = D[(t >= bas) & (t < pd.Timestamp(f"{yil+1}-01-01"))]
            test = test[test[kols].notna().sum(axis=1) >= len(kols) * 0.7]
            Xe = egit[kols].fillna(0.5).values - 0.5; ye = egit["y"].values - 0.5
            Xt = test[kols].fillna(0.5).values - 0.5
            tah["ridge"].loc[test.index] = Ridge(alpha=10.0).fit(Xe, ye).predict(Xt)
            m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                              min_samples_leaf=500, l2_regularization=1.0, random_state=389)
            tah["agac"].loc[test.index] = m.fit(Xe, ye).predict(Xt)
            print(f"  H{H} {yil}: egitim {len(egit):,} satir, test {len(test):,}", flush=True)
        for ad, p in tah.items():
            Pm = p.unstack(); R = ham.reindex_like(Pm)
            ic = Pm.T.corrwith(R.T, method="spearman") if False else pd.Series(
                [pd.Series(Pm.loc[i]).corr(pd.Series(R.loc[i]), method="spearman") for i in Pm.index], index=Pm.index)
            rk = Pm.rank(axis=1, pct=True)
            W = (rk >= 0.9).astype(float) - (rk <= 0.1).astype(float)
            lo = W.clip(lower=0); so = (-W).clip(lower=0)
            W = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 0.5 - \
                so.div(so.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 0.5
            if H > 1:
                W = W.iloc[::H].reindex(W.index).ffill().fillna(0)
            Wf = W.reindex(index=C.index, columns=C.columns).fillna(0)
            Wl = Wf.shift(1).fillna(0)
            g = (Wl * (C / C.shift(1) - 1).fillna(0).clip(-0.9, 3)).sum(axis=1) - (Wl * Fd).sum(axis=1) \
                - Wl.diff().abs().sum(axis=1).fillna(0) * MAL
            g = g[g.index >= "2023-01-01"]
            sh = lambda x: x.mean() / x.std() * np.sqrt(365.25) if x.std() > 0 else np.nan
            e = (1 + g).cumprod(); yil_ = (e.iloc[-1] ** (365.25 / len(g)) - 1) * 100
            dd = ((e / e.cummax()) - 1).min() * 100
            ix = g.index.intersection(carry.index)
            rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
            yy = " ".join(f"{y}: IC {ic[ic.index.year==y].mean():+.3f} Sh {sh(g[g.index.year==y]):+.2f}" for y in range(2023, 2027))
            print(f"H{H} {ad:<6} OOS 2023-26 net Sh {sh(g):+.2f} yillik %{yil_:+.1f} dusus %{dd:.1f} rho {rho:+.2f} | {yy}", flush=True)
            if ad == "agac":
                yic = [ic[ic.index.year == y].mean() for y in range(2023, 2027)]
                kabul = sh(g) >= 1.0 and min(yic) > 0 and rho <= 0.30
                print(f"   HUKUM H{H} agac: {'HARMAN TURUNA' if kabul else 'RED'}", flush=True)


if __name__ == "__main__":
    main()
