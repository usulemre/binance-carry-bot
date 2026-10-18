"""SİNYAL BOTU WALK-FORWARD — strateji seçimi dahil.

KULLANIM: python signal_walkforward.py

Kesitsel bot için full_walkforward.py var; bu onun sinyal botu karşılığı.

NOT: 4 aday x 7 dönem ~3-4 dakika sürer. Daha fazla aday eklerseniz
süre hızla artar (her aday tüm eğitim verisinde çalıştırılıyor).

ORİJİNAL AÇIKLAMA:

Strateji SECIMI dahil hicbir sey gelecekten bilinmiyor: her donem icin
onceki tum veriden en iyi strateji+parametre secilir, sonraki donemde
uygulanir.

Bu kritik cunku madde 86 da extreme_reversal'i TUM veriye bakarak
sectik. Walk-forward bunun gercekten onceden secilebilir olup
olmadigini test eder.
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, config
from backtest_yearly import load_all_csvs
from indicators import compute_all_indicators
from strategy import STRATEGY_VARIANTS
from backtest import COMMISSION_PCT_PER_SIDE, AVG_FUNDING_PCT_PER_8H, _timeframe_to_minutes
from data_quality import stale_orani

d=load_all_csvs('4h')
temiz={s:df for s,df in d.items() if stale_orani(df[df['date'].dt.year>=2022])<0.10}
IND={s:compute_all_indicators(df[df['date'].dt.year>=2022].reset_index(drop=True),config.STRATEGY)
     for s,df in temiz.items()}
print(f"{len(IND)} coin")

def run(sd, strateji, dd_scale=None, max_hold=None, max_conc=None, lag=1):
    # Varsayılanlar CANLI BOT ayarlarından - parite için (bkz.
    # test_backtest_parity.py). Sabit değer yazmak, config değişince
    # walk-forward'ın eski sistemi test etmesine yol açar.
    if dd_scale is None: dd_scale = config.DRAWDOWN_SCALE_FULL_R
    if max_hold is None: max_hold = int(config.MAX_HOLD_DAYS * 6)
    if max_conc is None: max_conc = config.RISK.max_concurrent_positions
    fn=STRATEGY_VARIANTS[strateji]; cfg=config.STRATEGY
    syms=list(sd)
    if not syms: return None
    n=min(len(sd[s]) for s in syms)
    if n<80: return None
    tf=_timeframe_to_minutes('4h')
    op={}; closed=[]; eq=[0.0]; pend=[]; peak=0.0
    for i in range(60,n):
        cur=eq[-1]; peak=max(peak,cur)
        sc=max(0.0,min(1.0,1.0-(peak-cur)/dd_scale)) if dd_scale else 1.0
        still=[]
        for (b,sym,sig) in pend:
            if b==i:
                if sym not in op and len(op)<max_conc and sc>0.01:
                    px=float(sd[sym].iloc[i]['open']); sh=px-sig.entry_price
                    r=abs(px-(sig.stop_loss+sh))
                    if r>0: op[sym]=dict(d=sig.direction,e=px,sl=sig.stop_loss+sh,
                                          tp=sig.take_profit+sh,b=i,r=r,s=sc)
            else: still.append((b,sym,sig))
        pend=still
        for sym in list(op):
            p=op[sym]; bar=sd[sym].iloc[i]
            hi,lo,cl=float(bar['high']),float(bar['low']),float(bar['close'])
            hs= lo<=p['sl'] if p['d']=='LONG' else hi>=p['sl']
            ht= hi>=p['tp'] if p['d']=='LONG' else lo<=p['tp']
            sure = max_hold and (i-p['b'])>=max_hold
            if hs or ht or sure:
                if hs:
                    raw=p['sl']; sl2=raw*0.0005
                    ex=raw-sl2 if p['d']=='LONG' else raw+sl2
                elif ht: ex=p['tp']
                else: ex=cl
                eff=p['e']*1.0002 if p['d']=='LONG' else p['e']*0.9998
                pl=(ex-eff) if p['d']=='LONG' else (eff-ex)
                com=(p['e']+ex)*(COMMISSION_PCT_PER_SIDE/100)
                fu=p['e']*(AVG_FUNDING_PCT_PER_8H/100)*((i-p['b'])*tf/480)
                closed.append((pl-com-fu)/p['r']*p['s']); eq.append(eq[-1]+closed[-1]); del op[sym]
        for sym in syms:
            if sym in op or len(op)>=max_conc: continue
            sg=fn(sym,sd[sym].iloc[i],cfg)
            if sg: pend.append((i+lag,sym,sg))
    if not closed: return None
    s=pd.Series(eq)
    return {'R':sum(closed),'n':len(closed),'dd':(s-s.cummax()).min()}

def kes(a,b):
    out={}
    for s,ind in IND.items():
        m=(ind['date']>=a)&(ind['date']<=b)
        if m.sum()>80: out[s]=ind[m].reset_index(drop=True)
    return out

# ÖNEMLİ: KORUMA PARAMETRELERİNİ BURADA ARAMAYIN.
# Kademeli azaltma / devre kesici gibi korumalar tepe-düşüş BİRİKİMİYLE
# çalışır. 6 aylık dilimlerde bu birikim oluşmaz, bu yüzden farklı
# eşikler neredeyse aynı sonucu verir (ölçüldü: 20R ile 50R arası fark
# %3) ve arama anlamsız bir seçim yapar.
# Bu parametreler UZUN KESİNTİSİZ dönemde ayrı ölçülmelidir.
# (Gerçek örnek: walk-forward her dönemde 50R seçti, ama kesintisiz
#  2022-2026 ölçümünde 20R risk ayarlı olarak açık ara daha iyiydi.)
# Koruma eşiği SABİT (yukarıdaki nota bakın) - sadece STRATEJİ aranıyor.
ADAYLAR=[(st, config.DRAWDOWN_SCALE_FULL_R)
         for st in ['mean_reversion','extreme_reversal','adaptive',
                    'breakout','trend_momentum']]
# NOT (madde 115): 'breakout' ve 'trend_momentum' uzun sure bu listede
# YOKTU. Eski BOZUK veride (madde 111) extreme_reversal kazaniyor
# gorundugu icin aday listesi ona gore daraltilmisti. Temiz veride
# breakout acik ara en iyi strateji cikti - yani walk-forward yillarca
# EN IYI ADAYI HIC DENEMEDEN calisti.
print(f"{len(ADAYLAR)} aday strateji (koruma eşiği sabit: {config.DRAWDOWN_SCALE_FULL_R}R)\n")

donemler=pd.period_range('2023-01','2026-01',freq='6M')
oos=[]; sec=[]
print(f"{'donem':<12} {'secilen':<28} {'OOS_R':>9} {'islem':>7}")
print('-'*60)
for dn in donemler:
    train=kes(pd.Timestamp('2022-01-01'), dn.start_time-pd.Timedelta(days=1))
    test=kes(dn.start_time, dn.end_time)
    if len(train)<5 or len(test)<5: continue
    en=(None,-1e9)
    for st,ds in ADAYLAR:
        m=run(train,st,dd_scale=ds)
        if m and m['R']>en[1]: en=((st,ds),m['R'])
    if en[0] is None: continue
    st,ds=en[0]
    mt=run(test,st,dd_scale=ds)
    if not mt: continue
    oos.append(mt['R']); sec.append(st)
    print(f"{str(dn):<12} {st+' '+str(int(ds))+'R':<28} {mt['R']:>+8.1f}R {mt['n']:>7}")
print()
if oos:
    a=np.array(oos)
    print(f">>> {len(a)} donem, {(a>0).sum()} pozitif (%{(a>0).mean()*100:.0f})")
    print(f">>> toplam {a.sum():+.1f}R, medyan {np.median(a):+.1f}R")
    from collections import Counter
    print(f">>> strateji secimi: {dict(Counter(sec))}")
    sir=np.argsort(a)[::-1]
    for k in [1,2]:
        if k<len(a): print(f">>> en iyi {k} donem haric: {np.delete(a,sir[:k]).sum():+.1f}R")
