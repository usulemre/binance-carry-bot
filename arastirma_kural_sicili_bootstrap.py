"""Sart 1'in gecme olasiligi: iki alt donem Sharpe farkinin ORTAK dagilimi."""
import pickle,sys,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
def gun(f0,f1):
    es=[pickle.load(open(f,'rb')).pct_change() for f in (f0,f1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1; return v[v.index>='2022-01-01']
B=gun('/tmp/m240/EW48_0.pkl','/tmp/m240/EW48_1.pkl')
sh=lambda r: r.mean()/r.std(ddof=1)*np.sqrt(365.25)
ix=B.index; e=ix<'2025-01-01'; g=~e
# KONTROLU KENDISINE KARSI: gunleri blok bootstrap ile yeniden ornekle,
# iki YARIYA ayir -> gercek fark SIFIR olan bir "aday" uret
n=len(B); blok=21; nb=(n+blok-1)//blok; rng=np.random.default_rng(3)
v=B.values
de=[]; dg=[]
for _ in range(4000):
    st=rng.integers(0,n-blok,size=nb)
    j=np.concatenate([np.arange(s,s+blok) for s in st])[:n]
    a=v[j]                      # "aday": ayni dagilimdan yeni bir gerceklesme
    # ayni gun maskeleriyle alt donemlere ayir
    de.append(sh(a[e])-sh(v[e])); dg.append(sh(a[g])-sh(v[g]))
de=np.array(de); dg=np.array(dg)
print("GERCEK FARKI SIFIR OLAN BIR ADAYIN ALT DONEM FARKLARI (4.000 ornek)")
print("  22-24: ort %+.4f  std %.4f  P(>0) %%%.1f"%(de.mean(),de.std(),(de>0).mean()*100))
print("  25-26: ort %+.4f  std %.4f  P(>0) %%%.1f"%(dg.mean(),dg.std(),(dg>0).mean()*100))
print("  iki fark arasi korelasyon: %+.3f"%np.corrcoef(de,dg)[0,1])
print("\n  SART 1'I GECME OLASILIGI (ikisi de >0): %%%.1f"%(((de>0)&(dg>0)).mean()*100))
print("  -> YANLIS RED ORANI: %%%.1f"%(100-((de>0)&(dg>0)).mean()*100))
print("\n  (bagimsiz yazi-tura olsa %25 gecer / %75 red olurdu)")
