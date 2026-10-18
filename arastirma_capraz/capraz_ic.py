"""Madde 219: geçmis FARK, ileriki farki tahmin ediyor mu?

Madde 214'un dersi: bir sinyalin ileriye donuk hedefi tahmin etmesi
VARSAYILAMAZ. Once IC (kesitsel rank korelasyonu) olculur; dusukse kitap
kurmanin anlami yok.

Gerceklesen kira: pozisyon (BN short / Gate long) ise 5 gun boyunca
BN'de +f_BN toplar, Gate'te -f_GATE oder -> net toplam.
"""
import pickle, numpy as np, pandas as pd, glob, os
P = pickle.load(open('/tmp/panel.pkl','rb')); C = P['C']; uy = P['uy']
X = pickle.load(open('/tmp/capraz_panel.pkl','rb'))
BN, GT = X['BN'], X['GT']
kol = list(BN.columns)
# gerceklesen HAM odemeler (yillik degil): bar bazina
R = '/home/claude/binance_bot/binance_bot'
def ham_panel(yol, ts_kol, r_kol, parse=False):
    out = {}
    for s in kol:
        p = yol.format(s=s)
        if not os.path.exists(p): continue
        d = pd.read_csv(p, parse_dates=['date']) if parse else pd.read_csv(p)
        t = (d['date'].values.astype('datetime64[s]').astype(np.int64) if parse
             else d[ts_kol].astype(np.int64).values)
        ser = pd.Series(d[r_kol].astype(float).values,
                        index=pd.to_datetime(t, unit='s'))
        ser = ser[~ser.index.duplicated()]
        # bar kovalarina TOPLA
        k = C.index.searchsorted(ser.index, side='right') - 1
        m = k >= 0
        out[s] = pd.Series(ser.values[m]).groupby(k[m]).sum()
    M = np.zeros((len(C), len(kol)))
    for j, s in enumerate(kol):
        if s in out:
            idx = out[s].index.values
            M[idx, j] = out[s].values
    return M
ODE_BN = ham_panel(R + '/data_funding_genis/{s}.csv', None, 'funding', parse=True)
ODE_GT = ham_panel('/tmp/gate/{s}.csv', 't', 'r')
pickle.dump({'ODE_BN': ODE_BN, 'ODE_GT': ODE_GT}, open('/tmp/capraz_ode.pkl','wb'))
print("ham odeme panelleri kuruldu", flush=True)

FARK = (BN - GT).values                     # yillik fark (sinyal)
H = 30                                      # 5 gun
csb = np.vstack([np.zeros((1, len(kol))), np.cumsum(ODE_BN, axis=0)])
csg = np.vstack([np.zeros((1, len(kol))), np.cumsum(ODE_GT, axis=0)])
U = uy.reindex(columns=kol).values
ic = []
for i in range(1200, len(C) - H - 2, 6):
    g = np.isfinite(FARK[i]) & U[i]
    ix = np.flatnonzero(g)
    if ix.size < 10: continue
    # ileriye donuk NET kira: isaret sinyalden gelir
    ileri_bn = csb[i+1+H, ix] - csb[i+1, ix]
    ileri_gt = csg[i+1+H, ix] - csg[i+1, ix]
    yon = np.sign(FARK[i, ix])              # +1: BN short/Gate long
    net = yon * (ileri_bn - ileri_gt)
    sin = np.abs(FARK[i, ix])               # buyukluk = beklenen kira
    if np.std(sin) == 0 or np.std(net) == 0: continue
    ra = pd.Series(sin).rank().values; rb = pd.Series(net).rank().values
    ic.append(np.corrcoef(ra, rb)[0,1])
ic = np.array(ic)
print(f"\nKESITSEL IC (|fark| -> ileriki 5 gun NET kira), {len(ic)} kesit:")
print(f"  ortalama {ic.mean():+.4f}   medyan {np.median(ic):+.4f}   "
      f"std {ic.std():.4f}")
print(f"  t-degeri {ic.mean()/ic.std()*np.sqrt(len(ic)):+.1f}   "
      f"pozitif kesit orani %{100*np.mean(ic>0):.0f}")
