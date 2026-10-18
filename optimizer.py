"""
Walk-Forward Edge Arayıcı (Anahtarsız)
==========================================
"En iyi backtest sonucunu bulana kadar parametre dene" yaklaşımı
OVERFITTING'e yol açar: yeterince kombinasyon denersen, geçmişte
tesadüfen harika görünen ama ileride hiçbir işe yaramayan bir sonuç
bulman garantidir.

Bu script bunun yerine WALK-FORWARD doğrulama yapar:
  1. Veri kronolojik olarak N parçaya (fold) bölünür.
  2. Her fold için: parametreler SADECE önceki (train) veride aranır.
  3. En iyi parametre seti, HİÇ GÖRMEDİĞİ bir sonraki (test/out-of-sample)
     fold'da değerlendirilir.
  4. Tüm fold'ların out-of-sample sonuçları birleştirilir.

Bir strateji sadece "train"de değil, hiç görmediği "test" verisinde de
tutarlı çalışıyorsa, bu gerçek bir edge adayıdır. Sadece train'de iyi
görünmesi hiçbir şey ifade etmez (ezber/overfitting olabilir).

3 farklı strateji tarzı birbirine karşı yarıştırılır:
  - trend_momentum : EMA trend + RSI momentum + hacim
  - breakout       : Donchian kanal kırılımı + hacim
  - mean_reversion : Bollinger band + RSI aşırı bölge (ortalamaya dönüş)

Kullanım:
    python optimizer.py --symbols 15 --limit 1500 --timeframe 4h --folds 4
"""

import argparse
import itertools
from dataclasses import replace

import config
from scanner_public import get_top_symbols, get_klines
from indicators import compute_all_indicators
from strategy import STRATEGY_VARIANTS
from backtest import simulate_range, compute_metrics

PARAM_GRIDS = {
    "trend_momentum": {
        "atr_sl_multiplier": [1.0, 1.5, 2.0],
        "atr_tp_multiplier": [2.0, 3.0],
        "volume_spike_multiplier": [1.1, 1.3],
        "min_signal_score": [3, 4],
    },
    "breakout": {
        "donchian_period": [10, 20, 30],
        "atr_sl_multiplier": [1.0, 1.5],
        "atr_tp_multiplier": [2.0, 3.0],
        "volume_spike_multiplier": [1.1, 1.3],
    },
    "mean_reversion": {
        "bb_period": [14, 20],
        "bb_std_dev": [1.5, 2.0],
        "rsi_oversold": [25, 30],
        "rsi_overbought": [70, 75],
        "atr_sl_multiplier": [1.0, 1.5],
        "atr_tp_multiplier": [1.5, 2.0],
    },
    "adaptive": {
        "adx_trend_threshold": [20, 25, 30],
        "adx_range_threshold": [15, 20],
        "vol_extreme_zscore": [1.5, 2.0, 2.5],
        "atr_sl_multiplier": [1.0, 1.5],
        "atr_tp_multiplier": [2.0, 3.0],
    },
    "extreme_reversal": {
        "extreme_lookback": [10, 20, 30],
        "extreme_threshold_pct": [10.0, 15.0, 20.0],
        "extreme_retrace_fraction": [0.3, 0.4, 0.5],
        "atr_sl_multiplier": [1.5, 2.0],
    },
}

WARMUP = 60  # tüm indikatörler için güvenli ısınma periyodu (bar sayısı)


def grid_combinations(grid: dict):
    keys = list(grid.keys())
    for values in itertools.product(*grid.values()):
        yield dict(zip(keys, values))


def fetch_all_data(symbols, timeframe, limit):
    data = {}
    for sym in symbols:
        try:
            data[sym] = get_klines(sym, timeframe, limit)
        except Exception as e:
            print(f"  {sym}: veri çekilemedi - {e}")
    return data


def _portfoy_olc(raw_data, cfg, variant_name, timeframe, warmup, son_bar):
    """Gerçek bot kısıtlarıyla ölçüm (slot limiti, gecikme, korumalar)."""
    import config as _c
    from portfolio_backtest import run_portfolio_backtest
    sd = {}
    for sym, df in raw_data.items():
        son = son_bar.get(sym, len(df))
        if son < warmup + 20:
            continue
        sub = df.iloc[:son].reset_index(drop=True)
        sd[sym] = compute_all_indicators(sub, cfg)
    if len(sd) < 3:
        return None
    try:
        r = run_portfolio_backtest(
            sd, variant_name, _c.RISK.max_concurrent_positions,
            True, 0.7, 50, timeframe, exec_lag=1,
            drawdown_scale_r=_c.DRAWDOWN_SCALE_FULL_R,
            max_hold_bars=int(_c.MAX_HOLD_DAYS * 6),
            strategy_cfg=cfg)
        return {"total_r": r["total_r"], "trades": r["trades"],
                "win_rate": r["win_rate"]}
    except Exception:
        return None


