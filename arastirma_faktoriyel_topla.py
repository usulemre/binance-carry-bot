import pickle,sys,os,itertools,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def gun(et):
    fs=[f'/tmp/m242/E{et}_{k}.pkl' for k in (0,1)]
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
MERKEZ="T0.40_H3_U0.40_R0.20"
ks=gun(MERKEZ)
if ks is None: print("merkez henuz yok"); sys.exit(0)
kont=K.Olcum("MERKEZ",**oz(ks))
rows=[]
for tpl,hav,uce,rez in itertools.product(("0.40","0.50"),("3","4"),("0.40","0.60"),("0.20","0.30")):
    et=f"T{tpl}_H{hav}_U{uce}_R{rez}"
    v=gun(et)
    if v is None: continue
    o=K.Olcum(et,**oz(v))
    kal,er,_=K.esit_risk_gercek(v.values,kont.dusus)
    r=K.gecer_mi(kont,o,gunluk_kontrol=ks,gunluk_aday=v)
    n=sum(1 for a,b in zip((tpl,hav,uce,rez),("0.40","3","0.40","0.20")) if a!=b)
    rows.append((n,et,o,er,kal,r["gecer"] if et!=MERKEZ else None))
rows.sort(key=lambda t:(-t[3],t[0]))
print("2^4 FAKTORIYEL - esit-risk sirasina gore (merkez = bugunku ayar)")
print("%-26s%4s%9s%8s%7s%7s%8s%11s%7s  %s"%("hucre","dgs","getiri","Sharpe","22-24","25-26","dusus","esit-risk","kald.","karar"))
for n,et,o,er,kal,g in rows:
    ad="MERKEZ" if et==MERKEZ else et.replace("T","TP").replace("_H"," H").replace("_U"," U").replace("_R"," R")
    print("%-26s%4d%+9.1f%8.3f%7.3f%7.3f%8.1f%+11.1f%7.2f  %s"%(ad,n,o.getiri,o.sharpe,
      o.erken,o.gec,-o.dusus,er,kal,"KONTROL" if g is None else ("KABUL" if g else "RED")))
