#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 265 — DAKİKA ÇÖZÜNÜRLÜKLÜ DOLUM: projenin ölçülmemiş TEK girdisi.

40+ turdur tekrarlanan cümle: *"doz kararı canlı ölçümden önce verilmez,
çünkü modellenmeyen İCRA SAPMASI kaldıraçla çarpılır"* (madde 227/261).
O sapmanın bir parçası anahtar gerektirmeden ölçülebilir ve bugüne dek
ölçülmedi.

NEDEN ÖLÇÜLMEMİŞTİ
------------------
Madde 213 dolumu ölçtü ama **4 saatlik barla**: "bar içinde LOW/HIGH
limite dokunduysa DOLDU". Kendi docstring'i sınırı yazıyor: *"bot 6
dakika sonra piyasaya düşüyor, bu ölçüm 4 SAAT dolmayanları alıyor."*
Yani 4 saatlik bar dolum olasılığını YUKARI, piyasa emrine düşme
sıklığını AŞAĞI saptırır. Dakika verisi projede hiç yoktu.

Ayrıca `fapi.binance.com` bu bölgeden **HTTP 451** veriyor; dakika
verisi `data.binance.vision` genel arşivinden çekildi (anahtar yok,
yalnızca kamuya açık dosyalar) — `m265_indir.py`.

ÖN KAYIT — ÜRETİMİN MERDİVENİ BİREBİR
-------------------------------------
`carry_bot.py`'den okunan gerçek sabitler:
  LIMIT_OFSET = 0.0005 · DOLUM_BEKLEME_SN = 180 · DOLUM_DENEME = 2
  GTX_DENEME_CARPANLARI = (1.0, 2.0, 4.0) · PIYASA_YEDEK = 1
Yani zaman çizgisi:
  t+0  : GTX limit, referans fiyattan 5bp UZAĞA   -> 3 dk bekle
  t+3  : fiyat YENİDEN okunur, 10bp uzağa         -> 3 dk bekle
  t+6  : fiyat YENİDEN okunur, 20bp uzağa         -> 3 dk bekle
  t+9  : dolmadıysa PİYASA emri
(Ofsetin açılması dolumu kolaylaştırmaz; GTX'in "hemen eşleşirse
reddet" kuralından kaçmak içindir — madde 160.)

Dolum ölçütü: alışta sonraki 3 dakikanın LOW'u limite <= dokunduysa
dolmuş sayılır; satışta HIGH >= limit. Bu, gerçek defterde kuyruğa
girme sorununu YOK sayar, yani ölçülen dolum oranı **gerçeğin ÜST
sınırıdır** — ve bu, sonucu bot aleyhine değil LEHİNE saptırır, o
yüzden çıkan maliyet bir TABAN olarak okunmalı.

Maliyet tanımı (karar anındaki referans fiyata göre, bp):
  maker dolum : (icra/referans − 1) işaretli + 2,0bp maker ücreti
  piyasa      : (t+9 kapanış/referans − 1) işaretli + 5,0bp taker
İşaret: alışta pozitif = pahalıya aldık.

Kıyas: backtest harmanlanmış **2,072bp/taraf** varsayıyor (madde 213).

KULLANIM
    python arastirma_dolum.py
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

KOK = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KOK, "data_1m")

LIMIT_OFSET = 0.0005
BEKLEME_DK = 3
MERDIVEN = (1.0, 2.0, 4.0)
MAKER_BP = 2.0
TAKER_BP = 5.0
VARSAYIM_BP = 2.072          # madde 213'ün harmanlanmış oranı
DILIM_SAAT = 8               # dilimler 8 saatte bir açılır (madde 264)
TERS_SECILIM_DK = 60


def seriler() -> dict:
    out = {}
    for f in sorted(glob.glob(os.path.join(VERI, "*_1m.csv"))):
        s = os.path.basename(f).replace("_1m.csv", "")
        d = pd.read_csv(f)
        d["t"] = pd.to_datetime(d["open_time"], unit="ms", errors="coerce")
        if d["t"].isna().all():
            d["t"] = pd.to_datetime(d["open_time"], unit="us", errors="coerce")
        out[s] = d.dropna(subset=["t"]).set_index("t").sort_index()
    return out


