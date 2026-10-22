#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 430 — İKİ YENİ EKSEN (mevcut günlük serilerden, motor koşusu gerekmez).

A) KİTABIN KENDİ GETİRİSİNE GÖRE DOZ (strateji üzerinde zaman-serisi momentumu):
   s_t, yalnız t-1'e kadarki kitap getirisinden belirlenir; günlük getiri s_t ile ölçeklenir,
   doz değişimi |Δs| x %0,10 maliyet (iki bacak ücret+kayma) öder.
   Kurallar (ön kayıt): MOMn  (son n gün > 0 → 1,25x, değilse 0,50x), n ∈ {10,20,30,60,90}
                        TERSn (tersi), DD10/DD15 (tepeden −%10/−%15 altındayken 0,50x).
   Kalıcılık testi: son n gün getirisi ile sonraki n gün getirisinin korelasyonu.
   Ölçüt: Sharpe (doz Sharpe'ı artırmazsa kaldıraçla aynı şey) ve EŞİT OYNAKLIKTA yıllık getiri.
B) AYAR TOPLULUĞU: madde 425 taramasında IS (22-24) Sharpe'ına göre en iyi k ayar (k=3,5,10)
   ve 24'ün tamamı, sermaye eşit bölünmüş (günlük getirilerin ortalaması ≈ ayrı alt hesaplar).
   OOS (2025-01..2026-09) kontrolle ve "IS'te en iyi TEK ayar" ile karşılaştırılır.
   Ön kayıt: topluluk OOS Sharpe'ta en iyi tek ayarı VE kontrolü geçerse protokol adayı.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m346_prim as M

M.CIKTI = "/tmp/m412"
SH = lambda x: x.mean() / x.std() * np.sqrt(365.25)
YIL = lambda x: ((1 + x).prod() ** (365.25 / len(x)) - 1) * 100
DD = lambda x: (((1 + x).cumprod() / (1 + x).cumprod().cummax()) - 1).min() * 100


def ozet(ad, g, ref=None):
    IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
    s = f"{ad:9s} Sh {SH(g):.2f} (IS {SH(IS):.2f} OOS {SH(OOS):.2f}) yil {YIL(g):+7.1f} dd {DD(g):6.1f}"
    if ref is not None:  # eşit oynaklıkta getiri
        e = g * (ref.std() / g.std())
        s += f" | esitVol yil {YIL(e):+7.1f} (fark {YIL(e)-YIL(ref):+6.1f}) dd {DD(e):6.1f}"
    return s


def doz(g, kural, n):
    eq = (1 + g).cumprod()
    if kural == "MOM":
        t = eq.pct_change(n).shift(1); s = np.where(t > 0, 1.25, 0.5)
    elif kural == "TERS":
        t = eq.pct_change(n).shift(1); s = np.where(t > 0, 0.5, 1.25)
    else:
        d = (eq / eq.cummax() - 1).shift(1); s = np.where(d < -n / 100, 0.5, 1.0)
    s = pd.Series(s, g.index); s[t.isna() if kural != "DD" else d.isna()] = 1.0
    return s * g - s.diff().abs().fillna(0) * 0.001, s.mean()


def A():
    for sev in (2000, 3500):
        g = (M.gunluk(f"M357_KAYMA_{sev}_0") + M.gunluk(f"M357_KAYMA_{sev}_1")) / 2
        print(f"\n=== A) {sev} $ kontrol (KAYMA) ===\n" + ozet("KONTROL", g))
        eq = (1 + g).cumprod()
        for n in (10, 20, 30, 60, 90):
            a, b = eq.pct_change(n), eq.pct_change(n).shift(-n)
            print(f"  kalicilik n={n:2d}: corr(son n, sonraki n) = {a.iloc[::n].corr(b.iloc[::n]):+.3f}")
        for k, ns in (("MOM", (10, 20, 30, 60, 90)), ("TERS", (10, 20, 30, 60, 90)), ("DD", (10, 15))):
            for n in ns:
                x, ort = doz(g, k, n)
                print(ozet(f"{k}{n}", x, g) + f" ort.doz {ort:.2f}")


def gunM(p):
    E = pd.read_pickle(p); r = E.pct_change().dropna()
    x = (1 + r).groupby(r.index.date).prod() - 1; x.index = pd.DatetimeIndex(x.index); return x


def B():
    G = {}
    for f in sorted(os.listdir("/tmp/m425")):
        if f.endswith("_0.pkl"):
            a = f[:-6]
            try:
                G[a] = (gunM(f"/tmp/m425/{a}_0.pkl") + gunM(f"/tmp/m425/{a}_1.pkl")) / 2
            except Exception:
                pass
    D = pd.DataFrame(G).dropna()
    k0 = D.pop("K00")
    IS = D[D.index < "2025-01-01"]
    sira = IS.apply(SH).sort_values(ascending=False).index
    print(f"\n=== B) ayar toplulugu (madde 425, {len(sira)} ayar, 2.000 $ D8) ===")
    print(ozet("KONTROL", k0))
    print(ozet(f"TEK {sira[0]}", D[sira[0]], k0))
    for k in (3, 5, 10, len(sira)):
        print(ozet(f"TOP{k}", D[list(sira[:k])].mean(axis=1), k0))
    c = D[list(sira[:5])][D.index >= "2025-01-01"].corr().values
    print(f"  ilk 5'in OOS gunluk korelasyon ort.: {c[np.triu_indices(5, 1)].mean():.3f}")
    for k in (3, 5, 10):
        x = D[list(sira[:k])].mean(axis=1)
        m = x[x.index >= "2026-07-01"]; mk = k0[k0.index >= "2026-07-01"]
        print(f"  TOP{k} Tem-Eyl 2026: {((1+m).prod()-1)*100:+.1f}% vs kontrol {((1+mk).prod()-1)*100:+.1f}%")


if __name__ == "__main__":
    A(); B()
