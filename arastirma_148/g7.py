"""Tarafa duyarli secim: her tarafta skora gore 2n aday, olcute gore n secilir.
olcut(i, adaylar, taraf) -> her aday icin puan (yuksek = sec). taraf=+1 long, -1 short."""
import sys; sys.path.insert(0,'/tmp')
from g import *
OV=pickle.load(open('/tmp/hlo.pkl','rb'))['O'].values
import os
HAVUZ=float(os.environ.get("HAVUZ","2"))
TP=float(os.environ.get("TP","0.7"))
KOM=float(os.environ.get("KOM","0.0002"))
AKW=float(os.environ.get("AKIS","0.2")); TPX=float(os.environ.get("TP","0.7"))
DOLDUR=int(os.environ.get("DOLDUR","0"))
TAKIP_BAS=float(os.environ.get("TBAS","0"))
TAKIP_GERI=float(os.environ.get("TGERI","0.2"))
TERS=int(os.environ.get("TERS","0"))
FAZ=int(os.environ.get("FAZ","5"))   # dilim sayisi: tepki suresi = 120sa / FAZ
say_t=[0,0]

say_d=[0]
AY={'Lf':0.0,'Lp':0.0,'Sf':0.0,'Sp':0.0,'Ltp':0.0,'Stp':0.0,'kom':0.0}
def bt2(bas,n,olcut=None,tp=None):
    tp=TPX if tp is None else tp
    nk=C.shape[1]; poz=np.zeros(nk); giris=np.full(nk,np.nan); zirve=np.full(nk,np.nan); eq=[1.0]; bek=None
    for i in range(bas,len(C)-1):
        if bek is not None and bek[0]==i:
            y=bek[1]; eq[-1]*=1-np.abs(y-poz).sum()*KOM; AY['kom']+=np.abs(y-poz).sum()*KOM
            poz=y; giris=np.where(y!=0,cv[i],np.nan); zirve=np.where(y!=0,cv[i],np.nan); bek=None
        if (i-bas)%REB==0:
            g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]; ix=np.flatnonzero(g); nn=min(n,len(ix)//2); mm=min(int(HAVUZ*nn),len(ix)//2)
            if nn>=min(8,n):
                sc=rk(S[i][ix]); a=pd.Series(A[i][ix])
                if AKW>0 and a.notna().sum()>=0.5*len(ix): sc=(1-AKW)*sc+AKW*(-a).rank(pct=True).fillna(0.5).values
                o=np.argsort(sc)
                if olcut is None:
                    lo=ix[o[:nn]]; sh=ix[o[-nn:]]; lo_s=ix[o[:mm]]; sh_s=ix[o[::-1][:mm]]
                else:
                    la=ix[o[:mm]]; sa=ix[o[-mm:]]
                    def sec(ad,taraf,sira_skor):
                        p=np.asarray(olcut(i,ad,taraf),float)
                        # olcut yoksa: skor sirasi (en uc) ile doldur
                        p=np.where(np.isfinite(p),pd.Series(p).rank(pct=True).values,np.nan)
                        yedek=sira_skor
                        p=np.where(np.isfinite(p),p,yedek)
                        return ad[np.argsort(-p)]
                    uc_l=np.linspace(1,0,mm); uc_s=np.linspace(0,1,mm)
                    lo_s=sec(la,+1,uc_l); sh_s=sec(sa,-1,uc_s); lo=lo_s[:nn]; sh=sh_s[:nn]
                y=np.zeros(nk); y[lo]=0.5/nn; y[sh]=-0.5/nn; bek=(i+1,y); yedek_l=list(lo_s[nn:]); yedek_s=list(sh_s[nn:]); w_=0.5/nn
        gec=np.isfinite(cv[i])&np.isfinite(cv[i+1])
        br=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0); br=np.nan_to_num(br)
        cik=np.zeros(nk,bool)
        if tp>0 or TAKIP_BAS>0:
            for k in np.flatnonzero(poz!=0):
                e=giris[k]
                if not (np.isfinite(e) and np.isfinite(cv[i,k]) and cv[i,k]>0 and np.isfinite(HV[i+1,k]) and np.isfinite(LV[i+1,k])): continue
                uzun=poz[k]>0
                if TAKIP_BAS>0:
                    zirve[k]=max(zirve[k],HV[i+1,k]) if uzun else min(zirve[k],LV[i+1,k])
                    kar=(zirve[k]/e-1) if uzun else (1-zirve[k]/e)
                    if kar>=TAKIP_BAS:
                        sev_t=zirve[k]*(1-TAKIP_GERI) if uzun else zirve[k]*(1+TAKIP_GERI)
                        vur=(LV[i+1,k]<=sev_t) if uzun else (HV[i+1,k]>=sev_t)
                        if vur:
                            op=OV[i+1,k]; ff=(min(sev_t,op) if uzun else max(sev_t,op)) if np.isfinite(op) else sev_t
                            br[k]=ff/cv[i,k]-1; cik[k]=True; say_t[0]+=1; continue
                sev=e*(1+tp) if uzun else e*(1-tp)
                if tp>0 and ((uzun and HV[i+1,k]>=sev) or ((not uzun) and LV[i+1,k]<=sev)):
                    br[k]=sev/cv[i,k]-1; cik[k]=True; say_t[1]+=1
        fu=np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])); pr=poz*br
        L_=poz>0; S_=poz<0
        AY['Lf']+=np.nansum(fu[L_]); AY['Sf']+=np.nansum(fu[S_])
        AY['Lp']+=np.nansum(pr[L_&~cik]); AY['Sp']+=np.nansum(pr[S_&~cik])
        AY['Ltp']+=np.nansum(pr[L_&cik]); AY['Stp']+=np.nansum(pr[S_&cik])
        r=np.nansum(poz*br)+np.nansum(np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])))
        eq.append(eq[-1]*(1+r))
        if cik.any():
            eq[-1]*=1-np.abs(poz[cik]).sum()*KOM
            eski=poz.copy()
            yon=np.sign(poz[cik]); poz=np.where(cik,0.0,poz); giris=np.where(cik,np.nan,giris); zirve=np.where(cik,np.nan,zirve)
            if TERS and i+1<len(C)-1:
                for k in np.flatnonzero(cik):
                    if U[i+1,k] and np.isfinite(cv[i+1,k]):
                        poz[k]=-eski[k]; giris[k]=cv[i+1,k]; zirve[k]=cv[i+1,k]; eq[-1]*=1-abs(eski[k])*KOM
            if DOLDUR and i+1<len(C)-1:
                for yk in yon:
                    liste=yedek_l if yk>0 else yedek_s
                    while liste:
                        k2=liste.pop(0)
                        if poz[k2]==0 and U[i+1,k2] and np.isfinite(cv[i+1,k2]):
                            poz[k2]=yk*w_; giris[k2]=cv[i+1,k2]; eq[-1]*=1-w_*KOM; say_d[0]+=1; break
    return pd.Series(eq,index=C.index[bas:])

