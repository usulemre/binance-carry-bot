#!/usr/bin/env python3
"""MADDE 394: spot listelemenin İLK GÜNÜ (data.binance.vision spot 1d günlük anahtarlar,
ilk aylık dosyanın ayı). Çıktı data_spot_ilk_gun.json {perp: "YYYY-MM-DD"}"""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
R = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(os.path.join(R, "data_spot_varlik.json")))
U = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/spot/daily/klines/{s}/1d/{s}-1d-{a}&delimiter=/"
def bir(kv):
    p, v = kv
    if not v["aylar"]: return p, None
    s, a = v["spot"], v["aylar"][0]
    x = subprocess.run(["curl", "-sS", "-m", "60", "--retry", "2", U.format(s=s, a=a)], capture_output=True, text=True).stdout
    g = sorted(set(re.findall(rf"{s}-1d-(\d{{4}}-\d{{2}}-\d{{2}})\.zip<", x)))
    return p, (g[0] if g else a + "-01")
with ThreadPoolExecutor(8) as ex:
    out = dict(ex.map(bir, J.items()))
json.dump(out, open(os.path.join(R, "data_spot_ilk_gun.json"), "w"), indent=0)
print(sum(v is not None for v in out.values()))
