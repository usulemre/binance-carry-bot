import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def g(gn):
    es=[pickle.load(open(f'/tmp/m223/E{gn}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    return (1+r).resample('1D').prod().dropna()-1
A={gn:g(gn) for gn in (3,4,5,6,7)}
ix=A[5].index
for gn in (3,4,6,7): ix=ix.intersection(A[gn].index)
M={gn:A[gn].reindex(ix).values for gn in A}
n=len(ix); blok=21; rng=np.random.default_rng(7)
def sh(r): return r.mean()/r.std(ddof=1)*np.sqrt(365.25)
print(f"BLOK BOOTSTRAP (n={n} gun, blok={blok}g, 2000 ornek) - EŞLİ, ayni gunler")
print(f"{'aday':<6}{'dSharpe':>10}{'p5':>8}{'p95':>8}{'P(dSh>0)':>10}   {'d esit-risk puan':>17}{'p5':>8}{'p95':>8}{'P(>0)':>8}")
nb=(n+blok-1)//blok
for gn in (3,4,6,7):
    ds=[]; de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        idx=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=M[gn][idx]; b=M[5][idx]
        ds.append(sh(a)-sh(b))
        _,dd=K._stat(b)
        if dd!=dd or dd<=0: continue
        ea=K.esit_risk_gercek(a,dd*100)[1]; eb=K.esit_risk_gercek(b,dd*100)[1]
        de.append(ea-eb)
    ds=np.array(ds); de=np.array(de)
    print(f"{gn:<6}{ds.mean():>+10.3f}{np.percentile(ds,5):>+8.3f}{np.percentile(ds,95):>+8.3f}"
          f"{(ds>0).mean():>10.2%}   {de.mean():>+17.1f}{np.percentile(de,5):>+8.1f}"
          f"{np.percentile(de,95):>+8.1f}{(de>0).mean():>8.2%}")
