import pickle, glob, sys, os, numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import carry_denetim as D, karar_kurali as K
# madde 222-230 boyunca olculen TUM yapilandirmalar
kayit=[]
tanim={
 '/tmp/m224/E%s_%%d.pkl':[('1.0','havuz 1,0'),('1.5','havuz 1,5'),('2','havuz 2,0'),
   ('3','havuz 3,0 (KONTROL)'),('4','havuz 4,0'),('5','havuz 5,0')],
 '/tmp/m225/E%s_%%d.pkl':[('0','rezerv 0'),('0.10','rezerv 0,10'),('0.30','rezerv 0,30'),('0.40','rezerv 0,40')],
 '/tmp/m226/E%s_%%d.pkl':[('50000000','hacim 50M'),('150000000','hacim 150M'),('200000000','hacim 200M')],
 '/tmp/m227/E%s_%%d.pkl':[('L25S20','TP 0,25/0,20'),('L30S20','TP 0,30/0,20'),('L50S20','TP 0,50/0,20'),
   ('L60S20','TP 0,60/0,20'),('L40S10','TP 0,40/0,10'),('L40S15','TP 0,40/0,15'),('L40S30','TP 0,40/0,30')],
 '/tmp/m228/E%s_%%d.pkl':[('A00Y90','akis %0'),('A10Y90','akis %10'),('A30Y90','akis %30'),('A40Y90','akis %40'),
   ('A20Y30','yas 30g'),('A20Y180','yas 180g'),('A20Y270','yas 270g')],
 '/tmp/m229/E%s_%%d.pkl':[('DOLDUR','koltuk DOLDUR'),('AYNI','koltuk AYNI'),('TERS','koltuk TERS')],
 '/tmp/m230/E%s_%%d.pkl':[('L3S5','3L/5S'),('L4S5','4L/5S'),('L7S5','7L/5S'),('L5S8','5L/8S'),
   ('L5S10','5L/10S'),('L3S8','3L/8S')],
}
for sab,liste in tanim.items():
    for kod,ad in liste:
        try:
            es=[pickle.load(open((sab%kod)%k,'rb')).pct_change() for k in (0,1)]
        except Exception: continue
        r=pd.concat(es,axis=1).mean(axis=1).dropna()
        e=(1+r).cumprod(); o=D.ozet(e)
        gun=(1+r).resample('1D').prod().dropna()-1
        kayit.append((ad,o['yillik'],o['sharpe'],abs(o['maxdd']),gun.values))
# kontrol
es=[pickle.load(open(f'/tmp/m230/EL5S5_{k}.pkl','rb')).pct_change() for k in (0,1)]
r=pd.concat(es,axis=1).mean(axis=1).dropna(); e=(1+r).cumprod(); o=D.ozet(e)
kg=((1+r).resample('1D').prod().dropna()-1).values
_,ddk=K._stat(kg)
kayit.append(("5L/5S (KONTROL)",o['yillik'],o['sharpe'],abs(o['maxdd']),kg))
print("MADDE 222-230: OLCULEN TUM YAPILANDIRMALAR, ESIT RISKTE")
print("(hepsi kontrolun dususune getirildi; %d yapilandirma)\n"%len(kayit))
print("%-24s%10s%9s%9s%13s"%("yapilandirma","yillik","Sharpe","dusus","ESIT-RISK"))
sat=[]
for ad,y,s,d,gun in kayit:
    er=K.esit_risk_gercek(gun,ddk*100)[1]
    sat.append((er,ad,y,s,d))
for er,ad,y,s,d in sorted(sat,reverse=True):
    isaret="  <-- EN IYI" if ad.startswith("5L/5S") else ""
    print("%-24s%+10.1f%9.3f%9.1f%+13.1f%s"%(ad,y,s,-d,er,isaret))
sh=[s for _,_,_,s,_ in sorted(sat,reverse=True)]
print("\nSharpe dagilimi: en yuksek %.3f, en dusuk %.3f, medyan %.3f"%(max(sh),min(sh),np.median(sh)))
