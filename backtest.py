"""
Backtest Motoru (Anahtarsız)
==============================
Stratejiyi gerçek geçmiş Binance Futures verisiyle test eder ve
kazanma oranı, profit factor, maksimum düşüş gibi metrikleri hesaplar.
API anahtarı GEREKTİRMEZ (public endpoint kullanır).

Kullanım:
    python backtest.py                     # varsayılan: en hacimli 15 coin, 1000 mum
    python backtest.py --symbols 10 --limit 1500 --timeframe 1h

ÖNEMLİ - Backtest'in gerçek sınırları:
    - Emirlerin gerçekten dolacağı varsayılır (slippage yok); gerçekte
      özellikle likit olmayan coinlerde gerçekleşen fiyat farklı olabilir.
    - Binance Futures taker komisyonu (giriş+çıkış ~%0.08) DAHİL edilmiştir.
    - Geçmişte iyi çalışan bir strateji gelecekte de iyi çalışacak demek
      DEĞİLDİR. Bu sadece "bu strateji tamamen anlamsız mı, yoksa makul
      bir edge'i var mı" sorusuna kaba bir fikir verir.
"""

import argparse
from dataclasses import dataclass
from typing import List

import pandas as pd

import config
from scanner_public import get_top_symbols, get_klines
from indicators import compute_all_indicators
from strategy import build_signal_from_row


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    exit_reason: str   # "TP", "SL", "EOD" (veri sonu)
    r_multiple: float  # kazanç/kayıp, risk biriminin katı olarak


COMMISSION_PCT_PER_SIDE = 0.04  # Binance Futures taker komisyonu (%). Giriş+çıkış = 2x bu oran.
AVG_FUNDING_PCT_PER_8H = 0.01   # Majör coinlerde tipik ortalama funding oranı (%/8 saat).
                                 # Güçlü trend dönemlerinde bunun kat kat üzerine çıkabilir
                                 # (ör. 2021 bull run'da %0.1-0.3/8h seviyelerine ulaştı).
                                 # Konservatif/basitleştirilmiş: yön farkı gözetmeden her
                                 # pozisyona uygulanır (gerçekte yöne göre alınır/verilir).


def _timeframe_to_minutes(timeframe: str) -> float:
    unit = timeframe[-1]
    value = float(timeframe[:-1])
    return {"m": value, "h": value * 60, "d": value * 1440}.get(unit, value)


def simulate_range(symbol: str, ind: pd.DataFrame, signal_fn, strategy_cfg,
                    entry_start: int, entry_end: int,
                    commission_pct_per_side: float = COMMISSION_PCT_PER_SIDE,
                    timeframe: str = "4h", sl_cooldown_bars: int = 0) -> List[Trade]:
    """Genel amaçlı simülasyon çekirdeği. `ind` indikatörleri ÖNCEDEN hesaplanmış
    TÜM veri setidir. Yeni işlem girişleri sadece [entry_start, entry_end)
    aralığında aranır, ama bir işlem açıldıktan sonra çıkışı (SL/TP) bulmak için
    verinin TAMAMI (aralık dışına taşsa bile) kullanılır — çünkü gerçek hayatta
    bir pozisyon açıldığında geleceği (o an henüz olmamış barları) izlemeye
    devam edersiniz, "test penceresi" sadece bizim değerlendirme için çizdiğimiz
    yapay bir sınırdır.
    """
    trades: List[Trade] = []
    n_total = len(ind)
    i = entry_start

    while i < entry_end:
        row = ind.iloc[i]
        signal = signal_fn(symbol, row, strategy_cfg)

        if signal is None:
            i += 1
            continue

        exit_price = None
        exit_reason = "EOD"
        j = i + 1
        while j < n_total:
            bar = ind.iloc[j]
            if signal.direction == "LONG":
                hit_sl = bar["low"] <= signal.stop_loss
                hit_tp = bar["high"] >= signal.take_profit
            else:
                hit_sl = bar["high"] >= signal.stop_loss
                hit_tp = bar["low"] <= signal.take_profit

            if hit_sl:
                exit_price, exit_reason = signal.stop_loss, "SL"  # ikisi de tetiklenirse muhafazakar varsayım
                break
            elif hit_tp:
                exit_price, exit_reason = signal.take_profit, "TP"
                break
            j += 1

        if exit_price is None:
            exit_price = float(ind.iloc[-1]["close"])
            exit_reason = "EOD"

        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        if signal.direction == "LONG":
            pnl_per_unit = exit_price - signal.entry_price
        else:
            pnl_per_unit = signal.entry_price - exit_price

        # Komisyon: giriş + çıkış, ikisi de işlem fiyatı üzerinden alınır
        commission_cost = signal.entry_price * (commission_pct_per_side / 100) * 2
        pnl_per_unit -= commission_cost

        # Funding maliyeti: pozisyon ne kadar uzun süre açık kaldıysa o kadar
        # 8 saatlik funding periyodu geçmiş demektir.
        bars_held = j - i if j < n_total else n_total - i
        tf_minutes = _timeframe_to_minutes(timeframe)
        funding_periods = (bars_held * tf_minutes) / 480  # 480 dk = 8 saat
        funding_cost = signal.entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * funding_periods
        pnl_per_unit -= funding_cost

        r_multiple = pnl_per_unit / risk_per_unit if risk_per_unit > 0 else 0.0

        trades.append(Trade(
            symbol=symbol, direction=signal.direction, entry_price=signal.entry_price,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit,
            exit_price=exit_price, exit_reason=exit_reason, r_multiple=r_multiple,
        ))

        i = j + 1 if j < n_total else entry_end
        if exit_reason == "SL" and sl_cooldown_bars > 0:
            i += sl_cooldown_bars  # SL sonrası aynı coin'e hemen dönme, whipsaw'dan kaçın

    return trades


