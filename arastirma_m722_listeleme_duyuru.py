#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 722 — Spot listeleme duyurusu (perp önceden işlem görüyorken) LONG. Ön kayıt KAR_HARITASI 722. Yalnız araştırma.
  python3 arastirma_m722_listeleme_duyuru.py indir | analiz"""
import json, os, re, sys, time, urllib.request, pickle
import numpy as np, pandas as pd
R = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(R, "data_duyuru")
API = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo={p}&pageSize=50"
KOM = 0.0005


def indir():
    os.makedirs(D, exist_ok=True); arts = []
    for p in range(1, 80):
        d = json.loads(urllib.request.urlopen(urllib.request.Request(API.format(p=p), headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
        cat = d.get("data", {}).get("catalogs") or []
        a = cat[0]["articles"] if cat else []
        if not a: break
        arts += a; time.sleep(0.4)
    json.dump(arts, open(os.path.join(D, "listeleme.json"), "w"))
    t = pd.to_datetime([a["releaseDate"] for a in arts], unit="ms")
    print("makale", len(arts), t.min(), t.max())


def olaylar(C):
    from tradfi_liste import TRADFI
    arts = json.load(open(os.path.join(D, "listeleme.json")))
    spot = json.load(open(os.path.join(R, "data_spot_ilk_gun.json")))
    out = []
    for a in arts:
        t = a["title"]
        if not t.startswith("Binance Will List"):
            continue
        for s in re.findall(r"\(([0-9A-Z]{2,15})\)", t):
            sem = f"{s}USDT"
            if sem not in C.columns or sem in TRADFI or not spot.get(sem):
                continue
            z = pd.to_datetime(a["releaseDate"], unit="ms")
            ilk = C[sem].first_valid_index()
            if ilk is None or ilk > z - pd.Timedelta(days=14):
                continue
            out.append(dict(zaman=z, sembol=sem, spot=pd.Timestamp(spot[sem]) + pd.Timedelta(hours=4), baslik=t))
    return pd.DataFrame(out).sort_values("zaman").drop_duplicates(["sembol"])


def funding(sem):
    y = os.path.join(R, "data_funding_uzun", f"{sem}.csv")
    if not os.path.exists(y): return None
    f = pd.read_csv(y); f["date"] = pd.to_datetime(f["date"], format="mixed")
    return f.set_index("date")["funding"]


def analiz():
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
    E = olaylar(C); rows = []
    print(f"aday olay: {len(E)}")
    for e in E.itertuples():
        c = C[e.sembol].dropna(); sonra = c[c.index > e.zaman]
        if len(sonra) < 3: continue
        tg = sonra.index[1]; pg = sonra.iloc[1]
        bit = min(e.spot, tg + pd.Timedelta(days=7), c.index[-1])
        if bit <= tg:
            continue                                     # spot girişten önce açıldı → sayılmaz
        tc = c[c.index <= bit].index[-1]; pc = c.loc[tc]
        fiy = pc / pg - 1; f = funding(e.sembol)
        fon = -float(f[(f.index > tg) & (f.index <= tc)].sum()) if f is not None else 0.0   # long: pozitif funding ÖDER
        rows.append(dict(sembol=e.sembol, duyuru=e.zaman, giris=tg, cikis=tc, saat=(tc - tg).total_seconds() / 3600, fiyat=fiy, funding=fon, net=fiy + fon - 2 * KOM))
    ok = pd.DataFrame(rows)
    if ok.empty:
        print("ölçülen olay yok"); return
    print(f"ölçülen olay {len(ok)}")
    print(ok.assign(fiyat=ok.fiyat * 100, funding=ok.funding * 100, net=ok.net * 100).round(2)[["sembol", "duyuru", "saat", "fiyat", "funding", "net"]].to_string(index=False))
    def ozet(x, ad):
        g = x.groupby(x.giris.dt.date).net.mean()
        t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
        print(f"  {ad}: olay {len(x)} · gün {len(g)} · ort net %{x.net.mean()*100:.2f} (medyan %{x.net.median()*100:.2f}) · fiyat %{x.fiyat.mean()*100:.2f} · "
              f"funding %{x.funding.mean()*100:.2f} · t(gün) {t:.2f} · kazanan %{(x.net > 0).mean()*100:.0f} · tutma medyan {x.saat.median():.0f} sa")
        return x.net.mean(), t
    print("\nLONG (ön kayıtlı yön):")
    m, t = ozet(ok, "tümü"); m1, _ = ozet(ok[ok.giris < "2025-01-01"], "2022-2024"); m2, _ = ozet(ok[ok.giris >= "2025-01-01"], "2025+")
    en = ok.sort_values("net", ascending=False); m3 = en.iloc[3:].net.mean()
    print(f"  en iyi 3 ({', '.join(en.sembol.iloc[:3])}) hariç ort %{m3*100:.2f} · en kötü 5: " + ", ".join(f"{r.sembol} %{r.net*100:.1f}" for r in en.tail(5).itertuples()))
    s = [m > 0, (t or 0) >= 2, m1 > 0, m2 > 0, m3 > 0]
    print(f"\nÖN KAYIT: ort>0 {'Y' if s[0] else 'X'} · t≥2 {'Y' if s[1] else 'X'} · 2022-24>0 {'Y' if s[2] else 'X'} · 2025+>0 {'Y' if s[3] else 'X'} · "
          f"en iyi 3 hariç>0 {'Y' if s[4] else 'X'} → {'PROMISING' if all(s) else 'RED'}")
    S = ok.assign(net=-ok.fiyat - ok.funding - 2 * KOM)
    print(f"bilgi — SHORT yönü ort net %{S.net.mean()*100:.2f} (medyan %{S.net.median()*100:.2f})")


if __name__ == "__main__":
    indir() if sys.argv[1] == "indir" else analiz()
