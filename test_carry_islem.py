"""MADDE 834 — panelden işlem kapısı (carry_islem.py) testleri. Sahte borsa; hiçbir gerçek API çağrısı yok."""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, ".")
import carry_islem as ci
import carry_elle as ce

basarisiz = []


def kontrol(ad, kosul, detay=""):
    print(f"  [{'OK' if kosul else 'HATA'}]   {ad}" + ("" if kosul else f"  {detay}"))
    if not kosul:
        basarisiz.append(ad)


def hata_mi(f, icerik=None, kod=None):
    try:
        f()
    except ci.Hata as e:
        return (icerik is None or icerik in e.mesaj) and (kod is None or e.kod == kod)
    return False


class SahteIc:
    def __init__(self):
        self.fiyat = {"AKEUSDT": 0.5, "BTCUSDT": 90000.0, "ONDOUSDT": 0.8}
        self.emirler, self.algolar, self.iptaller, self.algo_iptaller = [], [], [], []
        self.acik = {}           # sem -> [emir]
        self.algo_acik = {}      # sem -> [algo]
        self.poz = {}            # sem -> adet
        self.algo_patlat = False
        self.giris = {}
        self._oid = 100

    def futures_exchange_info(self):
        def s(sym, tick, step, mstep, tur="PERPETUAL", q="USDT", st="TRADING"):
            return {"symbol": sym, "contractType": tur, "quoteAsset": q, "status": st, "quantityPrecision": 0, "pricePrecision": 8,
                    "filters": [{"filterType": "PRICE_FILTER", "tickSize": tick}, {"filterType": "LOT_SIZE", "stepSize": step},
                                {"filterType": "MARKET_LOT_SIZE", "stepSize": mstep}, {"filterType": "MIN_NOTIONAL", "notional": "5"}]}
        return {"symbols": [s("AKEUSDT", "0.00001", "1", "1"), s("BTCUSDT", "0.10", "0.001", "0.001"),
                            s("ONDOUSDT", "0.0001", "0.1", "0.1"), s("ESKIUSDT", "0.01", "1", "1", st="SETTLING"),
                            s("BTCUSDT_261225", "0.1", "0.001", "0.001", tur="CURRENT_QUARTER"), s("XUSDC", "0.01", "1", "1", q="USDC")]}

    def futures_account_trades(self, symbol, startTime=None, limit=100):
        import time as _t
        return [{"time": e["_t"], "side": e["side"], "price": str(self.fiyat[symbol]), "qty": str(e["quantity"]),
                 "realizedPnl": str(e.get("_kz", 0)), "commission": "0.02"} for i, e in enumerate(self.emirler) if e["symbol"] == symbol and e["type"] == "MARKET"]

    def futures_mark_price(self, symbol):
        return {"markPrice": str(self.fiyat[symbol])}

    def futures_create_order(self, **kw):
        self._oid += 1
        import time as _t
        kw = dict(kw); kw["orderId"] = self._oid; kw["_t"] = int(_t.time() * 1000)
        self.emirler.append(kw)
        if kw["type"] == "MARKET":
            q = float(kw["quantity"]) * (1 if kw["side"] == "BUY" else -1)
            if not self.poz.get(kw["symbol"]):
                self.giris[kw["symbol"]] = self.fiyat[kw["symbol"]]
            self.poz[kw["symbol"]] = round(self.poz.get(kw["symbol"], 0.0) + q, 10)
            return {"orderId": self._oid, "status": "FILLED"}
        self.acik.setdefault(kw["symbol"], []).append({"orderId": self._oid, "clientOrderId": kw.get("newClientOrderId"),
                                                       "type": kw["type"], "side": kw["side"], "price": kw.get("price"),
                                                       "origQty": kw["quantity"]})
        return {"orderId": self._oid, "status": "NEW"}

    def futures_create_algo_order(self, **kw):
        if self.algo_patlat:
            raise RuntimeError("APIError(code=-2021): Order would immediately trigger. signature=abc123")
        self._oid += 1
        self.algolar.append(dict(kw))
        self.algo_acik.setdefault(kw["symbol"], []).append({"algoId": self._oid, "clientAlgoId": kw.get("clientAlgoId"),
                                                            "orderType": kw["type"], "triggerPrice": kw["triggerPrice"]})
        return {"algoId": self._oid}

    def futures_get_open_algo_orders(self, symbol=None):
        return list(self.algo_acik.get(symbol, []))

    def futures_cancel_algo_order(self, symbol, algoId):
        self.algo_iptaller.append((symbol, algoId))
        self.algo_acik[symbol] = [o for o in self.algo_acik.get(symbol, []) if o["algoId"] != algoId]

    def futures_get_open_orders(self, symbol=None):
        return list(self.acik.get(symbol, []))

    def futures_cancel_order(self, symbol, orderId):
        self.iptaller.append((symbol, orderId))
        self.acik[symbol] = [o for o in self.acik.get(symbol, []) if o["orderId"] != orderId]


