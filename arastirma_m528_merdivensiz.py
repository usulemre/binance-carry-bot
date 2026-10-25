#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 528 — DÜZELTİLMİŞ MODELDE (MERD_SIRA=1) MERDİVENSİZ T4 vs MERDİVENLİ T4 vs M0, uzun zemin, kaldıraçsız
(önce ./zemin_sec.sh uzun). Madde 527: merdivenin kazancı motor hatasıymış. T4'ün merdivensiz hali (TPL 0,60 / TPS 0,20)
ve son TP seviyeleri düzeltilmiş modelde yeniden. Merdivensiz kollarda MERD_SIRA etkisizdir (kademe yok)."""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m509_t4_uzun as B
import arastirma_tabanlar as TB

NL = {"MERD_ESIK": "0", "MERDS_ESIK": "0", "MERD_SIRA": "1"}
M0 = {k: v for k, v in TB.T1.items() if k not in ("MERD_ESIK", "MERD_PAY", "MERDS_ESIK")}
U.KOL = {"U_M0": M0, "Q_T1": {**TB.T1, "MERD_SIRA": "1"}, "Q_T4": {**B.T4, "MERD_SIRA": "1"},
         "Q_T4NL": {**B.T4, **NL}, "Q_T4NL_L50": {**B.T4, **NL, "TPL": "0.50"}, "Q_T4NL_L70": {**B.T4, **NL, "TPL": "0.70"},
         "Q_T4NL_S15": {**B.T4, **NL, "TPS": "0.15"}, "Q_T4NL_S25": {**B.T4, **NL, "TPS": "0.25"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    S = {k: U.seri(k) for k in U.KOL}
    for ad, a, b in (("TÜM", "2020-01-01", "2027-01-01"), ("YENİ 2020-21", "2020-01-01", "2022-01-01"),
                     ("2022-07..2024", "2022-07-20", "2025-01-01"), ("2025-26", "2025-01-01", "2027-01-01")):
        print(f"\n== {ad}\n  {'kol':12s} {'yıllık':>8s} {'Sh':>5s} {'dd':>6s} {'enkötü':>7s} {'-5%':>4s} | vs M0: yıl Sh | vs Q_T4: yıl Sh")
        m = S["U_M0"][(S["U_M0"].index >= a) & (S["U_M0"].index < b)]; q = S["Q_T4"][(S["Q_T4"].index >= a) & (S["Q_T4"].index < b)]
        om, oq = U.olc(m), U.olc(q)
        for k, g in S.items():
            x = g[(g.index >= a) & (g.index < b)]; y, sh, dd, mn, g5 = U.olc(x)
            print(f"  {k:12s} {y:+8.1f} {sh:5.2f} {dd:6.1f} {mn:7.2f} {g5:4d} | {y-om[0]:+6.1f} {sh-om[1]:+.2f} | {y-oq[0]:+6.1f} {sh-oq[1]:+.2f}")


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
