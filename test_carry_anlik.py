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

# MADDE 733: başlangıçtan beri gelir birikimi (artımlı, tekil)
class _G:
    def __init__(s, kayitlar, hata=False):
        s.kayitlar, s.hata, s.cagri = kayitlar, hata, []
        g = s
        class _C:
            def futures_income_history(c, startTime, endTime, limit):
                g.cagri.append(startTime)
                if g.hata:
                    raise RuntimeError("ağ")
                r = [k for k in g.kayitlar if startTime <= k["time"] <= endTime]
                return sorted(r, key=lambda k: k["time"])[:limit]
        s.client = _C()

_bd = os.path.join(tmp, "defter", "gelir_birikim.json")
_k = [{"tranId": 1, "incomeType": "FUNDING_FEE", "symbol": "A", "income": "0.5", "time": 1_000_500},
      {"tranId": 2, "incomeType": "COMMISSION", "symbol": "A", "income": "-0.1", "time": 1_000_600},
      {"tranId": 0, "incomeType": "REALIZED_PNL", "symbol": "B", "income": "9", "time": 999_000}]   # başlangıçtan ÖNCE
_g = _G(_k)
b = carry_anlik.gelir_birikim(_g, 1000, 1001.0, _bd)
kontrol("başlangıç öncesi sayılmaz, toplamlar doğru", b["toplam"] == {"FUNDING_FEE": 0.5, "COMMISSION": -0.1}, b["toplam"])
_k.append({"tranId": 3, "incomeType": "FUNDING_FEE", "symbol": "A", "income": "0.25", "time": 1_001_200})
b = carry_anlik.gelir_birikim(_g, 1000, 1002.0, _bd)
kontrol("örtüşen pencere ÇİFT saymaz, yeni kayıt eklenir", b["toplam"] == {"FUNDING_FEE": 0.75, "COMMISSION": -0.1}, b["toplam"])
_k.append({"tranId": 4, "incomeType": "COMMISSION", "symbol": "C", "income": "-0.05", "time": 1_001_900})   # geç düşen kayıt
b = carry_anlik.gelir_birikim(_g, 1000, 1003.0, _bd)
kontrol("geç düşen kayıt (örtüşme içinde) yakalanır", abs(b["toplam"]["COMMISSION"] + 0.15) < 1e-9, b["toplam"])
_once = json.load(open(_bd))
try:
    carry_anlik.gelir_birikim(_G(_k, hata=True), 1000, 1004.0, _bd); _h_ok = False
except RuntimeError:
    _h_ok = True
kontrol("borsa okunamazsa istisna, birikim DEĞİŞMEZ", _h_ok and json.load(open(_bd)) == _once)
b = carry_anlik.gelir_birikim(_g, 2000, 2001.0, _bd)
kontrol("başlangıç değişirse sıfırdan", b["toplam"] == {} and b["bas_ms"] == 2_000_000, b)
_cok = [{"tranId": i, "incomeType": "FUNDING_FEE", "symbol": "A", "income": "0.01", "time": 5_000_000 + i} for i in range(2500)]
b = carry_anlik.gelir_birikim(_G(_cok), 5000, 6000.0, os.path.join(tmp, "b2.json"))
kontrol("1000'den fazla kayıt sayfalanır", abs(b["toplam"]["FUNDING_FEE"] - 25.0) < 1e-6, b["toplam"])
# yaz(): defterin ilk satırı başlangıç
_df = os.path.join(tmp, "defter", "gunluk.jsonl")
open(_df, "w").write(json.dumps({"tarih": "x", "zaman": 1000}) + "\n" + json.dumps({"tarih": "y", "zaman": 9999}) + "\n")
class _S2(_Sahte):
    def __init__(s):
        super().__init__(); s.client = _g.client
_g.kayitlar = _k
k = carry_anlik.yaz(_S2(), simdi=1003.0, dosya=dosya, defter_dosya=_df)
kontrol("anlık dosyada döküm (başlangıç = defterin ilk satırı)", k["gelir_bas"]["bas"] == 1000 and k["gelir_bas"]["FUNDING_FEE"] == 0.75, k.get("gelir_bas"))
k = carry_anlik.yaz(c, simdi=1003.0, dosya=dosya, defter_dosya=os.path.join(tmp, "yok.jsonl"))
kontrol("defter yoksa döküm yok, anlık yine yazılır", "gelir_bas" not in k and k["pozisyonlar"])

# MADDE 742: gün içi kitap noktaları (panelin "bugün" eğrisi)
_gd = os.path.join(tmp, "defter", "anlik_gun.json")
_gb = 1_794_009_600   # 2026-11-07 00:00 UTC
carry_anlik.gun_egri_ekle(_gd, _gb - 200, 5000.0)                     # önceki günün son noktası (gün başına 200 sn)
d = carry_anlik.gun_egri_ekle(_gd, _gb + 100, 5002.0)
kontrol("gün değişince önceki günün son noktası açılış olur", d == {"gun": "2026-11-07", "nok": [[_gb, 5000.0], [_gb + 100, 5002.0]]}, d)
d = carry_anlik.gun_egri_ekle(_gd, _gb + 400, 5003.25)
kontrol("aynı gün nokta eklenir", d["nok"][-1] == [_gb + 400, 5003.25] and len(d["nok"]) == 3)
d = carry_anlik.gun_egri_ekle(_gd, _gb + 86400 + 3 * 3600, 5010.0)   # bir sonraki gün, 3 sa sonra (sunucu kapalıydı)
kontrol("eski nokta gün başından uzaksa açılış taşınmaz", d == {"gun": "2026-11-08", "nok": [[_gb + 86400 + 3 * 3600, 5010.0]]}, d)
open(_gd, "w").write("{bozuk")
kontrol("bozuk dosya: yeniden başlar", carry_anlik.gun_egri_ekle(_gd, _gb + 50, 1.0)["nok"] == [[_gb + 50, 1.0]])
for i in range(500):
    d = carry_anlik.gun_egri_ekle(_gd, _gb + 60 + i, 1.0)
kontrol("nokta sayısı sınırlı", len(d["nok"]) == 400)
os.remove(_gd)
k = carry_anlik.yaz(_S2(), simdi=1003.0, dosya=dosya, defter_dosya=_df)
_g1 = json.load(open(_gd))
kontrol("yaz(): gün noktası = özkaynak − transfer", _g1["nok"][-1] == [1003, 5000.0], _g1)
os.remove(_gd)
k = carry_anlik.yaz(c, simdi=1004.0, dosya=dosya, defter_dosya=os.path.join(tmp, "yok.jsonl"))
kontrol("transfer bilinmiyorsa (döküm yok) gün noktası YAZILMAZ", not os.path.exists(_gd))

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
