#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 270 — KULLANICININ İKİNCİ BOTU: tam onun kurallarıyla ölçüm.

Kullanıcı canlı çalışan ikinci botunu tarif etti:
  * günlük harekete bakar; **en çok yükseleni SHORT**, en çok düşeni LONG
  * yalnızca **±%30'u aşanlarda** işlem açar
  * **2.000$'ın %25'ini tek coine** yatırır
  * coin başına **−%25 STOP**
  * bazı günler yalnızca 2 short açıyor
  * "günde +%50 yükseldiği bile oluyor"

NEDEN YENİ BİR ÖLÇÜM (madde 197/241 yetmiyor)
---------------------------------------------
Madde 241 bu desenin ÇEKİRDEĞİNİ ölçmüştü ve en önemli sayıyı buldu:
**pump → SHORT %68,6 kazanıyor, medyan +%12,07, AMA ortalama +%4,06 ve
en kötü tek işlem −%743.** Kazananlar küçük, kaybedenler sınırsız; madde
202'nin yasası: *"kazanma oranı ile beklenti apayrı şeyler."*

Ama madde 241'in kurgusu kullanıcının botu DEĞİLDİ: ±%40 eşik, 3 gün
tutma, **stop YOK**, pozisyon başına sabit %20. Kullanıcının botunda
±%30, **1 gün** tutma, **%25** boyut ve **−%25 stop** var. Stop, madde
241'in −%743'lük kuyruğuna karşı duran tek şey — ve kriptoda bir stop'un
BOŞLUKLA aşılması olağan. Bu yüzden yeniden ölçüldü.

ÖN KAYIT (sonuçlara bakmadan)
-----------------------------
* Veri: `data_genis/` 4 saatlik, 847 sembol, 2022-01 → 2026-08.
* Gün = 6 bar. Günlük hareket = kapanış/6 bar önceki kapanış − 1.
* Giriş: günün son barının kapanışında, hareket >= +%30 ise SHORT,
  <= −%30 ise LONG. Aynı gün birden fazla aday varsa **harekete göre en
  uçtakiler** alınır (kullanıcı "en çok yükseleni" diyor), en fazla
  `AZAMI_POZ`.
* Stop: girişten **%25 aleyhte**. Her sonraki barda kontrol edilir ve
  **boşluk modellenir**: bar AÇILIŞI stop'un ötesindeyse dolum
  AÇILIŞTAN olur (gerçekte olan budur), değilse stop fiyatından.
* Çıkış: stop gelmediyse **1 gün sonra** (6 bar) kapanışta.
* Maliyet: taraf başına 5bp taker (giriş ve çıkış) — kullanıcının botu
  piyasa emri kullanıyor olmalı, çünkü uç hareketi kovalıyor.
* Boyut: öz kaynağın %25'i, **kaldıraçsız** (notional = 0,25 × bakiye).
  Kaldıraç ayrıca ölçülüyor (aşağıya bakın).

ÖLÇÜM 1 — İŞLEM BAZINDA (kaldıraçsız, pozisyon getirisi cinsinden)
-----------------------------------------------------------------
Sonuçlar modül içindeki `ISLEM` sözlüğünde. Özet: stop çalışıyor ama
BEDAVA DEĞİL — kazanma oranını düşürüyor ve boşlukla aşılıyor.

ÖLÇÜM 2 — HESAP YOLU (%25 boyut, bileşik)
-----------------------------------------
`HESAP` sözlüğü: yıllık getiri, maksimum düşüş, ve **iflas olasılığı**.

ÖLÇÜM 3 — "GÜNDE +%50" NE DEMEK
-------------------------------
2 pozisyon × %25 = öz kaynağın %50'si sahada. Kaldıraçsız bir günde
+%50 hesap kazancı için coinlerin **+%100** hareket etmesi gerekir —
yani kaldıraçsız mümkün değil. Kaldıraç L ile: coin hareketi × 0,50 × L
= 0,50 → **L = 1 / coin hareketi**. Coinler lehine %10 oynadıysa
**L ≈ 10x**. Bu, aynı dağılımın ters ucunda **tek günde −%50** demektir
ve −%25 stop ile bile boşluk riski kaldıraçla ÇARPILIR.

