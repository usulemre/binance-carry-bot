"""Premium index 4s mumlari (data.binance.vision) — sadece evrene en az bir kez girmis semboller.
Premium = (perp fiyat - endeks) / endeks; funding bundan hesaplanir. Madde 148.
Kullanim: python indir_premium.py /tmp/evren_hic.txt
"""
import concurrent.futures as cf, io, os, sys, urllib.request, zipfile
import pandas as pd
B="https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines"
R=os.path.dirname(os.path.abspath(__file__)); HEDEF=os.path.join(R,"data_premium")
os.makedirs(HEDEF,exist_ok=True)
AYLAR=[a for a in (f"{y}-{m:02d}" for y in range(2022,2027) for m in range(1,13)) if a<="2026-08"]
def ay(s,a):
    try:
        b=urllib.request.urlopen(f"{B}/{s}/4h/{s}-4h-{a}.zip",timeout=45).read()
        z=zipfile.ZipFile(io.BytesIO(b)); t=z.read(z.namelist()[0]).decode()
        return [l.split(",") for l in t.splitlines() if l and not l.startswith("open_time")]
    except Exception: return []
def sembol(s):
    p=os.path.join(HEDEF,f"{s}.csv")
    if os.path.exists(p): return None
    rows=[]
    with cf.ThreadPoolExecutor(14) as ex:
        for r in ex.map(lambda a: ay(s,a),AYLAR): rows+=r
    if not rows: return f"{s} bos"
    d=pd.DataFrame(rows).iloc[:,[0,1,2,3,4]]; d.columns=["open_time","open","high","low","close"]
    ot=pd.to_numeric(d.open_time,errors="coerce")
    d["date"]=pd.to_datetime(ot.where(ot<1e14,ot/1000),unit="ms")
    for c in ["open","high","low","close"]: d[c]=pd.to_numeric(d[c],errors="coerce")
    d.dropna(subset=["date","close"]).drop_duplicates("date").sort_values("date")[["date","open","high","low","close"]].to_csv(p,index=False)
syms=open(sys.argv[1]).read().split()
with cf.ThreadPoolExecutor(6) as ex:
    for i,r in enumerate(ex.map(sembol,syms)):
        if r: print(r,flush=True)
        if i%50==0: print(i,len(syms),flush=True)
print("bitti",flush=True)
