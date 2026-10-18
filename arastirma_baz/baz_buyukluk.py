"""Madde 220: ÇEYREKLİK BAZ — BÜYÜKLÜK TARAMASI.

Madde 219'un dersi: güçlü bir IC işlenebilir bir edge demek DEĞİL - önce
BÜYÜKLÜĞÜ ölç. Bu kez o disiplin ÖNCE uygulandı: kitap kurulmadan, motor
yazılmadan, sadece bazın yıllık büyüklüğü ve funding'le farkı ölçüldü.

Veri: data.binance.vision USDT-M aylık günlük klines (perp + vadeli).
İndirirken tarayıcı User-Agent başlığı gerekiyor (madde 219).

ÖLÇÜM SONUCU (BTC, 8 vade, 2023-2024):
    çeyreklik baz       %+9,46/yıl  (100% vadede pozitif)
    perp funding        %+7,28/yıl  (aynı dönem)
    NET (baz - funding) %+2,19/yıl
    kapsam              SADECE BTC ve ETH (USDT-M çeyrekliği olan tek ikili)

REDDEDİLDİ: net prim, 2 sembolde ve çeyreklik rollover mekaniğiyle,
ana kitabın brüt +109,8 puanlık funding gelirinin yanında anlamsız.

YAPISAL SEBEP: baz ile funding AYNI primin iki yüzü. İkisi de aynı
kaldıraç talebini fiyatlıyor, o yüzden neredeyse birbirini götürüyorlar -
madde 201'in ("funding, olayın fiyatıdır") genellemesi.
"""
import glob
import os
import re

import numpy as np
import pandas as pd


def oku(yol: str) -> pd.Series:
    """Binance kline CSV -> kapanış serisi (ms/µs damgası otomatik)."""
    d = pd.read_csv(yol, header=None, usecols=[0, 4], names=["t", "c"])
    d = d[pd.to_numeric(d["t"], errors="coerce").notna()]
    ts = d["t"].astype("int64")
    if ts.max() > 1e15:            # mikrosaniye damgası
        ts = ts // 1000
    d["t"] = pd.to_datetime(ts, unit="ms")
    return d.set_index("t")["c"].astype(float)


def tara(dizin: str = "/tmp/baz", kok: str = "BTCUSDT",
         alt_gun: float = 5, ust_gun: float = 120) -> pd.DataFrame:
    """Her vade için yıllıklaştırılmış baz primi.

    `alt_gun`: vadeye bu kadar günden az kalmışsa atlanır (son günlerde
    prim sıfıra yakınsar ve yıllıklaştırma patlar).
    """
    dosya = glob.glob(f"{dizin}/*.csv")
    perp = sorted(f for f in dosya
                  if re.search(rf"/{kok}_\d{{4}}-\d{{2}}\.csv$", f))
    if not perp:
        raise SystemExit(f"{dizin} içinde {kok} perp verisi yok")
    P = pd.concat([oku(f) for f in perp]).sort_index()
    P = P[~P.index.duplicated()]
    vadeler = sorted({re.search(rf"{kok}_(\d{{6}})_", os.path.basename(f)).group(1)
                      for f in dosya
                      if re.search(rf"{kok}_\d{{6}}_", os.path.basename(f))})
    sat = []
    for v in vadeler:
        fl = sorted(f for f in dosya if f"{kok}_{v}_" in os.path.basename(f))
        Q = pd.concat([oku(f) for f in fl]).sort_index()
        Q = Q[~Q.index.duplicated()]
        son = pd.Timestamp("20" + v[:2] + "-" + v[2:4] + "-" + v[4:6])
        d = pd.concat([P.rename("p"), Q.rename("q")], axis=1).dropna()
        kalan = (son - d.index).days.values.astype(float)
        m = (kalan > alt_gun) & (kalan < ust_gun)
        if m.sum() < 20:
            continue
        y = (d["q"].values / d["p"].values - 1)[m] * 365.0 / kalan[m]
        sat.append((v, int(m.sum()), np.nanmean(y) * 100, np.nanmedian(y) * 100,
                    np.nanpercentile(y, 10) * 100, np.nanpercentile(y, 90) * 100))
    return pd.DataFrame(sat, columns=["vade", "gun", "ort%", "medyan%",
                                      "p10%", "p90%"])


def funding_ayni_donem(sembol: str = "BTCUSDT", bas: str = "2023-01-01") -> float:
    """Aynı dönemde perp funding, yıllık yüzde (8 saat varsayımı)."""
    R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data_funding_genis", f"{sembol}.csv")
    b = pd.read_csv(R, parse_dates=["date"])
    b = b[b["date"] >= bas]
    return float(b["funding"].mean() * 3 * 365 * 100)


if __name__ == "__main__":
    f = tara()
    print("BTC ÇEYREKLİK BAZ — yıllıklaştırılmış prim (vadeye 5-120 gün):")
    print(f.round(2).to_string(index=False))
    baz = f["ort%"].mean()
    fnd = funding_ayni_donem()
    print(f"\nORTALAMA baz        : %{baz:+.2f}/yıl "
          f"(pozitif vade oranı %{100*np.mean(f['ort%']>0):.0f})")
    print(f"perp funding        : %{fnd:+.2f}/yıl")
    print(f"NET (baz - funding) : %{baz - fnd:+.2f}/yıl  <- işlenebilir kısım")
    print("\nKapsam: USDT-M çeyrekliği SADECE BTC ve ETH'de var -> kesitsel")
    print("seçim yok. Ana kitap brüt %+109,8 funding topluyor (6+6 bacak).")
    print("KARAR: REDDEDİLDİ (madde 220).")
