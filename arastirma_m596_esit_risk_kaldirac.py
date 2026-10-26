#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 596 — AYNI RİSKTE EN ÇOK KÂR: T4 / T6 / T7K'yı T4'ün (1,0x) risk ölçülerine kaldıraçla eşitle.
Gerekçe (madde 257/391/567): kâr adayları eşit riskte hep kaldıraca denk çıktı; demek ki kârı büyütmenin ölçülmüş yolu
YÜKSEK SHARPE'LI kitabı aynı riske kaldıraçlamak. T7K'nın Sharpe'ı ve en kötü günü T4'ten iyi (madde 584/586) ama hiç
eşit riskte kaldıraçlanmadı.
Seri: canlı gibi giriş + 5 bp + MERD_SIRA=1, uzun zemin, iki hiza ort. (madde 587 kuru koşusu /tmp/m_ekim_kuru).
Kaldıraç günlük getiri × k (madde 515 yöntemi; komisyon/kayma da k ile ölçeklenmeli → ek maliyet satırı ayrıca).
Risk ölçüleri (T4 1,0x referans): tam dönem maks düşüş, en kötü gün, −%5 altı gün, 1 yıllık düşüş p1 (eşli blok bootstrap,
blok 20 g, 3.000 yol). Kitap başına: dört ölçünün HER BİRİNİ T4'ünkini aşmadan taşıyabildiği en yüksek k (en bağlayıcı ölçü).
"""
import numpy as np, pandas as pd
import arastirma_m346_prim as M
M.CIKTI = "/tmp/m_ekim_kuru"
rng = np.random.default_rng(596)


def seri(k, sev):
    return sum(M.gunluk(f"M357_EK_{k}_{sev}_{h}") for h in (0, 1)) / 2


def olc(d):
    eq = (1 + d).cumprod()
    return dict(yil=(eq.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(eq / eq.cummax() - 1).min() * 100,
                ek=d.min() * 100, g5=int((d < -0.05).sum()))


def p1(d, idx):
    v = d.values; out = []
    for yol in idx:
        x = v[yol]; eq = np.cumprod(1 + x); out.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
    return np.percentile(out, 1)


for sev in (2000, 3500):
    S = {k: seri(k, sev) for k in ("T1", "T4", "T6", "T7K")}
    n = len(S["T4"]); B, L = 20, 365
    idx = []
    for _ in range(3000):
        bas = rng.integers(0, n - B, size=L // B + 1); idx.append(np.concatenate([np.arange(b, b + B) for b in bas])[:L])
    ref = olc(S["T4"]); ref["p1"] = p1(S["T4"], idx)
    print(f"\n{sev} $ — referans T4 1,0x: yıllık {ref['yil']:+.1f} · dd {ref['dd']:.1f} · en kötü {ref['ek']:.2f} · −%5 {ref['g5']} · 1y p1 {ref['p1']:.1f}")
    print(f"{'kitap':5s} {'k':>5s} {'yıllık':>8s} {'dd':>6s} {'en kötü':>8s} {'−%5':>4s} {'1y p1':>6s}  bağlayıcı")
    for kt in ("T1", "T4", "T6", "T7K"):
        best = None
        for k in np.arange(0.80, 2.51, 0.05):
            d = S[kt] * k; o = olc(d)
            if o["dd"] < ref["dd"] - 1e-9 or o["ek"] < ref["ek"] - 1e-9:
                break
            o["p1"] = p1(d, idx)
            if o["p1"] < ref["p1"] - 1e-9:
                break
            best = (k, o)
        if best is None:
            print(f"{kt:5s}  <0,80"); continue
        k, o = best; d = S[kt] * (k + 0.05); o2 = olc(d); o2["p1"] = p1(d, idx)
        bag = [a for a, c in (("dd", o2["dd"] < ref["dd"]), ("en kötü gün", o2["ek"] < ref["ek"]),
                               ("1y p1", o2["p1"] < ref["p1"])) if c]
        print(f"{kt:5s} {k:5.2f} {o['yil']:+8.1f} {o['dd']:6.1f} {o['ek']:8.2f} {o['g5']:4d} {o['p1']:6.1f}  {', '.join(bag)}")
