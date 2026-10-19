#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 347 — MADDE 305'İN TREND SLEEVE'İ BUGÜNÜN KİTABINDA (15 faz x 4
bacak), YENİDEN KURULAN ZEMİNDE, KURULABİLDİĞİ SERMAYE SEVİYELERİNDE.

Madde 305 sleeve'i 13x3 kitabına karşı ölçmüştü. Madde 341'den beri
bot 2.000-8.361 $ aralığında 15x4 koşuyor; sleeve hiç bu kitaba karşı
ölçülmedi (madde 305'in yasası: değer ana kitabın dozuna aittir).

KURULABİLİRLİK (madde 305: sleeve REZERV=0, taban pay 0,5; asgari bacak 10 $):
    carry bacağı  = (1-w) * B * 0,4 / 60
    sleeve bacağı =  w    * B * 0,5 / 60     (w=0,3 -> B/400)
    2.000 $ -> sleeve 5,00 $   KURULAMAZ
    3.500 $ -> sleeve 8,75 $   KURULAMAZ
    4.000 $ -> sleeve 10,00 $ (D9) · carry 18,67 $ (D8)
    8.361 $ -> sleeve 20,90 $ (D2) · carry 39,02 $ (D1)

SLEEVE: g33, SK_DOSYA = 1 günlük momentum paneli, REZERV=0. Panel
nedensel: C[i]/C[i-6]-1. İşaret koşuyla doğrulanır (madde 298'in
"kazananı long" kolu, kayıtlı 13x3 tam evren Sharpe 2,655).
PLASEBO: aynı panelin her satırı kesitsel karıştırılmış hâli.
HARMAN: günlük getiri düzeyinde (1-w)*carry + w*sleeve (sermaye bölünür).

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı), w = 0,3 (madde 305'in noktası):
  KABUL ancak bir sermaye seviyesinde İKİ hizalamada da:
    (1) gecer_mi dört şartı geçer,
    (2) eşli blok bootstrap P(eşit-risk farkı > 0) >= %80,
    (3) mom harmanının P'si plasebo harmanınınkinden yüksek.
  Şart 4'ten tek başına düşerse sonuç "KALDIRAÇ KARARI" olarak ayrı
  raporlanır (madde 225), KABUL sayılmaz. w=0,1/0,2 yalnız bilgi.
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
import arastirma_m346_prim as M  # noqa: E402  (aynı ölçüm fonksiyonları)

CIKTI = "/tmp/m347"
D9 = M.D8 + ["AVAXUSDT"]
SEVIYE = {4000: (M.D8, D9), 8361: (M.D1, M.D2)}   # (carry kümesi, sleeve kümesi)
CARRY_PKL = {4000: "K_2000", 8361: "K_8361"}      # madde 346'nın kontrolleri
W = (0.1, 0.2, 0.3)
W_KARAR = 0.3


def panel_kur():
    P = pickle.load(open("/tmp/panel.pkl", "rb"))
    C = P["C"]
    mom = C / C.shift(6) - 1
    rng = np.random.default_rng(347)
    v = mom.values.copy()
    for i in range(v.shape[0]):
        m = np.isfinite(v[i])
        v[i, m] = rng.permutation(v[i, m])
    pickle.dump(-mom, open(f"{CIKTI}/mom_kazanan.pkl", "wb"))       # düşük skor = LONG
    pickle.dump(mom, open(f"{CIKTI}/mom_kaybeden.pkl", "wb"))
    pickle.dump(-pd.DataFrame(v, index=C.index, columns=C.columns),
                open(f"{CIKTI}/mom_plasebo.pkl", "wb"))


def tek(ad, panel, haric, h):
    pkl = f"{CIKTI}/{ad}.pkl"
    if os.path.exists(pkl):
        return ad, "var"
    env = dict(os.environ, **M.TABAN, REZERV="0", SK_DOSYA=f"{CIKTI}/{panel}.pkl",
               FAZ_KAY=str(h), SEMBOL_HARIC=",".join(haric), E_CIKTI=pkl)
    with open(f"{CIKTI}/{ad}.txt", "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", str(M.BACAK)], cwd=KOK,
                           env=env, stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    os.makedirs(CIKTI, exist_ok=True)
    if not os.path.exists(f"{CIKTI}/mom_plasebo.pkl"):
        panel_kur()
    isler = [("ISARET_kazanan_0", "mom_kazanan", [], 0),
             ("ISARET_kaybeden_0", "mom_kaybeden", [], 0)]
    for sev, (_, sk) in SEVIYE.items():
        for h in M.HIZA:
            isler += [(f"S_{sev}_{h}", "mom_kazanan", sk, h),
                      (f"SP_{sev}_{h}", "mom_plasebo", sk, h)]
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek(*a), isler):
            print(ad, d, flush=True)


