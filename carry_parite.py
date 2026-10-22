"""SİNYAL TANIMI PARİTESİ (madde 210).

`carry_sapma.py` GERÇEKLEŞEN GETİRİYİ karşılaştırır. Madde 209 gösterdi ki
bu yeterli değil: canlı bot ile backtest **aynı sinyali** kullanmayı
bırakmıştı (canlı 8 saatlik pencere, backtest 3 günlük ortalama) ve
hiçbir test bunu yakalamadı. Getiri karşılaştırması yakalayamaz çünkü
canlı veri yokken kıyaslanacak getiri de yoktur - kırık, ölçüm
başlamadan önce oradaydı.

Bu araç GETİRİ DEĞİL TANIM karşılaştırır:

  canlı taraf    : `carry_bot.yillik_funding` ÇAĞRILIR (kopyası değil,
                   gerçek fonksiyon), her bar için o barda görülebilen
                   ödeme kayıtlarıyla.
  backtest tarafı: panelin kurulumu (`SIN = ham * 24/ARALIK`, sonra
                   `sk = SIN.rolling(BAR).mean()`).

Sonra iki sinyalin KESİTSEL SIRALAMA korelasyonu ölçülür - motor sadece
sıralama kullandığı için asıl önemli olan bu.

KARARI NE VERİR: referans ölçüm (madde 209: +%96.8 / Sharpe 3.02) canlı
botun tahmincisiyle 48 SAATLİK pencerede yapıldı. Yani doğru dayanak
panelin 72 saati DEĞİL, `REFERANS_PENCERE_SAAT` sabitidir. Üç şart:

  1. `cb.FUNDING_WINDOW_HOURS == REFERANS_PENCERE_SAAT`  (madde 209'un
     hatası tam buydu: kod 8, ölçüm 72)
  2. pencereye giren ödeme SAYISI her aralıkta tam `pencere/aralik`
  3. mevcut ayarın sıralaması, referans penceredeki sıralamayla >= 0.95

Panel ile korelasyon ayrıca yazılır ama KARARA GİRMEZ: panel genişleyen
medyan aralığı ve 72 barlık rolling kullanıyor, referans ölçüm ise canlı
tahminciyi - ikisi 48 saatte ~0.90 ile ayrışıyor ve bu BEKLENEN bir
ayrışma, hata değil.

ÜÇ HATA SINIFINI YAKALAR (üçü de madde 209'da canlıda bulundu):
  1. pencere uzunluğu farkı        -> korelasyon çöker
  2. pencere sınırının kapsayıcılığı -> ödeme SAYISI yanlış
  3. kayıt sayısı formülünün kırpması -> pencere sessizce kısalır

KULLANIM:
    python carry_parite.py                 # gerçek funding verisiyle
    python carry_parite.py --sembol 40     # daha hızlı, 40 sembol
    python carry_parite.py --pencere 8     # bozuk ayarı DOĞRULA (düşmeli)
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd

import carry_bot as cb

R = os.path.dirname(os.path.abspath(__file__))
FUNDING_DIZIN = os.path.join(R, "data_funding_genis")
BAR_SAAT = 4.0
PANEL_BAR = 18       # carry_denetim.FUNDING_PENCERE - panelin rolling'i (3 gün)

REFERANS_PENCERE_SAAT = 60.0
"""Referans beklentinin ÖLÇÜLDÜĞÜ funding penceresi (madde 209).
Canlı bottaki değer bundan farklıysa beklenti geçersizdir. Bu sabiti
değiştirmek, referans serisini yeniden üretmeyi gerektirir.

