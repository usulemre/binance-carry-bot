import sys,os; sys.path.insert(0,"/home/claude/binance-carry-bot")
import sys; sys.argv=["x"]
exec(open("arastirma_m649_yeni_kitap_tarama.py").read().split("BAS = ")[0])
BAS="2022-06-15"
TOPs=gun(MP["sum_toptrader_long_short_ratio"])
def kurq(rk,yon,H,q=0.2,kom=None):
    W=((rk>=1-q).astype(float)-(rk<=q).astype(float))*yon
    lo=W.clip(lower=0); so=(-W).clip(lower=0)
    Wl=lo.div(lo.sum(axis=1).replace(0,np.nan),axis=0).fillna(0)*0.5; Ws=-so.div(so.sum(axis=1).replace(0,np.nan),axis=0).fillna(0)*0.5
    if kom is not None: U.KOM=kom
    g=U.getiri(Wl+Ws,C,Fd,H); gl=U.getiri(Wl,C,Fd,H); gs=U.getiri(Ws,C,Fd,H); U.KOM=0.0005
    dev=(Wl+Ws).iloc[::H].diff().abs().sum(axis=1).mean()/H
    return g[g.index>=BAS], gl[gl.index>=BAS], gs[gs.index>=BAS], dev
def ozet(ad,g,ek=""):
    IS,OOS=g[g.index<"2025-01-01"],g[g.index>="2025-01-01"]
    e=(1+g).cumprod(); dd=((e/e.cummax())-1).min()*100
    yy=g.groupby(g.index.year).apply(yil).round(0).astype(int).to_dict()
    ix=g.index.intersection(carry.index); rho=np.corrcoef(g.loc[ix],carry.loc[ix])[0,1]
    print(f"{ad:34s} IS {sh(IS):+.2f} OOS {sh(OOS):+.2f} yıl {yil(g):+6.1f} dd {dd:6.1f} en kötü gün {g.min()*100:5.1f} rho {rho:+.2f} {yy} {ek}")
print(U.KOM)
for nm,sig in (("TOP (hesap)",np.log(TOP)),("TOPs (pozisyon)",np.log(TOPs)),("GLS (genel)",np.log(GLS))):
    for (q,H) in ((0.2,1),(0.1,1),(0.3,1),(0.2,2),(0.2,3)):
        rk=sig.replace([np.inf,-np.inf],np.nan).where(uy).rank(axis=1,pct=True)
        g,gl,gs,dev=kurq(rk,-1,H,q)
        ozet(f"{nm} q{q} H{H}",g,f"| long {yil(gl):+.0f} short {yil(gs):+.0f} devir/g {dev:.2f}")
rk=np.log(TOP).replace([np.inf,-np.inf],np.nan).where(uy).rank(axis=1,pct=True)
g,_,_,_=kurq(rk,-1,1,0.2,kom=0.001); ozet("TOP q0.2 H1 KOM 10bp",g)
g,_,_,_=kurq(rk,-1,1,0.2,kom=0.0015); ozet("TOP q0.2 H1 KOM 15bp",g)
# hacim 50M evren
uy2=uy&(gun(HAC4)>=5e7)
rk2=np.log(TOP).replace([np.inf,-np.inf],np.nan).where(uy2).rank(axis=1,pct=True)
g,_,_,_=kurq(rk2,-1,1,0.2); ozet("TOP q0.2 H1 hacim≥50M",g)
print("evren boyu ort:", int(uy[uy.index>=BAS].sum(axis=1).mean()), "50M:", int(uy2[uy2.index>=BAS].sum(axis=1).mean()))
# GLS ile korelasyon (sinyal düzeyi)
a=np.log(TOP).where(uy).rank(axis=1,pct=True); b=np.log(GLS).where(uy).rank(axis=1,pct=True)
print("TOP-GLS kesitsel sıra korelasyonu ort:", round(a[a.index>=BAS].corrwith(b[b.index>=BAS],axis=1).mean(),2))
