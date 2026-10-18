import pickle,sys,numpy as np,pandas as pd; sys.path.insert(0,'/tmp/kc')
from capraz import hizala, dilimli
from motor import uygunluk, rapor
bn=pickle.load(open('/tmp/kc/bn_gun.pkl','rb')); kc=pickle.load(open('/tmp/kc/kc_gun.pkl','rb'))
idx,ks,bs,A,B=hizala(bn,kc)
eA=float(sys.argv[1]); eB=float(sys.argv[2]); n=int(sys.argv[3]); kom=float(sys.argv[4])
UA=uygunluk(bn['C'],bn['HAC'],eA).reindex(index=idx)[bs].values
UB=uygunluk(kc['C'],kc['HAC'],eB).reindex(index=idx)[ks].values
bas=int((idx<'2022-03-01').sum())
E=dilimli(idx,A,B,UA,UB,bas,n,kom,kom)
pickle.dump(E,open(f'/tmp/kc/E_capraz_{eA:.0e}_{eB:.0e}_{n}_{kom}.pkl','wb'))
ortak=(UA&UB)[idx>='2022-03-01'].sum(axis=1)
print('CAPRAZ BN>=',eA/1e6,'M KC>=',eB/1e6,'M n',n,'kom',kom,rapor(E),'ortak aday medyan',int(np.median(ortak)),flush=True)
