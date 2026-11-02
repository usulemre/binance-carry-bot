#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 706 — ARŞİVDE EKSİK GÜNÜN 4 SA MUMLARINI HAM İŞLEMLERDEN KUR (data.binance.vision daily/trades).

Neden: Binance arşivinde 2026-10-28'in mum dosyaları (aylık ve günlük, bütün aralıklar) YOK; o günün ham işlem dosyası (trades) VAR.
Mum işlemlerden türetilir: aynı 4 sa kovasında ilk / en yüksek / en düşük / son fiyat, miktar toplamı, quote toplamı, taker alış
quote toplamı (is_buyer_maker = false). Doğrulama (2026-10-27, BTC / SOL / TAO): resmi mumla açılış, yüksek, düşük, kapanış, hacim,
quote hacim, taker alış quote ve işlem sayısı BİREBİR aynı (fark 0).

Kullanım: VERI_EK=uzun python3 eksik_gun_islemden.py 2026-10-28 [--dogrula]
  * Yalnız o gün mumu EKSİK olan ve bir önceki ya da sonraki gün işlem gören semboller ele alınır.
  * data_genis_uzun/<S>_4h.csv ve data_taker_uzun/<S>.csv'ye o günün satırları sıralı eklenir (var olan satıra dokunulmaz).
  * Ham işlem dosyası yoksa (sembol o gün işlem görmedi) atlanır ve sayılır; kurgu / doldurma YOK.
  --dogrula : yazmadan önce bir önceki günü aynı yöntemle kurup resmi mumla karşılaştırır (ilk 3 sembol).