class SahteClient:
    def __init__(self):
        self.client = SahteIc()

    def get_open_positions(self):
        return [{"symbol": s, "positionAmt": str(a), "entryPrice": str(self.client.giris.get(s, self.client.fiyat.get(s, 1))), "unRealizedProfit": "1.5",
                 "liquidationPrice": "0.21"}
                for s, a in self.client.poz.items() if a]


d = tempfile.mkdtemp()
SAAT = [1_000_000.0]


def yeni(**ek):
    a = {"acik": True, "pin": "482913", "max_usd": 200.0, "mod": "demo", "canli_izin": False, "elle": True,
         "defter": os.path.join(d, "panel_islem.jsonl"), "elle_panel": os.path.join(d, "elle_panel.json")}
    a.update(ek)
    bil = []
    k = ci.Kapi(SahteClient(), a, bildir=bil.append, saat=lambda: SAAT[0])
    return k, k.ic, bil


print("1) açık / kapalı")
for ek, beklenen in (({"acik": False}, "CARRY_PANEL_ISLEM"), ({"pin": ""}, "PIN"), ({"pin": "12345"}, "PIN"),
                     ({"mod": "live"}, "CARRY_ISLEM_CANLI"), ({"elle": False}, "CARRY_ELLE")):
    k, ic, _ = yeni(**ek)
    kontrol(f"kapalı: {beklenen}", k.durum()["acik"] is False and beklenen in k.durum()["neden"])
    kontrol(f"kapalıyken emir REDDEDİLİR ({beklenen})",
            hata_mi(lambda: k.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "482913"}), kod=403) and not ic.emirler)
k, ic, _ = yeni(mod="live", canli_izin=True)
kontrol("canlı + CARRY_ISLEM_CANLI=1 -> açık", k.durum()["acik"] is True)
k, ic, _ = yeni()
kontrol("durum yanıtında PIN yok", "482913" not in json.dumps(k.durum()))

print("2) PIN")
kontrol("yanlış PIN -> 403, emir yok", hata_mi(lambda: k.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "000000"}), "PIN yanlış", 403)
        and not ic.emirler)
for _ in range(4):
    hata_mi(lambda: k.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "1"}))
kontrol("5 yanlıştan sonra DOĞRU PIN de kilitli (429)", hata_mi(lambda: k.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "482913"}),
                                                              "kilitli", 429) and not ic.emirler)
SAAT[0] += ci.KILIT_SN + 1
k.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "482913"})
kontrol("15 dk sonra doğru PIN çalışır", len(ic.emirler) == 1)

print("3) önizleme denetimleri")
k, ic, _ = yeni()
o = {"sembol": "AKEUSDT", "yon": "L", "usd": 50}
kontrol("geçersiz sembol", hata_mi(lambda: k.onizle({**o, "sembol": "ake; rm"}), "geçersiz"))
kontrol("işlem görmeyen / vadeli / USDC reddedilir", all(hata_mi(lambda s=s: k.onizle({**o, "sembol": s}), "perpetual")
                                                        for s in ("ESKIUSDT", "YOKUSDT")))
kontrol("yön L/S dışı", hata_mi(lambda: k.onizle({**o, "yon": "X"}), "yön"))
kontrol("200 $ üstü reddedilir", hata_mi(lambda: k.onizle({**o, "usd": 200.01}), "en fazla 200"))
kontrol("tam 200 $ geçer", k.onizle({**o, "usd": 200})["adet"] == 400)
kontrol("5 $ altı reddedilir", hata_mi(lambda: k.onizle({**o, "usd": 4}), "en az"))
kontrol("tutar sayı değilse", hata_mi(lambda: k.onizle({**o, "usd": "abc"}), "tutar"))
kontrol("adet adıma aşağı yuvarlanır (ONDO 0,1 adım: 50/0,8=62,5)", k.onizle({**o, "sembol": "ONDOUSDT"})["adet"] == 62.5)
kontrol("BTC: 50 $ -> 0,000 adım altı -> reddedilir (en küçük adım 0,001 = 90 $)",
        hata_mi(lambda: k.onizle({**o, "sembol": "BTCUSDT", "usd": 50}), "adım"))
