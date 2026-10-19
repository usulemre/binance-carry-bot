#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 346 — MADDE 288 (PRİM-ÖLÇEKLİ BRÜT, CARRY_PRIM_E=0.10) YENİDEN
KURULAN ZEMİNDE, ÜÇ SERMAYE SEVİYESİNDE, İKİ HİZALAMADA YENİDEN ÖLÇÜLDÜ.

NEDEN: madde 288'in kodu ve ölçümü konteyner kaybından önceydi; kurtarılan
kayıt aday için yalnız tek bir sayı taşıyor (+8,24 → +177,07, 2.000 $).
Sermaye seviyesine göre hiç ölçülmemişti ve kullanıcı "hepsi" dedi.

KİTAPLAR (madde 341'in 4 bacak tavanı; bacak = bakiye*0,4/(15*4)):
    2.000 $ → bacak 13,33 $ → D8 (BTC,QNT,ETH,BCH,LTC,ETC,LINK,AAVE elenir)
    3.500 $ → bacak 23,33 $ → D2 (BTC,QNT)
    8.361 $ → bacak 55,74 $ → D1 (BTC)
Eleme basamakları madde 295'in borsa tablosundan.

KOLLAR (her biri FAZ_KAY 0 ve 1 ile, ayrı ayrı):
    K   kontrol (bugünün kitabı)
    P   BRUT_PRIM=0.10 REF=150 ALT=0.5 UST=1.5   (carry_bot varsayılanları)
    PK  P + BRUT_PLASEBO=2  (aynı çarpan dağılımı, zamanda KARIŞTIRILMIŞ)
    PT  P + BRUT_PLASEBO=1  (zamanda TERS)

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı):
  KABUL, ancak bir sermaye seviyesinde İKİ hizalamada da:
    (1) karar_kurali.gecer_mi dört şartı geçer, VE
    (2) eşli blok bootstrap'ta P(eşit-risk farkı > 0) >= %80 (KANIT_BARI), VE
    (3) aday P'si karıştırılmış plaseboun P'sinden yüksektir.
  Hizalamaların ORTALAMASI kullanılmaz (madde 323: canlı botun sahip
  olmadığı bir çeşitlendirme).

KULLANIM
    python3 arastirma_m346_prim.py kos      # 24 koşu, 2 paralel
    python3 arastirma_m346_prim.py analiz   # tablo + hüküm
