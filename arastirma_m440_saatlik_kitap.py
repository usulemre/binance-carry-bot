#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 440 — T60 KİTABININ SAATLİK GETİRİSİ ve saatlik koruma kuralları.

Kullanıcı: "saatlik baksak ne olur". Motor 4 sa çubukla çalışır. g33'e POZ_CIKTI eklendi (dilimler
arası ortalama pozisyon, her bar; parite tam). Pozisyonu tutulan 586 sembolün 4.211 sembol-ay 1 sa
kline'ı indirildi (data.binance.vision). Saatlik kitap = 4 sa barın ağırlıkları (önceki bar, ölçülen
hizalama: 4 sa yeniden kurulumla korelasyon 0,973) x saatlik fiyat getirisi. Funding/TP/stop bar içi
yok → yaklaşık; dinamik (düşüş sonrası ne oluyor) için yeterli.
SORULAR: (1) saatlik düşüşten sonraki 1/4/24 sa — devam mı, dönüş mü? (2) saatlik koruma kuralları:
KES (düşüşten 1 sa sonra brüt 0,5 / 0, N saat) ve EKLE (1 sa sonra brüt 1,5, N saat); aynı
ortalama dozda sabit kaldıraçla kıyas, |Δbrüt| x %0,10 maliyet; IS 22-24 / OOS 25-26 ayrı.
"""
import glob, os, sys, zipfile, itertools
import numpy as np, pandas as pd

D = "/tmp/m440"


def saatlik_fiyat():
    p = f"{D}/C1h.pkl"
    if os.path.exists(p):
        return pd.read_pickle(p)
    seri = {}
    for z in sorted(glob.glob(f"{D}/1h/*.zip")):
        s = os.path.basename(z).rsplit("-", 2)[0]
        try:
            with zipfile.ZipFile(z) as zf:
                df = pd.read_csv(zf.open(zf.namelist()[0]), header=None)
        except Exception:
            continue
        if not str(df.iloc[0, 0]).isdigit():
            df = df.iloc[1:]
        t = pd.to_datetime(df.iloc[:, 0].astype("int64"), unit="ms")
        seri.setdefault(s, []).append(pd.Series(df.iloc[:, 4].astype(float).values, index=t))
    C = pd.DataFrame({s: pd.concat(v).sort_index().loc[lambda x: ~x.index.duplicated()] for s, v in seri.items()})
    C.to_pickle(p)
    return C


def saatlik_kitap(h=0):
    import pickle
    C4 = pickle.load(open("/tmp/zemin.pkl", "rb"))["C"]
    P = pd.read_pickle(f"{D}/T60_poz_{h}.pkl")
    W = P.pivot_table(index="zaman", columns="sembol", values="w", aggfunc="sum").reindex(C4.index).fillna(0)
    W = W.shift(1)                      # ölçülen hizalama (madde 440)
    C1 = saatlik_fiyat()
    ortak = [s for s in W.columns if s in C1.columns]
    R1 = C1[ortak].pct_change().fillna(0).clip(-0.95, 5)
    blok = R1.index.floor("4h")
    Wh = W[ortak].reindex(blok).values
    r = pd.Series(np.nansum(Wh * R1.values, axis=1), index=R1.index)
    r = r[(r.index >= W.index[W.abs().sum(axis=1) > 0][0])]
    kapsam = W[ortak].abs().sum(axis=1).sum() / W.abs().sum(axis=1).sum()
    return r, kapsam


YIL = lambda x: (np.prod(1 + x) ** (365.25 * 24 / len(x)) - 1) * 100
def DD(x):
    e = np.cumprod(1 + x); return (e / np.maximum.accumulate(e) - 1).min() * 100


def kural(r, E, D_, N, gec=1):
    s = np.ones(len(r))
    for i in np.where(r < E)[0]:
        a, b = i + gec, i + gec + N
        s[a:b] = np.minimum(s[a:b], D_) if D_ < 1 else np.maximum(s[a:b], D_)
    m = np.abs(np.diff(np.r_[1.0, s])) * 0.001
    return s * r - m, s.mean()


def main():
    for h in (0,):
        r, kap = saatlik_kitap(h)
        E4 = pd.read_pickle(f"{D}/T60_0.pkl").pct_change().dropna()
        r4 = (1 + r).groupby(r.index.floor("4h")).prod() - 1
        i = r4.index.intersection(E4.index)
        print(f"hiza {h}: saatlik kitap {len(r)} saat, agirlik kapsami %{kap*100:.1f}, "
              f"4 sa'e toplanmis korelasyon (motor) {np.corrcoef(r4.loc[i], E4.loc[i])[0,1]:.3f}")
        x = r.values
        print("\n(1) SAATLIK DUSUSTEN SONRA (ortalama getiri, %)")
        norm = {n: np.mean([np.prod(1 + x[j:j + n]) - 1 for j in range(0, len(x) - n, 7)]) * 100 for n in (1, 4, 24)}
        print(f"  normal              sonraki 1 sa {norm[1]:+.3f}  4 sa {norm[4]:+.3f}  24 sa {norm[24]:+.3f}")
        for E in (-0.01, -0.015, -0.02, -0.03):
            ix = np.where(x < E)[0]; ix = ix[ix + 25 < len(x)]
            f = lambda n: np.mean([np.prod(1 + x[j + 1:j + 1 + n]) - 1 for j in ix]) * 100
            print(f"  saat < {E*100:4.1f}% ({len(ix):4d} kez) sonraki 1 sa {f(1):+.3f}  4 sa {f(4):+.3f}  24 sa {f(24):+.3f}")
        print("\n(2) SAATLIK KORUMA KURALLARI (1 sa gecikme; fark = kural - ayni ort. dozda sabit, yillik puan)")
        IS = r.index < "2025-01-01"
        rows = []
        for E, D_, N in itertools.product((-0.01, -0.015, -0.02, -0.03), (0.0, 0.5, 1.5), (2, 6, 24)):
            row = dict(E=E * 100, brut=D_, saat=N)
            for ad, m in (("IS", IS), ("OOS", ~IS), ("TAM", np.ones(len(r), bool))):
                xx = r.values[m]; a, ort = kural(xx, E, D_, N); b = xx * ort
                row[ad] = YIL(a) - YIL(b)
                if ad == "TAM":
                    row["dd_fark"] = DD(a) - DD(b); row["dd_vs_T60"] = DD(a) - DD(xx); row["doz"] = ort
            rows.append(row)
        T = pd.DataFrame(rows).sort_values("TAM", ascending=False)
        pd.set_option("display.width", 200)
        print(T.round(2).to_string(index=False))
        print(f"\nsaatlik kitap (kuralsiz): yillik {YIL(x):+.1f} dd {DD(x):.1f}")


if __name__ == "__main__":
    main()
