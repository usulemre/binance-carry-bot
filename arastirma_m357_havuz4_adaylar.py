#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 357 — HAVUZ 4 YENİ VARSAYILAN; BEKLEYEN ADAYLAR YENİ KONTROLE KARŞI.

Madde 222'nin yasası: kontrol değişince, ona karşı ölçülmüş her aday
yeniden açılır. Madde 352 KALABALIK_HAVUZ'u 3,0 -> 4,0 yaptı. Bekleyen,
sınırda kalmış üç aday ve bir kombinasyon:

    P      prim çarpanı (madde 346: 2.000 $ RED, 3.500 $ KABUL - gürültü bandı)
    T13    13 faz x 3 bacak (madde 348: 2.000 $'da P %64/%77, 3.500 $+ kayıp)
    T13P   13x3 + prim (madde 355: kullanıcının "+%154" satırı)
    KAP08  coin başına rezerv sınırı 0,08 (madde 351: +6..+7 puan, şart 1)

Hepsi HAVUZ 4 ile. KONTROL = madde 350'nin T350_HAVUZ4_* koşuları
(15x4, HAVUZ 4, aynı zemin) — yeniden koşulmaz.

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı): madde 346/348 ile aynı —
bir seviyede İKİ hizada (1) gecer_mi dört şart VE (2) eşli bootstrap
P >= %80. Ayar değişikliği yalnız İKİ seviyede de geçerse; tek seviyede
geçen bir aday "sermayeye bağlı kullanıcı kararı" olarak kaydedilir.
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
H4 = {"HAVUZ": "4"}
F13 = {"FAZ": "13", "FAZ_LISTE": "0,2,5,7,9,12,14,16,18,21,23,25,28"}
KOLLAR = {   # ad -> (ek ortam, bacak, evren fonksiyonu)
    "P":     (dict(H4, **M.PRIM), 4, {2000: M.D8, 3500: M.D2}),
    "T13":   (dict(H4, **F13), 3, {2000: M.D2, 3500: M.D1}),
    "T13P":  (dict(H4, **F13, **M.PRIM), 3, {2000: M.D2, 3500: M.D1}),
    "KAP08": (dict(H4, KAP="0.08"), 4, {2000: M.D8, 3500: M.D2}),
}
SEVIYE = (2000, 3500)


def tek(kol, sev, h):
    ad = f"M357_{kol}_{sev}_{h}"
    pkl = os.path.join(CIKTI, ad + ".pkl")
    if os.path.exists(pkl):
        return ad, "var"
    ek, bacak, evren = KOLLAR[kol]
    env = dict(os.environ, **dict(M.TABAN, **ek), FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(evren[sev]), E_CIKTI=pkl)
    with open(os.path.join(CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", str(bacak)], cwd=KOK,
                           env=env, stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"


def kos():
    with ThreadPoolExecutor(2) as ex:
        for ad, d in ex.map(lambda a: tek(*a),
                            [(k, s, h) for k in KOLLAR for s in SEVIYE for h in M.HIZA]):
            print(ad, d, flush=True)


def analiz():
    print(f"{'kol':<6} {'bak':>4} {'hz':>2} {'yillik':>7} {'Sh22':>5} {'Sh25':>5} "
          f"{'dusus':>6} {'esitR':>7} {'kald':>5} {'4sart':>5} {'P%':>5} {'med':>6}"
          "   (kontrol: 15x4 HAVUZ 4; farklar)")
    for kol in KOLLAR:
        gec = {}
        for sev in SEVIYE:
            n = 0
            for h in M.HIZA:
                gk = M.gunluk(f"T350_HAVUZ4_{sev}_{h}")
                ga = M.gunluk(f"M357_{kol}_{sev}_{h}")
                K, A = M.olcum("K", gk), M.olcum(kol, ga)
                s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, med = M.bootstrap(gk, ga, n=1000)
                isaret = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                print(f"{kol:<6} {sev:>4} {h:>2} {A.getiri - K.getiri:>+7.1f} "
                      f"{A.erken - K.erken:>+5.2f} {A.gec - K.gec:>+5.2f} "
                      f"{A.dusus - K.dusus:>+6.1f} {s['esit_risk'] - K.getiri:>+7.1f} "
                      f"{s['kaldirac']:>5.2f} {isaret:>5} {p:>5.1f} {med:>+6.1f}")
                n += int(s["gecer"] and p >= M.KANIT_BARI)
            gec[sev] = n == len(M.HIZA)
        hk = ("AYAR DEGISIKLIGI (iki seviyede gecti)" if all(gec.values()) else
              f"yalniz {[s for s in SEVIYE if gec[s]]} $ - sermayeye bagli kullanici karari"
              if any(gec.values()) else "RED")
        print(f"HUKUM {kol}: {hk}\n")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
