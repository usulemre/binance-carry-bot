import pickle,sys; sys.path.insert(0,'/tmp/kc')
from motor import *
P=pickle.load(open('/tmp/kc/bn_gun.pkl','rb'))
P['U']=uygunluk(P['C'],P['HAC'],1e8)
bas=int((P['C'].index<'2022-03-01').sum())
n=int(sys.argv[1])
E=dilimli(P,bas,n,0.0002); pickle.dump(E,open(f'/tmp/kc/E_bn_{n}.pkl','wb'))
print('BINANCE gunluk',n,rapor(E),'evren medyan',P['U'][P['U'].index>='2022-03-01'].sum(axis=1).median(),flush=True)
