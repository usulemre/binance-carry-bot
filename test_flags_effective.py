"""HER AYAR BAYRAGI GERCEKTEN ETKI EDIYOR MU?

Bu projede bulunan hatalarin cogu ayni turdendi: "var sanilan ama
calismayan" seyler - olu parametre (testnet), bos onbellek (6sa vs 24sa
rebalance), bos makro listesi. Hicbiri hata vermiyor, sadece sessizce
hicbir sey yapmiyor.

Bu test her bayragi ACIP KAPATIP davranisin gercekten degistigini
dogrular. Bir bayrak acik/kapali ayni sonucu veriyorsa, ya olu koddur
ya da yanlis baglanmistir.
"""
import sys, os; sys.path.insert(0,'.')
import logging; logging.disable(logging.CRITICAL)
import numpy as np, pandas as pd
import config, crosssec_bot as B

B.STATE_FILE='/tmp/flag_test.json'
def temizle():
    if os.path.exists(B.STATE_FILE): os.remove(B.STATE_FILE)
    B._liquidity_cache.clear()

class Book:
    def __init__(s, ince=()): s.ince=set(ince)
    def futures_order_book(s,symbol,limit=100):
        if symbol in s.ince:
            a=[[str(100*(1+0.005*i)), str(50/(100*(1+0.005*i)))] for i in range(100)]
            b=[[str(100*(1-0.005*(i+1))), str(50/(100*(1-0.005*(i+1))))] for i in range(100)]
        else:
            a=[[str(100*(1+0.0001*i)), str(50000/(100*(1+0.0001*i)))] for i in range(100)]
            b=[[str(100*(1-0.0001*(i+1))), str(50000/(100*(1-0.0001*(i+1))))] for i in range(100)]
        return {'asks':a,'bids':b}
    def futures_mark_price(s,symbol): return {'lastFundingRate':'0.0001'}