kontrol("limit ±%20 dışı reddedilir", hata_mi(lambda: k.onizle({**o, "tip": "LIMIT", "fiyat": 0.39}), "±%20"))
kontrol("limit adedi limit fiyatından", k.onizle({**o, "tip": "LIMIT", "fiyat": 0.45})["adet"] == 111)
kontrol("long: TP fiyatın altındaysa reddedilir", hata_mi(lambda: k.onizle({**o, "tp": 0.49}), "ÜSTÜNDE"))
kontrol("long: stop fiyatın üstündeyse reddedilir", hata_mi(lambda: k.onizle({**o, "sl": 0.51}), "ALTINDA"))
kontrol("short: TP fiyatın üstündeyse reddedilir", hata_mi(lambda: k.onizle({**o, "yon": "S", "tp": 0.51}), "ALTINDA"))
kontrol("short: stop fiyatın altındaysa reddedilir", hata_mi(lambda: k.onizle({**o, "yon": "S", "sl": 0.49}), "ÜSTÜNDE"))
kontrol("geçerli TP / SL kabul", k.onizle({**o, "tp": 0.6, "sl": 0.45})["tp"] == 0.6)
kontrol("önizleme emir GÖNDERMEZ", ic.emirler == [] and ic.algolar == [])

print("4) piyasa emri + TP / SL")
k, ic, bil = yeni()
r = k.emir({**o, "tp": 0.6, "sl": 0.45, "pin": "482913"})
e = ic.emirler[0]
kontrol("MARKET BUY 100 adet", e["type"] == "MARKET" and e["side"] == "BUY" and e["quantity"] == 100 and e["symbol"] == "AKEUSDT")
kontrol("emir kimliği panel_ önekli (bot öneki yok)", e["newClientOrderId"].startswith("panel_") and len(e["newClientOrderId"]) <= 36)
kontrol("bot bu emri KULLANICI sayar (madde 830)", ce.emir_sahibi({"clientOrderId": e["newClientOrderId"]}) == "kullanici")
kontrol("giriş emrinde reduceOnly yok", "reduceOnly" not in e)
tp = next(a for a in ic.algolar if a["type"] == "TAKE_PROFIT_MARKET"); sl = next(a for a in ic.algolar if a["type"] == "STOP_MARKET")
kontrol("TP: SELL, reduceOnly, adet = pozisyon, tetik tick'e göre", tp["side"] == "SELL" and tp["reduceOnly"] == "true"
        and tp["quantity"] == 100 and tp["triggerPrice"] == "0.60000" and tp["clientAlgoId"].startswith("panel_"), tp)
kontrol("SL: SELL STOP_MARKET 0.45000, işaret fiyatıyla", sl["triggerPrice"] == "0.45000" and sl["workingType"] == "MARK_PRICE")
kontrol("yanıtta TP + SL", [x["tur"] for x in r["tpsl"]] == ["TP", "SL"])
kontrol("deftere yazıldı", '"emir"' in open(os.path.join(d, "panel_islem.jsonl"), encoding="utf-8").read())
kontrol("madde 838: emir anında elle panel işareti yazıldı", "AKEUSDT" in ce.panel_okuma(os.path.join(d, "elle_panel.json")))
kontrol("Telegram bildirimi", len(bil) == 1 and "AKE LONG" in bil[0], bil)
kontrol("yanıtta / defterde PIN yok", "482913" not in json.dumps(r) and "482913" not in open(os.path.join(d, "panel_islem.jsonl")).read())

print("5) ekleme: TP / SL TOPLAM adede göre yeniden kurulur, botun stop'una dokunulmaz")
ic.algo_acik["AKEUSDT"].append({"algoId": 9, "clientAlgoId": "x-Cb7ytekJbotstop", "orderType": "STOP_MARKET", "triggerPrice": "0.3"})
k.emir({**o, "usd": 25, "tp": 0.7, "pin": "482913"})
pan = [a for a in ic.algo_acik["AKEUSDT"] if a["clientAlgoId"].startswith("panel_")]
kontrol("eski panel TP / SL iptal, yeni TP 150 adet", len(pan) == 1 and ic.algolar[-1]["quantity"] == 150
        and ic.algolar[-1]["triggerPrice"] == "0.70000", (pan, ic.algolar[-1]))
