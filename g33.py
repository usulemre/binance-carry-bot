"""Tarafa duyarli secim: her tarafta skora gore 2n aday, olcute gore n secilir.
olcut(i, adaylar, taraf) -> her aday icin puan (yuksek = sec). taraf=+1 long, -1 short."""
import sys; sys.path.insert(0,'/tmp')
from g import *
OV=pickle.load(open('/tmp/hlo.pkl','rb'))['O'].values
import os
HAVUZ=float(os.environ.get("HAVUZ","2"))
_HL=float(os.environ.get("HAVUZ_L","0")); _HS=float(os.environ.get("HAVUZ_S","0"))   # madde 364
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
#
# *** MADDE 299 UYARISI: BU PANEL SADECE BIR SIRALAMA DEGIL. ***
# Motor S'nin BUYUKLUGUNU de okuyor: REZ_ESIK karsilastirmalari
# (`S[i,k] <= -REZ_ESIK` ve satir ~490'daki yeniden-giris kurali) sinyali
# DOGRUDAN bir funding esigiyle kiyaslar. Bu yuzden:
#   - Paneli yuzdelik SIRAYA cevirirsen (0..1) rezerv HIC devreye girmez;
#     secim birebir ayni kalir ama sonuc degisir. Madde 299'da deneyip
#     pariteyi kirdim (+%112,3 -> +%94,4) ve "secim degisti" sandim;
#     301 rebalance barinin HEPSINDE secim AYNIYDI, kirilan rezervdi.
#   - Funding disi bir panel (or. ham gecmis getiri, ~0,1 olcegi) esigi
#     surekli asar: madde 298'in momentum kollarinda rezerv kullanimi
#     176-218/yil cikti, kontrolde 58. O yuzden funding-disi bir panelle
#     kontrole karsi karsilastirma yapiyorsan REZERV=0 ile KOS, yoksa
#     karsilastirma rezerv davranisini de iceriyor demektir.
#   - Sinyal harmani FUNDING BIRIMINDE yapilmali (madde 299: F + w*sigma_F*z),
#     o zaman w=0 pariteyi birebir verir.
_SKD = os.environ.get("SK_DOSYA", "")
if _SKD:
    import pickle as _pk2
    _S2 = _pk2.load(open(_SKD, "rb"))
    S = _S2.reindex(index=C.index, columns=C.columns).values
    print(f"# sinyal DISTAN: {_SKD}  ({np.isfinite(S).sum()} hucre)", flush=True)

# MADDE 490: TARAF BAZLI SINYAL PENCERESI. SK_DOSYA_S verilirse SHORT adaylari bu panelin sirasiyla secilir
# (long'lar SK_DOSYA ile). Long havuzuna giren coin short adayi olamaz. Bos -> tek panel (parite).
_SKDS = os.environ.get("SK_DOSYA_S", "").strip()
SS = None
if _SKDS:
    import pickle as _pk3
    SS = _pk3.load(open(_SKDS, "rb")).reindex(index=C.index, columns=C.columns).values
    print(f"# short sinyali DISTAN: {_SKDS}", flush=True)
_HES = float(os.environ.get("HACIM_ESIK", "1e8"))
_DON = float(os.environ.get("DONUK_ESIK", "0.10"))
# MADDE 228: listeleme yasi esigi (gun). Madde 133'te taranmis, hic
# yeniden acilmamisti; motor onu disari vermiyordu.
_YAS_GUN = float(os.environ.get("YAS_GUN", "90"))
# MADDE 507: GORELI EVREN. HACIM_SIRA=K>0 -> hacim kosulu "mutlak esik" yerine "hacimde ilk K" (yas/donuk/tradfi ayni;
# HACIM_TABAN altindaki coin yine giremez). Piyasa buyuklugune uyarlanir (2020'de 70M esigi ~5 coin birakiyordu). 0 -> parite.
_HSIRA = int(os.environ.get("HACIM_SIRA", "0")); _HTABAN = float(os.environ.get("HACIM_TABAN", "2e7"))
if _HES != 1e8 or _DON != 0.10 or _YAS_GUN != 90 or _HSIRA > 0:
    import pickle as _pk, carry_denetim as _D
    _P = _pk.load(open('/tmp/panel.pkl', 'rb'))
    _uy = _D.uygunluk(_P['C'], _P['HAC'], _P['YAS'], _P['DON'], hacim=_HES,
                      yas_bar=int(round(_YAS_GUN * 6)), donuk_esik=_DON)
    from tradfi_liste import TRADFI as _TF
    _uy = _uy.copy(); _uy[[c for c in _uy.columns if c in _TF]] = False
    if _HSIRA > 0:
        _taban = _D.uygunluk(_P['C'], _P['HAC'], _P['YAS'], _P['DON'], hacim=_HTABAN,
                             yas_bar=int(round(_YAS_GUN * 6)), donuk_esik=_DON)
        _taban[[c for c in _taban.columns if c in _TF]] = False
        _rk = _P['HAC'].where(_taban).rank(axis=1, ascending=False)
        _uy = _taban & (_rk <= _HSIRA)
        print(f"# HACIM_SIRA={_HSIRA} taban {_HTABAN:.0e}: ortalama uygun {float(_uy.sum(axis=1).mean()):.1f}", flush=True)
    U = _uy.reindex(index=C.index, columns=C.columns).fillna(False).values

# MADDE 461: GENC COIN YARIM AGIRLIK. GENC_GUN>0 -> evren yasi GENC_GUN'e iner, ama
# YAS_GUN'den genc coinlerin hedef agirligi GENC_PAY ile carpilir. 0 -> kapali (parite).
_GENC = float(os.environ.get("GENC_GUN", "0")); GENC_PAY = float(os.environ.get("GENC_PAY", "0.5"))
GENCV = None
if _GENC > 0:
    import pickle as _pkg, carry_denetim as _Dg
    _Pg = _pkg.load(open('/tmp/panel.pkl', 'rb'))
    _ug = _Dg.uygunluk(_Pg['C'], _Pg['HAC'], _Pg['YAS'], _Pg['DON'], hacim=_HES,
                       yas_bar=int(round(_GENC * 6)), donuk_esik=_DON)
    from tradfi_liste import TRADFI as _TFg
    _ug = _ug.copy(); _ug[[c for c in _ug.columns if c in _TFg]] = False
    _ug = _ug.reindex(index=C.index, columns=C.columns).fillna(False).values
    GENCV = _ug & ~U
    U = _ug | U
    print(f"# GENC_GUN={_GENC} GENC_PAY={GENC_PAY}: genc hucre payi {GENCV.sum()/max(1,U.sum()):.3f}", flush=True)

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

# MADDE 295: ADI VERILEN SEMBOLLERI EVRENDEN CIKAR.
# Madde 294 kucuk bacagin evreni daraltmasini SEMBOL_DUS (RASTGELE dusurme)
# ile fiyatladi. Ama bacak buyuklugu rastgele sembol dusurmez: borsanin
# gercek adim/asgari-notional tablosunda elenenler ISIMLI ve hepsi MAJOR
# (BTC, ETH, LINK, LTC, BCH, ETC, AAVE, AVAX, QNT). 9 majorun kaybi, 9
# rastgele altcoinin kaybiyla ayni sey DEGIL. Bos birakilirsa bu blok
# hic calismaz (parite birebir).
_HARIC=os.environ.get('SEMBOL_HARIC','').strip()
if _HARIC:
    _hs={x.strip().upper() for x in _HARIC.split(',') if x.strip()}
    _idx=[i for i,c_ in enumerate(C.columns) if str(c_).upper() in _hs]
    if _idx:
        U=U.copy(); U[:,_idx]=False
    print(f"# SEMBOL_HARIC: {len(_idx)}/{len(_hs)} sembol evrenden cikarildi",
          flush=True)

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
# MADDE 449: LONG 24 SA DUSUS STOP'U. Giris fiyatindan bagimsiz: coin son 24 sa'teki
# (6 bar once) kapanisindan SLL24 kadar duserse long bacak kapanir. 0 = kapali (parite).
SLL24=float(os.environ.get("SLL24","0"))
# SLL24_TAZE=n: seviye yalniz n barda bir (canli bot 8 sa = 2 bar) guncellenir; 1 = her bar (parite).
SLL24_TAZE=int(os.environ.get("SLL24_TAZE","1"))
# MADDE 454: pencere uzunlugu (bar) ve ikinci (kisa) kademe. SLL24_PEN=5 -> 24 sa (parite).
SLL24_PEN=int(os.environ.get("SLL24_PEN","5"))
SLLK=float(os.environ.get("SLLK","0")); SLLK_PEN=int(os.environ.get("SLLK_PEN","2"))
# MADDE 450: SHORT 24 SA YUKSELIS STOP'U (SLL24'un aynasi). 0 = kapali (parite).
SLS24=float(os.environ.get("SLS24","0"))
# MADDE 417: KAR HEDEFI SIFIRLAMA. Bacak girisinden aleyhe TP_SIFIRLA kadar gidince
# kar-al referansi o anki kapanisa tasinir (islem YOK, yalniz TP seviyesi). Cokus
# sonrasi toparlanmada eski dilimler de hasat eder (madde 414: H). 0 = kapali.
TP_SIFIRLA=float(os.environ.get("TP_SIFIRLA","0"))
# MADDE 419: AGIRLIK KAYMASI. Eski motor bacak agirligini tutus boyunca SABIT
# tutuyordu = her 4 sa bedava yeniden dengeleme (coken bacak kagit uzerinde
# tamamlaniyor). Gercek hesapta coin MIKTARI sabittir: agirlik fiyatla kayar.
# AGIRLIK_KAYMA=1 -> her bar sonunda poz = poz*(1+br)/(1+r). 0 = eski (parite).
AGIRLIK_KAYMA=int(os.environ.get("AGIRLIK_KAYMA","0"))
TP_SIF_TARAF=os.environ.get("TP_SIF_TARAF","iki")   # iki | long | short
UCELE=float(os.environ.get("UCELE","0"))   # 0=kapali. >=UCELE pump long adayi OLAMAZ
# MADDE 448: UCELE_TARAF=long -> yalniz pompa-long elemesi (cokmus coin short adayi KALIR). Bos/iki -> parite.
UCELE_TARAF=os.environ.get("UCELE_TARAF","iki").strip()
MOM_Q=float(os.environ.get('MOM_Q','0'))   # madde 383: 0 = kapali
_MOMV=None
if MOM_Q>0:
    import pickle as _pk5
    _MOMV=_pk5.load(open(os.environ.get('MOM_DOSYA','/tmp/mom5_panel.pkl'),'rb')).reindex(index=C.index,columns=C.columns).values
