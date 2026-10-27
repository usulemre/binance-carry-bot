#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 623 — KOŞULLU STOP (madde 622 ADAY) DOĞRULAMA: 3.500 $ D2 ve TAM evren (kullanıcının 20-100 bin $'ı).
ÖN KAYIT: canlı gibi giriş + 5 bp + MERD_SIRA=1, uzun zemin, iki hiza. Kollar: D2 seviyesinde T7K, T7K+P3, T7K+P5; TAM'da T6, T6+P3, T7K+P3
(TAM T7K tabanı madde 601). Eşit-risk kısıtı her seviyede o seviyenin T4 1,0x'i. DOĞRULANDI: her seviyede eşit-risk farkı ≥ +4 (yarım bar)
VE Sharpe ≤2024 / 2025+ tabandan düşük değil. Tutarsa bot (kapanış stop'u + piyasa koşulu, tur başında) ve preflight.
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1", "KOM": "0.0005"}
T4 = {**G, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
T6 = {**T4, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "CAP_ORTAK": "1.0"}
T7K = {**T6, "CAP_ORTAK": "0.08", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0"}
P3 = {"SLL24_KAP": "1", "SLL24_PIY": "0.03"}; P5 = {"SLL24_KAP": "1", "SLL24_PIY": "0.05"}
SEV = os.environ.get("SEV", "TAM")
if SEV == "TAM":
    KIT = {"T4": T4, "T6": T6, "T7K": T7K, "T6P3": {**T6, **P3}, "T7KP3": {**T7K, **P3}}; HARIC = ""; D = "/tmp/m601"
else:
    KIT = {"T4": T4, "T7K": T7K, "T7KP3": {**T7K, **P3}, "T7KP5": {**T7K, **P5}}; HARIC = ",".join(M.D2); D = "/tmp/m623d2"
os.makedirs(D, exist_ok=True)


def kos(a):
    ad, h = a; out = f"{D}/{ad}_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **KIT[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=HARIC, E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return a, r.returncode


def gunluk(p):
    import pickle, pandas as pd
    E = pickle.load(open(p, "rb")); r = E.pct_change().dropna(); g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index); return g


def olc(d):
    eq = (1 + d).cumprod()
    return dict(yil=(eq.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(eq / eq.cummax() - 1).min() * 100,
                ek=d.min() * 100, g5=int((d < -0.05).sum()), sh=d.mean() / d.std() * np.sqrt(365.25))


def p1(d, idx):
    v = d.values; out = []
    for yol in idx:
        eq = np.cumprod(1 + v[yol]); out.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
    return np.percentile(out, 1)


def analiz():
    rng = np.random.default_rng(596)
    S = {k: sum(gunluk(f"{D}/{k}_{h}.pkl") for h in (0, 1)) / 2 for k in KIT}
    n = len(S["T4"]); idx = []
    for _ in range(3000):
        bas = rng.integers(0, n - 20, size=365 // 20 + 1); idx.append(np.concatenate([np.arange(b, b + 20) for b in bas])[:365])
    ref = olc(S["T4"]); ref["p1"] = p1(S["T4"], idx)
    print(f"{SEV} — T4 1,0x: yıllık {ref['yil']:+.1f} Sh {ref['sh']:.2f} dd {ref['dd']:.1f} en kötü {ref['ek']:.2f} −%5 {ref['g5']} 1y p1 {ref['p1']:.1f}")
    for k in KIT:
        ham = olc(S[k]); best = None
        for x in np.arange(0.70, 2.51, 0.05):
            d = S[k] * x; o = olc(d)
            if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
            o["p1"] = p1(d, idx)
            if o["p1"] < ref["p1"]: break
            best = (x, o)
        x, o = best
        _d = S[k]; _s = lambda q: q.mean() / q.std() * np.sqrt(365.25)
        h = f"Sh ≤24 {_s(_d[_d.index < '2025-01-01']):.2f} 25+ {_s(_d[_d.index >= '2025-01-01']):.2f}"
        print(f"{k:4s} ham {ham['yil']:+.1f} Sh {ham['sh']:.2f} dd {ham['dd']:.1f} en kötü {ham['ek']:.2f} | eşit risk k {x:.2f} → "
              f"{o['yil']:+.1f} dd {o['dd']:.1f} en kötü {o['ek']:.2f} −%5 {o['g5']} 1y p1 {o['p1']:.1f} {h}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(k, h) for h in (0, 1) for k in KIT]): print(x, flush=True)
    else:
        analiz()
