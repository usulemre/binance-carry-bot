#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 691 — TP MOTORU DAYANIKLILIK VE KIRILGANLIK ANALİZİ. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya hiçbir şey bağlanmaz.
Girdi: madde 690'ın çıktıları (/tmp/m690: günlük coin bileşenleri, çıkış defteri, bacak defteri) + fiyat zemini (/tmp/zemin.pkl, /tmp/hlo.pkl).
Stres koşuları motorun KOPYASIYLA (/tmp/g33_m691.py) yapılır; kopyada iki ortam düğmesi vardır, varsayılanları (0) motorla aynıdır:
  TP_KAYMA=x  (bp)  TP / kademe dolum fiyatı x bp kötüleşir (long: ×(1−x), short: ×(1+x)) -> ek icra maliyeti
  TP_DELME=x  (bp)  TP / kademe limiti yalnız fiyat seviyeyi x bp GEÇERSE dolar (değip dönen bar dolmaz) -> dokunma iyimserliği
Coin çıkarma koşuları yalnız SEMBOL_HARIC ortam değişkenini genişletir (motor davranışı değişmez; boşalan yer diğer coinlere gider).
  python3 arastirma_m691_tp_motoru.py kos      -> /tmp/m691/E_<senaryo>_<hiza>.pkl (tek işçi; 7 GB makinede iki koşu aynı anda ölür)
  python3 arastirma_m691_tp_motoru.py analiz   -> /tmp/m691/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m691"; S690 = "/tmp/m690"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "def _dol(sev,uzun,i,k):\n"; assert s.count(a) == 1
    s = s.replace(a, "_TPK=float(os.environ.get('TP_KAYMA','0'))*1e-4\n_TPD=float(os.environ.get('TP_DELME','0'))*1e-4\n"
                     "def _dol(sev,uzun,i,k):\n    _x=_dol0(sev,uzun,i,k)\n    return _x*(1-_TPK) if uzun else _x*(1+_TPK)\n"
                     "def _dol0(sev,uzun,i,k):\n", 1)
    for lv in ("sev", "_s0", "_sm"):
        a = f"(uzun and HV[i+1,k]>={lv}) or ((not uzun) and LV[i+1,k]<={lv})"; assert s.count(a) == 1, lv
        s = s.replace(a, f"(uzun and HV[i+1,k]>={lv}*(1+_TPD)) or ((not uzun) and LV[i+1,k]<={lv}*(1-_TPD))", 1)
    open("/tmp/g33_m691.py", "w", encoding="utf-8").write(s)


def seviye_kopya():
    """Çıkış defterine limit SEVİYESİNİ ve referans girişi (TEK_GIRIS ortalama giriş) ekleyen ikinci kopya (/tmp/g33_m691s.py).
    Yalnız kayıt ekler; işlem davranışı değişmez (E paritesi kontrol edilir). Seviyesi olmayan çıkışlar (ör. azami tutma süresi)
    madde 621 defterinde 'TP' etiketiyle görünüyordu -> burada NaN seviye ile ayrılır."""
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "    for i in range(bas,len(C)-1):\n"; assert s.count(a) == 1
    s = s.replace(a, a + "        _SV=np.full(C.shape[1],np.nan); _SE=np.full(C.shape[1],np.nan)\n", 1)
    a = "                    br[k]=_dol(sev,uzun,i,k)/cv[i,k]-1; say_t[1]+=1\n"; assert s.count(a) == 1
    s = s.replace(a, a + "                    _SV[k]=sev; _SE[k]=e\n", 1)
    for a, lv in [("mpay[k]=f0+f1; merd[k]=True", "_sm"), ("mpay[k]=MERD_PAY if (uzun or MERDS_PAY<0) else MERDS_PAY; merd[k]=True", "_sm"),
                  ("mpay[k]=MERD0_PAY; merd[k]=True", "_s0")]:
        assert s.count(a) == 1; s = s.replace(a, f"_SV[k]={lv}; _SE[k]=e; " + a, 1)
    a = "                            float(giris[_k]) if np.isfinite(giris[_k]) else np.nan))"; assert s.count(a) == 1
    s = s.replace(a, "                            float(giris[_k]) if np.isfinite(giris[_k]) else np.nan,float(_SV[_k]),float(_SE[_k])))", 1)
    a = "columns=['zaman','sembol','yon','tur','w','fiyat','giris']"; assert s.count(a) == 1
    s = s.replace(a, "columns=['zaman','sembol','yon','tur','w','fiyat','giris','seviye','ref_giris']", 1)
    open("/tmp/g33_m691s.py", "w", encoding="utf-8").write(s)


