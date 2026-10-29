#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 663 testleri: preflight API anahtarı izin kontrolü (çekim izni, IP kısıtlaması, Futures izni)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carry_preflight as p
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1
class I:
    def __init__(s, iz, hata=False): s.iz, s.hata = iz, hata
    def get_account_api_permissions(s):
        if s.hata: raise RuntimeError("demo uç noktası yok")
        return s.iz
class C:
    def __init__(s, mode, iz, hata=False): s.mode = mode; s.client = I(iz, hata)
def kos(c):
    p._satirlar.clear(); p.kontrol_api_izinleri(c); return [(a, d) for a, d, m in p._satirlar]
r = kos(C("live", {"enableWithdrawals": True, "ipRestrict": False, "enableFutures": True}))
kontrol("canlı + çekim açık -> HATA", ("API izinleri (madde 663)", "HATA") in r, r)
kontrol("IP kısıtlaması yok -> UYARI", ("API IP kısıtlaması (madde 663)", "UYARI") in r, r)
r = kos(C("demo", {"enableWithdrawals": True, "ipRestrict": True, "enableFutures": True}))
kontrol("demo + çekim açık -> UYARI (HATA değil)", ("API izinleri (madde 663)", "UYARI") in r, r)
r = kos(C("live", {"enableWithdrawals": False, "ipRestrict": True, "enableFutures": True}))
kontrol("doğru anahtar -> iki TAMAM", r == [("API izinleri (madde 663)", "TAMAM"), ("API IP kısıtlaması (madde 663)", "TAMAM")], r)
r = kos(C("live", {"enableWithdrawals": False, "ipRestrict": True, "enableFutures": False}))
kontrol("Futures izni kapalı -> HATA", ("API vadeli işlem izni (madde 663)", "HATA") in r, r)
r = kos(C("demo", {}, hata=True))
kontrol("okunamazsa UYARI", r == [("API izinleri (madde 663)", "UYARI")], r)
print(f"\nSONUÇ: {_h} hata"); sys.exit(1 if _h else 0)
