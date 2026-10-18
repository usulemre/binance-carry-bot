"""indicators.py dogrulugu - her strateji buna bagli, hic test edilmemisti.

En kritik kontrol: LOOK-AHEAD. Bir indikator gelecekteki bir bari
kullaniyorsa TUM backtest sonuclari gecersiz olur ve bu sessizce olur.
"""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd
import indicators as I

def veri(n=200, seed=1):
    rng=np.random.default_rng(seed)
    c=100*np.cumprod(1+rng.normal(0,0.02,n))
    h=c*(1+abs(rng.normal(0,0.01,n))); l=c*(1-abs(rng.normal(0,0.01,n)))
    o=np.concatenate([[c[0]],c[:-1]])
    return pd.DataFrame({'open':o,'high':np.maximum(h,np.maximum(o,c)),
                         'low':np.minimum(l,np.minimum(o,c)),'close':c,
                         'volume':rng.uniform(1000,5000,n)})

print("=== 1) LOOK-AHEAD TARAMASI (en kritik) ===")
print("   Yontem: seriyi i. bardan KES, indikator degeri degisiyor mu?")
print("   Degisiyorsa o indikator GELECEGE bakiyor demektir.")
df=veri(200)
import config
tam=I.compute_all_indicators(df, config.STRATEGY)
kesim=150
kisa=I.compute_all_indicators(df.iloc[:kesim].reset_index(drop=True), config.STRATEGY)
sorunlu=[]
for kol in tam.columns:
    if kol in ('date','open','high','low','close','volume','open_time','close_time',
               'quote_volume','trades','taker_buy_base','taker_buy_quote','ignore'):
        continue
    if kol not in kisa.columns: continue
    a=tam[kol].iloc[kesim-1]; b=kisa[kol].iloc[kesim-1]
    if pd.isna(a) and pd.isna(b): continue
    if pd.isna(a) or pd.isna(b): sorunlu.append((kol,'NaN uyumsuz',a,b)); continue
    if abs(float(a)-float(b)) > max(1e-9, abs(float(a))*1e-9):
        sorunlu.append((kol, 'DEGER FARKLI', a, b))
print(f"   {len(tam.columns)} sutun kontrol edildi")
if sorunlu:
    for k,t,a,b in sorunlu: print(f"   !! {k}: {t} (tam={a} kesik={b})")
else:
    print("   LOOK-AHEAD YOK: OK")
assert not sorunlu, "LOOK-AHEAD BULUNDU - tum backtest sonuclari gecersiz!"

print("\n=== 2) Donchian shift(1) dogru mu ===")
d=pd.DataFrame({'high':[1,2,3,10,5],'low':[1,1,1,1,1],'close':[1,2,3,10,5]})
up,lo=I.donchian_channels(d,3)
print(f"   bar 3'te ust kanal: {up.iloc[3]} (3 olmali - kendi high'i 10 DAHIL OLMAMALI)")
assert up.iloc[3]==3, "Donchian kendi barini iceriyor - LOOKAHEAD!"

print("\n=== 3) RSI sinirlari (0-100) ===")
r=I.rsi(df['close'],14).dropna()
print(f"   min={r.min():.1f} max={r.max():.1f}")
assert r.min()>=0 and r.max()<=100
# UC UC DURUM (sifira bolme - burada gercek bir hata bulundu)
artan=pd.Series(np.arange(1,100,dtype=float))
azalan=pd.Series(np.arange(100,1,-1,dtype=float))
duz=pd.Series([100.0]*50)
print(f"   surekli artan : {I.rsi(artan,14).iloc[-1]:.1f} (100 olmali - hic kayip yok)")
print(f"   surekli azalan: {I.rsi(azalan,14).iloc[-1]:.1f} (0 olmali - hic kazanc yok)")
print(f"   duz fiyat     : {I.rsi(duz,14).iloc[-1]:.1f} (50 olmali - notr)")
assert I.rsi(artan,14).iloc[-1] == 100.0, "kayipsiz seride RSI 100 olmali (eski kod 50 veriyordu!)"
assert I.rsi(azalan,14).iloc[-1] == 0.0, "kazancsiz seride RSI 0 olmali"
assert I.rsi(duz,14).iloc[-1] == 50.0, "duz fiyatta RSI 50 olmali"

print("\n=== 4) ATR pozitif ve makul ===")
a=I.atr(df,14).dropna()
print(f"   min={a.min():.4f} ortalama/fiyat=%{(a.mean()/df['close'].mean()*100):.2f}")
assert (a>0).all(), "ATR negatif/sifir!"

print("\n=== 5) Bollinger: ust > orta > alt ===")
u,m,l=I.bollinger_bands(df['close'],20,2.0)
# DIKKAT: NaN karsilastirmasi her zaman False doner. Once NaN'lari
# ele, sonra karsilastir - aksi halde isinma donemindeki NaN'lar
# "bantlar ters" gibi gorunur (bu testte bir kez yasandi).
gecerli = u.notna() & m.notna() & l.notna()
ters = int(((u < m) | (m < l))[gecerli].sum())
print(f"   gecerli bar: {int(gecerli.sum())}, ters siralama: {ters} (0 olmali)")
assert ters == 0, "Bollinger bantlari ters!"

print("\n=== 6) ADX sinirlari (0-100) ===")
ad=I.adx(df,14)
adv = ad[0] if isinstance(ad,tuple) else ad
adv=pd.Series(adv).dropna()
print(f"   min={adv.min():.1f} max={adv.max():.1f}")
assert adv.min()>=0 and adv.max()<=100

print("\n=== 6b) Bollinger genisligi volatiliteyle artmali ===")
sakin=pd.Series(100+np.sin(np.arange(200)/10)*0.5)
oynak=pd.Series(100+np.sin(np.arange(200)/10)*10)
gs=(I.bollinger_bands(sakin,20,2.0)[0]-I.bollinger_bands(sakin,20,2.0)[2]).dropna().mean()
go=(I.bollinger_bands(oynak,20,2.0)[0]-I.bollinger_bands(oynak,20,2.0)[2]).dropna().mean()
print(f"   sakin seri genislik={gs:.3f}  oynak seri={go:.3f}")
assert go > gs*5, "Bollinger volatiliteye tepki vermiyor!"

print("\n=== 7) SABIT fiyat serisinde cokme olmamali (sifira bolme) ===")
sabit=pd.DataFrame({'open':[100.]*100,'high':[100.]*100,'low':[100.]*100,
                    'close':[100.]*100,'volume':[1000.]*100})
out=I.compute_all_indicators(sabit, config.STRATEGY)
inf_var=np.isinf(out.select_dtypes(include=[np.number]).values).any()
print(f"   sonsuz deger: {inf_var} (False olmali)")
assert not inf_var, "sabit seride sonsuz deger uretildi!"

print("\n=== 8) Yetersiz veri -> cokme yok ===")
for n in [1,5,20]:
    try:
        I.compute_all_indicators(veri(n), config.STRATEGY)
    except Exception as e:
        raise AssertionError(f"{n} barda coktu: {e}")
print("   1/5/20 barda cokme yok: OK")

print("\nINDIKATOR TESTLERI GECTI")
