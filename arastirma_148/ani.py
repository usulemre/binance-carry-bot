"""Madde 159: ANI hareket sonrasi ters donus modulu (carry'den BAGIMSIZ olcum).

Tetik: uygun evrendeki coin 4 saatte >= X kadar duser/cikar.
Islem: TERS yonde, bir sonraki bar KAPANISINDA giris (nedensel), H bar tutma.
Ucret: tek yon 2bp. Ayni anda birden fazla sinyal varsa sermaye bolunur (brut <= 0.2).
Funding de dahil (pozisyon tutuldugu barlarda odenen/alinan).
"""
import sys, warnings, pickle, os; warnings.filterwarnings('ignore')
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import numpy as np, pandas as pd
from g import C,cv,fv,U,S,HV,LV,KOM
import carry_denetim as D

ESIK=float(os.environ.get("ESIK","0.20"))
TUT=int(os.environ.get("TUT","6"))          # bar (6 = 1 gun)
YON=os.environ.get("YON","iki")             # "dus" (dusene al) | "cik" (cikana sat) | "iki"
BRUT=float(os.environ.get("BRUT","0.2"))
TAKIP=int(os.environ.get("TAKIP","0"))  # 1: hareketin YONUNDE git (momentum)
RAST=int(os.environ.get("RAST","0"))        # plasebo: rastgele giris
MAKS=int(os.environ.get("MAKS","6"))
FES=float(os.environ.get("FES","0"))   # >0: hareket sonrasi funding de uc olsun (gunluk)        # ayni anda en fazla kac pozisyon

def calis():
    rng=np.random.default_rng(int(os.environ.get("TOHUM","0")))
    T,nk=C.shape
    poz=np.zeros(nk); kalan=np.zeros(nk,int); eq=[1.0]
    say=0; getiri_kayit=[]
    bar_getiri=(cv[1:]/cv[:-1]-1)
    for i in range(1200,T-1):
        # 1) suresi dolanlari kapat
        bitti=(kalan==1)&(poz!=0)
        if bitti.any():
            eq[-1]*=1-np.abs(poz[bitti]).sum()*KOM
            poz=np.where(bitti,0.0,poz)
        kalan=np.maximum(kalan-1,0)
        # 2) yeni tetikler (bar i-1 -> i hareketi, giris bar i kapanisinda = nedensel)
        hareket=np.where(np.isfinite(cv[i])&np.isfinite(cv[i-1])&(cv[i-1]>0),cv[i]/cv[i-1]-1,0.0)
        uygun=U[i]&np.isfinite(cv[i])&(poz==0)
        if RAST:
            aday=np.flatnonzero(uygun)
            n_t=int((np.abs(hareket)>=ESIK).sum())
            tetik=rng.choice(aday,size=min(n_t,len(aday)),replace=False) if n_t and len(aday) else np.array([],int)
            yonler=rng.choice([-1,1],size=len(tetik))
        else:
            dus=uygun&(hareket<=-ESIK); cik=uygun&(hareket>=ESIK)
            if FES>0:
                dus&=np.nan_to_num(S[i])<=-FES      # dusus + short kalabaligi (funding cok negatif)
                cik&=np.nan_to_num(S[i])>=FES       # sicrama + long kalabaligi
            if YON=="dus": cik=np.zeros(nk,bool)
            if YON=="cik": dus=np.zeros(nk,bool)
            tetik=np.flatnonzero(dus|cik)
            yonler=np.where(dus[tetik],1,-1)
            if TAKIP: yonler=-yonler          # dusene SAT, cikana AL (momentum)
        acik=int((poz!=0).sum())
        if len(tetik) and acik<MAKS:
            tetik=tetik[:MAKS-acik]; yonler=yonler[:len(tetik)]
            w=BRUT/MAKS
            for k,y_ in zip(tetik,yonler):
                poz[k]=y_*w; kalan[k]=TUT; say+=1
            eq[-1]*=1-w*len(tetik)*KOM
        # 3) bar getirisi
        br=np.nan_to_num(bar_getiri[i]) if i<len(bar_getiri) else np.zeros(nk)
        r=float(np.nansum(poz*br)-np.nansum(poz*np.nan_to_num(fv[i+1])))
        eq.append(eq[-1]*(1+r))
    return pd.Series(eq,index=C.index[1200:]),say

if __name__=='__main__':
    E,say=calis()
    yil=(len(C)-1200)/(6*365.25)
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E,open(f'/tmp/aniE_{ESIK}_{TUT}_{YON}_{RAST}_{TAKIP}.pkl','wb'))
    print(f'FES{FES} TAKIP{TAKIP} ESIK{ESIK} TUT{TUT} YON{YON} RAST{RAST} islem/yil {say/yil:.0f} | '+' | '.join(out),flush=True)
