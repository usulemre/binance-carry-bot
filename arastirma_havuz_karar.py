import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
H=['1.0','1.5','2','3','4','5']
def seri(h):
    es=[pickle.load(open(f'/tmp/m224/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={h:seri(h) for h in H}
kon=olc('3',S['3'][0]); kg=S['3'][1]
print(f"KONTROL havuz 3,0: {kon.getiri:+.1f}%  Sh {kon.sharpe:.3f}  dd -{kon.dusus:.1f}"
      f"  | 22-24 {kon.erken:.3f}  25-26 {kon.gec:.3f}")
print(f"\n{'havuz':<7}{'yillik':>9}{'Sharpe':>8}{'dd':>7}{'Sh22-24':>9}{'Sh25-26':>9}{'esit-risk':>11}{'kald':>7}  KARAR")
res={}
for h in H:
    if h=='3':
        print(f"{h:<7}{kon.getiri:>+9.1f}{kon.sharpe:>8.3f}{-kon.dusus:>7.1f}{kon.erken:>9.3f}{kon.gec:>9.3f}"
              f"{kon.getiri:>+11.1f}{1.0:>7.2f}  KONTROL"); continue
    a=olc(h,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1]); res[h]=(a,s)
    print(f"{h:<7}{a.getiri:>+9.1f}{a.sharpe:>8.3f}{-a.dusus:>7.1f}{a.erken:>9.3f}{a.gec:>9.3f}"
          f"{s['esit_risk']:>+11.1f}{s['kaldirac']:>7.2f}  {'GECER' if s['gecer'] else 'RED'}")
print("\nSARTLAR:")
for h in ('2','4','5'):
    a,s=res[h]; print(f"  havuz {h} -> {s['gerekce']}")
    for ad,(ok,aci) in s['sartlar'].items(): print(f"      [{'OK ' if ok else 'RED'}] {ad:<20} {aci}")
print("\nFAZ YAYILIMI (iki faz arasi yillik getiri farki, madde 184 olcutu):")
for h in H:
    v=[]
    for k in (0,1):
        e=(1+pickle.load(open(f'/tmp/m224/E{h}_{k}.pkl','rb')).pct_change().dropna()).cumprod()
        v.append(D.ozet(e)['yillik'])
    print(f"  havuz {h:<5} faz0 {v[0]:+7.1f}%  faz1 {v[1]:+7.1f}%   yayilim {abs(v[0]-v[1]):5.1f} puan")
