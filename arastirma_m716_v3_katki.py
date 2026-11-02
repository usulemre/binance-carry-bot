#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 716 — V3 (madde 677) ile taban P3T2 karşılaştırması: Ekim OOS ve 676 penceresi (örnek içi, karar için değil).
Kaynak: /tmp/m677 (V3, Ekim dahil zemin, iki hiza) ve /tmp/m_ekim (EK_T7KKS). Yalnız ölçüm. Kullanım: python3 arastirma_m716_v3_katki.py"""
import arastirma_m346_prim as M
M.CIKTI = "/tmp/m677"; v = sum(M.gunluk(f"M357_EK_V3_2000_{h}") for h in (0, 1)) / 2
M.CIKTI = "/tmp/m_ekim"; b = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
v, b = v.align(b, join="inner")
f = lambda s: ((1 + s).prod() - 1) * 100
for ad, a, z in [("2025-06..2026-09 (676 penceresi, örnek içi)", "2025-06-01", "2026-09-30"), ("2026-10 (OOS)", "2026-10-01", "2026-10-31")]:
    x, y = v[a:z], b[a:z]; d = x - y
    print(ad, f"gün {len(x)} · V3 {f(x):+.2f} · taban {f(y):+.2f} · fark günlük ort {d.mean()*1e4:+.1f} bp, sd {d.std()*1e4:.1f} bp · V3 daha iyi gün "
          f"{(d > 0).mean()*100:.0f}% · kor(V3,taban) {x.corr(y):.3f} · kor(fark,taban) {d.corr(y):+.2f} · en kötü gün {x.min()*100:.2f} / {y.min()*100:.2f}")
    if len(x) > 40:
        m = d.resample("ME").apply(lambda s: s.sum() * 100)
        print("  aylık fark (basit, puan):", " ".join(f"{i:%y-%m}:{k:+.1f}" for i, k in m.items()))
