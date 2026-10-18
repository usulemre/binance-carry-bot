"""
Trend + Momentum + Hacim kombinasyon stratejisi.

Her coin için 0-4 arası bir puan hesaplanır:
  1) Trend yönü uyumu     (EMA20 vs EMA50)
  2) Fiyat trend üzerinde  (close, ema_fast'a göre konumu)
  3) RSI momentum aralığı uyumu
  4) Hacim spike'ı (son mum hacmi > ortalama * çarpan)

min_signal_score üzerindeki adaylar sinyal olarak kabul edilir.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd

from indicators import compute_all_indicators


@dataclass
class Signal:
    symbol: str
    direction: str          # "LONG" veya "SHORT"
    score: float
    entry_price: float
    atr_value: float
    stop_loss: float
    take_profit: float


def build_signal_from_row(symbol: str, last: pd.Series, strategy_cfg) -> Optional[Signal]:
    """last: compute_all_indicators() çıktısının TEK bir satırı (indikatörler dahil).
    Hem canlı taramada (evaluate_symbol) hem backtest'te (geçmiş her mumda) kullanılır."""
    if pd.isna(last[["ema_fast", "ema_slow", "rsi", "atr", "vol_ma"]]).any():
        return None

    trend_up = last["ema_fast"] > last["ema_slow"]
    trend_down = last["ema_fast"] < last["ema_slow"]
    price_above_fast = last["close"] > last["ema_fast"]
    price_below_fast = last["close"] < last["ema_fast"]
    volume_spike = last["volume"] > (last["vol_ma"] * strategy_cfg.volume_spike_multiplier)

    long_rsi_ok = strategy_cfg.rsi_long_min <= last["rsi"] <= strategy_cfg.rsi_long_max
    short_rsi_ok = strategy_cfg.rsi_short_min <= last["rsi"] <= strategy_cfg.rsi_short_max

    long_score = sum([trend_up, price_above_fast, long_rsi_ok, volume_spike])
    short_score = sum([trend_down, price_below_fast, short_rsi_ok, volume_spike])

    direction = None
    score = 0.0
    if long_score >= strategy_cfg.min_signal_score and long_score >= short_score:
        direction = "LONG"
        score = long_score
    elif short_score >= strategy_cfg.min_signal_score:
        direction = "SHORT"
        score = short_score

    if direction is None:
        return None

    # Üst zaman dilimi teyidi: düşük TF sinyali, büyük resimle çelişmemeli.
    # 2026 Eylül'ün konsolidasyon karakterinde bu, gürültü sinyallerini eler.
    if strategy_cfg.require_htf_confirmation and not pd.isna(last[["htf_ema_fast", "htf_ema_slow"]]).any():
        htf_up = last["htf_ema_fast"] > last["htf_ema_slow"]
        if direction == "LONG" and not htf_up:
            return None
        if direction == "SHORT" and htf_up:
            return None

    if strategy_cfg.require_orderflow_confirmation and "buy_ratio_ma" in last.index \
            and not pd.isna(last["buy_ratio_ma"]):
        if direction == "LONG" and last["buy_ratio_ma"] < strategy_cfg.orderflow_buy_threshold:
            return None
        if direction == "SHORT" and last["buy_ratio_ma"] > (1 - strategy_cfg.orderflow_buy_threshold):
            return None

    entry_price = float(last["close"])
    atr_value = float(last["atr"])
    if not atr_saglikli(entry_price, atr_value):
        return None

    if direction == "LONG":
        stop_loss = entry_price - atr_value * strategy_cfg.atr_sl_multiplier
        take_profit = entry_price + atr_value * strategy_cfg.atr_tp_multiplier
    else:
        stop_loss = entry_price + atr_value * strategy_cfg.atr_sl_multiplier
        take_profit = entry_price - atr_value * strategy_cfg.atr_tp_multiplier

    return Signal(
        symbol=symbol, direction=direction, score=score, entry_price=entry_price,
        atr_value=atr_value, stop_loss=stop_loss, take_profit=take_profit,
    )


