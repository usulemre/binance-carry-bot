"""MADDE 870: coin logosu yardımcıları (ağsız)."""
import os
import sys
import tempfile
import types

import coin_ikon as ci

basarisiz = []


def kontrol(ad, kosul, ek=None):
    print(("  [OK]   " if kosul else "  [X]    ") + ad + ("" if kosul else f"  -> {ek}"))
    if not kosul:
        basarisiz.append(ad)


ci.DIZIN = tempfile.mkdtemp()
ci.HARITA = os.path.join(ci.DIZIN, "harita.json")
ci._durum.update(m={"BTC": "u-png", "PEPE": "u-jpg", "KOTU": "u-svg"}, t=9e18)   # taze: arka plan kurulumu başlamaz

kontrol("taban: 1000PEPE -> PEPE", ci.taban("1000PEPE") == "PEPE")
kontrol("taban: 1MBABYDOGE -> BABYDOGE", ci.taban("1MBABYDOGE") == "BABYDOGE")
kontrol("taban: ONDO aynı kalır", ci.taban("ONDO") == "ONDO")
kontrol("geçersiz ad reddedilir (yol gezintisi)", ci.ikon("../etc") is None and ci.ikon("a/b") is None)

VERI = {"u-png": b"\x89PNG\r\n\x1a\n" + b"0" * 50, "u-jpg": b"\xff\xd8\xff" + b"1" * 50, "u-svg": b"<svg onload=alert(1)></svg>"}


class _Yanit:
    def __init__(self, u):
        self.raw = types.SimpleNamespace(read=lambda n, decode_content=True: VERI[u][:n])

    def raise_for_status(self):
        pass


sys.modules["requests"] = types.SimpleNamespace(get=lambda u, **kw: _Yanit(u))
y = ci.ikon("BTC")
kontrol("PNG indirildi ve kaydedildi", y and y[1] == "image/png" and os.path.exists(y[0]), y)
kontrol("1000PEPE, PEPE logosunu alır (JPEG)", (ci.ikon("1000PEPE") or ("", ""))[1] == "image/jpeg")
kontrol("SVG reddedilir, .yok işaretlenir", ci.ikon("KOTU") is None and os.path.exists(os.path.join(ci.DIZIN, "KOTU.yok")))
kontrol("haritada olmayan: None ve .yok", ci.ikon("YOKCOIN") is None and os.path.exists(os.path.join(ci.DIZIN, "YOKCOIN.yok")))
sys.modules["requests"] = types.SimpleNamespace(get=lambda u, **kw: (_ for _ in ()).throw(AssertionError("ağa çıkmamalı")))
kontrol("ikinci istek diskten (ağsız)", ci.ikon("BTC") is not None)

if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    sys.exit(1)
print("Tüm coin logo testleri geçti.")
