"""CARRY — GENIS EVREN (847 sembol, delist edilmisler DAHIL).

FARK: `carry_backtest.py` 183 sembolle calisiyor ve `dropna(how='any')`
ile tum donem boyunca YASAYAN sembollere indirgiyor. Bu iki yanlilik
demek:
  1. hayatta kalma yanliligi (delist olanlar hic yok)
  2. kapsam eksikligi (yeni listelemeler hic yok)

Bu modul data_genis/ + data_funding_genis/ kullanir, sembolun
listelendigi barda evrene girer, delist oldugu barda cikar. Bacaklar
her rebalance'ta O ANDA yasayan semboller arasindan secilir - yani
gelecek bilgisi yok.

Kullanim:
    python carry_genis.py --n-legs 30 --rebalance 30 --all-phases
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
KOM = 0.0006      # tek yon: %0.04 komisyon + %0.02 kayma


def panel_yukle(fiyat_dir="data_genis", funding_dir="data_funding_genis",
                min_bar=180):
    """Fiyat ve funding panelleri. NaN = sembol o anda yok (henuz
    listelenmemis ya da delist olmus). dropna YOK."""
    cl, fu, iv, hc = {}, {}, {}, {}
    for yol in sorted(glob.glob(os.path.join(R, fiyat_dir, "*_4h.csv"))):
        s = os.path.basename(yol).replace("_4h.csv", "")
        fy = os.path.join(R, funding_dir, f"{s}.csv")
        if not os.path.exists(fy):
            continue
        try:
            d = pd.read_csv(yol, parse_dates=["date"]).set_index("date")
            f = pd.read_csv(fy, parse_dates=["date"])
        except Exception:
            continue
        if len(d) < min_bar or len(f) < 20:
            continue
        cl[s] = d["close"]
        hc[s] = d["quote_volume"]
        f["date"] = f["date"].dt.floor("h")
        f = f.drop_duplicates("date").set_index("date").sort_index()
        fu[s] = f["funding"]
        # odeme araligi: ardisik funding damgalarinin ORTANCASI (saat).
        # 4 saatte bir odeyen sembolde yillik oran 2 KATIDIR (madde 114).
        d_h = f.index.to_series().diff().dt.total_seconds().div(3600)
        iv[s] = float(d_h.median()) if d_h.notna().any() else 8.0

    C = pd.DataFrame(cl).sort_index()
    C = C[C.index.year >= 2022]

    # DONUK SERI FILTRESI: ileri doldurulmus/islem gormeyen barlar
    # backtest'i yapay iyilestirir. Sadece sembolun YASADIGI aralikta bak.
    iyi = []
    for s in C.columns:
        c = C[s].dropna()
        if len(c) < min_bar:
            continue
        if (c.diff() == 0).mean() < 0.10:
            iyi.append(s)
    C = C[iyi]

    ham = pd.DataFrame({s: fu[s] for s in iyi}).sort_index()
    IV = pd.Series({s: iv[s] for s in iyi})

    # ODEME paneli: o barda GERCEKTEN odenen funding, her odeme tam bir kez
    ODEME = ham.reindex(ham.index.union(C.index)).reindex(C.index).fillna(0.0)
    dis = ham.index.difference(C.index)
    if len(dis):
        kova = pd.Series(C.index.searchsorted(dis, side="right") - 1, index=dis)
        ek = ham.loc[dis].groupby(kova.values).sum()
        ek = ek[ek.index >= 0]
        if len(ek):
            ODEME.iloc[ek.index] += ek.reindex(columns=ODEME.columns).fillna(0).values

    # SINYAL: YILLIKLASTIRILMIS oran (gunluk esdeger), ham oranla siralamak
    # 4 saatlik odeyenleri sistematik olarak kacirir.
    SINYAL = (ham.reindex(ham.index.union(C.index)).ffill(limit=4)
              .reindex(C.index).mul(24.0 / IV, axis=1))
    # sembol yasamiyorken sinyal de yok
    SINYAL = SINYAL.where(C.notna())
    ODEME = ODEME.where(C.notna(), 0.0)

    # UYGUNLUK panelleri: canli botun da bakabilecegi iki olcut.
    # HACIM: son 24 saatlik islem hacmi (6 bar toplami)
    # YAS  : listelemeden bu yana gecen bar sayisi
    HACIM = pd.DataFrame({s: hc[s] for s in iyi}).reindex(C.index).rolling(6).sum()
    YAS = C.notna().cumsum().where(C.notna())
    return C, SINYAL, ODEME, HACIM, YAS


def bt(C, ODEME, skor, n, reb, lag=1, bas=1200, vol_hedef=None,
       vol_pencere=180, min_bacak=None, uygun=None):
    """skor DUSUK olan long, YUKSEK olan short. Piyasa notr.

    Her rebalance'ta sadece O BARDA yasayan semboller aday."""
    cv = C.values
    fv = ODEME.values
    idx, kol = C.index, C.columns
    poz = np.zeros(len(kol))
    eq, tar, bek = [1.0], [idx[bas]], None
    fk = 0.0
    min_bacak = min_bacak or n
    UY = None if uygun is None else uygun.values
    for i in range(bas, len(C) - 1):
        if bek is not None and bek[0] == i:
            y = bek[1]
            eq[-1] *= (1 - np.abs(y - poz).sum() * KOM)
            poz, bek = y, None
        if (i - bas) % reb == 0:
            s = skor.iloc[i]
            # HAYATTA OLMA: fiyat hem bu barda hem sonraki barda var olmali
            g = (s.notna().values & np.isfinite(cv[i]) & np.isfinite(cv[i + 1]))
            if UY is not None:
                g = g & UY[i]
            m = int(g.sum())
            nn = min(n, m // 2)
            if nn >= min_bacak:
                sv = np.where(g, s.values, np.nan)
                sira = np.argsort(np.where(np.isnan(sv), np.inf, sv))
                L, S = sira[:nn], sira[m - nn:m]
                y = np.zeros(len(kol))
                y[L] = 0.5 / nn
                y[S] = -0.5 / nn
                if vol_hedef is not None and len(eq) > vol_pencere + 20:
                    _g = np.diff(eq[-vol_pencere:]) / np.array(eq[-vol_pencere:-1])
                    _s = np.nanstd(_g) * np.sqrt(365.25 * 6)
                    if _s > 1e-6:
                        y = y * float(np.clip(vol_hedef / _s, 0.3, 3.0))
                bek = (i + lag, y)
        br = np.where(np.isfinite(cv[i]) & np.isfinite(cv[i + 1]),
                      (cv[i + 1] - cv[i]) / np.where(cv[i] == 0, np.nan, cv[i]), 0.0)
        ret = float(np.nansum(poz * np.nan_to_num(br)))
        f = np.nan_to_num(fv[i + 1])
        fnd = float(np.nansum(-poz * f)) if f.any() else 0.0
        fk += fnd
        eq.append(eq[-1] * (1 + ret + fnd))
        tar.append(idx[i + 1])
    e = pd.Series(eq, index=tar)
    gun = max((e.index[-1] - e.index[0]).days, 1)
    yl = (max(e.iloc[-1], 1e-9) ** (365.25 / gun) - 1) * 100
    g = e.pct_change().dropna()
    sh = g.mean() / g.std() * np.sqrt(365.25 * 6) if g.std() > 0 else 0.0
    dd = ((e / e.cummax()) - 1).min() * 100
    return e, yl, sh, dd, fk * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-legs", type=int, default=30)
    ap.add_argument("--funding-window", type=int, default=18)
    ap.add_argument("--rebalance", type=int, default=30)
    ap.add_argument("--vol-hedef", type=float, default=0.0)
    ap.add_argument("--all-phases", action="store_true")
    a = ap.parse_args()

    C, FU, ODEME = panel_yukle()
    print(f"panel: {C.shape[1]} sembol x {len(C)} bar  "
          f"({C.index[0].date()} -> {C.index[-1].date()})")
    canli = C.notna().sum(axis=1)
    print(f"es zamanli yasayan sembol: ortanca {int(canli.median())}, "
          f"son {int(canli.iloc[-1])}\n")

    sk = FU.rolling(a.funding_window, min_periods=max(2, a.funding_window // 3)).mean()
    fazlar = (range(0, a.rebalance, max(1, a.rebalance // 5))
              if a.all_phases else [0])
    rs = []
    for f in fazlar:
        e, yl, sh, dd, fk = bt(C, ODEME, sk, a.n_legs, a.rebalance, bas=1200 + f,
                               vol_hedef=(a.vol_hedef or None))
        rs.append((yl, sh, dd, fk))
        if a.all_phases:
            print(f"  faz {f:>2}: yillik {yl:>+7.1f}%  Sharpe {sh:>5.2f}  "
                  f"dusus {dd:>6.1f}%  funding {fk:>+7.1f}%")
    o = np.mean(rs, axis=0)
    print(f"\nORTALAMA: yillik {o[0]:+.1f}%  Sharpe {o[1]:.2f}  "
          f"dusus {o[2]:.1f}%  funding katkisi {o[3]:+.1f}%")


if __name__ == "__main__":
    main()