KULLANIM
    python arastirma_kullanici_botu.py            # tam ölçüm (yavaş)
    python arastirma_kullanici_botu.py --ozet      # kayıtlı sonuçlar
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KOK, "data_genis")

BAR_GUN = 6
ESIK = 0.30
STOP = 0.25
BOYUT = 0.25
TUTMA_BAR = BAR_GUN
TAKER_BP = 5.0
AZAMI_POZ = 2
BAKIYE = 2000.0
HACIM_TABAN = 5e6          # 24sa ciro tabanı; uç hareket küçük coinlerde olur


def panel():
    kap, yuk, dus, cir, aci = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(VERI, "*_4h.csv"))):
        s = os.path.basename(f).replace("_4h.csv", "")
        try:
            d = pd.read_csv(f, usecols=["date", "open", "high", "low",
                                        "close", "quote_volume"])
        except Exception:
            continue
        if len(d) < 200:
            continue
        d["date"] = pd.to_datetime(d["date"])
        d = d.drop_duplicates("date").set_index("date").sort_index()
        kap[s] = d["close"].astype(float)
        aci[s] = d["open"].astype(float)
        yuk[s] = d["high"].astype(float)
        dus[s] = d["low"].astype(float)
        cir[s] = d["quote_volume"].astype(float)
    C = pd.DataFrame(kap).sort_index()
    return (C, pd.DataFrame(yuk).reindex_like(C),
            pd.DataFrame(dus).reindex_like(C),
            pd.DataFrame(cir).reindex_like(C),
            pd.DataFrame(aci).reindex_like(C))     # GERÇEK açılış (boşluk için)


def olc(azami: int = AZAMI_POZ, esik: float = ESIK, stop: float = STOP,
        tutma: int = TUTMA_BAR, hacim_taban: float = HACIM_TABAN,
        acilis: pd.DataFrame | None = None):
    C, H, L, V, O_ = panel()
    O = O_ if acilis is None else acilis   # GERÇEK açılış: boşluk modellenir
    cv, hv, lv, ov = C.values, H.values, L.values, O.values
    c24 = V.rolling(BAR_GUN, min_periods=BAR_GUN).sum().values
    n, m = cv.shape
    hareket = np.full((n, m), np.nan)
    hareket[BAR_GUN:] = cv[BAR_GUN:] / cv[:-BAR_GUN] - 1.0
    islem = []
    # MADDE 270 DUZELTME: kullanicinin botu GUNDE BIR bakar; her 4 saatlik
    # barda islem acmak gun basina 12 pozisyona kadar cikariyordu ve hesap
    # yolu anlamsizlasiyordu (dusus < -%100 gibi imkansiz degerler).
    for i in range(BAR_GUN, n - tutma - 1, BAR_GUN):
        uy = np.isfinite(hareket[i]) & np.isfinite(c24[i]) & (c24[i] >= hacim_taban)
        if not uy.any():
            continue
        h = np.where(uy, hareket[i], np.nan)
        tum_aday = []
        for yon, maske in ((-1, h >= esik), (+1, h <= -esik)):
            for k in np.flatnonzero(maske & uy):
                tum_aday.append((abs(h[k]), yon, int(k)))
        # MADDE 270: sinir TOPLAM pozisyon sayisi (kullanici "gunde 2" dedi),
        # taraf basina DEGIL. En uctaki hareketler secilir.
        tum_aday.sort(reverse=True)
        for _h, yon, k in tum_aday[:azami]:
            if True:
                giris = cv[i, k]
                if not np.isfinite(giris) or giris <= 0:
                    continue
                stop_f = giris * (1 + stop) if yon < 0 else giris * (1 - stop)
                cikis, nasil = None, "sure"
                for j in range(i + 1, min(i + 1 + tutma, n)):
                    acik = ov[j, k]
                    if yon < 0:
                        if np.isfinite(acik) and acik >= stop_f:
                            cikis, nasil = acik, "bosluk"; break
                        if np.isfinite(hv[j, k]) and hv[j, k] >= stop_f:
                            cikis, nasil = stop_f, "stop"; break
                    else:
                        if np.isfinite(acik) and acik <= stop_f:
                            cikis, nasil = acik, "bosluk"; break
                        if np.isfinite(lv[j, k]) and lv[j, k] <= stop_f:
                            cikis, nasil = stop_f, "stop"; break
                if cikis is None:
                    cikis = cv[min(i + tutma, n - 1), k]
                if not np.isfinite(cikis) or cikis <= 0:
                    continue
                ham = yon * (cikis / giris - 1.0)
                net = ham - 2 * TAKER_BP / 1e4
                islem.append({"i": i, "sembol": k, "yon": yon, "hareket": h[k],
                              "getiri": net, "nasil": nasil,
                              "tarih": C.index[i]})
    return pd.DataFrame(islem), C.index


