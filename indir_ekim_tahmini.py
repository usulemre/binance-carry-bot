#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 413 — EKİM 2026 (1-20) VERİSİ: fiyat/taker/metrik günlük arşivden, FUNDING TAHMİNİ.

Arşivde Ekim fundingRate yok (ay bitince yayımlanır). Binance formülü:
    F = P_ort + clamp(I − P_ort, −%0,05, +%0,05)
    P_ort = ödeme aralığındaki prim endeksinin ortalaması, I = %0,01 x (aralık/8)
Prim endeksi 1 sa kline'larından (her saatin open/close ortalaması), sembolün son
bilinen ödeme aralığıyla (interval_h). Sonra sembolün üst/alt sınırı: geçmişte
gözlenen en büyük |F| ile kırpılır.
Mod:
    dogrula : Eylül 2026 için tahmin vs gerçek funding (korelasyon, sapma, toplam)
    ekle    : Ekim 1-20 klines/taker/metrik + tahmini funding'i data_* dosyalarına ekle
"""
import io
import os
import subprocess
import sys
import tempfile
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
B = "https://data.binance.vision/data/futures/um"
PD = os.path.join(R, "data_premium_ek")
GUN_EKIM = [d.strftime("%Y-%m-%d") for d in pd.date_range("2026-10-01", "2026-10-20")]
sys.path.insert(0, R)
import indir_ek_ay as E  # noqa: E402


def prim_indir(s):
    p = os.path.join(PD, f"{s}.csv")
    if os.path.exists(p):
        return
    gec = tempfile.mkdtemp(prefix="p_%s_" % s)
    try:
        isler = [(f"{B}/monthly/premiumIndexKlines/{s}/1h/{s}-1h-2026-08.zip", "m08.zip"),
                 (f"{B}/monthly/premiumIndexKlines/{s}/1h/{s}-1h-2026-09.zip", "m09.zip")]
        isler += [(f"{B}/daily/premiumIndexKlines/{s}/1h/{s}-1h-{g}.zip", f"d{g}.zip") for g in GUN_EKIM]
        E.cek(isler, gec)
        parca = []
        for ad in ["m08.zip", "m09.zip"] + [f"d{g}.zip" for g in GUN_EKIM]:
            d = E.oku(os.path.join(gec, ad))
            if d is None:
                continue
            d = d.iloc[:, [0, 1, 4]].copy(); d.columns = ["t", "o", "c"]
            d["t"] = E.zaman(d.t)
            for c in ("o", "c"):
                d[c] = pd.to_numeric(d[c], errors="coerce")
            parca.append(d)
        if parca:
            d = pd.concat(parca).dropna().drop_duplicates("t").sort_values("t")
            os.makedirs(PD, exist_ok=True)
            d.to_csv(p, index=False)
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def tahmin(s, bas, bit):
    """[bas, bit] arası ödeme anlarında tahmini funding serisi."""
    pp = os.path.join(PD, f"{s}.csv"); pf = os.path.join(R, "data_funding_genis", f"{s}.csv")
    if not (os.path.exists(pp) and os.path.exists(pf)):
        return None
    pr = pd.read_csv(pp, parse_dates=["t"]).set_index("t")
    pr = ((pr.o + pr.c) / 2)
    f = pd.read_csv(pf, parse_dates=["date"])
    f = f[f.date < pd.Timestamp(bas)]
    if f.empty:
        return None
    ih = int(f.interval_h.dropna().iloc[-1]) if "interval_h" in f and f.interval_h.notna().any() else 8
    tavan = max(f.funding.abs().quantile(0.999), 0.00375)
    zaman = pd.date_range(pd.Timestamp(bas), pd.Timestamp(bit), freq=f"{ih}h")
    zaman = zaman[zaman.hour % ih == 0]
    I = 0.0001 * ih / 8
    out = {}
    for t in zaman:
        w = pr[(pr.index >= t - pd.Timedelta(hours=ih)) & (pr.index < t)]
        if len(w) < max(1, ih // 2):
            continue
        p = float(w.mean())
        out[t] = float(np.clip(p + np.clip(I - p, -0.0005, 0.0005), -tavan, tavan))
    return pd.Series(out, dtype=float), ih


def dogrula(syms):
    rows = []
    for s in syms:
        x = tahmin(s, "2026-09-01", "2026-09-30 23:00")
        if x is None:
            continue
        t, ih = x
        g = pd.read_csv(os.path.join(R, "data_funding_genis", f"{s}.csv"), parse_dates=["date"])
        g = g[(g.date >= "2026-09-01") & (g.date < "2026-10-01")]
        g.index = g.date.dt.floor("h")
        g = g.funding.groupby(level=0).sum()
        ix = t.index.intersection(g.index)
        if len(ix) < 20:
            continue
        rows.append((s, ih, len(ix), float(np.corrcoef(t[ix], g[ix])[0, 1]) if g[ix].std() > 0 and t[ix].std() > 0 else np.nan,
                     float(g[ix].sum()), float(t[ix].sum())))
    D = pd.DataFrame(rows, columns=["s", "ih", "n", "kor", "gercek_ay", "tahmin_ay"])
    print(f"{len(D)} sembol | korelasyon medyan {D.kor.median():.3f} (p10 {D.kor.quantile(0.1):.3f}) | "
          f"aylik toplam: gercek-tahmin korelasyonu {np.corrcoef(D.gercek_ay, D.tahmin_ay)[0,1]:.3f}, "
          f"ort mutlak fark {np.abs(D.gercek_ay-D.tahmin_ay).mean()*100:.3f}% (ort |gercek| {D.gercek_ay.abs().mean()*100:.3f}%)")
    # kesitsel sıralama tutarlılığı (carry seçimi bunu kullanır)
    print(f"aylik toplam sira korelasyonu (Spearman): {D.gercek_ay.rank().corr(D.tahmin_ay.rank()):.3f}")
    return D


def ekle_ekim(s):
    out = {}
    gec = tempfile.mkdtemp(prefix="o_%s_" % s)
    try:
        isler = [(f"{B}/daily/klines/{s}/4h/{s}-4h-{g}.zip", f"k{g}.zip") for g in GUN_EKIM]
        if os.path.exists(os.path.join(R, "data_metrik", f"{s}.csv")):
            isler += [(f"{B}/daily/metrics/{s}/{s}-metrics-{g}.zip", f"m{g}.zip") for g in GUN_EKIM]
        E.cek(isler, gec)
        ks = [E.oku(os.path.join(gec, f"k{g}.zip")) for g in GUN_EKIM]
        ks = [k for k in ks if k is not None]
        if ks:
            ham = pd.concat(ks)
            df = ham.iloc[:, [0, 1, 2, 3, 4, 5, 7]].copy()
            df.columns = ["t", "open", "high", "low", "close", "volume", "quote_volume"]
            df["date"] = E.zaman(df.t)
            for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
            out["fiyat"] = E.ekle(os.path.join(R, "data_genis", f"{s}_4h.csv"), df, "date")
            dt = ham.iloc[:, [0, 7, 10]].copy(); dt.columns = ["t", "quote_volume", "tb_quote"]
            dt["date"] = E.zaman(dt.t)
            for c in ["quote_volume", "tb_quote"]:
                dt[c] = pd.to_numeric(dt[c], errors="coerce")
            dt = dt.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
            dt["tb_oran"] = dt.tb_quote / dt.quote_volume.replace(0, float("nan"))
            pt = os.path.join(R, "data_taker_genis", f"{s}.csv")
            if os.path.exists(pt):
                out["taker"] = E.ekle(pt, dt, "date")
        pm = os.path.join(R, "data_metrik", f"{s}.csv")
        if os.path.exists(pm):
            parca = []
            for g in GUN_EKIM:
                z = os.path.join(gec, f"m{g}.zip")
                if not os.path.exists(z) or os.path.getsize(z) < 200:
                    continue
                try:
                    with zipfile.ZipFile(z) as zz:
                        x = pd.read_csv(zz.open(zz.namelist()[0]))
                except Exception:
                    continue
                x["t"] = pd.to_datetime(x.create_time)
                x["bar"] = (x.t - pd.Timedelta(seconds=1)).dt.floor("4h")
                parca.append(x.sort_values("t").groupby("bar")[E.KOL].last())
            if parca:
                d = pd.concat(parca); d = d[~d.index.duplicated(keep="last")].sort_index().reset_index()
                d = d[d["count_long_short_ratio"].notna() & (d["sum_open_interest_value"] > 0)]
                out["metrik"] = E.ekle(pm, d, "bar")
        x = tahmin(s, "2026-10-01", "2026-10-20 20:00")
        pf = os.path.join(R, "data_funding_genis", f"{s}.csv")
        if x is not None and len(x[0]) and out.get("fiyat", 0) > 0:
            t, ih = x
            d = pd.DataFrame({"date": t.index.strftime("%Y-%m-%d %H:%M:%S.000"), "funding": t.values,
                              "interval_h": ih})
            out["funding_tahmin"] = E.ekle(pf, d, "date")
        return s, out
    finally:
        shutil.rmtree(gec, ignore_errors=True)


if __name__ == "__main__":
    mod = sys.argv[1]
    syms = sorted(f[:-7] for f in os.listdir(os.path.join(R, "data_genis")) if f.endswith("_4h.csv"))
    if mod == "prim":
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(prim_indir, syms))
        print("prim:", len(os.listdir(PD)))
    elif mod == "dogrula":
        dogrula(syms)
    elif mod == "ekle":
        top = {}
        with ThreadPoolExecutor(6) as ex:
            for s, o in ex.map(ekle_ekim, syms):
                for k, v in o.items():
                    top[k] = top.get(k, 0) + v
        print("TOPLAM:", top)
