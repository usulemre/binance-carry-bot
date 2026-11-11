#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 765 — tamamlama ayrıştırma (TAMAMLA=2 long, 3 short) vs taban P3T2. Ön kayıt KAR_HARITASI 762. Yalnız araştırma.
Motor: /tmp/g33_m765.py (g33.py + yalnız TAMAMLA düğmesi).
  python3 arastirma_m765_tamamlama_taraf.py kos | analiz"""
import os, sys, subprocess, pickle
import numpy as np
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m765"; R = os.path.dirname(os.path.abspath(__file__)); MOTOR = "/tmp/g33_m765.py"
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"TL": {"TAMAMLA": "2"}, "TS": {"TAMAMLA": "3"}}


def kos():
    os.makedirs(OUT, exist_ok=True)
    for ad, ek in KOLLAR.items():          # parite önce
        for h in (0, 1):
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **ENV, **ek, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    if not all(os.path.exists(f"{OUT}/M357_EK_{a}_2000_{h}.pkl") for a in KOLLAR for h in (0, 1)):
        print("EKSİK KOŞU — analiz yapılmaz"); return
    seri = {}
    M.CIKTI = "/tmp/m_ekim"; seri["taban (tamamlama yok)"] = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = "/tmp/m762"; seri["762 iki taraf"] = sum(M.gunluk(f"M357_EK_TM_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = OUT
    seri["yalnız long"] = sum(M.gunluk(f"M357_EK_TL_2000_{h}") for h in (0, 1)) / 2
    seri["yalnız short"] = sum(M.gunluk(f"M357_EK_TS_2000_{h}") for h in (0, 1)) / 2
    for ad, s in seri.items():
        s = s[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); k, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:22s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · "
              f"Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · eşit risk {er:.1f} (doz {k:.2f}) | ×1,15 yıllar "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))
    for a in KOLLAR:
        for h in (0, 1):
            for l in open(f"{OUT}/M357_EK_{a}_2000_{h}.txt"):
                if "TAMAMLA" in l: print(f"{a} hiza {h}:", l.strip())


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
