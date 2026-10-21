#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 384 — HİÇ DENENMEMİŞ İKİ AİLE: ÇİFT TİCARETİ VE OYNAKLIK SIKIŞMASI.

ÖRNEK DIŞI YÖNTEM (madde 381 ile aynı, koşudan ÖNCE yazıldı):
seçim yalnız IS (2022-04..2024-12) Sharpe'ıyla; her aile için IS'te en
iyi TEK kol OOS'ta (2025-01..2026-08) raporlanır. KABUL (sonraki tura):
OOS net Sharpe >= 1,0, OOS plasebosunu >= 0,5 geçer, carry ile rho <= 0,30.

ORTAK: 4 sa panel, günlük karar (00 UTC kapanışı), giriş ertesi gün,
maliyet devir x taker %0,05, funding gerçek (günlük, madde 381 hizası).
Evren: TradFi hariç, hacim >= 50M$/gün, yaş >= 120 gün.

A. ÇİFT TİCARETİ (kointegrasyon-benzeri, nedensel):
   Her ay başında: son 90 günde günlük log getirisi korelasyonu en
   yüksek K çift (aynı coin en fazla 3 çiftte). Çift için log fiyat
   farkı s = ln A - b ln B, b = son 60 günün OLS eğimi; z = (s - ort60)/sd60.
   |z| >= GIR -> ucuz bacak long, pahalı short (dolar nötr, çift başı
   eşit); |z| <= 0,5 ya da 10 gün -> çık. Portföy: açık çiftlere eşit
   pay, brüt 1. PLASEBO: z işareti rastgele.
   Izgara: K {10, 30} x GIR {1,5 · 2,0 · 2,5}.
B. OYNAKLIK SIKIŞMASI KIRILIMI:
   Günlük aralık genişliği w = (20 gün en yüksek - en düşük)/fiyat; w'nin
   kendi 180 günlük yüzdeliği <= Q iken fiyat 20 günlük tepeyi aşarsa
   LONG, dibi kırarsa SHORT; H gün tut. Portföy: eşit pay, en fazla 20,
   brüt 1; piyasa nötrlüğü YOK (yönlü) — o yüzden BTC'ye karşı beta
   raporlanır. PLASEBO: aynı sayıda, aynı coinlerde rastgele gün ve yön.
   Izgara: Q {0,10 · 0,20} x H {3 · 7 · 14} x yön {her ikisi · yalnız long}.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import arastirma_m381_cok_ufuk as U  # noqa: E402

KOM = 0.0005
RNG = np.random.default_rng(384)


def yukle():
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); P = pickle.load(open("/tmp/panel.pkl", "rb"))
    hlo = pickle.load(open("/tmp/hlo.pkl", "rb"))
    C4 = z["C"]; sec = C4.index.hour == 0
    C = C4[sec]
    # günlük H/L: o güne ait 6 barın max/min (gün = (t-24sa, t])
    H4 = hlo["H"].reindex_like(C4); L4 = hlo["L"].reindex_like(C4)
    gun = (C4.index - pd.Timedelta(hours=1)).floor("D") + pd.Timedelta(days=1)
    Hd = H4.groupby(gun).max().reindex(C.index); Ld = L4.groupby(gun).min().reindex(C.index)
    _, Fd, _ = U.yukle()
    from tradfi_liste import TRADFI
    HAC = P["HAC"].reindex_like(C4)[sec]; YAS = P["YAS"].reindex_like(C4)[sec]
    uy = (HAC >= 5e7) & (YAS >= 120 * 6) & C.notna()
    uy = uy & ~uy.columns.isin(list(TRADFI))
    return C, Hd, Ld, Fd.reindex_like(C).fillna(0.0), uy


def sh(g):
    g = np.asarray(g, float)
    return float(g.mean() / g.std() * np.sqrt(365.25)) if g.std() > 0 else np.nan


def gunluk_getiri(W, C, Fd):
    Wl = W.shift(1).fillna(0.0)
    R1 = (C / C.shift(1) - 1).fillna(0.0).clip(-0.95, 5)
    return (Wl * R1).sum(axis=1) - (Wl * Fd).sum(axis=1) - Wl.diff().abs().sum(axis=1).fillna(0.0) * KOM


