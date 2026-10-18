"""Borsalar arasi funding farki (ayni coin, iki borsa). Onceden sabit kural:
 - aday: iki borsada da uygun (son gun hacmi >= esik, yas >= 90 gun, donuk degil)
 - sinyal: fark = (Binance 3g funding toplami) - (KuCoin 3g funding toplami)
 - en buyuk |fark| olan n coin: yuksek funding'li borsada SHORT, dusuk olanda LONG
 - her bacak 0.5/n (brut 1), 5 gun tutma, 5 dilim, 1 gun gecikme, iki borsada da ucret
 - kar al YOK (pozisyon fiyat riskine karsi korunmus)
"""
import numpy as np,pandas as pd,pickle,sys
sys.path.insert(0,'/tmp/kc')
from motor import uygunluk, rapor

def hizala(bn,kc):
    # KuCoin sembolu -> Binance sembolu
    bcol=set(bn['C'].columns); es={}
    for s in kc['C'].columns:
        b=s[:-5]; b='BTC' if b=='XBT' else b
        for c in (b+'USDT','1000'+b+'USDT','1000000'+b+'USDT'):
            if c in bcol: es[s]=c; break
    ks=list(es); bs=[es[k] for k in ks]
    idx=bn['C'].index.intersection(kc['C'].index)
    A={k:bn[k].reindex(index=idx)[bs].values for k in ('C','F','HAC')}
    B={k:kc[k].reindex(index=idx)[ks].values for k in ('C','F','HAC')}
    return idx,ks,bs,A,B

def bt(idx,A,B,UA,UB,bas,n,komA,komB,tut=5,gec_gun=1,esik_fark=0.0):
    SA=pd.DataFrame(A['F']).rolling(3,min_periods=3).sum().values
    SB=pd.DataFrame(B['F']).rolling(3,min_periods=3).sum().values
    T,nk=A['C'].shape; pa=np.zeros(nk); pb=np.zeros(nk); eq=[1.0]; bek=None
    for i in range(bas,T-1):
        if (i-bas)%tut==0:
            fark=SA[i]-SB[i]
            g=np.isfinite(fark)&UA[i]&UB[i]&np.isfinite(A['C'][i])&np.isfinite(B['C'][i])&(np.abs(fark)>esik_fark)
            ix=np.flatnonzero(g); nn=min(n,len(ix))
            ya=np.zeros(nk); yb=np.zeros(nk)
            if nn>=1:
                sec=ix[np.argsort(-np.abs(fark[ix]))[:nn]]
                w=0.5/n        # sabit bacak buyuklugu: az aday varsa kalan sermaye bos
                ya[sec]=-np.sign(fark[sec])*w; yb[sec]=np.sign(fark[sec])*w
            bek=(i+gec_gun,ya,yb)
        if bek is not None and bek[0]==i:
            _,ya,yb=bek
            eq[-1]*=1-np.abs(ya-pa).sum()*komA-np.abs(yb-pb).sum()*komB
            pa,pb,bek=ya,yb,None
        # bir bacagin fiyati yoksa (delist / veri sonu) ciftin IKI bacagi da kapanir, o bar katkisi 0
        kop=((pa!=0)|(pb!=0))&~(np.isfinite(A['C'][i+1])&np.isfinite(B['C'][i+1])&np.isfinite(A['C'][i])&np.isfinite(B['C'][i]))
        if kop.any():
            eq[-1]*=1-np.abs(pa[kop]).sum()*komA-np.abs(pb[kop]).sum()*komB
            pa=np.where(kop,0.0,pa); pb=np.where(kop,0.0,pb)
        r=0.0
        for p,X in ((pa,A),(pb,B)):
            c0,c1=X['C'][i],X['C'][i+1]
            ok=np.isfinite(c0)&np.isfinite(c1)&(c0>0)
            br=np.where(ok,c1/np.where(ok,c0,1)-1,0.0)
            r+=np.sum(p*br)-np.sum(p*np.nan_to_num(X['F'][i+1]))
        eq.append(eq[-1]*(1+r))
    return pd.Series(eq,index=idx[bas:])

def dilimli(*a,tut=5,**k):
    idx,A,B,UA,UB,bas,n,komA,komB=a
    g=pd.concat([bt(idx,A,B,UA,UB,bas+f,n,komA,komB,tut=tut,**k).pct_change() for f in range(tut)],axis=1).mean(axis=1).dropna()
    return (1+g).cumprod()
