import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
E=[("kontrol (tek esik)","KONTROL"),("YARIM (TP'de yarisi)","YARIM"),
   ("takip %20/geri %10","T20G10"),("takip %30/geri %15","T30G15"),
   ("takip %50/geri %20","T50G20"),
   ("merdiven %10 x1/3","M10P33"),("merdiven %20 x1/3","M20P33"),
   ("merdiven %20 x1/2","M20P50")]
def seri(h):
    es=[pickle.load(open(f'/tmp/m235/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={}
for ad,h in E:
    try: S[h]=seri(h)
    except Exception as e: print("atlandi",h,e)
kon=olc("kontrol",S["KONTROL"][0]); kg=S["KONTROL"][1]
print("ÇIKIŞ ŞEKLİ AİLESİ (madde 235)")
print("%-24s%9s%8s%7s%9s%9s%11s%7s  KARAR"%(
    "","yillik","Sharpe","dd","Sh22-24","Sh25-26","esit-risk","kald"))
res={}
for ad,h in E:
    if h not in S: continue
    if h=="KONTROL":
        print("%-24s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  KONTROL"%(
            ad,kon.getiri,kon.sharpe,-kon.dusus,kon.erken,kon.gec,kon.getiri,1.0)); continue
    a=olc(ad,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1]); res[h]=(a,s)
    print("%-24s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f%7.2f  %s"%(
        ad,a.getiri,a.sharpe,-a.dusus,a.erken,a.gec,s['esit_risk'],s['kaldirac'],
        'GECER' if s['gecer'] else 'RED'))
print("\nEŞİT RİSKTE KONTROLÜ GEÇEN ADAYLARIN ŞARTLARI:")
for h in res:
    a,s=res[h]
    if s['esit_risk']>kon.getiri:
        print(f"  {h} -> {s['gerekce']}")
        for k2,(ok,aci) in s['sartlar'].items(): print(f"      [{'OK ' if ok else 'RED'}] {k2:<22} {aci}")
