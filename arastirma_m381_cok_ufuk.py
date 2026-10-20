#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 381 — ÇOK UFUKLU PERFORMANS: KULLANICININ ÖNERİSİ VE KOMBİNASYONLARI.

Kullanıcı: "1 günde, 3 günde, 1 haftada, 1 ayda, 3 ayda pozitif olan ve
iyi artmış coini shortlamak gibi kombinasyonları dene."

ÇOKLU BAKIŞA KARŞI YÖNTEM — ÖRNEK DIŞI DOĞRULAMA (koşudan ÖNCE yazıldı):
  * SEÇİM yalnız 2022-01 .. 2024-12 (IS) Sharpe'ıyla yapılır.
  * Seçilen TEK kol 2025-01 .. 2026-08 (OOS) üzerinde raporlanır; OOS'a
    seçimde hiç bakılmaz.
  * KABUL (bir sonraki tura — harman, %95 protokolü — geçiş): OOS net
    Sharpe >= 1,0 VE OOS'ta aynı yapının plasebosunu (sinyal kesitsel
    karıştırılmış) >= 0,5 geçer VE carry ile rho <= 0,30.
  * Tüm kolların OOS'u da tabloya yazılır ama karar yalnız IS'te
    seçilen kol için verilir.

PANEL: 4 sa panelden 00 UTC kapanışları (günlük). Evren: TradFi hariç,
hacim >= 20M$/gün, yaş >= 90 gün (en uzun ufuk için).
UFUKLAR (gün): 1, 3, 7, 30, 90; getiri r_h = C_t / C_{t-h} - 1.
SİNYALLER (her biri kesitsel yüzdelik sıra, yüksek = çok yükselmiş):
    R1 R3 R7 R30 R90         tek ufuk
    KISA = ort(R1,R3,R7)     ORTA... UZUN = ort(R7,R30,R90)
    HEPSI = ort(beş ufuk)
    HEPSI_POZ = HEPSI, ama yalnız beş ufkun HEPSİNDE r_h > 0 olanlar
                (kullanıcının "her ufukta pozitif" şartı)
YÖN: TERS (yükseleni short, düşeni long — kullanıcının yaklaşımı) ve
     MOM (yükseleni long). Piyasa nötr: üst %10 / alt %10, eşit ağırlık,
     brüt 1. HEPSI_POZ'da long bacak = beş ufkun hepsinde NEGATİF olanlar.
TUTMA: 1 gün (her gün yeniden kur) ve 7 gün (7 günde bir).
MALİYET: devir x taker %0,05; funding gerçek (günlük toplam).
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
KOM = 0.0005
UFUK = (1, 3, 7, 30, 90)
RNG = np.random.default_rng(381)


def yukle():
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); P = pickle.load(open("/tmp/panel.pkl", "rb"))
    C4 = z["C"]; F4 = z["ODE"].reindex_like(C4).fillna(0.0)
    from tradfi_liste import TRADFI
    sec = C4.index.hour == 0
    C = C4[sec]
    # günlük funding: t satırı (t-1 00 UTC, t 00 UTC] aralığında ödenenleri taşır —
    # Wl (t-1'de kurulan pozisyon) t'ye kadar bu ödemeleri alır/öder. Bir önceki
    # takvim gününün toplamı = (t-24 sa, t) aralığı. (İlk yazımda bir gün ileri kaymıştı.)
    Fd = F4.groupby(F4.index.floor("D")).sum().reindex(C.index.floor("D") - pd.Timedelta(days=1)).fillna(0.0)
    Fd.index = C.index
    HAC = P["HAC"].reindex_like(C4)[sec]; YAS = P["YAS"].reindex_like(C4)[sec]
    uy = (HAC >= 2e7) & (YAS >= 90 * 6) & C.notna()
    uy = uy & ~uy.columns.isin(list(TRADFI))
    return C, Fd, uy


def sinyaller(C, uy):
    R = {h: (C / C.shift(h) - 1).where(uy) for h in UFUK}
    rk = {h: R[h].rank(axis=1, pct=True) for h in UFUK}
    ort = lambda hs: sum(rk[h] for h in hs) / len(hs)
    S = {f"R{h}": rk[h] for h in UFUK}
    S["KISA"] = ort((1, 3, 7)); S["UZUN"] = ort((7, 30, 90)); S["HEPSI"] = ort(UFUK)
    poz = sum((R[h] > 0).astype(int) for h in UFUK) == len(UFUK)
    neg = sum((R[h] < 0).astype(int) for h in UFUK) == len(UFUK)
    S["HEPSI_POZ"] = (S["HEPSI"], poz, neg)
    return S