# MADDE 386: SPOT SARTI. Spot piyasasi olmayan perp'te arbitrajci funding'i
# bastiramaz; OOS'ta en yuksek funding short adaylarinin %72'si spotsuz ve
# kuyrugu iki kat derin. SPOT_SART='short' -> yalniz (onceki ayda) spotu olan
# coin SHORT adayi olur; 'iki' -> spotsuz coin hic aday olmaz. Bos -> parite.
_SPOT=os.environ.get('SPOT_SART','').strip()
_SPV=None
if _SPOT:
    import json as _js, pandas as _pds
    _J=_js.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'data_spot_varlik.json')))
    _ay=(_pds.DatetimeIndex(C.index).to_period('M')-1).astype(str)
    _SPV=np.column_stack([np.isin(_ay,_J.get(str(c_),{}).get('aylar',[])) for c_ in C.columns])
    print(f"# SPOT_SART={_SPOT}: spotlu pay {_SPV.mean():.2f}",flush=True)
# MADDE 423: LONG KALABALIK VETOSU. Tam donem katki atfi (gercekci model): long
# bacaklarin log(long/short hesap orani) ust beste birligi (>=0,64, oran ~1,9+)
# IKI DONEMDE DE zarar ediyor (22-24 −150 $/yil, 25-26 −127 $/yil, 2.000 $). Funding
# negatif olsa da hesaplar LONG kalabaliksa coin long adayi olmasin. 0/bos = kapali.
_LSL=os.environ.get('LS_L_MAKS','').strip()
_LSLV=None
if _LSL:
    import pickle as _pk6
    _LSLV=np.log(_pk6.load(open('/tmp/metrik_panel.pkl','rb'))['count_long_short_ratio']).reindex(index=C.index,columns=C.columns).values
    _LSL=float(_LSL)
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
# MADDE 221: OYNAKLIGA GORE OLCEKLENMIS KAR AL ESIGI.
# Madde 214: karin TAMAMI kar-al hasadindan. Madde 216: ulasma orani
# LONG %8,8 / SHORT %18,1. Madde 221 taramasi: SABIT esikle ulasma
# oynaklik besliklerine gore LONG %0,7 -> %22,6 (32 KAT esitsizlik).
# Sabit %40, dusuk oynaklikli coinde ulasilamaz bir hedef.
# TPKAT>0 ise esik = TPKAT x (5 gunluk gerceklesen oynaklik), taraf
# bazli TPKATL/TPKATS ile ayrilabilir. 0 = sabit esik (eski davranis).
TPKAT=float(os.environ.get("TPKAT","0"))
TPKATL=float(os.environ.get("TPKATL","-1"))
TPKATS=float(os.environ.get("TPKATS","-1"))
TPKAT_ALT=float(os.environ.get("TPKAT_ALT","0.05"))   # esik alt siniri
TPKAT_UST=float(os.environ.get("TPKAT_UST","1.50"))   # esik ust siniri
_ret5=np.vstack([np.full((1,C.shape[1]),np.nan),cv[1:]/cv[:-1]-1])
VOL5=pd.DataFrame(_ret5).rolling(30,min_periods=20).std().values*np.sqrt(30)
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
# MADDE 235: MERDIVEN. Alt rung MERD_ESIK'te pozisyonun MERD_PAY'ini
# kapatir; KALAN normal TP'ye (TPL/TPS) devam eder. Yani tek esigi
# DEGISTIRMEZ, altina bir basamak EKLER. 0 = kapali.
MERD_ESIK=float(os.environ.get("MERD_ESIK","0"))
MERD_PAY=float(os.environ.get("MERD_PAY","0.5"))
# MADDE 476: ERKEN (IKINCI) KADEME. Ana kademeden ONCE MERD0_ESIK (long) / MERDS0_ESIK (short) seviyesinde
# pozisyonun MERD0_PAY'i kapanir; kalan icin ana kademe (MERD_PAY) ve son TP aynen gecerli. 0 = kapali (parite).
MERD0_ESIK=float(os.environ.get("MERD0_ESIK","0")); MERDS0_ESIK=float(os.environ.get("MERDS0_ESIK","0"))
MERD0_PAY=float(os.environ.get("MERD0_PAY","0.333"))
# MADDE 466: SHORT tarafina ayri rung (MERDS_ESIK; bos -> MERD_ESIK, parite) ve rung sonrasi
# BASABAS stop'u (MERD_BE=1: rung dolduktan sonra fiyat girise donerse kalan kapanir).
MERDS_ESIK=float(os.environ.get("MERDS_ESIK", str(MERD_ESIK)))
MERD_BE=int(os.environ.get("MERD_BE","0"))
# MADDE 471: OYNAKLIGA OLCEKLI KADEME. MERD_KAT>0 -> long kademe = MERD_KAT x VOL5 (5 g oynaklik),
# MERDS_KAT>0 -> short kademe = MERDS_KAT x VOL5; [MERD_KAT_ALT, MERD_KAT_UST] ile kirpilir. 0 -> sabit (parite).
MERD_KAT=float(os.environ.get("MERD_KAT","0")); MERDS_KAT=float(os.environ.get("MERDS_KAT","0"))
MERD_KAT_ALT=float(os.environ.get("MERD_KAT_ALT","0.05")); MERD_KAT_UST=float(os.environ.get("MERD_KAT_UST","1.0"))
# MADDE 473: SERBEST KALAN AGIRLIGI YAYMA. MERD_YAY=1 -> rung dolunca bosalan agirlik ayni dilimde
# ayni taraftaki ACIK diger bacaklara mevcut agirlikla orantili eklenir (brut korunur, yeni coin yok).
# MERD_YAY=2 -> TP ile tam kapananlarin agirligi da ayni sekilde yayilir. 0 = kapali (parite).
MERD_YAY=int(os.environ.get("MERD_YAY","0"))
# MADDE 493: S_REB=<bar> -> SHORT tarafi tam dengeleme arasinda bu siklikla yeniden secilir (long'lar REB ile). 0 = parite.
S_REB=int(os.environ.get("S_REB","0"))
# MADDE 496: L_REB=<bar> -> LONG tarafi ara dengelemesi (aynalanmis S_REB). 0 = parite.
L_REB=int(os.environ.get("L_REB","0"))
# MADDE 499: S_REB_DUR=x -> evrenin (U) medyan 3 g getirisi |.| >= x iken short ara dengelemesi atlanir (cokus/sikisma
# aninda taze short acilmaz). S_REB_PEN bar (varsayilan 18 = 3 g). 0 -> kapali (parite).
S_REB_DUR=float(os.environ.get("S_REB_DUR","0")); S_REB_PEN=int(os.environ.get("S_REB_PEN","18")); _SRD=[0]
if S_REB_DUR>0:
    _rp=np.full_like(cv,np.nan); _rp[S_REB_PEN:]=cv[S_REB_PEN:]/np.where(cv[:-S_REB_PEN]>0,cv[:-S_REB_PEN],np.nan)-1
    _PIY=np.nanmedian(np.where(U,_rp,np.nan),axis=1)
else:
    _PIY=None
# MADDE 491: MERD_GERI=1 -> kademe sonrasi fiyat girise donunce satilan pay geri alinir, kademe yeniden kurulur. 0 = parite.
MERD_GERI=int(os.environ.get("MERD_GERI","0"))
MERD_GERI_TARAF=os.environ.get("MERD_GERI_TARAF","iki").strip()
# MADDE 483: kademe sonrasi kalan pay icin iz suren cikis (long KOSUCU, short KOSUCU_S; zirveden geri cekilme orani). 0 = sabit TP (parite).
KOSUCU=float(os.environ.get("KOSUCU","0")); KOSUCU_S=float(os.environ.get("KOSUCU_S","0"))
# MADDE 474: KADEME SONRASI DEVIR. 0 = parite (yeniden secilen coin dengelemede tam boya ve yeni girise doner).
# 1 = tazelenmez (kalan pay ayni giris/TP ile surer, bosalan nakit) · 2 = kademesi dolan coin o dengelemede aday degil.
MERD_DEVIR=int(os.environ.get("MERD_DEVIR","0"))
_YAYS=[0,0.0]
def _yay(poz,bos,uygun,eq,giris=None,f=None):
    for sg in (1,-1):
        b=float(np.abs(bos[np.sign(bos)==sg]).sum())
        if b<=0: continue
        m=uygun&(np.sign(poz)==sg)
        t=float(np.abs(poz[m]).sum())
        if t<=0: continue
        if giris is not None:   # canli gibi: agirlikli ortalama giris (TP yeni giristen olculur)
            ok=m&np.isfinite(f)&(f>0)&np.isfinite(giris)
            giris[ok]=(giris[ok]+f[ok]*b/t)/(1+b/t)
        poz[m]=poz[m]*(1+b/t); eq[-1]*=1-b*KOM; _YAYS[0]+=1; _YAYS[1]+=b
