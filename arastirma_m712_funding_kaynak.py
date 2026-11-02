#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 712 — FUNDING ALPHA KAYNAĞI VE YOĞUNLAŞMA (yalnız ölçüm; strateji / parametre değişmez).
Kullanım:
  python3 arastirma_m712_funding_kaynak.py kos      # motor karşı-olguları (tek işçi, seri; /tmp/m712)
  python3 arastirma_m712_funding_kaynak.py analiz   # A-D analizleri (madde 711 defteri /tmp/m711 + motor koşuları)
"""
import os, sys, pickle, subprocess, glob
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arastirma_m346_prim as M
import izleme_ekim_oos as I
R = os.path.dirname(os.path.abspath(__file__))
GK = "/tmp/m711"; OUT = "/tmp/m712"; SON = "2026-10-31"
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}


def defter():
    G = pd.concat([pd.read_pickle(f"{GK}/gk_{h}.pkl").assign(hiza=h) for h in (0, 1)])
    G["gun"] = pd.to_datetime(G.gun); G = G[G.gun <= SON].copy()
    for c in ["fiyat_top", "funding", "tp", "stop", "komisyon", "fiyat_long_top"]:
        G[c] = G[c] / 2 * 100                      # iki hiza ortalaması, % puan
    G["fiyat"] = G.fiyat_top - G.tp - G.stop       # TP / stop hariç tutuş fiyatı
    G["net"] = G.fiyat_top + G.funding - G.komisyon
    G["yon"] = np.where(G.ort_poz > 0, "L", "S")
    G["sgun"] = G.ort_poz.abs() * G.bar / 6 / 2    # sermaye-gün (iki hiza ortalaması)
    G["yil"] = G.gun.dt.year
    return G


def funding_sirasi(G):
    return G.groupby("sembol").funding.sum().sort_values(ascending=False)


def senaryolar(G):
    import arastirma_m695_dayaniklilik as T
    top = list(funding_sirasi(G).index)
    S = {f"C_FUND{n}": ",".join(M.D8 + top[:n]) for n in (3, 5, 10)}
    fv = T.listeleme(); b0 = pd.Timestamp("2025-01-01")
    from tradfi_liste import TRADFI
    sec = sorted(s for s, t in fv.items() if b0 <= t < b0 + pd.Timedelta(days=180) and s not in TRADFI and s not in M.D8)
    S["C_DUR180"] = ",".join(M.D8 + sec)
    return S, top


def kos():
    import arastirma_m690_kar_kaynagi as A
    A.kopya(); os.makedirs(OUT, exist_ok=True)
    S, top = senaryolar(defter())
    print("funding ilk 10:", top[:10], flush=True)
    for ad, haric in S.items():
        for h in (0, 1):
            e = f"{OUT}/{ad}_{h}.pkl"
            if os.path.exists(e):
                continue
            env = dict(os.environ, **ENV, SEMBOL_HARIC=haric, FAZ_KAY=str(h), E_CIKTI=e + ".tmp",
                       GUNLUK_KATKI=f"{OUT}/{ad}_gk_{h}.pkl", GK_BAS="2019-01-01")
            with open(f"{OUT}/{ad}_{h}.txt", "w") as f:
                r = subprocess.run([sys.executable, "/tmp/g33_m690.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp") and os.path.exists(f"{OUT}/{ad}_gk_{h}.pkl")
            if ok:
                os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["kos"]:
        kos()


# ============================================================ ANALİZ
def panel():
    P = pickle.load(open("/tmp/panel.pkl", "rb"))
    yas = (P["YAS"].resample("D").last() / 6)
    son = P["C"].apply(lambda s: s.last_valid_index())
    return P, yas, son


def yas_ekle(G, yas):
    y = yas.stack().rename("yas_g").reset_index(); y.columns = ["gun", "sembol", "yas_g"]
    G = G.merge(y, on=["gun", "sembol"], how="left")
    G["yas_grp"] = pd.cut(G.yas_g, [-1, 180, 365, 730, 1e9], labels=["60-180 g", "181-365 g", "1-2 yıl", "> 2 yıl"])
    return G


def pay_tablosu(s):
    s = s.sort_values(ascending=False); t = s.sum()
    return {f"ilk {n}": s.head(n).sum() / t * 100 for n in (3, 5, 10, 20)} | {"toplam": t, "coin": int((s != 0).sum())}


def A_dagilim(G, son):
    print("\n==================== A) FUNDING GELİRİNİN COİN DAĞILIMI (% puan, 1,0x, iki hiza ort.)")
    for etiket, g in [("2020-26", G), ("2025", G[G.yil == 2025]), ("2026 (Eki dahil)", G[G.yil == 2026])]:
        L = g[g.yon == "L"].groupby("sembol").funding.sum(); S = g[g.yon == "S"].groupby("sembol").funding.sum()
        T = g.groupby("sembol").funding.sum()
        print(f"\n--- {etiket}: long funding {L.sum():.1f} · short funding {S.sum():.1f} · toplam {T.sum():.1f}")
        for ad, s in [("long", L), ("toplam", T)]:
            p = pay_tablosu(s)
            print(f"  {ad:6s} pay: " + " · ".join(f"{k} %{v:.0f}" for k, v in p.items() if k.startswith("ilk")) + f"  ({p['coin']} coin)")
        print("  en çok funding (toplam):", ", ".join(f"{k} {v:.1f}" for k, v in T.sort_values(ascending=False).head(10).items()))
        print("  en çok funding ÖDEYEN:", ", ".join(f"{k} {v:.1f}" for k, v in T.sort_values().head(5).items()))
        yg = g.groupby("yas_grp", observed=False).agg(funding=("funding", "sum"), sgun=("sgun", "sum"), net=("net", "sum"))
        yg["pay %"] = yg.funding / yg.funding.sum() * 100; yg["maruz %"] = yg.sgun / yg.sgun.sum() * 100
        yg["funding / sermaye-yıl %"] = yg.funding / yg.sgun * 365
        print("  yaş grubu:\n" + yg.round(1).to_string().replace("\n", "\n    "))
        dl = [s for s in T.index if pd.notna(son.get(s)) and son[s] < pd.Timestamp("2026-10-01")]
        print(f"  delist edilmiş {len(dl)} coin: funding {T[dl].sum():.1f}, net {g[g.sembol.isin(dl)].net.sum():.1f}")
    # yıllar: genç pay
    y = G.assign(genc=G.yas_g <= 365).groupby(["yil", "genc"]).funding.sum().unstack()
    y["genç pay %"] = y[True] / (y[True] + y[False]) * 100
    print("\n  yıl bazında funding: genç (≤365 g) / eski\n" + y.round(1).to_string())
    yt = {yl: pay_tablosu(g.groupby("sembol").funding.sum()) for yl, g in G.groupby("yil")}
    print("\n  yıl bazında toplam funding ilk 3 / 10 payı: " + " · ".join(f"{k}: %{v['ilk 3']:.0f} / %{v['ilk 10']:.0f}" for k, v in yt.items()))


def funding_paneli(semboller):
    """Ham ödeme kayıtlarından günlük ortalama YILLIK funding (%): oran × 24 / aralık × 365 × 100 (gerçek ödeme zaman damgası)."""
    d = {}
    for s in semboller:
        y = os.path.join(R, "data_funding_uzun", f"{s}.csv")
        if not os.path.exists(y):
            continue
        f = pd.read_csv(y); f["date"] = pd.to_datetime(f["date"], format="mixed")
        ara = f["interval_h"] if "interval_h" in f else pd.Series(np.nan, index=f.index)
        fark = f["date"].diff().dt.total_seconds().div(3600).round()          # aralık yazılmamışsa ödemeler arası süre
        ara = ara.fillna(fark.where(fark.isin([1, 2, 4, 8]))).fillna(8)
        f["yil"] = f.funding * 24 / ara * 365 * 100
        d[s] = f.set_index("date").yil.resample("D").mean()
    return pd.DataFrame(d)


def pozisyonlar(G):
    """Aynı hiza / sembol / yönde kesintisiz günler = bir pozisyon (günlük çözünürlük)."""
    G = G.sort_values(["hiza", "sembol", "gun"]).copy()
    yeni = (G.sembol != G.sembol.shift()) | (G.hiza != G.hiza.shift()) | (G.yon != G.yon.shift()) | \
           ((G.gun - G.gun.shift()).dt.days != 1)
    G["pid"] = yeni.cumsum()
    P = G.groupby("pid").agg(hiza=("hiza", "first"), sembol=("sembol", "first"), yon=("yon", "first"), giris=("gun", "first"),
                             cikis=("gun", "last"), gun_say=("gun", "size"), sgun=("sgun", "sum"), funding=("funding", "sum"),
                             fiyat=("fiyat", "sum"), tp=("tp", "sum"), stop=("stop", "sum"), kom=("komisyon", "sum"),
                             net=("net", "sum"), yas_g=("yas_g", "first"))
    P["yil"] = P.giris.dt.year
    return P


def B_sureklilik(G, P, FP):
    print("\n==================== B) FUNDING SÜREKLİLİĞİ (pozisyon = kesintisiz gün; giriş oranı = giriş gününden ÖNCEKİ günün ödemeleri)")
    med = FP.median(axis=1)
    onc = FP.shift(1); medo = med.shift(1)
    P["giris_oran"] = [onc.at[g, s] if s in onc.columns and g in onc.index else np.nan for g, s in zip(P.giris, P.sembol)]
    P["evren_med"] = medo.reindex(P.giris).values
    sgn = np.where(P.yon == "L", 1, -1)
    P["beklenen_carry"] = -sgn * P.giris_oran                       # yıllık %, pozitif = pozisyon funding ALIR
    P["teorik_funding"] = P.beklenen_carry / 365 * P.sgun            # giriş oranı sabit kalsaydı
    v = P.dropna(subset=["giris_oran"])
    print(f"  pozisyon: {len(P)} (giriş oranı bulunan {len(v)}); long {int((P.yon=='L').sum())} · short {int((P.yon=='S').sum())}")
    print(f"  gerçekleşen funding {P.funding.sum():.1f} · teorik (giriş oranı × süre) {v.teorik_funding.sum():.1f} puan "
          f"(aynı pozisyonlarda gerçekleşen {v.funding.sum():.1f})")
    for yon in ("L", "S"):
        x = v[v.yon == yon].copy()
        x["q"] = pd.qcut(x.beklenen_carry.rank(method="first"), 5, labels=["Q1 en az", "Q2", "Q3", "Q4", "Q5 en uç"])
        t = x.groupby("q", observed=True).agg(adet=("net", "size"), giris_carry_med=("beklenen_carry", "median"), gun_med=("gun_say", "median"),
                                              sgun=("sgun", "sum"), funding=("funding", "sum"), teorik=("teorik_funding", "sum"),
                                              fiyat=("fiyat", "sum"), tp=("tp", "sum"), net=("net", "sum"))
        for c in ["funding", "fiyat", "tp", "net"]:
            t[c + "/sy"] = t[c] / t.sgun * 365
        t["zarar pay %"] = x.groupby("q", observed=True).net.apply(lambda n: (n < 0).mean() * 100)
        print(f"\n  {('LONG' if yon == 'L' else 'SHORT')} — giriş carry beşte birlikleri (/sy = sermaye-yıl başına % puan)")
        print("  " + t[["adet", "giris_carry_med", "gun_med", "funding", "teorik", "fiyat", "tp", "net", "funding/sy", "fiyat/sy", "tp/sy", "net/sy", "zarar pay %"]]
              .round(1).to_string().replace("\n", "\n  "))
        yy = x.groupby(["yil", "q"], observed=True).apply(lambda g: g.net.sum() / g.sgun.sum() * 365).unstack()
        yy["Q5-Q1"] = yy["Q5 en uç"] - yy["Q1 en az"]
        print("  yıl bazında net/sy:\n  " + yy.round(0).to_string().replace("\n", "\n  "))
    # oran yolu: tutulan long'larda coin - evren medyanı farkı, girişe göre
    print("\n  Giriş sonrası funding farkı (coin − evren medyanı; giriş farkına oranla, medyan) — long, giriş carry > 0")
    L = v[(v.yon == "L") & (v.beklenen_carry > 0)]
    fark = FP.sub(med, axis=0)
    satir = {}
    for t in (0, 1, 3, 7, 14, 30, 60):
        r = []
        for g, s, in zip(L.giris, L.sembol):
            gt = g - pd.Timedelta(days=1) + pd.Timedelta(days=t)
            if s in fark.columns and gt in fark.index and (g - pd.Timedelta(days=1)) in fark.index:
                f0 = fark.at[g - pd.Timedelta(days=1), s]; ft = fark.at[gt, s]
                if pd.notna(f0) and pd.notna(ft) and f0 < 0:
                    r.append(ft / f0)
        satir[t] = (np.median(r) if r else np.nan, len(r))
    print("   gün: " + " · ".join(f"+{t}: {m:.2f} (n {n})" for t, (m, n) in satir.items()))
    # süre
    L2 = v[v.yon == "L"]
    print(f"  long pozisyon süresi gün: medyan {L2.gun_say.median():.0f} · ort {L2.gun_say.mean():.1f} · p90 {L2.gun_say.quantile(.9):.0f}")
    return P


def B_ek(P, FP):
    print("\n  --- B ek: yıl bazında +7 gün oran (H-B2) ve Q5-Q1 ilk 3 coin hariç (H-B1 dayanıklılık)")
    med = FP.median(axis=1); fark = FP.sub(med, axis=0)
    v = P.dropna(subset=["giris_oran"])
    L = v[(v.yon == "L") & (v.beklenen_carry > 0)]
    out = {}
    for yl, g in L.groupby("yil"):
        r = {t: [] for t in (3, 7)}
        for gi, s in zip(g.giris, g.sembol):
            g0 = gi - pd.Timedelta(days=1)
            if s not in fark.columns or g0 not in fark.index:
                continue
            f0 = fark.at[g0, s]
            for t in r:
                gt = g0 + pd.Timedelta(days=t)
                if gt in fark.index and pd.notna(f0) and f0 < 0 and pd.notna(fark.at[gt, s]):
                    r[t].append(fark.at[gt, s] / f0)
        out[yl] = {f"+{t}": np.median(x) if x else np.nan for t, x in r.items()} | {"n": len(r[7])}
    print("  long +3 / +7 gün oranı yıl bazında:\n  " + pd.DataFrame(out).T.round(2).to_string().replace("\n", "\n  "))
    for yon in ("L", "S"):
        x = v[v.yon == yon].copy()
        x["q"] = pd.qcut(x.beklenen_carry.rank(method="first"), 5, labels=False)
        q5 = x[x.q == 4]; top3 = q5.groupby("sembol").net.sum().sort_values(ascending=False).head(3)
        y = x[~x.sembol.isin(top3.index)]
        a = lambda g: g.net.sum() / g.sgun.sum() * 365 if g.sgun.sum() > 0 else np.nan
        tam = (a(x[x.q == 4]) - a(x[x.q == 0])); har = (a(y[y.q == 4]) - a(y[y.q == 0]))
        yy = y.groupby("yil").apply(lambda g: a(g[g.q == 4]) - a(g[g.q == 0]))
        print(f"  {yon}: Q5 en çok net 3 coin {dict(top3.round(1))}; Q5-Q1 net/sy tam {tam:.0f} → bu 3 coin hariç {har:.0f}; "
              f"yıllar (hariç): " + " ".join(f"{k}:{v:.0f}" for k, v in yy.items()))


def D_risk(G, P, Pn):
    print("\n==================== D) FUNDING - FİYAT RİSKİ (coin düzeyi ve pozisyon MAE; MAE kapanış bazlı 4 sa)")
    C = Pn["C"]
    mae = []
    for r in P.itertuples():
        if r.sembol not in C.columns:
            mae.append(np.nan); continue
        s = C[r.sembol].loc[r.giris - pd.Timedelta(hours=4): r.cikis + pd.Timedelta(hours=20)].dropna()
        if len(s) < 2:
            mae.append(np.nan); continue
        x = s / s.iloc[0] - 1
        mae.append(x.min() * 100 if r.yon == "L" else -x.max() * 100)
    P["mae"] = mae
    for yon in ("L", "S"):
        x = P[P.yon == yon]
        c = x.groupby("sembol").agg(sgun=("sgun", "sum"), funding=("funding", "sum"), fiyat=("fiyat", "sum"), tp=("tp", "sum"),
                                    net=("net", "sum"), mae_med=("mae", "median"), mae_min=("mae", "min"), poz=("net", "size"))
        c = c[c.sgun >= 0.5]                                  # en az yarım sermaye-gün (gürültü)
        c["f_sy"] = c.funding / c.sgun * 365; c["p_sy"] = c.fiyat / c.sgun * 365; c["n_sy"] = c.net / c.sgun * 365
        from scipy.stats import spearmanr
        rho = spearmanr(c.f_sy, c.p_sy)
        c["q"] = pd.qcut(c.f_sy.rank(method="first"), 5, labels=["Q1 en az", "Q2", "Q3", "Q4", "Q5 en çok"])
        t = c.groupby("q", observed=True).agg(coin=("poz", "size"), f_sy=("f_sy", "median"), p_sy=("p_sy", "median"), n_sy=("n_sy", "median"),
                                              net_top=("net", "sum"), zararli_coin_pay=("net", lambda n: (n < 0).mean() * 100),
                                              mae_med=("mae_med", "median"), mae_en_kotu=("mae_min", "median"))
        print(f"\n  {('LONG' if yon == 'L' else 'SHORT')}: {len(c)} coin (≥ 0,5 sermaye-gün); Spearman(funding/sy, TP hariç fiyat/sy) = {rho.statistic:+.2f} (p {rho.pvalue:.3g})")
        print("  " + t.round(1).to_string().replace("\n", "\n  "))
        ry = {}
        for yl, g in x.groupby("yil"):
            cc = g.groupby("sembol").agg(sgun=("sgun", "sum"), funding=("funding", "sum"), fiyat=("fiyat", "sum"))
            cc = cc[cc.sgun >= 0.25]
            if len(cc) >= 20:
                ry[yl] = round(spearmanr(cc.funding / cc.sgun, cc.fiyat / cc.sgun).statistic, 2)
        print("  yıl bazında Spearman:", ry)
        if yon == "L":
            k = c[(c.f_sy > c.f_sy.quantile(.8))].sort_values("net").head(10)
            print("  yüksek funding/sy (üst %20) ama NET ZARARLI long coinler:\n  " +
                  k[["poz", "sgun", "funding", "fiyat", "tp", "net", "f_sy", "mae_min"]].round(2).to_string().replace("\n", "\n  "))
            top = c.sort_values("funding", ascending=False).head(10)
            print("  en çok funding getiren 10 long coin:\n  " +
                  top[["poz", "sgun", "funding", "fiyat", "tp", "net", "f_sy", "mae_med", "mae_min"]].round(2).to_string().replace("\n", "\n  "))
    # pozisyon düzeyinde: gerçekleşen funding/sy beşte birlik vs MAE
    L = P[(P.yon == "L") & (P.sgun > 0.02)].copy(); L["f_sy"] = L.funding / L.sgun * 365
    L["q"] = pd.qcut(L.f_sy.rank(method="first"), 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    print("\n  long pozisyon (gerçekleşen funding/sy beşte birlik): MAE medyan / p10 · net/sy")
    print("  " + L.groupby("q", observed=True).apply(lambda g: pd.Series({"mae_med": g.mae.median(), "mae_p10": g.mae.quantile(.1),
          "net_sy": g.net.sum() / g.sgun.sum() * 365, "adet": len(g)})).round(1).to_string().replace("\n", "\n  "))
    return P


def bulmacalar(G, P, FP):
    print("\n==================== B) SORULAR: 2021 / 2026 / Mayıs 2026")
    med = FP.median(axis=1)
    L = G[G.yon == "L"].copy()
    L["fsy"] = L.funding
    def ozet(gr):
        g = L[np.asarray(gr(pd.DatetimeIndex(L.gun)))]
        s = g.sgun.sum()
        odenen = g[g.funding < 0]
        return pd.Series({"long funding": g.funding.sum(), "long sermaye-gün": s, "funding/sy %": g.funding.sum() / s * 365,
                          "ödenen funding (−)": odenen.funding.sum(), "alınan funding (+)": g[g.funding > 0].funding.sum(),
                          "ödeme yapılan gün payı %": (g.funding < 0).mean() * 100,
                          "evren medyan funding yıllık %": med[np.asarray(gr(med.index))].mean(),
                          "ilk 3 coin pay %": g.groupby("sembol").funding.sum().nlargest(3).sum() / max(g.funding.sum(), 1e-9) * 100})
    y = pd.DataFrame({yl: ozet(lambda d, yl=yl: d.year == yl) for yl in range(2020, 2027)})
    print("  yıllar:\n  " + y.round(1).to_string().replace("\n", "\n  "))
    a = pd.DataFrame({m: ozet(lambda d, m=m: (d.year == 2026) & (d.month == m)) for m in range(1, 11)})
    print("  2026 ayları:\n  " + a.round(1).to_string().replace("\n", "\n  "))
    for m in (5, 6):
        g = L[(L.gun.dt.year == 2026) & (L.gun.dt.month == m)].groupby("sembol").funding.sum().sort_values()
        print(f"  2026-{m:02d} long funding coin: en çok {dict(g.tail(4).round(2))} · en çok ödenen {dict(g.head(4).round(2))}")


def C_muhasebe(G):
    print("\n==================== C) MUHASEBE KARŞI-OLGULARI (motor YOK, sermaye yeniden dağıtılmaz → yalnız o coinlerin defter katkısı çıkar)")
    top = funding_sirasi(G)
    yil = G.groupby("yil")[["funding", "net"]].sum()
    satir = {"taban": yil.net}
    for n in (3, 5, 10):
        h = G[~G.sembol.isin(top.index[:n])]
        satir[f"tüm dönem ilk {n} funding coini çıkar"] = h.groupby("yil").net.sum()
    for n in (3, 5):
        out = {}
        for yl, g in G.groupby("yil"):
            t = g.groupby("sembol").funding.sum().nlargest(n).index
            out[yl] = g[~g.sembol.isin(t)].net.sum()
        satir[f"her yılın ilk {n} funding coini o yıl çıkar"] = pd.Series(out)
    for k in (0.25, 0.5, 0.75):
        gc = G.yas_g <= 365
        satir[f"genç funding −%{int(k*100)}"] = (G.net - np.where(gc, k * G.funding, 0)).groupby(G.yil).sum()
    T = pd.DataFrame(satir).T
    print("  net katkı (% puan, basit toplam, 1,0x):\n  " + T.round(1).to_string().replace("\n", "\n  "))
    f = {"taban funding": yil.funding}
    for n in (3, 5, 10):
        f[f"ilk {n} hariç funding"] = G[~G.sembol.isin(top.index[:n])].groupby("yil").funding.sum()
    print("  funding (% puan):\n  " + pd.DataFrame(f).T.round(1).to_string().replace("\n", "\n  "))


def D_ek(P):
    L = P[P.yon == "L"]
    out = {}
    for yl, x in L.groupby("yil"):
        c = x.groupby("sembol").agg(sgun=("sgun", "sum"), funding=("funding", "sum"), mae=("mae", "median"))
        c = c[c.sgun >= 0.25]
        if len(c) < 25:
            continue
        q = pd.qcut((c.funding / c.sgun).rank(method="first"), 5, labels=False)
        out[yl] = {"Q1 mae": c.mae[q == 0].median(), "Q5 mae": c.mae[q == 4].median(), "coin": len(c)}
    print("\n  H-D yıl bazında (long coin, medyan pozisyon MAE):\n  " + pd.DataFrame(out).T.round(1).to_string().replace("\n", "\n  "))


def C_motor():
    import arastirma_m695_dayaniklilik as T
    print("\n==================== C) MOTOR KARŞI-OLGULARI (evrenden çıkarma; sermaye kalan coinlere dağılır; 1,0x)")
    M.CIKTI = "/tmp/m_ekim"
    taban = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    seriler = {"taban (P3T2)": taban}
    M.CIKTI = OUT
    for ad in ("C_FUND3", "C_FUND5", "C_FUND10", "C_DUR180"):
        if all(os.path.exists(f"{OUT}/{ad}_{h}.pkl") for h in (0, 1)):
            seriler[ad] = sum(M.gunluk(f"{ad}_{h}") for h in (0, 1)) / 2
        else:
            print(f"  {ad}: EKSİK — sayılmaz")
    rows = {}
    for ad, s in seriler.items():
        s = s[:SON]; o = T.olc(s)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100)
        rows[ad] = {"CAGR %": o["cagr"], "Sharpe": o["sharpe"], "maks DD %": o["maks_dd"], "en kötü ay %": o["en_kotu_ay"],
                    **{str(k): v for k, v in yl.items()}}
    print("  " + pd.DataFrame(rows).T.round(1).to_string().replace("\n", "\n  "))
    for ad in ("C_FUND3", "C_FUND5", "C_FUND10", "C_DUR180"):
        y = [f"{OUT}/{ad}_gk_{h}.pkl" for h in (0, 1)]
        if all(os.path.exists(x) for x in y):
            g = pd.concat([pd.read_pickle(x) for x in y]); g["gun"] = pd.to_datetime(g.gun); g = g[g.gun <= SON]
            f = (g.funding / 2 * 100).groupby(g.gun.dt.year).sum()
            print(f"  {ad} funding (% puan): " + " · ".join(f"{k}: {v:.1f}" for k, v in f.items()))


def analiz():
    G = defter(); Pn, yas, son = panel(); G = yas_ekle(G, yas)
    print(f"defter: {len(G)} satır, {G.sembol.nunique()} sembol, {G.gun.min().date()} → {G.gun.max().date()}; yaşı bulunmayan satır {int(G.yas_g.isna().sum())}")
    A_dagilim(G, son)
    P = pozisyonlar(G); FP = funding_paneli(sorted(set(G.sembol)))
    P = B_sureklilik(G, P, FP); B_ek(P, FP); bulmacalar(G, P, FP)
    C_muhasebe(G); C_motor()
    P = D_risk(G, P, Pn); D_ek(P)


if __name__ == "__main__" and sys.argv[1:] == ["analiz"]:
    import warnings; warnings.filterwarnings("ignore")
    analiz()
