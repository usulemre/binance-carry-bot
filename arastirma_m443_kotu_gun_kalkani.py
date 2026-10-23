#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 443 — KÖTÜ GÜN KALKANI (T60): tek günlük büyük düşüşü az kâr kaybıyla kesmek.

Kullanıcı: "düşen günleri engellemem ama kârı çok minimum kesmem lazım; bir günde çok fazla düşüşü
engellemem lazım". Anatomi (T60, tüm dönem, en kötü 25 gün): piyasa geneli DEĞİL (BTC medyan +%1,5,
T60~BTC korelasyon −0,03); kaybın medyan %49'u TEK coinden, %86'sı ilk 3 coinden. İki tür:
(a) küçük coin LONG'unun tek günde %80-100 çöküşü (POWER, REEF, SIREN); (b) piyasa yükselirken
büyük coin SHORT'unun sıkışması (XRP, DOGE, ONDO, PEPE). Tek coinin hesap payı %7-16 (dilimler
üst üste biniyor).
KOLLAR (taban T60, 2.000 $ D8, iki hiza, kaymalı):
  L30/L40/L50  long stop −%30/−%40/−%50 (SLL) · S50 short stop +%50 (SLS 0,5; T60'ın +%200'ü yerine)
  C06/C08/C10  dilimler arası tek coin tavanı %6/%8/%10 (CAP_ORTAK) · birleşimler L40C08, L40C08S50, L50C10
ÖLÇÜT (ön kayıt): kuyruk = en kötü gün, p1 gün, −%5 altı gün sayısı. KÂR MALİYETİ, aynı kuyruğu
SABİT DOZ DÜŞÜRMEYLE elde etmeye göre ölçülür: T60 x k (k = kolun p1'i / T60 p1'i) yıllık getirisi
ile kolun yıllık getirisi farkı. Fark > 0 → kalkan kuyruğu dozdan UCUZA kesiyor. Bir kol ancak hem
p1'i hem en kötü günü >= %15 iyileştirip doz eşdeğerini >= +5 puan geçerse "ADAY" (madde 375'e).
"""
import sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T60 = dict(HAVUZ="4", REB_GUN="5", TPL="0.60", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60",
           HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0", AGIRLIK_KAYMA="1")
DEG = {"L30": {"SLL": "0.30"}, "L40": {"SLL": "0.40"}, "L50": {"SLL": "0.50"}, "S50": {"SLS": "0.5"},
       "C06": {"CAP_ORTAK": "0.06"}, "C08": {"CAP_ORTAK": "0.08"}, "C10": {"CAP_ORTAK": "0.10"},
       "L40C08": {"SLL": "0.40", "CAP_ORTAK": "0.08"}, "L40C08S50": {"SLL": "0.40", "CAP_ORTAK": "0.08", "SLS": "0.5"},
       "L50C10": {"SLL": "0.50", "CAP_ORTAK": "0.10"}}
A.KOLLAR = {f"K{a}": ({**T60, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}

YIL = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
DD = lambda x: (((1 + x).cumprod() / (1 + x).cumprod().cummax()) - 1).min() * 100


def seri(ad):
    return (M.gunluk(f"M357_{ad}_2000_0") + M.gunluk(f"M357_{ad}_2000_1")) / 2


def olc(g):
    return dict(yil=YIL(g), dd=DD(g), enkotu=g.min() * 100, p1=np.percentile(g, 1) * 100,
                p05=np.percentile(g, 0.5) * 100, g5=int((g < -0.05).sum()), g4=int((g < -0.04).sum()),
                son=((1 + g[g.index >= "2026-07-01"]).prod() - 1) * 100)


def analiz():
    t = seri("T60"); b = olc(t)
    rows = [dict(kol="T60", **b, doz_k=1.0, doz_yil=b["yil"], fark=0.0)]
    for kol in A.KOLLAR:
        g = seri(kol); o = olc(g)
        k = min(1.0, o["p1"] / b["p1"])           # aynı p1 için gereken sabit doz
        dy = YIL(t * k)
        rows.append(dict(kol=kol[1:], **o, doz_k=k, doz_yil=dy, fark=o["yil"] - dy))
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("fark = kolun yillik getirisi - AYNI p1'i sabit doz dusurmeyle elde etmenin yillik getirisi (puan)")
    print(T.round(2).to_string(index=False))
    print()
    for _, r in T.iloc[1:].iterrows():
        iy_p1 = 1 - r.p1 / b["p1"]; iy_ek = 1 - r.enkotu / b["enkotu"]
        aday = iy_p1 >= 0.15 and iy_ek >= 0.15 and r.fark >= 5
        print(f"{r.kol:10s} p1 iyilesme %{iy_p1*100:5.1f}  en kotu gun iyilesme %{iy_ek*100:5.1f}  doz esdegerine fark {r.fark:+6.1f}  -> {'ADAY' if aday else 'RED'}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
