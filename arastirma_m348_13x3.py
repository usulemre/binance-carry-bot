#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 348 — MADDE 325'İN 13 FAZ x 3 BACAK ADAYI, YENİ ZEMİNDE, BUGÜNÜN
KİTABINA (15 faz x 4 bacak) KARŞI, ÜÇ SERMAYE SEVİYESİNDE.

Madde 325 (kodu kayıp, metni kullanıcının kaydından kurtarıldı):
13 faz x 3 bacak, D2, 20,51 $ -> +176,37 net (+7,54), P(Sh) %68,9, dört
şart YYYY, "kanıt barının ALTINDA; sicile aday olarak girdi, ayar
değişikliği olarak GİRMEDİ". Faz ofsetleri 30 bara eşit aralıklı, bara
yuvarlanmış: [0,2,5,7,9,12,14,16,18,21,23,25,28] (g33 FAZ_LISTE, madde 338).

Mekanizma: daha az pozisyon -> daha büyük bacak -> majorler evrene geri
döner (madde 295 basamakları), bedeli faz çeşitlendirmesi (15 -> 13).

    bakiye   13x3 bacak  evren      15x4 bacak  evren
    2.000 $   20,51 $    D2         13,33 $     D8
    3.500 $   35,90 $    D1         23,33 $     D2
    8.361 $   85,76 $    TAM (D0)   55,74 $     D1

Canlıda kurulumu: CARRY_N_DILIM=13 CARRY_N_LEGS=3.

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı): KABUL ancak bir sermaye
seviyesinde İKİ hizalamada da (1) gecer_mi dört şartı geçer VE
(2) eşli blok bootstrap P(eşit-risk farkı > 0) >= %80.
Plasebo yok: aday bir sinyal değil yapı değişikliği; kontrol zaten
aynı sinyali taşıyor.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import karar_kurali as KK  # noqa: E402
import arastirma_m346_prim as M  # noqa: E402

CIKTI = M.CIKTI            # kontroller (K_*) zaten orada
FAZ_LISTE = "0,2,5,7,9,12,14,16,18,21,23,25,28"
EVREN = {2000: M.D2, 3500: M.D1, 8361: []}


def tek(sev, h):
    ad = f"T13_{sev}_{h}"
    pkl = os.path.join(CIKTI, ad + ".pkl")
    if os.path.exists(pkl):
        return ad, "var"
    env = dict(os.environ, **dict(M.TABAN, FAZ="13"), FAZ_LISTE=FAZ_LISTE,
               FAZ_KAY=str(h), SEMBOL_HARIC=",".join(EVREN[sev]), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "3"], cwd=KOK, env=env,
                           stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek(*a), [(s, h) for s in EVREN for h in M.HIZA]):
            print(ad, d, flush=True)


def analiz():
    print(f"{'bakiye':>6} {'hz':>2} {'kol':<5} {'yillik':>7} {'Sh':>5} {'Sh22':>5} "
          f"{'Sh25':>5} {'dusus':>6} {'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5} {'med':>6}")
    hukum = {}
    for sev in EVREN:
        gecen = 0
        for h in M.HIZA:
            gk, ga = M.gunluk(f"K_{sev}_{h}"), M.gunluk(f"T13_{sev}_{h}")
            K, A = M.olcum("K", gk), M.olcum("13x3", ga)
            s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
            p, med = M.bootstrap(gk, ga)
            isaret = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
            for ad, O, ek in (("15x4", K, ""),
                              ("13x3", A, f" {s['esit_risk']:>+7.1f} {s['kaldirac']:>5.2f} "
                                          f"{isaret:>5} {p:>5.1f} {med:>+6.1f}")):
                print(f"{sev:>6} {h:>2} {ad:<5} {O.getiri:>+7.1f} {O.sharpe:>5.2f} "
                      f"{O.erken:>5.2f} {O.gec:>5.2f} {-O.dusus:>6.1f}{ek}")
            if s["gecer"] and p >= M.KANIT_BARI:
                gecen += 1
        hukum[sev] = "KABUL" if gecen == len(M.HIZA) else f"RED ({gecen}/{len(M.HIZA)} hiza)"
    print()
    for sev, hk in hukum.items():
        print(f"HUKUM {sev} $: {hk}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
