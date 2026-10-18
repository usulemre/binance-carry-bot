"""MADDE 239: PRIM SEVIYESI EKSENININ BUTCESI (nedensel, iki rejimde).

Madde 237 "farkli bir SINYAL degil farkli bir YAPI ara" demisti. Bu
arac, denenen yapisal eksenlerden birinin bütçesini madde 213'un
disipliniyle ONCE olcer: gozlenebilir prim seviyesi, kitabin KENDI
ileriye donuk getirisini siraliyor mu?

OLCU (hepsi nedensel):
  prim[t]  = uygun sembollerin funding kesitinde p90 - p10
             (SIN paneli zaten 3 gunluk geriye bakan ortalama)
  olcum    = prim'in son 30 gunluk ortalamasi
  referans = YEREL kayan medyan (varsayilan 180 gun) -- genisleyen
             medyan DEGIL. Genisleyen medyan kullanilirsa olcu primin
             TRENDINI yakalar ve yapi "2025 sonrasi kaldirac arttir"a
             doner; bu TEK bir gerceklesmedir, yapi degil.
  m[t]     = (olcum / referans), 1 bar gecikmeli

NE BULUNDU (madde 239):
  - Tam ornekte ceyrekler TEK YONLU: +%49,7 -> +%84,6 -> +%117,0 ->
    +%239,9 (Sharpe 1,67 -> 4,42).
  - Oynaklik ceyrekler arasinda DUZ (%24-29). Yani olcu bir oynaklik
    vekili degil, EDGE YOGUNLUGU olcusu.
  - 22-24'te tek yonlu (+%19,3 -> +%410,0), 25-26'da DEGIL
    (+%122,0 / +%53,9 / +%280,9 / +%159,3). Eksen var ama ikinci
    donemde cok daha gurultulu - ve yapinin 25-26 Sharpe'ini
    dusurmesinin sebebi tam bu.

Kosum: python3 arastirma_prim_butce.py
"""
import pickle

import numpy as np
import pandas as pd

OLCUM_GUN = 30       # prim olcum penceresi
REFERANS_GUN = 180   # YEREL referans penceresi
BAR_GUN = 6          # 4 saatlik bar

# (yillik %, Sharpe, oynaklik %, ort m) -- madde 239'da olculen
CEYREK_TAM = {"Q1": (49.7, 1.67, 26.1, 0.49), "Q2": (84.6, 2.34, 27.9, 0.87),
              "Q3": (117.0, 3.29, 24.5, 1.23), "Q4": (239.9, 4.42, 28.7, 2.93)}
CEYREK_2224 = {"Q1": (19.3, 0.97, 20.4, 0.53), "Q2": (47.7, 1.73, 24.2, 0.87),
               "Q3": (61.1, 1.84, 28.0, 1.09), "Q4": (410.0, 6.33, 26.3, 2.15)}
CEYREK_2526 = {"Q1": (122.0, 2.62, 32.5, 0.45), "Q2": (53.9, 2.01, 22.8, 0.88),
               "Q3": (280.9, 4.49, 30.9, 1.75), "Q4": (159.3, 3.29, 30.4, 3.75)}


def prim_serisi(panel_yolu="/tmp/panel.pkl"):
    """Nedensel prim olcusu ve YEREL referansa gore carpan (bar bazinda)."""
    P = pickle.load(open(panel_yolu, "rb"))
    S = P["SIN"].where(P["uy"])
    pr = (S.quantile(0.9, axis=1) - S.quantile(0.1, axis=1))
    pr = pr.rolling(OLCUM_GUN * BAR_GUN, min_periods=OLCUM_GUN * 4).mean()
    ref = pr.rolling(REFERANS_GUN * BAR_GUN,
                     min_periods=REFERANS_GUN * BAR_GUN // 2).median()
    return pr, (pr / ref).shift(1)


def _yaz(ad, t):
    print(f"  --- {ad} ---")
    print("  %-5s%10s%9s%10s%8s" % ("ceyrek", "yillik", "Sharpe", "oynaklik", "ort m"))
    for q, (y, s, o, m) in t.items():
        print("  %-5s%+10.1f%9.2f%10.1f%8.2f" % (q, y, s, o, m))


if __name__ == "__main__":
    print("MADDE 239 - PRIM SEVIYESI EKSENININ BUTCESI")
    print("olcu: kesitsel funding dagilimi (p90-p10), %d gun ortalama, "
          "kendi %d gunluk YEREL medyanina gore" % (OLCUM_GUN, REFERANS_GUN))
    print("kitap: tam kitap (madde 238 F satiri), gunluk getiri\n")
    _yaz("tum ornek", CEYREK_TAM)
    _yaz("2022-24", CEYREK_2224)
    _yaz("2025-26", CEYREK_2526)
    print("\nSONUC: eksen VAR (tam ornekte tek yonlu, oynaklik duz), ama")
    print("2025-26'da tek yonlu DEGIL. Butce gercek, guven rejime bagli.")
