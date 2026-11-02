#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 715 ön araştırma (aday A, coinler arası liderlik / gecikmeli yayılım): BTC t → alt sepeti t+1 korelasyonu (4 sa, 1 g), alt öz-gecikme,
BTC yönünde alt sepeti t+1 (maliyet hariç) ve kitap(t+1) ~ BTC(t). Yalnız ölçüm; test açılmadı. Kullanım: python3 arastirma_m715_on_arastirma.py"""
import sys; sys.path.insert(0,'/home/claude/binance-carry-bot')
import pickle, numpy as np, pandas as pd, arastirma_m346_prim as M
from tradfi_liste import TRADFI
P=pickle.load(open('/tmp/panel.pkl','rb')); C=P['C']; H=P['HAC']; Y=P['YAS']
cols=[c for c in C.columns if c not in TRADFI and c not in M.D8 and c!='BTCUSDT']
U=(C[cols].notna()&(H[cols]>=7e7)&(Y[cols]>=360))
for ad,fr in [("4 sa",None),("1 gün","D")]:
    c=C if fr is None else C.resample(fr).last()
    u=U if fr is None else U.resample(fr).last().fillna(False).astype(bool)
    r=c.pct_change(); b=r['BTCUSDT']; a=r[cols].where(u)
    alt=a.median(axis=1)
    out={}
    for yl in range(2021,2027):
        m=(r.index.year==yl)
        x=pd.DataFrame({"alt_t1":alt.shift(-1)[m],"btc_t":b[m],"alt_t":alt[m]}).dropna()
        # kesitsel: coinin t+1 getirisi - medyan, beta*btc_t ile
        out[yl]={"kor(alt t+1, btc t)":x.alt_t1.corr(x.btc_t),"kor(alt t+1, alt t)":x.alt_t1.corr(x.alt_t),"n":len(x)}
    print(ad); print(pd.DataFrame(out).T.round(3))
    # basit strateji: btc_t>0 ise alt sepeti long t+1 (yön), brüt, maliyet hariç
    s=np.sign(b)*alt.shift(-1); s=s.dropna()
    print("  btc yönünde alt sepeti t+1 (maliyet hariç) ort bp/bar:", round(s.mean()*1e4,2), "| bar başı ortalama |alt| hareketi bp:", round(alt.abs().mean()*1e4,1))
M.CIKTI="/tmp/m_ekim"; k=sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0,1))/2
bd=C['BTCUSDT'].resample('D').last().pct_change()
x=pd.DataFrame({"kitap_t1":k.shift(-1),"btc_t":bd.reindex(k.index)}).dropna()
print("kitap(t+1) ~ btc(t) korelasyon:", round(x.kitap_t1.corr(x.btc_t),3), "n", len(x))
