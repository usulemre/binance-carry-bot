#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 457 — T60 ÜZERİNDE HİÇ OYNANMAMIŞ EKSENLER (yeni yapı arayışı).

Kullanıcı: "savunma yaklaşımı iyi değil; T60'ı bulmadan önce 'tek kazanç kaldıraç' demiştin, sonra T60'ı
bulduk — başka yaklaşımlar dene, yeni yapı bulalım". T60 araştırması evren/yaş/rezerv/pencere/TP
eksenlerini taradı. Taban: canlı varsayılan (T60 + 24 sa −%45 stop, TAZE 2). 2.000 $ D8, iki hiza, kaymalı.
EKSENLER (her kol TEK değişiklik):
  tutma 6/7 g (15 faz korunur: FAZ_LISTE) · oynaklığa ölçekli long TP (TPKATL 2/3) · short maks tutma
  2/3 g (YAS_S) · taraf havuzu (HAVUZ_L 6, HAVUZ_S 3) · bacak asimetrisi (5L/4S, 4L/3S) · rezerv eşiği
  (REZ_ESIK 0,010/0,025) · rezerv coin tavanı KAP 0,08 · akış sinyali ağırlığı (AKIS 0 / 0,4) ·
  sinyal büyüklüğüyle ağırlık (AGIRLIK=buyukluk, SK_GAMMA 0,5/1,0).
ÖN KAYIT: bu madde TARAMA; seçim yalnız IS (22-07..24-12) yıllık getirisiyle. IS'te tabanı >= +8 puan
geçen ve OOS'ta (25-01..26-09) tabanın gerisinde kalmayan eksenler madde 458'de birleştirilir.
"""
import sys
import numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
T = {**K.T60, "SLL24": "0.45", "SLL24_TAZE": "2"}
faz = lambda gun: ",".join(str(int(round(k * gun * 6 / 15))) for k in range(15))
DEG = {"REB6": {"REB_GUN": "6", "FAZ_LISTE": faz(6)}, "REB7": {"REB_GUN": "7", "FAZ_LISTE": faz(7)},
       "TPK2": {"TPKATL": "2.0"}, "TPK3": {"TPKATL": "3.0"},
       "YS12": {"YAS_S": "12"}, "YS18": {"YAS_S": "18"},
       "HL6": {"HAVUZ_L": "6", "HAVUZ_S": "4"}, "HS3": {"HAVUZ_L": "4", "HAVUZ_S": "3"},
       "N54": {"N_L": "5", "N_S": "4"}, "N43": {"N_L": "4", "N_S": "3"},
       "RE10": {"REZ_ESIK": "0.010"}, "RE25": {"REZ_ESIK": "0.025"}, "KAP8": {"KAP": "0.08"},
       "AK0": {"AKIS": "0"}, "AK4": {"AKIS": "0.4"},
       "BY05": {"AGIRLIK": "buyukluk", "SK_GAMMA": "0.5"}, "BY10": {"AGIRLIK": "buyukluk", "SK_GAMMA": "1.0"}}
A.KOLLAR = {f"E{a}": ({**T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}


def analiz():
    rows = []
    for ad in ["KD24_45T2"] + list(A.KOLLAR):
        try:
            g = K.seri(ad)
        except Exception as e:
            print(ad, "yok", e); continue
        o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        rows.append(dict(kol=ad, yil=o["yil"], IS=K.YIL(IS), OOS=K.YIL(OOS), dd=o["dd"], enkotu=o["enkotu"],
                         g5=o["g5"], TemEyl26=o["son"], sh=g.mean() / g.std() * np.sqrt(365.25)))
    T_ = pd.DataFrame(rows).set_index("kol"); b = T_.loc["KD24_45T2"]
    T_["dIS"] = T_.IS - b.IS; T_["dOOS"] = T_.OOS - b.OOS; T_["dYil"] = T_.yil - b.yil
    pd.set_option("display.width", 220)
    print(T_.sort_values("dIS", ascending=False).round(2).to_string())
    sec = T_[(T_.dIS >= 8) & (T_.dOOS >= 0) & (T_.index != "KD24_45T2")]
    print("\nIS'te >= +8 ve OOS'ta geride kalmayan eksenler:", list(sec.index) or "YOK")
    print("Genelleme: IS farki vs OOS farki sira korelasyonu", round(T_.dIS.rank().corr(T_.dOOS.rank()), 3))


if __name__ == "__main__":
    {"kos": A.kos, "analiz": analiz}[sys.argv[1]]()
