#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 478 veri: COIN-M (ters sözleşme, XXXUSD_PERP) ve USDⓈ-M (XXXUSDT) aylık fundingRate dosyaları,
aynı coin için (data.binance.vision). Çıktı /tmp/cm/funding.pkl: uzun tablo (zaman, coin, pazar, oran)."""
import io, zipfile, sys
from concurrent.futures import ThreadPoolExecutor
import pandas as pd, requests, re

B = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
def anahtarlar(prefix):
    out, mk = [], ""
    while True:
        for _ in range(4):
            try:
                t = requests.get(B, params={"prefix": prefix, "marker": mk}, timeout=60).text; break
            except Exception:
                t = ""
        k = re.findall(r"<Key>([^<]+\.zip)</Key>", t); out += k
        if "<IsTruncated>true" not in t or not k: return out
        mk = k[-1]

def al(key):
    for _ in range(4):
        try:
            r = requests.get("https://data.binance.vision/" + key, timeout=60); break
        except Exception:
            r = None
    if r is None or r.status_code != 200: return None
    z = zipfile.ZipFile(io.BytesIO(r.content)); d = pd.read_csv(z.open(z.namelist()[0]))
    return d

cm = [x for x in re.findall(r"<Prefix>[^<]*/fundingRate/([^/<]+)/</Prefix>",
      requests.get(B, params={"prefix": "data/futures/cm/monthly/fundingRate/", "delimiter": "/"}, timeout=60).text)]
isler = []
for s in cm:
    coin = s.replace("USD_PERP", "")
    for pz, sem in (("cm", s), ("um", coin + "USDT")):
        for k in anahtarlar(f"data/futures/{pz}/monthly/fundingRate/{sem}/"):
            isler.append((coin, pz, k))
print(len(cm), "coin,", len(isler), "dosya", flush=True)
satir = []
with ThreadPoolExecutor(16) as ex:
    for (coin, pz, k), d in zip(isler, ex.map(lambda a: al(a[2]), isler)):
        if d is None or d.empty: continue
        d.columns = [c.lower() for c in d.columns]
        tc = [c for c in d.columns if "time" in c][0]; rc = [c for c in d.columns if "rate" in c and "interval" not in c][0]
        satir.append(pd.DataFrame({"zaman": pd.to_datetime(d[tc], unit="ms"), "coin": coin, "pazar": pz, "oran": d[rc].astype(float)}))
pd.concat(satir, ignore_index=True).to_pickle("/tmp/cm/funding.pkl"); print("bitti", flush=True)
