#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 519 — MALİYET STRESİ: T4 vs T1, canlı gibi giriş, KOM 5 / 10 / 15 bp (uzun zemin, 2.000 $; önce ./zemin_sec.sh uzun).
T4 short tarafını 2 g'de bir yeniliyor → devir T1'den yüksek. Gerçek kayma/taker payı modelin 2 bp'sinden büyük olursa T4'ün
farkı ne kadar erir? Kırılma noktası (T4 = T1) hangi maliyette?"""
import sys
import numpy as np
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_tabanlar as TB
import arastirma_m497_uzun_gecmis as U

A.CIKTI = "/tmp/m_uzun"; M.CIKTI = "/tmp/m_uzun"; A.SEVIYE = (2000,)
T4 = {"S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
A.KOLLAR = {}
for k in ("0.0005", "0.0010", "0.0015"):
    b = int(float(k) * 1e4)
    A.KOLLAR[f"V1_TGK{b}" if b != 5 else "V1_TGK5"] = ({**TB.T1, "TEK_GIRIS": "1", "KOM": k}, 4, {2000: M.D8})
    A.KOLLAR[f"V4_TGK{b}" if b != 5 else "V4_TGK5"] = ({**TB.T1, **T4, "TEK_GIRIS": "1", "KOM": k}, 4, {2000: M.D8})


def analiz():
    print(f"{'maliyet':8s} {'T1 yıllık':>10s} {'T4 yıllık':>10s} {'fark':>7s} {'T1 Sh':>6s} {'T4 Sh':>6s} {'T1 dd':>6s} {'T4 dd':>6s}")
    for b in (5, 10, 15):
        a, c = U.seri(f"V1_TGK{b}"), U.seri(f"V4_TGK{b}")
        oa, oc = U.olc(a), U.olc(c)
        print(f"{b:>3d} bp   {oa[0]:+10.1f} {oc[0]:+10.1f} {oc[0]-oa[0]:+7.1f} {oa[1]:6.2f} {oc[1]:6.2f} {oa[2]:6.1f} {oc[2]:6.1f}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
