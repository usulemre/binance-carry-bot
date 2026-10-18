import pickle, sys, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import karar_kurali as K, carry_denetim as D
E=[("koltuk BOŞ (kontrol)","KONTROL"),("yedekle DOLDUR","DOLDUR"),
   ("AYNI yönde tekrar gir","AYNI"),("TERS yöne dön","TERS")]
def seri(h):
    es=[pickle.load(open(f'/tmp/m229/E{h}_{k}.pkl','rb')).pct_change() for k in (0,1)]
    r4=pd.concat(es,axis=1).mean(axis=1).dropna()
    return r4,(1+r4).resample('1D').prod().dropna()-1
def olc(ad,r4):
    e=(1+r4).cumprod(); o=D.ozet(e)
    ea=e[e.index<'2025-01-01']; eb=e[e.index>='2025-01-01']
    return K.Olcum(ad,o['yillik'],o['sharpe'],D.ozet(ea/ea.iloc[0])['sharpe'],
                   D.ozet(eb/eb.iloc[0])['sharpe'],abs(o['maxdd']))
S={h:seri(h) for _,h in E}
kon=olc("kontrol",S["KONTROL"][0]); kg=S["KONTROL"][1]
print("HASAT SONRASI KOLTUK: boş bırakmak mı, doldurmak mı? (madde 229)")
print("%-24s%9s%8s%7s%9s%9s%11s  KARAR"%("","yillik","Sharpe","dd","Sh22-24","Sh25-26","esit-risk"))
for ad,h in E:
    if h=="KONTROL":
        print("%-24s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f  KONTROL"%(
            ad,kon.getiri,kon.sharpe,-kon.dusus,kon.erken,kon.gec,kon.getiri)); continue
    a=olc(ad,S[h][0]); s=K.gecer_mi(kon,a,gunluk_kontrol=kg,gunluk_aday=S[h][1])
    print("%-24s%+9.1f%8.3f%7.1f%9.3f%9.3f%+11.1f  %s"%(
        ad,a.getiri,a.sharpe,-a.dusus,a.erken,a.gec,s['esit_risk'],
        'GECER' if s['gecer'] else 'RED'))
