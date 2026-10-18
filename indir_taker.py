import urllib.request, io, zipfile, os, sys, concurrent.futures as cf
import pandas as pd
B="https://data.binance.vision/data/futures/um/monthly/klines"
R="/home/claude/binance_bot/binance_bot"
AYLAR=[f"{y}-{m:02d}" for y in range(2022,2027) for m in range(1,13)]
AYLAR=[a for a in AYLAR if a<="2026-08"]
def ay(s,a):
    try:
        b=urllib.request.urlopen(f"{B}/{s}/4h/{s}-4h-{a}.zip",timeout=40).read()
        z=zipfile.ZipFile(io.BytesIO(b))
        t=z.read(z.namelist()[0]).decode()
        return [l.split(",") for l in t.splitlines() if l and not l.startswith("open_time")]
    except Exception: return []
def sembol(s):
    p=f"{R}/data_taker/{s}.csv"
    if os.path.exists(p): return None
    rows=[]
    with cf.ThreadPoolExecutor(12) as ex:
        for r in ex.map(lambda a: ay(s,a), AYLAR): rows+=r
    if len(rows)<5000: return f"{s} yetersiz({len(rows)})"
    df=pd.DataFrame(rows).iloc[:,[0,5,7,9,10]]
    df.columns=["open_time","volume","quote_volume","tb_vol","tb_quote"]
    ot=pd.to_numeric(df.open_time,errors="coerce")
    df["date"]=pd.to_datetime(ot.where(ot<1e14,ot/1000),unit="ms")
    for c in ["quote_volume","tb_quote"]:
        df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
    # taker DENGESIZLIGI: agresif alicinin payi. 0.5 = dengeli
    df["tb_oran"]=df.tb_quote/df.quote_volume.replace(0,float("nan"))
    df[["date","quote_volume","tb_quote","tb_oran"]].to_csv(p,index=False)
    return None
if __name__=="__main__":
    syms=sorted(x.replace("_4h.csv","") for x in os.listdir(f"{R}/historical_data_wide"))
    a,b=int(sys.argv[1]),int(sys.argv[2])
    for s in syms[a:b]:
        m=sembol(s)
        if m: print(m,flush=True)
    print(f"[{a}:{b}] bitti",flush=True)
