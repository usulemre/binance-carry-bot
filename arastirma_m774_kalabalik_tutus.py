#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 774 (betimsel, motor koşusu yok) — TUTUŞ SIRASINDA kalabalık: elde tutulan long'a (short'a) kalabalık yığılınca sonraki
günler kötü mü? 773: long kalabalık seçimi kitabın en değerli parçası (kapatınca eşit risk −172). Seçim yalnız GİRİŞTE bakıyor; 5 günlük
tutuşta kalabalık değişirse çıkmak değerli olabilir. Defter 711 (P3T2, iki hiza), kalabalık = perakende hesap sayısı L/S oranı (metrik_panel).
Her gün sonu: tutulan coinin log oranının EVREN içindeki yüzdeliği (yüksek = çok long'çu) ve girişten beri değişimi; sonraki gün getirisi."""
import pickle
import numpy as np, pandas as pd
M = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))["count_long_short_ratio"]
U = pickle.load(open("/tmp/zemin.pkl", "rb"))["uy"].reindex_like(M).fillna(False).astype(bool)
LR = np.log(M.where(M > 0)).where(U)
GUN = LR.resample("D").last()                         # gün sonu (20:00 barı) — nedensel: ertesi günün getirisiyle eşlenir
PCT = GUN.rank(axis=1, pct=True)
rows = []
for h in (0, 1):
    G = pickle.load(open(f"/tmp/m711/gk_{h}.pkl", "rb"))
    G = G[(G.gun >= "2022-01-01") & (G.bar > 0) & (G.ort_poz.abs() > 0)].copy()
    G["yon"] = np.where(G.ort_poz > 0, 1, -1)
    G["r"] = (G.fiyat_top + G.funding - G.komisyon) / (G.ort_poz.abs() * G.bar)   # sermaye başına günlük (ölçek sabit)
    G = G.sort_values(["sembol", "gun"])
    G["onceki_gun"] = G.groupby("sembol").gun.shift(); G["onceki_yon"] = G.groupby("sembol").yon.shift()
    G = G[(G.onceki_gun == G.gun - pd.Timedelta(days=1)) & (G.onceki_yon == G.yon)]          # dün de aynı yönde tutuluyordu
    G["pct"] = [PCT.at[d, s] if (s in PCT.columns and d in PCT.index) else np.nan for d, s in zip(G.onceki_gun, G.sembol)]
    G["h"] = h
    rows.append(G.dropna(subset=["pct", "r"]))
D = pd.concat(rows)
D["r"] = D.r.clip(D.r.quantile(.001), D.r.quantile(.999))
for yon, ad in ((1, "LONG"), (-1, "SHORT")):
    x = D[D.yon == yon].copy()
    x["q"] = pd.cut(x.pct, [0, .2, .4, .6, .8, 1.0] if yon > 0 else [0, .5, .7, .8, .9, 1.0], labels=["en az long'çu", "q2", "q3", "q4", "en çok long'çu"])
    t = x.groupby("q", observed=True).r.agg(["size", "mean", "median"]); t["mean"] *= 1e4; t["median"] *= 1e4
    print(f"\n{ad}: dün akşamki kalabalık yüzdeliğine göre ERTESİ GÜN getiri (bp, sermaye başına; 2022-01 → 2026-10)")
    print(t.round(2).to_string())
    x["yil"] = x.gun.dt.year
    print("  yıl bazında (en çok long'çu − en az long'çu, bp):",
          {y: round((g[g.pct > .8].r.mean() - g[g.pct <= .2].r.mean()) * 1e4, 1) for y, g in x.groupby("yil")})
