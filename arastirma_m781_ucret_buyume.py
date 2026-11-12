#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 781 — zincir üstü ÜCRET BÜYÜMESİ kitabı (DefiLlama günlük ücretler → Binance perp). Ön kayıt KAR_HARITASI 781. Yalnız araştırma.
  python3 arastirma_m781_ucret_buyume.py indir | analiz      (eşleme /tmp/m781/esleme.json: DefiLlama overview/fees + /protocols)"""
import json, os, sys, time, pickle, urllib.request
import numpy as np, pandas as pd
OUT = "/tmp/m781"
# isim çakışması — token o protokolün tokeni DEĞİL (elle, sonuç görülmeden)
YANLIS = {"WIF", "MASK", "LUNA", "FLOW", "XAI", "ALT", "FUN", "GAS", "META", "O", "V", "US", "LIGHT", "KITE", "TST", "TREE", "ALPHA", "CAP", "BASED",
          "LEND", "RE", "POWER", "CLO", "DAM", "PRL", "SLP", "SLX", "BTW", "CHIP", "APR", "HOME", "LAB", "OPEN", "BANK", "GENIUS", "TRIA", "INX", "MMT",
          "IR", "FLOCK", "GPS", "KGEN", "ZEST", "WET", "YALA", "OPN", "BR", "CTR", "STO", "XAUT", "BTC", "1000BONK", "KAITO", "EDGE", "MET", "STRK", "F"}


def indir():
    m = json.load(open(f"{OUT}/esleme.json")); os.makedirs(f"{OUT}/ucret", exist_ok=True)
    for sym, L in sorted(m.items()):
        if sym in YANLIS: continue
        for slug, ad, tip, _ in L:
            f = f"{OUT}/ucret/{slug}.json"
            if os.path.exists(f): continue
            u = f"https://api.llama.fi/summary/fees/{urllib.request.quote(slug)}?dataType=dailyFees"
            for i in range(3):
                try:
                    d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "m781"}), timeout=30).read())
                    json.dump(d.get("totalDataChart") or [], open(f, "w")); break
                except Exception as e:
                    time.sleep(2 * (i + 1))
            else:
                print("ALINAMADI", sym, slug, flush=True)
            time.sleep(0.25)
    print("bitti", len(os.listdir(f"{OUT}/ucret")))


def ucret_paneli():
    m = json.load(open(f"{OUT}/esleme.json")); d = {}
    for sym, L in m.items():
        if sym in YANLIS: continue
        s = None
        for slug, *_ in L:
            f = f"{OUT}/ucret/{slug}.json"
            if not os.path.exists(f): continue
            x = json.load(open(f))
            if not x: continue
            v = pd.Series({pd.Timestamp(int(t), unit="s").normalize(): float(a or 0) for t, a in x})
            v = v[~v.index.duplicated()]
            s = v if s is None else s.add(v, fill_value=0)
        if s is not None: d[sym + "USDT"] = s
    return pd.DataFrame(d).sort_index()


def kitap(sig, R, U, rng=None, maliyet=0.0010):
    """sig: haftalık sinyal (Pazartesi) · R: haftalık ileri getiri (fiyat + funding) · U: uygunluk. Dönen: haftalık net getiri serisi."""
    out = {}; w_once = pd.Series(dtype=float)
    for t in sig.index:
        s = sig.loc[t].where(U.loc[t]).dropna()
        s = s[R.loc[t].reindex(s.index).notna()]
        if len(s) < 12: continue
        if rng is not None: s = pd.Series(rng.permutation(s.values), index=s.index)
        n = len(s) // 3; o = s.sort_values()
        w = pd.Series(0.0, index=s.index); w[o.index[-n:]] = 0.5 / n; w[o.index[:n]] = -0.5 / n
        dev = w.sub(w_once, fill_value=0).abs().sum()
        out[t] = float((w * R.loc[t].reindex(w.index)).sum()) - dev * maliyet; w_once = w
    return pd.Series(out)


def sh(x): return float(x.mean() / x.std() * np.sqrt(52)) if len(x) > 10 and x.std() > 0 else np.nan


def analiz():
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = Z["C"]; U4 = Z["uy"].fillna(False).astype(bool); O = Z["ODE"].fillna(0)
    F = ucret_paneli(); F = F[[c for c in F.columns if c in C.columns]]
    print("ücret serisi olan perp:", F.shape[1], "·", F.index[0].date(), "→", F.index[-1].date())
    F = F.reindex(pd.date_range("2021-06-01", "2026-11-01")).fillna(0)
    haft = pd.date_range("2022-01-03", "2026-10-19", freq="W-MON")
    Ch = C.reindex(haft, method="ffill"); R = Ch.shift(-1) / Ch - 1
    Oc = (-O).cumsum().reindex(haft, method="ffill"); R = (R + (Oc.shift(-1) - Oc)).clip(-0.9, 3)       # long'un funding'i: −oran
    U = U4.reindex(haft, method="ffill").fillna(False)
    sigs = {}
    for ad, n in (("G14", 14), ("G30", 30)):
        son = F.rolling(n).sum(); onc = son.shift(n)
        g = np.log(son / onc).where((son >= 1000 * n / 14) & (onc > 0)).replace([np.inf, -np.inf], np.nan).shift(2)      # 2 gün yayın gecikmesi
        sigs[ad] = g.reindex(haft)
    import arastirma_m346_prim as M
    M.CIKTI = "/tmp/m_ekim"; P = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    Pw = (1 + P).resample("W-MON", label="left", closed="left").prod() - 1
    for ad, sig in sigs.items():
        n_ort = sig.where(U).notna().sum(axis=1)
        k = kitap(sig, R, U); br = kitap(sig, R, U, maliyet=0.0)
        rng = np.random.default_rng(781); pl = np.array([sh(kitap(sig, R, U, rng=rng)) for _ in range(200)])
        d = {"2022-23": k[:"2023-12-31"], "2024": k["2024-01-01":"2024-12-31"], "2025-26": k["2025-01-01":]}
        kor = k.corr(Pw.reindex(k.index))
        print(f"\n{ad}: hafta {len(k)} · evren ort {n_ort[n_ort >= 12].mean():.0f} coin (ilk {n_ort.iloc[0]}, son {n_ort.iloc[-1]}) · "
              f"net yıllık {k.mean() * 52 * 100:+.1f}% · Sh {sh(k):.2f} (maliyetsiz {sh(br):.2f}) · maks düşüş {((1 + k).cumprod() / (1 + k).cumprod().cummax() - 1).min() * 100:.0f}%")
        print("   dönem Sh:", {a: round(sh(b), 2) for a, b in d.items()}, f"· plasebo Sh %95 {np.nanpercentile(pl, 95):.2f} (medyan {np.nanmedian(pl):.2f}) · P3T2 korelasyon {kor:+.2f}")
        ok = sh(k) >= 1.5 and all(sh(b) > 0.5 for b in d.values()) and sh(k) > np.nanpercentile(pl, 95) and abs(kor) <= 0.30
        print("   ELEK:", "GEÇTİ → ADAY ikinci kitap" if ok else "RED")


if __name__ == "__main__":
    indir() if sys.argv[1] == "indir" else analiz()
