#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 521 — T4 ÜZERİNDE SHORT YAPISI: bacak sayısı ve short kademesi, kaldıraçsız, uzun zemin (önce ./zemin_sec.sh uzun).

T4'te short tarafı 2 g'de bir yenileniyor ve %8 tavanlı — short kademesi (−%15) ve 4 short bacak bu yapıdan ÖNCE seçildi.
Sık yenilenen kitapta kademe gereksiz, daha çok short bacak (tavanla birlikte daha geniş yayılma) faydalı olabilir.
KOLLAR: MS0 (short kademesi kapalı) · NS5 / NS6 (short bacak 5 / 6; long 4).
ÖN KAYIT (madde 503 ile aynı, T4'e karşı): TÜM dönemde yıllık ≥ +8 ve Sharpe ≥ +0,05, üç dönemin üçünde yıllık > 0, dd en
fazla 1 puan derin → aday.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m499_sreb_durdur as D
import arastirma_tabanlar as TB

T4 = {**TB.T1, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
U.KOL = {"U_T1": TB.T1, "U_T3FN30": T4, "U_T4MS0": {**T4, "MERDS_ESIK": "0"}, "U_T4NS5": {**T4, "N_L": "4", "N_S": "5"},
         "U_T4NS6": {**T4, "N_L": "4", "N_S": "6"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    D.analiz()
    S = {k: U.seri(k) for k in U.KOL}; b = S["U_T3FN30"]
    print("\n== T4'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26)")
    for k in ("U_T4MS0", "U_T4NS5", "U_T4NS6"):
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        x = S[k]; print(f"    {k} eşit oynaklıkta T4: {U.olc(x)[0]-U.olc(b * (x.std() / b.std()))[0]:+.1f}")
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:10s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
