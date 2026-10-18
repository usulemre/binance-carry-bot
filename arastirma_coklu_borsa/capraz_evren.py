import pickle,sys,numpy as np,pandas as pd; sys.path.insert(0,'/tmp/kc')
from capraz import hizala
from motor import uygunluk, dilimli, rapor
bn=pickle.load(open('/tmp/kc/bn_gun.pkl','rb')); kc=pickle.load(open('/tmp/kc/kc_gun.pkl','rb'))
idx,ks,bs,A,B=hizala(bn,kc)
UB_bn=uygunluk(bn['C'],bn['HAC'],1e8).reindex(index=idx)[bs].values
UK=uygunluk(kc['C'],kc['HAC'],1e7).reindex(index=idx)[ks].values
def panel(X,U,cols):
    P={k:pd.DataFrame(X[k],index=idx,columns=cols) for k in ('C','F')}
    src=bn if X is A else kc; c=bs if X is A else ks
    P['H']=src['H'].reindex(index=idx)[c].set_axis(cols,axis=1); P['L']=src['L'].reindex(index=idx)[c].set_axis(cols,axis=1)
    P['U']=pd.DataFrame(U,index=idx,columns=cols); return P
bas=int((idx<'2022-03-01').sum()); v=sys.argv[1]; n=int(sys.argv[2])
if v=='KC_fiyat_BN_evren': P=panel(B,UB_bn,ks)
if v=='BN_fiyat_KC_evren': P=panel(A,UK,ks)
if v=='BN_fiyat_BN_evren_ortak': P=panel(A,UB_bn,ks)
if v=='KC_fiyat_KC_evren_ortak': P=panel(B,UK,ks)
E=dilimli(P,bas,n,0.0002)
print(v,n,rapor(E),'evren medyan',int(P['U'][idx>='2022-03-01'].sum(axis=1).median()),flush=True)
