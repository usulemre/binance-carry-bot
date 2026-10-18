"""MADDE 239: vade merdiveni icin esli blok bootstrap."""
import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def gu(g):
    es=[pickle.load(open(f'/tmp/m239/EU{g}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    return (1+r).resample('1D').prod().dropna()-1
D=pd.DataFrame({g:gu(g) for g in (2,3,5)}).dropna(); D=D[D.index>='2022-01-01']
ADAY={"merd 25/75":0.25,"merd 33/67":1/3,"merd 50/50":0.5,"merd 100/0 (2g tek)":1.0}
n=len(D); blok=21; rng=np.random.default_rng(7); nb=(n+blok-1)//blok
B=D[5].values
def sh(r): return r.mean()/r.std(ddof=1)*np.sqrt(365.25)
print("ESLI BLOK BOOTSTRAP (n=%d gun, 21 gunluk blok, 2000 ornek)"%n)
print("kontrol = 5 gun TEK ufuk\n")
print("%-20s%10s%8s%8s%11s   %12s%8s%8s%8s"%(
 "aday","dSharpe","p5","p95","P(dSh>0)","d esit-risk","p5","p95","P(>0)"))
for ad,w in ADAY.items():
    A=((1-w)*D[5]+w*D[2]).values
    ds=[]; de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        idx=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=A[idx]; b=B[idx]
        ds.append(sh(a)-sh(b))
        _,ddb=K._stat(b)
        if ddb!=ddb or ddb<=0: continue
        de.append(K.esit_risk_gercek(a,ddb*100)[1]-K.esit_risk_gercek(b,ddb*100)[1])
    ds=np.array(ds); de=np.array(de)
    print("%-20s%+10.3f%+8.3f%+8.3f%10.1f%%   %+12.1f%+8.1f%+8.1f%8.1f%%"%(
      ad,ds.mean(),np.percentile(ds,5),np.percentile(ds,95),(ds>0).mean()*100,
      de.mean(),np.percentile(de,5),np.percentile(de,95),(de>0).mean()*100),flush=True)
