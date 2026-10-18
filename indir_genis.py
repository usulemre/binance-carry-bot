"""TAM EVREN indirici — 864 USDT-M perp, minimum geçmiş filtresi YOK.

NEDEN: mevcut `historical_data_wide/` 183 sembol içeriyor ve bunlar
uzun geçmişi olan, hâlâ listede olan coinler. Yani hem YENİ
listelemeler hem DELIST edilmişler eksik. Madde 132'de ölçüldüğü
gibi, eşik bazlı ters dönüş stratejisinin beslendiği yer tam olarak
bu eksik kısım (±%30 hareket edenler ezici çoğunlukla yeni/küçük
isimler).

data.binance.vision delist edilmiş sembollerin geçmişini de tutar -
bu yüzden bu indirme hayatta kalma yanlılığını da kapatır.

Kullanım:
    python indir_genis.py 0 200      # sembol dilimi
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
HEDEF = os.path.join(R, "data_genis")
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
    p = os.path.join(HEDEF, f"{s}_4h.csv")
    if os.path.exists(p):
        return None
    rows = []
    with cf.ThreadPoolExecutor(14) as ex:
        for r in ex.map(lambda a: ay(s, a), AYLAR):
            rows += r
    if len(rows) < 60:                      # ~10 gün; altı işe yaramaz
        return f"{s} yetersiz({len(rows)})"
    df = pd.DataFrame(rows).iloc[:, [0, 1, 2, 3, 4, 5, 7]]
    df.columns = ["open_time", "open", "high", "low", "close",
                  "volume", "quote_volume"]
    ot = pd.to_numeric(df.open_time, errors="coerce")
    df["date"] = pd.to_datetime(ot.where(ot < 1e14, ot / 1000), unit="ms")
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "close"]).drop_duplicates("date")
    df = df.sort_values("date")
    df[["date", "open", "high", "low", "close", "volume",
        "quote_volume"]].to_csv(p, index=False)
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