AYNI=int(os.environ.get("AYNI","0"))            # kar al sonrasi AYNI yonde yeniden gir
say_r=[0]
REZ_RAST=int(os.environ.get("REZ_RAST","0"))
TOL=float(os.environ.get("TOL","0"))   # hedefin bu oraninden az sapan bacaga dokunma
KAP=float(os.environ.get("KAP","0"))   # coin basina EK agirlik ust siniri
_rz=np.random.default_rng(int(os.environ.get("TOHUM","1")))   # sinyalden kac bar sonra girilsin (1 bar = 4 saat)   # dilim sayisi: tepki suresi = 120sa / FAZ
say_t=[0,0]

say_d=[0]
# MADDE 229: BOSLUK OLCUMU. TP dolan koltuk, o dilimin bir sonraki
# dengelemesine kadar bos kalir. BOSLUK=1 ise her barda FIILEN acik brut
# ile HEDEF brut toplanir; oran, bu eksenin butcesidir. Varsayilan yol
# hic degismez (sadece iki toplama eklenir).
BOSLUK=int(os.environ.get("BOSLUK","0"))
# MADDE 230: TARAF BAZLI BACAK SAYISI. Olculdu: LONG tarafta funding
# 1. bacaktan 5. bacaga 16 KAT soniyor (medyan -%0,733 -> -%0,045/gun),
# SHORT tarafta ise 5 bacagin hepsi ~%0,030/gun yani TABAN oranda - yani
# short tarafta toplanacak uc YOK. Bu asimetri hic denenmedi: bacak
# sayisi iki tarafta da ayni (n) idi. 0 = n kullan (eski davranis).
N_L=int(os.environ.get("N_L","0"))
N_S=int(os.environ.get("N_S","0"))
bos=[0.0,0.0,0]   # [fiili brut toplami, hedef brut toplami, bar sayisi]
# MADDE 232: TAHSIL EDILEN FUNDING'I SERMAYE ORANI olarak olc. Rapor
# bunu "BEKLENEN_GUNLUK x 0.94" diye TURETIYORDU; 0.94 madde 136'nin
# "funding gelirinin %94'u LONG bacaktan" ifadesinden gelen bir ETIKET
# HATASIydi (gelirin %94'u funding'den DEGIL). Artik olculuyor.
# MADDE 236: BACAK BAZINDA KATKI DEFTERI. Her bacagin tuttugu sure
# boyunca sermayeye katkisi + GIRISTEKI nitelikleri. Dususlerin NEREDEN
# geldigini bulmak icin; toplam istatistik bunu gosteremez.
KATKI=int(os.environ.get("KATKI","0"))
# MADDE 250: ORTALAMA DUSURME (kullanicinin onerisi). Bir bacak aleyhte
# EK_ESIK kadar giderse ozgun bacak agirliginin EK_PAY kati EKLENIR ve
# giris AGIRLIKLI ORTALAMAYA cekilir; TP artik yeni ortalamadan olculur,
# yani kar-al seviyesi fiyata YAKINLASIR. EK_SAYI = pozisyon basina en
# fazla kac ekleme. EK_ESIK=0 -> bayrak KAPALI (parite).
# NEDENSELLIK: ekleme bar i+1'in KAPANISINDA yapilir - motorun
# AYNI/TERS/DOLDUR bloklariyla ayni konvansiyon, look-ahead yok.
# MADDE 251: RISK PARITESI (oynakliga TERS agirlik). Madde 116'da
# olculdu, "panele bagli gurultu" diye VARSAYILAN YAPILMADI - ama o olcum
# madde 182'nin 41 puanlik sizintisi ve madde 209'un sinyal hatasi
# DUZELTILMEDEN ONCE, Sharpe 0,86-1,50 bandindaki bir taban uzerinde
# yapildi. Bugunun yuzeyinde (Sharpe 2,94) HIC olculmedi.
# AGIRLIK=vol -> bacak agirligi 1/oynaklik ile oranli; TARAF NOTRLUGU ve
# TOPLAM BRUT korunur (her taraf kendi icinde normalize edilir).
# AGIRLIK=esit (varsayilan) -> eski davranis, PARITE.
AGIRLIK=os.environ.get("AGIRLIK","esit")
KAL_EGIM=float(os.environ.get("KAL_EGIM","0"))   # madde 375
AG_TABAN=float(os.environ.get("AG_TABAN","0"))   # 1/(vol+AG_TABAN): 0 = saf 1/vol
AG_KIRP=float(os.environ.get("AG_KIRP","0"))
# MADDE 282: AGIRLIK="buyukluk" icin |S|^SK_GAMMA. 0 = esit agirlik
# (kontrolun birebir aynisi -> parite kolu).
SK_GAMMA=float(os.environ.get("SK_GAMMA","0"))     # agirlik/ortalama ust siniri (0=yok)
EK_ESIK=float(os.environ.get("EK_ESIK","0"))
EK_PAY=float(os.environ.get("EK_PAY","0.5"))
EK_SAYI=int(os.environ.get("EK_SAYI","1"))
EK_REZ=int(os.environ.get("EK_REZ","0"))   # 1 = eklemeyi brut yerine REZERVDEN finanse et
_EKS=[0,0.0]   # [ekleme sayisi, eklenen toplam notional]

katki_defter=[]
# MADDE 239: PRIM-OLCEKLI BRUT. Kesitsel funding dagilimi (p90-p10)
# kitabin ILERIYE DONUK getirisini tek yonlu siraliyor (her iki rejimde
# de). Burada o gozlenebilir seviyeye gore brut maruziyet olceklenir.
# NEDENSELLIK: olcu i. bara kadarki 180 barin (30 gun) ortalamasi, ve
# normalizasyon GENISLEYEN medyana gore (tam ornek kuantili KULLANILMAZ,
# o look-ahead olur). 1 bar gecikme ayrica uygulanir.
BRUT_PRIM=float(os.environ.get("BRUT_PRIM","0"))   # 0=kapali; >0 = duyarlilik ustu
BRUT_ALT=float(os.environ.get("BRUT_ALT","0.5"))   # carpanin tabani
BRUT_UST=float(os.environ.get("BRUT_UST","1.5"))   # carpanin tavani
BRUT_REF=int(os.environ.get("BRUT_REF","180"))     # gun: YEREL referans penceresi
BRUT_OLC=int(os.environ.get("BRUT_OLC","30"))      # gun: prim olcum penceresi
_PCARP=None
if BRUT_PRIM>0:
    _Sd=pd.DataFrame(S).where(pd.DataFrame(U))
    _pr=(_Sd.quantile(0.9,axis=1)-_Sd.quantile(0.1,axis=1))
    _pr=_pr.rolling(BRUT_OLC*6,min_periods=BRUT_OLC*4).mean()
    # YEREL referans (kayan medyan): primin TRENDINI degil, kendi son
    # normundan SAPMASINI olcer. Genisleyen medyan kullanilirsa yapi
    # "2025 sonrasi kaldirac arttir"a doner ve bu TEK bir gerceklesmedir.
    _ref=_pr.rolling(BRUT_REF*6,min_periods=BRUT_REF*3).median()
    _m=(_pr/_ref)**BRUT_PRIM
    _PCARP=_m.clip(BRUT_ALT,BRUT_UST).shift(1).fillna(1.0).values
    # PLASEBO: ayni carpan DAGILIMI, yanlis zamanlarda. 1=zamanda ters
    # cevir, 2=karistir. Yapi gercekse ikisi de kazanci yok etmeli.
    _BPL=int(os.environ.get("BRUT_PLASEBO","0"))
    if _BPL==1:
        _PCARP=_PCARP[::-1].copy()
    elif _BPL==2:
        # .values salt-okunur donebilir: KOPYALA (yoksa shuffle patlar ve
        # kabuk eski /tmp/g19E_*.pkl'i yeni sonuc sanip kopyalar)
        _PCARP=_PCARP.copy()
        np.random.default_rng(int(os.environ.get("BRUT_TOHUM","7"))).shuffle(_PCARP)
    print(f"# BRUT_PRIM={BRUT_PRIM} alt={BRUT_ALT} ust={BRUT_UST} "
          f"ort carpan={np.nanmean(_PCARP[1200:]):.3f}",flush=True)
_BRT=[0.0,0]   # [brut carpan toplami, sayi] - fiili ortalama kaldirac icin
FON_OLC=int(os.environ.get("FON_OLC","0"))
fon=[0.0,0]   # [toplam funding (sermaye orani), bar sayisi]
fon_seri=[]   # (zaman, bar basina funding) - rejim ayrimi icin
AY={'Lf':0.0,'Lp':0.0,'Sf':0.0,'Sp':0.0,'Ltp':0.0,'Stp':0.0,'kom':0.0}
GUN={}
# MADDE 414: GUNLUK_KATKI=<yol> -> (gun, sembol) basina fiyat/funding katkisi ve
# pozisyon yonu, butun fazlarin TOPLAMI (sonra faz sayisina bolunur). Bos -> kapali.
_GK_YOL=os.environ.get('GUNLUK_KATKI','').strip()
_GK={}
_GK_BAS=pd.Timestamp(os.environ.get('GK_BAS','2026-01-01'))
YIL={}   # yil -> [Lf,Lp,Ltp,Sf,Sp,Stp]
# MADDE 440: POZ_CIKTI=<yol> -> her barda (koordinatore bildirilen, o barin
# rebalance'indan ONCEKI) pozisyon agirliklarinin dilimler arasi ORTALAMASI.
# Saatlik kitap simulasyonu icin. Bos -> kapali (parite).
_PZ_YOL=os.environ.get('POZ_CIKTI','').strip()
# MADDE 479: ADAY_CIKTI=<yol> -> her dengelemede long/short ADAY HAVUZU (olcutten once) kaydedilir. Bos -> kapali.
_ADY_YOL=os.environ.get('ADAY_CIKTI','').strip(); _ADY=[]
_PZ=[None]
def bt2(bas,n,olcut=None,tp=None):
    # MADDE 415: bt2 artik _bt2g uretecini koordinasyonsuz surer (parite).
    _g=_bt2g(bas,n,olcut,tp)
    try:
        _m=next(_g)
        while True:
            if _PZ_YOL:
                if _PZ[0] is None:
                    _PZ[0]=np.zeros((len(C),C.shape[1]),np.float32)
                _PZ[0][_m[0]]+=_m[1]
            _m=_g.send(None)
    except StopIteration as _e:
        return _e.value

