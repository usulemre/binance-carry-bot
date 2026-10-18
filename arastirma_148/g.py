"""Madde 148 deney motoru. Canli ayar: 4s bar, n+n, 5 gun, 5 dilim, %70 kar al, TradFi haric,
%80 funding + %20 akis, maker ucret 2bp. Kancalar:
  agirlik: 'dolar' (canli) | 'beta' (taraflar beta-notr) | 'long60' (long %60 / short %40)
  ek_skor: (ad, matris, agirlik)  -> skor = (1-w)*canli_skor + w*rank(ek)   [ek yuksek = LONG adayi]
"""
import sys, warnings, pickle; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude/binance_bot/binance_bot'); sys.path.insert(0,'/tmp')
import numpy as np, pandas as pd
import carry_denetim as D
from tradfi_liste import TRADFI
P=pickle.load(open('/tmp/panel.pkl','rb')); C,ODE,sk,uy=P['C'],P['ODE'],P['sk'],P['uy']
uy=uy.copy(); uy[[c for c in uy.columns if c in TRADFI]]=False
AK=pickle.load(open('/tmp/akis.pkl','rb')); X=pickle.load(open('/tmp/hlo.pkl','rb'))
cv,fv,U,S,A=C.values,ODE.values,uy.values,sk.values,AK.values
HV,LV=X['H'].values,X['L'].values
KOM=0.0002; REB=30

def rk(v):
    return pd.Series(v).rank(pct=True).values

def bt(bas,n,agirlik='dolar',ek=None,ekw=0.0,BETA=None,tp=0.7):
    nk=C.shape[1]; poz=np.zeros(nk); giris=np.full(nk,np.nan); eq=[1.0]; bek=None
    for i in range(bas,len(C)-1):
        if bek is not None and bek[0]==i:
            y=bek[1]; eq[-1]*=1-np.abs(y-poz).sum()*KOM
            poz=y; giris=np.where(y!=0,cv[i],np.nan); bek=None
        if (i-bas)%REB==0:
            g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]; ix=np.flatnonzero(g); nn=min(n,len(ix)//2)
            if nn>=min(8,n):
                sc=rk(S[i][ix]); a=pd.Series(A[i][ix])
                if a.notna().sum()>=0.5*len(ix): sc=0.8*sc+0.2*(-a).rank(pct=True).fillna(0.5).values
                if ek is not None and ekw>0:
                    e=pd.Series(ek[i][ix])
                    if e.notna().sum()>=0.5*len(ix):
                        # ek yuksek = LONG adayi -> dusuk skor
                        sc=(1-ekw)*sc+ekw*(1-e.rank(pct=True).fillna(0.5).values)
                o=np.argsort(sc); lo=ix[o[:nn]]; sh=ix[o[-nn:]]
                wl,ws=0.5,0.5
                if agirlik=='long60': wl,ws=0.6,0.4
                if agirlik=='beta' and BETA is not None:
                    bl=np.nanmean(np.clip(BETA[i][lo],0.2,3)); bs=np.nanmean(np.clip(BETA[i][sh],0.2,3))
                    if np.isfinite(bl) and np.isfinite(bs): wl,ws=bs/(bl+bs),bl/(bl+bs)
                y=np.zeros(nk); y[lo]=wl/nn; y[sh]=-ws/nn; bek=(i+1,y)
        gec=np.isfinite(cv[i])&np.isfinite(cv[i+1])
        br=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0); br=np.nan_to_num(br)
        cik=np.zeros(nk,bool)
        if tp>0:
            for k in np.flatnonzero(poz!=0):
                e=giris[k]
                if not (np.isfinite(e) and np.isfinite(cv[i,k]) and cv[i,k]>0 and np.isfinite(HV[i+1,k]) and np.isfinite(LV[i+1,k])): continue
                uzun=poz[k]>0; sev=e*(1+tp) if uzun else e*(1-tp)
                if (uzun and HV[i+1,k]>=sev) or ((not uzun) and LV[i+1,k]<=sev):
                    br[k]=sev/cv[i,k]-1; cik[k]=True
        r=np.nansum(poz*br)+np.nansum(np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])))
        eq.append(eq[-1]*(1+r))
        if cik.any():
            eq[-1]*=1-np.abs(poz[cik]).sum()*KOM
            poz=np.where(cik,0.0,poz); giris=np.where(cik,np.nan,giris)
    return pd.Series(eq,index=C.index[bas:])

def calis(ad,n,**k):
    gs=[bt(1200+f,n,**k).pct_change() for f in range(0,REB,6)]
    g=pd.concat(gs,axis=1).mean(axis=1).dropna(); E=(1+g).cumprod()
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E,open(f'/tmp/gE_{ad}_{n}.pkl','wb'))
    print(f'{ad:<22} {n}+{n} | '+' | '.join(out),flush=True)
    return E
