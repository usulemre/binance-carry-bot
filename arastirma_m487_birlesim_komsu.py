#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 487 — P80+CAP+A43 KOMŞULUK (plato mu, tek nokta mı?).

Madde 486: protokol RED (P %76-86) ama Sharpe 8/8 hücrede ↑. Birleşim sonuç görülerek kuruldu; komşuları da aynı
yönde ise seçim yanlılığı açıklaması zayıflar (madde 463'teki merdiven platosu gibi).
KOMŞULAR (biri değişir): pay 0,75 / 0,85 · short tavan %7 / %9.
ÖN KAYIT (koşudan önce): dört komşunun DÖRDÜ de Sharpe ≥ taban + 0,10 VE eşitVol ≥ +8 → PLATO (birleşim kullanıcıya
"kanıtlanmış plato, P sınırda" olarak sunulur); değilse tek nokta → beklemede (Ekim OOS).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
B = {**W.T, "MERD_PAY": "0.80", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "N_L": "4", "N_S": "3"}
DEG = {"P75": {"MERD_PAY": "0.75"}, "P85": {"MERD_PAY": "0.85"}, "C07": {"CAP_ORTAK": "0.07"}, "C09": {"CAP_ORTAK": "0.09"}}
A.KOLLAR = {f"BK{a}": ({**B, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
A.KOLLAR["BRP80_CAP_A43"] = (B, 4, {2000: M.D8})
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
