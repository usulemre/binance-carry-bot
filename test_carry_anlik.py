#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 728 testleri: anlık pozisyon görüntüsü SALT OKUR, doğru biçimde ve tek adımda (atomik) yazar."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

import carry_anlik


class _Sahte:
    """Yalnız okuma çağrıları; emir çağrısı gelirse test DÜŞER."""
    def __init__(s):
        s.emir = []
        class _C:
            def __getattr__(c, ad):
                if any(x in ad for x in ("create", "cancel", "change", "order")):
                    s.emir.append(ad)
                raise AttributeError(ad)
        s.client = _C()
    def get_open_positions(s):
        return [{"symbol": "AUSDT", "positionAmt": "10", "entryPrice": "2.0", "markPrice": "2.1", "unRealizedProfit": "1.0"},
                {"symbol": "BUSDT", "positionAmt": "-4", "entryPrice": "5.0", "markPrice": "5.5", "unRealizedProfit": "-2.0"},
                {"symbol": "CUSDT", "positionAmt": "0", "entryPrice": "0", "markPrice": "1", "unRealizedProfit": "0"}]
    def get_account_equity_usd(s):
        return 5000.0


tmp = tempfile.mkdtemp(); dosya = os.path.join(tmp, "defter", "anlik.json")
os.environ["CARRY_SERMAYE_OLCEK"] = "0.4"
c = _Sahte()
k = carry_anlik.yaz(c, simdi=1_800_000_000, dosya=dosya)
d = json.load(open(dosya, encoding="utf-8"))
kontrol("dosya yazıldı, dönen kayıtla aynı", d == k)
kontrol("boş pozisyon atlandı", sorted(d["pozisyonlar"]) == ["AUSDT", "BUSDT"], list(d["pozisyonlar"]))
kontrol("long kâr %: +5", d["pozisyonlar"]["AUSDT"]["kar_yuzde"] == 5.0 and d["pozisyonlar"]["AUSDT"]["yon"] == "L")
kontrol("short kâr %: fiyat yükselince −10", d["pozisyonlar"]["BUSDT"]["kar_yuzde"] == -10.0 and d["pozisyonlar"]["BUSDT"]["yon"] == "S")
kontrol("gerçekleşmemiş toplam", d["gerceklesmemis_top"] == -1.0, d["gerceklesmemis_top"])
kontrol("kitap ölçekli (5000 × 0,4)", d["kitap"] == 2000.0 and d["ozkaynak"] == 5000.0)
kontrol("zaman yazıldı", d["zaman"] == 1_800_000_000)
kontrol("geçici dosya kalmadı (atomik)", not os.path.exists(dosya + ".tmp"))
kontrol("HİÇ emir çağrısı yok", c.emir == [], c.emir)
print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
