"""TAM EVREN funding indirici — carry kitabının evrenini 183'ten ~800'e çıkarır.

NEDEN: carry stratejisi 30+30 bacağı 183 sembolden seçiyor. Evren 4x
büyürse hem daha yüksek funding veren bacaklar seçilebilir hem de
çeşitlendirme artar. Bu, ana kitabın en doğrudan kâr kaldıracı.

data_funding_genis/<SEM>.csv  -> date, funding
data_premium_genis/<SEM>.csv  -> date, premium (4h kapanış)
"""
import concurrent.futures as cf
import io
import os
import sys
import urllib.request
import zipfile

import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
AYLAR = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)]
AYLAR = [a for a in AYLAR if a <= "2026-08"]
BF = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
BP = "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines"


def cek(url):
    try:
        b = urllib.request.urlopen(url, timeout=45).read()
        z = zipfile.ZipFile(io.BytesIO(b))
        t = z.read(z.namelist()[0]).decode()
        return [l.split(",") for l in t.splitlines()
                if l and not l[0].isalpha()]
    except Exception:
        return []


def zaman(seri):
    v = pd.to_numeric(seri, errors="coerce")
    return pd.to_datetime(v.where(v < 1e14, v / 1000), unit="ms")


def funding(s):
    p = os.path.join(R, "data_funding_genis", f"{s}.csv")
    if os.path.exists(p):
        return
    rows = []
    with cf.ThreadPoolExecutor(14) as ex:
        for r in ex.map(lambda a: cek(f"{BF}/{s}/{s}-fundingRate-{a}.zip"), AYLAR):
            rows += r
    if len(rows) < 30:
        return
    d = pd.DataFrame(rows).iloc[:, [0, 2]]
    d.columns = ["t", "funding"]
    d["date"] = zaman(d["t"])
    d["funding"] = pd.to_numeric(d["funding"], errors="coerce")
    d = d.dropna().drop_duplicates("date").sort_values("date")
    d[["date", "funding"]].to_csv(p, index=False)


def premium(s):
    p = os.path.join(R, "data_premium_genis", f"{s}.csv")
    if os.path.exists(p):
        return
    rows = []
    with cf.ThreadPoolExecutor(14) as ex:
        for r in ex.map(lambda a: cek(f"{BP}/{s}/4h/{s}-4h-{a}.zip"), AYLAR):
            rows += r
    if len(rows) < 30:
        return
    d = pd.DataFrame(rows).iloc[:, [0, 4]]
    d.columns = ["t", "premium"]
    d["date"] = zaman(d["t"])
    d["premium"] = pd.to_numeric(d["premium"], errors="coerce")
    d = d.dropna().drop_duplicates("date").sort_values("date")
    d[["date", "premium"]].to_csv(p, index=False)


if __name__ == "__main__":
    os.makedirs(os.path.join(R, "data_funding_genis"), exist_ok=True)
    os.makedirs(os.path.join(R, "data_premium_genis"), exist_ok=True)
    syms = [x.strip() for x in open("/tmp/tum_semboller.txt") if x.strip()]
    a, b = int(sys.argv[1]), int(sys.argv[2])
    ne = sys.argv[3] if len(sys.argv) > 3 else "both"
    for s in syms[a:b]:
        if ne in ("both", "funding"):
            funding(s)
        if ne in ("both", "premium"):
            premium(s)
    print(f"[{a}:{b}] bitti", flush=True)