"""
import io
import os
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
_EK = os.environ.get("VERI_EK", "")
D_FIYAT = os.path.join(R, "data_genis_" + _EK if _EK else "data_genis")
D_TAKER = os.path.join(R, "data_taker_" + _EK if _EK else "data_taker_genis")
B = "https://data.binance.vision/data/futures/um/daily"
BAR = 4 * 3600 * 1000


def indir(url: str, deneme: int = 3) -> bytes | None:
    import urllib.parse
    url = urllib.parse.quote(url, safe=":/")          # ASCII dışı sembol adları (ör. 币安人生USDT)
    for i in range(deneme):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"indirilemedi: {url}")


def islemden_mum(zbayt: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(zbayt)); f = z.open(z.namelist()[0])
    ilk = f.readline().decode(); f = z.open(z.namelist()[0])
    baslikli = ilk.lower().startswith("id")
    t = pd.read_csv(f, header=0 if baslikli else None, usecols=[1, 2, 3, 4, 5],
                    names=None if baslikli else ["id", "price", "qty", "quote_qty", "time", "is_buyer_maker"])
    t.columns = ["price", "qty", "quote_qty", "time", "is_buyer_maker"]
    t["b"] = (t.time.astype(np.int64) // BAR) * BAR
    al = t.is_buyer_maker.astype(str).str.lower().eq("false")
    t["tb"] = np.where(al, t.quote_qty, 0.0)
    g = t.groupby("b", sort=True)
    k = pd.DataFrame({"open": g.price.first(), "high": g.price.max(), "low": g.price.min(), "close": g.price.last(),
                      "volume": g.qty.sum(), "quote_volume": g.quote_qty.sum(), "tb_quote": g.tb.sum(), "count": g.size()})
    k.index = pd.to_datetime(k.index, unit="ms")
    return k


def dogrula(s: str, gun: str) -> dict:
    tb = indir(f"{B}/trades/{s}/{s}-trades-{gun}.zip"); kb = indir(f"{B}/klines/{s}/4h/{s}-4h-{gun}.zip")
    if tb is None or kb is None:
        return {"sembol": s, "durum": "veri yok"}
    k = islemden_mum(tb)
    z = zipfile.ZipFile(io.BytesIO(kb)); r = pd.read_csv(z.open(z.namelist()[0]))
    if not str(r.columns[0]).startswith("open"):
        r.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
                     "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
    r.index = pd.to_datetime(r.open_time, unit="ms")
    fark = {c: float((k[c] - r[c].astype(float)).abs().max()) for c in ["open", "high", "low", "close", "volume", "quote_volume"]}
    fark["tb_quote"] = float((k.tb_quote - r.taker_buy_quote_volume.astype(float)).abs().max())
    fark["count"] = int((k["count"] - r["count"]).abs().max())
    return {"sembol": s, "durum": "ok", **fark}


def _ekle(yol: str, yeni: pd.DataFrame) -> int:
    d = pd.read_csv(yol)
    d["date"] = d["date"].astype(str)
    var = set(d["date"])
    y = yeni[~yeni["date"].isin(var)]
    if y.empty:
        return 0
    o = pd.concat([d, y], ignore_index=True)
    o = o.sort_values("date", key=lambda x: pd.to_datetime(x)).reset_index(drop=True)
    tmp = yol + ".tmp"; o.to_csv(tmp, index=False); os.replace(tmp, yol)
    return len(y)


def bir(s: str, gun: str) -> tuple[str, str, int]:
    yf = os.path.join(D_FIYAT, f"{s}_4h.csv"); yt = os.path.join(D_TAKER, f"{s}.csv")
    if not os.path.exists(yf):
        return s, "dosya yok", 0
    d = pd.read_csv(yf, usecols=["date"])["date"].astype(str)
    g0 = pd.Timestamp(gun); onc, son = str((g0 - pd.Timedelta(days=1)).date()), str((g0 + pd.Timedelta(days=1)).date())
    if d.str.startswith(gun).sum() >= 6:
        return s, "tam", 0
    if not (d.str.startswith(onc).any() or d.str.startswith(son).any()):
        return s, "işlem görmüyor", 0
    tb = indir(f"{B}/trades/{s}/{s}-trades-{gun}.zip")
    if tb is None:
        # Binance, işlem olmayan kovada mumu önceki kapanışla ve SIFIR hacimle yazar. Yalnız o ay HİÇ hacmi olmayan (işlemsiz /
        # kapanmış) sembollerde aynısı yapılır; hacmi olan sembolde ham işlem yoksa doldurma YAPILMAZ.
        dd = pd.read_csv(yf); ay = dd[dd["date"].astype(str).str.startswith(gun[:7])]
        if len(ay) and float(ay["quote_volume"].fillna(0).sum()) == 0.0:
            onceki = dd[pd.to_datetime(dd["date"]) < pd.Timestamp(gun)].iloc[-1]
            tarih = pd.date_range(gun, periods=6, freq="4h").strftime("%Y-%m-%d %H:%M:%S")
            c = float(onceki["close"])
            fy = pd.DataFrame({"date": tarih, "open": c, "high": c, "low": c, "close": c, "volume": 0.0, "quote_volume": 0.0})
            n = _ekle(yf, fy)
            if os.path.exists(yt):
                _ekle(yt, pd.DataFrame({"date": tarih, "quote_volume": 0.0, "tb_quote": 0.0, "tb_oran": np.nan}))
            return s, "işlemsiz (sıfır hacim)", n
        return s, "ham işlem yok", 0
    k = islemden_mum(tb)
    tarih = k.index.strftime("%Y-%m-%d %H:%M:%S")
    fy = pd.DataFrame({"date": tarih, "open": k.open.values, "high": k.high.values, "low": k.low.values, "close": k.close.values,
                       "volume": k.volume.values, "quote_volume": k.quote_volume.values})
    n = _ekle(yf, fy)
    if os.path.exists(yt):
        ty = pd.DataFrame({"date": tarih, "quote_volume": k.quote_volume.values, "tb_quote": k.tb_quote.values,
                           "tb_oran": (k.tb_quote / k.quote_volume.replace(0, np.nan)).values})
        _ekle(yt, ty)
    return s, "eklendi", n


def main(argv):
    gun = argv[0]
    semboller = sorted(f[:-7] for f in os.listdir(D_FIYAT) if f.endswith("_4h.csv"))
    if "--dogrula" in argv:
        onc = str((pd.Timestamp(gun) - pd.Timedelta(days=1)).date())
        for s in ("BTCUSDT", "SOLUSDT", "TAOUSDT"):
            print("doğrulama", onc, dogrula(s, onc), flush=True)
    with ThreadPoolExecutor(8) as ex:
        def _guvenli(s):
            try:
                return bir(s, gun)
            except Exception as e:
                return s, f"HATA {str(e)[:60]}", 0
        sonuc = list(ex.map(_guvenli, semboller))
    say = pd.Series([d for _, d, _ in sonuc]).value_counts().to_dict()
    print(f"{gun}: {say} · eklenen fiyat satırı {sum(n for *_, n in sonuc)}", flush=True)
    hata = [f"{s}: {d}" for s, d, _ in sonuc if d.startswith("HATA")]
    if hata:
        print("HATALI (eksik kaldı, geçerli SAYILMAZ):", "; ".join(hata[:20]))
    eksik = [s for s, d, _ in sonuc if d == "ham işlem yok"]
    if eksik:
        print("ham işlem dosyası olmayan (o gün işlem görmüş olabilir, kontrol):", ", ".join(eksik[:30]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
