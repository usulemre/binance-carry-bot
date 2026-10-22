#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 436 — R30Y60S + TPL 0,60 (T60) İKİ SEVİYE PROTOKOL.

Madde 435: ön kayıtlı kural (IS 1.'si) T60R05S25'i seçti ama dd 4,3 puan kötü → RED.
TPL ekseni (0,50 / 0,60 / 0,70) ise dd'yi bozmadan IS ve OOS'ta düzenli iyileşiyor: T60 ve T70
IS +155/+159, OOS +346/+345, dd −20,8 (R30Y60S +143 / +295 / −20,9). T60 dd'ye bakıldıktan
sonra seçildi (seçim yanlılığı, açıkça kayıtlı). Burada iki seviye x iki hiza, iki karşılaştırma:
  (a) bugünkü kitap (M357_KAYMA) karşısında madde 375 kuralı,
  (b) R30Y60S karşısında artış (T60 R30Y60S'ten iyi mi).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import karar_kurali as KK

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; M.KANIT_BARI = 95.0
B = dict(HAVUZ="4", REB_GUN="5", TPL="0.60", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60",
         HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", AGIRLIK_KAYMA="1")
A.KOLLAR = {"T60": (B, 4, {2000: M.D8, 3500: M.D2})}


def analiz():
    for kont in ("KAYMA", "R30Y60S"):
        gec = {}
        for sev in (2000, 3500):
            n = 0
            for h in (0, 1):
                gk = M.gunluk(f"M357_{kont}_{sev}_{h}"); ga = M.gunluk(f"M357_T60_{sev}_{h}")
                K, Ad = M.olcum("K", gk), M.olcum("T60", ga)
                s = KK.gecer_mi(K, Ad, gunluk_kontrol=gk.values, gunluk_aday=ga.values)
                p, _ = M.bootstrap(gk, ga, n=1000)
                isr = "".join("Y" if v[0] else "X" for v in s["sartlar"].values())
                son = lambda x: ((1 + x[x.index >= "2026-07-01"]).prod() - 1) * 100
                print(f"T60 vs {kont:7s} {sev} {h} yillik {Ad.getiri-K.getiri:+6.1f} dusus {Ad.dusus-K.dusus:+.1f} "
                      f"esitR {s['esit_risk']-K.getiri:+6.1f} {isr} P {p:5.1f} | Tem-Eyl26 {son(ga):+.1f}% vs {son(gk):+.1f}%",
                      flush=True)
                n += int(s["gecer"] and p >= M.KANIT_BARI)
            gec[sev] = n == 2
        print(f"HUKUM T60 vs {kont}: {'AYAR' if all(gec.values()) else 'RED'}\n", flush=True)


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
