#!/usr/bin/env python3
# MADDE 399 — kullanicinin ikinci botu (+-%30 ters islem) karar saatine gore, 2022-2026.
import sys,numpy as np,pandas as pd
sys.path.insert(0,'/home/claude/binance-carry-bot')
import arastirma_m380_kullanici_kurali as K, arastirma_m379_haftalik_pump_short as Y
C,O,H,L,F,uy,lsr,f24,r24,sifir=K.hazirla()
sh=Y.sh
print(f"{'karar TRT':>9} {'NMAX':>4} | {'islem':>5} {'ort%':>6} {'med%':>6} | {'yillik':>8} {'Sh':>5} | yil yil getiri")
for nmax in (4,20):
  Y.NMAX=nmax
  for hu in (0,4,8,12,16,20):
    s=pd.Series(C.index.hour==hu,index=C.index)
    isl=[]
    for yon in (-1,1):
        kos=K.olay(r24,uy,lsr,f24,s,0.30,yon,"yok")
        isl+=K.islem(kos,C,O,H,L,F,1,0.25,yon)
    rr=np.array([x[3] for x in isl]); g=Y.portfoy(isl,C.index)
    e=(1+g).cumprod(); y=(e.iloc[-1]**(365.25/len(g))-1)*100
    yy=" ".join(f"{yr}:{((1+g[g.index.year==yr]).prod()-1)*100:+.0f}" for yr in range(2022,2027))
    son3=g[g.index>='2026-07-27']; s3=((1+son3).prod()-1)*100
    print(f"{(hu+3)%24:>7}:00 {nmax:>4} | {len(rr):>5} {rr.mean()*100:>+6.2f} {np.median(rr)*100:>+6.2f} | {y:>+8.1f} {sh(g):>5.2f} | {yy} | 27Tem-sonra {s3:+.0f}",flush=True)
