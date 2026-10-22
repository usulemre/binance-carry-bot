#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 441 — SAATLİK KİTAP TESTİ (madde 440) BÜTÜN ADAYLARDA.

Kitaplar: KAYMA (bugünkü canlı kitap, kaymalı model), R30Y60S, T60 — her biri iki hiza, 2.000 $ D8.
Her kitap için g33 POZ_CIKTI ile pozisyon dökümü (parite /tmp/m412 ile kontrol), eksik sembol-ay
1 sa kline'ları indirilir, saatlik kitap kurulur (madde 440 yöntemi). Ölçülen:
 (1) saatlik düşüş sonrası 1/4/24 sa ortalaması, (2) madde 440'ın 36 kuralı (KES / EKLE),
 (3) en kötü 10 günün saat profili: kaybın kaçı ilk 1/3 saatte geliyor (stop ne kadar erken
     tetiklenmeli ki işe yarasın).
"""
import os, sys, subprocess, itertools, glob
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m346_prim as M
import arastirma_m440_saatlik_kitap as S

D = "/tmp/m440"
KITAP = {
    "KAYMA": dict(HAVUZ="4"),
    "R30Y60S": dict(HAVUZ="4", REB_GUN="5", TPL="0.40", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60",
                    HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0"),
    "T60": dict(HAVUZ="4", REB_GUN="5", TPL="0.60", TPS="0.20", REZERV="0.10", UCELE="0", YAS_GUN="60",
                HACIM_ESIK="7e7", SK_DOSYA="/tmp/sk_bar60.pkl", SLS="2.0"),
}


def poz(ad, h):
    p = f"{D}/{ad}_poz_{h}.pkl"; e = f"{D}/{ad}_{h}.pkl"
    if os.path.exists(p):
        return
    env = dict(os.environ, **dict(M.TABAN, **KITAP[ad]), AGIRLIK_KAYMA="1", FAZ_KAY=str(h),
               SEMBOL_HARIC=",".join(M.D8), E_CIKTI=e, POZ_CIKTI=p)
    subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, capture_output=True, timeout=7200,
                   cwd=os.path.dirname(os.path.abspath(__file__)))


def kos():
    from concurrent.futures import ThreadPoolExecutor
    isler = [(a, h) for a in KITAP for h in (0, 1)]
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda t: poz(*t), isler))
    for a, h in isler:
        x = pd.read_pickle(f"{D}/{a}_{h}.pkl").iloc[-1]; y = pd.read_pickle(f"/tmp/m412/M357_{a}_2000_{h}.pkl").iloc[-1]
        print(f"parite {a} {h}: {x:.4f} vs {y:.4f}", flush=True)
    # eksik sembol-ay
    sm = pd.concat([pd.read_pickle(f"{D}/{a}_poz_{h}.pkl") for a, h in isler])
    sm = sm[sm.w.abs() > 1e-6]; sm["ay"] = sm.zaman.dt.strftime("%Y-%m")
    sm = sm[["sembol", "ay"]].drop_duplicates()
    eksik = [(s, a) for s, a in sm.values if not os.path.exists(f"{D}/1h/{s}-{a}.zip")]
    print("eksik sembol-ay", len(eksik), flush=True)
    if eksik:
        B = "https://data.binance.vision/data/futures/um/monthly/klines"
        with open(f"{D}/u2.txt", "w") as f:
            for s, a in eksik:
                f.write(f'url = "{B}/{s}/1h/{s}-1h-{a}.zip"\noutput = "{D}/1h/{s}-{a}.zip"\n')
        subprocess.run(["curl", "-sS", "-f", "--parallel", "--parallel-max", "16", "--max-time", "60",
                        "--retry", "2", "-K", f"{D}/u2.txt"], capture_output=True)
        if os.path.exists(f"{D}/C1h.pkl"):
            os.remove(f"{D}/C1h.pkl")


def kitap_saatlik(ad, h):
    import pickle
    C4 = pickle.load(open("/tmp/zemin.pkl", "rb"))["C"]
    P = pd.read_pickle(f"{D}/{ad}_poz_{h}.pkl")
    W = P.pivot_table(index="zaman", columns="sembol", values="w", aggfunc="sum").reindex(C4.index).fillna(0).shift(1)
    C1 = S.saatlik_fiyat()
    ortak = [s for s in W.columns if s in C1.columns]
    kap = W[ortak].abs().sum().sum() / W.abs().sum().sum()
    R1 = C1[ortak].pct_change().fillna(0).clip(-0.95, 5)
    Wh = W[ortak].reindex(R1.index.floor("4h")).values
    r = pd.Series(np.nansum(Wh * R1.values, axis=1), index=R1.index)
    r = r[r.index >= W.index[W.abs().sum(axis=1) > 0][0]]
    E4 = pd.read_pickle(f"{D}/{ad}_{h}.pkl").pct_change().dropna()
    r4 = (1 + r).groupby(r.index.floor("4h")).prod() - 1
    i = r4.index.intersection(E4.index)
    return r, kap, np.corrcoef(r4.loc[i], E4.loc[i])[0, 1]


def analiz():
    pd.set_option("display.width", 220)
    ozet = []
    for ad in KITAP:
        for h in (0, 1):
            r, kap, kor = kitap_saatlik(ad, h)
            x = r.values
            print(f"\n=== {ad} hiza {h}: kapsam %{kap*100:.1f}, motorla korelasyon {kor:.3f}, saatlik yillik {S.YIL(x):+.1f} dd {S.DD(x):.1f}")
            nrm = np.mean([np.prod(1 + x[j:j + 24]) - 1 for j in range(0, len(x) - 24, 7)]) * 100
            for E in (-0.015, -0.02, -0.03):
                ix = np.where(x < E)[0]; ix = ix[ix + 25 < len(x)]
                f = lambda n: np.mean([np.prod(1 + x[j + 1:j + 1 + n]) - 1 for j in ix]) * 100
                print(f"  saat < {E*100:4.1f}% ({len(ix):3d}) sonraki 1 sa {f(1):+.3f} 4 sa {f(4):+.3f} 24 sa {f(24):+.3f} (normal 24 sa {nrm:+.3f})")
            # en kötü 10 gün saat profili
            g = (1 + r).groupby(r.index.date).prod() - 1
            kotu = g.sort_values().head(10)
            ilk1 = []; ilk3 = []
            for d in kotu.index:
                xs = r[str(d)].values; top = np.prod(1 + xs) - 1
                kum = np.cumprod(1 + xs) - 1; j = int(np.argmax(np.abs(xs) > 0.002)) if (np.abs(xs) > 0.002).any() else 0
                # kaybın ilk sert saatten itibaren 1 ve 3 saatte gelen payı
                ilk1.append((np.prod(1 + xs[j:j + 1]) - 1) / top); ilk3.append((np.prod(1 + xs[j:j + 3]) - 1) / top)
            print(f"  en kotu 10 gun ort {kotu.mean()*100:+.2f}% | kaybin ilk hareketli 1 saatte gelen payi %{np.median(ilk1)*100:.0f}, ilk 3 saatte %{np.median(ilk3)*100:.0f} (medyan)")
            IS = r.index < "2025-01-01"
            for E, D_, N in itertools.product((-0.01, -0.015, -0.02, -0.03), (0.0, 0.5, 1.5), (2, 6, 24)):
                row = dict(kitap=ad, h=h, E=E * 100, brut=D_, saat=N)
                for nm, m in (("IS", IS), ("OOS", ~IS), ("TAM", np.ones(len(r), bool))):
                    xx = r.values[m]; a, o = S.kural(xx, E, D_, N); b = xx * o
                    row[nm] = S.YIL(a) - S.YIL(b)
                    if nm == "TAM":
                        row["dd_fark"] = S.DD(a) - S.DD(b)
                ozet.append(row)
    T = pd.DataFrame(ozet)
    G = T.groupby(["kitap", "E", "brut", "saat"])[["IS", "OOS", "TAM", "dd_fark"]].mean().reset_index()
    print("\n=== KURALLAR (iki hiza ortalamasi; fark = kural - ayni ort. dozda sabit, yillik puan) ===")
    for ad in KITAP:
        g = G[G.kitap == ad]
        kes = g[g.brut < 1]; ekl = g[g.brut > 1]
        print(f"\n{ad}: KES kurallari {len(kes)}'in {int((kes.TAM > 0).sum())}'i pozitif (en iyi {kes.TAM.max():+.2f}, en kotu {kes.TAM.min():+.2f}); "
              f"dd'yi 1 puandan fazla iyilestiren KES: {int((kes.dd_fark > 1).sum())}")
        print(g.sort_values("TAM", ascending=False).head(6).round(2).to_string(index=False))
        print("  dd'yi en cok iyilestiren 3 kural:")
        print(g.sort_values("dd_fark", ascending=False).head(3).round(2).to_string(index=False))


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
