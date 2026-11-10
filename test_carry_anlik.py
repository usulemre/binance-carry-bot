#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 728 testleri: anlık pozisyon görüntüsü SALT OKUR, doğru biçimde ve tek adımda (atomik) yazar."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

os.environ["CARRY_ANLIK_STOP"] = "0"   # madde 753: yaz() testlerinde gerçek evren ölçümü yok
import carry_anlik
from datetime import datetime, timezone


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

# MADDE 744: gerçek Binance oranlarıyla funding (yalnız demo)
H = 3600 * 1000
class _Oran:
    def __init__(s, oranlar, hata=False):
        s.oranlar, s.hata, s.cagri = oranlar, hata, []   # oranlar: sembol -> [(ms, oran, işaret)]
    def futures_funding_rate(s, symbol, startTime, endTime, limit):
        s.cagri.append(symbol)
        if s.hata:
            raise RuntimeError("ağ")
        return [{"fundingTime": t, "fundingRate": str(r), "markPrice": str(m)} for t, r, m in s.oranlar.get(symbol, [])
                if startTime <= t <= endTime][:limit]
class _DemoC(_Oran):
    def __init__(s, oranlar, gelir):
        super().__init__(oranlar); s.gelir = gelir
    def futures_income_history(s, startTime, endTime, limit, incomeType=None):
        return [g for g in s.gelir if incomeType in (None, g["incomeType"]) and startTime <= g["time"] <= endTime][:limit]
class _GF:
    def __init__(s, demo, gercek, veri_gercek=True):
        s.client, s.veri, s.veri_gercek = demo, gercek, veri_gercek
_b = 1_000 * H   # başlangıç
# demo: ESPORTS short, demo oranı −%0,72 -> short ÖDER (−0,126 $ = −(−17,5 $) × −0,0072)
_demo = _DemoC({"EUSDT": [(_b + 4 * H, -0.0072, 0.011)]},
               [{"incomeType": "FUNDING_FEE", "symbol": "EUSDT", "income": "-0.126", "time": _b + 4 * H}])
# gerçek: aynı anda +%0,08 (short ALIR), ayrıca demoda olmayan +8 sa'te +%0,05
_ger = _Oran({"EUSDT": [(_b + 4 * H, 0.0008, 0.011), (_b + 8 * H, 0.0005, 0.010)],
              "XUSDT": [(_b + 10 * H, 0.001, 2.0)]})
