import pickle,sys,os,glob,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def gun(pre):
    fs=[f'/tmp/m240/E{pre}_{k}.pkl' for k in (0,1)]
    if not all(os.path.exists(f) for f in fs): return None
    es=[pickle.load(open(f,'rb')).pct_change() for f in fs]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1; v=v[v.index>='2022-01-01']
    return v if len(v)>1400 else None
def oz(v):
    e=(1+v).cumprod(); sh=lambda x:x.mean()/x.std(ddof=1)*np.sqrt(365.25)
    return dict(getiri=(e.iloc[-1]**(365.25/len(v))-1)*100, sharpe=sh(v),
      erken=sh(v[v.index<'2025-01-01']), gec=sh(v[v.index>='2025-01-01']),
      dusus=-(e/e.cummax()-1).min()*100)
GRUP={
 "A) FUNDING SINYAL PENCERESI (saat)":[("W08","8 saat"),("W24","24 saat"),
   ("W36","36 saat"),("W60","60 saat"),("W72","72 saat")],
 "B) FIRSAT REZERVI ESIGI (gunluk)":[("R0.010","%1,0"),("R0.012","%1,2"),
   ("R0.018","%1,8"),("R0.020","%2,0"),("R0.022","%2,2"),("R0.025","%2,5"),("R0.030","%3,0")],
 "C) REZERV COIN KAPI":[("K0.03","%3"),("K0.08","%8"),("K0.15","%15")],
 "D) DONUK SERI ESIGI":[("D0.05","0,05"),("D0.20","0,20"),("D0.30","0,30")],
}
kser=gun('W48')
if kser is None: print("kontrol (W48) henuz yok"); sys.exit(0)
kont=K.Olcum("kontrol",**oz(kser))
for ad,liste in GRUP.items():
    A=[]
    for pre,et in liste:
        v=gun(pre)
        if v is None: continue
        A.append((K.Olcum(et,**oz(v)),v))
    if not A: continue
    print("\n"+"#"*78); print("# "+ad); print("#"*78)
    print("%-14s%8s%8s%7s%7s%8s%11s%8s  %s"%("aday","getiri","Sharpe","22-24","25-26","dusus","esit-risk","kald.","karar"))
    print("%-14s%+8.1f%8.3f%7.3f%7.3f%8.2f%+11.1f%8.2f  KONTROL"%("kontrol",
      kont.getiri,kont.sharpe,kont.erken,kont.gec,-kont.dusus,kont.getiri,1.0))
    for o,v in A:
        r=K.gecer_mi(kont,o,gunluk_kontrol=kser,gunluk_aday=v)
        kal,er,_=K.esit_risk_gercek(v.values,kont.dusus)
        print("%-14s%+8.1f%8.3f%7.3f%7.3f%8.2f%+11.1f%8.2f  %s"%(o.ad,o.getiri,
          o.sharpe,o.erken,o.gec,-o.dusus,er,kal,"KABUL" if r["gecer"] else "RED"))
        if not r["gecer"]:
            print("                 gecmeyen: "+", ".join(k2 for k2,(ok,_) in r["sartlar"].items() if not ok))