def kos_seviye():
    seviye_kopya()
    for h in (0, 1):
        out = f"{D}/E_S_{h}.pkl"
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=out, CIKIS_DEFTER=f"{D}/cikis_S_{h}.pkl")
        with open(out.replace(".pkl", ".txt"), "w") as f:
            rc = subprocess.run([sys.executable, "/tmp/g33_m691s.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode
        ayni = open(out, "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"seviye kaydı hiza {h}: rc {rc} · E paritesi {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)


def tp_coinleri():
    G = pd.read_csv(f"{S690}/gun_coin_bilesen.csv")
    return G.groupby("sembol").tp.sum().sort_values(ascending=False)


def senaryolar():
    top = list(tp_coinleri().index[:5])
    S = {f"K{x}": {"TP_KAYMA": str(x)} for x in (5, 10, 15, 20)}
    S.update({f"D{x}": {"TP_DELME": str(x)} for x in (5, 10, 20)})
    S.update({f"X{n}": {"SEMBOL_HARIC": ",".join(M.D8 + top[:n])} for n in (1, 3, 5)})
    return S, top


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m691.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    kopya(); S, top = senaryolar()
    print("en çok TP kârı getiren 5 coin (madde 690 defteri):", top, flush=True)
    # parite: düğmeler kapalıyken kopya = motor
    print("parite hiza 0:", _kos1("P0", {}, 0), flush=True)
    ayni = open(f"{D}/E_P0_0.pkl", "rb").read() == open(REF.format(h=0), "rb").read()
    print(f"parite: kopya (düğmeler kapalı) vs g33.py referansı -> {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
    if not ayni: sys.exit(1)
    for ad, ek in S.items():
        for h in (0, 1):
            print(ad, h, _kos1(ad, ek, h), flush=True)


# ------------------------------------------------------------------------------------------------ analiz
def _seri_yol(yol):
    """E dosyasından günlük getiri serisi (M.gunluk ile aynı yöntem)."""
    ad = os.path.basename(yol).replace(".pkl", ""); hedef = f"{D}/M357_EK_{ad}.pkl"
    if not os.path.exists(hedef): os.symlink(yol, hedef)
    M.CIKTI = D; return M.gunluk(f"M357_EK_{ad}")


def _seri(ad):
    if ad == "BAZ": return sum(_seri_yol(REF.format(h=h)) for h in (0, 1)) / 2
    return sum(_seri_yol(f"{D}/E_{ad}_{h}.pkl") for h in (0, 1)) / 2


def _olc(d):
    e = (1 + d).cumprod(); n = len(d)
    return dict(cagr=(e.iloc[-1] ** (365.25 / n) - 1) * 100, sharpe=d.mean() / d.std() * np.sqrt(365.25),
                maks_dd=(e / e.cummax() - 1).min() * 100, toplam_puan=d.sum() * 100)


def vol_panel():
    """Günlük kapanış (00:00 UTC) -> coin günlük log getirisi; 30 g gerçekleşen oynaklık (yıllık %)."""
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = Z["C"]
    Cg = C[C.index.hour == 0]; Cg.index = Cg.index.normalize()
    r = np.log(Cg).diff()
    v30 = r.rolling(30, min_periods=20).std() * np.sqrt(365) * 100
    rng = (pickle.load(open("/tmp/hlo.pkl", "rb"))["H"] / pickle.load(open("/tmp/hlo.pkl", "rb"))["L"] - 1)
    return r, v30, rng


def cikis_defteri():
    """TP / kademe olayları. Seviye kayıtlı defter (kos_seviye) varsa o kullanılır: seviyesi olmayan 'TP' etiketli çıkışlar
    (azami tutma süresi vb.) 'diger' olarak ayrılır ve kazanç TEK_GIRIS referans girişine göre hesaplanır."""
    sv = all(os.path.exists(f"{D}/cikis_S_{h}.pkl") for h in (0, 1))
    X = pd.concat([pd.read_pickle(f"{D}/cikis_S_{h}.pkl" if sv else f"{S690}/cikis_{h}.pkl").assign(h=h) for h in (0, 1)], ignore_index=True)
    X = X[X.tur.isin(["TP", "KAD"])].copy()
    if sv:
        X["seviyeli"] = X.seviye.notna(); ref = X.ref_giris.where(X.ref_giris.notna(), X.giris)
    else:
        X["seviyeli"] = True; X["seviye"] = np.nan; ref = X.giris
    X["kazanc"] = np.where(X.yon > 0, X.fiyat / ref - 1, 1 - X.fiyat / ref)   # referans girişe göre gerçekleşen kazanç (işlem getirisi)
    X["gun"] = pd.to_datetime(X.zaman).dt.normalize()
    return X


def analiz():
    pd.set_option("display.width", 220)
    G = pd.read_csv(f"{S690}/gun_coin_bilesen.csv", parse_dates=["gun"])
    B = pd.read_csv(f"{S690}/gun_kitap_bilesen.csv", parse_dates=["gun"], index_col="gun")
    X = cikis_defteri(); r, v30, rng = vol_panel()
    NF = 15  # FAZ=15 dilim: kitap ağırlığı = dilim ağırlığı / 15 (madde 690 gk birimleri NF'ye bölünür)
    # cikis defterinde w = dilim içi satılan ağırlık; kitap birimi = w / NF; iki hizanın ortalaması -> /2
    X["kitap_w"] = X.w / NF / 2
    X["katki"] = X.kitap_w * X.kazanc
    # seviyesi olmayan 'TP' etiketli çıkışlar: madde 690'ın TP bileşenine giren çıkış barı fiyatı (düzeltme için)
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); Cz = Z["C"]
    zi = Cz.index.get_indexer(pd.to_datetime(X.zaman)); ci_ = Cz.columns.get_indexer(X.sembol)
    c1 = Cz.values[zi, ci_]; c0 = Cz.values[zi - 1, ci_]
    X["cikis_bari_katki"] = np.where(X.seviyeli, np.nan, X.yon * X.kitap_w * (c1 / c0 - 1))
    Dg = X[~X.seviyeli]
    print(f"[ÖLÇÜM] seviyesi OLMAYAN 'TP' etiketli çıkış (madde 621 defterinin varsayılan etiketi; azami tutma süresi vb.): {len(Dg)} olay · "
          f"çıkış barı katkısı {Dg.cikis_bari_katki.sum()*100:+.1f} puan (madde 690 TP bileşenine dahildi) · girişe göre kazanç toplamı "
          f"{Dg.katki.sum()*100:+.1f} puan")
    duz = Dg.groupby("gun").cikis_bari_katki.sum()
    B["tp"] = B.tp - duz.reindex(B.index).fillna(0)      # düzeltilmiş TP bileşeni (yalnız seviyeli TP / kademe barları)
    print(f"  düzeltilmiş TP bileşeni toplamı {B.tp.sum()*100:.1f} puan")
    X = X[X.seviyeli].copy()
    print(f"[ÖLÇÜM] TP / kademe çıkış olayı (iki hiza toplamı): {len(X)} · TP {int((X.tur=='TP').sum())} · KAD {int((X.tur=='KAD').sum())} "
          f"· dönem {X.gun.min().date()} – {X.gun.max().date()}")
    print(f"  işlem getirisi (girişe göre) medyan {X.kazanc.median()*100:.1f}% · ort {X.kazanc.mean()*100:.1f}% · "
          f"long ort {X[X.yon>0].kazanc.mean()*100:.1f}% · short ort {X[X.yon<0].kazanc.mean()*100:.1f}%")

    # ---------------- 1) TP ve oynaklık
    # kitabın tuttuğu coinlerin oynaklığı: |ort_poz| ağırlıklı 30 g gerçekleşen oynaklık (o gün bilinen değer)
    vl = v30.stack().rename("v30").reset_index(); vl.columns = ["gun", "sembol", "v30"]
    Gv = G.merge(vl, on=["gun", "sembol"], how="left"); Gv["aw"] = Gv.ort_poz.abs()
    kv = Gv.dropna(subset=["v30"]).groupby("gun").apply(lambda d: np.average(d.v30, weights=d.aw) if d.aw.sum() > 0 else np.nan,
                                                          include_groups=False).rename("kitap_vol")
    evren = v30.median(axis=1).rename("evren_vol"); btc = v30["BTCUSDT"].rename("btc_vol")
    # bar içi hareket: evrenin medyan 4 sa (yüksek/düşük − 1), günlük ortalama
    rg = rng.median(axis=1); rg.index = pd.to_datetime(rg.index); rg = rg.groupby(rg.index.normalize()).mean().rename("evren_bar_aralik")
    V = pd.concat([B.tp, B.gercek_getiri, B.funding, B.long_fiyat + B.short_fiyat], axis=1, keys=["tp", "getiri", "funding", "tutus_fiyat"])
    V = V.join([kv, evren, btc, rg], how="left")
    ev = X.groupby("gun").agg(tp_sayi=("katki", "size"), tp_kazanc=("kazanc", "mean"), tp_katki=("katki", "sum"))
    V = V.join(ev, how="left").fillna({"tp_sayi": 0, "tp_katki": 0})
    V.to_csv(f"{D}/gun_tp_vol.csv")
    # aylık (örtüşmeyen) bloklar
    A = V.resample("ME").agg({"tp": "sum", "getiri": "sum", "funding": "sum", "tutus_fiyat": "sum", "tp_sayi": "sum", "tp_katki": "sum",
                              "kitap_vol": "mean", "evren_vol": "mean", "btc_vol": "mean", "evren_bar_aralik": "mean"})
    A["tp_kazanc_ort"] = X.groupby(X.gun.dt.to_period("M")).kazanc.mean().reindex(A.index.to_period("M")).values
    A["islem_basi_katki_bp"] = A.tp_katki / A.tp_sayi.replace(0, np.nan) * 1e4
    A = A[A.index >= "2020-08-01"]
    A.to_csv(f"{D}/ay_tp_vol.csv")
    print("\n[ÖLÇÜM] 1) TP – OYNAKLIK (aylık örtüşmeyen bloklar, n =", len(A), ")")
    for vc in ["kitap_vol", "evren_vol", "btc_vol", "evren_bar_aralik"]:
        print(f"  korelasyon {vc:17s}: TP {A.tp.corr(A[vc]):+.2f} · TP sayısı {A.tp_sayi.corr(A[vc]):+.2f} · "
              f"Spearman TP {A.tp.corr(A[vc], method='spearman'):+.2f} · getiri {A.getiri.corr(A[vc]):+.2f}")
    for w in (30, 60, 90):
        Rw = V[["tp", "tp_sayi"]].rolling(w).sum(); vw = V[["kitap_vol", "evren_vol", "btc_vol", "evren_bar_aralik"]].rolling(w).mean()
        print(f"  {w} g hareketli: TP ~ kitap_vol {Rw.tp.corr(vw.kitap_vol):+.2f} · evren_vol {Rw.tp.corr(vw.evren_vol):+.2f} · "
              f"btc_vol {Rw.tp.corr(vw.btc_vol):+.2f} · bar aralığı {Rw.tp.corr(vw.evren_bar_aralik):+.2f} · TP sayısı ~ kitap_vol "
              f"{Rw.tp_sayi.corr(vw.kitap_vol):+.2f}")
    # terciller (kitap oynaklığına göre aylar)
    print("\n  [ÖLÇÜM] oynaklık terciline göre aylar (kitabın tuttuğu coinlerin 30 g oynaklığı):")
    T = []
    for vc in ["kitap_vol", "evren_vol", "btc_vol"]:
        q = pd.qcut(A[vc], 3, labels=["düşük", "orta", "yüksek"])
        t = A.groupby(q, observed=True).agg(ay=("tp", "size"), vol_ort=(vc, "mean"), tp_ay=("tp", "mean"), tp_sayi_ay=("tp_sayi", "mean"),
                                            tp_kazanc_ort=("tp_kazanc_ort", "mean"), islem_basi_bp=("islem_basi_katki_bp", "mean"),
                                            funding_ay=("funding", "mean"), tutus_ay=("tutus_fiyat", "mean"), getiri_ay=("getiri", "mean"),
                                            zarar_ay_orani=("getiri", lambda s: (s < 0).mean()))
        t[["tp_ay", "funding_ay", "tutus_ay", "getiri_ay"]] *= 100; t["tp_kazanc_ort"] *= 100; t["zarar_ay_orani"] *= 100
        t.insert(0, "olcu", vc); T.append(t)
        print(f"   {vc}:\n" + t.round(2).to_string())
    pd.concat(T).to_csv(f"{D}/tercil_tp_vol.csv")
    # esneklik: log TP ~ log vol
    a = A[(A.tp > 0) & A.kitap_vol.notna()]
    b, c0 = np.polyfit(np.log(a.kitap_vol), np.log(a.tp), 1)
    b2, _ = np.polyfit(np.log(a.kitap_vol), np.log(a.tp_sayi.clip(lower=1)), 1)
    print(f"\n  [ÖLÇÜM] esneklik (aylık log-log, kitap_vol): TP katkısı {b:+.2f} · TP sayısı {b2:+.2f} "
          f"(oynaklık %10 düşerse TP ~%{(1-0.9**b)*100:.0f} azalır)")
    # oynaklık düşüşü -> TP düşüşü: oynaklığın en düşük çeyreği ile medyan karşılaştırma
    lo = A.kitap_vol <= A.kitap_vol.quantile(0.25); md = A.kitap_vol.between(A.kitap_vol.quantile(0.375), A.kitap_vol.quantile(0.625))
    print(f"  en düşük oynaklık çeyreği (aylar n={int(lo.sum())}): TP {A.tp[lo].mean()*100:.1f} / ay vs medyan bant {A.tp[md].mean()*100:.1f} / ay "
          f"(−%{(1-A.tp[lo].mean()/A.tp[md].mean())*100:.0f}) · getiri {A.getiri[lo].mean()*100:.1f} vs {A.getiri[md].mean()*100:.1f}")

    # ---------------- 2) TP gerçekleşme kalitesi
    H = pickle.load(open("/tmp/hlo.pkl", "rb")); Hh, Ll, Oo = H["H"], H["L"], H["O"]
    zt = pd.to_datetime(X.zaman)
    ri = Hh.index.get_indexer(zt); ci = Hh.columns.get_indexer(X.sembol)
    ok = (ri >= 0) & (ci >= 0)
    hv = np.full(len(X), np.nan); lv = hv.copy(); ov = hv.copy()
    hv[ok] = Hh.values[ri[ok], ci[ok]]; lv[ok] = Ll.values[ri[ok], ci[ok]]; ov[ok] = Oo.values[ri[ok], ci[ok]]
    # seviye: motorun kaydettiği limit seviyesi (TEK_GIRIS ortalama girişe göre kademe long +%45 / short −%15, TP +%60 / −%20)
    q = np.where(X.tur == "KAD", np.where(X.yon > 0, 0.45, -0.15), np.where(X.yon > 0, 0.60, -0.20))
    sev = np.where(X.seviye.notna(), X.seviye.values, X.giris.values * (1 + q))
    acilis_gecti = np.where(X.yon > 0, ov >= sev, ov <= sev)
    delme = np.where(X.yon > 0, hv / np.maximum(sev, np.where(np.isfinite(ov), ov, sev)) - 1, 1 - lv / np.minimum(sev, np.where(np.isfinite(ov), ov, sev)))
    X["delme_bp"] = delme * 1e4; X["acilista_gecti"] = acilis_gecti
    # model dolum fiyatı / seviye
    X["model_vs_seviye_bp"] = np.where(X.yon > 0, X.fiyat / sev - 1, 1 - X.fiyat / sev) * 1e4
    print("\n[ÖLÇÜM] 2) TP GERÇEKLEŞME (4 sa bar; dakika verisi bu koşuda yok)")
    print(f"  açılışta seviye zaten geçilmiş (boşluk; model açılıştan doldurur): %{np.nanmean(acilis_gecti)*100:.1f} olay · "
          f"model dolum fiyatı seviyeden medyan {np.nanmedian(X.model_vs_seviye_bp):.0f} bp, ort {np.nanmean(X.model_vs_seviye_bp):.0f} bp daha iyi")
    d = X.delme_bp
    for e in (5, 10, 20, 50, 100):
        m = d < e
        print(f"  seviyeyi < {e:3d} bp geçen (değip dönen) olay: %{m.mean()*100:5.2f} · ağırlıklı katkı payı %{X.katki[m].sum()/X.katki.sum()*100:5.2f}")
    print(f"  delme medyanı {d.median():.0f} bp · %10 {d.quantile(.1):.0f} bp · %25 {d.quantile(.25):.0f} bp")
    X.to_csv(f"{D}/tp_olaylari.csv", index=False)
    # analitik maliyet: k bp × TP / kademe işlem gören kitap ağırlığı
    tw = X.kitap_w.sum(); tk = X.katki.sum()
    yil = (X.gun.max() - X.gun.min()).days / 365.25
    print(f"  TP / kademe işlem gören kitap ağırlığı toplamı {tw:.2f} (≈ yılda {tw/yil:.2f} × özkaynak) · TP olaylarının girişe göre katkısı {tk*100:.0f} puan")
    for k in (5, 10, 15, 20):
        print(f"   ek {k:2d} bp (analitik): −{tw*k*1e-4*100:.1f} puan toplam · yılda −{tw*k*1e-4*100/yil:.2f} puan · TP olay katkısının %{tw*k*1e-4/tk*100:.1f}'i")

    # ---------------- 3) coin yoğunlaşması
    Cn = X.groupby("sembol").agg(tp_islem=("katki", "size"), tp_kar=("katki", "sum"), ort_kazanc=("kazanc", "mean"))
    Cn["islem_basi_katki_bp"] = Cn.tp_kar / Cn.tp_islem * 1e4
    Gt = G.groupby("sembol")[["tp", "funding", "fiyat", "stop", "komisyon"]].sum()
    Gt["net"] = Gt.tp + Gt.funding + Gt.fiyat + Gt.stop - Gt.komisyon
    _d = Dg.groupby("sembol").cikis_bari_katki.sum().reindex(Gt.index).fillna(0)
    Gt["tp"] = Gt.tp - _d; Gt["fiyat"] = Gt.fiyat + _d       # seviyesiz çıkış barı TP'den tutuşa taşınır (net değişmez)
    Cn = Cn.join(Gt, how="outer").fillna(0).sort_values("tp", ascending=False)
    Cn.to_csv(f"{D}/coin_tp.csv")
    tpp = Cn.tp.clip(lower=0)
    print("\n[ÖLÇÜM] 3) COİN YOĞUNLAŞMASI (TP bileşeni, madde 690 günlük defter)")
    print(f"  TP üreten coin {int((Cn.tp>0).sum())} · TP toplamı {Cn.tp.sum()*100:.0f} puan")
    for n in (1, 3, 5, 10, 20):
        print(f"   ilk {n:2d} coin: TP'nin %{Cn.tp.head(n).sum()/Cn.tp.sum()*100:.1f}'i · net kârın %{Cn.net.head(n).sum()/Cn.net.sum()*100:.1f}'i")
    hh = ((tpp / tpp.sum()) ** 2).sum()
    print(f"   Herfindahl (TP payları) {hh:.4f} -> etkin coin sayısı {1/hh:.0f}")
    print("  ilk 20 coin (TP işlem sayısı · TP kârı puan · ort. işlem getirisi · işlem başı katkı bp · net puan):")
    print((Cn.head(20)[["tp_islem", "tp", "ort_kazanc", "islem_basi_katki_bp", "net"]] * [1, 100, 100, 1, 100]).round(2).to_string())
    # statik çıkarma: coinin günlük katkılarını seriden düş (yer başkasına gitmez -> üst sınır kayıp)
    RET = _seri("BAZ"); RET.index = pd.to_datetime(RET.index)
    gc = G.assign(net=G.tp + G.funding + G.fiyat + G.stop - G.komisyon).pivot_table(index="gun", columns="sembol", values="net", aggfunc="sum").fillna(0)
    S, top = senaryolar()
    out = [dict(senaryo="BAZ", yontem="—", **_olc(RET))]
    for n in (1, 3, 5):
        d_ = RET - gc[top[:n]].sum(axis=1).reindex(RET.index).fillna(0)
        out.append(dict(senaryo=f"ilk {n} TP coini çıkar", yontem="statik (katkı düşülür)", **_olc(d_)))
        p = f"{D}/E_X{n}_1.pkl"
        if os.path.exists(p):
            out.append(dict(senaryo=f"ilk {n} TP coini çıkar", yontem="motor (evrenden çıkarılır)", **_olc(_seri(f"X{n}"))))
    # yıllık
    print(f"  çıkarılan coinler sırasıyla: {top}")
    print(pd.DataFrame(out).round(2).to_string(index=False))
    pd.DataFrame(out).to_csv(f"{D}/coin_cikarma.csv", index=False)

    # ---------------- 2b) motor stres koşuları (kayma / delme)
    print("\n[ÖLÇÜM + VARSAYIM] 2b) TP İCRA STRESİ (motor kopyası; tam bileşik backtest, iki hiza ortalaması)")
    rows = [dict(senaryo="BAZ (model)", **_olc(RET))]
    for ad, ac in [("K5", "TP/kademe dolumu 5 bp kötü"), ("K10", "10 bp kötü"), ("K15", "15 bp kötü"), ("K20", "20 bp kötü"),
                   ("D5", "seviye 5 bp delinmeden dolmaz"), ("D10", "10 bp delinmeden dolmaz"), ("D20", "20 bp delinmeden dolmaz")]:
        if os.path.exists(f"{D}/E_{ad}_1.pkl"):
            rows.append(dict(senaryo=f"{ad}: {ac}", **_olc(_seri(ad))))
    St = pd.DataFrame(rows); St["cagr_fark"] = St.cagr - St.cagr.iloc[0]; St["puan_fark"] = St.toplam_puan - St.toplam_puan.iloc[0]
    print(St.round(2).to_string(index=False)); St.to_csv(f"{D}/icra_stres.csv", index=False)
    # yıl yıl stres
    yy = {}
    for ad in ["BAZ", "K10", "K20", "D20", "X1", "X3", "X5"]:
        if ad != "BAZ" and not os.path.exists(f"{D}/E_{ad}_1.pkl"): continue
        s = RET if ad == "BAZ" else _seri(ad); s.index = pd.to_datetime(s.index)
        yy[ad] = s.groupby(s.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100)
    print("  yıl yıl getiri %:\n" + pd.DataFrame(yy).round(1).to_string()); pd.DataFrame(yy).to_csv(f"{D}/stres_yillik.csv")

    # ---------------- 4) TP başarısızlık dönemleri
    print("\n[ÖLÇÜM] 4) TP BAŞARISIZLIK DÖNEMLERİ")
    for w in (30, 60, 90):
        Rw = V[["tp", "funding", "tutus_fiyat", "getiri", "tp_sayi"]].rolling(w).sum()
        Rw["kitap_vol"] = V.kitap_vol.rolling(w).mean(); Rw = Rw.dropna()
        # örtüşmeyen en düşük 5 pencere
        secim = []; kalan = Rw.copy()
        while len(secim) < 5 and len(kalan):
            t = kalan.tp.idxmin(); secim.append(t); kalan = kalan[(kalan.index < t - pd.Timedelta(days=w)) | (kalan.index > t + pd.Timedelta(days=w))]
        tab = Rw.loc[secim].copy(); tab.index = [f"{(t - pd.Timedelta(days=w-1)).date()} – {t.date()}" for t in secim]
        tab[["tp", "funding", "tutus_fiyat", "getiri"]] *= 100
        print(f"  en düşük TP'li {w} g pencereler (örtüşmeyen; puan) — karşılaştırma: tüm pencerelerin medyanı "
              f"TP {Rw.tp.median()*100:.1f} · funding {Rw.funding.median()*100:.1f} · tutuş {Rw.tutus_fiyat.median()*100:.1f} · "
              f"getiri {Rw.getiri.median()*100:.1f} · TP sayısı {Rw.tp_sayi.median():.0f} · vol {Rw.kitap_vol.median():.0f}")
        print(tab.round(1).to_string())
        tab.to_csv(f"{D}/tp_dusuk_{w}g.csv")
    # zaman ilişkisi: bu ayın TP'si (düşük mü) -> sonraki ayların getirisi; ve tersi
    print("\n  [ÖLÇÜM] zaman sıralaması (aylık): korelasyon TP(t) ile getiri(t+k) ve tutuş fiyatı(t+k)")
    for k in (-2, -1, 0, 1, 2, 3):
        print(f"   k={k:+d}: getiri {A.tp.corr(A.getiri.shift(-k)):+.2f} · tutuş {A.tp.corr(A.tutus_fiyat.shift(-k)):+.2f} · "
              f"TP(t+k) {A.tp.corr(A.tp.shift(-k)):+.2f}")
    lowtp = A.tp < A.tp.quantile(0.25)
    for k in (0, 1, 2, 3):
        g = A.getiri.shift(-k)
        print(f"   TP alt çeyrek ay -> {k} ay sonra: getiri ort {g[lowtp].mean()*100:+.1f} (diğer {g[~lowtp].mean()*100:+.1f}) · "
              f"zarar ayı oranı %{(g[lowtp] < 0).mean()*100:.0f} (diğer %{(g[~lowtp] < 0).mean()*100:.0f}) · n {int(lowtp.sum())}")
    # zarar aylarından önce TP gidişatı
    zar = A.index[A.getiri < 0]
    pre = pd.DataFrame({f"t{k:+d}": [A.tp.shift(-k).get(t, np.nan) * 100 for t in zar] for k in (-3, -2, -1, 0)}, index=zar.date)
    print("   zarar aylarında ve öncesinde TP (puan / ay; tüm ayların medyanı "
          f"{A.tp.median()*100:.1f}):\n" + pre.round(1).to_string())
    # basit permütasyon: TP alt çeyrek -> sonraki ay zarar ilişkisi tesadüf mü (blok karıştırma yok, aylık otokorelasyon notu raporda)
    rng_ = np.random.default_rng(691); g1 = A.getiri.shift(-1); m = g1.notna()
    gozlem = (g1[lowtp & m] < 0).mean() - (g1[~lowtp & m] < 0).mean(); sim = []
    lt = lowtp[m].values; gv = (g1[m] < 0).values
    for _ in range(5000):
        p = rng_.permutation(lt); sim.append(gv[p].mean() - gv[~p].mean())
    print(f"   permütasyon: sonraki ay zarar oranı farkı {gozlem*100:+.1f} puan · p = {(np.array(sim) >= gozlem).mean():.3f} (5.000 karıştırma)")


if __name__ == "__main__":
    {"kos": kos, "kos_seviye": kos_seviye, "analiz": analiz}[sys.argv[1]]()
