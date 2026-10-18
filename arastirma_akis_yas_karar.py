import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
G1=[("akış %0","A00Y90"),("akış %10","A10Y90"),("akış %20 (kontrol)","A20Y90"),
    ("akış %30","A30Y90"),("akış %40","A40Y90")]
G2=[("yaş 30g","A20Y30"),("yaş 90g (kontrol)","A20Y90"),("yaş 180g","A20Y180"),("yaş 270g","A20Y270")]
def seri(h):
    es=[pickle.load(open(f'/tmp/m228/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={}
for _,h in G1+G2: S.setdefault(h,seri(h))
kon=olc("kontrol",S["A20Y90"][0]); kg=S["A20Y90"][1]
for baslik,G in [("EMİR AKIŞI AĞIRLIĞI (madde 117)",G1),("LİSTELEME YAŞI (madde 133)",G2)]:
    print(f"\n== {baslik} ==")
    print("%-20s%9s%8s%7s%9s%9s%11s%7s  KARAR"%(
        "","yillik","Sharpe","dd","Sh22-24","Sh25-26","esit-risk","kald"))
    for ad,h in G:
        if h=="A20Y90":
            print("%-20s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  KONTROL"%(
                ad,kon.getiri,kon.sharpe,-kon.dusus,kon.erken,kon.gec,kon.getiri,1.0)); continue
        a=olc(ad,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1])
        print("%-20s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  %s"%(
            ad,a.getiri,a.sharpe,-a.dusus,a.erken,a.gec,s['esit_risk'],s['kaldirac'],
            'GECER' if s['gecer'] else 'RED'))
