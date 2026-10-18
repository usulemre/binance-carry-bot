"""KuCoin USDT-M perp: funding (8s) + gunluk mum. Delist edilenler dahil (aday listesi)."""
import json,urllib.request,time,os,sys,threading
from concurrent.futures import ThreadPoolExecutor
B='https://api-futures.kucoin.com'
os.makedirs('/tmp/kc/fund',exist_ok=True); os.makedirs('/tmp/kc/gun',exist_ok=True)
kilit=threading.Lock(); son=[0.0]; HIZ=1/25.0; SAY={'istek':0,'429':0,'hata':0,'t0':time.time()}   # saniyede ~12 istek
def ac(yol):
    for d in range(8):
        with kilit:
            bekle=son[0]+HIZ-time.time()
            if bekle>0: time.sleep(bekle)
            son[0]=time.time()
        try:
            SAY['istek']+=1
            r=json.load(urllib.request.urlopen(urllib.request.Request(B+yol,headers={'User-Agent':'curl/8.5.0'}),timeout=30))
            if r.get('code')=='200000': return r['data']
            if r.get('code') in ('429000',): SAY['429']+=1; time.sleep(5+5*d); continue
            SAY['hata']+=1; print('KOD',r.get('code'),r.get('msg'),yol[:60],flush=True)
            return None
        except Exception as e:
            SAY['hata']+=1
            if SAY['hata']<20: print('EXC',e,yol[:60],flush=True)
            time.sleep(2+3*d)
    return 'HATA'
akt=ac('/api/v1/contracts/active')
aday={x['symbol'] for x in akt if x.get('quoteCurrency')=='USDT' and x['symbol'].endswith('USDTM')}
for s in open('/tmp/tum_semboller.txt').read().split():
    b=s[:-4]
    if b=='BTC': b='XBT'
    aday.add(b+'USDTM')
    for p in ('1000000','1000'):
        if b.startswith(p) and len(b)>len(p): aday.add(b[len(p):]+'USDTM'); break
aday=sorted(aday)
json.dump({x['symbol']:x for x in akt},open('/tmp/kc/aktif.json','w'))
print('aday',len(aday),flush=True)
T0=1640995200000; T1=1788220800000   # 2022-01-01 .. 2026-09-01
def fund(s):
    p=f'/tmp/kc/fund/{s}.csv'
    if os.path.exists(p): return 'var'
    rows=[]; to=T1
    while True:
        d=ac(f'/api/v1/contract/funding-rates?symbol={s}&from={T0}&to={to}')
        if d=='HATA': return 'HATA'
        if not d: break
        rows+= [(x['timepoint'],x['fundingRate']) for x in d]
        mn=min(x['timepoint'] for x in d)
        if len(d)<100 or mn<=T0: break
        to=mn-1
    if rows:
        rows=sorted(set(rows))
        open(p,'w').write('t,funding\n'+'\n'.join(f'{a},{b}' for a,b in rows))
        return len(rows)
    return 0
def gun(s):
    p=f'/tmp/kc/gun/{s}.csv'
    if os.path.exists(p): return 'var'
    rows=[]; fr=T0
    while fr<T1:
        to=min(fr+199*86400000,T1)
        d=ac(f'/api/v1/kline/query?symbol={s}&granularity=1440&from={fr}&to={to}')
        if d=='HATA': return 'HATA'
        if d: rows+=d
        fr=to+1
    if rows:
        seen={}
        for r in rows: seen[r[0]]=r
        open(p,'w').write('t,open,high,low,close,vol,turnover\n'+'\n'.join(','.join(str(v) for v in seen[k]) for k in sorted(seen)))
        return len(seen)
    return 0
say=[0,0,0]
def is_(s):
    a=fund(s)
    if a in (0,): say[1]+=1; return
    b=gun(s)
    with kilit:
        say[0]+=1
        if a=='HATA' or b=='HATA': say[2]+=1; print('HATA',s,a,b,flush=True)
        if say[0]%25==0: print('bitti',say[0],'bos',say[1],'hata',say[2],SAY,round(SAY['istek']/(time.time()-SAY['t0']),1),'istek/sn',flush=True)
with ThreadPoolExecutor(16) as ex: list(ex.map(is_,aday))
print('SON veri olan',say[0],'bos',say[1],'hata',say[2],flush=True)
