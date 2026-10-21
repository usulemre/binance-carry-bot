#!/usr/bin/env python3
# MADDE 398 — kullanicinin cockpit ekranindan: pump/dump x funding isareti olay calismasi (gun-kumeli t).
import sys,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance-carry-bot'); import arastirma_m395_olay_tarama as A
C,Fd,HAC,uy,m=A.panel(); r1=C/C.shift(1)-1; f8=Fd/3
bas=C.index.get_indexer([pd.Timestamp('2022-04-01')],method='bfill')[0]
ev={}
for X in (0.20,0.30,0.50):
    ev[f"PUMP+{int(X*100)} f<0 LONG"]=((r1>=X)&(f8<0),+1)
    ev[f"PUMP+{int(X*100)} f>0 SHORT"]=((r1>=X)&(f8>0),-1)
for X in (0.15,0.25):
    ev[f"DUMP-{int(X*100)} f>0 SHORT"]=((r1<=-X)&(f8>0),-1)
    ev[f"DUMP-{int(X*100)} f<0 LONG"]=((r1<=-X)&(f8<0),+1)
print(f"{'olay':<24} {'H':>2} | {'nIS':>4} {'gunIS':>5} {'ortIS%':>7} {'gun-tIS':>7} | {'nOOS':>4} {'gunOOS':>6} {'ortOOS%':>7} {'medOOS%':>7} {'gun-tOOS':>8} {'p5OOS%':>7}")
for ad,(k,d) in ev.items():
    k=(k&uy).fillna(False)
    for H in (1,3,7):
        isl=[x for x in A.islemler(k,d,C,Fd,H) if x[0]>=bas]
        if len(isl)<20: continue
        t=pd.DatetimeIndex([C.index[x[0]] for x in isl]); v=np.array([x[2] for x in isl])
        out=[]
        for mm in (t<'2025-01-01',t>='2025-01-01'):
            vv=v[mm]; g=pd.Series(vv).groupby(t[mm].floor('D')).mean()
            tg=g.mean()/g.std()*np.sqrt(len(g)) if len(g)>2 else np.nan
            out.append((len(vv),len(g),vv.mean()*100 if len(vv) else np.nan,np.median(vv)*100 if len(vv) else np.nan,tg,np.percentile(vv,5)*100 if len(vv) else np.nan))
        a,b=out
        print(f"{ad:<24} {H:>2} | {a[0]:>4} {a[1]:>5} {a[2]:>+7.2f} {a[4]:>+7.2f} | {b[0]:>4} {b[1]:>6} {b[2]:>+7.2f} {b[3]:>+7.2f} {b[4]:>+8.2f} {b[5]:>+7.1f}",flush=True)
