#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 626 — SERT 24 SA ALEYHTE HAREKETTEN SONRA EKLE (madde 625 tutuş otopsisi).
625: tutulan pozisyonda coin 24 sa'te sert aleyhte gidince (long −%20, short +%20..+%50) TUTMAK her kırılımda doğru; piyasa çöküşü
(medyan ≤ −%3) dışında coin 1-7 g'de geri dönüyor (long −%20 sakin: tutuş değeri 3 g +15 puan/yıl). Madde 250 (girişten birikmiş aleyhlik
→ momentum, ekleme RED) GİRİŞ referanslıydı; bu kural HIZLI 24 sa hareketine ve piyasa koşuluna bakar. Madde 579-A (tek başına kapitülasyon
long) RED'di — bu yalnız kitabın ZATEN tuttuğu (funding'i lehte) coinlerde.
ÖN KAYIT: g33 EK24_L / EK24_S / EK24_PAY / EK24_PIY (varsayılan kapalı). Taban YENİ: T7K 1,15x + koşullu stop (bot ritmi, madde 623; P3T2,
eşit risk +315,2). Kollar: L20 (long −%20, ek %50) · S35 (short +%35, ek %50) · LS (ikisi). Piyasa medyanı > −%3 şartı.
Ölçüm madde 596 eşit-risk. ADAY: eşit-risk yıllığı tabandan ≥ +8 VE Sharpe ≤2024 ve 2025+ tabandan düşük değil.
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1", "KOM": "0.0005"}
T4 = {**G, "S_REB": "10", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0", "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}   # = T7K + koşullu stop (P3T2)
D = "/tmp/m626"; os.makedirs(D, exist_ok=True)
KOL = {"L20": {"EK24_L": "0.20"}, "S35": {"EK24_S": "0.35"}, "LS": {"EK24_L": "0.20", "EK24_S": "0.35"}}


def kos(a):
    ad, h = a; out = f"{D}/M357_EK_{ad}_2000_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **T4, **KOL[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, stdout=f, stderr=subprocess.STDOUT)
    return a, r.returncode


def _seri(dizin, ad):
    M.CIKTI = dizin
    return sum(M.gunluk(f"M357_EK_{ad}_2000_{h}") for h in (0, 1)) / 2


def _olc(d):
    eq = (1 + d).cumprod()
    return dict(yil=(eq.iloc[-1] ** (365.25 / len(d)) - 1) * 100, dd=(eq / eq.cummax() - 1).min() * 100,
                ek=d.min() * 100, g5=int((d < -0.05).sum()))


def _sh(d):
    return d.mean() / d.std() * np.sqrt(365.25)


def _p1(d, idx):
    v = d.values; out = []
    for yol in idx:
        eq = np.cumprod(1 + v[yol]); out.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
    return np.percentile(out, 1)


def analiz():
    rng = np.random.default_rng(596)
    S = {"T4": _seri("/tmp/m_ekim_kuru", "T4")}; M.CIKTI = "/tmp/m622"; S["T7K"] = sum(M.gunluk(f"M357_EK_P3T2_2000_{h}") for h in (0, 1)) / 2
    for ad in KOL: S[ad] = _seri(D, ad)
    n = len(S["T4"]); idx = []
    for _ in range(3000):
        bas = rng.integers(0, n - 20, size=365 // 20 + 1); idx.append(np.concatenate([np.arange(b, b + 20) for b in bas])[:365])
    ref = _olc(S["T4"]); ref["p1"] = _p1(S["T4"], idx)
    gun = "2021-05-19"
    for ad in ["T4", "T7K"] + list(KOL):
        d = S[ad]; ham = _olc(d); is_, oos = d[d.index < "2025-01-01"], d[d.index >= "2025-01-01"]
        best = None
        for k in np.arange(0.80, 2.51, 0.05):
            dk = d * k; o = _olc(dk)
            if o["dd"] < ref["dd"] or o["ek"] < ref["ek"]: break
            o["p1"] = _p1(dk, idx)
            if o["p1"] < ref["p1"]: break
            best = (k, o)
        k, o = best if best else (np.nan, dict(yil=np.nan))
        S[ad + "_er"] = o["yil"]
        print(f"{ad:6s} ham {ham['yil']:+7.1f} dd {ham['dd']:6.1f} en kötü {ham['ek']:6.2f} −%5 {ham['g5']:2d} | 19 May "
              f"{d.get(gun, np.nan)*100:+6.2f} | Sh ≤24 {_sh(is_):.2f} 25+ {_sh(oos):.2f} | eşit-risk k {k:.2f} → {o['yil']:+.1f}")
        if ad == "T7K": S["_sh"] = (_sh(is_), _sh(oos))
    print("\nkötü 5 gün (T4 → kollar):")
    for g in S["T4"].nsmallest(5).index:
        print(f"  {g.date()} T4 {S['T4'][g]*100:+6.2f} | " + " ".join(f"{ad} {S[ad].get(g, np.nan)*100:+6.2f}" for ad in KOL))
    for ad in KOL:
        d = S[ad]; ham = _olc(d)
        sh = (_sh(d[d.index < "2025-01-01"]), _sh(d[d.index >= "2025-01-01"]))
        a = S[ad + "_er"] - S["T7K_er"] >= 8; b = ham["ek"] > ref["ek"]; c = ham["g5"] <= ref["g5"]
        dd_ = sh[0] >= S["_sh"][0] and sh[1] >= S["_sh"][1]
        print(f"{ad}: a {'Y' if a else 'X'} b {'Y' if b else 'X'} c {'Y' if c else 'X'} d {'Y' if dd_ else 'X'} → "
              f"{'ADAY' if a and b and c and dd_ else 'RED'}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, h) for a in KOL for h in (0, 1)]): print(x, flush=True)
    else:
        analiz()
