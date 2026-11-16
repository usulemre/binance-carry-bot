#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 800 — ML LONG VETOSU. Ön kayıt KAR_HARITASI 800. KARAR VERMEZ.
  python3 arastirma_m800_ml_long_veto.py panel | kos | analiz"""
import os, sys, pickle, subprocess
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
import arastirma_m389_ml_tahmin as A
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m800"; R = os.path.dirname(os.path.abspath(__file__)); TABAN = "/tmp/m783c"
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"V05": "0.05", "V10": "0.10"}


def panel():
    C, Fd, uy, X = A.panel()
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]
    H4 = pickle.load(open("/tmp/hlo.pkl", "rb"))["H"].reindex_like(C4)
    sec = C4.index.hour == 0
    fmax = H4[::-1].rolling(30, min_periods=24).max()[::-1].shift(-1)[sec]   # sonraki 30 bar (5 g) HIGH
    c5 = C.shift(-5) / C - 1
    fon = Fd.rolling(5).sum().shift(-5)
    y = np.where(fmax.values >= C.values * 1.45, 0.45, c5.values)
    y = pd.DataFrame(y, index=C.index, columns=C.columns) - fon
    y = y.where(uy).clip(-0.9, 0.45)
    D = A.uzun(X, y); kols = list(X); t = D.index.get_level_values(0)
    tah = pd.Series(np.nan, index=D.index)
    for yil in range(2022, 2027):
        bas = pd.Timestamp(f"{yil}-01-01")
        e = D[t < bas - pd.Timedelta(days=6)].dropna(subset=["y"]); e = e[e[kols].notna().sum(axis=1) >= len(kols) * 0.7]
        s = D[(t >= bas) & (t < pd.Timestamp(f"{yil + 1}-01-01"))]; s = s[s[kols].notna().sum(axis=1) >= len(kols) * 0.7]
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500,
                                          l2_regularization=1.0, random_state=800)
        tah.loc[s.index] = m.fit(e[kols].fillna(0.5).values - 0.5, e["y"].values).predict(s[kols].fillna(0.5).values - 0.5)
        print(f"{yil}: eğitim {len(e):,} · test {len(s):,}", flush=True)
    P = tah.unstack().reindex(index=C.index, columns=C.columns)
    Y = y.reindex_like(P)
    # teşhis: long adayları (fon3 sırası en düşük %10) içinde tahminin alt %20'si vs geri kalanı — gerçekleşen y
    F3 = X["fon3"].reindex_like(P); rk = P.rank(axis=1, pct=True)
    for yil in range(2022, 2027):
        ix = P.index.year == yil; cand = (F3 <= 0.10) & P.notna() & Y.notna()
        a = Y[ix][(cand & (rk <= 0.20))[ix]].stack(); b = Y[ix][(cand & (rk > 0.20))[ix]].stack()
        ic = np.nanmean([pd.Series(P.loc[d]).corr(pd.Series(Y.loc[d]), method="spearman") for d in P.index[ix] if P.loc[d].notna().sum() > 20])
        print(f"  {yil}: IC {ic:+.3f} | long adayı: veto edilecek (n {len(a)}) ort {a.mean() * 100:+.2f}%  kalan (n {len(b)}) ort {b.mean() * 100:+.2f}%", flush=True)
    V = 0.5 * rk
    V4 = V.reindex(C4.index.floor("D")); V4.index = C4.index
    pickle.dump(V4, open(f"{OUT}/veto.pkl", "wb")); print("yazıldı", f"{OUT}/veto.pkl", V4.notna().any(axis=1).mean())


def kos():
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
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    M.CIKTI = TABAN; seri = {"taban P3T2": sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2}
    M.CIKTI = OUT
    for ad, q in KOLLAR.items():
        if all(os.path.exists(f"{OUT}/M357_EK_{ad}_2000_{h}.pkl") for h in (0, 1)):
            seri[f"ML veto en kötü %{int(float(q) * 200)}"] = sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2
    for ad, s0 in seri.items():
        s = s0[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        ek = ((1 + s0["2026-10-01":"2026-11-15"] * 1.15).prod() - 1) * 100
        print(f"{ad:24s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · "
              f"eşit risk {er:.1f} | ×1,15 " + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()) + f" | Eki+Kas {ek:+.1f}")


if __name__ == "__main__":
    {"panel": panel, "kos": kos, "analiz": analiz}[sys.argv[1]]()
