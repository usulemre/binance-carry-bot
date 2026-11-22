# -*- coding: utf-8 -*-
"""MADDE 849 testleri: elle K/Z botun muhasebesinden ayrılır (carry_elle_kz + bot sermayesi + panel dökümü)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carry_elle_kz as K

_h = 0


def kontrol(ad, kosul):
    global _h
    print(("  OK  " if kosul else "  HATA ") + ad)
    if not kosul:
        _h += 1


def yakin(a, b, tol=1e-6):
    return a is not None and abs(a - b) <= tol


class Ic:
    def __init__(self):
        self.trades, self.orders, self.income = {}, {}, {}
        self.cagri = 0

    def futures_account_trades(self, symbol, startTime=0, endTime=None, limit=500):
        self.cagri += 1
        return [t for t in self.trades.get(symbol, []) if t["time"] >= startTime and (endTime is None or t["time"] <= endTime)][:limit]

    def futures_get_all_orders(self, symbol, startTime=0, limit=500):
        return [o for o in self.orders.get(symbol, []) if o["time"] >= startTime][:limit]

    def futures_income_history(self, symbol=None, incomeType=None, startTime=0, endTime=None, limit=1000):
        return [x for x in self.income.get(symbol, []) if x["time"] >= startTime and (endTime is None or x["time"] <= endTime)]


class Istemci:
    def __init__(self):
        self.client = Ic(); self.poz = {}

    def get_open_positions(self):
        return [{"symbol": s, "positionAmt": str(a), "unRealizedProfit": str(u), "markPrice": str(m), "entryPrice": "0"}
                for s, (a, u, m) in self.poz.items() if a]


_id = [0]


def emir(ic, sem, t, yon, adet, fiyat, cid="android_x", rpnl=0.0, kom=0.01):
    _id[0] += 1
    ic.orders.setdefault(sem, []).append({"orderId": _id[0], "clientOrderId": cid, "time": t, "updateTime": t, "executedQty": str(adet),
                                          "avgPrice": str(fiyat), "side": yon})
    ic.trades.setdefault(sem, []).append({"id": _id[0], "orderId": _id[0], "time": t, "side": yon, "qty": str(adet), "price": str(fiyat),
                                          "realizedPnl": str(rpnl), "commission": str(kom), "commissionAsset": "USDT"})


d = tempfile.mkdtemp()
ELLE = os.path.join(d, "carry_elle.json"); OLAY = os.path.join(d, "olay.jsonl"); PANEL = os.path.join(d, "panel.json")
KZ = os.path.join(d, "elle_kz.json")


def elle_yaz(semler, birak=None):
    with open(ELLE, "w") as f:
        json.dump({"elle": {s: {"t": t} for s, t in semler.items()}, "birakilan": birak or {}, "son_kontrol_ms": 1}, f)


def guncelle(c, simdi_ms):
    return K.guncelle(c, simdi=simdi_ms / 1000, dosya=KZ, elle_dosya=ELLE, olay_dosya=OLAY, panel_dosya=PANEL)


T0 = 1_800_000_000_000
print("1) devralmasız elle short")
c = Istemci(); ic = c.client
emir(ic, "AUSDT", T0, "SELL", 100, 0.8, kom=0.04)
ic.income["AUSDT"] = [{"time": T0 + 3600_000, "income": "0.10"}]
c.poz["AUSDT"] = (-100, 10.0, 0.7)
elle_yaz({"AUSDT": T0 + 1800_000})
st = guncelle(c, T0 + 2 * 3600_000)
a = st["aralik"]["AUSDT"][0]
kontrol("başlangıç = kullanıcının ilk dolumu", a["bas"] == T0 and yakin(a["ilk_fiyat"], 0.8))
kontrol("kz = açık 10 + funding 0,10 − komisyon 0,04", yakin(a["kz"], 10.06))
kontrol("devir 0 (bottan bir şey alınmadı)", yakin(a["devir"], 0.0) and yakin(a["devr_adet"], 0.0))
kontrol("toplam", yakin(st["toplam"], 10.06, 1e-3))

print("2) botun short'una ekleme (devralınan kısım devir anına kadar botun)")
c = Istemci(); ic = c.client
emir(ic, "BUSDT", T0 - 86400_000, "SELL", 100, 0.5, cid="x-Cb7ytekJbot1", kom=0)   # botun girişi (aralık dışında)
emir(ic, "BUSDT", T0, "SELL", 50, 0.8, kom=0)
c.poz["BUSDT"] = (-150, -15.0, 0.7)   # Binance ort. 0,6 → açık −15
elle_yaz({"BUSDT": T0 + 600_000})
st = guncelle(c, T0 + 3600_000)
a = st["aralik"]["BUSDT"][0]
kontrol("devralınan adet −100", yakin(a["devr_adet"], -100))
kontrol("elle kz = −150 × (0,7 − 0,8) = +15", yakin(a["kz"], 15.0))
kontrol("devir = botun −100 × (0,8 − 0,5) = −30", yakin(a["devir"], -30.0))
kontrol("R + F + C + U − devir = kz", yakin(a["R"] + a["F"] + a["C"] + a["U"] - a["devir"], a["kz"]))

print("3) botun long'unu kapatıp yeni long (AKE gibi)")
c = Istemci(); ic = c.client
emir(ic, "CUSDT", T0, "SELL", 3000, 0.0028, rpnl=-7.5, kom=0)      # botun 3000 long'u (giriş 0,0053) kapanıyor
emir(ic, "CUSDT", T0 + 10_000, "BUY", 30000, 0.0028, kom=0)
c.poz["CUSDT"] = (30000, -3.0, 0.0027)
elle_yaz({"CUSDT": T0 + 900_000})
st = guncelle(c, T0 + 3600_000)
a = st["aralik"]["CUSDT"][0]
kontrol("devralınan 3000 long", yakin(a["devr_adet"], 3000))
kontrol("botun kapanış zararı (−7,5) devirde, elleye yazılmaz", yakin(a["devir"], -7.5))
kontrol("elle kz yalnız yeni long: 30000 × (0,0027 − 0,0028) = −3", yakin(a["kz"], -3.0))

print("4) kapatılan aralık dondurulur, coin bota döner")
with open(OLAY, "w") as f:
    f.write(json.dumps({"olay": "birak", "t": T0 + 7200_000, "sembol": "AUSDT"}) + "\n")
c = Istemci(); ic = c.client
emir(ic, "AUSDT", T0, "SELL", 100, 0.8, kom=0.04)
emir(ic, "AUSDT", T0 + 3600_000, "BUY", 100, 0.7, rpnl=10.0, kom=0.04)
emir(ic, "AUSDT", T0 + 9000_000, "SELL", 40, 0.75, cid="x-Cb7ytekJbot2", kom=0.02)   # bot geri aldıktan sonra
c.poz["AUSDT"] = (-40, 0.0, 0.75)
os.remove(KZ)
elle_yaz({"AUSDT": T0 + 1800_000})
guncelle(c, T0 + 3700_000)
elle_yaz({}, birak={"AUSDT": T0 + 7200_000})
st = guncelle(c, T0 + 10_000_000)
a = st["aralik"]["AUSDT"][0]
kontrol("aralık bırakma anında kapandı", a["bit"] == T0 + 7200_000 and a.get("son") is True)
kontrol("kz = 10 − 0,08 (botun sonraki dolumu dahil değil)", yakin(a["kz"], 9.92))
n = ic.cagri
st = guncelle(c, T0 + 11_000_000)
kontrol("dondurulmuş aralık yeniden sorulmaz", ic.cagri == n and yakin(st["toplam"], 9.92, 1e-3))
kontrol("toplam_oku API'siz", yakin(K.toplam_oku(KZ), 9.92, 1e-3))

print("5) panel işareti var ama dolum yok → aralık açılmaz")
c = Istemci()
with open(PANEL, "w") as f:
    json.dump({"DUSDT": T0 + 11_000_000}, f)
elle_yaz({}, birak={"AUSDT": T0 + 7200_000})
st = guncelle(c, T0 + 11_100_000)
kontrol("DUSDT aralığı yok", not st["aralik"].get("DUSDT"))
os.remove(PANEL)

print("6) guncel_toplam önbellek")
c = Istemci()
st = K._oku(KZ)
kontrol("taze kayıt: API çağrısı yok", yakin(K.guncel_toplam(c, dosya=KZ, simdi=st["zaman"] + 10), 9.92, 1e-3) and c.client.cagri == 0)

print("7) panel elle_ayir: döküm parçaları botun kârına eşit kalır")
import panel
o = {"dokum": {"gerceklesen": 100.0, "funding": 20.0, "komisyon": -5.0, "diger_gelir": 0.0},
     "coin_ozet": [{"s": "B", "kapanan": 0.0, "funding": 0.0, "komisyon": 0.0, "acik": -15.0, "toplam": -15.0}]}
an = {"ozkaynak_hesap": 1000, "elle": K.ozet({"aralik": {"BUSDT": [{"bas": T0, "R": 0, "F": 0, "C": 0, "U": -15.0, "kz": 15.0, "devir": -30.0}]}})}
panel.elle_ayir(o, an)
kontrol("döküm: gerçekleşene botun devir payı (−30) eklendi", yakin(o["dokum"]["gerceklesen"], 70.0))
k = o["coin_ozet"][0]
kontrol("coin satırı: bot payı = −30 (açık 0, kapanan −30)", yakin(k["toplam"], -30.0) and yakin(k["acik"], 0.0) and yakin(k["elle_kz"], 15.0))
kontrol("o['elle'] özeti", o["elle"]["kz"] == 15.0)

print("8) bot sermayesi elle K/Z'yi düşer")
import carry_bot
cb_ham, cb_elle = carry_bot._sermaye_oku_ham, carry_bot.ELLE
try:
    carry_bot._sermaye_oku_ham = lambda c: 1000.0
    carry_bot.ELLE = True
    K_eski = K.guncel_toplam
    K.guncel_toplam = lambda c, **kw: -50.0
    kontrol("ELLE açık: (1000 − (−50)) × ölçek", yakin(carry_bot.sermaye_oku(None), 1050.0 * carry_bot.SERMAYE_OLCEK))
    carry_bot.ELLE = False
    kontrol("ELLE kapalı: eski davranış", yakin(carry_bot.sermaye_oku(None), 1000.0 * carry_bot.SERMAYE_OLCEK))
    K.guncel_toplam = lambda c, **kw: (_ for _ in ()).throw(RuntimeError("x"))
    carry_bot.ELLE = True
    kontrol("elle K/Z okunamazsa hesap özkaynağı", yakin(carry_bot.sermaye_oku(None), 1000.0 * carry_bot.SERMAYE_OLCEK))
finally:
    carry_bot._sermaye_oku_ham, carry_bot.ELLE = cb_ham, cb_elle
    K.guncel_toplam = K_eski

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
