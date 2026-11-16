#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 794 — demo haftası (6-14 Kas) Binance girişi taklidiyle (TEK_BINANCE=1). Ön kayıt KAR_HARITASI 794. KARAR VERMEZ.
  python3 arastirma_m794_hafta_binance.py kos | analiz"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m794"; TABAN = "/tmp/m783b"; MOTOR = "/tmp/m788/g33_m788.py"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8), "TEK_BINANCE": "1"}
RAMPA = dict(zip(pd.date_range("2026-11-06", "2026-11-14"), [0.1, 0.3, 0.5, 0.7, 0.9, 1, 1, 1, 1]))


def kos():
    os.makedirs(OUT, exist_ok=True); ps = []
    for h in (0, 1):
        e = f"{OUT}/M357_EK_BIN_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", GUNLUK_KATKI=f"{OUT}/gk_{h}.pkl", PYTHONPATH=R)
        ps.append((h, e, subprocess.Popen([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=open(e.replace(".pkl", ".txt"), "w"), stderr=subprocess.STDOUT)))
    for h, e, p in ps:
        rc = p.wait(); ok = rc == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", rc, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def ozet(ad, s):
    k = s["2026-11-06":"2026-11-14"] * 115
    rp = np.prod([1 + v * RAMPA[d] / 100 for d, v in k.items()]) - 1; tk = (1 + k["2026-11-07":] / 100).prod() - 1
    print(f"{ad:22s} rampa ayarlı 6-14 {rp * 100:+.2f}% · tam kitap 7-14 {tk * 100:+.2f}% | gün: " + " ".join(f"{d:%d}:{v:+.2f}" for d, v in k.items()))


def analiz():
    M.CIKTI = TABAN; t = [M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)]
    M.CIKTI = OUT; b = [M.gunluk(f"M357_EK_BIN_2000_{h}") for h in (0, 1)]
    M.CIKTI = "/tmp/m788"; o = [M.gunluk(f"M357_EK_BIN_2000_{h}") for h in (0, 1)]
    for h in (0, 1):
        x = b[h][:"2026-11-12"]; print(f"PARİTE BIN hiza {h} ≤ 12 Kas vs 788: en büyük günlük fark {np.abs(x - o[h].reindex(x.index)).max():.2e}")
        print(f"  BIN vs taban ≤ 31 Eki fark (beklenen ≠ 0): toplam {(b[h][:'2026-10-31'].sum() - t[h][:'2026-10-31'].sum()) * 100:+.1f} puan")
    ozet("taban (motor girişi)", (t[0] + t[1]) / 2); ozet("BIN (canlı gibi)", (b[0] + b[1]) / 2)
    for h in (0, 1): ozet(f"  hiza {h} taban", t[h]); ozet(f"  hiza {h} BIN", b[h])
    print("demo 6-14 Kas ≈ −3,6%")

    def gk(d):
        G = pd.concat([pd.read_pickle(f"{d}/gk_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun)
        G = G[(G.gun >= "2026-11-07") & (G.gun <= "2026-11-14")]; G["net"] = (G.fiyat + G.funding) / 2 * 115
        return G.groupby("sembol").net.sum()
    f = (gk(OUT) - gk(TABAN)).dropna().sort_values()
    print("7-14 Kas coin bazında BIN − taban (% kitap, tam kitap):", f.head(6).round(2).to_dict(), "…", f.tail(4).round(2).to_dict())
    for h in (0, 1):
        for l in open(f"{OUT}/M357_EK_BIN_2000_{h}.txt"):
            if "TEK_BINANCE" in l: print(h, l.strip())


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
