"""Madde 214: SINYAL EKSENININ BUTCESI.

Madde 213 icra ekseninin butcesini olctu (3,3 puan) ve ekseni kapatti.
Ayni disiplin sinyale uygulaniyor: MUKEMMEL ONGORU ile ne kazanilir?

  kahin_f : onumuzdeki 5 GUNUN GERCEKLESEN funding'ine gore sirala
            (funding ongorusunun TAVANI)
  kahin_p : onumuzdeki 5 gunun GERCEKLESEN FIYAT hareketine gore sirala
            (fiyat ongorusunun tavani - karsilastirma icin)
  kahin_t : ikisinin TOPLAMI - mutlak tavan
  mevcut  : 48sa gecmise donuk ortalama (bugunku bot)

Sinyal olarak verilen matris, motorun sirasiyla ayni: DUSUK = LONG.
Funding icin dusuk = long dogru (long, -ODE kazanir).
"""
import sys; sys.path.insert(0,'/tmp')
from g import *
import numpy as np, pickle
H = 30                      # 5 gun = 30 bar
nT, nK = C.shape
ODE = np.nan_to_num(fv)     # bar basina gerceklesen odeme
# ileriye donuk 5 gunluk toplam odeme (i+1 .. i+H)
cs = np.vstack([np.zeros((1, nK)), np.cumsum(ODE, axis=0)])
ileri_f = np.full((nT, nK), np.nan)
for i in range(nT - H - 1):
    ileri_f[i] = cs[i+1+H] - cs[i+1]
# ileriye donuk fiyat getirisi
ileri_p = np.full((nT, nK), np.nan)
with np.errstate(all='ignore'):
    for i in range(nT - H - 1):
        ileri_p[i] = cv[i+1+H] / cv[i+1] - 1
gec = ~np.isfinite(cv)
for M, ad in ((ileri_f, 'kahin_f'),
              (-ileri_p, 'kahin_p'),      # dusuk = long -> fiyat YUKSELECEK olan long
              (ileri_f - ileri_p, 'kahin_t')):
    X = M.copy(); X[gec] = np.nan
    df = pd.DataFrame(X, index=C.index, columns=C.columns)
    pickle.dump(df, open(f'/tmp/sk_{ad}.pkl','wb'))
    print(f"{ad:9s} hucre {int(df.notna().sum().sum())}", flush=True)
# kontrol: kahin_f gercekten ileriye mi bakiyor
i0 = 3000
print("\nkontrol - kahin_f[i] ile gercek 5 gun toplami ayni mi:",
      bool(np.allclose(np.nan_to_num(ileri_f[i0]),
                       np.nan_to_num(ODE[i0+1:i0+1+H].sum(axis=0)))))
