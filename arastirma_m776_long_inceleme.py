# MADDE 776 — demo long'ları inceleme (13 Kas 2026). Veri: data.binance.vision günlük 1 sa mum + metrics (/tmp/m776/raw), son saatler spot data-api. Betimsel.
import glob, zipfile, io, json, urllib.request
import pandas as pd, numpy as np
S = ["INIT","CYBER","ZEC","ONE","AKE","ICNT","BMT","WLD","BTC","ETH"]
def oku(pat, kol=None):
    fr=[]
    for f in sorted(glob.glob(pat)):
        z=zipfile.ZipFile(f); d=pd.read_csv(z.open(z.namelist()[0]), header=None if kol else 0)
        if kol and not str(d.iloc[0,0]).isdigit(): d=d.iloc[1:]
        fr.append(d)
    return pd.concat(fr)
K={}; Mt={}
for s in S:
    k=oku(f"raw/{s}USDT-1h-*.zip", kol=True); k=k.iloc[:,[0,4,7]].astype(float); k.columns=["t","c","qv"]
    k.index=pd.to_datetime(k.t,unit="ms"); K[s]=k
    m=oku(f"raw/{s}USDT-metrics-*.zip"); m.index=pd.to_datetime(m.create_time); Mt[s]=m.sort_index()
# son 24+ saat spot
for s in S:
    try:
        d=json.load(urllib.request.urlopen(f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=40",timeout=10))
        sp=pd.Series([float(x[4]) for x in d], index=pd.to_datetime([x[0] for x in d],unit="ms"))
    except Exception: sp=None
    K[s+"_sp"]=sp
pd.set_option("display.width",250)
rows=[]
for s in S:
    c=K[s].c; m=Mt[s]
    def at(t): return c[:t].iloc[-1]
    sp=K[s+"_sp"]; son=sp.iloc[-1] if sp is not None else np.nan
    sp_deg=(son/sp[:c.index[-1]].iloc[-1]-1)*100 if sp is not None and len(sp[:c.index[-1]]) else np.nan
    ls=m["count_long_short_ratio"].astype(float); oi=m["sum_open_interest_value"].astype(float)
    rows.append(dict(coin=s, f_1kas=round(at("2026-11-01"),5), f_11kas=round(c.iloc[-1],5),
        ekim20_11kas=round((c.iloc[-1]/c.iloc[0]-1)*100,1), kas1_11=round((c.iloc[-1]/at("2026-11-01")-1)*100,1),
        kas7_11=round((c.iloc[-1]/at("2026-11-07")-1)*100,1), son24sa_spot=round(sp_deg,1),
        LS_1kas=round(ls[:"2026-11-01"].iloc[-1],2), LS_7kas=round(ls[:"2026-11-07"].iloc[-1],2), LS_son=round(ls.iloc[-1],2),
        OI_deg_kas7=round((oi.iloc[-1]/oi[:"2026-11-07"].iloc[-1]-1)*100,1),
        hacim_mUSD_gun=round(K[s].qv[-72:].sum()/3/1e6,1)))
print(pd.DataFrame(rows).set_index("coin").to_string())
# günlük kapanışlar
D=pd.DataFrame({s:K[s].c.resample("D").last() for s in S})["2026-11-01":]
print("\nGünlük kapanış (Kas 1 = 100):"); print((D/D.iloc[0]*100).round(0).T.to_string())
