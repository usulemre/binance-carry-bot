#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 634 — İCRA ZAMANLAMASI 5 DAKİKALIK VERİYLE (yeni eksen: kitabın KENDİ işlemlerinin dolum anı).
Madde 519: maliyet 5 → 10 bp yıllık ~33 puan → kitap 1 bp icra farkına ~6,6 puan/yıl duyarlı. Motor işlemleri 4 sa bar kapanışında
doldurur. Kitap zaten işlem yapıyor; işlemin YAPILACAĞI dakika serbest. Soru: dengeleme işleminden sonraki dakikalarda fiyat işlemin
TERSİNE mi dönüyor (aldığımız coin 15-60 dk sonra ucuzluyor → beklemek/TWAP kazandırır) yoksa işlem yönünde mi gidiyor (hemen
yapmak doğru)? Önceki 5 dk çalışması (madde ~370) bağımsız bir strateji olarak komisyona yenildi; burada ek işlem YOK, yalnız zaman kayar.
Veri: data_5m (100 likit sembol, 2024-01 → 2026-08). İşlemler: T7K 1,15x + koşullu stop POZ_CIKTI (/tmp/m621/pozKS_{0,1}), ağırlık
değişimi Δw ≠ 0 olan (zaman, coin); icra anı T = o barın etiketi (motor kapanışı = 5 dk kapanışı T). Kayma_k = yön(Δw) × (P(T+k)/P(T) − 1);
negatif = fiyat işlemimizin tersine döndü (beklemek kazandırırdı). Ağırlıklı ortalama bp ve kitap etkisi ≈ Σ|Δw|·kayma / yıl × 1,15.
TANI; kural (bot'ta gecikmeli/dilimli emir) ayrı ön kayıtla.
"""
import os, zipfile, glob
import numpy as np
import pandas as pd

K5 = "/home/claude/veri5m/data_5m"
SYM = sorted({os.path.basename(f).split("-5m-")[0] for f in glob.glob(f"{K5}/*.zip")})
ADIM = [1, 3, 6, 12, 24, 48]          # 5 dk adım: 5, 15, 30, 60, 120, 240 dk


def seri(s):
    parcalar = []
    for f in sorted(glob.glob(f"{K5}/{s}-5m-*.zip")):
        z = zipfile.ZipFile(f)
        d = pd.read_csv(z.open(z.namelist()[0]), usecols=[0, 4], header=0, names=["t", "c"])
        parcalar.append(d)
    d = pd.concat(parcalar)
    d = d[pd.to_numeric(d.t, errors="coerce").notna()]
    d["t"] = pd.to_datetime(d.t.astype("int64"), unit="ms") + pd.Timedelta("5min")   # 5 dk KAPANIŞ zamanı
    return d.drop_duplicates("t").set_index("t").c.astype(float).sort_index()


kayit = []
for h in (0, 1):
    P = pd.read_pickle(f"/tmp/m621/pozKS_{h}.pkl")
    P = P[(P.zaman >= "2024-01-01") & P.sembol.isin(SYM)]
    W = P.pivot_table(index="zaman", columns="sembol", values="w", aggfunc="sum").fillna(0.0)
    tam = pd.date_range(W.index.min(), W.index.max(), freq="4h")
    W = W.reindex(tam).fillna(0.0)
    D = W.diff().iloc[1:]; Wb = W.abs().rolling(2).max().iloc[1:]
    for s in D.columns:
        # ağırlık kayması (fiyatla küçük oransal değişim) işlem DEĞİL: göreli değişim ≥ %25 ve mutlak ≥ 0,002 olanlar
        dd = D[s][(D[s].abs() > 0.002) & (D[s].abs() >= 0.25 * Wb[s])]
        if dd.empty: continue
        kayit.append(pd.DataFrame({"h": h, "s": s, "T": dd.index, "dw": dd.values}))
I = pd.concat(kayit, ignore_index=True)
print(f"işlem olayı: {len(I)} (iki hiza), sembol {I.s.nunique()}")

sonuc = []
for s, g in I.groupby("s"):
    c = seri(s)
    idx = c.index.get_indexer(g["T"])
    ok = idx >= 0
    g = g[ok].copy(); idx = idx[ok]
    p0 = c.values[idx]
    for a in ADIM:
        j = np.minimum(idx + a, len(c) - 1)
        g[f"k{a*5}"] = np.sign(g.dw.values) * (c.values[j] / p0 - 1)
    sonuc.append(g)
R = pd.concat(sonuc, ignore_index=True)
R["agr"] = R.dw.abs()
R["taraf"] = np.where(R.dw > 0, "al", "sat")
yil = (R["T"].max() - R["T"].min()).days / 365.25
kol = [f"k{a*5}" for a in ADIM]
print(f"eşleşen işlem {len(R)} · dönem {yil:.2f} yıl")
print("\nAğırlıklı ort. kayma (bp; − = fiyat işlemin TERSİNE döndü → beklemek kazandırırdı) ve kitap etkisi (puan/yıl, 1,15x):")
for ad, m in (("hepsi", R.agr > 0), ("alış", R.taraf == "al"), ("satış", R.taraf == "sat")):
    x = R[m]; w = x.agr
    bp = {k: (x[k] * w).sum() / w.sum() * 1e4 for k in kol}
    puan = {k: (x[k] * w).sum() / 2 * 100 / yil * 1.15 for k in kol}
    print(f"{ad:6s} n {len(x):6d} | " + " ".join(f"{k[1:]}dk {bp[k]:+6.1f}bp/{puan[k]:+5.1f}p" for k in kol))
R["yil"] = R["T"].dt.year
print("\nyıl bazında (60 dk, bp):", R.groupby("yil").apply(lambda x: (x.k60 * x.agr).sum() / x.agr.sum() * 1e4).round(1).to_dict())
R["saat"] = R["T"].dt.hour
print("işlem saati bazında (60 dk, bp):", R.groupby("saat").apply(lambda x: (x.k60 * x.agr).sum() / x.agr.sum() * 1e4).round(1).to_dict())
R.to_pickle("/tmp/m621/icra_5dk.pkl")
