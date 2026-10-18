"""Madde 219: CAPRAZ-BORSA FUNDING FARKI KITABI.

Her pozisyon = ayni sembolde iki borsada TERS bacak. Fiyat riski
YAPISAL olarak yok (ayni varlik). Gelir = funding farki.

MALIYET: pozisyon basina 4 bacak (BN acilis+kapanis, Gate acilis+kapanis).
GROSS: toplam nominal / sermaye. Bir cift, her borsada N nominal =
toplam 2N. n cift ve GROSS ile bacak = C*GROSS/(2n).

OLCULMEYEN RISK: borsalar arasi BAZ sapmasi. Gate fiyat verisi yok, o
yuzden fiyat bacaklarinin tam netlestigi VARSAYILDI. Gercekte iki borsa
fiyati birbirinden ayrilabilir; bu, kitabin en buyuk olculmemis riski.
"""
import pickle, numpy as np, pandas as pd, os, sys
P = pickle.load(open('/tmp/panel.pkl','rb')); C = P['C']; uy = P['uy']
X = pickle.load(open('/tmp/capraz_panel.pkl','rb')); BN, GT = X['BN'], X['GT']
O = pickle.load(open('/tmp/capraz_ode.pkl','rb'))
ODE_BN, ODE_GT = O['ODE_BN'], O['ODE_GT']
kol = list(BN.columns)
FARK = (BN - GT).values
U = uy.reindex(columns=kol).values & np.isfinite(FARK)
nk = len(kol)

def bt(bas, n, REB, KOM_BACAK, GROSS=1.0, GEC=1):
    poz = np.zeros(nk); eq = [1.0]; bek = None
    w = GROSS / (2 * n)            # her borsada bacak agirligi
    for i in range(bas, len(C) - 1):
        if bek is not None and bek[0] == i:
            y = bek[1]
            # 4 bacak: her borsada acilis+kapanis -> |dy| x 2 borsa
            eq[-1] *= 1 - np.abs(y - poz).sum() * 2 * KOM_BACAK
            poz = y; bek = None
        if (i - bas) % REB == 0:
            g = U[i]
            ix = np.flatnonzero(g)
            nn = min(n, ix.size)
            if nn >= max(3, n // 2):
                buyuk = ix[np.argsort(-np.abs(FARK[i][ix]))[:nn]]
                y = np.zeros(nk)
                y[buyuk] = np.sign(FARK[i][buyuk]) * w
                bek = (i + GEC, y)
        # bar getirisi: SADECE funding farki (fiyat netlesiyor)
        r = float(np.nansum(poz * (np.nan_to_num(ODE_BN[i+1])
                                   - np.nan_to_num(ODE_GT[i+1]))))
        eq.append(eq[-1] * (1 + r))
    return pd.Series(eq, index=C.index[bas:])

def ozet(e, ad):
    g = e.pct_change().dropna()
    gun = ((1 + g).resample('1D').prod() - 1).dropna()
    E = (1 + gun).cumprod()
    yil = E.iloc[-1] ** (365.25 / len(gun)) - 1
    sh = gun.mean() / gun.std() * np.sqrt(365.25)
    dd = -(E / E.cummax() - 1).min()
    m1 = gun.index < '2025-01-01'
    s1 = gun[m1].mean()/gun[m1].std()*np.sqrt(365.25)
    s2 = gun[~m1].mean()/gun[~m1].std()*np.sqrt(365.25)
    print(f"{ad:30s} yillik %{yil*100:+7.1f}  Sh {sh:5.2f}  "
          f"22-24 {s1:5.2f}  25-26 {s2:5.2f}  dusus %{dd*100:5.2f}", flush=True)
    return gun

print(f"evren: medyan {int(np.median(U[1200:].sum(axis=1)))} uygun sembol "
      f"(p10 {int(np.percentile(U[1200:].sum(axis=1),10))})")
print()
sonuc = {}
for n in (5, 10, 20):
    for REB in (6, 30):
        for kom in (0.0002, 0.0004):
            e = bt(1200, n, REB, kom)
            ad = f"n={n:<2d} tut={REB//6}g kom={kom*1e4:.0f}bp"
            sonuc[ad] = ozet(e, ad)
pickle.dump(sonuc, open('/tmp/capraz_sonuc.pkl','wb'))
