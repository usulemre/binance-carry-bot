#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 480 — MERDİVENLİ KİTAPTA RASTGELE ORTAK TARAMA (24 ayar, tohum 480).

Madde 438 T60'ı kendi bölgesinin tepesinde bulmuştu — ama MERDİVENDEN ÖNCE. Merdiven çıkışı değiştirdi; tek tek
eksenler (470-476) taban tepede dedi, fakat eksenler BİRLİKTE kayabilir (ör. merdivenle daha uzun tutma / daha
yüksek son TP / daha geniş havuz). Her ayar 11 düğmeyi aynı anda rastgele çeker.
ÖN KAYIT (koşudan önce): ayar SEÇİMİ yalnız IS'e (2022-2024) göre — IS Sharpe'ı en yüksek ayar. O ayar OOS'ta
tabanı geçmeli (yıllık) VE eşit oynaklıkta ≥ +8 → protokol. Ayrıca IS sırası ile OOS sırasının korelasyonu
raporlanır (genelleme var mı).
"""
import sys, numpy as np, pandas as pd
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W
import arastirma_m443_kotu_gun_kalkani as K

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
U = {"HAVUZ": ["3", "4", "5"], "REB_GUN": ["4", "5", "6"], "TPL": ["0.50", "0.60", "0.70", "0.80"],
     "TPS": ["0.18", "0.20", "0.25"], "MERD_ESIK": ["0.35", "0.45", "0.55"], "MERDS_ESIK": ["0.12", "0.15", "0.18"],
     "MERD_PAY": ["0.60", "0.667", "0.75"], "REZERV": ["0.05", "0.10", "0.15"], "YAS_GUN": ["60", "90"],
     "HACIM_ESIK": ["5e7", "7e7", "1e8"], "SK_DOSYA": ["/tmp/sk_bar48.pkl", "/tmp/sk_bar60.pkl", "/tmp/sk_bar96.pkl"]}
rng = np.random.default_rng(480)
AYAR = {f"R{j:02d}": {k: v[rng.integers(len(v))] for k, v in U.items()} for j in range(24)}
A.KOLLAR = {f"MT{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in AYAR.items()}
W.A.KOLLAR = A.KOLLAR

def ozet():
    b = K.seri(W.TABAN); SH = lambda x: x.mean() / x.std() * np.sqrt(365.25)
    s = []
    for ad in [W.TABAN] + list(A.KOLLAR):
        g = K.seri(ad); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
        s.append(dict(ad=ad, IS_sh=SH(IS), OOS_sh=SH(OOS), IS=K.YIL(IS), OOS=K.YIL(OOS), yil=K.YIL(g), sh=SH(g),
                      dd=K.DD(g), esit=K.YIL(g) - K.YIL(b * (g.std() / b.std()))))
    d = pd.DataFrame(s).set_index("ad").round(2); print(d.sort_values("IS_sh", ascending=False).to_string())
    x = d.drop(W.TABAN); print("\nIS Sharpe sırası ~ OOS Sharpe sırası (Spearman):", round(x.IS_sh.corr(x.OOS_sh, method="spearman"), 3))
    en = x.IS_sh.idxmax(); r = x.loc[en]; t = d.loc[W.TABAN]
    print(f"IS'te en iyi: {en} {AYAR[en[2:]]}\n  OOS {r.OOS:+.1f} vs taban {t.OOS:+.1f} · eşitVol {r.esit:+.1f} → "
          + ("PROTOKOL ADAYI" if r.OOS > t.OOS and r.esit >= 8 else "RED"))

if __name__ == "__main__":
    {"kos": A.kos, "analiz": ozet}[sys.argv[1]]()
