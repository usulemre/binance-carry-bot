"""Teknik indikatör hesaplamaları (harici TA kütüphanesi olmadan, pandas ile)."""

import pandas as pd
import numpy as np


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    # SIFIRA BÖLME - dikkatli ele alınmalı, çünkü üç farklı durum var:
    #   avg_loss = 0, avg_gain > 0  -> hiç kayıp yok, RSI = 100 (aşırı alım)
    #   avg_gain = 0, avg_loss > 0  -> hiç kazanç yok, RSI = 0   (aşırı satım)
    #   ikisi de 0 (düz fiyat)      -> RSI = 50 (nötr)
    # ESKİ KOD HATALIYDI: avg_loss=0 durumunda NaN üretip fillna(50) ile
    # 50'ye çeviriyordu. Yani KESİNTİSİZ YÜKSELİŞ dönemlerinde RSI 50
    # gösteriyor, aşırı alım sinyalini TAMAMEN kaçırıyordu.
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))

    kayip_yok = (avg_loss.fillna(0) == 0)
    kazanc_yok = (avg_gain.fillna(0) == 0)
    result = result.mask(kayip_yok & ~kazanc_yok, 100.0)   # sadece yükseliş
    result = result.mask(kazanc_yok & ~kayip_yok, 0.0)     # sadece düşüş
    result = result.mask(kayip_yok & kazanc_yok, 50.0)     # düz fiyat
    # Isınma dönemi (min_periods dolmadan) hâlâ NaN -> nötr 50
    return result.fillna(50)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """df: 'high', 'low', 'close' kolonlarını içermeli."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def volume_ma(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(window=period).mean()


def donchian_channels(df: pd.DataFrame, period: int):
    """Önceki `period` bar'ın en yüksek/en düşük seviyesi (mevcut bar HARİÇ,
    shift(1) ile - aksi halde bar kendi kendini kırıyor gibi görünür, lookahead olur)."""
    upper = df["high"].rolling(window=period).max().shift(1)
    lower = df["low"].rolling(window=period).min().shift(1)
    return upper, lower


def bollinger_bands(series: pd.Series, period: int, num_std: float):
    mid = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def adx(df: pd.DataFrame, period: int = 14):
    """Average Directional Index: trend GÜCÜNÜ ölçer (yön değil).
    ADX > ~25 -> piyasa trend halinde. ADX < ~20 -> yatay/choppy piyasa.
    Bu ayrım, hangi strateji tarzının (trend takibi vs mean-reversion)
    o an mantıklı olduğunu seçmek için kullanılır."""
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)
    plus_mask = (up_move > down_move) & (up_move > 0)
    minus_mask = (down_move > up_move) & (down_move > 0)
    plus_dm[plus_mask] = up_move[plus_mask]
    minus_dm[minus_mask] = down_move[minus_mask]

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low, (high - prev_close).abs(), (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr_smooth = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr_smooth.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr_smooth.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return plus_di.fillna(0), minus_di.fillna(0), adx_val.fillna(0)


def volatility_zscore(atr_series: pd.Series, close_series: pd.Series, lookback: int = 100):
    """ATR'yi fiyata oranlayıp (atr_pct), son `lookback` bara göre z-score'unu
    hesaplar. Yüksek z-score (ör. >2) = 'şu an normalden çok daha oynak piyasa'
    (ör. ani çöküş/flaş kriz) -> pozisyon riskini azaltmak veya işlem açmamak
    için sinyal."""
    atr_pct = atr_series / close_series
    rolling_mean = atr_pct.rolling(window=lookback, min_periods=lookback // 2).mean()
    rolling_std = atr_pct.rolling(window=lookback, min_periods=lookback // 2).std()
    zscore = (atr_pct - rolling_mean) / rolling_std.replace(0, np.nan)
    return atr_pct, zscore.fillna(0)


def compute_all_indicators(df: pd.DataFrame, strategy_cfg) -> pd.DataFrame:
    """df: 'open','high','low','close','volume' kolonlarını içeren OHLCV dataframe."""
    out = df.copy()
    out["ema_fast"] = ema(out["close"], strategy_cfg.ema_fast)
    out["ema_slow"] = ema(out["close"], strategy_cfg.ema_slow)
    out["rsi"] = rsi(out["close"], strategy_cfg.rsi_period)
    out["atr"] = atr(out, strategy_cfg.atr_period)
    out["vol_ma"] = volume_ma(out["volume"], strategy_cfg.volume_ma_period)
    out["donchian_upper"], out["donchian_lower"] = donchian_channels(out, strategy_cfg.donchian_period)
    out["bb_upper"], out["bb_mid"], out["bb_lower"] = bollinger_bands(
        out["close"], strategy_cfg.bb_period, strategy_cfg.bb_std_dev
    )
    out["plus_di"], out["minus_di"], out["adx"] = adx(out, strategy_cfg.adx_period)
    out["atr_pct"], out["vol_zscore"] = volatility_zscore(out["atr"], out["close"], strategy_cfg.vol_lookback)
    out["prev_close"] = out["close"].shift(1)
    out["prev_bb_lower"] = out["bb_lower"].shift(1)
    out["prev_bb_upper"] = out["bb_upper"].shift(1)
    # Üst zaman dilimi (higher timeframe) trend YAKLAŞIMI: aynı seri üzerinde
    # normal periyodun katı kadar uzun EMA'lar kullanarak "büyük resmi" tahmin
    # eder (gerçek üst TF verisi çekmeye gerek kalmadan, tutarlı ve hızlı).
    mult = strategy_cfg.htf_multiplier
    out["htf_ema_fast"] = ema(out["close"], strategy_cfg.ema_fast * mult)
    out["htf_ema_slow"] = ema(out["close"], strategy_cfg.ema_slow * mult)
    out["return_n_pct"] = out["close"].pct_change(periods=strategy_cfg.extreme_lookback) * 100
    if "taker_buy_base" in out.columns:
        # Order flow proxy: bu mumdaki hacmin ne kadarı ALICI tarafından
        # başlatıldı (taker buy). >0.5 = alıcı baskın, <0.5 = satıcı baskın.
        out["buy_ratio"] = (out["taker_buy_base"] / out["volume"]).clip(0, 1)
        out["buy_ratio_ma"] = out["buy_ratio"].rolling(window=10, min_periods=5).mean()

    n_persist = strategy_cfg.trend_persistence_bars
    is_trending = out["adx"] >= strategy_cfg.adx_trend_threshold
    out["adx_trend_persist"] = is_trending.rolling(window=n_persist, min_periods=n_persist).min().astype(bool)
    return out
