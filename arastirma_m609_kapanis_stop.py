#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 609 — PDF'İN EN KÖTÜ GÜNÜ (2021-05-19, T4 −%12,77) OTOPSİSİ ve 24 SA STOP'UN KAPANIŞLA TETİKLENMESİ.

Otopsi (GUNLUK_KATKI + POZ_CIKTI, T4 standart, uzun zemin; /tmp/m609, /tmp/m589):
  long −21,2 puan / short +8,4 (madde 537 ile aynı). Tutulan 15 long'un HEPSİ o gün −%25..−%40 (DOGE, YFI, IOTA, MKR, SRM, ZEC ...):
  coin seçimi değil piyasa çapında çöküş. YENİ bulgu, saat saat net maruziyet (dilimler arası ortalama ağırlık):
    00:00 long 0,40 / short 0,30 → 08:00 long 0,36 / short 0,05 (short kâr al %20 + kademe −%15 hedge'i çöküşün ORTASINDA
    hasat etti, kitap net +0,31 long kaldı) → 16:00 long 0,03 (24 sa stop −%45 gün içi İĞNEDE doldu) → ertesi gün coinler
    dipten %10-15 döndü, kitap long'suz kaçırdı.
  Madde 506: stop kapalıyken en kötü gün −11,7 → −6,8 ama −%5 altı gün 3 → 8. Yani stop'un işi doğru (kötü gün SAYISI),
  sorun tetik biçimi: bar içi dip (fitil) seviyeyi delip dönüyor. Haritada kapanışla tetik HİÇ sınanmadı (madde 449-453, 506,
  538-543 hep bar içi LOW ile).

ÖN KAYIT (koşudan önce yazıldı):
  Motor düğmesi SLL24_KAP=1 (g33, varsayılan 0 = parite): seviye aynı (24 sa önceki kapanış × (1 − SLL24)), tetik bar KAPANIŞI
  ≤ seviye, çıkış o kapanıştan. SLL24_KAP_TAZE=2: yalnız 8 sa'te bir kontrol (bot turu).
  Taban: T4 gerçekçi model (canlı gibi giriş TEK_GIRIS=1 + 5 bp + MERD_SIRA=1), uzun zemin, 2.000 $ D8, iki hiza; referans seri
  /tmp/m_ekim_kuru M357_EK_T4_2000_* (madde 587).
  Kollar: K45 (kapanış, her bar, −%45) · K45T2 (kapanış, 8 sa'te bir) · K35 (kapanış, her bar, −%35; kapanış fitilden sığ
  olduğu için seviye sıkılaştırılabilir mi) · S0 (stop kapalı; bağlam, aday olamaz).
  Ölçüm madde 596 eşit-risk yöntemi (k: dd / en kötü gün / 1y p1 ≤ T4 1,0x; blok bootstrap 20 g, 3000 yol, tohum 596).
  ADAY şartı: (a) eşit-risk yıllığı T4'ten ≥ +8 puan, (b) ham en kötü gün T4'ten sığ, (c) ham −%5 altı gün sayısı T4'ten
  fazla değil, (d) Sharpe ≤2024 ve 2025+ ayrı ayrı T4'ten düşük değil. Hepsi tutarsa T7K üzerinde tekrar (madde 610).
"""
import os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import arastirma_tabanlar as TB, arastirma_m346_prim as M
G = {**TB.T1, "MERD_SIRA": "1", "TEK_GIRIS": "1", "KOM": "0.0005"}
T4 = {**G, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
D = "/tmp/m609k"; os.makedirs(D, exist_ok=True)
KOL = {"K45": {"SLL24_KAP": "1"}, "K45T2": {"SLL24_KAP": "1", "SLL24_KAP_TAZE": "2"},
       "K35": {"SLL24_KAP": "1", "SLL24": "0.35"}, "S0": {"SLL24": "0"}}


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
    S = {"T4": _seri("/tmp/m_ekim_kuru", "T4")}
    for ad in KOL: S[ad] = _seri(D, ad)
    n = len(S["T4"]); idx = []
    for _ in range(3000):
        bas = rng.integers(0, n - 20, size=365 // 20 + 1); idx.append(np.concatenate([np.arange(b, b + 20) for b in bas])[:365])
    ref = _olc(S["T4"]); ref["p1"] = _p1(S["T4"], idx)
    gun = "2021-05-19"
    for ad in ["T4"] + list(KOL):
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
        if ad == "T4": S["_sh"] = (_sh(is_), _sh(oos))
    print("\nkötü 5 gün (T4 → kollar):")
    for g in S["T4"].nsmallest(5).index:
        print(f"  {g.date()} T4 {S['T4'][g]*100:+6.2f} | " + " ".join(f"{ad} {S[ad].get(g, np.nan)*100:+6.2f}" for ad in KOL))
    for ad in ("K45", "K45T2", "K35"):
        d = S[ad]; ham = _olc(d)
        sh = (_sh(d[d.index < "2025-01-01"]), _sh(d[d.index >= "2025-01-01"]))
        a = S[ad + "_er"] - S["T4_er"] >= 8; b = ham["ek"] > ref["ek"]; c = ham["g5"] <= ref["g5"]
        dd_ = sh[0] >= S["_sh"][0] and sh[1] >= S["_sh"][1]
        print(f"{ad}: a {'Y' if a else 'X'} b {'Y' if b else 'X'} c {'Y' if c else 'X'} d {'Y' if dd_ else 'X'} → "
              f"{'ADAY' if a and b and c and dd_ else 'RED'}")


if __name__ == "__main__":
    if sys.argv[1] == "kos":
        with ThreadPoolExecutor(2) as ex:
            for x in ex.map(kos, [(a, h) for a in KOL for h in (0, 1)]): print(x, flush=True)
    else:
        analiz()
