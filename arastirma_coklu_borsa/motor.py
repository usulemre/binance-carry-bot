"""Gunluk carry motoru - borsadan bagimsiz.
Panel: C (kapanis), H, L, F (gun ici funding odemeleri toplami, uzun pozisyon ODER isaretiyle: long getirisi -F),
        HAC (gunluk USD hacim), U (uygunluk)
Kural (onceden sabit): skor = son 3 gunun funding toplami; en dusuk n LONG, en yuksek n SHORT;
0.5/n agirlik; 5 gun tutma; 5 dilim (faz 0..4); %70 kar al (gunluk yuksek/dusuk); tek yon ucret KOM.
Sinyal gun i kapanisinda, pozisyon gun i+1 kapanisindan itibaren (1 gun gecikme).
"""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import carry_denetim as D

def uygunluk(C,HAC,esik,yas_gun=90,donuk_esik=0.10):
    """Canli botla ayni: SON GUNUN hacmi >= esik, yas >= 90 gun, donuk seri degil (nedensel)."""
    var=C.notna(); yas=var.cumsum().where(var)
    ayni=(C.diff()==0)&var; donuk=ayni.cumsum()/var.cumsum().replace(0,np.nan)
    return var&(HAC>=esik)&(yas>=yas_gun)&(donuk.fillna(0)<donuk_esik)

def bt(P,bas,n,kom,tp=0.7,tut=5,skor=None,gec_gun=1):
    C,H,L,F,U=P['C'].values,P['H'].values,P['L'].values,P['F'].values,P['U'].values
    S=(P['F'].rolling(3,min_periods=3).sum().values if skor is None else skor)
    T,nk=C.shape; poz=np.zeros(nk); gir=np.full(nk,np.nan); eq=[1.0]; bek=None
    for i in range(bas,T-1):
        if (i-bas)%tut==0:
            g=np.isfinite(S[i])&np.isfinite(C[i])&U[i]; ix=np.flatnonzero(g); nn=min(n,len(ix)//2)
            if nn>=min(8,n):
                o=np.argsort(S[i][ix]); y=np.zeros(nk); y[ix[o[:nn]]]=0.5/nn; y[ix[o[-nn:]]]=-0.5/nn; bek=(i+gec_gun,y)
        if bek is not None and bek[0]==i:
            y=bek[1]; eq[-1]*=1-np.abs(y-poz).sum()*kom; poz=y; gir=np.where(y!=0,C[i],np.nan); bek=None
        gec=np.isfinite(C[i])&np.isfinite(C[i+1])&(C[i]>0)
        br=np.where(gec,C[i+1]/np.where(gec,C[i],1)-1,0.0)
        f=np.nan_to_num(F[i+1]); cik=np.zeros(nk,bool)
        if tp>0:
            for k in np.flatnonzero(poz!=0):
                e=gir[k]
                if not (np.isfinite(e) and gec[k] and np.isfinite(H[i+1,k]) and np.isfinite(L[i+1,k])): continue
                if poz[k]>0 and H[i+1,k]>=e*(1+tp): br[k]=e*(1+tp)/C[i,k]-1; cik[k]=True
                elif poz[k]<0 and L[i+1,k]<=e*(1-tp): br[k]=e*(1-tp)/C[i,k]-1; cik[k]=True
        r=np.sum(poz*br)+np.sum(np.where(cik,0.0,-poz*f))
        eq.append(eq[-1]*(1+r))
        if cik.any():
            eq[-1]*=1-np.abs(poz[cik]).sum()*kom; poz=np.where(cik,0.0,poz); gir=np.where(cik,np.nan,gir)
    return pd.Series(eq,index=P['C'].index[bas:])

def dilimli(P,bas,n,kom,tp=0.7,tut=5,skor=None,gec_gun=1):
    g=pd.concat([bt(P,bas+f,n,kom,tp,tut,skor,gec_gun).pct_change() for f in range(tut)],axis=1).mean(axis=1).dropna()
    return (1+g).cumprod()

def ozet_g(e):
    gun=max((e.index[-1]-e.index[0]).days,1); g=e.pct_change().dropna()
    return {'yillik':(max(e.iloc[-1],1e-9)**(365.25/gun)-1)*100,
            'sharpe':float(g.mean()/g.std()*np.sqrt(365.25)) if g.std()>0 else 0.0,
            'maxdd':float(((e/e.cummax())-1).min()*100)}

def rapor(E,bas_tarih='2022-03-01'):
    out={}
    for ad,m in [('tam',E.index>=bas_tarih),('22-24',(E.index>=bas_tarih)&(E.index<'2025-01-01')),('25-26',E.index>='2025-01-01')]:
        e=E[m]; e=e/e.iloc[0]; o=ozet_g(e); out[ad]=(round(o['yillik'],1),round(o['sharpe'],2),round(o['maxdd'],1))
    ay=E[E.index>=bas_tarih].resample('ME').last().pct_change().dropna()
    out['ay_arti']=round((ay>0).mean()*100)
    return out
