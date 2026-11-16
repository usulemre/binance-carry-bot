#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 802 — sıçrama sınıflandırıcı + mum yolu özellikleri. Ön kayıt KAR_HARITASI 802. KARAR VERMEZ.
  python3 arastirma_m802_sicrama.py kapi | kos | analiz"""
import os, sys, pickle, subprocess
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
import arastirma_m389_ml_tahmin as A
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m802"; R = os.path.dirname(os.path.abspath(__file__)); TABAN = "/tmp/m783c"
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"S05": "0.05", "S10": "0.10"}


def kapi():
    C, Fd, uy, X = A.panel()
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; hlo = pickle.load(open("/tmp/hlo.pkl", "rb"))
    H4, L4, O4 = hlo["H"].reindex_like(C4), hlo["L"].reindex_like(C4), hlo["O"].reindex_like(C4)
    sec = C4.index.hour == 0
    r4 = C4 / C4.shift(1) - 1
    ust = (H4 - np.maximum(O4, C4)) / (H4 - L4).replace(0, np.nan); alt = (np.minimum(O4, C4) - L4) / (H4 - L4).replace(0, np.nan)
    mum = {"carp7": r4.rolling(42, min_periods=30).skew(), "carp30": r4.rolling(180, min_periods=120).skew(),
           "bas30": r4.rolling(180, min_periods=120).kurt(), "ustf7": ust.rolling(42, min_periods=30).mean(),
           "altf7": alt.rolling(42, min_periods=30).mean(), "r3_4s": C4 / C4.shift(18) - 1}
    for k, v in mum.items(): X[k] = v[sec].reindex_like(C).where(uy).rank(axis=1, pct=True)
    fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]
    y = (fmax >= C * 1.45).astype(float).where(uy & fmax.notna())
    D = A.uzun(X, y); kols = list(X); t = D.index.get_level_values(0)
    tah = pd.Series(np.nan, index=D.index)
    F3 = X["fon3"]
    gecti = True
    for yil in range(2022, 2027):
        bas = pd.Timestamp(f"{yil}-01-01")
        e = D[t < bas - pd.Timedelta(days=6)].dropna(subset=["y"]); e = e[e[kols].notna().sum(axis=1) >= len(kols) * 0.7]
        s = D[(t >= bas) & (t < pd.Timestamp(f"{yil + 1}-01-01"))]; s = s[s[kols].notna().sum(axis=1) >= len(kols) * 0.7]
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500, l2_regularization=1.0, random_state=802)
        m.fit(e[kols].fillna(0.5).values - 0.5, e["y"].values.astype(int))
        p = m.predict_proba(s[kols].fillna(0.5).values - 0.5)[:, 1]; tah.loc[s.index] = p
        ss = s.assign(p=p).dropna(subset=["y"])
        cand = ss[ss["fon3"] <= 0.10 - 0.5 + 0.5] if False else ss[F3.stack(future_stack=True).reindex(ss.index) <= 0.10]
        auc_t = roc_auc_score(ss.y, ss.p); auc_c = roc_auc_score(cand.y, cand.p) if cand.y.nunique() > 1 else np.nan
        print(f"{yil}: eğitim {len(e):,} (sıçrama %{e.y.mean() * 100:.1f}) · test AUC tüm {auc_t:.3f} · LONG ADAYI AUC {auc_c:.3f} (n {len(cand)}, sıçrama %{cand.y.mean() * 100:.1f})", flush=True)
        gecti = gecti and auc_c >= 0.60
    print("KAPI:", "GEÇTİ → motor" if gecti else "GEÇMEDİ → DUR (RED)")
    P = tah.unstack().reindex(index=C.index, columns=C.columns); V = 0.5 * P.rank(axis=1, pct=True)
    V4 = V.reindex(C4.index.floor("D")); V4.index = C4.index
    pickle.dump(V4, open(f"{OUT}/veto.pkl", "wb")); open(f"{OUT}/kapi.txt", "w").write("GECTI" if gecti else "GECMEDI")


def kos():
    if open(f"{OUT}/kapi.txt").read() != "GECTI": print("kapı geçmedi — motor koşulmaz"); return
    for ad, q in KOLLAR.items():
        for h in (0, 1):
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **ENV, MOM_Q=q, MOM_DOSYA=f"{OUT}/veto.pkl", FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m800_ml_long_veto as B
    B.OUT = OUT; B.KOLLAR = KOLLAR
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    M.CIKTI = TABAN; seri = {"taban P3T2": sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2}
    M.CIKTI = OUT
    for ad, q in KOLLAR.items():
        if all(os.path.exists(f"{OUT}/M357_EK_{ad}_2000_{h}.pkl") for h in (0, 1)):
            seri[f"sıçrama olas. en düşük %{int(float(q) * 200)} long olamaz"] = sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2
    for ad, s0 in seri.items():
        s = s0[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        ek = ((1 + s0["2026-10-01":"2026-11-15"] * 1.15).prod() - 1) * 100
        print(f"{ad:38s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · "
              f"eşit risk {er:.1f} | ×1,15 " + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()) + f" | Eki+Kas {ek:+.1f}")


if __name__ == "__main__":
    {"kapi": kapi, "kos": kos, "analiz": analiz}[sys.argv[1]]()
