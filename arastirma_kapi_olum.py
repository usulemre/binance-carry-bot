"""MADDE 234: IC kaldirildiktan sonra kapi GERCEK olumu yakaliyor mu?
Madde 139'un B ve C senaryolari, olculen F/DISP serileri uzerinde."""
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
ic_,f_,d_,zt=[],[],[],[]
for i in range(1200,len(C)-BLOK-1,BLOK):
    t0=i-SIN
    sin={}
    for j in range(O.shape[1]):
        if not U[i,j]: continue
        y=yillik(O[t0+1:i+1,j])
        if y is not None: sin[j]=y
    if len(sin)<6: continue
    sir=sorted(sin,key=sin.get); n=min(NL,len(sir)//2)
    L,S=sir[:n],sir[-n:]
    d_.append((np.mean([sin[s] for s in S])-np.mean([sin[s] for s in L]))/365.0)
    ger={s:float(np.nansum(O[i+1:i+BLOK+1,s])) for s in sin}
    ic_.append(CS._sira_korelasyonu({str(k):v for k,v in sin.items()},
                                    {str(k):v for k,v in ger.items()}))
    f_.append((-sum(ger[s] for s in L)+sum(ger[s] for s in S))/(2*n))
    zt.append(idx[i])
ic_,f_,d_=map(lambda x: np.array(x,float), (ic_,f_,d_))
print("temel seri: %d blok (%s -> %s)\n"%(len(f_),zt[0].date(),zt[-1].date()))

def kapi_ne_zaman(f,d,ic,t0i):
    """t0i'den sonra kapinin BOZUK dedigi ilk blok (gun olarak gecikme)."""
    for k in range(max(CS.PENCERE,t0i+1),len(f)+1):
        dur,_=CS.saglik_durumu(list(ic[:k]),list(f[:k]),list(d[:k]))
        if dur=="BOZUK":
            return (k-1-t0i)*5     # blok = 5 gun
    return None

print("MADDE 139'UN OLUM SENARYOLARI, YENI KAPIYLA (IC kapatmiyor)")
print("%-34s%16s%16s"%("senaryo (olum T0 = blok 30)","yakalama","gecikme (gun)"))
T0=30
for ad,don in [("B) prim sikismasi (funding x0.1)", lambda f,d,i: (
                   np.where(np.arange(len(f))>=T0, f*0.1, f),
                   np.where(np.arange(len(d))>=T0, d*0.1, d), ic_)),
               ("B') daha hafif sikisma (x0.25)", lambda f,d,i: (
                   np.where(np.arange(len(f))>=T0, f*0.25, f),
                   np.where(np.arange(len(d))>=T0, d*0.25, d), ic_)),
               ("C) yavas erime (180 gunde sifir)", lambda f,d,i: (
                   f*np.clip(1-np.maximum(0,np.arange(len(f))-T0)/36,0,1),
                   d*np.clip(1-np.maximum(0,np.arange(len(d))-T0)/36,0,1), ic_)),
               ("A) kalicilik olumu (YALNIZ IC coker)", lambda f,d,i: (
                   f,d,np.where(np.arange(len(i))>=T0, 0.0, i)))]:
    fx,dx,icx=don(f_.copy(),d_.copy(),ic_.copy())
    g=kapi_ne_zaman(fx,dx,icx,T0)
    print("%-34s%16s%16s"%(ad,"YAKALADI" if g is not None else "KACIRDI",
                           "-" if g is None else f"{g}"))
print("\nNOT: senaryo A'yi kacirmak KASITLI (madde 234) - madde 139 o")
print("senaryonun getiri faydasini t=-0,55 ile ANLAMSIZ olcmustu, ve IC")
print("esigi 4 yildaki tek yanlis alarmin sebebiydi (+%25,5'lik donemde).")
