#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 647 — FUNDING ÖDEME ANI ETRAFINDA FİYAT BASKISI (yeni eksen, 5 dk veri). Hipotez: funding'i uç olan coinde ödeyen taraf
(f > 0 → long'lar) ödemeden hemen ÖNCE kapatır → fiyat ödemeye doğru f'nin tersine (f>0 → aşağı) baskılanır, ödemeden SONRA geri döner.
Doğruysa: (a) carry'nin short girişlerini ödeme sonrasına / çıkışlarını ödeme öncesine kaydırmak icra kazancı, (b) ayrı bir "ödeme
anı" kitabı. Ölçüm: her (coin, ödeme T) için |f| ≥ eşik; yön = −sign(f) (funding ALAN tarafın, yani carry'nin tuttuğu tarafın
getirisi). r_önce = P(T)/P(T−k)−1, r_sonra = P(T+k)/P(T)−1, k = 5..120 dk. TANI; ≤2024 / 2025+ ayrı.
"""
import os, glob, zipfile, pickle
import numpy as np, pandas as pd
K5 = "/home/claude/veri5m/data_5m"
SYM = sorted({os.path.basename(f).split("-5m-")[0] for f in glob.glob(f"{K5}/*.zip")})
F = pickle.load(open("/tmp/zemin.pkl", "rb"))["ODE"]
ADIM = [1, 3, 6, 12, 24]


def seri(s):
    p = []
    for f in sorted(glob.glob(f"{K5}/{s}-5m-*.zip")):
        z = zipfile.ZipFile(f); d = pd.read_csv(z.open(z.namelist()[0]), usecols=[0, 1], header=0, names=["t", "o"]); p.append(d)
    d = pd.concat(p); d = d[pd.to_numeric(d.t, errors="coerce").notna()]
    d["t"] = pd.to_datetime(d.t.astype("int64"), unit="ms")          # 5 dk AÇILIŞ zamanı; açılış fiyatı = o anki fiyat
    return d.drop_duplicates("t").set_index("t").o.astype(float).sort_index()


R = []
for s in SYM:
    if s not in F.columns: continue
    f = F[s]; f = f[(f.index >= "2024-01-01") & (f.abs() > 0)].dropna()
    if f.empty: continue
    c = seri(s); T = f.index; ix = c.index.get_indexer(T); ok = ix >= 24
    T, ix, fv = T[ok], ix[ok], f.values[ok]
    ok2 = ix + 24 < len(c); T, ix, fv = T[ok2], ix[ok2], fv[ok2]
    p0 = c.values[ix]; yon = -np.sign(fv)
    d = {"s": s, "T": T, "f": fv}
    for a in ADIM:
        d[f"once{a*5}"] = yon * (p0 / c.values[ix - a] - 1); d[f"sonra{a*5}"] = yon * (c.values[ix + a] / p0 - 1)
    R.append(pd.DataFrame(d))
R = pd.concat(R, ignore_index=True); R.to_pickle("/tmp/m647/R.pkl")
R["af"] = R.f.abs(); R["d"] = np.where(R["T"] < "2025-01-01", "2024", "2025+")
print(f"olay {len(R)} · sembol {R.s.nunique()}")
for esik in (0.0, 0.0005, 0.001, 0.002):
    for dn in ("2024", "2025+"):
        x = R[(R.af >= esik) & (R.d == dn)]
        print(f"|f|≥{esik*100:.2f}% {dn:5s} n {len(x):6d} | önce " + " ".join(f"{a*5}dk {x[f'once{a*5}'].mean()*1e4:+6.1f}" for a in ADIM)
              + " | sonra " + " ".join(f"{a*5}dk {x[f'sonra{a*5}'].mean()*1e4:+6.1f}" for a in ADIM) + f" | f ort {x.af.mean()*1e4:.1f}bp")
