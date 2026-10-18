"""ESIK BAZLI TERS DONUS (REVERSAL) TESTI — madde 132.

Kullanicinin canli paper panosundaki yapi:
  - her gun 03:00 UTC'de karar
  - 24 saatte |getiri| >= ESIK (varsayilan %30) olanlar aday
  - asiri ARTANI SHORT, asiri DUSENI LONG
  - likidite filtresi (24s quote hacim esigi)
  - slot: bakiyenin %25'i tek pozisyona
  - sert stop: pozisyon bazinda %25 (bar ici high/low ile)
  - cikis: bir sonraki karar saatinde ya da stop

ONEMLI FARK: daha once test ettigim yapi "her gun en uc N coin"i
seciyordu — yani her gun MUTLAKA islem aciyordu. Bu yapi ise esik
asilmadikca HIC islem acmiyor. Bu ikisi ayni strateji degil.

Kullanim:
    python reversal_esik_backtest.py
    python reversal_esik_backtest.py --esik 0.30 --slot 0.25 --stop 0.25
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd

VERI = "historical_data_wide"
TAKER = 0.0005      # %0.05 tek yon
KAYMA = 0.0015      # uc hareket eden coinde gercekci kayma


def panel_yukle(klasor: str = VERI):
    kapanis, hacim, yuksek, dusuk = {}, {}, {}, {}
    for yol in sorted(glob.glob(os.path.join(klasor, "*_4h.csv"))):
        sem = os.path.basename(yol).replace("_4h.csv", "")
        try:
            d = pd.read_csv(yol, parse_dates=["date"]).set_index("date")
        except Exception:
            continue
        if len(d) < 200:
            continue
        kapanis[sem] = d["close"]
        hacim[sem] = d["quote_volume"]
        yuksek[sem] = d["high"]
        dusuk[sem] = d["low"]
    K = pd.DataFrame(kapanis).sort_index()
    return (K, pd.DataFrame(hacim).reindex_like(K),
            pd.DataFrame(yuksek).reindex_like(K),
            pd.DataFrame(dusuk).reindex_like(K))


def bt(K, H, YK, DS, esik=0.30, slot=0.25, stop=0.25, max_poz=2,
       min_hacim=5e6, karar_saati=3, baslangic=None, bitis=None, log=False):
    """Gunluk karar, bir sonraki karara kadar tut, bar ici sert stop."""
    idx = K.index
    if baslangic is not None:
        maske = (idx >= baslangic) & (idx <= (bitis or idx[-1]))
        K, H, YK, DS = K[maske], H[maske], YK[maske], DS[maske]
        idx = K.index

    # karar barlari: gunde bir, verilen saatte
    karar = [i for i, t in enumerate(idx) if t.hour == karar_saati]
    if len(karar) < 10:
        karar = list(range(0, len(idx), 6))

    bakiye = 1.0
    egri, islemler = [], []
    ret6 = K.pct_change(6)            # 6 bar x 4s = 24 saat
    hac24 = H.rolling(6).sum()

    for j in range(len(karar) - 1):
        i0, i1 = karar[j], karar[j + 1]
        r = ret6.iloc[i0]
        h = hac24.iloc[i0]
        p0 = K.iloc[i0]
        uygun = r.notna() & p0.notna() & (h >= min_hacim) & (r.abs() >= esik)
        adaylar = r[uygun]
        if len(adaylar) > max_poz:
            adaylar = adaylar.reindex(adaylar.abs().sort_values(ascending=False).index)[:max_poz]

        gun_pnl = 0.0
        for sem, deger in adaylar.items():
            yon = -1 if deger > 0 else 1       # artani short, duseni long
            giris = p0[sem]
            if not np.isfinite(giris) or giris <= 0:
                continue
            dilim = K[sem].iloc[i0 + 1:i1 + 1]
            yuk = YK[sem].iloc[i0 + 1:i1 + 1]
            dus = DS[sem].iloc[i0 + 1:i1 + 1]
            if len(dilim) == 0:
                continue
            # bar ici stop: long ise dusuk, short ise yuksek
            ham = None
            if yon == 1:
                vur = dus[dus <= giris * (1 - stop)]
                if len(vur) > 0:
                    ham = -stop
            else:
                vur = yuk[yuk >= giris * (1 + stop)]
                if len(vur) > 0:
                    ham = -stop
            if ham is None:
                cikis = dilim.iloc[-1]
                if not np.isfinite(cikis):
                    continue
                ham = yon * (cikis / giris - 1.0)
            net = ham - 2 * (TAKER + KAYMA)
            gun_pnl += slot * net
            islemler.append({"t": idx[i0], "sem": sem, "yon": yon,
                             "tetik": deger, "net": net, "stop": ham == -stop})
        bakiye *= (1 + gun_pnl)
        egri.append({"t": idx[i1], "bakiye": bakiye})
        if bakiye <= 0.02:
            break

    E = pd.DataFrame(egri).set_index("t")["bakiye"] if egri else pd.Series(dtype=float)
    T = pd.DataFrame(islemler)
    if len(E) < 5:
        return {"getiri": np.nan, "yillik": np.nan, "sharpe": np.nan,
                "maxdd": np.nan, "islem": 0, "egri": E, "islemler": T}
    gunluk = E.pct_change().dropna()
    yil = (E.index[-1] - E.index[0]).days / 365.25
    yillik = (E.iloc[-1] ** (1 / max(yil, 1e-9)) - 1) if E.iloc[-1] > 0 else -1
    sharpe = gunluk.mean() / gunluk.std() * np.sqrt(365) if gunluk.std() > 0 else np.nan
    maxdd = (E / E.cummax() - 1).min()
    return {"getiri": E.iloc[-1] - 1, "yillik": yillik, "sharpe": sharpe,
            "maxdd": maxdd, "islem": len(T), "kazanma": (T["net"] > 0).mean() if len(T) else np.nan,
            "stop_orani": T["stop"].mean() if len(T) else np.nan,
            "egri": E, "islemler": T}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esik", type=float, default=0.30)
    ap.add_argument("--slot", type=float, default=0.25)
    ap.add_argument("--stop", type=float, default=0.25)
    ap.add_argument("--max-poz", type=int, default=2)
    a = ap.parse_args()

    K, H, YK, DS = panel_yukle()
    print(f"panel: {K.shape[1]} sembol, {K.index[0].date()} -> {K.index[-1].date()}\n")

    print(f"TAM DONEM  esik=%{a.esik*100:.0f} slot=%{a.slot*100:.0f} stop=%{a.stop*100:.0f}")
    s = bt(K, H, YK, DS, esik=a.esik, slot=a.slot, stop=a.stop, max_poz=a.max_poz)
    print(f"  toplam getiri : {s['getiri']*100:+.1f}%")
    print(f"  yillik        : {s['yillik']*100:+.1f}%")
    print(f"  sharpe        : {s['sharpe']:.2f}")
    print(f"  max dusus     : {s['maxdd']*100:.1f}%")
    print(f"  islem sayisi  : {s['islem']}   kazanma: %{s['kazanma']*100:.0f}"
          f"   stop yiyen: %{s['stop_orani']*100:.0f}")

    print("\nYILLARA GORE")
    for yil in [2023, 2024, 2025, 2026]:
        b = pd.Timestamp(f"{yil}-01-01")
        e = pd.Timestamp(f"{yil}-12-31 23:59")
        if b > K.index[-1] or e < K.index[0]:
            continue
        y = bt(K, H, YK, DS, esik=a.esik, slot=a.slot, stop=a.stop,
               max_poz=a.max_poz, baslangic=b, bitis=e)
        if np.isnan(y["getiri"]):
            continue
        print(f"  {yil}: {y['getiri']*100:+7.1f}%   sharpe {y['sharpe']:5.2f}"
              f"   dusus {y['maxdd']*100:6.1f}%   islem {y['islem']}")

    print("\n70 GUNLUK PENCERE DAGILIMI (kullanicinin canli deneyi 70 gun)")
    E = s["egri"]
    if len(E) > 80:
        pen = []
        for i in range(len(E) - 70):
            pen.append(E.iloc[i + 70] / E.iloc[i] - 1)
        pen = np.array(pen)
        print(f"  pencere sayisi : {len(pen)}")
        print(f"  ortanca        : {np.median(pen)*100:+.1f}%")
        print(f"  %90 dilim      : {np.percentile(pen, 90)*100:+.1f}%")
        print(f"  en iyi         : {pen.max()*100:+.1f}%")
        print(f"  +%120 ustu     : %{(pen >= 1.20).mean()*100:.1f} ihtimal")
        print(f"  arti biten     : %{(pen > 0).mean()*100:.0f}")


if __name__ == "__main__":
    main()
