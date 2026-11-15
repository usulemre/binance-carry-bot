#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 786 — short coin tavanı (CAP_ORTAK) %6 / %7 vs %8, P3T2. Ön kayıt KAR_HARITASI 786. Yalnız araştırma.
  python3 arastirma_m786_short_tavan.py kos | analiz"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m786"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"C6": "0.06", "C7": "0.07"}


def kos():
    os.makedirs(OUT, exist_ok=True)
    for ad, cap in KOLLAR.items():
        for h in (0, 1):
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **{**ENV, "CAP_ORTAK": cap}, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", GUNLUK_KATKI=f"{OUT}/gk_{ad}_{h}.pkl", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def kuyruk(gkler):
    G = pd.concat([pd.read_pickle(g).assign(h=i) for i, g in enumerate(gkler)]); G["gun"] = pd.to_datetime(G.gun)
    G = G[(G.ort_poz < 0) & (G.gun <= "2026-10-31")]
    k = G.groupby(["gun", "sembol"]).apply(lambda x: (x.fiyat + x.funding).sum() / 2 * 115).sort_values()
    return k


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    seri = {}
    M.CIKTI = "/tmp/m783"; seri["%8 (taban P3T2)"] = (sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2, [f"/tmp/m783/gk_{h}.pkl" for h in (0, 1)])
    M.CIKTI = OUT
    for ad, cap in KOLLAR.items():
        if all(os.path.exists(f"{OUT}/M357_EK_{ad}_2000_{h}.pkl") for h in (0, 1)):
            seri[f"%{int(float(cap) * 100)}"] = (sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2, [f"{OUT}/gk_{ad}_{h}.pkl" for h in (0, 1)])
        else: print(ad, "EKSİK — sayılmaz")
    for ad, (s, gk) in seri.items():
        s = s[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:16s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · "
              f"Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · eşit risk {er:.1f} (doz {kk:.2f}) | ×1,15 yıllar "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))
        k = kuyruk(gk)
        print(f"   tek short coinin en kötü günü (% kitap ×1,15): {k.iloc[0]:.2f} · en kötü 5: "
              + ", ".join(f"{d:%y-%m-%d} {sy[:-4]} {v:.2f}" for (d, sy), v in k.head(5).items())
              + f" · ≤ −%1,5 olan gün sayısı {int((k <= -1.5).sum())}")


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
