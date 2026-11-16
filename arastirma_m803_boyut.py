#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 803 — meta-labeling boyutlandırma (802 sıçrama olasılığı). Ön kayıt KAR_HARITASI 803. KARAR VERMEZ.
  python3 arastirma_m803_boyut.py kos | analiz"""
import os, sys, subprocess
import arastirma_m346_prim as M, izleme_ekim_oos as I
import arastirma_m802_sicrama as S
OUT = "/tmp/m803"; MOTOR = "/tmp/m803/g33_m803.py"; R = os.path.dirname(os.path.abspath(__file__))
KOLLAR = {"B05": "0.5", "B10": "1.0"}


def kos():
    for ad, a in KOLLAR.items():
        for h in (0, 1):
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **S.ENV, OLAS_A=a, OLAS_DOSYA="/tmp/m802/veto.pkl", FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    S.OUT = OUT; S.KOLLAR = {}
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    M.CIKTI = S.TABAN; seri = {"taban P3T2": sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2}
    M.CIKTI = OUT
    for ad, a in KOLLAR.items():
        if all(os.path.exists(f"{OUT}/M357_EK_{ad}_2000_{h}.pkl") for h in (0, 1)):
            seri[f"boyut a={a}"] = sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2
    for ad, s0 in seri.items():
        s = s0[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        ek = ((1 + s0["2026-10-01":"2026-11-15"] * 1.15).prod() - 1) * 100
        print(f"{ad:14s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · "
              f"eşit risk {er:.1f} | ×1,15 " + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()) + f" | Eki+Kas {ek:+.1f}")
    for ad in KOLLAR:
        for l in open(f"{OUT}/M357_EK_{ad}_2000_0.txt"):
            if "OLAS_A" in l: print(ad, l.strip())


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
