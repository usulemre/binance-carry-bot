import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
E=["L3S5","L4S5","L5S5","L7S5","L5S8","L5S10","L3S8"]
def seri(h):
    es=[pickle.load(open(f'/tmp/m230/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={h:seri(h) for h in E}
kon=olc("5L/5S",S["L5S5"][0]); kg=S["L5S5"][1]
print("TARAF BAZLI BACAK SAYISI (madde 230)")
print("%-8s%9s%8s%7s%9s%9s%11s%7s  KARAR"%(
    "L/S","yillik","Sharpe","dd","Sh22-24","Sh25-26","esit-risk","kald"))
res={}
for h in E:
    ad=h[1]+"L/"+h[3:]+"S" if len(h)==4 else h[1]+"L/"+h[3:]+"S"
    if h=="L5S5":
        print("%-8s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  KONTROL"%(
            ad,kon.getiri,kon.sharpe,-kon.dusus,kon.erken,kon.gec,kon.getiri,1.0)); continue
    a=olc(ad,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1]); res[h]=(a,s)
    print("%-8s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  %s"%(
        ad,a.getiri,a.sharpe,-a.dusus,a.erken,a.gec,s['esit_risk'],s['kaldirac'],
        'GECER' if s['gecer'] else 'RED'))
print("\nSARTLAR (esit riskte kontrolu GECEN adaylar):")
for h in E:
    if h=="L5S5": continue
    a,s=res[h]
    if s['esit_risk']>kon.getiri:
        print(f"  {h} -> {s['gerekce']}")
        for k2,(ok,aci) in s['sartlar'].items(): print(f"      [{'OK ' if ok else 'RED'}] {k2:<22} {aci}")
