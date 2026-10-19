#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""METRİK İNDİRİCİ — SEMBOL BAŞINA DİSKE YAZAR, KALDIĞI YERDEN DEVAM EDER.

MADDE 335: `indir_metrik.py` 203.870 sembol-günü **bellekte** topluyor
ve ancak sonunda tek bir pickle yazıyor. 2026-10-19'da koşu %39'da
(80.000 dosya, ~22 dk) ağ üzerinde takıldı: CPU 7 dakikada 15 saniye
ilerledi, sayaç hiç ilerlemedi, arşiv ise 0,3 sn'de yanıt veriyordu.
Takılmayı kesmek **80 bin indirmeyi çöpe atmak** demekti, çünkü hiçbir
şey diske yazılmamıştı.

Bu sürüm:
  - her sembolü **ayrı dosyaya** yazar: `data_metrik/<SEMBOL>.csv`
  - var olan sembolü **atlar** (kaldığı yerden devam)
  - sembol içindeki günleri paralel çeker, sembolleri **sırayla** işler
  - her sembolden sonra ilerlemeyi basar

KULLANIM
    python indir_metrik_surdurulebilir.py            # hepsi
    python indir_metrik_surdurulebilir.py 0 200      # sembol dilimi
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import pickle
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

B = "https://data.binance.vision/data/futures/um/daily/metrics"
R = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(R, "data_metrik")
CIFT = "/tmp/metrik_cift.pkl"
KOL = ["sum_open_interest_value", "count_toptrader_long_short_ratio",
       "sum_toptrader_long_short_ratio", "count_long_short_ratio",
       "sum_taker_long_short_vol_ratio"]
ES_ZAMANLI = 10
PARCA = 120           # bir curl cagrisindaki en fazla gun
PARCA_SINIR = 150.0   # saniye: bir curl cagrisi icin mutlak sinir          # sembol ICINDE
DENEME = 3


TOPLAM_SINIR = 25.0      # saniye: BIR dosya icin mutlak ust sinir


def sembol(s, gunler):
    """MADDE 335: indirme CURL'e devredildi.

    NEDEN: Python'un `urlopen(timeout=)` degeri SOKET BASINA zaman
    asimidir; bu ortamda (cikis trafigi bir vekil sunucudan geciyor)
    yuksek es zamanlilikta surecler SESSIZCE TIKANDI - kendi saatleri
    ~100 saniyede durdu ama 20+ dakika gecti, CPU %2'de kaldi ve arsiv
    tek istege 0,3-0,7 sn'de yanit veriyordu. Iki ayri Python
    indiricisinde (bu dosyanin ilk hali ve `indir_metrik.py`) ayni sey
    oldu. `curl --max-time` zaman sinirini SURECIN DISINDA uygular ve
    `--parallel` ile baglanti yeniden kullanimi saglar; takilma
    imkansizlasir cunku curl'un kendisi oluyor.
    """
    p = os.path.join(HEDEF, f"{s}.csv")
    if os.path.exists(p):
        return "atlandi"
    gec = tempfile.mkdtemp(prefix="m_%s_" % s)
    try:
        # MADDE 335: gun listesi PARCALANIR. Ilk hal tek curl cagrisina
        # butun gunleri veriyor ve `timeout=60+2*len(gunler)` ile 1500
        # gunluk bir sembolde 51 DAKIKAYA kadar bloke oluyordu - yani
        # Python'un takilmasini curl'e devrettim ama BEKLEME SINIRINI
        # devretmemistim. Artik her parca <=PARCA gun ve <=PARCA_SINIR sn.
        for i in range(0, len(gunler), PARCA):
            obek = gunler[i:i + PARCA]
            liste = os.path.join(gec, "u%d.txt" % i)
            with open(liste, "w") as fh:
                for g in obek:
                    fh.write('url = "%s/%s/%s-metrics-%s.zip"\n' % (B, s, s, g))
                    fh.write('output = "%s/%s.zip"\n' % (gec, g))
            try:
                subprocess.run(["curl", "-sS", "--parallel",
                                "--parallel-max", str(ES_ZAMANLI),
                                "--max-time", str(int(TOPLAM_SINIR)),
                                "--retry", "1", "--retry-max-time", "20",
                                "-K", liste],
                               capture_output=True, timeout=PARCA_SINIR)
            except subprocess.TimeoutExpired:
                pass          # o obekten ne indiyse onunla devam
        parca = []
        for g in gunler:
            z = os.path.join(gec, "%s.zip" % g)
            if not os.path.exists(z) or os.path.getsize(z) < 200:
                continue
            try:
                with zipfile.ZipFile(z) as zz:
                    x = pd.read_csv(zz.open(zz.namelist()[0]))
            except Exception:
                continue
            x["t"] = pd.to_datetime(x.create_time)
            x["bar"] = (x.t - pd.Timedelta(seconds=1)).dt.floor("4h")
            parca.append(x.sort_values("t").groupby("bar")[KOL].last())
        if not parca:
            open(p, "w").write("bar," + ",".join(KOL) + "\n")
            return "veri yok"
        d = pd.concat(parca)
        d = d[~d.index.duplicated(keep="last")].sort_index()
        d.to_csv(p)
        return "%d bar" % len(d)
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def panel():
    """data_metrik/*.csv -> /tmp/metrik_panel.pkl (C izgarasina oturur)."""
    z = pickle.load(open("/tmp/zemin.pkl", "rb"))
    C = z["C"]
    veri = {k: {} for k in KOL}
    n = 0
    for ad in sorted(os.listdir(HEDEF)):
        if not ad.endswith(".csv"):
            continue
        s = ad[:-4]
        if s not in C.columns:
            continue
        try:
            d = pd.read_csv(os.path.join(HEDEF, ad), parse_dates=["bar"])
        except Exception:
            continue
        if d.empty:
            continue
        d = d.set_index("bar")
        for k in KOL:
            if k in d.columns:
                veri[k][s] = d[k]
        n += 1
    M = {}
    for k in KOL:
        p = pd.DataFrame(veri[k]).reindex(index=C.index, columns=C.columns)
        M[k] = p
        print("  %-38s %d hucre" % (k, int(p.notna().sum().sum())), flush=True)
    pickle.dump(M, open("/tmp/metrik_panel.pkl", "wb"))
    print("yazildi /tmp/metrik_panel.pkl  (%d sembol)" % n, flush=True)
    return n > 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["panel"]:
        sys.exit(0 if panel() else 1)
    os.makedirs(HEDEF, exist_ok=True)
    ciftler = pickle.load(open(CIFT, "rb"))
    gunluk = {}
    for s, g in ciftler:
        gunluk.setdefault(s, []).append(g)
    semboller = sorted(gunluk)
    a = int(sys.argv[1]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(semboller)
    t0 = time.time()
    for i, s in enumerate(semboller[a:b], start=a):
        m = sembol(s, sorted(gunluk[s]))
        print("%4d/%d %-16s %-10s %5d sn"
              % (i + 1, len(semboller), s, m, int(time.time() - t0)), flush=True)
    print("[METRIK-BITTI] %d dosya" % len(os.listdir(HEDEF)), flush=True)
