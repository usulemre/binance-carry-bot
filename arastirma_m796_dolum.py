#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 796 — limit (TP / kademe) dolum iyimserliği: DOL_ASIM. Ön kayıt KAR_HARITASI 796. KARAR VERMEZ.
  python3 arastirma_m796_dolum.py kos | analiz"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m796"; TABAN = "/tmp/m783c"; MOTOR = "/tmp/m796/g33_m796.py"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"A02": "0.002", "A10": "0.01"}


def kos():
    for ad, deg in KOLLAR.items():
        for h in (0, 1):
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **ENV, DOL_ASIM=deg, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", GUNLUK_KATKI=f"{OUT}/gk_{ad}_{h}.pkl", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    M.CIKTI = TABAN; seri = {"taban (tam değince dolar)": sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2}
    M.CIKTI = OUT
    for ad, deg in KOLLAR.items():
        if all(os.path.exists(f"{OUT}/M357_EK_{ad}_2000_{h}.pkl") for h in (0, 1)):
            seri[f"%{float(deg) * 100:.1f} geçerse dolar"] = sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2
        else: print(ad, "EKSİK — sayılmaz")
    for ad, s0 in seri.items():
        s = s0[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        ay = s0["2026-07-01":].resample("ME").apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:26s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · eşit risk {er:.1f} | ×1,15 "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()) + " | 2026 Tem-Kas " + " ".join(f"{x:+.1f}" for x in ay.values))


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
