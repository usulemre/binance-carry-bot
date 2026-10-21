#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 412 — GERÇEK ÖRNEK DIŞI: EYLÜL 2026 (GE2 + prim bu ayı hiç görmedi).

Zemin `indir_ek_ay.py 2026-09` + `yeniden_kur.py` ile 2026-09-30'a uzatıldı.
Bugünkü kitap (15x4 HAVUZ 4) ve G2P (yaş 60, hacim 70M, UCELE 0, prim 0,10)
2.000 D8 / 3.500 D2 x iki hiza koşulur (/tmp/m412).
ÖN KAYIT: (1) parite — 2022-07..2026-08 arası seriler eski koşularla (/tmp/m346)
uyuşmalı (fark < 1 puan/yıl), yoksa ölçüm geçersiz; (2) Eylül 2026 getirisi
G2P − bugün, dört hücre. Tek ay → yön işareti, karar değil.
"""
import os, sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

A.CIKTI = "/tmp/m412"
_E = {2000: M.D8, 3500: M.D2}
_G = {"YAS_GUN": "60", "UCELE": "0", "HACIM_ESIK": "7e7", "HAVUZ": "4"}
A.KOLLAR = {"BUGUN": ({"HAVUZ": "4"}, 4, _E), "G2P": (dict(_G, **M.PRIM), 4, _E)}

def gun(p):
    E = pd.read_pickle(p); r = E.pct_change().dropna()
    g = (1 + r).groupby(r.index.date).prod() - 1; g.index = pd.DatetimeIndex(g.index); return g

def analiz():
    for sev in (2000, 3500):
        for h in (0, 1):
            b = gun(f"/tmp/m412/M357_BUGUN_{sev}_{h}.pkl"); p = gun(f"/tmp/m412/M357_G2P_{sev}_{h}.pkl")
            eb = gun(f"/tmp/m346/T350_HAVUZ4_{sev}_{h}.pkl"); ep = gun(f"/tmp/m346/M357_G2P_{sev}_{h}.pkl")
            yil = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
            ix = eb.index.intersection(b.index)
            par_b = yil(b.loc[ix]) - yil(eb.loc[ix]); par_p = yil(p.loc[ix.intersection(ep.index)]) - yil(ep.loc[ix.intersection(ep.index)])
            ey = lambda x: ((1 + x[(x.index >= "2026-09-01")]).prod() - 1) * 100
            dd = lambda x: (((1 + x[x.index >= "2026-09-01"]).cumprod()).pipe(lambda e: (e / e.cummax() - 1).min()) * 100)
            print(f"{sev} hz{h} | parite fark bugun {par_b:+.2f} G2P {par_p:+.2f} puan/yil | EYLUL 2026: bugun {ey(b):+.2f}% (dusus {dd(b):.1f})  G2P {ey(p):+.2f}% (dusus {dd(p):.1f})  fark {ey(p)-ey(b):+.2f} puan")

if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
