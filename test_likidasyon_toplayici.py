#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 723 testleri: likidasyon toplayıcı — mesaj ayrıştırma, günlük dosya, yerel sahte akışla uçtan uca, kopma kaydı; anahtar / emir YOK."""
import asyncio, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import likidasyon_toplayici as L

_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

M = {"e": "forceOrder", "E": 1793836800123, "o": {"s": "BTWUSDT", "S": "SELL", "o": "LIMIT", "q": "120", "p": "1.0500", "ap": "1.0480",
                                                 "X": "FILLED", "l": "120", "z": "120", "T": 1793836800100}}
k = L.satir(M)
kontrol("SELL = long tasfiyesi", k["yon"] == "LONG_TASFIYE", k)
kontrol("usd = ort fiyat × adet", abs(k["usd"] - 1.048 * 120) < 1e-6, k)
kontrol("zaman = olay zamanı (T)", k["t"] == 1793836800100)
kontrol("BUY = short tasfiyesi", L.satir({**M, "o": {**M["o"], "S": "BUY"}})["yon"] == "SHORT_TASFIYE")
kontrol("bozuk mesaj: None, hata fırlatmaz", L.satir({"o": {}}) is None and L.satir({}) is None)

T = tempfile.mkdtemp()
y = L.yaz(T, k)
kontrol("günlük dosya UTC güne göre", os.path.basename(y) == "2026-11-05.jsonl", y)
kontrol("satır JSON olarak geri okunur", json.loads(open(y).read().splitlines()[0])["sembol"] == "BTWUSDT")

# yerel sahte akış (websockets sunucusu) ile uçtan uca
async def uctan_uca():
    import websockets
    async def sunucu(ws):
        for i in range(3):
            await ws.send(json.dumps({**M, "o": {**M["o"], "T": M["o"]["T"] + i}}))
        await ws.send("{\"bozuk\": true}")
        await ws.send(json.dumps({**M, "o": {**M["o"], "s": "APRUSDT", "S": "BUY"}}))
        await asyncio.sleep(0.5)
    async with websockets.serve(sunucu, "127.0.0.1", 0) as s:
        port = s.sockets[0].getsockname()[1]
        k2 = os.path.join(T, "e2e")
        n = await asyncio.wait_for(L.calis(k2, url=f"ws://127.0.0.1:{port}", en_cok=4), 10)
        return n, k2
n, k2 = asyncio.run(uctan_uca())
satirlar = [json.loads(x) for f in os.listdir(k2) for x in open(os.path.join(k2, f))]
kontrol("uçtan uca: 4 geçerli olay yazıldı, bozuk mesaj atlandı", n == 4 and len(satirlar) == 4, (n, len(satirlar)))
kontrol("uçtan uca: short tasfiyesi de kaydedildi", any(s["sembol"] == "APRUSDT" and s["yon"] == "SHORT_TASFIYE" for s in satirlar))

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "likidasyon_toplayici.py")).read()
kontrol("anahtar / emir kodu YOK", all(x not in src for x in ("API_KEY", "api_secret", "create_order", "futures_create", "SECRET")))

print("\nHEPSİ GEÇTİ" if _h == 0 else f"\n{_h} HATA"); sys.exit(1 if _h else 0)
