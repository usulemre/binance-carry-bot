"""
Çoklu Coin Portföy Backtest'i (Korelasyon Farkındalıklı)
=============================================================
Mevcut backtest.py, her coini BAĞIMSIZ simüle eder ve sonuçları toplar.
Bu, gerçek bir zayıflığı gizler: bot aynı anda 4 pozisyon açtığında
(max_concurrent_positions=4), bu 4 coin piyasa çöküşünde genelde birlikte
hareket eder (yüksek korelasyon) - yani "4 çeşitlendirilmiş bahis" değil,
"aynı bahsin 4 katı büyüklüğü" olabilir. Bu script bunu gerçek zamanlı
(bar bar, TÜM coinler aynı anda) simüle eder ve bir KORELASYON FİLTRESİ
ekler: zaten açık bir pozisyonla yüksek korelasyonlu yeni bir sinyal
varsa, o sinyal ATLANIR.

Kullanım:
    python portfolio_backtest.py --symbols 15 --limit 1500 --timeframe 4h --strategy adaptive
    python portfolio_backtest.py ... --no-correlation-filter   # filtresiz karşılaştırma için
"""

import argparse
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

import config
from scanner_public import get_top_symbols, get_klines
from indicators import compute_all_indicators
from strategy import STRATEGY_VARIANTS
from backtest import COMMISSION_PCT_PER_SIDE, AVG_FUNDING_PCT_PER_8H, _timeframe_to_minutes

# SLIPPAGE VARSAYILANLARI (%)
# Sıfır slippage varsaymak gerçekçi değil - emirler tam istenen fiyattan
# dolmaz. "Gerçekçi (tipik altcoin)" senaryosu varsayılan alındı.
# Ölçülen duyarlılık (mean_reversion, 2020-2026, 14 coin, max 4 pozisyon):
#   slippage yok        : +1046.72R
#   iyimser  (.01/.03)  : +1032.91R
#   gerçekçi (.02/.05)  : +1021.69R   <- varsayılan
#   kötümser (.03/.10)  : +1002.67R
#   stres    (.05/.20)  :  +964.63R
# Strateji slippage'a dayanıklı çıktı (en kötü senaryoda bile %8 kayıp),
# çünkü işlemlerin ~%68'i TP'den (limit emir, kayma yok) çıkıyor.
DEFAULT_ENTRY_SLIPPAGE_PCT = 0.02  # piyasa emri girişi, hafif aleyhte kayar
DEFAULT_SL_SLIPPAGE_PCT = 0.05     # stop-market: tetiklenince aleyhte kayar, en kötü anda


@dataclass
class OpenPosition:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    atr_value: float
    entry_bar: int
    # Kademeli azaltma devredeyse pozisyon küçültülerek açılır; R sonucu
    # da orantılı küçülür. 1.0 = tam boyut.
    size_scale: float = 1.0


@dataclass
class ClosedTrade:
    symbol: str
    r_multiple: float
    exit_bar: int
    direction: str = ""   # "LONG" / "SHORT" - yon bazli analiz icin
    entry_bar: int = -1


