import json,urllib.request,time,sys,threading
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
def ac(u): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'curl/8.5.0'}),timeout=60))
canli=set(open('/tmp/okx_canli.txt').read().split()); bn=open('/tmp/tum_semboller.txt').read().split()
aday=set(canli)
for s in bn:
    b=s[:-4]
    for p in ('1000000','1000'):
        if b.startswith(p) and len(b)>len(p): b=b[len(p):]; break
    aday.add(f'{b}-USDT')
aday=sorted(aday)
def ms(y,m): return int(datetime(y,m,1,tzinfo=timezone.utc).timestamp()*1000)
pencere=[(ms(2022,3),ms(2022,12)),(ms(2023,1),ms(2023,10)),(ms(2023,11),ms(2024,8)),(ms(2024,9),ms(2025,6)),(ms(2025,7),ms(2026,4)),(ms(2026,5),ms(2026,8))]
isler=[(mod,tuple(aday[i:i+5]),b,e) for mod in (3,2) for i in range(0,len(aday),5) for b,e in pencere]
out={}; kilit=threading.Lock(); say=[0,0]
def is_(x):
    mod,grp,b,e=x
    u=f"https://www.okx.com/api/v5/public/market-data-history?module={mod}&instType=SWAP&instFamilyList={','.join(grp)}&dateAggrType=monthly&begin={b}&end={e}"
    msg=''
    for d in range(8):
        try:
            r=ac(u)
            if r.get('code')=='0': break
            msg=r.get('msg')
        except Exception as ex: msg=str(ex)
        time.sleep(1+2*d)
    else:
        with kilit: say[1]+=1; print('HATA',grp[0],b,msg,flush=True)
        return
    with kilit:
        for dt in r['data']:
            for x in dt['details']:
                for g in x['groupDetails']:
                    out.setdefault(f"{mod}|{x['instFamily']}",set()).add(g['url'].split('?')[0])
        say[0]+=1
        if say[0]%100==0: print(say[0],'/',len(isler),'aile',len(out),'hata',say[1],flush=True)
t=time.time()
with ThreadPoolExecutor(4) as ex: list(ex.map(is_,isler))
json.dump({k:sorted(v) for k,v in out.items()},open('/tmp/okx/liste.json','w'))
print('bitti',len(out),sum(len(v) for v in out.values()),'hata',say[1],'sn',int(time.time()-t),flush=True)
