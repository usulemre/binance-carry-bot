"""Piyasa rejimi tespiti - stratejinin çalışmadığı rejimlerde botu durdurur.

NEDEN: `mean_reversion` stratejisi iki şeye muhtaç:
  1) Fiyatların geri dönmesi (negatif otokorelasyon)
  2) Yeterli hareket olması (volatilite) - hareket yoksa TP'ye ulaşılmaz
     ama komisyon+funding yine ödenir

2026'da ikisi de kayboldu ve strateji para kaybetmeye başladı:

  yıl    volatilite   otokorelasyon   yıllık R
  2022      %2.55        -0.173        +67
  2023      %3.65        -0.344       +166
  2024      %4.56        -0.296       +212
  2025      %3.10        -0.230        +91
  2026      %1.25        +0.021        -41   <-- rejim değişti

68 aylık örneklemde ölçülen tahmin gücü (ayın BAŞINDAKİ değer ile
o ayın getirisi - yani gelecek bilgisi kullanılmadan):
  volatilite    -> getiri korelasyonu: +0.643
  otokorelasyon -> getiri korelasyonu: -0.382

EŞİK TESTİ (vol >= 0.020):
  işlem yapılan 53 ay : ortalama +12.80R, toplam +678.3R
  durulan       15 ay : ortalama  -2.06R, toplam  -31.0R
  (filtresiz tüm 68 ay: +647.3R)

Yani bu filtre hem getiriyi artırıyor hem de botu %22 daha az zaman
riske maruz bırakıyor. 2026'nın 8 ayının HEPSİ eşiğin altında -
filtre o yıl boyunca botu durdururdu.

ÖNEMLİ SINIRLAMA: 68 aylık örneklem küçüktür ve eşik (0.020) bu veriye
bakarak seçildi - bir miktar overfitting riski taşır. Ancak mantığı
sağlamdır (hareket yoksa ortalamaya dönüş stratejisi kazanamaz) ve
eşik 0.015-0.025 aralığının tamamında benzer çalışır, yani tek bir
"sihirli sayıya" bağlı değildir.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("bot")


def compute_market_regime(closes_by_symbol: dict, lookback: int = 180) -> dict:
    """Piyasanın mevcut rejimini ölçer (sadece geçmiş veriye bakar).

    closes_by_symbol : {sembol: kapanış fiyatı dizisi}
    lookback         : kaç barlık geçmişe bakılacak (180 bar = ~30 gün @ 4h)

    Döner: {"volatility": float, "autocorrelation": float, "symbols_used": int}
    """
    vols, acs = [], []
    for closes in closes_by_symbol.values():
        s = pd.Series(closes, dtype="float64")
        if len(s) < lookback * 0.5:
            continue
        r = s.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if len(r) < 30 or r.std() == 0:
            continue
        r = r.tail(lookback)
        # uç değerleri kırp - tek bir bozuk tick ölçümü bozmasın
        r = r.clip(r.quantile(0.01), r.quantile(0.99))
        if r.std() == 0:
            continue
        vols.append(float(r.std()))
        ac = r.autocorr(lag=1)
        if np.isfinite(ac):
            acs.append(float(ac))

    return {
        "volatility": float(np.mean(vols)) if vols else float("nan"),
        "autocorrelation": float(np.mean(acs)) if acs else float("nan"),
        "symbols_used": len(vols),
    }


def is_regime_tradeable(regime: dict, min_volatility: float,
                        max_autocorrelation: float,
                        use_autocorr_filter: bool = False):
    """Mevcut rejimde işlem yapılmalı mı? (uygun_mu, sebep) döner.

    Veri yetersizse GÜVENLİ tarafta kalınır: işleme izin verilir ama
    loglanır (aksi halde bot sessizce hiç işlem yapmaz hale gelebilir).
    """
    vol = regime.get("volatility", float("nan"))
    ac = regime.get("autocorrelation", float("nan"))

    if not np.isfinite(vol):
        return True, "rejim ölçülemedi (veri yetersiz) - filtre uygulanmadı"

    if vol < min_volatility:
        return False, (f"volatilite çok düşük ({vol:.4f} < {min_volatility:.4f}) - "
                       f"ortalamaya dönüş stratejisi bu rejimde kaybediyor")

    if use_autocorr_filter and np.isfinite(ac) and ac > max_autocorrelation:
        return False, (f"otokorelasyon çok yüksek ({ac:+.3f} > {max_autocorrelation:+.3f}) - "
                       f"fiyatlar ortalamaya dönmüyor")

    return True, f"rejim uygun (vol={vol:.4f}, otokor={ac:+.3f})"
