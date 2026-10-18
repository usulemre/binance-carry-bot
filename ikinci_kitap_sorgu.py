"""Madde 218: harman iddiasini SORGULA. Kapasite ve bootstrap riski."""
import pickle, numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
sys.path.insert(0,'/tmp/kc')
# 1) KAPASITE: kac sembol IKI borsada da uygun?
try:
    from capraz import hizala
    from motor import uygunluk
    bn = pickle.load(open('/tmp/kc/bn_gun.pkl','rb'))
    kc = pickle.load(open('/tmp/kc/kc_gun.pkl','rb'))
    idx, ks, bs, A, B = hizala(bn, kc)
    UA = uygunluk(bn['C'], bn['HAC'], 1e8).reindex(index=idx)[bs].values
    UB = uygunluk(kc['C'], kc['HAC'], 1e7).reindex(index=idx)[ks].values
    ortak = (UA & UB)[idx >= '2022-03-01'].sum(axis=1)
    print(f"KAPASITE: ortak uygun sembol  medyan {int(np.median(ortak))}  "
          f"p10 {int(np.percentile(ortak,10))}  p90 {int(np.percentile(ortak,90))}  "
          f"min {int(ortak.min())}")
    print(f"  (kitap n=5 bacak istiyor -> medyan {int(np.median(ortak))} adaydan "
          f"seciliyor; ana kitap 60-95 adaydan 6 seciyor)")
except Exception as e:
    print("kapasite olculemedi:", e)

# 2) BOOTSTRAP: harmanin KALDIRACLI hali, madde 188'in dogru risk olcusu
E = [pickle.load(open(f'/tmp/E48_{f}.pkl','rb')) for f in (0,1)]
g = pd.concat([e.pct_change() for e in E], axis=1).mean(axis=1).dropna()
ana = ((1+g).resample('1D').prod() - 1).dropna()
cap = pickle.load(open('/tmp/kc/E_capraz_1e+08_1e+07_5_0.0002.pkl','rb'))
if not isinstance(cap, pd.Series): cap = pd.Series(cap)
d = pd.concat([ana.rename('ana'), cap.pct_change().dropna().rename('cap')],
              axis=1, sort=True).dropna()
def boot(r, B=30, n=365, N=4000, tohum=5):
    rng = np.random.default_rng(tohum); r = np.asarray(r); R=[]; D=[]
    for _ in range(N):
        p=[]
        while len(p) < n:
            i = rng.integers(0, len(r)-B); p.extend(r[i:i+B])
        p = np.array(p[:n]); e = np.cumprod(1+p)
        R.append(e[-1]-1); D.append((e/np.maximum.accumulate(e)-1).min())
    return np.array(R), np.array(D)
print("\nBOOTSTRAP (1 yil, 4000 yol, 5 gunluk blok) — madde 188'in olcusu:")
print(f"{'kitap':24s} {'getiri p5':>10s} {'ortanca':>9s} "
      f"{'dusus p5':>9s} {'p1':>8s} {'en kotu':>9s}")
for ad, r in (('ana kitap (1.0x)', d['ana'].values),
              ('harman %50 @1.99x', 1.99*(0.5*d['ana']+0.5*0.5*d['cap']).values),
              ('harman %70 @3.29x', 3.29*(0.3*d['ana']+0.7*0.5*d['cap']).values)):
    R, D = boot(r)
    print(f"{ad:24s} {np.percentile(R,5)*100:+10.1f} {np.percentile(R,50)*100:+9.1f} "
          f"{np.percentile(D,5)*100:9.1f} {np.percentile(D,1)*100:8.1f} "
          f"{D.min()*100:9.1f}")
