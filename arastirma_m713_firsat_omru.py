#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 713 — FUNDING FIRSATININ ÖMRÜ VE POZİSYON GETİRİSİ (yalnız ölçüm + muhasebe karşı-olgusu; strateji / parametre değişmez).
Veri: madde 711 tam geçmiş defteri (/tmp/m711, EK_T7KKS ile bayt bayt aynı), 712 pozisyon tanımı ve ham funding paneli.
Kullanım: python3 arastirma_m713_firsat_omru.py
"""
import os, sys, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")
import arastirma_m712_funding_kaynak as F
import arastirma_m346_prim as M

KOM = 0.0005
YAS_KOVA = [0, 1, 2, 3, 4, 5, 6, 7, 10, 15, 999]
YAS_ETK = ["0", "1", "2", "3", "4", "5", "6", "7-9", "10-14", "15+"]


def hazirla():
    G = F.defter(); Pn, yas, son = F.panel(); G = F.yas_ekle(G, yas)
    G = G.sort_values(["hiza", "sembol", "gun"]).copy()
    yeni = (G.sembol != G.sembol.shift()) | (G.hiza != G.hiza.shift()) | (G.yon != G.yon.shift()) | ((G.gun - G.gun.shift()).dt.days != 1)
    G["pid"] = yeni.cumsum(); G["pyas"] = G.groupby("pid").cumcount()
    G["tp_var"] = (G.tp != 0)
    P = F.pozisyonlar(G)                       # aynı tanım (pid sırası aynı)
    FP = F.funding_paneli(sorted(set(G.sembol)))
    med = FP.median(axis=1)
    onc = FP.shift(1); P["giris_oran"] = [onc.at[g, s] if s in onc.columns and g in onc.index else np.nan for g, s in zip(P.giris, P.sembol)]
    P["beklenen_carry"] = np.where(P.yon == "L", -1, 1) * P.giris_oran
    P["genc"] = P.yas_g <= 365
    for yon in ("L", "S"):
        m = P.yon == yon
        q = pd.qcut(P.loc[m, "beklenen_carry"].rank(method="first"), 5, labels=False)
        P.loc[m, "uc"] = (q == 4)
    G = G.merge(P[["genc", "uc", "beklenen_carry"]], left_on="pid", right_index=True, how="left")
    return G, P, FP, med, Pn


def yas_tablosu(g):
    g = g.assign(k=pd.cut(g.pyas, YAS_KOVA, right=False, labels=YAS_ETK))
    t = g.groupby("k", observed=True).agg(sgun=("sgun", "sum"), funding=("funding", "sum"), tp=("tp", "sum"), fiyat=("fiyat", "sum"),
                                          kom=("komisyon", "sum"), stop=("stop", "sum"), net=("net", "sum"), pg=("pid", "size"))
    tpo = g.groupby("k", observed=True).tp_var.mean() * 100
    for c in ["funding", "tp", "fiyat", "kom", "net"]:
        t[c + "/sy"] = t[c] / t.sgun * 365
    t["TP gün payı %"] = tpo
    t["sermaye payı %"] = t.sgun / t.sgun.sum() * 100
    return t[["pg", "sermaye payı %", "funding/sy", "tp/sy", "fiyat/sy", "kom/sy", "net/sy", "TP gün payı %"]]


def olcum(G, P, FP, med):
    print("==================== 1) GERÇEKLEŞEN: POZİSYON YAŞINA GÖRE (yaş 0 = giriş günü; /sy = sermaye-yıl başına % puan; 1,0x)")
    print(f"pozisyon {len(P)} (long {int((P.yon=='L').sum())}, short {int((P.yon=='S').sum())}); pozisyon-gün {len(G)}")
    for yon in ("L", "S"):
        g = G[G.yon == yon]
        print(f"\n--- {('LONG' if yon == 'L' else 'SHORT')} tüm\n" + yas_tablosu(g).round(1).to_string())
        for ad, m in [("genç (≤365 g)", g.genc == True), ("eski (>365 g)", g.genc == False), ("giriş carry en uç beşte bir", g.uc == True)]:
            t = yas_tablosu(g[m])
            print(f"  {ad}: net/sy yaş " + " · ".join(f"{i}:{v:.0f}" for i, v in t["net/sy"].items()) +
                  " | funding/sy " + " · ".join(f"{i}:{v:.0f}" for i, v in t["funding/sy"].items()))
        # yıl bazında yaş 0-2 vs >=3
        out = {}
        for yl, x in g.groupby("yil"):
            a = x[x.pyas <= 2]; b = x[x.pyas >= 3]
            out[yl] = {"0-2 net/sy": a.net.sum() / a.sgun.sum() * 365, "≥3 net/sy": b.net.sum() / b.sgun.sum() * 365,
                       "≥3 sermaye payı %": b.sgun.sum() / x.sgun.sum() * 100,
                       "0-2 funding/sy": a.funding.sum() / a.sgun.sum() * 365, "≥3 funding/sy": b.funding.sum() / b.sgun.sum() * 365}
        print("  yıl bazında yaş 0-2 vs ≥3:\n  " + pd.DataFrame(out).T.round(0).to_string().replace("\n", "\n  "))
    print("\n==================== 2) GİRİŞ CARRY'Sİ ve +1/2/3/5/7 GÜN GERÇEKLEŞEN FUNDING (pozisyon başına, % puan, ve sermaye-yıla oranla)")
    for yon in ("L", "S"):
        g = G[G.yon == yon]
        rows = {}
        for k in (1, 2, 3, 5, 7):
            x = g[g.pyas < k]
            s = x.groupby("pid").agg(f=("funding", "sum"), sg=("sgun", "sum"))
            rows[f"ilk {k} g"] = {"funding toplam": s.f.sum(), "funding/sy": s.f.sum() / s.sg.sum() * 365}
        pp = P[P.yon == yon]
        rows["giriş carry medyan (yıllık %)"] = {"funding toplam": np.nan, "funding/sy": pp.beklenen_carry.median()}
        rows["giriş carry sermaye ağırlıklı"] = {"funding toplam": np.nan, "funding/sy": np.average(pp.beklenen_carry.fillna(0), weights=pp.sgun)}
        print(f"  {yon}: " + " · ".join(f"{k}: {v['funding/sy']:.0f}" for k, v in rows.items()))
    print("\n==================== 3) SÖNME ↔ FİYAT YÖNÜ (long, giriş carry > 0, ≥ 4 gün tutulan; betimsel, aynı dönem)")
    fark = FP.sub(med, axis=0); C = Pn_C[0]
    L = P[(P.yon == "L") & (P.beklenen_carry > 0) & (P.gun_say >= 4)]
    r = []
    for p in L.itertuples():
        g0 = p.giris - pd.Timedelta(days=1); g3 = p.giris + pd.Timedelta(days=2)
        if p.sembol not in fark.columns or g0 not in fark.index or g3 not in fark.index or p.sembol not in C.columns:
            continue
        f0, f3 = fark.at[g0, p.sembol], fark.at[g3, p.sembol]
        c = C[p.sembol]
        try:
            c0 = c.asof(p.giris); c3 = c.asof(p.giris + pd.Timedelta(days=3)); ce = c.asof(p.cikis + pd.Timedelta(hours=20))
        except Exception:
            continue
        if pd.notna(f0) and pd.notna(f3) and f0 < 0 and c0 and c3 and ce:
            r.append(dict(sonme=1 - f3 / f0, f0=f0, r03=c3 / c0 - 1, r3e=ce / c3 - 1, yil=p.giris.year))
    R = pd.DataFrame(r)
    print(f"  n {len(R)}; sönme = 1 − (gün +3 farkı / giriş farkı); medyan sönme {R.sonme.median():.2f}")
    print(f"  Spearman(sönme, fiyat 0→3 g) {spearmanr(R.sonme, R.r03).statistic:+.2f} · (sönme, fiyat 3 g→çıkış) {spearmanr(R.sonme, R.r3e).statistic:+.2f}")
    R["kova"] = pd.qcut(R.sonme.rank(method="first"), 4, labels=["az söndü", "2", "3", "çok söndü"])
    print("  " + R.groupby("kova", observed=True).agg(n=("r03", "size"), sonme=("sonme", "median"), fiyat_0_3=("r03", "median"),
                                                     fiyat_3_cikis=("r3e", "median")).round(3).to_string().replace("\n", "\n  "))
    yy = R.groupby("yil").apply(lambda x: spearmanr(x.sonme, x.r03).statistic if len(x) > 30 else np.nan)
    print("  yıl bazında Spearman(sönme, fiyat 0→3): " + " ".join(f"{k}:{v:+.2f}" for k, v in yy.items()))


Pn_C = [None]


def karsi_olgu(G, P, FP, med):
    print("\n==================== 4) KARŞI-OLGU (muhasebe; kapanan sermaye NAKİT, ek kapanış komisyonu 5 bp; motor YOK)")
    fark = FP.sub(med, axis=0)
    L = G[G.yon == "L"]
    # Kol A: yaş 3 sonunda kapan
    kapA = L[L.pyas == 3][["pid", "gun"]].set_index("pid").gun
    # Kol B: önceki günün farkı >= 0 (avantaj tamamen söndü) ise o gün sonunda kapan; yaş >= 1
    Lb = L[L.pyas >= 1].copy()
    Lb["f_onc"] = [fark.at[g - pd.Timedelta(days=1), s] if (s in fark.columns and (g - pd.Timedelta(days=1)) in fark.index) else np.nan
                   for g, s in zip(Lb.gun, Lb.sembol)]
    kapB = Lb[Lb.f_onc >= 0].groupby("pid").gun.min()
    M.CIKTI = "/tmp/m_ekim"
    taban = (sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2)[:F.SON]
    import arastirma_m685_dinamik_doz as Z
    import arastirma_m695_dayaniklilik as T
    sonuc = {}

    def kol(kap, ad):
        x = L.merge(kap.rename("kap"), left_on="pid", right_index=True)
        cik = x[x.gun > x.kap]                                   # kapanıştan sonraki günler: katkı çıkar
        son = x[x.gun == x.kap]
        ek_kom = (son.ort_poz.abs() * KOM * 100 / 2)            # kapanış günü ek komisyon (% puan, hiza payı)
        ek_kom = ek_kom[son.pid.isin(cik.pid)]                  # zaten o gün biten pozisyona ek komisyon yok
        d_gun = cik.groupby("gun").net.sum()
        kom_gun = son[son.pid.isin(cik.pid)].assign(k=ek_kom).groupby("gun").k.sum()
        delta = (-d_gun).add(-kom_gun, fill_value=0) / 100
        s = taban.add(delta.reindex(taban.index).fillna(0))
        # ayrışım
        bil = {c: -cik[c].sum() for c in ["funding", "tp", "fiyat", "stop"]}
        bil["komisyon (geri alınan)"] = cik.komisyon.sum(); bil["ek kapanış komisyonu"] = -ek_kom.sum()
        bil["kapanan pozisyon"] = int(cik.pid.nunique()); bil["serbest kalan sermaye-gün"] = cik.sgun.sum()
        # coin bağımlılığı
        pc = (-cik.groupby("sembol").net.sum()).sort_values()
        sonuc[ad] = (s, bil, pc, cik)
        return s

    rows = {}
    seri = {"taban P3T2": taban, "Kol A (yaş 3 sonu kapan)": kol(kapA, "A"), "Kol B (avantaj söndü → kapan)": kol(kapB, "B")}
    for ad, s in seri.items():
        o = T.olc(s); zs = s.reindex(Z.P.index).dropna()
        k, er = Z.esit(zs)
        rows[ad] = {"CAGR %": o["cagr"], "Sharpe": o["sharpe"], "maks DD %": o["maks_dd"], "en kötü gün %": o["en_kotu_gun"],
                    "Sh ≤2024": Z.sh(s[:"2024-12-31"]), "Sh 2025+": Z.sh(s["2025-01-01":]), "eşit risk doz": k, "eşit risk yıllık %": er,
                    **{str(y): v for y, v in s.groupby(s.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100).items()}}
    print("  " + pd.DataFrame(rows).T.round(2).to_string().replace("\n", "\n  "))
    for ad in ("A", "B"):
        s, bil, pc, cik = sonuc[ad]
        print(f"\n  Kol {ad} ayrışım (tabana göre, % puan; + = kol lehine): " + " · ".join(f"{k} {v:.1f}" if isinstance(v, float) else f"{k} {v}" for k, v in bil.items()))
        print(f"   en çok KAZANDIRAN çıkarma: {dict(pc.tail(3).round(1))} · en çok KAYBETTİREN: {dict(pc.head(3).round(1))}")
        tek = pc.abs().idxmax(); fark_t = pc.sum(); fark_h = pc.drop(tek).sum()
        print(f"   net fark toplam {fark_t:+.1f} puan; en büyük katkılı coin ({tek}) hariç {fark_h:+.1f} → işaret {'AYNI' if np.sign(fark_t) == np.sign(fark_h) else 'DEĞİŞİR'}")
        yl = (-cik.groupby("yil").net.sum())
        print("   yıl bazında net fark (komisyon hariç): " + " · ".join(f"{k}: {v:+.1f}" for k, v in yl.items()))
    return rows


if __name__ == "__main__":
    G, P, FP, med, Pn = hazirla(); Pn_C[0] = Pn["C"]
    olcum(G, P, FP, med)
    karsi_olgu(G, P, FP, med)
