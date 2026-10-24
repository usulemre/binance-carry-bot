#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 499 — S_REB'İN DÜŞÜŞ SORUNU: sert piyasada short yenilemeyi DURDUR (uzun zemin, önce ./zemin_sec.sh uzun).

Madde 498: short'u 2 günde bir yenilemek Sharpe'ı her dönemde artırıyor ama en büyük düşüşü ~5 puan derinleştiriyor
(2021-05 çöküşü: medyan 3 g getirisi −%15..−%39 iken taze short açılıyor, ardından sıçrama). Kural (nedensel): evrenin
medyan 3 g getirisi |.| ≥ x ise ara short yenilemesi atlanır (tam dengeleme sürer).
KOLLAR (T1 + S_REB 12 üzerine): D10 (x 0,10; zamanın %15'i) · D15 (x 0,15; %5) · ayrıca SR18 (3 g'de bir).
ÖN KAYIT: aday, U_T1SR12'nin (madde 497) yıllık/Sharpe kazancının ≥ yarısını korurken TÜM dönem en büyük düşüşü T1'den
en fazla 1 puan derin olmalı → uzun zemin protokolüne aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_tabanlar as TB

B = {**TB.T1, "S_REB": "12"}
U.KOL = {"U_T1": TB.T1, "U_T1SR12": B, "U_SR12D10": {**B, "S_REB_DUR": "0.10"}, "U_SR12D15": {**B, "S_REB_DUR": "0.15"},
         "U_T1SR18": {**TB.T1, "S_REB": "18"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    import numpy as np
    S = {k: U.seri(k) for k in U.KOL}
    for ad, a, b in (("TÜM 2020-07..2026-09", "2020-01-01", "2027-01-01"), ("YENİ 2020-07..2021-12", "2020-01-01", "2022-01-01"),
                     ("2022-07..2024", "2022-07-20", "2025-01-01"), ("2025-26", "2025-01-01", "2027-01-01")):
        print(f"\n== {ad}\n  {'kol':10s} {'yıllık':>8s} {'Sh':>5s} {'dd':>6s} {'enkötü':>7s} {'-5%':>4s} | vs T1: {'yıl':>7s} {'Sh':>6s} {'dd':>6s}")
        bx = S["U_T1"][(S["U_T1"].index >= a) & (S["U_T1"].index < b)]; yb, shb, ddb, *_ = U.olc(bx)
        for k, g in S.items():
            x = g[(g.index >= a) & (g.index < b)]; y, sh, dd, mn, g5 = U.olc(x)
            print(f"  {k:10s} {y:+8.1f} {sh:5.2f} {dd:6.1f} {mn:7.2f} {g5:4d} | {y-yb:+7.1f} {sh-shb:+6.2f} {dd-ddb:+6.1f}")


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