MADDE 442: 48 -> 60. T60 kitabının beklentisi (madde 429-438) 60 saatlik
sinyal paneliyle (`/tmp/sk_bar60.pkl`, 15 x 4 sa bar) ölçüldü; canlı
varsayılan da 60. Eski kitap (CARRY_PROFIL=BUGUN) 48 ile ölçülmüştü."""

# Kabul eşikleri. Mevcut ayar referans pencereyle AYNI ise korelasyon
# 1.0'dır; madde 209'un hatalı ayarında (8 saat) 0.60'a düşüyordu.
PARITE_ESIK = 0.90
PARITE_INCELE = 0.95
PANEL_BILGI_ESIK = 0.80
"""Panel korelasyonu bunun altına inerse bilgi amaçlı UYARI yazılır
(karara girmez). 48 saatte beklenen değer ~0.90 (madde 209; 60 saatte ölçülmedi)."""


def odemeleri_oku(sembol: str, dizin: str = None) -> pd.DataFrame | None:
    """Bir sembolün funding ödemelerini (zaman, oran) döner."""
    dizin = dizin or FUNDING_DIZIN
    yol = os.path.join(dizin, f"{sembol}.csv")
    if not os.path.exists(yol):
        return None
    try:
        d = pd.read_csv(yol, parse_dates=["date"])
    except Exception:
        return None
    if "funding" not in d.columns or len(d) < 3:
        return None
    d["date"] = d["date"].dt.floor("h")
    return d.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def kayit_listesi(zamanlar: np.ndarray, oranlar: np.ndarray) -> list[dict]:
    """`carry_bot.yillik_funding`'in beklediği Binance biçimi."""
    return [{"fundingTime": int(t), "fundingRate": str(r)}
            for t, r in zip(zamanlar, oranlar)]


def canli_sinyal(odemeler: pd.DataFrame, barlar: pd.DatetimeIndex,
                 pencere: float = None) -> pd.Series:
    """CANLI BOTUN sinyali, her bar için.

    `carry_bot.yillik_funding` DOĞRUDAN çağrılır; kayıt sayısı da
    `funding_topla`'nın formülüyle belirlenir. Böylece bu araç, canlı
    koddaki bir değişikliği kaçıramaz - kopya tutmuyor.
    """
    pencere = cb.FUNDING_WINDOW_HOURS if pencere is None else pencere
    n_kayit = max(4, min(400, int(pencere) + 4))        # funding_topla ile AYNI
    t_ms = odemeler["date"].values.astype("datetime64[ms]").astype(np.int64)
    oran = odemeler["funding"].values.astype(float)
    bar_ms = barlar.values.astype("datetime64[ms]").astype(np.int64)
    hi = np.searchsorted(t_ms, bar_ms, side="right")    # barda görülebilen son kayıt
    out = np.full(len(barlar), np.nan)
    for i, h in enumerate(hi):
        if h < 2:
            continue
        a0 = max(0, h - n_kayit)
        y = cb.yillik_funding(kayit_listesi(t_ms[a0:h], oran[a0:h]), pencere)
        if y is not None:
            out[i] = y
    return pd.Series(out, index=barlar)


def backtest_sinyal(odemeler: pd.DataFrame, barlar: pd.DatetimeIndex,
                    panel_bar: int = PANEL_BAR) -> pd.Series:
    """BACKTEST PANELİNİN sinyali (carry_denetim + d1.py kurulumu).

    ARALIK: genişleyen medyan (nedensel). SIN: son ödemenin yıllık hâli,
    bara ffill'lenir. sk: `panel_bar` barlık ortalama.
    """
    t = odemeler["date"]
    dh = t.diff().dt.total_seconds().div(3600)
    aralik = dh.expanding(min_periods=2).median()
    aralik = aralik.where((aralik > 0) & np.isfinite(aralik), 8.0).ffill().fillna(8.0)
    ham = pd.Series(odemeler["funding"].values * (24.0 / aralik.values) * 365.0,
                    index=t.values)
    birlesik = ham.reindex(ham.index.union(barlar)).ffill(limit=4)
    sin = birlesik.reindex(barlar)
    return sin.rolling(panel_bar, min_periods=min(6, panel_bar)).mean()