def _g(path):
    E = pickle.load(open(path, "rb"))
    r = E.pct_change().dropna()
    g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index)
    return g


def analiz():
    for ad in ("ISARET_kazanan_0", "ISARET_kaybeden_0"):
        O = M.olcum(ad, _g(f"{CIKTI}/{ad}.pkl"))
        print(f"{ad:<20} yillik {O.getiri:+.1f} Sh {O.sharpe:.3f} dusus -{O.dusus:.1f}")
    print()
    print(f"{'bakiye':>6} {'hz':>2} {'kol':<9} {'yillik':>7} {'Sh':>5} {'Sh22':>5} "
          f"{'Sh25':>5} {'dusus':>6} {'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5} {'rho':>5}")
    hukum = {}
    for sev in SEVIYE:
        gecen, kaldirac_ile = 0, 0
        for h in M.HIZA:
            gk = M.gunluk(f"{CARRY_PKL[sev]}_{h}")
            gs = _g(f"{CIKTI}/S_{sev}_{h}.pkl")
            gp = _g(f"{CIKTI}/SP_{sev}_{h}.pkl")
            ix = gk.index.intersection(gs.index).intersection(gp.index)
            gk, gs, gp = gk.loc[ix], gs.loc[ix], gp.loc[ix]
            K = M.olcum("K", gk)
            print(f"{sev:>6} {h:>2} {'K':<9} {K.getiri:>+7.1f} {K.sharpe:>5.2f} "
                  f"{K.erken:>5.2f} {K.gec:>5.2f} {-K.dusus:>6.1f}")
            S = M.olcum("S", gs)
            print(f"{sev:>6} {h:>2} {'sleeve':<9} {S.getiri:>+7.1f} {S.sharpe:>5.2f} "
                  f"{S.erken:>5.2f} {S.gec:>5.2f} {-S.dusus:>6.1f} {'':>7} {'':>5} {'':>5} "
                  f"{'':>5} {np.corrcoef(gk, gs)[0, 1]:>5.2f}")
            sonuc_w = {}
            for w in W:
                for etk, gx in (("mom", gs), ("plasebo", gp)):
                    ga = (1 - w) * gk + w * gx
                    A = M.olcum(etk, ga)
                    s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                    p, _ = M.bootstrap(gk, ga, n=1000)
                    sonuc_w[(w, etk)] = (s, p)
                    isaret = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                    print(f"{sev:>6} {h:>2} {etk[:3]+' w'+str(w):<9} {A.getiri:>+7.1f} "
                          f"{A.sharpe:>5.2f} {A.erken:>5.2f} {A.gec:>5.2f} {-A.dusus:>6.1f} "
                          f"{s['esit_risk']:>+7.1f} {s['kaldirac']:>5.2f} {isaret:>5} {p:>5.1f}")
            s, p = sonuc_w[(W_KARAR, "mom")]
            _, pp = sonuc_w[(W_KARAR, "plasebo")]
            ilk3 = all(v[0] for k, v in list(s["sartlar"].items())[:3])
            if p >= M.KANIT_BARI and p > pp:
                if s["gecer"]:
                    gecen += 1
                elif ilk3:
                    kaldirac_ile += 1
        n = len(M.HIZA)
        hukum[sev] = ("KABUL" if gecen == n else
                      "KALDIRAÇ KARARI (yalnız şart 4)" if gecen + kaldirac_ile == n else
                      f"RED ({gecen}/{n} kabul, {kaldirac_ile}/{n} şart-4)")
    print()
    for sev in (2000, 3500):
        print(f"HUKUM {sev} $: KURULAMAZ (sleeve bacağı {0.3 * sev * 0.5 / 60:.2f} $ < 10 $)")
    for sev, hk in hukum.items():
        print(f"HUKUM {sev} $: {hk}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
