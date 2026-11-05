#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 723 — LİKİDASYON VERİSİ TOPLAYICI (madde 718: USDⓈ-M likidasyon arşivi yok → veri ileriye dönük biriktirilir).

Binance'in herkese açık `!forceOrder@arr` akışını dinler ve her zorunlu kapanışı günlük dosyaya yazar.
  * API ANAHTARI KULLANMAZ, EMİR GÖNDERMEZ, botla hiçbir paylaşımı yoktur (ayrı süreç, ayrı servis). Bot çalışmasa da çalışır.
  * Çıktı: <KLASOR>/YYYY-MM-DD.jsonl  (UTC gün; satır başına bir olay: t, sembol, yon, fiyat, ort_fiyat, adet, usd, durum)
  * Kopma olursa artan beklemeyle yeniden bağlanır; kopuklar ayrı bir satırla kaydedilir ({"bosluk": [bas, bit]}) ki
    analizde eksik dönem SIFIR likidasyon sanılmasın.
  * Sınır (Binance belgesi): akış sembol başına 1000 ms içinde yalnız SON likidasyonu gönderir → anlık yoğunlukta örneklem eksik.

Kullanım:  python3 likidasyon_toplayici.py [--klasor /opt/carry/veri_likidasyon]
Servis:    deploy/carry-likidasyon.service (varsayılan KAPALI; açmak kullanıcı kararı).
"""
import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone

AKIS = "wss://fstream.binance.com/ws/!forceOrder@arr"
VARSAYILAN = os.environ.get("CARRY_LIKIDASYON_KLASOR", "/opt/carry/veri_likidasyon")


def satir(mesaj: dict) -> dict | None:
    """Binance forceOrder mesajı -> kayıt satırı. Biçim dışıysa None (hata FIRLATMAZ)."""
    try:
        o = mesaj.get("o") or {}
        fiyat = float(o.get("p") or 0); ort = float(o.get("ap") or 0); adet = float(o.get("z") or o.get("q") or 0)
        # SELL = long pozisyon tasfiyesi (zorla satış), BUY = short tasfiyesi
        return {"t": int(o.get("T") or mesaj.get("E")), "sembol": str(o["s"]), "yon": "LONG_TASFIYE" if o.get("S") == "SELL" else "SHORT_TASFIYE",
                "fiyat": fiyat, "ort_fiyat": ort, "adet": adet, "usd": round((ort or fiyat) * adet, 4), "durum": o.get("X")}
    except Exception:
        return None


def yaz(klasor: str, kayit: dict) -> str:
    gun = datetime.fromtimestamp(kayit.get("t", time.time() * 1000) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    yol = os.path.join(klasor, f"{gun}.jsonl")
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return yol


async def calis(klasor: str, url: str = AKIS, en_cok: int | None = None) -> int:
    import websockets
    os.makedirs(klasor, exist_ok=True)
    say, bekle, kopus = 0, 1.0, None
    while en_cok is None or say < en_cok:
        try:
            async with websockets.connect(url, ping_interval=60, ping_timeout=60, max_queue=10_000) as ws:
                if kopus is not None:
                    yaz(klasor, {"t": int(time.time() * 1000), "bosluk": [kopus, int(time.time() * 1000)]}); kopus = None
                bekle = 1.0
                async for ham in ws:
                    k = satir(json.loads(ham))
                    if k:
                        yaz(klasor, k); say += 1
                        if en_cok is not None and say >= en_cok:
                            return say
        except Exception as e:                          # ağ / sunucu kopması: kaydet, bekle, yeniden bağlan
            if kopus is None:
                kopus = int(time.time() * 1000)
            print(f"likidasyon akışı koptu ({type(e).__name__}: {str(e)[:80]}); {bekle:.0f} sn sonra yeniden", flush=True)
            await asyncio.sleep(bekle); bekle = min(bekle * 2, 300.0)
    return say


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--klasor", default=VARSAYILAN)
    a = ap.parse_args()
    print(f"likidasyon toplayıcı → {a.klasor} (anahtarsız, salt okunur akış)", flush=True)
    asyncio.run(calis(a.klasor))
