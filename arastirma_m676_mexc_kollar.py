#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 676 — BORSALAR ARASI FUNDING ONAYI (MEXC). Ön kayıt KAR_HARITASI 676. Kollar V1 ONAY / V2 HARMAN (sinyal panelleri
arastirma_m676_mexc_funding.py panel 60 / 96). Pencere 2025-06 → 2026-09, iki yarı. Taban P3T2 (/tmp/m622).
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1", "KOM": "0.0005"}
T4 = {**G, "S_REB": "10", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0", "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}   # = T7K + koşullu stop (P3T2)
D = "/tmp/m676"; os.makedirs(D, exist_ok=True)
KOL = {"V1": {"SK_DOSYA": "/tmp/sk_bar60_onay.pkl", "SK_DOSYA_S": "/tmp/sk_bar96_onay.pkl"},
       "V2": {"SK_DOSYA": "/tmp/sk_bar60_harman.pkl", "SK_DOSYA_S": "/tmp/sk_bar96_harman.pkl"},
       "V3": {"SK_DOSYA": "/tmp/sk_bar60_ozel.pkl", "SK_DOSYA_S": "/tmp/sk_bar96_ozel.pkl"},   # madde 677 ön kayıt (yalnız 2026-10+ ile karar)
       "P3T2": {}}   # taban yeniden (aynı zemin; /tmp/m622 ile birebir olmalı -> parite kontrolü)


def kos(a):
    ad, h = a; out = f"{D}/M357_EK_{ad}_2000_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **T4, **KOL[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return a, r.returncode


def _seri(dizin, ad):
    M.CIKTI = dizin
    return sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2


def _olc(d):
    eq = (1 + d).cumprod()
    return dict(yil=(eq.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(eq / eq.cummax() - 1).min() * 100,
                ek=d.min() * 100, g5=int((d < -0.05).sum()))


def _sh(d):
    return d.mean() / d.std() * np.sqrt(365.25)


def _p1(d, idx):
    v = d.values; out = []
    for yol in idx:
        eq = np.cumprod(1 + v[yol]); out.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
    return np.percentile(out, 1)


def analiz():
    S = {ad: _seri(D, ad) for ad in KOL}
    M.CIKTI = "/tmp/m622"; eski = sum(M.gunluk(f"M357_EK_P3T2_2000_{h}") for h in (0, 1)) / 2
    print(f"parite: yeni taban vs /tmp/m622 en büyük günlük fark {(S['P3T2'] - eski).abs().max():.2e}")
    yarilar = [("2025-06-01", "2026-01-01"), ("2026-01-01", "2026-10-01")]
    sonuc = {}
    for ad in ["P3T2", "V1", "V2"]:
        d = S[ad]; w = d[(d.index >= "2025-06-01") & (d.index < "2026-10-01")]
        eq = (1 + w).cumprod(); sh = [_sh(d[(d.index >= a) & (d.index < b)]) for a, b in yarilar]
        sonuc[ad] = dict(top=(eq.iloc[-1] - 1) * 100, dd=(eq / eq.cummax() - 1).min() * 100, ek=w.min() * 100, sh=sh)
        tam = _olc(d)
        print(f"{ad:5s} pencere getiri {sonuc[ad]['top']:+8.1f}% dd {sonuc[ad]['dd']:6.1f} en kötü {sonuc[ad]['ek']:6.2f} | "
              f"Sh 25-H2 {sh[0]:.2f} 26 {sh[1]:.2f} | (tüm dönem yıllık {tam['yil']:+.1f}, dd {tam['dd']:.1f})")
    b = sonuc["P3T2"]
    for ad in ("V1", "V2"):
        v = sonuc[ad]
        ok = v["sh"][0] >= b["sh"][0] and v["sh"][1] >= b["sh"][1] and v["top"] >= b["top"] and v["ek"] >= b["ek"]
        print(f"{ad}: Sh iki yarı {'Y' if v['sh'][0] >= b['sh'][0] and v['sh'][1] >= b['sh'][1] else 'X'} · getiri "
              f"{'Y' if v['top'] >= b['top'] else 'X'} · en kötü gün {'Y' if v['ek'] >= b['ek'] else 'X'} → {'ADAY (izleme)' if ok else 'RED'}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, h) for a in KOL for h in (0, 1)]): print(x, flush=True)
    else:
        analiz()