# ------------------------------------------------------------------ A
def ciftler(C, uy, K, GIR, plasebo=False):
    lp = np.log(C)
    r = lp.diff()
    W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    aylar = C.index[C.index.is_month_start]
    acik = {}                                  # (a,b) -> (yön, giriş_i, beta)
    secili = []
    for i, t in enumerate(C.index):
        if i < 120:
            continue
        if t in aylar:
            pen = r.iloc[i - 90:i]
            ok = [c for c in C.columns if uy.iloc[i][c] and pen[c].notna().sum() >= 80]
            if len(ok) >= 10:
                kor = pen[ok].corr().where(lambda x: ~np.eye(len(ok), dtype=bool))
                st = kor.stack().sort_values(ascending=False)
                say, secili = {}, []
                for (a, b), v in st.items():
                    if a >= b or say.get(a, 0) >= 3 or say.get(b, 0) >= 3:
                        continue
                    secili.append((a, b)); say[a] = say.get(a, 0) + 1; say[b] = say.get(b, 0) + 1
                    if len(secili) >= K:
                        break
        for (a, b) in list(acik):
            d, i0, beta = acik[(a, b)]
            s = lp[a].iloc[i - 60:i + 1] - beta * lp[b].iloc[i - 60:i + 1]
            z = (s.iloc[-1] - s.iloc[:-1].mean()) / (s.iloc[:-1].std() + 1e-12)
            if abs(z) <= 0.5 or i - i0 >= 10 or not (uy.iloc[i][a] and uy.iloc[i][b]):
                del acik[(a, b)]
        for (a, b) in secili:
            if (a, b) in acik or not (uy.iloc[i][a] and uy.iloc[i][b]):
                continue
            ya, yb = lp[a].iloc[i - 60:i + 1], lp[b].iloc[i - 60:i + 1]
            if ya.isna().any() or yb.isna().any():
                continue
            beta = np.polyfit(yb.values[:-1], ya.values[:-1], 1)[0]
            s = ya - beta * yb
            z = (s.iloc[-1] - s.iloc[:-1].mean()) / (s.iloc[:-1].std() + 1e-12)
            if abs(z) >= GIR:
                d = -np.sign(z)                # z>0: A pahalı -> A short, B long
                if plasebo:
                    d = RNG.choice([-1, 1])
                acik[(a, b)] = (d, i, beta)
        if acik:
            pay = 1.0 / len(acik)
            for (a, b), (d, _, _) in acik.items():
                W.iat[i, W.columns.get_loc(a)] += d * pay / 2
                W.iat[i, W.columns.get_loc(b)] -= d * pay / 2
    return W


# ------------------------------------------------------------------ B
def sikisma(C, Hd, Ld, uy, Q, H, yon, plasebo=False):
    hi20 = Hd.rolling(20, min_periods=20).max(); lo20 = Ld.rolling(20, min_periods=20).min()
    w = (hi20 - lo20) / C
    wp = w.rolling(180, min_periods=120).rank(pct=True)
    dar = (wp.shift(1) <= Q)
    up = dar & (C > hi20.shift(1)) & uy
    dn = dar & (C < lo20.shift(1)) & uy
    sig = up.astype(int) - (dn.astype(int) if yon == "iki" else 0)
    v = sig.values.astype(float)
    if plasebo:
        p = np.zeros_like(v)
        for j in range(v.shape[1]):
            n = int((v[:, j] != 0).sum())
            ad = np.flatnonzero(uy.values[:, j])
            if n and len(ad):
                ix = RNG.choice(ad, size=min(n, len(ad)), replace=False)
                p[ix, j] = RNG.choice([-1, 1], size=len(ix)) if yon == "iki" else 1
        v = p
    T, N = v.shape
    pos = np.zeros((T, N))
    for j in range(N):
        for i in np.flatnonzero(v[:, j]):
            pos[i:min(i + H, T), j] = v[i, j]
    n = np.abs(pos).sum(axis=1, keepdims=True)
    W = np.where(n > 0, pos / np.maximum(n, 20), 0.0)   # en fazla 20 eşit pay, brüt <= 1
    return pd.DataFrame(W, index=C.index, columns=C.columns)


def rapor(ad, g, gp, carry, btc):
    IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
    e = (1 + g).cumprod(); dd = ((e / e.cummax()) - 1).min() * 100
    ix = g.index.intersection(carry.index)
    rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
    beta = float(np.cov(g.loc[btc.index], btc)[0, 1] / btc.var())
    return dict(ad=ad, IS=sh(IS), OOS=sh(OOS), PLA=sh(gp[gp.index >= "2025-01-01"]),
                rho=rho, beta=beta, dd=dd)


def main():
    C, Hd, Ld, Fd, uy = yukle()
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    btc = (C["BTCUSDT"] / C["BTCUSDT"].shift(1) - 1).fillna(0.0)
    bas = "2022-04-01"
    for aile, kollar in (
        ("CIFT", [(K, G) for K in (10, 30) for G in (1.5, 2.0, 2.5)]),
        ("SIKISMA", [(Q, H, y) for Q in (0.10, 0.20) for H in (3, 7, 14) for y in ("iki", "long")]),
    ):
        sat = []
        for k in kollar:
            if aile == "CIFT":
                W, Wp = ciftler(C, uy, *k), ciftler(C, uy, *k, plasebo=True)
            else:
                W, Wp = sikisma(C, Hd, Ld, uy, *k), sikisma(C, Hd, Ld, uy, *k, plasebo=True)
            g = gunluk_getiri(W, C, Fd); g = g[g.index >= bas]
            gp = gunluk_getiri(Wp, C, Fd); gp = gp[gp.index >= bas]
            sat.append(rapor(f"{aile} {k}", g, gp, carry, btc.loc[g.index]))
            print(f"  {sat[-1]['ad']:<30} IS {sat[-1]['IS']:>5.2f} OOS {sat[-1]['OOS']:>5.2f} "
                  f"PLA_OOS {sat[-1]['PLA']:>5.2f} rho {sat[-1]['rho']:+.2f} beta {sat[-1]['beta']:+.2f} "
                  f"dusus {sat[-1]['dd']:.1f}", flush=True)
        en = max(sat, key=lambda x: x["IS"] if np.isfinite(x["IS"]) else -9)
        kabul = en["OOS"] >= 1.0 and en["OOS"] - en["PLA"] >= 0.5 and en["rho"] <= 0.30
        print(f"{aile}: IS'TE SECILEN {en['ad']} (IS {en['IS']:.2f}) -> OOS {en['OOS']:.2f}, "
              f"PLA {en['PLA']:.2f} -> {'SONRAKI TURA' if kabul else 'RED'}\n", flush=True)


if __name__ == "__main__":
    main()
