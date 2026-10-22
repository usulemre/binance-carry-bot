#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 438 — T60 BÖLGESİNDE RASTGELE TARAMA (20 kombinasyon + T60 kontrolü).

Madde 433: bu bölgede IS→OOS sırası korunuyor (Spearman 0,75). T60 = HAVUZ 4, REB 5, TPL 0,60,
TPS 0,20, REZ 0,10, UCELE 0, yaş 60, hacim 70M, 60 sa, SLS 2,0 (canlıya geçiyor, madde 437).
UZAY: HAVUZ {4,5} · TPL {0,50·0,60·0,70} · TPS {0,15·0,20·0,25} · REZ {0,05·0,10·0,15} ·
      UCELE {0·0,40} · yaş {60·75} · hacim {50M·70M·100M} · pencere {48·60} · SLS {1,5·2,0·3,0}
ÖN KAYIT (koşudan ÖNCE): 2.000 $ D8, iki hiza ortalaması, kaymalı model.
  * Genelleme: 21 serinin IS (22-07..24-12) ve OOS (25-01..26-09) yıllık getiri sıra korelasyonu.
  * SEÇİM yalnız IS yıllık getirisiyle, dd şartı: tam dönem dd T60'tan en fazla 2 puan kötü.
  * Seçilen OOS'ta T60'ı yıllık >= +15 puan geçerse → iki seviye protokol (madde 439); değilse
    "T60 bölgenin tepesinde" kaydı.
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m346_prim as M

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = "/tmp/m438"
T60 = dict(HAVUZ="4", TPL="0.60", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60", HACIM_ESIK="7e7",
           SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0")
UZAY = dict(HAVUZ=["4", "5"], TPL=["0.50", "0.60", "0.70"], TPS=["0.15", "0.20", "0.25"],
            REZERV=["0.05", "0.10", "0.15"], UCELE=["0", "0.40"], YAS_GUN=["60", "75"],
            HACIM_ESIK=["5e7", "7e7", "1e8"], SK_DOSYA=["/tmp/sk_bar48.pkl", "/tmp/sk_bar60.pkl"],
            SLS=["1.5", "2.0", "3.0"])


def kombinasyonlar(n=20, tohum=438):
    rng = np.random.default_rng(tohum)
    out = {"T60": T60}
    while len(out) < n + 1:
        k = {a: v[rng.integers(len(v))] for a, v in UZAY.items()}
        if k not in out.values():
            out[f"Q{len(out):02d}"] = k
    return out


def tek(ad, k, h):
    pkl = os.path.join(CIKTI, f"{ad}_{h}.pkl")
    if os.path.exists(pkl):
        return ad, h, "var"
    env = dict(os.environ, **dict(M.TABAN, **k), REB_GUN="5", AGIRLIK_KAYMA="1", FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(M.D8), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, f"{ad}_{h}.txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], cwd=KOK, env=env,
                           stdout=f, stderr=subprocess.STDOUT, timeout=7200)
    return ad, h, r.returncode


def kos():
    os.makedirs(CIKTI, exist_ok=True)
    K = kombinasyonlar()
    pd.DataFrame(K).T.to_csv(os.path.join(CIKTI, "kombinasyonlar.csv"))
    with ThreadPoolExecutor(2) as ex:
        for x in ex.map(lambda t: tek(*t), [(a, k, h) for a, k in K.items() for h in (0, 1)]):
            print(*x, flush=True)


def gun(p):
    E = pd.read_pickle(p); r = E.pct_change().dropna()
    g = (1 + r).groupby(r.index.date).prod() - 1; g.index = pd.DatetimeIndex(g.index); return g


def analiz():
    K = kombinasyonlar()
    YIL = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
    DD = lambda x: (((1 + x).cumprod() / (1 + x).cumprod().cummax()) - 1).min() * 100
    rows = []
    for a in K:
        g = (gun(f"{CIKTI}/{a}_0.pkl") + gun(f"{CIKTI}/{a}_1.pkl")) / 2
        IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        rows.append(dict(ad=a, yIS=YIL(IS), yOOS=YIL(OOS), yTAM=YIL(g), dd=DD(g),
                         TemEyl26=((1 + g[g.index >= "2026-07-01"]).prod() - 1) * 100,
                         **{k: v for k, v in K[a].items() if k != "SK_DOSYA"}, pen=K[a]["SK_DOSYA"][-6:-4]))
    T = pd.DataFrame(rows).sort_values("yIS", ascending=False)
    pd.set_option("display.width", 250)
    print(T.round(1).to_string(index=False))
    print(f"\nGenelleme: IS->OOS yillik getiri sira korelasyonu = {T.yIS.rank().corr(T.yOOS.rank()):.3f} (n={len(T)})")
    t = T[T.ad == "T60"].iloc[0]
    uygun = T[(T.ad != "T60") & (T.dd >= t.dd - 2)]
    s = uygun.iloc[0]
    gec = s.yOOS - t.yOOS >= 15
    print(f"T60: IS {t.yIS:+.1f} OOS {t.yOOS:+.1f} dd {t.dd:.1f} | IS sirasi {int((T.yIS > t.yIS).sum()) + 1}/{len(T)}")
    print(f"SECILEN (IS 1., dd sarti): {s.ad} IS {s.yIS:+.1f} OOS {s.yOOS:+.1f} ({s.yOOS - t.yOOS:+.1f}) dd {s.dd:.1f} "
          f"-> {'PROTOKOLE' if gec else 'RED (T60 bolgenin tepesinde)'}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