def evaluate_symbol(symbol: str, df: pd.DataFrame, strategy_cfg, signal_fn=None) -> Optional[Signal]:
    warmup = max(
        strategy_cfg.ema_slow, strategy_cfg.volume_ma_period, strategy_cfg.atr_period,
        strategy_cfg.donchian_period, strategy_cfg.bb_period, strategy_cfg.adx_period,
    ) + 5
    if len(df) < warmup:
        return None  # yeterli veri yok

    ind = compute_all_indicators(df, strategy_cfg)
    fn = signal_fn or build_signal_from_row
    sig = fn(symbol, ind.iloc[-1], strategy_cfg)
    # SON SAVUNMA: stop-loss çok uzaksa likidasyon riski var (bkz.
    # MAX_SL_DISTANCE_PCT). Her strateji kendi SL'ini hesapladığı için
    # kontrolü burada, tek merkezde yapıyoruz.
    if sig is not None and not sl_mesafesi_kabul_edilebilir(sig.entry_price, sig.stop_loss):
        return None
    return sig


# ATR, fiyatın bu oranını aşarsa sinyal ÜRETİLMEZ.
# Neden: bozuk/aşırı uç bir bar ATR'yi şişirebilir ve saçma stop-loss
# mesafeleri doğurur. Gerçek örnek (2020 verisi): ADAUSDT'de ATR fiyatın
# 59 KATI çıktı, stop-loss girişin %8905 uzağına kondu. Böyle bir
# pozisyon açılırsa risk hesabı tamamen anlamsızlaşır ve kaldıraçlı
# işlemde likidasyona yol açar.
# Veri temizleyici (data_quality.py) fiyatları onarır ama ATR geçmişe
# baktığı için bozuk dönemin etkisi bir süre daha sürer - bu, son
# savunma hattıdır.
MAX_ATR_RATIO = 0.25   # ATR > fiyatın %25'i ise sinyal üretme

# Stop-loss mesafesi bu oranı aşarsa sinyal üretilmez.
# Neden: SL likidasyon mesafesine yaklaşırsa fiyat SL'e ULAŞMADAN
# pozisyon likide olur ve zarar planlanandan büyük olur. Backtest bunu
# modellemez (R cinsinden çalışır), bu yüzden ayrı bir kural gerekiyor.
# config.RISK.leverage=2 iken likidasyon ~%50 uzakta; %20'lik üst sınır
# rahat bir tampon bırakır.
MAX_SL_DISTANCE_PCT = 20.0


def sl_mesafesi_kabul_edilebilir(entry_price: float, stop_loss: float) -> bool:
    """Stop-loss girişe göre çok mu uzak? Uzaksa likidasyon riski var."""
    if not (entry_price > 0):
        return False
    return abs(entry_price - stop_loss) / entry_price * 100 <= MAX_SL_DISTANCE_PCT


def atr_saglikli(entry_price: float, atr_value: float) -> bool:
    """ATR ve fiyat mantıklı mı? Değilse sinyal üretilmemeli.

    TÜM strateji varyantları bunu çağırmalı - her biri kendi stop-loss'unu
    hesapladığı için tek bir yerde kontrol etmek yetmiyor.
    """
    if not (entry_price > 0) or not (atr_value > 0):
        return False
    if not np.isfinite(entry_price) or not np.isfinite(atr_value):
        return False
    return (atr_value / entry_price) <= MAX_ATR_RATIO


def _make_signal(symbol: str, direction: str, score: float, last: pd.Series, strategy_cfg) -> Optional[Signal]:
    entry_price = float(last["close"])
    atr_value = float(last["atr"])
    if not (entry_price > 0) or not (atr_value > 0):
        return None
    if not np.isfinite(entry_price) or not np.isfinite(atr_value):
        return None
    if atr_value / entry_price > MAX_ATR_RATIO:
        # ATR mantıksız derecede büyük - veri bozuk veya piyasa kaotik.
        return None
    if direction == "LONG":
        stop_loss = entry_price - atr_value * strategy_cfg.atr_sl_multiplier
        take_profit = entry_price + atr_value * strategy_cfg.atr_tp_multiplier
    else:
        stop_loss = entry_price + atr_value * strategy_cfg.atr_sl_multiplier
        take_profit = entry_price - atr_value * strategy_cfg.atr_tp_multiplier
    return Signal(symbol=symbol, direction=direction, score=score, entry_price=entry_price,
                  atr_value=atr_value, stop_loss=stop_loss, take_profit=take_profit)


