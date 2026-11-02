#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 714 — SHORT POZİSYON YAŞI VE KÂRLILIK PROFİLİ (yalnız ölçüm; strateji / parametre değişmez; motor koşusu yok).
Gruplama yalnız GİRİŞ ANINDA bilinen özelliklerle: coin yaşı (giriş günü), giriş carry'si (giriş gününden önceki günün ödemeleri), yıl.
Veri: madde 711 defteri (EK_T7KKS ile bayt bayt aynı) + 712 / 713 pozisyon tanımı. Kullanım: python3 arastirma_m714_short_yas.py
"""
import os, sys, warnings
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")
import arastirma_m713_firsat_omru as A

ERKEN = (0, 2)       # yaş 0-2 g
GEC = (3, 999)       # yaş >= 3 g


def ns(x, c="net"):
    s = x.sgun.sum()
    return x[c].sum() / s * 365 if s > 0 else np.nan


def bolum(g, ad):
    e = g[g.pyas <= ERKEN[1]]; l = g[g.pyas >= GEC[0]]
    return {"grup": ad, "poz": g.pid.nunique(), "erken net/sy": ns(e), "geç net/sy": ns(l), "fark": ns(e) - ns(l),
            "erken TP/sy": ns(e, "tp"), "geç TP/sy": ns(l, "tp"), "erken fiyat/sy": ns(e, "fiyat"), "geç fiyat/sy": ns(l, "fiyat"),
            "erken funding/sy": ns(e, "funding"), "geç funding/sy": ns(l, "funding"), "geç sermaye payı %": l.sgun.sum() / g.sgun.sum() * 100}


def main():
    G, P, FP, med, Pn = A.hazirla()
    S = G[G.yon == "S"].copy(); PS = P[P.yon == "S"].copy()
    print(f"SHORT: {len(PS)} pozisyon, {len(S)} pozisyon-gün; süre medyan {PS.gun_say.median():.0f} g, ort {PS.gun_say.mean():.1f}, p90 {PS.gun_say.quantile(.9):.0f}")
    print("\n==================== 1) YAŞA GÖRE (tüm) — 713 tablosu\n" + A.yas_tablosu(S).round(1).to_string())
    rows = [bolum(S, "tümü")]
    rows += [bolum(S[S.genc == True], "genç coin (≤365 g, girişte)"), bolum(S[S.genc == False], "eski coin")]
    PS["cq"] = pd.qcut(PS.beklenen_carry.rank(method="first"), 3, labels=["carry düşük", "carry orta", "carry yüksek"])
    S = S.merge(PS[["cq"]], left_on="pid", right_index=True, how="left")
    rows += [bolum(S[S.cq == q], q) for q in ["carry düşük", "carry orta", "carry yüksek"]]
    rows += [bolum(S[S.yil == y], str(y)) for y in range(2020, 2027)]
    print("\n==================== 2) ERKEN (0-2 g) vs GEÇ (≥3 g): gruplar (giriş anı özellikleri) ve yıllar\n" +
          pd.DataFrame(rows).set_index("grup").round(1).to_string())
    # 3) seçilim kontrolü: AYNI pozisyonlar içinde (≥ 5 gün tutulanlar) yaş 0-2 vs 3-4
    uz = PS[PS.gun_say >= 5].index; X = S[S.pid.isin(uz)]
    out = {}
    for ad, x in [("tümü", X)] + [(str(y), X[X.yil == y]) for y in range(2020, 2027)]:
        a = x[x.pyas <= 2]; b = x[(x.pyas >= 3) & (x.pyas <= 4)]
        out[ad] = {"poz": x.pid.nunique(), "0-2 net/sy": ns(a), "3-4 net/sy": ns(b), "0-2 TP/sy": ns(a, "tp"), "3-4 TP/sy": ns(b, "tp"),
                   "0-2 fiyat/sy": ns(a, "fiyat"), "3-4 fiyat/sy": ns(b, "fiyat")}
    print("\n==================== 3) SEÇİLİM KONTROLÜ: yalnız ≥ 5 gün tutulan short'lar, AYNI pozisyonlarda yaş 0-2 vs 3-4\n" +
          pd.DataFrame(out).T.round(1).to_string())
    # kısa ve uzun ömürlü pozisyonların yaş 0-2'si (ömür sonradan bilinir → yalnız betimsel)
    ki = PS[PS.gun_say <= 3].index
    print(f"  betimsel: ≤ 3 g süren short'ların yaş 0-2 net/sy {ns(S[S.pid.isin(ki) & (S.pyas <= 2)]):.0f} · ≥ 5 g sürenlerin {ns(S[S.pid.isin(uz) & (S.pyas <= 2)]):.0f}"
          f" (ömür sonradan bilinir; karar için kullanılamaz)")
    # 4) yoğunlaşma: erken net'e en çok katkı yapan 3 coin çıkınca
    e = S[S.pyas <= 2]; l = S[S.pyas >= 3]
    top = (e.groupby("sembol").net.sum()).sort_values(ascending=False).head(3)
    h = S[~S.sembol.isin(top.index)]
    print(f"\n==================== 4) YOĞUNLAŞMA: erken net'e en çok katkı yapan 3 coin {dict(top.round(1))}")
    print(f"  fark (erken − geç net/sy): tam {ns(e) - ns(l):.0f} → 3 coin hariç {ns(h[h.pyas <= 2]) - ns(h[h.pyas >= 3]):.0f}")
    yy = {y: ns(h[(h.yil == y) & (h.pyas <= 2)]) - ns(h[(h.yil == y) & (h.pyas >= 3)]) for y in range(2020, 2027)}
    print("  3 coin hariç yıllar: " + " · ".join(f"{k}: {v:+.0f}" for k, v in yy.items()))
    pay = e.groupby("sembol").net.sum().sort_values(ascending=False)
    print(f"  erken net'te ilk 3 / 10 coin payı: %{pay.head(3).sum() / pay.sum() * 100:.0f} / %{pay.head(10).sum() / pay.sum() * 100:.0f}")
    # 5) yaşa göre en büyük ters hareket (short: girişten o yaşa kadar en yüksek yükseliş, 4 sa kapanış)
    C = Pn["C"]; r = []
    for p in PS.itertuples():
        if p.sembol not in C.columns:
            continue
        c = C[p.sembol].loc[p.giris - pd.Timedelta(hours=4): p.cikis + pd.Timedelta(hours=20)].dropna()
        if len(c) < 2:
            continue
        x = c / c.iloc[0] - 1
        for a in (0, 1, 2, 3, 5, 7):
            if a < p.gun_say:
                son = p.giris + pd.Timedelta(days=a + 1)
                r.append({"yas": a, "mae": -x[:son].max() * 100, "yil": p.yil})
    R = pd.DataFrame(r)
    print("\n==================== 5) YAŞA KADAR EN BÜYÜK TERS HAREKET (short; girişten itibaren en yüksek yükseliş, %; 4 sa kapanış)")
    print("  " + R.groupby("yas").mae.describe(percentiles=[.1, .5]).round(1)[["count", "50%", "10%", "min"]].to_string().replace("\n", "\n  "))
    # artış: yaş a'dan a+1'e EK ters hareket olasılığı
    print("\n  gün başına sermaye: short sermayesinin yaşa göre payı 0-2 g %{:.0f}, ≥3 g %{:.0f}".format(
        S[S.pyas <= 2].sgun.sum() / S.sgun.sum() * 100, S[S.pyas >= 3].sgun.sum() / S.sgun.sum() * 100))


if __name__ == "__main__":
    main()
