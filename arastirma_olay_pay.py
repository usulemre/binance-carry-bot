import pickle,sys,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K
def gun(f0,f1):
    es=[pickle.load(open(f,'rb')).pct_change() for f in (f0,f1)]
    r=pd.concat(es,axis=1).mean(axis=1).dropna()
    v=(1+r).resample('1D').prod().dropna()-1; return v[v.index>='2022-01-01']
CA=gun('/tmp/m240/EW48_0.pkl','/tmp/m240/EW48_1.pkl')
RV=gun('/tmp/m241/EREV_0.pkl','/tmp/m241/EREV_1.pkl')
ix=CA.index.intersection(RV.index); CA=CA.reindex(ix); RV=RV.reindex(ix)
sh=lambda v: v.mean()/v.std(ddof=1)*np.sqrt(365.25)
def oz(v):
    e=(1+v).cumprod()
    return dict(getiri=(e.iloc[-1]**(365.25/len(v))-1)*100, sharpe=sh(v),
      erken=sh(v[v.index<'2025-01-01']), gec=sh(v[v.index>='2025-01-01']),
      dusus=-(e/e.cummax()-1).min()*100)
print("GETIRI KORELASYONU (madde 237'nin olcutu)")
print("  carry vs geri donus (gunluk) = %+.4f"%CA.corr(RV))
print("  (karsilastirma: carry vs momentum = +0,718 -> o da EKLEMEDI)")
print()
kont=K.Olcum("carry %100",**oz(CA))
A=[]; S={}
for w in (0.05,0.10,0.15,0.25,0.50,1.00):
    v=(1-w)*CA+w*RV; ad="geri donus %%%d"%(w*100)
    A.append(K.Olcum(ad,**oz(v))); S[ad]=v
print(K.yaz(kont,A))
print("\nGERCEK KALDIRACLA ESIT RISK (kontrolun dususune eslenmis)")
print("  %-18s%12s%9s"%("dagilim","esit-risk","kald."))
print("  %-18s%+12.1f%9.2f"%("carry %100",kont.getiri,1.00))
for ad,v in S.items():
    kal,er,_=K.esit_risk_gercek(v.values,kont.dusus)
    print("  %-18s%+12.1f%9.2f"%(ad,er,kal))
