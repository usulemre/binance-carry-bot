#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 489 — T2 (BRP80_CAP_A43) BÖLGESİNDE RASTGELE ORTAK TARAMA (16 ayar, tohum 489).

Madde 480 T1 çevresini taradı (taban tepede). T2 yeni bir bölge: short tarafı 3 bacak + tavan, kademe payı 0,80.
Düğmeler birlikte rastgele çekilir (T2'nin kendi düğmeleri dahil: N_S, tavan, pay).
ÖN KAYIT: seçim yalnız IS Sharpe'ına göre; IS birincisi OOS'ta T2'yi geçmeli VE eşitVol (T2'ye karşı) ≥ +8 →
T3 adayı. IS↔OOS sıra korelasyonu raporlanır.
"""
import sys, numpy as np, pandas as pd
import arastirma_tabanlar as TB
import arastirma_m443_kotu_gun_kalkani as K

U = {"HAVUZ": ["3", "4", "5"], "REB_GUN": ["4", "5", "6"], "TPL": ["0.55", "0.60", "0.70"], "TPS": ["0.18", "0.20", "0.25"],
     "MERD_ESIK": ["0.40", "0.45", "0.50"], "MERDS_ESIK": ["0.12", "0.15", "0.18"], "MERD_PAY": ["0.75", "0.80", "0.85"],
     "REZERV": ["0.05", "0.10", "0.15"], "CAP_ORTAK": ["0.07", "0.08", "0.09"], "N_S": ["2", "3", "4"],
     "SK_DOSYA": ["/tmp/sk_bar48.pkl", "/tmp/sk_bar60.pkl", "/tmp/sk_bar96.pkl"]}
rng = np.random.default_rng(489)
AYAR = {f"Q{j:02d}": {k: v[rng.integers(len(v))] for k, v in U.items()} for j in range(16)}
TB.kur({}, onek="T")
for a, d in AYAR.items():
    TB.A.KOLLAR[f"T2R_{a}"] = ({**TB.T2, **d}, 4, {2000: TB.M.D8})
TB.W.A.KOLLAR = TB.A.KOLLAR


def ozet():
    SH = lambda x: x.mean() / x.std() * np.sqrt(365.25)
    b = K.seri(TB.TABAN[2]); s = []
    for ad in [TB.TABAN[1], TB.TABAN[2]] + [f"T2R_{a}" for a in AYAR]:
        g = K.seri(ad); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]; o = K.olc(g)
        s.append(dict(ad=ad, IS_sh=SH(IS), OOS_sh=SH(OOS), IS=K.YIL(IS), OOS=K.YIL(OOS), yil=K.YIL(g), sh=SH(g),
                      dd=K.DD(g), g5=o["g5"], esit=K.YIL(g) - K.YIL(b * (g.std() / b.std()))))
    d = pd.DataFrame(s).set_index("ad").round(2); print(d.sort_values("IS_sh", ascending=False).to_string())
    x = d.drop([TB.TABAN[1], TB.TABAN[2]])
    print("\nIS~OOS Sharpe sıra korelasyonu:", round(x.IS_sh.corr(x.OOS_sh, method="spearman"), 3))
    en = x.IS_sh.idxmax(); r = x.loc[en]; t = d.loc[TB.TABAN[2]]
    print(f"IS birincisi {en} {AYAR[en[4:]]}\n  OOS {r.OOS:+.1f} vs T2 {t.OOS:+.1f} · eşitVol {r.esit:+.1f} → "
          + ("T3 ADAYI" if r.OOS > t.OOS and r.esit >= 8 else "RED"))


if __name__ == "__main__":
    {"kos": TB.A.kos, "analiz": ozet}[sys.argv[1]]()
