import sys; sys.path.insert(0,'/home/claude/binance-carry-bot')
import os
KAY=os.environ.get("GK_KAY","/tmp/m711")
import pandas as pd, numpy as np, pickle, arastirma_m346_prim as M
from tradfi_liste import TRADFI
G=pd.concat([pd.read_pickle(f"{KAY}/gk_{h}.pkl") for h in (0,1)]); G["gun"]=pd.to_datetime(G.gun)
G=G[G.gun<="2026-10-31"]
G["fiyat"]=G.fiyat_top-G.tp-G.stop
for c in ["fiyat_top","funding","tp","stop","fiyat","komisyon"]: G[c]=G[c]/2*100
G["yon"]=np.where(G.ort_poz>0,"L","S"); G["ay"]=G.gun.dt.to_period("M")
G["bw"]=G.ort_poz.abs()*G.bar/6/2
P=pickle.load(open('/tmp/panel.pkl','rb')); C=P['C']; H=P['HAC']; Y=P['YAS']; Dn=P['DON']
cols=[c for c in C.columns if c not in TRADFI and c not in M.D8]
U=(C[cols].notna()&(H[cols]>=7e7)&(Y[cols]>=360)&(Dn[cols].fillna(0)<0.1))
gen=(U&(Y[cols]<=365*6)).sum(axis=1).resample('D').mean()
d=C[cols].resample('D').last().pct_change(); u=U.resample('D').last()
altm=d.where(u).median(axis=1); disp=d.where(u).std(axis=1)
btc=C['BTCUSDT'].resample('D').last().pct_change()
rows=[]
M.CIKTI="/tmp/m_ekim"; s=sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0,1))/2
for ay,g in G.groupby("ay"):
    L=g[g.yon=="L"]; S=g[g.yon=="S"]; m=str(ay)
    ser=s[m]; e=(1+ser).cumprod()
    tut=g.groupby("sembol").fiyat_top.sum()+g.groupby("sembol").funding.sum()
    rows.append({"ay":m,"kitap%":((1+ser).prod()-1)*100,
      "TP+kademe":g.tp.sum(),"stop":g.stop.sum(),"L fiyat(TPsiz)":L.fiyat.sum(),"S fiyat(TPsiz)":S.fiyat.sum(),
      "L funding":L.funding.sum(),"S funding":S.funding.sum(),"komisyon":-g.komisyon.sum(),
      "en kötü 3 coin":tut.nsmallest(3).sum(),
      "BTC%":((1+btc[m]).prod()-1)*100,"alt medyan%":((1+altm[m].fillna(0)).prod()-1)*100,
      "alt dağılım(sd gün%)":disp[m].mean()*100,"genç coin(ort)":gen[m].mean(),"ay içi dd%":((e/e.cummax())-1).min()*100})
T=pd.DataFrame(rows).set_index("ay"); pd.set_option("display.width",250)
T.round(2).to_csv(os.environ.get("CIKTI","/tmp/m711/aylik.csv"))
Y=T.copy(); Y["yil"]=[a[:4] for a in Y.index]
topla=["TP+kademe","stop","L fiyat(TPsiz)","S fiyat(TPsiz)","L funding","S funding","komisyon","en kötü 3 coin"]
Yr=Y.groupby("yil")[topla].sum()
Yr["kitap%"]=Y.groupby("yil")["kitap%"].apply(lambda x:((1+x/100).prod()-1)*100)
Yr["BTC%"]=Y.groupby("yil")["BTC%"].apply(lambda x:((1+x/100).prod()-1)*100)
Yr["alt medyan%"]=Y.groupby("yil")["alt medyan%"].apply(lambda x:((1+x/100).prod()-1)*100)
Yr["genç coin(ort)"]=Y.groupby("yil")["genç coin(ort)"].mean()
Yr["zararlı ay"]=Y.groupby("yil")["kitap%"].apply(lambda x:int((x<0).sum()))
Yr["ay sayısı"]=Y.groupby("yil").size()
print(Yr.round(1).T.to_string()); print(); print(T.round(1).to_string())
