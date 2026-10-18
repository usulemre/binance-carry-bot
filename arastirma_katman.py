"""MADDE 238: CIPLAK KESITSEL SECICIDEN TAM KITABA, katman katman.

"Kesitsel secici tek basina karli mi?" sorusunun olculmus cevabi.
Proje bugune kadar her katmani TAM yapilandirmadan TEK TEK CIKARARAK
olcmustu (224 havuz, 225 rezerv, 228 akis, 236 ucele, 227 TP). Hicbiri
tersini yapmamisti: CIPLAK secicidan baslayip katmanlari EKLEMEK.

Fark onemli, cunku katmanlar TOPLAMSAL DEGIL - isaretleri neyin
yaninda durduklarina bagli (madde 238'in ana bulgusu).

Kosum: arastirma_katman_kos.sh
"""
import pickle

import numpy as np
import pandas as pd

KATMANLAR = [("A  ciplak secici", "A_CIPLAK"), ("B  + kalabalik havuzu", "B_HAVUZ"),
             ("C  + emir akisi %20", "C_AKIS"), ("D  + uc hareket elemesi", "D_UCELE"),
             ("E  + firsat rezervi", "E_REZERV"), ("F  + KAR AL (tam kitap)", "F_TAM")]

OLCUM = {   # (yillik, Sharpe, dusus, esit-risk)  -- madde 238
    "A_CIPLAK": (72.5, 1.389, -34.8, 26.1), "B_HAVUZ": (107.1, 2.058, -20.4, 68.9),
    "C_AKIS": (109.8, 2.095, -23.0, 59.8), "D_UCELE": (103.1, 2.238, -23.6, 54.0),
    "E_REZERV": (92.8, 2.200, -19.8, 61.8), "F_TAM": (112.5, 2.942, -14.5, 112.5),
}


def gunluk(etiket, dizin="/tmp/m238b"):
    es = [pickle.load(open(f"{dizin}/E{etiket}_{k}.pkl", "rb")).pct_change()
          for k in (0, 1)]
    r = pd.concat(es, axis=1).mean(axis=1).dropna()
    return (1 + r).resample("1D").prod().dropna() - 1


def sharpe(v):
    return v.mean() / v.std(ddof=1) * np.sqrt(365.25)


if __name__ == "__main__":
    print("%-26s%10s%9s%9s%12s" % ("", "yillik", "Sharpe", "dusus", "esit-risk"))
    onc = None
    for ad, h in KATMANLAR:
        y, s, d, er = OLCUM[h]
        fark = "" if onc is None else "  (%+.1f puan)" % (er - onc)
        print("%-26s%+10.1f%9.3f%9.1f%+12.1f%s" % (ad, y, s, d, er, fark))
        onc = er