def agirlik(sig, uy, yon, pay=0.10, plasebo=False):
    if isinstance(sig, tuple):
        s, poz, neg = sig
        ust = s.where(poz).rank(axis=1, ascending=False)        # pozitiflerin en güçlüleri
        alt = s.where(neg).rank(axis=1, ascending=True)
        n = uy.sum(axis=1); k = (n * pay).clip(lower=1).round()
        U = ust.le(k, axis=0) & ust.notna(); A = alt.le(k, axis=0) & alt.notna()
    else:
        s = sig
        if plasebo:
            v = s.values.copy()
            for i in range(v.shape[0]):
                m = np.isfinite(v[i]); v[i, m] = RNG.permutation(v[i, m])
            s = pd.DataFrame(v, index=s.index, columns=s.columns)
        U = s >= 1 - pay; A = s <= pay
    # TERS: üst (yükselen) short, alt long ; MOM: tersi
    W = A.astype(float) - U.astype(float)
    if yon == "MOM":
        W = -W
    lo = W.clip(lower=0); sh = (-W).clip(lower=0)
    lo = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0) * 0.5
    sh = sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0) * 0.5
    W = (lo - sh).fillna(0.0)
    W.loc[(lo.sum(axis=1) == 0) | (sh.sum(axis=1) == 0)] = 0.0   # iki bacak da yoksa nakit
    return W


def getiri(W, C, Fd, H):
    if H > 1:
        W = W.iloc[::H].reindex(W.index).ffill().fillna(0.0)
    Wl = W.shift(1).fillna(0.0)
    R1 = (C / C.shift(1) - 1).fillna(0.0).clip(-0.95, 5)
    brut = (Wl * R1).sum(axis=1)
    fon = -(Wl * Fd).sum(axis=1)
    mal = Wl.diff().abs().sum(axis=1).fillna(0.0) * KOM
    return brut + fon - mal


def sh(g):
    g = np.asarray(g, float)
    return float(g.mean() / g.std() * np.sqrt(365.25)) if g.std() > 0 else np.nan


def main():
    C, Fd, uy = yukle()
    S = sinyaller(C, uy)
    import arastirma_m346_prim as M
    carry = M.gunluk("T350_HAVUZ4_2000_0")
    IS = C.index < "2025-01-01"
    satir = []
    for ad, sig in S.items():
        for yon in ("TERS", "MOM"):
            for H in (1, 7):
                g = getiri(agirlik(sig, uy, yon), C, Fd, H)
                g = g[g.index >= "2022-04-01"]                 # 90 gün ısınma
                satir.append((f"{ad} {yon} H{H}", sh(g[g.index < '2025-01-01']),
                              sh(g[g.index >= '2025-01-01']), g))
    satir.sort(key=lambda x: -(x[1] if np.isfinite(x[1]) else -9))
    print(f"{'kol':<22} {'IS Sh':>6} {'OOS Sh':>7} {'yillik':>7} {'dusus':>7}")
    for ad, a, b, g in satir:
        e = (1 + g).cumprod(); yil = (e.iloc[-1] ** (365.25 / len(g)) - 1) * 100
        dd = ((e / e.cummax()) - 1).min() * 100
        print(f"{ad:<22} {a:>6.2f} {b:>7.2f} {yil:>+7.1f} {dd:>7.1f}")
    ad, a, b, g = satir[0]
    print(f"\nIS'TE SECILEN: {ad} (IS Sh {a:.2f}) -> OOS Sh {b:.2f}")
    sig_ad, yon, Hs = ad.split(); H = int(Hs[1:])
    if not isinstance(S[sig_ad], tuple):
        gp = getiri(agirlik(S[sig_ad], uy, yon, plasebo=True), C, Fd, H)
        gp = gp[gp.index >= "2025-01-01"]
        pla = sh(gp)
    else:
        pla = float("nan")
    oos = g[g.index >= "2025-01-01"]
    ix = g.index.intersection(carry.index)
    rho = float(np.corrcoef(g.loc[ix], carry.loc[ix])[0, 1])
    kabul = b >= 1.0 and (not np.isfinite(pla) or b - pla >= 0.5) and rho <= 0.30
    print(f"OOS plasebo Sh {pla:.2f} | carry rho {rho:+.2f} | HUKUM: {'SONRAKI TURA (harman, %95)' if kabul else 'RED'}")


if __name__ == "__main__":
    main()
