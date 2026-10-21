#!/usr/bin/env python3
# MADDE 418 — cokus sonrasi dip alimi (24 sa <= -X ve 24 sa funding <= -FE -> long, TP veya H gun), gun-kumeli t.
import sys,numpy as np,pandas as pd,pickle
sys.path.insert(0,'/home/claude/binance-carry-bot')
z=pickle.load(open('/tmp/zemin.pkl','rb'));P=pickle.load(open('/tmp/panel.pkl','rb'));hlo=pickle.load(open('/tmp/hlo.pkl','rb'))
C=z['C'];F=z['ODE'].reindex_like(C).fillna(0.0);H=hlo['H'].reindex_like(C);O=hlo['O'].reindex_like(C)
from tradfi_liste import TRADFI
uy=(P['HAC'].reindex_like(C)>=2e7)&(P['YAS'].reindex_like(C)>=30*6)&C.notna(); uy=uy&~uy.columns.isin(list(TRADFI))
r24=C/C.shift(6)-1; f24=F.rolling(6).sum()
cv,hv,ov,fv=C.values,H.values,O.values,F.values
def kos(X,FE,TPv,Hg):
    k=((r24<=-X)&(f24<=-FE)&uy).values; T,N=cv.shape; out=[]
    for j in range(N):
        serb=-1
        for i in np.flatnonzero(k[:,j]):
            if i<=serb or i+1>=T: continue
            g=ov[i+1,j]
            if not np.isfinite(g) or g<=0: continue
            son=min(i+1+Hg*6,T-1); ci,cf=son,cv[son,j]
            hit=np.flatnonzero(hv[i+1:son+1,j]>=g*(1+TPv))
            if len(hit): ci=i+1+hit[0]; cf=g*(1+TPv)
            if not np.isfinite(cf): continue
            r=(cf/g-1)-np.nansum(fv[i+1:ci+1,j])-0.001
            out.append((C.index[i],r)); serb=ci
    return out
print(f"{'X':>4} {'fon':>6} {'TP':>4} {'H':>2} | {'nIS':>4} {'gunIS':>5} {'ortIS%':>7} {'gun-tIS':>7} | {'nOOS':>4} {'gunOOS':>6} {'ortOOS%':>7} {'medOOS%':>7} {'gun-tOOS':>8} {'kazan%':>6}")
for X in (0.30,0.40):
  for FE in (0.003,0.01):
    for TPv,Hg in ((0.40,5),(0.25,3)):
      o=kos(X,FE,TPv,Hg)
      if len(o)<10: continue
      t=pd.DatetimeIndex([a for a,_ in o]); v=np.array([b for _,b in o])
      res=[]
      for m in (t<'2025-01-01',t>='2025-01-01'):
          vv=v[m]; g=pd.Series(vv).groupby(t[m].floor('D')).mean()
          res.append((len(vv),len(g),vv.mean()*100 if len(vv) else np.nan,np.median(vv)*100 if len(vv) else np.nan,g.mean()/g.std()*np.sqrt(len(g)) if len(g)>2 else np.nan,(vv>0).mean()*100 if len(vv) else np.nan))
      a,b=res
      print(f"{X:>4} {FE:>6} {TPv:>4} {Hg:>2} | {a[0]:>4} {a[1]:>5} {a[2]:>+7.2f} {a[4]:>+7.2f} | {b[0]:>4} {b[1]:>6} {b[2]:>+7.2f} {b[3]:>+7.2f} {b[4]:>+8.2f} {b[5]:>6.0f}",flush=True)
