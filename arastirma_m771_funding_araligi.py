#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 771 — funding ödeme ARALIĞI (1 / 2 / 4 / 8 sa) ile bacak sonucu (betimsel; motor koşusu yok).
Kullanıcı gözlemi: "saatlik funding'ler (8 / 4 saatliklerden) daha iyi ödüyor". 711 defteri (P3T2, iki hiza ortalaması, % kitap).
Her coin-gün için o günün ödeme aralığı (ham ödeme zaman damgaları); pozisyonun GİRİŞ günündeki aralığa göre gruplanır."""
import os, numpy as np, pandas as pd
import arastirma_m712_funding_kaynak as K
R = os.path.dirname(os.path.abspath(__file__))


def aralik_paneli(semboller):
    d = {}
    for s in semboller:
        y = os.path.join(R, "data_funding_uzun", f"{s}.csv")
        if not os.path.exists(y):
            continue
        f = pd.read_csv(y); f["date"] = pd.to_datetime(f["date"], format="mixed")
        ara = f["interval_h"] if "interval_h" in f else pd.Series(np.nan, index=f.index)
        fark = f["date"].diff().dt.total_seconds().div(3600).round()
        ara = ara.fillna(fark.where(fark.isin([1, 2, 4, 8]))).fillna(8)
        d[s] = pd.Series(ara.values, index=f["date"]).resample("D").min()     # gün içindeki en kısa aralık
    return pd.DataFrame(d).ffill()


G = K.defter(); G["yas_g"] = 0; G["fiyat"] = G["fiyat_top"]; P = K.pozisyonlar(G)
A = aralik_paneli(sorted(P.sembol.unique()))
P["aralik"] = [A.at[g, s] if (s in A.columns and g in A.index) else np.nan for s, g in zip(P.sembol, P.giris)]
P = P.dropna(subset=["aralik"])
P = P[P.sgun > 0]
for c in ("funding", "fiyat", "tp", "stop", "kom", "net"):
    P[c + "_g"] = P[c] / P["sgun"]          # sermaye-gün başına (% / gün, bacak büyüklüğünden bağımsız)
pd.set_option("display.width", 220)
for yon in ("L", "S"):
    Q = P[P.yon == yon]
    T = Q.groupby("aralik").agg(poz=("net", "size"), sermaye_gun=("sgun", "sum"),
                                 funding_g=("funding", "sum"), fiyat_g=("fiyat", "sum"), tp_g=("tp", "sum"), stop_g=("stop", "sum"),
                                 kom_g=("kom", "sum"), net_g=("net", "sum"))
    for c in ("funding_g", "fiyat_g", "tp_g", "stop_g", "kom_g", "net_g"):
        T[c] = T[c] / T["sermaye_gun"] * 100           # baz puan / sermaye-gün
    T["net pozitif %"] = Q.groupby("aralik").net.apply(lambda x: (x > 0).mean() * 100)
    print(f"\n{'LONG' if yon == 'L' else 'SHORT'} — giriş günündeki funding aralığına göre (bp / sermaye-gün; net = fiyat + funding − kom, TP/stop dahil):")
    print(T.round(2).to_string())
print("\nYıllara göre 1 sa aralıklı pozisyon payı (sermaye-gün %):")
P["yil"] = P.giris.dt.year
print((P[P.aralik <= 1].groupby("yil").sgun.sum() / P.groupby("yil").sgun.sum() * 100).round(1).to_dict())
print("\nLONG 2025+ (1 sa aralık yaygınlaşınca):")
Q = P[(P.yon == "L") & (P.giris >= "2025-01-01")]
T = Q.groupby("aralik").agg(poz=("net", "size"), sg=("sgun", "sum"), f=("funding", "sum"), n=("net", "sum"))
T["funding bp/sg"] = T.f / T.sg * 100; T["net bp/sg"] = T.n / T.sg * 100
print(T[["poz", "funding bp/sg", "net bp/sg"]].round(2).to_string())

print("\nSağlamlık (LONG, 2025+): en iyi N pozisyon çıkarılınca net bp/sg; ve yarıyıllar")
Q = P[(P.yon == "L") & (P.giris >= "2025-01-01")].copy()
Q["grp"] = np.where(Q.aralik <= 2, "1-2 sa", np.where(Q.aralik == 4, "4 sa", "8 sa"))
for n in (0, 5, 10, 20):
    r = {}
    for g, x in Q.groupby("grp"):
        x = x.sort_values("net", ascending=False).iloc[n:]
        r[g] = round(x.net.sum() / x.sgun.sum() * 100, 1)
    print(f"  ilk {n:2d} çıkarılınca:", r)
Q["yy"] = Q.giris.dt.year.astype(str) + np.where(Q.giris.dt.month <= 6, "-1", "-2")
t = Q.groupby(["yy", "grp"]).apply(lambda x: pd.Series({"n": len(x), "net": x.net.sum() / x.sgun.sum() * 100})).unstack()
print(t.round(1).to_string())
print("  1-2 sa coin sayısı:", Q[Q.grp == "1-2 sa"].sembol.nunique(), "· en çok:", Q[Q.grp == "1-2 sa"].groupby("sembol").net.sum().sort_values().round(2).to_dict())