def run_portfolio_backtest(symbol_data: dict, strategy_name: str, max_concurrent: int,
                            correlation_filter: bool, correlation_threshold: float,
                            correlation_lookback: int, timeframe: str,
                            entry_slippage_pct: float = DEFAULT_ENTRY_SLIPPAGE_PCT,
                            sl_slippage_pct: float = DEFAULT_SL_SLIPPAGE_PCT,
                            exec_lag: int = 1,
                            drawdown_scale_r: float = None,
                            max_hold_bars: int = None,
                            strategy_cfg=None):
    """...

    ÖNEMLİ - CANLI BOTLA PARİTE:
    drawdown_scale_r ve max_hold_bars VARSAYILAN None ama canlı bot
    ikisini de KULLANIYOR. Gerçekçi sonuç için config'deki değerleri
    geçirin:
        run_portfolio_backtest(..., drawdown_scale_r=config.DRAWDOWN_SCALE_FULL_R,
                               max_hold_bars=int(config.MAX_HOLD_DAYS*6))
    Etki ölçüldü (temiz veri, extreme_reversal):
        ikisi de yok : +888.5R, max düşüş -61.2R
        tam parite   : +852.9R, max düşüş -27.4R
    Kademeli azaltma düşüşü YARIYA indiriyor - parite olmadan risk
    olduğundan büyük görünür.
    """
    """symbol_data: {symbol: indikatörlü DataFrame (aynı bar sayısına hizalanmış)}

    strategy_cfg: sinyal üretiminde kullanılacak strateji ayarları.
    None ise config.STRATEGY kullanılır.

    SEMBOL SIRASI SONUCU ETKİLER (±%3 belirsizlik):
    Slot limiti dolunca sonraki sinyaller elenir, yani hangi sembolün
    ÖNCE tarandığı sonucu değiştirir. Ölçüldü: sembol sırası ters
    çevrilince 262.38R -> 253.08R (%3.5 fark).
    Bu gerçek bir davranış (canlı botta da aynı - önce gelen sinyal
    slotu alır) ama backtest rakamlarında ±%3 gürültü demek.
    Küçük farkları (%1-2) anlamlı kabul etmeyin.

    DİKKAT - PARAMETRE TARAMASI YAPARKEN: Bu fonksiyon eskiden HER ZAMAN
    global config.STRATEGY kullanıyordu. Yani çağıran taraf indikatörleri
    farklı bir cfg ile hesaplasa bile SİNYAL ÜRETİMİ global ayarlarla
    yapılıyordu - eşik/ATR taramaları sessizce ETKİSİZ kalıyordu
    (tüm değerler aynı sonucu veriyordu). Tarama yaparken hem
    compute_all_indicators'a hem buraya AYNI cfg'yi geçirin.
    """
    signal_fn = STRATEGY_VARIANTS[strategy_name]
    cfg = strategy_cfg if strategy_cfg is not None else config.STRATEGY
    tf_minutes = _timeframe_to_minutes(timeframe)

    symbols = list(symbol_data.keys())
    n_bars = min(len(df) for df in symbol_data.values())
    warmup = 60

    # Getiri geçmişi (korelasyon hesabı için)
    returns = {s: symbol_data[s]["close"].pct_change().values for s in symbols}

    open_positions: dict = {}
    closed_trades: list = []
    rejected_for_correlation = 0
    max_correlated_cluster = 0  # aynı anda açık, birbiriyle yüksek korelasyonlu pozisyon sayısı
    equity_curve = [0.0]

    def rolling_correlation(sym_a: str, sym_b: str, bar_idx: int) -> float:
        start = max(0, bar_idx - correlation_lookback)
        ra = returns[sym_a][start:bar_idx]
        rb = returns[sym_b][start:bar_idx]
        if len(ra) < correlation_lookback // 2:
            return 0.0
        mask = ~(np.isnan(ra) | np.isnan(rb))
        if mask.sum() < 10:
            return 0.0
        ra_m, rb_m = ra[mask], rb[mask]
        if np.std(ra_m) == 0 or np.std(rb_m) == 0:
            return 0.0
        corr = np.corrcoef(ra_m, rb_m)[0, 1]
        return 0.0 if np.isnan(corr) else corr

    pending_entries = []   # (uygulama_bari, sembol, sinyal)
    peak_r = 0.0           # kademeli azaltma için tepe takibi

    for bar_idx in range(warmup, n_bars):
        # KADEMELİ EXPOSURE AZALTMA (canlı bottaki USE_DRAWDOWN_SCALING).
        # Tepe R'den düşüş arttıkça yeni pozisyonlar küçültülür, eşiğe
        # ulaşınca hiç açılmaz. Mevcut pozisyonlar etkilenmez.
        cur_r = sum(t.r_multiple for t in closed_trades)
        peak_r = max(peak_r, cur_r)
        exposure_scale = 1.0
        if drawdown_scale_r:
            exposure_scale = max(0.0, min(1.0, 1.0 - (peak_r - cur_r) / drawdown_scale_r))
        # Gecikmeli girişleri uygula
        if pending_entries:
            still = []
            for (ebar, esym, esig) in pending_entries:
                if ebar != bar_idx:
                    still.append((ebar, esym, esig))
                    continue
                if esym in open_positions or len(open_positions) >= max_concurrent:
                    continue
                if exposure_scale <= 0.01:
                    continue    # düşüş çok büyük - yeni pozisyon açma
                fill = float(symbol_data[esym].iloc[bar_idx]["open"])
                # SL/TP seviyeleri de yeni giriş fiyatına KAYDIRILMALI; aksi
                # halde eski fiyata göre hesaplanmış seviyeler kalır ve
                # risk/ödül oranı bozulup sonucu YANLIŞ yönde şişirir.
                shift = fill - esig.entry_price
                open_positions[esym] = OpenPosition(
                    symbol=esym, direction=esig.direction, entry_price=fill,
                    stop_loss=esig.stop_loss + shift, take_profit=esig.take_profit + shift,
                    atr_value=esig.atr_value, entry_bar=bar_idx,
                    size_scale=exposure_scale,
                )
            pending_entries = still
        # 1) Açık pozisyonları yönet (SL/TP kontrolü)
        for symbol in list(open_positions.keys()):
            pos = open_positions[symbol]
            bar = symbol_data[symbol].iloc[bar_idx]
            if pos.direction == "LONG":
                hit_sl = bar["low"] <= pos.stop_loss
                hit_tp = bar["high"] >= pos.take_profit
            else:
                hit_sl = bar["high"] >= pos.stop_loss
                hit_tp = bar["low"] <= pos.take_profit

            # MAKSİMUM TUTMA SÜRESİ (canlı bottaki USE_MAX_HOLD).
            # Süre dolunca pozisyon bar kapanışında kapatılır.
            sure_doldu = (max_hold_bars is not None
                          and (bar_idx - pos.entry_bar) >= max_hold_bars)

            if hit_sl or hit_tp or sure_doldu:
                if sure_doldu and not (hit_sl or hit_tp):
                    raw_exit = float(bar["close"])
                else:
                    raw_exit = pos.stop_loss if hit_sl else pos.take_profit
                # SLIPPAGE: gerçekte emirler tam istenen fiyattan dolmaz.
                # - SL (stop-market): tetiklenince piyasa emrine döner ve
                #   genelde ALEYHTE kayar - hem de en kötü anda (sert hareket,
                #   ince emir defteri). Bu yüzden SL slippage'ı daha yüksek
                #   varsayılır.
                # - TP (limit): lehte kayma olmaz, en iyi ihtimalle tam dolar,
                #   bazen hiç dolmaz. Muhafazakâr olarak sıfır kayma alınır
                #   ama komisyon zaten düşülür.
                # - Giriş: piyasa emri, hafif aleyhte kayar.
                if hit_sl:
                    slip = raw_exit * (sl_slippage_pct / 100)
                    exit_price = raw_exit - slip if pos.direction == "LONG" else raw_exit + slip
                else:
                    exit_price = raw_exit
                # Girişteki kayma da aleyhte
                entry_slip = pos.entry_price * (entry_slippage_pct / 100)
                eff_entry = pos.entry_price + entry_slip if pos.direction == "LONG" else pos.entry_price - entry_slip

                risk_per_unit = abs(pos.entry_price - pos.stop_loss)
                pnl = (exit_price - eff_entry) if pos.direction == "LONG" else (eff_entry - exit_price)
                commission = (pos.entry_price + exit_price) * (COMMISSION_PCT_PER_SIDE / 100)
                bars_held = bar_idx - pos.entry_bar
                funding = pos.entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held * tf_minutes / 480)
                r_multiple = (pnl - commission - funding) / risk_per_unit if risk_per_unit > 0 else 0.0
                # Pozisyon kademeli azaltmayla küçültülmüşse R de orantılı küçülür
                r_multiple *= pos.size_scale
                closed_trades.append(ClosedTrade(symbol, r_multiple, bar_idx, pos.direction, pos.entry_bar))
                equity_curve.append(equity_curve[-1] + r_multiple)
                del open_positions[symbol]

        # 2) Şu an açık pozisyonlar arasındaki en büyük "korelasyon kümesi"ni kaydet
        if len(open_positions) >= 2:
            syms = list(open_positions.keys())
            cluster_size = 1
            for a_idx in range(len(syms)):
                count = 1
                for b_idx in range(len(syms)):
                    if a_idx != b_idx and abs(rolling_correlation(syms[a_idx], syms[b_idx], bar_idx)) >= correlation_threshold:
                        count += 1
                cluster_size = max(cluster_size, count)
            max_correlated_cluster = max(max_correlated_cluster, cluster_size)

        # 3) Yeni sinyal ara (slot varsa)
        if len(open_positions) < max_concurrent:
            for symbol in symbols:
                if symbol in open_positions or len(open_positions) >= max_concurrent:
                    continue
                row = symbol_data[symbol].iloc[bar_idx]
                signal = signal_fn(symbol, row, cfg)
                if signal is None:
                    continue

                if correlation_filter and open_positions:
                    too_correlated = any(
                        abs(rolling_correlation(symbol, open_sym, bar_idx)) >= correlation_threshold
                        for open_sym in open_positions
                    )
                    if too_correlated:
                        rejected_for_correlation += 1
                        continue

                if exec_lag <= 0:
                    open_positions[symbol] = OpenPosition(
                        symbol=symbol, direction=signal.direction, entry_price=signal.entry_price,
                        stop_loss=signal.stop_loss, take_profit=signal.take_profit,
                        atr_value=signal.atr_value, entry_bar=bar_idx,
                    )
                else:
                    # UYGULAMA GECİKMESİ: sinyali bar kapanışında görürsünüz,
                    # emri bir sonraki barın AÇILIŞINDA doldurursunuz.
                    pending_entries.append((bar_idx + exec_lag, symbol, signal))

    # DÖNEM SONU: hâlâ açık olan pozisyonları son kapanış fiyatından kapat.
    # Bunu yapmamak ciddi bir hataydı: uzun süre açık kalan pozisyonlar
    # (özellikle geniş TP hedefi olan stratejilerde) sonuçlara HİÇ
    # yansımıyordu - ne kârı ne zararı. Bu, hem toplam R'yi hem işlem
    # sayısını çarpıtıyor, ve en kötüsü: açıkta kalan ZARARLAR gizleniyordu.
    # Ölçülen etki: extreme_reversal tüm dönemde 432 işlem gösteriyordu,
    # ama ay ay bölününce 2474 işlem çıkıyordu (2042 işlem "kayboluyordu").
    for symbol, pos in list(open_positions.items()):
        last_bar = symbol_data[symbol].iloc[n_bars - 1]
        exit_price = float(last_bar["close"])
        entry_slip = pos.entry_price * (entry_slippage_pct / 100)
        eff_entry = pos.entry_price + entry_slip if pos.direction == "LONG" else pos.entry_price - entry_slip
        risk_per_unit = abs(pos.entry_price - pos.stop_loss)
        pnl = (exit_price - eff_entry) if pos.direction == "LONG" else (eff_entry - exit_price)
        commission = (pos.entry_price + exit_price) * (COMMISSION_PCT_PER_SIDE / 100)
        bars_held = (n_bars - 1) - pos.entry_bar
        funding = pos.entry_price * (AVG_FUNDING_PCT_PER_8H / 100) * (bars_held * tf_minutes / 480)
        r_multiple = (pnl - commission - funding) / risk_per_unit if risk_per_unit > 0 else 0.0
        closed_trades.append(ClosedTrade(symbol, r_multiple, n_bars - 1, pos.direction, pos.entry_bar))
        equity_curve.append(equity_curve[-1] + r_multiple)
    open_positions.clear()

    total_r = sum(t.r_multiple for t in closed_trades)
    wins = sum(1 for t in closed_trades if t.r_multiple > 0)
    peak, max_dd = equity_curve[0], 0.0
    for v in equity_curve:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)

    return {
        "trades": len(closed_trades),
        "wins": wins,
        "win_rate": (wins / len(closed_trades) * 100) if closed_trades else 0.0,
        "total_r": total_r,
        "max_drawdown_r": max_dd,
        "rejected_for_correlation": rejected_for_correlation,
        "max_correlated_cluster": max_correlated_cluster,
        "closed_trades": closed_trades,
    }


