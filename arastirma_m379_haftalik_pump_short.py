#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 379 — KULLANICININ GERÇEK SHORT'LARINDAN TÜRETİLEN KURAL: HAFTALIK
PUMP + TEPEDEN DÖNÜŞ.

Kullanıcının açık 6 short'u (Ekim 2026) 1 saatlik veriyle incelendi:
giriş, 7 günlük dibin +%12..+%735 ÜSTÜNDE ve çoğu 72 saatlik tepenin
−%2..−%34 ALTINDA. Projenin eski kuralları (madde 187/195/203) "son 24
saatte ±%X, sabit saatte gir" diyordu; HAFTALIK yükseliş + tepe teyidi hiç
sınanmadı. (Not: ekran görüntüsü AÇIK pozisyonlar — kapanmış zararlılar
görünmüyor; bu ölçüm hepsini sayar.)

OLAY (4 sa panel, 2022-2026, 850 sembol, TradFi hariç, hacim >= 20M$/gün,
yaş >= 14 gün): t barında
    C_t >= (1 + A) * min(L, son 7 gün)          (haftalık pump)
    C_t <= (1 - B) * max(H, son 72 saat)        (tepe teyidi; B=0 -> yok)
Aynı sembolde açık pozisyon varken yeni olay alınmaz.
İŞLEM: t+1 açılışında short, H gün tut; isteğe bağlı STOP: fiyat girişin
+%S üstüne çıkarsa (barın HIGH'ı) o seviyeden kapat (kullanıcının −%25'i).
MALİYET: taker %0,05 giriş + çıkış; funding gerçek (short alır/öder).
PORTFÖY: her işlem sermayenin 1/N'i (N=10), aynı anda en fazla 10.
PLASEBO: aynı sembol, aynı sayıda işlem, rastgele (uygun) zamanlarda.

ÖN KAYITLI ELEK (koşudan ÖNCE yazıldı; madde 353 + 375):
  portföy net Sharpe 2022-24 VE 2025-26 >= 1,0; tam >= 1,5; plaseboyu
  >= 0,5 geçer; carry ile korelasyon <= 0,30. Elekten geçen bir kol
  sonra harman turuna (madde 289 barı) %95 protokolüyle girer.
Izgara: A {0,5 · 1,0 · 2,0} x B {0 · 0,10 · 0,20} x H {1 · 3 · 7 gün}
x stop {yok · %25}. 54 kol — çoklu bakış büyük; elek gevşek ama karar
harmanda %95'le verilir.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
KOM = 0.0005
NMAX = 10
RNG = np.random.default_rng(379)


def yukle():
    z = pickle.load(open("/tmp/zemin.pkl", "rb"))
    P = pickle.load(open("/tmp/panel.pkl", "rb"))
    hlo = pickle.load(open("/tmp/hlo.pkl", "rb"))
    C = z["C"]
    O, H, L = (hlo[k].reindex_like(C) for k in ("O", "H", "L"))
    F = z["ODE"].reindex_like(C).fillna(0.0)
    from tradfi_liste import TRADFI
    uy = (P["HAC"].reindex_like(C) >= 2e7) & (P["YAS"].reindex_like(C) >= 14 * 6)
    uy = uy & ~uy.columns.isin(list(TRADFI))
    return C, O, H, L, F, uy


def olaylar(C, H, L, uy, A, B):
    lo7 = L.rolling(42, min_periods=30).min()
    hi72 = H.rolling(18, min_periods=12).max()
    k = (C >= (1 + A) * lo7)
    if B > 0:
        k = k & (C <= (1 - B) * hi72)
    return (k & uy).values


