import pickle,numpy as np,pandas as pd
z=pickle.load(open('/tmp/zemin.pkl','rb'));P=pickle.load(open('/tmp/panel.pkl','rb'));Mt=pickle.load(open('/tmp/metrik_panel.pkl','rb'))
C=z['C'];F=z['ODE'].reindex_like(C).fillna(0)
sk=pd.read_pickle('/tmp/sk_bar48.pkl').reindex_like(C)
# gun basi = onceki gunun 20:00 bari (kapanis 24:00) -> nedensel
t0=C.index[C.index.hour==20]
def gunluk(df): x=df.loc[t0]; x.index=(x.index+pd.Timedelta(hours=4)).normalize(); return x
r1=C/C.shift(1)-1
feat={
 'funding48':gunluk(sk),
 'ls':gunluk(np.log(Mt['count_long_short_ratio'].reindex_like(C))),
 'yas_gun':gunluk(P['YAS'].reindex_like(C)/6),
 'hacim':gunluk(np.log(P['HAC'].reindex_like(C))),
 'r1':gunluk(C/C.shift(6)-1),'r7':gunluk(C/C.shift(42)-1),'r30':gunluk(C/C.shift(180)-1),
 'oyn30':gunluk(r1.rolling(180).std()),
 'oi7':gunluk(Mt['sum_open_interest_value'].reindex_like(C)/Mt['sum_open_interest_value'].reindex_like(C).shift(42)-1),
}
G=pd.concat([pd.read_pickle(f"/tmp/m412/gkt_kayma_2000_{h}.pkl").assign(h=h) for h in (0,1)])
G['c']=G.fiyat+G.funding; G['w']=G.ort_poz.abs()*G.bar/6; G['yon']=np.where(G.ort_poz>0,'L','S')
G=G[G.w>0]
for k,f in feat.items():
    st=f.stack(); st.index.names=['gun','sembol']; st=st.rename(k)
    G=G.join(st,on=['gun','sembol'])
G['donem']=np.where(G.gun<'2025-01-01','22-24','25-26')
yil={'22-24':(pd.Timestamp('2025-01-01')-pd.Timestamp('2022-07-20')).days/365,'25-26':(pd.Timestamp('2026-10-01')-pd.Timestamp('2025-01-01')).days/365}
sat=[]
for yon in ('L','S'):
    g=G[G.yon==yon]
    for k in feat:
        try: q=pd.qcut(g[k],5,labels=False,duplicates='drop')
        except Exception: continue
        for b in sorted(q.dropna().unique()):
            m=q==b; row={'yon':yon,'ozellik':k,'kova':int(b)+1,'aralik':f"{g[k][m].min():.3g}..{g[k][m].max():.3g}"}
            for d in ('22-24','25-26'):
                x=g[m&(g.donem==d)]
                row[f'{d}_$/yil']=x.c.sum()/2*2000/yil[d]; row[f'{d}_bp']=x.c.sum()/max(x.w.sum(),1e-9)*1e4
            sat.append(row)
T=pd.DataFrame(sat)
pd.set_option('display.width',250)
iki_negatif=T[(T['22-24_$/yil']<0)&(T['25-26_$/yil']<0)]
print("IKI DONEMDE DE ZARAR EDEN KOVALAR (2.000 $, yillik $):"); print(iki_negatif.round(1).to_string(index=False))
print("\nEN COK KAZANDIRAN KOVALAR (iki donem toplami ust 6):")
T['top']=T['22-24_$/yil']+T['25-26_$/yil']; print(T.sort_values('top',ascending=False).head(6).round(1).to_string(index=False))
print("\nTOPLAM yillik $:",{d:round(G[G.donem==d].c.sum()/2*2000/yil[d]) for d in yil})
T.to_csv('/tmp/m412/segment423.csv',index=False)
