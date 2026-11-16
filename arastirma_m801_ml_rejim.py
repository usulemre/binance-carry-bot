#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 801 — ML REJİM: long tarafının dozu. Ön kayıt KAR_HARITASI 801. KARAR VERMEZ.
  python3 arastirma_m801_ml_rejim.py defter | analiz"""
import os, sys, pickle, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m801"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}


def defter():
    os.makedirs(OUT, exist_ok=True)
    for h in (0, 1):
        e = f"{OUT}/M357_EK_GK_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **ENV, GK_BAS="2020-01-01", FAZ_KAY=str(h), E_CIKTI=e + ".tmp", GUNLUK_KATKI=f"{OUT}/gk_{h}.pkl", PYTHONPATH=R)
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def ozellik():
    import arastirma_m389_ml_tahmin as A
    C, Fd, uy, X = A.panel()                     # günlük 00 UTC (04:00 kapanış), uy evren
    Mt = pickle.load(open("/tmp/metrik_panel.pkl", "rb")); z = pickle.load(open("/tmp/zemin.pkl", "rb")); sec = z["C"].index.hour == 0
    r1 = (C / C.shift(1) - 1).where(uy); b = C["BTCUSDT"]
    f = pd.DataFrame(index=C.index)
    for h in (1, 7, 30): f[f"btc{h}"] = b / b.shift(h) - 1; f[f"med{h}"] = (C / C.shift(h) - 1).where(uy).median(axis=1)
    rb = b.pct_change(); f["btcv7"] = rb.rolling(7).std(); f["btcv30"] = rb.rolling(30).std()
    f["dag"] = (C / C.shift(7) - 1).where(uy).std(axis=1)
    F3 = Fd.rolling(3).sum().where(uy); f["fmed"] = F3.median(axis=1)
    q10 = F3.quantile(0.10, axis=1); q90 = F3.quantile(0.90, axis=1)
    f["flong"] = F3.where(F3.le(q10, axis=0)).mean(axis=1); f["fyay"] = F3.where(F3.ge(q90, axis=0)).mean(axis=1) - f["flong"]
    oi = Mt["sum_open_interest_value"].reindex_like(z["C"])[sec].reindex(C.index)
    f["oi7"] = (oi / oi.shift(7) - 1).where(uy).median(axis=1)
    f["ls"] = Mt["count_long_short_ratio"].reindex_like(z["C"])[sec].reindex(C.index).where(uy).median(axis=1)
    f5 = C.shift(-5) / C - 1; ken = f5.where(F3.le(q10, axis=0)).mean(axis=1) - f5.where(uy).median(axis=1)
    ken = ken.shift(6)                           # 5 g sonra gerçekleşir → nedensel gecikme
    f["ken30"] = ken.rolling(30, min_periods=10).mean(); f["ken90"] = ken.rolling(90, min_periods=30).mean()
    return f


def analiz():
    from sklearn.ensemble import HistGradientBoostingRegressor
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    M.CIKTI = OUT; s = sum(M.gunluk(f"M357_EK_GK_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = "/tmp/m783c"; t0 = sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2
    print(f"PARİTE E serisi vs m783c: {np.abs(s - t0.reindex(s.index)).max():.1e}")
    G = pd.concat([pd.read_pickle(f"{OUT}/gk_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun)
    L = G[G.ort_poz > 0].groupby("gun").apply(lambda x: (x.fiyat + x.funding).sum() / 2).reindex(s.index).fillna(0.0)
    print(f"long katkısı ilk gün {G.gun.min().date()} · toplam long {L.sum() * 100:.0f} puan")
    f = ozellik().reindex(s.index)
    f["kl10"] = L.shift(1).rolling(10).sum(); f["kl30"] = L.shift(1).rolling(30).sum()
    y = L[::-1].rolling(5).sum()[::-1].shift(-1)          # t+1..t+5
    tah = pd.Series(np.nan, index=s.index)
    for yil in range(2022, 2027):
        bas = pd.Timestamp(f"{yil}-01-01"); e = (f.index < bas - pd.Timedelta(days=6)) & y.notna() & f.notna().sum(axis=1).gt(len(f.columns) * 0.7)
        te = (f.index >= bas) & (f.index < pd.Timestamp(f"{yil + 1}-01-01"))
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=50, l2_regularization=1.0, random_state=801)
        m.fit(f[e].values, y[e].values); tah[te] = m.predict(f[te].values)
        ic = pd.Series(tah[te]).corr(pd.Series(y[te]), method="spearman")
        print(f"{yil}: eğitim {e.sum()} gün · IC {ic:+.3f} · tahmin<0 payı {(tah[te] < 0).mean():.2f}", flush=True)
    seri = {"taban P3T2": s}
    for olc in (0.5, 0.75):
        k = pd.Series(np.where(tah < 0, olc, 1.0), index=s.index).where(tah.notna(), 1.0)
        maliyet = k.diff().abs().fillna(0) * 0.001 * 0.6
        seri[f"tahmin<0 → long ×{olc}"] = s - (1 - k) * L - maliyet
        print(f"  ×{olc}: azaltılmış gün payı (2022+) {(k['2022':] < 1).mean():.2f}")
    for ad, s0 in seri.items():
        x = s0[:"2026-10-31"]; o = T.olc(x); zs = x.reindex(Z.P.index).dropna(); kk, er = Z.esit(zs)
        yl = x.groupby(x.index.year).apply(lambda v: ((1 + v * 1.15).prod() - 1) * 100)
        ek = ((1 + s0["2026-10-01":"2026-11-15"] * 1.15).prod() - 1) * 100
        print(f"{ad:24s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · Sh ≤2024 {Z.sh(x[:'2024-12-31']):.2f} · 2025+ {Z.sh(x['2025-01-01':]):.2f} · "
              f"eşit risk {er:.1f} | ×1,15 " + " ".join(f"{yy}:{v:.0f}" for yy, v in yl.items()) + f" | Eki+Kas {ek:+.1f}")


if __name__ == "__main__":
    {"defter": defter, "analiz": analiz}[sys.argv[1]]()
