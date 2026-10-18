import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
E=["L25S20","L30S20","L40S20","L50S20","L60S20","L40S10","L40S15","L40S30"]
def seri(h):
    es=[pickle.load(open(f'/tmp/m227/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={h:seri(h) for h in E}
kon=olc("L40S20",S["L40S20"][0]); kg=S["L40S20"][1]
print(f"KONTROL TPL 0,40 / TPS 0,20: {kon.getiri:+.1f}%  Sh {kon.sharpe:.3f}  dd -{kon.dusus:.1f}"
      f"  | 22-24 {kon.erken:.3f}  25-26 {kon.gec:.3f}")
print("\n%-9s%9s%8s%7s%9s%9s%11s%7s  KARAR"%(
    "TPL/TPS","yillik","Sharpe","dd","Sh22-24","Sh25-26","esit-risk","kald"))
res={}
for h in E:
    ad=f"{h[1:3]}/{h[4:6]}"
    if h=="L40S20":
        print("%-9s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  KONTROL"%(
            ad,kon.getiri,kon.sharpe,-kon.dusus,kon.erken,kon.gec,kon.getiri,1.0)); continue
    a=olc(ad,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1]); res[h]=(a,s)
    print("%-9s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  %s"%(
        ad,a.getiri,a.sharpe,-a.dusus,a.erken,a.gec,s['esit_risk'],s['kaldirac'],
        'GECER' if s['gecer'] else 'RED'))
print("\nGECEN/YAKIN ADAYLARIN SARTLARI:")
for h in E:
    if h=="L40S20": continue
    a,s=res[h]
    if s['gecer'] or s['esit_risk']>kon.getiri:
        print(f"  {h} -> {s['gerekce']}")
        for k2,(ok,aci) in s['sartlar'].items(): print(f"      [{'OK ' if ok else 'RED'}] {k2:<22} {aci}")
