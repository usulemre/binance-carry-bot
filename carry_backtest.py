"""FUNDING CARRY backtest - funding GERCEK veriyle, gelir olarak modellenir.

Onceki backtestlerin en buyuk eksigi: funding 'gross * sabit oran' maliyet
olarak varsayiliyordu (README madde 'FUNDING MODELI'). Artik coin bazinda
gercek tarihsel funding elimizde.

Piyasa notr portfoyde:
  - long pozisyon: funding POZITIFSE oder, NEGATIFSE alir
  - short pozisyon: funding POZITIFSE alir, NEGATIFSE oder
Yani dogru secimle funding GELIR olur.
"""
import pandas as pd, numpy as np
import os

def panel_yukle(kok="."):
    """Fiyat / premium / funding panellerini diskten kurar.

    historical_data_wide/  fiyat (Binance resmi arsivi - madde 111)
    data_premium/          premium index (perpetual - spot farki)
    data_funding/          gercek tarihsel funding oranlari
    """
    hd=os.path.join(kok,"historical_data_wide")
    syms=sorted(x.replace("_4h.csv","") for x in os.listdir(hd)
                if x.endswith("_4h.csv")
                and os.path.exists(os.path.join(kok,"data_funding",
                    x.replace("_4h.csv",".csv")))
                and os.path.exists(os.path.join(kok,"data_premium",
                    x.replace("_4h.csv",".csv"))))
    cl,pr,fu,iv={},{},{},{}
    for s in syms:
        cl[s]=pd.read_csv(f"{hd}/{s}_4h.csv",parse_dates=["date"]).set_index("date")["close"]
        pr[s]=pd.read_csv(f"{kok}/data_premium/{s}.csv",parse_dates=["date"]).set_index("date")["close"]
        f=pd.read_csv(f"{kok}/data_funding/{s}.csv",parse_dates=["date"])
        f["date"]=f["date"].dt.floor("h")      # ms ofseti temizle (yoksa %50 bosluk)
        f=f.drop_duplicates("date").set_index("date")
        fu[s]=f["rate"]
        iv[s]=f["interval_h"]
    C=pd.DataFrame(cl).sort_index(); C=C[C.index.year>=2022]
    # KALITE FILTRESI: donuk (ileri doldurulmus/delist) seriler backtest'i
    # yapay olarak iyilestirir - madde 111'in kucuk kardesi.
    donuk=(C.diff()==0).mean()
    C=C[donuk[donuk<0.10].index]
    # delist olanlari da ele: son barina kadar veri vermeyenler
    son=C.apply(lambda c: c.last_valid_index())
    C=C[son[son>=C.index[-1]-pd.Timedelta(days=7)].index].dropna(how="any")
    PR=pd.DataFrame(pr)[C.columns].reindex(C.index)
    ham=pd.DataFrame(fu)[C.columns].sort_index()
    IV=pd.DataFrame(iv)[C.columns].sort_index()

    # ODEME paneli: o barda GERCEKTEN odenen funding. Bir odeme tam bir kez
    # sayilir. Onceki surum hepsini 8 saatlik varsayiyordu - 4 saatlik
    # funding odeyen 24 sembolde gelirin YARISI kayboluyordu (madde 114).
    ODEME=ham.reindex(ham.index.union(C.index)).reindex(C.index).fillna(0.0)
    # bar arasina dusen odemeleri de topla (funding saati bar saatiyle
    # tam ortusmezse kaybolmasin)
    dis=ham.index.difference(C.index)
    if len(dis):
        kova=pd.Series(C.index.searchsorted(dis,side="right")-1,index=dis)
        ek=ham.loc[dis].groupby(kova.values).sum()
        ek=ek[ek.index>=0]
        if len(ek):
            ODEME.iloc[ek.index]+=ek.values

    # SINYAL paneli: YILLIKLASTIRILMIS oran. 4 saatlik funding odeyen bir
    # coinin ham orani dusuk gorunur ama yillik getirisi 2 KATIDIR -
    # ham oranla siralamak yanlis secim yaptirir.
    IVd=IV.reindex(IV.index.union(C.index)).ffill(limit=8).reindex(C.index).ffill()
    IVd=IVd.where(IVd>0, 8.0).fillna(8.0)
    SINYAL=ham.reindex(ham.index.union(C.index)).ffill(limit=4).reindex(C.index)*(24.0/IVd)
    return C,PR,SINYAL,ODEME

C,PR,FU,ODEME=panel_yukle(os.path.dirname(os.path.abspath(__file__)) or ".")
KOM=0.0006   # tek yon: %0.04 komisyon + %0.02 kayma

