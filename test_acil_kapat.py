#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 663 testleri: acil_kapat.py — listeleme modu emir göndermez; --evet bütün emirleri iptal eder, pozisyonları kapatır, defteri boşaltır."""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CARRY_PROFIL", "T4")
import carry_bot as cb, acil_kapat as A
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1
class I:
    def __init__(s): s.iptal = []; s.tek = []; s.algo = []
    def futures_get_open_orders(s): return [{"symbol": "XUSDT"}, {"symbol": "AUSDT"}]
    def futures_cancel_all_open_orders(s, symbol): s.iptal.append(symbol)
    def futures_cancel_order(s, symbol, orderId): s.tek.append(symbol)
    def futures_cancel_algo_order(s, symbol, algoId): s.algo.append(symbol)
class C:
    mode = "demo"
    def __init__(s): s.client = I(); s.kapanan = []
    def get_open_positions(s): return [{"symbol": "AUSDT", "positionAmt": "5"}, {"symbol": "BUSDT", "positionAmt": "-3"}, {"symbol": "ZUSDT", "positionAmt": "0"}]
    def close_position(s, sem, yon, adet): s.kapanan.append((sem, yon, adet))
d = tempfile.mkdtemp(); dosya = os.path.join(d, "dilim.json")
_eski = cb.dilim_durum_oku, cb.dilim_durum_yaz
durum0 = {"dilimler": {"0": {"AUSDT": 10}}, "kar_al": {"AUSDT": 1}, "felaket": {"BUSDT": 9}, "merdiven": {}}
cb.dilim_durum_oku = lambda *a, **k: json.loads(json.dumps(durum0))
yazilan = {}
cb.dilim_durum_yaz = lambda dur, *a, **k: yazilan.update(dur)
c = C(); r = A.main([], client=c)
kontrol("liste modu: emir yok, kapatma yok", r == 0 and c.kapanan == [] and c.client.iptal == [] and not yazilan)
c = C(); r = A.main(["--evet", "--servis-kontrolu-yok"], client=c)
kontrol("--evet: iki pozisyon doğru yönde kapandı (0 adetli atlandı)", sorted(c.kapanan) == [("AUSDT", "SELL", 5.0), ("BUSDT", "BUY", 3.0)], c.kapanan)
kontrol("--evet: pozisyonlu + açık emirli bütün semboller iptal", sorted(c.client.iptal) == ["AUSDT", "BUSDT", "XUSDT"], c.client.iptal)
kontrol("--evet: kayıtlı kâr al ve felaket (algo) emirleri iptal", c.client.tek == ["AUSDT"] and c.client.algo == ["BUSDT"])
kontrol("--evet: dilim defteri boşaltıldı", yazilan.get("dilimler") == {} and r == 0, yazilan)
A.servis_acik = lambda: True
c = C(); r = A.main(["--evet"], client=c)
kontrol("servis çalışıyorsa reddeder (2), hiçbir şey yapmaz", r == 2 and c.kapanan == [])
cb.dilim_durum_oku, cb.dilim_durum_yaz = _eski
print(f"\nSONUÇ: {_h} hata"); sys.exit(1 if _h else 0)
