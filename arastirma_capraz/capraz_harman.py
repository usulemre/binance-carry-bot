"""Madde 219: harman testi ama DOGRULANMIS capraz kitapla (madde 218'in
dogrulanmamis KuCoin kitabi yerine)."""
import pickle, numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
from karar_kurali import Olcum, gecer_mi, _stat
E = [pickle.load(open(f'/tmp/E48_{f}.pkl','rb')) for f in (0,1)]
g = pd.concat([e.pct_change() for e in E], axis=1).mean(axis=1).dropna()
ana = ((1+g).resample('1D').prod() - 1).dropna()
S = pickle.load(open('/tmp/capraz_sonuc.pkl','rb'))
def olc(r, ad):
    y, dd = _stat(r)
    sh = r.mean()/r.std()*np.sqrt(365.25)
    m1 = r.index < '2025-01-01'
    return Olcum(ad, y*100, sh, r[m1].mean()/r[m1].std()*np.sqrt(365.25),
                 r[~m1].mean()/r[~m1].std()*np.sqrt(365.25), dd*100)
kon = olc(ana, 'ana kitap')
print(f"{'aday':30s} {'Sh':>5s} {'22-24':>6s} {'25-26':>6s} {'dusus':>7s} "
      f"{'kald':>5s} {'ESIT RISK':>10s}  karar")
print(f"{kon.ad:30s} {kon.sharpe:5.2f} {kon.erken:6.3f} {kon.gec:6.3f} "
      f"{-kon.dusus:7.2f} {'--':>5s} {kon.getiri:+10.1f}  KONTROL")
# en iyi capraz ayar + KuCoin karsilastirmasi icin ayni agirliklar
for ayar in ('n=5  tut=5g kom=2bp', 'n=5  tut=5g kom=4bp', 'n=10 tut=5g kom=2bp'):
    cap = S[ayar]
    d = pd.concat([ana.rename('a'), cap.rename('b')], axis=1, sort=True).dropna()
    kor = float(d['a'].corr(d['b']))
    print(f"\n--- {ayar}  (ana ile korelasyon {kor:+.4f}, ortak {len(d)} gun)")
    for w in (0.2, 0.3, 0.5, 0.7):
        r = (1-w)*d['a'] + w*0.5*d['b']       # iki borsa teminati: yarim
        a = olc(r, f'  %{int(w*100)} capraz')
        res = gecer_mi(kon, a, gunluk_kontrol=d['a'].values, gunluk_aday=r.values)
        print(f"{a.ad:30s} {a.sharpe:5.2f} {a.erken:6.3f} {a.gec:6.3f} "
              f"{-a.dusus:7.2f} {res['kaldirac']:5.2f} {res['esit_risk']:+10.1f}  "
              f"{'KABUL' if res['gecer'] else 'RED'}"
              + ("" if res['gecer'] else "  <- " + res['gerekce'].replace('geçmeyen şart: ','')))
