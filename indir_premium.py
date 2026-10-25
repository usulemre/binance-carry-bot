#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 550 veri: Binance USDⓈ-M aylık premiumIndexKlines 1h (data.binance.vision). Prim = (mark − endeks)/endeks; funding'in
ana bileşeni. Her ay bellekte açılır, 4 saatlik barın kapanış primi ve bar ortalaması alınır. Çıktı: tek pickle (uzun tablo).
Kullanım: python3 indir_premium.py <sembol_listesi> <ilk_ay YYYY-MM> <son_ay YYYY-MM> <cikti.pkl>"""
import io, sys, zipfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd, requests

LISTE, ILK, SON, CIKTI = sys.argv[1:5]
URL = "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/{s}/1h/{s}-1h-{a}.zip"
ses = threading.local()
AD = ["acilis_t", "acilis", "yuksek", "dusuk", "kapanis", "hacim", "kapanis_t", "q", "n", "a", "b", "c"]


def al(sem, ay):
    if not hasattr(ses, "s"): ses.s = requests.Session()
    for _ in range(4):
        try:
            r = ses.s.get(URL.format(s=sem, a=ay), timeout=60)
            if r.status_code == 404: return None
            r.raise_for_status(); break
        except Exception:
            continue
    else:
        return ("HATA", sem, ay)
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        d = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(d.iloc[0, 0]).isdigit(): d = d.iloc[1:]
        d.columns = AD[:d.shape[1]]
    except Exception:
        return ("HATA", sem, ay)
    t = pd.to_datetime(pd.to_numeric(d["acilis_t"]), unit="ms")
    x = pd.DataFrame({"t": t, "p": pd.to_numeric(d["kapanis"])})
    x["bar"] = x["t"].dt.floor("4h")
    g = x.groupby("bar").p.agg(["last", "mean"]).reset_index()
    g["sembol"] = sem
    return g


semler = [l.strip() for l in open(LISTE) if l.strip()]
aylar = [str(p) for p in pd.period_range(ILK, SON, freq="M")]
is_ = [(s, a) for s in semler for a in aylar]
out = []; hata = []; n = 0
with ThreadPoolExecutor(24) as ex:
    fs = [ex.submit(al, s, a) for s, a in is_]
    for f in as_completed(fs):
        n += 1; x = f.result()
        if isinstance(x, tuple): hata.append(x[1:])
        elif x is not None: out.append(x)
        if n % 3000 == 0:
            print(f"{n}/{len(is_)} dolu {len(out)} hata {len(hata)}", flush=True)
pd.concat(out).to_pickle(CIKTI)
open(CIKTI + ".hata", "w").write("\n".join(f"{s} {a}" for s, a in hata))
print("bitti", n, len(out), "hata", len(hata), flush=True)
