import glob, zipfile, json, urllib.request
import pandas as pd, numpy as np
S=["INIT","CYBER","ZEC","ONE","AKE","ICNT","BMT","WLD"]
def z(f):
    zz=zipfile.ZipFile(f); d=pd.read_csv(zz.open(zz.namelist()[0]),header=None)
    if not str(d.iloc[0,0]).isdigit(): d=d.iloc[1:]
    return d.iloc[:,:5].astype(float)
rows=[]
for s in S:
    d=pd.concat([z(f) for f in sorted(glob.glob(f"raw/{s}USDT-1d-*.zip"))]); d.index=pd.to_datetime(d[0],unit="ms")
    h=pd.concat([z(f) for f in sorted(glob.glob(f"raw/{s}USDT-1h-*.zip"))]); h.index=pd.to_datetime(h[0],unit="ms")
    hd=h.resample("D").agg({1:"first",2:"max",3:"min",4:"last"}); hd=hd[hd.index>d.index[-1]]
    D=pd.concat([d[[1,2,3,4]],hd]); D.columns=["o","h","l","c"]
    son=D.c.iloc[-1]
    try:
        k=json.load(urllib.request.urlopen(f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=30",timeout=10)); son=float(k[-1][4]); kay="spot"
    except Exception: kay="vadeli 11 Kas"
    ilk=D.index[0]
    ath=D.h.max(); athg=D.h.idxmax(); low=D.l.min(); lowg=D.l.idxmin()
    h30=D.h[-30:].max(); l30=D.l[-30:].min()
    rows.append(dict(coin=s, ilk_veri=ilk.strftime("%m-%d"), son=son, kaynak=kay,
        tepe=f"{ath:.5g} ({athg:%m-%d})", tepeden=f"{(son/ath-1)*100:.0f}%",
        dip=f"{low:.5g} ({lowg:%m-%d})", dipten=f"+{(son/low-1)*100:.0f}%",
        aralik30_konum=f"%{(son-l30)/(h30-l30)*100:.0f}", gunluk_oynaklik=f"%{D.c.pct_change()[-30:].std()*100:.0f}"))
pd.set_option("display.width",250)
print(pd.DataFrame(rows).set_index("coin").to_string())
