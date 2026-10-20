#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 367 — BTC ÖNCÜ-TAKİPÇİ, 5 DAKİKALIK VERİDE.

Madde 353-B: 4 saatlik panelde sinyal VAR (plasebo −3,92 vs −2,50
Sharpe) ama maliyet yutuyordu. Bu etki dakika ölçeğinde yaşar. Veri:
`indir_5m.sh` (en likit 100 sembol, TradFi ve 2023-12 sonrası listelenen
hariç, 2024-01 .. 2026-08).

SİNYAL (nedensel): son K barda
    açık_i = beta_i * r_BTC(K) - r_i(K)
beta_i: son 288 bar (1 gün) 5 dk getirilerle, bir bar gecikmeli.
Açığı en büyük %10 LONG (BTC'ye henüz yetişmemiş), en küçük %10 SHORT.
Eşit ağırlık, brüt 1, piyasa nötr. Her H barda yeniden kurulur; karar
t barının kapanışında, getiri t+1'den itibaren.

MALİYET: devir × komisyon. İki senaryo: taker %0,05/taraf, maker
%0,02/taraf. Funding hesaba katılmaz (tutma <= 1 saat; ödeme anına
denk gelme payı ihmal edilebilir — bu bir YAKLAŞIM, not edildi).
PLASEBO: açık her barda kesitsel karıştırılır (makine aynı).

ÖN KAYITLI ELEK (koşudan ÖNCE yazıldı) — maker senaryosunda, NET:
  (1) 2024'te VE 2025-26'da Sharpe >= 1,0
  (2) tam dönem Sharpe >= 2,0  (madde 289'un barına yakın; harmanda
      işe yaraması için ~2,5 gerekir)
  (3) plaseboyu en az 1,0 Sharpe geçer
  (4) carry kitabıyla günlük korelasyon <= +0,30
Taker senaryosu bilgi içindir: canlıda dakika ölçeğinde maker dolum
garantisi yok (madde 213'ün ters seçilimi), o yüzden taker'da da pozitif
olmayan bir aday "maker'a bağımlı" diye işaretlenir.
"""
import glob
import io
import os
import pickle
import sys
import zipfile

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
VERI = os.path.join(KOK, "data_5m")
PANEL = "/tmp/m346/panel_5m.pkl"
BAR_YIL = 288 * 365.25
RNG = np.random.default_rng(367)
KOM = {"maker": 0.0002, "taker": 0.0005}


def panel_kur():
    if os.path.exists(PANEL):
        return pickle.load(open(PANEL, "rb"))
    kap = {}
    for f in sorted(glob.glob(os.path.join(VERI, "*-5m-*.zip"))):
        s = os.path.basename(f).split("-5m-")[0]
        try:
            with zipfile.ZipFile(f) as z:
                raw = z.read(z.namelist()[0]).decode()
        except (zipfile.BadZipFile, IndexError):
            continue
        d = pd.read_csv(io.StringIO(raw), header=None, usecols=[0, 4],
                        names=["t", "c"], low_memory=False)
        d = d[pd.to_numeric(d["t"], errors="coerce").notna()]      # başlık satırı
        t = pd.to_numeric(d["t"]).astype("int64")
        t = np.where(t > 1e14, t // 1000, t)                         # µs -> ms
        kap.setdefault(s, []).append(pd.Series(pd.to_numeric(d["c"]).values,
                                               index=pd.to_datetime(t, unit="ms")))
    C = pd.DataFrame({s: pd.concat(v).sort_index().pipe(lambda x: x[~x.index.duplicated()])
                      for s, v in kap.items()})
    C = C.asfreq("5min")
    pickle.dump(C, open(PANEL, "wb"))
    return C


def strateji(R, K, H, plasebo=False, pay=0.10):
    rb = R["BTCUSDT"]
    var_b = rb.rolling(288, min_periods=200).var()
    cov = R.apply(lambda x: x.rolling(288, min_periods=200).cov(rb))
    beta = cov.div(var_b, axis=0).shift(1)
    rK = R.rolling(K, min_periods=K).sum()          # log-yaklaşık K bar getirisi
    acik = beta.mul(rK["BTCUSDT"], axis=0) - rK
    acik = acik.drop(columns=["BTCUSDT"])
    if plasebo:
        v = acik.values.copy()
        for i in range(v.shape[0]):
            m = np.isfinite(v[i]); v[i, m] = RNG.permutation(v[i, m])
        acik = pd.DataFrame(v, index=acik.index, columns=acik.columns)
    rk = acik.rank(axis=1, pct=True)
    n = acik.notna().sum(axis=1)
    W = (rk >= 1 - pay).astype(float) - (rk <= pay).astype(float)
    W = W.where(n >= 30, 0.0)
    W = W.div(W.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    if H > 1:
        W = W.iloc[::H].reindex(W.index).ffill().fillna(0.0)
    Wl = W.shift(1).fillna(0.0)                     # karar t, getiri t+1
    brut = (Wl * R.drop(columns=["BTCUSDT"]).fillna(0.0)).sum(axis=1)
    devir = Wl.diff().abs().sum(axis=1).fillna(0.0)
    return brut, devir


def gunluk(r):
    g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index)
    return g


def sh(g):
    g = np.asarray(g, float)
    return float(g.mean() / g.std() * np.sqrt(365.25)) if g.std() > 0 else np.nan


def ozet(g):
    e = (1 + g).cumprod()
    return dict(yil=(e.iloc[-1] ** (365.25 / len(g)) - 1) * 100, sh=sh(g),
                sh24=sh(g[g.index < "2025-01-01"]), sh25=sh(g[g.index >= "2025-01-01"]),
                dd=((e / e.cummax()) - 1).min() * 100)


def main():
    C = panel_kur()
    print(f"panel: {C.shape[1]} sembol, {len(C)} bar ({C.index[0]} .. {C.index[-1]})")
    R = C.pct_change(fill_method=None)
    R = R.where(R.abs() < 0.5)
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    print(f"{'kol':<10} {'senaryo':<6} {'yillik':>8} {'Sh':>6} {'Sh24':>6} {'Sh25':>6} "
          f"{'dusus':>7} {'devir/gun':>9} {'rho':>6} | {'PLA Sh':>6} | elek")
    gecen = []
    for K in (1, 3):
        for H in (1, 3, 12):
            brut, devir = strateji(R, K, H)
            bp, dp = strateji(R, K, H, plasebo=True)
            gb = gunluk(brut)
            print(f"{'K'+str(K)+' H'+str(H):<10} {'brut':<6} {ozet(gb)['yil']:>+8.1f} "
                  f"{sh(gb):>6.2f}   (maliyetsiz — sinyalin varlığı)")
            for sen, kom in KOM.items():
                g = gunluk(brut - devir * kom); gp = gunluk(bp - dp * kom)
                o, op = ozet(g), ozet(gp)
                ix = g.index.intersection(carry.index)
                rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
                dg = float(devir.groupby(devir.index.date).sum().mean())
                e = [o["sh24"] >= 1.0 and o["sh25"] >= 1.0, o["sh"] >= 2.0,
                     o["sh"] - op["sh"] >= 1.0, rho <= 0.30]
                isa = "".join("Y" if x else "X" for x in e)
                print(f"{'':<10} {sen:<6} {o['yil']:>+8.1f} {o['sh']:>6.2f} {o['sh24']:>6.2f} "
                      f"{o['sh25']:>6.2f} {o['dd']:>7.1f} {dg:>9.1f} {rho:>+6.2f} | "
                      f"{op['sh']:>6.2f} | {isa}")
                if sen == "maker" and all(e):
                    gecen.append(f"K{K} H{H}")
    print("\nELEKTEN GECEN (maker):", gecen or "YOK")


if __name__ == "__main__":
    main()
