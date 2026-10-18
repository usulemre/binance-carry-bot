import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
H=['1.5','2','4','5']
def g(h):
    es=[pickle.load(open(f'/tmp/m224/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    return (1+r).resample('1D').prod().dropna()-1
A={h:g(h) for h in H+['3']}
ix=A['3'].index
for h in H: ix=ix.intersection(A[h].index)
M={h:A[h].reindex(ix).values for h in A}
n=len(ix); blok=21; rng=np.random.default_rng(7); nb=(n+blok-1)//blok
def sh(r): return r.mean()/r.std(ddof=1)*np.sqrt(365.25)
print(f"ESLI BLOK BOOTSTRAP (n={n}, blok={blok}g, 2000 ornek), kontrol = havuz 3,0")
print(f"{'havuz':<7}{'dSharpe':>10}{'p5':>8}{'p95':>8}{'P(dSh>0)':>10}   {'d esit-risk':>12}{'p5':>8}{'p95':>8}{'P(>0)':>8}")
for h in H:
    ds=[];de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        idx=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=M[h][idx]; b=M['3'][idx]
        ds.append(sh(a)-sh(b))
        _,dd=K._stat(b)
        if dd!=dd or dd<=0: continue
        de.append(K.esit_risk_gercek(a,dd*100)[1]-K.esit_risk_gercek(b,dd*100)[1])
    ds=np.array(ds); de=np.array(de)
    print(f"{h:<7}{ds.mean():>+10.3f}{np.percentile(ds,5):>+8.3f}{np.percentile(ds,95):>+8.3f}{(ds>0).mean():>10.2%}"
          f"   {de.mean():>+12.1f}{np.percentile(de,5):>+8.1f}{np.percentile(de,95):>+8.1f}{(de>0).mean():>8.2%}",flush=True)
