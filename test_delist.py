#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 661 testleri: delist'e 48 sa kalan semboldeki açık pozisyon kapatılır, dilimlerden çıkar; uzak / normal semboller dokunulmaz."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CARRY_PROFIL", "T4")
import carry_bot as cb
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

simdi = time.time() * 1000
UZAK = 4133404800000   # Binance perp'lerin normal deliveryDate'i (2100)
class _Ic:
    def __init__(s, semler): s.semler = semler; s.iptal = []
    def futures_exchange_info(s): return {"symbols": s.semler}
    def futures_cancel_all_open_orders(s, symbol): s.iptal.append(symbol)
class F:
    def __init__(s, pozlar, semler): s.pozlar = pozlar; s.client = _Ic(semler); s.kapanan = []
    def get_open_positions(s): return s.pozlar
    def close_position(s, sem, yon, adet): s.kapanan.append((sem, yon, adet))

def kur():
    semler = [{"symbol": "AAAUSDT", "status": "TRADING", "contractType": "PERPETUAL", "deliveryDate": simdi + 20 * 3600e3},   # 20 sa
              {"symbol": "BBBUSDT", "status": "TRADING", "contractType": "PERPETUAL", "deliveryDate": simdi + 10 * 86400e3},  # 10 gün
              {"symbol": "CCCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "deliveryDate": UZAK},
              {"symbol": "DDDUSDT", "status": "SETTLING", "contractType": "PERPETUAL", "deliveryDate": UZAK}]
    pozlar = [{"symbol": "AAAUSDT", "positionAmt": "100"}, {"symbol": "BBBUSDT", "positionAmt": "-50"},
              {"symbol": "CCCUSDT", "positionAmt": "10"}, {"symbol": "DDDUSDT", "positionAmt": "-7"}]
    durum = {"dilimler": {"0": {"AAAUSDT": 30.0, "CCCUSDT": 20.0}, "1": {"AAAUSDT": 30.0, "DDDUSDT": -10.0, "BBBUSDT": -15.0}}}
    return F(pozlar, semler), durum

c, d = kur(); k = cb.delist_kapat(c, d)
kontrol("20 sa kalan AAA ve SETTLING DDD kapandı", sorted(k) == ["AAAUSDT", "DDDUSDT"], k)
kontrol("long SELL / short BUY ile, tam adet", sorted(c.kapanan) == [("AAAUSDT", "SELL", 100.0), ("DDDUSDT", "BUY", 7.0)], c.kapanan)
kontrol("açık emirleri iptal edildi", sorted(c.client.iptal) == ["AAAUSDT", "DDDUSDT"], c.client.iptal)
kontrol("dilimlerden çıkarıldı (AAA, DDD yok; BBB, CCC duruyor)",
        all("AAAUSDT" not in h and "DDDUSDT" not in h for h in d["dilimler"].values()) and d["dilimler"]["1"].get("BBBUSDT") == -15.0
        and d["dilimler"]["0"].get("CCCUSDT") == 20.0, d)
c, d = kur(); k = cb.delist_kapat(c, d, dry_run=True)
kontrol("kuru çalışma: emir yok, dilim değişmez", c.kapanan == [] and "AAAUSDT" in d["dilimler"]["0"] and sorted(k) == ["AAAUSDT", "DDDUSDT"])
_e = cb.DELIST_KAPAT_SAAT; cb.DELIST_KAPAT_SAAT = 0
c, d = kur(); kontrol("CARRY_DELIST_KAPAT_SAAT=0: kapalı", cb.delist_kapat(c, d) == [] and c.kapanan == [])
cb.DELIST_KAPAT_SAAT = 300   # 12,5 gün: BBB de girer
c, d = kur(); kontrol("ufuk 300 sa: 10 gün kalan BBB de kapanır", "BBBUSDT" in cb.delist_kapat(c, d))
cb.DELIST_KAPAT_SAAT = _e
class Hata(F):
    def get_open_positions(s): raise RuntimeError("bakım")
c, d = kur(); c.__class__ = Hata
kontrol("pozisyonlar okunamazsa hiçbir şey yapılmaz", cb.delist_kapat(c, d) == [])
kontrol("bilgi yoksa delist sayılmaz", not cb.delist_yakin_mi(None, 48))
print(f"\nSONUÇ: {_h} hata"); sys.exit(1 if _h else 0)