def build_breakout_signal(symbol: str, last: pd.Series, strategy_cfg) -> Optional[Signal]:
    """Donchian kanalı kırılımı + hacim onayı. 'Fiyat son N barın en yükseğini/
    en düşüğünü kırıyor ve bunu güçlü hacim destekliyor' mantığı."""
    if pd.isna(last[["donchian_upper", "donchian_lower", "atr", "vol_ma"]]).any():
        return None
    volume_spike = last["volume"] > (last["vol_ma"] * strategy_cfg.volume_spike_multiplier)
    if not volume_spike:
        return None
    if last["close"] > last["donchian_upper"]:
        return _make_signal(symbol, "LONG", 4.0, last, strategy_cfg)
    if last["close"] < last["donchian_lower"]:
        return _make_signal(symbol, "SHORT", 4.0, last, strategy_cfg)
    return None


def build_mean_reversion_signal(symbol: str, last: pd.Series, strategy_cfg) -> Optional[Signal]:
    """Fiyat Bollinger bandının dışına taştı, RSI aşırı bölgedeydi, VE fiyat
    şimdi banda GERİ DÖNMÜŞ (önceki bar dışarıda, şimdiki bar içeride) ->
    ortalamaya dönüş beklentisiyle pozisyon.

    ÖNEMLİ - iki tasarım kararı:
    1) Kâr hedefi bant ORTASI (bb_mid)'dir, ATR ile uzağa uzatılmış bir hedef
       DEĞİL. Tez "fiyat ortalamaya dönecek" - hedefi ötesine koymak bu tezle
       çelişir.
    2) Giriş, bant kırıldığı ANDA değil, fiyat GERİ DÖNMEYE BAŞLADIĞINDA
       yapılır ("düşen bıçağı yakalama" hatasından kaçınmak için). Bant
       kırılır kırılmaz girmek, fiyat bir mum daha aynı yönde devam ederse
       dar ATR stop'un hemen vurulmasına yol açar."""
    if pd.isna(last[["bb_upper", "bb_lower", "bb_mid", "rsi", "atr",
                       "prev_close", "prev_bb_lower", "prev_bb_upper"]]).any():
        return None

    entry_price = float(last["close"])
    atr_value = float(last["atr"])
    if not atr_saglikli(entry_price, atr_value):
        return None
    bb_mid = float(last["bb_mid"])

    was_below = last["prev_close"] < last["prev_bb_lower"]
    now_recovering = last["close"] >= last["bb_lower"]
    if was_below and now_recovering and last["rsi"] < 45:
        stop_loss = entry_price - atr_value * strategy_cfg.atr_sl_multiplier
        take_profit = bb_mid
        if take_profit <= entry_price:
            return None
        return Signal(symbol=symbol, direction="LONG", score=4.0, entry_price=entry_price,
                      atr_value=atr_value, stop_loss=stop_loss, take_profit=take_profit)

    was_above = last["prev_close"] > last["prev_bb_upper"]
    now_falling_back = last["close"] <= last["bb_upper"]
    if was_above and now_falling_back and last["rsi"] > 55:
        stop_loss = entry_price + atr_value * strategy_cfg.atr_sl_multiplier
        take_profit = bb_mid
        if take_profit >= entry_price:
            return None
        return Signal(symbol=symbol, direction="SHORT", score=4.0, entry_price=entry_price,
                      atr_value=atr_value, stop_loss=stop_loss, take_profit=take_profit)

    return None


