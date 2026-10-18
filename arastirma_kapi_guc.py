"""MADDE 234: kapinin UC OLCUTU ileriye donuk kotu performansi HABER VERIYOR MU?
Bir kapi ancak zarardan ONCE oterse degerlidir."""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import carry_saglik as CS, carry_denetim as D
from tradfi_liste import TRADFI
P=pickle.load(open('/tmp/panel.pkl','rb')); C,ODE=P['C'],P['ODE']
uy=D.uygunluk(P['C'],P['HAC'],P['YAS'],P['DON'],hacim=1e8,yas_bar=540,donuk_esik=0.10).copy()
uy[[c for c in uy.columns if c in TRADFI]]=False
U=uy.values; O=ODE.values; idx=C.index
BLOK=30; SIN=6; NL=12
def yillik(pen):
    v=pen[np.isfinite(pen)&(pen!=0)]
    return None if v.size<2 else float(v.mean())*3*365.0
kay=[]
for i in range(1200,len(C)-BLOK-1,SIN):          # her 24 saatte bir olc
    t0=i-SIN
    if t0<0: continue
    sin={}
    for j in range(O.shape[1]):
        if not U[i,j]: continue
        y=yillik(O[t0+1:i+1,j])
        if y is not None: sin[j]=y
    if len(sin)<2*3: continue
    sir=sorted(sin,key=sin.get); n=min(NL,len(sir)//2)
    L,S=sir[:n],sir[-n:]
    disp=(np.mean([sin[s] for s in S])-np.mean([sin[s] for s in L]))/365.0
    ger={s:float(np.nansum(O[i+1:i+BLOK+1,s])) for s in sin}
    ic=CS._sira_korelasyonu({str(k):v for k,v in sin.items()},{str(k):v for k,v in ger.items()})
    f=(-sum(ger[s] for s in L)+sum(ger[s] for s in S))/(2*n)
    kay.append((idx[i],ic,f,disp))
df=pd.DataFrame(kay,columns=['t','IC','F','DISP']).set_index('t')
es=[pickle.load(open(f'/tmp/g19E_{k}.pkl','rb')).pct_change() for k in (0,1)]
g=(1+pd.concat(es,axis=1).mean(axis=1).dropna()).resample('1D').prod().dropna()-1
# ILERIYE donuk 30 gunluk getiri
ileri=[]
for t in df.index:
    v=g[(g.index>t)&(g.index<=t+pd.Timedelta(days=30))]
    ileri.append(((1+v).prod()-1)*100 if len(v)>20 else np.nan)
df['ileri30']=ileri
df=df.dropna()
# kayan 6-pencere ortalamasi (kapinin kullandigi hal)
for c in ('IC','F','DISP'): df[c+'_o']=df[c].rolling(6).mean()
df=df.dropna()
print("OLCUT -> ILERIYE DONUK 30 GUNLUK GETIRI (%d gozlem)"%len(df))
print("Bir kapi ancak ALT DILIMDE getiri DUSUKSE degerlidir.\n")
print("%-8s%14s%14s%14s%12s"%("olcut","alt %10 ort","ust %90 ort","tum ort","Spearman"))
from scipy import stats
for c in ('IC','F','DISP'):
    v=df[c+'_o'].values; y=df['ileri30'].values
    a=np.percentile(v,10); b=np.percentile(v,90)
    rho,p=stats.spearmanr(v,y)
    print("%-8s%+13.1f%%%+13.1f%%%+13.1f%%%9.3f (p=%.3f)"%(
        c,y[v<=a].mean(),y[v>=b].mean(),y.mean(),rho,p))
print("\nKAPININ ESIKLERINDE olan gozlemler:")
for c,esik,ad in [('IC_o',CS.IC_ESIK,'IC < 0.193'),('F_o',CS.F_ESIK,'F <= 0'),
                  ('DISP_o',CS.DISP_ESIK,'DISP < 2.86bp')]:
    m=df[c]<esik if c!='F_o' else df[c]<=esik
    if m.sum():
        print("  %-16s %3d gozlem (%%%.1f) -> ileri 30g ort %+.1f%% (tum ort %+.1f%%)"%(
            ad,m.sum(),100*m.mean(),df['ileri30'][m].mean(),df['ileri30'].mean()))
    else:
        print("  %-16s hic gozlem yok"%ad)
