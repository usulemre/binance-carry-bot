#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İKİ TABANLI ARAŞTIRMA ALTYAPISI (kullanıcı kararı 2026-10-24, ADAYLAR.md).

T1 = ZSR15P67 (şu anki bot), T2 = BRP80_CAP_A43 (2. aday). Bir deneme kolu bir DEĞİŞİKLİK sözlüğüdür; `kollar()`
onu iki tabana da uygular (ad öneki 1_/2_), `analiz()` her kolu KENDİ tabanına karşı ölçer (madde 470 ön kaydı:
IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8) ve ayrıca T1'e karşı mutlak tabloyu verir.

Kullanım (deneme betiğinde):
    import arastirma_tabanlar as TB
    TB.kur({"X1": {...}, "X2": {...}}, onek="XY")
    if __name__ == "__main__": TB.calistir()
"""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T1 = dict(W.T)
T2 = {**W.T, "MERD_PAY": "0.80", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "N_L": "4", "N_S": "3"}
TABAN = {1: "ZSR15P67", 2: "BRP80_CAP_A43"}
_KOL = {}


def kur(degisiklik: dict, onek: str, bacak: int = 4):
    A.KOLLAR = {}
    for t, base in ((1, T1), (2, T2)):
        A.KOLLAR[TABAN[t]] = (dict(base), bacak, {2000: M.D8})
        for a, d in degisiklik.items():
            ad = f"{onek}{t}_{a}"; A.KOLLAR[ad] = ({**base, **d}, bacak, {2000: M.D8}); _KOL[ad] = t
    W.A.KOLLAR = A.KOLLAR


def analiz():
    SH = lambda x: x.mean() / x.std() * np.sqrt(365.25)
    print(f"{'kol':16s} {'taban':>5s} {'yillik':>7s} {'IS':>7s} {'OOS':>7s} {'Sh':>5s} {'dd':>6s} {'enkotu':>7s} {'-5%':>4s} "
          f"{'TemEyl':>7s} {'dYil':>6s} {'esitVol':>8s}")
    for ad in list(TABAN.values()) + list(_KOL):
        t = _KOL.get(ad, 1 if ad == TABAN[1] else 2)
        b = K.seri(TABAN[t]); bIS, bOOS = b[b.index < "2025-01-01"], b[b.index >= "2025-01-01"]
        g = K.seri(ad); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        f = o["yil"] - K.YIL(b * (g.std() / b.std()))
        dIS, dOOS = K.YIL(IS) - K.YIL(bIS), K.YIL(OOS) - K.YIL(bOOS)
        h = "ADAY" if ad in _KOL and dIS >= 8 and dOOS >= 0 and f >= 8 else ""
        print(f"{ad:16s} {'T'+str(t):>5s} {o['yil']:+7.1f} {K.YIL(IS):+7.1f} {K.YIL(OOS):+7.1f} {SH(g):5.2f} {o['dd']:6.1f} "
              f"{o['enkotu']:7.2f} {o['g5']:4d} {o['son']:+7.1f} {o['yil']-K.YIL(b):+6.1f} {f:+8.1f} {h}")


def calistir():
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