def hesap_yolu(isl: pd.DataFrame, idx, boyut: float = BOYUT,
               bakiye: float = BAKIYE, kaldirac: float = 1.0):
    """Günlük olarak: o gün açılan işlemlerin ağırlıklı katkısı."""
    if isl.empty:
        return pd.Series(dtype=float), {}
    gun = isl.groupby("i")["getiri"].sum() * boyut * kaldirac
    e = pd.Series(1.0, index=range(len(idx)))
    seri = pd.Series(0.0, index=range(len(idx)))
    seri.loc[gun.index] = gun.values
    oz = (1.0 + seri).cumprod()
    dd = (oz / oz.cummax() - 1.0)
    yil = len(idx) / (365.25 * BAR_GUN)
    son = float(oz.iloc[-1])
    return oz, {
        "yillik_pct": (son ** (1 / yil) - 1) * 100 if son > 0 else -100.0,
        "toplam_pct": (son - 1) * 100,
        "maks_dusus_pct": float(dd.min()) * 100,
        "iflas_yarim": bool((oz <= 0.5).any()),
        "iflas_onda": bool((oz <= 0.1).any()),
        "son_bakiye": son * bakiye,
    }


# ===========================================================================
# ÖLÇÜLEN SONUÇLAR (bu modül koşularak üretildi) — `--ozet` bunları yazar
# ===========================================================================
# Kullanicinin TAM yapilandirmasi: ±%30, 1 gun, −%25 stop, en fazla 2 poz,
# poz basina %25, gunde BIR bakis, 5bp taker, 5M$ ciro tabani.
ISLEM = {
    "n": 1483, "short": 1222, "long": 261,
    "ortalama_pct": 0.19, "medyan_pct": 1.16,
    "short_kazanma_pct": 54.7, "short_medyan_pct": 2.37,
    "stop_ile_kapanan_pct": 27.9, "bosluk_pct": 0.0,
}
HESAP = {
    "boyut25_yillik_pct": -22.88, "boyut25_dusus_pct": -92.4,
    "boyut25_son_usd": 595,
    "stop_yok_yillik_pct": -74.04, "stop_yok_iflas": True,
    "tutma3g_yillik_pct": -66.35,
    "tek_poz_yillik_pct": -8.21,
}
# BOYUT CEPHESI: ayni islem kumesi, yalnizca pozisyon boyutu degisiyor
BOYUT_CEPHESI_30 = {   # esik ±%30, islem ORT +0,19%
    0.250: (-22.88, -92.4, 595), 0.200: (-13.29, -85.7, 1028),
    0.150: (-5.61, -74.7, 1528), 0.125: (-2.72, -67.0, 1759),
    0.100: (-0.55, -57.7, 1949), 0.075: (+0.84, -46.8, 2079),
    0.050: (+1.40, -34.1, 2134), 0.025: (+1.12, -18.6, 2107),
}
BOYUT_CEPHESI_40 = {   # esik ±%40, islem ORT +0,53%
    0.250: (-4.05, -76.1, 1649), 0.200: (+1.66, -65.7, 2160),
    0.150: (+5.10, -52.6, 2523), 0.125: (+5.89, -45.1, 2612),
    0.100: (+6.01, -36.9, 2626), 0.075: (+5.48, -28.2, 2565),
    0.050: (+4.29, -19.1, 2433), 0.025: (+2.45, -9.6, 2239),
}
BOSLUK_OLCUMU = {      # 4 saatlik barda acilis/onceki kapanis
    "p99_9_pct": 0.40, "mutlak_25_ustu_bar_pct": 0.0001,
    "yorum": "kripto 7/24 isledigi icin 4sa barlarda bosluk YOK; stop'un "
             "boslukla asilmasi korkusu bu veride gerceklesmiyor. Bar ICINDE "
             "kayma olcelemedi -> stop'un tam -%25'ten dolmasi IYIMSER.",
}
BENIM_UC_HATAM = (
    "acilis fiyati yerine onceki kapanisi kullandim -> bosluk hic "
    "modellenmedi ('bosluk %0,0' oradan geliyordu)",
    "pozisyon sinirini TARAF BASINA uyguladim, kullanici 'gunde 2' demisti",
    "her 4 SAATLIK BARDA islem actirdim, oysa bot GUNDE BIR bakiyor -> gun "
    "basina 12 pozisyona cikti ve hesap yolu imkansiz degerler verdi "
    "(dusus -%103,7, -%118,1)",
)
KALDIRAC_IMA: dict = {
    "iki_poz_saha_pct": 50.0,
    "gunde_50_icin_coin_hareketi_kaldiracsiz_pct": 100.0,
    "coin_10_hareket_icin_kaldirac": 10.0,
    "ters_ucta": "aynı kaldıraçla tek günde −%50",
}
MADDE_241 = {"pump_short_kazanma": 68.6, "pump_short_medyan": 12.07,
             "pump_short_ortalama": 4.06, "en_kotu_tek_islem": -743.0,
             "dump_long_medyan": -10.33, "dump_long_kazanma": 35.2,
             "esik30_pump_gun": 1.30, "esik30_dump_gun": 0.37,
             "dumpsiz_gun_pct": 78.0}


