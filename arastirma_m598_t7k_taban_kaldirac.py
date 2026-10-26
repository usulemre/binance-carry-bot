#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 598 — T7K'nın prim tabanı (doz düğmesi, madde 586) AYNI RİSKTE kaldıraçla: hangi taban en çok kazandırır?
Madde 596: T7K (taban 0,7) T4'ün riskine 1,10-1,15x kaldıraçla +31..+59 puan. Taban düşükse kötü gün daha sığ (madde 586:
0,6 → en kötü −6,5) → aynı riske daha çok kaldıraç taşıyabilir. Soru: ham getiri kaybını kaldıraç fazlası geri alıyor mu?
ÖN KAYIT: canlı gibi giriş + 5 bp + MERD_SIRA=1, uzun zemin, 2.000 $ D8 ve 3.500 $ D2, iki hiza. Kollar taban 0,5 / 0,6 / 0,8
(0,7 = madde 587 serisi). Her kol madde 596'nın kısıtıyla (T4 1,0x'in dd / en kötü gün / 1y p1'ini aşmadan en yüksek k) ölçülür.
ADAY: iki seviyede de eşit-risk yıllığı T7K(0,7)'nin eşit-risk yıllığından ≥ +8 puan yüksek. Değilse 0,7 yerinde.
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1", "KOM": "0.0005"}
T7K = {**G, "S_REB": "10", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30",
       "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0"}
D = "/tmp/m598"; os.makedirs(D, exist_ok=True)
KOL = {"A50": "0.5", "A60": "0.6", "A80": "0.8"}
EV = {2000: M.D8, 3500: M.D2}


def kos(a):
    ad, sev, h = a; out = f"{D}/M357_EK_{ad}_{sev}_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **T7K, "BRUT_ALT": KOL[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(EV[sev]), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return a, r.returncode


def _seri(dizin, ad, sev):
    M.CIKTI = dizin
    return sum(M.gunluk(f"M357_EK_{ad}_{sev}_{h}") for h in (0, 1)) / 2


def _olc(d):
    eq = (1 + d).cumprod()
    return dict(yil=(eq.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(eq / eq.cummax() - 1).min() * 100,
                ek=d.min() * 100, g5=int((d < -0.05).sum()))


def _p1(d, idx):
    v = d.values; out = []
    for yol in idx:
        eq = np.cumprod(1 + v[yol]); out.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
    return np.percentile(out, 1)


def analiz():
    rng = np.random.default_rng(596)    # madde 596 ile aynı tohum ve yol üretimi
    sonuc = {}
    for sev in (2000, 3500):
        S = {"T4": _seri("/tmp/m_ekim_kuru", "T4", sev), "A70": _seri("/tmp/m_ekim_kuru", "T7K", sev)}
        for ad in KOL: S[ad] = _seri(D, ad, sev)
        n = len(S["T4"]); idx = []
        for _ in range(3000):
            bas = rng.integers(0, n - 20, size=365 // 20 + 1); idx.append(np.concatenate([np.arange(b, b + 20) for b in bas])[:365])
        ref = _olc(S["T4"]); ref["p1"] = _p1(S["T4"], idx)
        print(f"\n{sev} $ — T4 1,0x: yıllık {ref['yil']:+.1f} dd {ref['dd']:.1f} en kötü {ref['ek']:.2f} 1y p1 {ref['p1']:.1f}")
        for ad in ("A50", "A60", "A70", "A80"):
            ham = _olc(S[ad]); best = None
            for k in np.arange(0.80, 2.51, 0.05):
                d = S[ad] * k; o = _olc(d)
                if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
                o["p1"] = _p1(d, idx)
                if o["p1"] < ref["p1"]: break
                best = (k, o)
            k, o = best
            sonuc.setdefault(ad, {})[sev] = o["yil"]
            print(f"  taban {ad[1:]:>3s}: ham {ham['yil']:+.1f} / en kötü {ham['ek']:.2f} | eşit risk k {k:.2f} → yıllık {o['yil']:+.1f} "
                  f"dd {o['dd']:.1f} en kötü {o['ek']:.2f} −%5 {o['g5']} 1y p1 {o['p1']:.1f}")
    for ad in KOL:
        f = [sonuc[ad][s] - sonuc["A70"][s] for s in (2000, 3500)]
        print(f"{ad}: eşit-risk farkı 0,7'ye göre {f[0]:+.1f} / {f[1]:+.1f} → {'ADAY' if min(f) >= 8 else 'RED'}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, s, h) for s in (2000, 3500) for h in (0, 1) for a in KOL]): print(x, flush=True)
    else:
        analiz()
