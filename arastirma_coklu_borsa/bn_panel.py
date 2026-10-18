import pickle,numpy as np,pandas as pd,sys
sys.path.insert(0,'/tmp')
from tradfi_liste import TRADFI
P=pickle.load(open('/tmp/panel.pkl','rb')); X=pickle.load(open('/tmp/hlo.pkl','rb')); V=pickle.load(open('/tmp/V.pkl','rb'))
C4=P['C']; tf=[c for c in C4.columns if c not in TRADFI]
C4=C4[tf]
g=lambda df: df[tf]
C=C4.resample('1D').last(); H=g(X['H']).resample('1D').max(); L=g(X['L']).resample('1D').min()
F=g(P['ODE']).resample('1D').sum(min_count=1).where(C.notna())
HAC=g(V).resample('1D').sum(min_count=1)
pickle.dump(dict(C=C,H=H,L=L,F=F,HAC=HAC),open('/tmp/kc/bn_gun.pkl','wb'))
# Binance 4s evreninin gunluk buyuklugu (referans)
uy=g(P['uy']); print('Binance 4s evren medyan boyut (2022-03+):',uy[uy.index>='2022-03-01'].sum(axis=1).median())
print(C.shape)