def yaz() -> None:
    print("MADDE 270 — KULLANICININ İKİNCİ BOTU\n")
    print("kurallar: ±%%%.0f eşik · %%%.0f boyut · −%%%.0f stop · 1 gün tutma"
          " · en fazla %d pozisyon" % (ESIK * 100, BOYUT * 100, STOP * 100,
                                       AZAMI_POZ))
    print("\nMADDE 241'in çekirdek ölçümü (stop YOK, ±%40, 3 gün):")
    print("  pump → SHORT: kazanma %%%.1f · medyan +%%%.2f · ORTALAMA +%%%.2f"
          % (MADDE_241["pump_short_kazanma"], MADDE_241["pump_short_medyan"],
             MADDE_241["pump_short_ortalama"]))
    print("  en kötü tek işlem: %%%.0f" % MADDE_241["en_kotu_tek_islem"])
    print("  dump → LONG: medyan %%%.2f · kazanma %%%.1f"
          % (MADDE_241["dump_long_medyan"], MADDE_241["dump_long_kazanma"]))
    print("  arz: ±%%30'da günde %.2f pump / %.2f dump · dumpsız gün %%%.0f"
          % (MADDE_241["esik30_pump_gun"], MADDE_241["esik30_dump_gun"],
             MADDE_241["dumpsiz_gun_pct"]))
    if ISLEM:
        print("\nBU TURUN ÖLÇÜMÜ (stop VAR, boşluk modellendi):")
        for k, v in ISLEM.items():
            print("  %-22s %s" % (k, v))
    if HESAP:
        print("\nHESAP YOLU (%%%.0f boyut, bileşik):" % (BOYUT * 100))
        for k, v in HESAP.items():
            print("  %-22s %s" % (k, v))
    print("\n\"GÜNDE +%50\" ARİTMETİĞİ:")
    print("  2 pozisyon × %%25 = öz kaynağın %%%.0f'i sahada"
          % KALDIRAC_IMA["iki_poz_saha_pct"])
    print("  kaldıraçsız +%%50 için coinlerin +%%%.0f hareket etmesi gerekir"
          % KALDIRAC_IMA["gunde_50_icin_coin_hareketi_kaldiracsiz_pct"])
    print("  coinler %%10 oynadıysa ima edilen kaldıraç ≈ %.0fx"
          % KALDIRAC_IMA["coin_10_hareket_icin_kaldirac"])
    print("  ve aynı kaldıraçla: %s" % KALDIRAC_IMA["ters_ucta"])


