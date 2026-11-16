#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 804 — asimetri vetosu: P(çöküş) − P(sıçrama). Ön kayıt KAR_HARITASI 804. KARAR VERMEZ.
  python3 arastirma_m804_asimetri.py kapi | kos | analiz"""
import os, sys, pickle, subprocess
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
import arastirma_m389_ml_tahmin as A
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m804"; R = os.path.dirname(os.path.abspath(__file__)); TABAN = "/tmp/m783c"
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"A05": "0.05", "A10": "0.10"}


def kapi():
    os.makedirs(OUT, exist_ok=True)
    C, Fd, uy, X = A.panel()
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; hlo = pickle.load(open("/tmp/hlo.pkl", "rb"))
    H4, L4, O4 = hlo["H"].reindex_like(C4), hlo["L"].reindex_like(C4), hlo["O"].reindex_like(C4)
    sec = C4.index.hour == 0; r4 = C4 / C4.shift(1) - 1
    ust = (H4 - np.maximum(O4, C4)) / (H4 - L4).replace(0, np.nan); alt = (np.minimum(O4, C4) - L4) / (H4 - L4).replace(0, np.nan)
    mum = {"carp7": r4.rolling(42, min_periods=30).skew(), "carp30": r4.rolling(180, min_periods=120).skew(),
           "bas30": r4.rolling(180, min_periods=120).kurt(), "ustf7": ust.rolling(42, min_periods=30).mean(),
           "altf7": alt.rolling(42, min_periods=30).mean(), "r3_4s": C4 / C4.shift(18) - 1}
    for k, v in mum.items(): X[k] = v[sec].reindex_like(C).where(uy).rank(axis=1, pct=True)
    fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]
    fmin = L4[::-1].rolling(30, min_periods=24).min()[::-1].shift(-1)[sec]
    ys = (fmax >= C * 1.45).astype(float).where(uy & fmax.notna())
    yc = (fmin <= C * 0.70).astype(float).where(uy & fmin.notna())
    c5 = C.shift(-5) / C - 1; fon = Fd.rolling(5).sum().shift(-5)
    pay = (pd.DataFrame(np.where(fmax.values >= C.values * 1.45, 0.45, c5.values), index=C.index, columns=C.columns) - fon).where(uy).clip(-0.9, 0.45)
    kols = list(X); D = A.uzun(X, ys).rename(columns={"y": "ys"}); D["yc"] = yc.stack(future_stack=True).reindex(D.index)
    D["pay"] = pay.stack(future_stack=True).reindex(D.index); D["f3"] = X["fon3"].stack(future_stack=True).reindex(D.index)
    t = D.index.get_level_values(0); sk = pd.Series(np.nan, index=D.index); gec = 0
    for yil in range(2022, 2027):
        bas = pd.Timestamp(f"{yil}-01-01")
        e = D[t < bas - pd.Timedelta(days=6)].dropna(subset=["ys", "yc"]); e = e[e[kols].notna().sum(axis=1) >= len(kols) * 0.7]
        s = D[(t >= bas) & (t < pd.Timestamp(f"{yil + 1}-01-01"))]; s = s[s[kols].notna().sum(axis=1) >= len(kols) * 0.7]
        p = {}
        for hed in ("ys", "yc"):
            m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500, l2_regularization=1.0, random_state=804)
            m.fit(e[kols].fillna(0.5).values - 0.5, e[hed].values.astype(int)); p[hed] = m.predict_proba(s[kols].fillna(0.5).values - 0.5)[:, 1]
        sk.loc[s.index] = p["yc"] - p["ys"]
        c = s.assign(sk=p["yc"] - p["ys"]); c = c[(c.f3 <= 0.10) & c.pay.notna()]
        esik = c.sk.quantile(0.80); v = c[c.sk >= esik].pay.mean(); k = c[c.sk < esik].pay.mean(); ok = (k - v) * 100 >= 1.0; gec += ok
        print(f"{yil}: çöküş oranı (eğitim) %{e.yc.mean() * 100:.1f} · long adayı n {len(c)} · skor üst %20 ödeme {v * 100:+.2f}% · kalan {k * 100:+.2f}% · fark {(k - v) * 100:+.2f} {'✓' if ok else '✗'}", flush=True)
    karar = gec >= 4; print(f"KAPI: {gec}/5 yıl → " + ("GEÇTİ → motor" if karar else "GEÇMEDİ → DUR (RED)"))
    P = sk.unstack().reindex(index=C.index, columns=C.columns); V = 0.5 * (1 - P.rank(axis=1, pct=True))
    V4 = V.reindex(C4.index.floor("D")); V4.index = C4.index
    pickle.dump(V4, open(f"{OUT}/veto.pkl", "wb")); open(f"{OUT}/kapi.txt", "w").write("GECTI" if karar else "GECMEDI")


def kos():
    import arastirma_m802_sicrama as S
    S.OUT, S.KOLLAR = OUT, KOLLAR; S.kos()


def analiz():
    import arastirma_m802_sicrama as S
    S.OUT, S.KOLLAR = OUT, KOLLAR; S.analiz()


if __name__ == "__main__":
    {"kapi": kapi, "kos": kos, "analiz": analiz}[sys.argv[1]]()
