"""Korelasyon riski yönetimi (hem backtest hem CANLI bot tarafından kullanılır).

Neden gerekli: bot aynı anda `max_concurrent_positions` kadar pozisyon açar.
Kripto altcoinleri birbirine yüksek korelasyonludur, özellikle çöküşlerde.
Filtresiz haliyle "4 çeşitlendirilmiş bahis" sandığınız şey aslında "aynı
bahsin 4 katı" olabilir - piyasa aleyhe tek bir hareket yaptığında 4 pozisyon
birden aynı anda kaybeder.

Gerçek 2020-2026 verisiyle (14 coin, 4h, mean_reversion, max 4 pozisyon)
ölçüldü - bu filtre HEM getiriyi artırdı HEM riski azalttı:
  filtresiz : +1005.89R, max düşüş -61.10R, en büyük korelasyonlu küme 3
  filtreli  : +1046.72R, max düşüş -46.23R, en büyük korelasyonlu küme 2
(137 sinyal korelasyon nedeniyle atlandı)

NOT: Bu sonuç stratejiye bağlıdır. Daha önce `adaptive` ile sentetik veride
yapılan testte filtre getiriyi DÜŞÜRMÜŞTÜ (bir risk/getiri dengesiydi).
Gerçek veri + mean_reversion ile ücretsiz bir iyileştirmeye dönüştü.
"""

import numpy as np
import pandas as pd


def rolling_correlation_from_closes(closes_a, closes_b, lookback: int) -> float:
    """İki fiyat serisinin son `lookback` barlık getiri korelasyonu.
    Veri yetersizse 0.0 döner (yani "korelasyon bilinmiyor" -> engelleme)."""
    ra = pd.Series(closes_a).pct_change().values[-lookback:]
    rb = pd.Series(closes_b).pct_change().values[-lookback:]
    if len(ra) < 10 or len(rb) < 10:
        return 0.0
    n = min(len(ra), len(rb))
    ra, rb = ra[-n:], rb[-n:]
    mask = ~(np.isnan(ra) | np.isnan(rb))
    if mask.sum() < 10:
        return 0.0
    ra_m, rb_m = ra[mask], rb[mask]
    if np.std(ra_m) == 0 or np.std(rb_m) == 0:
        return 0.0
    corr = np.corrcoef(ra_m, rb_m)[0, 1]
    return 0.0 if np.isnan(corr) else float(corr)


def is_too_correlated(candidate_closes, open_positions_closes: dict,
                      threshold: float, lookback: int):
    """Yeni bir sinyal, halihazırda AÇIK pozisyonlardan biriyle fazla
    korelasyonlu mu? (True, sembol, korelasyon) veya (False, None, 0.0) döner.

    candidate_closes       : aday sembolün kapanış fiyatı serisi
    open_positions_closes  : {sembol: kapanış serisi} açık pozisyonlar
    """
    for open_sym, open_closes in open_positions_closes.items():
        corr = rolling_correlation_from_closes(candidate_closes, open_closes, lookback)
        if abs(corr) >= threshold:
            return True, open_sym, corr
    return False, None, 0.0
