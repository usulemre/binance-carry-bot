import pickle,sys,numpy as np,pandas as pd; sys.path.insert(0,'/tmp/kc')
from capraz import hizala
from motor import uygunluk
bn=pickle.load(open('/tmp/kc/bn_gun.pkl','rb')); kc=pickle.load(open('/tmp/kc/kc_gun.pkl','rb'))
idx,ks,bs,A,B=hizala(bn,kc)
print('ortak coin',len(ks))
m=np.isfinite(A['F'])&np.isfinite(B['F'])&(A['F']!=0)&(B['F']!=0)
print('gunluk funding korelasyonu (ayni coin-gun):',round(np.corrcoef(A['F'][m],B['F'][m])[0,1],3),'n',m.sum())
print('isaret uyumu:',round((np.sign(A['F'][m])==np.sign(B['F'][m])).mean(),3))
# fiyat getiri korelasyonu
ra=A['C'][1:]/A['C'][:-1]-1; rb=B['C'][1:]/B['C'][:-1]-1; mm=np.isfinite(ra)&np.isfinite(rb)
print('gunluk getiri korelasyonu:',round(np.corrcoef(ra[mm],rb[mm])[0,1],3))
# funding dagilimi: gunluk funding'in alt/ust kuyruklari
for ad,X in (('Binance',A),('KuCoin',B)):
    f=X['F'][m]*100
    print(ad,'gunluk funding % yuzdelikler 1/5/50/95/99:',np.round(np.percentile(f,[1,5,50,95,99]),3))
# ayni coin-gun, Binance cok negatifken KuCoin ne?
neg=m&(A['F']<-0.003)
print('Binance gunluk funding < -%0.3 olan',neg.sum(),'gozlem; KuCoin ortanca',round(np.median(B['F'][neg])*100,3),'% Binance ortanca',round(np.median(A['F'][neg])*100,3),'%')
