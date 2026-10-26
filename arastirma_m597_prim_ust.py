#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 597 — T7K'nın prim çarpanına ÜST (fırsat zenginken brüt > 1): kâr kolu mu, gizli kaldıraç mı?
T7K çarpanı yalnız azaltır (alt 0,7 · üst 1,0). Madde 239/288 primin zamanlaması GERÇEK (plasebo kazancı yok ediyor) dedi.
Soru: fırsat zengin dönemde brütü artırmak, AYNI ortalama riske sabit kaldıraçtan daha çok kazandırıyor mu (madde 257 testi)?
ÖN KAYIT: taban T7K standart + MERD_SIRA=1, 2.000 $ D8, iki hiza (/tmp/m592/T7K_*). Kollar: üst 1,2 ve 1,4 (alt 0,7, e 1).
Kıyas: kolun tam dönem maks düşüşüne kaldıraçlanmış T7K (k×). ADAY: iki hiza ort. yıllık ≥ kaldıraçlı T7K + 8 puan, üç dönemde
(2020-21 / 22-24 / 25-26) > kaldıraçlı T7K, ve en kötü gün kaldıraçlı T7K'dan kötü değil. Değilse "gizli kaldıraç" → RED.
"""
import os, subprocess, sys, pickle
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
T4 = {**TB.T1, "MERD_SIRA": "1", "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
T7K = {**T4, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0"}
D = "/tmp/m597"; os.makedirs(D, exist_ok=True)
KOL = {"U12": {"BRUT_UST": "1.2"}, "U14": {"BRUT_UST": "1.4"}}


def kos(a):
    ad, h = a; out = f"{D}/{ad}_{h}.pkl"
    if os.path.exists(out): return ad, h, "var"
    env = dict(os.environ, **{**M.TABAN, **T7K, **KOL[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out)
    with open(f"{D}/{ad}_{h}.txt", "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return ad, h, r.returncode


def gun(p):
    E = pickle.load(open(p, "rb")); r = E.pct_change().dropna(); d = (1 + r).groupby(r.index.date).prod() - 1
    d.index = pd.DatetimeIndex(d.index); return d


Y = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
DD = lambda x: ((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min() * 100
DON = (("2020", "2022"), ("2022", "2025"), ("2025", "2027"))


def analiz():
    for ad in KOL:
        sat = []
        for h in (0, 1):
            b, c = gun(f"/tmp/m592/T7K_{h}.pkl"), gun(f"{D}/{ad}_{h}.pkl")
            ks = np.arange(0.5, 2.5, 0.005); k = ks[np.argmin([abs(DD(b * x) - DD(c)) for x in ks])]
            bk = b * k
            sat.append((Y(c) - Y(bk), [Y(c[(c.index >= s) & (c.index < e)]) - Y(bk[(bk.index >= s) & (bk.index < e)]) for s, e in DON],
                        c.min() * 100, bk.min() * 100, k, Y(c), DD(c)))
        f = np.mean([s[0] for s in sat]); dp = np.mean([s[1] for s in sat], axis=0)
        ek, ekb = np.mean([s[2] for s in sat]), np.mean([s[3] for s in sat])
        aday = f >= 8 and all(dp > 0) and ek >= ekb
        print(f"{ad}: ham yıllık {np.mean([s[5] for s in sat]):+.1f} dd {np.mean([s[6] for s in sat]):.1f} | eşit-dd T7K×{np.mean([s[4] for s in sat]):.2f} "
              f"farkı {f:+.1f} · dönemler {dp[0]:+.1f}/{dp[1]:+.1f}/{dp[2]:+.1f} · en kötü {ek:.2f} vs {ekb:.2f} → {'ADAY' if aday else 'RED (gizli kaldıraç)'}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, h) for h in (0, 1) for a in KOL]): print(x, flush=True)
    else:
        analiz()
