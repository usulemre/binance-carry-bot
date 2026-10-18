import pickle,sys,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot'); import karar_kurali as K
def gun(et):
    es=[pickle.load(open(f'/tmp/m242/E{et}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1; return v[v.index>='2022-01-01']
B=gun("T0.40_H3_U0.40_R0.20")
ADAY={"en uzak kose (4 dgs)":"T0.50_H4_U0.60_R0.30",
      "TP0.50 tek (1 dgs)":"T0.50_H3_U0.40_R0.20",
      "UCELE0.60 tek (1 dgs)":"T0.40_H3_U0.60_R0.20"}
n=len(B); blok=21; rng=np.random.default_rng(7); nb=(n+blok-1)//blok
sh=lambda r: r.mean()/r.std(ddof=1)*np.sqrt(365.25)
Bv=B.values
print("ESLI BLOK BOOTSTRAP (n=%d, 21 gunluk blok, 2000 ornek) - kontrol MERKEZ\n"%n)
print("%-24s%10s%9s%11s   %12s%9s%9s"%("aday","dSharpe","p5","P(dSh>0)","d esit-risk","p5","P(>0)"))
for ad,et in ADAY.items():
    A=gun(et).reindex(B.index).values; ds=[]; de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        ix=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=A[ix]; b=Bv[ix]; ds.append(sh(a)-sh(b))
        _,ddb=K._stat(b)
        if ddb!=ddb or ddb<=0: continue
        de.append(K.esit_risk_gercek(a,ddb*100)[1]-K.esit_risk_gercek(b,ddb*100)[1])
    ds=np.array(ds); de=np.array(de)
    print("%-24s%+10.3f%+9.3f%10.1f%%   %+12.1f%+9.1f%8.1f%%"%(ad,ds.mean(),
      np.percentile(ds,5),(ds>0).mean()*100,de.mean(),np.percentile(de,5),(de>0).mean()*100),flush=True)
