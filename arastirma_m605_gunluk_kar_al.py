#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 605 — KULLANICI HEDEFİ: GÜNLÜK KÂR AL. Gün içinde kitabın getirisi +X%'e ulaşınca TÜM pozisyonlar kapanır, gün bitene
kadar düz kalınır, ertesi gün (00 UTC) aynı kitap yeniden açılır. Hiç ölçülmedi (madde 264 haftalık realizasyonu, 280 düşüşte kesmeyi
ölçtü; kitap düzeyinde GÜNLÜK KÂR TAVANI yok). Madde 243: günlük getiri hafif ortalamaya dönüyor (lag1 −0,05) → iyi günün kalanını
almamak işe yarayabilir mi?
YÖNTEM: motorun 4 sa'lik özsermaye serisi (canlı gibi giriş + 5 bp + MERD_SIRA=1, uzun zemin, 2.000 $, iki hiza ayrı ayrı).
Gün (UTC) içinde birikimli getiri ≥ X olduğu ilk 4 sa barın kapanışında çıkılır (gerçekte limit/tetik bar içinde daha erken
dolabilir → bu ölçüm kâr tarafında İHTİYATLI); kalan barlar 0. Maliyet: çıkış + ertesi gün yeniden giriş = 2 × brüt (1,0) × 5 bp
= %0,10, tetiklenen her gün. Varsayım: yeniden kurulan kitap kesintisiz tutulan kitapla aynı (dilim/TP durumu korunur) — iyimser
yön; canlıda yeniden girişte giriş fiyatları ve kademe referansları sıfırlanır.
ÖN KAYIT: X ∈ {%0,5, %1, %1,5, %2, %3}. ADAY: iki hizada da ve hem ≤2024 hem 2025+ döneminde yıllık VE Sharpe tabandan yüksek.
"""
import pickle, sys
import numpy as np, pandas as pd

KITAP = sys.argv[1] if len(sys.argv) > 1 else "T7K"
MAL = 0.0010
ESIK = (0.005, 0.01, 0.015, 0.02, 0.03)


def bar_getiri(kitap, h):
    E = pickle.load(open(f"/tmp/m_ekim_kuru/M357_EK_{kitap}_2000_{h}.pkl", "rb"))
    return E.pct_change().dropna()


def uygula(r, x):
    out = np.array(r.values, dtype=float, copy=True); gun = r.index.normalize().values; idx = 0; n = len(out); tet = 0
    while idx < n:
        g = gun[idx]; j = idx; kum = 1.0; vurdu = False
        while j < n and gun[j] == g:
            if vurdu:
                out[j] = 0.0
            else:
                kum *= 1 + out[j]
                if kum - 1 >= x:
                    vurdu = True; tet += 1; out[j] = (1 + out[j]) * (1 - MAL) - 1
            j += 1
        idx = j
    return pd.Series(out, index=r.index), tet


def olc(r):
    d = (1 + r).groupby(r.index.date).prod() - 1; d.index = pd.DatetimeIndex(d.index)
    Y = lambda z: ((1 + z).prod() ** (365.25 / len(z)) - 1) * 100
    S = lambda z: z.mean() / z.std() * np.sqrt(365.25)
    eq = (1 + d).cumprod()
    return dict(yil=Y(d), sh=S(d), dd=(eq / eq.cummax() - 1).min() * 100, art=(d > 0).mean() * 100, med=d.median() * 100,
                IS=(Y(d[d.index < "2025"]), S(d[d.index < "2025"])), OOS=(Y(d[d.index >= "2025"]), S(d[d.index >= "2025"])))


for h in (0, 1):
    r = bar_getiri(KITAP, h); b = olc(r)
    print(f"\n{KITAP} hiza {h} — taban: yıllık {b['yil']:+.1f} Sh {b['sh']:.2f} dd {b['dd']:.1f} · artı gün %{b['art']:.0f} · "
          f"medyan gün {b['med']:+.2f}% · ≤2024 {b['IS'][0]:+.0f}/{b['IS'][1]:.2f} · 2025+ {b['OOS'][0]:+.0f}/{b['OOS'][1]:.2f}")
    for x in ESIK:
        rr, t = uygula(r, x); o = olc(rr)
        ok = o["IS"][0] > b["IS"][0] and o["IS"][1] > b["IS"][1] and o["OOS"][0] > b["OOS"][0] and o["OOS"][1] > b["OOS"][1]
        print(f"  günlük +%{x*100:.1f}: tetik {t/len(set(r.index.date))*100:4.1f}% gün · yıllık {o['yil']:+7.1f} ({o['yil']-b['yil']:+6.1f}) "
              f"Sh {o['sh']:.2f} dd {o['dd']:.1f} · ≤2024 {o['IS'][0]-b['IS'][0]:+.0f} · 2025+ {o['OOS'][0]-b['OOS'][0]:+.0f} {'ADAY' if ok else ''}")
