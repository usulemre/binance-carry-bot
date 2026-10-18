"""metrics: acik pozisyon (open interest) + trader konumlanma.
GUNLUK dosyalar - cok fazla. En likit N sembol, gunluk ozet olarak saklanir."""
import urllib.request, io, zipfile, os, sys, concurrent.futures as cf
import pandas as pd
B="https://data.binance.vision/data/futures/um/daily/metrics"
R="/home/claude/binance_bot/binance_bot"
GUNLER=pd.date_range("2022-06-01","2026-08-31",freq="D").strftime("%Y-%m-%d").tolist()
def gun(s,g):
    try:
        b=urllib.request.urlopen(f"{B}/{s}/{s}-metrics-{g}.zip",timeout=30).read()
        z=zipfile.ZipFile(io.BytesIO(b))
        t=z.read(z.namelist()[0]).decode().splitlines()
        sat=[l.split(",") for l in t if l and not l.startswith("create_time")]
        if not sat: return None
        df=pd.DataFrame(sat).iloc[:,[0,2,3,4,5,6]]
        df.columns=["t","oi","oi_val","tt_cnt_ls","tt_sum_ls","cnt_ls"]
        for c in df.columns[1:]: df[c]=pd.to_numeric(df[c],errors="coerce")
        # gunluk OZET: son deger + ortalama konumlanma
        return {"date":g,"oi_val":df.oi_val.iloc[-1],
                "tt_sum_ls":df.tt_sum_ls.mean(),"cnt_ls":df.cnt_ls.mean()}
    except Exception: return None
def sembol(s):
    p=f"{R}/data_oi/{s}.csv"
    if os.path.exists(p): return None
    rows=[]
    with cf.ThreadPoolExecutor(24) as ex:
        for r in ex.map(lambda g: gun(s,g), GUNLER):
            if r: rows.append(r)
    if len(rows)<600: return f"{s} yetersiz({len(rows)})"
    pd.DataFrame(rows).to_csv(p,index=False)
    return None
if __name__=="__main__":
    import json
    syms=json.load(open(sys.argv[3])) if len(sys.argv)>3 else \
         sorted(x.replace("_4h.csv","") for x in os.listdir(f"{R}/historical_data_wide"))
    for s in syms[int(sys.argv[1]):int(sys.argv[2])]:
        m=sembol(s)
        if m: print(m,flush=True)
    print(f"bitti {len(os.listdir(R+'/data_oi'))}",flush=True)
