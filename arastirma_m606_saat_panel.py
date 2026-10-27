#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 606 veri: data_5m (100 sembol, 2024-01..2026-08, veri dalı) → SAATLİK kapanış ve quote hacim paneli (/tmp/saat_panel.pkl)."""
import glob, os, sys, zipfile, pickle
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
KOK = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/veri5m/data_5m"


def oku(sem):
    parcalar = []
    for z in sorted(glob.glob(f"{KOK}/{sem}-5m-*.zip")):
        with zipfile.ZipFile(z) as f:
            d = pd.read_csv(f.open(f.namelist()[0]))
        if not str(d.iloc[0, 0]).isdigit():
            d = pd.read_csv(f.open(f.namelist()[0]) if False else zipfile.ZipFile(z).open(zipfile.ZipFile(z).namelist()[0]), header=None)
        d = d.iloc[:, [0, 4, 7]]; d.columns = ["t", "c", "q"]
        parcalar.append(d)
    d = pd.concat(parcalar); d["t"] = pd.to_datetime(d["t"].astype("int64"), unit="ms"); d = d.drop_duplicates("t").set_index("t").sort_index()
    h = pd.DataFrame({"c": d["c"].astype(float).resample("1h").last(), "q": d["q"].astype(float).resample("1h").sum()})
    return sem, h


if __name__ == "__main__":
    semler = sorted({os.path.basename(p).split("-5m-")[0] for p in glob.glob(f"{KOK}/*.zip")})
    with ProcessPoolExecutor(2) as ex:
        sonuc = dict(ex.map(oku, semler))
    C = pd.DataFrame({s: v["c"] for s, v in sonuc.items()}); Q = pd.DataFrame({s: v["q"] for s, v in sonuc.items()})
    pickle.dump({"C": C, "Q": Q}, open("/tmp/saat_panel.pkl", "wb"))
    print(f"saat paneli: {C.shape}, {C.index[0]} .. {C.index[-1]}, dolu hücre {int(C.notna().sum().sum())}")
