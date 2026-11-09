#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 746 testleri: piyasa tarayıcısı — sahte Binance yanıtlarıyla değişim / funding hesabı, filtre, atomik yazım; anahtar / emir YOK."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tarayici as T

_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

SIMDI = 1_794_000_000.0
def gun(kapanislar):   # 1d mumlar: [açılış zamanı, o, h, l, c, ...]; son eleman açık gün
    return [[0, "0", "0", "0", str(c)] for c in kapanislar]
def dk5(acilis_once, n=13):
    return [[0, str(acilis_once)]] + [[0, "1"]] * (n - 1)

YANIT = {
    "/fapi/v1/exchangeInfo": {"symbols": [
        {"symbol": "AUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING", "onboardDate": int((SIMDI - 10 * 86400) * 1000)},
        {"symbol": "BUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING", "onboardDate": int((SIMDI - 400 * 86400) * 1000)},
        {"symbol": "CUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "SETTLING"},
        {"symbol": "DUSDC", "contractType": "PERPETUAL", "quoteAsset": "USDC", "status": "TRADING"},
        {"symbol": "EUSDT", "contractType": "CURRENT_QUARTER", "quoteAsset": "USDT", "status": "TRADING"}]},
    "/fapi/v1/ticker/24hr": [{"symbol": "AUSDT", "openPrice": "1.0", "lastPrice": "1.2", "quoteVolume": "123456789"},
                             {"symbol": "BUSDT", "openPrice": "100", "lastPrice": "90", "quoteVolume": "5000000"}],
    "/fapi/v1/premiumIndex": [{"symbol": "AUSDT", "markPrice": "1.2", "lastFundingRate": "-0.001"},
                              {"symbol": "BUSDT", "markPrice": "90", "lastFundingRate": "0.0001"}],
    "/fapi/v1/fundingInfo": [{"symbol": "AUSDT", "fundingIntervalHours": 4}],
    "/fapi/v1/klines?symbol=AUSDT&interval=1d&limit=31": gun([0.6] * 25 + [0.8, 0.9, 1.0, 1.0, 1.0, 1.15]),
    "/fapi/v1/klines?symbol=AUSDT&interval=5m&limit=13": dk5(1.0),
    "/fapi/v1/klines?symbol=BUSDT&interval=1d&limit=31": gun([100, 95]),
    "/fapi/v1/klines?symbol=BUSDT&interval=5m&limit=13": None,      # okunamadı
}
cagri = []
def sahte(yol):
    cagri.append(yol); return YANIT.get(yol)

v = T.tara(simdi=SIMDI, al=sahte)
c = {x["s"]: x for x in v["coinler"]}
kontrol("yalnız USDT süresiz + TRADING", set(c) == {"AUSDT", "BUSDT"}, set(c))
a, b = c["AUSDT"], c["BUSDT"]
kontrol("24 sa değişim (mark / açılış)", a["d24"] == 20.0 and b["d24"] == -10.0, (a["d24"], b["d24"]))
kontrol("1 sa değişim (~60 dk önceki 5 dk açılışı)", a["d1"] == 20.0, a)
kontrol("3 g / 7 g = tamamlanmış gün kapanışlarından", a["d3"] == 20.0 and a["d7"] == 100.0, (a.get("d3"), a.get("d7")))
kontrol("referans fiyatlar (panel canlı % için)", a["r1"] == 1.0 and a["r3"] == 1.0 and a["r7"] == 0.6 and a["r30"] == 0.6 and "r30" not in b, a)
kontrol("30 g: yeterli gün varsa", a["d30"] == 100.0 and "d30" not in b, (a.get("d30"), b))
kontrol("eksik mum: değişim yok, hata yok", "d1" not in b and "d3" not in b)
kontrol("funding % ve aralık", a["fr"] == -0.1 and a["ah"] == 4 and b["ah"] == 8.0)
kontrol("funding yıllık = oran × 24/aralık × 365", a["fy"] == round(-0.001 * 6 * 365 * 100, 1) and b["fy"] == round(0.0001 * 3 * 365 * 100, 1))
kontrol("hacim milyon $, yaş gün", a["hacim"] == 123.46 and a["yas"] == 10 and b["yas"] == 400)
kontrol("yalnız HERKESE AÇIK uçlar", all(y.startswith(("/fapi/v1/exchangeInfo", "/fapi/v1/ticker/24hr", "/fapi/v1/premiumIndex",
                                                        "/fapi/v1/fundingInfo", "/fapi/v1/klines")) for y in cagri))
try:
    T.tara(simdi=SIMDI, al=lambda y: None); kontrol("exchangeInfo yoksa hata", False)
except RuntimeError:
    kontrol("exchangeInfo yoksa hata (boş dosya yazılmaz)", True)

d = os.path.join(tempfile.mkdtemp(), "defter", "tarayici.json")
T.yaz(d, v)
kontrol("atomik yazım, geri okunur", json.load(open(d))["coinler"][0]["s"] == "AUSDT" and not os.path.exists(d + ".tmp"))

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarayici.py")).read()
kontrol("anahtar / emir kodu YOK", all(x not in src for x in ("API_KEY", "api_secret", "create_order", "X-MBX-APIKEY", "SECRET", "/order")))

print("\nHEPSİ GEÇTİ" if _h == 0 else f"\n{_h} HATA"); sys.exit(1 if _h else 0)
