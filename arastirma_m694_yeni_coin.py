#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 694 — YENİ LİSTELENEN COİN AVANTAJI VE EVREN SÜRDÜRÜLEBİLİRLİĞİ. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Motor kopyası /tmp/g33_m694.py = g33.py'nin DEĞİŞMEMİŞ kopyası; karşı-olgular yalnız ortam değişkenleriyle (stres senaryosu, önerilen ayar değil):
  L25 / L50 / L75 (_a, _b iki rastgele çekiliş)  2021-01-01 sonrası listelenen (TradFi hariç) coinlerin %25 / %50 / %75'i EVRENDEN çıkar
                                                 (SEMBOL_HARIC; o coin hiç listelenmemiş gibi; boşalan yer diğer coinlere gider)
  DUR24 / DUR25                                  2024-H1 / 2025-H1'de listelenen bütün coinler çıkar (6 aylık listeleme duruşu)
  Y365K                                          evrene asgari yaş 365 g (madde 693 Y365) + günlük coin defteri (kapasite analizi için)
Listeleme tarihi = vadeli işlem verisinin ilk günü (veri 2020-01'de başlar; 2021 öncesi listelemeler kesik sayılır, çıkarma havuzuna girmez).
  python3 arastirma_m694_yeni_coin.py kos      -> /tmp/m694/E_<senaryo>_<hiza>.pkl (tek işçi)
  python3 arastirma_m694_yeni_coin.py analiz   -> /tmp/m694/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle, shutil, json
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
from tradfi_liste import TRADFI

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m694"; os.makedirs(D, exist_ok=True)
S690, S691, S692, S693 = "/tmp/m690", "/tmp/m691", "/tmp/m692", "/tmp/m693"
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
NF = 15


def listeleme():
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
    fv = C.apply(lambda s: s.first_valid_index()); lv = C.apply(lambda s: s.last_valid_index())
    return fv, lv


def senaryolar():
    fv, _ = listeleme()
    havuz = sorted(s for s, t in fv.items() if t >= pd.Timestamp("2021-01-01") and s not in TRADFI and s not in M.D8)
    S = {}
    for p in (25, 50, 75):
        for tohum, ek in ((694, "a"), (6940, "b")):
            rng = np.random.default_rng(tohum + p); sec = sorted(rng.choice(havuz, size=int(round(len(havuz) * p / 100)), replace=False))
            S[f"L{p}_{ek}"] = sec
    S["DUR24"] = [s for s in havuz if pd.Timestamp("2024-01-01") <= fv[s] < pd.Timestamp("2024-07-01")]
    S["DUR25"] = [s for s in havuz if pd.Timestamp("2025-01-01") <= fv[s] < pd.Timestamp("2025-07-01")]
    return S, havuz


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        rc = subprocess.run([sys.executable, "/tmp/g33_m694.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode
    if "KATKI" in ek and os.path.exists(f"/tmp/katki_{h}.pkl"): os.replace(f"/tmp/katki_{h}.pkl", f"{D}/katki_{ad}_{h}.pkl")
    return rc


def kos():
    shutil.copy(os.path.join(R, "g33.py"), "/tmp/g33_m694.py")
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · kopya vs g33.py -> {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    S, havuz = senaryolar()
    json.dump({k: v for k, v in S.items()}, open(f"{D}/senaryo_coinleri.json", "w"), ensure_ascii=False, indent=0)
    print(f"çıkarma havuzu: 2021+ listelenen {len(havuz)} coin (TradFi ve D8 hariç)", flush=True)
    for h in (0, 1):
        print("Y365K", h, _kos1("Y365K", {"YAS_GUN": "365", "GUNLUK_KATKI": f"{D}/gk_Y365K_{h}.pkl", "GK_BAS": "2019-01-01", "KATKI": "1"}, h), flush=True)
    for ad, sec in S.items():
        for h in (0, 1):
            print(ad, len(sec), h, _kos1(ad, {"SEMBOL_HARIC": ",".join(M.D8 + sec)}, h), flush=True)


# ------------------------------------------------------------------------------------------------ yardımcılar
def _seri_yol(yol, ad):
    hedef = f"{D}/M357_EK_{ad}.pkl"
    if not os.path.exists(hedef): os.symlink(yol, hedef)
    M.CIKTI = D; s = M.gunluk(f"M357_EK_{ad}"); s.index = pd.to_datetime(s.index); return s


def seri(ad):
    if ad == "BAZ": return sum(_seri_yol(REF.format(h=h), f"BAZ_{h}") for h in (0, 1)) / 2
    return sum(_seri_yol(f"{D}/E_{ad}_{h}.pkl", f"{ad}_{h}") for h in (0, 1)) / 2


def _olc(d):
    d = d.dropna(); e = (1 + d).cumprod()
    return dict(cagr=(e.iloc[-1] ** (365.25 / len(d)) - 1) * 100, sharpe=d.mean() / d.std() * np.sqrt(365.25), maks_dd=(e / e.cummax() - 1).min() * 100)


def _yil(d): return d.groupby(d.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100)


def analiz():
    pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40)
    fv, lv = listeleme()
    Pn = pickle.load(open("/tmp/panel.pkl", "rb")); YAS = Pn["YAS"]; HAC = Pn["HAC"]
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = Z["C"]; ODE = Z["ODE"]
    gun_idx = C4.index.floor("D")
    yas_g = YAS.groupby(gun_idx).last() / 6
    hac_g = HAC.groupby(gun_idx).last()                         # panel hacmi (madde 228 evren ölçüsü; gün sonu değeri)
    Cg = C4.groupby(gun_idx).last(); lr = np.log(Cg).diff()
    vol30 = lr.rolling(30, min_periods=10).std() * np.sqrt(365) * 100
    fund_g = ODE.groupby(gun_idx).sum()                        # günlük toplam funding ödemesi (oran)
    fund30 = fund_g.rolling(30, min_periods=10).mean() * 365 * 100   # yıllık %
    Hl = pickle.load(open("/tmp/hlo.pkl", "rb"))
    bins = [-1, 30, 90, 180, 365, 730, 1e9]; lab = ["0-30 g", "31-90 g", "91-180 g", "181-365 g", "1-2 yıl", ">2 yıl"]
    BAZ = seri("BAZ")

    # ================= 1) yaş grubu ayrıştırması (2021+; yaş kesikliği sonrası)
    G = pd.read_csv(f"{S690}/gun_coin_bilesen.csv", parse_dates=["gun"])
    G["net"] = G.tp + G.funding + G.fiyat + G.stop - G.komisyon
    gk = pd.concat([pd.read_pickle(f"{S690}/gk_{h}.pkl").assign(h=h) for h in (0, 1)]); gk["gun"] = pd.to_datetime(gk.gun)
    gk["bw"] = gk.ort_poz.abs() * gk.bar / 6
    bw = gk.groupby(["gun", "sembol"]).bw.sum().rename("bw") / 2
    G = G.merge(bw.reset_index(), on=["gun", "sembol"], how="left")
    def _ek(df, X, ad):
        s = X.stack().rename(ad).reset_index(); s.columns = ["gun", "sembol", ad]; return df.merge(s, on=["gun", "sembol"], how="left")
    G = _ek(G, yas_g, "yas"); G = _ek(G, vol30.shift(1), "vol30"); G = _ek(G, fund30.shift(1), "fund30"); G = _ek(G, hac_g.shift(1), "hacim")
    G["yas_grup"] = pd.cut(G.yas, bins, labels=lab)
    E = pd.read_pickle(f"{S693}/epizot_yol.pkl")
    E["yas_grup"] = pd.cut(E.yas_bas, bins, labels=lab)
    def _at(X, t, s):
        X = X.copy(); rr = X.index.get_indexer(t); cc = X.columns.get_indexer(s); v = np.full(len(t), np.nan); ok = (rr >= 0) & (cc >= 0)
        v[ok] = X.values[rr[ok], cc[ok]]; return v
    tb = E.bas.dt.normalize() - pd.Timedelta(days=1)
    E["vol_on"] = _at(vol30, tb, E["sem"]); E["fund_on"] = _at(fund30, tb, E["sem"]); E["hacim_on"] = _at(hac_g, tb, E["sem"])
    E["fund_yon"] = E.fund_on * -E.yon      # pozisyon lehine funding (short + pozitif funding = kazanç)
    G21 = G[G.gun >= "2021-01-01"]; E21 = E[E.bas >= "2021-01-01"]
    print("[ÖLÇÜM] 1) YAŞ GRUBU AYRIŞTIRMASI (2021-01 – 2026-09; puan = kitap, iki hiza ort.; yaş = vadeli verinin başladığı günden)")
    for donem, g_, e_ in (("2021-2026", G21, E21), ("2024-2026", G[G.gun >= "2024-01-01"], E[E.bas >= "2024-01-01"])):
        T = g_.groupby("yas_grup", observed=True).agg(net=("net", "sum"), tp=("tp", "sum"), funding=("funding", "sum"), long_fiyat=("long_fiyat", "sum"),
                                                      short_fiyat=("short_fiyat", "sum"), stop=("stop", "sum"), komisyon=("komisyon", "sum"),
                                                      maruziyet=("bw", "sum"), coin=("sembol", "nunique"))
        T[["net", "tp", "funding", "long_fiyat", "short_fiyat", "stop", "komisyon"]] *= 100
        T["net_payi"] = T.net / T.net.sum() * 100; T["maruz_payi"] = T.maruziyet / T.maruziyet.sum() * 100
        T["maruz_basi_yillik"] = T.net / T.maruziyet * 365
        pe = e_.groupby("yas_grup", observed=True).agg(poz=("ep", "size"), poz_basi_bp=("pnl", lambda s: s.mean() * 1e4), tp_orani=("tp_oldu", "mean"),
                                                       sure=("sure_gun", "mean"), mae_med=("mae_bar", "median"), mfe_med=("mfe", "median"),
                                                       long_pay=("yon", lambda s: (s > 0).mean()))
        pe[["tp_orani", "mae_med", "mfe_med", "long_pay"]] *= 100
        ch = g_[g_.bw > 0].groupby("yas_grup", observed=True).agg(vol_med=("vol30", "median"), fund_med=("fund30", "median"),
                                                                  fund_p90=("fund30", lambda s: s.quantile(.9)), fund_p10=("fund30", lambda s: s.quantile(.1)),
                                                                  hacim_med_musd=("hacim", lambda s: s.median() / 1e6))
        T = T.join(pe).join(ch); T.insert(0, "donem", donem)
        print(f"  {donem}:\n" + T.round(2).to_string()); T.to_csv(f"{D}/yas_grup_{donem}.csv")
    # yaş mı özellik mi: tabakalama (oynaklık tercili içinde genç vs yaşlı) + regresyon
    e = E21.dropna(subset=["vol_on", "fund_on", "hacim_on", "yas_bas"]).copy()
    e["genc"] = e.yas_bas < 365; e["pnl_bp"] = e.pnl * 1e4
    print("\n  [ÖLÇÜM] tabakalama: pozisyon başı net (bp) — aynı özellik tercili içinde genç (< 1 yıl) / yaşlı:")
    TB = []
    for k, ad in (("vol_on", "oynaklık"), ("fund_yon", "lehte funding"), ("hacim_on", "hacim")):
        for yn, yad in ((1, "long"), (-1, "short")):
            x = e[e.yon == yn]; q = pd.qcut(x[k], 3, labels=["düşük", "orta", "yüksek"])
            t = x.groupby([q, "genc"], observed=True).pnl_bp.agg(["mean", "size"]).unstack()
            for qq in t.index:
                TB.append(dict(ozellik=ad, yon=yad, tercil=qq, genc_bp=t.loc[qq, ("mean", True)], yasli_bp=t.loc[qq, ("mean", False)],
                               genc_n=t.loc[qq, ("size", True)], yasli_n=t.loc[qq, ("size", False)]))
    TB = pd.DataFrame(TB); TB["fark"] = TB.genc_bp - TB.yasli_bp; print(TB.round(1).to_string(index=False)); TB.to_csv(f"{D}/tabakalama.csv", index=False)
    print("  [ÖLÇÜM] regresyon (pozisyon başı net bp; OLS; katsayı ve t; standart hata bağımsızlık varsayar -> t iyimser):")
    REG = []
    e["log_hacim"] = np.log(e.hacim_on.clip(lower=1e5)); e["genc_f"] = e.genc.astype(float)
    for yn, yad in ((1, "long"), (-1, "short")):
        x = e[e.yon == yn]
        for cols in (["genc_f"], ["vol_on", "fund_yon", "log_hacim"], ["genc_f", "vol_on", "fund_yon", "log_hacim"]):
            A = np.c_[np.ones(len(x)), x[cols].values]; y = x.pnl_bp.values
            b, *_ = np.linalg.lstsq(A, y, rcond=None); res = y - A @ b; s2 = res.var(ddof=A.shape[1])
            se = np.sqrt(np.diag(s2 * np.linalg.pinv(A.T @ A))); r2 = 1 - res.var() / y.var()
            REG.append(dict(yon=yad, model="+".join(cols), r2=r2, **{f"b_{c}": b[i + 1] for i, c in enumerate(cols)},
                            **{f"t_{c}": b[i + 1] / se[i + 1] for i, c in enumerate(cols)}))
    REG = pd.DataFrame(REG); print(REG.round(3).to_string(index=False)); REG.to_csv(f"{D}/regresyon.csv", index=False)

    # ================= 2) listeleme kohortları
    print("\n[ÖLÇÜM] 2) LİSTELEME KOHORTLARI (2021-01 sonrası; pencere tam gözlenen coinler; delist olanlar dahil)")
    gc = G.groupby("sembol")
    son_veri = Cg.index[-1]
    coins = [s for s in fv.index if fv[s] >= pd.Timestamp("2021-01-01") and s not in TRADFI and s not in M.D8]
    rows = []
    for s in coins:
        l0 = fv[s].normalize(); g = gc.get_group(s) if s in gc.groups else None
        r = dict(sembol=s, liste=l0, ceyrek=l0.to_period("Q"), ay=l0.to_period("M"), delist=lv[s] < pd.Timestamp("2026-09-01"))
        p = Cg[s].dropna()
        for w in (30, 90, 180, 365):
            tam = l0 + pd.Timedelta(days=w) <= son_veri
            r[f"tam{w}"] = tam
            if not tam: continue
            if g is not None:
                gg = g[(g.gun >= l0) & (g.gun < l0 + pd.Timedelta(days=w))]
                r[f"net{w}"] = gg.net.sum() * 100; r[f"tp{w}"] = gg.tp.sum() * 100; r[f"fund{w}"] = gg.funding.sum() * 100
                r[f"islem_gun{w}"] = int((gg.bw > 0).sum())
            else:
                r[f"net{w}"] = 0.0; r[f"tp{w}"] = 0.0; r[f"fund{w}"] = 0.0; r[f"islem_gun{w}"] = 0
            pw = p[(p.index >= l0) & (p.index < l0 + pd.Timedelta(days=w))]
            r[f"fiyat_getiri{w}"] = (pw.iloc[-1] / pw.iloc[0] - 1) * 100 if len(pw) > 1 else np.nan
            r[f"vol{w}"] = np.log(pw).diff().std() * np.sqrt(365) * 100 if len(pw) > 5 else np.nan
            fw = fund_g[s][(fund_g.index >= l0) & (fund_g.index < l0 + pd.Timedelta(days=w))]
            r[f"funding_ort{w}"] = fw.mean() * 365 * 100 if len(fw) else np.nan
        rows.append(r)
    K = pd.DataFrame(rows); K.to_csv(f"{D}/kohort_coin.csv", index=False)
    K["donem"] = np.where(K.liste < pd.Timestamp("2024-01-01"), "2021-2023", "2024-2026")
    KT = []
    for w in (30, 90, 180, 365):
        x = K[K[f"tam{w}"]]
        t = x.groupby("donem").agg(coin=("sembol", "size"), islem_goren_pct=(f"islem_gun{w}", lambda s: (s > 0).mean() * 100),
                                   islem_gunu_ort=(f"islem_gun{w}", "mean"), coin_basi_net=(f"net{w}", "mean"), coin_basi_net_med=(f"net{w}", "median"),
                                   tp_toplam=(f"tp{w}", "sum"), funding_toplam=(f"fund{w}", "sum"), net_toplam=(f"net{w}", "sum"),
                                   zararli_pct=(f"net{w}", lambda s: (s[x.loc[s.index, f'islem_gun{w}'] > 0] < 0).mean() * 100),
                                   fiyat_getiri_med=(f"fiyat_getiri{w}", "median"), vol_med=(f"vol{w}", "median"), funding_ort_med=(f"funding_ort{w}", "median"),
                                   delist_pct=("delist", lambda s: s.mean() * 100))
        t.insert(0, "pencere_gun", w); KT.append(t)
    KT = pd.concat(KT); print(KT.round(2).to_string()); KT.to_csv(f"{D}/kohort_donem.csv")
    KQ = K[K.tam90].groupby("ceyrek").agg(coin=("sembol", "size"), islem_goren_pct=("islem_gun90", lambda s: (s > 0).mean() * 100),
                                          coin_basi_net90=("net90", "mean"), net90_toplam=("net90", "sum"), tp90=("tp90", "sum"), fund90=("fund90", "sum"),
                                          vol90_med=("vol90", "median"), fiyat90_med=("fiyat_getiri90", "median"), funding90_med=("funding_ort90", "median"))
    KQ = KQ.join(K[K.tam365].groupby("ceyrek").agg(coin_basi_net365=("net365", "mean"), net365_toplam=("net365", "sum")))
    print("  çeyreklik kohortlar (ilk 90 / 365 gün; puan):\n" + KQ.round(2).to_string()); KQ.to_csv(f"{D}/kohort_ceyrek.csv")
    KM = K[K.tam90].groupby("ay").agg(coin=("sembol", "size"), net90=("net90", "sum"), coin_basi_net90=("net90", "mean"))
    KM.to_csv(f"{D}/kohort_ay.csv")
    # yaşa göre birikimli: bir coinin katkısı ilk N günde mi yoğun? (365 g tam gözlenen kohortlar)
    x = K[K.tam365]
    print(f"  365 g tam gözlenen {len(x)} kohort coini: ilk yıl net katkısının %{x.net30.sum()/x.net365.sum()*100:.0f}'i ilk 30 günde, "
          f"%{x.net90.sum()/x.net365.sum()*100:.0f}'i ilk 90, %{x.net180.sum()/x.net365.sum()*100:.0f}'i ilk 180 günde")
    for dn in ("2021-2023", "2024-2026"):
        y = x[x.donem == dn]
        if len(y) and y.net365.sum():
            print(f"   {dn} ({len(y)} coin): ilk 30 / 90 / 180 g payı %{y.net30.sum()/y.net365.sum()*100:.0f} / %{y.net90.sum()/y.net365.sum()*100:.0f} / "
                  f"%{y.net180.sum()/y.net365.sum()*100:.0f} · coin başı ilk yıl net {y.net365.mean():.2f} puan")

    # ================= 3A) karşı-olgu (motor)
    print("\n[ÖLÇÜM; senaryo VARSAYIM] 3A) LİSTELEME AKIŞI KARŞI-OLGUSU (motor; tarihsel coinler evrenden çıkarıldı)")
    Sx = json.load(open(f"{D}/senaryo_coinleri.json")) if os.path.exists(f"{D}/senaryo_coinleri.json") else {}
    rows = [dict(senaryo="BAZ (mevcut akış)", cikan_coin=0, **_olc(BAZ), cagr_2024=_olc(BAZ[BAZ.index >= "2024-01-01"])["cagr"], **{f"y{k}": v for k, v in _yil(BAZ).items()})]
    eksik = []
    for ad in ["L25_a", "L25_b", "L50_a", "L50_b", "L75_a", "L75_b", "DUR24", "DUR25", "Y365K"]:
        if all(os.path.exists(f"{D}/E_{ad}_{h}.pkl") for h in (0, 1)):
            s = seri(ad)
            rows.append(dict(senaryo=ad, cikan_coin=len(Sx.get(ad, [])), **_olc(s), cagr_2024=_olc(s[s.index >= "2024-01-01"])["cagr"],
                             **{f"y{k}": v for k, v in _yil(s).items()}))
        else: eksik.append(ad)
    KO = pd.DataFrame(rows); print(KO.round(1).to_string(index=False)); KO.to_csv(f"{D}/karsi_olgu.csv", index=False)
    if eksik: print("  EKSİK SENARYO (başarılı sayılmadı):", eksik)
    # 6 aylık duruş: duruştan sonraki 12 ay
    for ad, b0 in (("DUR24", "2024-01-01"), ("DUR25", "2025-01-01")):
        if ad in eksik: continue
        s = seri(ad); b0 = pd.Timestamp(b0); e0 = b0 + pd.DateOffset(months=18)
        a1 = _olc(BAZ[(BAZ.index >= b0) & (BAZ.index < e0)])["cagr"]; a2 = _olc(s[(s.index >= b0) & (s.index < e0)])["cagr"]
        print(f"  {ad}: duruşun başladığı aydan itibaren 18 ay CAGR baz %{a1:.0f} -> %{a2:.0f}")

    # ================= 3B) senaryo analizi (model; VARSAYIM)
    print("\n[VARSAYIM] 3B) SENARYO ANALİZİ (model; tarihsel sonuç değil)")
    g24 = G[G.gun >= "2024-01-01"]; genc = g24.yas < 365
    yil24 = (g24.gun.max() - g24.gun.min()).days / 365.25
    gn = g24[genc].net.sum() * 100 / yil24; yn = g24[~genc].net.sum() * 100 / yil24
    print(f"  2024-26 statik ayrıştırma: genç coin net {gn:.1f} puan / yıl · yaşlı {yn:.1f} puan / yıl (bileşik değil)")
    # genç katkının oynaklığa duyarlılığı: genç pozisyonlarda oynaklık tercili başına pozisyon başı net
    e24 = E[(E.bas >= "2024-01-01") & (E.yas_bas < 365)].dropna(subset=["vol_on"])
    qv = pd.qcut(e24.vol_on, 3, labels=["düşük", "orta", "yüksek"])
    tv = e24.groupby(qv, observed=True).agg(poz=("ep", "size"), vol=("vol_on", "median"), poz_basi_bp=("pnl", lambda s: s.mean() * 1e4))
    print("  genç coin pozisyonları (2024+), giriş oynaklığı tercili:\n" + tv.round(1).to_string())
    oran_vol = tv.poz_basi_bp.iloc[0] / e24.pnl.mean() / 1e4 if e24.pnl.mean() else np.nan
    SC = []
    for ad, f_list, f_vol in (("mevcut akış", 1.0, 1.0), ("listeleme −%25", 0.75, 1.0), ("listeleme −%50", 0.50, 1.0), ("listeleme −%75", 0.25, 1.0),
                              ("6 ay duruş (yılda)", 0.5, 1.0), ("akış aynı, ilk yıl oynaklığı düşük tercile iner", 1.0, oran_vol)):
        SC.append(dict(senaryo=ad, genc_carpani=f_list * f_vol, yillik_puan=yn + gn * f_list * f_vol, baz_puan=yn + gn))
    SC = pd.DataFrame(SC); SC["degisim_pct"] = (SC.yillik_puan / SC.baz_puan - 1) * 100
    print("  doğrusal model: yıllık puan = yaşlı katkı + genç katkı × akış çarpanı × kalite çarpanı (yeniden dağıtım YOK, bileşik değil):\n"
          + SC.round(2).to_string(index=False)); SC.to_csv(f"{D}/senaryo_model.csv", index=False)
    print("  (6 ay duruşun etkisi genç coinin 12 aylık ömrüne yayıldığı için yıllık ~%50 genç katkı kaybı varsayıldı)")

    # ================= 4) eski coinler yerini doldurabilir mi
    print("\n[ÖLÇÜM] 4) ESKİ COİNLER YERİ DOLDURABİLİR Mİ (motor Y365K vs baz)")
    if all(os.path.exists(f"{D}/gk_Y365K_{h}.pkl") for h in (0, 1)):
        gy = pd.concat([pd.read_pickle(f"{D}/gk_Y365K_{h}.pkl").assign(h=h) for h in (0, 1)]); gy["gun"] = pd.to_datetime(gy.gun)
        gy["bw"] = gy.ort_poz.abs() * gy.bar / 6
        def ozet(g_, ad):
            g_ = g_[g_.gun >= "2021-01-01"]
            d = g_.groupby("gun").agg(brut=("bw", "sum"), coin=("sembol", "nunique")); d.brut /= 2
            net = (g_.fiyat + g_.funding).sum() / 2 * 100
            return dict(senaryo=ad, brut_ort=d.brut.mean(), coin_gun_ort=d.coin.mean() / 2, fiyat_puan=g_.fiyat.sum() / 2 * 100,
                        funding_puan=g_.funding.sum() / 2 * 100, fiyat_funding_puan=net, maruz_basi_yillik=net / (d.brut.sum()) * 365)
        o = [ozet(gk, "BAZ"), ozet(gy, "Y365K (genç coin yok)")]
        for t in (2021, 2024):
            o.append(ozet(gk[gk.gun.dt.year >= t], f"BAZ {t}+")); o.append(ozet(gy[gy.gun.dt.year >= t], f"Y365K {t}+"))
        O4 = pd.DataFrame(o); print(O4.round(3).to_string(index=False)); O4.to_csv(f"{D}/eski_coin_kapasite.csv", index=False)
        ky = pd.concat([pd.read_pickle(f"{D}/katki_Y365K_{h}.pkl").assign(h=h) for h in (0, 1)]) if all(os.path.exists(f"{D}/katki_Y365K_{h}.pkl") for h in (0, 1)) else None
        kb = pd.read_csv(f"{S690}/pozisyon_defteri.csv", parse_dates=["t"])
        for ad, k in (("BAZ", kb), ("Y365K", ky)):
            if k is None: continue
            k = k[pd.to_datetime(k.t) >= "2021-01-01"]
            print(f"  {ad}: dilim bacağı {len(k)} · TP ile kapanan %{(k.kapanis=='TP').mean()*100:.2f} · bacak başı net {k.pnl.mean()*1e4:.1f} bp (dilim) · "
                  f"long bacak payı %{(k.yon>0).mean()*100:.0f}")
    else:
        print("  EKSİK: Y365K defteri yok")
    # eski coinlerde (> 2 yıl) bazdaki fırsatlar
    eo = E21[E21.yas_bas >= 730]; ey = E21[E21.yas_bas < 365]
    print(f"  bazda (2021+): > 2 yıl coin pozisyonları {len(eo)} · TP oranı %{eo.tp_oldu.mean()*100:.1f} · poz başı {eo.pnl.mean()*1e4:.1f} bp · "
          f"< 1 yıl {len(ey)} · TP %{ey.tp_oldu.mean()*100:.1f} · {ey.pnl.mean()*1e4:.1f} bp")
    # eski coinlerin oynaklık / trend davranışı zaman içinde
    oz = []
    for y in range(2021, 2027):
        m = (vol30.index.year == y)
        v = vol30[m]; a = yas_g.reindex(v.index)[v.columns]
        oz.append(dict(yil=y, genc_vol_med=np.nanmedian(v.values[(a.values < 365)]), yasli_vol_med=np.nanmedian(v.values[(a.values >= 730)]),
                       genc_fund_med=np.nanmedian(fund30[m].values[(yas_g.reindex(fund30[m].index)[fund30.columns].values < 365)]),
                       yasli_fund_med=np.nanmedian(fund30[m].values[(yas_g.reindex(fund30[m].index)[fund30.columns].values >= 730)])))
    OZ = pd.DataFrame(oz); print("  evren oynaklığı ve funding (yıllık %, medyan; coin-gün):\n" + OZ.round(1).to_string(index=False)); OZ.to_csv(f"{D}/yas_ozellik_yil.csv", index=False)

    # ================= 5) risk
    print("\n[ÖLÇÜM] 5) YENİ COİN RİSKLERİ (4 sa veri; coin-bar yaşı gruplarına göre; 2021+)")
    H4 = Hl["H"].reindex_like(C4); L4 = Hl["L"].reindex_like(C4); O4_ = Hl["O"].reindex_like(C4)
    Y4 = YAS.reindex_like(C4) / 6
    m21 = C4.index >= "2021-01-01"
    r24 = (C4 / C4.shift(6) - 1)[m21]; bosluk = (O4_ / C4.shift(1) - 1).abs()[m21]
    fz = ODE[m21].abs(); ya = Y4[m21]
    yg = pd.DataFrame(np.select([ya.values <= 30, ya.values <= 90, ya.values <= 180, ya.values <= 365, ya.values <= 730], lab[:5], lab[5]), index=ya.index, columns=ya.columns).where(ya.notna())
    hv = HAC.reindex_like(C4)[m21]
    RK = []
    for gname in lab:
        mm = (yg == gname).values & np.isfinite(r24.values)
        n = mm.sum()
        if n == 0: continue
        rv = r24.values[mm]; bv = bosluk.values[(yg == gname).values]; fv_ = fz.values[(yg == gname).values]; hh = hv.values[(yg == gname).values]
        RK.append(dict(yas_grup=gname, coin_bar=int(n), cokus_24s_30=(rv <= -0.30).mean() * 1e4, sicrama_24s_50=(rv >= 0.50).mean() * 1e4,
                       bosluk_5pct=np.nanmean(bv > 0.05) * 1e4, funding_asiri_05=np.nanmean(fv_ >= 0.005) * 1e4, funding_asiri_1=np.nanmean(fv_ >= 0.01) * 1e4,
                       hacim_med_musd=np.nanmedian(hh) / 1e6, hacim_p10_musd=np.nanquantile(hh[np.isfinite(hh)], .1) / 1e6))
    RK = pd.DataFrame(RK)
    print("  (1 / 10.000 coin-bar: 24 sa ≤ −%30 çöküş · 24 sa ≥ +%50 sıçrama · açılış boşluğu > %5 · |funding| ≥ %0,5 / ≥ %1 ödeme; hacim panel ölçüsü M$)\n"
          + RK.round(2).to_string(index=False)); RK.to_csv(f"{D}/risk_yas.csv", index=False)
    # delist riski: kohort coinlerinin dönem içinde verisi biten payı (yaşa göre)
    dl = K.assign(omur=(K.sembol.map(lv) - K.liste).dt.days)
    dd = dl[dl.delist]
    print(f"  delist: 2021+ listelenen {len(K)} coinden {int(K.delist.sum())}'inin verisi 2026-09 öncesi bitti (%{K.delist.mean()*100:.1f}); ömür medyanı "
          f"{dd.omur.median():.0f} g · ilk yılında biten {int((dd.omur < 365).sum())} coin · bu coinlerin toplam net katkısı "
          f"{G[G.sembol.isin(dd.sembol)].net.sum()*100:+.1f} puan")
    # gerçekleşebilir emir büyüklüğü: bot tutarken coin hacmi
    hb = G21[(G21.bw > 0)].copy()
    hb["kitap_usd_2000"] = hb.bw * 2000; hb["kitap_usd_100k"] = hb.bw * 1e5
    hz = hb.groupby("yas_grup", observed=True).agg(hacim_med_musd=("hacim", lambda s: s.median() / 1e6), hacim_p5_musd=("hacim", lambda s: s.quantile(.05) / 1e6),
                                                   poz_100k_hacim_payi_p95=("kitap_usd_100k", lambda s: (s / hb.loc[s.index, "hacim"]).quantile(.95) * 1e4))
    print("  bot pozisyondayken coin hacmi (panel, M$) ve 100.000 $ kitapta pozisyonun hacme oranı (%95, baz puan):\n" + hz.round(2).to_string())
    hz.to_csv(f"{D}/likidite_yas.csv")
    print("  spread / emir defteri derinliği: VERİ YOK (ölçülemedi)")
    # TP'de kazandırıp taşımada kaybettiren coinler
    cc = G21.groupby("sembol").agg(tp=("tp", "sum"), tasima=("net", "sum"), ilk_yas=("yas", "min"))
    cc["tasima"] = cc.tasima - cc.tp; cc["net"] = cc.tp + cc.tasima; cc *= [100, 100, 1, 100]
    cc["genc_ilk"] = cc.ilk_yas < 365
    ters = cc[(cc.tp > 0) & (cc.net < 0)].sort_values("net")
    print(f"  TP'de kazandırıp toplamda kaybettiren coin: {len(ters)} (genç başlayan %{ters.genc_ilk.mean()*100:.0f}) · TP {ters.tp.sum():+.1f} · taşıma "
          f"{ters.tasima.sum():+.1f} · net {ters.net.sum():+.1f} puan; en kötü 10:\n" + ters.head(10).round(2).to_string())
    ters.to_csv(f"{D}/tp_kazanip_tasimada_kaybeden.csv")
    print(f"  karşılaştırma: genç başlayan coinlerde TP {cc[cc.genc_ilk].tp.sum():+.1f}, taşıma {cc[cc.genc_ilk].tasima.sum():+.1f} · yaşlı başlayan TP "
          f"{cc[~cc.genc_ilk].tp.sum():+.1f}, taşıma {cc[~cc.genc_ilk].tasima.sum():+.1f}")

    # ================= 6) gerçek zamanlı tespit
    print("\n[ÖLÇÜM] 6) LİSTELEME AKIŞI GÖSTERGELERİ -> SONRAKİ 30 / 60 / 90 g (kronolojik; o gün bilinen)")
    gun = BAZ.index[BAZ.index >= "2021-01-01"]
    lst = pd.Series(1, index=pd.DatetimeIndex([fv[s].normalize() for s in coins])).groupby(level=0).sum().reindex(pd.date_range("2020-01-01", gun[-1])).fillna(0)
    Fz = pd.DataFrame(index=gun)
    for w in (30, 90, 180): Fz[f"liste{w}"] = lst.rolling(w).sum().reindex(gun)
    ya_g = yas_g.reindex(gun)
    genc_m = (ya_g < 365) & Cg.reindex(gun).notna()
    Fz["genc_coin"] = genc_m.sum(axis=1)
    Fz["genc_vol"] = vol30.reindex(gun).where(genc_m).median(axis=1)
    Fz["genc_fund"] = fund30.reindex(gun).where(genc_m).median(axis=1)
    Fz["genc_hacim"] = np.log(hac_g.reindex(gun).where(genc_m).median(axis=1).clip(lower=1))
    for w in (30, 60, 90): Fz[f"ileri{w}"] = BAZ.reindex(gun)[::-1].rolling(w).sum()[::-1].shift(-1)
    Fz.to_csv(f"{D}/akis_ozellik.csv")
    oz_ = ["liste30", "liste90", "liste180", "genc_coin", "genc_vol", "genc_fund", "genc_hacim"]
    sinir = pd.Timestamp("2023-12-31"); rng = np.random.default_rng(694); RT = []
    for w in (30, 60, 90):
        d = Fz.dropna(subset=oz_ + [f"ileri{w}"])
        tr = d[d.index <= sinir - pd.Timedelta(days=w)]; te = d[d.index > sinir]
        for k in oz_:
            # eğitimde işaret ve eğim; testte Spearman ve dairesel kaydırmalı p
            b = np.polyfit(tr[k], tr[f"ileri{w}"], 1)[0]
            rho_tr = tr[k].corr(tr[f"ileri{w}"], method="spearman"); rho_te = te[k].corr(te[f"ileri{w}"], method="spearman")
            yv = te[f"ileri{w}"].values; xv = te[k].rank().values; n = len(yv); nul = []
            for _ in range(1000):
                s = rng.integers(w + 15, n - w - 15); nul.append(np.corrcoef(xv, pd.Series(np.roll(yv, s)).rank().values)[0, 1])
            nul = np.abs(np.array(nul))
            # eğitimdeki işaretle tahmin: test korelasyonu aynı işaretli mi
            # ortak zaman eğilimi kontrolü: testte iki seri de tarihe göre doğrusal eğilimden arındırılır
            tt = np.arange(n)
            rx = te[k].values - np.polyval(np.polyfit(tt, te[k].values, 1), tt); ry = yv - np.polyval(np.polyfit(tt, yv, 1), tt)
            rho_eg = np.corrcoef(rx, ry)[0, 1]
            # zarar ayrımı: testte sonraki ufuk getirisi < 0 olan günleri ayırt ediyor mu (AUC; eğitim işaretiyle)
            from sklearn.metrics import roc_auc_score
            yz = (yv < 0).astype(int)
            auc = roc_auc_score(yz, -np.sign(rho_tr) * te[k].values) if 0 < yz.sum() < n else np.nan
            RT.append(dict(ufuk=w, ozellik=k, rho_egitim=rho_tr, rho_test=rho_te, ayni_isaret=np.sign(rho_tr) == np.sign(rho_te), p_dairesel=(nul >= abs(rho_te)).mean(),
                           rho_test_egilimsiz=rho_eg, zarar_auc=auc, zarar_orani=yz.mean() * 100, test_n=n, bagimsiz_blok=n // w))
    RT = pd.DataFrame(RT); print(RT.round(3).to_string(index=False)); RT.to_csv(f"{D}/akis_ongoru.csv", index=False)
    print(f"  eğitim 2021-01 – {sinir.date()} (ufuk kadar ambargo) · test 2024-01 – sonu · çoklu test: {len(RT)} test, Bonferroni eşiği {0.05/len(RT):.4f}")

    bek = ["yas_grup_2021-2026.csv", "yas_grup_2024-2026.csv", "tabakalama.csv", "regresyon.csv", "kohort_coin.csv", "kohort_donem.csv", "kohort_ceyrek.csv",
           "kohort_ay.csv", "karsi_olgu.csv", "senaryo_model.csv", "eski_coin_kapasite.csv", "yas_ozellik_yil.csv", "risk_yas.csv", "likidite_yas.csv",
           "tp_kazanip_tasimada_kaybeden.csv", "akis_ozellik.csv", "akis_ongoru.csv", "senaryo_coinleri.json"] + \
          [f"E_{a}_{h}.pkl" for a in ["P0", "Y365K", "L25_a", "L25_b", "L50_a", "L50_b", "L75_a", "L75_b", "DUR24", "DUR25"] for h in (0, 1)] + \
          [f"gk_Y365K_{h}.pkl" for h in (0, 1)] + [f"katki_Y365K_{h}.pkl" for h in (0, 1)]
    yok = [b for b in bek if not os.path.exists(f"{D}/{b}")]
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if not yok else f"EKSİK: {yok}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
