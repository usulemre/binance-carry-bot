#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 395 — TOPLU OLAY TARAMASI: 10 YENİ OLAY x 3 TUTMA SÜRESİ.

ÖN KAYIT (koşudan ÖNCE):
  * Günlük panel (00 UTC), TradFi hariç, hacim >= 20M$, yaş >= 30 gün.
  * Giriş olay gününün kapanışı, H gün tut (H = 1, 3, 7); getiri yönlü,
    gerçek funding dahil, 10 bp maliyet. Aynı coinde açık işlem varken
    yeni olay alınmaz.
  * SEÇİM yalnız IS (2022-04..2024-12): olay x H içinde IS t'si en yüksek
    3 kol. OOS (2025-01..2026-08) bu 3 kolda raporlanır.
  * KABUL (harman turuna): OOS ort > 0, OOS t >= 2,0, OOS n >= 100 VE
    portföy (işlem başı 1/10, en fazla 10 açık) OOS Sharpe >= 1,0.
OLAYLAR (yön):
  E1 TAVAN−   8 sa eşdeğeri funding <= −%0,30 (short kalabalık tavanda) → LONG
  E2 TAVAN+   funding >= +%0,10 (long kalabalık uçta) → SHORT
  E3 TESLİM   3 g funding ort >= +%0,03 iken son gün funding < 0 (long teslimiyeti) → LONG
  E4 SESSİZ   hacim / 30 g ort >= 4 VE |1 g getiri| <= %3 (sessiz birikim) → LONG
  E5 LSZIP    long hesap oranı 1 günde >= %40 arttı (perakende akını) → SHORT
  E6 ZİRVE    kapanış 180 günlük zirvenin üstünde (kırılım) → LONG
  E7 DİP      kapanış 180 günlük dibin altında (çöküş) → SHORT
  E8 GÜÇ      BTC 1 günde <= −%7 iken coin 1 g getirisi en iyi %10 içinde → LONG
  E9 TÜKENİŞ  taker alış oranı 3 gün üst üste kesitsel üst %5 → SHORT
  E10 OIKAÇ   OI 1 günde >= %25 düştü VE fiyat 1 günde <= −%10 (tasfiye sonrası) → LONG
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
MAL = 0.0010


def panel():
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); P = pickle.load(open("/tmp/panel.pkl", "rb"))
    Mt = pickle.load(open("/tmp/metrik_panel.pkl", "rb"))
    C4 = z["C"]; F4 = z["ODE"].reindex_like(C4).fillna(0.0)
    sec = C4.index.hour == 0
    C = C4[sec]
    Fd = F4.groupby(F4.index.floor("D")).sum().reindex(C.index.floor("D") - pd.Timedelta(days=1)).fillna(0.0)
    Fd.index = C.index
    from tradfi_liste import TRADFI
    HAC = P["HAC"].reindex_like(C4)[sec]; YAS = P["YAS"].reindex_like(C4)[sec]
    uy = (HAC >= 2e7) & (YAS >= 30 * 6) & C.notna()
    uy = uy & ~uy.columns.isin(list(TRADFI))
    m = {k: Mt[k].reindex_like(C4)[sec] for k in ("count_long_short_ratio", "sum_taker_long_short_vol_ratio",
                                                  "sum_open_interest_value")}
    return C, Fd, HAC, uy, m


def olaylar(C, Fd, HAC, uy, m):
    r1 = C / C.shift(1) - 1
    ar = 1.0                                   # Fd günlük toplam; 8 sa eşdeğeri = Fd / 3
    f8 = Fd / 3
    E = {}
    E["E1_TAVAN-"] = (f8 <= -0.003, +1)
    E["E2_TAVAN+"] = (f8 >= 0.001, -1)
    E["E3_TESLIM"] = ((f8.shift(1).rolling(3).mean() >= 0.0003) & (f8 < 0), +1)
    E["E4_SESSIZ"] = ((HAC / HAC.rolling(30).mean() >= 4) & (r1.abs() <= 0.03), +1)
    ls = m["count_long_short_ratio"]
    E["E5_LSZIP"] = (ls / ls.shift(1) - 1 >= 0.40, -1)
    E["E6_ZIRVE"] = (C > C.shift(1).rolling(180, min_periods=150).max(), +1)
    E["E7_DIP"] = (C < C.shift(1).rolling(180, min_periods=150).min(), -1)
    b = r1["BTCUSDT"]
    E["E8_GUC"] = ((b <= -0.07).values[:, None] & (r1.where(uy).rank(axis=1, pct=True) >= 0.9), +1)
    tk = m["sum_taker_long_short_vol_ratio"].where(uy).rank(axis=1, pct=True) >= 0.95
    E["E9_TUKENIS"] = (tk & tk.shift(1, fill_value=False) & tk.shift(2, fill_value=False), -1)
    oi = m["sum_open_interest_value"]
    E["E10_OIKAC"] = ((oi / oi.shift(1) - 1 <= -0.25) & (r1 <= -0.10), +1)
    return {k: (pd.DataFrame(v, index=C.index, columns=C.columns).fillna(False).astype(bool) & uy, d)
            for k, (v, d) in E.items()}


