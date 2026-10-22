#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 432 — İLERİ YÜRÜYEN AYAR SEÇİMİ (bot ayarını kendisi değiştirir).

Soru: sabit bir ayar yerine, her ay başı son L ayda en iyi Sharpe'lı k ayara geçmek
(sermaye eşit bölünmüş) kontrolü geçer mi? Yalnız geçmiş bilgiyle seçim → seçim yanlılığı yok.
Havuzlar: P25 = madde 425 (24 ayar + kontrol), P50 = 425 + 427 (yaş 45 batanlar dahil:
gerçekte de o ayarı seçme riski vardır). Seri: iki hiza ortalaması, 2.000 $ D8, kaymalı model.
Kurallar (ön kayıt): L ∈ {6, 12} ay, k ∈ {1, 3, 5}, aylık yeniden seçim; geçiş maliyeti:
ayar değişen sermaye payı x %0,20 (tüm kitabı kapat/aç). Test dönemi 2023-07..2026-09.
Ölçüt: kontrolle aynı dönemde Sharpe, yıllık, dd; yıllara göre.
"""
import os
import numpy as np, pandas as pd

SH = lambda x: x.mean() / x.std() * np.sqrt(365.25)
YIL = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
DD = lambda x: (((1 + x).cumprod() / (1 + x).cumprod().cummax()) - 1).min() * 100


def gunM(p):
    E = pd.read_pickle(p); r = E.pct_change().dropna()
    x = (1 + r).groupby(r.index.date).prod() - 1; x.index = pd.DatetimeIndex(x.index); return x


def havuz(dizinler):
    G = {}
    for d in dizinler:
        for f in sorted(os.listdir(d)):
            if f.endswith("_0.pkl"):
                a = f[:-6]
                if a == "K00" and "K00" in G:
                    continue
                try:
                    G[(a if a == "K00" else f"{os.path.basename(d)}_{a}")] = (gunM(f"{d}/{a}_0.pkl") + gunM(f"{d}/{a}_1.pkl")) / 2
                except Exception:
                    pass
    D = pd.DataFrame(G).dropna()
    return D.clip(lower=-0.99)  # batan ayar: günlük -%100 altı → hesap biter


def yuru(D, L, k, bas="2023-07-01"):
    aylar = pd.date_range(bas, D.index[-1], freq="MS")
    out, onceki = [], set()
    for i, a in enumerate(aylar):
        b = aylar[i + 1] if i + 1 < len(aylar) else D.index[-1] + pd.Timedelta(days=1)
        gecmis = D[(D.index >= a - pd.DateOffset(months=L)) & (D.index < a)]
        # batmış ayar bir daha seçilemez (özsermaye <= 0)
        canli = [c for c in D if ((1 + D.loc[D.index < a, c]).cumprod() > 0.01).all()]
        sec = list(gecmis[canli].apply(SH).sort_values(ascending=False).index[:k])
        r = D.loc[(D.index >= a) & (D.index < b), sec].mean(axis=1).copy()
        degisen = len(set(sec) - onceki) / k if onceki else 0
        r.iloc[0] -= degisen * 0.002
        onceki = set(sec); out.append(r)
    return pd.concat(out), sec


def main():
    for ad, dz in (("P25", ["/tmp/m425"]), ("P50", ["/tmp/m425", "/tmp/m427"])):
        D = havuz(dz)
        k0 = D["K00"]; k0 = k0[k0.index >= "2023-07-01"]
        print(f"\n=== {ad}: {D.shape[1]} ayar ===")
        yillar = sorted(set(k0.index.year))
        bas = lambda x: f"Sh {SH(x):.2f} yil {YIL(x):+7.1f} dd {DD(x):6.1f} | " + " ".join(
            f"{y}:{((1 + x[x.index.year == y]).prod() - 1) * 100:+5.0f}" for y in yillar)
        print(f"KONTROL      {bas(k0)}")
        for L in (6, 12):
            for k in (1, 3, 5):
                r, son = yuru(D, L, k)
                print(f"L{L:2d} k{k}       {bas(r)}  | simdi: {','.join(s.split('_')[-1] for s in son)}")


if __name__ == "__main__":
    main()
