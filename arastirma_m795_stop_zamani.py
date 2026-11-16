#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 795 — koşullu stop: canlı gibi aynı turda alınanı da kontrol (CANLI_STOP). Ön kayıt KAR_HARITASI 795. KARAR VERMEZ.
  python3 arastirma_m795_stop_zamani.py kos | analiz"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m795"; TABAN = "/tmp/m783b"; MOTOR = "/tmp/m795/g33_m795.py"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"CS": "1", "PAR": "0"}


def kos():
    for ad, deg in KOLLAR.items():
        e = f"{OUT}/M357_EK_{ad}_2000_0.pkl"
        if os.path.exists(e): print(ad, "var"); continue
        env = dict(os.environ, **ENV, CANLI_STOP=deg, FAZ_KAY="0", E_CIKTI=e + ".tmp", GUNLUK_KATKI=f"{OUT}/gk_{ad}_0.pkl", PYTHONPATH=R)
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(ad, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    M.CIKTI = TABAN; t = M.gunluk("M357_EK_KAS_2000_0")
    M.CIKTI = OUT; c = M.gunluk("M357_EK_CS_2000_0")
    if os.path.exists(f"{OUT}/M357_EK_PAR_2000_0.pkl"):
        p = M.gunluk("M357_EK_PAR_2000_0"); print(f"PARİTE PAR vs m783b hiza 0: en büyük günlük fark {np.abs(p - t.reindex(p.index)).max():.2e}")
    for ad, s0 in (("taban hiza 0", t), ("CS hiza 0 (canlı gibi)", c)):
        s = s0[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:24s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · eşit risk {er:.1f} | "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))
        k = s0["2026-11-06":"2026-11-14"] * 115; print("   6-14 Kas:", " ".join(f"{d:%d}:{v:+.2f}" for d, v in k.items()), f"toplam {((1 + k / 100).prod() - 1) * 100:+.2f}")
    for l in open(f"{OUT}/M357_EK_CS_2000_0.txt"):
        if "CANLI_STOP" in l: print(l.strip())


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
