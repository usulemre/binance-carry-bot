#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 799 — aday profiller (T1 / T4 / T6 / T6KS / T7K) Ekim + 1-15 Kasım'da (ölçüm, karar vermez). Taban P3T2 = /tmp/m783c.
  python3 arastirma_m799_profiller.py kos | analiz"""
import os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m799"; R = os.path.dirname(os.path.abspath(__file__))
PROF = {k: I.ANA[k][0] for k in ("EK_T1", "EK_T4", "EK_T6", "EK_T6KS", "EK_T7K")}


def tek(a):
    ad, h = a; e = f"{OUT}/M357_{ad}_2000_{h}.pkl"
    if os.path.exists(e): return ad, h, "var"
    env = dict(os.environ, **{**M.TABAN, **PROF[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=e + ".tmp", PYTHONPATH=R)
    with open(e.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
    ok = r.returncode == 0 and os.path.exists(e + ".tmp")
    if ok: os.replace(e + ".tmp", e)
    return ad, h, f"rc {r.returncode} " + ("TAMAM" if ok else "EKSİK — SAYILMAZ")


def kos():
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        for x in ex.map(tek, [(a, h) for a in PROF for h in (0, 1)]): print(*x, flush=True)


def analiz():
    seri = {}
    M.CIKTI = "/tmp/m783c"; seri["P3T2 (önerilen, T7K+KS)"] = (sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2, 1.15)
    for ad in PROF:
        if not all(os.path.exists(f"{OUT}/M357_{ad}_2000_{h}.pkl") for h in (0, 1)): print(ad, "EKSİK"); continue
        M.CIKTI = OUT; yeni = [M.gunluk(f"M357_{ad}_2000_{h}") for h in (0, 1)]
        M.CIKTI = "/tmp/m_ekim"; eski = [M.gunluk(f"M357_{ad}_2000_{h}") for h in (0, 1)]
        par = max(float(np.abs(yeni[h].reindex(eski[h][:"2026-10-29"].index) - eski[h][:"2026-10-29"]).max()) for h in (0, 1))
        print(f"PARİTE {ad} ≤ 29 Eki: {par:.1e}")
        seri[ad.replace("EK_", "")] = (sum(yeni) / 2, 1.15 if ad == "EK_T7K" else 1.0)
    print(f"\n{'profil':26s} {'doz':>4s} {'Eyl':>6s} {'Eki':>6s} {'Kas1-15':>8s} {'Eki+Kas':>8s} {'zirveden':>9s} {'6y maks dd':>10s} {'2026 Oca-Eyl':>12s}")
    for ad, (s, d) in seri.items():
        x = s * d; e = (1 + x).cumprod()
        def p(a, b): return ((1 + x[a:b]).prod() - 1) * 100
        print(f"{ad:26s} {d:4.2f} {p('2026-09-01','2026-09-30'):+6.1f} {p('2026-10-01','2026-10-31'):+6.1f} {p('2026-11-01','2026-11-15'):+8.1f} "
              f"{p('2026-10-01','2026-11-15'):+8.1f} {(e.iloc[-1] / e.cummax().iloc[-1] - 1) * 100:+9.1f} {((e / e.cummax()) - 1)[:'2026-09-30'].min() * 100:+10.1f} {p('2026-01-01','2026-09-30'):+12.0f}")


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