def main():
    parser = argparse.ArgumentParser(description="Çoklu coin, korelasyon farkındalıklı portföy backtest'i")
    parser.add_argument("--symbols", type=int, default=15)
    parser.add_argument("--limit", type=int, default=1500)
    parser.add_argument("--timeframe", type=str, default="4h")
    parser.add_argument("--strategy", type=str, default="mean_reversion", choices=list(STRATEGY_VARIANTS.keys()))
    parser.add_argument("--correlation-threshold", type=float, default=0.7)
    parser.add_argument("--correlation-lookback", type=int, default=50)
    parser.add_argument("--no-correlation-filter", action="store_true")
    parser.add_argument("--entry-slippage", type=float, default=DEFAULT_ENTRY_SLIPPAGE_PCT,
                        help="Giris emri slippage %% (varsayilan: %(default)s)")
    parser.add_argument("--sl-slippage", type=float, default=DEFAULT_SL_SLIPPAGE_PCT,
                        help="Stop-loss slippage %% (varsayilan: %(default)s)")
    parser.add_argument("--local-data", action="store_true",
                        help="Canlı API yerine historical_data/ içindeki indirilmiş "
                             "CSV'leri kullan (uzun vadeli, 2020-2026 test için; ayrıca "
                             "API'nin erişilemediği ortamlarda çalışır)")
    args = parser.parse_args()

    symbol_data = {}
    if args.local_data:
        from backtest_yearly import load_all_csvs
        print(f"Yerel veri yükleniyor: historical_data/*_{args.timeframe}.csv ...")
        raw = load_all_csvs(args.timeframe)
        for symbol, df in raw.items():
            symbol_data[symbol] = compute_all_indicators(df, config.STRATEGY)
    else:
        print(f"Veri çekiliyor: en hacimli {args.symbols} coin, {args.limit} mum, {args.timeframe}...")
        symbols = get_top_symbols(config.SCAN.quote_asset, args.symbols, config.SCAN.excluded_symbols)
        for symbol in symbols:
            try:
                df = get_klines(symbol, args.timeframe, args.limit)
                symbol_data[symbol] = compute_all_indicators(df, config.STRATEGY)
            except Exception as e:
                print(f"  {symbol}: hata - {e}")
    print(f"{len(symbol_data)} coin için veri hazır.\n")

    for use_filter in ([False, True] if not args.no_correlation_filter else [False]):
        label = "KORELASYON FİLTRESİ VAR" if use_filter else "KORELASYON FİLTRESİ YOK"
        print(f"\n{'='*60}\n{label}\n{'='*60}")
        result = run_portfolio_backtest(
            symbol_data, args.strategy, config.RISK.max_concurrent_positions,
            correlation_filter=use_filter, correlation_threshold=args.correlation_threshold,
            correlation_lookback=args.correlation_lookback, timeframe=args.timeframe,
            entry_slippage_pct=args.entry_slippage, sl_slippage_pct=args.sl_slippage,
        )
        print(f"Toplam işlem       : {result['trades']}")
        print(f"Kazanma oranı      : %{result['win_rate']:.1f}")
        print(f"Toplam R           : {result['total_r']:+.2f}")
        print(f"Maksimum düşüş     : -{result['max_drawdown_r']:.2f}R")
        print(f"Korelasyon nedeniyle atlanan sinyal: {result['rejected_for_correlation']}")
        print(f"En büyük eşzamanlı KORELASYONLU pozisyon kümesi: {result['max_correlated_cluster']}")
        print(f"  (Bu sayı = piyasa aleyhe tek bir hareket yaptığında, ANINDA kaybedilebilecek")
        print(f"   maksimum R miktarı. Sıralı 'max_drawdown' metriği bunu YAKALAMAZ çünkü o,")
        print(f"   işlemler zamanla teker teker kapandığı varsayımıyla hesaplanır - ama korelasyonlu")
        print(f"   pozisyonlar aynı anda, aynı yönde kaybedebilir.)")


if __name__ == "__main__":
    main()
