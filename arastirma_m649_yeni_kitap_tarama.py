#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 649 — YENİ KİTAP TARAMASI (kullanıcı: "farklı bir kitap kovalayalım, sen seç"). Carry'den AYRI, piyasa-nötr kesitsel kitaplar,
daha önce BAĞIMSIZ kitap olarak hiç sınanmamış sinyallerle (metrik paneli: OI, top-trader / genel long-short oranı, taker oranı; hacim).
Denenmişler hariç: momentum / ters dönüş (381-383, 411), MAX / IVOL / SIZE (411), ML (389), BTC trend (459), olay aileleri (579).
Kurulum (madde 411 ile aynı): 00 UTC günlük, H günde bir yeniden kurma, beşte birlik L/S, eşit ağırlık, brüt 1 (0,5 + 0,5), gerçek funding,
devir × 5 bp. Evren: hacim ≥ 20 M$, yaş ≥ 90 g, TradFi hariç. Metrik verisi 2022-06'dan.
SİNYALLER (yüksek değer = sinyal; her biri İKİ yönde, H ∈ {1, 3, 7}):
  OI7 / OI1    açık pozisyon 7 g / 1 g değişimi          OIPR   OI 3 g değişimi − fiyat 3 g değişimi (fiyatsız kaldıraç birikimi)
  TOP          top-trader hesap long/short oranı           TOPF   log(top oranı) − log(genel oran) ("akıllı para" − kalabalık)
  TAK1 / TAK7  taker alış/satış hacim oranı 1 g / 7 g ort.  HACS   1 g hacim / 30 g medyan (anormal hacim)
  AMI          Amihud illikitlik (|r| / hacim, 30 g)        FVOL   funding oynaklığı (30 g std)
ELEK (koşudan ÖNCE; çoklu bakış 10 × 2 × 3 = 60 → madde 411'den sıkı): IS (2022-06..2024-12) Sh ≥ 0,7 VE OOS (2025-01..2026-09) Sh ≥ 1,0,
OOS plasebo farkı ≥ 0,5, en kötü yıl > 0, carry (T7K + KS) rho ≤ 0,30, yıllık ≥ +%15. Geçen → komşuluk + 4 sa doğrulama turu.
"""
import os, sys, pickle
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m381_cok_ufuk as U
import arastirma_m346_prim as M

C, Fd, uy = U.yukle()
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = z["C"]; sec = C4.index.hour == 0
F4 = z["ODE"].reindex_like(C4)
MP = pickle.load(open("/tmp/zu/metrik_panel.pkl", "rb"))
P = pickle.load(open("/tmp/panel.pkl", "rb")); HAC4 = P["HAC"].reindex_like(C4)


def gun(x):            # 4 sa panelden 00 UTC satırı
    return x.reindex_like(C4)[sec].reindex_like(C)


def gun_ort(x, n):     # son n gün (6n bar) ortalaması, 00 UTC'de
    return x.reindex_like(C4).rolling(6 * n, min_periods=3 * n).mean()[sec].reindex_like(C)


OI = gun(MP["sum_open_interest_value"]); TOP = gun(MP["count_toptrader_long_short_ratio"]); GLS = gun(MP["count_long_short_ratio"])
TAKr = MP["sum_taker_long_short_vol_ratio"]
r1 = C / C.shift(1) - 1; HACg = gun(HAC4)
S = {
    "OI7": OI / OI.shift(7) - 1, "OI1": OI / OI.shift(1) - 1,
    "OIPR": (OI / OI.shift(3) - 1) - (C / C.shift(3) - 1),
    "TOP": np.log(TOP), "TOPF": np.log(TOP) - np.log(GLS),
    "TAK1": gun_ort(TAKr, 1), "TAK7": gun_ort(TAKr, 7),
    "HACS": HACg / HACg.rolling(30).median(),
    "AMI": (r1.abs() / HACg).rolling(30).mean(),
    "FVOL": F4.fillna(0).rolling(180).std()[sec].reindex_like(C),
}
M.CIKTI = "/tmp/m622"
carry = sum(M.gunluk(f"M357_EK_P3T2_2000_{h}") for h in (0, 1)) / 2
sh = lambda g: g.mean() / g.std() * np.sqrt(365.25) if len(g) > 20 and g.std() > 0 else np.nan
yil = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100


def kur(rk, yon, H):
    W = ((rk >= 0.8).astype(float) - (rk <= 0.2).astype(float)) * yon
    lo = W.clip(lower=0); so = (-W).clip(lower=0)
    W = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 0.5 - so.div(so.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 0.5
    return U.getiri(W, C, Fd, H)


BAS = "2022-06-15"
satir = []
for ad, sig in S.items():
    rk = sig.where(uy & sig.notna()).rank(axis=1, pct=True)
    v = rk.values.copy(); rng = np.random.default_rng(649)
    for i in range(v.shape[0]):
        m = np.isfinite(v[i]); v[i, m] = rng.permutation(v[i, m])
    rkp = pd.DataFrame(v, index=rk.index, columns=rk.columns)
    for H in (1, 3, 7):
        for yon, yad in ((+1, "YÜKSEK LONG"), (-1, "YÜKSEK SHORT")):
            g = kur(rk, yon, H); g = g[g.index >= BAS]
            gp = kur(rkp, yon, H); gp = gp[gp.index >= BAS]
            IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
            e = (1 + g).cumprod(); dd = ((e / e.cummax()) - 1).min() * 100
            yy = g.groupby(g.index.year).apply(yil)
            ix = g.index.intersection(carry.index); rho = np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1]
            pla = sh(gp[gp.index >= "2025-01-01"])
            gec = (sh(IS) >= 0.7 and sh(OOS) >= 1.0 and sh(OOS) - pla >= 0.5 and yy.min() > 0 and rho <= 0.30 and yil(g) >= 15)
            satir.append(dict(sinyal=ad, H=H, yon=yad, IS=sh(IS), OOS=sh(OOS), yil=yil(g), dd=dd, kotu_yil=yy.min(), pla=pla, rho=rho,
                              sonuc="GEÇTİ" if gec else ""))
            g.to_pickle(f"/tmp/m649/{ad}_{H}_{yon}.pkl")
T = pd.DataFrame(satir)
pd.set_option("display.width", 200)
print(T.round(2).to_string(index=False))
T.to_pickle("/tmp/m649/tablo.pkl")
