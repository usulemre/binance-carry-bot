import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D

def seri(g):
    es=[pickle.load(open(f'/tmp/m223/E{g}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()          # 4 saatlik (motor birimi)
    rg=(1+r4).resample('1D').prod().dropna()-1             # gunluk (esit-risk icin)
    return r4, rg

def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],
                   D.ozet(ea/ea.iloc[0])['sharpe'], D.ozet(eb/eb.iloc[0])['sharpe'],
                   abs(o['maxdd']))

S={g:seri(g) for g in (3,4,5,6,7)}
kon=olc('5g',S[5][0]); kg=S[5][1]
print(f"KONTROL  5 gun / 15 dilim : {kon.getiri:+.1f}%  Sh {kon.sharpe:.3f}  dd -{kon.dusus:.1f}"
      f"  | 22-24 {kon.erken:.3f}  25-26 {kon.gec:.3f}")
print(f"\n{'gun':<4}{'dilim':>6}{'yillik':>9}{'Sharpe':>8}{'dd':>7}{'Sh22-24':>9}{'Sh25-26':>9}{'esit-risk':>11}{'kald':>7}  KARAR")
sonuc={}
for g in (3,4,6,7):
    a=olc(f'{g}g',S[g][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[g][1])
    sonuc[g]=(a,s)
    print(f"{g:<4}{g*3:>6}{a.getiri:>+9.1f}{a.sharpe:>8.3f}{-a.dusus:>7.1f}{a.erken:>9.3f}{a.gec:>9.3f}"
          f"{s['esit_risk']:>+11.1f}{s['kaldirac']:>7.2f}  {'GECER' if s['gecer'] else 'RED'}")
print("\nSARTLAR (on-kayitli kural, madde 212/218):")
for g in (3,4,6,7):
    a,s=sonuc[g]; print(f"  {g} gun -> {s['gerekce']}")
    for ad,(ok,aci) in s['sartlar'].items():
        print(f"      [{'OK ' if ok else 'RED'}] {ad:<20} {aci}")
