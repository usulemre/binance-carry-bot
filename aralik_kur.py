#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 552 panel: coinin GÜNCEL funding aralığı (saat) her barda — son 3 ödemenin ardışık farklarının medyanı (bar anına kadar).
Binance funding tavana dayanan coinin aralığını 8 → 4 (→ 1) sa'e indirir: aralık kısalması = aşırı kalabalık / sıkışma işareti.
Kullanım: VERI_EK=uzun python3 aralik_kur.py → /tmp/aralik.pkl (ve /tmp/zu/aralik.pkl)."""
import os, pickle, shutil
import numpy as np, pandas as pd
R = os.path.dirname(os.path.abspath(__file__))
P = pickle.load(open('/tmp/panel.pkl', 'rb')); C = P['C']; kol = list(C.columns)
bar_h = C.index.values.astype('datetime64[s]').astype(np.int64) / 3600.0
out = np.full((len(bar_h), len(kol)), np.nan)
klas = ('data_funding_' + os.environ['VERI_EK']) if os.environ.get('VERI_EK') else 'data_funding_genis'
for j, s in enumerate(kol):
    fy = os.path.join(R, klas, f'{s}.csv')
    if not os.path.exists(fy): continue
    try: f = pd.read_csv(fy, parse_dates=['date'])
    except Exception: continue
    f['date'] = f['date'].dt.floor('h'); f = f.drop_duplicates('date').sort_values('date')
    if len(f) < 4: continue
    t = f['date'].values.astype('datetime64[s]').astype(np.int64) / 3600.0
    d = np.diff(t)                                   # d[k] = t[k+1]-t[k]
    hi = np.searchsorted(t, bar_h, side='right')     # bar anına kadar ödeme sayısı
    for i in range(len(bar_h)):
        h = hi[i]
        if h < 4: continue
        x = d[h - 4:h - 1]; x = x[(x >= 0.5) & (x <= 24)]
        if x.size: out[i, j] = float(np.median(x))
A = pd.DataFrame(out, index=C.index, columns=kol).where(C.notna())
pickle.dump(A, open('/tmp/aralik.pkl', 'wb')); shutil.copy('/tmp/aralik.pkl', '/tmp/zu/aralik.pkl')
v = A.stack()
print("aralık dağılımı:", v.round().value_counts().head(6).to_dict())
for y in range(2020, 2027):
    x = A.loc[str(y)].stack(); print(y, f"<8 sa payı {float((x < 7.5).mean()):.3f}")
