import json,urllib.request,io,zipfile,os,sys,time,threading
import pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
L=json.load(open('/tmp/okx/liste.json'))
os.makedirs('/tmp/okx/fund',exist_ok=True); os.makedirs('/tmp/okx/k4',exist_ok=True)
MOD=sys.argv[1]            # '3' funding, '2' mum
TH=int(sys.argv[2])
def al(u):
    err=None
    for d,v in enumerate(('999','1000')):
        try:
            r=urllib.request.urlopen(urllib.request.Request(u+'?v='+v,headers={'User-Agent':'curl/8.5.0'}),timeout=10).read()
            z=zipfile.ZipFile(io.BytesIO(r)); return pd.read_csv(z.open(z.namelist()[0]))
        except Exception as e:
            err=e; time.sleep(1)
    return None
def isle(fam,u):
    d=al(u)
    if d is None: return fam,u,None
    d=d[d.instrument_name.astype(str).str.endswith('-SWAP')]
    if MOD=='3':
        return fam,u,d[['funding_time','funding_rate']]
    for c in ['open','high','low','close','vol','vol_ccy','vol_quote']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d['t']=pd.to_datetime(d.open_time,unit='ms').dt.floor('4h')
    g=d.sort_values('open_time').groupby('t').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),
        vol=('vol','sum'),vol_ccy=('vol_ccy',lambda x: x.sum(min_count=1)),vol_quote=('vol_quote',lambda x: x.sum(min_count=1)),n=('close','size'))
    return fam,u,g
isler=[(k.split('|')[1],u) for k,us in L.items() if k.startswith(MOD+'|') for u in us]
print('dosya',len(isler),flush=True)
parca={}; hata=[]; t=time.time(); say=0
with ThreadPoolExecutor(TH) as ex:
    fs=[ex.submit(isle,f,u) for f,u in isler]
    for fu in as_completed(fs):
        try: fam,u,d=fu.result()
        except Exception as e: hata.append(str(e)); continue
        if d is None: hata.append(u)
        else: parca.setdefault(fam,[]).append(d)
        say+=1
        if say%500==0: print(say,'/',len(isler),'hata',len(hata),int(time.time()-t),'sn',flush=True)
for fam,ps in parca.items():
    d=pd.concat(ps)
    if MOD=='3':
        d.drop_duplicates('funding_time').sort_values('funding_time').to_csv(f'/tmp/okx/fund/{fam}.csv',index=False)
    else:
        d=d[~d.index.duplicated(keep='last')].sort_index(); d.to_csv(f'/tmp/okx/k4/{fam}.csv')
open(f'/tmp/okx/hata_{MOD}.txt','w').write('\n'.join(hata))
print('bitti aile',len(parca),'hata',len(hata),int(time.time()-t),'sn',flush=True)
