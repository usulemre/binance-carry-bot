"""MADDE 235 BUTCESI: cikis SEKLI ekseninin tavani ne?

Her secilen bacagin 5 gunluk tutma suresi icindeki EN IYI lehte
hareketini (maksimum favorable excursion) olcer. Bu dagilim, merdiven /
kismi hasat / takip eden cikis ailesinin tavanini belirler.
"""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import carry_denetim as D
from tradfi_liste import TRADFI
P=pickle.load(open('/tmp/panel.pkl','rb')); HL=pickle.load(open('/tmp/hlo.pkl','rb'))
C=P['C']; S2=pickle.load(open('/tmp/sk_bar48.pkl','rb'))
uy=D.uygunluk(P['C'],P['HAC'],P['YAS'],P['DON'],hacim=1e8,yas_bar=540,donuk_esik=0.10).copy()
uy[[c for c in uy.columns if c in TRADFI]]=False
S=S2.reindex(index=C.index,columns=C.columns).values; U=uy.values
cv=C.values; HV=HL['H'].values; LV=HL['L'].values
REB=30; ADIM=2; NL=5; HAVUZ=3
_r6=np.vstack([np.full((6,C.shape[1]),np.nan),cv[6:]/np.where(cv[:-6]>0,cv[:-6],np.nan)-1])
UCELE=0.40
kay=[]   # (taraf, maks lehte hareket)
for bas in range(0,REB,ADIM):                 # 15 dilim
    for i in range(1200+bas,len(C)-REB-1,REB):
        g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]
        a=_r6[i]
        pump=np.isfinite(a)&(a>=UCELE); dump=np.isfinite(a)&(a<=-UCELE)
        sr=np.where(g,S[i],np.nan)
        med=np.nanmedian(sr) if np.isfinite(sr).any() else 0.0
        g=g&~(pump&(sr<med))&~(dump&(sr>med))
        ix=np.flatnonzero(g)
        if len(ix)<30: continue
        v=S[i][ix]; o=np.argsort(v)
        for yon,sec in ((+1,ix[o[:NL]]),(-1,ix[o[-NL:]])):
            for k in sec:
                e=cv[i,k]
                if not (np.isfinite(e) and e>0): continue
                h=HV[i+1:i+REB+1,k]; l=LV[i+1:i+REB+1,k]
                if not np.isfinite(h).any(): continue
                if yon>0: mfe=np.nanmax(h)/e-1
                else:     mfe=1-np.nanmin(l)/e
                if np.isfinite(mfe): kay.append((yon,float(mfe)))
df=pd.DataFrame(kay,columns=['yon','mfe'])
print("SECILEN BACAK SAYISI: %d (LONG %d, SHORT %d), 15 dilim x tum turlar"%(
    len(df),(df.yon>0).sum(),(df.yon<0).sum()))
print("\nTUTMA SURESI ICINDE EN IYI LEHTE HAREKETE DEGME ORANI")
print("%-10s%14s%14s%14s"%("esik","LONG","SHORT","ikisi"))
for e in (0.10,0.15,0.20,0.25,0.30,0.40,0.50,0.60,0.80,1.00):
    a=(df.mfe[df.yon>0]>=e).mean()*100
    b=(df.mfe[df.yon<0]>=e).mean()*100
    c=(df.mfe>=e).mean()*100
    print("%-10s%13.1f%%%13.1f%%%13.1f%%"%(f"+{e*100:.0f}%",a,b,c))
print("\nMEVCUT ESIKLER: LONG %40, SHORT %20  (madde 227'de optimum)")
print("  -> LONG bacaklarin %%%.1f'i +%%40'a degiyor"%((df.mfe[df.yon>0]>=0.40).mean()*100))
print("  -> SHORT bacaklarin %%%.1f'i +%%20'ye degiyor"%((df.mfe[df.yon<0]>=0.20).mean()*100))
print("  (madde 216'nin GERCEKLESEN TP orani: LONG %8,8 / SHORT %18,1)")
print("\nMEDYAN ve KUYRUK")
for ad,m in (("LONG",df.yon>0),("SHORT",df.yon<0)):
    v=df.mfe[m]*100
    print("  %-6s medyan %+6.1f%%  p75 %+6.1f%%  p90 %+7.1f%%  p99 %+8.1f%%"%(
        ad,np.median(v),np.percentile(v,75),np.percentile(v,90),np.percentile(v,99)))
