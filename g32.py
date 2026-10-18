"""Tarafa duyarli secim: her tarafta skora gore 2n aday, olcute gore n secilir.
olcut(i, adaylar, taraf) -> her aday icin puan (yuksek = sec). taraf=+1 long, -1 short."""
import sys; sys.path.insert(0,'/tmp')
from g import *
OV=pickle.load(open('/tmp/hlo.pkl','rb'))['O'].values
import os
HAVUZ=float(os.environ.get("HAVUZ","2"))
_fz=int(os.environ.get('FAZ_KAY','0'))
REB=int(os.environ.get('REB_GUN','5'))*6   # tutma suresi (gun -> 4s bar)
# SINYAL PENCERESI: funding orani kac GUN geriye ortalanarak siralansin.
# DIKKAT (MADDE 209): 0 = panelin KENDI HALI, ve panelin kendi hali
# `SIN.rolling(18 bar).mean()` yani 3 GUNLUK ORTALAMADIR - "en son odeme"
# DEGIL. Buradaki rolling, o 3 gunun USTUNE biner: SINYAL_GUN=3 efektif
# ~6 gun demektir. Eski yorum "en son odeme" diyordu; madde 182 o etikete
# guvenip canli botun penceresini 72sa -> 8sa cekti ve bot HIC OLCULMEMIS
# bir pencereyle calisiyordu (8sa Sharpe 2.70 vs 72sa 2.91).
_SP = float(os.environ.get('SINYAL_GUN', '0'))
if _SP > 0:
    import pandas as _pd
    _bar = max(1, int(round(_SP * 6)))
    S = _pd.DataFrame(S).rolling(_bar, min_periods=max(1, _bar // 2)).mean().values

# MADDE 209: SINYAL PANELINI DISTAN YUKLE (canli botun tahmincisiyle kurulmus)
_SKD = os.environ.get("SK_DOSYA", "")
if _SKD:
    import pickle as _pk2
    _S2 = _pk2.load(open(_SKD, "rb"))
    S = _S2.reindex(index=C.index, columns=C.columns).values
    print(f"# sinyal DISTAN: {_SKD}  ({np.isfinite(S).sum()} hucre)", flush=True)

_HES = float(os.environ.get("HACIM_ESIK", "1e8"))
_DON = float(os.environ.get("DONUK_ESIK", "0.10"))
if _HES != 1e8 or _DON != 0.10:
    import pickle as _pk, carry_denetim as _D
    _P = _pk.load(open('/tmp/panel.pkl', 'rb'))
    _uy = _D.uygunluk(_P['C'], _P['HAC'], _P['YAS'], _P['DON'], hacim=_HES, donuk_esik=_DON)
    from tradfi_liste import TRADFI as _TF
    _uy = _uy.copy(); _uy[[c for c in _uy.columns if c in _TF]] = False
    U = _uy.values

# DELIST UFKU: canli bot delisti duyurulmus sembolu YENI SECIME almiyor
# (DELIST_UFUK_GUN=30). Backtest'te duyuru verisi yok; vekil olarak her
# sembolun serisi bittiginden onceki N gunu uygunluktan dusuruyoruz.
_DU = float(os.environ.get('DELIST_UFUK', '0'))
if _DU > 0:
    import numpy as _np
    _bar = int(round(_DU * 6))
    _U = U.copy()
    _fin = _np.isfinite(cv)
    _nT = _U.shape[0]
    for _j in range(_U.shape[1]):
        _ix = _np.flatnonzero(_fin[:, _j])
        if _ix.size == 0:
            continue
        _son = _ix[-1]
        if _son >= _nT - 6:      # panel sonuna kadar yasayan sembol: delist yok
            continue
        _U[max(0, _son - _bar + 1):_son + 1, _j] = False
    U = _U

# SEMBOL DAYANIKLILIGI: evrenden rastgele bir pay DUSUR
_DUS=float(os.environ.get('SEMBOL_DUS','0'))
_DTOHUM=int(os.environ.get('DTOHUM','0'))
if _DUS>0:
    _r=np.random.default_rng(_DTOHUM)
    _n=U.shape[1]; _k=int(_n*_DUS)
    _at=_r.choice(_n,size=_k,replace=False)
    U=U.copy(); U[:,_at]=False
TP=float(os.environ.get("TP","0.7"))
KOM=float(os.environ.get("KOM","0.0002"))
AKW=float(os.environ.get("AKIS","0.2")); TPX=float(os.environ.get("TP","0.7"))
SLL=float(os.environ.get("SLL","0"))   # LONG bacak stop (0=kapali)
SLS=float(os.environ.get("SLS","0"))   # SHORT bacak stop
UCELE=float(os.environ.get("UCELE","0"))   # 0=kapali. >=UCELE pump long adayi OLAMAZ
_uc6=int(os.environ.get("UCGERI","6"))
_UART=np.full_like(cv,np.nan); _UART[_uc6:]=cv[_uc6:]/np.where(cv[:-_uc6]>0,cv[:-_uc6],np.nan)-1
SSEC=os.environ.get("SSEC","funding")  # funding|rast|voldus|volyuk|btc
_srng=np.random.default_rng(int(os.environ.get("STOHUM","0")))
_ret=np.vstack([np.full((1,C.shape[1]),np.nan),cv[1:]/cv[:-1]-1])
VOL=pd.DataFrame(_ret).rolling(30,min_periods=20).std().values
_BTC=[i for i,c_ in enumerate(C.columns) if c_=='BTCUSDT']
BTCI=_BTC[0] if _BTC else -1
# MADDE 215: TARAF BAZLI MAKS TUTMA SURESI (bar; 6 bar = 1 gun).
# Madde 214: LONG bacak kârının %73'u funding (CARRY -> uzun tutmayi sever),
# SHORT bacak kârının %86'si fiyat+TP (GERI DONUS HASADI -> cabuk cikmayi
# sever). Bu asimetri hic denenmedi. 0 = sinir yok (eski davranis).
YAS_L=int(os.environ.get("YAS_L","0"))
YAS_S=int(os.environ.get("YAS_S","0"))
say_y=[0,0]
TPL=float(os.environ.get("TPL","-1"))   # -1 = tp ile ayni
TPS=float(os.environ.get("TPS","-1"))
DOLDUR=int(os.environ.get("DOLDUR","0"))
TAKIP_BAS=float(os.environ.get("TBAS","0"))
TAKIP_GERI=float(os.environ.get("TGERI","0.2"))
TERS=int(os.environ.get("TERS","0"))
FAZ=int(os.environ.get("FAZ","5"))
GEC=int(os.environ.get("GEC","1"))
REZERV=float(os.environ.get("REZERV","0"))      # ucta firsat cikinca devreye giren sermaye payi
REZ_ESIK=float(os.environ.get("REZ_ESIK","1.0"))# yillik funding esigi (|S| >= bu ise "uc firsat")
YARIM=int(os.environ.get("YARIM","0"))          # kar alda pozisyonun YARISI kapanir
AYNI=int(os.environ.get("AYNI","0"))            # kar al sonrasi AYNI yonde yeniden gir
say_r=[0]
REZ_RAST=int(os.environ.get("REZ_RAST","0"))
TOL=float(os.environ.get("TOL","0"))   # hedefin bu oraninden az sapan bacaga dokunma
KAP=float(os.environ.get("KAP","0"))   # coin basina EK agirlik ust siniri
_rz=np.random.default_rng(int(os.environ.get("TOHUM","1")))   # sinyalden kac bar sonra girilsin (1 bar = 4 saat)   # dilim sayisi: tepki suresi = 120sa / FAZ
say_t=[0,0]

say_d=[0]
AY={'Lf':0.0,'Lp':0.0,'Sf':0.0,'Sp':0.0,'Ltp':0.0,'Stp':0.0,'kom':0.0}
GUN={}
YIL={}   # yil -> [Lf,Lp,Ltp,Sf,Sp,Stp]
def bt2(bas,n,olcut=None,tp=None):
    tp=TPX if tp is None else tp
    nk=C.shape[1]; poz=np.zeros(nk); giris=np.full(nk,np.nan); zirve=np.full(nk,np.nan); tp_yapildi=np.zeros(nk,bool); eq=[1.0]; bek=None; _yas=np.zeros(nk,int)
    for i in range(bas,len(C)-1):
        if bek is not None and bek[0]==i:
            y=bek[1]
            if TOL>0:
                bacak=0.5/max(1,int(np.count_nonzero(y)/2))
                kucuk=np.abs(y-poz)<TOL*bacak
                y=np.where(kucuk,poz,y)
            eq[-1]*=1-np.abs(y-poz).sum()*KOM
            poz=y; giris=np.where(y!=0,cv[i],np.nan); zirve=np.where(y!=0,cv[i],np.nan); tp_yapildi=np.where(y!=0,False,tp_yapildi); bek=None
        if (i-bas)%REB==0:
            g=np.isfinite(S[i])&np.isfinite(cv[i])&U[i]
            if UCELE>0:
                # MADDE 196: uc hareket etmis coin KARSI tarafta aday olmasin.
                # Pump olmus coin long adayi olmaz (tepeden alma), dump olmus
                # coin short adayi olmaz (dipten satma). Eleme SIRALAMADAN
                # ONCE yapilir, yani sirayi degistirmez - adayi cikarir.
                _a=_UART[i]
                _pump=np.isfinite(_a)&(_a>=UCELE)
                _dump=np.isfinite(_a)&(_a<=-UCELE)
                _sr=np.where(g,S[i],np.nan)
                _med=np.nanmedian(_sr) if np.isfinite(_sr).any() else 0.0
                # long adayi = medyandan DUSUK funding; short adayi = YUKSEK
                g=g&~(_pump&(_sr<_med))&~(_dump&(_sr>_med))
            ix=np.flatnonzero(g); nn=min(n,len(ix)//2); mm=min(int(HAVUZ*nn),len(ix)//2)
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
                taban=0.5-REZERV/2
                # MADDE 190: SHORT tarafi funding yerine baska olcute gore sec
                if SSEC!="funding":
                    uy=np.flatnonzero(U[i]&np.isfinite(cv[i]))
                    _lset=set(int(x) for x in lo)
                    uy=np.array([k for k in uy if int(k) not in _lset],dtype=int)
                    if SSEC=="btc" and BTCI>=0 and U[i,BTCI] and np.isfinite(cv[i,BTCI]):
                        sh=np.array([BTCI])
                    elif len(uy)>=len(lo):
                        if SSEC=="rast":
                            sh=_srng.choice(uy,len(lo),replace=False)
                        else:
                            v=VOL[i][uy]
                            iy=np.argsort(np.where(np.isfinite(v),v,np.inf))
                            sh=uy[iy[:len(lo)]] if SSEC=="voldus" else uy[iy[::-1][:len(lo)]]
                y=np.zeros(nk); y[lo]=taban/len(lo); y[sh]=-taban/len(sh)
                if REZERV>0:
                    ul=([int(_rz.choice(lo))] if _rz.random()<0.4 else []) if REZ_RAST else [k for k in lo if np.isfinite(S[i,k]) and S[i,k]<=-REZ_ESIK]
                    if ul:
                        pay=(REZERV/2)/len(ul)
                        if KAP>0: pay=min(pay,KAP)
                        kullanilan=pay*len(ul)
                        for k in ul: y[k]+=pay
                        for k in sh: y[k]-=kullanilan/len(sh)   # notrluk korunur
                        say_r[0]+=1
                bek=(i+GEC,y); yedek_l=list(lo_s[nn:]); yedek_s=list(sh_s[nn:]); w_=0.5/nn
        gec=np.isfinite(cv[i])&np.isfinite(cv[i+1])
        br=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0); br=np.nan_to_num(br)
        cik=np.zeros(nk,bool); yaridan=np.zeros(nk,bool)
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
                # MADDE 191: taraf bazli STOP. Muhafazakar: bar acilisi
                # seviyenin otesindeyse ACILISTAN dolar, ve ayni barda hem
                # stop hem kar al varsa STOP once sayilir.
                _sl = SLL if uzun else SLS
                if _sl > 0:
                    _ss = e*(1-_sl) if uzun else e*(1+_sl)
                    _vur = (LV[i+1,k] <= _ss) if uzun else (HV[i+1,k] >= _ss)
                    if _vur:
                        _op = OV[i+1,k]
                        _ff = (min(_ss,_op) if uzun else max(_ss,_op)) if np.isfinite(_op) else _ss
                        br[k] = _ff/cv[i,k]-1; cik[k]=True; say_t[1]+=1
                        continue
                _tp = (TPL if TPL>=0 else tp) if uzun else (TPS if TPS>=0 else tp)
                sev=e*(1+_tp) if uzun else e*(1-_tp)
                if _tp>0 and ((uzun and HV[i+1,k]>=sev) or ((not uzun) and LV[i+1,k]<=sev)):
                    if YARIM and tp_yapildi[k]:
                        continue                  # yarisi zaten alindi, kalan normal getiri alir
                    br[k]=sev/cv[i,k]-1; say_t[1]+=1
                    if YARIM: yaridan[k]=True; tp_yapildi[k]=True
                    else: cik[k]=True
        # MADDE 215: taraf bazli maks tutma suresi. TP/stop kontrolunden
        # SONRA bakilir: ayni barda TP varsa TP kazanir (daha iyi fiyat).
        if YAS_L or YAS_S:
            for _k in np.flatnonzero((poz!=0)&~cik):
                _sn = YAS_L if poz[_k]>0 else YAS_S
                if _sn and _yas[_k]+1 >= _sn:
                    cik[_k]=True                      # bar kapanisindan cik
                    say_y[0 if poz[_k]>0 else 1]+=1
        fu=np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])); pr=poz*br
        L_=poz>0; S_=poz<0
        for _k in np.flatnonzero(poz!=0):
            _g=int(min(5,(_yas[_k])//6))
            _t='L' if poz[_k]>0 else 'S'
            _c=GUN.setdefault((_t,_g),[0.0,0.0,0.0,0])
            _c[0]+=float(np.nan_to_num(fu[_k]))
            if cik[_k]: _c[2]+=float(poz[_k]*np.nan_to_num(br[_k]))
            else:       _c[1]+=float(poz[_k]*np.nan_to_num(br[_k]))
            _c[3]+=1
        _yas=np.where(poz!=0,_yas+1,0)
        _yy=C.index[i+1].year; _yc=YIL.setdefault(_yy,[0.0]*6)
        _yc[0]+=float(np.nansum(fu[L_])); _yc[3]+=float(np.nansum(fu[S_]))
        _yc[1]+=float(np.nansum(pr[L_&~cik])); _yc[4]+=float(np.nansum(pr[S_&~cik]))
        _yc[2]+=float(np.nansum(pr[L_&cik])); _yc[5]+=float(np.nansum(pr[S_&cik]))
        AY['Lf']+=np.nansum(fu[L_]); AY['Sf']+=np.nansum(fu[S_])
        AY['Lp']+=np.nansum(pr[L_&~cik]); AY['Sp']+=np.nansum(pr[S_&~cik])
        AY['Ltp']+=np.nansum(pr[L_&cik]); AY['Stp']+=np.nansum(pr[S_&cik])
        if yaridan.any():
            # yarisi TP seviyesinden cikar, yarisi barin kapanisiyla devam eder
            kapanis=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0)
            br=np.where(yaridan,0.5*br+0.5*np.nan_to_num(kapanis),br)
        r=np.nansum(poz*br)+np.nansum(np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])))
        eq.append(eq[-1]*(1+r))
        if yaridan.any():
            eq[-1]*=1-np.abs(poz[yaridan]).sum()*0.5*KOM
            poz=np.where(yaridan,poz*0.5,poz)
        if cik.any():
            eq[-1]*=1-np.abs(poz[cik]).sum()*KOM
            eski=poz.copy()
            yon=np.sign(poz[cik]); poz=np.where(cik,0.0,poz); giris=np.where(cik,np.nan,giris); zirve=np.where(cik,np.nan,zirve)
            if AYNI and i+1<len(C)-1:
                for k in np.flatnonzero(cik):
                    if U[i+1,k] and np.isfinite(cv[i+1,k]) and np.isfinite(S[i+1,k]) and (
                       (eski[k]>0 and S[i+1,k]<=-REZ_ESIK) or (eski[k]<0 and S[i+1,k]>=REZ_ESIK)):
                        poz[k]=eski[k]; giris[k]=cv[i+1,k]; zirve[k]=cv[i+1,k]; eq[-1]*=1-abs(eski[k])*KOM
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
    adim=max(1,REB//FAZ); gs=[bt2(1200+_fz+f,n,olcut,tp=TP).pct_change() for f in range(0,REB,adim)]
    g=pd.concat(gs,axis=1).mean(axis=1).dropna(); E=(1+g).cumprod()
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E,open(f'/tmp/g19E_{_fz}.pkl','wb'))
    yil=(len(C)-1200)/(6*365.25)
    print('takip cikis/yil',round(say_t[0]/5/yil),'sabit TP/yil',round(say_t[1]/5/yil),
          '| YAS cikisi/yil L',round(say_y[0]/5/yil),'S',round(say_y[1]/5/yil))
    yl=(len(C)-1200)/(6*365.25)
    t=sum(abs(v) for k,v in AY.items() if k!='kom')
    print('  YIL YIL LONG vs SHORT TARAF (yillik puan, 5 fazin ortalamasi):')
    print(f'    {"yil":<6}{"LONG fnd":>10}{"LONG fiy":>10}{"LONG tp":>9}{"LONG NET":>10}   {"SHORT fnd":>10}{"SHORT fiy":>10}{"SHORT tp":>9}{"SHORT NET":>11}')
    for _y in sorted(YIL):
        v=[x/5*100 for x in YIL[_y]]
        print(f'    {_y:<6}{v[0]:>+10.1f}{v[1]:>+10.1f}{v[2]:>+9.1f}{v[0]+v[1]+v[2]:>+10.1f}   '
              f'{v[3]:>+10.1f}{v[4]:>+10.1f}{v[5]:>+9.1f}{v[3]+v[4]+v[5]:>+11.1f}')
    print('  TUTMA GUNUNE GORE (yillik puan, 5 fazin ortalamasi):')
    print(f'    {"":<6}{"LONG fnd":>10}{"LONG fiyat":>12}{"LONG tp":>10}{"SHORT fnd":>11}{"SHORT fiyat":>12}{"SHORT tp":>10}')
    _y=(len(C)-1200)/(6*365.25)
    for _g in range(6):
        _l=GUN.get(('L',_g),[0,0,0,0]); _s=GUN.get(('S',_g),[0,0,0,0])
        _ad=f'{_g+1}.gun' if _g<5 else '6+'
        print(f'    {_ad:<6}{_l[0]/5/_y*100:>+10.1f}{_l[1]/5/_y*100:>+12.1f}{_l[2]/5/_y*100:>+10.1f}'
              f'{_s[0]/5/_y*100:>+11.1f}{_s[1]/5/_y*100:>+12.1f}{_s[2]/5/_y*100:>+10.1f}')
    print('  KAR KAYNAKLARI (5 fazin toplami, yillik puan olarak):')
    for k,ad in [('Sf','SHORT bacak funding'),('Lf','LONG bacak funding'),
                 ('Sp','SHORT bacak fiyat'),('Lp','LONG bacak fiyat'),
                 ('Stp','SHORT kar-al fiyat'),('Ltp','LONG kar-al fiyat')]:
        print(f'    {ad:<22} {AY[k]/5/yl*100:>+8.1f} puan/yil   (payi %{abs(AY[k])/t*100:>4.1f})')
    print(f'    {"TOPLAM":<22} {sum(AY[k] for k in ("Sf","Lf","Sp","Lp","Stp","Ltp"))/5/yl*100:>+8.1f} puan/yil')
    print(f'REB{REB//6}g FAZ{_fz} TOL{TOL} REZ{REZERV}/{REZ_ESIK} YARIM{YARIM} AYNI{AYNI} rez_kullanim/yil {say_r[0]/5/((len(C)-1200)/(6*365.25)):.0f} | {ad:<4} tp{TP} kom{KOM} doldur{DOLDUR} dolan{say_d[0]//5} {n}+{n} | '+' | '.join(out),flush=True)

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
        elif ad in ('pump','ls_pump'):
            # taraf duyarli fiyat hareketi: short tarafta EN COK YUKSELEN,
            # long tarafta EN COK DUSEN secilsin (kullanicinin gozlemi)
            _g6=int(os.environ.get('PGERI','6'))
            _art=np.full_like(cv,np.nan)
            _art[_g6:]=cv[_g6:]/np.where(cv[:-_g6]>0,cv[:-_g6],np.nan)-1
            if ad=='pump':
                calis2(ad,n,lambda i,a,t: -t*_art[i][a])
            else:
                L2=np.log(M['count_long_short_ratio']).values
                _w=float(os.environ.get('PW','0.5'))
                def _bl(i,a,t):
                    p1=pd.Series(-t*L2[i][a]).rank(pct=True).fillna(0.5).values
                    p2=pd.Series(-t*_art[i][a]).rank(pct=True).fillna(0.5).values
                    return (1-_w)*p1+_w*p2
                calis2(ad,n,_bl)
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
