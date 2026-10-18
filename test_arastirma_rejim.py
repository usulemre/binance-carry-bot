"""MADDE 231 TESTLERI: rejim analizi araci.

Bu dosyanin varlik sebebi: madde 231'in sayilari CANLIYA_CIKIS.md'nin
alarm esiklerini ve beklenti tablosunu belirliyor. Araci kimse
denetlemezse, o esikler bir daha dogrulanamaz.
"""
import sys

import numpy as np

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad} {detay}")
        basarisiz.append(ad)


import arastirma_rejim as AR

print("1) PERMUTASYON EGIM TESTI DOGRU CALISIYOR")
# saf gurultude egim anlamsiz cikmali
rng = np.random.default_rng(1)
_p = []
for t in range(40):
    eg, p = AR.permutasyon_egim(rng.normal(0, 1, 16), n=2000, tohum=t)
    _p.append(p)
kontrol("gurultude p degerleri cogunlukla buyuk", np.median(_p) > 0.3,
        f"(medyan p={np.median(_p):.3f})")
# guclu trendde p kucuk olmali
eg, p = AR.permutasyon_egim(np.arange(16) + rng.normal(0, 0.5, 16), n=4000)
kontrol("guclu trendde p kucuk", p < 0.01, f"(p={p:.4f})")
kontrol("egim dogru isaretli", eg > 0, f"({eg:+.3f})")

print("\n2) SEVIYE vs TREND AYIRIMI DOGRU CALISIYOR")
# saf seviye atlamasi: seviye modeli KAZANMALI
v = np.r_[np.zeros(10), np.ones(6) * 3] + rng.normal(0, 0.1, 16)
r_t, r_s = AR.seviye_mi_trend_mi(v, 10)
kontrol("saf seviye atlamasinda SEVIYE modeli kazanir", r_s < r_t,
        f"(trend {r_t:.3f} vs seviye {r_s:.3f})")
# saf dogrusal trend: trend modeli KAZANMALI
v2 = np.arange(16) * 1.0 + rng.normal(0, 0.1, 16)
r_t2, r_s2 = AR.seviye_mi_trend_mi(v2, 10)
kontrol("saf trendde TREND modeli kazanir", r_t2 < r_s2,
        f"(trend {r_t2:.3f} vs seviye {r_s2:.3f})")

print("\n3) MADDE 231'IN OLCUMLERI SABITLENDI (regresyon)")
R = AR.REJIM
kontrol("dusuk prim rejiminin getirisi yuksek primden DUSUK",
        R["dusuk"]["yillik"] < R["yuksek"]["yillik"])
kontrol("yayinlanan sayi iki rejimin ARASINDA (harman)",
        R["dusuk"]["yillik"] < R["tum"]["yillik"] < R["yuksek"]["yillik"],
        f"({R['dusuk']['yillik']} / {R['tum']['yillik']} / {R['yuksek']['yillik']})")
kontrol("KENAR IKI REJIMDE DE VAR (Sharpe ikisinde de > 2.5)",
        R["dusuk"]["sharpe"] > 2.5 and R["yuksek"]["sharpe"] > 2.5)
kontrol("alarm esigi en KOTU rejimin p1'ini kapsiyor (-%23 < -%22,3)",
        -23.0 < R["dusuk"]["dusus_p1"],
        f"(dusuk prim p1 {R['dusuk']['dusus_p1']})")
kontrol("dusuk prim rejiminin p1'i tum ornekten DAHA DERIN",
        R["dusuk"]["dusus_p1"] < R["tum"]["dusus_p1"],
        "(eski esik yanlis alarm verirdi - madde 231'in gevsetme sebebi)")

print("\n4) BOOTSTRAP ARACI MAKUL")
x = np.full(400, 0.002)          # sabit pozitif getiri: dusus ~0 olmali
b = AR.yil_bootstrap(x, n=300)
kontrol("sabit pozitif seride dusus ~0", abs(b["dusus_p1"]) < 0.01,
        f"({b['dusus_p1']:.4f})")
kontrol("sabit %0,2/gun ~1 yilda +%105 civari",
        100 < b["getiri_ort"] < 115, f"({b['getiri_ort']:.1f})")

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum rejim analizi testleri gecti.")
print("""
NE DOGRULANDI: madde 231'in ARACI (permutasyon egim testi, seviye/trend
ayirimi, bootstrap) ve OLCUMLERININ ic tutarliligi.

NE DOGRULANMADI: priminin gelecekte ne yapacagi. Olculen sey "2025Q1'de
seviye atladi"; "surecek" DEGIL. Yayinlanan beklenti bu yuzden harman
olarak birakildi.
""")
