"""Tarihsel veri kalite kontrolü ve temizleme.

NEDEN GEREKLİ: historical_data/ içindeki 2020 verisi (Binance Futures'ın
ilk ayları) bozuk barlar içeriyor - likidite boşlukları, hatalı tick'ler,
borsa hataları. Örnekler (hepsi gerçek, tespit edildi):
  BTCUSDT  2020-07-13: 9.400 -> 65.000 -> 11.299   (%591 sonra %-82)
  LTCUSDT  2020-06-06: 46,66 -> 99.999,99 -> 47,20 (%214.216)
  XRPUSDT  2020-06-10: 0,2013 -> 1.490 -> 0,2017   (%740.088)
  XTZUSDT  2020-10-04: 2,132 -> 0,001 -> 2,110     (%-100 sonra %210.900)

Bunlar gerçek fiyat hareketi DEĞİL. Backtest'te bu barlar:
  - Sahte "aşırı hareket" sinyalleri üretir (özellikle extreme_reversal'da)
  - Stop-loss'ları anlamsız yerlerden tetikler
  - Volatilite/ATR hesaplarını bozar
Ölçüldü: 2020 tüm stratejilerde negatiftir ve bunun büyük kısmı bu
bozuk barlardan kaynaklanıyor olabilir.

YAKLAŞIM: Bir bar, komşularına göre aşırı sapıyor VE hemen ardından
geri dönüyorsa ("spike-and-revert"), bu gerçek hareket değil veri
hatasıdır. Gerçek bir çöküş geri dönmez; veri hatası döner.
"""

import numpy as np
import pandas as pd


