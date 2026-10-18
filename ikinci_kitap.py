"""Madde 218: harman testi. Iki surum:
  (a) NAIF   : agirliklar toplami 1, borsa sermaye kisiti YOK
  (b) GERCEK : capraz kitap AYNI pozisyon icin IKI borsada teminat ister,
               yani toplam sermaye basina dolar getirisi YARIYA iner.
"""
import pickle, numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
from karar_kurali import Olcum, gecer_mi, yaz
E = [pickle.load(open(f'/tmp/E48_{f}.pkl','rb')) for f in (0,1)]
g = pd.concat([e.pct_change() for e in E], axis=1).mean(axis=1).dropna()
ana = ((1+g).resample('1D').prod() - 1).dropna()
cap = pickle.load(open('/tmp/kc/E_capraz_1e+08_1e+07_5_0.0002.pkl','rb'))
if not isinstance(cap, pd.Series): cap = pd.Series(cap)
cap = cap.pct_change().dropna()
d = pd.concat([ana.rename('ana'), cap.rename('cap')], axis=1, sort=True).dropna()
print(f"ortak {len(d)} gun  {d.index[0].date()}..{d.index[-1].date()}")

def olc(r, ad):
    e = (1+r).cumprod()
    yil = e.iloc[-1]**(365.25/len(r)) - 1
    sh = r.mean()/r.std()*np.sqrt(365.25)
    dd = -(e/e.cummax()-1).min()
    m1 = r.index < '2025-01-01'; m2 = ~m1
    s1 = r[m1].mean()/r[m1].std()*np.sqrt(365.25)
    s2 = r[m2].mean()/r[m2].std()*np.sqrt(365.25)
    return Olcum(ad, yil*100, sh, s1, s2, dd*100)

kontrol = olc(d['ana'], 'ana kitap')
adaylar = []
for w in (0.10, 0.20, 0.30, 0.40, 0.50):
    for kisit, etiket in ((1.0, 'naif'), (0.5, 'gerçek')):
        r = (1-w)*d['ana'] + w*kisit*d['cap']
        adaylar.append(olc(r, f'{etiket} %{int(w*100)} çapraz'))
print()
print(yaz(kontrol, adaylar))
