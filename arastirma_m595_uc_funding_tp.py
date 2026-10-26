#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 595 — YENİ EKSEN: girişte funding'i UÇ olan LONG bacağa daha yüksek son TP.
Ölçülmemiş olan: TP hep tek seviye (madde 227/300/536) ya da oynaklıkla ölçekli (madde 221, RED). Funding UÇLUĞUNA bağlı TP
hiç ölçülmedi. Mekanizma: en negatif funding = en kalabalık short = en büyük sıkışma potansiyeli; +%60'ta kapatmak bu
bacakların kuyruğunu kesiyor olabilir (madde 236: kazancın tamamı long TP kuyruğunda).

ÖN KAYIT (koşudan önce): taban T4 standart model + MERD_SIRA=1, 2.000 $ D8, uzun zemin, iki hiza (/tmp/m591/K_*).
Kollar: X = rezerv eşiği 0,015/gün (önceden tanımlı, ayarlanmadı) ile uç long TP 0,80 / 1,00; X = 0,005 ile 0,80.
ADAY şartı (madde 503 kuralı, iki hiza ortalaması): tüm dönem yıllık ≥ +8 puan, Sharpe ≥ +0,05, dd en fazla 1 puan derin,
üç dönemde (2020-21 / 2022-24 / 2025-26) yıllık farkı > 0. Aday çıkarsa canlı gibi giriş + 5 bp protokolüne gider.
"""
import os, subprocess, sys, pickle
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
T4 = {**TB.T1, "MERD_SIRA": "1", "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
D = "/tmp/m595"; os.makedirs(D, exist_ok=True)
KOL = {"U80": {"TPF_UC": "0.80"}, "U100": {"TPF_UC": "1.00"}, "U80X5": {"TPF_UC": "0.80", "TPF_ESIK": "0.005"}}


def kos(a):
    ad, h = a; out = f"{D}/{ad}_{h}.pkl"
    if os.path.exists(out): return ad, h, "var"
    env = dict(os.environ, **dict(M.TABAN, **T4, **KOL[ad]), FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out)
    with open(f"{D}/{ad}_{h}.txt", "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return ad, h, r.returncode


def gun(p):
    E = pickle.load(open(p, "rb")); r = E.pct_change().dropna(); d = (1 + r).groupby(r.index.date).prod() - 1
    d.index = pd.DatetimeIndex(d.index); return d


def olc(d):
    eq = (1 + d).cumprod(); y = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
    return dict(yil=y(d), sh=d.mean() / d.std() * np.sqrt(365.25), dd=(eq / eq.cummax() - 1).min() * 100,
                ek=d.min() * 100, g5=int((d < -0.05).sum()),
                p=[y(d[(d.index >= a) & (d.index < b)]) for a, b in (("2020", "2022"), ("2022", "2025"), ("2025", "2027"))])


def analiz():
    k = [olc(gun(f"/tmp/m591/K_{h}.pkl")) for h in (0, 1)]
    ort = lambda L, x: np.mean([o[x] for o in L])
    print(f"taban T4: yıllık {ort(k,'yil'):+.1f} Sh {ort(k,'sh'):.2f} dd {ort(k,'dd'):.1f} en kötü {ort(k,'ek'):.2f} −%5 {ort(k,'g5'):.1f}")
    for ad in KOL:
        o = [olc(gun(f"{D}/{ad}_{h}.pkl")) for h in (0, 1)]
        dy, ds, dd = ort(o, "yil") - ort(k, "yil"), ort(o, "sh") - ort(k, "sh"), ort(o, "dd") - ort(k, "dd")
        dp = [np.mean([o[h]["p"][j] - k[h]["p"][j] for h in (0, 1)]) for j in range(3)]
        aday = dy >= 8 and ds >= 0.05 and dd >= -1 and all(x > 0 for x in dp)
        print(f"{ad:6s} yıllık {dy:+6.1f} Sh {ds:+.3f} dd {dd:+.1f} en kötü {ort(o,'ek'):.2f} −%5 {ort(o,'g5'):.1f} | "
              f"2020-21 {dp[0]:+.1f} · 22-24 {dp[1]:+.1f} · 25-26 {dp[2]:+.1f}  → {'ADAY' if aday else 'RED'}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, h) for h in (0, 1) for a in KOL]): print(x, flush=True)
    else:
        analiz()
