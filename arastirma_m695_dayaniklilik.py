#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 695 — STRATEJİ DAYANIKLILIK VE BAŞARISIZLIK ANALİZİ. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Baz (dondurulmuş referans): /tmp/m622/M357_EK_P3T2_2000_{0,1}.pkl (P3T2, 2.000 $, 1,0x, gerçekçi model).
Motor kopyası /tmp/g33_m695.py: g33.py + TEK düğme TP_DOLUM_P (TP / kademe limitinin seviyeye değdiği barda dolma olasılığı; deterministik
sözde rastgele; 1 = parite). Diğer bütün senaryolar yalnız ORTAM DEĞİŞKENİYLE (stres / duyarlılık; önerilen ayar değildir).
Her koşu GUNLUK_KATKI defteri de yazar (sermaye kullanımı, pozisyon, long / short katkısı için; E çıktısını değiştirmez — madde 690 / 694).
Önceki maddelerde ölçülenler TEKRARLANMAZ, referans verilir: listeleme −%25 / 50 / 75 ve 6 ay duruş, genç coin yok (694); TP kayması ve delme
(691); TP coinlerini çıkarma (691 / 692); yaş ayrıştırması (694).
  python3 arastirma_m695_dayaniklilik.py kos      -> /tmp/m695/E_<senaryo>_<hiza>.pkl + gk (tek işçi; ANALİZİ EŞZAMANLI ÇALIŞTIRMAYIN)
  python3 arastirma_m695_dayaniklilik.py analiz   -> /tmp/m695/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle, json
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
from tradfi_liste import TRADFI

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m695"; os.makedirs(D, exist_ok=True)
S690, S691, S692, S693, S694 = "/tmp/m690", "/tmp/m691", "/tmp/m692", "/tmp/m693", "/tmp/m694"
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
KOM0 = float(ENV["KOM"])

# H) parametre çevresi: tek seferde bir parametre, mevcut değerin iki yanı (yeni optimum ARANMAZ; plato / kırılma için)
DUY = {"TPL": ("0.50", "0.70"), "TPS": ("0.15", "0.25"), "MERD_ESIK": ("0.35", "0.55"), "MERD_PAY": ("0.70", "0.90"),
       "MERDS_ESIK": ("0.12", "0.18"), "REB_GUN": ("4", "6"), "HAVUZ": ("3", "5"), "YAS_GUN": ("30", "90"),
       "HACIM_ESIK": ("5e7", "1e8"), "SLL24": ("0.35", "0.55")}


def listeleme():
    C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
    return C.apply(lambda s: s.first_valid_index())


def net_sirasi():
    G = pd.read_csv(f"{S690}/gun_coin_bilesen.csv")
    G["net"] = G.tp + G.funding + G.fiyat + G.stop - G.komisyon
    return G.groupby("sembol").net.sum().sort_values(ascending=False)


