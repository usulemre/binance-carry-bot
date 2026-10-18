"""TAM EVREN taker hacmi indirici — emir akışı bileşenini temiz panelde
test edebilmek için.

NEDEN: canlı bot `AKIS_AGIRLIK=0.20` ile çalışıyor (carry %80 + emir
akışı %20). Bu oranın gerekçesi madde 119'daki 14 kombinasyon
tablosundan geliyor ve o tablo 137 sembollük HAYATTA KALAN panelde
ölçüldü. `data_taker/` de sadece 183 sembol içeriyor.

`indir_genis.py` kline ZIP'lerinden yalnızca OHLCV + quote_volume
sütunlarını almıştı; emir akışı için gereken
`taker_buy_quote_asset_volume` (sütun 10) alınmamıştı.

Emir akışı sinyali (carry_bot.py:450):
    (son 5g agresif alıcı payı - 0.5) x (son 5g hacim / son 30g hacim)
"""
import concurrent.futures as cf
import io
import os
import sys
import urllib.request
import zipfile

import pandas as pd

B = "https://data.binance.vision/data/futures/um/monthly/klines"
R = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(R, "data_taker_genis")
AYLAR = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)]
AYLAR = [a for a in AYLAR if a <= "2026-08"]


def ay(s, a):
    try:
        b = urllib.request.urlopen(f"{B}/{s}/4h/{s}-4h-{a}.zip", timeout=45).read()
        z = zipfile.ZipFile(io.BytesIO(b))
        t = z.read(z.namelist()[0]).decode()
        return [l.split(",") for l in t.splitlines()
                if l and not l.startswith("open_time")]
    except Exception:
        return []


def sembol(s):
    p = os.path.join(HEDEF, f"{s}.csv")
    if os.path.exists(p):
        return None
    rows = []
    with cf.ThreadPoolExecutor(14) as ex:
        for r in ex.map(lambda a: ay(s, a), AYLAR):
            rows += r
    if len(rows) < 60:
        return f"{s} yetersiz({len(rows)})"
    df = pd.DataFrame(rows).iloc[:, [0, 7, 10]]
    df.columns = ["open_time", "quote_volume", "tb_quote"]
    ot = pd.to_numeric(df.open_time, errors="coerce")
    df["date"] = pd.to_datetime(ot.where(ot < 1e14, ot / 1000), unit="ms")
    for c in ["quote_volume", "tb_quote"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
    # tb_oran: hacmin ne kadari AGRESIF ALIM (piyasa emriyle alan). 0.5 = dengeli
    df["tb_oran"] = df.tb_quote / df.quote_volume.replace(0, float("nan"))
    df[["date", "quote_volume", "tb_quote", "tb_oran"]].to_csv(p, index=False)
    return None


if __name__ == "__main__":
    os.makedirs(HEDEF, exist_ok=True)
    syms = [x.strip() for x in open("/tmp/tum_semboller.txt") if x.strip()]
    a, b = int(sys.argv[1]), int(sys.argv[2])
    for s in syms[a:b]:
        m = sembol(s)
        if m:
            print(m, flush=True)
    print(f"[{a}:{b}] bitti", flush=True)