def walk_forward_search(variant_name: str, raw_data: dict, n_folds: int,
                         timeframe: str = "4h", min_trades_train: int = 15,
                         portfolio_mode: bool = True):
    """Walk-forward parametre araması.

    portfolio_mode=True (VARSAYILAN): gerçek bot kısıtlarıyla ölçer -
    slot limiti, uygulama gecikmesi, kademeli azaltma, max tutma.

    portfolio_mode=False: her coin BAĞIMSIZ simüle edilir (simulate_range).
    Bu ÇOK ŞİŞİK sonuç verir çünkü:
      - aynı anda sınırsız pozisyon açılabilir (gerçekte 5 slot var)
      - uygulama gecikmesi yok (sinyal barında dolum varsayılır)
      - kademeli azaltma yok
    ÖLÇÜLDÜ (2024, temiz veri): bağımsız +1106.6R, portföy kısıtlı
    +477.7R -> 2.3 KAT ŞİŞME.
    Şişme sabit bir çarpan değil; parametreye göre değişir, bu yüzden
    YANLIŞ PARAMETRE SEÇİMİNE yol açabilir. Sadece hızlı kaba tarama
    için kullanın.
    """
    signal_fn = STRATEGY_VARIANTS[variant_name]
    grid = PARAM_GRIDS[variant_name]

    fold_bounds = {}
    for sym, df in raw_data.items():
        n = len(df)
        size = n // n_folds
        fold_bounds[sym] = [k * size for k in range(n_folds)] + [n]

    fold_reports = []
    oos_trades_all = []

    for fold_k in range(1, n_folds):
        best_cfg, best_train_score, best_train_trades = None, float("-inf"), 0

        for override in grid_combinations(grid):
            cfg = replace(config.STRATEGY, **override)
            train_trades = []
            if not portfolio_mode:
                for sym, df in raw_data.items():
                    train_end = fold_bounds[sym][fold_k]
                    if train_end < WARMUP + 20:
                        continue
                    ind = compute_all_indicators(df, cfg)
                    train_trades.extend(simulate_range(sym, ind, signal_fn, cfg, WARMUP,
                                                       train_end, timeframe=timeframe))

            if portfolio_mode:
                m = _portfoy_olc(raw_data, cfg, variant_name, timeframe,
                                 WARMUP, {sym: fold_bounds[sym][fold_k]
                                          for sym in raw_data})
            else:
                m = compute_metrics(train_trades)
            if not m or m["trades"] < min_trades_train:
                continue
            if m["total_r"] > best_train_score:
                best_train_score, best_cfg, best_train_trades = m["total_r"], cfg, m["trades"]

        if best_cfg is None:
            fold_reports.append({"fold": fold_k, "cfg": None, "train_trades": 0, "test_metrics": None})
            continue

        # TEST DÖNEMİ - eğitimle AYNI yöntemle ölçülmeli, yoksa
        # karşılaştırma anlamsız olur.
        if portfolio_mode:
            test_m = _portfoy_olc(
                raw_data, best_cfg, variant_name, timeframe, WARMUP,
                {sym: fold_bounds[sym][fold_k + 1] for sym in raw_data})
            # Portföy modunda kümülatif OOS toplamı tutulamaz (işlem
            # listesi yok); fold bazlı raporlanır.
            if test_m:
                oos_trades_all.append(test_m["total_r"])
        else:
            test_trades = []
            for sym, df in raw_data.items():
                train_end, test_end = fold_bounds[sym][fold_k], fold_bounds[sym][fold_k + 1]
                if test_end - train_end < 10:
                    continue
                ind = compute_all_indicators(df, best_cfg)
                test_trades.extend(simulate_range(sym, ind, signal_fn, best_cfg,
                                                  train_end, test_end, timeframe=timeframe))
            oos_trades_all.extend(test_trades)
            test_m = compute_metrics(test_trades)

        fold_reports.append({
            "fold": fold_k, "cfg": best_cfg, "train_trades": best_train_trades,
            "test_metrics": test_m,
        })

    if portfolio_mode:
        # oos_trades_all burada fold bazlı R toplamları listesi
        gecerli = [x for x in oos_trades_all if x is not None]
        overall = ({"total_r": sum(gecerli), "trades": len(gecerli),
                    "win_rate": (sum(1 for x in gecerli if x > 0) / len(gecerli) * 100)
                    if gecerli else 0.0}
                   if gecerli else None)
    else:
        overall = compute_metrics(oos_trades_all)
    return overall, fold_reports


