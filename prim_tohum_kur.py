#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 585: T7K prim çarpanı için TOHUM geçmişi. Bot çarpanı ancak ~90 günlük kendi geçmişi birikince uygular (öncesinde 1,0).
Bu betik araştırma zemininden (uzun zemin, sk_bar60) son 180 günün kesitsel primini (p90 − p10, YILLIK birim = günlük × 365,
botun prim_olc'u ile aynı birim) bot biçiminde yazar: carry_prim_tohum.csv (zaman,değer; 4 sa'te bir). Sunucuda:
  cp carry_prim_tohum.csv carry_prim.csv   (yalnız carry_prim.csv YOKSA)
Böylece çarpan ilk turdan itibaren motordaki gibi çalışır. Kullanım: ./zemin_sec.sh uzun && python3 prim_tohum_kur.py

MADDE 590 DÜZELTMESİ: ilk sürüm primi zeminin TEMEL uygunluk maskesinden ('uy': 100M hacim, 90 g yaş) ölçüyordu. Motor
(g33, BRUT_PRIM) ve canlı bot (prim_olc(funding)) ise T7K'NIN KENDİ EVRENİNDEN ölçer: 70M hacim, 60 g yaş, TradFi hariç,
evren tabanı 30, bakiye kademesinin asgari-emir dışlaması (2.000 $ = D8). O evren daha geniş ve uçlu → prim ~%27-48 daha büyük.
Tohum küçük kalınca canlıda "30 g ölçüm (canlı evren) / 180 g medyan (tohum evreni)" oranı şişer, çarpan 1,0'a yapışır ve
T7K ilk aylarda backtest'teki kadar küçülmez. Artık evren motorla birebir kurulur. Kademe: TOHUM_KADEME=D8 (varsayılan) | D2 | D1.
"""
import os, pickle
import pandas as pd
import carry_denetim as D
import arastirma_m346_prim as M
from tradfi_liste import TRADFI

KOK = os.environ.get("TOHUM_ZEMIN", "/tmp/zu")
KADEME = os.environ.get("TOHUM_KADEME", "D8")
HACIM, YAS_GUN, TABAN_N, TABAN_HACIM = 7e7, 60, 30, 2e7          # T4/T7K evreni (carry_bot varsayılanları)


def evren(P, C):
    """g33'ün HACIM_ESIK / YAS_GUN / HACIM_MIN_EVREN / SEMBOL_HARIC bloklarıyla AYNI maske."""
    u = D.uygunluk(P["C"], P["HAC"], P["YAS"], P["DON"], hacim=HACIM, yas_bar=YAS_GUN * 6, donuk_esik=0.10).copy()
    u[[c for c in u.columns if c in TRADFI]] = False
    tb = D.uygunluk(P["C"], P["HAC"], P["YAS"], P["DON"], hacim=TABAN_HACIM, yas_bar=YAS_GUN * 6, donuk_esik=0.10).copy()
    tb[[c for c in tb.columns if c in TRADFI]] = False
    rk = P["HAC"].where(tb).rank(axis=1, ascending=False)
    u = u | (tb & (rk <= TABAN_N)).where(u.sum(axis=1) < TABAN_N, False)
    u = u.reindex(index=C.index, columns=C.columns).fillna(False).astype(bool)
    u[[c for c in u.columns if c in getattr(M, KADEME)]] = False
    return u


if __name__ == "__main__":
    Z = pickle.load(open(f"{KOK}/zemin.pkl", "rb")); C = Z["C"]
    P = pickle.load(open(f"{KOK}/panel.pkl", "rb"))
    U = evren(P, C)
    S = pickle.load(open(f"{KOK}/sk_bar60.pkl", "rb")).reindex(index=C.index, columns=C.columns)
    Sd = S.where(U)
    pr = (Sd.quantile(0.9, axis=1) - Sd.quantile(0.1, axis=1)) * 365.0
    pr = pr[pr.index >= pr.index[-1] - pd.Timedelta(days=180)].dropna()
    with open("carry_prim_tohum.csv", "w") as f:
        for t, v in pr.items():
            f.write("%.0f,%.8f\n" % (t.timestamp(), v))
    print(f"carry_prim_tohum.csv ({KADEME}, ort. uygun {float(U.loc[pr.index].sum(axis=1).mean()):.1f} coin): {len(pr)} satır, "
          f"{pr.index[0]} .. {pr.index[-1]}, medyan {pr.median():.4f}, son 30 g ort {pr.iloc[-180:].mean():.4f}")