def _bir_emir(d: pd.DataFrame, i: int, yon: int) -> dict | None:
    """yon=+1 alış, -1 satış. i = karar dakikasının indeksi."""
    n = len(d)
    if i + BEKLEME_DK * len(MERDIVEN) + TERS_SECILIM_DK + 2 >= n:
        return None
    ref = float(d["open"].iloc[i])
    if not np.isfinite(ref) or ref <= 0:
        return None
    t = i
    for k, carpan in enumerate(MERDIVEN):
        yeni_ref = float(d["open"].iloc[t])
        limit = yeni_ref * (1.0 - yon * LIMIT_OFSET * carpan)
        pencere = d.iloc[t:t + BEKLEME_DK]
        if yon > 0:
            dolu = bool((pencere["low"] <= limit).any())
        else:
            dolu = bool((pencere["high"] >= limit).any())
        if dolu:
            sonra = float(d["close"].iloc[min(t + TERS_SECILIM_DK, n - 1)])
            return {
                "maker": True, "deneme": k + 1,
                "kayma_bp": yon * (limit / ref - 1.0) * 1e4,
                "maliyet_bp": yon * (limit / ref - 1.0) * 1e4 + MAKER_BP,
                # ters seçilim: dolumdan sonra fiyat bizim ALEYHİMİZE mi?
                "ters_bp": -yon * (sonra / limit - 1.0) * 1e4,
            }
        t += BEKLEME_DK
    piyasa = float(d["close"].iloc[t])
    sonra = float(d["close"].iloc[min(t + TERS_SECILIM_DK, n - 1)])
    return {
        "maker": False, "deneme": 0,
        "kayma_bp": yon * (piyasa / ref - 1.0) * 1e4,
        "maliyet_bp": yon * (piyasa / ref - 1.0) * 1e4 + TAKER_BP,
        "ters_bp": -yon * (sonra / piyasa - 1.0) * 1e4,
    }


def olc(seri: dict | None = None) -> dict:
    if seri is None:
        seri = seriler()
    kayit = []
    for s, d in seri.items():
        dk = d.index
        # dilim anları: 8 saatin katları, dakika 0
        maske = (dk.hour % DILIM_SAAT == 0) & (dk.minute == 0)
        idx = np.flatnonzero(np.asarray(maske))
        for i in idx:
            for yon in (+1, -1):
                r = _bir_emir(d, int(i), yon)
                if r is None:
                    continue
                r["sembol"] = s
                r["yon"] = "alis" if yon > 0 else "satis"
                kayit.append(r)
    k = pd.DataFrame(kayit)
    if k.empty:
        return {}
    out = {
        "n": int(len(k)),
        "sembol": int(k["sembol"].nunique()),
        "maker_oran": float(k["maker"].mean()) * 100.0,
        "deneme1_oran": float((k["deneme"] == 1).mean()) * 100.0,
        "deneme2_oran": float((k["deneme"] == 2).mean()) * 100.0,
        "deneme3_oran": float((k["deneme"] == 3).mean()) * 100.0,
        "piyasa_oran": float((~k["maker"]).mean()) * 100.0,
        "maliyet_ort_bp": float(k["maliyet_bp"].mean()),
        "maliyet_medyan_bp": float(k["maliyet_bp"].median()),
        "maker_maliyet_bp": float(k.loc[k["maker"], "maliyet_bp"].mean()),
        "piyasa_maliyet_bp": float(k.loc[~k["maker"], "maliyet_bp"].mean()),
        "piyasa_kayma_bp": float(k.loc[~k["maker"], "kayma_bp"].mean()),
        "ters_secilim_bp": float(k.loc[k["maker"], "ters_bp"].mean()),
        "alis_maliyet_bp": float(k.loc[k["yon"] == "alis", "maliyet_bp"].mean()),
        "satis_maliyet_bp": float(k.loc[k["yon"] == "satis", "maliyet_bp"].mean()),
    }
    out["varsayimdan_fark_bp"] = out["maliyet_ort_bp"] - VARSAYIM_BP
    return out


def yillik_puan_etkisi(fark_bp: float, devir_yil: float = 73.0) -> float:
    """bp cinsinden taraf başına sapma -> yıllık getiri puanı.

    Madde 213: komisyon ekseninin TOPLAM bütçesi 3,3 puan ve bu
    2,072bp/taraf varsayımına karşılık geliyor. Oran doğrusal
    kabul edilir: 1bp sapma ~ 3,3/2,072 = 1,59 puan/yıl.
    """
    return fark_bp * (3.3 / VARSAYIM_BP)


def yaz() -> None:
    o = olc()
    if not o:
        print("veri yok - once m265_indir.py")
        return
    print("MADDE 265 — DAKİKA ÇÖZÜNÜRLÜKLÜ DOLUM")
    print("%d emir denemesi, %d sembol, 8 saatlik dilim ızgarası\n"
          % (o["n"], o["sembol"]))
    print("DOLUM:")
    print("  maker toplam        %%%.1f" % o["maker_oran"])
    print("    1. deneme (5bp)   %%%.1f" % o["deneme1_oran"])
    print("    2. deneme (10bp)  %%%.1f" % o["deneme2_oran"])
    print("    3. deneme (20bp)  %%%.1f" % o["deneme3_oran"])
    print("  PİYASA emrine düşme %%%.1f" % o["piyasa_oran"])
    print("\nMALİYET (karar fiyatına göre, bp/taraf):")
    print("  harmanlanmış ortalama   %+.3f bp   (varsayım %.3f)"
          % (o["maliyet_ort_bp"], VARSAYIM_BP))
    print("  medyan                  %+.3f bp" % o["maliyet_medyan_bp"])
    print("  maker dolumlarda        %+.3f bp" % o["maker_maliyet_bp"])
    print("  piyasaya düşenlerde     %+.3f bp  (kayma %+.3f)"
          % (o["piyasa_maliyet_bp"], o["piyasa_kayma_bp"]))
    print("  alış %+.3f | satış %+.3f"
          % (o["alis_maliyet_bp"], o["satis_maliyet_bp"]))
    print("\nTERS SEÇİLİM (dolumdan 60 dk sonra, aleyhte = pozitif):")
    print("  %+.3f bp" % o["ters_secilim_bp"])
    print("\nSAPMA: %+.3f bp/taraf -> yıllık %+.2f puan"
          % (o["varsayimdan_fark_bp"],
             yillik_puan_etkisi(o["varsayimdan_fark_bp"])))