def _bt2g(bas,n,olcut=None,tp=None):
    tp=TPX if tp is None else tp
    hedef_brut=[0.0]; _acik={}
    nk=C.shape[1]; poz=np.zeros(nk); giris=np.full(nk,np.nan); zirve=np.full(nk,np.nan); tp_yapildi=np.zeros(nk,bool); eq=[1.0]; bek=None; _yas=np.zeros(nk,int)
    merd_yapildi=np.zeros(nk,bool); merd0_yapildi=np.zeros(nk,bool); _kisb=[False]
    ek_say=np.zeros(nk,int); ilk_w=np.zeros(nk)
    for i in range(bas,len(C)-1):
        # MADDE 415: her bar koordinatore (i, poz, yeni hedef ya da None) bildirilir;
        # koordinator hedefi degistirebilir (dilimler arasi ortak coin tavani).
        _ytek=bek[1] if (bek is not None and bek[0]==i) else None
        _cvp=yield (i, poz, _ytek)
        if _ytek is not None and _cvp is not None:
            bek=(bek[0], _cvp)
        if bek is not None and bek[0]==i:
            y=bek[1]
            if TOL>0:
                bacak=0.5/max(1,int(np.count_nonzero(y)/2))
                kucuk=np.abs(y-poz)<TOL*bacak
                y=np.where(kucuk,poz,y)
            _dv=np.zeros(nk,bool)
            if _kisb[0]=='L':
                _dv=poz<0; y=np.where(_dv,poz,y)      # short'lar dokunulmadan surer
            elif _kisb[0]:
                _dv=poz>0; y=np.where(_dv,poz,y)      # long'lar dokunulmadan surer (giris/kademe durumu korunur)
            if MERD_DEVIR==1:
                # MADDE 474: kademesi dolmus ve yeniden secilen coin TAZELENMEZ: kalan ⅓ ayni giris/TP ile surer
                _dv=merd_yapildi&(poz!=0)&(np.sign(y)==np.sign(poz))
                y=np.where(_dv,poz,y)
            eq[-1]*=1-np.abs(y-poz).sum()*KOM
            _gs,_zs=giris.copy(),zirve.copy()
            poz=y; giris=np.where(y!=0,cv[i],np.nan); zirve=np.where(y!=0,cv[i],np.nan); tp_yapildi=np.where(y!=0,False,tp_yapildi); bek=None
            giris=np.where(_dv,_gs,giris); zirve=np.where(_dv,_zs,zirve)
            merd_yapildi=np.where((y!=0)&~_dv,False,merd_yapildi)
            merd0_yapildi=np.where((y!=0)&~_dv,False,merd0_yapildi)
            ek_say=np.where(y!=0,0,ek_say); ilk_w=np.where(y!=0,np.abs(y),ilk_w)
            if BOSLUK: hedef_brut[0]=float(np.abs(poz).sum())
            if KATKI:
                # MADDE 236: yeni kohort kurulmadan ONCE acik kalanlari
                # deftere yaz - yoksa defter yalnizca TP ile kapananlari
                # (yani KAZANANLARI) tasir ve dusus analizi anlamsiz olur.
                for _k2, _d2 in list(_acik.items()):
                    _d2['kapanis'] = 'DEVIR'
                    katki_defter.append(_d2)
                _acik = {}
                for _k in np.flatnonzero(poz!=0):
                    _acik[_k]=dict(t=C.index[i], sem=C.columns[_k],
                                   yon=int(np.sign(poz[_k])), w=float(poz[_k]),
                                   sin=float(S[i,_k]) if np.isfinite(S[i,_k]) else np.nan,
                                   vol=float(VOL[i,_k]) if np.isfinite(VOL[i,_k]) else np.nan,
                                   uc=float(_UART[i,_k]) if np.isfinite(_UART[i,_k]) else np.nan,
                                   pnl=0.0, fon=0.0, fiy=0.0, bar=0)
        _kis=(S_REB>0 and (i-bas)%S_REB==0 and (i-bas)%REB!=0)
        if _kis and S_REB_DUR>0 and np.isfinite(_PIY[i]) and abs(_PIY[i])>=S_REB_DUR:
            _kis=False; _SRD[0]+=1        # MADDE 499: piyasa sert hareketteyse short yenileme DURUR
        _kisL=(L_REB>0 and (i-bas)%L_REB==0 and (i-bas)%REB!=0)
        if _kisL and _kis: _kisL=False      # ikisi ayni barda -> once short (basit kural)
        if (i-bas)%REB==0 or _kis or _kisL:
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
                if UCELE_TARAF=="long":
                    g=g&~(_pump&(_sr<_med))
                else:
                    g=g&~(_pump&(_sr<_med))&~(_dump&(_sr>_med))
            if _MOMV is not None:
                # MADDE 383: COK UFUKLU MOMENTUM VETOSU (madde 381: kriptoda
                # kesitsel olarak yukselen yukselmeye devam ediyor, OOS).
                # Momentumun ust MOM_Q diliminde olan coin SHORT adayi,
                # alt diliminde olan LONG adayi olmasin. Eleme siralamadan once.
                _m=_MOMV[i]
                _yuk=np.isfinite(_m)&(_m>=1-MOM_Q); _dus=np.isfinite(_m)&(_m<=MOM_Q)
                _sr2=np.where(g,S[i],np.nan)
                _md2=np.nanmedian(_sr2) if np.isfinite(_sr2).any() else 0.0
                g=g&~(_yuk&(_sr2>_md2))&~(_dus&(_sr2<_md2))
            if _LSLV is not None:
                _lv=_LSLV[i]
                _sr4=np.where(g,S[i],np.nan)
                _md4=np.nanmedian(_sr4) if np.isfinite(_sr4).any() else 0.0
                g=g&~(np.isfinite(_lv)&(_lv>_LSL)&(_sr4<_md4))
            if _SPV is not None:
                _sp=_SPV[i]
                if _SPOT=='iki':
                    g=g&_sp
                else:
                    _sr3=np.where(g,S[i],np.nan)
                    _md3=np.nanmedian(_sr3) if np.isfinite(_sr3).any() else 0.0
                    g=g&~(~_sp&(_sr3>_md3))
            if MERD_DEVIR==2:
                # MADDE 474: kademesi dolmus coin bu dengelemede aday OLMAZ (pompa sonrasi yeniden alma yok)
                g=g&~(merd_yapildi&(poz!=0))
            ix=np.flatnonzero(g)
            _nl=N_L if N_L>0 else n; _ns=N_S if N_S>0 else n
            # her iki taraf da ayni havuzdan beslenir; havuz en buyuk
            # taraf icin yeterli olmali
            nn=min(n,len(ix)//2); _nl=min(_nl,len(ix)//2); _ns=min(_ns,len(ix)//2)
            mm=min(int(HAVUZ*max(_nl,_ns)),len(ix)//2)
            # MADDE 364: taraf basina ayri havuz (HAVUZ_L/HAVUZ_S). Bos -> HAVUZ (parite).
            _mml=min(int(_HL*_nl),len(ix)//2) if _HL>0 else mm
            _mms=min(int(_HS*_ns),len(ix)//2) if _HS>0 else mm
            if nn>=min(8,n):
                sc=rk(S[i][ix]); a=pd.Series(A[i][ix])
                if AKW>0 and a.notna().sum()>=0.5*len(ix): sc=(1-AKW)*sc+AKW*(-a).rank(pct=True).fillna(0.5).values
                o=np.argsort(sc)
                if SS is not None:
                    _ss=pd.Series(SS[i][ix]).rank(pct=True).fillna(0.5).values
                    _lav=set(int(x) for x in ix[o[:max(_mml,_nl)]])
                    _ss=np.where(np.array([int(x) in _lav for x in ix]),-1.0,_ss)   # long havuzu short olamaz
                    o_s=np.argsort(_ss)
                else:
                    o_s=o
                if olcut is None:
                    lo=ix[o[:_nl]]; sh=ix[o_s[-_ns:]]; lo_s=ix[o[:mm]]; sh_s=ix[o_s[::-1][:mm]]
                else:
                    la=ix[o[:_mml]]; sa=ix[o_s[-_mms:]]
                    if _ADY_YOL: _ADY.append((i, la.copy(), sa.copy()))
                    def sec(ad,taraf,sira_skor):
                        p=np.asarray(olcut(i,ad,taraf),float)
                        # olcut yoksa: skor sirasi (en uc) ile doldur
                        p=np.where(np.isfinite(p),pd.Series(p).rank(pct=True).values,np.nan)
                        yedek=sira_skor
                        p=np.where(np.isfinite(p),p,yedek)
                        return ad[np.argsort(-p)]
                    uc_l=np.linspace(1,0,_mml); uc_s=np.linspace(0,1,_mms)
                    lo_s=sec(la,+1,uc_l); sh_s=sec(sa,-1,uc_s); lo=lo_s[:_nl]; sh=sh_s[:_ns]
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
                y=np.zeros(nk)
                if AGIRLIK=="buyukluk":
                    # MADDE 282: kitap bugune kadar sinyalin yalniz SIRALAMASINI
                    # kullandi (sc=rk(...)); BUYUKLUGU atildi. Burada taraf ici
                    # agirlik |S|^SK_GAMMA ile olceklenyor. Taraf basina
                    # normalize edildigi icin DOLAR NOTRLUGU ve BRUT aynen
                    # korunur (madde 251'in yontemi). SK_GAMMA=0 -> esit agirlik,
                    # yani kontrolun BIREBIR aynisi (parite kolu).
                    def _agb(idx):
                        s=np.abs(S[i][idx].astype(float))
                        iy=np.where(np.isfinite(s)&(s>0),s**SK_GAMMA,np.nan)
                        if not np.isfinite(iy).any(): return np.full(len(idx),1.0/len(idx))
                        iy=np.where(np.isfinite(iy),iy,np.nanmedian(iy))
                        if AG_KIRP>0:
                            iy=np.minimum(iy,AG_KIRP*iy.mean())
                        return iy/iy.sum()
                    y[lo]=taban*_agb(lo); y[sh]=-taban*_agb(sh)
                elif AGIRLIK in ("vol","volduz"):
                    # MADDE 251: her bacak esit RISK tasisin, esit PARA degil.
                    # Taraf basina normalize -> taraf notrlugu ve brut AYNEN korunur.
                    def _ag(idx):
                        v=VOL[i][idx].astype(float)
                        # MADDE 257: volduz = oynaklikla ORANTILI (vol'un AYNASI).
                        # Madde 142.2 bunu olcmustu ama madde 182'nin 41 puanlik
                        # sizintisi duzeltilmeden ONCEKI yuzeyde.
                        if AGIRLIK=="volduz":
                            iy=np.where(np.isfinite(v)&(v>0),v+AG_TABAN,np.nan)
                        else:
                            iy=1.0/np.where(np.isfinite(v)&(v>0),v+AG_TABAN,np.nan)
                        # olcusu olmayan bacak: o tarafin MEDYAN agirligi
                        if not np.isfinite(iy).any(): return np.full(len(idx),1.0/len(idx))
                        iy=np.where(np.isfinite(iy),iy,np.nanmedian(iy))
                        if AG_KIRP>0:
                            iy=np.minimum(iy,AG_KIRP*iy.mean())
                        return iy/iy.sum()
                    y[lo]=taban*_ag(lo); y[sh]=-taban*_ag(sh)
                elif AGIRLIK=="kalabalik":
                    # MADDE 375: secilen bacaklar EN KALABALIKTAN baslayarak
                    # sirali gelir (sec(): p azalan). Agirlik sira konumuyla
                    # egilir: w_j ~ 1 + KAL_EGIM*(n-1-2j)/(n-1), taraf basina
                    # normalize -> brut ve dolar notrlugu korunur.
                    # KAL_EGIM=0 -> esit agirlik (parite).
                    def _agk(idx):
                        m=len(idx)
                        if m<2: return np.full(m,1.0/max(m,1))
                        j=np.arange(m); iy=1.0+KAL_EGIM*(m-1-2*j)/(m-1)
                        return iy/iy.sum()
                    y[lo]=taban*_agk(lo); y[sh]=-taban*_agk(sh)
                else:
                    y[lo]=taban/len(lo); y[sh]=-taban/len(sh)
                if REZERV>0:
                    ul=([int(_rz.choice(lo))] if _rz.random()<0.4 else []) if REZ_RAST else [k for k in lo if np.isfinite(S[i,k]) and S[i,k]<=-REZ_ESIK]
                    if ul:
                        pay=(REZERV/2)/len(ul)
                        if KAP>0: pay=min(pay,KAP)
                        kullanilan=pay*len(ul)
                        for k in ul: y[k]+=pay
                        for k in sh: y[k]-=kullanilan/len(sh)   # notrluk korunur
                        say_r[0]+=1
                if _PCARP is not None:
                    _mi=float(_PCARP[i]) if np.isfinite(_PCARP[i]) else 1.0
                    y=y*_mi; _BRT[0]+=_mi; _BRT[1]+=1
                if GENCV is not None:
                    _gm=GENCV[i]&(y!=0)
                    if _gm.any(): y=np.where(_gm,y*GENC_PAY,y)
                if _kis: y=np.where(y>0,0.0,y); _kisb[0]=True     # MADDE 493: ara dengeleme yalniz SHORT
                elif _kisL: y=np.where(y<0,0.0,y); _kisb[0]='L'   # MADDE 496: ara dengeleme yalniz LONG
                else: _kisb[0]=False
                bek=(i+GEC,y); yedek_l=list(lo_s[_nl:]); yedek_s=list(sh_s[_ns:]); w_=0.5/max(_nl,_ns)
        gec=np.isfinite(cv[i])&np.isfinite(cv[i+1])
        br=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0); br=np.nan_to_num(br)
        cik=np.zeros(nk,bool); yaridan=np.zeros(nk,bool)
        merd=np.zeros(nk,bool); mpay=np.zeros(nk); _gx=np.zeros(nk); _gw=np.zeros(nk)
        if TEK_GIRIS:
            _REG[bas]=(poz,giris)
            _Pw=np.zeros(nk); _Pe=np.zeros(nk)
            for _pq,_gq in _REG.values():
                _ok=np.isfinite(_gq)&(_pq!=0)
                _Pw[_ok]+=_pq[_ok]; _Pe[_ok]+=_pq[_ok]*_gq[_ok]
        if tp>0 or TAKIP_BAS>0:
            for k in np.flatnonzero(poz!=0):
                e=giris[k]
                if TEK_GIRIS and _Pw[k]*poz[k]>0:
                    # MADDE 481: canli gibi TEK HESAP - TP/kademe/stop referansi coinin TUM dilimlerdeki
                    # agirlikli ortalama girisi (Binance entryPrice). Ters yonlu dilim varsa (nadir) kendi girisi.
                    e=_Pe[k]/_Pw[k]
                if not (np.isfinite(e) and np.isfinite(cv[i,k]) and cv[i,k]>0 and np.isfinite(HV[i+1,k]) and np.isfinite(LV[i+1,k])): continue
                uzun=poz[k]>0
                if TP_SIFIRLA>0 and (TP_SIF_TARAF=='iki' or (TP_SIF_TARAF=='long')==uzun):
                    if (uzun and cv[i,k]<=e*(1-TP_SIFIRLA)) or ((not uzun) and cv[i,k]>=e*(1+TP_SIFIRLA)):
                        giris[k]=cv[i,k]; e=cv[i,k]
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
                _i24 = i - (i % SLL24_TAZE) if SLL24_TAZE > 1 else i
                _s24 = -1.0
                if SLL24 > 0 and uzun and _i24 >= SLL24_PEN and np.isfinite(cv[_i24-SLL24_PEN,k]) and cv[_i24-SLL24_PEN,k] > 0:
                    _s24 = cv[_i24-SLL24_PEN,k]*(1-SLL24)
                if SLLK > 0 and uzun and _i24 >= SLLK_PEN and np.isfinite(cv[_i24-SLLK_PEN,k]) and cv[_i24-SLLK_PEN,k] > 0:
                    _s24 = max(_s24, cv[_i24-SLLK_PEN,k]*(1-SLLK))
                if _s24 > 0:
                    if LV[i+1,k] <= _s24:
                        _op = OV[i+1,k]
                        _ff = min(_s24,_op) if np.isfinite(_op) else _s24
                        br[k] = _ff/cv[i,k]-1; cik[k]=True; say_t[1]+=1
                        continue
                if SLS24 > 0 and (not uzun) and i >= 5 and np.isfinite(cv[i-5,k]) and cv[i-5,k] > 0:
                    _s24s = cv[i-5,k]*(1+SLS24)
                    if HV[i+1,k] >= _s24s:
                        _op = OV[i+1,k]
                        _ff = max(_s24s,_op) if np.isfinite(_op) else _s24s
                        br[k] = _ff/cv[i,k]-1; cik[k]=True; say_t[1]+=1
                        continue
                if MERD_GERI and merd_yapildi[k] and not merd0_yapildi[k] and (MERD_GERI_TARAF=='iki' or (MERD_GERI_TARAF=='long')==uzun):
                    # MADDE 491: KADEME GERI ALIMI. Kademe sattiktan sonra fiyat girise donerse satilan pay girisle
                    # GERI alinir (bekleyen limit; acilis gecmisse acilistan) ve kademe yeniden kurulur -> pompa-dump
                    # salinimini tekrar tekrar hasat eder. Funding de tam boyda toplanmaya devam eder.
                    _vg = (LV[i+1,k] <= e) if uzun else (HV[i+1,k] >= e)
                    if _vg:
                        _op = OV[i+1,k]
                        _fg = (min(e,_op) if uzun else max(e,_op)) if np.isfinite(_op) else e
                        _dw = abs(poz[k])*MERD_PAY/(1-MERD_PAY)
                        _gx[k] = np.sign(poz[k])*_dw*(cv[i+1,k]/_fg-1); _gw[k] = np.sign(poz[k])*_dw
                        merd_yapildi[k] = False; say_t[1]+=1
                        continue
                if MERD_BE and merd_yapildi[k]:
                    _vbe = (LV[i+1,k] <= e) if uzun else (HV[i+1,k] >= e)
                    if _vbe:
                        _op = OV[i+1,k]
                        _ff = (min(e,_op) if uzun else max(e,_op)) if np.isfinite(_op) else e
                        br[k] = _ff/cv[i,k]-1; cik[k]=True; say_t[1]+=1
                        continue
                if KOSUCU>0 and uzun and merd_yapildi[k]:
                    # MADDE 483: KOSUCU. Kademe dolduktan sonra kalan pay sabit TP yerine zirveden KOSUCU kadar
                    # geri cekilince kapanir (onceki barlarin zirvesi -> bar ici bakis yok; acilis gecmisse acilistan).
                    _pz=zirve[k] if np.isfinite(zirve[k]) else e
                    _st=_pz*(1-KOSUCU)
                    if LV[i+1,k]<=_st:
                        _op=OV[i+1,k]; _ff=min(_st,_op) if np.isfinite(_op) else _st
                        br[k]=_ff/cv[i,k]-1; cik[k]=True; say_t[1]+=1
                        continue
                    zirve[k]=max(_pz,HV[i+1,k])
                    continue
                if KOSUCU_S>0 and (not uzun) and merd_yapildi[k]:
                    _pz=zirve[k] if np.isfinite(zirve[k]) else e
                    _st=_pz*(1+KOSUCU_S)
                    if HV[i+1,k]>=_st:
                        _op=OV[i+1,k]; _ff=max(_st,_op) if np.isfinite(_op) else _st
                        br[k]=_ff/cv[i,k]-1; cik[k]=True; say_t[1]+=1
                        continue
                    zirve[k]=min(_pz,LV[i+1,k])
                    continue
                _tp = (TPL if TPL>=0 else tp) if uzun else (TPS if TPS>=0 else tp)
                # MADDE 221: oynakliga gore olcekle (nedensel: VOL5[i])
                _kat = (TPKATL if uzun and TPKATL>=0 else
                        TPKATS if (not uzun) and TPKATS>=0 else TPKAT)
                if _kat > 0:
                    _v = VOL5[i,k]
                    if np.isfinite(_v) and _v > 0:
                        _tp = min(TPKAT_UST, max(TPKAT_ALT, _kat*_v))
                sev=e*(1+_tp) if uzun else e*(1-_tp)
                if _tp>0 and ((uzun and HV[i+1,k]>=sev) or ((not uzun) and LV[i+1,k]<=sev)):
                    if YARIM and tp_yapildi[k]:
                        continue                  # yarisi zaten alindi, kalan normal getiri alir
                    br[k]=_dol(sev,uzun,i,k)/cv[i,k]-1; say_t[1]+=1
                    if YARIM: yaridan[k]=True; tp_yapildi[k]=True
                    else: cik[k]=True
                    continue
                # MADDE 235: ALT RUNG. Ust TP vurmadiysa bakilir (ayni
                # barda ust rung varsa o kazanir - daha iyi fiyat).
                _me = MERD_ESIK if uzun else MERDS_ESIK
                _mk = MERD_KAT if uzun else MERDS_KAT
                if _mk > 0 and np.isfinite(VOL5[i,k]) and VOL5[i,k] > 0:
                    _me = min(MERD_KAT_UST, max(MERD_KAT_ALT, _mk*VOL5[i,k]))
                    _tpx = (TPL if TPL>=0 else tp) if uzun else (TPS if TPS>=0 else tp)
                    if _tpx > 0: _me = min(_me, 0.95*_tpx)
                _m0 = MERD0_ESIK if uzun else MERDS0_ESIK
                _h0 = False
                if _m0>0 and not merd0_yapildi[k]:
                    _s0=e*(1+_m0) if uzun else e*(1-_m0)
                    _h0 = (uzun and HV[i+1,k]>=_s0) or ((not uzun) and LV[i+1,k]<=_s0)
                _hm = False
                if _me>0 and not merd_yapildi[k]:
                    _sm=e*(1+_me) if uzun else e*(1-_me)
                    _hm = (uzun and HV[i+1,k]>=_sm) or ((not uzun) and LV[i+1,k]<=_sm)
                if _h0 and _hm:      # ayni barda iki kademe: once erken, sonra ana (kalanin MERD_PAY'i)
                    f0=MERD0_PAY; f1=(1-MERD0_PAY)*MERD_PAY
                    br[k]=(f0*(_dol(_s0,uzun,i,k)/cv[i,k]-1)+f1*(_dol(_sm,uzun,i,k)/cv[i,k]-1))/(f0+f1)
                    mpay[k]=f0+f1; merd[k]=True; merd0_yapildi[k]=True; merd_yapildi[k]=True; say_t[1]+=1
                elif _hm:
                    br[k]=_dol(_sm,uzun,i,k)/cv[i,k]-1
                    if KOSUCU>0 or KOSUCU_S>0: zirve[k]=_sm
                    mpay[k]=MERD_PAY; merd[k]=True; merd_yapildi[k]=True; say_t[1]+=1
                    if _m0>0: merd0_yapildi[k]=True   # erken kademe ana kademeden sonra anlamsiz
                elif _h0:
                    br[k]=_dol(_s0,uzun,i,k)/cv[i,k]-1
                    mpay[k]=MERD0_PAY; merd[k]=True; merd0_yapildi[k]=True; say_t[1]+=1
        # MADDE 215: taraf bazli maks tutma suresi. TP/stop kontrolunden
        # SONRA bakilir: ayni barda TP varsa TP kazanir (daha iyi fiyat).
        if YAS_L or YAS_S:
            for _k in np.flatnonzero((poz!=0)&~cik):
                _sn = YAS_L if poz[_k]>0 else YAS_S
                if _sn and _yas[_k]+1 >= _sn:
                    cik[_k]=True                      # bar kapanisindan cik
                    say_y[0 if poz[_k]>0 else 1]+=1
        if BOSLUK:
            bos[0]+=float(np.abs(poz).sum()); bos[1]+=float(hedef_brut[0]); bos[2]+=1
        fu=np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])); pr=poz*br
        if KATKI:
            for _k, _d in list(_acik.items()):
                if poz[_k]==0: continue
                _d['fon']+=float(np.nan_to_num(fu[_k])); _d['fiy']+=float(np.nan_to_num(pr[_k]))
                _d['pnl']+=float(np.nan_to_num(fu[_k])+np.nan_to_num(pr[_k])); _d['bar']+=1
        if FON_OLC:
            _f=float(np.nansum(fu)); fon[0]+=_f; fon[1]+=1
            fon_seri.append((C.index[i],_f))
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
        if merd.any():
            kapanis=cv[i+1]/np.where(cv[i]==0,np.nan,cv[i])-1
            br=np.where(merd,mpay*br+(1-mpay)*np.nan_to_num(kapanis),br)
        if yaridan.any():
            # yarisi TP seviyesinden cikar, yarisi barin kapanisiyla devam eder
            kapanis=np.where(gec,(cv[i+1]-cv[i])/np.where(cv[i]==0,np.nan,cv[i]),0.0)
            br=np.where(yaridan,0.5*br+0.5*np.nan_to_num(kapanis),br)
        r=np.nansum(poz*br)+np.nansum(np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1])))
        if MERD_GERI and _gw.any():
            r+=float(np.nansum(_gx)-np.nansum(_gw*np.nan_to_num(fv[i+1])))
        if _GK_YOL and C.index[i+1]>=_GK_BAS:
            _gd=C.index[i+1].normalize()
            _fu=np.where(cik,0.0,-poz*np.nan_to_num(fv[i+1]))
            for _k in np.flatnonzero(poz!=0):
                _e=_GK.setdefault((_gd,_k),[0.0,0.0,0.0,0])
                _e[0]+=float(np.nan_to_num(poz[_k]*br[_k])); _e[1]+=float(_fu[_k]); _e[2]+=float(poz[_k]); _e[3]+=1
        eq.append(eq[-1]*(1+r))
        if AGIRLIK_KAYMA:
            poz=poz*(1.0+np.nan_to_num(br))/(1.0+r)
        if MERD_GERI and _gw.any():
            poz=poz+_gw; eq[-1]*=1-np.abs(_gw).sum()*KOM
        if merd.any():
            eq[-1]*=1-np.abs(poz[merd]*mpay[merd]).sum()*KOM
            if MERD_YAY: _bos=poz*merd*mpay
            poz=np.where(merd,poz*(1-mpay),poz)
            if MERD_YAY: _yay(poz,_bos,~merd,eq,giris,cv[i+1])
        if yaridan.any():
            eq[-1]*=1-np.abs(poz[yaridan]).sum()*0.5*KOM
            poz=np.where(yaridan,poz*0.5,poz)
        if cik.any():
            eq[-1]*=1-np.abs(poz[cik]).sum()*KOM
            eski=poz.copy()
            if KATKI:
                for _k in np.flatnonzero(cik):
                    if _k in _acik:
                        _d=_acik.pop(_k); _d['kapanis']='TP'; katki_defter.append(_d)
            if MERD_YAY>=2: _bos2=np.where(cik,poz,0.0)
            yon=np.sign(poz[cik]); poz=np.where(cik,0.0,poz); giris=np.where(cik,np.nan,giris); zirve=np.where(cik,np.nan,zirve)
            if MERD_YAY>=2: _yay(poz,_bos2,~cik,eq,giris,cv[i+1])
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
        if EK_ESIK>0:
            # MADDE 250: ALEYHTE giden ve TP'si dolmamis bacaklara ekle
            for k in np.flatnonzero(poz!=0):
                if ek_say[k]>=EK_SAYI or cik[k]: continue
                e=giris[k]; f=cv[i+1,k]
                if not (np.isfinite(e) and e>0 and np.isfinite(f) and f>0): continue
                uzun=poz[k]>0
                aleyh=(1-f/e) if uzun else (f/e-1)
                if aleyh<EK_ESIK: continue
                if not U[i+1,k]: continue
                dw=ilk_w[k]*EK_PAY
                if dw<=0: continue
                if EK_REZ and REZERV>0:
                    # rezervden finanse et: brut sabit kalsin diye esit
                    # agirlikta kisilma YOK - rezerv zaten bosta duran sermaye
                    pass
                yeni=poz[k]+(dw if uzun else -dw)
                # AGIRLIKLI ORTALAMA giris
                giris[k]=(abs(poz[k])*e+dw*f)/(abs(poz[k])+dw)
                poz[k]=yeni; zirve[k]=f
                ek_say[k]+=1; eq[-1]*=1-dw*KOM
                _EKS[0]+=1; _EKS[1]+=dw
    return pd.Series(eq,index=C.index[bas:])

