import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def gun(pre):
    es=[pickle.load(open(f'/tmp/m239/E{pre}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1
    return v[v.index>='2022-01-01']
ADAY=[("e0.5 ref180","P_e05"),("e1.0 ref180","P_e10"),("e1.5 ref180","P_e15"),
      ("e1.0 ust2.0","P_ust20"),("PLASEBO ters","P_PLASEBO_ters")]
B=gun('U5'); ix=B.index
S={ad:gun(p) for ad,p in ADAY}
for v in S.values(): ix=ix.intersection(v.index)
Bv=B.reindex(ix).values; Sv={a:v.reindex(ix).values for a,v in S.items()}
n=len(ix); blok=21; rng=np.random.default_rng(7); nb=(n+blok-1)//blok
sh=lambda r: r.mean()/r.std(ddof=1)*np.sqrt(365.25)
print("ESLI BLOK BOOTSTRAP (n=%d gun, 21 gunluk blok, 2000 ornek)"%n)
print("kontrol = prim olceklemesi YOK\n")
print("%-15s%10s%8s%8s%10s   %12s%8s%8s%8s"%(
 "aday","dSharpe","p5","p95","P(dSh>0)","d esit-risk","p5","p95","P(>0)"))
for ad in Sv:
    A=Sv[ad]; ds=[]; de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        idx=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=A[idx]; b=Bv[idx]; ds.append(sh(a)-sh(b))
        _,ddb=K._stat(b)
        if ddb!=ddb or ddb<=0: continue
        de.append(K.esit_risk_gercek(a,ddb*100)[1]-K.esit_risk_gercek(b,ddb*100)[1])
    ds=np.array(ds); de=np.array(de)
    print("%-15s%+10.3f%+8.3f%+8.3f%9.1f%%   %+12.1f%+8.1f%+8.1f%8.1f%%"%(
      ad,ds.mean(),np.percentile(ds,5),np.percentile(ds,95),(ds>0).mean()*100,
      de.mean(),np.percentile(de,5),np.percentile(de,95),(de>0).mean()*100),flush=True)
