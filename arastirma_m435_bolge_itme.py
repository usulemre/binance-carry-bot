#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 435 — R30Y60S BÖLGESİNİ İTME (iyileşen yönlerin birleşimi ve uzatılması).

Madde 433 komşuları IS→OOS sırası Spearman 0,75 (bölge içi ayar burada GENELLİYOR, madde 427'nin
aksine); IS'te 1. olan TPL 0,50 OOS'ta da 1. İyileşen yönler: TPL↑, REZ↓, TPS↑.
KOLLAR (2.000 $ D8, iki hiza, kaymalı; taban R30Y60S):
  T60 (TPL 0,60) · T70 (TPL 0,70) · T50R05 (TPL 0,50 + REZ 0,05) ·
  T50R05S25 (+ TPS 0,25) · T60R05S25 · T50S25
ÖN KAYIT: SEÇİM yalnız IS (2022-07..2024-12) yıllık getirisiyle; IS 1.'si OOS'ta R30Y60S'i
geçer ve dd R30Y60S'ten 3 puandan fazla kötü değilse → iki seviye protokole (madde 436).
"""
import os, sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
B = dict(HAVUZ="4", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60",
         HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", AGIRLIK_KAYMA="1")
DEG = {"T60": {"TPL": "0.60"}, "T70": {"TPL": "0.70"}, "T50R05": {"TPL": "0.50", "REZERV": "0.05"},
       "T50R05S25": {"TPL": "0.50", "REZERV": "0.05", "TPS": "0.25"},
       "T60R05S25": {"TPL": "0.60", "REZERV": "0.05", "TPS": "0.25"}, "T50S25": {"TPL": "0.50", "TPS": "0.25"}}
A.KOLLAR = {a: ({**B, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    YIL = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
    DD = lambda x: (((1 + x).cumprod() / (1 + x).cumprod().cummax()) - 1).min() * 100
    ad = ["KAYMA", "R30Y60S", "NTL50"] + list(A.KOLLAR)
    G = {a: (M.gunluk(f"M357_{a}_2000_0") + M.gunluk(f"M357_{a}_2000_1")) / 2 for a in ad}
    D = pd.DataFrame(G).dropna()
    IS, OOS = D[D.index < "2025-01-01"], D[D.index >= "2025-01-01"]
    s26 = lambda x: ((1 + x[x.index >= "2026-07-01"]).prod() - 1) * 100
    t = pd.DataFrame({"yIS": IS.apply(YIL), "yOOS": OOS.apply(YIL), "yTAM": D.apply(YIL), "dd": D.apply(DD),
                      "TemEyl26": D.apply(s26)}).sort_values("yIS", ascending=False)
    print(t.round(1).to_string())
    aday = [a for a in t.index if a in A.KOLLAR][0]
    r = t.loc["R30Y60S"]; c = t.loc[aday]
    gec = c.yOOS > r.yOOS and c.dd >= r.dd - 3
    print(f"\nIS'te 1. yeni kol: {aday} -> OOS {c.yOOS:+.1f} vs R30Y60S {r.yOOS:+.1f}, dd {c.dd:.1f} vs {r.dd:.1f} -> "
          f"{'PROTOKOLE' if gec else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
