#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 859 — iki kol: A hibrit (carry short + momentum long), B ayrı momentum motoru (80 / 20 hesap). Ön kayıt KAR_HARITASI 859. KARAR VERMEZ.
Önce veri hattı + `M783_OUT=/tmp/m783k GK_BAS=2020-01-01 python3 arastirma_m783_kasim_hafta.py kos`.
  python3 arastirma_m859_iki_kol.py kos      # T4 eşit risk referansı (iki hiza), /tmp/m859
  python3 arastirma_m859_iki_kol.py analiz"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M
R = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("M859_OUT", "/tmp/m859"); KAS = os.environ.get("M783_OUT", "/tmp/m783k")
DONEM = slice("2026-10-01", "2026-11-25")
PARITE = {"2026-11-20": -4.30, "2026-11-21": -0.53, "2026-11-22": -2.47, "2026-11-23": -0.04, "2026-11-24": 0.98}


def kos():
    import izleme_ekim_oos as I
    os.makedirs(OUT, exist_ok=True)
    env0 = {**M.TABAN, **I._T4, "SEMBOL_HARIC": ",".join(M.D8)}
    for h in (0, 1):
        e = f"{OUT}/M357_EK_T4_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **env0, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
        env.pop("GUNLUK_KATKI", None)
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def olc(d):
    e = (1 + d).cumprod()
    return dict(yil=(e.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(e / e.cummax() - 1).min() * 100, ek=d.min() * 100)


def sh(d): return d.mean() / d.std() * np.sqrt(365.25)


def esit_kur(T4):
    """madde 685 Z.esit ile birebir (dd / en kötü gün / blok-bootstrap p1, tohum 596), T4 referansı bu koşunun verisiyle."""
    rng = np.random.default_rng(596); n = len(T4)
    idx = [np.concatenate([np.arange(b, b + 20) for b in rng.integers(0, n - 20, size=19)])[:365] for _ in range(3000)]
    def p1(d):
        v = d.values; return np.percentile([((np.cumprod(1 + v[i])) / np.maximum.accumulate(np.cumprod(1 + v[i])) - 1).min() * 100 for i in idx], 1)
    ref = olc(T4); ref["p1"] = p1(T4)
    def esit(d):
        best = None
        for k in np.arange(0.80, 2.51, 0.05):
            x = d * k; o = olc(x)
            if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
            if p1(x) < ref["p1"]: break
            best = (k, o["yil"])
        return best or (np.nan, np.nan)
    return ref, esit


def momentum(k=7, tut=3, n_=5):
    """821'in tasarımla seçilmiş varyantı (dondurulmuş); (iki bacak, yalnız long bacak)."""
    import arastirma_m389_ml_tahmin as A
    C, Fd, uy, X = A.panel(); r1 = (C / C.shift(1) - 1).fillna(0); Fz = Fd.reindex_like(C).fillna(0)
    g = (C / C.shift(k) - 1).where(uy); rk = g.rank(axis=1); n = g.notna().sum(axis=1)
    lo = rk.le(n_, axis=0) & g.notna(); hi = rk.ge(n - n_ + 1, axis=0) & g.notna()
    def bacak(w):
        W = sum(w.shift(j) for j in range(1, tut + 1)) / tut
        return (W * r1).sum(axis=1) - (W * Fz).sum(axis=1) - (W - W.shift(1)).abs().sum(axis=1) * 0.0010
    wl = hi.astype(float) / n_ * 0.5; ws = -lo.astype(float) / n_ * 0.5
    iki = bacak(wl + ws); uzun = bacak(wl)
    iki.index = iki.index.floor("D"); uzun.index = uzun.index.floor("D")
    return iki, uzun


def bilesik(x): return ((1 + x * 1.15).prod() - 1) * 100


def analiz():
    M.CIKTI = KAS; P = sum(M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)) / 2
    P.index = pd.to_datetime(P.index).floor("D")
    print(f"P serisi {P.index.min().date()} → {P.index.max().date()} ({len(P)} gün)")
    fark = max(abs(P.get(pd.Timestamp(g), np.nan) * 115 - v) for g, v in PARITE.items())
    kas = bilesik(P["2026-11-01":"2026-11-24"])
    print(f"PARİTE (783 uzatma 8): Kasım günlük en büyük fark {fark:.3f} puan · Kasım 1-24 {kas:+.2f} (beklenen −9,50)")
    if not (fark <= 0.05 and abs(kas + 9.50) <= 0.05):
        if os.environ.get("M859_SAPMA") != "1":
            print("PARİTE TUTMADI — ön kayıt gereği analiz YAPILMAZ"); return 1
        print("PARİTE TUTMADI — SAPMA kaydı (KAR 859) ile devam: ana okuma Eki-15 Kas (parite tam), Eki-24 Kas ek")
    G = pd.concat([pd.read_pickle(f"{KAS}/gk_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun).dt.floor("D")
    L = G[G.ort_poz > 0].groupby("gun").apply(lambda x: (x.fiyat + x.funding).sum() / 2).reindex(P.index).fillna(0.0)
    S_ = G[G.ort_poz < 0].groupby("gun").apply(lambda x: (x.fiyat + x.funding).sum() / 2).reindex(P.index).fillna(0.0)
    print(f"GK defteri {G.gun.min().date()} → {G.gun.max().date()} · long + short − P (komisyon / rezerv farkı) ort. {((L + S_) - P).mean() * 1e4:+.2f} bp/gün")
    Mi, Ml = momentum(); Mi = Mi.reindex(P.index).fillna(0.0); Ml = Ml.reindex(P.index).fillna(0.0)
    M.CIKTI = OUT; T4 = sum(M.gunluk(f"M357_EK_T4_2000_{h}") for h in (0, 1)) / 2; T4.index = pd.to_datetime(T4.index).floor("D")
    ref, esit = esit_kur(T4.reindex(P.index).dropna())
    print(f"T4 referansı: dd {ref['dd']:.1f} · en kötü gün {ref['ek']:.2f} · p1 {ref['p1']:.1f}")
    kollar = {"taban P3T2": P, "A hibrit (short carry + long mom)": P - L + Ml, "B 80/20 iki hesap": 0.8 * P + 0.2 * Mi}
    print(f"\nmomentum tek başına (iki bacak) 2021+ Sh {sh(Mi['2021':]):.2f} · 2025+ {sh(Mi['2025':]):.2f} · Eki-25 Kas {bilesik(Mi[DONEM]) / 1.15:+.1f} % (×1) · "
          f"17-25 Kas {bilesik(Mi['2026-11-17':'2026-11-25']) / 1.15:+.1f} %")
    print(f"long bacak karşılaştırma (puan, ×1,15 toplamsal): carry long Eki-25 Kas {L[DONEM].sum() * 115:+.1f} · momentum long {Ml[DONEM].sum() * 115:+.1f} | "
          f"2025 {L['2025'].sum() * 115:+.0f} / {Ml['2025'].sum() * 115:+.0f} · 2026 {L['2026'].sum() * 115:+.0f} / {Ml['2026'].sum() * 115:+.0f}")
    taban = None; satir = []
    for ad, s in kollar.items():
        o = olc(s); kk, er = esit(s); e = (1 + s * 1.15).cumprod(); dd = (e / e.cummax() - 1).min() * 100
        d = dict(ad=ad, yil=o["yil"], sh=sh(s), dd=dd, ek=o["ek"], sh1=sh(s[:"2024-12-31"]), sh2=sh(s["2025-01-01":]), er=er, kk=kk,
                 donem=bilesik(s[DONEM]), d15=bilesik(s["2026-10-01":"2026-11-15"]), eki=bilesik(s["2026-10"]), kasim=bilesik(s["2026-11-01":"2026-11-25"]), son=bilesik(s["2026-11-17":"2026-11-25"]))
        yl = s.groupby(s.index.year).apply(bilesik)
        print(f"\n{ad}: yıllık {d['yil']:.1f} · Sh {d['sh']:.2f} · dd(×1,15) {dd:.1f} · en kötü gün {d['ek']:.2f} · Sh ≤2024 {d['sh1']:.2f} / 2025+ {d['sh2']:.2f} · "
              f"eşit risk {er:.1f} (doz {kk:.2f})\n   yıllar ×1,15: " + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()) +
              f"\n   Eki {d['eki']:+.1f} · Eki-15 Kas {d['d15']:+.1f} · Kas 1-25 {d['kasim']:+.1f} · Eki-25 Kas {d['donem']:+.1f} · 17-25 Kas {d['son']:+.1f}")
        if taban is None: taban = d; continue
        k1 = (d["er"] >= taban["er"] - 8) and (d["sh1"] >= taban["sh1"] - 0.1) and (d["sh2"] >= taban["sh2"] - 0.1) and (d["dd"] >= taban["dd"])
        k2 = d["donem"] >= taban["donem"] + 5; k2b = d["d15"] >= taban["d15"] + 5
        satir.append(f"{ad}: ölçüt 1 {'✓' if k1 else '✗'} (eşit risk {d['er'] - taban['er']:+.1f} · Sh ≤2024 {d['sh1'] - taban['sh1']:+.2f} · 2025+ {d['sh2'] - taban['sh2']:+.2f} · "
                     f"dd {d['dd'] - taban['dd']:+.1f}) · ölçüt 2 {'✓' if k2 else '✗'} (dönem farkı {d['donem'] - taban['donem']:+.1f} puan; Eki-15 Kas {d['d15'] - taban['d15']:+.1f} {'✓' if k2b else '✗'}) → "
                     + ("AYRI DEMO ADAYI" if (k1 and k2 and k2b) else "RED"))
    print("\nSONUÇ"); [print("  " + x) for x in satir]
    return 0


if __name__ == "__main__":
    raise SystemExit({"kos": kos, "analiz": analiz}[sys.argv[1]]() or 0)
