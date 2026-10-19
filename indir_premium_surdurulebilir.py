#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PREMIUM ENDEKSİ İNDİRİCİ — CURL TABANLI, KALDIĞI YERDEN DEVAM EDER.

MADDE 336: konteyner kaybından sonra `data_premium_genis/` **boş** ve
`carry_prim.csv` **yok** çıktı. Yani prim ekseninin (madde 332'nin
`CARRY_PRIM_E` kararı, kasımdaki tohum yenilemesi) BULGULARI modüllerde
duruyor ama HAM GİRDİSİ kayıp. Bu dosya o girdiyi geri kurar.

NEDEN YENİ DOSYA, `indir_funding_genis.py premium` DEĞİL: o sürüm
`urllib.request.urlopen(timeout=45)` + `ThreadPoolExecutor(14)`
kullanıyor. Bu ortamda tam o desen İKİ AYRI indiricide SESSİZCE TIKANDI
(madde 335): `timeout=` değeri SOKET BAŞINA zaman aşımıdır, damlayarak
gelen bir yanıtta `.read()` sonsuza kadar bloke olur — süreçlerin kendi
saati ~100 saniyede durdu, 20+ dakika geçti, CPU %2'de kaldı, arşiv ise
tek isteğe 0,3-0,7 sn'de yanıt veriyordu. `curl --max-time` sınırı
SÜRECİN DIŞINDA uygular; takılan taraf curl'un kendisi olur ve ölür.

Ayrıca her sembolü AYRI DOSYAYA yazar ve var olanı ATLAR: madde 335'te
bellekte biriktiren indiriciyi kesmek 80 bin indirmeyi çöpe atmak
demekti. Burada kesinti en fazla bir sembol kaybettirir.

KULLANIM
    python indir_premium_surdurulebilir.py            # hepsi
    python indir_premium_surdurulebilir.py 0 300      # sembol dilimi
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(R, "data_premium_genis")
BP = "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines"
AYLAR = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)]
AYLAR = [a for a in AYLAR if a <= "2026-08"]

ES_ZAMANLI = 10       # curl --parallel-max
DOSYA_SINIR = 25      # saniye: BIR dosya icin mutlak ust sinir
CAGRI_SINIR = 150.0   # saniye: BIR curl cagrisi icin mutlak ust sinir
EN_AZ_SATIR = 30      # bundan az satir gelirse sembol "veri yok" sayilir


def zaman(seri):
    v = pd.to_numeric(seri, errors="coerce")
    return pd.to_datetime(v.where(v < 1e14, v / 1000), unit="ms")


def sembol(s):
    """data_premium_genis/<SEM>.csv yazar: date, premium (4h kapanis)."""
    p = os.path.join(HEDEF, f"{s}.csv")
    if os.path.exists(p):
        return "atlandi"
    gec = tempfile.mkdtemp(prefix="p_%s_" % s)
    try:
        liste = os.path.join(gec, "u.txt")
        with open(liste, "w") as fh:
            for a in AYLAR:
                fh.write('url = "%s/%s/4h/%s-4h-%s.zip"\n' % (BP, s, s, a))
                fh.write('output = "%s/%s.zip"\n' % (gec, a))
        try:
            subprocess.run(["curl", "-sS", "--parallel",
                            "--parallel-max", str(ES_ZAMANLI),
                            "--max-time", str(DOSYA_SINIR),
                            "--retry", "1", "--retry-max-time", "20",
                            "-K", liste],
                           capture_output=True, timeout=CAGRI_SINIR)
        except subprocess.TimeoutExpired:
            pass          # ne indiyse onunla devam
        satir = []
        for a in AYLAR:
            z = os.path.join(gec, "%s.zip" % a)
            if not os.path.exists(z) or os.path.getsize(z) < 200:
                continue
            try:
                with zipfile.ZipFile(z) as zz:
                    t = zz.read(zz.namelist()[0]).decode()
            except Exception:
                continue
            satir += [l.split(",") for l in t.splitlines()
                      if l and not l[0].isalpha()]
        if len(satir) < EN_AZ_SATIR:
            return "veri yok (%d satir)" % len(satir)
        d = pd.DataFrame(satir).iloc[:, [0, 4]]
        d.columns = ["t", "premium"]
        d["date"] = zaman(d["t"])
        d["premium"] = pd.to_numeric(d["premium"], errors="coerce")
        d = d.dropna().drop_duplicates("date").sort_values("date")
        if len(d) < EN_AZ_SATIR:
            return "veri yok (temiz %d)" % len(d)
        d[["date", "premium"]].to_csv(p, index=False)
        return "%d bar" % len(d)
    finally:
        shutil.rmtree(gec, ignore_errors=True)


if __name__ == "__main__":
    os.makedirs(HEDEF, exist_ok=True)
    kaynak = "/tmp/tum_semboller.txt"
    if not os.path.exists(kaynak):
        kaynak = os.path.join(R, "tum_semboller.txt")
    syms = [x.strip() for x in open(kaynak) if x.strip()]
    a = int(sys.argv[1]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(syms)
    t0 = time.time()
    for i, s in enumerate(syms[a:b], start=a):
        m = sembol(s)
        print("%4d/%d %-16s %-18s %5d sn"
              % (i + 1, len(syms), s, m, int(time.time() - t0)), flush=True)
    print("[PREMIUM-BITTI] %d dosya" % len(os.listdir(HEDEF)), flush=True)
