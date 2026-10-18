"""CANLI BOT ile BACKTEST PARITESI.

Bu projede iki kez ayni hata yasandi: canli bota yeni bir mekanizma
eklendi ama backtest modulune yansitilmadi. Sonuc: backtest sessizce
FARKLI bir sistemi test etmeye devam etti.
  - madde 56: cok ufuklu siralama, TP, kademeli azaltma eksikti
  - madde 94: dispersiyon filtresi eksikti
  - bu test: acil stop eksikti

Bu test, canli bottaki her ozelligin backtest modulunde de
DESTEKLENDIGINI dogrular. Yeni ozellik eklenince bu teste de
eklenmeli.
"""
import sys, inspect; sys.path.insert(0,'.')
import config
import crosssec_bot as cb
import crosssec_backtest as cbt
import portfolio_backtest as pbt

print("=== KESITSEL BOT: canli ozellikler backtestte var mi? ===")
bt = inspect.getsource(cbt.run_crosssectional)
sig = inspect.signature(cbt.run_crosssectional).parameters

kontroller = [
    ("cok ufuklu siralama", cb.USE_MULTI_HORIZON, "horizons_bars"),
    ("kar alma (TP)",       cb.USE_POSITION_TAKE_PROFIT, "pos_tp"),
    ("acil stop",           cb.USE_EMERGENCY_STOP, "pos_sl"),
    ("kademeli azaltma",    cb.USE_DRAWDOWN_SCALING, "trail_scale"),
    ("dispersiyon filtresi",cb.USE_DISPERSION_FILTER, "min_dispersion"),
]
eksik = []
for ad, canli_acik, param in kontroller:
    var = param in sig
    isaret = "OK  " if var else "!!!!"
    print(f"  {isaret} {ad:<24} canli={str(canli_acik):<5} backtest_parametresi={var}")
    if canli_acik and not var:
        eksik.append(ad)
assert not eksik, (
    f"BACKTEST CANLI BOTU TEMSIL ETMIYOR! Eksik: {eksik}. "
    f"Bu ozellikler canlida acik ama backtest modulunde yok - "
    f"backtest sonuclari gercek bot davranisini gostermiyor.")

print("\n=== Uygulama gecikmesi VARSAYILAN olarak acik mi? ===")
for ad, fn in [("crosssec_backtest", cbt.run_crosssectional),
               ("portfolio_backtest", pbt.run_portfolio_backtest)]:
    p = inspect.signature(fn).parameters.get("exec_lag")
    v = p.default if p else None
    print(f"  {ad:<22} exec_lag varsayilani = {v}")
    assert v == 1, f"{ad}: gecikme varsayilani 1 olmali (gercekci), {v} bulundu"

print("\n=== Bilesik mod VARSAYILAN olarak acik mi? ===")
p = inspect.signature(cbt.run_crosssectional).parameters.get("compound")
print(f"  compound varsayilani = {p.default} (canli bot bilesik calisiyor)")
assert p.default is True, "canli bot bilesik ama backtest varsayilani sabit nominal!"

print("\n=== SINYAL BOTU: canli ozellikler backtestte var mi? ===")
psig = inspect.signature(pbt.run_portfolio_backtest).parameters
sig_kontrol = [
    ("kademeli azaltma", config.USE_DRAWDOWN_SCALING, "drawdown_scale_r"),
    ("max tutma suresi", config.USE_MAX_HOLD, "max_hold_bars"),
    ("korelasyon filtresi", config.RISK.use_correlation_filter, "correlation_filter"),
]
eksik2 = []
for ad, canli_acik, param in sig_kontrol:
    var = param in psig
    print(f"  {'OK  ' if var else '!!!!'} {ad:<24} canli={str(canli_acik):<5} backtest_parametresi={var}")
    if canli_acik and not var:
        eksik2.append(ad)
assert not eksik2, f"portfolio_backtest canli botu temsil etmiyor! Eksik: {eksik2}"

print("\n=== SINYAL BOTU: strateji bazli ayarlar okunuyor mu? ===")
mk = open("main.py").read()
for ad, anahtar in [("rejim filtresi", "USE_REGIME_FILTER_BY_STRATEGY"),
                     ("kar kilitleme", "USE_POSITION_MANAGEMENT"),
                     ("max tutma suresi", "MAX_HOLD_DAYS")]:
    var = anahtar in mk
    print(f"  {'OK  ' if var else '!!!!'} {ad:<22} main.py'da okunuyor={var}")
    assert var, f"{ad} main.py'da kullanilmiyor!"