def print_fold_report(variant_name: str, fold_reports: list):
    print(f"\n--- {variant_name} : fold bazlı walk-forward detayı ---")
    for fr in fold_reports:
        if fr["cfg"] is None:
            print(f"  Fold {fr['fold']}: yeterli train işlemi bulunamadı, atlandı.")
            continue
        tm = fr["test_metrics"]
        if tm is None:
            print(f"  Fold {fr['fold']}: train'de {fr['train_trades']} işlem, test'te hiç işlem yok.")
            continue
        print(f"  Fold {fr['fold']}: train={fr['train_trades']} işlem -> "
              f"OOS test={tm['trades']} işlem, kazanma=%{tm['win_rate']:.0f}, "
              f"toplamR={tm['total_r']:+.2f}, PF={tm['profit_factor']:.2f}")


def run_optimizer(top_n: int, limit: int, timeframe: str, n_folds: int, portfolio_mode: bool = True):
    print(f"Veri çekiliyor: en hacimli {top_n} coin, {limit} mum, {timeframe}...")
    symbols = get_top_symbols(config.SCAN.quote_asset, top_n, config.SCAN.excluded_symbols)
    raw_data = fetch_all_data(symbols, timeframe, limit)
    print(f"{len(raw_data)} coin için veri hazır.\n")

    results = {}
    for variant_name in STRATEGY_VARIANTS:
        print(f"=== {variant_name} taranıyor (walk-forward, {n_folds} fold) ===")
        overall, fold_reports = walk_forward_search(variant_name, raw_data, n_folds,
                                                   timeframe=timeframe,
                                                   portfolio_mode=portfolio_mode)
        results[variant_name] = overall
        print_fold_report(variant_name, fold_reports)
        if overall:
            _pf = overall.get("profit_factor")
            _birim = "fold" if portfolio_mode else "işlem"
            print(f"  >>> TOPLAM OUT-OF-SAMPLE: {overall['trades']} {_birim}, "
                  f"kazanma=%{overall['win_rate']:.1f}, toplamR={overall['total_r']:+.2f}"
                  + (f", PF={_pf:.2f}" if _pf else ""))
        else:
            print("  >>> Yeterli out-of-sample işlem üretilmedi.")
        print()

    print("=" * 70)
    print("SONUÇ: STRATEJİ KARŞILAŞTIRMASI (SADECE OUT-OF-SAMPLE SONUÇLAR)")
    print("=" * 70)
    ranked = sorted(
        [(name, m) for name, m in results.items() if m],
        key=lambda kv: kv[1]["total_r"], reverse=True
    )
    if not ranked:
        print("Hiçbir strateji yeterli out-of-sample işlem üretmedi.")
        print("Muhtemelen: veri/lookback yetersiz, ya da min trade eşiği yüksek.")
        return

    for name, m in ranked:
        verdict = "olası edge adayı" if (m["profit_factor"] > 1.3 and m["trades"] >= 20) else "yetersiz kanıt"
        print(f"{name:<18} PF={m['profit_factor']:.2f}  toplamR={m['total_r']:+.2f}  "
              f"işlem={m['trades']:<4}  -> {verdict}")

    print("\nÖNEMLİ: 'Olası edge adayı' etiketi bile kesinlik ifade etmez.")
    print("Bu sadece geçmişte, komisyon ve ortalama funding maliyeti dahil, slippage'siz simülasyonda,")
    print("out-of-sample olarak tutarlı görünen bir strateji demektir.")
    print("Canlıya geçmeden önce:")
    print("  1) Mutlaka testnette haftalarca paper-trade doğrulaması yapın")
    print("  2) Küçük sermaye ile başlayın, kademeli artırın")
    print("  3) Piyasa rejimi değişebilir; geçmiş performans garanti değildir")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walk-forward strateji/edge arayıcı (anahtarsız)")
    parser.add_argument("--symbols", type=int, default=15)
    parser.add_argument("--limit", type=int, default=1500)
    parser.add_argument("--timeframe", type=str, default=config.SCAN.timeframe)
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--fast", action="store_true",
                        help="HIZLI mod: her coin bağımsız simüle edilir "
                             "(portföy kısıtı yok). 2.3 KAT ŞİŞİK sonuç "
                             "verir ve yanlış parametre seçebilir - sadece "
                             "kaba ön tarama için.")
    args = parser.parse_args()
    run_optimizer(args.symbols, args.limit, args.timeframe, args.folds, portfolio_mode=not args.fast)
