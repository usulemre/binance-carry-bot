#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 459 — BAĞIMSIZ İKİNCİ KOL: BTC/ETH ZAMAN-SERİSİ TREND TAKİBİ (carry ile harman).

Madde 305/347'nin "trend sleeve"i carry evreni İÇİNDE kesitsel momentumdu. Burada carry'den bağımsız,
klasik yön stratejisi: BTC ve ETH perp'inde son L gün getirisi > 0 ise long, değilse short (LS) ya da
nakit (L0). Günlük karar (00 UTC kapanışı, ertesi gün uygulanır), pozisyon değişiminde 5 bp, perp
funding'i ödenir/alınır (zemin ODE). Kol = BTC ve ETH eşit.
Harman: günlük getiri = (1−w) x T60(+24 sa stop) + w x trend, w ∈ {0,10 · 0,20 · 0,30}.
ÖN KAYIT: L ve tür IS (22-07..24-12) Sharpe'ıyla seçilir; harman, T60'ı EŞİT OYNAKLIĞA kaldıraçlamaktan
hem IS'te hem OOS'ta >= +10 puan yıllık iyi olmalı → "İKİNCİ KOL ADAYI".
"""
import pickle, itertools
import numpy as np, pandas as pd
import arastirma_m443_kotu_gun_kalkani as K

SH = lambda x: x.mean() / x.std() * np.sqrt(365.25)


def trend_kolu(L, tur):
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); C, ODE = z["C"], z["ODE"]
    out = []
    for s in ("BTCUSDT", "ETHUSDT"):
        c = C[s].groupby(C.index.date).last(); c.index = pd.DatetimeIndex(c.index)
        f = ODE[s].groupby(ODE.index.date).sum(); f.index = pd.DatetimeIndex(f.index)   # günlük funding oranı toplamı
        r = c.pct_change()
        sig = np.sign(c / c.shift(L) - 1)
        if tur == "L0":
            sig = sig.clip(lower=0)
        poz = sig.shift(1)                         # dünkü kapanışta karar, bugün uygulanır
        net = poz * r - poz * f.reindex(r.index).fillna(0) - poz.diff().abs().fillna(0) * 0.0005
        out.append(net)
    return pd.concat(out, axis=1).mean(axis=1).dropna()


def main():
    t = K.seri("KD24_45T2")
    print("TREND KOLU TEK BASINA (Sharpe IS / OOS, yillik, BTC~T60 korelasyon):")
    secim = []
    for L, tur in itertools.product((20, 50, 100), ("LS", "L0")):
        k = trend_kolu(L, tur); i = t.index.intersection(k.index); k = k[i]
        IS, OOS = k[k.index < "2025-01-01"], k[k.index >= "2025-01-01"]
        print(f"  L{L:3d} {tur}: Sh IS {SH(IS):+.2f} OOS {SH(OOS):+.2f} | yillik IS {K.YIL(IS):+6.1f} OOS {K.YIL(OOS):+6.1f} | korelasyon T60 {k.corr(t[i]):+.3f}")
        secim.append((SH(IS), L, tur))
    _, L, tur = max(secim)
    k = trend_kolu(L, tur); i = t.index.intersection(k.index); k, tt = k[i], t[i]
    print(f"\nIS'te secilen: L{L} {tur}")
    for w in (0.10, 0.20, 0.30):
        h = (1 - w) * tt + w * k
        for ad, m in (("IS", h.index < "2025-01-01"), ("OOS", h.index >= "2025-01-01")):
            hh, t0 = h[m], tt[m]
            kv = hh.std() / t0.std(); tv = t0 * kv
            print(f"  w {w:.2f} {ad:3s}: harman yil {K.YIL(hh):+7.1f} Sh {SH(hh):.2f} dd {K.DD(hh):6.1f} | T60 esit oynaklik (x{kv:.2f}) yil {K.YIL(tv):+7.1f} Sh {SH(t0):.2f} | fark {K.YIL(hh)-K.YIL(tv):+6.1f}")


if __name__ == "__main__":
    main()