def parite_olc(semboller: list[str], dizin: str = None,
               pencere: float = None, panel_bar: int = PANEL_BAR,
               barlar: pd.DatetimeIndex = None) -> dict:
    """Kesitsel sıralama paritesini ölçer.

    Döner: {'kor': ortalama Spearman, 'n_kesit', 'n_sembol', 'kor_p5',
            'durum', 'gerekce'}
    """
    canli, bt = {}, {}
    for s in semboller:
        d = odemeleri_oku(s, dizin)
        if d is None:
            continue
        b = barlar
        if b is None:
            b = pd.date_range(d["date"].iloc[0].ceil("4h"),
                              d["date"].iloc[-1].floor("4h"), freq="4h")
        if len(b) < 10:
            continue
        canli[s] = canli_sinyal(d, b, pencere)
        bt[s] = backtest_sinyal(d, b, panel_bar)
    if len(canli) < 3:
        return {"kor": float("nan"), "n_kesit": 0, "n_sembol": len(canli),
                "durum": "VERI_YOK",
                "gerekce": f"parite için en az 3 sembol gerekiyor ({len(canli)} var)"}
    A = pd.DataFrame(canli)
    B = pd.DataFrame(bt).reindex(index=A.index, columns=A.columns)
    kors = []
    for i in range(len(A)):
        a, b_ = A.iloc[i].values, B.iloc[i].values
        m = np.isfinite(a) & np.isfinite(b_)
        if m.sum() < 3:
            continue
        ra = pd.Series(a[m]).rank().values
        rb = pd.Series(b_[m]).rank().values
        if ra.std() == 0 or rb.std() == 0:
            continue
        kors.append(float(np.corrcoef(ra, rb)[0, 1]))
    if not kors:
        return {"kor": float("nan"), "n_kesit": 0, "n_sembol": len(canli),
                "durum": "VERI_YOK", "gerekce": "ortak kesit bulunamadı"}
    k = np.array(kors)
    ort = float(k.mean())
    p5 = float(np.percentile(k, 5))
    if ort >= PARITE_INCELE:
        durum, ger = "TAMAM", f"sıralama paritesi %{ort*100:.1f}"
    elif ort >= PARITE_ESIK:
        durum, ger = "INCELE", (f"sıralama paritesi %{ort*100:.1f} - eşiğin "
                                f"(%{PARITE_INCELE*100:.0f}) altında")
    else:
        durum, ger = "BOZUK", (f"sıralama paritesi %{ort*100:.1f} - sinyal tanımı "
                               f"ölçülenden AYRIŞMIŞ (madde 209)")
    return {"kor": ort, "kor_p5": p5, "n_kesit": len(k), "n_sembol": len(canli),
            "durum": durum, "gerekce": ger}


def referans_parite(semboller: list[str], dizin: str = None,
                    pencere: float = None) -> dict:
    """Mevcut ayarın sıralaması, REFERANS penceredeki sıralamayla aynı mı?

    Karara giren asıl ölçüm bu: karşılaştırma dayanağı panel değil,
    beklentinin ölçüldüğü pencere (`REFERANS_PENCERE_SAAT`). Ayarlar
    eşitse korelasyon tam 1.0 çıkar; madde 209'un hatalı ayarında
    (8 saate karşı 48) ~0.6'ya düşüyordu.
    """
    pen = cb.FUNDING_WINDOW_HOURS if pencere is None else pencere
    canli, ref = {}, {}
    for s in semboller:
        d = odemeleri_oku(s, dizin)
        if d is None:
            continue
        b = pd.date_range(d["date"].iloc[0].ceil("4h"),
                          d["date"].iloc[-1].floor("4h"), freq="4h")
        if len(b) < 10:
            continue
        canli[s] = canli_sinyal(d, b, pen)
        ref[s] = (canli[s] if pen == REFERANS_PENCERE_SAAT
                  else canli_sinyal(d, b, REFERANS_PENCERE_SAAT))
    if len(canli) < 3:
        return {"kor": float("nan"), "n_kesit": 0, "durum": "VERI_YOK",
                "gerekce": "en az 3 sembol gerekiyor"}
    A = pd.DataFrame(canli)
    B = pd.DataFrame(ref).reindex(index=A.index, columns=A.columns)
    kors = []
    for i in range(len(A)):
        a, b_ = A.iloc[i].values, B.iloc[i].values
        m = np.isfinite(a) & np.isfinite(b_)
        if m.sum() < 3:
            continue
        ra = pd.Series(a[m]).rank().values
        rb = pd.Series(b_[m]).rank().values
        if ra.std() == 0 or rb.std() == 0:
            continue
        kors.append(float(np.corrcoef(ra, rb)[0, 1]))
    if not kors:
        return {"kor": float("nan"), "n_kesit": 0, "durum": "VERI_YOK",
                "gerekce": "ortak kesit bulunamadı"}
    k = np.array(kors)
    ort = float(k.mean())
    return {"kor": ort, "kor_p5": float(np.percentile(k, 5)), "n_kesit": len(k),
            "durum": ("TAMAM" if ort >= PARITE_INCELE
                      else "INCELE" if ort >= PARITE_ESIK else "BOZUK"),
            "gerekce": f"referans pencereye ({REFERANS_PENCERE_SAAT:.0f}sa) "
                       f"göre sıralama paritesi %{ort*100:.1f}"}


