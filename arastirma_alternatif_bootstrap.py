import pickle,sys,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot'); import karar_kurali as K
def gun(p,d='/tmp/m244'):
    es=[pickle.load(open(f'{d}/E{p}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1; return v[v.index>='2022-01-01']
B=gun('W48','/tmp/m240'); S=gun('sk_tt_ters')
ix=B.index.intersection(S.index); B=B.reindex(ix); S=S.reindex(ix)
n=len(B); blok=21; rng=np.random.default_rng(7); nb=(n+blok-1)//blok
sh=lambda r: r.mean()/r.std(ddof=1)*np.sqrt(365.25)
Bv=B.values
print("ESLI BLOK BOOTSTRAP (n=%d, 21 gunluk blok, 2000 ornek)"%n)
print("kol = ust trader KONTRARIAN, kontrol = carry %100\n")
print("%-10s%10s%9s%11s   %12s%9s%9s"%("pay","dSharpe","p5","P(dSh>0)","d esit-risk","p5","P(>0)"))
for w in (0.10,0.20,0.30):
    A=((1-w)*B+w*S).values; ds=[]; de=[]
    for _ in range(2000):
        st=rng.integers(0,n-blok,size=nb)
        j=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
        a=A[j]; b=Bv[j]; ds.append(sh(a)-sh(b))
        _,ddb=K._stat(b)
        if ddb!=ddb or ddb<=0: continue
        de.append(K.esit_risk_gercek(a,ddb*100)[1]-K.esit_risk_gercek(b,ddb*100)[1])
    ds=np.array(ds); de=np.array(de)
    print("%-10s%+10.3f%+9.3f%10.1f%%   %+12.1f%+9.1f%8.1f%%"%("%%%d"%(w*100),ds.mean(),
      np.percentile(ds,5),(ds>0).mean()*100,de.mean(),np.percentile(de,5),(de>0).mean()*100),flush=True)
