#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 619 — T6 KOMŞULUĞU KULLANICININ GERÇEK BAKİYESİNDE (TAM evren, 20-100 bin $). T6'nın ayarları (short tavansız, short 96 sa
penceresi, short 40 sa) 2.000 / 3.500 $ dışlamalı evrende seçildi (madde 568-573); TAM'da T6 1,10x en kârlı (madde 601/618). TAM evren daha
geniş ve uçlu → short tarafının optimumu kaymış olabilir.
ÖN KAYIT: madde 601 koşulu. Kollar (T6'dan tek değişiklik): C12 short coin tavanı %12 · W72 short penceresi 72 sa · W144 short penceresi
144 sa · R12 short 48 sa'te bir. ADAY: eşit-risk yıllığı T6'dan (+354,9) ≥ +8 (TAM T4 1,0x kısıtı).
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1", "KOM": "0.0005"}
T4 = {**G, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
T6 = {**T4, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "CAP_ORTAK": "1.0"}
T7K = {**T6, "CAP_ORTAK": "0.08", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0"}
KIT = {"T4": T4, "T6": T6, "C12": {**T6, "CAP_ORTAK": "0.12", "CAP_TARAF": "short"}, "W72": {**T6, "SK_DOSYA_S": "/tmp/zu/sk_bar72.pkl"},
       "W144": {**T6, "SK_DOSYA_S": "/tmp/zu/sk_bar144.pkl"}, "R12": {**T6, "S_REB": "12"}}
D = "/tmp/m601"; os.makedirs(D, exist_ok=True)


def kos(a):
    ad, h = a; out = f"{D}/{ad}_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **KIT[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC="", E_CIKTI=out)
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
    print(f"TAM evren — T4 1,0x: yıllık {ref['yil']:+.1f} Sh {ref['sh']:.2f} dd {ref['dd']:.1f} en kötü {ref['ek']:.2f} −%5 {ref['g5']} 1y p1 {ref['p1']:.1f}")
    for k in KIT:
        ham = olc(S[k]); best = None
        for x in np.arange(0.70, 2.51, 0.05):
            d = S[k] * x; o = olc(d)
            if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
            o["p1"] = p1(d, idx)
            if o["p1"] < ref["p1"]: break
            best = (x, o)
        x, o = best
        h = "ADAY" if k not in ("T4", "T1") and o["yil"] - ref["yil"] >= 8 else ""
        print(f"{k:4s} ham {ham['yil']:+.1f} Sh {ham['sh']:.2f} dd {ham['dd']:.1f} en kötü {ham['ek']:.2f} | eşit risk k {x:.2f} → "
              f"{o['yil']:+.1f} dd {o['dd']:.1f} en kötü {o['ek']:.2f} −%5 {o['g5']} 1y p1 {o['p1']:.1f} {h}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(k, h) for h in (0, 1) for k in KIT]): print(x, flush=True)
    else:
        analiz()
