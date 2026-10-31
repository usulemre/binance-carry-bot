#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 693 — PİYASA YOLU, FİTİL AVANTAJI VE REJİM DAYANIKLILIĞI. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Girdi: madde 690 (bileşenler, gk), 691 (seviye kayıtlı çıkış defteri, kitap oynaklığı), 692 (pozisyon defteri, TP açık / kapalı motor
serileri) + fiyat zemini. Rejim etiketleri NEDENSEL: gün d'nin etiketi d kapanışına kadarki veriyle hesaplanır ve d+1 getirisine uygulanır;
oynaklık / yol eşikleri GENİŞLEYEN (yalnız geçmiş) dağılımdan.
Karşı-olgu (yeni coin yok): motor kopyası /tmp/g33_m693.py (g33.py'nin değişmemiş kopyası) YAS_GUN=180 / 365 ortam değişkeniyle
(evrene alınacak asgari listeleme yaşı; bu bir STRES SENARYOSUDUR, önerilen ayar değildir). Parite: ortam değişmeden kopya = g33.py.
  python3 arastirma_m693_rejim.py kos      -> /tmp/m693/E_<senaryo>_<hiza>.pkl (tek işçi)
  python3 arastirma_m693_rejim.py analiz   -> /tmp/m693/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle, shutil
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m693"; os.makedirs(D, exist_ok=True)
S690, S691, S692 = "/tmp/m690", "/tmp/m691", "/tmp/m692"
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
SEN = {"Y180": {"YAS_GUN": "180"}, "Y365": {"YAS_GUN": "365"}}
NF = 15


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m693.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    shutil.copy(os.path.join(R, "g33.py"), "/tmp/g33_m693.py")
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · kopya vs g33.py referansı -> {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    for ad, ek in SEN.items():
        for h in (0, 1): print(ad, h, _kos1(ad, ek, h), flush=True)


# ------------------------------------------------------------------------------------------------ yardımcılar
def _seri_yol(yol, ad):
    hedef = f"{D}/M357_EK_{ad}.pkl"
    if not os.path.exists(hedef): os.symlink(yol, hedef)
    M.CIKTI = D; s = M.gunluk(f"M357_EK_{ad}"); s.index = pd.to_datetime(s.index); return s


def seri(ad):
    if ad == "BAZ": return sum(_seri_yol(REF.format(h=h), f"BAZ_{h}") for h in (0, 1)) / 2
    kaynak = S692 if ad in ("YOK", "F0", "F50", "G7", "G14", "G3") else D
    return sum(_seri_yol(f"{kaynak}/E_{ad}_{h}.pkl", f"{ad}_{h}") for h in (0, 1)) / 2


def _olc(d):
    d = d.dropna()
    if len(d) < 20: return dict(gun=len(d), cagr=np.nan, sharpe=np.nan, maks_dd=np.nan)
    e = (1 + d).cumprod()
    return dict(gun=len(d), cagr=(e.iloc[-1] ** (365.25 / len(d)) - 1) * 100, sharpe=d.mean() / d.std() * np.sqrt(365.25),
                maks_dd=(e / e.cummax() - 1).min() * 100)


def _genisleyen_q(s, q, min_n=90):
    return s.expanding(min_n).quantile(q)


def gunluk_panel():
    """Günlük OHLC (UTC gün), coin günlük getirisi."""
    yol = f"{D}/gunluk_ohlc.pkl"
    if os.path.exists(yol): return pd.read_pickle(yol)
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); Hl = pickle.load(open("/tmp/hlo.pkl", "rb"))
    C = Z["C"]; O = Hl["O"].reindex_like(C); H = Hl["H"].reindex_like(C); L = Hl["L"].reindex_like(C)
    g = C.index.floor("D")
    out = dict(C=C.groupby(g).last(), O=O.groupby(g).first(), H=H.groupby(g).max(), L=L.groupby(g).min())
    pd.to_pickle(out, yol); return out


def ozellikler(P):
    """Coin bazında NEDENSEL 30 g özellikler (gün d kapanışı dahil): getiri, oynaklık, verimlilik oranı (ER = |net| / Σ|günlük|),
    fitil payı (1 − |kapanış − açılış| / (yüksek − düşük), 30 g ort.), gün içi aralık ((yüksek − düşük) / kapanış, 30 g ort.)."""
    yol = f"{D}/ozellik.pkl"
    if os.path.exists(yol): return pd.read_pickle(yol)
    C, O, H, L = P["C"], P["O"], P["H"], P["L"]
    lr = np.log(C).diff()
    r30 = C / C.shift(30) - 1
    vol = lr.rolling(30, min_periods=20).std() * np.sqrt(365) * 100
    er = (np.log(C / C.shift(30))).abs() / lr.abs().rolling(30, min_periods=20).sum()
    rng = (H - L).where(H > L)
    fitil = (1 - (C - O).abs() / rng).rolling(30, min_periods=20).mean()
    aralik = ((H - L) / C).rolling(30, min_periods=20).mean()
    out = dict(r30=r30, vol=vol, er=er, fitil=fitil, aralik=aralik)
    pd.to_pickle(out, yol); return out


def kitap_agirlik():
    G = pd.concat([pd.read_pickle(f"{S690}/gk_{h}.pkl").assign(h=h) for h in (0, 1)])
    G["bw"] = G.ort_poz.abs() * G.bar / 6; G["gun"] = pd.to_datetime(G.gun)
    return (G.groupby(["gun", "sembol"]).bw.sum() / 2).unstack().fillna(0)


def analiz():
    pd.set_option("display.width", 230); pd.set_option("display.max_columns", 30)
    P = gunluk_panel(); F = ozellikler(P); W = kitap_agirlik()
    B = pd.read_csv(f"{S690}/gun_kitap_bilesen.csv", parse_dates=["gun"], index_col="gun")
    V = pd.read_csv(f"{S691}/gun_tp_vol.csv", parse_dates=["gun"], index_col="gun")
    E = pd.read_pickle(f"{S692}/epizot.pkl")
    BAZ, YOK = seri("BAZ"), seri("YOK")
    gun = BAZ.index[BAZ.index >= "2020-08-01"]
    W = W.reindex(index=gun).fillna(0)

    # ================= 1) rejim etiketleri (gün d özellikleri -> d+1 getirisi)
    def kitap_ort(X):
        X = X.reindex(index=gun, columns=W.columns)
        w = W.where(X.notna(), 0)
        return (X.fillna(0) * w).sum(axis=1) / w.sum(axis=1).replace(0, np.nan)
    btc = {k: F[k]["BTCUSDT"].reindex(gun) for k in ("r30", "vol", "er")}
    kit = {k: kitap_ort(F[k]) for k in ("r30", "vol", "er", "fitil", "aralik")}
    # kitabın long / short sepetlerinin 30 g getirisi
    Wl = pd.concat([pd.read_pickle(f"{S690}/gk_{h}.pkl") for h in (0, 1)]); Wl["gun"] = pd.to_datetime(Wl.gun)
    Wl["sw"] = Wl.ort_poz * Wl.bar / 6
    Ws = Wl.groupby(["gun", "sembol"]).sw.sum().unstack().reindex(index=gun).fillna(0) / 2
    r30k = F["r30"].reindex(index=gun, columns=Ws.columns)
    kit["long_r30"] = (r30k.fillna(0) * Ws.clip(lower=0)).sum(axis=1) / Ws.clip(lower=0).sum(axis=1).replace(0, np.nan)
    kit["short_r30"] = (r30k.fillna(0) * (-Ws.clip(upper=0))).sum(axis=1) / (-Ws.clip(upper=0)).sum(axis=1).replace(0, np.nan)
    evren_r30 = F["r30"].reindex(gun).median(axis=1)
    L = pd.DataFrame(index=gun)
    L["BTC yön"] = np.select([btc["r30"] > 0.10, btc["r30"] < -0.10], ["güçlü yükseliş", "güçlü düşüş"], "yatay")
    L["BTC oynaklık"] = np.where(btc["vol"] >= _genisleyen_q(btc["vol"], 0.5), "yüksek", "düşük")
    L["BTC yol"] = np.select([btc["er"] >= _genisleyen_q(btc["er"], 2 / 3), btc["er"] <= _genisleyen_q(btc["er"], 1 / 3)],
                             ["kalıcı tek yön", "sık geri dönüş"], "ara")
    L["Evren yön"] = np.select([evren_r30 > 0.15, evren_r30 < -0.15], ["güçlü yükseliş", "güçlü düşüş"], "yatay")
    L["Kitap oynaklık"] = np.where(kit["vol"] >= _genisleyen_q(kit["vol"], 0.5), "yüksek", "düşük")
    L["Kitap yol"] = np.select([kit["er"] >= _genisleyen_q(kit["er"], 2 / 3), kit["er"] <= _genisleyen_q(kit["er"], 1 / 3)],
                               ["kalıcı tek yön", "sık geri dönüş"], "ara")
    L["Kitap fitil"] = np.select([kit["fitil"] >= _genisleyen_q(kit["fitil"], 2 / 3), kit["fitil"] <= _genisleyen_q(kit["fitil"], 1 / 3)],
                                 ["yüksek fitil", "düşük fitil"], "ara")
    L["Long sepeti yön"] = np.select([kit["long_r30"] > 0.20, kit["long_r30"] < -0.20], ["güçlü yükseliş", "güçlü düşüş"], "yatay")
    L["Short sepeti yön"] = np.select([kit["short_r30"] > 0.20, kit["short_r30"] < -0.20], ["güçlü yükseliş", "güçlü düşüş"], "yatay")
    # ilk 90 gün genişleyen eşik yok -> etiket yok
    for c in ["BTC oynaklık", "BTC yol", "Kitap oynaklık", "Kitap yol", "Kitap fitil"]:
        L.loc[L.index < gun[0] + pd.Timedelta(days=90), c] = None
    Ln = L.shift(1)   # NEDENSEL: gün d etiketi d+1 getirisine
    L.to_csv(f"{D}/rejim_etiket.csv")
    Bc = B.reindex(gun); tps = V.tp_sayi.reindex(gun)
    E["bas_g"] = E.bas.dt.normalize(); ep_bas = E.groupby("bas_g").size().reindex(gun).fillna(0) / 2
    rows = []
    for col in Ln.columns:
        for et in [x for x in pd.unique(Ln[col].dropna())]:
            m = Ln[col] == et
            o = _olc(BAZ.reindex(gun)[m]); oy = _olc(YOK.reindex(gun)[m])
            ep = E[E.bas_g.map(Ln[col]) == et]
            rows.append(dict(boyut=col, rejim=et, gun_pay=m.mean() * 100, **o, tp_yok_cagr=oy["cagr"], tp_yok_sharpe=oy["sharpe"],
                             tp_yok_dd=oy["maks_dd"], tp_degeri_cagr=o["cagr"] - oy["cagr"],
                             tp_yillik=Bc.tp[m].mean() * 36525, funding_yillik=Bc.funding[m].mean() * 36525,
                             long_fiyat_yillik=Bc.long_fiyat[m].mean() * 36525, short_fiyat_yillik=Bc.short_fiyat[m].mean() * 36525,
                             tp_olay_gun=tps[m].mean(), yeni_poz_gun=ep_bas[m].mean(),
                             tp_orani=ep.tp_oldu.mean() * 100 if len(ep) else np.nan, poz_sure=ep.sure_gun.mean() if len(ep) else np.nan))
    RJ = pd.DataFrame(rows).sort_values(["boyut", "cagr"], ascending=[True, False])
    RJ.to_csv(f"{D}/rejim_tablo.csv", index=False)
    print("[ÖLÇÜM] 1) REJİMLER (nedensel etiket; CAGR / DD rejim günleri birleştirilerek; bileşenler yıllık puan; tp_degeri = TP açık − kapalı CAGR)")
    print(RJ.round(1).to_string(index=False))

    # ================= 2) fiyat yolu (pozisyon bazında)
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C4 = Z["C"]; Hl = pickle.load(open("/tmp/hlo.pkl", "rb"))
    H4 = Hl["H"].reindex_like(C4).values; L4 = Hl["L"].reindex_like(C4).values; O4 = Hl["O"].reindex_like(C4).values; Cv = C4.values
    X = pd.concat([pd.read_pickle(f"{S691}/cikis_S_{h}.pkl").assign(h=h) for h in (0, 1)], ignore_index=True)
    X = X[X.tur.isin(["TP", "KAD"]) & X.seviye.notna()].copy(); X["zaman"] = pd.to_datetime(X.zaman)
    ilk = X.groupby(["h", "sembol", "yon", "zaman"]).apply(lambda d: np.average(d.fiyat, weights=d.w), include_groups=False).rename("ilk_fiyat").reset_index()
    E = E.merge(ilk.rename(columns={"sembol": "sem", "zaman": "ilk_olay"}), on=["h", "sem", "yon", "ilk_olay"], how="left")
    ri = C4.index.get_indexer(E.bas); ci = C4.columns.get_indexer(E["sem"])
    si = C4.index.get_indexer(E.son.clip(upper=C4.index[-1]), method="pad")
    fi = C4.index.get_indexer(E.ilk_olay.fillna(pd.Timestamp("2100-01-01")))
    n4 = len(C4); mfe = np.full(len(E), np.nan); mae = mfe.copy(); pre_mae = mfe.copy(); post_fav = mfe.copy(); post_c5 = mfe.copy(); cikis_r = mfe.copy()
    for j in range(len(E)):
        r, c, s = ri[j], ci[j], si[j]
        if r < 0 or c < 0 or s <= r: continue
        e0 = E.giris_fiyat.iat[j]
        if not np.isfinite(e0) or e0 <= 0: continue
        up = E.yon.iat[j] > 0
        hh, ll = H4[r + 1:s + 1, c], L4[r + 1:s + 1, c]
        if up: mfe[j] = np.nanmax(hh) / e0 - 1; mae[j] = np.nanmin(ll) / e0 - 1
        else:  mfe[j] = 1 - np.nanmin(ll) / e0; mae[j] = 1 - np.nanmax(hh) / e0
        cikis_r[j] = (Cv[s, c] / e0 - 1) if up else (1 - Cv[s, c] / e0)
        f = fi[j]
        if f > r and np.isfinite(E.ilk_fiyat.iat[j]):
            pf = E.ilk_fiyat.iat[j]
            pl = L4[r + 1:f, c] if up else H4[r + 1:f, c]       # ilk olay barından ÖNCE
            if len(pl) and np.isfinite(pl).any(): pre_mae[j] = (np.nanmin(pl) / e0 - 1) if up else (1 - np.nanmax(pl) / e0)
            else: pre_mae[j] = 0.0
            q1 = min(n4 - 1, f + 30)
            if q1 > f:
                if up: post_fav[j] = np.nanmax(H4[f + 1:q1 + 1, c]) / pf - 1; post_c5[j] = Cv[q1, c] / pf - 1
                else:  post_fav[j] = 1 - np.nanmin(L4[f + 1:q1 + 1, c]) / pf; post_c5[j] = 1 - Cv[q1, c] / pf
    E["mfe"], E["mae_bar"], E["pre_mae"], E["post_fav5"], E["post_c5"], E["cikis_r"] = mfe, mae, pre_mae, post_fav, post_c5, cikis_r
    # giriş anındaki (nedensel) coin fitil / aralık
    def _at(Fk):
        Fk = Fk.copy(); Fk.index = pd.to_datetime(Fk.index)
        rr = Fk.index.get_indexer(E.bas.dt.normalize() - pd.Timedelta(days=1)); cc = Fk.columns.get_indexer(E["sem"])
        v = np.full(len(E), np.nan); ok = (rr >= 0) & (cc >= 0); v[ok] = Fk.values[rr[ok], cc[ok]]; return v
    E["fitil_on"] = _at(F["fitil"]); E["aralik_on"] = _at(F["aralik"]); E["er_on"] = _at(F["er"]); E["vol_on"] = _at(F["vol"])
    # pozisyon süresince günlük fitil / aralık (eşzamanlı)
    print("\n[ÖLÇÜM] 2) FİYAT YOLU (16.619 pozisyon; bar içi MFE / MAE girişe göre)")
    for yn, ad in ((1, "long"), (-1, "short")):
        e = E[E.yon == yn]
        print(f"  {ad}: MFE medyan {e.mfe.median()*100:.1f}% (%90 {e.mfe.quantile(.9)*100:.1f}) · MAE medyan {e.mae_bar.median()*100:.1f}% (%10 "
              f"{e.mae_bar.quantile(.1)*100:.1f}) · çıkış getirisi medyan {e.cikis_r.median()*100:.1f}%")
    b20 = E[E.mfe >= 0.20]
    print(f"  aşırı seviyeden geri dönüş: MFE ≥ %20 olan {len(b20)} pozisyonun %{(b20.cikis_r <= b20.mfe/2).mean()*100:.0f}'i kapanışta kazancın yarısından "
          f"fazlasını geri verdi (TP'li %{(b20[b20.tp_oldu].cikis_r <= b20[b20.tp_oldu].mfe/2).mean()*100:.0f} · TP'siz "
          f"%{(b20[~b20.tp_oldu].cikis_r <= b20[~b20.tp_oldu].mfe/2).mean()*100:.0f})")
    zi = C4.index.get_indexer(X.zaman); cj = C4.columns.get_indexer(X.sembol)
    kap = Cv[zi, cj]; geri = np.where(X.yon > 0, kap < X.seviye, kap > X.seviye)
    k6 = Cv[np.minimum(zi + 6, n4 - 1), cj]; geri24 = np.where(X.yon > 0, k6 < X.seviye, k6 > X.seviye)
    print(f"  TP / kademe seviyesine ulaşan barların %{np.nanmean(geri)*100:.0f}'i seviyenin GERİSİNDE kapandı (fitil dokunuşu); 24 sa sonra kapanış "
          f"seviyenin gerisinde: %{np.nanmean(geri24)*100:.0f} (long %{np.nanmean(geri24[X.yon.values>0])*100:.0f} · short "
          f"%{np.nanmean(geri24[X.yon.values<0])*100:.0f})")
    pd.DataFrame({"geri_bar": geri, "geri_24s": geri24, "tur": X.tur.values, "yon": X.yon.values}).to_csv(f"{D}/tp_bar_geri.csv", index=False)
    # TP başarısı ~ giriş anındaki yol özellikleri (tercil)
    T2 = []
    for k, ad in (("fitil_on", "fitil payı"), ("aralik_on", "gün içi aralık"), ("er_on", "verimlilik (ER)"), ("vol_on", "oynaklık")):
        for yn, yad in ((1, "long"), (-1, "short")):
            e = E[(E.yon == yn) & E[k].notna()]; q = pd.qcut(e[k], 3, labels=["düşük", "orta", "yüksek"])
            t = e.groupby(q, observed=True).agg(poz=("ep", "size"), deger=(k, "median"), tp_orani=("tp_oldu", "mean"), mfe_med=("mfe", "median"),
                                                net_bp=("pnl", "mean"))
            t["tp_orani"] *= 100; t["mfe_med"] *= 100; t["net_bp"] *= 1e4; t.insert(0, "yon", yad); t.insert(0, "ozellik", ad); T2.append(t)
    T2 = pd.concat(T2); T2.to_csv(f"{D}/yol_tercil.csv")
    print("  [ÖLÇÜM] giriş ÖNCESİ 30 g coin özelliği tercili -> TP oranı / MFE / pozisyon başı net (bp, kitap):\n" + T2.round(2).to_string())

    # ================= 3) trend / geri dönüş kategorileri
    tp = E.tp_oldu
    kat = np.select([~tp, tp & (E.pre_mae <= -0.05), tp & (E.post_c5 >= 0.05), tp & (E.post_c5 <= -0.05)],
                    ["TP'ye ulaşamayan", "TP öncesi geri dönüş (≥%5 ters)", "TP sonrası trend devam (5 g'de ≥%5 lehte)",
                     "TP sonrası ters yön (5 g'de ≥%5 aleyhte)"], "TP'li, sonrası nötr")
    E["kategori"] = kat
    K = E.groupby("kategori").agg(poz=("ep", "size"), net_puan=("pnl", "sum"), fiyat_puan=("fiy", "sum"), funding_puan=("fon", "sum"),
                                  sure=("sure_gun", "mean"), mfe_med=("mfe", "median"), post_fav5_med=("post_fav5", "median"))
    K[["net_puan", "fiyat_puan", "funding_puan"]] *= 50; K["mfe_med"] *= 100; K["post_fav5_med"] *= 100; K["pay"] = K.poz / K.poz.sum() * 100
    print("\n[ÖLÇÜM] 3) KATEGORİLER (puan, iki hiza ort.):\n" + K.round(2).to_string()); K.to_csv(f"{D}/kategori.csv")
    tpE = E[tp]
    xt = pd.crosstab(np.where(tpE.pre_mae <= -0.05, "önce ≥%5 ters", "önce ters yok"),
                     np.select([tpE.post_c5 >= 0.05, tpE.post_c5 <= -0.05], ["sonra devam", "sonra ters"], "sonra nötr"),
                     values=tpE.pnl, aggfunc="sum") * 50
    print("  TP'li pozisyonlar: önce × sonra net puan:\n" + xt.round(1).to_string())
    print(f"  TP'li pozisyonlarda ilk olaydan 5 g sonra kapanış medyanı {tpE.post_c5.median()*100:+.1f}% (long {tpE[tpE.yon>0].post_c5.median()*100:+.1f} · "
          f"short {tpE[tpE.yon<0].post_c5.median()*100:+.1f}); 5 g içinde lehte en iyi medyan {tpE.post_fav5.median()*100:+.1f}%")
    # TP açık / kapalı aynı aylar
    Am = pd.DataFrame({"BAZ": BAZ.resample("ME").sum(), "YOK": YOK.resample("ME").sum()}).loc["2020-08":] * 100
    Am["fark"] = Am.BAZ - Am.YOK
    km = pd.DataFrame({k: kit[k].resample("ME").mean() for k in ("fitil", "er", "vol", "aralik", "r30", "long_r30")})
    km["btc_er"] = btc["er"].resample("ME").mean(); km["btc_r30"] = btc["r30"].resample("ME").mean()
    Am = Am.join(km); Am.to_csv(f"{D}/ay_tp_acik_kapali.csv")
    print(f"\n  [ÖLÇÜM] TP açık − kapalı aylık getiri farkı: ort {Am.fark.mean():+.2f} · medyan {Am.fark.median():+.2f} · TP'nin kazandırdığı ay "
          f"%{(Am.fark>0).mean()*100:.0f} · en iyi {Am.fark.max():+.1f} ({Am.fark.idxmax():%Y-%m}) · en kötü {Am.fark.min():+.1f} ({Am.fark.idxmin():%Y-%m})")
    print("  aylık fark ile korelasyon (eşzamanlı / bir önceki ayın değeri):")
    for k in ["fitil", "er", "vol", "aralik", "r30", "long_r30", "btc_er", "btc_r30"]:
        print(f"   {k:9s}: {Am.fark.corr(Am[k]):+.2f} / {Am.fark.corr(Am[k].shift(1)):+.2f} · Spearman eşzamanlı {Am.fark.corr(Am[k], method='spearman'):+.2f}"
              f" · BAZ getirisi ile {Am.BAZ.corr(Am[k]):+.2f}")
    # açıklanan pay: aylık BAZ getirisi ~ eşzamanlı fitil + er + vol (R²)
    from numpy.linalg import lstsq
    def r2(y, cols, df):
        d = df[[y] + cols].dropna(); A = np.c_[np.ones(len(d)), d[cols].values]; b = lstsq(A, d[y].values, rcond=None)[0]
        res = d[y].values - A @ b; return 1 - res.var() / d[y].values.var(), len(d)
    for y in ("BAZ", "fark"):
        for cols in (["fitil"], ["er"], ["vol"], ["fitil", "er"], ["fitil", "er", "vol"], ["fitil", "er", "vol", "long_r30"]):
            rr, n = r2(y, cols, Am)
            print(f"   R² {y:5s} ~ {'+'.join(cols):26s}: {rr:.2f} (n {n}, eşzamanlı)")

    # ================= 4) gerçek tarihsel gruplar (aylar)
    print("\n[ÖLÇÜM] 4) GERÇEK TARİHSEL GRUPLAR (aylar; kitabın tuttuğu coinlerin özellikleri)")
    G4 = []
    for k, ad in (("fitil", "fitil payı"), ("er", "trend sürekliliği (ER)"), ("aralik", "gün içi aralık")):
        for zaman, s in (("eşzamanlı (betimleyici)", Am[k]), ("önceki ay (nedensel)", Am[k].shift(1))):
            med = s.expanding(6).median().shift(1) if zaman.startswith("önceki") else s.median()
            hi = s >= med; ok = s.notna() & (pd.Series(med, index=s.index).notna() if not np.isscalar(med) else True)
            for et, m in (("yüksek", hi & ok), ("düşük", (~hi) & ok)):
                G4.append(dict(ozellik=ad, zaman=zaman, grup=et, ay=int(m.sum()), baz_ay=Am.BAZ[m].mean(), yok_ay=Am.YOK[m].mean(),
                               fark=Am.fark[m].mean(), zarar_ay=(Am.BAZ[m] < 0).mean() * 100, tp_kazandirdi=(Am.fark[m] > 0).mean() * 100))
    G4 = pd.DataFrame(G4); print(G4.round(2).to_string(index=False)); G4.to_csv(f"{D}/gercek_gruplar.csv", index=False)
    # 2x2: fitil × ER (eşzamanlı)
    fq = Am.fitil >= Am.fitil.median(); eq = Am.er >= Am.er.median()
    t = Am.groupby([np.where(fq, "yüksek fitil", "düşük fitil"), np.where(eq, "kalıcı (yüksek ER)", "geri dönüşlü (düşük ER)")])[["BAZ", "YOK", "fark"]].agg(["mean", "size"])
    print("  fitil × trend sürekliliği (eşzamanlı, ay ortalaması %):\n" + t.round(2).to_string())

    # ================= 5) yeni coinler (2024-2026)
    print("\n[ÖLÇÜM] 5) YENİ COİN BAĞIMLILIĞI (yaş = vadeli işlem verisinin başladığı günden; o gün bilinen)")
    Pn = pickle.load(open("/tmp/panel.pkl", "rb"))["YAS"]; yas = (Pn.groupby(Pn.index.floor("D")).last() / 6)
    Gc = pd.read_csv(f"{S690}/gun_coin_bilesen.csv", parse_dates=["gun"])
    Gc["net"] = Gc.tp + Gc.funding + Gc.fiyat + Gc.stop - Gc.komisyon
    yl = yas.stack().rename("yas").reset_index(); yl.columns = ["gun", "sembol", "yas"]
    Gc = Gc.merge(yl, on=["gun", "sembol"], how="left")
    Wst = W.stack().rename("bw").reset_index(); Wst.columns = ["gun", "sembol", "bw"]
    Gc = Gc.merge(Wst, on=["gun", "sembol"], how="left")
    bins = [0, 90, 180, 365, 730, 1460, 1e9]; lab = ["<90 g", "90-180 g", "180-365 g", "1-2 yıl", "2-4 yıl", ">4 yıl"]
    Gc["yas_grup"] = pd.cut(Gc.yas, bins, labels=lab)
    g24 = Gc[Gc.gun >= "2024-01-01"]
    T5 = g24.groupby("yas_grup", observed=True).agg(net=("net", "sum"), tp=("tp", "sum"), funding=("funding", "sum"), fiyat=("fiyat", "sum"),
                                                    maruziyet=("bw", "sum"), coin=("sembol", "nunique"))
    T5[["net", "tp", "funding", "fiyat"]] *= 100; T5["net_payi"] = T5.net / T5.net.sum() * 100; T5["tp_payi"] = T5.tp / T5.tp.sum() * 100
    T5["maruziyet_payi"] = T5.maruziyet / T5.maruziyet.sum() * 100; T5["maruziyet_basi_yillik"] = T5.net / T5.maruziyet * 365
    # coin bazında zarar oranı (2024+ net) ve pozisyon bazında
    cz = g24.groupby(["sembol"]).agg(net=("net", "sum"), ilk_yas=("yas", "min"))
    cz["yas_grup"] = pd.cut(cz.ilk_yas, bins, labels=lab)
    T5["zararli_coin_pct"] = cz.groupby("yas_grup", observed=True).net.apply(lambda s: (s < 0).mean() * 100)
    E["yas_bas"] = [yas.at[d, s] if (d in yas.index and s in yas.columns) else np.nan for d, s in zip(E.bas.dt.normalize(), E["sem"])]
    e24 = E[E.bas >= "2024-01-01"].copy(); e24["yas_grup"] = pd.cut(e24.yas_bas, bins, labels=lab)
    pe = e24.groupby("yas_grup", observed=True).agg(poz=("ep", "size"), poz_basi_net_bp=("pnl", "mean"), zararli_poz=("pnl", lambda s: (s < 0).mean() * 100),
                                                    tp_orani=("tp_oldu", "mean"))
    pe["tp_orani"] *= 100; pe["poz_basi_net_bp"] *= 1e4
    T5 = T5.join(pe); print(T5.round(2).to_string()); T5.to_csv(f"{D}/yeni_coin_2024.csv")
    genc = Gc.yas < 365
    q = Gc[Gc.gun >= "2021-01-01"].assign(genc=genc, ceyrek=Gc.gun.dt.to_period("Q"))
    QT = q.groupby(["ceyrek", "genc"])[["net", "tp", "bw"]].sum().unstack()
    QQ = pd.DataFrame({"genc_net_payi": QT[("net", True)] / QT["net"].sum(axis=1) * 100, "genc_tp_payi": QT[("tp", True)] / QT["tp"].sum(axis=1) * 100,
                       "genc_maruziyet_payi": QT[("bw", True)] / QT["bw"].sum(axis=1) * 100,
                       "genc_net_puan": QT[("net", True)] * 100, "yasli_net_puan": QT[("net", False)] * 100})
    print("  çeyreklik: genç (< 1 yıl) coinlerin payı (2021'den; öncesinde 2020 veri başlangıcı yüzünden yaş kesik):\n" + QQ.round(1).to_string())
    QQ.to_csv(f"{D}/genc_ceyrek.csv")
    yy = q.assign(yil=q.gun.dt.year).groupby(["yil", "genc"]).net.sum().unstack() * 100
    yy["genc_maruziyet_basi"] = (q[q.genc].groupby(q.gun.dt.year).net.sum() / q[q.genc].groupby(q.gun.dt.year).bw.sum() * 365)
    yy["yasli_maruziyet_basi"] = (q[~q.genc].groupby(q.gun.dt.year).net.sum() / q[~q.genc].groupby(q.gun.dt.year).bw.sum() * 365)
    print("  yıl yıl net puan (genç / yaşlı) ve maruziyet başına yıllık getiri:\n" + yy.round(2).to_string())
    # sağkalım: verisi dönem bitmeden kesilen (listeden çıkan) coinler
    son = Z["C"].apply(lambda s: s.last_valid_index()); cik = son[son < pd.Timestamp("2026-09-01")].index
    gc = Gc[Gc.sembol.isin(cik)]
    print(f"  sağkalım: verisi 2026-09 öncesi biten {len(cik)} coin evrende VAR; bunların toplam net katkısı {gc.net.sum()*100:+.1f} puan "
          f"(genç iken {gc[gc.yas<365].net.sum()*100:+.1f})")
    # karşı-olgu: motor (YAS_GUN)
    print("  [ÖLÇÜM; senaryo VARSAYIM] motor karşı-olgusu (evrene asgari listeleme yaşı; boşalan yer yaşlı coinlere gider):")
    oz = [dict(senaryo="BAZ (asgari yaş 60 g)", **_olc(BAZ), cagr_2024=_olc(BAZ[BAZ.index >= "2024-01-01"])["cagr"])]
    eks = []
    for ad, aciklama in (("Y180", "asgari yaş 180 g"), ("Y365", "asgari yaş 365 g (1 yaşından genç coin yok)")):
        if all(os.path.exists(f"{D}/E_{ad}_{h}.pkl") for h in (0, 1)):
            s = seri(ad); oz.append(dict(senaryo=aciklama, **_olc(s), cagr_2024=_olc(s[s.index >= "2024-01-01"])["cagr"]))
            yyy = s.groupby(s.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100); oz[-1].update({f"y{k}": v for k, v in yyy.items()})
        else: eks.append(ad)
    yb = BAZ.groupby(BAZ.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100); oz[0].update({f"y{k}": v for k, v in yb.items()})
    OZ = pd.DataFrame(oz); print(OZ.round(1).to_string(index=False)); OZ.to_csv(f"{D}/yeni_coin_karsi_olgu.csv", index=False)
    if eks: print("  EKSİK SENARYO (başarılı sayılmadı):", eks)

    # ================= 6) en kötü rejimler gerçek zamanlı tespit edilebilir mi?
    print("\n[ÖLÇÜM] 6) EN KÖTÜ REJİMLER GERÇEK ZAMANLI")
    ileri = BAZ.reindex(gun)[::-1].rolling(30).sum()[::-1].shift(-1)
    kotu = RJ.nsmallest(5, "cagr")[["boyut", "rejim", "cagr", "gun_pay"]]
    print("  en düşük CAGR'li 5 nedensel rejim:\n" + kotu.round(1).to_string(index=False))
    rr = []
    for _, r_ in RJ.iterrows():
        m = L[r_.boyut] == r_.rejim       # gün d sonunda bilinen etiket -> d+1..d+30
        ok = ileri.notna() & L[r_.boyut].notna()
        a, b_ = ileri[m & ok], ileri[~m & ok]
        kal = (L[r_.boyut] == L[r_.boyut].shift(1))[m].mean()
        rr.append(dict(boyut=r_.boyut, rejim=r_.rejim, sonraki30_ort=a.mean() * 100, diger_ort=b_.mean() * 100,
                       sonraki30_zarar_pct=(a < 0).mean() * 100, diger_zarar_pct=(b_ < 0).mean() * 100, ertesi_gun_ayni_rejim=kal * 100))
    RR = pd.DataFrame(rr).sort_values("sonraki30_zarar_pct", ascending=False)
    print("  rejim etiketi aktifken sonraki 30 g (taban zarar oranı %"
          f"{(ileri.dropna()<0).mean()*100:.1f}):\n" + RR.round(1).to_string(index=False)); RR.to_csv(f"{D}/rejim_gercek_zaman.csv", index=False)
    # en kötü 10 ay: başında hangi etiketler vardı
    am = BAZ.resample("ME").sum().loc["2020-11":]; en_kotu = am.nsmallest(10)
    bas_et = pd.DataFrame({c: [L[c].asof(t - pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)) for t in en_kotu.index] for c in L.columns}, index=en_kotu.index.strftime("%Y-%m"))
    bas_et.insert(0, "getiri", en_kotu.values * 100)
    print("  en kötü 10 ay ve ay BAŞINDA bilinen etiketler:\n" + bas_et.round(1).to_string()); bas_et.to_csv(f"{D}/en_kotu_aylar_etiket.csv")

    E.to_pickle(f"{D}/epizot_yol.pkl")
    bek = ["rejim_etiket.csv", "rejim_tablo.csv", "tp_bar_geri.csv", "yol_tercil.csv", "kategori.csv", "ay_tp_acik_kapali.csv", "gercek_gruplar.csv",
           "yeni_coin_2024.csv", "genc_ceyrek.csv", "yeni_coin_karsi_olgu.csv", "rejim_gercek_zaman.csv", "en_kotu_aylar_etiket.csv", "epizot_yol.pkl"] + \
          [f"E_{a}_{h}.pkl" for a in ["P0"] + list(SEN) for h in (0, 1)]
    yok = [b for b in bek if not os.path.exists(f"{D}/{b}")]
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if not yok else f"EKSİK: {yok}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
