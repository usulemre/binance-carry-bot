#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 477 — YENİ VERİ: EMİR DEFTERİ DERİNLİĞİ (Binance bookDepth, 2023-01 →).

Projede hiç kullanılmamış tek Binance veri kaynağı. Kitabın (ZSR15P67, hiza 0) 2023'ten beri tuttuğu her
(coin, gün) için bir ÖNCEKİ günün defter derinliği (±%1/±%2/±%5 notional) → o günün yön düzeltilmiş getirisi.
ÖN KAYITLI HİPOTEZLER (koşudan önce):
  H1 dengesizlik: imb2 = (alış2 − satış2)/(alış2 + satış2). Long'da düşük imb (ince alış) → kötü gün / çöküş;
     short'ta yüksek imb (ince satış) → sıkışma.
  H2 likidite çekilmesi: D2 = alış2 + satış2, önceki 7 günün medyanına oran. Düşük oran → büyük hareket.
  H3 incelik: log D1 (±%1 toplam notional) küçükse kuyruk derin.
Ölçüt: beşte birlik dilimlerde ortalama yön düzeltilmiş günlük getiri ve çöküş oranı (≤ −%15), IS (<2025) ve OOS
AYRI. Filtre adayı yalnız: en kötü beşte birlik iki dönemde de en kötü/ikinci en kötü VE monoton eğilim.
"""
import numpy as np, pandas as pd, pickle

def yukle():
    bd = pd.read_pickle("/tmp/bd/bd4h.pkl")
    bd["gun"] = bd["bar"].dt.normalize()
    g = bd.groupby(["sembol", "gun"])[["n-1", "n+1", "n-2", "n+2", "n-5", "n+5"]].mean().reset_index()
    g["imb2"] = (g["n-2"] - g["n+2"]) / (g["n-2"] + g["n+2"])
    g["imb5"] = (g["n-5"] - g["n+5"]) / (g["n-5"] + g["n+5"])
    g["D2"] = g["n-2"] + g["n+2"]; g["lD1"] = np.log(g["n-1"] + g["n+1"])
    g = g.sort_values(["sembol", "gun"])
    g["cek"] = g["D2"] / g.groupby("sembol")["D2"].transform(lambda x: x.shift(1).rolling(7, min_periods=3).median())
    g["gun"] = g["gun"] + pd.Timedelta(days=1)   # ÖNCEKİ günün özelliği → bu güne
    return g

def main():
    gk = pd.read_pickle("/tmp/m477_gk.pkl"); gk["gun"] = pd.to_datetime(gk["gun"])
    gk = gk[gk["ort_poz"].abs() > 1e-4]
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = Z["C"]
    Cg = C.groupby(C.index.normalize()).last(); R = Cg.pct_change()
    r = R.stack().rename("ret").reset_index(); r.columns = ["gun", "sembol", "ret"]
    d = gk.merge(r, on=["gun", "sembol"], how="left").merge(yukle(), on=["sembol", "gun"], how="inner")
    d["yon"] = np.sign(d["ort_poz"]); d["sr"] = d["yon"] * d["ret"]; d["cok"] = d["sr"] <= -0.15
    d["katki"] = d["fiyat"] + d["funding"]
    d = d.dropna(subset=["sr"])
    print(f"gözlem {len(d)} (long {int((d.yon>0).sum())}, short {int((d.yon<0).sum())}), sembol {d.sembol.nunique()}")
    for oz in ("imb2", "imb5", "cek", "lD1"):
        for yon, ad in ((1, "LONG"), (-1, "SHORT")):
            x = d[(d.yon == yon) & d[oz].notna()].copy()
            # kesitsel değil zamansal eşik sızıntısını önlemek için beşte birlik eşikleri IS'ten
            IS = x[x.gun < "2025-01-01"]
            q = IS[oz].quantile([.2, .4, .6, .8]).values
            x["q"] = np.searchsorted(q, x[oz].values)
            print(f"\n{oz} {ad} (eşikler IS'ten: {np.round(q,3)})")
            print(f"  {'q':>2} {'IS ort%':>8} {'IS çök%':>8} {'OOS ort%':>9} {'OOS çök%':>9} {'n':>6}  kitap katkısı IS/OOS (bp/gün)")
            for k in range(5):
                a = x[(x.q == k) & (x.gun < "2025-01-01")]; b = x[(x.q == k) & (x.gun >= "2025-01-01")]
                print(f"  {k:>2} {a.sr.mean()*100:+8.2f} {a.cok.mean()*100:8.2f} {b.sr.mean()*100:+9.2f} {b.cok.mean()*100:9.2f} {len(a)+len(b):6d}"
                      f"  {a.katki.sum()/max(a.gun.nunique(),1)*1e4:+7.1f} / {b.katki.sum()/max(b.gun.nunique(),1)*1e4:+7.1f}")
    d.to_pickle("/tmp/m477_olay.pkl")

if __name__ == "__main__":
    main()