# MADDE 415: DILIMLER ARASI ORTAK COIN TAVANI. Canli botta 15 dilim TEK hesapta;
# ayni coin bircok dilimde secilince toplam agirligi kitabin %10-15'ine cikiyor
# (madde 414: LAB 0,148). CAP_ORTAK=c -> bir dilim yeniden dengelerken coin basina
# toplam (diger dilimler + bu dilim) agirlik / faz sayisi <= c. CAP_DAGIT=1 ->
# kirpilan pay ayni taraftaki diger bacaklara orantili dagitilir (brut korunur).
CAP_ORTAK=float(os.environ.get('CAP_ORTAK','0'))
# MADDE 481: TEK_GIRIS=1 -> dilimler lockstep kosar ve TP/kademe/stop coinin hesap duzeyindeki agirlikli
# ortalama girisinden olculur (canli botun Binance entryPrice'i). 0 -> dilim basina giris (parite).
TEK_GIRIS=int(os.environ.get('TEK_GIRIS','0')); _REG={}
def _dol(sev,uzun,i,k):
    """Kar-al limitinin dolum fiyati. TEK_GIRIS'te ortalama giris kayinca seviye barin ACILISINDA zaten gecilmis
    olabilir (limit piyasanin icine kurulur -> acilistan dolar, daha iyi fiyat). Parite modunda eski davranis."""
    if not TEK_GIRIS: return sev
    o=OV[i+1,k]
    if not np.isfinite(o): return sev
    return max(sev,o) if uzun else min(sev,o)