_gfd = os.path.join(tmp, "defter", "gercek_funding.json")
kontrol("canlıda (veri_gercek yok) hesaplanmaz", carry_anlik.gercek_funding(_GF(_demo, _ger, False), _b // 1000, (_b + 9 * H) / 1000, {}, _gfd) is None
        and not os.path.exists(_gfd))
g = carry_anlik.gercek_funding(_GF(_demo, _ger), _b // 1000, (_b + 9 * H) / 1000, {}, _gfd)
# büyüklük = −(−0,126) / −0,0072 = −17,5 $ (short); gerçek: −(−17,5) × 0,0008 + −(−17,5) × 0,0005 = +0,01400 + 0,00875
kontrol("tohum: demo kaydından büyüklük, gerçek oranlar (8 sa içindeki gerçek anlar dahil)", abs(g["toplam"] - (17.5 * 0.0008 + 17.5 * 0.0005)) < 1e-6, g)
_poz = {"XUSDT": {"miktar": -5.0, "isaret": 2.0}, "EUSDT": {"miktar": -1590.0, "isaret": 0.011}}
g2 = carry_anlik.gercek_funding(_GF(_demo, _ger), _b // 1000, (_b + 11 * H) / 1000, _poz, _gfd)
kontrol("artımlı: son çalışmadan beri gerçek funding anı × şu anki pozisyon × o anın işaret fiyatı",
        abs(g2["toplam"] - (g["toplam"] + 5.0 * 2.0 * 0.001)) < 1e-6, g2)
_once = json.load(open(_gfd))
try:
    carry_anlik.gercek_funding(_GF(_demo, _Oran({}, hata=True)), _b // 1000, (_b + 12 * H) / 1000, _poz, _gfd); _ok = False
except RuntimeError:
    _ok = True
kontrol("gerçek borsa okunamazsa istisna, dosya DEĞİŞMEZ", _ok and json.load(open(_gfd)) == _once)
g3 = carry_anlik.gercek_funding(_GF(_demo, _ger), _b // 1000, (_b + 11 * H) / 1000 + 60, _poz, _gfd)
kontrol("aynı funding anı iki kez sayılmaz", abs(g3["toplam"] - g2["toplam"]) < 1e-12)
_gk = datetime.fromtimestamp((_b + 10 * H) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
kontrol("madde 748: artımlı funding UTC GÜN kırılımında (tekrar sayılmaz)", abs(g3["gun"].get(_gk, 0) - 5.0 * 2.0 * 0.001) < 1e-9 and sum(g3["gun"].values()) == g3["gun"][_gk], g3.get("gun"))
class _S3(_Sahte):
    def __init__(s):
        super().__init__(); s.client = _DemoC({}, _k); s.veri = _Oran({}); s.veri_gercek = True
    def get_open_positions(s):
        return [{"symbol": "AUSDT", "positionAmt": "10", "entryPrice": "2.0", "markPrice": "2.1", "unRealizedProfit": "1.0"}]
k = carry_anlik.yaz(_S3(), simdi=1003.0, dosya=dosya, defter_dosya=_df)
kontrol("yaz(): anlık dosyada gerçek-oran funding (başlangıç = defterin ilk satırı)", k.get("gercek_funding", {}).get("bas") == 1000, k.get("gercek_funding"))
k = carry_anlik.yaz(c, simdi=1004.0, dosya=dosya, defter_dosya=_df)
kontrol("yaz(): canlı istemcide gerçek-oran satırı yok", "gercek_funding" not in k)

# MADDE 745: pozisyon geçmişi yalnız değişince yazılır, kapanan coin 0 ile işaretlenir, eski satırlar atılır
_pg = os.path.join(tempfile.mkdtemp(), "anlik_poz.json")
carry_anlik.poz_gecmis_ekle(_pg, 1000, {"AUSDT": {"miktar": 10.0, "giris": 1.0}})
carry_anlik.poz_gecmis_ekle(_pg, 1300, {"AUSDT": {"miktar": 10.0, "giris": 1.0}})
carry_anlik.poz_gecmis_ekle(_pg, 1600, {"AUSDT": {"miktar": 15.0, "giris": 0.9}, "BUSDT": {"miktar": -3.0, "giris": 2.0}})
_g = carry_anlik.poz_gecmis_ekle(_pg, 1900, {"BUSDT": {"miktar": -3.0, "giris": 2.0}})["s"]
kontrol("poz geçmişi: değişmeyen görüntü yazılmaz", [x[0] for x in _g["AUSDT"]] == [1000, 1600, 1900], _g)
kontrol("poz geçmişi: kapanış [t, 0, 0]", _g["AUSDT"][-1] == [1900, 0.0, 0.0] and _g["BUSDT"] == [[1600, -3.0, 2.0]])
_g = carry_anlik.poz_gecmis_ekle(_pg, 1900 + 15 * 86400, {"BUSDT": {"miktar": -3.0, "giris": 2.0}}, sakla_gun=14)["s"]
kontrol("poz geçmişi: eski kapanmış coin atılır, açığın son durumu kalır", "AUSDT" not in _g and _g["BUSDT"] == [[1600, -3.0, 2.0]], _g)

# MADDE 747: gerçek borsa funding kaydını GEÇ yayınlarsa kaçmasın, iki kez sayılmasın, açılmadan önceki ödeme sayılmasın
_gf7 = os.path.join(tmp, "defter", "gf7.json")
_b7 = 2_000 * H
_or7 = _Oran({})
_d7 = _DemoC({}, [])
_p7 = {"HUSDT": {"miktar": 1000.0, "isaret": 1.0}}
carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + 600_000) / 1000, {}, _gf7)              # tohum (boş)
carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + H - 300_000) / 1000, _p7, _gf7)         # HUSDT açıldı (ödeme öncesi)
g = carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + H + 40_000) / 1000, _p7, _gf7)      # ödeme anı geçti, kayıt YOK
kontrol("kayıt henüz yayınlanmadı: sayılmaz", abs(g["toplam"]) < 1e-12, g)
_or7.oranlar["HUSDT"] = [(_b7 + H, -0.004, 1.0)]                                                       # kayıt GEÇ yayınlandı
g = carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + H + 300_000) / 1000, _p7, _gf7)
kontrol("geç yayınlanan ödeme sonraki çalışmada sayılır", abs(g["toplam"] - 4.0) < 1e-9, g)
g = carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + H + 600_000) / 1000, _p7, _gf7)
kontrol("aynı ödeme iki kez sayılmaz (örtüşme penceresinde)", abs(g["toplam"] - 4.0) < 1e-9, g)
_or7.oranlar["YUSDT"] = [(_b7 + H, 0.01, 1.0)]                                                         # yeni coin: ödeme açılmadan önce
g = carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + H + 900_000) / 1000, {**_p7, "YUSDT": {"miktar": -500.0, "isaret": 1.0}}, _gf7)
kontrol("yeni açılan coinin açılmadan önceki ödemesi sayılmaz", abs(g["toplam"] - 4.0) < 1e-9, g)
g = carry_anlik.gercek_funding(_GF(_d7, _or7), _b7 // 1000, (_b7 + H + 1_200_000) / 1000, {"YUSDT": {"miktar": -500.0, "isaret": 1.0}}, _gf7)
kontrol("kapanan coinin kaydı silinir", "HUSDT" not in g["sayilan"] and g["poz"] == ["YUSDT"], g)

# MADDE 748: demo hesabın sıradaki funding'i (yalnız o saatte ödeyenler, demo oranıyla)
class _PI:
    def __init__(s, satir): s.satir = satir
    def futures_mark_price(s): return s.satir
_t0 = 1_800_000_000
_pi = _PI([{"symbol": "HUSDT", "markPrice": "0.5", "lastFundingRate": "-0.004", "nextFundingTime": (_t0 + 3600) * 1000},
           {"symbol": "CUSDT", "markPrice": "2", "lastFundingRate": "0.001", "nextFundingTime": (_t0 + 7200) * 1000},
           {"symbol": "DUSDT", "markPrice": "1", "lastFundingRate": "0.002", "nextFundingTime": (_t0 + 3600) * 1000 + 5}])
_pz = {"HUSDT": {"miktar": 100.0, "isaret": 0.5}, "CUSDT": {"miktar": -10.0, "isaret": 2.0}, "DUSDT": {"miktar": -50.0, "isaret": 1.0}}
d = carry_anlik.demo_funding(_GF(_pi, _Oran({})), _pz, _t0)
kontrol("demo funding: en yakın saat, yalnız o saatte ödeyenler, demo oranı", d["T"] == _t0 + 3600 and d["n"] == 2
        and abs(d["tahmin"] - (-100 * 0.5 * -0.004 + 50 * 1 * 0.002)) < 1e-9, d)
kontrol("demo funding: canlıda None", carry_anlik.demo_funding(_GF(_pi, _Oran({}), False), _pz, _t0) is None)
kontrol("demo funding: pozisyon yoksa None", carry_anlik.demo_funding(_GF(_pi, _Oran({})), {}, _t0) is None)

# MADDE 749: funding ödemeleri olaylar için
_fo = os.path.join(tmp, "defter", "fo.json")
_t9 = 1_800_000_000
d = carry_anlik.funding_olay_ekle(_fo, _t9, [(_t9 * 1000, "AUSDT", 0.1), (_t9 * 1000 + 300, "BUSDT", -0.05)], [(_t9 * 1000, "AUSDT", 0.2)])
_k9 = str(_t9 * 1000 // 60000 * 60000)
kontrol("funding olayı: aynı dakika tek olay, demo ve gerçek ayrı", d["d"][_k9] == {"AUSDT": 0.1, "BUSDT": -0.05} and d["g"][_k9] == {"AUSDT": 0.2}, d)
d = carry_anlik.funding_olay_ekle(_fo, _t9 + 15 * 86400, [((_t9 + 15 * 86400) * 1000, "AUSDT", 0.3)], [])
kontrol("funding olayı: 14 günden eskiler atılır", _k9 not in d["d"] and len(d["d"]) == 1, d)
b = carry_anlik.gelir_birikim(_G([{"tranId": 9, "incomeType": "FUNDING_FEE", "symbol": "A", "income": "0.5", "time": 7_000_500}]), 7000, 7001.0, os.path.join(tmp, "b9.json"))
kontrol("gelir birikimi yeni funding kayıtlarını döndürür (dosyaya yazmaz)", b["_yeni_funding"] == [(7_000_500, "A", 0.5)]
        and "_yeni_funding" not in json.load(open(os.path.join(tmp, "b9.json"))), b)

# MADDE 753: coin bazında gelir birikimi (+ eski dosyaya bir kez geçmiş kurulumu) ve koşullu stop durumu
_k3 = [{"tranId": 1, "incomeType": "REALIZED_PNL", "symbol": "A", "income": "2", "time": 8_000_100},
       {"tranId": 2, "incomeType": "FUNDING_FEE", "symbol": "A", "income": "0.5", "time": 8_000_200},
       {"tranId": 3, "incomeType": "COMMISSION", "symbol": "B", "income": "-0.1", "time": 8_000_300}]
_b3 = os.path.join(tmp, "b753.json")
b = carry_anlik.gelir_birikim(_G(_k3), 8000, 8001.0, _b3)
kontrol("coin kırılımı: tür başına doğru", b["coin"] == {"A": {"REALIZED_PNL": 2.0, "FUNDING_FEE": 0.5}, "B": {"COMMISSION": -0.1}}, b["coin"])
_eski = json.load(open(_b3)); _eski.pop("coin"); json.dump(_eski, open(_b3, "w"))   # coin alanı olmayan eski dosya
_k3.append({"tranId": 4, "incomeType": "REALIZED_PNL", "symbol": "B", "income": "-1", "time": 8_001_500})
b = carry_anlik.gelir_birikim(_G(_k3), 8000, 8002.0, _b3)
kontrol("eski dosya: geçmiş bir kez kurulur, yeni kayıt ÇİFT sayılmaz",
        b["coin"] == {"A": {"REALIZED_PNL": 2.0, "FUNDING_FEE": 0.5}, "B": {"COMMISSION": -0.1, "REALIZED_PNL": -1.0}}
        and b["toplam"]["REALIZED_PNL"] == 1.0, b)
_ev = {f"S{i}": -0.01 * i for i in range(11)}; _ev.update({"AKE": -0.42, "ZEC": -0.12, "YOK": None})
_sd = carry_anlik.stop_hesapla(list(_ev), ["AKE", "ZEC", "YOK"], _ev.get, 0.45, 0.03)
kontrol("stop: piyasa medyanı (13 coin) ve şart", _sd["medyan"] == -0.06 and _sd["n"] == 13 and _sd["piyasa_sart"] is True, _sd)
kontrol("stop: long başına 24 sa (okunamayan yok)", _sd["coin"] == {"AKE": -0.42, "ZEC": -0.12}, _sd)
_sd2 = carry_anlik.stop_hesapla(["A", "B"], [], {"A": -0.5, "B": -0.5}.get, 0.45, 0.03)
kontrol("stop: 10 coinden az = medyan yok (bot da ölçmez)", _sd2["medyan"] is None and _sd2["piyasa_sart"] is False, _sd2)
_sf = os.path.join(tmp, "stop753.json")
json.dump({"saat": 10, "longlar": ["AKEUSDT"], "coin": {"AKEUSDT": -0.4}}, open(_sf, "w"))
kontrol("stop: aynı saat + aynı long seti = önbellek (borsa çağrısı yok)",
        carry_anlik.stop_durum(None, {"AKEUSDT": {"yon": "L"}, "XUSDT": {"yon": "S"}}, 10 * 3600 + 5, _sf)["coin"] == {"AKEUSDT": -0.4})

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