def islemler(kos, d, C, Fd, H):
    cv, fv = C.values, Fd.values
    T, N = cv.shape
    out = []
    for j in range(N):
        serbest = -1
        for i in np.flatnonzero(kos.values[:, j]):
            if i <= serbest or i + H >= T:
                continue
            g, c = cv[i, j], cv[i + H, j]
            if not (np.isfinite(g) and np.isfinite(c) and g > 0):
                continue
            fon = np.nansum(fv[i + 1:i + H + 1, j])
            r = d * (c / g - 1) - d * fon - MAL if d > 0 else (1 - c / g) + fon - MAL
            out.append((i, i + H, max(r, -1.0)))
            serbest = i + H
    return out


def portfoy(isl, idx, nmax=10):
    # DÜZELTME (ilk koşu): sorted(isl) aynı gün olayları GETİRİYE göre diziyordu ->
    # kalabalık günlerde en KÖTÜ nmax işlem seçiliyordu. Aynı gün içinde rastgele sıra.
    rng = np.random.default_rng(395)
    acik, r = [], np.zeros(len(idx))
    isl = [isl[k] for k in rng.permutation(len(isl))]
    for a, b, x in sorted(isl, key=lambda q: q[0]):
        acik = [c for c in acik if c > a]
        if len(acik) >= nmax:
            continue
        acik.append(b); r[b] += x / nmax
    return pd.Series(r, index=idx)


def main():
    C, Fd, HAC, uy, m = panel()
    E = olaylar(C, Fd, HAC, uy, m)
    sinir = C.index.get_indexer([pd.Timestamp("2025-01-01")], method="bfill")[0]
    bas = C.index.get_indexer([pd.Timestamp("2022-04-01")], method="bfill")[0]
    sat = []
    print(f"{'kol':<16} {'nIS':>5} {'ortIS%':>7} {'tIS':>6} | {'nOOS':>5} {'ortOOS%':>8} {'medOOS%':>8} {'tOOS':>6} {'ShOOS':>6}")
    for ad, (kos, d) in E.items():
        for H in (1, 3, 7):
            isl = [x for x in islemler(kos, d, C, Fd, H) if x[0] >= bas]
            a = np.array([x[2] for x in isl if x[0] < sinir]); b = np.array([x[2] for x in isl if x[0] >= sinir])
            t = lambda v: v.mean() / v.std() * np.sqrt(len(v)) if len(v) > 2 and v.std() > 0 else np.nan
            g = portfoy(isl, C.index); go = g[g.index >= "2025-01-01"]
            sho = go.mean() / go.std() * np.sqrt(365.25) if go.std() > 0 else np.nan
            sat.append(dict(ad=f"{ad} H{H}", nI=len(a), oI=a.mean() * 100 if len(a) else np.nan, tI=t(a),
                            nO=len(b), oO=b.mean() * 100 if len(b) else np.nan,
                            mO=np.median(b) * 100 if len(b) else np.nan, tO=t(b), shO=sho))
            r = sat[-1]
            print(f"{r['ad']:<16} {r['nI']:>5} {r['oI']:>+7.2f} {r['tI']:>+6.2f} | {r['nO']:>5} {r['oO']:>+8.2f} "
                  f"{r['mO']:>+8.2f} {r['tO']:>+6.2f} {r['shO']:>+6.2f}", flush=True)
    S = pd.DataFrame(sat)
    sec = S[S.nI >= 50].sort_values("tI", ascending=False).head(3)
    print("\nIS'TE SECILEN 3 KOL (OOS'a hic bakilmadan):")
    for _, r in sec.iterrows():
        kabul = r.oO > 0 and r.tO >= 2.0 and r.nO >= 100 and r.shO >= 1.0
        print(f"  {r.ad:<16} IS t {r.tI:+.2f} -> OOS n {r.nO} ort %{r.oO:+.2f} t {r.tO:+.2f} Sh {r.shO:+.2f} -> "
              f"{'HARMAN TURUNA' if kabul else 'RED'}")


if __name__ == "__main__":
    main()