# MADDE 455: CAP_TARAF=short -> tavan yalniz SHORT bacaklara (long serbest). Bos/iki -> parite.
CAP_TARAF=os.environ.get('CAP_TARAF','iki').strip()
CAP_DAGIT=int(os.environ.get('CAP_DAGIT','0'))
_CAPS=[0,0]   # [kirpilan bacak sayisi, toplam kirpilan agirlik]
def _ortak_kos(baslar,n,olcut,tp):
    gens=[_bt2g(b,n,olcut,tp) for b in baslar]
    NF_=len(gens); lim=CAP_ORTAK*NF_ if CAP_ORTAK>0 else np.inf
    msg=[next(g) for g in gens]; bitti=[False]*NF_; son=[None]*NF_
    poz_son=[np.zeros(C.shape[1]) for _ in gens]
    t=min(m[0] for m in msg)
    while not all(bitti):
        aktif=[j for j in range(NF_) if not bitti[j] and msg[j][0]==t]
        for j in aktif: poz_son[j]=msg[j][1]
        for j in aktif:
            _i,_p,y=msg[j]
            cev=None
            if y is not None:
                diger=sum(poz_son[q] for q in range(NF_) if q!=j)
                y2=y.copy(); serbest={1:0.0,-1:0.0}
                for k in np.flatnonzero(y2!=0):
                    sg=1 if y2[k]>0 else -1
                    if (CAP_TARAF=='short' and sg>0) or (CAP_TARAF=='long' and sg<0):
                        continue
                    izin=max(0.0,lim-sg*diger[k])
                    if abs(y2[k])>izin:
                        serbest[sg]+=abs(y2[k])-izin; _CAPS[0]+=1; _CAPS[1]+=abs(y2[k])-izin
                        y2[k]=sg*izin
                if CAP_DAGIT:
                    for sg in (1,-1):
                        if serbest[sg]<=0: continue
                        ad=[k for k in np.flatnonzero(y2*sg>0) if abs(y2[k])<max(0.0,lim-sg*diger[k])-1e-12]
                        top=sum(abs(y2[k]) for k in ad)
                        if top<=0: continue
                        for k in ad:
                            ek=serbest[sg]*abs(y2[k])/top
                            y2[k]=sg*min(abs(y2[k])+ek,max(0.0,lim-sg*diger[k]))
                cev=y2
            try:
                msg[j]=gens[j].send(cev)
            except StopIteration as e:
                bitti[j]=True; son[j]=e.value
        t+=1
    print(f"# CAP_ORTAK={CAP_ORTAK} DAGIT={CAP_DAGIT}: kirpilan bacak {_CAPS[0]}, toplam kirpilan agirlik {_CAPS[1]/NF_:.1f}",flush=True)
    return son

