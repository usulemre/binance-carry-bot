#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 676 — MEXC funding geçmişi -> Binance sinyal ızgarasına oturan MEXC sinyali (aynı formül: pencere ort. × 24/aralık).
  python3 arastirma_m676_mexc_funding.py indir      -> data_mexc_funding/<BINANCE_SEMBOL>.csv
  python3 arastirma_m676_mexc_funding.py panel 60 / 96 -> /tmp/skm_bar60.pkl (MEXC), harman / onay panelleri
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, pickle

R = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(R, "data_mexc_funding")
API = "https://contract.mexc.com/api/v1/contract"


def get(u):
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "m676"}), timeout=30).read())
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def eslesme(binance: list, mexc: set) -> dict:
    out = {}
    for s in binance:
        b = s[:-4]
        for on in ("", "1000000", "10000", "1000"):
            if b.startswith(on) and on:
                b2 = b[len(on):]
            elif not on:
                b2 = b
            else:
                continue
            for aday in (f"{b}_USDT", f"{b2}_USDT"):
                if aday in mexc:
                    out[s] = aday; break
            if s in out:
                break
    return out


def bir(ikili):
    s, m = ikili
    yol = os.path.join(D, f"{s}.csv")
    if os.path.exists(yol) and not os.getenv("M676_TAZELE"):    # M676_TAZELE=1: yeni ayları almak için baştan indir
        return s, -1
    rows, p = [], 1
    while True:
        d = get(f"{API}/funding_rate/history?symbol={m}&page_num={p}&page_size=1000")
        if not d or not d.get("success"):
            break
        r = d["data"]["resultList"]; rows += r
        if p >= d["data"]["totalPage"] or not r:
            break
        p += 1
        time.sleep(0.15)
    if rows:
        f = pd.DataFrame(rows)
        f["date"] = pd.to_datetime(f.settleTime, unit="ms")
        f = f.rename(columns={"fundingRate": "funding", "collectCycle": "interval_h"})[["date", "funding", "interval_h"]]
        f.sort_values("date").drop_duplicates("date").to_csv(yol, index=False)
    return s, len(rows)


def indir():
    os.makedirs(D, exist_ok=True)
    mexc = {x["symbol"] for x in get(f"{API}/detail")["data"] if x["symbol"].endswith("_USDT")}
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
    akt = [c for c in C.columns if C[c].iloc[-6:].notna().any()]
    es = eslesme(akt, mexc)
    print(f"Binance aktif {len(akt)} · MEXC'te eşleşen {len(es)}", flush=True)
    n = 0
    with ThreadPoolExecutor(4) as ex:
        for s, k in ex.map(bir, es.items()):
            n += 1
            if n % 100 == 0:
                print(n, s, k, flush=True)


def panel(pen: float):
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]; kol = list(C.columns)
    bar_h = C.index.values.astype("datetime64[s]").astype(np.int64) / 3600.0
    out = np.full((len(bar_h), len(kol)), np.nan)
    for j, s in enumerate(kol):
        y = os.path.join(D, f"{s}.csv")
        if not os.path.exists(y):
            continue
        f = pd.read_csv(y, parse_dates=["date"]); f["date"] = f["date"].dt.floor("h")
        f = f.drop_duplicates("date").sort_values("date")
        if len(f) < 3:
            continue
        t = f["date"].values.astype("datetime64[s]").astype(np.int64) / 3600.0
        r = (f["funding"] * 24.0 / f["interval_h"].clip(lower=1)).values.astype(float)   # günlük eşdeğer, ödeme başına
        cs = np.concatenate([[0.0], np.cumsum(r)])
        hi = np.searchsorted(t, bar_h, side="right"); lo = np.searchsorted(t, bar_h - pen, side="right")
        ok = (hi > lo) & (bar_h >= t[0] + pen)          # tam pencere dolmadan sinyal yok
        out[ok, j] = (cs[hi[ok]] - cs[lo[ok]]) / (hi[ok] - lo[ok])
    M = pd.DataFrame(out, index=C.index, columns=kol).where(C.notna())
    ad = f"bar{int(pen)}"
    B = pickle.load(open(f"/tmp/sk_{ad}.pkl", "rb"))
    pickle.dump(M, open(f"/tmp/skm_{ad}.pkl", "wb"))
    var = M.notna()
    onay = B.where(~var | (np.sign(M) == np.sign(B)) | (B == 0), 0.0)        # V1
    harman = B.where(~var, 0.5 * B + 0.5 * M)                                   # V2
    ozel = B.where(~var, B + 0.5 * (B - M))                                     # V3 (madde 677 ön kayıt): yalnız-Binance primi büyütülür
    pickle.dump(onay, open(f"/tmp/sk_{ad}_onay.pkl", "wb")); pickle.dump(harman, open(f"/tmp/sk_{ad}_harman.pkl", "wb"))
    pickle.dump(ozel, open(f"/tmp/sk_{ad}_ozel.pkl", "wb"))
    son = C.index >= "2025-06-01"
    kor = []
    for i in np.where(son)[0][::30]:
        a, b = B.iloc[i], M.iloc[i]; m = a.notna() & b.notna()
        if m.sum() > 30:
            kor.append(a[m].rank().corr(b[m].rank()))
    deg = ((onay != B) & var).values[son].sum(); hucre = (var.values[son] & B.notna().values[son]).sum()
    print(f"{ad}: MEXC hücre (2025-06+) {hucre} · kesitsel sıra kor. ort {np.nanmean(kor):+.3f} · V1'in sıfırladığı hücre %{100*deg/max(hucre,1):.1f}")


if __name__ == "__main__":
    if sys.argv[1] == "indir":
        indir()
    else:
        panel(float(sys.argv[2]))
