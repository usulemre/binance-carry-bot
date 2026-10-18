"""İSTATİSTİKSEL GÜVENİLİRLİK ANALİZİ.

Backtest bir Sharpe rakamı verir; bu araç o rakamın NE KADAR
GÜVENİLİR olduğunu ölçer. Parametreler değiştiğinde tekrar çalıştırın.

Üç kontrol yapar:
  1) Blok bootstrap - Sharpe'ın güven aralığı
  2) Evren bağımlılığı - belirli coinlere mi bağlı?
  3) Çoklu test uyarısı - kaç konfigürasyon denendiyse o kadar şişme olur

KULLANIM: python robustness_check.py
"""
"""(eski aciklama) Sharpe ne kadar guvenilir?
Blok bootstrap: getiri serisinden bloklar halinde rastgele ornekleme yapip
Sharpe dagilimini cikar. Bloklar kullanilir cunku ardisik getiriler
bagimsiz degil (otokorelasyon var).
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd
from backtest_yearly import load_all_csvs
from crosssec_backtest import build_price_panel, run_crosssectional

d=load_all_csvs("4h"); panel=build_price_panel(d)
H=[30,60,90]
eq,m = run_crosssectional(panel[panel.index.year>=2022],60,6,4,
                          horizons_bars=H,pos_tp=0.04,trail_scale=0.30)
r = eq.diff().dropna().values
print(f"getiri serisi: {len(r)} bar ({len(r)/6/365.25:.1f} yil)")
print(f"gozlenen Sharpe: {m['sharpe']:.2f}")
print()

rng=np.random.default_rng(42)
ANN=np.sqrt(365.25*6)

def block_bootstrap(x, block, n_iter=2000):
    n=len(x); nb=int(np.ceil(n/block)); out=[]
    for _ in range(n_iter):
        idx=rng.integers(0,n-block,size=nb)
        samp=np.concatenate([x[i:i+block] for i in idx])[:n]
        s=samp.std()
        out.append(samp.mean()/s*ANN if s>0 else 0)
    return np.array(out)

print("BLOK BOOTSTRAP (blok boyutu = bagimlilik suresi):")
print(f"{'blok':<14} {'ort Sharpe':>12} {'%5':>8} {'%95':>8} {'Sharpe<0 olasilik':>19}")
print('-'*68)
for blok,lbl in [(6,'1 gun'),(42,'1 hafta'),(180,'1 ay'),(540,'3 ay')]:
    b=block_bootstrap(r,blok)
    print(f'{lbl:<14} {b.mean():>12.2f} {np.percentile(b,5):>8.2f} {np.percentile(b,95):>8.2f} {(b<0).mean()*100:>18.1f}%')

print()
print("ETKIN ORNEKLEM BUYUKLUGU:")
# otokorelasyon -> etkin bagimsiz gozlem sayisi
ac=pd.Series(r).autocorr(lag=1)
n_eff=len(r)*(1-ac)/(1+ac) if ac>-1 else len(r)
print(f"  ham gozlem       : {len(r)}")
print(f"  1-gecikme otokor : {ac:+.3f}")
print(f"  etkin gozlem     : {n_eff:.0f}")
print(f"  Sharpe standart hatasi ~ {np.sqrt((1+m['sharpe']**2/2)/n_eff)*ANN/ANN:.2f}")


# --- 2) EVREN BAĞIMLILIĞI ---
print()
print("EVREN BAĞIMLILIĞI (rastgele coin alt kümeleri):")
print(f"{'coin sayısı':<14} {'ort Sharpe':>12} {'en düşük':>10} {'en yüksek':>11}")
print('-' * 50)
p22 = panel[panel.index.year >= 2022]
cols = list(p22.columns)
for k in [8, 10, 12, len(cols)]:
    shs = []
    n_iter = 25 if k < len(cols) else 1
    for _ in range(n_iter):
        sub = list(rng.choice(cols, size=k, replace=False)) if k < len(cols) else cols
        try:
            _, mm = run_crosssectional(p22[sub], 60, 6, min(4, k // 2),
                                       horizons_bars=H, pos_tp=0.04, trail_scale=0.30)
            if np.isfinite(mm["sharpe"]):
                shs.append(mm["sharpe"])
        except Exception:
            pass
    if shs:
        a = np.array(shs)
        print(f"{k:<14} {a.mean():>12.2f} {a.min():>10.2f} {a.max():>11.2f}")

# --- 2b) SİNYAL BOTU: İŞLEM BAZLI GÜVENİLİRLİK ---
# Sharpe, otokorelasyonlu BAR getirilerine dayanır. İşlem bazlı
# t-istatistiği daha güvenilir çünkü her işlem büyük ölçüde bağımsız
# bir gözlemdir.
print()
print("SİNYAL BOTU - işlem bazlı güvenilirlik:")
try:
    from data_quality import stale_orani as _stale
    temiz = {s2: df for s2, df in d.items()
             if _stale(df[df["date"].dt.year >= 2022]) < 0.10}
    from indicators import compute_all_indicators
    from strategy import STRATEGY_VARIANTS
    from backtest import COMMISSION_PCT_PER_SIDE, AVG_FUNDING_PCT_PER_8H, _timeframe_to_minutes
    import config as _cfg
    _fn = STRATEGY_VARIANTS[_cfg.ACTIVE_STRATEGY]
    _c = _cfg.STRATEGY
    _sd = {s2: compute_all_indicators(df[df["date"].dt.year >= 2022].reset_index(drop=True), _c)
           for s2, df in temiz.items()}
    _syms = list(_sd); _n = min(len(_sd[s2]) for s2 in _syms)
    _tf = _timeframe_to_minutes("4h"); _mc = _cfg.RISK.max_concurrent_positions
    _op = {}; _cl = []; _eq = [0.0]; _pend = []; _peak = 0.0
    for _i in range(60, _n):
        _cur = _eq[-1]; _peak = max(_peak, _cur)
        _sc = max(0.0, min(1.0, 1.0 - (_peak - _cur) / _cfg.DRAWDOWN_SCALE_FULL_R))
        _still = []
        for (_b, _sym, _sig) in _pend:
            if _b == _i:
                if _sym not in _op and len(_op) < _mc and _sc > 0.01:
                    _px = float(_sd[_sym].iloc[_i]["open"]); _sh = _px - _sig.entry_price
                    _r = abs(_px - (_sig.stop_loss + _sh))
                    if _r > 0:
                        _op[_sym] = dict(d=_sig.direction, e=_px, sl=_sig.stop_loss + _sh,
                                         tp=_sig.take_profit + _sh, b=_i, r=_r, s=_sc)
            else:
                _still.append((_b, _sym, _sig))
        _pend = _still
        for _sym in list(_op):
            _p = _op[_sym]; _bar = _sd[_sym].iloc[_i]
            _hi, _lo = float(_bar["high"]), float(_bar["low"])
            _hs = _lo <= _p["sl"] if _p["d"] == "LONG" else _hi >= _p["sl"]
            _ht = _hi >= _p["tp"] if _p["d"] == "LONG" else _lo <= _p["tp"]
            if _hs or _ht or (_i - _p["b"]) >= int(_cfg.MAX_HOLD_DAYS * 6):
                _ex = (_p["sl"] * 0.9995 if _p["d"] == "LONG" else _p["sl"] * 1.0005) if _hs \
                    else (_p["tp"] if _ht else float(_bar["close"]))
                _eff = _p["e"] * 1.0002 if _p["d"] == "LONG" else _p["e"] * 0.9998
                _pl = (_ex - _eff) if _p["d"] == "LONG" else (_eff - _ex)
                _com = (_p["e"] + _ex) * (COMMISSION_PCT_PER_SIDE / 100)
                _fu = _p["e"] * (AVG_FUNDING_PCT_PER_8H / 100) * ((_i - _p["b"]) * _tf / 480)
                _cl.append((_pl - _com - _fu) / _p["r"] * _p["s"])
                _eq.append(_eq[-1] + _cl[-1]); del _op[_sym]
        for _sym in _syms:
            if _sym in _op or len(_op) >= _mc:
                continue
            _s2 = _fn(_sym, _sd[_sym].iloc[_i], _c)
            if _s2:
                _pend.append((_i + 1, _sym, _s2))
    _cl = np.array(_cl)
    if len(_cl) > 30:
        _se = _cl.std() / np.sqrt(len(_cl))
        _t = _cl.mean() / _se
        _boot = np.array([rng.choice(_cl, size=len(_cl), replace=True).sum() for _ in range(2000)])
        print(f"  {len(_cl)} işlem, toplam {_cl.sum():+.1f}R")
        print(f"  işlem başına {_cl.mean():+.4f}R (std hata {_se:.4f}) -> t = {_t:.2f}")
        print(f"  bootstrap %5-%95: {np.percentile(_boot, 5):+.1f}R .. {np.percentile(_boot, 95):+.1f}R")
        print(f"  negatif çıkma olasılığı: %{(_boot < 0).mean() * 100:.2f}")
        SIGNAL_T = _t
    else:
        SIGNAL_T = None
except Exception as _e:
    print(f"  ölçülemedi: {_e}")
    SIGNAL_T = None


# --- 3) ÇOKLU TEST UYARISI ---
print()
print("ÇOKLU TEST DÜZELTMESİ:")
N_DENEME = 1328   # bu projede denenen yaklaşık konfigürasyon sayısı
se = 1 / np.sqrt(len(r)) * ANN
beklenen_max = np.sqrt(2 * np.log(N_DENEME)) * se
print(f"  denenen konfigürasyon      : ~{N_DENEME}")
print(f"  tek denemede Sharpe std hata: {se:.3f}")
print(f"  ŞANS ESERİ beklenen en yüksek Sharpe: {beklenen_max:.2f}")
print(f"  gözlenen Sharpe            : {m['sharpe']:.2f}")
print()
if m["sharpe"] > beklenen_max * 2:
    print("  Çoklu test düzeltmesinden sonra da net şekilde anlamlı.")
elif m["sharpe"] > beklenen_max:
    print("  Şans aralığının ÜSTÜNDE ama çok uzağında değil.")
    print("  Gerçek Sharpe muhtemelen gözlenenden DÜŞÜKTÜR.")
    print("  Backtest rakamını beklenti olarak almayın.")
else:
    print("  DİKKAT: gözlenen Sharpe şans aralığının içinde - güvenilmez.")

# İşlem bazlı t-istatistiği ile çapraz kontrol (daha güvenilir)
if SIGNAL_T is not None:
    t_sans = np.sqrt(2 * np.log(N_DENEME))
    print()
    print("  İŞLEM BAZLI ÇAPRAZ KONTROL (sinyal botu):")
    print(f"    gözlenen t              : {SIGNAL_T:.2f}")
    print(f"    {N_DENEME} denemede şans eseri: {t_sans:.2f}")
    if SIGNAL_T > t_sans * 2:
        print("    -> şans aralığının ÇOK üstünde, güçlü şekilde anlamlı.")
        print("    (Bu ölçüm Sharpe'tan daha güvenilir: her işlem büyük ölçüde")
        print("     bağımsız bir gözlem, Sharpe ise otokorelasyonlu bar")
        print("     getirilerine dayanıyor.)")
    elif SIGNAL_T > t_sans:
        print("    -> şans aralığının üstünde ama uzağında değil.")
    else:
        print("    -> DİKKAT: şans aralığında.")