def calis2(ad,n,olcut):
    # MADDE 338: FAZ_LISTE geri yazildi (madde 325'te eklenmisti, konteyner
    # kaybinda gitti - madde 335). Faz ofsetleri ARTIK LISTE olabilir, yani
    # REB'i tam bolmeyen faz sayilari da kurulabilir (13 faz gibi). Engel
    # hic panelin 4 saatlik olmasi degildi, ofsetlerin range() ile
    # uretilmesiydi. Bos ise eski davranis BIREBIR korunur (parite).
    _fl=os.environ.get('FAZ_LISTE','').strip()
    if _fl:
        ofs=[int(x) for x in _fl.replace(' ','').split(',') if x!='']
        print(f'# FAZ_LISTE: {len(ofs)} faz {ofs}',flush=True)
    else:
        adim=max(1,REB//FAZ); ofs=list(range(0,REB,adim))
    # MADDE 338: FAZ SAYISI ARTIK SABIT DEGIL. Eskiden butun teshis ve
    # kar-kaynagi ciktilari SABIT 5'e boluyordu, oysa FAZ=15/REB=30'da
    # motor 15 faz kosuyor: o tablolarin hepsi 3 KAT SISKINDI. Mansetler
    # (CAGR/Sharpe/dusus) etkilenmemisti cunku onlar E'den gelir; sisen
    # yalniz atif tablolariydi. Artik fiili faz sayisina bolunuyor.
    NF=len(ofs)
    if CAP_ORTAK>0 or TEK_GIRIS:
        gs=[x.pct_change() for x in _ortak_kos([1200+_fz+f for f in ofs],n,olcut,TP)]
    else:
        gs=[bt2(1200+_fz+f,n,olcut,tp=TP).pct_change() for f in ofs]
    g=pd.concat(gs,axis=1).mean(axis=1).dropna(); E=(1+g).cumprod()
    out=[]
    for p,m in [('tam',E.index>='2022-01-01'),('22-24',E.index<'2025-01-01'),('25-26',E.index>='2025-01-01')]:
        e=E[m]/E[m].iloc[0]; o=D.ozet(e); out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    # MADDE 346: E_CIKTI verilirse oraya yaz (paralel kosular birbirinin
    # /tmp/g19E_{_fz}.pkl'ini ezmesin). Bos -> eski davranis, parite ayni.
    pickle.dump(E,open(os.environ.get('E_CIKTI') or f'/tmp/g19E_{_fz}.pkl','wb'))
    if _PZ_YOL and _PZ[0] is not None:
        _W=_PZ[0]/NF; _ii,_kk=np.nonzero(_W)
        pd.DataFrame({'zaman':C.index[_ii],'sembol':C.columns[_kk],'w':_W[_ii,_kk]}).to_pickle(_PZ_YOL)
    if _ADY_YOL:
        pd.DataFrame([(C.index[i],C.columns[k],t) for i,la_,sa_ in _ADY for t,ks in ((1,la_),(-1,sa_)) for k in ks],
                     columns=['zaman','sembol','taraf']).drop_duplicates().to_pickle(_ADY_YOL)
    if _GK_YOL:
        _df=pd.DataFrame([(d,C.columns[k],v[0]/NF,v[1]/NF,v[2]/max(v[3],1),v[3]/NF) for (d,k),v in _GK.items()],
                         columns=['gun','sembol','fiyat','funding','ort_poz','bar'])
        _df.to_pickle(_GK_YOL)
    if KATKI and katki_defter:
        import pickle as _pk4
        _pk4.dump(pd.DataFrame(katki_defter), open(f'/tmp/katki_{_fz}.pkl','wb'))
        print(f'KATKI defteri: {len(katki_defter)} bacak',flush=True)
    if FON_OLC and fon_seri:
        import pickle as _pk3
        _pk3.dump(pd.Series([v for _,v in fon_seri],
                            index=pd.DatetimeIndex([d for d,_ in fon_seri])),
                  open(f'/tmp/fon_{_fz}.pkl','wb'))
    if FON_OLC and fon[1]>0:
        _bg=fon[0]/fon[1]*6.0      # bar -> gun (6 bar = 1 gun)
        print(f'FUNDING: tahsil edilen {fon[0]/fon[1]*100:.4f}%/bar = '
              f'{_bg*100:.4f}%/gun  ({fon[1]} bar)',flush=True)
    if _BRT[1]>0:
        print(f'BRUT: fiili ortalama carpan {_BRT[0]/_BRT[1]:.4f} '
              f'({_BRT[1]} kurulum)',flush=True)
    if BOSLUK and bos[1]>0:
        print(f'BOSLUK: fiili/hedef brut = {bos[0]/bos[1]*100:.2f}%  '
              f'(bos sermaye {100-bos[0]/bos[1]*100:.2f}%, {bos[2]} bar)',flush=True)
    yil=(len(C)-1200)/(6*365.25)
    print('takip cikis/yil',round(say_t[0]/NF/yil),'sabit TP/yil',round(say_t[1]/NF/yil),
          '| YAS cikisi/yil L',round(say_y[0]/NF/yil),'S',round(say_y[1]/NF/yil))
    yl=(len(C)-1200)/(6*365.25)
    t=sum(abs(v) for k,v in AY.items() if k!='kom')
    print(f'  YIL YIL LONG vs SHORT TARAF (yillik puan, {NF} fazin ortalamasi):')
    print(f'    {"yil":<6}{"LONG fnd":>10}{"LONG fiy":>10}{"LONG tp":>9}{"LONG NET":>10}   {"SHORT fnd":>10}{"SHORT fiy":>10}{"SHORT tp":>9}{"SHORT NET":>11}')
    for _y in sorted(YIL):
        v=[x/5*100 for x in YIL[_y]]
        print(f'    {_y:<6}{v[0]:>+10.1f}{v[1]:>+10.1f}{v[2]:>+9.1f}{v[0]+v[1]+v[2]:>+10.1f}   '
              f'{v[3]:>+10.1f}{v[4]:>+10.1f}{v[5]:>+9.1f}{v[3]+v[4]+v[5]:>+11.1f}')
    print(f'  TUTMA GUNUNE GORE (yillik puan, {NF} fazin ortalamasi):')
    print(f'    {"":<6}{"LONG fnd":>10}{"LONG fiyat":>12}{"LONG tp":>10}{"SHORT fnd":>11}{"SHORT fiyat":>12}{"SHORT tp":>10}')
    _y=(len(C)-1200)/(6*365.25)
    for _g in range(6):
        _l=GUN.get(('L',_g),[0,0,0,0]); _s=GUN.get(('S',_g),[0,0,0,0])
        _ad=f'{_g+1}.gun' if _g<5 else '6+'
        print(f'    {_ad:<6}{_l[0]/NF/_y*100:>+10.1f}{_l[1]/NF/_y*100:>+12.1f}{_l[2]/NF/_y*100:>+10.1f}'
              f'{_s[0]/NF/_y*100:>+11.1f}{_s[1]/NF/_y*100:>+12.1f}{_s[2]/NF/_y*100:>+10.1f}')
    print(f'  KAR KAYNAKLARI (5 fazin toplami, yillik puan olarak):')
    for k,ad in [('Sf','SHORT bacak funding'),('Lf','LONG bacak funding'),
                 ('Sp','SHORT bacak fiyat'),('Lp','LONG bacak fiyat'),
                 ('Stp','SHORT kar-al fiyat'),('Ltp','LONG kar-al fiyat')]:
        print(f'    {ad:<22} {AY[k]/NF/yl*100:>+8.1f} puan/yil   (payi %{abs(AY[k])/t*100:>4.1f})')
    print(f'    {"TOPLAM":<22} {sum(AY[k] for k in ("Sf","Lf","Sp","Lp","Stp","Ltp"))/NF/yl*100:>+8.1f} puan/yil')
    print(f'REB{REB//6}g FAZ{_fz} TOL{TOL} REZ{REZERV}/{REZ_ESIK} YARIM{YARIM} AYNI{AYNI} rez_kullanim/yil {say_r[0]/NF/((len(C)-1200)/(6*365.25)):.0f} | {ad:<4} tp{TP} kom{KOM} doldur{DOLDUR} dolan{say_d[0]//NF} {n}+{n} | '+' | '.join(out),flush=True)

if __name__=='__main__':
    ad=sys.argv[1]; n=int(sys.argv[2])
    if ad=='uc':            # 2n adaydan en uc n (tabanla ayni olmali)
        calis2(ad,n,lambda i,a,t: np.full(len(a),np.nan))
    elif ad.startswith('rast'):
        rng=np.random.default_rng(int(ad[4:]))
        calis2(ad,n,lambda i,a,t: rng.random(len(a)))
    else:
        M=pickle.load(open('/tmp/metrik_panel.pkl','rb'))
        if ad in ('tpmdl','tpmdl_p'):
            # MADDE 254: GRAFIK MODELI. Havuz olcutu = modelin tahmin ettigi
            # "bu bacagin TP'si tutma suresi icinde dolar" olasiligi.
            # Taraf duyarli: long tarafta long paneli, short tarafta short.
            _y=('/tmp/tp_olasilik_plasebo.pkl' if ad=='tpmdl_p'
                else '/tmp/tp_olasilik.pkl')
            _TP=pickle.load(open(_y,'rb'))
            _PL=_TP['long'].reindex(index=C.index,columns=C.columns).values
            _PS=_TP['short'].reindex(index=C.index,columns=C.columns).values
            calis2(ad,n,lambda i,a,t: (_PL if t>0 else _PS)[i][a])
        elif ad=='oi':
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
        elif ad in ('ls_derin','ls_cek'):
            # MADDE 479: kalabalik olcutu + EMIR DEFTERI. Long tarafta onceki gunun defter derinligi
            # (ad=ls_derin: log ±%1 notional, INCE tercih; ls_cek: derinligin 7 g medyanina orani, DUSUK tercih)
            # sira harmani: rank(kalabalik) + DW*rank(defter). Short tarafi saf 'ls'. Veri yok -> 0,5.
            _DP=pickle.load(open('/tmp/derin_panel.pkl','rb'))['lD1' if ad=='ls_derin' else 'cek'].values
            _L9=np.log(M['count_long_short_ratio']).values
            _DW=float(os.environ.get('DW','0.5'))
            def _r9(v): return pd.Series(v).rank(pct=True).fillna(0.5).values
            def _dsec(i,a,t):
                b=_r9(-t*_L9[i][a])
                if t>0: b=b+_DW*_r9(-_DP[i][a])
                return b
            calis2(ad,n,_dsec)
        elif ad=='ls':
            # MADDE 362: LS_GECIKME bar (4 sa) kadar BAYAT oran - canli botun
            # oran API'si cevap vermezse "son bilinen oranlari" kullanmasinin
            # maliyeti. 0 (varsayilan) -> eski davranis birebir.
            _lg=int(os.environ.get('LS_GECIKME','0'))
            # MADDE 365: LS_KOL ile oran sutunu secilebilir; '+' ile birden fazla
            # sutunun LOG ortalamasi (geometrik). Bos -> count_long_short_ratio (parite).
            _kol=os.environ.get('LS_KOL','').strip() or 'count_long_short_ratio'
            _kl=[k for k in _kol.split('+') if k]
            _Lr=np.exp(sum(np.log(M[k]) for k in _kl)/len(_kl)) if len(_kl)>1 else M[_kl[0]]
            if _lg>0: _Lr=_Lr.shift(_lg)
            # MADDE 364: LS_ORT bar boyunca log oranin kayan ortalamasi (0 -> anlik).
            _lo=int(os.environ.get('LS_ORT','0'))
            _Ll=np.log(_Lr)
            if _lo>1: _Ll=_Ll.rolling(_lo,min_periods=1).mean()
            L=_Ll.values
            calis2(ad,n,lambda i,a,t: -t*L[i][a])     # long tarafta dusuk oran, short tarafta yuksek
        elif ad in ('tp_ters','ls_tpele','ls_tpkat','ls_tpele_p','ls_tpkat_p'):
            # MADDE 255: madde 254'un ondalik tablosu TARAF ASIMETRIK cikti -
            # long tarafta tahmin ile para TERS (en ust ondalik -1,53%),
            # short tarafta DUZ (+1,72 puan). Uc kullanim denenir:
            #   tp_ters  : long'da DUSUK, short'ta YUKSEK olasilik secilir
            #   ls_tpele : uretim olcutu secer, model yalnizca long tarafta
            #              en yuksek TPELE dilimini ELER (veto, secim degil)
            #   ls_tpkat : sira harmani, agirlik TPW
            # ls_tpele_p: AYNI eleme ama PLASEBO olasilik paneliyle
            _y=('/tmp/tp_olasilik_plasebo.pkl'
                if ad in ('ls_tpele_p','ls_tpkat_p') else '/tmp/tp_olasilik.pkl')
            _T=pickle.load(open(_y,'rb'))
            _PL=_T['long'].reindex(index=C.index,columns=C.columns).values
            _PS=_T['short'].reindex(index=C.index,columns=C.columns).values
            _L5=np.log(M['count_long_short_ratio']).values
            _ELE=float(os.environ.get('TPELE','0.20'))
            _TPW=float(os.environ.get('TPW','0.5'))
            def _r(v): return pd.Series(v).rank(pct=True).values
            if ad=='tp_ters':
                calis2(ad,n,lambda i,a,t: (-_PL[i][a]) if t>0 else _PS[i][a])
            elif ad in ('ls_tpele','ls_tpele_p'):
                def _ele(i,a,t):
                    base=-t*_L5[i][a]
                    if t>0:
                        pp=_PL[i][a]
                        g=np.isfinite(pp)
                        if g.sum()>=4:
                            esik=np.nanquantile(pp[g],1.0-_ELE)
                            # elenenler EN DIBE: sira korunur, yalnizca veto
                            base=np.where(g&(pp>=esik),-np.inf,base)
                    return base
                calis2(ad,n,_ele)
            else:
                calis2(ad,n,lambda i,a,t: _r(-t*_L5[i][a])
                       + _TPW*_r((-_PL[i][a]) if t>0 else _PS[i][a]))
        elif ad in ('volsec','volsec_ters'):
            # MADDE 257: havuz olcutu = OYNAKLIK. Kitap funding ile taraf
            # basina 15 aday seciyor; burada havuz onlardan EN OYNAK 5'ini
            # aliyor (kullanicinin "yogun volatiliteyi yakala" onerisi).
            # _ters: en SAKIN 5 - yon kontrolu.
            _V180=pd.DataFrame(_ret).rolling(180,min_periods=60).std().values
            if ad=='volsec': calis2(ad,n,lambda i,a,t: _V180[i][a])
            else:            calis2(ad,n,lambda i,a,t: -_V180[i][a])
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