def simulate_range_managed(symbol: str, ind: pd.DataFrame, signal_fn, strategy_cfg,
                            entry_start: int, entry_end: int,
                            breakeven_trigger_atr: float, breakeven_buffer_pct: float,
                            partial_tp_r_multiple: float, partial_tp_fraction: float,
                            trailing_atr_multiple: float,
                            commission_pct_per_side: float = COMMISSION_PCT_PER_SIDE,
                            timeframe: str = "4h") -> List[Trade]:
    """simulate_range ile AYNI sinyalleri kullanır, ama çıkışta position_manager.py'daki
    3 aşamalı kâr kilitleme mantığını (breakeven -> kısmi kâr alma -> trailing stop)
    BAR BAR simüle eder. Bu, canlı botun gerçekte yapacağı şeyin geçmiş veride
    bir tahminidir - "kâr kilitleme gerçekten kârı artırıyor mu?" sorusuna cevap
    vermek için simulate_range (basit SL/TP) ile karşılaştırılmalıdır."""
    trades: List[Trade] = []
    n_total = len(ind)
    tf_minutes = _timeframe_to_minutes(timeframe)
    i = entry_start

    while i < entry_end:
        row = ind.iloc[i]
        signal = signal_fn(symbol, row, strategy_cfg)
        if signal is None:
            i += 1
            continue

        entry_price = signal.entry_price
        atr_value = signal.atr_value
        direction = signal.direction
        risk_per_unit = abs(entry_price - signal.stop_loss)
        if risk_per_unit <= 0:
            i += 1
            continue

        current_stop = signal.stop_loss
        take_profit = signal.take_profit
        best_price = entry_price
        breakeven_done = False
        partial_done = False
        remaining_fraction = 1.0
        realized_pnl_per_unit = 0.0
        exit_reason = "EOD"
        j = i + 1
        bars_held_total = 0

        while j < n_total:
            bar = ind.iloc[j]
            bars_held_total = j - i

            if direction == "LONG":
                hit_sl = bar["low"] <= current_stop
                hit_tp = bar["high"] >= take_profit
            else:
                hit_sl = bar["high"] >= current_stop
                hit_tp = bar["low"] <= take_profit

            if hit_sl or hit_tp:
                exit_price = current_stop if hit_sl else take_profit
                exit_reason = "SL" if hit_sl else "TP"
                pnl_chunk = (exit_price - entry_price) if direction == "LONG" else (entry_price - exit_price)
                pnl_chunk *= remaining_fraction
                commission_chunk = (entry_price + exit_price) * (commission_pct_per_side / 100) * remaining_fraction
                funding_chunk = entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held_total * tf_minutes / 480) * remaining_fraction
                realized_pnl_per_unit += pnl_chunk - commission_chunk - funding_chunk
                remaining_fraction = 0.0
                break

            # Tam çıkış yok -> en iyi fiyatı güncelle, kademeleri kontrol et
            if direction == "LONG":
                best_price = max(best_price, bar["high"])
                profit_in_atr = (best_price - entry_price) / atr_value
                profit_in_r = (best_price - entry_price) / risk_per_unit
            else:
                best_price = min(best_price, bar["low"])
                profit_in_atr = (entry_price - best_price) / atr_value
                profit_in_r = (entry_price - best_price) / risk_per_unit

            if not partial_done and profit_in_r >= partial_tp_r_multiple:
                partial_price = entry_price + partial_tp_r_multiple * risk_per_unit if direction == "LONG" \
                    else entry_price - partial_tp_r_multiple * risk_per_unit
                pnl_chunk = (partial_price - entry_price) if direction == "LONG" else (entry_price - partial_price)
                pnl_chunk *= partial_tp_fraction
                commission_chunk = (entry_price + partial_price) * (commission_pct_per_side / 100) * partial_tp_fraction
                funding_chunk = entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held_total * tf_minutes / 480) * partial_tp_fraction
                realized_pnl_per_unit += pnl_chunk - commission_chunk - funding_chunk
                remaining_fraction -= partial_tp_fraction
                partial_done = True

            if not breakeven_done and profit_in_atr >= breakeven_trigger_atr:
                buffer = entry_price * (breakeven_buffer_pct / 100)
                current_stop = entry_price + buffer if direction == "LONG" else entry_price - buffer
                breakeven_done = True

            if breakeven_done:
                if direction == "LONG":
                    trail_sl = best_price - trailing_atr_multiple * atr_value
                    current_stop = max(current_stop, trail_sl)
                else:
                    trail_sl = best_price + trailing_atr_multiple * atr_value
                    current_stop = min(current_stop, trail_sl)

            j += 1

        if remaining_fraction > 0:
            # Veri sonuna gelindi, kalan miktarı son kapanış fiyatından kapat
            final_price = float(ind.iloc[-1]["close"])
            pnl_chunk = (final_price - entry_price) if direction == "LONG" else (entry_price - final_price)
            pnl_chunk *= remaining_fraction
            commission_chunk = (entry_price + final_price) * (commission_pct_per_side / 100) * remaining_fraction
            funding_chunk = entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held_total * tf_minutes / 480) * remaining_fraction
            realized_pnl_per_unit += pnl_chunk - commission_chunk - funding_chunk

        r_multiple = realized_pnl_per_unit / risk_per_unit
        trades.append(Trade(
            symbol=symbol, direction=direction, entry_price=entry_price,
            stop_loss=current_stop, take_profit=take_profit,
            exit_price=best_price, exit_reason=exit_reason, r_multiple=r_multiple,
        ))

        i = j + 1 if j < n_total else entry_end

    return trades


