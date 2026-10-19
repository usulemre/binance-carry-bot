#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 353 — PROJEDE HİÇ DENENMEMİŞ ÜÇ STRATEJİ AİLESİ, ÖN ELEME.

Sicilde olmayanlar (grep: "kointegr", "lead-lag", "haftanın günü",
"listeleme sonrası" 0 kayıt; yeni listelemeler yalnız CARRY havuzu
olarak denendi, madde 202):

  A. YENİ LİSTELEME SHORT'U — perp listelendikten D0 gün sonra short,
     H gün tut. Fiyat yönlü (carry değil). Varyant: BTC long ile hedge.
  B. BTC ÖNCÜ-TAKİPÇİ — skor = beta_i * r_BTC(t) - r_i(t) ("BTC'nin
     hareketine henüz yetişmemiş kısım"), kesitsel üst/alt %10, nötr.
  C. HAFTALIK MEVSİMSELLİK — eşit ağırlıklı alt endeksi, haftanın
     günü x 4 saatlik dilim; işaret YALNIZ 2022-24'ten öğrenilir,
     2025-26'da sınanır.

MALİYET: işlem başına KOM_TAKER = %0,05 (muhafazakâr; kitap maker %0,02
kullanıyor) + gerçek funding (ODE paneli: long öder, short alır).
Gecikme: sinyal t barında, işlem t+1 barının getirisinde.

ÖN KAYITLI ELEK (madde 289'un şartnamesinden; koşudan ÖNCE yazıldı):
  Bir aday bir sonraki tura (motor + harman + bootstrap) geçer, ancak:
    (1) net Sharpe 2022-24'te VE 2025-26'da >= 1,0,
    (2) tam dönem net Sharpe >= 1,5,
    (3) plasebosunu tam dönemde en az 0,5 Sharpe geçer,
    (4) carry kitabıyla (K_2000) günlük getiri korelasyonu <= +0,30.
  Madde 289: harmana değer katmak için tek başına ~2,5 ve rho <= 0
  gerekir; bu elek o barın ALTINDA tutuldu ki aday erkenden ölmesin —
  geçen aday harman turunda asıl bara karşı ölçülür.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)

KOM = 0.0005
BAR_YIL = 6 * 365.25
RNG = np.random.default_rng(353)


def yukle():
    z = pickle.load(open("/tmp/zemin.pkl", "rb"))
    P = pickle.load(open("/tmp/panel.pkl", "rb"))
    C, ODE = z["C"], z["ODE"].reindex_like(z["C"]).fillna(0.0)
    R = C.pct_change(fill_method=None)
    R = R.where(R.abs() < 2.0)            # bozuk barlar (madde 27'nin sınıfı)
    return C, R, ODE, P["HAC"]


def gunluk(rbar):
    r = pd.Series(rbar).fillna(0.0)
    g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index)
    return g


def sh(g):
    g = np.asarray(g, float)
    return float(g.mean() / g.std() * np.sqrt(365.25)) if g.std() > 0 else np.nan


def ozet(g, ad, carry=None):
    e, l = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
    eq = (1 + g).cumprod()
    yil = eq.iloc[-1] ** (365.25 / len(g)) - 1
    dd = (eq / eq.cummax() - 1).min()
    rho = np.nan
    if carry is not None:
        ix = g.index.intersection(carry.index)
        rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
    return dict(ad=ad, yil=yil * 100, sh=sh(g), sh22=sh(e), sh25=sh(l),
                dd=dd * 100, rho=rho)


# ------------------------------------------------------------------ A
def strateji_A(C, R, ODE, HAC, D0=1, H=14, MAXN=10, hedge=False, plasebo=False,
               hacim_min=2e7):
    """Her yeni listelemeyi D0 gün sonra short'la, H gün tut.
    Pozisyon ağırlığı 1/MAXN; aynı anda MAXN'den fazlaysa ölçeklenir (brüt <= 1)."""
    ilk = C.apply(lambda s: s.first_valid_index())
    ilk = ilk[ilk > C.index[0] + pd.Timedelta(days=14)]
    idx = C.index
    W = pd.DataFrame(0.0, index=idx, columns=C.columns)
    for s, t0 in ilk.items():
        i0 = idx.get_loc(t0) + int(D0 * 6)
        if plasebo:                       # aynı sembol, rastgele (listeleme sonrası) zaman
            son = C[s].last_valid_index()
            j = idx.get_loc(son) - int(H * 6) - 1
            if j <= i0:
                continue
            i0 = int(RNG.integers(i0, j))
        i1 = min(i0 + int(H * 6), len(idx) - 1)
        if i0 >= len(idx) - 1:
            continue
        if not (HAC[s].iloc[i0] >= hacim_min):
            continue
        W.iloc[i0 + 1:i1 + 1, W.columns.get_loc(s)] = -1.0 / MAXN
    brut = W.abs().sum(axis=1)
    W = W.div(np.maximum(brut, 1.0), axis=0)
    if hedge:
        W["BTCUSDT"] = W["BTCUSDT"] + W.abs().sum(axis=1)
    Wl = W.shift(1).fillna(0.0)           # karar t, getiri t+1
    fiyat = (Wl * R.fillna(0.0)).sum(axis=1)
    fund = -(Wl * ODE).sum(axis=1)        # long öder, short alır
    maliyet = Wl.diff().abs().sum(axis=1).fillna(0.0) * KOM
    return fiyat + fund - maliyet, W


