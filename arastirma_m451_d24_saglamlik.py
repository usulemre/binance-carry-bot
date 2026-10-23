#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 451 — 24 SA DÜŞÜŞ STOP'UNUN SAĞLAMLIĞI (madde 449'un en iyisi D24_45).

Madde 449: SLL24 0,45 (coin 24 sa'te −%45 → long kapanır) T60'ın en kötü gününü −8,63 → −5,49 (%36)
kesti, yıllık maliyet yalnız 4 puan (IS +5, OOS −25), son çeyrek aynı. 7 komşu-sonuçtan biri en iyi
→ seçim yanlılığı riski. KOLLAR: D24_40, D24_50, D24_55 (2.000 $) · D24_45 3.500 $ D2.
ÖN KAYIT: D24_40/45/50 üçü de en kötü günü >= %25 iyileştirip maliyeti <= 12 puan tutarsa ve 3.500 $'da
D24_45 en kötü günü >= %20 iyileştirip maliyeti <= 12 puan tutarsa → "CANLIYA ADAY" (düğme olarak).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"
T = K.T60
A.KOLLAR = {"KD24_40": ({**T, "SLL24": "0.40"}, 4, {2000: M.D8}), "KD24_50": ({**T, "SLL24": "0.50"}, 4, {2000: M.D8}),
            "KD24_55": ({**T, "SLL24": "0.55"}, 4, {2000: M.D8}), "KD24_45": ({**T, "SLL24": "0.45"}, 4, {3500: M.D2})}
A.SEVIYE = (2000, 3500)
_o = A.tek
A.tek = lambda kol, sev, h: (f"M357_{kol}_{sev}_{h}", "atlandi") if sev not in A.KOLLAR[kol][2] else _o(kol, sev, h)


def seri(ad, sev=2000):
    return (M.gunluk(f"M357_{ad}_{sev}_0") + M.gunluk(f"M357_{ad}_{sev}_1")) / 2


def analiz():
    sonuc = {}
    for sev, kollar in ((2000, ["T60", "KD24_40", "KD24_45", "KD24_50", "KD24_55"]), (3500, ["T60", "KD24_45"])):
        b = K.olc(seri("T60", sev)); print(f"\n=== {sev} $ ===")
        for kol in kollar:
            g = seri(kol, sev); o = K.olc(g); iy = 1 - o["enkotu"] / b["enkotu"]; mal = b["yil"] - o["yil"]
            IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
            print(f"{kol:8s} yillik {o['yil']:+7.1f} (maliyet {-mal:+6.1f}) dd {o['dd']:6.1f} en kotu {o['enkotu']:6.2f} (%{iy*100:3.0f}) "
                  f"-%5 alti {o['g5']} -%4 alti {o['g4']} Tem-Eyl26 {o['son']:+.1f} IS {K.YIL(IS):+.1f} OOS {K.YIL(OOS):+.1f}")
            sonuc[(kol, sev)] = (iy, mal)
    ok = all(sonuc[(k, 2000)][0] >= 0.25 and sonuc[(k, 2000)][1] <= 12 for k in ("KD24_40", "KD24_45", "KD24_50"))
    ok35 = sonuc[("KD24_45", 3500)][0] >= 0.20 and sonuc[("KD24_45", 3500)][1] <= 12
    print(f"\nHUKUM: komsuluk {'TUTUYOR' if ok else 'TUTMUYOR'}, 3.500 $ {'TUTUYOR' if ok35 else 'TUTMUYOR'} -> "
          f"{'CANLIYA ADAY' if ok and ok35 else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
