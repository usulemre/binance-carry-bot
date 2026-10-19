#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 340 — FUNDING ARALIĞI TAHMİNCİSİ: MEDYAN mı SON GÖZLEM mi?

BULGU (ölçüldü, varsayılmadı): evren ödeme aralığına göre yarılıyor —
**482 sembol 4 saatte bir, 355 sembol 8 saatte bir**, 4 sembol saatlik.
Ve **826 sembolün 199'u (%24,1) örnek içinde aralığını DEĞİŞTİRMİŞ**
(ör. 8 sa → 4 sa).

Sinyal (`canli_sinyal_kur.py`) ödeme oranını günlüğe çevirirken aralığı
**son 30 ödemenin medyanından** alıyor:

    ar = max(median(son NK ardisik fark), TABAN=4)
    sinyal = ortalama_oran * (24 / ar)

MEKANİZMA: bir sembol 8 sa'dan 4 sa'ya geçtiğinde medyan ~15 ödeme
boyunca hâlâ 8 der. O pencerede sinyal günlük birikimi **YARI**
hesaplar, sembol kesitsel sıralamada hak ettiğinden aşağıda kalır ve
kitap o carry'yi kaçırır. Ters yönde (4 → 8) sembol fazla sıralanır ve
hak etmediği bacak açılır. Binance aralığı tipik olarak funding
oynaklığı arttığında kısaltır, yani hata **en çok carry'nin en yüksek
olduğu yerde** oluyor.

ADAY: medyan yerine **en son gözlenen aralık**. İkisi de NEDENSELDİR
(yalnız bar anına kadarki ödemeler kullanılır) — bu bir look-ahead
değişikliği değil, tahminci değişikliği.

PLASEBO (ön kayıt): `KARISTIR=1` aralık tahmincisini sembol-bazında
KARIŞTIRIR (her sembole başka bir sembolün aralık serisi verilir).
Kazanç gerçekten aralık bilgisindense plasebo onu yok etmeli.

ÜRETİR
    /tmp/sk_<AD>.pkl   — motorun SK_DOSYA'sı ile doğrudan kullanılabilir

KULLANIM
    AD=son   YONTEM=son      python sinyal_aralik_varyanti.py
    AD=med   YONTEM=medyan   python sinyal_aralik_varyanti.py   # parite
    AD=plas  YONTEM=son KARISTIR=1 python sinyal_aralik_varyanti.py
"""
from __future__ import annotations

import os
import pickle

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
P = pickle.load(open("/tmp/panel.pkl", "rb"))
C = P["C"]
kol = list(C.columns)

PEN = float(os.environ.get("PEN", "48"))
TABAN = float(os.environ.get("TABAN", "4"))
AD = os.environ.get("AD", "aralik_son")
YONTEM = os.environ.get("YONTEM", "son")        # son | medyan
KARISTIR = int(os.environ.get("KARISTIR", "0"))
TOHUM = int(os.environ.get("TOHUM", "11"))
NK = max(4, min(400, int(PEN) + 4))

bar_h = C.index.values.astype("datetime64[s]").astype(np.int64) / 3600.0
out = np.full((len(bar_h), len(kol)), np.nan)

# aralık serilerini (gerekirse) karıştırmak için önce hepsini oku
veri = {}
for s in kol:
    fy = os.path.join(R, "data_funding_genis", f"{s}.csv")
    if not os.path.exists(fy):
        continue
    try:
        f = pd.read_csv(fy, parse_dates=["date"])
    except Exception:
        continue
    f["date"] = f["date"].dt.floor("h")
    f = f.drop_duplicates("date").sort_values("date")
    if len(f) < 3:
        continue
    veri[s] = (f["date"].values.astype("datetime64[s]").astype(np.int64) / 3600.0,
               f["funding"].values.astype(float))

# PLASEBO: aralık bilgisini başka sembollerden ver (oranlar kendi kalır)
aralik_kaynak = {s: s for s in veri}
if KARISTIR:
    ss = sorted(veri)
    karisik = list(ss)
    np.random.default_rng(TOHUM).shuffle(karisik)
    aralik_kaynak = dict(zip(ss, karisik))

for j, s in enumerate(kol):
    if s not in veri:
        continue
    t, r = veri[s]
    ta, _ = veri[aralik_kaynak[s]]
    cs = np.concatenate([[0.0], np.cumsum(r)])
    hi = np.searchsorted(t, bar_h, side="right")
    lo = np.searchsorted(t, bar_h - PEN, side="right")
    hia = np.searchsorted(ta, bar_h, side="right")
    for i in range(len(bar_h)):
        h, l = hi[i], lo[i]
        if h == 0 or h <= l:
            continue
        ort = (cs[h] - cs[l]) / (h - l)
        ha = hia[i]
        a0 = max(0, ha - NK)
        tt = ta[a0:ha]
        if tt.size < 2:
            continue
        d = np.diff(tt)
        d = d[(d >= 0.5) & (d <= 24)]
        if d.size == 0:
            continue
        if YONTEM == "son":
            ham = d[-1]                       # EN SON gözlenen aralık
        else:
            ham = np.sort(d)[d.size // 2]     # medyan (mevcut davranış)
        ar = max(ham, TABAN)
        out[i, j] = ort * (24.0 / ar)

SIN = pd.DataFrame(out, index=C.index, columns=kol).where(C.notna())
pickle.dump(SIN, open(f"/tmp/sk_{AD}.pkl", "wb"))

eski = P.get("sk")
kors = []
if eski is not None:
    for i in range(0, len(C), 50):
        a, b = SIN.values[i], eski.values[i]
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() > 20:
            kors.append(np.corrcoef(a[m], b[m])[0, 1])
print("%s: yontem=%s karistir=%d pencere %.0fsa | hucre %d | panel sk ile "
      "kesitsel kor %+.4f" % (AD, YONTEM, KARISTIR, PEN,
                              int(SIN.notna().sum().sum()),
                              float(np.nanmean(kors)) if kors else float("nan")),
      flush=True)
