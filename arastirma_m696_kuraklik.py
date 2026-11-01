#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 696 — LİSTELEME KURAKLIĞINDA SERMAYE KORUMA. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Ön kayıt: KAR_HARITASI.md "Madde 696 ÖN KAYIT" (sonuçlar görülmeden, commit f9d34d4).
Yeni motor koşusu YOK: dünyalar madde 694 (/tmp/m694) ve 695 (/tmp/m695) motor çıktıları; savunma kolları kitap düzeyi örtü (günlük seri × s).
  python3 arastirma_m696_kuraklik.py analiz   -> /tmp/m696/*.csv + ekran raporu
"""
import os, sys, pickle
import numpy as np, pandas as pd
import arastirma_m695_dayaniklilik as T, arastirma_m694_yeni_coin as A4, arastirma_m346_prim as M
from tradfi_liste import TRADFI

D = "/tmp/m696"; os.makedirs(D, exist_ok=True)
BAS = "2021-01-01"
MALIYET = 0.0010          # |Δs| başına (iki taraf 5'er bp)
ESIK = 0.05               # ölçek ancak |Δs| ≥ 0,05 ise değişir
N_REF = 6.0               # K1: baz dünya 2021-23 genç coin sayısı %10'luğu (5,8) ≈ 6 — ön kayıt
KURAK = ["Y365K", "L50_a", "L50_b", "L75_a", "L75_b", "DUR24", "DUR25"]
HAFIF = ["L25_a", "L25_b"]
KAYNAK = {**{a: "/tmp/m694" for a in KURAK + HAFIF}, "A_DUR180": "/tmp/m695"}


def dunyalar():
    W = {"BAZ": T.seri("BAZ")}
    for a in KURAK + HAFIF + ["A_DUR180"]:
        if not T.tam(a, KAYNAK[a]): print("EKSİK:", a); continue
        W[a] = T.seri(a, KAYNAK[a])
    return W


def genc_sayi():
    """Her dünyanın evreninde (70M hacim, 60 g yaş, TradFi / D8 hariç, dünyanın çıkardıkları hariç) 60-365 g yaşında coin sayısı (gün ort.)."""
    P = pickle.load(open("/tmp/panel.pkl", "rb"))
    U = (P["C"].notna() & (P["HAC"] >= 7e7) & (P["YAS"] >= 360) & (P["DON"].fillna(0) < 0.10))
    U = U.drop(columns=[c for c in U.columns if c in TRADFI or c in M.D8])
    GEN = U & (P["YAS"] <= 365 * 6)
    S, _ = A4.senaryolar(); out = {}
    for ad, exc in [("BAZ", [])] + list(S.items()):
        ex = set(exc); out[ad] = GEN[[c for c in GEN.columns if c not in ex]].sum(axis=1).resample("D").mean()
    out["Y365K"] = out["BAZ"] * 0                               # genç coin hiç yok (asgari yaş 365 g dünyası)
    out["A_DUR180"] = out["DUR25"]
    G = pd.DataFrame(out); G.index = pd.to_datetime(G.index); return G


def uygula(r, hedef, nakit=0.0):
    """hedef: t günü için t−1'e kadarki veriyle hesaplanmış ölçek. Histerezis + değişim maliyeti; boşalan sermaye 'nakit' yıllık getiri."""
    h = hedef.reindex(r.index).fillna(1.0).values; x = r.values
    s = np.empty_like(h); cur = 1.0; out = np.empty_like(x)
    for i in range(len(x)):
        maliyet = 0.0
        if abs(h[i] - cur) >= ESIK: maliyet = MALIYET * abs(h[i] - cur); cur = h[i]
        s[i] = cur; out[i] = cur * x[i] + (1 - cur) * nakit / 365.25 - maliyet
    return pd.Series(out, index=r.index), pd.Series(s, index=r.index)


def hedefler(r, n, sigma_yildiz):
    e = (1 + r).cumprod(); dd = (e / e.cummax() - 1).shift(1).fillna(0)
    k1 = (n.rolling(30, min_periods=1).mean().shift(1).reindex(r.index).ffill().fillna(N_REF) / N_REF).clip(0.5, 1.0)
    k2 = (1 + 3 * dd).clip(lower=0.5, upper=1.0)
    s60 = r.rolling(60, min_periods=40).std().shift(1)
    k3 = (sigma_yildiz / s60).clip(0.5, 1.0).fillna(1.0)
    k4 = (k1 * k2).clip(lower=0.25)
    return {"K0 baz": pd.Series(1.0, index=r.index), "K1 KURAK": k1, "K2 DDA2": k2, "K3 V60K": k3, "K4 K1×K2": k4}


def olc2(d):
    o = T.olc(d); e = (1 + d).cumprod(); dd = e / e.cummax() - 1
    uw = (dd < 0).astype(int); g = (uw.diff() != 0).cumsum()
    r365 = e / e.shift(365) - 1
    o.update(en_kotu_365g=r365.min() * 100, zarar_365g_pay=(r365 < 0).mean() * 100, su_alti_maks_g=int(uw.groupby(g).sum().max()))
    return o


rng = np.random.default_rng(696)


def boot(d, ufuk=365, blok=10, n=2000):
    x = d.dropna().values; N = len(x); p = 1.0 / blok
    idx = np.empty((n, ufuk), dtype=np.int64); idx[:, 0] = rng.integers(0, N, n)
    yeni = rng.random((n, ufuk)) < p; rs = rng.integers(0, N, (n, ufuk))
    for t in range(1, ufuk): idx[:, t] = np.where(yeni[:, t], rs[:, t], (idx[:, t - 1] + 1) % N)
    eq = np.cumprod(1 + x[idx], axis=1); dd = ((eq / np.maximum.accumulate(eq, axis=1)) - 1).min(axis=1) * 100
    return dict(bs_zarar_olas=(eq[:, -1] < 1).mean() * 100, bs_cagr_p5=(np.percentile(eq[:, -1], 5) - 1) * 100,
                bs_dd_p5=np.percentile(dd, 5), bs_dd20_olas=(dd <= -20).mean() * 100)


def analiz():
    W = dunyalar(); G = genc_sayi(); G.to_pickle(f"{D}/genc_sayi.pkl")
    print(f"[KONTROL] dünya {len(W)} (beklenen {1 + len(KURAK) + len(HAFIF) + 1})")
    a, b = W["DUR25"], W["A_DUR180"]; print(f"[KONTROL] DUR25 (694) ile A_DUR180 (695) günlük seri farkı maks {float((a - b).abs().max()):.2e} (aynı evren)")
    rb = W["BAZ"][W["BAZ"].index >= BAS]
    sigma_yildiz = float(rb.rolling(60, min_periods=40).std().median())
    print(f"[ÖN KAYIT SABİTLERİ] N_REF {N_REF} · σ* (baz 60 g günlük oynaklık medyanı) {sigma_yildiz*100:.3f}% · maliyet 10 bp × |Δs| · eşik 0,05")

    rows, yil, olcek = [], {}, {}
    for nakit in (0.0, 0.05):
        for ad, r0 in W.items():
            if ad == "A_DUR180": continue
            r = r0[r0.index >= BAS]
            for kol, h in hedefler(r, G[ad], sigma_yildiz).items():
                rr, s = uygula(r, h, nakit)
                o = olc2(rr); o.update(dunya=ad, kol=kol, nakit=nakit, s_ort=s.mean(), s_son=s.iloc[-1], s_kisik_gun_pay=(s < 0.999).mean() * 100)
                if nakit == 0.0:
                    o.update(boot(rr)); yil[(ad, kol)] = T.yillik(rr); olcek[(ad, kol)] = s
                rows.append(o)
    R = pd.DataFrame(rows); R.to_csv(f"{D}/kollar.csv", index=False)
    pd.to_pickle(olcek, f"{D}/olcek.pkl")
    cols = ["cagr", "sharpe", "maks_dd", "calmar", "en_kotu_gun", "en_kotu_ay", "en_kotu_365g", "zarar_365g_pay", "su_alti_maks_g",
            "bs_zarar_olas", "bs_cagr_p5", "bs_dd20_olas", "s_ort", "s_kisik_gun_pay"]
    R0 = R[R.nakit == 0.0]
    for ad in ["BAZ"] + KURAK + HAFIF:
        print(f"\n==== {ad}" + ("  (normal dünya)" if ad == "BAZ" else "  (kuraklık)" if ad in KURAK else "  (hafif, yalnız rapor)"))
        print(R0[R0.dunya == ad].set_index("kol")[cols].round(2).to_string())
        Y = pd.DataFrame({k: yil[(ad, k)] for k in hedefler(rb, G["BAZ"], sigma_yildiz)}).T.round(1)
        print("  yıllık %: " + Y.to_string().replace("\n", "\n            "))

    # ------------------------------------------------------------------ ön kayıt şartları
    print("\n================ ÖN KAYIT ŞARTLARI (nakit %0)")
    K = []
    baz0 = R0[(R0.dunya == "BAZ") & (R0.kol == "K0 baz")].iloc[0]
    for kol in R0.kol.unique():
        k = R0[(R0.kol == kol) & R0.dunya.isin(KURAK)]
        n = R0[(R0.kol == kol) & (R0.dunya == "BAZ")].iloc[0]
        s1a = (k.en_kotu_365g >= 0).all(); s1b = (k.maks_dd >= -15).all(); s1c = (k.bs_zarar_olas <= 1).all()
        s2a = n.cagr >= 0.9 * baz0.cagr; s2b = n.maks_dd >= baz0.maks_dd - 1e-9
        K.append(dict(kol=kol, kurak_en_kotu_365g_min=k.en_kotu_365g.min(), kurak_365g_gecen=f"{(k.en_kotu_365g >= 0).sum()}/{len(k)}",
                      kurak_dd_min=k.maks_dd.min(), kurak_dd_gecen=f"{(k.maks_dd >= -15).sum()}/{len(k)}",
                      kurak_bs_zarar_maks=k.bs_zarar_olas.max(), kurak_bs_gecen=f"{(k.bs_zarar_olas <= 1).sum()}/{len(k)}",
                      kurak_cagr_med=k.cagr.median(), baz_cagr=n.cagr, baz_cagr_oran=n.cagr / baz0.cagr, baz_dd=n.maks_dd,
                      sart1=bool(s1a and s1b and s1c), sart2=bool(s2a and s2b), ADAY=bool(s1a and s1b and s1c and s2a and s2b)))
    KT = pd.DataFrame(K); print(KT.round(2).to_string(index=False)); KT.to_csv(f"{D}/sartlar.csv", index=False)

    # ------------------------------------------------------------------ nakit duyarlılığı
    print("\n[VARSAYIM] boşalan sermaye yıllık %5 (ör. USDT getirisi) ile, kuraklık dünyaları medyanı ve BAZ:")
    R5 = R[R.nakit == 0.05]
    t5 = R5[R5.dunya.isin(KURAK)].groupby("kol")[["cagr", "maks_dd", "en_kotu_365g"]].median().join(
        R5[R5.dunya == "BAZ"].set_index("kol")[["cagr", "maks_dd"]], rsuffix="_BAZ")
    print(t5.round(2).to_string())

    # ------------------------------------------------------------------ gösterge: gerçek dünyada şimdi ne diyor
    print("\n[ÖLÇÜM] gerçek (baz) dünyada genç coin sayısı n (30 g ort.) ve K1 ölçeği, çeyrek sonu:")
    n30 = G["BAZ"].rolling(30, min_periods=1).mean()
    q = pd.DataFrame({"n30": n30, "K1_s": (n30 / N_REF).clip(0.5, 1), "evren": G.get("evren", np.nan)}).resample("QE").last()
    print(q[q.index >= "2021-01-01"].round(2).T.to_string())
    print(f"  son gün ({n30.index[-1].date()}): n30 {n30.iloc[-1]:.1f} -> K1 ölçeği {min(1, max(0.5, n30.iloc[-1] / N_REF)):.2f}")
    s1 = olcek[("BAZ", "K1 KURAK")]; print(f"  baz dünyada K1'in kısık olduğu günler: {(s1 < 0.999).mean()*100:.1f}% · yıllara göre kısık gün payı %: "
                                        + ", ".join(f"{y} {(s1[s1.index.year == y] < 0.999).mean()*100:.0f}" for y in range(2021, 2027)))
    # göstergenin baz dünyada öngörü gücü (bilgi): kısık dönemlerde kitabın günlük ortalaması
    kis = s1 < 0.999
    print(f"  baz dünyada kitap günlük ort: K1 kısıkken {rb[kis].mean()*1e4:.1f} bp (sd {rb[kis].std()*1e4:.0f}) · açıkken {rb[~kis].mean()*1e4:.1f} bp (sd {rb[~kis].std()*1e4:.0f})")

    bek = ["kollar.csv", "sartlar.csv", "genc_sayi.pkl", "olcek.pkl"]
    yok = [f for f in bek if not os.path.exists(f"{D}/{f}")]
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if not yok else f"EKSİK {yok}")


def ek():
    """ÖN KAYIT DIŞI (sonuçlar görüldükten sonra): K1 eşik taraması ve sabit doz aritmetiği. Seçim yapılmaz; ailenin sınırını göstermek için."""
    W = dunyalar(); G = pd.read_pickle(f"{D}/genc_sayi.pkl")
    def ozet(fn):
        rows = []
        for ad in ["BAZ"] + KURAK:
            r = W[ad][W[ad].index >= BAS]; rr, s = uygula(r, fn(r, ad)); o = olc2(rr); o.update(boot=boot(rr)["bs_zarar_olas"]); o["dunya"] = ad; rows.append(o)
        R = pd.DataFrame(rows).set_index("dunya"); k = R.loc[KURAK]
        return dict(baz_cagr=R.loc["BAZ", "cagr"], baz_dd=R.loc["BAZ", "maks_dd"], kurak_cagr_med=k.cagr.median(), kurak_dd_min=k.maks_dd.min(),
                    kurak_dd_gecen=(k.maks_dd >= -15).sum(), kurak_365_min=k.en_kotu_365g.min(), kurak_365_gecen=(k.en_kotu_365g >= 0).sum(),
                    kurak_bs_maks=k.boot.max())
    print("[SONRADAN, ön kayıt dışı] K1 eşiği N_REF taraması:")
    rows = []
    for nref in (4, 6, 8, 10, 12, 15):
        f = lambda r, ad, n=nref: (G[ad].rolling(30, min_periods=1).mean().shift(1).reindex(r.index).ffill().fillna(n) / n).clip(0.5, 1.0)
        rows.append(dict(N_REF=nref, **ozet(f)))
    A = pd.DataFrame(rows); print(A.round(2).to_string(index=False)); A.to_csv(f"{D}/ek_esik.csv", index=False)
    print("\n[ARİTMETİK] sabit doz (kitap × d; kural değil, bilgi):")
    rows = [dict(doz=d, **ozet(lambda r, ad, d=d: pd.Series(d, index=r.index))) for d in (1.0, 0.85, 0.75, 0.67, 0.6, 0.5)]
    B = pd.DataFrame(rows); print(B.round(2).to_string(index=False)); B.to_csv(f"{D}/ek_doz.csv", index=False)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    elif len(sys.argv) > 1 and sys.argv[1] == "ek": ek()
    else: print(__doc__)