def simulate_time_based_range(symbol: str, ind: pd.DataFrame, signal_fn, strategy_cfg,
                               decision_hour: int, holding_bars: int,
                               commission_pct_per_side: float = COMMISSION_PCT_PER_SIDE,
                               timeframe: str = "4h") -> List[Trade]:
    """'Sabit saatte karar, sabit süre tutma' mantığı: sadece belirli bir
    saatte (ör. 03:00 UTC) yeni pozisyon değerlendirilir. Pozisyon açıldıktan
    sonra `holding_bars` kadar bar boyunca (ör. 3 gün) TUTULUR - ara sinyal
    değişikliklerine bakılmaz. Stop-loss güvenlik ağı olarak hâlâ çalışır
    (sert bir ters harekette sonsuza kadar beklenmez), ama normal koşulda
    çıkış zamana bağlıdır, fiyat hedefine değil.

    `ind` dataframe'i 'date' (datetime) kolonu içermelidir."""
    if "date" not in ind.columns:
        raise ValueError("simulate_time_based_range için 'date' kolonu gereklidir.")

    trades: List[Trade] = []
    n_total = len(ind)
    tf_minutes = _timeframe_to_minutes(timeframe)
    warmup = max(strategy_cfg.ema_slow, strategy_cfg.volume_ma_period, strategy_cfg.atr_period,
                 strategy_cfg.donchian_period, strategy_cfg.bb_period, strategy_cfg.adx_period) + 5
    i = warmup

    while i < n_total:
        row = ind.iloc[i]
        if row["date"].hour != decision_hour:
            i += 1
            continue

        signal = signal_fn(symbol, row, strategy_cfg)
        if signal is None:
            i += 1
            continue

        entry_price = signal.entry_price
        direction = signal.direction
        risk_per_unit = abs(entry_price - signal.stop_loss)
        if risk_per_unit <= 0:
            i += 1
            continue

        exit_price = None
        exit_reason = "TIME"
        j = i + 1
        bars_held = 0
        while j < n_total and bars_held < holding_bars:
            bar = ind.iloc[j]
            if direction == "LONG":
                hit_sl = bar["low"] <= signal.stop_loss
            else:
                hit_sl = bar["high"] >= signal.stop_loss

            if hit_sl:
                exit_price = signal.stop_loss
                exit_reason = "SL"
                break
            bars_held += 1
            j += 1

        if exit_price is None:
            # Süre doldu (veya veri bitti) -> o barın kapanışından çık
            exit_idx = min(j, n_total - 1)
            exit_price = float(ind.iloc[exit_idx]["close"])
            exit_reason = "TIME" if bars_held >= holding_bars else "EOD"

        pnl = (exit_price - entry_price) if direction == "LONG" else (entry_price - exit_price)
        commission = (entry_price + exit_price) * (commission_pct_per_side / 100)
        funding = entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held * tf_minutes / 480)
        r_multiple = (pnl - commission - funding) / risk_per_unit

        trades.append(Trade(
            symbol=symbol, direction=direction, entry_price=entry_price,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit,
            exit_price=exit_price, exit_reason=exit_reason, r_multiple=r_multiple,
        ))

        i = j + 1 if j < n_total else n_total

    return trades


