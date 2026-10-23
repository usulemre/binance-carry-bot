#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 460 — SİNYAL PENCERESİ TOPLULUĞU (seçimin kalbi: hangi coin).

T60 tek pencere kullanıyor (60 sa funding ortalaması). Kısa pencere taze ama gürültülü, uzun pencere
kalıcı ama geç. Birkaç pencerenin ORTALAMASI (aynı birim, rezerv eşiği bozulmaz) iki zaafı birlikte
azaltabilir. Paneller canli_sinyal_kur.py ile (canlı tahminciyle aynı): 24 / 96 / 144 sa yeni.
KOLLAR (taban T60 + 24 sa stop, 2.000 $): P24, P96, P144 tek pencere · E24_60, E36_60_96, E48_96_144,
E24_60_144 topluluk.
ÖN KAYIT: seçim yalnız IS yıllık getirisiyle; IS'te tabanı >= +8 ve OOS'ta >= 0 geçen kol, eşit oynaklıkta
da >= +8 ise madde 461 sağlamlık testine.
"""
import sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
DEG = {"P24": "/tmp/sk_bar24.pkl", "P96": "/tmp/sk_bar96.pkl", "P144": "/tmp/sk_bar144.pkl",
       "E24_60": "/tmp/sk_ens_24_60.pkl", "E36_60_96": "/tmp/sk_ens_36_60_96.pkl",
       "E48_96_144": "/tmp/sk_ens_48_96_144.pkl", "E24_60_144": "/tmp/sk_ens_24_60_144.pkl"}
A.KOLLAR = {f"S{a}": ({**T, "SK_DOSYA": f}, 4, {2000: M.D8}) for a, f in DEG.items()}


def analiz():
    b = K.seri("KD24_45T2"); bIS, bOOS = b[b.index < "2025-01-01"], b[b.index >= "2025-01-01"]
    print(f"{'kol':12s} {'yillik':>7s} {'IS':>7s} {'OOS':>7s} {'Sh':>5s} {'dd':>6s} {'enkotu':>7s} {'-5%':>4s} {'TemEyl':>7s} {'esitVol fark':>12s}")
    for ad in ["KD24_45T2"] + list(A.KOLLAR):
        g = K.seri(ad); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        kv = g.std() / b.std(); fark = o["yil"] - K.YIL(b * kv)
        dIS, dOOS = K.YIL(IS) - K.YIL(bIS), K.YIL(OOS) - K.YIL(bOOS)
        h = "ADAY" if ad != "KD24_45T2" and dIS >= 8 and dOOS >= 0 and fark >= 8 else ""
        print(f"{ad:12s} {o['yil']:+7.1f} {K.YIL(IS):+7.1f} {K.YIL(OOS):+7.1f} {g.mean()/g.std()*np.sqrt(365.25):5.2f} {o['dd']:6.1f} "
              f"{o['enkotu']:7.2f} {o['g5']:4d} {o['son']:+7.1f} {fark:+12.1f} {h}")


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