if __name__ == "__main__":
    if "--ozet" in sys.argv:
        yaz()
    else:
        isl, idx = olc()
        print("işlem sayısı: %d" % len(isl))
        if not isl.empty:
            for yon, ad in ((-1, "pump→SHORT"), (+1, "dump→LONG")):
                x = isl[isl.yon == yon]
                if x.empty:
                    continue
                print("%s n=%d kazanma %.1f%% medyan %+.2f%% ortalama %+.2f%% "
                      "en kötü %+.1f%% stop %.1f%% boşluk %.1f%%"
                      % (ad, len(x), (x.getiri > 0).mean() * 100,
                         x.getiri.median() * 100, x.getiri.mean() * 100,
                         x.getiri.min() * 100,
                         (x.nasil == "stop").mean() * 100,
                         (x.nasil == "bosluk").mean() * 100))
            oz, h = hesap_yolu(isl, idx)
            print("HESAP:", {k: (round(v, 2) if isinstance(v, float) else v)
                             for k, v in h.items()})


def en_iyi_boyut(cephe: dict) -> tuple:
    """Hesap getirisini maksimize eden pozisyon boyutu."""
    b = max(cephe, key=lambda k: cephe[k][0])
    return b, cephe[b]


def boyut_kac_kat_buyuk(esik: float = 0.30) -> float:
    """Kullanıcının %25'i, optimumun kaç katı?"""
    c = BOYUT_CEPHESI_30 if esik < 0.35 else BOYUT_CEPHESI_40
    return BOYUT / en_iyi_boyut(c)[0]


def sinyal_pozitif_mi() -> bool:
    """İşlem başına beklenti pozitif mi? (sinyal var mı)"""
    return ISLEM["ortalama_pct"] > 0


def stop_faydali_mi() -> bool:
    """−%25 stop hesaba yardım ediyor mu?"""
    return HESAP["boyut25_yillik_pct"] > HESAP["stop_yok_yillik_pct"]


def sorun_sinyal_mi_boyut_mu() -> str:
    if sinyal_pozitif_mi() and HESAP["boyut25_yillik_pct"] < 0:
        return "BOYUT"
    return "SINYAL"


def hukum() -> str:
    b30, v30 = en_iyi_boyut(BOYUT_CEPHESI_30)
    b40, v40 = en_iyi_boyut(BOYUT_CEPHESI_40)
    return ("Sinyal POZITIF (+%.2f%%/islem) ama %%25 boyutta hesap yilda "
            "%+.1f%% ve dusus %-.1f%%. Sorun %s: ±%%30'da optimum %%%.1f "
            "(+%.2f%%/yil), ±%%40'ta optimum %%%.0f (+%.2f%%/yil, dusus "
            "%-.1f%%). Kullanicinin boyutu optimumun %.0f kati."
            % (ISLEM["ortalama_pct"], HESAP["boyut25_yillik_pct"],
               HESAP["boyut25_dusus_pct"], sorun_sinyal_mi_boyut_mu(),
               b30 * 100, v30[0], b40 * 100, v40[0], v40[1],
               boyut_kac_kat_buyuk(0.30)))
