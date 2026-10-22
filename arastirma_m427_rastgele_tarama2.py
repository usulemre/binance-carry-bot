#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 427 — İKİNCİ RASTGELE TARAMA: GEÇERLİ YAPI (REB 5 / 15 dilim / 4 bacak SABİT), KAZANAN BÖLGESİ.

Madde 426: REB 4 motorda 24 dilim kurdu ve 3-5 bacakla bacak küçülüp evren iyimser ölçüldü.
Bu turda yapı sabit (çarpıtma yok); uzay madde 425 kazananlarının bölgesi. Tam ızgara (~10^4-10^5) koşulamaz; bunun
yerine sabit tohumlu rastgele tarama. Gerçekçi ağırlık kayması (madde 419) açık.
Uzay:
  HAVUZ {3,4,5} · REB_GUN {4,5,6} · TPL {0,30·0,40·0,50} · TPS {0,15·0,20·0,25}
  bacak {3,4,5} · REZERV {0,10·0,20·0,30} · UCELE {0·0,40} · YAS_GUN {60·90}
  HACIM_ESIK {70M·100M} · funding penceresi {36·48·60 sa}
ÖN KAYIT (koşudan ÖNCE):
  * 2.000 $ (D8), iki hiza; ölçüt hizaların ORTALAMA günlük serisi.
  * SEÇİM yalnız IS (2022-07..2024-12) Sharpe'ıyla; IS'te en iyi 5 kombinasyonun
    OOS (2025-01..2026-09) Sharpe ve getirisi kontrolle karşılaştırılır.
  * Genelleme testi: 25 kombinasyonda IS Sharpe sırası ile OOS Sharpe sırası
    arasındaki Spearman korelasyonu (≈0 → ayar seçimi geleceği iyileştirmiyor).
  * Bir kombinasyon ancak IS'te seçilip OOS'ta kontrolü Sharpe'ta >= +0,15 ve
    getiride >= +10 puan geçerse madde 375 protokolüne (iki seviye, %95) gönderilir.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import arastirma_m346_prim as M  # noqa: E402

CIKTI = "/tmp/m427"
UZAY = dict(HAVUZ=["4", "5", "6"], REB_GUN=["5"], TPL=["0.35", "0.40", "0.45"],
            TPS=["0.15", "0.20", "0.25"], bacak=[4], REZERV=["0.05", "0.10", "0.15", "0.20"],
            UCELE=["0", "0.40"], YAS_GUN=["45", "60", "75", "90"], HACIM_ESIK=["5e7", "7e7", "1e8"],
            SK_DOSYA=["/tmp/sk_bar48.pkl", "/tmp/sk_bar60.pkl"], KAP=["0.05", "0.08"])
KONTROL = dict(HAVUZ="4", REB_GUN="5", TPL="0.40", TPS="0.20", bacak=4, REZERV="0.20",
               UCELE="0.40", YAS_GUN="90", HACIM_ESIK="1e8", SK_DOSYA="/tmp/sk_bar48.pkl", KAP="0.05")


def kombinasyonlar(n=30, tohum=427):
    rng = np.random.default_rng(tohum)
    out = {"K00": KONTROL}
    while len(out) < n + 1:
        k = {a: v[rng.integers(len(v))] for a, v in UZAY.items()}
        if k == KONTROL or k in out.values():
            continue
        out[f"R{len(out):02d}"] = k
    return out


def tek(ad, k, h):
    pkl = os.path.join(CIKTI, f"{ad}_{h}.pkl")
    if os.path.exists(pkl):
        return ad, h, "var"
    ek = {a: v for a, v in k.items() if a != "bacak"}
    env = dict(os.environ, **dict(M.TABAN, **ek), AGIRLIK_KAYMA="1", FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(M.D8), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, f"{ad}_{h}.txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", str(k["bacak"])], cwd=KOK, env=env,
                           stdout=f, stderr=subprocess.STDOUT, timeout=7200)
    return ad, h, r.returncode


def kos():
    os.makedirs(CIKTI, exist_ok=True)
    K = kombinasyonlar()
    pd.DataFrame(K).T.to_csv(os.path.join(CIKTI, "kombinasyonlar.csv"))
    isler = [(a, k, h) for a, k in K.items() for h in (0, 1)]
    with ThreadPoolExecutor(2) as ex:
        for x in ex.map(lambda t: tek(*t), isler):
            print(*x, flush=True)


def gun(p):
    E = pd.read_pickle(p); r = E.pct_change().dropna()
    g = (1 + r).groupby(r.index.date).prod() - 1; g.index = pd.DatetimeIndex(g.index); return g


def analiz():
    K = kombinasyonlar()
    sh = lambda x: x.mean() / x.std() * np.sqrt(365.25)
    yil = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
    rows = []
    for a in K:
        try:
            g = (gun(os.path.join(CIKTI, f"{a}_0.pkl")) + gun(os.path.join(CIKTI, f"{a}_1.pkl"))) / 2
        except Exception:
            continue
        IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        e = (1 + g).cumprod(); dd = ((e / e.cummax()) - 1).min() * 100
        rows.append(dict(ad=a, shIS=sh(IS), shOOS=sh(OOS), yilIS=yil(IS), yilOOS=yil(OOS), yil=yil(g), dd=dd,
                         **{k: v for k, v in K[a].items() if k != "SK_DOSYA"},
                         pen=K[a]["SK_DOSYA"][-6:-4]))
    T = pd.DataFrame(rows).sort_values("shIS", ascending=False)
    pd.set_option("display.width", 250)
    print(T.round(2).to_string(index=False))
    k0 = T[T.ad == "K00"].iloc[0]
    print(f"\nGenelleme: IS Sharpe sirasi vs OOS Sharpe sirasi Spearman = {T.shIS.rank().corr(T.shOOS.rank()):.3f} "
          f"(n={len(T)})")
    print(f"Kontrol K00: IS Sh {k0.shIS:.2f} OOS Sh {k0.shOOS:.2f} yil OOS {k0.yilOOS:+.1f} | kontrolun IS sirasi "
          f"{int((T.shIS > k0.shIS).sum()) + 1}/{len(T)}, OOS sirasi {int((T.shOOS > k0.shOOS).sum()) + 1}/{len(T)}")
    print("\nIS'TE EN IYI 5 (OOS'a hic bakilmadan secildi):")
    for _, r in T[T.ad != "K00"].head(5).iterrows():
        gec = r.shOOS - k0.shOOS >= 0.15 and r.yilOOS - k0.yilOOS >= 10
        print(f"  {r.ad}: IS Sh {r.shIS:.2f} -> OOS Sh {r.shOOS:.2f} ({r.shOOS-k0.shOOS:+.2f}), OOS yil {r.yilOOS:+.1f} "
              f"({r.yilOOS-k0.yilOOS:+.1f}) -> {'PROTOKOLE' if gec else 'RED'}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
