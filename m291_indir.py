#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 291: dakika verisini 2 aydan REJIM KARSITI aylara genislet.

Madde 265/266/267 projenin UC icra varsayimini dakika cozunurlugunde
olctu - ama yalniz 2026-07/08 uzerinde (2 ay, tek rejim). Yayinlanan
+%112,3 bu varsayimlara dayaniyor. Bu indirici ayni 18 sembolu
rejim karsiti aylarda indirir; her ay AYRI dosyaya gider ki olcum
ay bazinda tekrarlanabilsin.
"""
import io, os, sys, urllib.request, zipfile
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(KOK, "data_1m_ay")
AYLAR = ("2022-11", "2023-08", "2024-03", "2025-02", "2025-10", "2026-02")
SEMBOL = ("1000PEPEUSDT", "ADAUSDT", "BEATUSDT", "BNBUSDT", "BTCUSDT",
          "CYSUSDT", "DOGEUSDT", "ENAUSDT", "ETHUSDT", "HYPEUSDT",
          "LINKUSDT", "PUMPUSDT", "SOLUSDT", "SUIUSDT", "TUTUSDT",
          "WLDUSDT", "XRPUSDT", "ZECUSDT")
KOL = ["open_time", "open", "high", "low", "close", "volume", "close_time",
       "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]

def indir(sembol, ay):
    u = ("https://data.binance.vision/data/futures/um/monthly/klines/"
         f"{sembol}/1m/{sembol}-1m-{ay}.zip")
    try:
        ham = urllib.request.urlopen(u, timeout=120).read()
    except Exception as e:
        return None, str(e)[:40]
    try:
        with zipfile.ZipFile(io.BytesIO(ham)) as z:
            with z.open(z.namelist()[0]) as fh:
                d = pd.read_csv(fh, header=None, names=KOL)
    except Exception as e:
        return None, "zip: " + str(e)[:40]
    if str(d.iloc[0, 0]).lower().startswith("open"):
        d = d.iloc[1:]
    for c in ("open_time", "open", "high", "low", "close", "quote_volume"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[["open_time", "open", "high", "low", "close", "quote_volume"]].dropna(), None

def main():
    os.makedirs(HEDEF, exist_ok=True)
    for ay in AYLAR:
        klasor = os.path.join(HEDEF, ay)
        os.makedirs(klasor, exist_ok=True)
        var = 0
        for s in SEMBOL:
            yol = os.path.join(klasor, s + ".csv")
            if os.path.exists(yol):
                var += 1
                continue
            d, hata = indir(s, ay)
            if d is None:
                continue
            d.to_csv(yol, index=False)
            var += 1
        print("%s: %d/%d sembol" % (ay, var, len(SEMBOL)), flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
