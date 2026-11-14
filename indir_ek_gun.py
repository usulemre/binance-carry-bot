#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 783 — AY BİTMEDEN artımlı veri eki (günlük dosyalar + resmi funding geçmişi). indir_ek_ay.py'nin günlük karşılığı.
  VERI_EK=uzun python3 indir_ek_gun.py 2026-11-01 2026-11-13
  * 4 sa mum (fiyat + taker) ve metrik: data.binance.vision GÜNLÜK dosyalar
  * funding: Binance web'in herkese açık funding geçmişi ucu (bapi get-funding-rate-history; anahtar yok) — aylık arşivle aynı kayıt
Yalnız mevcut son tarihten SONRAKİ satırlar eklenir (indir_ek_ay.ekle); yeni sembol eklenmez."""
import json, os, sys, time, tempfile, shutil, zipfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import indir_ek_ay as E
R = E.R; B = E.B
BAPI = "https://www.binance.com/bapi/futures/v1/public/future/common/get-funding-rate-history"


def funding_al(s, bas_ms):
    for i in range(4):
        try:
            r = urllib.request.Request(BAPI, data=json.dumps({"symbol": s, "page": 1, "rows": 1000}).encode(),
                                       headers={"Content-Type": "application/json", "User-Agent": "m783"})
            d = json.loads(urllib.request.urlopen(r, timeout=20).read()).get("data") or []
            return [x for x in d if int(x["calcTime"]) >= bas_ms]
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def bir(s, gunler, bit):
    gec = tempfile.mkdtemp(prefix="eg_%s_" % s); out = {}
    try:
        isler = [(f"{B}/daily/klines/{s}/4h/{s}-4h-{g}.zip", f"k{g}.zip") for g in gunler]
        if os.path.exists(os.path.join(R, "data_metrik", f"{s}.csv")):
            isler += [(f"{B}/daily/metrics/{s}/{s}-metrics-{g}.zip", f"m{g}.zip") for g in gunler]
        E.cek(isler, gec, s)
        ks = [k for k in (E.oku(os.path.join(gec, f"k{g}.zip")) for g in gunler) if k is not None]
        if ks:
            ham = pd.concat(ks)
            df = ham.iloc[:, [0, 1, 2, 3, 4, 5, 7]].copy(); df.columns = ["t", "open", "high", "low", "close", "volume", "quote_volume"]
            df["date"] = E.zaman(df.t)
            for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
            out["fiyat"] = E.ekle(os.path.join(R, E.D_FIYAT, f"{s}_4h.csv"), df, "date")
            dt = ham.iloc[:, [0, 7, 10]].copy(); dt.columns = ["t", "quote_volume", "tb_quote"]; dt["date"] = E.zaman(dt.t)
            for c in ["quote_volume", "tb_quote"]:
                dt[c] = pd.to_numeric(dt[c], errors="coerce")
            dt = dt.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
            dt["tb_oran"] = dt.tb_quote / dt.quote_volume.replace(0, float("nan"))
            pt = os.path.join(R, E.D_TAKER, f"{s}.csv")
            if os.path.exists(pt): out["taker"] = E.ekle(pt, dt, "date")
        pf = os.path.join(R, E.D_FUND, f"{s}.csv")
        if ks and os.path.exists(pf):                       # yalnız Kasım'da mumu olan (yaşayan) sembol
            f = funding_al(s, int(pd.Timestamp(gunler[0]).timestamp() * 1000))
            if f is None: out["funding_hata"] = 1
            elif f:
                d = pd.DataFrame({"date": pd.to_datetime([int(x["calcTime"]) for x in f], unit="ms"),
                                  "funding": [float(x["lastFundingRate"]) for x in f],
                                  "interval_h": pd.array([int(x["fundingIntervalHours"]) for x in f], dtype="Int64")})
                d = d[d.date < pd.Timestamp(bit) + pd.Timedelta(days=1)].drop_duplicates("date").sort_values("date")
                d["date"] = d["date"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]
                out["funding"] = E.ekle(pf, d, "date")
        pm = os.path.join(R, "data_metrik", f"{s}.csv")
        if os.path.exists(pm):
            parca = []
            for g in gunler:
                zf = os.path.join(gec, f"m{g}.zip")
                if not os.path.exists(zf) or os.path.getsize(zf) < 200: continue
                try:
                    with zipfile.ZipFile(zf) as zz: x = pd.read_csv(zz.open(zz.namelist()[0]))
                except Exception: continue
                x["t"] = pd.to_datetime(x.create_time); x["bar"] = (x.t - pd.Timedelta(seconds=1)).dt.floor("4h")
                parca.append(x.sort_values("t").groupby("bar")[E.KOL].last())
            if parca:
                d = pd.concat(parca); d = d[~d.index.duplicated(keep="last")].sort_index().reset_index()
                d = d[d["count_long_short_ratio"].notna() & (d["sum_open_interest_value"] > 0)]
                out["metrik"] = E.ekle(pm, d, "bar")
        return s, out
    finally:
        shutil.rmtree(gec, ignore_errors=True)


if __name__ == "__main__":
    bas, bit = sys.argv[1], sys.argv[2]
    gunler = [d.strftime("%Y-%m-%d") for d in pd.date_range(bas, bit)]
    syms = sorted(f[:-7] for f in os.listdir(os.path.join(R, E.D_FIYAT)) if f.endswith("_4h.csv"))
    # yalnız Ekim sonunda yaşayan semboller (son satırı 2026-10 olan)
    canli = []
    for s in syms:
        with open(os.path.join(R, E.D_FIYAT, f"{s}_4h.csv"), "rb") as fh:
            fh.seek(max(0, os.path.getsize(fh.name) - 200)); son = fh.read().decode(errors="ignore").strip().splitlines()[-1][:7]
        if son >= "2026-10": canli.append(s)
    print(len(syms), "sembol ·", len(canli), "yaşayan", flush=True)
    top = {}; hata = 0
    with ThreadPoolExecutor(6) as ex:
        for i, (s, o) in enumerate(ex.map(lambda s: bir(s, gunler, bit), canli)):
            for k, v in o.items(): top[k] = top.get(k, 0) + v
            if i % 100 == 0: print(i, s, o, flush=True)
    print("TOPLAM eklenen satır:", top, flush=True)