def build_extreme_reversal_signal(symbol: str, last: pd.Series, strategy_cfg) -> Optional[Signal]:
    """'Çok yükselene short, çok düşene long': son `extreme_lookback` barda
    fiyat %`extreme_threshold_pct`'ten fazla hareket ettiyse, tersine bir
    pozisyon açılır. Mean-reversion'dan farkı: Bollinger bandı/RSI yerine
    doğrudan ham % hareket eşiğine dayanır - daha agresif, daha az sinyal
    ama potansiyel olarak daha güçlü tükenme (exhaustion) anlarını yakalar.

    Kâr hedefi: hareketin `extreme_retrace_fraction` kadarının geri alınması
    (mean-reversion düzeltmesindeki gibi - hedef gerçekçi olmalı, hareketin
    tamamının tersine dönmesini beklemek değil)."""
    if pd.isna(last[["return_n_pct", "atr"]]).any():
        return None

    entry_price = float(last["close"])
    atr_value = float(last["atr"])
    if not atr_saglikli(entry_price, atr_value):
        return None
    move_pct = last["return_n_pct"]

    if move_pct >= strategy_cfg.extreme_threshold_pct:
        # Çok yükseldi -> SHORT (tükenme/geri çekilme bekle)
        move_amount = entry_price * (move_pct / 100)
        take_profit = entry_price - move_amount * strategy_cfg.extreme_retrace_fraction
        stop_loss = entry_price + atr_value * strategy_cfg.atr_sl_multiplier
        if take_profit >= entry_price:
            return None
        return Signal(symbol=symbol, direction="SHORT", score=4.0, entry_price=entry_price,
                      atr_value=atr_value, stop_loss=stop_loss, take_profit=take_profit)

    if move_pct <= -strategy_cfg.extreme_threshold_pct:
        # Çok düştü -> LONG (tükenme/toparlanma bekle)
        move_amount = entry_price * (abs(move_pct) / 100)
        take_profit = entry_price + move_amount * strategy_cfg.extreme_retrace_fraction
        stop_loss = entry_price - atr_value * strategy_cfg.atr_sl_multiplier
        if take_profit <= entry_price:
            return None
        return Signal(symbol=symbol, direction="LONG", score=4.0, entry_price=entry_price,
                      atr_value=atr_value, stop_loss=stop_loss, take_profit=take_profit)

    return None


# Optimizer ve backtest'in ortak arayüzle çağırabilmesi için isim -> fonksiyon eşlemesi
STRATEGY_VARIANTS = {
    "trend_momentum": build_signal_from_row,
    "breakout": build_breakout_signal,
    "mean_reversion": build_mean_reversion_signal,
    "extreme_reversal": build_extreme_reversal_signal,
    "adaptive": None,  # aşağıda tanımlanıyor, referans için placeholder
}


def build_adaptive_signal_with_regime(symbol: str, last: pd.Series, strategy_cfg):
    """build_adaptive_signal_from_row ile AYNI mantık, ama ayrıca hangi rejimde
    ateşlendiğini de döner: (signal, regime). regime: 'trend', 'range', veya None.
    Hibrit çıkış mantığı (trend'de sabit süre tut, range'de hedefe göre çık)
    için hangi rejimde açıldığını bilmek gerekir."""
    if pd.isna(last[["adx", "vol_zscore", "atr"]]).any():
        return None, None

    if last["vol_zscore"] >= strategy_cfg.vol_extreme_zscore:
        return None, None

    if last["adx"] >= strategy_cfg.adx_trend_threshold:
        if strategy_cfg.trend_persistence_bars > 1 and "adx_trend_persist" in last.index:
            if pd.isna(last["adx_trend_persist"]) or not last["adx_trend_persist"]:
                return None, None  # ADX yeterince uzun süre eşiğin üzerinde kalmamış
        signal = build_signal_from_row(symbol, last, strategy_cfg)
        if signal is None:
            signal = build_breakout_signal(symbol, last, strategy_cfg)
        return signal, ("trend" if signal else None)

    if last["adx"] <= strategy_cfg.adx_range_threshold:
        signal = build_mean_reversion_signal(symbol, last, strategy_cfg)
        return signal, ("range" if signal else None)

    return None, None


def build_adaptive_signal_from_row(symbol: str, last: pd.Series, strategy_cfg) -> Optional[Signal]:
    """Rejim tespiti yapıp DOĞRU strateji tarzını seçer:
      - Aşırı oynaklık (ani çöküş/flaş kriz)  -> HİÇ İŞLEM AÇMA (en güvenli seçim)
      - ADX yüksek (piyasa trend halinde)      -> trend takibi + breakout dene
      - ADX düşük (piyasa yatay/choppy)         -> mean-reversion dene
    Tek bir stratejinin HER rejimde zorla çalıştırılması yerine, her rejimde
    kendi güçlü olduğu alanda çalışmasını sağlar."""
    signal, _ = build_adaptive_signal_with_regime(symbol, last, strategy_cfg)
    return signal


STRATEGY_VARIANTS["adaptive"] = build_adaptive_signal_from_row