kontrol("botun stop'u yerinde", any(a["algoId"] == 9 for a in ic.algo_acik["AKEUSDT"]) and (("AKEUSDT", 9) not in ic.algo_iptaller))

k.emir({**o, "usd": 25, "pin": "482913"})       # TP / SL VERMEDEN ekleme
pan = [a_ for a_ in ic.algo_acik["AKEUSDT"] if a_["clientAlgoId"].startswith("panel_")]
kontrol("madde 835: TP vermeden eklemede mevcut panel TP aynı fiyatla TOPLAM adede (200) yeniden kuruldu",
        len(pan) == 1 and ic.algolar[-1]["quantity"] == 200 and ic.algolar[-1]["triggerPrice"] == "0.70000", (pan, ic.algolar[-1]))
kontrol("botun stop'u yine yerinde", any(a_["algoId"] == 9 for a_ in ic.algo_acik["AKEUSDT"]))

print("6) TP / SL hatası emri geri almaz, açıkça söylenir")
k2, ic2, bil2 = yeni(); ic2.algo_patlat = True
r2 = k2.emir({**o, "tp": 0.6, "pin": "482913"})
kontrol("emir doldu, tpsl_hata dolu", r2["emir"]["durum"] == "FILLED" and "TP/SL konamadı" in r2["tpsl_hata"])
kontrol("bildirimde uyarı var", "⚠️" in bil2[0])

print("7) limit emri")
k3, ic3, _ = yeni()
r3 = k3.emir({**o, "tip": "LIMIT", "fiyat": 0.4512345, "tp": 0.6, "pin": "482913"})
e3 = ic3.emirler[0]
kontrol("LIMIT GTC, fiyat tick'e yuvarlı string", e3["type"] == "LIMIT" and e3["timeInForce"] == "GTC" and e3["price"] == "0.45123")
kontrol("limitte TP / SL konmaz (önce dolmalı)", ic3.algolar == [] and r3["tpsl"] == [])

print("8) TP / SL güncelleme")
k4, ic4, _ = yeni()
kontrol("pozisyon yokken reddedilir", hata_mi(lambda: k4.tpsl({"sembol": "AKEUSDT", "tp": 0.6, "pin": "482913"}), "pozisyon yok"))
ic4.poz["AKEUSDT"] = -40.0
kontrol("short pozisyonda yanlış yönlü TP reddedilir", hata_mi(lambda: k4.tpsl({"sembol": "AKEUSDT", "tp": 0.6, "pin": "482913"}), "ALTINDA"))
k4.tpsl({"sembol": "AKEUSDT", "tp": 0.4, "sl": 0.6, "pin": "482913"})
kontrol("short TP / SL: BUY, 40 adet", all(a["side"] == "BUY" and a["quantity"] == 40 for a in ic4.algolar) and len(ic4.algolar) == 2)
k4.tpsl({"sembol": "AKEUSDT", "pin": "482913"})
kontrol("boş TP / SL = kaldır", [a for a in ic4.algo_acik["AKEUSDT"] if a["clientAlgoId"].startswith("panel_")] == [])

print("9) kapatma")
k5, ic5, _ = yeni()
k5.emir({**o, "usd": 50.5, "tp": 0.6, "sl": 0.45, "pin": "482913"})       # 101 adet
ic5.acik["AKEUSDT"] = [{"orderId": 1, "clientOrderId": "panel_x", "type": "LIMIT"}, {"orderId": 2, "clientOrderId": "x-Cb7ytekJtp", "type": "LIMIT"}]
ic5.algo_acik["AKEUSDT"].append({"algoId": 9, "clientAlgoId": "x-Cb7ytekJbotstop", "orderType": "STOP_MARKET", "triggerPrice": "0.3"})
k5.kapat({"sembol": "AKEUSDT", "oran": 0.5, "pin": "482913"})
kz = ic5.emirler[-1]
kontrol("%50 kapat: SELL reduceOnly 50 adet (aşağı yuvarlı)", kz["side"] == "SELL" and kz["reduceOnly"] == "true" and kz["quantity"] == 50
        and kz["newClientOrderId"].startswith("panel_"), kz)
