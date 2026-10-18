#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOTOR ZEMİNİNİ SIFIRDAN KURAR (madde 335).

NEDEN VAR: motorun (`g33.py` ve bütün `gNN.py` kardeşleri) zemini
`/tmp`'de yaşıyordu — `/tmp/g.py`, `/tmp/panel.pkl`, `/tmp/hlo.pkl`,
`/tmp/sk_bar48.pkl`. 2026-10-19'da konteyner geri alındı ve **hepsi
gitti**; proje arşivinde yoktular çünkü hiçbir zaman projede değillerdi.
Madde 262 bunu bir kez haber vermişti ("`/tmp/kontrol_E*.pkl` bugün
bakıldığında SİLİNMİŞTİ") ama ders yalnızca yayınlanan sayılar için
alınmış, **motorun kendi zemini için alınmamıştı.**

Bu betik o zemini depodaki veriden ve depodaki kodun kendi tarifinden
yeniden üretir. Tarif uydurma değildir: `carry_denetim.panel_yukle_temiz`
+ `carry_guncel_backtest.panel()` zaten bu projede duruyordu ve formüller
oradan birebir alındı.

KULLANIM
    python yeniden_kur.py            # panelleri + /tmp/g.py + sinyali kur
    python yeniden_kur.py --kontrol  # yalnizca dosyalar yerinde mi

ÜRETTİĞİ ŞEYLER
    /tmp/g.py          motorun `from g import *` ile aldigi zemin
    /tmp/panel.pkl     dict(C, HAC, YAS, DON)
    /tmp/hlo.pkl       dict(O, H, L)
    /tmp/sk_bar48.pkl  48 saatlik pencereyle canli tahminci sinyali

PARİTE ÖLÇÜTÜ (kabul testi): kanonik kontrol ortaminda
    HAVUZ=3 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 UCELE=0.40
    REB_GUN=5 FAZ=15 REZERV=0.20 SK_DOSYA=/tmp/sk_bar48.pkl
    python3 g33.py ls 5
beklenen: tam **+112,3%** · dusus **-14,5** (madde 320'nin parite kolu).
Tutmuyorsa zemin DOGRU KURULMAMISTIR ve hicbir olcum yapilmaz.
"""
from __future__ import annotations

import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)

PANEL = "/tmp/panel.pkl"
HLO = "/tmp/hlo.pkl"
GPY = "/tmp/g.py"
SK48 = "/tmp/sk_bar48.pkl"

G_KAYNAK = '''"""MOTOR ZEMINI - `yeniden_kur.py` tarafindan URETILDI (madde 335).
Elle duzenlenmez; kaynagi projedeki yeniden_kur.py'dir."""
import pickle, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, %(kok)r)
import carry_denetim as D

_Z = pickle.load(open(%(zemin)r, "rb"))
C = _Z["C"]; cv = C.values
fv = _Z["ODE"].values
S = _Z["sk"].values
A = _Z["AK"].values
U = _Z["uy"].values
HV = _Z["H"].values
LV = _Z["L"].values


def rk(x):
    """Yuzdelik sira (0..1). carry_guncel_backtest.bt ile birebir."""
    return pd.Series(x).rank(pct=True).values
'''

ZEMIN = "/tmp/zemin.pkl"


def paneller():
    import carry_denetim as D
    print("panel_yukle_temiz() ...", flush=True)
    C, SIN, ODE, HAC, YAS, DON = D.panel_yukle_temiz()
    print("  C: %d bar x %d sembol  (%s .. %s)"
          % (len(C), C.shape[1], C.index[0], C.index[-1]), flush=True)
    uy = D.uygunluk(C, HAC, YAS, DON)
    try:
        from tradfi_liste import TRADFI as TF
        uy = uy.copy()
        kes = [c for c in uy.columns if c in TF]
        uy[kes] = False
        print("  TradFi elendi: %d sembol" % len(kes), flush=True)
    except Exception as e:
        print("  [!] tradfi_liste okunamadi (%s) - eleme YAPILMADI" % e)
    sk = SIN.rolling(D.FUNDING_PENCERE, min_periods=6).mean()

    # AKIS paneli: canli formulle birebir (carry_guncel_backtest.panel)
    tb, qv = {}, {}
    for p in glob.glob(os.path.join(R, "data_taker_genis", "*.csv")):
        s = os.path.basename(p)[:-4]
        if s in C.columns:
            d = pd.read_csv(p, parse_dates=["date"]).set_index("date")
            tb[s], qv[s] = d["tb_oran"], d["quote_volume"]
    TB = pd.DataFrame(tb).reindex(index=C.index, columns=C.columns)
    QV = pd.DataFrame(qv).reindex(index=C.index, columns=C.columns)
    AK = ((TB.rolling(30, min_periods=20).mean() - 0.5)
          * (QV.rolling(30, min_periods=20).mean()
             / QV.rolling(180, min_periods=120).mean()))
    print("  AKIS: %d sembol" % len(tb), flush=True)

    # OPEN / HIGH / LOW panelleri (motor TP ve takip cikisi icin ister)
    O, H, L = {}, {}, {}
    for yol in sorted(glob.glob(os.path.join(R, "data_genis", "*_4h.csv"))):
        s = os.path.basename(yol).replace("_4h.csv", "")
        if s not in C.columns:
            continue
        d = pd.read_csv(yol, parse_dates=["date"]).set_index("date")
        O[s], H[s], L[s] = d["open"], d["high"], d["low"]
    mk = lambda dd: pd.DataFrame(dd).reindex(index=C.index, columns=C.columns)
    O, H, L = mk(O), mk(H), mk(L)
    print("  OHL: %d sembol" % O.notna().any().sum(), flush=True)
    return C, ODE, sk, uy, AK, O, H, L, HAC, YAS, DON


def kur():
    C, ODE, sk, uy, AK, O, H, L, HAC, YAS, DON = paneller()
    pickle.dump({"C": C, "ODE": ODE, "sk": sk, "uy": uy, "AK": AK,
                 "H": H, "L": L}, open(ZEMIN, "wb"))
    pickle.dump({"C": C, "HAC": HAC, "YAS": YAS, "DON": DON},
                open(PANEL, "wb"))
    pickle.dump({"O": O, "H": H, "L": L}, open(HLO, "wb"))
    open(GPY, "w", encoding="utf-8").write(
        G_KAYNAK % {"kok": R, "zemin": ZEMIN})
    print("yazildi: %s · %s · %s · %s" % (ZEMIN, PANEL, HLO, GPY), flush=True)

    # 48 saatlik canli tahminci sinyali (madde 209'un penceresi)
    os.environ["PEN"] = "48"
    os.environ["AD"] = "bar48"
    import subprocess
    k = subprocess.run([sys.executable, os.path.join(R, "canli_sinyal_kur.py")],
                       cwd=R, capture_output=True, text=True, env=os.environ)
    print("canli_sinyal_kur.py cikis %d" % k.returncode, flush=True)
    if k.stdout.strip():
        print("  " + k.stdout.strip().splitlines()[-1])
    if k.returncode != 0:
        print("  [!] stderr: " + (k.stderr.strip().splitlines() or ["(yok)"])[-1])
    return kontrol()


def kontrol():
    tamam = True
    for y in (ZEMIN, PANEL, HLO, GPY, SK48):
        var = os.path.exists(y)
        print("  %-22s %s" % (os.path.basename(y), "VAR" if var else "YOK"))
        tamam = tamam and var
    return tamam


if __name__ == "__main__":
    if "--kontrol" in sys.argv:
        sys.exit(0 if kontrol() else 1)
    sys.exit(0 if kur() else 1)
