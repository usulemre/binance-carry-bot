import glob,os,pickle,numpy as np,pandas as pd
R='/tmp/kc'
C,H,L,HAC,F={},{},{},{},{}
eksik_mum=[]
for p in glob.glob(f'{R}/fund/*.csv'):
    s=os.path.basename(p)[:-4]
    f=pd.read_csv(p)
    q=f'{R}/gun/{s}.csv'
    if not os.path.exists(q): eksik_mum.append(s); continue
    g=pd.read_csv(q)
    if len(g)<30: eksik_mum.append(s); continue
    g['d']=pd.to_datetime(g.t,unit='ms').dt.floor('D'); g=g.drop_duplicates('d').set_index('d').sort_index()
    C[s],H[s],L[s],HAC[s]=g.close,g.high,g.low,g.turnover
    f['d']=pd.to_datetime(f.t,unit='ms').dt.floor('D')
    F[s]=f.groupby('d').funding.sum()
C=pd.DataFrame(C).sort_index(); C=C[C.index>='2022-01-01']
idx=C.index; cols=C.columns
H=pd.DataFrame(H).reindex(index=idx,columns=cols); L=pd.DataFrame(L).reindex(index=idx,columns=cols)
HAC=pd.DataFrame(HAC).reindex(index=idx,columns=cols)
F=pd.DataFrame(F).reindex(index=idx,columns=cols).fillna(0.0).where(C.notna())
# fiyat verisi bittikten sonra ileri doldurma YOK (KuCoin delistte mum vermiyor) -> pozisyon son fiyattan kapanmis sayilir
pickle.dump(dict(C=C,H=H,L=L,F=F,HAC=HAC),open(f'{R}/kc_gun.pkl','wb'))
son=C.apply(lambda s:s.last_valid_index())
print('sembol',C.shape[1],'gun',C.shape[0],'mumu eksik',len(eksik_mum),'veri erken biten (delist)',(son<idx[-1]-pd.Timedelta(days=3)).sum())
print('eksik mum ornek',eksik_mum[:15])