def calis2(ad,n,olcut):
    adim=max(1,REB//FAZ); gs=[bt2(1200+f,n,olcut,tp=TP).pct_change() for f in range(0,REB,adim)]
    g=pd.concat(gs,axis=1).mean(axis=1).dropna(); E=(1+g).cumprod()
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E,open(f'/tmp/g7E_{ad}_{n}_{HAVUZ}_{TP}_{KOM}_{DOLDUR}.pkl','wb'))
    yil=(len(C)-1200)/(6*365.25)
    print('takip cikis/yil',round(say_t[0]/5/yil),'sabit TP/yil',round(say_t[1]/5/yil))
    print(f'FAZ{FAZ} (tepki {120/FAZ:.0f}sa) | {ad:<4} tp{TP} kom{KOM} doldur{DOLDUR} dolan{say_d[0]//5} {n}+{n} | '+' | '.join(out),flush=True)

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
        elif ad in ('fark','fark_ters','lsdeg','lsdeg_ters','ls_lsdeg','ls_fark'):
            Lg=np.log(M['count_long_short_ratio']).values
            Lt=np.log(M['sum_toptrader_long_short_ratio']).values
            dg=Lg-np.roll(Lg,6,axis=0)
            def r_(v): return pd.Series(v).rank(pct=True).values
            if ad=='fark':       calis2(ad,n,lambda i,a,t: -t*(Lg[i][a]-Lt[i][a]))
            if ad=='fark_ters':  calis2(ad,n,lambda i,a,t: t*(Lg[i][a]-Lt[i][a]))
            if ad=='lsdeg':      calis2(ad,n,lambda i,a,t: -t*dg[i][a])
            if ad=='lsdeg_ters': calis2(ad,n,lambda i,a,t: t*dg[i][a])
            if ad=='ls_lsdeg':   calis2(ad,n,lambda i,a,t: r_(-t*Lg[i][a])+r_(-t*dg[i][a]))
            if ad=='ls_fark':    calis2(ad,n,lambda i,a,t: r_(-t*Lg[i][a])+r_(-t*(Lg[i][a]-Lt[i][a])))
