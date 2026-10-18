#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""METRİK PANELİNİ KURAR (madde 335) — iki adım, ikisi de projede eksikti.

MADDE 335: motorun `ls` kolu `/tmp/metrik_panel.pkl` istiyor
(`count_long_short_ratio` vb.) ama o dosyayı üreten iki adım **projede
hiç yoktu**; madde 253'ün `YENIDEN_KURMA` tarifi anlatıyor, betiği
yazılmamıştı. 2026-10-19'daki konteyner kaybında dosya gitti ve
yeniden üretilemedi. Artık üretilebilir.

ADIM 1 — `cift`: hangi sembol-günler indirilecek. Tarif: "Yalnızca
UYGUN günler + 35 gün ısınma indirilir (tam geçmiş DEĞİL) -> ~125 bin
dosya". Uygunluk maskesi `carry_denetim.uygunluk` ile hesaplanır, yani
indirilecek küme motorun kendi evreninden türetilir.

ADIM 2 — panel: `indir_metrik.py`'nin ürettiği UZUN tabloyu (date,
sembol, 5 metrik) metrik adına göre GENİŞ panellere çevirir ve C'nin
ızgarasına oturtur.

KULLANIM
    python metrik_kur.py cift        # /tmp/metrik_cift.pkl uret
    python metrik_kur.py panel       # /tmp/metrik4.pkl -> /tmp/metrik_panel.pkl
"""
from __future__ import annotations

import os
import pickle
import sys

import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)

ZEMIN = "/tmp/zemin.pkl"
CIFT = "/tmp/metrik_cift.pkl"
HAM = "/tmp/metrik4.pkl"
PANEL = "/tmp/metrik_panel.pkl"
ISINMA_GUN = 35
KOL = ["sum_open_interest_value", "count_toptrader_long_short_ratio",
       "sum_toptrader_long_short_ratio", "count_long_short_ratio",
       "sum_taker_long_short_vol_ratio"]


def cift_uret():
    z = pickle.load(open(ZEMIN, "rb"))
    C, uy = z["C"], z["uy"]
    gun = pd.Series(C.index.date, index=C.index)
    ciftler = set()
    for s in C.columns:
        m = uy[s].fillna(False).values
        if not m.any():
            continue
        g = sorted(set(gun[m]))
        ilk = g[0] - pd.Timedelta(days=ISINMA_GUN).to_pytimedelta()
        for d in pd.date_range(ilk, g[-1], freq="D").date:
            ciftler.add((s, d.isoformat()))
    ciftler = sorted(ciftler)
    pickle.dump(ciftler, open(CIFT, "wb"))
    sem = len({s for s, _ in ciftler})
    print("cift: %d sembol-gun, %d sembol -> %s" % (len(ciftler), sem, CIFT))
    return len(ciftler) > 0


def panel_uret():
    D = pickle.load(open(HAM, "rb"))
    if "date" not in D.columns and "bar" in D.columns:
        D = D.rename(columns={"bar": "date"})
    print("ham: %d satir, %d sembol" % (len(D), D.sembol.nunique()))
    z = pickle.load(open(ZEMIN, "rb"))
    C = z["C"]
    M = {}
    for k in KOL:
        if k not in D.columns:
            print("  [!] %s ham tabloda YOK" % k)
            continue
        p = (D.pivot_table(index="date", columns="sembol", values=k,
                           aggfunc="last")
             .reindex(index=C.index, columns=C.columns))
        M[k] = p
        print("  %-38s %d hucre dolu" % (k, int(p.notna().sum().sum())))
    pickle.dump(M, open(PANEL, "wb"))
    print("yazildi:", PANEL)
    return len(M) == len(KOL)


if __name__ == "__main__":
    ne = sys.argv[1] if len(sys.argv) > 1 else "cift"
    ok = cift_uret() if ne == "cift" else panel_uret()
    sys.exit(0 if ok else 1)
