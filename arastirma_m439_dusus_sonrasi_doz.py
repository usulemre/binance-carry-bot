#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 439 — KİTAP DÜŞÜŞÜNDEN SONRA GEÇİCİ DOZ ARTIŞI (T60, 4 sa çubuk).

Gözlem (T60, iki hiza): 4 sa'lik kitap getirisi < −%2 olduktan sonraki 24 sa ortalaması +%1,4-1,5
(normal +%0,34); < −%3 sonrası +%2,3-3,1; en kötü 15 günün ertesi günü +%1,4-2,1. Kesmek
(madde 280) toparlanmayı kaçırıyor; bu madde TERSİNİ dener: düşüşten sonra doz geçici ARTAR.
KURAL (ön kayıt): 4 sa getirisi < E ise, GECİKME kadar bar sonra başlayıp T bar boyunca brüt
= D (sonra 1,0). E ∈ {−%1,5, −%2, −%3}, D ∈ {1,25, 1,50}, T ∈ {3, 6} bar (12/24 sa),
gecikme ∈ {1, 2} bar (bot 8 sa'de bir döner → 2 bar gerçekçi). Maliyet: |Δbrüt| x %0,10.
Ölçüt: aynı ortalama dozda sabit kaldıraçla kıyas (eşit ort. doz) ve eşit dd'de getiri;
IS (22-24) ve OOS (25-26) ayrı. KARAR: bir kural IS'te seçilir (eşit ort. dozda en yüksek
fark), OOS'ta da sabit kaldıracı geçerse ve tam dönem dd'yi bozmazsa → motor içi doğrulama.
"""
import itertools, sys, os
import numpy as np, pandas as pd

YIL = lambda x, n: (np.prod(1 + x) ** (365.25 * 6 / n) - 1) * 100
def DD(x):
    e = np.cumprod(1 + x); return (e / np.maximum.accumulate(e) - 1).min() * 100


def uygula(r, E, D, T, gec):
    s = np.ones(len(r))
    for i in np.where(r < E)[0]:
        s[i + gec:i + gec + T] = np.maximum(s[i + gec:i + gec + T], D)
    s = s[:len(r)]
    m = np.abs(np.diff(np.r_[1.0, s])) * 0.001
    return s * r - m, s.mean()


def main():
    S = {h: pd.read_pickle(f"/tmp/m412/M357_T60_2000_{h}.pkl").pct_change().dropna() for h in (0, 1)}
    sonuc = []
    for E, D, T, gec in itertools.product((-0.015, -0.02, -0.03), (1.25, 1.5), (3, 6), (1, 2)):
        row = dict(E=E * 100, D=D, bar=T, gec=gec)
        for h, r in S.items():
            for ad, mask in (("IS", r.index < "2025-01-01"), ("OOS", r.index >= "2025-01-01"), ("TAM", r.index == r.index)):
                x = r[mask].values
                a, ort = uygula(x, E, D, T, gec)
                b = x * ort                     # aynı ortalama dozda sabit kaldıraç
                row[f"{ad}{h}"] = YIL(a, len(a)) - YIL(b, len(b))
                if ad == "TAM":
                    row[f"dd{h}"] = DD(a) - DD(b); row[f"doz{h}"] = ort
                    row[f"ddT60_{h}"] = DD(a) - DD(x)
        sonuc.append(row)
    T_ = pd.DataFrame(sonuc)
    T_["IS"] = (T_.IS0 + T_.IS1) / 2; T_["OOS"] = (T_.OOS0 + T_.OOS1) / 2; T_["TAM"] = (T_.TAM0 + T_.TAM1) / 2
    T_["dd"] = (T_.dd0 + T_.dd1) / 2; T_["doz"] = (T_.doz0 + T_.doz1) / 2; T_["ddT60"] = (T_.ddT60_0 + T_.ddT60_1) / 2
    pd.set_option("display.width", 200)
    print("fark = kural - ayni ortalama dozda sabit kaldirac (yillik puan); dd farki + = daha sig")
    print(T_[["E", "D", "bar", "gec", "doz", "IS", "OOS", "TAM", "dd", "ddT60"]].sort_values("IS", ascending=False).round(2).to_string(index=False))
    s = T_.sort_values("IS", ascending=False).iloc[0]
    print(f"\nIS 1.: E {s.E}% D {s.D} bar {s.bar} gec {s.gec} -> OOS {s.OOS:+.1f}, dd farki {s.dd:+.1f} -> "
          f"{'MOTOR ICI DOGRULAMAYA' if s.OOS > 0 and s.dd >= -1 else 'RED'}")


if __name__ == "__main__":
    main()