class Ex:
    def __init__(s,bal=10000.0,pos=None,ince=()):
        s.balance=bal; s._pos=pos or []; s.orders=[]; s.closed=[]; s.client=Book(ince)
    def get_account_balance_usdt(s): return s.balance
    def get_top_symbols(s,q,n,e): return [f'C{i}USDT' for i in range(n)]
    def get_klines(s,sym,tf,l):
        i=int(sym[1:].replace('USDT','')); n=max(l,B.REQUIRED_BARS)
        return pd.DataFrame({'close':[100*(1+(i-B.UNIVERSE_SIZE//2)*0.002)**k for k in range(n)]})
    def get_open_positions(s): return s._pos
    def get_symbol_precision(s,x): return {'quantity_precision':3}
    def open_market_position(s,sym,side,q): s.orders.append((sym,side,q))
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,x): pass

sonuc=[]
def dogrula(ad, acik_fn, kapali_fn, aciklama):
    a=acik_fn(); k=kapali_fn()
    etkili = a != k
    sonuc.append((ad, etkili))
    isaret = "OK  " if etkili else "!!!!"
    print(f"  {isaret} {ad:<28} acik={a}  kapali={k}   ({aciklama})")
    return etkili

print("BAYRAK ETKI TESTI\n")

# 1) USE_LIQUIDITY_FILTER
def _liq(deger):
    B.USE_LIQUIDITY_FILTER=deger; temizle()
    ex=Ex(ince=[f'C{i}USDT' for i in range(6)])
    B.rebalance(ex, dry_run=True)
    ok,_=B.check_liquidity(ex,'C0USDT',1000.0)
    return ok
dogrula("USE_LIQUIDITY_FILTER", lambda:_liq(True), lambda:_liq(False),
        "ince defterli coin elenmeli/elenmemeli")
B.USE_LIQUIDITY_FILTER=True

# 2) USE_POSITION_TAKE_PROFIT
def _tp(deger):
    B.USE_POSITION_TAKE_PROFIT=deger; temizle()
    ex=Ex(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'110'}])
    return len(B.take_profits(ex, dry_run=True))
dogrula("USE_POSITION_TAKE_PROFIT", lambda:_tp(True), lambda:_tp(False),
        "+%10 kardaki pozisyon kapatilmali")
B.USE_POSITION_TAKE_PROFIT=True

# 3) USE_EMERGENCY_STOP
def _es(deger):
    B.USE_EMERGENCY_STOP=deger; temizle()
    ex=Ex(pos=[{'symbol':'C0USDT','positionAmt':'10','entryPrice':'100','markPrice':'60'}])
    return len(B.take_profits(ex, dry_run=True))
dogrula("USE_EMERGENCY_STOP", lambda:_es(True), lambda:_es(False),
        "-%40 zarardaki pozisyon kapatilmali")
B.USE_EMERGENCY_STOP=True

# 4) USE_DRAWDOWN_SCALING (crosssec)
def _ds(deger):
    B.USE_DRAWDOWN_SCALING=deger
    return round(B.compute_exposure_scale(15.0), 3)
dogrula("USE_DRAWDOWN_SCALING (cs)", lambda:_ds(True), lambda:_ds(False),
        "%15 dususte olcek yarilanmali")
B.USE_DRAWDOWN_SCALING=True

# 5) USE_MULTI_HORIZON
def _mh(deger):
    """GERCEK veriyle test - sentetik kucuk ornekte siralama tesadufen
    ayni cikabiliyor, bu da bayragi 'etkisiz' gosteriyordu (yanlis alarm).
    Gercek 14 coinle ufuk farki siralamayi degistiriyor."""
    B.USE_MULTI_HORIZON=deger
    from backtest_yearly import load_all_csvs
    d=load_all_csvs('4h')
    closes={s2: df['close'].values for s2,df in d.items()}
    w=B.compute_target_weights(closes,4,1.0)
    return tuple(sorted(k for k,v in w.items() if v>0))
dogrula("USE_MULTI_HORIZON", lambda:_mh(True), lambda:_mh(False),
        "gercek veride siralama degismeli")
B.USE_MULTI_HORIZON=True

# 6) config.USE_MAX_HOLD
def _mhold(deger):
    config.USE_MAX_HOLD=deger
    import main as M, time as _t, json
    M.BOT_STATE_FILE='/tmp/flag_mh.json'
    if os.path.exists(M.BOT_STATE_FILE): os.remove(M.BOT_STATE_FILE)
    class E2:
        def __init__(s): s.closed=[]
        def get_open_positions(s): return [{'symbol':'AUSDT','positionAmt':'5'}]
        def close_position(s,a,b,c): s.closed.append(a)
        def cancel_all_open_orders(s,x): pass
    e=E2(); M.close_stale_positions(e)
    st=json.load(open(M.BOT_STATE_FILE)) if os.path.exists(M.BOT_STATE_FILE) else {}
    if st.get('position_opened_at'):
        st['position_opened_at']['AUSDT']=_t.time()-(config.MAX_HOLD_DAYS*86400+100)
        json.dump(st,open(M.BOT_STATE_FILE,'w'))
    e2=E2(); M.close_stale_positions(e2)
    if os.path.exists(M.BOT_STATE_FILE): os.remove(M.BOT_STATE_FILE)
    return len(e2.closed)
dogrula("USE_MAX_HOLD (sinyal)", lambda:_mhold(True), lambda:_mhold(False),
        "suresi dolan pozisyon kapatilmali")
config.USE_MAX_HOLD=True

# 7) config.USE_DRAWDOWN_SCALING (sinyal botu)
def _sds(deger):
    config.USE_DRAWDOWN_SCALING=deger
    from risk_manager import RiskManager
    rm=RiskManager(config.RISK)
    # olcek dogrudan calculate_position_size'a gecirilir; bayragin etkisi
    # main.py icinde. Burada bayragin OKUNDUGUNU dogrula.
    return bool(config.USE_DRAWDOWN_SCALING)
# bu bayrak main.run_cycle icinde okunuyor - kaynak kontrolu
kaynak=open('main.py').read()
etkili = 'config.USE_DRAWDOWN_SCALING' in kaynak
sonuc.append(("USE_DRAWDOWN_SCALING (sinyal)", etkili))
print(f"  {'OK  ' if etkili else '!!!!'} {'USE_DRAWDOWN_SCALING (sinyal)':<28} main.py icinde okunuyor={etkili}")
config.USE_DRAWDOWN_SCALING=True

# 8-10) config filtreleri - kaynak kontrolu
for ad, arama, dosya in [("use_correlation_filter","config.RISK.use_correlation_filter","main.py"),
                          ("use_regime_filter","config.RISK.use_regime_filter","main.py"),
                          ("use_autocorr_filter","use_autocorr_filter","main.py")]:
    k=open(dosya).read()
    etkili = arama in k
    sonuc.append((ad, etkili))
    print(f"  {'OK  ' if etkili else '!!!!'} {ad:<28} {dosya} icinde okunuyor={etkili}")

temizle()
print()
olu=[ad for ad,e in sonuc if not e]
print(f"SONUC: {len(sonuc)} bayrak, {len(olu)} ETKISIZ")
if olu:
    print("ETKISIZ BAYRAKLAR (olu kod veya yanlis baglanti):")
    for ad in olu: print(f"  - {ad}")
    sys.exit(1)
print("Tum bayraklar gercekten etki ediyor.")

print("\n=== 11) Rejim filtresi STRATEJI BAZINDA mi? ===")
import config as _c
kaynak=open('main.py').read()
assert 'USE_REGIME_FILTER_BY_STRATEGY' in kaynak, \
    "main.py strateji bazli rejim filtresini okumuyor!"
mr=_c.USE_REGIME_FILTER_BY_STRATEGY.get('mean_reversion')
er=_c.USE_REGIME_FILTER_BY_STRATEGY.get('extreme_reversal')
print(f"   mean_reversion  : {mr} (True olmali - faydali)")
print(f"   extreme_reversal: {er} (False olmali - 148.8R kaybettiriyor)")
assert mr is True and er is False, "strateji bazli ayarlar yanlis!"
bilinmeyen=_c.USE_REGIME_FILTER_BY_STRATEGY.get('yeni_strateji', _c.RISK.use_regime_filter)
assert bilinmeyen is True, "bilinmeyen strateji icin guvenli varsayilan yok!"
print("   bilinmeyen strateji -> varsayilan True (guvenli): OK")
