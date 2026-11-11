#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 766 — prim çarpanı ısınması: BRUT_PRIM=0 (canlıdaki ilk ~90 gün) vs P3T2. Ön kayıt KAR_HARITASI 766. Motor g33.py (değişmez).
  python3 arastirma_m766_prim_isinma.py kos | analiz"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m766"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8), "BRUT_PRIM": "0"}


def kos():
    os.makedirs(OUT, exist_ok=True)
    for h in (0, 1):
        e = f"{OUT}/M357_EK_P0_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=e + ".tmp")
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    if not all(os.path.exists(f"{OUT}/M357_EK_P0_2000_{h}.pkl") for h in (0, 1)):
        print("EKSİK KOŞU"); return
    M.CIKTI = "/tmp/m_ekim"; b = (sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2)[:"2026-10-31"]
    M.CIKTI = OUT; v = (sum(M.gunluk(f"M357_EK_P0_2000_{h}") for h in (0, 1)) / 2)[:"2026-10-31"]
    for ad, s in (("P3T2 (prim açık)", b), ("prim kapalı (ilk 90 gün canlı)", v)):
        o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); k, er = Z.esit(zs)
        print(f"{ad:32s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · eşit risk {er:.1f}")
    b, v = b * 1.15, v * 1.15
    fg, fd = [], []
    idx = b.index
    for i in range(0, len(idx) - 90, 5):
        x, y = b.iloc[i:i + 90], v.iloc[i:i + 90]
        fg.append(((1 + y).prod() - (1 + x).prod()) * 100)
        ex, ey = (1 + x).cumprod(), (1 + y).cumprod()
        fd.append(((ey / ey.cummax()) - 1).min() * 100 - ((ex / ex.cummax()) - 1).min() * 100)
    fg, fd = np.array(fg), np.array(fd)
    print(f"90 günlük pencereler ({len(fg)}), ×1,15: getiri farkı (kapalı − açık) p10 {np.percentile(fg, 10):+.1f} · medyan {np.median(fg):+.1f} · "
          f"p90 {np.percentile(fg, 90):+.1f} puan | düşüş farkı p10 {np.percentile(fd, 10):+.1f} · medyan {np.median(fd):+.1f} · p90 {np.percentile(fd, 90):+.1f}")
    x, y = b["2026-08-01":"2026-10-31"], v["2026-08-01":"2026-10-31"]
    print(f"son 90 gün (Ağu–Eki 2026): açık {((1 + x).prod() - 1) * 100:+.1f}% · kapalı {((1 + y).prod() - 1) * 100:+.1f}%")
    yb = b.groupby(b.index.year).apply(lambda s: ((1 + s).prod() - 1) * 100); yv = v.groupby(v.index.year).apply(lambda s: ((1 + s).prod() - 1) * 100)
    print("yıllar açık / kapalı:", " ".join(f"{y}:{yb[y]:.0f}/{yv[y]:.0f}" for y in yb.index))


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
