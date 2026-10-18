"""TAM SISTEM WALK-FORWARD — en dürüst doğrulama aracı.

KULLANIM: python full_walkforward.py

Parametreler değiştirildiğinde tekrar çalıştırın. Çıktıda bakılacaklar:
  1) Kaç dönem pozitif? (yarısından azsa dikkat)
  2) Parametre kararlılığı - aynı seçim tekrar ediyor mu?
     (her dönem farklı seçiliyorsa overfitting işareti)
  3) Kazanç yoğunlaşması - en iyi 2-3 dönem çıkarılınca ne kalıyor?

ORİJİNAL AÇIKLAMA:

Simdiye kadar parcalar ayri ayri dogrulandi (cok ufuk, TP, kademeli
azaltma, dispersiyon filtresi...). Ama HEPSI BIRLIKTE, parametreler
SADECE gecmisten secilerek hic test edilmedi.

Yontem: veriyi kronolojik dilimlere bol. Her dilim icin ONCEKI tum
veriden en iyi parametreyi sec, SONRAKI dilimde uygula. Boylece
gelecek bilgisi hic kullanilmaz - canli kullanimin en dogru taklidi.
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, itertools
from backtest_yearly import load_all_csvs
from crosssec_backtest import build_price_panel, run_crosssectional
from data_quality import stale_orani
import crosssec_bot as cb_cfg

d=load_all_csvs('4h')
temiz={s:df for s,df in d.items() if stale_orani(df[df['date'].dt.year>=2022])<0.10}
P=build_price_panel(temiz); P=P[P.index.year>=2022]
print(f"{P.shape[1]} coin, {P.shape[0]} bar ({P.index[0].date()} - {P.index[-1].date()})")

# Aday parametre uzayi (kucuk tutuldu - buyuk grid = coklu test sismesi)
# ÖNEMLİ: KORUMA PARAMETRELERİNİ BURADA ARAMAYIN.
# Kademeli azaltma / devre kesici gibi korumalar tepe-düşüş BİRİKİMİYLE
# çalışır. 6 aylık dilimlerde bu birikim oluşmaz, bu yüzden farklı
# eşikler neredeyse aynı sonucu verir (ölçüldü: 20R ile 50R arası fark
# %3) ve arama anlamsız bir seçim yapar.
# Bu parametreler UZUN KESİNTİSİZ dönemde ayrı ölçülmelidir.
# (Gerçek örnek: walk-forward her dönemde 50R seçti, ama kesintisiz
#  2022-2026 ölçümünde 20R risk ayarlı olarak açık ara daha iyiydi.)
GRID=[]
for hor in [[30,60,90],[30,60],[60,120,180]]:
    for legs in [2,3,4]:
        for tp in [0.03,0.04,0.06]:
            GRID.append((hor,legs,tp))
print(f"{len(GRID)} aday konfigurasyon\n")

# Tersine dönüş filtresi eşiği. Bir KORUMA parametresidir, bu yüzden
# yukarıdaki uyarı gereği GRID'de aranmaz - sabit tutulup açık/kapalı
# karşılaştırması yapılır:  REVCORR=-0.10 python3 full_walkforward.py
import os as _os
_REV = _os.getenv("REVCORR")
_REV = float(_REV) if _REV else None
if _REV == 0:
    _REV = None
print(f"tersine donus filtresi: {'KAPALI' if _REV is None else _REV}\n")


def olc(panel,hor,legs,tp):
    try:
        _,m=run_crosssectional(panel,60,6,legs,horizons_bars=hor,pos_tp=tp,
                               trail_scale=0.30,compound=True,
                               max_reversal_corr=_REV,
                               min_dispersion=cb_cfg.MIN_DISPERSION
                               if cb_cfg.USE_DISPERSION_FILTER else None,
                               dispersion_window=cb_cfg.DISPERSION_WINDOW_BARS,
                               pos_sl=cb_cfg.EMERGENCY_STOP_PCT / 100
                               if cb_cfg.USE_EMERGENCY_STOP else None)
        return m
    except Exception:
        return None

# 6 aylik dilimler
donemler=pd.period_range('2022-07','2026-07',freq='6M')
oos=[]; secimler=[]
print(f"{'donem':<12} {'secilen (ufuk,bacak,TP)':<26} {'OOS getiri':>11} {'Sharpe':>8}")
print('-'*62)
for dn in donemler:
    test_m=(P.index>=dn.start_time)&(P.index<=dn.end_time)
    train_m=P.index<dn.start_time
    if test_m.sum()<200 or train_m.sum()<600: continue
    train=P[train_m]
    # EGITIM: en iyi Sharpe
    en=(None,-99)
    for hor,legs,tp in GRID:
        m=olc(train,hor,legs,tp)
        if m and np.isfinite(m['sharpe']) and m['sharpe']>en[1]:
            en=((hor,legs,tp),m['sharpe'])
    if en[0] is None: continue
    hor,legs,tp=en[0]
    # TEST: onceki veriden warmup ekle
    ctx=P[train_m].tail(max(hor)+30)
    seg=pd.concat([ctx,P[test_m]])
    mt=olc(seg,hor,legs,tp)
    if not mt: continue
    oos.append(mt['total_return_pct']); secimler.append((hor,legs,tp))
    ad=f"{'/'.join(str(h//6) for h in hor)}g,{legs}+{legs},%{tp*100:.0f}"
    print(f"{str(dn):<12} {ad:<26} {mt['total_return_pct']:>+10.1f}% {mt['sharpe']:>8.2f}")

print()
if oos:
    a=np.array(oos)
    bilesik=np.prod([1+x/100 for x in a])
    print(f">>> {len(a)} OOS donem, {(a>0).sum()} pozitif (%{(a>0).mean()*100:.0f})")
    print(f">>> medyan donem getirisi: {np.median(a):+.1f}%")
    print(f">>> bilesik toplam: {(bilesik-1)*100:+.1f}%")
    yil=len(a)/2
    print(f">>> yillik esdeger: {((bilesik**(1/yil))-1)*100:+.1f}%")
    print()
    # parametre kararliligi
    from collections import Counter
    c=Counter(str(s) for s in secimler)
    print("Parametre kararliligi (ayni secim tekrar ediyor mu?):")
    for k,v in c.most_common(3):
        print(f"  {v}/{len(secimler)} kez: {k}")
    print()
    print("KAZANC YOGUNLASMASI (en onemli risk gostergesi):")
    sirali=np.argsort(a)[::-1]
    print(f"  tum donemler        : {(bilesik-1)*100:>+10.1f}%")
    for k in [1,2,3]:
        if k>=len(a): break
        kalan=np.delete(a,sirali[:k])
        b=np.prod([1+x/100 for x in kalan])
        print(f"  en iyi {k} donem haric : {(b-1)*100:>+10.1f}%")
    kalan3=np.delete(a,sirali[:3]) if len(a)>3 else a
    if len(a)>3 and np.prod([1+x/100 for x in kalan3])<1.0:
        print()
        print("  !! UYARI: en iyi 3 donem cikarilinca ZARAR ediliyor.")
        print("     Kazanc birkac patlama donemine bagli - sureklilik yok.")
        print("     Botu uzun sure kesintisiz calistirmak kritik.")
