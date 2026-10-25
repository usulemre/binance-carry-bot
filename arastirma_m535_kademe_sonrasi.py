#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 535 — DÜZELTİLMİŞ MODELDE T4: KADEME SONRASI ÇIKIŞLAR (geri alım / koşucu / başabaş) (kaldıraçsız, uzun zemin; önce ./zemin_sec.sh uzun).
Merdivenin bütün ayarları (kademe +%45 / −%15, pay) iyimser dolum kuralıyla seçilmişti (madde 527). Düzeltilmiş modelde
optimum kaymış olabilir. Taban Q_T4 (T4 + MERD_SIRA=1). KOLLAR: M35 / M55 (long kademe) · MS10 / MS18 (short kademe) ·
P50 / P67 (pay). Ayrıca Q_T4NL (merdivensiz) referans.
ÖN KAYIT (madde 503 kuralı, Q_T4'e karşı): TÜM yıllık ≥ +8, Sh ≥ +0,05, üç dönemde > 0, dd en fazla 1 puan derin."""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m509_t4_uzun as B

Q = {**B.T4, "MERD_SIRA": "1"}
U.KOL = {"Q_T4": Q, "Q_GERI_L": {**Q, "MERD_GERI": "1", "MERD_GERI_TARAF": "long"},
         "Q_KOS25": {**Q, "KOSUCU": "0.25"}, "Q_KOS40": {**Q, "KOSUCU": "0.40"}, "Q_BE": {**Q, "MERD_BE": "1"}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    S = {k: U.seri(k) for k in U.KOL}; b = S["Q_T4"]
    print(f"Q_T4: {U.olc(b)}")
    print("== Q_T4'e karşı (yıllık · Sh · dd farkı; TÜM / YENİ / 22-24 / 25-26) · eşitVol · −%5 altı")
    for k in [k for k in U.KOL if k != "Q_T4"]:
        r = []
        for a, z in (("2020-01-01", "2027-01-01"), ("2020-01-01", "2022-01-01"), ("2022-07-20", "2025-01-01"), ("2025-01-01", "2027-01-01")):
            x = S[k][(S[k].index >= a) & (S[k].index < z)]; y = b[(b.index >= a) & (b.index < z)]
            ox, oy = U.olc(x), U.olc(y); r.append((ox[0] - oy[0], ox[1] - oy[1], ox[2] - oy[2]))
        x = S[k]; ev = U.olc(x)[0] - U.olc(b * (x.std() / b.std()))[0]
        ok = r[0][0] >= 8 and r[0][1] >= 0.05 and all(q[0] > 0 for q in r[1:]) and r[0][2] >= -1
        print(f"  {k:9s} " + " | ".join(f"{q[0]:+6.1f} {q[1]:+.2f} {q[2]:+.1f}" for q in r) + f" · {ev:+6.1f} · {U.olc(x)[4]}" + ("  ADAY" if ok else ""))


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
