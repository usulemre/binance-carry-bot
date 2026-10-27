#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 620 — FARKLI YAKLAŞIM: PROFİL SEÇİCİ (kitaplar arası rejim/momentum). Bugüne kadar hep TEK kitap seçildi; T4 / T6 / T7K'nın
göreli başarısı döneme göre değişiyor (madde 601: T6 2025-26'da uçuyor, T7K kötü günde iyi). Her ay başında son N günde (nedensel,
1 gün gecikme) en yüksek Sharpe'lı profile geçmek, sabit T7K 1,15x'ten aynı riskte daha çok kazandırır mı? Haritada yok.
ÖN KAYIT (koşudan önce yazıldı): seriler hazır (gerçekçi model; 2.000 $ = /tmp/m_ekim_kuru EK_*, TAM = /tmp/m601), yeni motor koşusu yok.
  Aday havuzu {T4, T6, T7K}; ölçüt geçmiş N g Sharpe, N ∈ {90, 180}; ayda bir karar; geçişte kitabın tamamı döner → 2 × 5 bp = 0,10 %
  (yalnız profil değişince). İlk N g T7K. Ölçüm madde 596 eşit-risk (o seviyenin T4 1,0x kısıtı).
  ADAY: eşit-risk yıllığı, o seviyedeki en iyi SABİT profilin eşit-risk yıllığından (2.000 $: T7K +303,2; TAM: T6 +354,9) ≥ +8,
  N=90 ve N=180'de birlikte (tek pencere tutarsa şans).
"""
import numpy as np, pandas as pd, pickle
import arastirma_m346_prim as M
import arastirma_m609_kapanis_stop as A


def gun(p):
    E = pickle.load(open(p, "rb")); r = E.pct_change().dropna(); g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index); return g


def seriler(sev):
    if sev == "TAM":
        return {k: sum(gun(f"/tmp/m601/{k}_{h}.pkl") for h in (0, 1)) / 2 for k in ("T4", "T6", "T7K")}
    M.CIKTI = "/tmp/m_ekim_kuru"
    return {k: sum(M.gunluk(f"M357_EK_{k}_2000_{h}") for h in (0, 1)) / 2 for k in ("T4", "T6", "T7K")}


def secici(S, N):
    D = pd.DataFrame(S).dropna(); out = pd.Series(0.0, index=D.index); secim = []
    cur = "T7K"; aylar = D.index.to_period("M")
    for p in sorted(set(aylar)):
        idx = D.index[aylar == p]; t0 = idx[0]
        gec = D[D.index < t0].iloc[-N:]
        if len(gec) >= N:
            sh = gec.mean() / gec.std(); yeni = sh.idxmax()
        else:
            yeni = "T7K"
        r = D.loc[idx, yeni].copy()
        if yeni != cur: r.iloc[0] -= 0.001
        cur = yeni; out[idx] = r.values; secim.append(yeni)
    return out, pd.Series(secim).value_counts().to_dict()


def esit_risk(d, ref, idx):
    best = None
    for k in np.arange(0.80, 2.51, 0.05):
        dk = d * k; o = A._olc(dk)
        if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
        o["p1"] = A._p1(dk, idx)
        if o["p1"] < ref["p1"]: break
        best = (k, o)
    return best


for sev, enbest in (("2000", "T7K"), ("TAM", "T6")):
    S = seriler(sev)
    rng = np.random.default_rng(596); n = len(S["T4"]); idx = []
    for _ in range(3000):
        b = rng.integers(0, n - 20, size=365 // 20 + 1); idx.append(np.concatenate([np.arange(x, x + 20) for x in b])[:365])
    ref = A._olc(S["T4"]); ref["p1"] = A._p1(S["T4"], idx)
    k0, o0 = esit_risk(S[enbest], ref, idx)
    print(f"\n{sev}: en iyi sabit {enbest} k {k0:.2f} → {o0['yil']:+.1f} (dd {o0['dd']:.1f}, en kötü {o0['ek']:.2f}, −%5 {o0['g5']})")
    gec = []
    for N in (90, 180):
        d, say = secici(S, N); ham = A._olc(d); k, o = esit_risk(d, ref, idx)
        print(f"  seçici N={N}: ham {ham['yil']:+.1f} dd {ham['dd']:.1f} | k {k:.2f} → {o['yil']:+.1f} (fark {o['yil']-o0['yil']:+.1f}) "
              f"−%5 {o['g5']} | ay sayısı {say}")
        gec.append(o["yil"] - o0["yil"] >= 8)
    print("  HÜKÜM:", "ADAY" if all(gec) else "RED")