# ------------------------------------------------------------------ B
def strateji_B(C, R, ODE, HAC, TUT=1, PAY=0.10, plasebo=False, hacim_min=1e8):
    rb = R["BTCUSDT"]
    var_b = rb.rolling(180, min_periods=120).var()
    beta = R.apply(lambda x: x.rolling(180, min_periods=120).cov(rb)).div(var_b, axis=0)
    skor = beta.mul(rb, axis=0) - R               # BTC'ye henüz yetişilmemiş kısım
    skor = skor.where(HAC >= hacim_min)
    skor = skor.drop(columns=["BTCUSDT"])
    if plasebo:
        v = skor.values.copy()
        for i in range(v.shape[0]):
            m = np.isfinite(v[i]); v[i, m] = RNG.permutation(v[i, m])
        skor = pd.DataFrame(v, index=skor.index, columns=skor.columns)
    rk = skor.rank(axis=1, pct=True)
    n = skor.notna().sum(axis=1)
    W = (rk >= 1 - PAY).astype(float).sub((rk <= PAY).astype(float))
    W = W.where(n >= 20, 0.0)
    W = W.div(W.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    if TUT > 1:                            # her TUT barda bir yeniden kur
        W = W.iloc[::TUT].reindex(W.index).ffill()
    W = W.reindex(columns=C.columns, fill_value=0.0)
    Wl = W.shift(1).fillna(0.0)
    fiyat = (Wl * R.fillna(0.0)).sum(axis=1)
    fund = -(Wl * ODE).sum(axis=1)
    maliyet = Wl.diff().abs().sum(axis=1).fillna(0.0) * KOM
    return fiyat + fund - maliyet, W


# ------------------------------------------------------------------ C
def strateji_C(C, R, ODE, HAC, plasebo=False, hacim_min=1e8):
    m = R.where(HAC >= hacim_min).mean(axis=1)     # eşit ağırlıklı likit endeks
    f = ODE.where(HAC >= hacim_min).mean(axis=1)
    hucre = m.index.dayofweek * 6 + m.index.hour // 4
    ogren = m.index < "2025-01-01"
    ort = m[ogren].groupby(hucre[ogren]).mean()
    isaret = np.sign(ort)
    if plasebo:
        isaret = pd.Series(RNG.permutation(isaret.values), index=isaret.index)
    w = pd.Series(hucre, index=m.index).map(isaret).fillna(0.0)
    wl = w.shift(1).fillna(0.0)                    # karar bir önceki bar, getiri bu bar
    # not: hücre işareti bilinen bir takvimdir; shift yalnız icra gecikmesi
    w_bu = w                                       # o hücrede tutulan yön
    fiyat = w_bu * m
    fund = -w_bu * f
    maliyet = w_bu.diff().abs().fillna(0.0) * KOM
    return fiyat + fund - maliyet, None


def main():
    C, R, ODE, HAC = yukle()
    import arastirma_m346_prim as M
    carry = M.gunluk("K_2000_0")
    satir = []

    for D0 in (1, 3):
        for H in (7, 14, 30):
            for hedge in (False, True):
                ad = f"A D0={D0} H={H}{' +BTC' if hedge else ''}"
                r, _ = strateji_A(C, R, ODE, HAC, D0=D0, H=H, hedge=hedge)
                rp, _ = strateji_A(C, R, ODE, HAC, D0=D0, H=H, hedge=hedge, plasebo=True)
                satir.append((ozet(gunluk(r), ad, carry), ozet(gunluk(rp), ad + " PLA", carry)))
    for TUT in (1, 6):
        ad = f"B tut={TUT}bar"
        r, _ = strateji_B(C, R, ODE, HAC, TUT=TUT)
        rp, _ = strateji_B(C, R, ODE, HAC, TUT=TUT, plasebo=True)
        satir.append((ozet(gunluk(r), ad, carry), ozet(gunluk(rp), ad + " PLA", carry)))
    r, _ = strateji_C(C, R, ODE, HAC)
    rp, _ = strateji_C(C, R, ODE, HAC, plasebo=True)
    satir.append((ozet(gunluk(r), "C hafta x saat", carry), ozet(gunluk(rp), "C PLA", carry)))

    print(f"{'aday':<22} {'yillik':>8} {'Sh':>6} {'Sh22':>6} {'Sh25':>6} {'dusus':>7} "
          f"{'rho':>6} | {'PLA Sh':>6} | elek")
    gecen = []
    for a, p in satir:
        e = [a["sh22"] >= 1.0 and a["sh25"] >= 1.0, a["sh"] >= 1.5,
             a["sh"] - p["sh"] >= 0.5, a["rho"] <= 0.30]
        isa = "".join("Y" if x else "X" for x in e)
        print(f"{a['ad']:<22} {a['yil']:>+8.1f} {a['sh']:>6.2f} {a['sh22']:>6.2f} "
              f"{a['sh25']:>6.2f} {a['dd']:>7.1f} {a['rho']:>+6.2f} | {p['sh']:>6.2f} | {isa}")
        if all(e):
            gecen.append(a["ad"])
    print("\nELEKTEN GECEN:", gecen or "YOK")
    pickle.dump(satir, open("/tmp/m346/m353_sonuc.pkl", "wb"))


if __name__ == "__main__":
    main()
