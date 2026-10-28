#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 644 — KULLANICININ "REVERSAL DENEYİ" (ayrı bot, kâğıt üstünde 2026-07-10'dan beri 109 g: 2.000 $ → 9.838 $, +%392).
Kural (ekrandan): 24 sa'te ±%30'dan fazla hareket eden LİKİT coin → aşırı artanı SHORT, aşırı düşeni LONG; slot bakiyenin %25'i; sert stop
%25. Kullanıcının backtest'i +%326 / yıl. Bu araç aynı kuralı BİZİM 6 yıllık zeminimizde (2020-07 → 2026-09, 853 sembol, delist edilenler
dahil = hayatta kalan yanlılığı yok) ve bizim maliyet modelimizle sınar.
Model: 4 sa bar. Sinyal bar i kapanışında r24 = C[i]/C[i−6] − 1, |r24| ≥ eşik, coin "likit" (24 sa hacim ≥ HACIM) ve en az 30 g geçmiş.
Giriş bar i kapanışı + kayma (KAYMA bp), çıkışta da; funding ödemesi (zemin ODE) yönle işlenir. En fazla 4 slot (her biri girişte özkaynağın
%25'i), sinyal çoksa en büyük |r24| önce; aynı coinde tek pozisyon. Çıkış: stop (bar içi H/L, açılış stop'u geçtiyse açılıştan) ya da
TUT bar dolunca kapanış; isteğe bağlı kâr al TP. Özkaynak her bar piyasaya göre değerlenir (MTM).
Kollar: tutuş 1 / 3 / 7 g, TP yok / %25; hacim 20M / 70M; eşik %30 / %50. Dönemler ayrı: 2020-21, 2022-24, 2025-26 ve 2026-07 sonrası
(kullanıcının canlı penceresi — veri 09-30'da bitiyor).
"""
import pickle
import numpy as np
import pandas as pd

z = pickle.load(open("/tmp/zemin.pkl", "rb"))
C, H, L, F = z["C"], z["H"], z["L"], z["ODE"]
O = pickle.load(open("/tmp/hlo.pkl", "rb"))["O"].reindex(index=C.index, columns=C.columns)
P = pickle.load(open("/tmp/zu/panel.pkl", "rb"))
HAC = P["HAC"].reindex(index=C.index, columns=C.columns)
cv, hv, lv, ov, fv, hac = (x.values for x in (C, H, L, O, F.fillna(0.0), HAC))
ilk = np.argmax(np.isfinite(cv), axis=0)                   # her sembolün ilk barı
r24 = np.full_like(cv, np.nan); r24[6:] = cv[6:] / cv[:-6] - 1
T = len(C.index); bas = int(C.index.searchsorted(pd.Timestamp("2020-07-19")))


def kos(esik=0.30, hacim=2e7, tut=6, tp=0.0, stop=0.25, slot=0.25, nslot=4, kayma=0.0005, soguma=6, karar_saat=None):
    eq = 1.0; acik = {}; seri = np.ones(T); islem = []; son_cikis = {}
    for i in range(bas, T - 1):
        # 1) açık pozisyonlar: bar i+1 içinde stop / TP / süre
        kapat = []
        pnl_bar = 0.0
        for k, p in acik.items():
            yon, giris, w, t0 = p["yon"], p["giris"], p["w"], p["t0"]
            o, h, l, c = ov[i + 1, k], hv[i + 1, k], lv[i + 1, k], cv[i + 1, k]
            if not np.isfinite(c):
                c = p["son"]; h = l = o = c
            if not np.isfinite(o): o = p["son"]
            if not np.isfinite(h): h = max(o, c)
            if not np.isfinite(l): l = min(o, c)
            s_sev = giris * (1 + stop) if yon < 0 else giris * (1 - stop)
            t_sev = (giris * (1 - tp) if yon < 0 else giris * (1 + tp)) if tp > 0 else None
            cikis = None
            if (yon < 0 and h >= s_sev) or (yon > 0 and l <= s_sev):
                cikis = (max(o, s_sev) if yon < 0 else min(o, s_sev)); neden = "stop"
            elif t_sev is not None and ((yon < 0 and l <= t_sev) or (yon > 0 and h >= t_sev)):
                cikis = (min(o, t_sev) if yon < 0 else max(o, t_sev)); neden = "tp"
            elif i + 1 - t0 >= tut:
                cikis = c; neden = "sure"
            fon = -yon * fv[i + 1, k] * w * (1 if cikis is None else 0)   # funding: bar sonunda pozisyondaysa
            fiyat_son = cikis if cikis is not None else c
            pnl_bar += w * yon * (fiyat_son / p["son"] - 1) + fon
            p["w"] = w * (fiyat_son / p["son"])          # nominal (adet × fiyat) fiyatla kayar
            p["son"] = fiyat_son
            if cikis is not None:
                pnl_bar -= p["w"] * kayma; kapat.append(k)
                islem.append((C.index[i + 1], C.columns[k], yon, giris, cikis, neden, yon * (cikis / giris - 1), C.index[t0], p["w0"]))
        eq += pnl_bar
        for k in kapat:
            acik.pop(k); son_cikis[k] = i + 1
        # 2) yeni sinyaller (bar i+1 kapanışında; aynı bar içi çıkışlardan sonra)
        j = i + 1
        if len(acik) < nslot and (karar_saat is None or (C.index[j] + pd.Timedelta(hours=4)).hour == karar_saat):
            x = r24[j]
            m = np.isfinite(x) & (np.abs(x) >= esik) & (hac[j] >= hacim) & (j - ilk >= 180)
            ad = [k for k in np.flatnonzero(m) if k not in acik and j - son_cikis.get(k, -10**9) >= soguma]
            ad.sort(key=lambda k: -abs(x[k]))
            for k in ad[: nslot - len(acik)]:
                w = slot * eq
                acik[k] = {"yon": -1 if x[k] > 0 else 1, "giris": cv[j, k], "son": cv[j, k], "w": w, "t0": j, "w0": w}
                eq -= w * kayma
        # 3) özkaynak: eq nakit + açık pozisyonların birikmiş kârı zaten eq'ye işlendi (MTM)
        seri[j] = eq
        if eq <= 0.01:
            seri[j:] = eq; break
    s = pd.Series(seri[bas:], index=C.index[bas:])
    return s, pd.DataFrame(islem, columns=["zaman", "sembol", "yon", "giris", "cikis", "neden", "getiri", "giris_zaman", "tutar"])


def ozet(s, ad):
    d = (s.resample("1D").last().pct_change().dropna())
    def yil(x):
        if len(x) < 30: return np.nan
        e = (1 + x).prod(); return (e ** (365.25 / len(x)) - 1) * 100 if e > 0 else -100
    dd = ((s / s.cummax()) - 1).min() * 100
    donem = {"20-21": d[d.index < "2022"], "22-24": d[(d.index >= "2022") & (d.index < "2025")], "25-26": d[d.index >= "2025"],
             "26/07+": d[d.index >= "2026-07-10"]}
    print(f"{ad:28s} yıllık {yil(d):+8.1f} · dd {dd:6.1f} · en kötü gün {d.min()*100:6.1f} · " +
          " ".join(f"{k} {yil(v):+7.0f}" for k, v in donem.items()) +
          f" · 26/07+ toplam {((1 + donem['26/07+']).prod() - 1) * 100:+.0f}%")


if __name__ == "__main__":
    for ad, kw in (("taban: %30 · 20M · 1g · stop25 · soğuma 1g", {}),
                   ("soğuma yok", {"soguma": 0}), ("soğuma 3 g", {"soguma": 18}),
                   ("slot %10", {"slot": 0.10}), ("slot %10 · 3 g tut", {"slot": 0.10, "tut": 18}),
                   ("tutuş 3 g", {"tut": 18}), ("tutuş 7 g", {"tut": 42}),
                   ("1 g + TP %25", {"tp": 0.25}), ("3 g + TP %25", {"tut": 18, "tp": 0.25}),
                   ("hacim 70M · 1 g", {"hacim": 7e7}), ("eşik %50 · 1 g", {"esik": 0.5}),
                   ):
        s, isl = kos(**kw)
        ozet(s, ad)
        if ad.startswith("taban"):
            isl.to_pickle("/tmp/m644_islem.pkl")
            print("   işlem", len(isl), "· short", int((isl.yon < 0).sum()), "long", int((isl.yon > 0).sum()),
                  "· short ort", f"{isl[isl.yon < 0].getiri.mean()*100:+.2f}%", "long ort", f"{isl[isl.yon > 0].getiri.mean()*100:+.2f}%",
                  "· stop payı", f"{(isl.neden == 'stop').mean()*100:.0f}%")
