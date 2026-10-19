#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 362 — ORAN API'Sİ SUSARSA: SON BİLİNEN ORAN MI, EN UÇ n Mİ?

Madde 361: yedek (en uç n) yılda −38..−47 puan, düşüş +6..+9 derin.
Alternatif yedek: son bilinen oranları kullanmak. Maliyeti, `ls`
ölçütünü LS_GECIKME bar (4 sa) kadar bayat veriyle koşarak ölçülür
(parite LS_GECIKME=0 ile birebir, maks fark 0,0).

    gecikme 6 bar = 1 gün · 12 = 2 gün · 36 = 6 gün

KARAR (koşudan önce yazıldı): bir gecikmenin eşit-risk farkı İKİ hizada
ve İKİ seviyede madde 361'in `uc` farkından iyiyse, o süreye kadar bayat
oran `uc`'den güvenli bir yedektir ve bota "son bilinen oranı kullan,
en fazla X gün" yedeği önerilir.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
import karar_kurali as KK  # noqa: E402
import arastirma_m346_prim as M  # noqa: E402

GECIKME = (6, 12, 36)
EVREN = {2000: M.D8, 3500: M.D2}


def tek(g, sev, h):
    ad = f"M362_g{g}_{sev}_{h}"
    pkl = os.path.join(M.CIKTI, ad + ".pkl")
    if os.path.exists(pkl):
        return ad, "var"
    env = dict(os.environ, **dict(M.TABAN, HAVUZ="4"), LS_GECIKME=str(g),
               FAZ_KAY=str(h), SEMBOL_HARIC=",".join(EVREN[sev]), E_CIKTI=pkl)
    with open(os.path.join(M.CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], cwd=KOK, env=env,
                           stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek(*a),
                            [(g, s, h) for g in GECIKME for s in EVREN for h in M.HIZA]):
            print(ad, d, flush=True)


def _fark(ad_aday, sev, h):
    gk = M.gunluk(f"T350_HAVUZ4_{sev}_{h}"); ga = M.gunluk(ad_aday)
    K, A = M.olcum("K", gk), M.olcum("a", ga)
    s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
    return A.getiri - K.getiri, A.dusus - K.dusus, s["esit_risk"] - K.getiri


def analiz():
    print(f"{'yedek':<12} {'bak':>4} {'hz':>2} {'yillik':>7} {'dusus':>6} {'esitR':>7}   (kontrole gore)")
    uc = {}
    for sev in EVREN:
        for h in M.HIZA:
            y, d, e = _fark(f"M358_uc_{sev}_{h}", sev, h); uc[(sev, h)] = e
            print(f"{'en uc n':<12} {sev:>4} {h:>2} {y:>+7.1f} {d:>+6.1f} {e:>+7.1f}")
    for g in GECIKME:
        iyi = 0
        for sev in EVREN:
            for h in M.HIZA:
                y, d, e = _fark(f"M362_g{g}_{sev}_{h}", sev, h)
                iyi += int(e > uc[(sev, h)])
                print(f"{'bayat ' + str(g * 4) + ' sa':<12} {sev:>4} {h:>2} {y:>+7.1f} {d:>+6.1f} {e:>+7.1f}")
        print(f"HUKUM {g * 4} sa bayat: {'en uc n yedeginden GUVENLI' if iyi == 4 else f'{iyi}/4 hucrede iyi - degil'}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
