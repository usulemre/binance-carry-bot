#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 809 — CoinGecko'dan dolaşan arz (piyasa değeri / fiyat), 365 g. Ham veri /tmp/m809/ham (güvenilmeyen veri; yalnız JSON okunur)."""
import json, os, pickle, time, urllib.request
OUT = "/tmp/m809/ham"; os.makedirs(OUT, exist_ok=True)
def al(url, dosya):
    yol = f"{OUT}/{dosya}"
    if os.path.exists(yol): return json.load(open(yol))
    for dene in range(6):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
            json.dump(d, open(yol, "w")); time.sleep(2.5); return d
        except Exception as e:
            time.sleep(20 * (dene + 1))
    return None
pazar = []
for s in range(1, 5):
    pazar += al(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page={s}", f"markets_{s}.json") or []
z = pickle.load(open("/tmp/zemin.pkl", "rb")); ev = {c.replace("USDT", "").replace("1000", "") for c in z["C"].columns}
idm = {}
for p in pazar:
    s = p["symbol"].upper()
    if s in ev and s not in idm: idm[s] = p["id"]
print("eşleşen", len(idm), flush=True)
json.dump(idm, open(f"{OUT}/idmap.json", "w"))
for i, (s, cid) in enumerate(sorted(idm.items())):
    d = al(f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=365&interval=daily", f"mc_{s}.json")
    if i % 25 == 0: print(i, s, "ok" if d else "YOK", flush=True)
print("bitti")
