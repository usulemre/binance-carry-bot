#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 377 — KARAR ARACININ KENDİ DOĞRULAMASI (madde 344-376'nın aracı).

(1) DETERMİNİZM: madde 352'nin HAVUZ 4 hücresi (2.000 $, hiza 0/1)
    aynı araçla yeniden hesaplanır; P %92,6 / %94,3 birebir çıkmalı.
(2) YANLIŞ POZİTİF ORANI: "aday" = kontrolün günlük serisi + ortalaması
    SIFIR gürültü. Gürültünün oynaklığı GERÇEK bir adayın izleme hatasına
    eşitlenir (HAVUZ 4 − HAVUZ 3 günlük farkının std'si). Bu adayın
    gerçek etkisi yoktur; kuralı geçmesi yanlış pozitiftir. Hücre başına
    (tek seviye, tek hiza) geçme oranı %80 ve %95 barında ölçülür.
    Madde 289 bunu motor plasebolarıyla %20 bulmuştu (dört şart, bootstrap'sız).
"""
import numpy as np
import arastirma_m346_prim as M
import karar_kurali as KK


def main(N=200, B=400):
    print("(1) DETERMINIZM — madde 352 HAVUZ 4 @2.000 $")
    for h in (0, 1):
        gk, ga = M.gunluk(f"K_2000_{h}"), M.gunluk(f"T350_HAVUZ4_2000_{h}")
        p, _ = M.bootstrap(gk, ga)
        print(f"   hiza {h}: P %{p:.1f}  (kayitli %{(92.6, 94.3)[h]})")
    print("(2) YANLIS POZITIF — sifir-etkili aday, gercekci izleme hatasi")
    rng = np.random.default_rng(377)
    for h in (0, 1):
        gk = M.gunluk(f"T350_HAVUZ4_2000_{h}")
        iz = (M.gunluk(f"T350_HAVUZ4_2000_{h}") - M.gunluk(f"K_2000_{h}")).std()
        K = M.olcum("K", gk)
        dort = g80 = g95 = 0
        for k in range(N):
            ga = gk + rng.normal(0.0, iz, len(gk))
            A = M.olcum("a", ga)
            s = KK.gecer_mi(K, A, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
            if not s["gecer"]:
                continue
            dort += 1
            p, _ = M.bootstrap(gk, ga, n=B, tohum=1000 + k)
            g80 += p >= 80; g95 += p >= 95
        print(f"   hiza {h}: izleme hatasi {iz*100:.3f}%/gun | dort sart gecen %{dort/N*100:.1f} | "
              f"+P>=80 %{g80/N*100:.1f} | +P>=95 %{g95/N*100:.1f}  (N={N})")


if __name__ == "__main__":
    main()
