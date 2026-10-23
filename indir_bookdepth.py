#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 477 veri: Binance USDⓈ-M günlük bookDepth (data.binance.vision, ~30 sn'lik derinlik anlık görüntüleri,
±%1..±%5 seviyeleri, notional USDT). Liste: 'SEMBOL YYYY-MM-DD' satırları. Her dosya bellekte açılır, 4 saatlik
barlara (ortalama notional, seviye başına) indirgenir; ham dosya diske yazılmaz. Çıktı: tek pickle (uzun tablo)."""
import io, sys, zipfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd, requests

LISTE, CIKTI = sys.argv[1], sys.argv[2]
URL = "https://data.binance.vision/data/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{g}.zip"
ses = threading.local()

def al(sem, gun):
    if not hasattr(ses, "s"): ses.s = requests.Session()
    for _ in range(3):
        try:
            r = ses.s.get(URL.format(s=sem, g=gun), timeout=60)
            if r.status_code == 404: return None
            r.raise_for_status(); break
        except Exception:
            continue
    else:
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        d = pd.read_csv(z.open(z.namelist()[0]))
    except Exception:
        return None
    if d.empty or "percentage" not in d: return None
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d["bar"] = d["timestamp"].dt.floor("4h")
    p = d.pivot_table(index="bar", columns="percentage", values="notional", aggfunc="mean")
    p.columns = [f"n{int(round(float(c))):+d}" for c in p.columns]
    p = p.T.groupby(level=0).mean().T            # yinelenen seviye adlarını birleştir
    p["sembol"] = sem
    return p.reset_index()

satir = [l.split() for l in open(LISTE).read().split("\n") if l.strip()]
out = []; n = 0
with ThreadPoolExecutor(24) as ex:
    fs = [ex.submit(al, s, g) for s, g in satir]
    for f in as_completed(fs):
        n += 1
        x = f.result()
        if x is not None: out.append(x)
        if n % 2000 == 0:
            print(f"{n}/{len(satir)} dolu {len(out)}", flush=True)
            pd.concat(out).to_pickle(CIKTI)
pd.concat(out).to_pickle(CIKTI)
print("bitti", n, len(out), flush=True)
