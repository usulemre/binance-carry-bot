"""MADDE 236: BACAK BAZINDA KATKI DEFTERI ve dusus ayristirmasi.

Motoru `KATKI=1` ile calistirip /tmp/katki_<faz>.pkl uretir, sonra
bacak bazinda kar/zarar yogunlasmasini, taraf x kapanis turu
ayristirmasini ve en kotu/en iyi bacaklarin NITELIKLERINI cikarir.

NEDEN: madde 230'a kadar ~50 yapilandirma TOPLAM istatistikle
kiyaslandi. Hicbiri "parayi hangi bacaklar kaybetti" diye sormadi -
oysa bir zarar kaynagi birkac olayda yogunlasmis olabilir ve parametre
taramasi onu bulamaz (her esik tum kitabi birden oynatir).

ANA BULGU (2026-10): bacaklarin %90'i (dengelemede kapananlar) net
-65 PUANLIK YUK; %10'u (TP ile kapananlar) +114,5 kazandirip hepsini
oduyor. Ve en kotu bacaklarin ayirt edici nitelikleri (yuksek oynaklik,
girişten onceki yukari hareket) EN IYI bacaklarda da var - yani
KUYRUK seciciler, ZARAR secicisi degil.
"""
import pickle
import sys

import numpy as np
import pandas as pd


def defter_oku(faz=0):
    return pickle.load(open(f"/tmp/katki_{faz}.pkl", "rb"))


def yogunlasma(d, kademeler=(10, 50, 100, 250, 500)):
    s = d.pnl.astype(float).sort_values()
    top = float(s.sum())
    return [(k, float(s.iloc[:k].sum()), float(s.iloc[-k:].sum()), top)
            for k in kademeler]


def taraf_kapanis(d):
    """ANA TABLO: taraf x kapanis turu."""
    return d.groupby([d.yon.map({1: "LONG", -1: "SHORT"}), "kapanis"]
                     ).pnl.agg(["count", "sum", "mean"])


def nitelik_karsilastir(d, n=250):
    """En kotu n, en iyi n ve tum bacaklarin niteliklerinin MEDYANI.

    DIKKAT: bir nitelik hem en kotude hem en iyide yuksekse, o nitelik
    bir KUYRUK secicidir - zarar secicisi DEGIL. Oynaklik ve onceki
    hareket tam bunu yapiyor; bu yuzden ikisine dayanan filtreler
    (madde 221 vol-olcekleme, madde 236 UCELE sikma) basarisiz oluyor.
    """
    kotu, iyi = d.nsmallest(n, "pnl"), d.nlargest(n, "pnl")
    out = {}
    for c in ("sin", "vol", "uc", "bar"):
        out[c] = (float(kotu[c].median()), float(iyi[c].median()),
                  float(d[c].median()))
    out["long_orani"] = (float((kotu.yon > 0).mean()),
                         float((iyi.yon > 0).mean()), float((d.yon > 0).mean()))
    return out


if __name__ == "__main__":
    d = defter_oku(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    d["pnl"] = d.pnl.astype(float)
    print(f"DEFTER: {len(d)} bacak | TP ile kapanan %{(d.kapanis=='TP').mean()*100:.1f}")
    print("\nTARAF x KAPANIS (ANA BULGU)")
    print(taraf_kapanis(d).to_string(float_format=lambda x: f"{x:+.5f}"))
    print("\nNITELIK KARSILASTIRMASI (en kotu 250 / en iyi 250 / tumu)")
    for k, v in nitelik_karsilastir(d).items():
        print(f"  {k:<12} {v[0]:+10.4f} {v[1]:+10.4f} {v[2]:+10.4f}")
