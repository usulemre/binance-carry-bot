import sys; sys.path.insert(0,'/tmp')
from g import *
ad=sys.argv[1]; n=int(sys.argv[2])
if ad=='taban': calis('taban',n)
elif ad=='long60': calis('long60',n,agirlik='long60')
elif ad=='beta':
    r=C.pct_change(); btc=r['BTCUSDT']
    cov=r.rolling(540,min_periods=270).cov(btc); var=btc.rolling(540,min_periods=270).var()
    B=cov.div(var,axis=0).values
    calis('beta',n,agirlik='beta',BETA=B)
elif ad.startswith('hacim'):
    w=float(ad[5:])
    V=pickle.load(open('/tmp/V.pkl','rb'))
    V1=V.rolling(6,min_periods=6).sum(); V30=V.rolling(180,min_periods=120).mean()*6
    calis(ad,n,ek=(V1/V30).values,ekw=w)
if ad.startswith('ters'):
    w=float(ad[4:]); V=pickle.load(open('/tmp/V.pkl','rb'))
    V1=V.rolling(6,min_periods=6).sum(); V30=V.rolling(180,min_periods=120).mean()*6
    calis(ad,n,ek=-(V1/V30).values,ekw=w)
if ad.startswith('rast'):
    s=int(ad[4:]); rng=np.random.default_rng(s)
    R=rng.random(C.shape)
    calis(ad,n,ek=R,ekw=0.35)
if ad.startswith('prem'):
    pen=int(ad.split('_')[1]); w=float(ad.split('_')[2])
    PR=pickle.load(open('/tmp/prem.pkl','rb'))
    calis(ad,n,ek=-(PR.rolling(pen,min_periods=pen//2).mean()).values,ekw=w)
