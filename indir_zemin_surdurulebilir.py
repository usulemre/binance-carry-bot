#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZEMİN İNDİRİCİ — CURL TABANLI, KALDIĞI YERDEN DEVAM EDER, TEK GEÇİŞ.

MADDE 342: konteyner kaybından sonra (madde 335) zemini yeniden kurmak
bu betiklerin işi. Ama üçü de hâlâ `urllib.request.urlopen(timeout=45)`
+ `ThreadPoolExecutor(14)` kullanıyordu:

    indir_genis.py        -> data_genis/        (fiyat, 236 MB)
    indir_taker_genis.py  -> data_taker_genis/  (taker, 210 MB)
    indir_funding_genis.py-> data_funding_genis/ (funding, 79 MB)

Tam o desen bu ortamda İKİ AYRI indiricide SESSİZCE TIKANDI (madde
335): `timeout=` SOKET BAŞINA zaman aşımıdır, damlayarak gelen bir
yanıtta `.read()` sonsuza kadar bloke olur — süreçlerin kendi saati
~100 saniyede durdu, 20+ dakika geçti, CPU %2'de kaldı, arşiv ise tek
isteğe 0,3-0,7 sn'de yanıt veriyordu. Yani bir sonraki yeniden kurulum
**tam buradan asılacaktı** ve bunu ancak saatler sonra fark ederdiniz.

`curl --max-time` sınırı SÜRECİN DIŞINDA uygular; takılan taraf curl'ün
kendisi olur ve ölür. Bu dosya o dersi fiyat/taker/funding'e de taşır.

İKİNCİ KAZANÇ — TEK GEÇİŞ: fiyat ve taker AYNI zip'ten çıkıyor (aylık
4h klines; fiyat kolon [0,1,2,3,4,5,7], taker kolon [0,7,10]). Eski iki
betik aynı 236 MB'ı İKİ KEZ indiriyordu. Burada bir kez indirilip iki
dosya birden yazılıyor.

PARİTE: `dogrula` modu mevcut dosyalarla BAYT BAYT karşılaştırır.
Dönüşüm eski betiklerden birebir kopyalandı; değiştirilen yalnız
ÇEKME KATMANI.

KULLANIM
    python indir_zemin_surdurulebilir.py klines          # fiyat + taker
    python indir_zemin_surdurulebilir.py funding         # funding
    python indir_zemin_surdurulebilir.py klines 0 300    # sembol dilimi
    python indir_zemin_surdurulebilir.py dogrula BTCUSDT ETHUSDT
