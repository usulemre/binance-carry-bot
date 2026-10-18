import pickle,sys; sys.path.insert(0,'/tmp/kc'); sys.path.insert(0,'/tmp')
from motor import *
from tradfi_liste import TRADFI
K=pickle.load(open('/tmp/kc/kc_gun.pkl','rb'))
# KuCoin'de TradFi (hisse/emtia) perp'leri de cikar: Binance listesindeki kokler + bilinen
tf_kok={t[:-4] for t in TRADFI}
drop=[c for c in K['C'].columns if c[:-5] in tf_kok]
for k in list(K): K[k]=K[k].drop(columns=drop)
esik=float(sys.argv[1]); n=int(sys.argv[2]); kom=float(sys.argv[3])
K['U']=uygunluk(K['C'],K['HAC'],esik)
bas=int((K['C'].index<'2022-03-01').sum())
E=dilimli(K,bas,n,kom); pickle.dump(E,open(f'/tmp/kc/E_kc_{esik:.0e}_{n}_{kom}.pkl','wb'))
print('KUCOIN esik',esik/1e6,'M n',n,'kom',kom,rapor(E),'evren medyan',int(K['U'][K['U'].index>='2022-03-01'].sum(axis=1).median()),'TradFi atilan',len(drop),flush=True)