def simulate_adaptive_hybrid_range(symbol: str, ind: pd.DataFrame, strategy_cfg,
                                    entry_start: int, entry_end: int,
                                    trend_holding_bars: int,
                                    commission_pct_per_side: float = COMMISSION_PCT_PER_SIDE,
                                    timeframe: str = "4h") -> List[Trade]:
    """HİBRİT: adaptive'in rejim tespitini kullanır, ama ÇIKIŞ mantığı rejime
    göre değişir:
      - TREND rejiminde ateşlenen sinyal -> SABİT SÜRE tut (time_based_backtest.py
        testinde bu, kazananı sabit bir ATR hedefinde kesmek yerine trendin daha
        büyük kısmını yakaladığı için daha yüksek ortalama R üretti)
      - RANGE (yatay) rejiminde ateşlenen sinyal -> normal HEDEFE GÖRE çık
        (mean-reversion'ın tezi zaten "ortalamaya değince çık" - süre uzatmanın
        mantığı yok, hatta zararlı olabilir)
    Stop-loss HER İKİ modda da güvenlik ağı olarak çalışır."""
    from strategy import build_adaptive_signal_with_regime

    trades: List[Trade] = []
    n_total = len(ind)
    tf_minutes = _timeframe_to_minutes(timeframe)
    i = entry_start

    while i < entry_end:
        row = ind.iloc[i]
        signal, regime = build_adaptive_signal_with_regime(symbol, row, strategy_cfg)
        if signal is None:
            i += 1
            continue

        entry_price = signal.entry_price
        direction = signal.direction
        risk_per_unit = abs(entry_price - signal.stop_loss)
        if risk_per_unit <= 0:
            i += 1
            continue

        exit_price = None
        exit_reason = "EOD"
        j = i + 1
        bars_held = 0

        while j < n_total:
            bar = ind.iloc[j]
            if direction == "LONG":
                hit_sl = bar["low"] <= signal.stop_loss
                hit_tp = bar["high"] >= signal.take_profit
            else:
                hit_sl = bar["high"] >= signal.stop_loss
                hit_tp = bar["low"] <= signal.take_profit

            if hit_sl:
                exit_price, exit_reason = signal.stop_loss, "SL"
                break

            if regime == "range" and hit_tp:
                # Range rejiminde: hedefe ulaşınca hemen çık (mean-reversion tezi)
                exit_price, exit_reason = signal.take_profit, "TP"
                break

            if regime == "trend":
                bars_held += 1
                if bars_held >= trend_holding_bars:
                    # Trend rejiminde: süre doldu, o barın kapanışından çık
                    exit_price, exit_reason = float(bar["close"]), "TIME"
                    break
            j += 1

        if exit_price is None:
            exit_price = float(ind.iloc[-1]["close"])
            exit_reason = "EOD"
            bars_held = (n_total - 1) - i

        pnl = (exit_price - entry_price) if direction == "LONG" else (entry_price - exit_price)
        commission = (entry_price + exit_price) * (commission_pct_per_side / 100)
        funding = entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held * tf_minutes / 480)
        r_multiple = (pnl - commission - funding) / risk_per_unit

        trades.append(Trade(
            symbol=symbol, direction=direction, entry_price=entry_price,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit,
            exit_price=exit_price, exit_reason=exit_reason, r_multiple=r_multiple,
        ))

        i = j + 1 if j < n_total else entry_end

    return trades


