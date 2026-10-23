#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 446 — FELAKET İMZASI: kötü günü yaratan coin önceden tanınabilir mi? (T60 olay çalışması)

Kullanıcı: "hangi coin düştü biliyoruz, nedenini araştırıp engellemeye çalış". Madde 443: kötü gün
TEK coinden geliyor (long'ta küçük coin çöküşü, short'ta büyük coin sıkışması).
OLAY: T60 pozisyon dökümünde (POZ_CIKTI, iki hiza) bir barda tutulan (coin, yön) için sonraki 24 sa
katkısı w x r24 <= −%1,5 sermaye (felaket). KONTROL: aynı yönde tutulan diğer bütün bar-coin'ler.
Özellikler YALNIZ o bara kadar bilinen veriyle: funding sinyali (60 sa) ve anlık oran, 1 g / 7 g /
30 g fiyat değişimi, 24 sa aralık (H/L), açık pozisyon (OI) 1 g / 3 g değişimi, OI / piyasa değeri
yerine OI düzeyi, hesap long/short oranı, toptrader oranı, taker oranı, listeleme yaşı, spot varlığı.
ÇIKTI: her özelliğin olay vs kontrol medyanı ve ON-DİLİM RİSK ORANI (en riskli %10 dilimde felaket
olasılığı / genel olasılık). IS (22-07..24-12) ve OOS (25-01..26-09) ayrı — iki dönemde de tutmayan
imza sayılmaz. Sonra en iyi imza(lar) motor içinde ele/küçült kuralı olarak sınanır (madde 447).
"""
import json, os, pickle
import numpy as np, pandas as pd

D = "/tmp/m440"


def panel():
    p = f"{D}/imza_panel.pkl"
    if os.path.exists(p):
        return pd.read_pickle(p)
    z = pickle.load(open("/tmp/zemin.pkl", "rb")); C, H, L, sk, ODE = z["C"], z["H"], z["L"], z["sk"], z["ODE"]
    m = pd.read_pickle("/tmp/metrik_panel.pkl")
    sk60 = pd.read_pickle("/tmp/sk_bar60.pkl")
    oi = m["sum_open_interest_value"]
    ilk = C.notna().idxmax()
    yas = pd.DataFrame({c: (C.index - ilk[c]).days for c in C.columns}, index=C.index)
    spot = {k: set(v.get("aylar", [])) for k, v in json.load(open("data_spot_varlik.json")).items()}
    F = {
        "fund60": sk60, "fund_anlik": ODE,
        "r1g": C / C.shift(6) - 1, "r7g": C / C.shift(42) - 1, "r30g": C / C.shift(180) - 1,
        "aralik24": H.rolling(6).max() / L.rolling(6).min() - 1,
        "oi1g": oi / oi.shift(6) - 1, "oi3g": oi / oi.shift(18) - 1, "oi_log": np.log10(oi),
        "ls_hesap": m["count_long_short_ratio"], "ls_top": m["sum_toptrader_long_short_ratio"],
        "taker": m["sum_taker_long_short_vol_ratio"], "yas": yas,
    }
    r24 = C.shift(-6) / C - 1
    rows = []
    for h in (0, 1):
        P = pd.read_pickle(f"{D}/T60_poz_{h}.pkl")
        P = P[P.w.abs() > 1e-4]
        ii = C.index.get_indexer(P.zaman); kk = C.columns.get_indexer(P.sembol)
        df = pd.DataFrame({"zaman": P.zaman.values, "sembol": P.sembol.values, "w": P.w.values, "hiza": h})
        df["r24"] = r24.values[ii, kk]
        for ad, X in F.items():
            df[ad] = X.reindex(index=C.index, columns=C.columns).values[ii, kk]
        ay = pd.to_datetime(df.zaman).dt.strftime("%Y-%m")
        df["spot"] = [float(a in spot.get(s_, ())) for s_, a in zip(df.sembol, ay)]
        rows.append(df)
    T = pd.concat(rows, ignore_index=True)
    T["katki"] = T.w * T.r24
    T["yon"] = np.where(T.w > 0, "LONG", "SHORT")
    T = T.dropna(subset=["r24"])
    T.to_pickle(p)
    return T


def main():
    T = panel()
    T["felaket"] = T.katki <= -0.015
    T["IS"] = T.zaman < "2025-01-01"
    oz = ["fund60", "fund_anlik", "r1g", "r7g", "r30g", "aralik24", "oi1g", "oi3g", "oi_log", "ls_hesap", "ls_top", "taker", "yas", "spot"]
    for yon in ("LONG", "SHORT"):
        S = T[T.yon == yon]
        # aynı coin-gün olaylarını tekille (felaket bir kez sayılsın)
        S = S.assign(gun=S.zaman.dt.floor("D"))
        print(f"\n=== {yon}: {len(S)} bar-pozisyon, felaket {int(S.felaket.sum())} bar "
              f"({S[S.felaket].groupby(['sembol','gun']).ngroups} coin-gün), genel oran %{S.felaket.mean()*100:.2f}")
        print(f"{'ozellik':11s} {'olay med':>9s} {'kontrol med':>11s} | ust %10 risk orani IS / OOS | alt %10 risk orani IS / OOS")
        for o in oz:
            x = S[o]
            if x.notna().mean() < 0.5:
                print(f"{o:11s} veri yetersiz ({x.notna().mean()*100:.0f}%)"); continue
            om, km = S.loc[S.felaket, o].median(), S.loc[~S.felaket, o].median()
            sat = []
            for donem in (S.IS, ~S.IS):
                s = S[donem & x.notna()]
                if len(s) < 100 or s.felaket.sum() < 3:
                    sat += [np.nan, np.nan]; continue
                q9, q1 = s[o].quantile(0.9), s[o].quantile(0.1)
                g = s.felaket.mean()
                sat += [s[s[o] >= q9].felaket.mean() / g, s[s[o] <= q1].felaket.mean() / g]
            print(f"{o:11s} {om:9.4f} {km:11.4f} | {sat[0]:5.2f} / {sat[2]:5.2f}            | {sat[1]:5.2f} / {sat[3]:5.2f}")
    # en kötü olayların listesi
    E = T[T.felaket].sort_values("katki").drop_duplicates(["sembol", "yon"]).head(20)
    pd.set_option("display.width", 250)
    print("\nEN BUYUK 20 FELAKET (coin bazinda ilki):")
    print(E[["zaman", "sembol", "yon", "w", "r24", "katki", "fund60", "r1g", "r7g", "aralik24", "oi1g", "ls_hesap", "yas"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
