#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 809 — kilit açılışı teşhisi (kapı). Ön kayıt KAR_HARITASI 809. KARAR VERMEZ."""
import json, os, pickle
import numpy as np, pandas as pd
import arastirma_m389_ml_tahmin as A
H = "/tmp/m809/ham"; idm = json.load(open(f"{H}/idmap.json"))
C, Fd, uy, X = A.panel()
kol = {c.replace("USDT", "").replace("1000", ""): c for c in C.columns}
arz = {}
for s in idm:
    yol = f"{H}/mc_{s}.json"
    if not os.path.exists(yol): continue
    d = json.load(open(yol))
    if not d or "prices" not in d: continue
    p = pd.Series({pd.Timestamp(t, unit="ms").normalize(): v for t, v in d["prices"]})
    m = pd.Series({pd.Timestamp(t, unit="ms").normalize(): v for t, v in d["market_caps"]})
    a = (m / p).replace([np.inf, -np.inf], np.nan); a = a[a > 0]
    if len(a) > 200 and s in kol: arz[kol[s]] = a[~a.index.duplicated(keep="last")]
S = pd.DataFrame(arz).sort_index(); S = S[(S.index >= "2025-11-17") & (S.index <= "2026-11-15")]
g = S / S.shift(1) - 1; g3 = S.shift(-3) / S.shift(1) - 1
olay = (g >= 0.02) & (g3 >= 0.015)
ol = [(t, c, float(g.loc[t, c])) for c in olay.columns for t in olay.index[olay[c]]]
print(f"arz verisi olan coin {S.shape[1]} · olay (≥%2 arz artışı) {len(ol)} · coin başına medyan {pd.Series([c for _, c, _ in ol]).value_counts().median() if ol else 0}")
# (a) olay etrafı fazla getiri (evren medyanına göre)
r = (C / C.shift(1) - 1).where(uy); fz = r.sub(r.median(axis=1), axis=0)
pen = range(-7, 8); M = []
for t, c, b in ol:
    if t not in fz.index or c not in fz.columns: continue
    i = fz.index.get_loc(t); 
    if i < 8 or i + 8 > len(fz): continue
    M.append([fz[c].iloc[i + k] for k in pen])
M = pd.DataFrame(M, columns=list(pen)); print(f"(a) n {len(M)} olay")
cum = M.loc[:, -7:0].sum(axis=1); sonra = M.loc[:, 1:7].sum(axis=1)
print(f"   −7…0 birikimli fazla getiri ort {cum.mean() * 100:+.2f} (medyan {cum.median() * 100:+.2f}) · +1…+7 ort {sonra.mean() * 100:+.2f} (medyan {sonra.median() * 100:+.2f})")
print("   gün gün ort (%):", " ".join(f"{k}:{M[k].mean() * 100:+.2f}" for k in pen))
# (b) olay öncesi fon3 sırası
F3 = X["fon3"]; fb = [F3[c].loc[:t].iloc[-7:].mean() for t, c, b in ol if c in F3.columns and t in F3.index]
print(f"(b) olaydan önceki 7 g fon3 sırası ort {np.nanmean(fb):.2f} (0 = en negatif funding / en kalabalık short; evren ort 0,50)")
# (c) P3T2 long katkısı: olaydan önceki 7 g vs diğer long günleri
G = pd.concat([pd.read_pickle(f"/tmp/m783c/gk_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun); G = G[G.ort_poz > 0]
G["net"] = (G.fiyat + G.funding) / G.ort_poz.abs()        # birim pozisyon başına günlük getiri
on = set()
for t, c, b in ol:
    for k in range(0, 8): on.add((t - pd.Timedelta(days=k), c))
G["olay_oncesi"] = [(d, s) in on for d, s in zip(G.gun, G.sembol)]
a_ = G[G.olay_oncesi].net; b_ = G[~G.olay_oncesi].net
print(f"(c) P3T2 long-gün: olaydan önceki 7 g (n {len(a_)}) birim getiri ort {a_.mean() * 100:+.3f}%/gün · diğer (n {len(b_)}) {b_.mean() * 100:+.3f}%/gün")
print("   olay öncesi tutulan coinler:", G[G.olay_oncesi].sembol.str.replace("USDT", "").value_counts().head(12).to_dict())
gec = cum.mean() <= -0.02 and a_.mean() < b_.mean()
print("KAPI:", "GEÇTİ → 810 motor ön kaydı" if gec else "GEÇMEDİ → kapanır")
pickle.dump({"olay": ol}, open("/tmp/m809/olaylar.pkl", "wb"))