def islemler(kos, C, O, H, F, Hgun, S, plasebo=False, uy=None):
    cv, ov, hv, fv = C.values, O.values, H.values, F.values
    T, N = cv.shape
    hb = int(Hgun * 6)
    out = []
    for j in range(N):
        ix = np.flatnonzero(kos[:, j])
        if plasebo:
            aday = np.flatnonzero(uy.values[:, j]) if uy is not None else np.arange(T)
            aday = aday[aday < T - hb - 2]
            if len(ix) == 0 or len(aday) == 0:
                continue
            ix = np.sort(RNG.choice(aday, size=min(len(ix), len(aday)), replace=False))
        serbest = -1
        for i in ix:
            if i <= serbest or i + 1 >= T:
                continue
            g = ov[i + 1, j]
            if not np.isfinite(g) or g <= 0:
                continue
            son = min(i + 1 + hb, T - 1)
            cik_i, cik_f = son, cv[son, j]
            if S > 0:
                dur = np.flatnonzero(hv[i + 1:son + 1, j] >= g * (1 + S))
                if len(dur):
                    cik_i = i + 1 + dur[0]; cik_f = g * (1 + S)
            if not np.isfinite(cik_f):
                continue
            fon = np.nansum(fv[i + 1:cik_i + 1, j])          # short alır
            # DÜZELTME (madde 379, ilk koşu GEÇERSİZ): short getirisi 1 - çıkış/giriş.
            # İlk sürüm g/çıkış - 1 kullanıyordu: fiyat %90 düşünce +%900 gösterir
            # (gerçek azami +%100). Sonuçlar bu yüzden absürt şişmişti.
            r = (1 - cik_f / g) + fon - 2 * KOM
            out.append((i + 1, cik_i, j, r))
            serbest = cik_i
    return out


def portfoy(isl, idx):
    """Her işlem 1/NMAX; işlemin getirisi kapanış barına yazılır, aynı anda
    NMAX'tan fazlası varsa fazlası atılır (giriş sırasına göre)."""
    isl = sorted(isl)
    acik, r = [], np.zeros(len(idx))
    for a, b, j, x in isl:
        acik = [c for c in acik if c > a]
        if len(acik) >= NMAX:
            continue
        acik.append(b)
        r[b] += x / NMAX
    s = pd.Series(r, index=idx)
    g = (1 + s).groupby(s.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index)
    return g


def sh(g):
    g = np.asarray(g, float)
    return float(g.mean() / g.std() * np.sqrt(365.25)) if g.std() > 0 else np.nan


def main():
    C, O, H, L, F, uy = yukle()
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    print(f"{'kol':<22} {'islem':>6} {'ort%':>6} {'med%':>6} {'kaz%':>5} {'p1%':>7} "
          f"{'yillik':>7} {'Sh':>5} {'Sh22':>5} {'Sh25':>5} {'dusus':>6} {'rho':>5} | {'PLA':>5} | elek")
    gecen = []
    for A in (0.5, 1.0, 2.0):
        for B in (0.0, 0.10, 0.20):
            kos = olaylar(C, H, L, uy, A, B)
            for Hg in (1, 3, 7):
                for S in (0.0, 0.25):
                    isl = islemler(kos, C, O, H, F, Hg, S)
                    if len(isl) < 30:
                        continue
                    rr = np.array([x[3] for x in isl])
                    g = portfoy(isl, C.index)
                    pl = portfoy(islemler(kos, C, O, H, F, Hg, S, plasebo=True, uy=uy), C.index)
                    e = (1 + g).cumprod(); yil = (e.iloc[-1] ** (365.25 / len(g)) - 1) * 100
                    dd = ((e / e.cummax()) - 1).min() * 100
                    s22, s25 = sh(g[g.index < "2025-01-01"]), sh(g[g.index >= "2025-01-01"])
                    ix = g.index.intersection(carry.index)
                    rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
                    el = [s22 >= 1.0 and s25 >= 1.0, sh(g) >= 1.5, sh(g) - sh(pl) >= 0.5, rho <= 0.30]
                    ad = f"A{A} B{B} H{Hg} S{int(S*100)}"
                    print(f"{ad:<22} {len(rr):>6} {rr.mean()*100:>+6.2f} {np.median(rr)*100:>+6.2f} "
                          f"{(rr>0).mean()*100:>5.1f} {np.percentile(rr,1)*100:>+7.1f} {yil:>+7.1f} "
                          f"{sh(g):>5.2f} {s22:>5.2f} {s25:>5.2f} {dd:>6.1f} {rho:>+5.2f} | "
                          f"{sh(pl):>5.2f} | {''.join('Y' if x else 'X' for x in el)}", flush=True)
                    if all(el):
                        gecen.append(ad)
    print("\nELEKTEN GECEN:", gecen or "YOK")


if __name__ == "__main__":
    main()
