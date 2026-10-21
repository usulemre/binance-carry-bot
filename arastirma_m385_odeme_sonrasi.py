#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 385 — 00 UTC FUNDING ÖDEMESİNDEN SONRAKİ 4 SAAT: FUNDING SIRASINA GÖRE KAYMA.

TEŞHİS (koşudan önce, 4 sa panel, 8 saatlik coinler, TradFi hariç, hacim >= 20M$):
00 UTC ödemesinden HEMEN SONRAKİ bar (00-04 UTC) içinde, son bilinen funding
sırasına göre üst ondalık − alt ondalık getirisi:
    IS +39,8 bp (t 3,0) · OOS +43,6 bp (t 3,4) · medyan aynı yönde
    ödemesiz barlarda (04/12/20) ~0; 08 ve 16 ödemelerinden sonra tutarsız.
    24 sa ve 4 sa getiriden arındırınca +24,8 bp (t 5,4); hacim >= 100M$'da +56 bp.
    Yıllar: 2022 +47 · 2023 −3 · 2024 +55 · 2025 +32 · 2026 +27.
Yani yüksek funding'li (long kalabalık) coin 00-04 UTC'de düşük funding'liyi geçiyor —
carry kitabının TERS yönü.

STRATEJİ (nedensel): her gün 00:00 UTC barının AÇILIŞINDA (ödeme gerçekleştikten
sonra) son bilinen funding (16 UTC ödemesi) sırasıyla üst q LONG, alt q SHORT,
eşit ağırlık, brüt 1 (0,5 / 0,5); 04:00 UTC kapanışında çık. Pozisyon hiçbir
ödeme anından geçmez → funding ÖDENMEZ/ALINMAZ.
MALİYET: taraf başı taker %0,05 + kayma %0,01 = 6 bp; günde giriş + çıkış =
brüt x 2 x 6 bp = 12 bp/gün.
IZGARA (6 kol): q {0,10 · 0,20} x hacim eşiği {20M · 50M · 100M$}.
SEÇİM yalnız IS (2022-01..2024-12) Sharpe'ıyla; seçilen TEK kol OOS'ta
(2025-01..2026-08) raporlanır.
PLASEBO (iki): (a) aynı kural 12-16 UTC barında (ödemesiz bar), (b) 00 UTC'de
funding sırası kesitsel karıştırılmış.
KABUL (sonraki tura — carry ile birlikte %95 protokolü): OOS net Sh >= 1,0,
iki plaseboyu da >= 0,5 geçer. (rho şartı burada yön gereği negatif beklenir;
raporlanır, eleme şartı değil — carry'nin tersi olduğu için harman turunda
asıl soru NETLEŞMİŞ kitabın getirisi.)
2.000 $ fizibilitesi: bacak başı $ raporlanır (Binance asgari 5 $).
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
MAL = 0.0006
RNG = np.random.default_rng(385)


def yukle():
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); P = pickle.load(open("/tmp/panel.pkl", "rb"))
    C = z["C"]; F = z["ODE"].reindex_like(C).fillna(0.0)
    from tradfi_liste import TRADFI
    HAC = P["HAC"].reindex_like(C)
    taban = (P["YAS"].reindex_like(C) >= 14 * 6) & C.notna()
    taban = taban & ~taban.columns.isin(list(TRADFI))
    # yalnız 8 saatlik coinler (son 3 günde 04/12/20'de ödeme yok)
    ara = (F[F.index.hour.isin([4, 12, 20])] != 0).rolling(18, min_periods=1).sum()
    ara8 = (ara.reindex(C.index).ffill() == 0)
    Rb = (C / C.shift(1) - 1).clip(-0.9, 3)          # bar t: fiyat(t) -> fiyat(t+4s)
    son = F.where(F != 0).ffill(limit=6).shift(1)      # bar t'den önce bilinen son ödeme
    return C, HAC, taban & ara8, Rb, son


def gunluk(son, Rb, uy, saat, q, karistir=False):
    m = Rb.index.hour == saat
    S = son[m].where(uy[m])
    if karistir:
        v = S.values.copy()
        for i in range(v.shape[0]):
            k = np.isfinite(v[i]); v[i, k] = RNG.permutation(v[i, k])
        S = pd.DataFrame(v, index=S.index, columns=S.columns)
    rk = S.rank(axis=1, pct=True)
    X = Rb[m]
    ust, alt = X.where(rk >= 1 - q).mean(axis=1), X.where(rk <= q).mean(axis=1)
    n = (rk >= 1 - q).sum(axis=1)
    g = (0.5 * ust - 0.5 * alt - 2 * MAL).where(ust.notna() & alt.notna(), 0.0)
    g.index = g.index.floor("D")
    n.index = g.index
    return g, n


def sh(g):
    g = np.asarray(g, float)
    return float(g.mean() / g.std() * np.sqrt(365.25)) if g.std() > 0 else np.nan


def ozet(g):
    e = (1 + g).cumprod()
    return (e.iloc[-1] ** (365.25 / len(g)) - 1) * 100, ((e / e.cummax()) - 1).min() * 100


def main():
    C, HAC, taban, Rb, son = yukle()
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    print(f"{'kol':<16} {'IS Sh':>6} {'OOS Sh':>7} {'OOS yil%':>9} {'OOS dusus':>9} "
          f"{'PLA12':>6} {'PLAkar':>6} {'rho':>6} {'bacak/taraf':>11} {'$/bacak@2000':>12}")
    sat = []
    for q in (0.10, 0.20):
        for esik in (2e7, 5e7, 1e8):
            uy = taban & (HAC >= esik)
            g, n = gunluk(son, Rb, uy, 0, q)
            g12, _ = gunluk(son, Rb, uy, 12, q)
            gk, _ = gunluk(son, Rb, uy, 0, q, karistir=True)
            IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
            o = lambda x: x[x.index >= "2025-01-01"]
            yil, dd = ozet(OOS)
            ix = g.index.intersection(carry.index)
            rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
            nb = float(n[n.index >= "2025-01-01"].median())
            r = dict(ad=f"q{q:.2f} {esik/1e6:.0f}M", IS=sh(IS), OOS=sh(OOS), yil=yil, dd=dd,
                     p12=sh(o(g12)), pk=sh(o(gk)), rho=rho, nb=nb, g=g)
            sat.append(r)
            print(f"{r['ad']:<16} {r['IS']:>6.2f} {r['OOS']:>7.2f} {yil:>+9.1f} {dd:>9.1f} "
                  f"{r['p12']:>6.2f} {r['pk']:>6.2f} {rho:>+6.2f} {nb:>11.0f} {1000/max(nb,1):>12.1f}",
                  flush=True)
    en = max(sat, key=lambda x: x["IS"])
    kabul = en["OOS"] >= 1.0 and en["OOS"] - en["p12"] >= 0.5 and en["OOS"] - en["pk"] >= 0.5
    print(f"\nIS'TE SECILEN: {en['ad']} (IS {en['IS']:.2f}) -> OOS {en['OOS']:.2f} "
          f"(plasebo12 {en['p12']:.2f}, karisik {en['pk']:.2f}) -> {'SONRAKI TURA' if kabul else 'RED'}")
    g = en["g"]
    for y in range(2022, 2027):
        gy = g[g.index.year == y]
        print(f"  {y}: Sh {sh(gy):+.2f}  getiri {((1+gy).prod()-1)*100:+.1f}%")
    pickle.dump({k: v for k, v in en.items()}, open("/tmp/m385_secilen.pkl", "wb"))


if __name__ == "__main__":
    main()