pan = [a for a in ic5.algo_acik["AKEUSDT"] if a["clientAlgoId"].startswith("panel_")]
kontrol("kalan 51 adede göre TP / SL aynı fiyatlarla yeniden kuruldu", len(pan) == 2 and all(a["quantity"] == 51 for a in ic5.algolar[-2:])
        and {a["triggerPrice"] for a in ic5.algolar[-2:]} == {"0.60000", "0.45000"}, ic5.algolar[-2:])
k5.kapat({"sembol": "AKEUSDT", "oran": 1, "pin": "482913"})
kontrol("tamamını kapat: kalan 51 adet", ic5.emirler[-1]["quantity"] == 51 and ic5.poz["AKEUSDT"] == 0)
kontrol("panel emirleri (normal + algo) iptal; botun emirleri YERİNDE",
        ("AKEUSDT", 1) in ic5.iptaller and ("AKEUSDT", 2) not in ic5.iptaller
        and [a["algoId"] for a in ic5.algo_acik["AKEUSDT"]] == [9])
kontrol("pozisyon yokken kapat reddedilir", hata_mi(lambda: k5.kapat({"sembol": "AKEUSDT", "oran": 1, "pin": "482913"}), "pozisyon yok"))
kontrol("oran sınırı", hata_mi(lambda: k5.kapat({"sembol": "AKEUSDT", "oran": 1.5, "pin": "482913"}), "oran"))

print("10) iptal yalnız panel emirleri")
k6, ic6, _ = yeni()
ic6.acik["AKEUSDT"] = [{"orderId": 1, "clientOrderId": "panel_a"}, {"orderId": 2, "clientOrderId": "x-Cb7ytekJ"}, {"orderId": 3, "clientOrderId": "android_x"}]
ic6.algo_acik["AKEUSDT"] = [{"algoId": 7, "clientAlgoId": "panel_b"}, {"algoId": 8, "clientAlgoId": "android_sl"}]
r6 = k6.iptal({"sembol": "AKEUSDT", "pin": "482913"})
kontrol("2 panel emri iptal; bot ve uygulama emirleri yerinde", r6["iptal"] == 2 and [o_["orderId"] for o_ in ic6.acik["AKEUSDT"]] == [2, 3]
        and [a["algoId"] for a in ic6.algo_acik["AKEUSDT"]] == [8])

print("11) pozisyon okuma")
p6 = k6.pozisyon("akeusdt")
kontrol("pozisyon + bekleyen + TP/SL + işaret; panel olmayanlar panel=False", p6["isaret"] == 0.5
        and [b_["panel"] for b_ in p6["bekleyen"]] == [False, False] and [t_["panel"] for t_ in p6["tpsl"]] == [False], p6)

k8, ic8, _ = yeni()
k8.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "482913"})
p8 = k8.pozisyon("AKEUSDT")
kontrol("madde 835: pozisyon yanıtında dolumlar (grafik işaretleri) ve likidasyon fiyatı",
        p8["islemler"] and p8["islemler"][0]["yon"] == "AL" and p8["islemler"][0]["adet"] == 100 and p8["pozisyon"]["likidasyon"] == 0.21, p8)

print("11b) madde 839: elle özeti, tek emir iptali, sahiplik bayrakları")
import time as _zaman
SAAT[0] = _zaman.time()          # dolum zamanları gerçek saatte
d9 = tempfile.mkdtemp()
k9, ic9, _ = yeni(elle_dosya=os.path.join(d9, "e.json"), elle_panel=os.path.join(d9, "p.json"), elle_olay=os.path.join(d9, "o.jsonl"),
                  dilim=os.path.join(d9, "dil.json"))
json.dump({"dilimler": {"0": {"ONDOUSDT": 50.0}}}, open(os.path.join(d9, "dil.json"), "w"))
p9 = k9.pozisyon("ONDOUSDT")
kontrol("botun coini: bot_tutuyor=True, elle=False", p9["bot_tutuyor"] is True and p9["elle"] is False)
k9.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "sl": 0.45, "pin": "482913"})
p9 = k9.pozisyon("AKEUSDT")
kontrol("panelden alınan coin: elle=True (bot bir sonraki kontrolü yapmadan)", p9["elle"] is True and p9["bot_tutuyor"] is False)
oz = k9.elle_ozet()
kontrol("Pozisyonlarım: AKE long 100 adet, giriş 0,5, stop 0,45", len(oz["pozisyonlar"]) == 1 and oz["pozisyonlar"][0]["adet"] == 100
        and oz["pozisyonlar"][0]["sl"] == 0.45 and oz["pozisyonlar"][0]["giris"] == 0.5, oz)