def karar(pencere: float = None, semboller: list[str] = None,
          dizin: str = None) -> dict:
    """ÜÇ ŞARTIN birleşik kararı (madde 210).

    1. pencere == REFERANS_PENCERE_SAAT
    2. her aralıkta ödeme sayısı tam `pencere/aralik` (sınır dışlayıcı)
    3. referans pencereyle sıralama paritesi >= PARITE_INCELE

    Şart 3 için veri gerekiyor; veri yoksa 1 ve 2 ile karar verilir -
    ikisi zaten madde 209'un üç hatasının ikisini yakalıyor.
    """
    pen = cb.FUNDING_WINDOW_HOURS if pencere is None else pencere
    sorun = []
    if pen != REFERANS_PENCERE_SAAT:
        sorun.append(
            f"PENCERE AYRIŞMIŞ: canlı {pen:.0f}sa, referans ölçüm "
            f"{REFERANS_PENCERE_SAAT:.0f}sa - beklenti bu ayarla ÖLÇÜLMEDİ")
    sayim = {}
    for ar in (1.0, 2.0, 4.0, 8.0):
        g, b = odeme_sayisi(pen, ar), odeme_sayisi_beklenen(pen, ar)
        sayim[ar] = (g, b)
        if g != b:
            sorun.append(f"ÖDEME SAYISI YANLIŞ: {ar:.0f}sa sembolde {g} ödeme "
                         f"girmiş, {b} olmalı (sınır/kayıt sayısı hatası)")
    ref = None
    if semboller:
        ref = referans_parite(semboller, dizin, pen)
        if ref["durum"] == "BOZUK":
            sorun.append("SIRALAMA AYRIŞMIŞ: " + ref["gerekce"])
    return {"durum": "BOZUK" if sorun else "TAMAM", "sorunlar": sorun,
            "pencere": pen, "sayim": sayim, "referans": ref}


def odeme_sayisi(pencere: float, aralik_saat: float, n: int = 400) -> int:
    """Pencereye KAÇ ödeme giriyor - CANLI KODDAN geri çıkarılır.

    Madde 209: sınır kapsayıcı olduğunda 8sa pencere 8sa sembolde 2 ödeme
    alıyordu ve hiçbir test bunu görmüyordu.

    Sayı, `carry_bot.yillik_funding`'in dönüşünden hesaplanır - burada
    yeniden uygulanmaz, yoksa canlı koddaki bir değişikliği kaçırırdı.
    Bütün oranlar 0, SADECE en yeni ödeme 1.0 verilir; fonksiyonun
    ortalaması 1/sayı olur, yıllıklaştırma çarpanı bilindiğinden sayı
    tek adımda geri çıkar.
    """
    t0 = 1_700_000_000_000
    adim = int(aralik_saat * 3600000)
    kayit = [{"fundingTime": t0 + i * adim,
              "fundingRate": ("1.0" if i == n - 1 else "0.0")}
             for i in range(n)]
    y = cb.yillik_funding(kayit, pencere)
    if not y or y <= 0:
        return 0
    carpan = (24.0 / max(aralik_saat, 4.0)) * 365.0
    return int(round(carpan / y))


def odeme_sayisi_beklenen(pencere: float, aralik_saat: float) -> int:
    """Dışlayıcı sınırla pencereye girmesi GEREKEN ödeme sayısı.

    Pencere SON ödemeden geriye `pencere` saattir ve alt sınır dışlayıcıdır:
    son ödeme (k=0) ve k*aralik < pencere olan her k girer -> tavan(p/a).
    Pencere aralığın katıyken (48/8) bu eski `int(p/a)` ile aynıdır; katı
    değilken (madde 442: 60/8) eski formül 7 derdi, canlı kod (doğru olarak)
    8 ödeme alır: 0,8,...,56 sa. Kapsayıcı sınır (madde 209 hatası) katta
    BİR FAZLA verir; tavan formülü bunu hâlâ yakalar."""
    import math
    return max(1, math.ceil(pencere / max(aralik_saat, 1.0) - 1e-9))


