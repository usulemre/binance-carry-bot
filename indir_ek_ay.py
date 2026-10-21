#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 412 — MEVCUT ZEMİNE YENİ AY(LAR) EKLE (artımlı, mevcut satırlara dokunmaz).

Kullanım: python3 indir_ek_ay.py 2026-09 [2026-10 ...]
  * data_genis/<S>_4h.csv ve data_taker_genis/<S>.csv : aylık 4h klines (aynı kolon dönüşümü)
  * data_funding_genis/<S>.csv : aylık fundingRate (date, funding, interval_h)
  * data_metrik/<S>.csv : günlük metrics (4 sa bara son değer)
Yalnız mevcut son tarihten SONRAKİ satırlar eklenir; yeni sembol eklenmez.
"""
import io
import os
import subprocess
import sys
import tempfile
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
B = "https://data.binance.vision/data/futures/um"
KOL = ["sum_open_interest_value", "count_toptrader_long_short_ratio",
       "sum_toptrader_long_short_ratio", "count_long_short_ratio",
       "sum_taker_long_short_vol_ratio"]


def cek(isler, gec):
    liste = os.path.join(gec, "u.txt")
    with open(liste, "w") as fh:
        for url, ad in isler:
            fh.write('url = "%s"\noutput = "%s/%s"\n' % (url, gec, ad))
    try:
        subprocess.run(["curl", "-sS", "-f", "--parallel", "--parallel-max", "10", "--max-time", "30",
                        "--retry", "1", "-K", liste], capture_output=True, timeout=240)
    except subprocess.TimeoutExpired:
        pass


def oku(z):
    if not os.path.exists(z) or os.path.getsize(z) < 100:
        return None
    try:
        with zipfile.ZipFile(z) as zz:
            raw = zz.read(zz.namelist()[0])
    except Exception:
        return None
    d = pd.read_csv(io.BytesIO(raw), header=None)
    if not str(d.iloc[0, 0]).lstrip("-").isdigit():
        d = pd.read_csv(io.BytesIO(raw))
        d.columns = range(d.shape[1]) if d.columns[0] != "create_time" else d.columns
    return d


def zaman(x):
    x = pd.to_numeric(x, errors="coerce")
    birim = "us" if x.dropna().gt(1e14).any() else "ms"
    return pd.to_datetime(x, unit=birim)


def ekle(yol, yeni, tarih_kol):
    if yeni is None or yeni.empty:
        return 0
    eski = pd.read_csv(yol)
    son = pd.to_datetime(eski[tarih_kol]).max()
    yeni = yeni[pd.to_datetime(yeni[tarih_kol]) > son]
    if yeni.empty:
        return 0
    yeni = yeni[eski.columns].copy()
    # MADDE 412 DÜZELTMESİ: tarih kolonu AÇIK biçimle yazılır. pandas, bir kolonun
    # tüm değerleri gece yarısıysa saati düşürür ("2026-09-01"); karışık biçim
    # okuyucuda tarihi metne çevirip sembolün TÜM geçmişini boşaltıyordu (480 sembol).
    if not pd.api.types.is_string_dtype(yeni[tarih_kol]):
        yeni[tarih_kol] = pd.to_datetime(yeni[tarih_kol]).dt.strftime("%Y-%m-%d %H:%M:%S")
    yeni.to_csv(yol, mode="a", header=False, index=False)
    return len(yeni)


def bir(s, aylar):
    gec = tempfile.mkdtemp(prefix="ek_%s_" % s)
    out = {}
    try:
        gunler = [d.strftime("%Y-%m-%d") for a in aylar for d in pd.date_range(a + "-01", pd.Period(a).end_time.normalize())]
        isler = [(f"{B}/monthly/klines/{s}/4h/{s}-4h-{a}.zip", f"k{a}.zip") for a in aylar]
        isler += [(f"{B}/monthly/fundingRate/{s}/{s}-fundingRate-{a}.zip", f"f{a}.zip") for a in aylar]
        if os.path.exists(os.path.join(R, "data_metrik", f"{s}.csv")):
            isler += [(f"{B}/daily/metrics/{s}/{s}-metrics-{g}.zip", f"m{g}.zip") for g in gunler]
        cek(isler, gec)
        # klines -> fiyat + taker
        ks = [oku(os.path.join(gec, f"k{a}.zip")) for a in aylar]
        ks = [k for k in ks if k is not None]
        if ks:
            ham = pd.concat(ks)
            df = ham.iloc[:, [0, 1, 2, 3, 4, 5, 7]].copy()
            df.columns = ["t", "open", "high", "low", "close", "volume", "quote_volume"]
            df["date"] = zaman(df.t)
            for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
            out["fiyat"] = ekle(os.path.join(R, "data_genis", f"{s}_4h.csv"), df, "date")
            dt = ham.iloc[:, [0, 7, 10]].copy(); dt.columns = ["t", "quote_volume", "tb_quote"]
            dt["date"] = zaman(dt.t)
            for c in ["quote_volume", "tb_quote"]:
                dt[c] = pd.to_numeric(dt[c], errors="coerce")
            dt = dt.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
            dt["tb_oran"] = dt.tb_quote / dt.quote_volume.replace(0, float("nan"))
            pt = os.path.join(R, "data_taker_genis", f"{s}.csv")
            if os.path.exists(pt):
                out["taker"] = ekle(pt, dt, "date")
        fs = [oku(os.path.join(gec, f"f{a}.zip")) for a in aylar]
        fs = [f for f in fs if f is not None]
        pf = os.path.join(R, "data_funding_genis", f"{s}.csv")
        if fs and os.path.exists(pf):
            d = pd.concat(fs).iloc[:, [0, 2, 1]].copy(); d.columns = ["t", "funding", "interval_h"]
            d["date"] = zaman(d.t)
            d["funding"] = pd.to_numeric(d["funding"], errors="coerce")
            d["interval_h"] = pd.to_numeric(d["interval_h"], errors="coerce").astype("Int64")
            d = d.dropna(subset=["date", "funding"]).drop_duplicates("date").sort_values("date")
            d["date"] = d["date"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]
            out["funding"] = ekle(pf, d, "date")
        pm = os.path.join(R, "data_metrik", f"{s}.csv")
        if os.path.exists(pm):
            parca = []
            for g in gunler:
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
                parca.append(x.sort_values("t").groupby("bar")[KOL].last())
            if parca:
                d = pd.concat(parca); d = d[~d.index.duplicated(keep="last")].sort_index().reset_index()
                # delist sonrası arşivdeki sıfır/boş satırlar (STORJ gibi) atılır
                d = d[d["count_long_short_ratio"].notna() & (d["sum_open_interest_value"] > 0)]
                out["metrik"] = ekle(pm, d, "bar")
        return s, out
    finally:
        shutil.rmtree(gec, ignore_errors=True)


if __name__ == "__main__":
    aylar = sys.argv[1:] or ["2026-09"]
    syms = sorted(f[:-7] for f in os.listdir(os.path.join(R, "data_genis")) if f.endswith("_4h.csv"))
    top = {"fiyat": 0, "taker": 0, "funding": 0, "metrik": 0}
    with ThreadPoolExecutor(6) as ex:
        for i, (s, o) in enumerate(ex.map(lambda x: bir(x, aylar), syms)):
            for k, v in o.items():
                top[k] += v
            if i % 100 == 0:
                print(i, s, o, flush=True)
    print("TOPLAM eklenen satir:", top, flush=True)