def simulate_adaptive_adx_exit_range(symbol: str, ind: pd.DataFrame, strategy_cfg,
                                      entry_start: int, entry_end: int,
                                      max_holding_bars: int = 200,
                                      commission_pct_per_side: float = COMMISSION_PCT_PER_SIDE,
                                      timeframe: str = "4h") -> List[Trade]:
    """Hibrit v2: sabit süre yerine, TREND rejiminde açılan pozisyon "trend
    gerçekten zayıflayana kadar" tutulur - ADX, giriş anındaki trend eşiğinin
    ALTINA düşünce (momentum tükendi demektir) o barın kapanışından çıkılır.
    Bu, önceki hibrit'in sorununu (sabit süre, trendin gerçek uzunluğuyla
    uyuşmuyor, fiyat zirve yapıp geri çekilirken bile beklemeye devam ediyor)
    çözmeyi hedefler. max_holding_bars sadece bir güvenlik sınırıdır (sonsuza
    kadar beklenmesin diye), normal koşulda ADX düşüşü çok daha erken tetikler.
    RANGE rejiminde davranış STANDART adaptive ile aynıdır (hedefe göre çık)."""
    from strategy import build_adaptive_signal_with_regime

    trades: List[Trade] = []
    n_total = len(ind)
    tf_minutes = _timeframe_to_minutes(timeframe)
    i = entry_start

    while i < entry_end:
        row = ind.iloc[i]
        signal, regime = build_adaptive_signal_with_regime(symbol, row, strategy_cfg)
        if signal is None:
            i += 1
            continue

        entry_price = signal.entry_price
        direction = signal.direction
        risk_per_unit = abs(entry_price - signal.stop_loss)
        if risk_per_unit <= 0:
            i += 1
            continue

        exit_price = None
        exit_reason = "EOD"
        j = i + 1
        bars_held = 0

        while j < n_total:
            bar = ind.iloc[j]
            if direction == "LONG":
                hit_sl = bar["low"] <= signal.stop_loss
                hit_tp = bar["high"] >= signal.take_profit
            else:
                hit_sl = bar["high"] >= signal.stop_loss
                hit_tp = bar["low"] <= signal.take_profit

            if hit_sl:
                exit_price, exit_reason = signal.stop_loss, "SL"
                break

            if regime == "range" and hit_tp:
                exit_price, exit_reason = signal.take_profit, "TP"
                break

            if regime == "trend":
                bars_held += 1
                # ADX giriş eşiğinin altına düştü -> trend momentum tükendi, çık
                if bar["adx"] < strategy_cfg.adx_trend_threshold:
                    exit_price, exit_reason = float(bar["close"]), "ADX_FADE"
                    break
                if bars_held >= max_holding_bars:
                    exit_price, exit_reason = float(bar["close"]), "MAX_HOLD"
                    break
            j += 1

        if exit_price is None:
            exit_price = float(ind.iloc[-1]["close"])
            exit_reason = "EOD"
            bars_held = (n_total - 1) - i

        pnl = (exit_price - entry_price) if direction == "LONG" else (entry_price - exit_price)
        commission = (entry_price + exit_price) * (commission_pct_per_side / 100)
        funding = entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held * tf_minutes / 480)
        r_multiple = (pnl - commission - funding) / risk_per_unit

        trades.append(Trade(
            symbol=symbol, direction=direction, entry_price=entry_price,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit,
            exit_price=exit_price, exit_reason=exit_reason, r_multiple=r_multiple,
        ))

        i = j + 1 if j < n_total else entry_end

    return trades