print("\nPARITE TESTLERI GECTI")

print("\n=== PARAMETRE TARAMASI GERCEKTEN ETKI EDIYOR MU? ===")
# Madde 97: run_portfolio_backtest eskiden HER ZAMAN global config.STRATEGY
# kullaniyordu -> tum esik degerleri AYNI sonucu veriyordu (tarama etkisiz).
from dataclasses import replace
import numpy as np, pandas as pd
from backtest_yearly import load_all_csvs
from indicators import compute_all_indicators
from data_quality import stale_orani
_d = load_all_csvs("4h")
_t = {s: df for s, df in _d.items() if stale_orani(df[df["date"].dt.year >= 2022]) < 0.10}
_sonuclar = []
for _th in [8.0, 15.0]:
    _c = replace(config.STRATEGY, extreme_threshold_pct=_th)
    _sd = {}
    for s, df in list(_t.items())[:6]:
        sub = df[df["date"].dt.year == 2024].reset_index(drop=True)
        if len(sub) > 300:
            _sd[s] = compute_all_indicators(sub, _c)
    if len(_sd) < 4:
        break
    _r = pbt.run_portfolio_backtest(_sd, "extreme_reversal", 5, True, 0.7, 50, "4h",
                                    exec_lag=1, strategy_cfg=_c)
    _sonuclar.append(_r["trades"])
    print(f"  esik %{_th:.0f} -> {_r['trades']} islem")
if len(_sonuclar) == 2:
    assert _sonuclar[0] != _sonuclar[1], (
        "PARAMETRE TARAMASI ETKISIZ! Farkli esikler ayni islem sayisi veriyor - "
        "strategy_cfg sinyal uretimine gecmiyor olabilir (bkz. madde 97).")
    print("  OK: farkli esikler farkli sonuc veriyor, tarama calisiyor")
print("\nTARAMA ETKINLIK TESTI GECTI")

print("\n=== CLI VARSAYILANLARI bot ayarlarini mi okuyor? ===")
# Madde 101: CLI'de --horizons varsayilani "5,10,15" sabit yazilmisti.
# Bot HORIZON_DAYS degisince CLI eski ufukla calisiyordu (sessiz parite kaybi).
_cbt_src = open("crosssec_backtest.py").read()
_kontroller = [
    ("ufuklar", "HORIZON_DAYS"),
    ("dispersiyon", "MIN_DISPERSION"),
    ("acil stop", "EMERGENCY_STOP_PCT"),
]
for _ad, _anahtar in _kontroller:
    _var = _anahtar in _cbt_src
    print(f"  {'OK  ' if _var else '!!!!'} {_ad:<16} crosssec_backtest.py bot ayarini okuyor={_var}")
    assert _var, (
        f"crosssec_backtest.py '{_anahtar}' ayarini okumuyor - CLI sabit deger "
        f"kullaniyor olabilir, bot ayari degisince backtest ESKI sistemi test eder.")
print("\nCLI PARITE TESTI GECTI")

print("\n=== OPTIMIZER portfoy kisiti kullaniyor mu? ===")
# Madde 106: optimizer simulate_range kullaniyordu -> 2.3 kat sisik olcum
import optimizer as _opt, inspect as _i
_sig = _i.signature(_opt.walk_forward_search).parameters
_var = "portfolio_mode" in _sig
_vars = _sig["portfolio_mode"].default if _var else None
print(f"  portfolio_mode parametresi : {_var}")
print(f"  varsayilan                 : {_vars} (True olmali)")
assert _var and _vars is True, (
    "optimizer portfoy kisiti kullanmiyor - slot limiti/gecikme/koruma "
    "olmadan olcum 2.3 KAT sisik cikar ve YANLIS parametre secilir!")
print("  OK: gercek bot kisitlariyla oluyor")

print("\n=== ANALIZ ARACLARI portfoy kisiti kullaniyor mu? ===")
import backtest_yearly as _by
_s = _i.signature(_by.run_yearly_breakdown).parameters
_v = "portfolio_mode" in _s
_d = _s["portfolio_mode"].default if _v else None
print(f"  backtest_yearly portfolio_mode : {_v}, varsayilan={_d}")
assert _v and _d is True, (
    "backtest_yearly portfoy kisiti kullanmiyor - yil yil rakamlar "
    "1.4-2.3 kat sisik cikar, 2022'de isaret bile degisir!")
print("  OK")
