"""Madde 214: CIKIS (KAR AL) EKSENININ BUTCESI.

Kar ayrisimi: funding +109,8 · ham fiyat -108,0 · KAR AL +210,5 = +212,3.
Yani kârin TAMAMI cikis kuralindan geliyor. O halde asil butce burada.

Olculen: her bacak-tutmasi icin
  MFE  = tutma suresince ULASILAN en iyi lehte hareket (kahin cikis)
  simdi= mevcut kural (esik asilirsa TP, asilmazsa kapanis)
Fark, cikis kuralinda kalan TAVAN.
"""
import sys; sys.path.insert(0,'/tmp')
from g import *
import numpy as np, pickle
S = pickle.load(open('/tmp/sk_bar48.pkl','rb')).reindex(index=C.index, columns=C.columns).values
H, NDILIM, GROSS, n = 30, 15, 3.0, 6
TPL, TPS = 0.40, 0.20
adim = H // NDILIM
mfe_l, mfe_s, sim_l, sim_s = [], [], [], []
for i in range(1200, len(C) - H - 2, adim):
    g = np.isfinite(S[i]) & np.isfinite(cv[i]) & U[i]
    ix = np.flatnonzero(g); nn = min(n, len(ix)//2)
    if nn < 4: continue
    sc = rk(S[i][ix]); a = pd.Series(A[i][ix])
    if a.notna().sum() >= 0.5*len(ix):
        sc = 0.8*sc + 0.2*(-a).rank(pct=True).fillna(0.5).values
    o = np.argsort(sc)
    for taraf, sec, tp, M, SM in ((+1, ix[o[:nn]], TPL, mfe_l, sim_l),
                                  (-1, ix[o[-nn:]], TPS, mfe_s, sim_s)):
        for j in sec:
            g0 = cv[i+1, j]
            if not np.isfinite(g0) or g0 <= 0: continue
            hi = HV[i+1:i+1+H, j]; lo = LV[i+1:i+1+H, j]; kap = cv[i+H, j]
            if not np.isfinite(kap) or not np.isfinite(hi).any(): continue
            if taraf > 0:
                en_iyi = np.nanmax(hi)/g0 - 1                 # long: yukari lehte
                tp_oldu = en_iyi >= tp
            else:
                en_iyi = 1 - np.nanmin(lo)/g0                 # short: asagi lehte
                tp_oldu = en_iyi >= tp
            M.append(en_iyi)
            SM.append(tp if tp_oldu else taraf*(kap/g0 - 1))
for ad, M, SM, tp in (('LONG', mfe_l, sim_l, TPL), ('SHORT', mfe_s, sim_s, TPS)):
    M = np.array(M); SM = np.array(SM)
    bacak = GROSS/(NDILIM*2*n)
    tur_yil = 365.25/ (H/6) * NDILIM      # her dilim 5 gunde bir, 15 dilim
    # yillik puan: bacak agirligi x ortalama getiri x yillik bacak sayisi
    bacak_yil = len(M) / ((len(C)-1200)/(6*365.25))
    print(f"\n{ad} ({len(M)} bacak-tutma, yilda {bacak_yil:.0f}):")
    print(f"  TP esigi                 %{tp*100:.0f}")
    print(f"  TP'ye ULASAN oran        %{100*np.mean(M>=tp):.1f}")
    print(f"  MFE (kahin cikis) ort    %{M.mean()*100:+.2f}  medyan %{np.median(M)*100:+.2f}")
    print(f"  MEVCUT kural ort         %{SM.mean()*100:+.2f}  medyan %{np.median(SM)*100:+.2f}")
    print(f"  yakalanan pay            %{100*SM.mean()/M.mean():.1f}")
    print(f"  yillik puan  mevcut      {bacak*SM.mean()*bacak_yil*100:+.1f}")
    print(f"  yillik puan  KAHIN       {bacak*M.mean()*bacak_yil*100:+.1f}")
    print(f"  ==> CIKIS BUTCESI        {bacak*(M.mean()-SM.mean())*bacak_yil*100:+.1f} puan/yil")
