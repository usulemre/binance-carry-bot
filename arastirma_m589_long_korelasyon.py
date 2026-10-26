#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 589 — YENİ EKSEN (ön eleme): TUTULAN LONG'LARIN BİRBİRİYLE KORELASYONU → kötü gün.

Haritada ölçülmemiş: seçim yalnız funding + kalabalık sırasına bakar; seçilen 4 long'un BİRBİRİNE benzeyip benzemediğine
(aynı anlatı / aynı sepet) hiç bakılmadı. Hipotez: tutulan long'lar yüksek korelasyonluyken kötü gün (aynı anda çökme)
daha sık → havuzdan korelasyona göre çeşitlendiren bir seçim kuralı kötü günü kesebilir.

ÖN KAYIT (koşudan önce yazıldı):
  Kitap: T4 (standart model, MERD_SIRA=1), 2.000 $ D8, hiza 0, uzun zemin; POZ_CIKTI ile her bar dilimler arası ortalama
  pozisyon. Her gün sonu: long ağırlığı > 0 olan coinlerin son 30 g (180 bar) 4 sa getiri korelasyonlarının ağırlıklı
  ortalaması RHO (yalnız o güne kadarki veri). RHO yüzdeliği GENİŞLEYEN pencereyle (≥ 180 g geçmiş).
  Motor kuralı yazmaya geçme şartı (IS ≤2024 ve OOS 2025+ AYRI AYRI):
    (a) RHO üst beşte birinde ertesi gün ≤ −%3 olasılığı genelin ≥ 1,5 katı, ve
    (b) RHO üst beşte birinde ileri 5 g getirisi genelin ortalamasından YÜKSEK DEĞİL (kötü gün bir kâr primi değil).
  Tutmazsa eksen KAPANIR.
"""
import os, pickle, subprocess, sys
import numpy as np
import pandas as pd
import arastirma_tabanlar as TB
import arastirma_m346_prim as M

D = "/tmp/m589"; os.makedirs(D, exist_ok=True)
T4 = {**TB.T1, "MERD_SIRA": "1", "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80",
      "HACIM_MIN_EVREN": "30"}
E, P = f"{D}/T4.pkl", f"{D}/T4_poz.pkl"
if not os.path.exists(P):
    env = dict(os.environ, **dict(M.TABAN, **T4), FAZ_KAY="0", SEMBOL_HARIC=",".join(M.D8), E_CIKTI=E, POZ_CIKTI=P)
    with open(f"{D}/T4.txt", "w") as f:
        subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
Eq = pickle.load(open(E, "rb")); r = Eq.pct_change().dropna()
g = (1 + r).groupby(r.index.date).prod() - 1; g.index = pd.DatetimeIndex(g.index)
poz = pd.read_pickle(P)
z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = z["C"]
R = np.log(C).diff()

L = poz[poz.w > 0]
L = L.assign(gun=L.zaman.dt.normalize())
son = L[L.zaman == L.groupby("gun").zaman.transform("max")]          # günün son barındaki long'lar
rho = {}
for gun, grp in son.groupby("gun"):
    t = grp.zaman.iloc[0]; syms = list(grp.sembol); w = grp.w.values
    if len(syms) < 2:
        continue
    pen = R.loc[:t, syms].iloc[-180:]
    if pen.notna().sum().min() < 90:
        continue
    k = pen.corr().values; ww = np.outer(w, w); np.fill_diagonal(ww, 0)
    rho[gun] = np.nansum(k * ww) / ww.sum()
rho = pd.Series(rho).sort_index()


def yuzdelik(x):
    v = x.values; out = np.full(len(v), np.nan)
    for i in range(180, len(v)):
        out[i] = (v[:i] < v[i]).mean() * 100
    return pd.Series(out, index=x.index)


q = yuzdelik(rho).reindex(g.index)
ileri5 = (1 + g).rolling(5).apply(np.prod, raw=True).shift(-5) - 1
kotu = (g.shift(-1) <= -0.03).astype(float)
print(f"T4 {g.index[0].date()} → {g.index[-1].date()} · yıllık {((1+g).prod()**(365.25/len(g))-1)*100:+.1f} · "
      f"RHO ort {rho.mean():.3f} sd {rho.std():.3f} ({len(rho)} gün)")
print(f"{'dönem':6s} {'kova':>8s} {'gün':>5s} {'ileri5 %':>9s} {'−%3 olas.':>9s}")
gec = []
for dn, m in (("IS", g.index < "2025-01-01"), ("OOS", g.index >= "2025-01-01")):
    ok = m & q.notna()
    for kv, (lo, hi) in (("0-20", (0, 20)), ("20-80", (20, 80)), ("80-100", (80, 101))):
        s = ok & (q >= lo) & (q < hi)
        print(f"{dn:6s} {kv:>8s} {int(s.sum()):5d} {ileri5[s].mean()*100:+9.2f} {kotu[s].mean()*100:9.2f}")
    s = ok & (q >= 80)
    a = kotu[s].mean() >= 1.5 * kotu[ok].mean(); b = ileri5[s].mean() <= ileri5[ok].mean()
    print(f"{dn:6s} {'tümü':>8s} {int(ok.sum()):5d} {ileri5[ok].mean()*100:+9.2f} {kotu[ok].mean()*100:9.2f}   "
          f"şart a {'Y' if a else 'X'} · b {'Y' if b else 'X'}")
    gec.append(a and b)
print("\nHÜKÜM:", "MOTORA (seçim kuralı yazılır)" if all(gec) else "KAPANDI")
