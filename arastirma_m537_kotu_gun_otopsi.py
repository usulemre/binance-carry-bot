#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 537 — T4'ÜN KÖTÜ GÜN OTOPSİSİ (düzeltilmiş model, uzun zemin, 1,0x; önce ./zemin_sec.sh uzun).
Her kötü gün (≤ −%2) coin/taraf bazında fiyat ve funding katkısına ayrılır (GUNLUK_KATKI, madde 414).
Soru: kayıplar hangi tipte yoğunlaşıyor (tek coin short sıkışması / piyasa çapında long çöküşü / funding)?
Bulunan tip için önleyici kural ayrı maddede ön kayıtla sınanır; burada yalnız tanı."""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m497_uzun_gecmis as U
import arastirma_m509_t4_uzun as B
KOK = os.path.dirname(os.path.abspath(__file__)); CIK = "/tmp/m537"; os.makedirs(CIK, exist_ok=True)
Q = {**B.T4, "MERD_SIRA": "1"}


def kos():
    from concurrent.futures import ThreadPoolExecutor
    def bir(h):
        env = dict(os.environ, **dict(U.M.TABAN, **Q), FAZ_KAY=str(h), SEMBOL_HARIC=",".join(U.M.D8),
                   E_CIKTI=f"{CIK}/e_{h}.pkl", GUNLUK_KATKI=f"{CIK}/gk_{h}.pkl", GK_BAS="2020-01-01")
        with open(f"{CIK}/log_{h}.txt", "w") as f:
            return subprocess.run([sys.executable, "g33.py", "ls", "4"], cwd=KOK, env=env, stdout=f,
                                  stderr=subprocess.STDOUT, timeout=6000).returncode
    with ThreadPoolExecutor(2) as ex:
        print(list(ex.map(bir, (0, 1))))


def analiz():
    g = U.seri("Q_T4")
    gk = pd.concat([pd.read_pickle(f"{CIK}/gk_{h}.pkl") for h in (0, 1)])
    gk = gk.groupby(["gun", "sembol"]).agg(fiyat=("fiyat", "sum"), funding=("funding", "sum"), poz=("ort_poz", "mean"))
    gk[["fiyat", "funding"]] /= 2
    gk["taraf"] = np.where(gk.poz > 0, "L", "S")
    kot = g[g <= -0.02]
    print(f"kötü gün (≤ −%2): {len(kot)}  toplam {kot.sum()*100:.1f}")
    sat = []
    for d, v in kot.sort_values().items():
        x = gk.loc[d] if d in gk.index.get_level_values(0) else None
        if x is None: continue
        t = x.fiyat + x.funding
        L = t[x.taraf == "L"].sum(); S = t[x.taraf == "S"].sum(); F = x.funding.sum()
        en = t.sort_values().head(3)
        tek = en.iloc[0] / t[t < 0].sum() if (t < 0).any() else 0
        sat.append(dict(gun=d.date(), getiri=v*100, L=L*100, S=S*100, funding=F*100, tek_pay=tek,
                        en_kotu=", ".join(f"{s}{x.taraf[s]} {en[s]*100:+.1f}" for s in en.index)))
    df = pd.DataFrame(sat); pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 70)
    print(df.head(30).round(2).to_string(index=False))
    df["tip"] = np.select([df.tek_pay > 0.5, (df.L < 0) & (df.S >= 0), (df.S < 0) & (df.L >= 0)],
                          ["tek coin", "long tarafı", "short tarafı"], "iki taraf")
    print("\ntip dağılımı (gün · toplam kayıp puanı):")
    print(df.groupby("tip").getiri.agg(["count", "sum"]).round(1))
    print(f"\nkayıp payı: long {df.L.sum():.1f} · short {df.S.sum():.1f} · funding {df.funding.sum():.1f}")
    df.to_pickle(f"{CIK}/otopsi.pkl")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
