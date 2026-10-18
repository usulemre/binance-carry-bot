import sys; sys.path.insert(0,'/tmp')
from ml import *
if sys.argv[1]=='katsayi':
    X,y,t=veri_kur(); print('ornek',X.shape)
    for ad,m in [('2022-24',t<len(C)*0.0+ (C.index<'2025-01-01').sum()),('2025-26',t>=(C.index<'2025-01-01').sum())]:
        r=Ridge(alpha=10.0).fit(X[m],y[m])
        print(ad,{a:round(c,4) for a,c in zip(AD,r.coef_)})
    # tek tek IC (Spearman benzeri): ozellik sirasi ile hedef sirasi korelasyonu
    print('tekil korelasyon (tum ornek):',{a:round(float(np.corrcoef(X[:,j],pd.Series(y).rank(pct=True))[0,1]),3) for j,a in enumerate(AD)})
else:
    ad=sys.argv[1]; n=int(sys.argv[2]); HAVUZ=2
    SK=pickle.load(open(f'/tmp/mlSK_{ad}.pkl','rb'))
    import g2
    def olcut(i,a,taraf): return taraf*SK[i][a]
    g2.HAVUZ=HAVUZ; g2.calis2(f'mlhavuz_{ad}',n,olcut)
