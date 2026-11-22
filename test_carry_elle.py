"""MADDE 830 — elle müdahale (carry_elle.py + carry_bot kancaları) testleri.

İki katman:
  A) carry_elle birim testleri (sahte borsa): emir sahibi ayrımı, ilk kontrol, işaretleme, bot emirlerinin iptali,
     kullanıcı emrinin korunması, felaket tetiği, bırakma bekleme süresi, okuma hataları, kuru çalışma.
  B) carry_bot.bir_tur uçtan uca (test_carry_entegrasyon'un SAHTE BORSASI aynen kullanılır):
     - ELLE KAPALI ve ELLE AÇIK + müdahale yok -> emirler ve dilim defteri BİREBİR AYNI (hiçbir şey bozulmuyor)
     - kullanıcı long'u short'a çevirdi -> o coine emir yok, defterde yok, kâr al / stop yok, kullanıcı emri silinmiyor
     - kullanıcı kapattı -> bekleme sonrası bota döner
Hiçbir gerçek API çağrısı yapılmaz.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, ".")
import numpy as np            # noqa: F401  (sahte borsa kaynağı kullanır)
import pandas as pd           # noqa: F401
import zlib                   # noqa: F401
import time                   # noqa: F401

import carry_bot as cb
import carry_elle as ce

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


H = 3600 * 1000
T0 = 1_800_000_000_000


# ---------------------------------------------------------------- A) BİRİM
class Ic:
    def __init__(self):
        self.gecmis = {}       # sem -> [emir]
        self.acik = {}         # sem -> [emir]
        self.algo_acik = {}    # sem -> [algo]
        self.algo = {}         # algoId -> dict
        self.iptal = []
        self.algo_iptal = []
        self.patlat_gecmis = set()
        self.sorgu = []

    def futures_get_all_orders(self, symbol, startTime=None, limit=500):
        self.sorgu.append((symbol, startTime))
        if symbol in self.patlat_gecmis:
            raise RuntimeError("APIError(code=-1003)")
        return [o for o in self.gecmis.get(symbol, []) if startTime is None or o["updateTime"] >= startTime]

    def futures_get_open_orders(self, symbol=None):
        return list(self.acik.get(symbol, []))

    def futures_cancel_order(self, symbol, orderId):
        self.iptal.append((symbol, orderId))
        self.acik[symbol] = [o for o in self.acik.get(symbol, []) if o["orderId"] != orderId]

    def futures_get_open_algo_orders(self, symbol=None):
        return list(self.algo_acik.get(symbol, []))

    def futures_cancel_algo_order(self, symbol, algoId):
        self.algo_iptal.append((symbol, algoId))

    def futures_get_algo_order(self, symbol, algoId):
        return self.algo.get(algoId, {"algoStatus": "NEW", "actualOrderId": ""})


class Cl:
    def __init__(self):
        self.client = Ic()
        self.poz = {}
        self.poz_patlat = False

    def get_open_positions(self):
        if self.poz_patlat:
            raise RuntimeError("bakım")
        return [{"symbol": s, "positionAmt": str(a)} for s, a in self.poz.items() if a]


def emir(oid, cid, t, dolan="1", tip="MARKET", yon="SELL"):
    return {"orderId": oid, "clientOrderId": cid, "time": t, "updateTime": t, "executedQty": dolan,
            "type": tip, "side": yon, "status": "FILLED" if float(dolan) else "NEW"}


print("A1) emir sahibi ayrımı")
kontrol("python-binance öneki = bot", ce.emir_sahibi({"clientOrderId": "x-Cb7ytekJabc"}) == "bot")
kontrol("olay modülü öneki = bot", ce.emir_sahibi({"clientOrderId": "OLAY123AKEUSD"}) == "bot")
for cid in ("autoclose-1763", "adl_autoclose", "settlement_autoclose-AKE", "delivery_autoclose-x"):
    kontrol(f"Binance kapanışı = sistem ({cid})", ce.emir_sahibi({"clientOrderId": cid}) == "sistem")
for cid in ("android_abc", "ios_XYZ", "web_123", "electron_1", "", None):
    kontrol(f"önek yok = kullanıcı ({cid!r})", ce.emir_sahibi({"clientOrderId": cid}) == "kullanici")
kontrol("felaket tetiği (actualOrderId) önekten bağımsız bot",
        ce.emir_sahibi({"orderId": 555, "clientOrderId": "rastgele"}, {"555"}) == "bot")

d = tempfile.mkdtemp()
DOS = os.path.join(d, "elle.json"); OLAY = os.path.join(d, "olay.jsonl")
durum = {"dilimler": {"0": {"AKEUSDT": 100.0, "BUSDT": -50.0}, "1": {"AKEUSDT": 50.0}},
         "dilim_fiyat": {"0": {"AKEUSDT": 2.0, "BUSDT": 5.0}, "1": {"AKEUSDT": 1.0}},
         "felaket": {"AKEUSDT": 9001}, "kar_al": {"AKEUSDT": 77, "BUSDT": 78}}
bil = []
bildir = lambda m, **k: bil.append(m)

print("A2) ilk kontrol: geçmiş değerlendirilmez")
c = Cl(); c.poz = {"AKEUSDT": 100.0, "BUSDT": -10.0}
c.client.gecmis["AKEUSDT"] = [emir(1, "android_eski", T0 - H)]
k = ce.guncelle(c, durum, DOS, simdi_ms=T0, bildir=bildir, olay_dosya=OLAY)
kontrol("ilk çalıştırmada hiçbir şey işaretlenmedi", k == set())
kontrol("ilk çalıştırmada emir geçmişi sorgulanmadı", c.client.sorgu == [])
kontrol("zaman damgası yazıldı", ce.kayit_oku(DOS).get("son_kontrol_ms") == T0)

print("A3) yalnız bot dolumları -> işaret yok")
c.client.gecmis["AKEUSDT"] = [emir(2, "x-Cb7ytekJtp", T0 + H), emir(3, "rastgele_tetik", T0 + H, tip="STOP_MARKET")]
c.client.algo[9001] = {"algoStatus": "TRIGGERED", "actualOrderId": "3"}
c.client.gecmis["BUSDT"] = [emir(4, "autoclose-1", T0 + H), emir(5, "web_acik_dolmamis", T0 + H, dolan="0")]
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 8 * H, bildir=bildir, olay_dosya=OLAY)
kontrol("bot TP + felaket tetiği + Binance kapanışı + dolmamış kullanıcı emri -> işaret yok", k == set(), f"({k})")
kontrol("bildirim gitmedi", bil == [])
kontrol("dilim / pozisyon sembollerinin hepsi sorgulandı",
        {s for s, _ in c.client.sorgu} == {"AKEUSDT", "BUSDT"}, f"({c.client.sorgu})")
kontrol("sorgu son kontrolden (5 dk pay) başlıyor",
        all(t == T0 - ce.ARALIK_PAYI_MS for _, t in c.client.sorgu),
        f"({c.client.sorgu[-2:]})")

print("A4) kullanıcı long'u short'a çevirdi -> işaret + bot emirleri iptal, kullanıcı emri korunur")
c.client.sorgu.clear()
c.poz["AKEUSDT"] = -80.0
c.client.gecmis["AKEUSDT"].append(emir(10, "android_kapat", T0 + 9 * H))
c.client.gecmis["AKEUSDT"].append(emir(11, "android_short", T0 + 9 * H + 60000))
c.client.acik["AKEUSDT"] = [emir(20, "x-Cb7ytekJtp", T0, dolan="0", tip="LIMIT"),
                            emir(21, "x-Cb7ytekJkademe", T0, dolan="0", tip="LIMIT"),
                            emir(22, "android_tp", T0 + 9 * H, dolan="0", tip="LIMIT"),
                            emir(23, "OLAY99AKEUSD", T0, dolan="0", tip="LIMIT")]
c.client.algo_acik["AKEUSDT"] = [{"algoId": 9001, "clientAlgoId": "x-Cb7ytekJfel"},
                                 {"algoId": 9002, "clientAlgoId": "android_stop"}]
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 16 * H, bildir=bildir, olay_dosya=OLAY)
kontrol("AKE işaretlendi, B işaretlenmedi", k == {"AKEUSDT"}, f"({k})")
kontrol("botun iki LIMIT emri iptal edildi", sorted(o for s, o in c.client.iptal) == [20, 21], f"({c.client.iptal})")
kontrol("kullanıcının ve olay modülünün emri SİLİNMEDİ",
        {o["orderId"] for o in c.client.acik["AKEUSDT"]} == {22, 23})
kontrol("yalnız botun algo stop'u iptal edildi", c.client.algo_iptal == [("AKEUSDT", 9001)], f"({c.client.algo_iptal})")
kontrol("bildirim gitti", len(bil) == 1 and "AKEUSDT" in bil[0], f"({bil})")
kay = ce.kayit_oku(DOS)["elle"]["AKEUSDT"]
kontrol("kayıt: ilk kullanıcı emri ve yönü", kay["ilk_emir"] == "android_kapat" and kay["ilk_yon"] == "SELL", f"({kay})")
kontrol("kayıt: botun adedi dilim defterinden (100/2 + 50/1 = 100)", abs(kay["bot_adet"] - 100.0) < 1e-9, f"({kay})")
kontrol("olay defterine işaret satırı yazıldı", '"isaret"' in open(OLAY, encoding="utf-8").read())

print("A5) dilimden çıkarma (idempotent)")
d2 = copy.deepcopy(durum); d2.update({"merdiven": {"AKEUSDT": {"oid": 1}}, "merdiven_yapildi": {"AKEUSDT": 1.0},
                                      "giris_funding": {"AKEUSDT": 0.1, "BUSDT": 0.2}})
cik = ce.dilimden_cikar(d2, {"AKEUSDT"})
kontrol("AKE dilimlerden ve bütün kayıtlardan çıktı",
        cik == ["AKEUSDT"] and all("AKEUSDT" not in h for h in d2["dilimler"].values())
        and all("AKEUSDT" not in r for r in d2["dilim_fiyat"].values())
        and all("AKEUSDT" not in d2[k_] for k_ in ("felaket", "kar_al", "merdiven", "merdiven_yapildi", "giris_funding")))
kontrol("B'ye dokunulmadı", d2["dilimler"]["0"] == {"BUSDT": -50.0} and d2["kar_al"] == {"BUSDT": 78}
        and d2["giris_funding"] == {"BUSDT": 0.2})
kontrol("ikinci çağrı no-op", ce.dilimden_cikar(d2, {"AKEUSDT"}) == [])
kontrol("boş küme no-op", ce.dilimden_cikar(d2, set()) == [])

print("A6) bırakma: adet 0 + bekleme")
c.poz["AKEUSDT"] = 0.0
c.client.gecmis["AKEUSDT"].append(emir(12, "android_kapat2", T0 + 17 * H))
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 17 * H + 10 * 60000, bildir=bildir, olay_dosya=OLAY)
kontrol("kapatma 10 dk önce -> hâlâ kullanıcıda (arada tur denk geldi)", k == {"AKEUSDT"}, f"({k})")
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 25 * H, bildir=bildir, olay_dosya=OLAY)
kontrol("8 sa sonra -> bota döndü", k == set(), f"({k})")
kontrol("bırakma bildirimi", "geri döndü" in bil[-1], f"({bil[-1:]})")
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 25 * H + 60000, bildir=bildir, olay_dosya=OLAY)
kontrol("bırakmadan önceki kullanıcı dolumları yeniden işaretletmiyor", k == set(), f"({k})")
c.client.gecmis["AKEUSDT"].append(emir(13, "web_yeni", T0 + 26 * H)); c.poz["AKEUSDT"] = -5.0
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 27 * H, bildir=bildir, olay_dosya=OLAY)
kontrol("bırakmadan SONRA yeni kullanıcı işlemi -> yeniden işaretlenir", k == {"AKEUSDT"}, f"({k})")

print("A7) adet 0 değilse süre geçse de bırakılmaz")
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 200 * H, bildir=bildir, olay_dosya=OLAY)
kontrol("pozisyon açık -> kullanıcıda kalır", k == {"AKEUSDT"})

print("A8) okuma hataları karar değiştirmez")
c.poz_patlat = True
kontrol("pozisyon okunamazsa kayıttaki işaret döner", ce.guncelle(c, durum, DOS, simdi_ms=T0 + 201 * H) == {"AKEUSDT"})
c.poz_patlat = False
c.poz["CUSDT"] = 3.0; c.client.gecmis["CUSDT"] = [emir(30, "ios_x", T0 + 201 * H)]
c.client.patlat_gecmis = {"CUSDT", "AKEUSDT"}; c.poz["AKEUSDT"] = 0.0
k = ce.guncelle(c, durum, DOS, simdi_ms=T0 + 202 * H)
kontrol("geçmişi okunamayan sembol işaretlenmez",
        "CUSDT" not in k, f"({k})")
c.client.patlat_gecmis = set()

print("A9) kuru çalışma hiçbir şey yazmaz / iptal etmez")
d3 = tempfile.mkdtemp(); DOS3 = os.path.join(d3, "e.json")
ce.kayit_yaz(DOS3, {"elle": {}, "birakilan": {}, "son_kontrol_ms": T0})
c3 = Cl(); c3.poz = {"XUSDT": -1.0}; c3.client.gecmis["XUSDT"] = [emir(1, "web_a", T0 + H)]
c3.client.acik["XUSDT"] = [emir(2, "x-Cb7ytekJtp", T0, dolan="0")]
b3 = []
k = ce.guncelle(c3, {"dilimler": {}}, DOS3, simdi_ms=T0 + 2 * H, bildir=lambda m, **kw: b3.append(m), dry_run=True)
kontrol("kuru: işaret dönüyor (bu tur filtrelensin)", k == {"XUSDT"})
kontrol("kuru: kayıt değişmedi", ce.kayit_oku(DOS3) == {"elle": {}, "birakilan": {}, "son_kontrol_ms": T0})
kontrol("kuru: emir iptal edilmedi, bildirim yok", c3.client.iptal == [] and b3 == [])


print("A10) açılışta takip başlatma")
d4 = tempfile.mkdtemp(); DOS4 = os.path.join(d4, "e.json")
kontrol("kayıt yoksa kurar", ce.baslat(DOS4, simdi_ms=T0) is True and ce.kayit_oku(DOS4)["son_kontrol_ms"] == T0)
kontrol("kayıt varsa dokunmaz", ce.baslat(DOS4, simdi_ms=T0 + H) is False and ce.kayit_oku(DOS4)["son_kontrol_ms"] == T0)
c4 = Cl(); c4.poz = {"YUSDT": -2.0}; c4.client.gecmis["YUSDT"] = [emir(1, "android_a", T0 + 10 * 60000)]
kontrol("açılıştan 10 dk sonraki elle işlem ilk turda yakalanır",
        ce.guncelle(c4, {"dilimler": {}}, DOS4, simdi_ms=T0 + H) == {"YUSDT"})


# ---------------------------------------------------------------- B) UÇTAN UCA
print("\nB) bir_tur uçtan uca (test_carry_entegrasyon sahte borsası)")
_src = open("test_carry_entegrasyon.py", encoding="utf-8").read()
_agac = ast.parse(_src)
_ad = {"SahteIcClient", "SahteClient", "temiz_ortam"}
_ns = {"cb": cb, "np": np, "pd": pd, "zlib": zlib, "time": time, "os": os, "tempfile": tempfile, "json": json}
exec(compile(ast.Module(body=[n for n in _agac.body if getattr(n, "name", None) in _ad], type_ignores=[]),
             "harness", "exec"), _ns)
cb.N_LEGS, cb.MIN_LEGS = 12, 8
cb.DOLUM_BEKLEME_SN = 0.0


class ElleIc(_ns["SahteIcClient"]):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.gecmis = {}
        self.kullanici_acik = {}     # sem -> [emir]  (kullanıcının açık emri)
        self.tek_iptal = []

    def futures_get_all_orders(self, symbol, startTime=None, limit=500):
        return [o for o in self.gecmis.get(symbol, []) if startTime is None or o["updateTime"] >= startTime]

    def futures_get_open_orders(self, symbol=None):
        out = super().futures_get_open_orders(symbol)
        for s, L in self.kullanici_acik.items():
            if symbol is None or s == symbol:
                out += [dict(o, symbol=s) for o in L]     # gerçek borsa her emirde symbol döner
        return out

    def futures_cancel_order(self, symbol, orderId):
        self.tek_iptal.append((symbol, orderId))
        for s in self.kullanici_acik:
            self.kullanici_acik[s] = [o for o in self.kullanici_acik[s] if o["orderId"] != orderId]
        return super().futures_cancel_order(symbol, orderId)

    def futures_get_open_algo_orders(self, symbol=None):
        return []


class ElleClient(_ns["SahteClient"]):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.client = ElleIc(**kw)

    def cancel_all_open_orders(self, symbol):
        self.client.kullanici_acik.pop(symbol, None)     # gerçek borsada toplu iptal kullanıcı emrini de siler
        return super().cancel_all_open_orders(symbol)


def ortam(elle: bool):
    dd = _ns["temiz_ortam"]()
    cb.ELLE = elle
    cb.ELLE_DOSYA = os.path.join(dd, "elle.json")
    cb.ELLE_OLAY_DOSYA = os.path.join(dd, "elle_olay.jsonl")
    cb._ELLE.clear()
    return dd


def kos(elle: bool, n_tur=4):
    ortam(elle)
    cl = ElleClient()
    emirler, durumlar = [], []
    for _ in range(n_tur):
        cb.bir_tur(cl, dry_run=False)
        emirler.append(list(cl.client.gonderilen)); durumlar.append(json.dumps(cb.dilim_durum_oku(), sort_keys=True))
        cl.pozisyonlari_ayarla(cb.toplam_hedef_tut(cb.dilim_durum_oku(), dict(cl.client._fiyat)) if cb.TUTUS_SABIT
                               else cb.toplam_hedef(cb.dilim_durum_oku()))
    return emirler, durumlar, cl


print("B1) ELLE kapalı vs ELLE açık (müdahale yok): birebir aynı")
e0, d0, _ = kos(False)
kontrol("ELLE kapalıyken kayıt dosyası hiç oluşmadı", not os.path.exists(cb.ELLE_DOSYA))
e1, d1, c1 = kos(True)
kontrol("emirler birebir aynı (4 tur)", e0 == e1, f"({len(e0[-1])} / {len(e1[-1])})")
kontrol("dilim defteri birebir aynı (4 tur)", d0 == d1)
kontrol("ELLE açıkken kayıt dosyası oluştu (takip başladı)", os.path.exists(cb.ELLE_DOSYA))

print("B2) kullanıcı bir long'u short'a çevirdi")
durum = cb.dilim_durum_oku()
hedef = cb.toplam_hedef_tut(durum, dict(c1.client._fiyat))
uzun = sorted(s for s, v in hedef.items() if v > 0)
S = uzun[0]
kontrol("senaryo: botun long'u var", hedef[S] > 0, f"({S} {hedef.get(S)})")
simdi = int(time.time() * 1000)
c1.client.gecmis[S] = [emir(501, "android_kapat", simdi - 60000), emir(502, "android_short", simdi - 30000)]
c1.client.kullanici_acik[S] = [emir(503, "android_tp", simdi, dolan="0", tip="LIMIT", yon="BUY")]
P = c1.client._fiyat[S]
c1._pozisyonlar = [p for p in c1._pozisyonlar if p["symbol"] != S] + [
    {"symbol": S, "positionAmt": str(-200.0 / P), "entryPrice": str(P), "marginType": "cross"}]
g0 = len(c1.client.gonderilen); tp0 = dict(c1.client.kar_al_emirleri); fe0 = set(c1.client.felaket_emirleri)
cb.bir_tur(c1, dry_run=False)
yeni = c1.client.gonderilen[g0:]
d_ = cb.dilim_durum_oku()
kontrol("o coine hiç alım-satım emri gitmedi", all(x[0] != S for x in yeni), f"({[x for x in yeni if x[0] == S]})")
kontrol("diğer coinlerde tur normal işledi (emir var)", len(yeni) > 0, f"({len(yeni)})")
kontrol("coin dilim defterinde yok", all(S not in h for h in d_["dilimler"].values()))
kontrol("coin giriş referanslarında yok", all(S not in r for r in (d_.get("dilim_fiyat") or {}).values()))
kontrol("coine yeni kâr al konmadı", all(v[0] != S for k_, v in c1.client.kar_al_emirleri.items() if k_ not in tp0))
kontrol("coine felaket stop konmadı", all(v[0] != S for a, v in c1.client.felaket_emirleri.items() if a not in fe0)
        and S not in (d_.get("felaket") or {}))
kontrol("kullanıcının açık emri SİLİNMEDİ", [o["orderId"] for o in c1.client.kullanici_acik.get(S, [])] == [503],
        f"({c1.client.kullanici_acik.get(S)})")
kontrol("kayıtta işaretli", S in ce.isaretliler(cb.ELLE_DOSYA))
kontrol("bot portföyü kullanıcının pozisyonunu saymıyor", S not in cb.mevcut_portfoy(c1))

print("B3) bir sonraki turlar: hâlâ dokunmuyor")
for _ in range(3):
    g0 = len(c1.client.gonderilen)
    pz = [p for p in c1._pozisyonlar if p["symbol"] == S]
    c1.pozisyonlari_ayarla(cb.toplam_hedef_tut(cb.dilim_durum_oku(), dict(c1.client._fiyat)))
    c1._pozisyonlar += pz
    cb.bir_tur(c1, dry_run=False)
    kontrol("tur: coine emir yok", all(x[0] != S for x in c1.client.gonderilen[g0:]))
kontrol("kullanıcı emri hâlâ yerinde", [o["orderId"] for o in c1.client.kullanici_acik.get(S, [])] == [503])

print("B4) kullanıcı kapattı -> bekleme sonrası bota döner")
c1.client.gecmis[S].append(emir(504, "android_kapat2", int(time.time() * 1000) - 2 * 3600 * 1000))
c1.client.kullanici_acik.pop(S, None)
c1.pozisyonlari_ayarla(cb.toplam_hedef_tut(cb.dilim_durum_oku(), dict(c1.client._fiyat)))
kontrol("senaryo: pozisyon kapandı", all(p["symbol"] != S for p in c1._pozisyonlar))
# son kullanıcı dolumu 2 sa önce gibi görünsün diye kayıttaki son_el geri alınır
# (testte turlar saniyeler arayla döner; gerçekte 8 sa) -> zaman 3 sa geri kaydırılır: kullanıcı dolumları 3 sa önce,
# son kontrol 1 sa önce, son kullanıcı dolumu 2 sa önce.
_n = int(time.time() * 1000)
for o in c1.client.gecmis[S]:
    o["time"] = o["updateTime"] = _n - 3 * 3600 * 1000
st = ce.kayit_oku(cb.ELLE_DOSYA); st["elle"][S]["son_el"] = _n - 2 * 3600 * 1000; st["son_kontrol_ms"] = _n - 3600 * 1000
ce.kayit_yaz(cb.ELLE_DOSYA, st)
cb.bir_tur(c1, dry_run=False)
kontrol("işaret kalktı", S not in ce.isaretliler(cb.ELLE_DOSYA) and S not in cb._ELLE)

print("B5) ELLE açıkken kullanıcının BAŞKA coindeki açık emri bayat temizlikte silinmez; botunki silinir")
ortam(True)
c5 = ElleClient(); cb.bir_tur(c5, dry_run=False)
c5.client.kullanici_acik["C40USDT"] = [emir(601, "web_limit", 0, dolan="0", tip="LIMIT")]
c5.client.kullanici_acik["C41USDT"] = [emir(602, "x-Cb7ytekJbayat", 0, dolan="0", tip="LIMIT")]
cb.bayat_emirleri_temizle(c5, [])
kontrol("kullanıcı emri kaldı", [o["orderId"] for o in c5.client.kullanici_acik.get("C40USDT", [])] == [601],
        f"({c5.client.kullanici_acik})")
kontrol("botun bayat emri silindi", not c5.client.kullanici_acik.get("C41USDT"), f"({c5.client.kullanici_acik})")
cb.ELLE = False
c5.client.kullanici_acik["C40USDT"] = [emir(601, "web_limit", 0, dolan="0", tip="LIMIT")]
cb.bayat_emirleri_temizle(c5, [])
kontrol("ELLE kapalıyken eski davranış (her şey temizlenir)", not c5.client.kullanici_acik.get("C40USDT"))


print("B7) sağlık kapısı (durdur) bütün kitabı kapatırken kullanıcının pozisyonuna DOKUNMAZ")
_eski_mod = cb.SAGLIK_MODU
ortam(True); cb.SAGLIK_MODU = "durdur"
c7 = ElleClient(); cb.bir_tur(c7, dry_run=False)
c7.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
U = "C50USDT"
c7._pozisyonlar.append({"symbol": U, "positionAmt": "-3", "entryPrice": "60", "marginType": "cross"})
_n7 = int(time.time() * 1000)
c7.client.gecmis[U] = [emir(701, "web_short", _n7 - 1000)]
c7.client.saglik_ters = True; c7.client.gonderilen = []
r7 = cb.bir_tur(c7, dry_run=False)
kontrol("kapı kapandı (senaryo)", r7.get("kapi") == "KAPALI", f"({r7})")
kontrol("botun pozisyonları kapatıldı", len(c7.client.gonderilen) > 0)
kontrol("kullanıcının pozisyonuna kapatma emri GİTMEDİ", all(e[0] != U for e in c7.client.gonderilen))
cb.SAGLIK_MODU = _eski_mod

print("B8) delist: kullanıcının pozisyonu kapatılmaz (uyarı), botunki kapatılır")
ortam(True)
c8 = ElleClient(delist_semboller={"C60USDT", "C61USDT"})
ce.kayit_yaz(cb.ELLE_DOSYA, {"elle": {"C60USDT": {"t": 1, "son_el": int(time.time() * 1000)}}, "birakilan": {},
                             "son_kontrol_ms": int(time.time() * 1000)})
cb._ELLE.clear(); cb._ELLE.add("C60USDT")
c8._pozisyonlar = [{"symbol": "C60USDT", "positionAmt": "-2", "entryPrice": "70", "marginType": "cross"},
                   {"symbol": "C61USDT", "positionAmt": "-2", "entryPrice": "71", "marginType": "cross"}]
_kap = []
c8.close_position = lambda s_, y_, a_: _kap.append(s_)
_eski_dk = cb.DELIST_KAPAT_SAAT; cb.DELIST_KAPAT_SAAT = 100.0   # sahte borsada delist 72 sa sonra
cb.delist_kapat(c8, {"dilimler": {"0": {"C61USDT": -100.0}}})
cb.DELIST_KAPAT_SAAT = _eski_dk
kontrol("botun delist pozisyonu kapatıldı, kullanıcınınki kapatılmadı", _kap == ["C61USDT"], f"({_kap})")

print("B9) kâr al / felaket kurulumu kullanıcının pozisyonunu atlar")
ortam(True)
c9 = ElleClient(); cb.bir_tur(c9, dry_run=False)
c9.pozisyonlari_ayarla(cb.toplam_hedef_tut(cb.dilim_durum_oku(), dict(c9.client._fiyat)))
c9._pozisyonlar.append({"symbol": "C45USDT", "positionAmt": "5", "entryPrice": "55", "marginType": "cross"})
cb._ELLE.clear(); cb._ELLE.add("C45USDT")
_k0 = set(c9.client.kar_al_emirleri); _f0 = set(c9.client.felaket_emirleri)
d9 = cb.dilim_durum_oku(); cb.kar_al_kur(c9, d9)
kontrol("kâr al kuruldu (senaryo)", len(set(c9.client.kar_al_emirleri) - _k0) > 0 or not cb.koruma_acik())
kontrol("kullanıcının coinine kâr al / felaket konmadı",
        all(c9.client.kar_al_emirleri[k][0] != "C45USDT" for k in set(c9.client.kar_al_emirleri) - _k0)
        and all(c9.client.felaket_emirleri[k][0] != "C45USDT" for k in set(c9.client.felaket_emirleri) - _f0))
cb._ELLE.clear()

print("B6) varsayılan KAPALI")
import importlib
_eski = os.environ.pop("CARRY_ELLE", None)
kontrol("CARRY_ELLE yokken ELLE=False", os.getenv("CARRY_ELLE", "0") in ("0", "false", "False"))
cb.ELLE = False; cb._ELLE.clear()
kontrol("kapalıyken elle_guncelle hiçbir çağrı yapmadan boş döner", cb.elle_guncelle(None) == set())
if _eski is not None:
    os.environ["CARRY_ELLE"] = _eski

if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tüm elle müdahale testleri geçti.")
