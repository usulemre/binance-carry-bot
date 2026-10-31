#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 685 — dinamik doz (oynaklık hedefi / kitap momentumu / düşüşe göre) önerilen ayarda. Ön kayıt KAR_HARITASI 685."""
import numpy as np, pandas as pd
import arastirma_m346_prim as M

M.CIKTI = "/tmp/m622"; P = sum(M.gunluk(f"M357_EK_P3T2_2000_{h}") for h in (0, 1)) / 2
M.CIKTI = "/tmp/m_ekim_kuru"; T4 = sum(M.gunluk(f"M357_EK_T4_2000_{h}") for h in (0, 1)) / 2
P, T4 = P.align(T4, join="inner")
MAL = 0.0010; ESIK = 0.05


def uygula(olcek_fn):
    v = P.values; n = len(v); out = np.zeros(n); k = 1.0; eq = [1.0]; zirve = 1.0
    for t in range(n):
        hedef = olcek_fn(t, v, eq, zirve)
        if hedef is not None and abs(hedef - k) >= ESIK:
            out[t] -= MAL * abs(hedef - k); k = hedef
        out[t] += k * v[t]
        eq.append(eq[-1] * (1 + out[t])); zirve = max(zirve, eq[-1])
    return pd.Series(out, index=P.index)


SDMED = float(pd.Series(P.values).rolling(20).std().median())
SDMED60 = float(pd.Series(P.values).rolling(60).std().median())


def v_hedef(pen, med):
    def f(t, v, eq, z):
        if t < pen: return None
        return float(np.clip(med / max(v[t - pen:t].std(), 1e-9), 0.7, 1.6))
    return f


def mom(t, v, eq, z):
    if t < 395: return None
    r30 = pd.Series(v[t - 395:t]).rolling(30).sum().dropna().values
    z_ = (r30[-1] - r30[:-1][-365:].mean()) / max(r30[:-1][-365:].std(), 1e-9)
    return float(np.clip(1 + 0.25 * z_, 0.7, 1.3))


def dd_(t, eq, z): return eq[-1] / z - 1
def dda(t, v, eq, z): d = dd_(t, eq, z); return 0.5 if d < -0.10 else 0.75 if d < -0.05 else 1.0
def dda2(t, v, eq, z): return max(0.5, 1 + 3 * dd_(t, eq, z))
def ddb(t, v, eq, z): d = dd_(t, eq, z); return 1.5 if d < -0.10 else 1.25 if d < -0.05 else 1.0


KOL = {"V20": v_hedef(20, SDMED), "V60": v_hedef(60, SDMED60), "MOM": mom, "DDA": dda, "DDA2": dda2, "DDB": ddb}


def olc(d):
    e = (1 + d).cumprod()
    return dict(yil=(e.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(e / e.cummax() - 1).min() * 100, ek=d.min() * 100)


def sh(d): return d.mean() / d.std() * np.sqrt(365.25)


rng = np.random.default_rng(596); n = len(P)
IDX = [np.concatenate([np.arange(b, b + 20) for b in rng.integers(0, n - 20, size=19)])[:365] for _ in range(3000)]
def p1(d):
    v = d.values; return np.percentile([((np.cumprod(1 + v[i])) / np.maximum.accumulate(np.cumprod(1 + v[i])) - 1).min() * 100 for i in IDX], 1)


ref = olc(T4); ref["p1"] = p1(T4)
def esit(d):
    best = None
    for k in np.arange(0.80, 2.51, 0.05):
        x = d * k; o = olc(x)
        if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
        if p1(x) < ref["p1"]: break
        best = (k, o["yil"])
    return best or (np.nan, np.nan)


if __name__ == "__main__":
    print(f"T4 risk: dd {ref['dd']:.1f} en kötü {ref['ek']:.2f} p1 {ref['p1']:.1f}")
    S = {"P3T2": P, **{a: uygula(f) for a, f in KOL.items()}}
    base_sh = None; base_er = None
    for a, d in S.items():
        o = olc(d); k, er = esit(d); s1, s2 = sh(d[d.index < "2025-01-01"]), sh(d[d.index >= "2025-01-01"])
        if a == "P3T2": base_sh, base_er = (s1, s2), er
        ver = "" if a == "P3T2" else (" → ADAY" if er >= base_er + 8 and s1 >= base_sh[0] and s2 >= base_sh[1] else " → RED")
        print(f"{a:5s} ham {o['yil']:+7.1f} dd {o['dd']:6.1f} en kötü {o['ek']:6.2f} | Sh ≤24 {s1:.2f} 25+ {s2:.2f} | eşit-risk k {k:.2f} → {er:+.1f}{ver}")
