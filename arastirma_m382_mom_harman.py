#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 382 — MADDE 381'İN ÖRNEK DIŞINDA GEÇEN KOLU (HEPSI MOM H1) CARRY'YE HARMAN.

Madde 381: beş ufkun ortalama sırasıyla momentum (üst %10 long / alt %10
short, günlük), IS 2022-24'te seçildi, OOS 2025-26 Sharpe 1,27 (plasebo
0,48), carry ile rho +0,07. Madde 237'nin momentumu carry MAKİNESİNİ
kullanıyordu (rho +0,718, "aynı piyasa duvarı"); bu kol ayrı bir makine
(günlük, desil, TP/rezerv yok) — korelasyonun düşük olmasının sebebi bu.

HARMAN: günlük getiri (1-w) carry + w mom, w = 0,05 / 0,10 / 0,20.
Kontrol: T350_HAVUZ4 (2.000 $ ve 3.500 $, iki hiza).
ÖN KAYITLI KARAR (madde 375 protokolü): bir w, İKİ seviyede İKİ hizada
dört şart + eşli bootstrap P >= %95 geçerse ve eşit-risk farkı w ile
monoton artıyorsa (en azından ilk iki adımda) KABUL adayı. Sonra
UYGULANABİLİRLİK ayrıca sorulur (küçük sermayede desil portföyü çok
sayıda küçük bacak ister).
"""
import numpy as np
import arastirma_m346_prim as M
import arastirma_m381_cok_ufuk as U
import karar_kurali as KK

M.KANIT_BARI = 95.0


def main():
    C, Fd, uy = U.yukle()
    S = U.sinyaller(C, uy)
    mom = U.getiri(U.agirlik(S["HEPSI"], uy, "MOM"), C, Fd, 1)
    print(f"{'w':>5} {'bak':>5} {'hz':>2} {'yillik':>7} {'Sh22':>6} {'Sh25':>6} {'dusus':>6} "
          f"{'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5}")
    for w in (0.05, 0.10, 0.20):
        gec = 0
        for sev in (2000, 3500):
            for h in M.HIZA:
                gk = M.gunluk(f"T350_HAVUZ4_{sev}_{h}")
                ix = gk.index.intersection(mom.index)
                gk2 = gk.loc[ix]; ga = (1 - w) * gk2 + w * mom.loc[ix].values
                K, A = M.olcum("K", gk2), M.olcum("H", ga)
                s = KK.gecer_mi(K, A, gunluk_kontrol=gk2.values, gunluk_aday=ga.values)
                p, _ = M.bootstrap(gk2, ga, n=2000)
                isa = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                print(f"{w:>5.2f} {sev:>5} {h:>2} {A.getiri-K.getiri:>+7.1f} {A.erken-K.erken:>+6.2f} "
                      f"{A.gec-K.gec:>+6.2f} {A.dusus-K.dusus:>+6.1f} {s['esit_risk']-K.getiri:>+7.1f} "
                      f"{s['kaldirac']:>5.2f} {isa:>5} {p:>5.1f}")
                gec += int(s["gecer"] and p >= 95)
        print(f"HUKUM w={w}: {'KABUL ADAYI' if gec == 4 else f'RED ({gec}/4)'}\n")


if __name__ == "__main__":
    main()
