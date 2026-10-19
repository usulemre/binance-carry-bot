#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 350 — BUGÜNÜN KİTABINDA (15 faz x 4 bacak) HİÇ TARANMAMIŞ BEŞ
AYARIN KOMŞU TARAMASI.

NEDEN: madde 222'nin yasası — "bir parametre taranmış ve optimumda ise,
o taramadan beri kabul edilen her değişiklik onu yeniden açar". Bu beş
ayar en son başka kitaplarda tarandı:
    HAVUZ 3,0      madde 224 (5 bacak) · 304 (13x3)
    REB 5 gün      madde 223 (5 bacak) · 304 (13x3)
    TPL 0,40       madde 227 (5 bacak) · 300 (13x3)
    TPS 0,20       madde 227 (5 bacak) · 300 (13x3)
    UCELE 0,40     madde 196
Bot 2.000-20.000 $ aralığında 15x4 koşuyor (madde 349) ve bu kitapta
hiçbiri taranmadı.

KOLLAR (her biri tek değişiklik, kontrolün iki yanı):
    HAVUZ 2 / 4 · REB_GUN 4 / 6 · TPL 0,30 / 0,50 · TPS 0,15 / 0,25 ·
    UCELE 0,30 / 0,50
SEVİYELER: 2.000 $ (D8) ve 3.500 $ (D2) — merdivenin iki farklı evreni.
Kontroller madde 346'nın K_* kolları.

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı):
  Bir kol bir seviyede GEÇER, ancak İKİ hizalamada da:
    (1) gecer_mi dört şartı geçer VE (2) eşli bootstrap P >= %80.
  AYAR DEĞİŞİKLİĞİ yalnız bir kol İKİ seviyede de geçerse önerilir
  (bot tek varsayılanla iki seviyede de koşacak).
  Çoklu bakış: 10 kol x 2 seviye. Madde 224'e göre beklenen isabet
  ~%20; tek seviyede tek hizada geçen kol bilgi sayılır, karar değil.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import karar_kurali as KK  # noqa: E402
import arastirma_m346_prim as M  # noqa: E402

CIKTI = M.CIKTI
KOLLAR = {
    "HAVUZ2": {"HAVUZ": "2"}, "HAVUZ4": {"HAVUZ": "4"},
    "REB4": {"REB_GUN": "4"}, "REB6": {"REB_GUN": "6"},
    "TPL30": {"TPL": "0.30"}, "TPL50": {"TPL": "0.50"},
    "TPS15": {"TPS": "0.15"}, "TPS25": {"TPS": "0.25"},
    "UC30": {"UCELE": "0.30"}, "UC50": {"UCELE": "0.50"},
}
SEVIYE = {2000: M.D8, 3500: M.D2}


def tek(kol, sev, h):
    ad = f"T350_{kol}_{sev}_{h}"
    pkl = os.path.join(CIKTI, ad + ".pkl")
    if os.path.exists(pkl):
        return ad, "var"
    env = dict(os.environ, **dict(M.TABAN, **KOLLAR[kol]), FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(SEVIYE[sev]), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", str(M.BACAK)], cwd=KOK,
                           env=env, stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    isler = [(k, s, h) for s in SEVIYE for k in KOLLAR for h in M.HIZA]
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek(*a), isler):
            print(ad, d, flush=True)


def analiz():
    print(f"{'kol':<7} {'bak':>4} {'hz':>2} {'yillik':>7} {'Sh22':>5} {'Sh25':>5} "
          f"{'dusus':>6} {'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5} {'med':>6}")
    gecis = {}
    for kol in KOLLAR:
        for sev in SEVIYE:
            n = 0
            for h in M.HIZA:
                gk, ga = M.gunluk(f"K_{sev}_{h}"), M.gunluk(f"T350_{kol}_{sev}_{h}")
                K, A = M.olcum("K", gk), M.olcum(kol, ga)
                s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, med = M.bootstrap(gk, ga, n=1000)
                isaret = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                print(f"{kol:<7} {sev:>4} {h:>2} {A.getiri - K.getiri:>+7.1f} "
                      f"{A.erken - K.erken:>+5.2f} {A.gec - K.gec:>+5.2f} "
                      f"{A.dusus - K.dusus:>+6.1f} {s['esit_risk'] - K.getiri:>+7.1f} "
                      f"{s['kaldirac']:>5.2f} {isaret:>5} {p:>5.1f} {med:>+6.1f}")
                n += int(s["gecer"] and p >= M.KANIT_BARI)
            gecis[(kol, sev)] = n
    print("\n(sutunlar kontrole gore FARK: yillik, Sharpe, dusus puani, esit-risk)\n")
    for kol in KOLLAR:
        seviyeler = [s for s in SEVIYE if gecis[(kol, s)] == len(M.HIZA)]
        if len(seviyeler) == len(SEVIYE):
            hk = "AYAR DEGISIKLIGI ONERILIR (iki seviyede de gecti)"
        elif seviyeler:
            hk = f"yalniz {seviyeler} $'da gecti - KARAR DEGIL"
        else:
            hk = "RED"
        print(f"HUKUM {kol:<7}: {hk}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
