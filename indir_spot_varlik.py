#!/usr/bin/env python3
"""MADDE 386: her perp sembolü için Binance SPOT USDT çiftinin hangi aylarda
işlem gördüğü (data.binance.vision S3 listesi, 1d aylık kline anahtarları).
1000/1000000/1M önekli perp'ler önek atılarak eşlenir (1000BONKUSDT -> BONKUSDT).
Çıktı: data_spot_varlik.json {perp: {"spot": SPOTSEMBOL, "aylar": ["2023-03", ...]}}"""
import json, os, re, subprocess, glob
from concurrent.futures import ThreadPoolExecutor
R = os.path.dirname(os.path.abspath(__file__))
U = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/spot/monthly/klines/{s}/1d/&delimiter=/"

def aylar(s):
    x = subprocess.run(["curl", "-sS", "-m", "60", "--retry", "2", U.format(s=s)], capture_output=True, text=True).stdout
    return sorted(set(re.findall(rf"{s}-1d-(\d{{4}}-\d{{2}})\.zip<", x)))

def adaylar(p):
    b = p[:-4]
    c = [b]
    m = re.match(r"^(1000000|100000|10000|1000|1M)(.+)$", b)
    if m: c.append(m.group(2))
    return [x + "USDT" for x in c]

def bir(p):
    for s in adaylar(p):
        a = aylar(s)
        if a: return p, {"spot": s, "aylar": a}
    return p, {"spot": None, "aylar": []}

if __name__ == "__main__":
    perps = sorted(os.path.basename(f)[:-7] for f in glob.glob(os.path.join(R, "data_genis", "*_4h.csv")))
    with ThreadPoolExecutor(8) as ex:
        out = dict(ex.map(bir, perps))
    json.dump(out, open(os.path.join(R, "data_spot_varlik.json"), "w"), indent=0)
    n = sum(1 for v in out.values() if v["aylar"])
    print(f"{len(out)} perp, spotu olan {n}")
