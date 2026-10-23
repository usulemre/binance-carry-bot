#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 456 — SHORT COİN TAVANI %8'İN SAĞLAMLIĞI.

Madde 455: T60 + 24 sa stop üzerine short tavanı %8 (CS08): yıllık −2,3 puan, −%5 altı gün 7 → 4,
−%4 altı 14 → 10, dd −20,8 → −17,2; ama en kötü gün −5,49 → −5,61 (ön kayıt RED, fark gürültü düzeyi).
YENİ ÖN KAYIT (sonuç görüldükten sonra yazıldı, kayıtlı): CS07/CS08/CS09 üçü de −%5 altı günü <= 5,
dd'yi >= 2 puan iyileştirip ek maliyeti <= 6 puan tutarsa ve 3.500 $'da CS08 dd'yi >= 1,5 puan
iyileştirip ek maliyeti <= 6 puan tutarsa → "CANLIYA ADAY".
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
A.KOLLAR = {"KCS07": ({**T, "CAP_ORTAK": "0.07", "CAP_TARAF": "short"}, 4, {2000: M.D8}),
            "KCS09": ({**T, "CAP_ORTAK": "0.09", "CAP_TARAF": "short"}, 4, {2000: M.D8}),
            "KCS08": ({**T, "CAP_ORTAK": "0.08", "CAP_TARAF": "short"}, 4, {3500: M.D2}),
            "KD24_45T2": (T, 4, {3500: M.D2})}
A.SEVIYE = (2000, 3500)
_o = A.tek
A.tek = lambda kol, sev, h: (f"M357_{kol}_{sev}_{h}", "atlandi") if sev not in A.KOLLAR[kol][2] else _o(kol, sev, h)


def seri(ad, sev=2000):
    return (M.gunluk(f"M357_{ad}_{sev}_0") + M.gunluk(f"M357_{ad}_{sev}_1")) / 2


def analiz():
    r = {}
    for sev, kollar in ((2000, ["KD24_45T2", "KCS07", "KCS08", "KCS09"]), (3500, ["KD24_45T2", "KCS08"])):
        print(f"\n=== {sev} $ ===")
        b = K.olc(seri("KD24_45T2", sev))
        for kol in kollar:
            o = K.olc(seri(kol, sev)); r[(kol, sev)] = (o, b)
            print(f"{kol:10s} yillik {o['yil']:+7.1f} (ek maliyet {b['yil']-o['yil']:+5.1f}) dd {o['dd']:6.1f} en kotu {o['enkotu']:6.2f} "
                  f"-%5 alti {o['g5']} -%4 alti {o['g4']} p1 {o['p1']:.2f} Tem-Eyl26 {o['son']:+.1f}")
    ok = all(r[(k, 2000)][0]["g5"] <= 5 and r[(k, 2000)][0]["dd"] - r[(k, 2000)][1]["dd"] >= 2
             and r[(k, 2000)][1]["yil"] - r[(k, 2000)][0]["yil"] <= 6 for k in ("KCS07", "KCS08", "KCS09"))
    o, b = r[("KCS08", 3500)]
    ok35 = o["dd"] - b["dd"] >= 1.5 and b["yil"] - o["yil"] <= 6
    print(f"\nHUKUM: komsuluk {'TUTUYOR' if ok else 'TUTMUYOR'}, 3.500 $ {'TUTUYOR' if ok35 else 'TUTMUYOR'} -> {'CANLIYA ADAY' if ok and ok35 else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
