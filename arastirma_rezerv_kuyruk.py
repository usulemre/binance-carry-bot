import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def g(h):
    es=[pickle.load(open(f'/tmp/m225/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    return (1+r).resample('1D').prod().dropna()-1
A={h:g(h) for h in ("0.20","0.30","0.40")}
ix=A["0.20"].index
for h in A: ix=ix.intersection(A[h].index)
M={h:A[h].reindex(ix).values for h in A}
# tam donemde AYNI dususe getiren gercek kaldirac
_,dd0=K._stat(M["0.20"])
kal={h:(1.0 if h=="0.20" else K.esit_risk_gercek(M[h],dd0*100)[0]) for h in M}
print("tam donem esit-risk kaldiraclari:", {h:round(v,3) for h,v in kal.items()})
n=len(ix); blok=21; nb=(365+blok-1)//blok; rng=np.random.default_rng(11)
print("\n1 YILLIK PENCERE BOOTSTRAP (4000 ornek, kaldiracli seriler):")
print("%-8s%7s%12s%10s%10s%10s%10s"%("rezerv","kald","getiri ort","getiri p5","dusus p5","dusus p1","en kotu"))
for h in ("0.20","0.30","0.40"):
    r=M[h]*kal[h]; gs=[]; ds=[]
    for _ in range(4000):
        st=rng.integers(0,n-blok,size=nb)
        idx=np.concatenate([np.arange(s,s+blok) for s in st])[:365]
        e=np.cumprod(1+r[idx]); gs.append(e[-1]-1)
        ds.append(-(e/np.maximum.accumulate(e)-1).min())
    gs=np.array(gs)*100; ds=np.array(ds)*100
    print("%-8s%7.2f%+12.1f%+10.1f%10.1f%10.1f%10.1f"%(
        h,kal[h],gs.mean(),np.percentile(gs,5),-np.percentile(ds,95),
        -np.percentile(ds,99),-ds.max()))
