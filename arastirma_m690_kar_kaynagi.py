#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 690 — KÂR KAYNAĞI SÜRDÜRÜLEBİLİRLİK ANALİZİ. KAYNAK KOD DEĞİŞMEZ; strateji / parametre değişmez; göstergeler canlıya BAĞLANMAZ.
Önerilen ayar (P3T2 = T7K + koşullu stop, 2.000 $, 1,0x; gerçekçi model) motorun KOPYASIYLA (/tmp/g33_m690.py) koşulur; kopya yalnız
mevcut GUNLUK_KATKI defterine sütun ekler (çıkış barı fiyatı türüne göre, komisyon payı). Parite: E dosyası g33.py ile bayt bayt aynı.
  python3 arastirma_m690_kar_kaynagi.py kos      -> /tmp/m690/{E,gk,katki,cikis}_{0,1}.pkl (tek işçi; ~6 dk)
  python3 arastirma_m690_kar_kaynagi.py analiz   -> /tmp/m690/*.csv + ekran raporu
TANIMLAR: funding = −poz × ödeme (çıkış barı hariç, motorla aynı) · fiyat = çıkış OLMAYAN barlarda poz × getiri · TP = kâr al (TP) ve
kademe (KAD) barlarında poz × getiri (TP seviyesine kadar + kademe sonrası kalan) · stop = SL / S24K / diğer çıkış barları · komisyon =
KOM × işlem gören ağırlık (yeniden dengeleme farkı + çıkış + kademe satışı; motorun eq kesintisinin yaklaşığı) · gerçekleşmiş =
funding (anında nakit) + KAPANAN bacakların fiyat P&L'i (KATKI defteri, kapanış günü) · gerçekleşmemiş = kalan (açık bacakların değişimi).
Hepsi dilim ortalaması (= kitap ağırlığı), getiri biriminde (özkaynak oranı), bileşik değil.
"""
import os, sys, subprocess, pickle
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m690"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "    for i in range(bas,len(C)-1):\n"; assert s.count(a) == 1
    s = s.replace(a, a + "        _poz0=poz.copy()\n", 1)
    a = """            for _k in np.flatnonzero(poz!=0):
                _e=_GK.setdefault((_gd,_k),[0.0,0.0,0.0,0])
                _e[0]+=_nz(poz[_k]*br[_k]); _e[1]+=float(_fu[_k]); _e[2]+=float(poz[_k]); _e[3]+=1
"""
    assert s.count(a) == 1
    s = s.replace(a, """            _ism=np.abs(poz-_poz0)+np.where(cik,np.abs(poz),0.0)+np.where(merd,np.abs(poz*mpay),0.0)+np.where(yaridan,0.5*np.abs(poz),0.0)
            for _k in np.flatnonzero((poz!=0)|(_poz0!=0)):
                _e=_GK.setdefault((_gd,_k),[0.0,0.0,0.0,0,0.0,0.0,0.0,0.0])
                _p=_nz(poz[_k]*br[_k])
                _e[0]+=_p; _e[1]+=float(_fu[_k]); _e[2]+=float(poz[_k]); _e[3]+=1
                _t=_tur[_k] or ('KAD' if merd[_k] else ('TP' if cik[_k] else ''))
                if _t in ('TP','KAD'): _e[4]+=_p
                elif _t: _e[5]+=_p
                if poz[_k]>0: _e[6]+=_p
                _e[7]+=float(_ism[_k])*KOM
""", 1)
    a = """        _df=pd.DataFrame([(d,C.columns[k],v[0]/NF,v[1]/NF,v[2]/max(v[3],1),v[3]/NF) for (d,k),v in _GK.items()],
                         columns=['gun','sembol','fiyat','funding','ort_poz','bar'])"""
    assert s.count(a) == 1
    s = s.replace(a, """        _df=pd.DataFrame([(d,C.columns[k],v[0]/NF,v[1]/NF,v[2]/max(v[3],1),v[3]/NF,v[4]/NF,v[5]/NF,v[6]/NF,v[7]/NF) for (d,k),v in _GK.items()],
                         columns=['gun','sembol','fiyat_top','funding','ort_poz','bar','tp','stop','fiyat_long_top','komisyon'])""", 1)
    open("/tmp/g33_m690.py", "w", encoding="utf-8").write(s)


def kos():
    kopya()
    for h in (0, 1):
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=f"{D}/E_{h}.pkl", GUNLUK_KATKI=f"{D}/gk_{h}.pkl", GK_BAS="2019-01-01",
                   KATKI="1", CIKIS_DEFTER=f"{D}/cikis_{h}.pkl")
        with open(f"{D}/E_{h}.txt", "w") as f:
            rc = subprocess.run([sys.executable, "/tmp/g33_m690.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode
        os.replace(f"/tmp/katki_{h}.pkl", f"{D}/katki_{h}.pkl")
        ayni = open(f"{D}/E_{h}.pkl", "rb").read() == open(f"/tmp/m622/M357_EK_P3T2_2000_{h}.pkl", "rb").read()
        print(f"hiza {h}: rc {rc} · E paritesi {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)


# ------------------------------------------------------------------------------------------------ analiz
def yukle():
    G = pd.concat([pd.read_pickle(f"{D}/gk_{h}.pkl").assign(h=h) for h in (0, 1)])
    G["fiyat"] = G.fiyat_top - G.tp - G.stop                  # çıkış olmayan barlar
    G["long_fiyat_top"] = G.fiyat_long_top
    num = ["fiyat_top", "funding", "tp", "stop", "fiyat", "komisyon", "fiyat_long_top"]
    G = G.groupby(["gun", "sembol"])[num + ["ort_poz"]].mean().reset_index()   # iki hiza ortalaması
    K = pd.concat([pd.read_pickle(f"{D}/katki_{h}.pkl").assign(h=h) for h in (0, 1)])
    E = sum(M.gunluk_yol(f"{D}/E_{h}.pkl") for h in (0, 1)) / 2 if hasattr(M, "gunluk_yol") else None
    return G, K


def gunluk_seri():
    M.CIKTI = D
    # M.gunluk "M357_EK_<ad>" adlı dosya bekler -> sembolik ad
    for h in (0, 1):
        hedef = f"{D}/M357_EK_M690_2000_{h}.pkl"
        if not os.path.exists(hedef): os.symlink(f"{D}/E_{h}.pkl", hedef)
    return sum(M.gunluk(f"M357_EK_M690_2000_{h}") for h in (0, 1)) / 2


def analiz():
    G, K = yukle(); RET = gunluk_seri(); RET.index = pd.to_datetime(RET.index)
    G["gun"] = pd.to_datetime(G.gun)
    G["long_fiyat"] = np.where(G.ort_poz > 0, G.fiyat, 0.0); G["short_fiyat"] = np.where(G.ort_poz < 0, G.fiyat, 0.0)
    G.to_csv(f"{D}/gun_coin_bilesen.csv", index=False)
    # ---- pozisyon (bacak) defteri: KATKI
    K["kapanis_gun"] = pd.to_datetime(K.get("t_kapanis", K.get("t"))).dt.normalize() if "t_kapanis" in K else pd.NaT
    K.to_csv(f"{D}/pozisyon_defteri.csv", index=False)
    # ---- günlük kitap bileşenleri
    B = G.groupby("gun")[["funding", "long_fiyat", "short_fiyat", "tp", "stop", "komisyon"]].sum()
    B["fiyat"] = B.long_fiyat + B.short_fiyat
    B["toplam_bilesen"] = B.funding + B.fiyat + B.tp + B.stop - B.komisyon
    B = B.join(RET.rename("gercek_getiri"), how="inner")
    B.to_csv(f"{D}/gun_kitap_bilesen.csv")
    kor = B.toplam_bilesen.corr(B.gercek_getiri); fark = (B.toplam_bilesen - B.gercek_getiri).abs().mean()
    print(f"[ÖLÇÜM] ayrıştırma doğrulaması: bileşen toplamı vs motorun günlük getirisi korelasyon {kor:.4f} · ort. mutlak fark {fark*1e4:.2f} bp/gün")
    # gerçekleşmiş / gerçekleşmemiş (KATKI: kapanan bacakların fiyat P&L'i kapanış gününe)
    print("\n[ÖLÇÜM] YILLIK BİLEŞENLER (getiri puanı, 1,0x, bileşik değil):")
    Y = B.groupby(B.index.year)[["funding", "long_fiyat", "short_fiyat", "tp", "stop", "komisyon", "gercek_getiri"]].sum() * 100
    print(Y.round(1).to_string())
    Y.to_csv(f"{D}/yil_bilesen.csv")
    # coin bazında
    Cn = G.groupby("sembol")[["funding", "fiyat", "tp", "stop", "komisyon"]].sum()
    Cn["net"] = Cn.funding + Cn.fiyat + Cn.tp + Cn.stop - Cn.komisyon
    Cn.sort_values("net").to_csv(f"{D}/coin_bilesen.csv")
    pay = Cn.net.sort_values(ascending=False); top = pay.clip(lower=0)
    print(f"\n[ÖLÇÜM] coin dağılımı: {len(Cn)} coin · net kârın %{pay.head(10).sum()/pay.sum()*100:.0f}'i ilk 10 coinden · "
          f"%{pay.head(30).sum()/pay.sum()*100:.0f}'i ilk 30 · zararlı coin {int((pay<0).sum())}")
    print("   en kârlı 5:", ", ".join(f"{s} {v*100:+.1f}" for s, v in pay.head(5).items()), "| en zararlı 5:",
          ", ".join(f"{s} {v*100:+.1f}" for s, v in pay.tail(5).items()))
    # gerçekleşmiş vs gerçekleşmemiş (pozisyon defterinden)
    if {"pnl", "fon", "fiy"}.issubset(K.columns):
        print(f"\n[ÖLÇÜM] pozisyon defteri: {len(K)} bacak (dilim düzeyi) · kapanış türleri {K.get('kapanis', pd.Series()).value_counts().to_dict()}")
        kz = K.groupby(K.get("kapanis", pd.Series("?", index=K.index)))[["fon", "fiy", "pnl"]].agg(["mean", "sum"])
        print(kz.round(5).to_string())

    # ---- 2) 30/60/90 günlük hareketli
    print("\n[ÖLÇÜM] HAREKETLİ PENCERELER (son değerler ve dağılım; yıllık puan):")
    for w in (30, 60, 90):
        Rw = B[["funding", "long_fiyat", "short_fiyat", "tp", "stop", "komisyon"]].rolling(w).sum() * (365 / w) * 100
        sh = B.gercek_getiri.rolling(w).mean() / B.gercek_getiri.rolling(w).std() * np.sqrt(365)
        eq = (1 + B.gercek_getiri).cumprod(); dd = eq.rolling(w).apply(lambda x: (x / np.maximum.accumulate(x) - 1).min(), raw=True) * 100
        Rw["sharpe"] = sh; Rw["maks_dd"] = dd
        Rw.to_csv(f"{D}/hareketli_{w}g.csv")
        q = Rw.quantile([0.05, 0.5, 0.95]).T
        print(f"  {w} g: " + " · ".join(f"{c} med {q.loc[c,0.5]:+.0f} [%5 {q.loc[c,0.05]:+.0f}, %95 {q.loc[c,0.95]:+.0f}]" for c in
                                       ["funding", "long_fiyat", "short_fiyat", "tp", "sharpe", "maks_dd"]))
        nz = {c: (Rw[c] < 0).mean() * 100 for c in ["funding", "long_fiyat", "short_fiyat", "tp"]}
        print(f"        negatif pencere oranı: " + " · ".join(f"{c} %{v:.0f}" for c, v in nz.items()))
    # işlem başına beklenen getiri (dilim bacakları)
    if "pnl" in K:
        K["kapanis_t"] = pd.to_datetime(K["t"]) + pd.to_timedelta(K["bar"] * 4, unit="h")
        kb = K.set_index("kapanis_t").sort_index().pnl
        for w in (30, 60, 90):
            m = kb.rolling(f"{w}D").mean() * 1e4
            print(f"  işlem başına beklenen getiri ({w} g, dilim bacağı, bp): medyan {m.median():.1f} · %5 {m.quantile(.05):.1f} · %95 {m.quantile(.95):.1f}")

    # ---- 3) rejimler
    print("\n[ÖLÇÜM] REJİMLER (çeyrek; getiri puanı):")
    Q = B.groupby(pd.PeriodIndex(B.index, freq="Q"))[["funding", "long_fiyat", "short_fiyat", "tp", "stop", "komisyon", "gercek_getiri"]].sum() * 100
    Q.to_csv(f"{D}/ceyrek_bilesen.csv")
    print(Q[(Q.index.year >= 2021) & (Q.index.year <= 2024)].round(1).to_string())

    # ---- 4) erken uyarı
    print("\n[ÖLÇÜM] ERKEN UYARI (ön tanımlı, optimize EDİLMEDİ): kötü dönem = sonraki 30 gün kitap getirisi < 0")
    ileri = B.gercek_getiri[::-1].rolling(30).sum()[::-1].shift(-1)
    kotu = (ileri < 0); taban = kotu.mean()
    gosterge = {
        "FUNDING 30 g ≤ 0 (mevcut kapının F kuralı)": B.funding.rolling(30).sum() <= 0,
        "FUNDING 60 g ≤ 0": B.funding.rolling(60).sum() <= 0,
        "FİYAT (long+short) 60 g < 0": B.fiyat.rolling(60).sum() < 0,
        "LONG fiyat 60 g < 0": B.long_fiyat.rolling(60).sum() < 0,
        "SHORT fiyat 60 g < 0": B.short_fiyat.rolling(60).sum() < 0,
        "TP 60 g < medyanının yarısı (genişleyen)": B.tp.rolling(60).sum() < 0.5 * B.tp.rolling(60).sum().expanding(180).median(),
        "TOPLAM getiri 60 g < 0": B.gercek_getiri.rolling(60).sum() < 0,
        "İKİ bileşen birden (fiyat 60 g < 0 VE funding 30 g altta yarıda)": (B.fiyat.rolling(60).sum() < 0) &
            (B.funding.rolling(30).sum() < 0.5 * B.funding.rolling(30).sum().expanding(180).median()),
    }
    satir = []
    gecerli = ileri.notna()
    for ad, a in gosterge.items():
        a = a.fillna(False) & gecerli
        n = int(a.sum())
        isabet = kotu[a].mean() if n else np.nan
        yakalama = a[kotu & gecerli].mean()
        yanlis = 1 - isabet if n else np.nan
        kacan = (ileri[a]).mean() * 100 if n else np.nan          # alarm günlerinde sonraki 30 günün ortalama getirisi (kapı kapansa kaçacak)
        kac_top = ileri[a & ~kotu].sum() / 30 * 100 if n else 0    # iyi dönemleri kapatma maliyeti (yaklaşık, puan)
        # öncü süre: her kötü bölümün başlangıcından önceki 30 günde ilk alarm kaç gün önce
        bas = kotu & ~kotu.shift(1, fill_value=False)
        once = []
        for t in kotu.index[bas]:
            pen = a[(a.index < t) & (a.index >= t - pd.Timedelta(days=30))]
            if pen.any(): once.append((t - pen[pen].index[0]).days)
        satir.append((ad, n, a.mean() * 100, isabet * 100, (isabet / taban) if n else np.nan, yakalama * 100, yanlis * 100,
                      kacan, kac_top, np.median(once) if once else np.nan, len(once), int(bas.sum())))
    T = pd.DataFrame(satir, columns=["gösterge", "alarm_gün", "alarm_%", "isabet_%", "kaldıraç(lift)", "yakalama_%", "yanlış_alarm_%",
                                     "alarm_sonrası_30g_getiri_%", "iyi_dönem_kaybı_puan", "öncü_gün_medyan", "önceden_yakalanan_bölüm", "kötü_bölüm"])
    T.to_csv(f"{D}/erken_uyari.csv", index=False)
    print(f"  taban oran (herhangi bir günde sonraki 30 gün zararlı): %{taban*100:.1f}")
    print(T.round(1).to_string(index=False))


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
