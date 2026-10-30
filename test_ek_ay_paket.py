#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 673 testleri: yeni ay veri paketi (ekim_paket_indir.py) Binance biçiminde dosyaları doğru adlarla toplar;
indir_ek_ay.py --paket (VERI_EK=uzun) paketten okuyup uzun zemin dosyalarına YALNIZ yeni satırları doğru kolonlarla ekler."""
import io, os, shutil, subprocess, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
R0 = os.path.dirname(os.path.abspath(__file__))
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

def zipcsv(ad, metin):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(ad, metin)
    return b.getvalue()

T = tempfile.mkdtemp()
for d in ("data_genis_uzun", "data_funding_uzun", "data_taker_uzun", "data_metrik"):
    os.makedirs(os.path.join(T, d))
shutil.copy(os.path.join(R0, "indir_ek_ay.py"), T)
S = "AAAUSDT"
open(f"{T}/data_genis_uzun/{S}_4h.csv", "w").write("date,open,high,low,close,volume,quote_volume\n"
    "2026-09-30 16:00:00,1,1,1,1,10,10\n2026-09-30 20:00:00,1,1.1,0.9,1.05,10,10.5\n")
open(f"{T}/data_funding_uzun/{S}.csv", "w").write("date,funding\n2026-09-30 16:00:00.000,0.0001\n")
open(f"{T}/data_taker_uzun/{S}.csv", "w").write("date,quote_volume,tb_quote,tb_oran\n2026-09-30 20:00:00,10.5,5,0.476\n")
open(f"{T}/data_metrik/{S}.csv", "w").write("bar,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,"
                                            "count_long_short_ratio,sum_taker_long_short_vol_ratio\n2026-09-30 20:00:00,100,1,1,1.2,1\n")
ms = lambda s: int(__import__("pandas").Timestamp(s).value // 10**6)
k = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
k += f"{ms('2026-09-30 20:00')},9,9,9,9,1,0,9,1,1,4,0\n"     # tekrar eden eski bar: EKLENMEMELİ
for i, t in enumerate(["2026-10-01 00:00", "2026-10-01 04:00", "2026-10-31 20:00"]):
    k += f"{ms(t)},1,1.2,0.8,{1.1 + i / 10},20,0,22,5,10,11,0\n"
f = "calc_time,funding_interval_hours,last_funding_rate\n" + "".join(f"{ms(t)},8,{v}\n" for t, v in
     [("2026-09-30 16:00", 0.0001), ("2026-10-01 00:00", 0.0003), ("2026-10-01 08:00", -0.0002)])
m = ("create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,"
     "count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
     "2026-10-01 00:05:00,AAAUSDT,5,110,1.1,1.1,1.30,1\n2026-10-01 03:55:00,AAAUSDT,5,120,1.1,1.1,1.40,1\n"
     "2026-10-01 04:00:00,AAAUSDT,5,130,1.1,1.1,1.50,1\n")
pk = os.path.join(T, "paket_2026-10.zip")
with zipfile.ZipFile(pk, "w") as z:
    z.writestr(f"{S}/k2026-10.zip", zipcsv("k.csv", k))
    z.writestr(f"{S}/f2026-10.zip", zipcsv("f.csv", f))
    z.writestr(f"{S}/m2026-10-01.zip", zipcsv("m.csv", m))
    z.writestr("MANIFEST.txt", "ay=2026-10\n")
r = subprocess.run([sys.executable, "indir_ek_ay.py", "--paket", pk], cwd=T, capture_output=True, text=True,
                   env={**os.environ, "VERI_EK": "uzun"}, timeout=120)
kontrol("indir_ek_ay --paket çalıştı", r.returncode == 0, r.stderr[-500:])
import pandas as pd
F = pd.read_csv(f"{T}/data_genis_uzun/{S}_4h.csv")
kontrol("fiyat: 3 yeni bar, eski bar tekrar edilmedi", len(F) == 5 and list(F.columns)[0] == "date", F.tail(4).to_string())
kontrol("fiyat: tarih biçimi ve close", F.date.iloc[2] == "2026-10-01 00:00:00" and abs(F.close.iloc[-1] - 1.3) < 1e-9)
kontrol("fiyat: quote_volume 8. kolondan", F.quote_volume.iloc[-1] == 22)
FU = pd.read_csv(f"{T}/data_funding_uzun/{S}.csv")
kontrol("funding: 2 yeni satır, uzun biçim (interval kolonu yok)", len(FU) == 3 and list(FU.columns) == ["date", "funding"]
        and abs(FU.funding.iloc[-1] + 0.0002) < 1e-12, FU.to_string())
TK = pd.read_csv(f"{T}/data_taker_uzun/{S}.csv")
kontrol("taker: tb_oran = 11/22", len(TK) == 4 and abs(TK.tb_oran.iloc[-1] - 0.5) < 1e-9, TK.to_string())
M = pd.read_csv(f"{T}/data_metrik/{S}.csv")
kontrol("metrik: 4 sa bara son değer (00:05, 03:55, 04:00 -> 00:00 barı; son = 1.50)",
        len(M) == 2 and abs(M.count_long_short_ratio.iloc[-1] - 1.50) < 1e-9, M.to_string())
r2 = subprocess.run([sys.executable, "indir_ek_ay.py", "--paket", pk], cwd=T, capture_output=True, text=True,
                    env={**os.environ, "VERI_EK": "uzun"}, timeout=120)
kontrol("ikinci kez çalıştırmak tekrar EKLEMEZ", len(pd.read_csv(f"{T}/data_genis_uzun/{S}_4h.csv")) == 5)

# paket indirici: dosya adları ve yayınlanmamış ay
import ekim_paket_indir as E
ii = E.isler(["AAAUSDT"], "2026-10")
kontrol("31 günlük metrik + aylık mum + funding", len(ii) == 33 and ii[0][1] == "AAAUSDT/k2026-10.zip" and ii[-1][1] == "AAAUSDT/m2026-10-31.zip")
kontrol("adlar indir_ek_ay ile uyumlu", ii[1][1] == "AAAUSDT/f2026-10.zip")
E.indir = lambda url, deneme=3: None
eski = os.getcwd(); os.chdir(T)
kontrol("ay yayınlanmamışsa 1 döner, dosya yazmaz", E.main(["2026-11"]) == 1 and not os.path.exists(os.path.join(T, "paket_2026-11.zip")))
E.indir = lambda url, deneme=3: b"PK-sahte"
kontrol("indirme: paket yazılır (metrik yalnız metrikli sembollere)", E.main(["2026-10"]) == 0 and zipfile.ZipFile(os.path.join(T, "paket_2026-10.zip")).read("BTCUSDT/f2026-10.zip") == b"PK-sahte")
os.chdir(eski)
print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
