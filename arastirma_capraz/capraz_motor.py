"""Madde 219: BORSALAR ARASI FUNDING FARKI — ana kitabin titizligiyle.

YAPI: ayni sembolde iki borsada TERS bacak. Funding pozitifse long oder,
short alir. O yuzden f_BN > f_GATE ise: BN'de SHORT (f_BN alir), Gate'te
LONG (f_GATE oder) -> net (f_BN - f_GATE) > 0. FIYAT RISKI YOK: ayni
varlik, ters bacaklar. Risk sadece (a) borsalar arasi baz sapmasi,
(b) funding'in odeme anina kadar donmesi, (c) icra.

TITIZLIK (madde 209/216 dersleri):
  - Aralik tahmincisi CANLI BOTUN kendisi: son ~52 kaydin medyani, 4sa
    tabanli, 48 saatlik DISLAYICI pencere, BAR aninda hesaplanir.
  - Uygunluk: Binance tarafinda ana kitabin filtresi (hacim/yas/donuk).
    Gate tarafinda hacim verisi YOK -> bu bir EKSIK, raporda yazili.
  - Maliyet: pozisyon basina 4 bacak (2 acilis + 2 kapanis).
  - Sinyal 1 bar GECIKMELI uygulanir (look-ahead yok).
"""
import os, glob, pickle, numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/claude/binance_bot/binance_bot')
R = '/home/claude/binance_bot/binance_bot'
PEN = 48.0          # canli bot ile ayni
TABAN = 4.0
NK = max(4, min(400, int(PEN) + 4))

def yillik_panel(odemeler: pd.DataFrame, barlar) -> np.ndarray:
    """Canli botun tahmincisi, her BAR icin (bkz. canli_sinyal_kur.py)."""
    t = odemeler['t'].values.astype(float) / 3600.0      # saat
    r = odemeler['r'].values.astype(float)
    bar_h = barlar.values.astype('datetime64[s]').astype(np.int64) / 3600.0
    hi = np.searchsorted(t, bar_h, side='right')
    lo = np.searchsorted(t, bar_h - PEN, side='right')
    cs = np.concatenate([[0.0], np.cumsum(r)])
    out = np.full(len(bar_h), np.nan)
    for i in range(len(bar_h)):
        h = hi[i]
        if h == 0: continue
        l = lo[i]
        if h <= l: continue
        ort = (cs[h] - cs[l]) / (h - l)
        a0 = max(0, h - NK)
        tt = t[a0:h]
        if tt.size < 2: continue
        d = np.diff(tt); d = d[(d >= 0.5) & (d <= 24)]
        if d.size == 0: continue
        ar = max(np.sort(d)[d.size // 2], TABAN)
        out[i] = ort * (24.0 / ar) * 365.0
    return out

def kur():
    P = pickle.load(open('/tmp/panel.pkl', 'rb'))
    C = P['C']; barlar = C.index
    bn_sin = {}; gt_sin = {}
    gate_dosya = {os.path.basename(p)[:-4] for p in glob.glob('/tmp/gate/*.csv')}
    hedef = [s for s in C.columns if s in gate_dosya]
    print(f"panel {len(C.columns)} sembol · Gate verisi olan {len(hedef)}", flush=True)
    for k, s in enumerate(hedef):
        try:
            g = pd.read_csv(f'/tmp/gate/{s}.csv')
            b = pd.read_csv(f'{R}/data_funding_genis/{s}.csv', parse_dates=['date'])
        except Exception:
            continue
        if len(g) < 100 or len(b) < 100: continue
        g = g.sort_values('t').drop_duplicates('t')
        bo = pd.DataFrame({'t': b['date'].values.astype('datetime64[s]').astype(np.int64),
                           'r': b['funding'].values})
        bo = bo.sort_values('t').drop_duplicates('t')
        bn_sin[s] = yillik_panel(bo, barlar)
        gt_sin[s] = yillik_panel(g[['t', 'r']], barlar)
        if k % 50 == 0: print(f"  [{k}/{len(hedef)}] {s}", flush=True)
    BN = pd.DataFrame(bn_sin, index=barlar)
    GT = pd.DataFrame(gt_sin, index=barlar)
    pickle.dump({'BN': BN, 'GT': GT}, open('/tmp/capraz_panel.pkl', 'wb'))
    print(f"kaydedildi: {BN.shape}, ortak hucre "
          f"{int((BN.notna() & GT.notna()).sum().sum())}", flush=True)

if __name__ == '__main__':
    kur()
