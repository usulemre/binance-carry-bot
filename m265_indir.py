#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Madde 265: 1 DAKİKALIK kline indirici (data.binance.vision arşivi).

fapi.binance.com bu bölgeden 451 veriyor; genel arşiv erişilebilir.
Anahtar GEREKMEZ, yalnızca kamuya açık dosyalar.
"""
import io
import os
import sys
import urllib.request
import zipfile

import pandas as pd

HEDEF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_1m")
AYLAR = ("2026-07", "2026-08")
KOL = ["open_time", "open", "high", "low", "close", "volume", "close_time",
       "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]


def indir(sembol: str, ay: str) -> pd.DataFrame | None:
    u = ("https://data.binance.vision/data/futures/um/monthly/klines/"
         f"{sembol}/1m/{sembol}-1m-{ay}.zip")
    try:
        ham = urllib.request.urlopen(u, timeout=90).read()
    except Exception as e:
        print("  ATLA %s %s: %s" % (sembol, ay, str(e)[:60]), flush=True)
        return None
    with zipfile.ZipFile(io.BytesIO(ham)) as z:
        ad = z.namelist()[0]
        with z.open(ad) as fh:
            d = pd.read_csv(fh, header=None, names=KOL)
    if str(d.iloc[0, 0]).lower().startswith("open"):
        d = d.iloc[1:]
    for c in ("open_time", "open", "high", "low", "close", "quote_volume"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[["open_time", "open", "high", "low", "close", "quote_volume"]].dropna()


def main() -> int:
    os.makedirs(HEDEF, exist_ok=True)
    semboller = [s.strip() for s in open("/tmp/m265_semboller.txt")
                 if s.strip()]
    print("%d sembol x %d ay" % (len(semboller), len(AYLAR)), flush=True)
    for s in semboller:
        yol = os.path.join(HEDEF, s + "_1m.csv")
        if os.path.exists(yol):
            print("  var %s" % s, flush=True)
            continue
        parca = [d for ay in AYLAR if (d := indir(s, ay)) is not None]
        if not parca:
            continue
        d = pd.concat(parca).drop_duplicates("open_time").sort_values("open_time")
        d.to_csv(yol, index=False)
        print("  %s: %d bar" % (s, len(d)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
