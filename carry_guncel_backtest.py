"""CANLI AYARIN BACKTEST'İ — madde 140-142 sonuçlarını yeniden üretir.

Canlı botla aynı yapı:
  - evren: hacim >= $100M, yaş >= 90 gün, donuk seri yok, TradFi HARİÇ
  - skor : %80 funding sırası + %20 emir akışı sırası (carry_bot.birlesik_skor)
  - n+n bacak, 5 günlük tutma, 5 dilim eşzamanlı (N_DILIM=5)
  - maliyet %0.06 tek yön, kaldıraçsız

Kullanım:
    python carry_guncel_backtest.py --n 12          # canlı ayar
    python carry_guncel_backtest.py --n 6 --n 8     # birden fazla bacak sayısı
    python carry_guncel_backtest.py --n 12 --tradfi-dahil

Gerekenler: data_genis/, data_funding_genis/, data_taker_genis/
(indirme komutları NEREDE_NE_VAR.md içinde). İlk çalıştırmada panel
kurulur (~20-60 sn), sonra .cache_panel.pkl'den okunur.
"""
from __future__ import annotations

import argparse
import glob
import os
import pickle
import warnings

import numpy as np
import pandas as pd

import carry_denetim as D
from carry_bot import _TRADFI_YEDEK

warnings.filterwarnings("ignore")
R = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(R, ".cache_panel.pkl")
KOM = 0.0006
AKIS = 0.20


def panel():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    C, SIN, ODE, HAC, YAS, DON = D.panel_yukle_temiz()
    uy = D.uygunluk(C, HAC, YAS, DON)
    sk = SIN.rolling(D.FUNDING_PENCERE, min_periods=6).mean()
    tb, qv = {}, {}
    for p in glob.glob(os.path.join(R, "data_taker_genis", "*.csv")):
        s = os.path.basename(p)[:-4]
        if s in C.columns:
            d = pd.read_csv(p, parse_dates=["date"]).set_index("date")
            tb[s], qv[s] = d["tb_oran"], d["quote_volume"]
    TB = pd.DataFrame(tb).reindex(index=C.index, columns=C.columns)
    QV = pd.DataFrame(qv).reindex(index=C.index, columns=C.columns)
    # canlı formülle birebir: (5g alıcı payı - 0.5) x (5g hacim / 30g hacim)
    AK = ((TB.rolling(30, min_periods=20).mean() - 0.5)
          * (QV.rolling(30, min_periods=20).mean()
             / QV.rolling(180, min_periods=120).mean()))
    P = dict(C=C, ODE=ODE, sk=sk, uy=uy, AK=AK)
    pickle.dump(P, open(CACHE, "wb"))
    return P


def bt(P, uy, bas, msk, n):
    C, ODE, sk, AK = P["C"], P["ODE"], P["sk"], P["AK"]
    cv, fv = C[msk].values, ODE[msk].values
    U, S, A, idx = uy[msk].values, sk[msk].values, AK[msk].values, C[msk].index
    nk = C.shape[1]
    poz, eq, bek = np.zeros(nk), [1.0], None
    for i in range(bas, len(idx) - 1):
        if bek is not None and bek[0] == i:
            y = bek[1]
            eq[-1] *= 1 - np.abs(y - poz).sum() * KOM
            poz, bek = y, None
        if (i - bas) % 30 == 0:
            g = np.isfinite(S[i]) & np.isfinite(cv[i]) & U[i]
            ix = np.flatnonzero(g)
            nn = min(n, len(ix) // 2)
            if nn >= min(8, n):
                sc = pd.Series(S[i][ix]).rank(pct=True).values
                a = pd.Series(A[i][ix])
                if a.notna().sum() >= 0.5 * len(ix):
                    sc = (1 - AKIS) * sc + AKIS * (-a).rank(pct=True).fillna(0.5).values
                o = np.argsort(sc)
                y = np.zeros(nk)
                y[ix[o[:nn]]] = 0.5 / nn
                y[ix[o[-nn:]]] = -0.5 / nn
                bek = (i + 1, y)
        br = np.where(np.isfinite(cv[i]) & np.isfinite(cv[i + 1]),
                      (cv[i + 1] - cv[i]) / np.where(cv[i] == 0, np.nan, cv[i]), 0.0)
        eq.append(eq[-1] * (1 + np.nansum(poz * np.nan_to_num(br))
                            + np.nansum(-poz * np.nan_to_num(fv[i + 1]))))
    return pd.Series(eq, index=idx[bas:])


def dilimli(P, uy, msk, b0, n):
    g = pd.concat([bt(P, uy, b0 + f, msk, n).pct_change() for f in range(0, 30, 6)],
                  axis=1).mean(axis=1).dropna()
    return (1 + g).cumprod()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, action="append", help="bacak sayısı (tekrar edilebilir)")
    ap.add_argument("--tradfi-dahil", action="store_true")
    a = ap.parse_args()
    P = panel()
    C, uy = P["C"], P["uy"].copy()
    if not a.tradfi_dahil:
        uy[[c for c in uy.columns if c in _TRADFI_YEDEK]] = False
    donemler = [("TÜM", C.index >= "2022-01-01", 1200),
                ("EĞİTİM 22-24", (C.index >= "2022-01-01") & (C.index < "2025-01-01"), 1200),
                ("TEST 25-26", C.index >= "2025-01-01", 100)]
    for n in (a.n or [12]):
        print(f"\n=== {n}+{n} bacak | TradFi {'DAHİL' if a.tradfi_dahil else 'hariç'} ===")
        for ad, msk, b0 in donemler:
            e = dilimli(P, uy, msk, b0, n)
            o = D.ozet(e)
            ay = e.resample("ME").last().pct_change().dropna()
            hf = e.resample("W").last().pct_change().dropna()
            print(f"  {ad:<13} yıllık {o['yillik']:+6.1f}%  Sharpe {o['sharpe']:4.2f}  "
                  f"düşüş {o['maxdd']:6.1f}%  | ay: orta {ay.median()*100:+.2f}% "
                  f"en iyi {ay.max()*100:+.1f}% en kötü {ay.min()*100:+.1f}% artıda %{(ay>0).mean()*100:.0f}"
                  f"  | hafta: orta {hf.median()*100:+.2f}% en kötü {hf.min()*100:+.1f}%")


if __name__ == "__main__":
    main()
