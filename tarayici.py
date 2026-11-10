#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 746 — PİYASA TARAYICISI (panelin "Piyasa" sekmesi için). Kullanıcı isteği: tüm coinlerde saatlik / günlük /
3 günlük / haftalık / aylık en çok yükselen-düşen, funding'i en uç olanlar.

  * API ANAHTARI KULLANMAZ, EMİR GÖNDERMEZ; botla bağı yok. Yalnız Binance USDⓈ-M HERKESE AÇIK uçları okur
    (exchangeInfo, ticker/24hr, premiumIndex, fundingInfo, klines). Demo kurulumda da GERÇEK piyasa okunur.
  * Çıktı: defter/tarayici.json (atomik yazım). Zamanlayıcı: deploy/carry-tarayici.timer (10 dk).
  * Değişimler: 1 sa = 5 dk mumlardan (~60 dk önceki açılış), 3 g / 7 g / 30 g = günlük mum kapanışlarından (UTC gün),
    24 sa = Binance ticker. Funding yıllık = son oran × (24 / ödeme aralığı) × 365.

Kullanım:  python3 tarayici.py [--cikti defter/tarayici.json]
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = os.getenv("CARRY_TARAYICI_URL", "https://fapi.binance.com")
CIKTI = os.getenv("CARRY_TARAYICI_DOSYA", os.path.join("defter", "tarayici.json"))
ISCI = int(os.getenv("CARRY_TARAYICI_ISCI", "6"))


def _al(yol: str, deneme: int = 3):
    """Herkese açık uçtan JSON; hata olursa artan beklemeyle tekrar. Başarısızsa None."""
    for i in range(deneme):
        try:
            r = urllib.request.Request(URL + yol, headers={"User-Agent": "carry-tarayici"})
            with urllib.request.urlopen(r, timeout=15) as f:
                return json.loads(f.read())
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def _yuzde(simdi: float, once) -> float | None:
    try:
        once = float(once)
        return round((simdi / once - 1) * 100, 2) if once > 0 else None
    except (TypeError, ValueError):
        return None


def coin_satiri(s: str, tik: dict, pi: dict, aralik_h: float, onboard_ms: int | None, gunluk: list | None,
                dk5: list | None, simdi_ms: int) -> dict | None:
    """Tek coinin satırı (saf fonksiyon; test edilir). gunluk: 1d mumlar (eskiden yeniye, son eleman açık gün);
    dk5: 5m mumlar (son 13)."""
    try:
        fiyat = float(pi.get("markPrice") or tik.get("lastPrice"))
    except (TypeError, ValueError):
        return None
    if not fiyat > 0:
        return None
    fr = pi.get("lastFundingRate")
    fr = None if fr in (None, "") else float(fr)
    k = {"s": s, "f": fiyat, "d24": _yuzde(fiyat, tik.get("openPrice")) if tik.get("openPrice") else None,
         "hacim": round(float(tik.get("quoteVolume") or 0) / 1e6, 2),
         "fr": None if fr is None else round(fr * 100, 4), "ah": aralik_h,
         "fy": None if fr is None else round(fr * (24.0 / aralik_h) * 365 * 100, 1),
         "yas": None if not onboard_ms else int((simdi_ms - int(onboard_ms)) // 86_400_000)}
    if dk5 and len(dk5) >= 12:
        k["d1"] = _yuzde(fiyat, dk5[-12][1])          # ~55–60 dk önceki 5 dk mumun açılışı
    if gunluk and len(gunluk) >= 2:
        kap = [float(x[4]) for x in gunluk[:-1]]      # tamamlanmış günler
        for ad, n in (("d3", 3), ("d7", 7), ("d30", 30)):
            if len(kap) >= n:
                k[ad] = _yuzde(fiyat, kap[-n])
    return k


def tara(simdi: float | None = None, al=_al) -> dict:
    simdi = simdi or time.time(); simdi_ms = int(simdi * 1000)
    ei = al("/fapi/v1/exchangeInfo") or {}
    sem = {x["symbol"]: x for x in ei.get("symbols", [])
           if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING"}
    if not sem:
        raise RuntimeError("exchangeInfo okunamadı / boş")
    tik = {x["symbol"]: x for x in (al("/fapi/v1/ticker/24hr") or []) if x.get("symbol") in sem}
    pi = {x["symbol"]: x for x in (al("/fapi/v1/premiumIndex") or []) if x.get("symbol") in sem}
    ara = {x["symbol"]: float(x.get("fundingIntervalHours") or 8) for x in (al("/fapi/v1/fundingInfo") or [])}

    def mum(s):
        return s, al(f"/fapi/v1/klines?symbol={s}&interval=1d&limit=31"), al(f"/fapi/v1/klines?symbol={s}&interval=5m&limit=13")

    with ThreadPoolExecutor(max_workers=max(1, ISCI)) as ex:
        mumlar = {s: (g, d) for s, g, d in ex.map(mum, sorted(sem))}
    out = []
    for s in sorted(sem):
        if s not in pi and s not in tik:
            continue
        g, d = mumlar.get(s, (None, None))
        k = coin_satiri(s, tik.get(s, {}), pi.get(s, {}), ara.get(s, 8.0), sem[s].get("onboardDate"), g, d, simdi_ms)
        if k:
            out.append(k)
    return {"zaman": int(simdi), "coinler": out, "kaynak": URL}


def yaz(dosya: str, veri: dict) -> None:
    os.makedirs(os.path.dirname(dosya) or ".", exist_ok=True)
    tmp = dosya + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, dosya)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--cikti", default=CIKTI)
    a = ap.parse_args()
    t0 = time.time()
    try:
        v = tara()
    except Exception as e:
        print(f"tarayıcı başarısız: {e}", file=sys.stderr); sys.exit(1)
    yaz(a.cikti, v)
    print(f"tarayıcı: {len(v['coinler'])} coin → {a.cikti} ({time.time() - t0:.0f} sn)")
