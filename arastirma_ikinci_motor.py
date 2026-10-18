"""MADDE 237: BASKA BIR MOTOR VAR MI? (kesitsel momentum / geri donus)

Madde 214: funding GELIR degil SECICI; kari ureten sey TP hasadi.
Kimse funding'in EN IYI secici olup olmadigini sormamisti.

YONTEM: motor zaten `SK_DOSYA` ile disaridan sinyal paneli aliyor, yani
alternatif seciciler YENI KOD YAZMADAN denenebiliyor. Panel kuralı:
"en DUSUK skor -> LONG".

  kahin     : S = -(gelecek 5 gunluk getiri)   [mukemmel ongoru, TAVAN]
  momentum  : S = -(gecmis 5 gunluk getiri)    [kazananı long]
  reversal  : S = +(gecmis 5 gunluk getiri)    [kaybedeni long]
  harman    : S = (1-w)*rank(funding) + w*rank(momentum)

DIKKAT - CONFOUND: harman/momentum panelleri SIRA birimindedir, oysa
firsat rezervi HAM funding oranina bakar (S <= -REZ_ESIK). Yani bu
kosularda rezerv HIC tetiklenmez. Harman kiyasi bu yuzden "w=0 =
yalniz funding SIRASI" kontrolune karsi yapilmalidir, tam yapilandirma
kontrolune karsi DEGIL.

SONUC (2026-10):
  kahin      +%62.077  Sh 23,2   <- tavan astronomik, eksen insaat
                                     geregi KAPALI DEGIL
  momentum     +%82,5  Sh 1,94   <- gercek, bagimsiz bir motor
  reversal     +%32,1  Sh 1,23
  carry       +%112,5  Sh 2,94

AMA: sinyal korelasyonu +0,012 (neredeyse dik) iken GUNLUK GETIRI
korelasyonu **+0,718**. Sinyal dikligi, GETIRI dikligi demek degil.
Ne harman ne sermaye paylastirmasi ekliyor; ikisi de monoton kotulestiriyor.
"""
import pickle
import sys

import numpy as np
import pandas as pd


def panel_kur(C, tur, reb=30):
    """Alternatif secici paneli uretir. 'en dusuk skor -> LONG' kuralinda."""
    cv = C.values
    if tur == "kahin":
        x = np.full_like(cv, np.nan)
        x[:-reb] = cv[reb:] / np.where(cv[:-reb] > 0, cv[:-reb], np.nan) - 1
        return pd.DataFrame(-x, index=C.index, columns=C.columns)
    g = np.full_like(cv, np.nan)
    g[reb:] = cv[reb:] / np.where(cv[:-reb] > 0, cv[:-reb], np.nan) - 1
    isaret = -1.0 if tur == "momentum" else +1.0
    return pd.DataFrame(isaret * g, index=C.index, columns=C.columns)


def harman_kur(F, M, w):
    """rank harmani. w=0 -> yalniz funding SIRASI (dogru kontrol)."""
    b = (1 - w) * F.rank(axis=1, pct=True) + w * M.rank(axis=1, pct=True)
    return b.where(np.isfinite(F.values) & np.isfinite(M.values))


def gunluk(pat, fazlar=(0, 1)):
    es = [pickle.load(open(pat % k, "rb")).pct_change() for k in fazlar]
    r4 = pd.concat(es, axis=1).mean(axis=1).dropna()
    return (1 + r4).resample("1D").prod().dropna() - 1


def sharpe(v):
    return v.mean() / v.std(ddof=1) * np.sqrt(365.25)


OLCUM = {   # madde 237'de olculdu
    "kahin": (62077.3, 23.23), "momentum": (82.5, 1.935),
    "reversal": (32.1, 1.228), "carry": (112.5, 2.942),
    "sinyal_korelasyon": 0.012, "getiri_korelasyon": 0.718,
}

if __name__ == "__main__":
    c = gunluk("/tmp/m236/EU0.40_%d.pkl"); m = gunluk("/tmp/m237/EMOMENTUM_%d.pkl")
    ix = c.index.intersection(m.index)
    print("carry Sh %.3f | momentum Sh %.3f | gunluk getiri korelasyonu %+.3f"
          % (sharpe(c[ix]), sharpe(m[ix]), c[ix].corr(m[ix])))