def find_bad_bars(df: pd.DataFrame, spike_threshold: float = 0.35,
                  revert_threshold: float = 0.5,
                  median_window: int = 101, median_ratio: float = 3.0) -> pd.Series:
    """Bozuk barları (True) işaretleyen boolean seri döner.

    spike_threshold  : bir barda |getiri| bu oranı aşarsa "spike" adayı (0.35 = %35)
    revert_threshold : spike'ın bu oranı sonraki barda geri alınırsa veri hatası
                       sayılır (0.5 = hareketin yarısından fazlası geri alındı)
    median_window    : ortanca penceresi (101 bar ~ 17 gün @ 4h)
    median_ratio     : fiyat, pencere ortancasının bu katından fazla/azsa bozuk
                       (3.0 = 3 kat sapma; gerçek kripto hareketleri bile
                       17 günlük ortancadan 3 kat sapmaz)

    Ayrıca tutarsız OHLC barları (high < low, close aralık dışı) her zaman
    bozuk sayılır.
    """
    close = df["close"].values
    n = len(close)
    bad = np.zeros(n, dtype=bool)

    # 1) OHLC tutarsızlıkları - bunlar kesin hatadır
    if {"high", "low", "open"}.issubset(df.columns):
        h, l, o, c = df["high"].values, df["low"].values, df["open"].values, close
        bad |= (h < l) | (c > h) | (c < l) | (o > h) | (o < l) | (l <= 0) | (c <= 0)

    # 2) Spike-and-revert tespiti
    ret = np.zeros(n)
    ret[1:] = (close[1:] - close[:-1]) / np.where(close[:-1] == 0, np.nan, close[:-1])

    for i in range(1, n - 1):
        if abs(ret[i]) < spike_threshold:
            continue
        # Sonraki bar spike'ı geri alıyor mu? (ters yönde, büyük ölçüde)
        if ret[i] * ret[i + 1] < 0 and abs(ret[i + 1]) >= abs(ret[i]) * revert_threshold:
            bad[i] = True

    # 3) Ortanca bazlı aykırı değer tespiti (UZUN SÜRELİ bozuk bloklar için)
    # Spike-and-revert, tek bar hatalarını yakalar ama GÜNLERCE süren kaotik
    # blokları kaçırır. Gerçek örnek - ETHUSDT 2020-11-14/16: ETH gerçekte
    # ~460$ iken veride 90.000$ olarak kaydedilmiş barlar var (birkaç gün
    # boyunca 321 ile 90.000 arasında zıplıyor). Bu tür bloklarda her bar
    # komşusuna göre "tutarlı" göründüğü için spike-and-revert çalışmaz.
    # Çözüm: bar, etrafındaki geniş pencerenin ORTANCASINDAN kat kat
    # sapıyorsa bozuktur (ortanca, uç değerlerden etkilenmez).
    s = pd.Series(close).replace(0, np.nan)
    # Pencere veri uzunluğunu aşarsa ortanca hiç hesaplanamaz (min_periods
    # sağlanamaz) ve filtre SESSİZCE devre dışı kalır. Kısa serilerde
    # pencereyi küçült - böylece filtre her zaman çalışır.
    win = min(median_window, max(5, len(s) // 2 * 2 + 1))
    min_p = max(3, win // 4)
    med = s.rolling(window=win, center=True, min_periods=min_p).median()
    ratio = s / med
    bad |= ((ratio > median_ratio) | (ratio < 1.0 / median_ratio)).fillna(False).values

    return pd.Series(bad, index=df.index)


def clean_ohlcv(df: pd.DataFrame, verbose: bool = False, symbol: str = "") -> pd.DataFrame:
    """Bozuk barları tespit edip komşularından interpolasyonla onarır.

    Barı SİLMEK yerine onarmak tercih edilir: silmek zaman serisinde boşluk
    yaratır ve geriye bakan indikatörleri (return_n_pct, ATR) kaydırır.
    """
    bad = find_bad_bars(df)
    if not bad.any():
        return df

    out = df.copy()
    for col in ["open", "high", "low", "close"]:
        if col not in out.columns:
            continue
        s = out[col].astype(float)
        s[bad.values] = np.nan
        # önce/sonra bilinen değerlerden doğrusal interpolasyon
        out[col] = s.interpolate(method="linear", limit_direction="both")

    # Hacim de bozuk olabilir - o barlarda 0 yerine medyan kullan
    if "volume" in out.columns:
        v = out["volume"].astype(float)
        v[bad.values] = np.nan
        out["volume"] = v.fillna(v.median())

    if verbose:
        print(f"  {symbol}: {int(bad.sum())} bozuk bar onarildi ({bad.sum()/len(df)*100:.2f}%)")

    return out


def find_stale_bars(df: pd.DataFrame, min_run: int = 6) -> pd.Series:
    """DONUK (ileri doldurulmuş) barları işaretler.

    Kalıp: high VE low ardışık barlarda aynı kalıyor. Gerçek bir piyasada
    4 saatlik barın yüksek ve düşüğü art arda tıpatıp aynı olmaz - bu,
    verinin ileri doldurulduğunu (forward-fill) gösterir.

    Gerçek örnek: EOSUSDT 2025-05-21'den itibaren 2869 bar (16 ay)
    boyunca open=high=low=close=0.78. Coin muhtemelen delist edilmiş ve
    veri sağlayıcı son fiyatı tekrarlamış.

    min_run: en az kaç ardışık bar aynıysa donuk sayılsın. Tek tük
    tekrarlar normal olabilir (özellikle düşük volatilitede); uzun
    seriler veri sorunudur.
    """
    if not {"high", "low"}.issubset(df.columns):
        return pd.Series(False, index=df.index)
    ayni = (df["high"].diff() == 0) & (df["low"].diff() == 0)
    stale = pd.Series(False, index=df.index)
    seri = 0
    for i in range(len(ayni)):
        if ayni.iloc[i]:
            seri += 1
        else:
            if seri >= min_run:
                stale.iloc[i - seri:i] = True
            seri = 0
    if seri >= min_run:
        stale.iloc[len(ayni) - seri:] = True
    return stale


def stale_orani(df: pd.DataFrame, min_run: int = 6) -> float:
    """Donuk bar oranını döner (0.0 - 1.0). Coin eleme kararı için."""
    if len(df) == 0:
        return 0.0
    return float(find_stale_bars(df, min_run).mean())


def quality_report(data: dict) -> dict:
    """Her sembol için bozuk bar sayısını raporlar (temizleme yapmaz)."""
    report = {}
    for sym, df in data.items():
        bad = find_bad_bars(df)
        stale = find_stale_bars(df)
        report[sym] = {
            "total_bars": len(df),
            "bad_bars": int(bad.sum()),
            "pct": bad.sum() / len(df) * 100 if len(df) else 0.0,
            "stale_bars": int(stale.sum()),
            "stale_pct": stale.sum() / len(df) * 100 if len(df) else 0.0,
        }
    return report
