#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 719 — short yenileme 36 sa (S_REB 9) önerilen ayarda (P3T2) vs taban 40 sa (S_REB 10). Ön kayıt KAR_HARITASI 719.
  python3 arastirma_m719_short36.py kos | analiz"""
import os, sys, subprocess, pickle
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m719"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8), "S_REB": "9"}


def kos():
    os.makedirs(OUT, exist_ok=True)
    for h in (0, 1):
        e = f"{OUT}/M357_EK_SR9_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=e + ".tmp")
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    if not all(os.path.exists(f"{OUT}/M357_EK_SR9_2000_{h}.pkl") for h in (0, 1)):
        print("EKSİK KOŞU"); return
    M.CIKTI = OUT; v = sum(M.gunluk(f"M357_EK_SR9_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = "/tmp/m_ekim"; b = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    for ad, s in [("taban 40 sa (S_REB 10)", b), ("36 sa (S_REB 9)", v)]:
        s = s[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); k, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100)
        print(f"{ad:24s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · "
              f"Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · eşit risk {er:.1f} (doz {k}) · Ekim {yl.get(2026, 0) and ((1+s['2026-10']).prod()-1)*100:.2f} | "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