def senaryolar():
    S = {}
    for p, (a, b) in DUY.items():
        S[f"H_{p}_lo"] = {p: a}; S[f"H_{p}_hi"] = {p: b}
    for p in (0.97, 0.90, 0.80, 0.70):
        # TP / kademe dolum olasılığı + giriş / dengeleme emirlerinin dolmayan payı için taker'a düşme bedeli (10 bp kayma varsayımı)
        S[f"E_{int(p*100)}"] = {"TP_DOLUM_P": str(p), "KOM": f"{KOM0 + (1 - p) * 0.0010:.6f}"}
    fv = listeleme(); b0 = pd.Timestamp("2025-01-01")
    for g in (30, 60, 90, 180):
        sec = sorted(s for s, t in fv.items() if b0 <= t < b0 + pd.Timedelta(days=g) and s not in TRADFI and s not in M.D8)
        S[f"A_DUR{g}"] = {"SEMBOL_HARIC": ",".join(M.D8 + sec)}
    top = list(net_sirasi().index)
    for n in (1, 3, 5, 10):
        S[f"G_NET{n}"] = {"SEMBOL_HARIC": ",".join(M.D8 + top[:n])}
    return S


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "def _dol(sev,uzun,i,k):\n"; assert s.count(a) == 1
    s = s.replace(a, "_TDP=float(os.environ.get('TP_DOLUM_P','1'))\n"
                     "def _dolp(i,k):\n    return _TDP>=1 or (((i*1000003+k*7919+12345)%100003)/100003.0)<_TDP\n" + a, 1)
    for lv in ("sev", "_s0", "_sm"):
        a = f"(uzun and HV[i+1,k]>={lv}) or ((not uzun) and LV[i+1,k]<={lv})"; assert s.count(a) == 1, lv
        s = s.replace(a, f"(_dolp(i,k) and ((uzun and HV[i+1,k]>={lv}) or ((not uzun) and LV[i+1,k]<={lv})))", 1)
    open("/tmp/g33_m695.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h, gk=True):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    ex = {"GUNLUK_KATKI": f"{D}/gk_{ad}_{h}.pkl", "GK_BAS": "2019-01-01"} if gk else {}
    env = dict(os.environ, **{**ENV, **ek, **ex}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m695.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    kopya()
    for h in (0, 1):
        rc = _kos1("P0", {}, h, gk=True)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · kopya (düğme kapalı, defter açık) vs g33.py -> {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    S = senaryolar(); json.dump(S, open(f"{D}/senaryolar.json", "w"), ensure_ascii=False, indent=0)
    for ad, ek in S.items():
        for h in (0, 1):
            print(ad, h, _kos1(ad, ek, h), flush=True)


# ------------------------------------------------------------------------------------------------ analiz yardımcıları
def _seri_yol(yol, ad):
    hedef = f"{D}/M357_EK_{ad}.pkl"
    if not os.path.exists(hedef): os.symlink(yol, hedef)
    M.CIKTI = D; s = M.gunluk(f"M357_EK_{ad}"); s.index = pd.to_datetime(s.index); return s


def seri(ad, kaynak=D):
    if ad == "BAZ": return sum(_seri_yol(REF.format(h=h), f"BAZ_{h}") for h in (0, 1)) / 2
    return sum(_seri_yol(f"{kaynak}/E_{ad}_{h}.pkl", f"{os.path.basename(kaynak)}_{ad}_{h}") for h in (0, 1)) / 2


def tam(ad, kaynak=D):
    return all(os.path.exists(f"{kaynak}/E_{ad}_{h}.pkl") for h in (0, 1))


def olc(d):
    d = d.dropna(); e = (1 + d).cumprod(); a = d.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    cagr = (e.iloc[-1] ** (365.25 / len(d)) - 1) * 100; dd = (e / e.cummax() - 1).min() * 100
    return dict(cagr=cagr, sharpe=d.mean() / d.std() * np.sqrt(365.25), maks_dd=dd, calmar=cagr / abs(dd) if dd < 0 else np.nan,
                en_kotu_gun=d.min() * 100, en_kotu_ay=a.min() * 100, zarar_ay=(a < 0).mean() * 100)


def defter(ad, kaynak=D):
    """Sermaye kullanımı, pozisyon (coin-gün), long / short katkısı (fiyat + funding; komisyon hariç)."""
    yollar = [f"{kaynak}/gk_{ad}_{h}.pkl" for h in (0, 1)] if ad != "BAZ" else [f"{S690}/gk_{h}.pkl" for h in (0, 1)]
    if not all(os.path.exists(y) for y in yollar): return {}
    G = pd.concat([pd.read_pickle(y) for y in yollar]); G["gun"] = pd.to_datetime(G.gun)
    if "fiyat" not in G.columns: G["fiyat"] = G.fiyat_top
    G["bw"] = G.ort_poz.abs() * G.bar / 6; G["k"] = G.fiyat + G.funding
    gg = G.groupby("gun")
    brut = gg.bw.sum() / 2
    return dict(brut_ort=brut.mean(), brut_p95=brut.quantile(.95), coin_gun_ort=gg.sembol.nunique().mean() / 2,
                long_puan=G.k[G.ort_poz > 0].sum() / 2 * 100, short_puan=G.k[G.ort_poz < 0].sum() / 2 * 100)


def yillik(d): return d.groupby(d.index.year).apply(lambda x: ((1 + x).prod() - 1) * 100)


def tablo(adlar, baz, etiket=None):
    rows = []; yy = {}
    for ad in adlar:
        if ad != "BAZ" and not tam(ad): rows.append(dict(senaryo=ad, durum="EKSİK")); continue
        s = baz if ad == "BAZ" else seri(ad)
        r = dict(senaryo=etiket.get(ad, ad) if etiket else ad, durum="tamam", **olc(s), **defter(ad)); rows.append(r); yy[r["senaryo"]] = yillik(s)
    T = pd.DataFrame(rows)
    if "cagr" in T: T["cagr_fark"] = T.cagr - T.cagr.iloc[0]
    return T, pd.DataFrame(yy)


def guven(fark, n_hiza_fark=None):
    return fark


# ------------------------------------------------------------------------------------------------ analiz
def analiz():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    BAZ = seri("BAZ"); S = json.load(open(f"{D}/senaryolar.json"))
    eksik_tum = [ad for ad in S if not tam(ad)]
    print(f"[KONTROL] senaryo {len(S)} · eksik {len(eksik_tum)} {eksik_tum if eksik_tum else ''}")
    print("[KONTROL] parite: " + ", ".join(f"hiza {h} {'AYNI' if open(f'{D}/E_P0_{h}.pkl','rb').read()==open(REF.format(h=h),'rb').read() else 'FARKLI'}" for h in (0, 1)))
    T0, Y0 = tablo(["BAZ"], BAZ, {"BAZ": "BAZ"})
    print("\n[ÖLÇÜM] BAZ (dondurulmuş referans):\n" + T0.round(2).to_string(index=False) + "\n  yıllık %:\n" + Y0.round(1).T.to_string())

    # ================= A) listeleme kuraklığı
    print("\n================ A) YENİ LİSTELEME KURAKLIĞI")
    TA, YA = tablo(["BAZ", "A_DUR30", "A_DUR60", "A_DUR90", "A_DUR180"], BAZ,
                   {"BAZ": "BAZ", "A_DUR30": "2025-01'den 30 g duruş", "A_DUR60": "60 g duruş", "A_DUR90": "90 g duruş", "A_DUR180": "180 g duruş"})
    print("[ÖLÇÜM; senaryo VARSAYIM] motor (2025-01-01'de başlayan duruş; o pencerede listelenen coinler evrenden çıkar):\n" + TA.round(2).to_string(index=False))
    print("  yıllık %:\n" + YA.round(1).T.to_string())
    b0 = pd.Timestamp("2025-01-01"); e0 = b0 + pd.DateOffset(months=18)
    for ad in ["A_DUR30", "A_DUR60", "A_DUR90", "A_DUR180"]:
        if tam(ad):
            s = seri(ad); print(f"  {ad}: duruştan itibaren 18 ay CAGR baz %{olc(BAZ[(BAZ.index>=b0)&(BAZ.index<e0)])['cagr']:.0f} -> %{olc(s[(s.index>=b0)&(s.index<e0)])['cagr']:.0f}")
    TA.to_csv(f"{D}/A_motor.csv", index=False); YA.to_csv(f"{D}/A_yillik.csv")
    # statik: bütün çeyrek başlangıçları × süre (seçilmiş dönem yok) — madde 691: statik ≈ motor
    G = pd.read_csv(f"{S690}/gun_coin_bilesen.csv", parse_dates=["gun"]); G["net"] = G.tp + G.funding + G.fiyat + G.stop - G.komisyon
    Pn = G.pivot_table(index="gun", columns="sembol", values="net", aggfunc="sum").fillna(0)
    fv = listeleme(); rows = []
    for bas in pd.date_range("2022-01-01", "2026-01-01", freq="QS"):
        for g in (30, 60, 90, 180):
            sec = [s for s, t in fv.items() if bas <= t < bas + pd.Timedelta(days=g) and s in Pn.columns]
            d = BAZ.sub(Pn[sec].sum(axis=1).reindex(BAZ.index).fillna(0), fill_value=0)
            w = (BAZ.index >= bas) & (BAZ.index < bas + pd.DateOffset(months=18))
            rows.append(dict(bas=bas.date(), sure=g, coin=len(sec), cagr_18ay_baz=olc(BAZ[w])["cagr"], cagr_18ay=olc(d[w])["cagr"],
                             kayip_puan_18ay=(BAZ[w].sum() - d[w].sum()) * 100))
    AS = pd.DataFrame(rows); AS["oran"] = AS.cagr_18ay / AS.cagr_18ay_baz
    print("[ÖLÇÜM] statik (17 çeyrek başı × 4 süre; duruştan sonraki 18 ay; yeniden dağıtım yok):")
    print(AS.groupby("sure").agg(pencere=("bas", "size"), coin_ort=("coin", "mean"), kayip_puan_med=("kayip_puan_18ay", "median"),
                                 kayip_puan_maks=("kayip_puan_18ay", "max"), cagr_oran_med=("oran", "median"), cagr_oran_min=("oran", "min")).round(3).to_string())
    AS.to_csv(f"{D}/A_statik.csv", index=False)
    if tam("A_DUR180"):
        st = AS[(AS.bas == b0.date()) & (AS.sure == 180)].iloc[0]
        print(f"  karşılaştırma 2025-01 180 g: statik 18 ay CAGR %{st.cagr_18ay:.0f} · motor %{olc(seri('A_DUR180')[(BAZ.index>=b0)&(BAZ.index<e0)])['cagr']:.0f}")
    print("  referans (madde 694, tekrar koşulmadı): listeleme −%25 / −%50 / −%75 -> 2024-26 CAGR %141-186 / %104-107 / %65-69; genç coin yok %51;"
          " eski coinler aynı brüt maruziyette maruziyet başı getiriyi %187 -> %97'ye indiriyor")

    # ================= B) Monte Carlo / blok bootstrap
    print("\n================ B) DURAĞAN BLOK BOOTSTRAP (Politis-Romano; 10.000 simülasyon; günlük bağımlılık blokla korunur)")
    rng = np.random.default_rng(695)
    def boot(d, ufuk, blok, n=10000):
        x = d.dropna().values; N = len(x); out = np.empty((n, ufuk))
        p = 1.0 / blok
        idx = np.empty((n, ufuk), dtype=np.int64); idx[:, 0] = rng.integers(0, N, n)
        yeni = rng.random((n, ufuk)) < p; rs = rng.integers(0, N, (n, ufuk))
        for t in range(1, ufuk):
            idx[:, t] = np.where(yeni[:, t], rs[:, t], (idx[:, t - 1] + 1) % N)
        out = x[idx]
        eq = np.cumprod(1 + out, axis=1)
        cagr = (eq[:, -1] ** (365.25 / ufuk) - 1) * 100
        dd = ((eq / np.maximum.accumulate(eq, axis=1)) - 1).min(axis=1) * 100
        sh = out.mean(axis=1) / out.std(axis=1) * np.sqrt(365.25)
        ay = out[:, :ufuk // 30 * 30].reshape(n, -1, 30); aym = (np.prod(1 + ay, axis=2) - 1).min(axis=1) * 100
        return dict(cagr_p5=np.percentile(cagr, 5), cagr_med=np.median(cagr), cagr_p95=np.percentile(cagr, 95), sharpe_p5=np.percentile(sh, 5),
                    sharpe_med=np.median(sh), dd_med=np.median(dd), dd_p5=np.percentile(dd, 5), dd_p1=np.percentile(dd, 1),
                    en_kotu_gun_p5=np.percentile(out.min(axis=1) * 100, 5), en_kotu_30g_p5=np.percentile(aym, 5),
                    kayip_olasilik=(eq[:, -1] < 1).mean() * 100, dd20_olasilik=(dd <= -20).mean() * 100, dd30_olasilik=(dd <= -30).mean() * 100,
                    dd50_olasilik=(dd <= -50).mean() * 100)
    BR = []
    seriler = {"BAZ 2020-26": BAZ, "BAZ 2024-26": BAZ[BAZ.index >= "2024-01-01"], "BAZ 2022 (en zayıf yıl)": BAZ[BAZ.index.year == 2022]}
    if tam("Y365", S693): seriler["genç coin yok (694 / 693) 2024-26"] = seri("Y365", S693)[lambda s: s.index >= "2024-01-01"]
    if tam("E_80"): seriler["maker dolum %80 (E_80)"] = seri("E_80")
    if tam("YOK", S692): seriler["TP yok (692)"] = seri("YOK", S692)
    for ad, d in seriler.items():
        for blok in (10, 30):
            BR.append(dict(seri=ad, blok_gun=blok, ufuk="1 yıl", **boot(d, 365, blok)))
    BRt = pd.DataFrame(BR); print(BRt.round(2).to_string(index=False)); BRt.to_csv(f"{D}/B_bootstrap.csv", index=False)
    print("  VARSAYIM: geçmiş günlük getirilerin dağılımı ve bağımlılık yapısı geleceği temsil eder; bootstrap rejim değişimini (ör. listeleme kuraklığı) üretemez.")

    # ================= C) walk-forward
    print("\n================ C) WALK-FORWARD (aday kümesi = baz + 20 komşu ayar; her yıl yalnız geçmişe göre seçim)")
    aday = ["BAZ"] + [a for a in S if a.startswith("H_") and tam(a)]
    SR = {a: (BAZ if a == "BAZ" else seri(a)) for a in aday}
    WF = []
    for kip in ("genişleyen", "kayan 2 yıl"):
        oos = []; sec_log = []
        for y in range(2022, 2027):
            bas = pd.Timestamp(f"{y}-01-01"); gb = pd.Timestamp("2020-08-01") if kip == "genişleyen" else bas - pd.DateOffset(years=2)
            puan = {a: olc(s[(s.index >= gb) & (s.index < bas)])["sharpe"] for a, s in SR.items()}
            sec = max(puan, key=puan.get); sec_log.append(f"{y}:{sec}")
            oos.append(SR[sec][(SR[sec].index >= bas) & (SR[sec].index < pd.Timestamp(f"{y+1}-01-01"))])
        o = pd.concat(oos); b = BAZ[BAZ.index >= "2022-01-01"]
        WF.append(dict(kip=kip, **{f"wf_{k}": v for k, v in olc(o).items()}, **{f"baz_{k}": v for k, v in olc(b).items()}, secimler=" ".join(sec_log)))
        print(f"  {kip}: seçimler {' '.join(sec_log)}")
        print("   yıllık WF / baz %: " + " · ".join(f"{y} {a:.0f}/{c:.0f}" for (y, a), c in zip(yillik(o).items(), yillik(b).values)))
    WFt = pd.DataFrame(WF); print(WFt.round(2).drop(columns="secimler").to_string(index=False)); WFt.to_csv(f"{D}/C_walkforward.csv", index=False)
    # seçimin değeri: her yıl geçmişte en iyi olan aday o yıl adaylar arasında kaçıncı?
    rk = []
    for y in range(2022, 2027):
        yr = {a: olc(s[s.index.year == y])["sharpe"] for a, s in SR.items()}
        gec = {a: olc(s[(s.index >= "2020-08-01") & (s.index < f"{y}-01-01")])["sharpe"] for a, s in SR.items()}
        r = pd.Series(yr).rank(ascending=False); rk.append(dict(yil=y, gecmis_en_iyi=max(gec, key=gec.get), o_yil_sirasi=r[max(gec, key=gec.get)],
                                                               baz_sirasi=r["BAZ"], aday=len(SR), sira_kor=pd.Series(gec).corr(pd.Series(yr), method="spearman")))
    RK = pd.DataFrame(rk); print("  geçmiş Sharpe sırası -> o yılın sırası:\n" + RK.round(2).to_string(index=False)); RK.to_csv(f"{D}/C_sira.csv", index=False)
    print("  UYARI: baz ayar 2020-2026 verisinin TAMAMI üzerinde geliştirildi; adaylar bazın komşuları -> bu walk-forward bağımsız OOS DEĞİL. "
          "Parametre dondurulduktan sonraki ilk gerçek OOS ayı 2026-10 (izleme_ekim_oos; veri 2 Kasım'da).")

    # ================= D) coin yaşı (694'e ek: rejim kontrolü, MFE / MAE, sermaye)
    print("\n================ D) COİN YAŞI × REJİM (694'e ek; 2021+)")
    E = pd.read_pickle(f"{S693}/epizot_yol.pkl"); L = pd.read_csv(f"{S693}/rejim_etiket.csv", index_col=0, parse_dates=True)
    E = E[E.bas >= "2021-01-01"].copy()
    bins = [-1, 90, 180, 365, 730, 1e9]; lab = ["60-90 g", "90-180 g", "180-365 g", "1-2 yıl", ">2 yıl"]
    E["yas_grup"] = pd.cut(E.yas_bas, bins, labels=lab)
    E["btc_yon"] = E.bas.dt.normalize().map(L["BTC yön"]); E["kitap_vol"] = E.bas.dt.normalize().map(L["Kitap oynaklık"])
    DT = E.groupby("yas_grup", observed=True).agg(poz=("ep", "size"), tp_orani=("tp_oldu", "mean"), poz_basi_bp=("pnl", lambda s: s.mean() * 1e4),
                                                  tp_bp=("fiy", lambda s: s[E.loc[s.index, "tp_oldu"]].sum() / max(len(s), 1) * 1e4),
                                                  funding_bp=("fon", lambda s: s.mean() * 1e4), mfe_med=("mfe", "median"), mae_med=("mae_bar", "median"),
                                                  sermaye_gun=("agirlik_gun", "sum"))
    DT[["tp_orani", "mfe_med", "mae_med"]] *= 100; DT["sermaye_payi"] = DT.sermaye_gun / DT.sermaye_gun.sum() * 100
    DT["sermaye_basi_yillik"] = E.groupby("yas_grup", observed=True).apply(lambda d: d.pnl.sum() / d.agirlik_gun.sum() * 365 * 100, include_groups=False)
    print(DT.round(2).to_string()); DT.to_csv(f"{D}/D_yas.csv")
    for col in ("btc_yon", "kitap_vol"):
        pv = E.pivot_table(index="yas_grup", columns=col, values="pnl", aggfunc="mean", observed=True) * 1e4
        print(f"  pozisyon başı net bp, yaş × {col}:\n" + pv.round(1).to_string()); pv.to_csv(f"{D}/D_yas_{col}.csv")

    # ================= E) icra stresi
    print("\n================ E) İCRA STRESİ (motor; TP / kademe dolum olasılığı + dolmayan giriş payı için 10 bp taker kayması)")
    TE, YE = tablo(["BAZ", "E_97", "E_90", "E_80", "E_70"], BAZ,
                   {"BAZ": "BAZ (dokunan limit %100 dolar)", "E_97": "dolum %97", "E_90": "dolum %90", "E_80": "dolum %80", "E_70": "dolum %70"})
    print(TE.round(2).to_string(index=False)); print("  yıllık %:\n" + YE.round(1).T.to_string()); TE.to_csv(f"{D}/E_icra.csv", index=False); YE.to_csv(f"{D}/E_yillik.csv")
    print("  VARSAYIM: dolmayan TP limiti bekler ve sonraki barlarda yeniden dokunursa yine aynı olasılıkla dolar; kısmi dolum, emir bekleme süresi ve"
          " ters seçilim (adverse selection) modellenmedi -> UNKNOWN. Referans (691): ek 20 bp kayma CAGR −5,8; 20 bp delme şartı −4,1.")

    # ================= F) piyasa stresi (portföy düzeyi şoklar, tarihsel pozisyonlara)
    print("\n================ F) PİYASA STRESİ")
    P = pd.read_pickle(f"{S693}/gunluk_ohlc.pkl"); Cg = P["C"]; r = Cg.pct_change()
    btc = r["BTCUSDT"]
    beta = r.rolling(90, min_periods=45).cov(btc).div(btc.rolling(90, min_periods=45).var(), axis=0).shift(1)   # nedensel
    gk = pd.concat([pd.read_pickle(f"{S690}/gk_{h}.pkl") for h in (0, 1)]); gk["gun"] = pd.to_datetime(gk.gun)
    gk["sw"] = gk.ort_poz * gk.bar / 6
    W = (gk.groupby(["gun", "sembol"]).sw.sum() / 2).unstack().fillna(0); W = W[W.index >= "2021-01-01"]
    bt = beta.reindex(index=W.index, columns=W.columns).fillna(1.0).clip(-1, 4)
    Wl, Ws = W.clip(lower=0), W.clip(upper=0)
    net = W.sum(axis=1); brut = W.abs().sum(axis=1)
    def sok(f):
        return f.sum(axis=1) * 100
    sc = {}
    for x in (-0.20, -0.40, +0.20, +0.40):
        sc[f"BTC {x:+.0%} (beta)"] = sok(W * (bt * x).clip(-0.95, 3))
    sc["BTC −%30, korelasyon artışı (long beta ×1,5, short beta ×0,5)"] = sok(Wl * (bt * 1.5 * -0.30).clip(-0.95, 3) + Ws * (bt * 0.5 * -0.30).clip(-0.95, 3))
    def topk(Wx, k, hareket):
        out = pd.Series(0.0, index=Wx.index)
        for d, row in Wx.iterrows():
            idx = row.abs().nlargest(k).index; out[d] = (row[idx] * hareket).sum() * 100
        return out
    sc["short sıkışması: en büyük 3 short +%100"] = topk(Ws, 3, 1.0)
    sc["long çöküşü: en büyük 3 long −%50 + BTC −%10"] = topk(Wl, 3, -0.5) + sok(W * (bt * -0.10).clip(-0.95, 3))
    sc["likidite kaybı: brütün %2'si çıkış maliyeti"] = -brut * 2
    sc["likidite kaybı: brütün %5'i"] = -brut * 5
    B = pd.read_csv(f"{S690}/gun_kitap_bilesen.csv", parse_dates=["gun"], index_col="gun")
    f30 = B.funding[::-1].rolling(30).sum()[::-1].shift(-1).reindex(W.index) * 100
    sc["funding tersine döner (sonraki 30 g funding −2×)"] = -2 * f30
    SC = pd.DataFrame(sc)
    FT = pd.DataFrame({"medyan": SC.median(), "en_kotu_%5": SC.quantile(0.05), "en_kotu": SC.min(), "en_iyi": SC.max()}).T.T
    print("[VARSAYIM: şok büyüklükleri] [ÖLÇÜM: 2021+ her günün gerçek pozisyonlarına uygulandı] tek günlük kitap etkisi, özkaynağın %'si:\n" + FT.round(2).to_string())
    print(f"  kitap: brüt maruziyet ort {brut.mean():.2f} (maks {brut.max():.2f}) · net (long − short) ort {net.mean():+.2f} (%5 {net.quantile(.05):+.2f}, %95 {net.quantile(.95):+.2f})")
    print("  teminat: 1,0x doz, brüt ≤ ~0,9 özkaynak; çapraz teminatta tasfiye yalnız kayıp ≈ özkaynak − bakım teminatı (brüt × ~%0,5-2,5) olursa. "
          f"En kötü senaryo günü {SC.min().min():.1f}% -> tasfiye yok. Tek pozisyon izole 1x short: fiyat ~+%95-100'de tasfiye (pozisyon değeri kadar kayıp).")
    SC.to_csv(f"{D}/F_sok.csv"); FT.to_csv(f"{D}/F_sok_ozet.csv")
    # gerçek stres günleri
    btc_r = btc.reindex(BAZ.index)
    dn = btc_r.nsmallest(10); up = btc_r.nlargest(10)
    fw7 = BAZ[::-1].rolling(7).sum()[::-1]
    gs = pd.DataFrame({"btc_%": pd.concat([dn, up]) * 100, "kitap_gun_%": BAZ.reindex(pd.concat([dn, up]).index) * 100,
                       "kitap_7g_%": fw7.reindex(pd.concat([dn, up]).index) * 100})
    print("  [ÖLÇÜM] gerçek en sert 10 BTC düşüş ve 10 yükseliş günü (kitap aynı gün ve 7 gün):\n" + gs.round(2).to_string()); gs.to_csv(f"{D}/F_gercek_gunler.csv")
    # faktörler
    ew = r.where(Cg.notna()).reindex(BAZ.index).median(axis=1)
    lr = (Wl.shift(0) * r.reindex(index=W.index, columns=W.columns)).sum(axis=1); sr_ = (Ws * r.reindex(index=W.index, columns=W.columns)).sum(axis=1)
    k = pd.DataFrame({"kitap": BAZ.reindex(W.index), "btc": btc.reindex(W.index), "alt": ew.reindex(W.index), "long_bacak": lr, "short_bacak": sr_}).dropna()
    bb = np.polyfit(k.btc, k.kitap, 1)[0]; ba = np.polyfit(k.alt, k.kitap, 1)[0]
    print(f"  [ÖLÇÜM] faktör: kitap ↔ BTC korelasyon {k.kitap.corr(k.btc):+.2f} (beta {bb:+.3f}) · ↔ alt evren medyanı {k.kitap.corr(k.alt):+.2f} (beta {ba:+.3f}) · "
          f"long bacak ↔ short bacak {k.long_bacak.corr(k.short_bacak):+.2f} (short bacak işaretli; −1'e yakın = iyi hedge)")
    ac = r.reindex(index=W.index).rolling(30).corr(btc.reindex(W.index))
    ort_kor = ac.where(W.abs() > 0).mean(axis=1)
    hi = ort_kor >= ort_kor.median()
    print(f"  tutulan coinlerin BTC ile 30 g korelasyonu yüksekken kitap günlük ort {BAZ.reindex(W.index)[hi].mean()*1e4:.1f} bp, sd {BAZ.reindex(W.index)[hi].std()*1e4:.0f} · "
          f"düşükken {BAZ.reindex(W.index)[~hi].mean()*1e4:.1f} bp, sd {BAZ.reindex(W.index)[~hi].std()*1e4:.0f}")

    # ================= G) yoğunlaşma
    print("\n================ G) YOĞUNLAŞMA")
    top = net_sirasi()
    TG, YG = tablo(["BAZ", "G_NET1", "G_NET3", "G_NET5", "G_NET10"], BAZ,
                   {"BAZ": "BAZ", "G_NET1": f"net ilk 1 ({top.index[0]}) çıkar", "G_NET3": "net ilk 3 çıkar", "G_NET5": "net ilk 5 çıkar", "G_NET10": "net ilk 10 çıkar"})
    print("[ÖLÇÜM; geriye bakan seçim = en kötü durum] motor (evrenden çıkarıldı):\n" + TG.round(2).to_string(index=False)); print("  yıllık %:\n" + YG.round(1).T.to_string())
    print(f"  çıkarılan coinler: {list(top.index[:10])}")
    TG.to_csv(f"{D}/G_coin.csv", index=False); YG.to_csv(f"{D}/G_yillik.csv")
    am = BAZ.resample("ME").sum(); rows = []
    for n in (0, 1, 3, 5, 10):
        en_iyi = am.nlargest(n).index if n else []
        d = BAZ[~BAZ.index.to_period("M").isin(pd.PeriodIndex(en_iyi, freq="M"))] if n else BAZ
        rows.append(dict(cikarilan_en_iyi_ay=n, aylar=",".join(t.strftime("%Y-%m") for t in en_iyi), **olc(d)))
    GA = pd.DataFrame(rows); print("  en kârlı aylar çıkarılınca (kalan günler birleştirilerek):\n" + GA.round(2).to_string(index=False)); GA.to_csv(f"{D}/G_aylar.csv", index=False)
    print(f"  long / short (baz, fiyat + funding, komisyon hariç; puan): {defter('BAZ').get('long_puan', np.nan):+.1f} / {defter('BAZ').get('short_puan', np.nan):+.1f}")
    ylk = gk.assign(k=gk.fiyat_top + gk.funding, yil=gk.gun.dt.year, yon=np.sign(gk.ort_poz)).groupby(["yil", "yon"]).k.sum().unstack() / 2 * 100
    print("  yıl yıl long (+1) / short (−1) katkısı:\n" + ylk.round(1).to_string()); ylk.to_csv(f"{D}/G_long_short_yil.csv")

    # ================= H) parametre duyarlılığı
    print("\n================ H) PARAMETRE DUYARLILIĞI (tek parametre, mevcut değerin iki yanı; yeni optimum aranmadı)")
    rows = [dict(parametre="—", deger="mevcut", **olc(BAZ), **defter("BAZ"))]
    for p, (a, b) in DUY.items():
        for yon, v in (("lo", a), ("hi", b)):
            ad = f"H_{p}_{yon}"
            if tam(ad): rows.append(dict(parametre=p, deger=f"{v} (mevcut {ENV.get(p, '?')})", **olc(seri(ad)), **defter(ad)))
            else: rows.append(dict(parametre=p, deger=v, durum="EKSİK"))
    TH = pd.DataFrame(rows); TH["cagr_fark"] = TH.cagr - TH.cagr.iloc[0]; TH["sharpe_fark"] = TH.sharpe - TH.sharpe.iloc[0]
    print(TH.round(2).to_string(index=False)); TH.to_csv(f"{D}/H_duyarlilik.csv", index=False)
    yh = pd.DataFrame({r_["parametre"] + " " + r_["deger"].split(" ")[0]: yillik(seri(f"H_{r_['parametre']}_{'lo' if r_['deger'].split(' ')[0]==DUY[r_['parametre']][0] else 'hi'}"))
                       for _, r_ in TH.iloc[1:].iterrows() if r_.get("durum") != "EKSİK"})
    yh.insert(0, "BAZ", yillik(BAZ)); print("  yıllık %:\n" + yh.round(0).T.to_string()); yh.to_csv(f"{D}/H_yillik.csv")
    print(f"  plato: 20 komşudan CAGR'si bazın ±%20'si içinde kalan {int((TH.cagr.iloc[1:].between(TH.cagr.iloc[0]*0.8, TH.cagr.iloc[0]*1.2)).sum())}; "
          f"Sharpe'ı 3'ün altına düşen {int((TH.sharpe.iloc[1:] < 3).sum())}; bazdan iyi CAGR {int((TH.cagr.iloc[1:] > TH.cagr.iloc[0]).sum())} "
          "(baz tam veriyle seçildiği için 'bazdan iyi' komşu, aşırı uyum değil gürültü göstergesidir)")

    bek = ["A_motor.csv", "A_statik.csv", "B_bootstrap.csv", "C_walkforward.csv", "C_sira.csv", "D_yas.csv", "E_icra.csv", "F_sok.csv", "F_gercek_gunler.csv",
           "G_coin.csv", "G_aylar.csv", "H_duyarlilik.csv"] + [f"E_{a}_{h}.pkl" for a in ["P0"] + list(S) for h in (0, 1)]
    yok = [b for b in bek if not os.path.exists(f"{D}/{b}")]
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if not yok else f"EKSİK: {yok}")


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz, "kopya": kopya}[sys.argv[1]]()
