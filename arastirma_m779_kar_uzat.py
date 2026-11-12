#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 779 — süresi dolan KÂRDAKİ long'u uzat (778'in aynası; ZUZAT + ZUZAT_KAR=1). Ön kayıt KAR_HARITASI 779. Motor /tmp/m779/g33_m779.py.
Kollar: K12 (en çok +2 g), K30 (en çok +5 g); girişine geri düşerse ya da süre dolunca kapanır. Parite: ZUZAT=0 hiza 0 taban ile birebir.
  python3 arastirma_m779_kar_uzat.py kos | analiz"""
import os, sys, subprocess, pickle
import numpy as np
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m779"; R = os.path.dirname(os.path.abspath(__file__)); MOTOR = f"{OUT}/g33_m779.py"
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"PAR": ({"ZUZAT": "0"}, (0,)), "K12": ({"ZUZAT": "12", "ZUZAT_KAR": "1"}, (0, 1)), "K30": ({"ZUZAT": "30", "ZUZAT_KAR": "1"}, (0, 1))}


def kos():
    for ad, (ek, hz) in KOLLAR.items():
        for h in hz:
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)
            if ad == "PAR" and ok:
                a = pickle.load(open(e, "rb")); b = pickle.load(open("/tmp/m_ekim/M357_EK_T7KKS_2000_0.pkl", "rb"))
                d = float(np.nanmax(np.abs(a.values - b.reindex(a.index).values)))
                print("PARİTE (ZUZAT=0 vs taban hiza 0) en büyük fark", d, flush=True)
                if d > 1e-12: print("PARİTE TUTMADI — DUR"); sys.exit(1)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    seri = {}
    M.CIKTI = "/tmp/m_ekim"; seri["taban P3T2"] = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = OUT
    for a, ad in (("K12", "779 kârdaki long +2 gün"), ("K30", "779 kârdaki long +5 gün")):
        if all(os.path.exists(f"{OUT}/M357_EK_{a}_2000_{h}.pkl") for h in (0, 1)):
            seri[ad] = sum(M.gunluk(f"M357_EK_{a}_2000_{h}") for h in (0, 1)) / 2
        else:
            print(a, "EKSİK — sayılmaz")
    for ad, s in seri.items():
        s = s[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); k, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:30s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · "
              f"Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · eşit risk {er:.1f} (doz {k:.2f}) | ×1,15 yıllar "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))
    for a in ("K12", "K30"):
        for h in (0, 1):
            for l in open(f"{OUT}/M357_EK_{a}_2000_{h}.txt"):
                if "ZUZAT" in l: print(a, h, l.strip())


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
