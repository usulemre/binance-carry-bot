#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 464 — MERDİVEN MR45 İKİ SEVİYE PROTOKOL (madde 375) + 3.500 $.

Madde 463: merdiven platosu (ilk kademe %35-%50, pay 1/3-2/3) hepsi Sharpe 3,54-3,72 (taban 3,44), eşit
oynaklıkta +11..+29. IS'te en iyi: MR45 (long'un yarısı +%45'te, kalanı +%60'ta) IS +166,2.
KONTROL: KD24_45T2 (canlı varsayılan: T60 + 24 sa stop). İki seviye (2.000 D8 / 3.500 D2) x iki hiza;
dört şart + P >= %95 → AYAR. P'nin güç sınırı (madde 434) bilinçli: P %80-95 + plato → kullanıcıya
"güçlü aday" olarak sunulur.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
A.SEVIYE = (2000, 3500)   # m443 importu (2000,) yapiyor
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
A.KOLLAR = {"XMR45": ({**T, "MERD_ESIK": "0.45", "MERD_PAY": "0.5"}, 4, {2000: M.D8, 3500: M.D2})}


def analiz():
    gec = {}
    for sev in (2000, 3500):
        n = 0
        for h in (0, 1):
            gk = M.gunluk(f"M357_KD24_45T2_{sev}_{h}"); ga = M.gunluk(f"M357_XMR45_{sev}_{h}")
            Kc, Ad = M.olcum("K", gk), M.olcum("MR45", ga)
            s = KK.gecer_mi(Kc, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
            p, _ = M.bootstrap(gk, ga, n=1000)
            isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
            son = lambda x: ((1 + x[x.index >= "2026-07-01"]).prod() - 1) * 100
            print(f"MR45 {sev} {h} yillik {Ad.getiri-Kc.getiri:+6.1f} Sh22 {Ad.erken-Kc.erken:+.2f} Sh25 {Ad.gec-Kc.gec:+.2f} "
                  f"dusus {Ad.dusus-Kc.dusus:+.1f} esitR {s['esit_risk']-Kc.getiri:+6.1f} {isr} P {p:5.1f} | Tem-Eyl26 {son(ga):+.1f}% vs {son(gk):+.1f}%", flush=True)
            n += int(s["gecer"] and p >= M.KANIT_BARI)
        gec[sev] = n == 2
    print(f"HUKUM MR45: {'AYAR' if all(gec.values()) else 'RED (P bari)'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
