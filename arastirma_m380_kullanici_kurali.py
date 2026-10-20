#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 380 — KULLANICININ KURALI + SIKIŞMA FİLTRELERİ.

Kullanıcının beyan ettiği kural (bellek, madde 187'de aynen ölçüldü:
−%57,7/yıl): her gün 00:00 UTC (03:00 İstanbul) son 24 saatte >= +%X
yükseleni SHORT, <= −%X düşeni LONG; pozisyon başına bakiyenin %25'i, en
fazla 4 pozisyon, coin başına −%25 stop.

Madde 203/379'un deseni: işlemlerin ÇOĞU kazanıyor (medyan +, %55-62)
ama nadir sıkışmalar (p1 −%72..−%299) ortalamayı negatife çekiyor.
Kuralı değiştirmeden SIKIŞMAYI ayıklamak için projenin kendi en güçlü
bulgusundan türetilen filtreler (madde 358: kalabalık oranı ~80 puanlık
bilgi; madde 195: pump short'u funding ÖDÜYOR = short taraf kalabalık):
    yok    — kullanıcının kuralı aynen
    LS     — short yalnız long hesapların KALABALIK olduğu pump'ta
             (o barda uygun evrende count_long_short_ratio üst üçte biri);
             long yalnız short'ların kalabalık olduğu düşüşte (alt üçte bir)
    FON    — short yalnız son 24 sa funding >= 0 iken (short ALIR);
             long yalnız funding <= 0 iken
    LS+FON — ikisi birden

İŞLEM: 00 UTC barının kapanışında karar, sonraki bar açılışında giriş,
H gün (1 ya da 3) sonra 00 UTC kapanışında çıkış; stop %25 (barın
H/L'si). Maliyet taker %0,05 x2 + gerçek funding. Evren: TradFi hariç,
hacim >= 20M$/gün, yaş >= 14 gün, metrik verisi olan semboller.
PORTFÖY: işlem başı 1/4, aynı anda en fazla 4 (kullanıcının %25'i).
Getiri kapanış barına yazılır (gün içi değerleme yok — düşüş sığ çıkar;
işlem başı sonuçlar etkilenmez).

ÖN KAYITLI ELEK (koşudan ÖNCE yazıldı; madde 379 ile aynı):
  net Sharpe 2022-24 VE 2025-26 >= 1,0; tam >= 1,5; aynı filtreyle
  RASTGELE zamanlı plaseboyu >= 0,5 geçer; carry ile rho <= 0,30.
  Ayrıca işlem başı ORTALAMA her iki dönemde > 0.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import arastirma_m379_haftalik_pump_short as Y  # noqa: E402

Y.NMAX = 4
RNG = np.random.default_rng(380)


def hazirla():
    C, O, H, L, F, uy = Y.yukle()
    Mt = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))
    LS = Mt["count_long_short_ratio"].reindex_like(C)
    uy = uy & LS.notna()
    lsr = np.log(LS.where(uy)).rank(axis=1, pct=True)
    f24 = F.rolling(6, min_periods=6).sum()
    r24 = C / C.shift(6) - 1
    sifir = pd.Series(C.index.hour == 0, index=C.index)
    return C, O, H, L, F, uy, lsr, f24, r24, sifir


def olay(r24, uy, lsr, f24, sifir, X, yon, filtre):
    k = uy & sifir.values[:, None]
    k = k & ((r24 >= X) if yon < 0 else (r24 <= -X))
    if "LS" in filtre:
        k = k & ((lsr >= 2 / 3) if yon < 0 else (lsr <= 1 / 3))
    if "FON" in filtre:
        k = k & ((f24 >= 0) if yon < 0 else (f24 <= 0))
    return k.fillna(False).values


def islem(kos, C, O, H, L, F, Hg, S, yon, plasebo=False, uygun=None):
    cv, ov, hv, lv, fv = C.values, O.values, H.values, L.values, F.values
    T, N = cv.shape
    hb = int(Hg * 6)
    out = []
    for j in range(N):
        ix = np.flatnonzero(kos[:, j])
        if plasebo:
            ad = np.flatnonzero(uygun[:, j]); ad = ad[ad < T - hb - 2]
            if len(ix) == 0 or len(ad) == 0:
                continue
            ix = np.sort(RNG.choice(ad, size=min(len(ix), len(ad)), replace=False))
        serbest = -1
        for i in ix:
            if i <= serbest or i + 1 >= T:
                continue
            g = ov[i + 1, j]
            if not np.isfinite(g) or g <= 0:
                continue
            son = min(i + 1 + hb, T - 1)
            ci, cf = son, cv[son, j]
            if S > 0:
                if yon < 0:
                    d = np.flatnonzero(hv[i + 1:son + 1, j] >= g * (1 + S))
                    if len(d): ci = i + 1 + d[0]; cf = g * (1 + S)
                else:
                    d = np.flatnonzero(lv[i + 1:son + 1, j] <= g * (1 - S))
                    if len(d): ci = i + 1 + d[0]; cf = g * (1 - S)
            if not np.isfinite(cf):
                continue
            fon = np.nansum(fv[i + 1:ci + 1, j])
            if yon < 0:
                r = (1 - cf / g) + fon            # short: fiyat düşerse kazanır, funding alır
            else:
                r = (cf / g - 1) - fon            # long: funding öder
            out.append((i + 1, ci, j, r - 2 * Y.KOM))
            serbest = ci
    return out


def main():
    C, O, H, L, F, uy, lsr, f24, r24, sifir = hazirla()
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    uygun0 = (uy & sifir.values[:, None]).values
    print(f"{'kol':<26} {'islem':>6} {'ort%':>6} {'o22':>6} {'o25':>6} {'med%':>6} {'kaz%':>5} "
          f"{'p1%':>7} {'yillik':>7} {'Sh':>5} {'Sh22':>5} {'Sh25':>5} {'dusus':>6} | {'PLA':>5} | elek")
    gecen = []
    kollar = [(yon, X, fl, Hg) for yon in (-1, +1) for X in (0.30, 0.40)
              for fl in ("yok", "LS", "FON", "LS+FON") for Hg in (1, 3)]
    for yon, X, fl, Hg in kollar:
        kos = olay(r24, uy, lsr, f24, sifir, X, yon, fl)
        isl = islem(kos, C, O, H, L, F, Hg, 0.25, yon)
        if len(isl) < 20:
            print(f"{('SHORT' if yon<0 else 'LONG')+f' {X:.0%} {fl} H{Hg}':<26} {len(isl):>6}  (az islem)")
            continue
        rr = np.array([x[3] for x in isl]); tt = np.array([C.index[x[0]] for x in isl])
        e22, e25 = rr[tt < pd.Timestamp("2025-01-01")], rr[tt >= pd.Timestamp("2025-01-01")]
        g = Y.portfoy(isl, C.index)
        pl = Y.portfoy(islem(kos, C, O, H, L, F, Hg, 0.25, yon, plasebo=True, uygun=uygun0), C.index)
        eq = (1 + g).cumprod(); yil = (eq.iloc[-1] ** (365.25 / len(g)) - 1) * 100
        dd = ((eq / eq.cummax()) - 1).min() * 100
        s22, s25 = Y.sh(g[g.index < "2025-01-01"]), Y.sh(g[g.index >= "2025-01-01"])
        ix = g.index.intersection(carry.index)
        rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
        el = [s22 >= 1.0 and s25 >= 1.0, Y.sh(g) >= 1.5, Y.sh(g) - Y.sh(pl) >= 0.5, rho <= 0.30,
              (len(e22) == 0 or e22.mean() > 0) and (len(e25) == 0 or e25.mean() > 0)]
        ad = f"{'SHORT' if yon<0 else 'LONG'} {X:.0%} {fl} H{Hg}"
        print(f"{ad:<26} {len(rr):>6} {rr.mean()*100:>+6.2f} {e22.mean()*100 if len(e22) else 0:>+6.2f} "
              f"{e25.mean()*100 if len(e25) else 0:>+6.2f} {np.median(rr)*100:>+6.2f} {(rr>0).mean()*100:>5.1f} "
              f"{np.percentile(rr,1)*100:>+7.1f} {yil:>+7.1f} {Y.sh(g):>5.2f} {s22:>5.2f} {s25:>5.2f} "
              f"{dd:>6.1f} | {Y.sh(pl):>5.2f} | {''.join('Y' if x else 'X' for x in el)}", flush=True)
        if all(el):
            gecen.append(ad)
    print("\nELEKTEN GECEN:", gecen or "YOK")


if __name__ == "__main__":
    main()
