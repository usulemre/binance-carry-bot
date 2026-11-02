#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 717 — V3 kuralının Hyperliquid funding'iyle bağımsız sınaması (ön kayıt KAR_HARITASI 717). Yalnız araştırma.
  python3 arastirma_m717_hyperliquid.py indir        -> data_hl_funding/<BINANCE_SEMBOL>.csv (date, funding, interval_h=1)
  python3 arastirma_m717_hyperliquid.py panel 60/96  -> /tmp/skh_bar60.pkl (HL), /tmp/sk_bar60_hlozel.pkl (V3H)
  python3 arastirma_m717_hyperliquid.py kos          -> /tmp/m717h/M357_EK_V3H_2000_{0,1}.pkl (tek işçi)
  python3 arastirma_m717_hyperliquid.py analiz
"""
import json, os, sys, time, pickle, subprocess, urllib.request, urllib.error
import numpy as np, pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(R, "data_hl_funding")
API = "https://api.hyperliquid.xyz/info"
OUT = "/tmp/m717h"


def post(b, deneme=6):
    for i in range(deneme):
        try:
            r = urllib.request.Request(API, data=json.dumps(b).encode(), headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(r, timeout=30).read())
        except urllib.error.HTTPError as e:
            time.sleep((10 if e.code == 429 else 2) * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"HL isteği başarısız: {b}")


def eslesme(hl: list, binance: set) -> dict:
    out = {}
    for a in hl:
        aday = [f"{a}USDT"]
        if a.startswith("k") and len(a) > 1 and a[1].isupper():
            aday = [f"1000{a[1:]}USDT", f"{a[1:]}USDT"]
        for c in aday:
            if c in binance:
                out[a] = c; break
    return out


def indir():
    os.makedirs(D, exist_ok=True)
    uni = post({"type": "meta"})["universe"]
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
    es = eslesme([u["name"] for u in uni], set(C.columns))
    eks = [u["name"] for u in uni if u["name"] not in es]
    print(f"HL meta {len(uni)} (delist işaretli {sum(1 for u in uni if u.get('isDelisted'))}) · Binance'le eşleşen {len(es)} · eşleşmeyen {len(eks)}: {eks}", flush=True)
    bas0 = int(pd.Timestamp("2023-04-01").timestamp() * 1000); bit = int(pd.Timestamp("2026-11-01").timestamp() * 1000)
    for n, (a, s) in enumerate(sorted(es.items()), 1):
        yol = os.path.join(D, f"{s}.csv")
        if os.path.exists(yol):
            continue
        rows, t = [], bas0
        while t < bit:
            d = post({"type": "fundingHistory", "coin": a, "startTime": t, "endTime": bit})
            if not d:
                break
            rows += d
            son = max(int(x["time"]) for x in d)
            if son <= t or len(d) < 2:
                break
            t = son + 1
            time.sleep(0.25)
        if rows:
            f = pd.DataFrame(rows); f["date"] = pd.to_datetime(f["time"].astype("int64"), unit="ms")
            f["funding"] = f["fundingRate"].astype(float); f["interval_h"] = 1
            f = f[["date", "funding", "interval_h"]].sort_values("date").drop_duplicates("date")
            f.to_csv(yol + ".tmp", index=False); os.replace(yol + ".tmp", yol)
        print(n, a, s, len(rows), flush=True)
    print("İNDİRME BİTTİ", flush=True)


def panel(pen: float):
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]; kol = list(C.columns)
    bar_h = C.index.values.astype("datetime64[s]").astype(np.int64) / 3600.0
    out = np.full((len(bar_h), len(kol)), np.nan)
    for j, s in enumerate(kol):
        y = os.path.join(D, f"{s}.csv")
        if not os.path.exists(y):
            continue
        f = pd.read_csv(y, parse_dates=["date"]); f["date"] = f["date"].dt.floor("h")
        f = f.drop_duplicates("date").sort_values("date")
        if len(f) < 3:
            continue
        t = f["date"].values.astype("datetime64[s]").astype(np.int64) / 3600.0
        r = (f["funding"] * 24.0 / f["interval_h"].clip(lower=1)).values.astype(float)   # 676 ile aynı: günlük eşdeğer, ödeme başına
        cs = np.concatenate([[0.0], np.cumsum(r)])
        hi = np.searchsorted(t, bar_h, side="right"); lo = np.searchsorted(t, bar_h - pen, side="right")
        ok = (hi > lo) & (bar_h >= t[0] + pen)
        out[ok, j] = (cs[hi[ok]] - cs[lo[ok]]) / (hi[ok] - lo[ok])
    H = pd.DataFrame(out, index=C.index, columns=kol).where(C.notna())
    ad = f"bar{int(pen)}"
    B = pickle.load(open(f"/tmp/sk_{ad}.pkl", "rb"))
    pickle.dump(H, open(f"/tmp/skh_{ad}.pkl", "wb"))
    var = H.notna()
    ozel = B.where(~var, B + 0.5 * (B - H))
    pickle.dump(ozel, open(f"/tmp/sk_{ad}_hlozel.pkl", "wb"))
    kor = []
    for i in range(0, len(C), 30):
        a, b = B.iloc[i], H.iloc[i]; m = a.notna() & b.notna()
        if m.sum() > 30:
            kor.append(a[m].rank().corr(b[m].rank()))
    for a, z in [("2023-06-01", "2025-05-31"), ("2025-06-01", "2026-09-30"), ("2026-10-01", "2026-10-31")]:
        m = (C.index >= a) & (C.index <= z)
        hb = (var.values[m] & B.notna().values[m]).sum(); tb = B.notna().values[m].sum()
        print(f"{ad} {a}..{z}: HL hücre {hb} / Binance sinyal hücresi {tb} (%{100*hb/max(tb,1):.1f})")
    print(f"{ad}: kesitsel sıra kor. (B, HL) ort {np.nanmean(kor):+.3f} · ozel ≠ B hücre {int(((ozel != B) & var).values.sum())}")


def kos():
    import arastirma_m676_mexc_kollar as K, arastirma_m346_prim as M
    os.makedirs(OUT, exist_ok=True)
    kol = {"SK_DOSYA": "/tmp/sk_bar60_hlozel.pkl", "SK_DOSYA_S": "/tmp/sk_bar96_hlozel.pkl"}
    for h in (0, 1):
        out = f"{OUT}/M357_EK_V3H_2000_{h}.pkl"
        if os.path.exists(out):
            print(h, "var"); continue
        env = dict(os.environ, **{**M.TABAN, **K.T4, **kol}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out + ".tmp")
        with open(out.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, "g33.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(out + ".tmp")
        if ok:
            os.replace(out + ".tmp", out)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m346_prim as M
    if not all(os.path.exists(f"{OUT}/M357_EK_V3H_2000_{h}.pkl") for h in (0, 1)):
        print("EKSİK KOŞU — analiz yapılmaz"); return
    M.CIKTI = OUT; v = sum(M.gunluk(f"M357_EK_V3H_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = "/tmp/m_ekim"; b = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    v, b = v.align(b, join="inner")
    H = pickle.load(open("/tmp/skh_bar60.pkl", "rb")); ilk = H.notna().any(axis=1).idxmax()
    d = (v - b).abs(); fark0 = d[d > 0].index.min()
    print(f"parite: HL sinyalinin ilk barı {ilk} · seriler ilk ayrıştığı gün {fark0} · ondan önce maks fark {d[:fark0 - pd.Timedelta(days=1)].max() if fark0 is not pd.NaT else 0}")
    f = lambda s: ((1 + s).prod() - 1) * 100
    sh = lambda s: s.mean() / s.std() * np.sqrt(365.25)
    rows = {}
    for ad, a, z in [("BİRİNCİL 2023-06..2025-05", "2023-06-01", "2025-05-31"), ("2023-H2", "2023-06-01", "2023-12-31"),
                     ("2024", "2024-01-01", "2024-12-31"), ("2025-H1", "2025-01-01", "2025-05-31"),
                     ("676 penceresi 2025-06..2026-09", "2025-06-01", "2026-09-30"), ("2026-10 (677 OOS)", "2026-10-01", "2026-10-31")]:
        x, y = v[a:z], b[a:z]
        e1, e2 = (1 + x).cumprod(), (1 + y).cumprod()
        rows[ad] = {"V3H getiri %": f(x), "taban getiri %": f(y), "V3H Sh": sh(x), "taban Sh": sh(y), "V3H en kötü gün %": x.min() * 100,
                    "taban en kötü gün %": y.min() * 100, "V3H maks DD %": ((e1 / e1.cummax()) - 1).min() * 100,
                    "taban maks DD %": ((e2 / e2.cummax()) - 1).min() * 100, "kor": x.corr(y)}
    T = pd.DataFrame(rows).T
    pd.set_option("display.width", 220); print(T.round(2).to_string())
    p = T.loc["BİRİNCİL 2023-06..2025-05"]
    s1, s2, s3 = p["V3H getiri %"] >= p["taban getiri %"], p["V3H Sh"] >= p["taban Sh"], p["V3H en kötü gün %"] >= p["taban en kötü gün %"]
    print(f"\nÖN KAYIT ölçütü (birincil pencere): getiri {'Y' if s1 else 'X'} · Sharpe {'Y' if s2 else 'X'} · en kötü gün {'Y' if s3 else 'X'} → "
          f"{'V3 DESTEKLENİR (bağımsız)' if (s1 and s2 and s3) else 'V3 DESTEKLENMEZ'}")
    m = (v - b)["2023-06-01":"2026-10-31"].resample("ME").apply(lambda s: s.sum() * 100)
    print("aylık fark (basit, puan):", " ".join(f"{i:%y-%m}:{k:+.1f}" for i, k in m.items()))


if __name__ == "__main__":
    k = sys.argv[1]
    if k == "indir": indir()
    elif k == "panel": panel(float(sys.argv[2]))
    elif k == "kos": kos()
    else: analiz()
