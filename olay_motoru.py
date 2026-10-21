#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLAY MOTORU (madde 400) — kullanıcının ±% hareket kuralının ölçülmüş bulgularla kurulmuş hali.

Bileşenler (her biri bir maddeye dayanır):
  * OLAY: 24 sa getiri >= +X -> SHORT adayı, <= −X -> LONG adayı (madde 187/380)
  * FUNDING FİLTRESİ: short yalnız son 24 sa funding >= 0 (long kalabalık,
    short funding ALIR); long yalnız funding <= 0 (madde 380, 398)
  * KARAR SAATİ: UTC 00 (03 TRT) ya da 04 (07 TRT) — gece saatleri işlem başı
    pozitif, öğleden sonra negatif (madde 399)
  * BOYUT: işlem başı 1/NMAX; NMAX 10 / 20 (madde 399: %25 boyut sermayeyi eritir)
  * STOP: girişten aleyhe %S (barın H/L'si), 0 = yok
  * TUTMA: H gün, 00/04 UTC kapanışında çık
  * YÖN: iki taraf ya da yalnız short
Maliyet: taker %0,05 x 2; gerçek funding. Aynı coinde açık işlem varken yeni olay yok.
Portföy: aynı gün olaylarından rastgele sıra (madde 395 düzeltmesi), en fazla NMAX açık.
"""
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import arastirma_m380_kullanici_kurali as K  # noqa: E402
import arastirma_m379_haftalik_pump_short as Y  # noqa: E402


@dataclass(frozen=True)
class Ayar:
    saat_utc: int = 0
    X: float = 0.30
    H: int = 1
    stop: float = 0.25
    nmax: int = 20
    yon: str = "iki"          # "iki" | "short"
    filtre: str = "FON"       # "yok" | "FON"

    def ad(self):
        return (f"{(self.saat_utc+3)%24:02d}TRT X{int(self.X*100)} H{self.H} S{int(self.stop*100)} "
                f"N{self.nmax} {self.yon} {self.filtre}")


_VERI = None


def veri():
    global _VERI
    if _VERI is None:
        _VERI = K.hazirla()
    return _VERI


def islemler(a: Ayar):
    C, O, H, L, F, uy, lsr, f24, r24, _ = veri()
    s = pd.Series(C.index.hour == a.saat_utc, index=C.index)
    out = []
    for yon in ((-1, 1) if a.yon == "iki" else (-1,)):
        kos = K.olay(r24, uy, lsr, f24, s, a.X, yon, a.filtre)
        out += K.islem(kos, C, O, H, L, F, a.H, a.stop, yon)
    return out


def portfoy(isl, idx, nmax, tohum=400):
    rng = np.random.default_rng(tohum)
    isl = [isl[k] for k in rng.permutation(len(isl))]
    acik, r = [], np.zeros(len(idx))
    for a, b, j, x in sorted(isl, key=lambda q: q[0]):
        acik = [c for c in acik if c > a]
        if len(acik) >= nmax:
            continue
        acik.append(b); r[b] += x / nmax
    s = pd.Series(r, index=idx)
    g = (1 + s).groupby(s.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index)
    return g


def olc(a: Ayar):
    C = veri()[0]
    isl = islemler(a)
    g = portfoy(isl, C.index, a.nmax)
    g = g[g.index >= "2022-04-01"]
    sh = lambda x: float(x.mean() / x.std() * np.sqrt(365.25)) if len(x) > 2 and x.std() > 0 else np.nan
    yil = lambda x: float(((1 + x).prod() ** (365.25 / len(x)) - 1) * 100) if len(x) else np.nan
    e = (1 + g).cumprod(); dd = float(((e / e.cummax()) - 1).min() * 100)
    IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
    rr = np.array([x[3] for x in isl]); tt = pd.DatetimeIndex([C.index[x[0]] for x in isl])
    gun = pd.Series(rr).groupby(tt.floor("D")).mean()
    gO = gun[gun.index >= "2025-01-01"]
    return dict(ad=a.ad(), ayar=a, n=len(rr), ort=rr.mean() * 100 if len(rr) else np.nan,
                med=np.median(rr) * 100 if len(rr) else np.nan,
                shIS=sh(IS), shOOS=sh(OOS), yilIS=yil(IS), yilOOS=yil(OOS), yil=yil(g), dd=dd,
                tgunOOS=float(gO.mean() / gO.std() * np.sqrt(len(gO))) if len(gO) > 2 else np.nan, g=g)
