"""Madde 209: canli botun tahmincisi ama HER BAR'da hesaplanir.

Onceki kurulum pencereyi ODEME ANINDA hesaplayip bara ffill ediyordu -
bu 0-4 saat BAYAT bir sinyal demek ve panele karsi haksiz bir dezavantaj.
Canli bot pencereyi TUR ANINDA hesaplar. Burada da bar aninda hesaplanir,
boylece panelle tek fark ARALIK TAHMINCISI kalir.
"""
import pandas as pd, numpy as np, pickle, os, sys
R = '/home/claude/binance_bot/binance_bot'
P = pickle.load(open('/tmp/panel.pkl','rb')); C = P['C']; kol = list(C.columns)
PEN = float(os.environ.get('PEN', '72'))
TABAN = float(os.environ.get('TABAN', '4'))
AD = os.environ.get('AD', 'bar72')
NK = max(4, min(400, int(PEN) + 4))
bar_h = C.index.values.astype('datetime64[s]').astype(np.int64) / 3600.0
out = np.full((len(bar_h), len(kol)), np.nan)
for j, s in enumerate(kol):
    fy = os.path.join(R, 'data_funding_genis', f'{s}.csv')
    if not os.path.exists(fy): continue
    try:
        f = pd.read_csv(fy, parse_dates=['date'])
    except Exception: continue
    f['date'] = f['date'].dt.floor('h')
    f = f.drop_duplicates('date').sort_values('date')
    if len(f) < 3: continue
    t = f['date'].values.astype('datetime64[s]').astype(np.int64) / 3600.0
    r = f['funding'].values.astype(float)
    cs = np.concatenate([[0.0], np.cumsum(r)])
    # her bar icin: son odeme indeksi (t <= bar)
    hi = np.searchsorted(t, bar_h, side='right')          # [0..len(t)]
    lo = np.searchsorted(t, bar_h - PEN, side='right')     # pencere basi (dislayici)
    for i in range(len(bar_h)):
        h = hi[i]
        if h == 0: continue
        l = lo[i]
        if h <= l: continue
        ort = (cs[h] - cs[l]) / (h - l)
        # aralik: son NK kaydin ardisik farklarinin medyani, taban uygulanir
        a0 = max(0, h - NK)
        tt = t[a0:h]
        if tt.size < 2: continue
        d = np.diff(tt)
        d = d[(d >= 0.5) & (d <= 24)]
        if d.size == 0: continue
        ar = max(np.sort(d)[d.size // 2], TABAN)
        out[i, j] = ort * (24.0 / ar)
SIN = pd.DataFrame(out, index=C.index, columns=kol).where(C.notna())
pickle.dump(SIN, open(f'/tmp/sk_{AD}.pkl', 'wb'))
sk = P['sk']
kors = []
for i in range(0, len(C), 50):
    a, b = SIN.values[i], sk.values[i]
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() > 20: kors.append(np.corrcoef(a[m], b[m])[0, 1])
print(f"{AD}: pencere {PEN}sa taban {TABAN} kayit {NK} | hucre {int(SIN.notna().sum().sum())} "
      f"| panel sk ile kesitsel kor {np.nanmean(kors):+.4f}", flush=True)
