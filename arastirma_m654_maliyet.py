#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 654 — MALİYET DUYARLILIĞI (canlıya hazırlık): önerilen ayar (T7K 1,15x + koşullu stop) ile T4'ün farkı işlem maliyeti 5 → 8 → 10 bp
olursa korunuyor mu? Demo raporlarındaki gerçek komisyon / kayma bu tabloyla karşılaştırılacak (madde 519 T4 için: 1 bp ≈ 6,6 puan/yıl).
Kollar: T4 ve P3T2, KOM 0,0008 / 0,0010 (5 bp tabanları mevcut). TANI (karar kuralı değil): fark ve kırılma noktası.
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1"}
_T4 = {**G, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
_KS = {**G, "S_REB": "10", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30", "SK_DOSYA_S": "/tmp/sk_bar96.pkl",
       "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0", "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
D = "/tmp/m654"; os.makedirs(D, exist_ok=True)
KOL = {f"{a}_K{k}": ({**b, "KOM": f"0.000{k}" if k < 10 else "0.0010"}) for a, b in (("T4", _T4), ("KS", _KS)) for k in (8, 10)}


def kos(a):
    ad, h = a; out = f"{D}/M357_EK_{ad}_2000_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **KOL[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return a, r.returncode


def analiz():
    def seri(d, ad):
        M.CIKTI = d; return sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2
    def olc(d):
        eq = (1 + d).cumprod()
        return (eq.iloc[-1] ** (365.25 / len(d)) - 1) * 100, (eq / eq.cummax() - 1).min() * 100, d.min() * 100, d.mean() / d.std() * np.sqrt(365.25)
    S = {5: (seri("/tmp/m_ekim_kuru", "T4"), seri("/tmp/m622", "P3T2"))}
    for k in (8, 10): S[k] = (seri(D, f"T4_K{k}"), seri(D, f"KS_K{k}"))
    for k, (t4, ks) in S.items():
        a, b = olc(t4), olc(ks); c = olc(ks * 1.15)
        print(f"{k:2d} bp | T4 {a[0]:+7.1f} dd {a[1]:6.1f} en kötü {a[2]:6.2f} Sh {a[3]:.2f} | T7K+KS 1x {b[0]:+7.1f} dd {b[1]:6.1f} Sh {b[3]:.2f} | "
              f"×1,15 {c[0]:+7.1f} dd {c[1]:6.1f} en kötü {c[2]:6.2f} | fark (×1,15 − T4) {c[0]-a[0]:+6.1f}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, h) for a in KOL for h in (0, 1)]): print(x, flush=True)
    else:
        analiz()
