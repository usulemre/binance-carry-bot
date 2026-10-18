"""Madde 213: yillik DEVIR HIZI. Komisyonun kac puana mal oldugunu
anlamak icin |delta pozisyon| toplamini olcmek gerekiyor."""
import sys; sys.path.insert(0,'/tmp')
from g import *
import numpy as np, pickle
S = pickle.load(open('/tmp/sk_bar48.pkl','rb')).reindex(index=C.index, columns=C.columns).values
REBB, NDILIM, GROSS, n = 30, 15, 3.0, 6
adim = REBB // NDILIM        # 2 bar = 8 saat
poz = np.zeros(C.shape[1])
dilimler = {}
devir = 0.0
bar_say = 0
for i in range(1200, len(C) - 1):
    if (i - 1200) % adim == 0:
        sira = ((i - 1200) // adim) % NDILIM
        g = np.isfinite(S[i]) & np.isfinite(cv[i]) & U[i]
        ix = np.flatnonzero(g); nn = min(n, len(ix) // 2)
        if nn >= 4:
            sc = rk(S[i][ix]); a = pd.Series(A[i][ix])
            if a.notna().sum() >= 0.5 * len(ix):
                sc = 0.8*sc + 0.2*(-a).rank(pct=True).fillna(0.5).values
            o = np.argsort(sc)
            y = np.zeros(C.shape[1])
            y[ix[o[:nn]]] = (GROSS/2) / (NDILIM * nn)
            y[ix[o[-nn:]]] = -(GROSS/2) / (NDILIM * nn)
            dilimler[sira] = y
            yeni = sum(dilimler.values())
            devir += np.abs(yeni - poz).sum()
            poz = yeni
    bar_say += 1
yil = bar_say / (6 * 365.25)
print(f"{bar_say} bar = {yil:.2f} yil")
print(f"toplam |delta pozisyon| = {devir:.1f} x sermaye")
print(f"YILLIK DEVIR = {devir/yil:.1f} x sermaye")
for bp in (1, 2, 3, 5):
    print(f"  {bp} bp komisyon -> yillik %{devir/yil*bp/10000*100:.2f} maliyet "
          f"(basit), bilesikte daha fazla")
