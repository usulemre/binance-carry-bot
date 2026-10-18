import pickle,sys,os,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot'); import karar_kurali as K
def gun(p,d='/tmp/m246'):
    fs=[f'{d}/E{p}_{k}.pkl' for k in (0,1)]
    if not all(os.path.exists(f) for f in fs): return None
    es=[pickle.load(open(f,'rb')).pct_change() for f in fs]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1; v=v[v.index>='2022-01-01']
    return v if len(v)>1400 else None
sh=lambda v: v.mean()/v.std(ddof=1)*np.sqrt(365.25)
def oz(v):
    e=(1+v).cumprod()
    return dict(getiri=(e.iloc[-1]**(365.25/len(v))-1)*100, sharpe=sh(v),
      erken=sh(v[v.index<'2025-01-01']), gec=sh(v[v.index>='2025-01-01']),
      dusus=-(e/e.cummax()-1).min()*100)
ks=gun('W48','/tmp/m240'); kont=K.Olcum("KONTROL (medyan 48sa)",**oz(ks))
print("%-26s%9s%8s%8s%8s%8s%12s%7s  %s"%("aday","getiri","Sharpe","22-24","25-26","dusus","esit-risk","kald.","karar"))
print("%-26s%+9.1f%8.3f%8.3f%8.3f%8.1f%+12.1f%7.2f  KONTROL"%("KONTROL medyan 48sa",
  kont.getiri,kont.sharpe,kont.erken,kont.gec,-kont.dusus,kont.getiri,1.0))
for p,ad in [("sk_ode24","ODE toplam 24sa"),("sk_ode48","ODE toplam 48sa"),
             ("sk_ode72","ODE toplam 72sa"),("sk_ode120","ODE toplam 120sa")]:
    v=gun(p)
    if v is None: continue
    ix=ks.index.intersection(v.index); v=v.reindex(ix)
    o=K.Olcum(ad,**oz(v)); kal,er,_=K.esit_risk_gercek(v.values,kont.dusus)
    r=K.gecer_mi(kont,o,gunluk_kontrol=ks.reindex(ix),gunluk_aday=v)
    print("%-26s%+9.1f%8.3f%8.3f%8.3f%8.1f%+12.1f%7.2f  %s"%(ad,o.getiri,o.sharpe,
      o.erken,o.gec,-o.dusus,er,kal,"KABUL" if r["gecer"] else "RED"))
