#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 753 testleri: funding doğrulama — sahte resmi oranlarla yeniden hesap, pozisyon = ödeme ÖNCESİ son görüntü; anahtar / emir YOK."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funding_dogrula as F

_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

T0 = 1_794_000_000_000          # ms, funding anı
k = tempfile.mkdtemp(); os.makedirs(os.path.join(k, "defter"))
# panel kaydı: dakika anahtarlı; A long 100 adet, oran −0,1% , işaret 2 → +0,2 $ ; B short 10 adet, oran +0,05%, işaret 50 → +0,25 $
json.dump({"g": {str(T0): {"AUSDT": 0.2, "BUSDT": 0.30}, str(T0 + 3600_000): {"CUSDT": 1.0}},
           "d": {str(T0): {"AUSDT": -0.05}}}, open(os.path.join(k, "defter", "funding_olay.json"), "w"))
json.dump({"s": {"AUSDT": [[T0 // 1000 - 7200, 50.0, 2.1], [T0 // 1000 - 600, 100.0, 2.0], [T0 // 1000 + 600, 0.0, 0.0]],
                 "BUSDT": [[T0 // 1000 - 900, -10.0, 51.0]]}}, open(os.path.join(k, "defter", "anlik_poz.json"), "w"))
def sahte(yol):
    if "AUSDT" in yol: return [{"fundingTime": T0 + 37, "fundingRate": "-0.001", "markPrice": "2.0"}]
    if "BUSDT" in yol: return [{"fundingTime": T0 + 12, "fundingRate": "0.0005", "markPrice": "50"}]
    return []
r = F.dogrula(k, gun=30, simdi=T0 / 1000 + 7200, al=sahte)
a = r["coin"]["AUSDT"]; b = r["coin"]["BUSDT"]
kontrol("A: −adet × işaret × oran, pozisyon = ödeme ÖNCESİ son görüntü (100, sonraki 0 değil)", abs(a[1] - 0.2) < 1e-12, a)
kontrol("B (short, pozitif oran → alır)", abs(b[1] - 0.25) < 1e-12, b)
kontrol("toplam ve fark", abs(r["panel"] - 0.5) < 1e-12 and abs(r["resmi"] - 0.45) < 1e-12, r)
kontrol("resmi kaydı / pozisyonu olmayan ödeme ölçülemeyen sayılır, toplama girmez", r["olculemeyen"] == 1 and r["olculemeyen_panel"] == 1.0)
kontrol("demo hesaba yatan ayrıca", abs(r["demo"] + 0.05) < 1e-12)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "funding_dogrula.py")).read()
kontrol("anahtar / emir kodu YOK", all(x not in src for x in ("API_KEY", "api_secret", "create_order", "X-MBX-APIKEY", "/order")))
print("\nHEPSİ GEÇTİ" if _h == 0 else f"\n{_h} HATA"); sys.exit(1 if _h else 0)
