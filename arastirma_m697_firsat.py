#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 697 — FIRSAT AZLIĞINDA SERMAYE KORUMA VE FIRSAT DÖNÜNCE YAKALAMA. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Otomatik strateji değişikliği YOK: alternatifler yalnız geçmişte ÖLÇÜLÜR. Ön kayıt: KAR_HARITASI "Madde 697 ÖN KAYIT".
Motor kopyası /tmp/g33_m690.py (madde 690: g33 + coin-gün defterinde tp / stop / komisyon ayrımı; E çıktısı bayt bayt aynı).
Dünyalar: BAZ + madde 694 kuraklık dünyaları (aynı SEMBOL_HARIC listeleri / YAS_GUN 365), bu kez ayrıntılı coin-gün defteriyle.
  python3 arastirma_m697_firsat.py kos      -> /tmp/m697/E_<dünya>_<hiza>.pkl + gk (tek işçi; ANALİZİ EŞZAMANLI ÇALIŞTIRMAYIN)
  python3 arastirma_m697_firsat.py analiz   -> /tmp/m697/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I, arastirma_m690_kar_kaynagi as A690, arastirma_m694_yeni_coin as A4
from tradfi_liste import TRADFI

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m697"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
DUNYA = ["Y365K", "L50_a", "L50_b", "L75_a", "L75_b", "DUR24", "DUR25"]


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out, GUNLUK_KATKI=f"{D}/gk_{ad}_{h}.pkl", GK_BAS="2019-01-01")
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m690.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    A690.kopya()
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    S, _ = A4.senaryolar()
    for ad in DUNYA:
        ek = {"YAS_GUN": "365"} if ad == "Y365K" else {"SEMBOL_HARIC": ",".join(M.D8 + S[ad])}
        for h in (0, 1):
            rc = _kos1(ad, ek, h)
            ayni = open(f"{D}/E_{ad}_{h}.pkl", "rb").read() == open(f"/tmp/m694/E_{ad}_{h}.pkl", "rb").read()
            print(ad, h, rc, "· 694 ile", "BAYT BAYT AYNI" if ayni else "FARKLI!", flush=True)

# ------------------------------------------------------------------------------------------------ analiz
import arastirma_m695_dayaniklilik as T, arastirma_m696_kuraklik as K6
DUNYA_T = ["BAZ"] + DUNYA
BAS = "2021-01-01"


def seri(ad):
    return T.seri("P0" if ad == "BAZ" else ad, D)


