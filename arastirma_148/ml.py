"""Madde 152: makine ogrenmesiyle siralama, walk-forward.

Hedef: pozisyonun 5 gunluk getirisi (long tarafi icin) = fiyat degisimi + alinan funding.
Model her 90 gunde bir YENIDEN egitilir, sadece o ana kadarki veriyle; hedef 5 gunluk
oldugu icin egitim verisinin son 30 bari (5 gun) ATILIR - yoksa sizinti olur.
Secim: model skoru en yuksek n LONG, en dusuk n SHORT (skor = beklenen long getirisi).
Motor geri kalan her seyde canli ayarla ayni (5 dilim, %70 kar al, maker, TradFi haric).
"""
import sys, os, warnings, pickle; warnings.filterwarnings('ignore')
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import numpy as np, pandas as pd
from g import C,ODE,sk,uy,AK,cv,fv,U,S,A,HV,LV,KOM,REB,rk
import carry_denetim as D
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

M=pickle.load(open('/tmp/metrik_panel.pkl','rb'))
PR=pickle.load(open('/tmp/prem.pkl','rb'))
V=pickle.load(open('/tmp/V.pkl','rb'))
Lg=np.log(M['count_long_short_ratio']).values
Lt=np.log(M['sum_toptrader_long_short_ratio']).values
OI=M['sum_open_interest_value']; dOI=(OI/OI.shift(6)-1).values
PRm=PR.rolling(6,min_periods=3).mean().values
V1=V.rolling(6,min_periods=6).sum(); HP=(V1/(V.rolling(180,min_periods=120).mean()*6)).values
MOM=(C/C.shift(30)-1).values
OYN=(C.pct_change().rolling(180,min_periods=90).std()*np.sqrt(6*365)).values
AD=['funding','akis','ls','top','doi','premium','hacim_patlama','momentum','oynaklik']

def ozellik(i,ix):
    """Kesitsel YUZDELIK SIRA (borsa genelindeki seviyeden bagimsiz)."""
    ham=[S[i][ix],-A[i][ix],-Lg[i][ix],-Lt[i][ix],dOI[i][ix],PRm[i][ix],HP[i][ix],MOM[i][ix],OYN[i][ix]]
    X=np.column_stack([pd.Series(h).rank(pct=True).fillna(0.5).values for h in ham])
    return X

def hedef(i,ix,ileri=30):
    """i barinda acilan LONG pozisyonun 5 gunluk getirisi (fiyat + funding)."""
    j=min(i+ileri,len(C)-1)
    p=cv[j][ix]/cv[i][ix]-1
    f=-np.nansum(np.nan_to_num(fv[i+1:j+1])[:,ix],axis=0)
    return p+f

def veri_kur():
    Xs,ys,ts=[],[],[]
    for i in range(300,len(C)-31,6):     # her gun bir kesit
        g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]
        ix=np.flatnonzero(g)
        if len(ix)<20: continue
        X=ozellik(i,ix); y=hedef(i,ix)
        ok=np.isfinite(y)&np.isfinite(X).all(axis=1)
        if ok.sum()<20: continue
        Xs.append(X[ok]); ys.append(y[ok]); ts.append(np.full(ok.sum(),i))
    return np.vstack(Xs),np.concatenate(ys),np.concatenate(ts)

def modeli_kur(ad):
    if ad=='ridge': return Ridge(alpha=10.0)
    return HistGradientBoostingRegressor(max_depth=3,max_iter=200,learning_rate=0.05,
                                         min_samples_leaf=200,l2_regularization=1.0,random_state=0)

def skor_paneli(ad='gbm',yenile=540,min_egitim=180*6):
    """Her bar icin model skoru (walk-forward). yenile: kac barda bir yeniden egitim."""
    X,y,t=veri_kur()
    SK=np.full(C.shape,np.nan)
    model=None; son_egitim=-10**9
    for i in range(1200,len(C)-1,6):
        if i-son_egitim>=yenile:
            m=t<=i-30          # 5 gunluk hedef sizmasin
            if m.sum()>=min_egitim:
                model=modeli_kur(ad); model.fit(X[m],y[m]); son_egitim=i
        if model is None: continue
        g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]; ix=np.flatnonzero(g)
        if len(ix)<16: continue
        Xi=ozellik(i,ix); ok=np.isfinite(Xi).all(axis=1)
        if ok.sum()<16: continue
        SK[i,ix[ok]]=model.predict(Xi[ok])
    return SK

def bt(bas,n,SK,tp=0.7):
    nk=C.shape[1]; poz=np.zeros(nk); giris=np.full(nk,np.nan); eq=[1.0]; bek=None
    for i in range(bas,len(C)-1):
        if bek is not None and bek[0]==i:
            y=bek[1]; eq[-1]*=1-np.abs(y-poz).sum()*KOM
            poz=y; giris=np.where(y!=0,cv[i],np.nan); bek=None
        if (i-bas)%REB==0:
            g=np.isfinite(SK[i])&np.isfinite(cv[i])&U[i]; ix=np.flatnonzero(g); nn=min(n,len(ix)//2)
            if nn>=min(8,n):
                o=np.argsort(-SK[i][ix])          # yuksek beklenen getiri -> LONG
                y=np.zeros(nk); y[ix[o[:nn]]]=0.5/nn; y[ix[o[-nn:]]]=-0.5/nn; bek=(i+1,y)
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

if __name__=='__main__':
    ad=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 12
    SK=skor_paneli(ad)
    pickle.dump(SK,open(f'/tmp/mlSK_{ad}.pkl','wb'))
    gs=[bt(1200+f,n,SK).pct_change() for f in range(0,REB,6)]
    g=pd.concat(gs,axis=1).mean(axis=1).dropna(); E=(1+g).cumprod()
    pickle.dump(E,open(f'/tmp/mlE_{ad}_{n}.pkl','wb'))
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    print(f'ML-{ad:<6} {n}+{n} | '+' | '.join(out),flush=True)
