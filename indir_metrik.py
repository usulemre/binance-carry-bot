"""Binance metrics (OI, long/short oranlari) — sadece aday sembol-gunleri. Madde 148.
5 dakikalik degerler 4s bara indirilir: bar t (t..t+4s) icin, kapanis anina kadarki SON deger.
04:00:00 damgali satir 00:00 barina aittir (o anda bilinir). Nedensel.
Kullanim: python indir_metrik.py /tmp/metrik_cift.pkl /tmp/metrik4.pkl
"""
import io, pickle, sys, time, urllib.request, zipfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
B = "https://data.binance.vision/data/futures/um/daily/metrics"
KOL = ["sum_open_interest_value", "count_toptrader_long_short_ratio",
       "sum_toptrader_long_short_ratio", "count_long_short_ratio",
       "sum_taker_long_short_vol_ratio"]


def al(s, g):
    for d in range(3):
        try:
            b = urllib.request.urlopen(f"{B}/{s}/{s}-metrics-{g}.zip", timeout=30).read()
            z = zipfile.ZipFile(io.BytesIO(b))
            x = pd.read_csv(z.open(z.namelist()[0]))
            x["t"] = pd.to_datetime(x.create_time)
            x["bar"] = (x.t - pd.Timedelta(seconds=1)).dt.floor("4h")
            y = x.sort_values("t").groupby("bar")[KOL].last()
            y["sembol"] = s
            return y
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + d)
        except Exception:
            time.sleep(1 + d)
    return "HATA"


cift = pickle.load(open(sys.argv[1], "rb"))
parca, hata, t0 = [], 0, time.time()
with ThreadPoolExecutor(32) as ex:
    fs = [ex.submit(al, s, g) for s, g in cift]
    for i, f in enumerate(as_completed(fs)):
        r = f.result()
        if isinstance(r, str):
            hata += 1
        elif r is not None:
            parca.append(r)
        if i % 5000 == 0:
            print(i, len(cift), "hata", hata, int(time.time() - t0), "sn", flush=True)
D = pd.concat(parca).reset_index().rename(columns={"bar": "date"})
pickle.dump(D, open(sys.argv[2], "wb"))
print("bitti satir", len(D), "hata", hata, int(time.time() - t0), "sn", flush=True)
