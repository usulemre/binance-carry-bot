"""Tarafa duyarli secim: her tarafta skora gore 2n aday, olcute gore n secilir.
olcut(i, adaylar, taraf) -> her aday icin puan (yuksek = sec). taraf=+1 long, -1 short."""
import sys; sys.path.insert(0,'/tmp')
from g import *
import os
HAVUZ=float(os.environ.get("HAVUZ","2"))

def bt2(bas,n,olcut=None,tp=0.7):
    nk=C.shape[1]; poz=np.zeros(nk); giris=np.full(nk,np.nan); eq=[1.0]; bek=None
    for i in range(bas,len(C)-1):
        if bek is not None and bek[0]==i:
            y=bek[1]; eq[-1]*=1-np.abs(y-poz).sum()*KOM
            poz=y; giris=np.where(y!=0,cv[i],np.nan); bek=None
        if (i-bas)%REB==0:
            g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]; ix=np.flatnonzero(g); nn=min(n,len(ix)//2); mm=min(int(HAVUZ*nn),len(ix)//2)
            if nn>=min(8,n):
                sc=rk(S[i][ix]); a=pd.Series(A[i][ix])
                if a.notna().sum()>=0.5*len(ix): sc=0.8*sc+0.2*(-a).rank(pct=True).fillna(0.5).values
                o=np.argsort(sc)
                if olcut is None:
                    lo=ix[o[:nn]]; sh=ix[o[-nn:]]
                else:
                    la=ix[o[:mm]]; sa=ix[o[-mm:]]
                    def sec(ad,taraf,sira_skor):
                        p=np.asarray(olcut(i,ad,taraf),float)
                        # olcut yoksa: skor sirasi (en uc) ile doldur
                        p=np.where(np.isfinite(p),pd.Series(p).rank(pct=True).values,np.nan)
                        yedek=sira_skor
                        p=np.where(np.isfinite(p),p,yedek)
                        return ad[np.argsort(-p)[:nn]]
                    uc_l=np.linspace(1,0,mm); uc_s=np.linspace(0,1,mm)
                    lo=sec(la,+1,uc_l); sh=sec(sa,-1,uc_s)
                y=np.zeros(nk); y[lo]=0.5/nn; y[sh]=-0.5/nn; bek=(i+1,y)
        gec=np.isfinite(cv[i])&np.isfinite(cv[i+1])
        br=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0); br=np.nan_to_num(br)
        cik=np.zeros(nk,bool)
        if tp>0:
            for k in np.flatnonzero(poz!=0):
                e=giris[k]
                if not (np.isfinite(e) and np.isfinite(cv[i,k]) and cv[i,k]>0 and np.isfinite(HV[i+1,k]) and np.isfinite(LV[i+1,k])): continue
                uzun=poz[k]>0; sev=e*(1+tp) if uzun else e*(1-tp)
                if (uzun and HV[i+1,k]>=sev) or ((not uzun) and LV[i+1,k]<=sev):
                    br[k]=sev/cv[i,k]-1; cik[k]=True
        r=np.nansum(poz*br)+np.nansum(np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])))
        eq.append(eq[-1]*(1+r))
        if cik.any():
            eq[-1]*=1-np.abs(poz[cik]).sum()*KOM
            poz=np.where(cik,0.0,poz); giris=np.where(cik,np.nan,giris)
    return pd.Series(eq,index=C.index[bas:])

def calis2(ad,n,olcut):
    gs=[bt2(1200+f,n,olcut).pct_change() for f in range(0,REB,6)]
    g=pd.concat(gs,axis=1).mean(axis=1).dropna(); E=(1+g).cumprod()
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E,open(f'/tmp/g2E_{ad}_{n}_{HAVUZ}.pkl','wb'))
    print(f'{ad:<14} havuz {HAVUZ} {n}+{n} | '+' | '.join(out),flush=True)

if __name__=='__main__':
    ad=sys.argv[1]; n=int(sys.argv[2])
    if ad=='uc':            # 2n adaydan en uc n (tabanla ayni olmali)
        calis2(ad,n,lambda i,a,t: np.full(len(a),np.nan))
    elif ad.startswith('rast'):
        rng=np.random.default_rng(int(ad[4:]))
        calis2(ad,n,lambda i,a,t: rng.random(len(a)))
    else:
        M=pickle.load(open('/tmp/metrik_panel.pkl','rb'))
        if ad=='oi':
            OI=M['sum_open_interest_value']; d=(OI/OI.shift(6)-1).values
            calis2(ad,n,lambda i,a,t: d[i][a])
        elif ad=='ls':
            L=np.log(M['count_long_short_ratio']).values
            calis2(ad,n,lambda i,a,t: -t*L[i][a])     # long tarafta dusuk oran, short tarafta yuksek
        elif ad=='top':
            L=np.log(M['sum_toptrader_long_short_ratio']).values
            calis2(ad,n,lambda i,a,t: -t*L[i][a])
        elif ad=='oi_ters':
            OI=M['sum_open_interest_value']; d=(OI/OI.shift(6)-1).values
            calis2(ad,n,lambda i,a,t: -d[i][a])
        elif ad in ('ls_ters','ls_long','ls_short'):
            L=np.log(M['count_long_short_ratio']).values
            if ad=='ls_ters':  calis2(ad,n,lambda i,a,t: t*L[i][a])
            if ad=='ls_long':  calis2(ad,n,lambda i,a,t: (-L[i][a]) if t>0 else np.full(len(a),np.nan))
            if ad=='ls_short': calis2(ad,n,lambda i,a,t: L[i][a] if t<0 else np.full(len(a),np.nan))
