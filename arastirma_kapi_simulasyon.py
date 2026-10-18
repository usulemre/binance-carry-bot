"""MADDE 234: saglik kapisi YANLIS OTUYOR MU? Tarihsel simulasyon.

carry_saglik.metrikleri_hesapla'nin mantigini panel verisinden
yeniden uretir ve kapinin tum ornekte ne zaman "BOZUK" dedigini sayar.
Kapi otunce bot TUM POZISYONLARI KAPATIR, o yuzden yanlis otme pahalidir.
"""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import carry_saglik as CS, carry_denetim as D
from tradfi_liste import TRADFI

P=pickle.load(open('/tmp/panel.pkl','rb'))
C,ODE=P['C'],P['ODE']
uy=D.uygunluk(P['C'],P['HAC'],P['YAS'],P['DON'],hacim=1e8,yas_bar=540,donuk_esik=0.10).copy()
uy[[c for c in uy.columns if c in TRADFI]]=False
U=uy.values; O=ODE.values; idx=C.index
BAR=4.0                      # saat
BLOK=int(120/BAR)            # 120 saat = 30 bar
SIN_BAR=int(24/BAR)          # dedektorun sinyal penceresi: 24 saat (madde 185)
NL=CS.SAGLIK_GOLGE_BACAK if hasattr(CS,'SAGLIK_GOLGE_BACAK') else 12

def yillik(pen):
    """_yillik'in panel karsiligi: pencereye dusen odemelerden yillik oran."""
    v=pen[np.isfinite(pen)&(pen!=0)]
    if v.size<2: return None
    return float(v.mean())*3*365.0     # 8 saatlik odeme -> yillik

def metrik(i):
    """i. barda biten blok icin (IC, F, DISP)."""
    t0=i-SIN_BAR
    if t0<0: return None
    sin={}
    for j in range(O.shape[1]):
        if not U[i,j]: continue
        y=yillik(O[t0+1:i+1,j])
        if y is not None: sin[j]=y
    if len(sin)<2*max(1,min(NL,3)): return None
    sir=sorted(sin,key=sin.get); n=min(NL,len(sir)//2)
    L,S=sir[:n],sir[-n:]
    disp=(np.mean([sin[s] for s in S])-np.mean([sin[s] for s in L]))/365.0
    if i+BLOK>=len(C): return (None,None,disp)
    ger={s:float(np.nansum(O[i+1:i+BLOK+1,s])) for s in sin}
    ic=CS._sira_korelasyonu({str(k):v for k,v in sin.items()},
                            {str(k):v for k,v in ger.items()})
    f=(-sum(ger[s] for s in L)+sum(ger[s] for s in S))/(2*n)
    return (ic,f,disp)

ics,fs,disps,zaman=[],[],[],[]
for i in range(1200,len(C)-BLOK-1,BLOK):
    m=metrik(i)
    if m is None: continue
    ics.append(m[0]); fs.append(m[1]); disps.append(m[2]); zaman.append(idx[i])
print("blok sayisi: %d  (%s -> %s)"%(len(ics),zaman[0].date(),zaman[-1].date()))
ics=np.array([np.nan if x is None else x for x in ics],float)
fs=np.array([np.nan if x is None else x for x in fs],float)
disps=np.array(disps,float)
print("\nOLCULEN DAGILIMLAR (blok basina)")
for ad,v,bir in [("IC",ics,1),("F",fs,1e4),("DISP",disps,1e4)]:
    q=np.nanpercentile(v,[1,5,50,95])*bir
    print("  %-6s p1 %+8.3f  p5 %+8.3f  medyan %+8.3f  p95 %+8.3f %s"%(
        ad,*q,"(bp)" if bir>1 else ""))
# kayan 6-blok ortalamalari ve kapi karari
print("\nKAPI KARARI (kayan %d blok ortalamasi, esikler IC<%.3f, F<=%.1f, DISP<%.2fbp)"%(
    CS.PENCERE,CS.IC_ESIK,CS.F_ESIK,CS.DISP_ESIK*1e4))
dur=[]
for k in range(CS.PENCERE,len(ics)+1):
    d,g=CS.saglik_durumu(list(ics[:k]),list(fs[:k]),list(disps[:k]))
    dur.append((zaman[k-1],d,g))
boz=[x for x in dur if x[1]=="BOZUK"]
isi=[x for x in dur if x[1]=="ISINMA"]
print("  degerlendirilen pencere: %d | SAGLIKLI %d | BOZUK %d (%%%.1f) | ISINMA %d"%(
    len(dur),sum(1 for x in dur if x[1]=="SAGLIKLI"),len(boz),100*len(boz)/max(1,len(dur)),len(isi)))
if boz:
    print("\n  BOZUK dedigi pencereler:")
    for z,d,g in boz[:14]: print("    %s  %s"%(z.date(),g))
    if len(boz)>14: print("    ... (%d tane daha)"%(len(boz)-14))
# rejim bazinda
for ad,m in [("dusuk prim (<2025)",lambda z:z<pd.Timestamp('2025-01-01')),
             ("yuksek prim (2025+)",lambda z:z>=pd.Timestamp('2025-01-01'))]:
    alt=[x for x in dur if m(x[0])]
    b=sum(1 for x in alt if x[1]=="BOZUK")
    if alt: print("  %-22s %d pencere, BOZUK %d (%%%.1f)"%(ad,len(alt),b,100*b/len(alt)))
