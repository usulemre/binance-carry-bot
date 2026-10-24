#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 497 veri: 2020-01 → 2021-12 USDⓈ-M 4 sa kline + funding (data.binance.vision, delist edilenler dahil).

Motorun zemini 2022-01'de başlıyor (ısınma sonrası ölçüm 2022-07'den). Adaylar (T2, short ara dengelemesi) yalnız
~4 yılda ölçüldü ve 2025-26'ya yaslanıyor; 2020-21 (boğa çılgınlığı + 2021 ortası çöküş) bağımsız bir sınav.
Çıktı: data_genis_uzun/<S>_4h.csv, data_funding_uzun/<S>.csv, data_taker_uzun/<S>.csv — 2020-21 + mevcut 2022+ birleşik.
Kullanım: python3 indir_uzun_gecmis.py
"""
import concurrent.futures as cf, io, os, re, zipfile
import pandas as pd, requests

R = os.path.dirname(os.path.abspath(__file__))
AYLAR = [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)]
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
V = "https://data.binance.vision/"

def get(url, n=4):
    for _ in range(n):
        try:
            r = requests.get(url, timeout=60)
            return r if r.status_code == 200 else None
        except Exception:
            pass
    return None

def semboller():
    out, mk = [], ""
    while True:
        t = requests.get(S3, params={"prefix": "data/futures/um/monthly/klines/", "delimiter": "/", "marker": mk}, timeout=60).text
        p = re.findall(r"<Prefix>data/futures/um/monthly/klines/([^/<]+)/</Prefix>", t); out += p
        if "<IsTruncated>true" not in t or not p: return [s for s in out if s.endswith("USDT")]
        mk = "data/futures/um/monthly/klines/" + p[-1] + "/"

def zip_satir(r):
    z = zipfile.ZipFile(io.BytesIO(r.content)); t = z.read(z.namelist()[0]).decode()
    return [l.split(",") for l in t.splitlines() if l and not l[0].isalpha()]

def zaman(v):
    v = pd.to_numeric(v, errors="coerce"); return pd.to_datetime(v.where(v < 1e14, v / 1000), unit="ms")

def sembol(s):
    kl, fu = [], []
    for a in AYLAR:
        r = get(f"{V}data/futures/um/monthly/klines/{s}/4h/{s}-4h-{a}.zip")
        if r is not None: kl += zip_satir(r)
        r = get(f"{V}data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{a}.zip")
        if r is not None: fu += zip_satir(r)
    if len(kl) < 60: return s, 0, 0
    d = pd.DataFrame(kl).iloc[:, [0, 1, 2, 3, 4, 5, 7, 10]]
    d.columns = ["t", "open", "high", "low", "close", "volume", "quote_volume", "tb_quote"]
    d["date"] = zaman(d.t)
    for c in d.columns[1:8]: d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
    eski = os.path.join(R, "data_genis", f"{s}_4h.csv")
    k = d[["date", "open", "high", "low", "close", "volume", "quote_volume"]]
    if os.path.exists(eski): k = pd.concat([k, pd.read_csv(eski, parse_dates=["date"])])
    k.drop_duplicates("date").sort_values("date").to_csv(os.path.join(R, "data_genis_uzun", f"{s}_4h.csv"), index=False)
    tk = d[["date", "quote_volume", "tb_quote"]].copy(); tk["tb_oran"] = tk.tb_quote / tk.quote_volume
    eski = os.path.join(R, "data_taker_genis", f"{s}.csv")
    if os.path.exists(eski): tk = pd.concat([tk, pd.read_csv(eski, parse_dates=["date"])])
    tk.drop_duplicates("date").sort_values("date").to_csv(os.path.join(R, "data_taker_uzun", f"{s}.csv"), index=False)
    if len(fu) >= 3:
        f = pd.DataFrame(fu).iloc[:, [0, 2]]; f.columns = ["t", "funding"]; f["date"] = zaman(f.t)
        f["funding"] = pd.to_numeric(f.funding, errors="coerce"); f = f.dropna()[["date", "funding"]]
        eski = os.path.join(R, "data_funding_genis", f"{s}.csv")
        if os.path.exists(eski): f = pd.concat([f, pd.read_csv(eski, parse_dates=["date"])[["date", "funding"]]])
        f.drop_duplicates("date").sort_values("date").to_csv(os.path.join(R, "data_funding_uzun", f"{s}.csv"), index=False)
    return s, len(kl), len(fu)

if __name__ == "__main__":
    for d in ("data_genis_uzun", "data_funding_uzun", "data_taker_uzun"): os.makedirs(os.path.join(R, d), exist_ok=True)
    S = semboller(); print(len(S), "sembol", flush=True)
    n = 0
    with cf.ThreadPoolExecutor(16) as ex:
        for s, a, b in ex.map(sembol, S):
            n += a > 0
    print("2020-21 verisi olan sembol:", n, flush=True)
    # 2020-21 verisi olmayan semboller: mevcut 2022+ dosyaları aynen kopyala (evren eksiksiz kalsın)
    import shutil, glob
    for p in glob.glob(os.path.join(R, "data_genis", "*_4h.csv")):
        q = os.path.join(R, "data_genis_uzun", os.path.basename(p))
        if not os.path.exists(q): shutil.copy(p, q)
    for src, dst in (("data_funding_genis", "data_funding_uzun"), ("data_taker_genis", "data_taker_uzun")):
        for p in glob.glob(os.path.join(R, src, "*.csv")):
            q = os.path.join(R, dst, os.path.basename(p))
            if not os.path.exists(q): shutil.copy(p, q)
    print("bitti", flush=True)