ic9.emirler[-1]["_kz"] = 0      # açılış
ic9.fiyat["AKEUSDT"] = 0.6
k9.kapat({"sembol": "AKEUSDT", "oran": 1, "pin": "482913"}); ic9.emirler[-1]["_kz"] = 10.0
oz = k9.elle_ozet()
kontrol("30 gün sonucu: 1 kapanış, kârlı, net = 10 − komisyon", oz["sonuc"]["kapanis"] == 1 and oz["sonuc"]["kazanan"] == 1
        and abs(oz["sonuc"]["net"] - (10 - 0.04)) < 1e-9 and oz["pozisyonlar"] == [], oz["sonuc"])
ic9.fiyat["AKEUSDT"] = 0.5
k9.emir({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "tip": "LIMIT", "fiyat": 0.45, "pin": "482913"})
oid = ic9.acik["AKEUSDT"][-1]["orderId"]
ic9.acik["AKEUSDT"].append({"orderId": 4242, "clientOrderId": "android_x", "type": "LIMIT", "side": "BUY", "price": "0.4", "origQty": "5"})
kontrol("başkasının emri buradan iptal edilmez", hata_mi(lambda: k9.iptal({"sembol": "AKEUSDT", "orderId": 4242, "pin": "482913"}), "yalnız panelden"))
kontrol("olmayan emir", hata_mi(lambda: k9.iptal({"sembol": "AKEUSDT", "orderId": 1, "pin": "482913"}), "açık değil"))
r9 = k9.iptal({"sembol": "AKEUSDT", "orderId": oid, "pin": "482913"})
kontrol("tek panel emri iptal edildi, diğerleri yerinde", r9["iptal"] == 1 and [o_["orderId"] for o_ in ic9.acik["AKEUSDT"]] == [4242])
kontrol("tek emir iptali de PIN ister", hata_mi(lambda: k9.iptal({"sembol": "AKEUSDT", "orderId": 4242, "pin": "0"}), "PIN"))
kontrol("bekleyen emirde orderId döner", all("orderId" in b_ for b_ in k9.pozisyon("AKEUSDT")["bekleyen"]))

print("12) Flask uygulaması")
app = ci.uygulama(lambda: yeni()[0]).test_client()
kontrol("GET /durum", app.get("/durum").get_json()["acik"] is True)
r = app.post("/onizle", json={"sembol": "AKEUSDT", "yon": "L", "usd": 500})
kontrol("hata 400 + mesaj", r.status_code == 400 and "en fazla" in r.get_json()["hata"])
kontrol("JSON olmayan gövde reddedilir", app.post("/emir", data="x").status_code == 400)
kontrol("yanlış PIN 403", app.post("/emir", json={**o, "pin": "9"}).status_code == 403)
k7, ic7, _ = yeni(); ic7.algo_patlat = True; ic7.poz["AKEUSDT"] = 10
app7 = ci.uygulama(lambda: k7).test_client()
r7 = app7.post("/tpsl", json={"sembol": "AKEUSDT", "tp": 0.6, "pin": "482913"})
kontrol("Binance hatası 502, imza gizlenir", r7.status_code == 502 and "abc123" not in r7.get_data(as_text=True)
        and "[gizli]" in r7.get_json()["hata"], r7.get_data(as_text=True))
r8 = app.post("/emir", json={**o, "pin": "482913"})
kontrol("doğru PIN ile emir", r8.status_code == 200 and r8.get_json()["ok"] is True)

print("13) ayarlar .env'den")
os.environ.update({"CARRY_PANEL_ISLEM": "1", "CARRY_ISLEM_PIN": "  777777 ", "CARRY_ISLEM_MAX_USD": "150", "CARRY_ELLE": "1", "BINANCE_MODE": "demo"})
a = ci.ayarlar()
kontrol("ayarlar okunur (PIN kırpılır, sınır 150)", a["acik"] and a["pin"] == "777777" and a["max_usd"] == 150 and a["elle"])
os.environ["CARRY_ELLE"] = "0"
kontrol("CARRY_ELLE=0 -> elle kapalı", ci.ayarlar()["elle"] is False)
for v in ("CARRY_PANEL_ISLEM", "CARRY_ISLEM_PIN", "CARRY_ISLEM_MAX_USD", "CARRY_ELLE"):
    os.environ.pop(v, None)
kontrol("varsayılan KAPALI", ci.ayarlar()["acik"] is False)

if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tüm panel işlem kapısı testleri geçti.")
