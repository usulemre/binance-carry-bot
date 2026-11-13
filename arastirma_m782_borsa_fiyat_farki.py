#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 782 — borsalar arası FİYAT farkı (Binance ↔ OKX perp, 5 dk). Ön kayıt KAR_HARITASI 782. Yalnız araştırma (anahtar yok, emir yok).
  python3 arastirma_m782_borsa_fiyat_farki.py indir | analiz      (coin listesi /tmp/m782/coinler.json)"""
import json, os, sys, time, io, zipfile, urllib.request
import numpy as np, pandas as pd
OUT = "/tmp/m782"; BAS, BIT = "2026-10-12", "2026-11-11"


def _al(u, ham=False):
    for i in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "m782"}), timeout=30).read()
            return r if ham else json.loads(r)
        except Exception as e:
            if "404" in str(e): return None
            time.sleep(1.5 * (i + 1))
    return None


def indir():
    for s in json.load(open(f"{OUT}/coinler.json")):
        fb = f"{OUT}/b_{s}.pkl"
        if not os.path.exists(fb):
            fr = []
            for d in pd.date_range(BAS, BIT):
                z = _al(f"https://data.binance.vision/data/futures/um/daily/klines/{s}USDT/5m/{s}USDT-5m-{d:%Y-%m-%d}.zip", ham=True)
                if z is None: continue
                zz = zipfile.ZipFile(io.BytesIO(z)); x = pd.read_csv(zz.open(zz.namelist()[0]), header=None)
                if not str(x.iloc[0, 0]).isdigit(): x = x.iloc[1:]
                fr.append(x.iloc[:, [0, 4, 7]].astype(float))
            if fr:
                x = pd.concat(fr); pd.Series(x[4].values, index=pd.to_datetime(x[0], unit="ms")).to_pickle(fb)
                pd.Series(x[7].values, index=pd.to_datetime(x[0], unit="ms")).to_pickle(f"{OUT}/bv_{s}.pkl")
        fo = f"{OUT}/o_{s}.pkl"
        if not os.path.exists(fo):
            t0 = int(pd.Timestamp(BAS).timestamp() * 1000); t = int((pd.Timestamp(BIT) + pd.Timedelta(days=1)).timestamp() * 1000); rows = []
            while t > t0:
                d = _al(f"https://www.okx.com/api/v5/market/history-candles?instId={s}-USDT-SWAP&bar=5m&limit=100&after={t}")
                d = (d or {}).get("data") or []
                if not d: break
                rows += [(int(r[0]), float(r[4])) for r in d]; t = min(int(r[0]) for r in d); time.sleep(0.11)
            if rows:
                x = pd.Series({pd.Timestamp(a, unit="ms"): b for a, b in rows}).sort_index(); x[BAS:].to_pickle(fo)
        print(s, os.path.exists(fb), os.path.exists(fo), flush=True)


def islemler(d, X, tut=288):
    """d: sapma serisi (5 dk). Dönen: [(giriş i, çıkış i, yön, brüt bp)] — giriş / çıkış sinyalden sonraki bar."""
    v = d.values; out = []; i = 288; n = len(v)
    while i < n - 2:
        if np.isfinite(v[i]) and abs(v[i]) >= X and np.isfinite(v[i + 1]):
            yon = -np.sign(v[i]); g = i + 1; j = g
            while j < n - 2 and j - g < tut and not (np.isfinite(v[j]) and abs(v[j]) <= X / 4): j += 1
            c = j + 1
            if not np.isfinite(v[c]): i = c + 1; continue
            out.append((g, c, yon, yon * (v[c] - v[g]) * 1e4)); i = c + 1      # yon=+1: OKX ucuz → OKX long / Binance short; kazanç = d'nin yükselmesi
        else:
            i += 1
    return out


def analiz():
    S = [s for s in json.load(open(f"{OUT}/coinler.json")) if os.path.exists(f"{OUT}/b_{s}.pkl") and os.path.exists(f"{OUT}/o_{s}.pkl")]
    ix = pd.date_range(BAS, pd.Timestamp(BIT) + pd.Timedelta(hours=23, minutes=55), freq="5min"); D = {}; satir = []
    for s in S:
        b = pd.read_pickle(f"{OUT}/b_{s}.pkl").reindex(ix); o = pd.read_pickle(f"{OUT}/o_{s}.pkl").reindex(ix)
        sp = np.log(o / b); d = sp - sp.rolling(288, min_periods=144).median().shift(1); D[s] = d
        hac = pd.read_pickle(f"{OUT}/bv_{s}.pkl").sum() / 30 / 1e6
        satir.append(dict(coin=s, hacim_mUSD=round(hac), baz_med_bp=round(sp.median() * 1e4, 1), sapma_sd_bp=round(d.std() * 1e4, 1),
                          p99_bp=round(d.abs().quantile(.99) * 1e4, 1), maks_bp=round(d.abs().max() * 1e4)))
    T = pd.DataFrame(satir).set_index("coin"); pd.set_option("display.width", 200)
    print(f"{len(S)} coin · |sapma| medyan sd {T.sapma_sd_bp.median():.1f} bp · %99 medyan {T.p99_bp.median():.1f} bp")
    print(T.sort_values("p99_bp", ascending=False).head(12).to_string())
    gun = 30 - 1
    for X in (0.0030, 0.0060):
        tum = []
        for s in S:
            tum += [(g, c, s, br) for g, c, y, br in islemler(D[s], X)]
        tum.sort(); acik = []; al = []
        for g, c, s, br in tum:                       # 10 eşzamanlı yer
            acik = [e for e in acik if e > g]
            if len(acik) >= 10: continue
            acik.append(c); al.append((s, br, (c - g) * 5 / 60))
        if not al: print(f"\nX = {X * 1e4:.0f} bp: işlem yok"); continue
        A = pd.DataFrame(al, columns=["coin", "brut", "saat"])
        print(f"\nX = {X * 1e4:.0f} bp: sinyal {len(tum)} · alınan {len(A)} · coin başına en çok {A.coin.value_counts().head(4).to_dict()} · brüt ort {A.brut.mean():.1f} bp "
              f"(medyan {A.brut.median():.1f}) · tutuş medyan {A.saat.median():.1f} sa · brütü > 0 %{(A.brut > 0).mean() * 100:.0f}")
        for ad, m in (("gerçekçi 20 bp", 20), ("iyimser 8 bp", 8)):
            net = A.brut - m
            yil = net.sum() / 1e4 * 0.05 * 365 / gun * 100          # bacak = sermayenin %5'i; sapma kazancı tek bacak nominali üzerinden
            print(f"   {ad}: işlem başı net {net.mean():+.1f} bp · kazanan %{(net > 0).mean() * 100:.0f} · sermayeye yıllık {yil:+.1f}%  → {'RED' if (m == 20 and yil < 20) else ''}")
        en = A.groupby("coin").brut.sum().sort_values(ascending=False)
        print("   brüt toplamın coinlere dağılımı (bp):", en.head(5).round(0).to_dict(), "… ilk 3 coin payı %{:.0f}".format(en.head(3).sum() / max(en.sum(), 1e-9) * 100))


if __name__ == "__main__":
    indir() if sys.argv[1] == "indir" else analiz()
