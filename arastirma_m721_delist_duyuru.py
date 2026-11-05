#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 721 — Vadeli (USDⓈ-M perpetual) delist duyurusu olayı. Ön kayıt KAR_HARITASI 721. Yalnız araştırma.
  python3 arastirma_m721_delist_duyuru.py indir   -> data_duyuru/delist.json (Binance cms 'Delisting' kataloğu, bütün sayfalar)
  python3 arastirma_m721_delist_duyuru.py analiz
"""
import json, os, re, sys, time, urllib.request, pickle
import numpy as np, pandas as pd
R = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(R, "data_duyuru")
API = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo={p}&pageSize=50"
KOM = 0.0005


def indir():
    os.makedirs(D, exist_ok=True); arts = []
    for p in range(1, 40):
        d = json.loads(urllib.request.urlopen(urllib.request.Request(API.format(p=p), headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
        cat = d.get("data", {}).get("catalogs") or []
        a = cat[0]["articles"] if cat else []
        if not a: break
        arts += a; time.sleep(0.5)
    json.dump(arts, open(os.path.join(D, "delist.json"), "w"))
    print("makale", len(arts))
    det = {}
    for a in arts:
        if not VADELI.search(a["title"]):
            continue
        u = f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={a['code']}"
        d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())["data"]
        det[a["code"]] = sorted(set(re.findall(r"\b[0-9A-Z]{2,25}USDT\b", (d.get("title") or "") + " " + (d.get("body") or ""))))
        time.sleep(0.4)
    json.dump(det, open(os.path.join(D, "delist_sembol.json"), "w"))
    print("vadeli makale", len(det), "· sembol", sum(len(v) for v in det.values()))


VADELI = re.compile(r"(futures|perpetual|usd[sⓈ]?-?m)", re.I)
HARIC = re.compile(r"(margin|spot trading pairs|options|copy trading|convert|earn|simple|loan|coin-m|cross margin|isolated)", re.I)


def olaylar(C):
    arts = json.load(open(os.path.join(D, "delist.json"))); det = json.load(open(os.path.join(D, "delist_sembol.json")))
    out = []
    for a in arts:
        t = a["title"]
        if a["code"] not in det:
            continue
        for sem in det[a["code"]]:
            if sem in C.columns:
                out.append(dict(zaman=pd.to_datetime(a["releaseDate"], unit="ms"), sembol=sem, baslik=t))
    E = pd.DataFrame(out).sort_values("zaman").drop_duplicates(["sembol"])     # sembol başına İLK duyuru
    return E


def funding(sem):
    y = os.path.join(R, "data_funding_uzun", f"{sem}.csv")
    if not os.path.exists(y): return None
    f = pd.read_csv(y); f["date"] = pd.to_datetime(f["date"], format="mixed")
    return f.set_index("date")["funding"]


def analiz():
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
    E = olaylar(C)
    print(f"vadeli delist olayı (panelde sembolü olan, sembol başına ilk duyuru): {len(E)}")
    rows = []
    for e in E.itertuples():
        c = C[e.sembol].dropna()
        sonra = c[c.index > e.zaman]
        if len(sonra) < 3:
            rows.append(dict(sembol=e.sembol, zaman=e.zaman, durum="giriş barı yok")); continue
        tg = sonra.index[1]; pg = sonra.iloc[1]                     # ikinci 4 sa kapanış
        bit = min(tg + pd.Timedelta(days=7), c.index[-1])
        tc = c[c.index <= bit].index[-1]; pc = c.loc[tc]
        fiy = -(pc / pg - 1)
        f = funding(e.sembol); fon = 0.0
        if f is not None:
            fon = float(f[(f.index > tg) & (f.index <= tc)].sum())      # short: pozitif funding ALIR, negatif ÖDER
        net = fiy + fon - 2 * KOM
        rows.append(dict(sembol=e.sembol, zaman=e.zaman, giris=tg, cikis=tc, gun=(tc - tg).total_seconds() / 86400, fiyat=fiy, funding=fon, net=net, durum="ok"))
    T = pd.DataFrame(rows); ok = T[T.durum == "ok"].copy()
    print(f"ölçülen olay {len(ok)} · giriş barı yok {int((T.durum != 'ok').sum())}")
    print(ok[["sembol", "zaman", "gun", "fiyat", "funding", "net"]].assign(fiyat=lambda d: d.fiyat * 100, funding=lambda d: d.funding * 100, net=lambda d: d.net * 100).round(2).to_string(index=False))
    def ozet(x, ad):
        g = x.groupby(x.giris.dt.date).net.mean()                     # gün kümelenmesi
        t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
        print(f"  {ad}: olay {len(x)} · gün {len(g)} · ort net %{x.net.mean()*100:.2f} (medyan %{x.net.median()*100:.2f}) · fiyat %{x.fiyat.mean()*100:.2f} · "
              f"funding %{x.funding.mean()*100:.2f} · t(gün) {t:.2f} · kazanan %{(x.net > 0).mean()*100:.0f}")
        return x.net.mean(), t
    print("\nSHORT (ön kayıtlı yön):")
    m, t = ozet(ok, "tümü")
    m1, _ = ozet(ok[ok.giris < "2025-01-01"], "2020-2024")
    m2, _ = ozet(ok[ok.giris >= "2025-01-01"], "2025+")
    en = ok.sort_values("net", ascending=False)
    m3 = en.iloc[3:].net.mean()
    print(f"  en iyi 3 olay ({', '.join(en.sembol.iloc[:3])}) çıkınca ort %{m3*100:.2f}")
    s = [m > 0, t >= 2, m1 > 0, m2 > 0, m3 > 0]
    print(f"\nÖN KAYIT: ort>0 {'Y' if s[0] else 'X'} · t≥2 {'Y' if s[1] else 'X'} · 2020-24>0 {'Y' if s[2] else 'X'} · 2025+>0 {'Y' if s[3] else 'X'} · "
          f"en iyi 3 hariç>0 {'Y' if s[4] else 'X'} → {'PROMISING' if all(s) else 'RED'}")
    L = ok.assign(net=-ok.fiyat - ok.funding - 2 * KOM)
    print(f"bilgi — LONG yönü ort net %{L.net.mean()*100:.2f} (medyan %{L.net.median()*100:.2f})")


if __name__ == "__main__":
    indir() if sys.argv[1] == "indir" else analiz()
