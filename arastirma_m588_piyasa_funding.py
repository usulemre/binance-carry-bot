#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 588 — YENİ EKSEN: PİYASA GENELİ FUNDING SEVİYESİ (kaldıraç talebinin DÜZEYİ) → T4'ün ileri getirisi / kötü günü.

Haritada ölçülmemiş: prim çarpanı (madde 239/288/581) funding'in KESİTSEL YAYILIMINA (p90 − p10) bakar; piyasa çapında
funding DÜZEYİNE (uygun evrenin medyanı) hiç bakılmadı. Hipotez: bütün piyasa long kaldıraçlıyken (medyan funding yüksek)
piyasa çapında long çöküşü (madde 537: kaybın %60'ı long, en büyük günler piyasa çapında) daha olası → T4'ün ileri
getirisi düşük, kötü günü sık.

ÖN KAYIT (koşudan önce yazıldı):
  Ölçü X = uygun evrenin (zemin 'uy') medyan 60 sa funding'i (sk_bar60), günlük son bar, 30 g ortalama, nedensel (1 gün gecikme).
  İkinci ölçü X7 = 7 g ortalama (hızlı). Kitap serisi: T4, canlı gibi giriş + 5 bp, MERD_SIRA=1, 2.000 $ iki hiza ortalaması
  (/tmp/m_ekim_kuru, madde 587 kuru koşusu, uzun zemin 2020-07 → 2026-09).
  X'in yüzdeliği GENİŞLEYEN pencereyle (o güne kadarki geçmiş, en az 180 g) hesaplanır — tam örnek kuantili YOK.
  Motor koşusuna geçme şartı (X ya da X7 için, IS = ≤2024 ve OOS = 2025+ AYRI AYRI):
    (a) üst beşte birde (yüzdelik ≥ 80) sonraki 5 g T4 getirisi ortalaması, tüm günlerin ortalamasının ALTINDA, ve
    (b) üst beşte birde sonraki gün ≤ −%3 olasılığı, genelin ≥ 1,5 katı.
  İkisi de iki dönemde tutmazsa eksen KAPANIR (motor koşusu yapılmaz).
"""
import pickle
import numpy as np
import pandas as pd
import arastirma_m346_prim as M

M.CIKTI = "/tmp/m_ekim_kuru"
g = sum(M.gunluk(f"M357_EK_T4_2000_{h}") for h in (0, 1)) / 2
z = pickle.load(open("/tmp/zemin.pkl", "rb"))
sk = pickle.load(open("/tmp/sk_bar60.pkl", "rb"))
uy = z["uy"]
uy = (uy if isinstance(uy, pd.DataFrame) else pd.DataFrame(uy, index=z["C"].index, columns=z["C"].columns))
sk = sk.reindex(index=uy.index, columns=uy.columns)
med = sk.where(uy.astype(bool)).median(axis=1)
gun = med.groupby(med.index.date).last(); gun.index = pd.DatetimeIndex(gun.index)

ileri5 = (1 + g).rolling(5).apply(np.prod, raw=True).shift(-5) - 1        # t+1..t+5
kotu = (g.shift(-1) <= -0.03).astype(float)


def yuzdelik(x):
    v = x.values; out = np.full(len(v), np.nan)
    for i in range(180, len(v)):
        gec = v[:i][np.isfinite(v[:i])]
        if len(gec) >= 180 and np.isfinite(v[i]):
            out[i] = (gec < v[i]).mean() * 100
    return pd.Series(out, index=x.index)


print(f"T4 serisi {g.index[0].date()} → {g.index[-1].date()}, {len(g)} gün; uygun evren medyan coin "
      f"{int(uy.sum(axis=1).median())}")
sonuc = {}
for ad, pen in (("X30", 30), ("X7", 7)):
    x = gun.rolling(pen, min_periods=pen // 2).mean().shift(1)
    q = yuzdelik(x).reindex(g.index)
    print(f"\n{ad}: medyan funding (günlük birim) ort {x.mean():.5f}, sd {x.std():.5f}")
    print(f"{'dönem':6s} {'kova':>8s} {'gün':>5s} {'ileri5 %':>9s} {'−%3 olas.':>9s}")
    gec = []
    for dn, m in (("IS", g.index < "2025-01-01"), ("OOS", g.index >= "2025-01-01")):
        ok = m & q.notna()
        tum5, tumk = ileri5[ok].mean() * 100, kotu[ok].mean() * 100
        for kv, (lo, hi) in (("0-20", (0, 20)), ("20-80", (20, 80)), ("80-100", (80, 101))):
            s = ok & (q >= lo) & (q < hi)
            print(f"{dn:6s} {kv:>8s} {int(s.sum()):5d} {ileri5[s].mean()*100:+9.2f} {kotu[s].mean()*100:9.2f}")
        s = ok & (q >= 80)
        a = ileri5[s].mean() * 100 < tum5; b = kotu[s].mean() * 100 >= 1.5 * tumk
        print(f"{dn:6s} {'tümü':>8s} {int(ok.sum()):5d} {tum5:+9.2f} {tumk:9.2f}   şart a {'Y' if a else 'X'} · b {'Y' if b else 'X'}")
        gec.append(a and b)
    sonuc[ad] = all(gec)
print("\nHÜKÜM:", {k: ("MOTORA" if v else "KAPANDI") for k, v in sonuc.items()})