def yaz(sembol_sayisi: int = 0, pencere: float = None, dizin: str = None) -> str:
    """İnsan okunur parite raporu."""
    dizin = dizin or FUNDING_DIZIN
    yollar = sorted(glob.glob(os.path.join(dizin, "*.csv")))
    sem = [os.path.basename(p)[:-4] for p in yollar]
    if sembol_sayisi:
        sem = sem[:sembol_sayisi]
    s = ["=" * 64, "SİNYAL TANIMI PARİTESİ (madde 210)", "=" * 64]
    pen = cb.FUNDING_WINDOW_HOURS if pencere is None else pencere
    s.append(f"canlı pencere     : {pen:.0f} saat"
             + ("" if pencere is None else "  (ELLE VERİLDİ)"))
    s.append(f"referans pencere  : {REFERANS_PENCERE_SAAT:.0f} saat "
             f"(beklentinin ölçüldüğü ayar)")
    s.append(f"kayıt sayısı      : {max(4, min(400, int(pen) + 4))}")
    s.append("")
    k = karar(pencere, sem if sem else None, dizin)
    s.append("ŞART 1 - PENCERE referans ayarla aynı mı:")
    s.append(f"  {'OK ' if pen == REFERANS_PENCERE_SAAT else '!! '}"
             f"canlı {pen:.0f}sa / referans {REFERANS_PENCERE_SAAT:.0f}sa")
    s.append("")
    s.append("ŞART 2 - PENCEREYE GİREN ÖDEME SAYISI (sınır dışlayıcı):")
    for ar, (n, bek) in k["sayim"].items():
        s.append(f"  {'OK ' if n == bek else '!! '}{ar:.0f} saatlik sembol: "
                 f"{n} ödeme (olmalı {bek})")
    s.append("")
    if not sem:
        s.append("ŞART 3 - funding verisi yok, kesitsel parite ÖLÇÜLEMEDİ")
    else:
        r = k["referans"]
        s.append(f"ŞART 3 - REFERANS PENCEREYLE SIRALAMA ({r['n_kesit']} kesit):")
        s.append(f"  {'OK ' if r['durum'] == 'TAMAM' else '!! '}"
                 f"ortalama Spearman {r['kor']:.4f}"
                 + (f"  p5 {r['kor_p5']:.4f}" if "kor_p5" in r else ""))
        s.append(f"  eşikler: tamam >= {PARITE_INCELE}, incele >= {PARITE_ESIK}")
        s.append("")
        p = parite_olc(sem, dizin, pencere)
        s.append(f"BİLGİ - panel sinyaliyle korelasyon: {p['kor']:.4f} "
                 f"({p['n_sembol']} sembol)")
        s.append(f"  Panel genişleyen medyan aralığı + {PANEL_BAR} barlık rolling")
        s.append("  kullanıyor; referans ölçüm ise canlı tahminciyi. Bu sayının")
        s.append("  1.0 OLMAMASI beklenir ve KARARA GİRMEZ.")
        if np.isfinite(p["kor"]) and p["kor"] < PANEL_BILGI_ESIK:
            s.append(f"  UYARI: {PANEL_BILGI_ESIK} altına indi - panel kurulumu")
            s.append("  değişmiş olabilir, `carry_denetim.FUNDING_PENCERE`ye bakın.")
    s.append("")
    s.append(f"KARAR: {k['durum']}")
    for x in k["sorunlar"]:
        s.append(f"  - {x}")
    if k["durum"] == "BOZUK":
        s.append("")
        s.append("  Backtest'in ölçtüğü şey ile botun yaptığı şey farklı.")
        s.append("  Beklenti (+%112.5 / Sharpe 3.12) bu ayarla ÖLÇÜLMEDİ.")
        s.append("  CARRY_FUNDING_WINDOW_H'yi kontrol edin (madde 209).")
    s.append("=" * 64)
    return "\n".join(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sembol", type=int, default=0,
                    help="kaç sembolle ölçülsün (0 = hepsi)")
    ap.add_argument("--pencere", type=float, default=None,
                    help="canlı pencereyi elle ver (bozuk ayarı doğrulamak için)")
    ap.add_argument("--dizin", default=None, help="funding verisi dizini")
    a = ap.parse_args()
    print(yaz(a.sembol, a.pencere, a.dizin))


if __name__ == "__main__":
    main()
