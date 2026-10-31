#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 692 — SIÇRAMA FIRSATI KAYBI VE POZİSYON TAŞIMA DAYANIKLILIĞI. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Girdi: madde 690 (/tmp/m690: bacak defteri, günlük bileşenler, gk) + madde 691 (/tmp/m691: seviye kayıtlı çıkış defteri, günlük TP-oynaklık)
+ fiyat zemini (/tmp/zemin.pkl, /tmp/hlo.pkl).
Sentetik stres: motorun KOPYASI (/tmp/g33_m692.py); düğmeler (varsayılan = motorla aynı, parite kontrolü yapılır):
  TP_KIRP=f    TP / kademe kontrolünde barın fitili kırpılır: yüksek' = max(açılış, kapanış) + f × (yüksek − max(açılış, kapanış))
               (short simetrik). f=1 parite, f=0 yalnız gövde (açılış / kapanış) seviyeyi geçerse dolar -> "sıçramasız dünya"
  TP_YOK=1     TP / kademe hiç dolmaz (hasat tamamen yok; stop / funding / tutuş aynen)
  TP_GEC=n     TP / kademe pozisyonun dilim yaşı n bar (4 sa) olmadan dolmaz -> fırsat n bar gecikir (seviye hâlâ geçiliyorsa
               ilk izinli barda açılıştan / seviyeden dolar)
  python3 arastirma_m692_sicrama.py kos      -> /tmp/m692/E_<senaryo>_<hiza>.pkl (tek işçi)
  python3 arastirma_m692_sicrama.py analiz   -> /tmp/m692/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m692"; os.makedirs(D, exist_ok=True)
S690, S691 = "/tmp/m690", "/tmp/m691"
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
NF = 15
SEN = {"F50": {"TP_KIRP": "0.5"}, "F0": {"TP_KIRP": "0"}, "YOK": {"TP_YOK": "1"},
       "G3": {"TP_GEC": "18"}, "G7": {"TP_GEC": "42"}, "G14": {"TP_GEC": "84"}}
