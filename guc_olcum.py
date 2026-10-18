"""Madde 216: CANLI GOZLEMLERIN GUCU.

Madde 151: toplam getiri karsilastirmasi 30 gunde olu edge'i ancak %15
olasilikla yakaliyor. Madde 214: karin TAMAMI kar-al hasadindan geliyor.
O halde hangi GOZLEM en cabuk karar verdirir?

Adaylar (hepsi canlida olculebilir):
  getiri    : gunluk ozsermaye getirisi
  funding   : tahsil edilen funding (gunluk, sermaye orani)
  tp_long   : LONG bacaklarin kar-al eşigine ulasma orani
  tp_short  : SHORT bacaklarin ulasma orani
  yayilim   : kesitsel funding yayilimi (saglik dedektorunun olcusu)

Her gozlem icin: CANLI dagilim (gercek secim) ve OLU dagilim (plasebo
secim = rastgele n long + n short, funding edge'i YOK). Sonra t-testi
gucu: N gun sonra %5 seviyesinde olu edge'i yakalama olasiligi.
"""
import sys; sys.path.insert(0,'/tmp')
from g import *
import numpy as np, pickle
from scipy import stats as st
S = pickle.load(open('/tmp/sk_bar48.pkl','rb')).reindex(index=C.index, columns=C.columns).values
H, NDILIM, GROSS, n = 30, 15, 3.0, 6
TPL, TPS = 0.40, 0.20
adim = H // NDILIM
rng = np.random.default_rng(17)
bacak = GROSS/(NDILIM*2*n)

def tur_gozlemleri(plasebo: bool):
    """Her tur icin (funding_tahsil, tp_l, tp_s, yayilim, getiri_yaklasik)."""
    out = []
    for i in range(1200, len(C) - H - 2, adim):
        g = np.isfinite(S[i]) & np.isfinite(cv[i]) & U[i]
        ix = np.flatnonzero(g); nn = min(n, len(ix)//2)
        if nn < 4: continue
        if plasebo:
            sec = rng.choice(ix, size=2*nn, replace=False)
            lo, sh = sec[:nn], sec[nn:]
        else:
            sc = rk(S[i][ix]); a = pd.Series(A[i][ix])
            if a.notna().sum() >= 0.5*len(ix):
                sc = 0.8*sc + 0.2*(-a).rank(pct=True).fillna(0.5).values
            o = np.argsort(sc); lo, sh = ix[o[:nn]], ix[o[-nn:]]
        # funding tahsilati: 5 gun boyunca long -ODE, short +ODE
        fl = -np.nansum(fv[i+1:i+1+H][:, lo])
        fs = +np.nansum(fv[i+1:i+1+H][:, sh])
        fund = (fl + fs) * bacak
        # TP ulasma oranlari
        def tp_oran(sec_, taraf, esik):
            v = []
            for j in sec_:
                g0 = cv[i+1, j]
                if not np.isfinite(g0) or g0 <= 0: continue
                if taraf > 0:
                    hi = HV[i+1:i+1+H, j]
                    if not np.isfinite(hi).any(): continue
                    v.append(float(np.nanmax(hi)/g0 - 1 >= esik))
                else:
                    lo_ = LV[i+1:i+1+H, j]
                    if not np.isfinite(lo_).any(): continue
                    v.append(float(1 - np.nanmin(lo_)/g0 >= esik))
            return np.mean(v) if v else np.nan
        tl = tp_oran(lo, +1, TPL); ts = tp_oran(sh, -1, TPS)
        # kesitsel yayilim (saglik olcusu)
        yay = float(np.nanstd(S[i][ix]))
        out.append((fund, tl, ts, yay))
    return np.array(out, float)

canli = tur_gozlemleri(False)
olu = tur_gozlemleri(True)
adlar = ['funding tahsilati', 'TP oranı LONG', 'TP oranı SHORT', 'kesitsel yayılım']
TUR_GUN = (H/6)/NDILIM     # bir tur kac gun = 0.333 gun (8 saat)
print(f"{len(canli)} tur, tur araligi {TUR_GUN*24:.0f} saat\n")
print(f"{'gozlem':20s} {'CANLI ort':>11s} {'OLU ort':>11s} {'std':>9s} "
      f"{'etki/std':>9s} | 14g  30g  60g  90g")
for k, ad in enumerate(adlar):
    c = canli[:, k]; o = olu[:, k]
    m = np.isfinite(c) & np.isfinite(o)
    c, o = c[m], o[m]
    if c.size < 20: continue
    sd = np.sqrt((c.var(ddof=1) + o.var(ddof=1))/2)
    if sd == 0: continue
    d = (c.mean() - o.mean())/sd          # Cohen d
    satir = f"{ad:20s} {c.mean():11.5f} {o.mean():11.5f} {sd:9.5f} {d:9.3f} |"
    for gun in (14, 30, 60, 90):
        N = max(2, int(gun / TUR_GUN))    # kac tur
        # tek ornek t-testi: canli ortalamasi olu ortalamasindan farkli mi
        se = sd/np.sqrt(N)
        kritik = st.norm.ppf(0.95)
        guc = 1 - st.norm.cdf(kritik - abs(d)*np.sqrt(N))
        satir += f" {guc*100:4.0f}%"
    print(satir)