if __name__ == "__main__":
    yaz()
    sys.exit(0)


# ===========================================================================
# ÖLÇÜM SONUÇLARI (madde 265) — makine okunur
# ===========================================================================
# 6.696 emir denemesi, 18 sembol (100M$ üstü kripto evren, TRADFI hariç),
# 2026-07-01 → 2026-08-31, 8 saatlik dilim ızgarası, her an için alış+satış.
OLCUM = {
    "n": 6696, "sembol": 18,
    "maker_oran": 82.6,
    "deneme1_oran": 72.3, "deneme2_oran": 8.5, "deneme3_oran": 1.9,
    "piyasa_oran": 17.4,
    "maliyet_ort_bp": 2.570, "maliyet_medyan_bp": -3.000,
    "maker_maliyet_bp": -0.502,
    "piyasa_maliyet_bp": 17.190, "piyasa_kayma_bp": 12.190,
    "alis_maliyet_bp": 2.851, "satis_maliyet_bp": 2.290,
    "ters_secilim_bp": -0.508,
}
SAPMA_BP = OLCUM["maliyet_ort_bp"] - VARSAYIM_BP        # +0,498
SAPMA_PUAN_YIL = SAPMA_BP * (3.3 / VARSAYIM_BP)         # ~0,79

# Merdiven varyantları (aynı 6.696 deneme). ad -> (maker%, ort bp)
MERDIVEN_CEPHESI = {
    "uretim_5_10_20_9dk": (82.6, 2.570),
    "ek3dk_5bp_12dk": (90.2, 2.375),
    "ek9dk_5bp_18dk": (93.8, 2.251),
    "ek21dk_5bp_30dk": (95.9, 2.096),
    "yalniz_5bp_9dk": (92.4, 2.587),
    "tek_deneme_3dk_piyasa": (72.3, 2.835),
}


def maliyetin_kaynagi() -> dict:
    """Maliyet nereden geliyor? maker'lar mı, piyasaya düşenler mi?"""
    mk = OLCUM["maker_oran"] / 100.0
    return {
        "maker_katkisi_bp": mk * OLCUM["maker_maliyet_bp"],
        "piyasa_katkisi_bp": (1 - mk) * OLCUM["piyasa_maliyet_bp"],
    }


def dolum_orani_ust_sinir_mi() -> bool:
    """Ölçüt 'LOW limite dokundu' - defterde KUYRUK yok sayıldı.

    Bu, dolum oranını YUKARI (ve maliyeti AŞAĞI) saptırır. Yani
    ölçülen 2,570bp gerçek maliyetin TABANIDIR.
    """
    return True


def beklemek_ucuz_mu() -> dict:
    """Daha uzun beklemek bp olarak ucuz mu? (dolum tarafı YALNIZ)

    DİKKAT: bu yarım bir hesap. Beklemek dolum maliyetini düşürür ama
    GECİKME maliyeti doğurur (madde 213'ün GEC taraması: 4 saatte 1,1
    puan) ve pozisyon o süre boyunca açık DEĞİLDİR. İki tarafı aynı
    ölçüde kıyaslamak motorda ayrı bir koşu ister; bu yüzden burada
    bir ÖNERİ YOK, bir ADAY var.
    """
    u = MERDIVEN_CEPHESI["uretim_5_10_20_9dk"][1]
    return {ad: round(u - v[1], 3) for ad, v in MERDIVEN_CEPHESI.items()}


def aday_canli_testi() -> str:
    return ("ADAY: dolmayan emirde piyasaya düşmek yerine 5bp'de 21 dk daha "
            "beklemek dolum maliyetini 2,570 -> 2,096bp indiriyor (~0,75 "
            "puan/yıl). AMA (1) kuyruk yok sayıldığı için bütün oranlar "
            "iyimser, (2) gecikme maliyeti bu tabloda YOK. Canlı testi: "
            "CARRY_DOLUM_BEKLEME ve CARRY_DOLUM_DENEME ile iki ayarı "
            "DÖNÜŞÜMLÜ koşup gerçekleşen dolum oranını ve kaymayı "
            "karşılaştırmak. Karar canlı ölçümden önce VERİLMEZ.")


def hukum() -> str:
    return ("VARSAYIM İYİMSER: 2,072bp -> ölçülen 2,570bp (+0,498bp/taraf, "
            "~0,79 puan/yıl). Ayar DEĞİŞMEDİ.")