SEN_AD = {"F50": "fitil %50 kırpık", "F0": "fitil yok (yalnız gövde)", "YOK": "TP / kademe hiç yok",
          "G3": "TP 3 gün gecikmeli", "G7": "TP 7 gün gecikmeli", "G14": "TP 14 gün gecikmeli"}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "def _dol(sev,uzun,i,k):\n"; assert s.count(a) == 1
    s = s.replace(a, """_TKF=float(os.environ.get('TP_KIRP','1')); _TYOK=int(os.environ.get('TP_YOK','0')); _TGEC=int(os.environ.get('TP_GEC','0'))
def _HK(i,k):
    if _TKF>=1: return HV[i+1,k]
    m=np.fmax(OV[i+1,k],cv[i+1,k]); return m+_TKF*(HV[i+1,k]-m)
def _LK(i,k):
    if _TKF>=1: return LV[i+1,k]
    m=np.fmin(OV[i+1,k],cv[i+1,k]); return m-_TKF*(m-LV[i+1,k])
def _tpok(a):
    return (not _TYOK) and (_TGEC<=0 or a>=_TGEC)
""" + a, 1)
    for lv in ("sev", "_s0", "_sm"):
        a = f"(uzun and HV[i+1,k]>={lv}) or ((not uzun) and LV[i+1,k]<={lv})"; assert s.count(a) == 1, lv
        s = s.replace(a, f"(_tpok(_yas[k]) and ((uzun and _HK(i,k)>={lv}) or ((not uzun) and _LK(i,k)<={lv})))", 1)
    open("/tmp/g33_m692.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m692.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    kopya()
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · kopya (düğmeler kapalı) vs g33.py -> {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    for ad, ek in SEN.items():
        for h in (0, 1):
            print(ad, h, _kos1(ad, ek, h), flush=True)


# ------------------------------------------------------------------------------------------------ yardımcılar
def _seri_yol(yol):
    ad = os.path.basename(yol).replace(".pkl", ""); hedef = f"{D}/M357_EK_{ad}.pkl"
    if not os.path.exists(hedef): os.symlink(yol, hedef)
    M.CIKTI = D; s = M.gunluk(f"M357_EK_{ad}"); s.index = pd.to_datetime(s.index); return s


def _seri(ad):
    if ad == "BAZ": return sum(_seri_yol(REF.format(h=h)) for h in (0, 1)) / 2
    return sum(_seri_yol(f"{D}/E_{ad}_{h}.pkl") for h in (0, 1)) / 2


def _olc(d):
    e = (1 + d).cumprod(); n = len(d); a = d.resample("ME").sum()
    return dict(cagr=(e.iloc[-1] ** (365.25 / n) - 1) * 100, sharpe=d.mean() / d.std() * np.sqrt(365.25), maks_dd=(e / e.cummax() - 1).min() * 100,
                toplam_puan=d.sum() * 100, gunluk_ort_bp=d.mean() * 1e4, gunluk_sd_bp=d.std() * 1e4, ay_ort=a.mean() * 100,
                zarar_ay=(a < 0).mean() * 100, en_kotu_ay=a.min() * 100)


def epizotlar():
    """Pozisyon = coinin bir hizada aynı yönde KESİNTİSİZ tutulduğu dönem (borsa hesabındaki tek pozisyon; TEK_GIRIS). Dilim bacakları
    (madde 690 KATKI defteri) [t, t + bar × 4 sa] aralıklarının birleşimi. Birimler kitap / hiza (dilim ağırlığı / 15)."""
    yol = f"{D}/epizot.pkl"
    if os.path.exists(yol): return pd.read_pickle(yol)
    K = pd.read_csv(f"{S690}/pozisyon_defteri.csv", parse_dates=["t"])
    K["son"] = K.t + pd.to_timedelta(K.bar * 4, unit="h"); K["aw"] = K.w.abs()
    K = K.sort_values(["h", "sem", "yon", "t"]).reset_index(drop=True)
    yeni = (K[["h", "sem", "yon"]] != K[["h", "sem", "yon"]].shift()).any(axis=1)
    onceki_son = K.groupby(["h", "sem", "yon"]).son.transform(lambda s: s.cummax().shift())
    yeni |= K.t > onceki_son
    K["ep"] = yeni.cumsum()
    E = K.groupby("ep").agg(h=("h", "first"), sem=("sem", "first"), yon=("yon", "first"), bas=("t", "min"), son=("son", "max"),
                            n_bacak=("t", "size"), pnl=("pnl", "sum"), fon=("fon", "sum"), fiy=("fiy", "sum"),
                            agirlik_bar=("aw", lambda s: float((s * K.loc[s.index, "bar"]).sum())), maks_w=("aw", "max"),
                            tp_bacak=("kapanis", lambda s: int((s == "TP").sum())))
    for c in ["pnl", "fon", "fiy"]: E[c] = E[c] / NF
    E["agirlik_gun"] = E.agirlik_bar / 6 / NF; E["sure_gun"] = (E.son - E.bas).dt.total_seconds() / 86400
    E["ort_w"] = E.agirlik_gun / E.sure_gun.clip(lower=1 / 6)
    # gerçekleşen TP / kademe olayları (seviye kayıtlı çıkış defteri, madde 691)
    X = pd.concat([pd.read_pickle(f"{S691}/cikis_S_{h}.pkl").assign(h=h) for h in (0, 1)], ignore_index=True)
    X = X[X.tur.isin(["TP", "KAD"]) & X.seviye.notna()]; X["zaman"] = pd.to_datetime(X.zaman)
    E = E.reset_index()
    m = E[["ep", "h", "sem", "yon", "bas", "son"]].merge(X[["h", "sembol", "yon", "zaman", "tur", "w"]].rename(columns={"sembol": "sem"}),
                                                         on=["h", "sem", "yon"])
    m = m[(m.zaman > m.bas) & (m.zaman <= m.son)]
    f = m.groupby("ep").agg(ilk_olay=("zaman", "min"), olay_sayi=("zaman", "size"),
                            ilk_kad=("zaman", lambda z: z[m.loc[z.index, "tur"] == "KAD"].min()),
                            ilk_tp=("zaman", lambda z: z[m.loc[z.index, "tur"] == "TP"].min()))
    E = E.merge(f, left_on="ep", right_index=True, how="left"); E["olay_sayi"] = E.olay_sayi.fillna(0).astype(int)
    E["tp_oldu"] = E.olay_sayi > 0
    for c in ["ilk_olay", "ilk_kad", "ilk_tp"]: E[c + "_gun"] = (E[c] - E.bas).dt.total_seconds() / 86400
    # potansiyel: girişten (bas barı kapanışı) itibaren 14 gün içinde 1. ve 2. seviyeye ilk dokunuş (fiyat yolu; çıkıştan bağımsız)
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = Z["C"]; Hh = pickle.load(open("/tmp/hlo.pkl", "rb"))
    Cv, Hv, Lv = C.values, Hh["H"].reindex(index=C.index, columns=C.columns).values, Hh["L"].reindex(index=C.index, columns=C.columns).values
    ri = C.index.get_indexer(E.bas); ci = C.columns.get_indexer(E["sem"]); son_i = C.index.get_indexer(E.son.clip(upper=C.index[-1]), method="pad")
    U = 84; n = len(C)
    s1 = np.full(len(E), np.nan); s2 = s1.copy(); mae = s1.copy(); giris = s1.copy()
    for j in range(len(E)):
        r, c = ri[j], ci[j]
        if r < 0 or c < 0: continue
        e0 = Cv[r, c]
        if not np.isfinite(e0) or e0 <= 0: continue
        giris[j] = e0; up = E.yon.iat[j] > 0
        hh = Hv[r + 1:min(n, r + 1 + U), c]; ll = Lv[r + 1:min(n, r + 1 + U), c]
        if up:
            a1 = np.flatnonzero(hh >= e0 * 1.45); a2 = np.flatnonzero(hh >= e0 * 1.60)
        else:
            a1 = np.flatnonzero(ll <= e0 * 0.85); a2 = np.flatnonzero(ll <= e0 * 0.80)
        s1[j] = (a1[0] + 1) / 6 if len(a1) else np.nan; s2[j] = (a2[0] + 1) / 6 if len(a2) else np.nan
        cc = Cv[r + 1:max(r + 2, son_i[j] + 1), c]; cc = cc[np.isfinite(cc)]
        if len(cc): mae[j] = (cc / e0 - 1).min() if up else (1 - cc / e0).min()   # açıkken en kötü kapanış (gerçekleşmemiş, birim pozisyon)
    E["giris_fiyat"] = giris; E["sev1_gun"] = s1; E["sev2_gun"] = s2; E["mae"] = mae
    E.to_pickle(yol); return E


def gunluk_durum(E):
    """Günlük açık pozisyon yaşı, brüt maruziyet ve yoğunlaşma (gün sonu; o güne kadar bilinen)."""
    yol = f"{D}/gunluk_durum.pkl"
    if os.path.exists(yol): return pd.read_pickle(yol)
    gun = pd.date_range(E.bas.min().normalize(), E.son.max().normalize(), freq="D")
    t = gun + pd.Timedelta(hours=23, minutes=59)
    yas_w = np.zeros(len(gun)); w = np.zeros(len(gun)); w7 = np.zeros(len(gun)); w14 = np.zeros(len(gun)); wtpsiz = np.zeros(len(gun))
    tb = t.values
    for b, s, ow, tp in zip(E.bas.values, E.son.values, E.ort_w.values, E.tp_oldu.values):
        i0 = np.searchsorted(tb, b); i1 = np.searchsorted(tb, s)
        if i1 <= i0: continue
        yas = (tb[i0:i1] - b) / np.timedelta64(1, "D")
        yas_w[i0:i1] += ow * yas; w[i0:i1] += ow; w7[i0:i1] += ow * (yas > 7); w14[i0:i1] += ow * (yas > 14)
        if not tp: wtpsiz[i0:i1] += ow
    Dd = pd.DataFrame({"acik_w": w / 2, "yas_ort": yas_w / np.where(w > 0, w, np.nan), "yas7_pay": w7 / np.where(w > 0, w, np.nan),
                       "yas14_pay": w14 / np.where(w > 0, w, np.nan), "tpsiz_w_pay": wtpsiz / np.where(w > 0, w, np.nan)}, index=gun)
    # brüt maruziyet ve yoğunlaşma (madde 690 gk: ort_poz = ortalama dilim ağırlığı, bar = bar sayısı / NF)
    G = pd.concat([pd.read_pickle(f"{S690}/gk_{h}.pkl").assign(h=h) for h in (0, 1)])
    G["bw"] = G.ort_poz.abs() * G.bar / 6
    gr = G.groupby(["gun", "sembol"]).bw.sum() / 2
    gg = gr.groupby(level=0)
    top = pd.DataFrame({"brut": gg.sum(), "top5": gg.apply(lambda s: s.nlargest(5).sum()), "top10": gg.apply(lambda s: s.nlargest(10).sum()),
                        "coin_say": gg.size()})
    top.index = pd.to_datetime(top.index)
    top["top5_pay"] = top.top5 / top.brut; top["top10_pay"] = top.top10 / top.brut
    Dd = Dd.join(top, how="left"); Dd.to_pickle(yol); return Dd


# ------------------------------------------------------------------------------------------------ analiz
def analiz():
    pd.set_option("display.width", 230); pd.set_option("display.max_columns", 30)
    E = epizotlar(); Dd = gunluk_durum(E)
    B = pd.read_csv(f"{S690}/gun_kitap_bilesen.csv", parse_dates=["gun"], index_col="gun")
    V = pd.read_csv(f"{S691}/gun_tp_vol.csv", parse_dates=["gun"], index_col="gun")
    RET = _seri("BAZ")
    yil = (E.son.max() - E.bas.min()).days / 365.25

    # ================= 2) TP'ye ulaşma süresi
    print("[ÖLÇÜM] 2) POZİSYONLAR (coin × hiza × yön kesintisiz tutuş; iki hiza toplamı):", len(E),
          f"· dönem {E.bas.min().date()} – {E.son.max().date()}")
    print(f"  süre gün: medyan {E.sure_gun.median():.1f} · ort {E.sure_gun.mean():.1f} · %90 {E.sure_gun.quantile(.9):.1f} · maks {E.sure_gun.max():.1f}"
          f" · TP / kademe gerçekleşen pozisyon %{E.tp_oldu.mean()*100:.1f}")
    for yn, ad in ((1, "long"), (-1, "short")):
        e = E[E.yon == yn]
        print(f"   {ad}: {len(e)} poz · süre medyan {e.sure_gun.median():.1f} g · TP'li %{e.tp_oldu.mean()*100:.1f} · ilk olay medyan "
              f"{e.ilk_olay_gun.median():.1f} g · ilk kademe {e.ilk_kad_gun.median():.1f} g · ilk TP {e.ilk_tp_gun.median():.1f} g")
    rows = []
    for d in (1, 3, 5, 7, 10, 14):
        rows.append(dict(gun=d, acik_kalan=(E.sure_gun > d).mean() * 100,
                         sev1_dokundu_pot=(E.sev1_gun <= d).mean() * 100, sev2_dokundu_pot=(E.sev2_gun <= d).mean() * 100,
                         ilk_olay_gerceklesti=(E.ilk_olay_gun <= d).mean() * 100,
                         olaylarin_payi=(E.ilk_olay_gun <= d).sum() / E.tp_oldu.sum() * 100,
                         long_sev1_pot=(E[E.yon > 0].sev1_gun <= d).mean() * 100, short_sev1_pot=(E[E.yon < 0].sev1_gun <= d).mean() * 100))
    T2 = pd.DataFrame(rows); T2.to_csv(f"{D}/tp_ulasma_sure.csv", index=False)
    print("  [ÖLÇÜM] kümülatif % (pozisyonlar): açık kalan · 1. seviyeye (kademe) potansiyel dokunuş · 2. seviye (TP) · gerçekleşen ilk TP/kademe ·"
          " gerçekleşen olayların bu süreye kadarki payı\n" + T2.round(1).to_string(index=False))
    print(f"  TP'li pozisyonda ilk olay > 7 gün: %{(E[E.tp_oldu].ilk_olay_gun > 7).mean()*100:.1f} · > 14 gün: %{(E[E.tp_oldu].ilk_olay_gun > 14).mean()*100:.1f}")
    # süre grupları
    E["sure_grup"] = pd.cut(E.sure_gun, [0, 1, 3, 5, 7, 10, 14, 1e9], labels=["≤1", "1-3", "3-5", "5-7", "7-10", "10-14", ">14"])
    gt = E.groupby(["sure_grup", "tp_oldu"], observed=True).agg(poz=("ep", "size"), fiyat_puan=("fiy", "sum"), funding_puan=("fon", "sum"),
                                                                 net_puan=("pnl", "sum"), agirlik_gun=("agirlik_gun", "sum"), mae_med=("mae", "median"))
    gt[["fiyat_puan", "funding_puan", "net_puan"]] *= 100 / 2; gt["agirlik_gun"] /= 2; gt["mae_med"] *= 100
    gt.to_csv(f"{D}/sure_grup.csv")
    print("  [ÖLÇÜM] süre grubu × TP oldu mu (puan, iki hiza ort.; ağırlık-gün = kitap özkaynağı × gün; mae = açıkken en kötü kapanış %):\n"
          + gt.round(2).to_string())
    # TP'siz pozisyonlar
    n_ = E[~E.tp_oldu]; t_ = E[E.tp_oldu]
    tw = E.agirlik_gun.sum()
    print("  [ÖLÇÜM] TP'ye ULAŞAMAYAN pozisyonlar (gerçekleşen TP / kademe yok):")
    for ad, e in (("TP'siz", n_), ("TP'li", t_)):
        print(f"   {ad:7s}: {len(e)} poz (%{len(e)/len(E)*100:.0f}) · fiyat {e.fiy.sum()*50:+.1f} · funding {e.fon.sum()*50:+.1f} · net {e.pnl.sum()*50:+.1f} puan · "
              f"sermaye kullanımı %{e.agirlik_gun.sum()/tw*100:.0f} (ağırlık-gün) · süre ort {e.sure_gun.mean():.1f} g · açıkken en kötü kapanış medyan "
              f"{e.mae.median()*100:.1f}% · %10 {e.mae.quantile(.1)*100:.1f}%")
    for yn, ad in ((1, "long"), (-1, "short")):
        e = n_[n_.yon == yn]
        print(f"     TP'siz {ad}: fiyat {e.fiy.sum()*50:+.1f} · funding {e.fon.sum()*50:+.1f} · net {e.pnl.sum()*50:+.1f} · sermaye %{e.agirlik_gun.sum()/tw*100:.0f}")

    # ================= 3) sıçramasız dönemler: gerçek tarih
    Dg = V[["tp", "tp_sayi", "funding", "tutus_fiyat", "getiri", "kitap_vol"]].join(Dd[["yas_ort", "yas7_pay", "acik_w", "brut"]], how="left")
    print("\n[ÖLÇÜM] 3a) GERÇEK TARİH: kitap oynaklığının 30 / 60 / 90 g ortalamasına göre pencere tercilleri (pencere başına; puan)")
    S3 = []
    for w in (30, 60, 90):
        Rw = Dg[["tp", "tp_sayi", "funding", "tutus_fiyat", "getiri"]].rolling(w).sum()
        Rw[["kitap_vol", "yas_ort", "yas7_pay", "brut"]] = Dg[["kitap_vol", "yas_ort", "yas7_pay", "brut"]].rolling(w).mean()
        Rw["gunluk_sd"] = Dg.getiri.rolling(w).std(); Rw["kotu_gun"] = Dg.getiri.rolling(w).min()
        Rw = Rw.dropna(); q = pd.qcut(Rw.kitap_vol, 3, labels=["düşük", "orta", "yüksek"])
        t = Rw.groupby(q, observed=True).median()
        t[["tp", "funding", "tutus_fiyat", "getiri"]] *= 100; t["gunluk_sd"] *= 1e4; t["kotu_gun"] *= 100; t["yas7_pay"] *= 100
        t["funding_telafi"] = np.where(t.tutus_fiyat < 0, t.funding / -t.tutus_fiyat * 100, np.nan)
        t["zarar_pencere"] = Rw.groupby(q, observed=True).getiri.apply(lambda s: (s < 0).mean() * 100)
        t.insert(0, "pencere", w); S3.append(t)
        print(f"  {w} g (medyanlar):\n" + t.round(2).to_string())
    pd.concat(S3).to_csv(f"{D}/dusuk_vol_gercek.csv")
    # düşük oynaklık dönemlerinde başlayan pozisyonlar
    vol_bas = Dg.kitap_vol.rolling(30).mean().reindex(E.bas.dt.normalize()).values
    E["vol30_bas"] = vol_bas; qv = pd.qcut(E.vol30_bas, 3, labels=["düşük", "orta", "yüksek"])
    pv = E.groupby(qv, observed=True).agg(poz=("ep", "size"), sure_ort=("sure_gun", "mean"), tp_oran=("tp_oldu", "mean"),
                                          ilk_olay_med=("ilk_olay_gun", "median"), mae_med=("mae", "median"), net_ort_bp=("pnl", "mean"))
    pv["tp_oran"] *= 100; pv["mae_med"] *= 100; pv["net_ort_bp"] *= 1e4
    print("  [ÖLÇÜM] pozisyonun başladığı andaki 30 g kitap oynaklığına göre (tercil):\n" + pv.round(2).to_string())
    pv.to_csv(f"{D}/poz_vol_tercil.csv")

    # ================= 3b) sentetik stres (motor kopyası)
    print("\n[ÖLÇÜM; senaryo VARSAYIM] 3b) SENTETİK STRES (motor kopyası, tam bileşik backtest, iki hiza ortalaması)")
    rows = [dict(senaryo="BAZ (model)", **_olc(RET))]; eksik = []
    for ad in SEN:
        if all(os.path.exists(f"{D}/E_{ad}_{h}.pkl") for h in (0, 1)):
            rows.append(dict(senaryo=f"{ad}: {SEN_AD[ad]}", **_olc(_seri(ad))))
        else: eksik.append(ad)
    St = pd.DataFrame(rows); St["cagr_fark"] = St.cagr - St.cagr.iloc[0]
    print(St.round(2).to_string(index=False)); St.to_csv(f"{D}/sentetik_stres.csv", index=False)
    if eksik: print("  EKSİK SENARYO (başarılı sayılmadı):", eksik)
    yy = {}
    for ad in ["BAZ"] + [a for a in SEN if a not in eksik]:
        s = RET if ad == "BAZ" else _seri(ad); yy[ad] = s.groupby(s.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100)
    print("  yıl yıl getiri %:\n" + pd.DataFrame(yy).round(1).to_string()); pd.DataFrame(yy).to_csv(f"{D}/sentetik_yillik.csv")
    for ad in ("F0", "YOK"):
        if ad in eksik: continue
        s = _seri(ad); a = s.resample("ME").sum() * 100
        print(f"  {ad}: aylık getiri medyan {a.median():+.2f} · %10 {a.quantile(.1):+.2f} · en kötü {a.min():+.2f} · zarar ayı %{(a<0).mean()*100:.0f} · "
              f"maks DD {_olc(s)['maks_dd']:.1f}%")

    # ================= 4) TP fırsatı gelmeyen pozisyonların sermaye maliyeti
    print("\n[ÖLÇÜM] 4) SERMAYE BAĞLAMA")
    print(f"  TP'siz pozisyon süresi ort {n_.sure_gun.mean():.1f} g · maks {n_.sure_gun.max():.1f} g · %95 {n_.sure_gun.quantile(.95):.1f} g · "
          f"TP'li ort {t_.sure_gun.mean():.1f} g")
    print(f"  TP'siz pozisyonlara bağlı sermaye: toplam {n_.agirlik_gun.sum()/2:.0f} özkaynak-gün (yılda {n_.agirlik_gun.sum()/2/yil:.0f}) · "
          f"bütün pozisyonların %{n_.agirlik_gun.sum()/tw*100:.0f}'i · bu sermayenin getirisi {n_.pnl.sum()/n_.agirlik_gun.sum()*365*100:+.1f}%/yıl "
          f"(TP'liler {t_.pnl.sum()/t_.agirlik_gun.sum()*365*100:+.1f}%/yıl)")
    print(f"  günlük: açık ağırlık ort {Dd.acik_w.mean():.2f} · brüt maruziyet ort {Dd.brut.mean():.2f} (%5 {Dd.brut.quantile(.05):.2f}, %95 "
          f"{Dd.brut.quantile(.95):.2f}) · 7 günden yaşlı pay ort %{Dd.yas7_pay.mean()*100:.0f} (%95 %{Dd.yas7_pay.quantile(.95)*100:.0f}) · "
          f"14 günden yaşlı %{Dd.yas14_pay.mean()*100:.0f} · ilk 5 coin brütün %{Dd.top5_pay.mean()*100:.0f}'i (%95 %{Dd.top5_pay.quantile(.95)*100:.0f}) · "
          f"ilk 10 %{Dd.top10_pay.mean()*100:.0f}")
    # uzayan pozisyonlar yeni girişleri azaltıyor mu? (aynı hizada yeni pozisyon sayısı)
    yeni = E.groupby(E.bas.dt.normalize()).size().reindex(Dd.index).fillna(0) / 2
    yeni5 = yeni.rolling(5).sum().shift(-5)
    k1 = Dd.yas7_pay.corr(yeni5); k2 = Dd.yas7_pay.corr(Dd.coin_say)
    print(f"  7 g'den yaşlı pozisyon payı ile sonraki 5 gündeki yeni pozisyon sayısı korelasyonu {k1:+.2f} · aynı gün coin sayısı ile {k2:+.2f}")
    print(f"  brüt maruziyet ile 7 g yaşlı payı korelasyonu {Dd.brut.corr(Dd.yas7_pay):+.2f}")
    uz = E[E.sure_gun > 7]
    print(f"  7 günden uzun pozisyonların bacak sayısı medyanı {uz.n_bacak.median():.0f} (yeniden seçilerek uzuyor; motor dilim yenilemesinde "
          f"kapasiteyi bloke etmez) · bu pozisyonlarda TP oranı %{uz.tp_oldu.mean()*100:.0f}")
    Dd.to_csv(f"{D}/gunluk_durum.csv")

    # ================= 5) yıldız coinler: walk-forward (gelecek bilgisi yok)
    print("\n[ÖLÇÜM] 5) YILDIZ COİNLER — WALK-FORWARD (her ay başında yalnız o güne kadarki veri)")
    G = pd.read_csv(f"{S690}/gun_coin_bilesen.csv", parse_dates=["gun"])
    G["net"] = G.tp + G.funding + G.fiyat + G.stop - G.komisyon
    Zc = pickle.load(open("/tmp/zemin.pkl", "rb"))["C"]; liste = Zc.apply(lambda s: s.first_valid_index())
    ay = pd.date_range("2021-02-01", G.gun.max(), freq="MS")
    Pn = G.pivot_table(index="gun", columns="sembol", values="net", aggfunc="sum").fillna(0)
    Pt = G.pivot_table(index="gun", columns="sembol", values="tp", aggfunc="sum").fillna(0)
    sonuc = {}; kalici = []
    for geri in (180, 365):
        for olcut, P in (("tp", Pt), ("net", Pn)):
            for n in (1, 3, 5, 10):
                d = RET.copy()
                for m in ay:
                    gecmis = P[(P.index >= m - pd.Timedelta(days=geri)) & (P.index < m)].sum()
                    yildiz = gecmis.nlargest(n).index
                    mm = (Pn.index >= m) & (Pn.index < m + pd.offsets.MonthBegin(1))
                    d = d.sub(Pn.loc[mm, yildiz].sum(axis=1).reindex(d.index).fillna(0), fill_value=0)
                d = d[d.index >= ay[0]]
                sonuc[(geri, olcut, n)] = _olc(d)
    baz = _olc(RET[RET.index >= ay[0]])
    W = pd.DataFrame(sonuc).T; W.index.names = ["geri_gun", "olcut", "N"]
    W = W[["cagr", "sharpe", "maks_dd", "toplam_puan", "zarar_ay"]]
    print(f"  baz (2021-02 sonrası): CAGR {baz['cagr']:.1f} · Sharpe {baz['sharpe']:.2f} · maks DD {baz['maks_dd']:.1f} · puan {baz['toplam_puan']:.0f}")
    print("  o ana kadarki ilk N 'yıldız' her ay çıkarılınca (statik; madde 691: statik ≈ motor):\n" + W.round(2).to_string())
    W.to_csv(f"{D}/yildiz_walkforward.csv")
    # rastgele taban: her ay geçmiş 180 g'de işlem görmüş coinlerden RASTGELE N coin çıkarılır (yıldız çıkarmanın bedeli rastgele kayıptan büyük mü?)
    rg_ = np.random.default_rng(6920); tab = {}
    akt = {m: Pn.columns[(Pn[(Pn.index >= m - pd.Timedelta(days=180)) & (Pn.index < m)] != 0).any()] for m in ay}
    aym = {m: (Pn.index >= m) & (Pn.index < m + pd.offsets.MonthBegin(1)) for m in ay}
    ayk = {m: Pn.loc[aym[m]] for m in ay}
    for n in (5, 10):
        cg = []
        for _ in range(200):
            d = RET.copy()
            for m in ay:
                sec = rg_.choice(akt[m], size=min(n, len(akt[m])), replace=False)
                d = d.sub(ayk[m][sec].sum(axis=1).reindex(d.index).fillna(0), fill_value=0)
            cg.append(_olc(d[d.index >= ay[0]])["cagr"])
        cg = np.array(cg); y_ = W.loc[(180, "tp", n), "cagr"]
        tab[n] = dict(rastgele_cagr_med=np.median(cg), rastgele_p5=np.quantile(cg, .05), rastgele_p95=np.quantile(cg, .95), yildiz_cagr=y_,
                      yildiz_rastgeleden_kotu_olasilik=(cg <= y_).mean())
    RT = pd.DataFrame(tab).T; print("  rastgele N coin çıkarma (200 tekrar, 180 g aktif coinlerden) vs yıldız çıkarma:\n" + RT.round(3).to_string())
    RT.to_csv(f"{D}/yildiz_rastgele_taban.csv")
    # kalıcılık: geçmiş 180 g TP ilk 10'unun sonraki ay / çeyrek TP payı; sıra korelasyonu
    for m in ay:
        g = Pt[(Pt.index >= m - pd.Timedelta(days=180)) & (Pt.index < m)].sum()
        s1 = Pt[(Pt.index >= m) & (Pt.index < m + pd.offsets.MonthBegin(1))].sum()
        s3 = Pt[(Pt.index >= m) & (Pt.index < m + pd.offsets.MonthBegin(3))].sum()
        top = g.nlargest(10).index; ort = g[g > 0].index.intersection(s3.index)
        kalici.append(dict(ay=m, top10_sonraki_ay_tp_payi=s1[top].sum() / s1.sum() if s1.sum() else np.nan,
                           top10_sonraki_ceyrek_tp_payi=s3[top].sum() / s3.sum() if s3.sum() else np.nan,
                           sira_kor_ceyrek=g.reindex(ort).corr(s3.reindex(ort), method="spearman"),
                           sonraki_ceyrek_top10_icinde_eski=len(set(s3.nlargest(10).index) & set(g.nlargest(20).index)),
                           rastgele10_ceyrek_payi_beklenen=10 / max(int((g != 0).sum()), 10)))
    KL = pd.DataFrame(kalici).set_index("ay"); KL.to_csv(f"{D}/yildiz_kalicilik.csv")
    print(f"  kalıcılık (ay başına ort.): geçmiş 180 g TP ilk 10'u sonraki ayın TP'sinin %{KL.top10_sonraki_ay_tp_payi.mean()*100:.0f}'ini, sonraki "
          f"çeyreğin %{KL.top10_sonraki_ceyrek_tp_payi.mean()*100:.0f}'ini veriyor · sıra korelasyonu (çeyrek) {KL.sira_kor_ceyrek.mean():+.2f} · "
          f"sonraki çeyreğin TP ilk 10'unun ort. {KL.sonraki_ceyrek_top10_icinde_eski.mean():.1f}'i geçmiş ilk 20'deydi · rastgele 10 coinin beklenen payı %{KL.rastgele10_ceyrek_payi_beklenen.mean()*100:.0f}")
    # yeni coinler: yılın TP / net katkısının ne kadarı son 12 ayda listelenen coinlerden
    print("  yeni coin katkısı (coin borsada / veri setinde 365 günden genç):")
    Gy = G.assign(yil=G.gun.dt.year, liste=G.sembol.map(liste))
    Gy["genc"] = (Gy.gun - pd.to_datetime(Gy.liste)).dt.days < 365
    yt = Gy.groupby(["yil", "genc"])[["tp", "net"]].sum().unstack()
    for y in yt.index:
        tp_t = yt.loc[y, "tp"].sum(); nt = yt.loc[y, "net"].sum()
        print(f"   {y}: TP'nin %{yt.loc[y, ('tp', True)]/tp_t*100 if ('tp', True) in yt.columns else 0:.0f}'i, net kârın "
              f"%{yt.loc[y, ('net', True)]/nt*100 if ('net', True) in yt.columns else 0:.0f}'i genç coinlerden")
    yt.to_csv(f"{D}/genc_coin_katki.csv")

    # ================= 6) erken uyarı: kronolojik eğitim / test
    print("\n[ÖLÇÜM] 6) ERKEN UYARI (hedef: sonraki 30 gün kitap getirisi < 0; kronolojik ayrım, 30 g ambargo)")
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    F = pd.DataFrame(index=B.index)
    for w in (30, 60, 90): F[f"tp{w}"] = B.tp.rolling(w).sum()
    F["fund30"] = B.funding.rolling(30).sum()
    F["kitap_vol"] = V.kitap_vol.reindex(F.index)
    # TP'ye ulaşma süresi: son 30 günde GERÇEKLEŞEN ilk TP / kademe olaylarının pozisyon yaşı (olay anında bilinir)
    ev = E.dropna(subset=["ilk_olay"]).set_index(E.dropna(subset=["ilk_olay"]).ilk_olay.dt.normalize()).ilk_olay_gun.sort_index()
    F["tp_sure30"] = ev.groupby(level=0).mean().reindex(F.index).rolling(30, min_periods=5).mean()
    # TP gerçekleşmeyen pozisyon oranı: son 30 günde KAPANAN pozisyonlar
    kap = E.set_index(E.son.dt.normalize()).tp_oldu.sort_index()
    kk = kap.groupby(level=0).agg(["sum", "size"]).reindex(F.index).fillna(0).rolling(30).sum()
    F["tpsiz_oran30"] = 1 - kk["sum"] / kk["size"].replace(0, np.nan)
    F = F.join(Dd[["yas_ort", "yas7_pay", "top5_pay", "top10_pay"]], how="left")
    ileri = RET.reindex(F.index).fillna(0)[::-1].rolling(30).sum()[::-1].shift(-1)
    y = (ileri < 0).astype(float).where(ileri.notna())
    F["y"] = y; F = F[F.index >= "2020-11-01"].dropna()
    egitim_son = pd.Timestamp("2023-06-30"); test_bas = egitim_son + pd.Timedelta(days=31)
    tr = F[F.index <= egitim_son - pd.Timedelta(days=30)]   # hedef penceresi eğitim sınırını aşmasın
    te = F[F.index >= test_bas]
    print(f"  eğitim {tr.index.min().date()} – {tr.index.max().date()} (n {len(tr)}, kötü %{tr.y.mean()*100:.1f}) · test {te.index.min().date()} – "
          f"{te.index.max().date()} (n {len(te)}, kötü %{te.y.mean()*100:.1f}; bağımsız 30 g blok ≈ {len(te)//30})")
    rng = np.random.default_rng(692); ozell = [c for c in F.columns if c != "y"]

    def _null_auc(p, yy, k=2000):
        """Dairesel kaydırma: hedef serisi en az 45 gün kaydırılır (otokorelasyon korunur)."""
        n = len(yy); out = []
        for _ in range(k):
            s = rng.integers(45, n - 45); out.append(roc_auc_score(np.roll(yy, s), p))
        return np.array(out)

    rows = []
    sets = [[c] for c in ozell] + [ozell]
    for cols in sets:
        mu, sd = tr[cols].mean(), tr[cols].std().replace(0, 1)
        m = LogisticRegression(C=1.0, max_iter=2000).fit((tr[cols] - mu) / sd, tr.y)
        p_tr = m.predict_proba((tr[cols] - mu) / sd)[:, 1]; p_te = m.predict_proba((te[cols] - mu) / sd)[:, 1]
        if te.y.nunique() < 2: continue
        auc_te = roc_auc_score(te.y, p_te); auc_tr = roc_auc_score(tr.y, p_tr)
        nul = _null_auc(p_te, te.y.values); pval = (nul >= auc_te).mean()
        esik = np.quantile(p_tr, 0.80)   # eğitimde riskin en yüksek %20'si -> alarm (eşik eğitimden; testte sabit)
        al = p_te >= esik; yt_ = te.y.values.astype(bool)
        isabet = yt_[al].mean() if al.any() else np.nan
        rows.append(dict(ozellik="HEPSİ" if len(cols) > 1 else cols[0], auc_egitim=auc_tr, auc_test=auc_te, p_dairesel=pval,
                         alarm_gun_pct=al.mean() * 100, isabet_pct=isabet * 100 if al.any() else np.nan,
                         yanlis_alarm_pct=(1 - isabet) * 100 if al.any() else np.nan, yakalama_pct=(al & yt_).sum() / max(yt_.sum(), 1) * 100,
                         lift=isabet / te.y.mean() if al.any() else np.nan,
                         alarm_sonrasi_30g=ileri.reindex(te.index)[al].mean() * 100 if al.any() else np.nan))
    U = pd.DataFrame(rows)
    print(f"  rastgele taban çizgisi: AUC 0,50 · her gün alarm -> isabet %{te.y.mean()*100:.1f} (yanlış alarm %{(1-te.y.mean())*100:.1f}), lift 1,0")
    print(U.round(3).to_string(index=False)); U.to_csv(f"{D}/erken_uyari_test.csv", index=False)
    print(f"  test dönemi ileri 30 g getiri ort. {ileri.reindex(te.index).mean()*100:.1f}% (alarm sonrası sütunuyla karşılaştır)")
    F.to_csv(f"{D}/erken_uyari_ozellik.csv")

    # ================= çıktı kontrolü
    bek = ["tp_ulasma_sure.csv", "sure_grup.csv", "dusuk_vol_gercek.csv", "poz_vol_tercil.csv", "sentetik_stres.csv", "sentetik_yillik.csv",
           "gunluk_durum.csv", "yildiz_walkforward.csv", "yildiz_kalicilik.csv", "genc_coin_katki.csv", "erken_uyari_test.csv",
           "erken_uyari_ozellik.csv", "epizot.pkl", "gunluk_durum.pkl"] + [f"E_{a}_{h}.pkl" for a in list(SEN) + ["P0"] for h in (0, 1)]
    yok = [b for b in bek if not os.path.exists(f"{D}/{b}")]
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if not yok else f"EKSİK: {yok}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz, "kopya": kopya}[sys.argv[1]]()
