import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
E=[("kapali","U0"),("0,20","U0.20"),("0,30","U0.30"),("0,40 (kontrol)","U0.40"),("0,60","U0.60")]
def seri(h):
    es=[pickle.load(open(f'/tmp/m236/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={h:seri(h) for _,h in E}
kon=olc("kontrol",S["U0.40"][0]); kg=S["U0.40"][1]
print("UCELE ESIGI (madde 236) - uc hareket etmis coin KARSI tarafta aday olmasin")
print("%-16s%9s%8s%7s%9s%9s%11s%7s  KARAR"%(
    "esik","yillik","Sharpe","dd","Sh22-24","Sh25-26","esit-risk","kald"))
for ad,h in E:
    if h=="U0.40":
        print("%-16s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  KONTROL"%(
            ad,kon.getiri,kon.sharpe,-kon.dusus,kon.erken,kon.gec,kon.getiri,1.0)); continue
    a=olc(ad,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1])
    print("%-16s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  %s"%(
        ad,a.getiri,a.sharpe,-a.dusus,a.erken,a.gec,s['esit_risk'],s['kaldirac'],
        'GECER' if s['gecer'] else 'RED'))
