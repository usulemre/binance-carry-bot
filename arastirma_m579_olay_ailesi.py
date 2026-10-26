#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 579 — CARRY DIŞI YENİ OLAY AİLELERİ (uzun zemin 2020-2026, 4 sa bar; nedensel, maliyet 10 bp gidiş-dönüş + gerçek funding).
Kullanıcı: "sadece T6 olarak düşünme". Hiç denenmemiş tek-coin olayları (madde 353/354/379 piyasa çapı ve haftalık pompaydı):
  A) TEK COİN KAPİTÜLASYONU: coin 24 sa'te ≥ X düştü, evren medyanı ise ≥ −%5 (piyasa çökmüyor) → LONG, H gün tut
  B) FUNDING DÖNÜŞÜ: funding (sk60) yüksek pozitiften (≥ %0,1/gün) ilk kez NEGATİFE döndü → LONG (short kalabalığı sıkışma yakıtı)
  C) AYNASI: funding derin negatiften pozitife döndü → SHORT
Her olay: giriş bar i+1 açılışı (≈ i kapanışı), çıkış H gün sonra. Kol getirisi = aktif olayların eşit ağırlıklı günlük ortalaması
(aktif yoksa nakit). Plasebo: aynı barlarda, aynı evrende RASTGELE coin (aynı yön). Elek (madde 353): Sh ≥ 1,5, Sh 2020-21/22-24/25-26
hepsi > 0,5, plasebo + 0,5, T6 ile korelasyon ≤ 0,30."""
import pickle, numpy as np, pandas as pd

Z = pickle.load(open("/tmp/zu/zemin.pkl", "rb"))
C = Z["C"]; cv = C.values; fv = np.nan_to_num(Z["ODE"].values); U = Z["uy"].values
S = pickle.load(open("/tmp/zu/sk_bar60.pkl", "rb")).reindex(index=C.index, columns=C.columns).values
T, N = cv.shape
r1 = np.full_like(cv, np.nan); r1[1:] = cv[1:] / cv[:-1] - 1
r6 = np.full_like(cv, np.nan); r6[6:] = cv[6:] / cv[:-6] - 1
med6 = np.nanmedian(np.where(U, r6, np.nan), axis=1)
rng = np.random.default_rng(7)
KOM = 0.0010


def olaylar_A(X):
    m = U & (r6 <= -X) & (med6[:, None] >= -0.05)
    return m, +1


def olaylar_B():
    S2 = np.full_like(S, np.nan); S2[6:] = np.nanmax(np.stack([S[k:T - 6 + k] for k in range(6)]), axis=0) if False else S[:-6]
    onc = np.full_like(S, np.nan); onc[6:] = pd.DataFrame(S).rolling(42, min_periods=18).max().values[:-6]
    m = U & (onc >= 0.001) & (S < 0) & np.isfinite(S)
    return m, +1


def olaylar_C():
    onc = np.full_like(S, np.nan); onc[6:] = pd.DataFrame(S).rolling(42, min_periods=18).min().values[:-6]
    m = U & (onc <= -0.001) & (S > 0) & np.isfinite(S)
    return m, -1


def kol(m, yon, H, plasebo=False):
    """Günlük getiri serisi. m[i,k] True: bar i kapanışında olay → i..i+6H barı boyunca pozisyon."""
    hb = 6 * H
    gun = np.zeros(T); say = np.zeros(T)
    ii, kk = np.nonzero(m)
    # aynı coinde tutma süresi içinde tekrar eden olayı at
    son = {}
    sec = []
    for i, k in zip(ii, kk):
        if i + hb + 1 >= T: continue
        if son.get(k, -10**9) + hb > i: continue
        son[k] = i; sec.append((i, k))
    for i, k in sec:
        if plasebo:
            adaylar = np.flatnonzero(U[i] & np.isfinite(cv[i]))
            if len(adaylar) == 0: continue
            k = int(rng.choice(adaylar))
        p = cv[i:i + hb + 1, k]
        if not np.isfinite(p).all(): continue
        r = yon * (p[1:] / p[:-1] - 1) - yon * fv[i + 1:i + hb + 1, k]
        r[0] -= KOM / 2; r[-1] -= KOM / 2
        gun[i + 1:i + hb + 1] += r; say[i + 1:i + hb + 1] += 1
    bar = np.where(say > 0, gun / np.maximum(say, 1), 0.0)
    g = pd.Series(bar, index=C.index).groupby(C.index.normalize()).apply(lambda x: (1 + x).prod() - 1)
    return g.loc["2020-07-19":], len(sec)


def sh(g):
    return float(g.mean() / g.std() * np.sqrt(365)) if g.std() > 0 else 0.0


import arastirma_m497_uzun_gecmis as UG
t6 = UG.seri("Q_T6")
print(f"{'kol':22s} olay   yıllık    Sh   20-21  22-24  25-26   dd     plasebo Sh   kor(T6)  elek")
for ad, (m, yon) in [("A kapitülasyon %25", olaylar_A(0.25)), ("A kapitülasyon %35", olaylar_A(0.35)),
                     ("B funding +→− long", olaylar_B()), ("C funding −→+ short", olaylar_C())]:
    for H in (1, 3, 5):
        g, n = kol(m, yon, H); gp, _ = kol(m, yon, H, plasebo=True)
        y = ((1 + g).prod() ** (365 / len(g)) - 1) * 100
        e = (1 + g).cumprod(); dd = float((e / e.cummax() - 1).min() * 100)
        d = [sh(g.loc[a:b]) for a, b in (("2020", "2021"), ("2022", "2024"), ("2025", "2026"))]
        k = float(np.corrcoef(g.reindex(t6.index).fillna(0), t6)[0, 1])
        ok = sh(g) >= 1.5 and all(x > 0.5 for x in d) and sh(g) >= sh(gp) + 0.5 and abs(k) <= 0.3
        print(f"{ad:22s} H{H} {n:5d} {y:+8.1f} {sh(g):5.2f} {d[0]:6.2f} {d[1]:6.2f} {d[2]:6.2f} {dd:6.1f}   {sh(gp):6.2f}     {k:+.2f}   {'GEÇTİ' if ok else '-'}")
