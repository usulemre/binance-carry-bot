#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 485 — KIL PAYI KALAN BULGULARIN BİRLEŞİMİ (kullanıcı: "birleşik kaçırdığımız parametre olabilir").

Tek başına ön kaydın altında kalmış ama aynı yönde işaret veren dört kol, merdivenli taban (ZSR15P67) üzerinde
birlikte: P80 (kademe payı 0,80; madde 470: eşitVol +8,9, IS +5) · CAP (short coin tavanı %8, CAP_TARAF=short;
madde 455/456: dd ↓, kötü gün ↓) · A43 (4 long / 3 short; madde 458: eşitVol +7) · E08 (short ⅓ @ −%8 erken kademe;
madde 476: dd −14,6, −%5 altı 2). Etkiler toplanabilir mi, yoksa hepsi aynı riski mi kesiyor?
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8); geçen birleşim → iki seviye protokol.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
P = {"P80": {"MERD_PAY": "0.80"}, "CAP": {"CAP_ORTAK": "0.08", "CAP_TARAF": "short"},
     "A43": {"N_L": "4", "N_S": "3"}, "E08": {"MERDS0_ESIK": "0.08"}}
BIR = ["P80+CAP", "P80+A43", "CAP+A43", "P80+E08", "P80+CAP+A43", "P80+CAP+A43+E08", "CAP+E08"]
def kol(ad):
    d = {}
    for p in ad.split("+"): d.update(P[p])
    return d
A.KOLLAR = {f"BR{a.replace('+', '_')}": ({**W.T, **kol(a)}, 4, {2000: M.D8}) for a in ["CAP", "A43"] + BIR}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