"""
from __future__ import annotations

import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
BK = "https://data.binance.vision/data/futures/um/monthly/klines"
BF = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
FIYAT = os.path.join(R, "data_genis")
TAKER = os.path.join(R, "data_taker_genis")
FUND = os.path.join(R, "data_funding_genis")

AYLAR = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)]
AYLAR = [a for a in AYLAR if a <= "2026-08"]

ES_ZAMANLI = 10       # curl --parallel-max
DOSYA_SINIR = 25      # saniye: BIR dosya icin mutlak ust sinir
CAGRI_SINIR = 180.0   # saniye: BIR curl cagrisi icin mutlak ust sinir
EN_AZ_SATIR = 60      # ~10 gun; altinda sembol atlanir (eski betikle ayni)


def _cek(urller: list[tuple[str, str]], gec: str) -> None:
    """(url, cikti_adi) listesini curl ile indirir. Takilma imkansiz."""
    liste = os.path.join(gec, "u.txt")
    with open(liste, "w") as fh:
        for url, ad in urller:
            fh.write('url = "%s"\noutput = "%s/%s"\n' % (url, gec, ad))
    try:
        subprocess.run(["curl", "-sS", "--parallel",
                        "--parallel-max", str(ES_ZAMANLI),
                        "--max-time", str(DOSYA_SINIR),
                        "--retry", "1", "--retry-max-time", "20",
                        "-K", liste],
                       capture_output=True, timeout=CAGRI_SINIR)
    except subprocess.TimeoutExpired:
        pass          # ne indiyse onunla devam


def _satirlar(gec: str, adlar: list[str], bas_atla: str) -> list[list[str]]:
    out = []
    for ad in adlar:
        z = os.path.join(gec, ad)
        if not os.path.exists(z) or os.path.getsize(z) < 200:
            continue
        try:
            with zipfile.ZipFile(z) as zz:
                t = zz.read(zz.namelist()[0]).decode()
        except Exception:
            continue
        out += [l.split(",") for l in t.splitlines()
                if l and not l.startswith(bas_atla)]
    return out


def _zaman(seri):
    v = pd.to_numeric(seri, errors="coerce")
    return pd.to_datetime(v.where(v < 1e14, v / 1000), unit="ms")


def klines(s: str, zorla: bool = False) -> str:
    """Bir sembolun aylik 4h klines'ini BIR KEZ indirip IKI dosya yazar."""
    pf = os.path.join(FIYAT, f"{s}_4h.csv")
    pt = os.path.join(TAKER, f"{s}.csv")
    if not zorla and os.path.exists(pf) and os.path.exists(pt):
        return "atlandi"
    gec = tempfile.mkdtemp(prefix="k_%s_" % s)
    try:
        _cek([(f"{BK}/{s}/4h/{s}-4h-{a}.zip", f"{a}.zip") for a in AYLAR], gec)
        satir = _satirlar(gec, [f"{a}.zip" for a in AYLAR], "open_time")
        if len(satir) < EN_AZ_SATIR:
            return "yetersiz(%d)" % len(satir)
        ham = pd.DataFrame(satir)

        # --- FIYAT: indir_genis.py'den BIREBIR kopya (kolon [0,1,2,3,4,5,7])
        df = ham.iloc[:, [0, 1, 2, 3, 4, 5, 7]].copy()
        df.columns = ["open_time", "open", "high", "low", "close",
                      "volume", "quote_volume"]
        df["date"] = _zaman(df.open_time)
        for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["date", "close"]).drop_duplicates("date")
        df = df.sort_values("date")
        os.makedirs(FIYAT, exist_ok=True)
        df[["date", "open", "high", "low", "close", "volume",
            "quote_volume"]].to_csv(pf, index=False)

        # --- TAKER: indir_taker_genis.py'den BIREBIR kopya (kolon [0,7,10])
        dt = ham.iloc[:, [0, 7, 10]].copy()
        dt.columns = ["open_time", "quote_volume", "tb_quote"]
        dt["date"] = _zaman(dt.open_time)
        for c in ["quote_volume", "tb_quote"]:
            dt[c] = pd.to_numeric(dt[c], errors="coerce")
        dt = dt.dropna(subset=["date"]).drop_duplicates("date")
        dt = dt.sort_values("date")
        dt["tb_oran"] = dt.tb_quote / dt.quote_volume.replace(0, float("nan"))
        os.makedirs(TAKER, exist_ok=True)
        dt[["date", "quote_volume", "tb_quote", "tb_oran"]].to_csv(
            pt, index=False)
        return "%d bar" % len(df)
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def funding(s: str, zorla: bool = False) -> str:
    """data_funding_genis/<SEM>.csv -> date, funding (indir_funding_genis ile ayni)."""
    p = os.path.join(FUND, f"{s}.csv")
    if not zorla and os.path.exists(p):
        return "atlandi"
    gec = tempfile.mkdtemp(prefix="f_%s_" % s)
    try:
        _cek([(f"{BF}/{s}/{s}-fundingRate-{a}.zip", f"{a}.zip")
              for a in AYLAR], gec)
        satir = _satirlar(gec, [f"{a}.zip" for a in AYLAR], "calc_time")
        satir = [r for r in satir if r and not r[0][:1].isalpha()]
        if len(satir) < 30:
            return "yetersiz(%d)" % len(satir)
        # MADDE 342: UCUNCU KOLON `interval_h` KORUNUYOR.
        # `indir_funding_genis.py` yalniz `date,funding` yaziyor, oysa
        # bu konteynerdeki dosyalarda `interval_h` DA var ve arsivin
        # zip'i onu zaten tasiyor (kolon 1 = funding_interval_hours).
        # Deponun indiricisiyle yeniden kurulsa bu bilgi KAYBOLACAKTI.
        # Madde 340 evrenin %24,1'inin odeme araligini DEGISTIRDIGINI
        # olctu (482 sembol 4sa, 355 sembol 8sa); bu kolon o eksenin ham
        # verisidir ve timestamp farkindan CIKARMAKTAN daha dogrudur.
        d = pd.DataFrame(satir).iloc[:, [0, 2, 1]].copy()
        d.columns = ["t", "funding", "interval_h"]
        d["date"] = _zaman(d["t"])
        d["funding"] = pd.to_numeric(d["funding"], errors="coerce")
        d["interval_h"] = pd.to_numeric(d["interval_h"], errors="coerce")
        d = d.dropna(subset=["date", "funding"])
        d = d.drop_duplicates("date").sort_values("date")
        if len(d) < 30:
            return "yetersiz(temiz %d)" % len(d)
        d["interval_h"] = d["interval_h"].astype("Int64")
        os.makedirs(FUND, exist_ok=True)
        d[["date", "funding", "interval_h"]].to_csv(p, index=False)
        return "%d odeme" % len(d)
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def dogrula(semboller: list[str]) -> bool:
    """PARITE: mevcut dosyalari gecici dizine yeniden uretip BAYT BAYT kiyasla."""
    global FIYAT, TAKER, FUND
    eski = (FIYAT, TAKER, FUND)
    gec = tempfile.mkdtemp(prefix="dogrula_")
    tamam = True
    try:
        for s in semboller:
            FIYAT = os.path.join(gec, "f"); TAKER = os.path.join(gec, "t")
            FUND = os.path.join(gec, "u")
            klines(s, zorla=True); funding(s, zorla=True)
            for yeni, asil in ((os.path.join(FIYAT, f"{s}_4h.csv"),
                                os.path.join(eski[0], f"{s}_4h.csv")),
                               (os.path.join(TAKER, f"{s}.csv"),
                                os.path.join(eski[1], f"{s}.csv")),
                               (os.path.join(FUND, f"{s}.csv"),
                                os.path.join(eski[2], f"{s}.csv"))):
                if not os.path.exists(asil):
                    print("  %-34s ASIL YOK (atlandi)" % os.path.basename(asil))
                    continue
                ok = os.path.exists(yeni) and filecmp.cmp(yeni, asil, shallow=False)
                print("  %-34s %s" % (os.path.basename(asil),
                                      "BIREBIR" if ok else "FARKLI"))
                tamam = tamam and ok
        return tamam
    finally:
        FIYAT, TAKER, FUND = eski
        shutil.rmtree(gec, ignore_errors=True)


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "klines"
    if mod == "dogrula":
        sys.exit(0 if dogrula(sys.argv[2:] or ["BTCUSDT"]) else 1)
    kaynak = "/tmp/tum_semboller.txt"
    if not os.path.exists(kaynak):
        kaynak = os.path.join(R, "tum_semboller.txt")
    syms = [x.strip() for x in open(kaynak) if x.strip()]
    a = int(sys.argv[2]) if len(sys.argv) > 3 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else len(syms)
    isle = klines if mod == "klines" else funding
    t0 = time.time()
    for i, s in enumerate(syms[a:b], start=a):
        m = isle(s)
        print("%4d/%d %-16s %-16s %5d sn"
              % (i + 1, len(syms), s, m, int(time.time() - t0)), flush=True)
    print("[%s-BITTI]" % mod.upper(), flush=True)
