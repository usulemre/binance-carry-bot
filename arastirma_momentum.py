#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 263 — MOMENTUM (SÜREKLİLİK): "+%100 yükselene gir" kitabı.

Kullanıcının fikri: *"+100 yükseldi bir coin geçen girdim kazandım."*

NEDEN BU AYRI BİR ÖLÇÜM
-----------------------
Madde 241'de kullanıcının kendi yöntemi ölçülmüştü ama o TERS işaretliydi:
"+%40 yükselene SHORT, −%40 düşene LONG" (ortalama dönüş). Bu fikir
süreklilik: yükselene LONG. Aynı eksende zıt iki hipotez, ikisi birden
doğru olamaz — ve ikisi birden yanlış OLABİLİR (uç hareket hiçbir yöne
bilgi taşımıyorsa).

Eski kitapta (carry'den önce) `trend_momentum` ve `breakout` ölçülmüş ve
ağır kaybetmişti (−1047R / −388R, 2020-2022). AMA o motor 15 dakikalık
bar + ATR stop kullanıyordu ve stop'un kendisi momentum stratejilerini
öldüren şeydi. Bu modül STOP KULLANMIYOR: sadece "gir, H bar tut, çık".
Böylece ölçülen şey stratejinin ham işareti.

ÖN KAYIT (sonuçlara bakmadan sabitlendi)
----------------------------------------
* Evren: 4 saatlik seri, listelenme yaşı >= 90 bar*6, 24sa ciro medyanı
  >= HACIM_ESIK (varsayılan 20M$; 100M$ de ölçülüyor).
* İki kurgu:
  (A) EŞİK: geriye bakış penceresinde getiri >= ESIK ise gir (kullanıcının
      tarifi: +%100), eşit ağırlık, H bar tut.
  (B) KESİTSEL: pencere getirisine göre sırala, en üst K sembolü al
      (klasik momentum), eşit ağırlık, H bar tut.
* Her kurgu LONG ve SHORT olarak ayrı ayrı ölçülür. Bu PLASEBO'dur:
  süreklilik gerçekse long kazanır VE short kaybeder. İkisi de sıfıra
  yakınsa işaret yok.
* Maliyet: taraf başına 2,072bp (madde 213'ün harmanlanmış ölçümü).
* Karar: madde 200 — ikinci kitap ana kitapla korelasyonu <0,1 ise
  düşük Sharpe tolere edilir; ama kendi başına Sharpe > 0 ve getiri > 0
  olmak ZORUNDA. Sonra madde 218'in gerçek eşit-risk harmanı.

KULLANIM
    python arastirma_momentum.py                 # tam cephe
    python arastirma_momentum.py --hizli         # tek yapılandırma
"""
from __future__ import annotations

import csv
import glob
import os
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KOK, "data_genis")
ONBELLEK = "/tmp/m263_panel.pkl"

KOMISYON_BP = 2.072          # madde 213: harmanlanmış gerçek oran, taraf başına
BAR_SAAT = 4
YIL_BAR = 365 * 24 // BAR_SAAT
MIN_BAR = 90 * 24 // BAR_SAAT   # 90 gün listelenme yaşı (madde 133)


def panel(hacim_esik_usd: float = 20e6):
    """close ve uygunluk matrisleri. İlk çağrıda diske önbelleklenir."""
    if os.path.exists(ONBELLEK):
        kapanis, ciro = pd.read_pickle(ONBELLEK)
    else:
        kap, cir = {}, {}
        for f in sorted(glob.glob(os.path.join(VERI, "*_4h.csv"))):
            s = os.path.basename(f).replace("_4h.csv", "")
            try:
                d = pd.read_csv(f, usecols=["date", "close", "quote_volume"])
            except Exception:
                continue
            if len(d) < MIN_BAR + 50:
                continue
            d["date"] = pd.to_datetime(d["date"])
            d = d.drop_duplicates("date").set_index("date").sort_index()
            kap[s] = d["close"].astype(float)
            cir[s] = d["quote_volume"].astype(float)
        kapanis = pd.DataFrame(kap).sort_index()
        ciro = pd.DataFrame(cir).reindex_like(kapanis)
        pd.to_pickle((kapanis, ciro), ONBELLEK)
    # 24 saatlik ciro (6 bar) medyanı, 30 günlük pencere
    ciro24 = ciro.rolling(6, min_periods=6).sum()
    uygun = (ciro24.rolling(180, min_periods=60).median() >= hacim_esik_usd)
    # listelenme yaşı: ilk gözlemden MIN_BAR sonra uygun
    yas = kapanis.notna().cumsum() >= MIN_BAR
    return kapanis, (uygun & yas & kapanis.notna())


def _getiri_serisi(kapanis: pd.DataFrame, uygun: pd.DataFrame,
                   bakis: int, tut: int, yon: int,
                   esik: float | None = None, k: int | None = None):
    """Bar bazında portföy getirisi döndürür (maliyet dahil).

    yon=+1 long, -1 short. esik verilirse (A) kurgusu, k verilirse (B).
    Pozisyonlar `tut` bar boyunca tutulur; her bar yeni bir DİLİM açılır
    (ana kitabın 15 dilimli yapısının momentum karşılığı: her bar
    sermayenin 1/tut'u yenilenir) -> hiçbir bar özel değil, zamanlama
    şansı ortalanır.
    """
    px = kapanis.values
    uy = uygun.values
    n, m = px.shape
    gec = np.zeros(n)                 # portföy bar getirisi
    maliyet_bar = np.zeros(n)
    # bar getirileri
    r = np.full((n, m), np.nan)
    r[1:] = px[1:] / px[:-1] - 1.0
    # geriye bakış getirisi
    gb = np.full((n, m), np.nan)
    gb[bakis:] = px[bakis:] / px[:-bakis] - 1.0

    # her dilim: t anında seçilen sepet, t+1..t+tut arası tutulur
    agirlik = np.zeros((n, m))
    for t in range(bakis, n - 1):
        sinyal = np.where(uy[t], gb[t], np.nan)
        if not np.isfinite(sinyal).any():
            continue
        if esik is not None:
            sec = np.where(np.isfinite(sinyal) & (sinyal >= esik))[0]
        else:
            sira = np.argsort(-sinyal)          # büyükten küçüğe, nan sonda
            gecerli = [i for i in sira if np.isfinite(sinyal[i])]
            sec = np.array(gecerli[:k], dtype=int)
        if len(sec) == 0:
            continue
        pay = (1.0 / tut) / len(sec)            # dilim sermayesi eşit bölünür
        son = min(t + tut, n - 1)
        agirlik[t + 1:son + 1, sec] += pay
        # giriş + çıkış maliyeti
        maliyet_bar[t + 1] += pay * len(sec) * KOMISYON_BP / 1e4
        maliyet_bar[son] += pay * len(sec) * KOMISYON_BP / 1e4

    rr = np.where(np.isfinite(r), r, 0.0)
    gec = yon * (agirlik * rr).sum(axis=1) - maliyet_bar
    brut = np.abs(agirlik).sum(axis=1)
    return pd.Series(gec, index=kapanis.index), brut


def ozet(g: pd.Series) -> dict:
    g = g.fillna(0.0).values
    if g.std(ddof=1) == 0:
        return {"getiri": 0.0, "sharpe": 0.0, "dusus": 0.0, "bar": len(g)}
    yil = len(g) / YIL_BAR
    tam = float(np.prod(1.0 + g))
    e = np.cumprod(1.0 + g)
    return {
        "getiri": (tam ** (1.0 / yil) - 1.0) * 100.0 if tam > 0 else -100.0,
        "sharpe": float(g.mean() / g.std(ddof=1) * np.sqrt(YIL_BAR)),
        "dusus": float((e / np.maximum.accumulate(e) - 1.0).min()) * 100.0,
        "bar": len(g),
    }


def gunluk(g: pd.Series) -> pd.Series:
    """4 saatlik seriyi günlüğe bileşikler (ana kitapla kıyas için)."""
    return (1.0 + g.fillna(0.0)).groupby(g.index.date).prod() - 1.0


def ana_kitap() -> pd.Series:
    yol = os.path.join(KOK, "referans_getiri.csv")
    with open(yol) as f:
        d = list(csv.DictReader(f))
    return pd.Series([float(r["getiri"]) for r in d],
                     index=pd.to_datetime([r["tarih"] for r in d]).date)


def korelasyon(g4h: pd.Series) -> float:
    a = ana_kitap()
    b = gunluk(g4h)
    ort = a.index.intersection(b.index)
    if len(ort) < 100:
        return float("nan")
    return float(np.corrcoef(a.loc[ort].values, b.loc[ort].values)[0, 1])


def cephe(hacim_esik: float = 20e6, hizli: bool = False) -> list:
    kapanis, uygun = panel(hacim_esik)
    print("evren: %d sembol, %d bar (%s -> %s)"
          % (kapanis.shape[1], kapanis.shape[0],
             kapanis.index[0].date(), kapanis.index[-1].date()))
    print("uygun sembol medyanı: %.1f" % uygun.sum(axis=1).median())
    out = []
    if hizli:
        kurgular = [("ESIK", 1.00, 180, 30)]
    else:
        kurgular = []
        # (A) kullanıcının tarifi: eşik bazlı
        for esik in (0.50, 1.00, 2.00):
            for bakis_gun in (7, 15, 30):
                for tut_gun in (3, 7, 15):
                    kurgular.append(("ESIK", esik, bakis_gun * 6, tut_gun * 6))
        # (B) klasik kesitsel momentum
        for k in (5, 10):
            for bakis_gun in (7, 15, 30, 90):
                for tut_gun in (5, 15):
                    kurgular.append(("KESIT", k, bakis_gun * 6, tut_gun * 6))
    for tip, par, bakis, tut in kurgular:
        satir = {"tip": tip, "par": par, "bakis_gun": bakis // 6,
                 "tut_gun": tut // 6}
        for yon, ad in ((+1, "long"), (-1, "short")):
            g, brut = _getiri_serisi(
                kapanis, uygun, bakis, tut, yon,
                esik=par if tip == "ESIK" else None,
                k=int(par) if tip == "KESIT" else None)
            o = ozet(g)
            satir[ad] = o
            if yon == +1:
                satir["brut_ort"] = float(np.mean(brut))
                satir["kor"] = korelasyon(g)
        out.append(satir)
        print("%-5s par=%-5s bakış %2dg tut %2dg | LONG %+8.1f%% Sh %+6.2f dd %+6.1f"
              " | SHORT %+8.1f%% Sh %+6.2f | brüt %.2f kor %+.3f"
              % (tip, par, satir["bakis_gun"], satir["tut_gun"],
                 satir["long"]["getiri"], satir["long"]["sharpe"],
                 satir["long"]["dusus"], satir["short"]["getiri"],
                 satir["short"]["sharpe"], satir["brut_ort"], satir["kor"]))
    return out


if __name__ == "__main__":
    hizli = "--hizli" in sys.argv
    he = 100e6 if "--hacim100" in sys.argv else 20e6
    cephe(he, hizli)


# ===========================================================================
# ÖLÇÜM SONUÇLARI (madde 263) — makine okunur
# ===========================================================================
# Cephe: 43 yapılandırma (27 eşik + 16 kesitsel), 712 sembol, 10.224 adet
# 4 saatlik bar (2022-01-01 -> 2026-08-31), uygun sembol medyanı 98.
# LONG tarafı 43/43 KAYBETTİ. En iyi long: −%7,8 (eşik +%200, bakış 15g,
# tut 15g) ve o bile brüt 0,12 ile neredeyse hiç işlem yapmıyor.
CEPHE_LONG_KAYBEDEN = 43
CEPHE_TOPLAM = 43
EN_IYI_LONG_YILLIK = -7.8          # %  (hiçbiri pozitif değil)
EN_KOTU_LONG_YILLIK = -77.4        # %
LONG_DUSUS_ARALIGI = (-54.6, -100.0)   # % maks düşüş

# Kullanıcının tarif ettiği yapılandırma (+%100 yükselene gir):
KULLANICI_KURGUSU = {
    "esik": 1.00, "bakis_gun": 30, "tut_gun": 5,
    "long_yillik": -61.6, "long_sharpe": 0.04, "long_dusus": -99.4,
    "short_yillik": -67.2, "short_sharpe": -0.07,
}

# TEŞHİS — portföy mekaniğinden ve maliyetten ARINDIRILMIŞ ham işaret.
# Bakış 30 gün. (ileri_gun, esik) -> ölçümler
HAM_ISARET = {
    (5, 1.00): {"n": 29917, "aritmetik": -0.22, "geometrik": -3.95,
                "medyan": -4.53, "kazanma": 39.1, "p95": 44.0, "p": 0.044},
    (15, 1.00): {"n": 29665, "aritmetik": -3.11, "geometrik": -11.52,
                 "medyan": -11.31, "kazanma": 31.8, "p95": 71.2, "p": 0.000},
    (5, 2.00): {"n": 7926, "aritmetik": +2.25, "geometrik": -5.11,
                "medyan": -5.29, "kazanma": 39.9, "p95": 69.7, "p": 0.000},
    (15, 2.00): {"n": 7848, "aritmetik": -0.90, "geometrik": -15.89,
                 "medyan": -13.12, "kazanma": 32.0, "p95": 104.2, "p": 0.255},
}
# Aynı ölçüler EVREN için (kıyas tabanı)
EVREN = {
    5: {"aritmetik": -0.57, "geometrik": -1.51, "medyan": -1.15, "kazanma": 44.5},
    15: {"aritmetik": -1.80, "geometrik": -4.36, "medyan": -3.95, "kazanma": 39.9},
}


def kullanicinin_deneyimi_aciklanabilir_mi() -> bool:
    """"Geçen girdim kazandım" ile "bu kitap para kaybeder" çelişir mi?

    Hayır. Kazanma oranı %39 -> on girişten dördü kazanır; üst %5 dilim
    +%44 getiriyor, yani KAZANAN giriş akılda kalır. Aritmetik ortalama
    bile bir hücrede POZİTİF (+%2,25, p<0,001). Çelişki yok: tek bir
    kazanan giriş, negatif geometrik ortalamayı çürütmez.
    """
    return (HAM_ISARET[(5, 1.00)]["kazanma"] > 30.0
            and HAM_ISARET[(5, 2.00)]["aritmetik"] > 0
            and HAM_ISARET[(5, 2.00)]["geometrik"] < 0)


def aritmetik_pozitif_ama_geometrik_negatif() -> list:
    """Madde 263'ün yasası: pozitif ortalama kazanılabilir kenar DEĞİL."""
    return [k for k, v in HAM_ISARET.items()
            if v["aritmetik"] > 0 > v["geometrik"]]


def pompa_evrenden_kotu_mu() -> bool:
    """Pompalanmış coin, rastgele coinden DAHA MI kötü? (medyan ve kazanma)"""
    return all(HAM_ISARET[(h, e)]["medyan"] < EVREN[h]["medyan"]
               and HAM_ISARET[(h, e)]["kazanma"] < EVREN[h]["kazanma"]
               for h in (5, 15) for e in (1.00, 2.00))


def kitap_bunu_zaten_kullaniyor_mu() -> str:
    """Bulgu kitapta nasıl para ediyor? TERS işaretle, ELEME olarak."""
    return ("madde 196 UCELE: son 24 saatte +%40 pompalanmış coin LONG "
            "adayı olamaz. Madde 236 taraması 0,40'ın argmax olduğunu "
            "doğruladı (kapalı +%116,2/3,017 · 0,40 +%112,6/3,128 — "
            "eşit riskte 0,40 en iyi). Yani bulgu GİRİŞ kuralı olarak "
            "para kaybettirirken ELEME kuralı olarak zaten kullanılıyor.")


def hukum() -> str:
    return "RED"