def simulate_symbol(symbol: str, df: pd.DataFrame, strategy_cfg, signal_fn=build_signal_from_row,
                     timeframe: str = "4h") -> List[Trade]:
    """Tek bir coin için, baştan sona tüm veri üzerinde sinyal arar ve simüle eder."""
    ind = compute_all_indicators(df, strategy_cfg)
    warmup = max(
        strategy_cfg.ema_slow, strategy_cfg.volume_ma_period, strategy_cfg.atr_period,
        strategy_cfg.donchian_period, strategy_cfg.bb_period,
    ) + 5
    return simulate_range(symbol, ind, signal_fn, strategy_cfg, warmup, len(ind), timeframe=timeframe)


def compute_metrics(trades: List[Trade]) -> dict:
    """Bir işlem listesinden özet metrikler üretir. Boşsa None döner."""
    if not trades:
        return None
    wins = [t for t in trades if t.r_multiple > 0]
    losses = [t for t in trades if t.r_multiple <= 0]
    total_r = sum(t.r_multiple for t in trades)
    gross_win = sum(t.r_multiple for t in wins)
    gross_loss = abs(sum(t.r_multiple for t in losses))
    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:
        profit_factor = float("inf") if gross_win > 0 else 0.0
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) * 100,
        "total_r": total_r,
        "avg_r": total_r / len(trades),
        "profit_factor": profit_factor,
    }


def summarize(trades: List[Trade]):
    m = compute_metrics(trades)
    if not m:
        print("Hiç işlem üretilmedi. min_signal_score çok yüksek olabilir veya veri yetersiz.")
        return

    equity = [0.0]
    for t in trades:
        equity.append(equity[-1] + t.r_multiple)
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)

    print("\n" + "=" * 60)
    print("BACKTEST SONUÇLARI (birim: R = risk edilen tutarın katı)")
    print("=" * 60)
    print(f"Toplam işlem       : {m['trades']}")
    print(f"Kazanan / Kaybeden : {m['wins']} / {m['losses']}")
    print(f"Kazanma oranı      : %{m['win_rate']:.1f}")
    print(f"Ortalama R         : {m['avg_r']:+.2f}")
    print(f"Toplam R           : {m['total_r']:+.2f}")
    print(f"Profit factor      : {m['profit_factor']:.2f}  (>1 kâr, <1 zarar demektir)")
    print(f"Maksimum düşüş     : -{max_dd:.2f}R")
    print("=" * 60)
    print("NOT: Binance taker komisyonu ve ortalama funding maliyeti dahil edilmiştir.")
    print("Slippage dahil değildir, likit olmayan coinlerde gerçek sonuç biraz")
    print("daha zayıf olabilir. Profit factor 1.3'ün altındaysa strateji")
    print("gerçekte muhtemelen kazandırmaz.")

    print("\nCoin bazlı özet:")
    by_symbol = {}
    for t in trades:
        by_symbol.setdefault(t.symbol, []).append(t.r_multiple)
    for sym, rs in sorted(by_symbol.items(), key=lambda kv: -sum(kv[1])):
        wr = sum(1 for r in rs if r > 0) / len(rs) * 100
        print(f"  {sym:<12} işlem={len(rs):<4} toplamR={sum(rs):+.2f}  kazanma=%{wr:.0f}")


def run_backtest(top_n: int, limit: int, timeframe: str):
    print(f"Backtest başlıyor: en hacimli {top_n} coin, {limit} mum, {timeframe} periyot...")
    symbols = get_top_symbols(config.SCAN.quote_asset, top_n, config.SCAN.excluded_symbols)

    all_trades: List[Trade] = []
    for symbol in symbols:
        try:
            df = get_klines(symbol, timeframe, limit)
            trades = simulate_symbol(symbol, df, config.STRATEGY, timeframe=timeframe)
            all_trades.extend(trades)
            print(f"  {symbol}: {len(trades)} işlem simüle edildi")
        except Exception as e:
            print(f"  {symbol}: hata - {e}")

    summarize(all_trades)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anahtarsız strateji backtest'i")
    parser.add_argument("--symbols", type=int, default=15, help="Kaç coin test edilecek")
    parser.add_argument("--limit", type=int, default=1000, help="Coin başına kaç mum çekilecek (max ~1500)")
    parser.add_argument("--timeframe", type=str, default=config.SCAN.timeframe, help="Mum periyodu (örn. 15m, 1h, 4h)")
    args = parser.parse_args()
    run_backtest(args.symbols, args.limit, args.timeframe)