"""
import os
import pickle
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import karar_kurali as KK  # noqa: E402

CIKTI = "/tmp/m346"
TABAN = dict(HAVUZ="3", REZ_ESIK="0.015", KAP="0.05", TP="0.4", TPL="0.40",
             TPS="0.20", UCELE="0.40", REB_GUN="5", FAZ="15", REZERV="0.20",
             SK_DOSYA="/tmp/sk_bar48.pkl")
D1 = ["BTCUSDT"]
D2 = D1 + ["QNTUSDT"]
D8 = D2 + ["ETHUSDT", "BCHUSDT", "LTCUSDT", "ETCUSDT", "LINKUSDT", "AAVEUSDT"]
SEVIYE = {2000: D8, 3500: D2, 8361: D1}
BACAK = 4
PRIM = dict(BRUT_PRIM="0.10", BRUT_REF="150", BRUT_ALT="0.5", BRUT_UST="1.5")
KOLLAR = {"K": {}, "P": PRIM, "PK": dict(PRIM, BRUT_PLASEBO="2"),
          "PT": dict(PRIM, BRUT_PLASEBO="1")}
HIZA = (0, 1)
KANIT_BARI = 80.0
BOOT_N = 2000
BLOK_GUN = 20


def _ad(kol, sev, h):
    return f"{kol}_{sev}_{h}"


def tek_kos(kol, sev, h):
    ad = _ad(kol, sev, h)
    pkl = os.path.join(CIKTI, ad + ".pkl")
    if os.path.exists(pkl):
        return ad, "var"
    env = dict(os.environ, **TABAN, **KOLLAR[kol], FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(SEVIYE[sev]), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", str(BACAK)],
                           cwd=KOK, env=env, stdout=f, stderr=subprocess.STDOUT,
                           timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    os.makedirs(CIKTI, exist_ok=True)
    isler = [(k, s, h) for s in SEVIYE for k in KOLLAR for h in HIZA]
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek_kos(*a), isler):
            print(ad, d, flush=True)


def gunluk(ad):
    E = pickle.load(open(os.path.join(CIKTI, ad + ".pkl"), "rb"))
    r = E.pct_change().dropna()
    g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index)
    return g


def _sharpe(r):
    r = np.asarray(r, float)
    return float(r.mean() / r.std() * np.sqrt(365.25)) if r.std() > 0 else np.nan


def olcum(ad, g):
    y, dd = KK._stat(g.values)
    e, l = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
    return KK.Olcum(ad, y * 100, _sharpe(g), _sharpe(e), _sharpe(l), dd * 100)


def _esit_risk_fark(rk, ra):
    """Adayı kontrolün düşüşüne GERÇEKTEN kaldıraçla, getiri farkı (puan)."""
    yk, ddk = KK._stat(rk)
    if not (ddk == ddk):
        return np.nan
    _, er, _ = KK.esit_risk_gercek(ra, ddk * 100, ust=4.0)
    return er - yk * 100


def bootstrap(gk, ga, n=BOOT_N, blok=BLOK_GUN, tohum=346):
    """Eşli DURAĞAN blok bootstrap: aynı günler iki seriden birlikte çekilir."""
    ix = gk.index.intersection(ga.index)
    rk, ra = gk.loc[ix].values, ga.loc[ix].values
    T = len(ix)
    rng = np.random.default_rng(tohum)
    farklar = np.empty(n)
    for b in range(n):
        idx = np.empty(T, int)
        t = 0
        while t < T:
            bas = rng.integers(T)
            L = min(rng.geometric(1.0 / blok), T - t)
            idx[t:t + L] = (bas + np.arange(L)) % T
            t += L
        farklar[b] = _esit_risk_fark(rk[idx], ra[idx])
    f = farklar[np.isfinite(farklar)]
    return float((f > 0).mean() * 100), float(np.median(f))


def analiz():
    satirlar, hukum = [], {}
    for sev in SEVIYE:
        gecen_hiza = 0
        for h in HIZA:
            gk = gunluk(_ad("K", sev, h))
            K = olcum("K", gk)
            satirlar.append((sev, h, "K", K, None, None, None))
            P_boot = {}
            for kol in ("P", "PK", "PT"):
                ga = gunluk(_ad(kol, sev, h))
                A = olcum(kol, ga)
                sonuc = KK.gecer_mi(K, A, gunluk_kontrol=gk.values,
                                    gunluk_aday=ga.values)
                p, med = bootstrap(gk, ga)
                P_boot[kol] = p
                satirlar.append((sev, h, kol, A, sonuc, p, med))
            ana = [s for s in satirlar if s[0] == sev and s[1] == h and s[2] == "P"][0]
            if ana[4]["gecer"] and P_boot["P"] >= KANIT_BARI and P_boot["P"] > P_boot["PK"]:
                gecen_hiza += 1
        hukum[sev] = "KABUL" if gecen_hiza == len(HIZA) else f"RED ({gecen_hiza}/{len(HIZA)} hiza)"

    print(f"{'bakiye':>6} {'hz':>2} {'kol':<3} {'yillik':>7} {'Sh':>5} {'Sh22':>5} "
          f"{'Sh25':>5} {'dusus':>6} {'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5} {'med':>6}")
    for sev, h, kol, O, s, p, med in satirlar:
        if s is None:
            print(f"{sev:>6} {h:>2} {kol:<3} {O.getiri:>+7.1f} {O.sharpe:>5.2f} "
                  f"{O.erken:>5.2f} {O.gec:>5.2f} {-O.dusus:>6.1f}")
        else:
            isaret = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
            print(f"{sev:>6} {h:>2} {kol:<3} {O.getiri:>+7.1f} {O.sharpe:>5.2f} "
                  f"{O.erken:>5.2f} {O.gec:>5.2f} {-O.dusus:>6.1f} "
                  f"{s['esit_risk']:>+7.1f} {s['kaldirac']:>5.2f} {isaret:>5} "
                  f"{p:>5.1f} {med:>+6.1f}")
    print()
    for sev, hk in hukum.items():
        print(f"HUKUM {sev} $: {hk}")
    pickle.dump({"satirlar": [(a, b, c, d.__dict__, (e or {}).get("gecer"),
                               (e or {}).get("esit_risk"), (e or {}).get("kaldirac"), f, g)
                              for a, b, c, d, e, f, g in satirlar],
                 "hukum": hukum}, open(os.path.join(CIKTI, "sonuc.pkl"), "wb"))


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