def defter(ad, YAS):
    a = "P0" if ad == "BAZ" else ad
    G = pd.concat([pd.read_pickle(f"{D}/gk_{a}_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun)
    G["net"] = G.fiyat_top + G.funding - G.komisyon
    G["bw"] = G.ort_poz.abs() * G.bar / 6; G["yon"] = np.sign(G.ort_poz)
    G = G.groupby(["gun", "sembol", "yon"], as_index=False)[["net", "fiyat_top", "funding", "komisyon", "tp", "bw"]].sum()
    G[["net", "fiyat_top", "funding", "komisyon", "tp", "bw"]] /= 2            # iki hiza ortalaması (yokluk = 0)
    G = G.join(YAS, on=["gun", "sembol"]); G["genc"] = G.yas < 365
    return G[G.gun >= BAS]


def ozet_seri(d):
    return K6.olc2(d)


def analiz():
    P = pickle.load(open("/tmp/panel.pkl", "rb"))
    YAS = (P["YAS"].resample("D").last() / 6).stack(); YAS.index.names = ["gun", "sembol"]; YAS.name = "yas"
    GS = K6.genc_sayi()                                     # n (günlük) her dünya
    N30 = GS.rolling(30, min_periods=1).mean().shift(1)     # o gün bilinen
    eksik = [ad for ad in DUNYA_T if not all(os.path.exists(f"{D}/E_{'P0' if ad == 'BAZ' else ad}_{h}.pkl") and
                                              os.path.exists(f"{D}/gk_{'P0' if ad == 'BAZ' else ad}_{h}.pkl") for h in (0, 1))]
    print(f"[KONTROL] dünya {len(DUNYA_T)}, eksik {eksik}");
    if eksik: sys.exit(1)
    for ad in DUNYA:
        ok = all(open(f"{D}/E_{ad}_{h}.pkl", "rb").read() == open(f"/tmp/m694/E_{ad}_{h}.pkl", "rb").read() for h in (0, 1))
        print(f"[KONTROL] {ad}: 694 çıktısıyla {'bayt bayt aynı' if ok else 'FARKLI!'}")
    ok = all(open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read() for h in (0, 1))
    print(f"[KONTROL] BAZ parite (iki hiza): {'bayt bayt aynı' if ok else 'FARKLI!'}")

    S, Gd = {}, {}
    for ad in DUNYA_T:
        r = seri(ad); S[ad] = r[r.index >= BAS]; Gd[ad] = defter(ad, YAS)
    # defter tutarlılığı
    for ad in ("BAZ", "Y365K"):
        dn = Gd[ad].groupby("gun").net.sum().reindex(S[ad].index).fillna(0)
        print(f"[KONTROL] {ad}: coin-gün defteri toplamı ↔ günlük kitap getirisi korelasyon {np.corrcoef(dn, S[ad])[0,1]:.4f} · "
              f"toplam {dn.sum()*100:.0f} vs {S[ad].sum()*100:.0f} puan (bileşiksiz)")

    # ---------------------------------------------------------------- günlük kitap tabloları (her dünya)
    GUN = {}
    for ad in DUNYA_T:
        g = Gd[ad]; idx = S[ad].index
        f = lambda m, c: g[m].groupby("gun")[c].sum().reindex(idx).fillna(0)
        GUN[ad] = pd.DataFrame({"r": S[ad], "genc_net": f(g.genc, "net"), "eski_net": f(~g.genc, "net"),
                                "genc_bw": f(g.genc, "bw"), "eski_bw": f(~g.genc, "bw"), "n30": N30[ad].reindex(idx).ffill(),
                                "n": GS[ad].reindex(idx).ffill()})
    pd.to_pickle(GUN, f"{D}/gunluk.pkl")

    # ================================================================ T1 listeleme akışı
    print("\n================ T1) LİSTELEME AKIŞI (gerçek dünya; TradFi / D8 hariç; 2021+)")
    fv = P["C"].apply(lambda s: s.first_valid_index())
    fv = fv[[c for c in fv.index if c not in TRADFI and c not in M.D8]]; fv = fv[fv > pd.Timestamp("2020-02-01")]
    gun_say = fv.dt.normalize().value_counts().sort_index().reindex(pd.date_range("2020-02-01", S["BAZ"].index[-1], freq="D"), fill_value=0)
    L = pd.DataFrame({f"L{w}": gun_say.rolling(w).sum() for w in (30, 60, 90)})
    for w in (30, 60, 90): L[f"L{w}_oran"] = L[f"L{w}"] / (gun_say.rolling(365, min_periods=180).sum() * w / 365)
    b = GUN["BAZ"]; eq = (1 + b.r).cumprod()
    ileri = {f"ileri{k}": eq.shift(-k) / eq - 1 for k in (30, 90)}
    yil = gun_say[gun_say.index >= "2021-01-01"].groupby(gun_say[gun_say.index >= "2021-01-01"].index.year).sum()
    print("  yıllık ham listeleme: " + ", ".join(f"{y} {v}" for y, v in yil.items()))
    ay = pd.DataFrame({**{c: L[c] for c in L}, **ileri, "n30": b.n30}).reindex(b.index).resample("ME").last().dropna()
    rows = []
    for c in ["L30", "L60", "L90", "L30_oran", "L60_oran", "L90_oran"]:
        for k in ("ileri30", "ileri90"):
            x = ay[[c, k]].dropna(); x2 = x[x.index < "2024-01-01"]; x3 = x[x.index >= "2024-01-01"]
            rows.append(dict(gosterge=c, hedef=k, rho_tum=x[c].corr(x[k], "spearman"), rho_21_23=x2[c].corr(x2[k], "spearman"),
                             rho_24_26=x3[c].corr(x3[k], "spearman"), n_ay=len(x)))
    T1 = pd.DataFrame(rows); print("  [ÖLÇÜM] Spearman (örtüşmeyen ay sonları; ileri90 için ardışık aylar örtüşür → anlamlılık abartılı):")
    print(T1.round(2).to_string(index=False)); T1.to_csv(f"{D}/T1_akis.csv", index=False)
    lead = {k: L["L90"].reindex(b.index).corr(b.n30.shift(-k)) for k in (0, 30, 60, 90, 120, 180)}
    print("  L90(t) ↔ n30(t+k) korelasyonu: " + ", ".join(f"k={k} {v:.2f}" for k, v in lead.items()))
    q = ay.copy(); q["kova"] = pd.qcut(q.L90_oran, 4, labels=["Ç1 düşük", "Ç2", "Ç3", "Ç4 yüksek"])
    print("  L90_oran çeyreklerine göre sonraki 90 g kitap getirisi medyanı %: " +
          q.groupby("kova", observed=True).ileri90.median().mul(100).round(1).to_string().replace("\n", " · "))
    son = L.iloc[-1]; print(f"  son gün ({L.index[-1].date()}): L30 {son.L30:.0f} · L60 {son.L60:.0f} · L90 {son.L90:.0f} · L90_oran {son.L90_oran:.2f} · n30 {b.n30.iloc[-1]:.1f}")

    # ================================================================ aylık dünya paneli (T2 / T5)
    rows = []
    for ad in DUNYA_T:
        g = GUN[ad]; m = g.resample("ME")
        x = pd.DataFrame({"ret": m.r.apply(lambda v: (1 + v).prod() - 1), "genc_pay": m.genc_bw.sum() / (m.genc_bw.sum() + m.eski_bw.sum()),
                          "brut": (m.genc_bw.sum() + m.eski_bw.sum()) / m.r.count(), "n30": m.n30.mean()})
        x["dunya"] = ad; rows.append(x)
    PN = pd.concat(rows).reset_index().rename(columns={"index": "ay", "gun": "ay"}); PN.to_csv(f"{D}/panel_aylik.csv", index=False)
    rng = np.random.default_rng(697)

    def fe_egim(df, x, y="ret"):
        d = df[[x, y, "ay"]].dropna().copy()
        d[x + "_d"] = d[x] - d.groupby("ay")[x].transform("mean"); d[y + "_d"] = d[y] - d.groupby("ay")[y].transform("mean")
        b_ = (d[x + "_d"] * d[y + "_d"]).sum() / (d[x + "_d"] ** 2).sum()
        aylar = d.ay.unique(); bs = []
        for _ in range(1000):
            s_ = rng.choice(aylar, len(aylar)); dd = pd.concat([d[d.ay == a_] for a_ in s_]) if False else d.set_index("ay").loc[s_]
            bs.append((dd[x + "_d"] * dd[y + "_d"]).sum() / (dd[x + "_d"] ** 2).sum())
        return b_, np.percentile(bs, 5), np.percentile(bs, 95)

    print("\n================ T2) GENÇ COİN SERMAYESİ ↔ GETİRİ")
    g = Gd["BAZ"]
    for donem, (a_, b_) in {"2021-23": ("2021", "2023"), "2024-26": ("2024", "2026")}.items():
        x = g[(g.gun.dt.year >= int(a_)) & (g.gun.dt.year <= int(b_))]
        t = x.groupby("genc").agg(net=("net", "sum"), bw=("bw", "sum"))
        t["sermaye_pay_%"] = t.bw / t.bw.sum() * 100; t["kar_pay_%"] = t.net / t.net.sum() * 100; t["maruziyet_basi_yillik_%"] = t.net / t.bw * 365.25 * 100
        print(f"  [ÖLÇÜM] BAZ {donem} (genç=True):\n" + t.drop(columns=["net", "bw"]).round(1).to_string())
    pb = PN[(PN.dunya == "BAZ") & (PN.ay >= BAS)].set_index("ay")
    pb["ret_ileri"] = pb.ret.shift(-1); pb["genc_pay_ar"] = pb.genc_pay - pb.genc_pay.rolling(12, min_periods=6).mean()
    print(f"  [ÖLÇÜM] BAZ aylık: genç pay ↔ aynı ay getiri ρ {pb.genc_pay.corr(pb.ret, 'spearman'):.2f} · ↔ sonraki ay ρ {pb.genc_pay.corr(pb.ret_ileri, 'spearman'):.2f}"
          f" · eğilimden arındırılmış pay ↔ sonraki ay ρ {pb.genc_pay_ar.corr(pb.ret_ileri, 'spearman'):.2f}")
    b2, lo2, hi2 = fe_egim(PN[PN.ay >= BAS], "genc_pay")
    print(f"  [ÖLÇÜM] dünyalar arası AY SABİT ETKİLİ eğim (8 dünya, aynı ay): genç brüt payı +10 puan → aylık getiri {b2*0.1*100:+.2f} puan "
          f"(%90 bootstrap {lo2*0.1*100:+.2f} … {hi2*0.1*100:+.2f})")

    # ================================================================ T5 fırsat yoğunluğu
    print("\n================ T5) FIRSAT YOĞUNLUĞU (n30 = evrende 60-365 g coin sayısı)")
    b5, lo5, hi5 = fe_egim(PN[PN.ay >= BAS], "n30")
    print(f"  ay sabit etkili: n30 +1 → aylık getiri {b5*100:+.2f} puan (%90 {lo5*100:+.2f} … {hi5*100:+.2f})")
    d = PN[PN.ay >= BAS].copy(); d["ret_d"] = d.ret - d.groupby("ay").ret.transform("mean")
    d["kova"] = pd.cut(d.n30, [-0.1, 2, 4, 6, 8, 10, 15, 100], labels=["0-2", "2-4", "4-6", "6-8", "8-10", "10-15", "15+"])
    t5 = d.groupby("kova", observed=True).agg(ay_dunya=("ret", "size"), ret_ham_med=("ret", "median"), ret_ay_etkisi_ort=("ret_d", "mean"), brut=("brut", "mean"))
    t5[["ret_ham_med", "ret_ay_etkisi_ort"]] *= 100
    print("  [ÖLÇÜM] n30 kovası: aylık getiri (ham medyan, ay ortalamasından sapma; %):\n" + t5.round(2).to_string()); t5.to_csv(f"{D}/T5_yogunluk.csv")
    db = d[d.dunya == "BAZ"]
    print("  yalnız gerçek dünya (ay etkisi yok, rejim karışık), n30 kovası → aylık getiri medyanı %: " +
          db.groupby("kova", observed=True).ret.median().mul(100).round(1).to_string().replace("\n", " · "))
    ev = (P["C"].notna() & (P["HAC"] >= 7e7) & (P["YAS"] >= 360) & (P["DON"].fillna(0) < 0.10))
    ev = ev[[c for c in ev.columns if c not in TRADFI and c not in M.D8]].sum(axis=1).resample("D").mean()
    print(f"  bilgi: gerçek evren toplam coin sayısı (30 g ort.) son {ev.rolling(30).mean().iloc[-1]:.0f}, 2021+ medyan {ev[ev.index>=BAS].median():.0f}; "
          f"kitap aynı anda ~13 coin tutuyor (madde 695)")

    # ================================================================ T3 eski coin alternatifi
    print("\n================ T3) ESKİ COİN ALTERNATİFİ (eski = ≥ 365 g; net = fiyat + TP + funding − komisyon)")
    rows = []
    for ad in DUNYA_T:
        g_ = GUN[ad]; st = pd.cut(g_.n30, [-1, 6, 12, 1e9], labels=["n30<6", "6-12", ">12"])
        for s_, x in g_.groupby(st, observed=True):
            for kol, c in (("eski", "eski"), ("genc", "genc")):
                bw = x[f"{c}_bw"].sum()
                if bw <= 0: continue
                dd = x[f"{c}_net"]
                rows.append(dict(dunya=ad, durum=s_, kol=kol, gun=len(x), brut_ort=x[f"{c}_bw"].mean(),
                                 maruziyet_basi_yillik=dd.sum() / bw * 365.25 * 100, katki_yillik_puan=dd.mean() * 365.25 * 100,
                                 sharpe=dd.mean() / dd.std() * np.sqrt(365.25) if dd.std() > 0 else np.nan, en_kotu_gun=dd.min() * 100))
    T3 = pd.DataFrame(rows); T3.to_csv(f"{D}/T3_eski.csv", index=False)
    print("  [ÖLÇÜM] eski kolun maruziyet başı yıllık getirisi % (dünya × n30 durumu):")
    print(T3[T3.kol == "eski"].pivot(index="dunya", columns="durum", values="maruziyet_basi_yillik").round(0).to_string())
    print("  eski kol günlük katkı Sharpe:"); print(T3[T3.kol == "eski"].pivot(index="dunya", columns="durum", values="sharpe").round(2).to_string())
    print("  gün sayısı:"); print(T3[T3.kol == "eski"].pivot(index="dunya", columns="durum", values="gun").to_string())
    print("  genç kol maruziyet başı yıllık % (karşılaştırma):"); print(T3[T3.kol == "genc"].pivot(index="dunya", columns="durum", values="maruziyet_basi_yillik").round(0).to_string())
    by = GUN["BAZ"]; e_y = by.groupby(by.index.year).apply(lambda x: x.eski_net.sum() / x.eski_bw.sum() * 365.25 * 100)
    print("  BAZ eski kol maruziyet başı yıllık % yıl yıl: " + ", ".join(f"{y} {v:.0f}" for y, v in e_y.items()))

    # ================================================================ T6 nakit mi eski coin mi
    print("\n================ T6) NAKİT Mİ ESKİ COİN Mİ (örtü; genç coinlere dokunulmayan kollar = fırsat kaçırmaz)")
    def kol(g_, esik, m, hepsi):
        dus = (g_.n30 < esik).astype(float); mm = 1 - (1 - m) * dus                     # o günün çarpanı
        net = g_.r if hepsi else g_.eski_net; bw = (g_.genc_bw + g_.eski_bw) if hepsi else g_.eski_bw
        maliyet = 0.0010 * bw * mm.diff().abs().fillna(0)
        return g_.r - (1 - mm) * net - maliyet, mm
    rows = []; Y = {}
    for esik, etiket in ((6, "ön kayıt"), (10, "sonradan (696)")):
        for ad in DUNYA_T:
            g_ = GUN[ad]
            for ad_k, m, hepsi in (("A0 baz", 1, False), ("E50 eski×0,5", 0.5, False), ("E0 eski→nakit", 0, False),
                                   ("T50 tüm×0,5", 0.5, True), ("T0 tüm→nakit", 0, True)):
                rr, mm = kol(g_, esik, m, hepsi); o = ozet_seri(rr)
                kac = ((1 - mm) * g_.genc_net).sum() * 100 if hepsi else 0.0
                o.update(esik=esik, etiket=etiket, dunya=ad, kol=ad_k, dusuk_gun_pay=(g_.n30 < esik).mean() * 100, kacan_genc_puan=kac)
                rows.append(o)
                if esik == 6: Y[(ad, ad_k)] = T.yillik(rr)
    R6 = pd.DataFrame(rows); R6.to_csv(f"{D}/T6_kollar.csv", index=False)
    cols = ["cagr", "sharpe", "maks_dd", "calmar", "en_kotu_ay", "en_kotu_365g", "su_alti_maks_g", "dusuk_gun_pay", "kacan_genc_puan"]
    for esik in (6, 10):
        print(f"\n  ---- eşik n30 < {esik} ({'ön kayıt' if esik == 6 else 'sonradan, etiketli'})")
        for ad in DUNYA_T:
            x = R6[(R6.esik == esik) & (R6.dunya == ad)].set_index("kol")[cols]
            print(f"  {ad}:\n" + x.round(2).to_string())
    ozet = R6.assign(kurak=R6.dunya.isin(DUNYA)).groupby(["esik", "kol"]).apply(lambda x: pd.Series({
        "BAZ_cagr": x[x.dunya == "BAZ"].cagr.iloc[0], "BAZ_dd": x[x.dunya == "BAZ"].maks_dd.iloc[0], "BAZ_sharpe": x[x.dunya == "BAZ"].sharpe.iloc[0],
        "kurak_cagr_med": x[x.kurak].cagr.median(), "kurak_dd_min": x[x.kurak].maks_dd.min(), "kurak_dd_med": x[x.kurak].maks_dd.median(),
        "kurak_365_min": x[x.kurak].en_kotu_365g.min(), "kurak_sharpe_med": x[x.kurak].sharpe.median(),
        "BAZ_kacan_genc": x[x.dunya == "BAZ"].kacan_genc_puan.iloc[0]}), include_groups=False)
    print("\n  [ÖLÇÜM] ÖZET (kuraklık = 7 dünya):\n" + ozet.round(2).to_string()); ozet.to_csv(f"{D}/T6_ozet.csv")
    print("  yıllık % (eşik 6), BAZ ve Y365K:")
    for ad in ("BAZ", "Y365K", "L75_b", "DUR25"):
        print(f"  {ad}: " + pd.DataFrame({k: Y[(ad, k)] for k in ["A0 baz", "E50 eski×0,5", "E0 eski→nakit", "T50 tüm×0,5", "T0 tüm→nakit"]}).T.round(1).to_string().replace("\n", "\n        "))
    # fırsat dönünce: düşük durumdan çıktıktan sonraki 90 g genç / eski katkı (BAZ)
    g_ = GUN["BAZ"]; dus = g_.n30 < 6; cik = dus.shift(1, fill_value=False) & ~dus
    for t0 in g_.index[cik]:
        w = g_[t0: t0 + pd.Timedelta(days=90)]
        print(f"  BAZ düşük durumdan çıkış {t0.date()}: sonraki 90 g genç katkı {w.genc_net.sum()*100:+.1f} · eski {w.eski_net.sum()*100:+.1f} puan · "
              f"kitap {((1+w.r).prod()-1)*100:+.1f}%")

    # ================================================================ T4 genç short kuyruğu
    print("\n================ T4) GENÇ COİN SHORT KUYRUĞU (BAZ; madde 689 long tarafındaydı)")
    g = Gd["BAZ"]; sh = g[g.yon < 0].copy()
    sh["grup"] = pd.cut(sh.yas, [0, 180, 365, 730, 1e9], labels=["60-180 g", "180-365 g", "1-2 yıl", ">2 yıl"])
    t4 = sh.groupby("grup", observed=True).agg(coin_gun=("net", "size"), brut_pay=("bw", "sum"), net=("net", "sum"),
                                               p01=("net", lambda v: v.quantile(0.001) * 100), en_kotu=("net", lambda v: v.min() * 100),
                                               kayip_1=("net", lambda v: (v < -0.01).sum()), kayip_2=("net", lambda v: (v < -0.02).sum()))
    t4["brut_pay"] = t4.brut_pay / t4.brut_pay.sum() * 100; t4["net_puan"] = t4.pop("net") * 100
    t4["kayip_1_per_1000_bw_gun"] = t4.kayip_1 / (sh.groupby("grup", observed=True).bw.sum()) / 1000
    print("  [ÖLÇÜM] short coin-gün (kitap %): p0,1 / en kötü / −%1 ve −%2'den kötü gün sayısı:\n" + t4.round(3).to_string()); t4.to_csv(f"{D}/T4_short.csv")
    en = sh.nsmallest(10, "net")[["gun", "sembol", "yas", "net"]].assign(net=lambda x: x.net * 100)
    print("  en kötü 10 short coin-günü (kitap %):\n" + en.round(2).to_string(index=False))
    gk_ = sh[sh.genc].groupby("gun").net.apply(lambda v: (v < -0.005).sum())
    print(f"  aynı gün ≥ 2 genç short'un her biri kitapta −%0,5'ten kötü: {(gk_ >= 2).sum()} gün · ≥ 3: {(gk_ >= 3).sum()} gün · toplam genç short günü {sh[sh.genc].gun.nunique()}")
    gun_sh = sh.groupby(["gun", "genc"]).net.sum().unstack().fillna(0) * 100
    print(f"  genç short bacağının günlük toplamı: en kötü {gun_sh[True].min():.2f}% · %0,1 {gun_sh[True].quantile(0.001):.2f}% | eski: en kötü {gun_sh[False].min():.2f}%")
    E = pd.read_pickle("/tmp/m693/epizot_yol.pkl"); es = E[E.yon < 0].copy()
    es["grup"] = pd.cut(es.yas_bas, [0, 180, 365, 730, 1e9], labels=["60-180 g", "180-365 g", "1-2 yıl", ">2 yıl"])
    es["aleyhte"] = -es.mae_bar if es.mae_bar.median() <= 0 else es.mae_bar
    t4b = es.groupby("grup", observed=True).agg(epizot=("pnl", "size"), aleyhte_med=("aleyhte", "median"),
                                                 p_25=("aleyhte", lambda v: (v >= 0.25).mean() * 100), p_50=("aleyhte", lambda v: (v >= 0.5).mean() * 100),
                                                 p_100=("aleyhte", lambda v: (v >= 1.0).mean() * 100), pnl_p1=("pnl", lambda v: v.quantile(0.01) * 100 / 2),
                                                 pnl_min=("pnl", lambda v: v.min() * 100 / 2), pnl_ort_bp=("pnl", lambda v: v.mean() * 1e4 / 2))
    print("  [ÖLÇÜM] short epizotları (693): bar içi en büyük aleyhte hareket (fiyat, oran) ≥ +%25 / +%50 / +%100 olasılığı %, epizot net kitap % (iki hiza ort.):\n"
          + t4b.round(3).to_string()); t4b.to_csv(f"{D}/T4_epizot.csv")
    print("  referans: madde 664 (YAS_S_GUN, short için yaş eşiği yükseltme) RED; 652 yaş kuralını gevşetmek KESİN RED; 689 tek coin long kuyruğu.")

    bek = ["T1_akis.csv", "panel_aylik.csv", "T5_yogunluk.csv", "T3_eski.csv", "T6_kollar.csv", "T6_ozet.csv", "T4_short.csv", "T4_epizot.csv", "gunluk.pkl"]
    yok = [f for f in bek if not os.path.exists(f"{D}/{f}")]
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if not yok else f"EKSİK {yok}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
