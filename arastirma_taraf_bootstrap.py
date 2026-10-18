import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
H=["L3S5","L4S5"]
def g(h,d='/tmp/m230'):
    es=[pickle.load(open(f'{d}/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    return (1+r).resample('1D').prod().dropna()-1
A={h:g(h) for h in H+["L5S5"]}
ix=A["L5S5"].index
for h in H: ix=ix.intersection(A[h].index)
M={h:A[h].reindex(ix).values for h in A}
n=len(ix); blok=21; rng=np.random.default_rng(7); nb=(n+blok-1)//blok
def sh(r): return r.mean()/r.std(ddof=1)*np.sqrt(365.25)
print("ESLI BLOK BOOTSTRAP (n=%d, 2000 ornek), kontrol = 5L/5S"%n)
print("%-8s%10s%8s%8s%10s   %12s%8s%8s%8s"%(
    "aday","dSharpe","p5","p95","P(dSh>0)","d esit-risk","p5","p95","P(>0)"))
for h in H:
    ds=[]; de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        idx=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=M[h][idx]; b=M["L5S5"][idx]
        ds.append(sh(a)-sh(b))
        _,ddb=K._stat(b)
        if ddb!=ddb or ddb<=0: continue
        de.append(K.esit_risk_gercek(a,ddb*100)[1]-K.esit_risk_gercek(b,ddb*100)[1])
    ds=np.array(ds); de=np.array(de)
    print("%-8s%+10.3f%+8.3f%+8.3f%10.2f%%   %+12.1f%+8.1f%+8.1f%8.2f%%"%(
        h,ds.mean(),np.percentile(ds,5),np.percentile(ds,95),(ds>0).mean()*100,
        de.mean(),np.percentile(de,5),np.percentile(de,95),(de>0).mean()*100),flush=True)