def bt(skor, n, reb, lag=1, bas=1200, funding_gelir=True, odeme=None,
       agirlik='esit', vol_hedef=None, vol_pencere=180):
    """skor DUSUK olan long, YUKSEK olan short. Piyasa notr."""
    cv=C.values; fv=(ODEME if odeme is None else odeme).values
    # OYNAKLIK: risk-pariteli agirlik ve oynaklik hedefi icin (madde 116)
    VV=C.pct_change().rolling(vol_pencere).std().values
    idx=C.index; kol=C.columns
    poz=np.zeros(len(kol)); eq=[1.0]; tar=[idx[bas]]; bek=None
    fk=0.0  # kumulatif funding katkisi
    for i in range(bas, len(C)-1):
        if bek is not None and bek[0]==i:
            y=bek[1]; eq[-1]*= (1-np.abs(y-poz).sum()*KOM); poz=y; bek=None
        if (i-bas)%reb==0:
            s=skor.iloc[i]
            g=s.notna().values & np.isfinite(cv[i])
            if g.sum()>=2*n:
                sv=np.where(g,s.values,np.nan)
                sira=np.argsort(np.where(np.isnan(sv),np.inf,sv))
                L=sira[:n]; S=sira[g.sum()-n:g.sum()]
                y=np.zeros(len(kol))
                if agirlik=='vol':
                    # RISK PARITESI: her pozisyon esit RISK tasisin, esit
                    # PARA degil. Oynak coine daha az sermaye. Olculdu
                    # (madde 116): Sharpe 0.86 -> 1.14, KALDIRACSIZ.
                    a=1/np.where(np.isfinite(VV[i][L])&(VV[i][L]>0),VV[i][L],np.nan)
                    b=1/np.where(np.isfinite(VV[i][S])&(VV[i][S]>0),VV[i][S],np.nan)
                    a=np.nan_to_num(a); b=np.nan_to_num(b)
                    a=a/a.sum() if a.sum()>0 else np.ones(n)/n
                    b=b/b.sum() if b.sum()>0 else np.ones(n)/n
                    y[L]=0.5*a; y[S]=-0.5*b
                else:
                    y[L]=0.5/n; y[S]=-0.5/n
                if vol_hedef is not None and len(eq)>vol_pencere+20:
                    # OYNAKLIK HEDEFI: portfoy oynakligi hedeften dusukse
                    # buyut, yuksekse kucult. Sinir [0.3x, 3.0x].
                    _g=np.diff(eq[-vol_pencere:])/np.array(eq[-vol_pencere:-1])
                    _s=np.nanstd(_g)*np.sqrt(365.25*6)
                    if _s>1e-6:
                        y=y*float(np.clip(vol_hedef/_s,0.3,3.0))
                bek=(i+lag,y)
        br=(cv[i+1]-cv[i])/cv[i]
        ret=float(np.nansum(poz*np.nan_to_num(br)))
        # funding: 8 saatte bir (00,08,16). 4h barlarda 2 barda 1 kez.
        fnd=0.0
        if funding_gelir:
            f=np.nan_to_num(fv[i+1])       # o barda GERCEKTEN odenen funding
            if f.any():
                fnd=float(np.nansum(-poz*f))   # long pozitif funding ODER
                fk+=fnd
        eq.append(eq[-1]*(1+ret+fnd))
        tar.append(idx[i+1])
    e=pd.Series(eq,index=tar)
    gun=(e.index[-1]-e.index[0]).days
    yl=(e.iloc[-1]**(365.25/gun)-1)*100
    g=e.pct_change().dropna()
    sh=g.mean()/g.std()*np.sqrt(365.25*6) if g.std()>0 else 0
    dd=((e/e.cummax())-1).min()*100
    return e,yl,sh,dd,fk*100


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(description="Funding carry backtest (madde 113)")
    ap.add_argument("--n-legs",type=int,default=20)
    ap.add_argument("--funding-window",type=int,default=6,help="bar (6=1 gun)")
    ap.add_argument("--rebalance",type=int,default=30,help="bar (30=5 gun)")
    ap.add_argument("--agirlik",default="esit",choices=["esit","vol"],
                    help="esit (varsayilan) veya vol=risk paritesi. DIKKAT: vol KARARSIZ - dar evrende Sharpe 0.86->1.14 iyilestirdi, genis evrende 1.50->0.82 BOZDU (madde 116)")
    ap.add_argument("--vol-hedef",type=float,default=0.20,
                    help="yillik oynaklik hedefi (0 = kapali)")
    ap.add_argument("--all-phases",action="store_true",
                    help="tum rebalance fazlarinin ORTALAMASI - gercekci beklenti budur")
    a=ap.parse_args()
    sk=FU.rolling(a.funding_window).mean()
    print(f"{C.shape[1]} coin | {a.n_legs}+{a.n_legs} bacak | "
          f"funding {a.funding_window} bar ort | {a.rebalance} bar rebalance\n")
    fazlar=range(0,a.rebalance,max(1,a.rebalance//5)) if a.all_phases else [0]
    rs=[]
    for f in fazlar:
        e,yl,sh,dd,fk=bt(sk,a.n_legs,a.rebalance,bas=1200+f,
                         agirlik=a.agirlik,
                         vol_hedef=(a.vol_hedef or None))
        rs.append((yl,sh,dd,fk))
        if a.all_phases:
            print(f"  faz {f:>2}: yillik {yl:>+7.1f}%  Sharpe {sh:>5.2f}  dusus {dd:>6.1f}%")
    import numpy as _np
    o=_np.mean(rs,axis=0)
    print(f"\n{'ORTALAMA' if a.all_phases else 'SONUC'}: yillik {o[0]:+.1f}%  "
          f"Sharpe {o[1]:.2f}  dusus {o[2]:.1f}%  funding katkisi {o[3]:+.1f}%")
    if not a.all_phases:
        print("NOT: --all-phases ile calistirin; tek faz sonucu yaniltici olabilir.")
