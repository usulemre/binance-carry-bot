#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 358 — KALABALIK SEÇİMİNİN ÖLÇÜTÜ, HAVUZ 4'LÜK 15x4 KİTABINDA.

Madde 352 havuzu 3 -> 4 yaptı: aynı bacak için 12 yerine 16 aday, yani
havuz İÇİNDEKİ seçimin payı büyüdü. O seçimi bugün `ls` yapıyor
(Binance globalLongShortAccountRatio, madde 148). Motorda başka ölçütler
zaten var ve eski kitaplarda denendi; hiçbiri bu kitapta ölçülmedi
(madde 222'nin yasası).

KOLLAR (motorun `ad` argümanı; hepsi HAVUZ 4):
    top       üst trader POZİSYON oranı (sum_toptrader_long_short_ratio)
    ls_fark   ls + (genel − üst trader) farkı, sıra toplamı
    ls_lsdeg  ls + oranın 1 günlük değişimi, sıra toplamı
    oi_ters   OI artışının tersi
    rast1     PLASEBO: havuz içinde rastgele seçim (makine aynı)

KONTROL: T350_HAVUZ4_* (ölçüt `ls`). Plasebo, kalabalık bilgisinin bu
kitapta ne kadar değerli olduğunu ölçer.

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı): madde 357 ile aynı (iki hiza,
dört şart + P >= %80; ayar değişikliği iki seviyede de geçerse).
Ek şart: bir kol, rast1 plasebosunu da aynı ölçütte geçmelidir.
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
KOLLAR = ("top", "ls_fark", "ls_lsdeg", "oi_ters", "rast1")
EVREN = {2000: M.D8, 3500: M.D2}


def tek(kol, sev, h):
    ad = f"M358_{kol}_{sev}_{h}"
    pkl = os.path.join(CIKTI, ad + ".pkl")
    if os.path.exists(pkl):
        return ad, "var"
    env = dict(os.environ, **dict(M.TABAN, HAVUZ="4"), FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(EVREN[sev]), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", kol, str(M.BACAK)], cwd=KOK,
                           env=env, stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek(*a),
                            [(k, s, h) for k in KOLLAR for s in EVREN for h in M.HIZA]):
            print(ad, d, flush=True)


def analiz():
    print(f"{'kol':<9} {'bak':>4} {'hz':>2} {'yillik':>7} {'Sh22':>5} {'Sh25':>5} "
          f"{'dusus':>6} {'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5} {'P_pla':>6}"
          "   (kontrol: ls, HAVUZ 4; farklar)")
    for kol in KOLLAR:
        gec = {}
        for sev in EVREN:
            n = 0
            for h in M.HIZA:
                gk = M.gunluk(f"T350_HAVUZ4_{sev}_{h}")
                ga = M.gunluk(f"M358_{kol}_{sev}_{h}")
                gp = M.gunluk(f"M358_rast1_{sev}_{h}")
                K, A = M.olcum("K", gk), M.olcum(kol, ga)
                s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, _ = M.bootstrap(gk, ga, n=1000)
                pp, _ = M.bootstrap(gp, ga, n=1000) if kol != "rast1" else (float("nan"), 0)
                isaret = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                print(f"{kol:<9} {sev:>4} {h:>2} {A.getiri - K.getiri:>+7.1f} "
                      f"{A.erken - K.erken:>+5.2f} {A.gec - K.gec:>+5.2f} "
                      f"{A.dusus - K.dusus:>+6.1f} {s['esit_risk'] - K.getiri:>+7.1f} "
                      f"{s['kaldirac']:>5.2f} {isaret:>5} {p:>5.1f} {pp:>6.1f}")
                n += int(s["gecer"] and p >= M.KANIT_BARI and (kol == "rast1" or pp >= M.KANIT_BARI))
            gec[sev] = n == len(M.HIZA)
        if kol == "rast1":
            print("(rast1 plasebodur; satirlari kalabalik bilgisinin DEGERINI gosterir)\n")
            continue
        hk = ("AYAR DEGISIKLIGI (iki seviyede gecti)" if all(gec.values()) else
              f"yalniz {[s for s in EVREN if gec[s]]} $" if any(gec.values()) else "RED")
        print(f"HUKUM {kol}: {hk}\n")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
