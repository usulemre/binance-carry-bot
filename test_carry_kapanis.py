"""MADDE 838 — -2022 "ReduceOnly Order is rejected" sağlamlaştırması (AKE 20 Kas, madde 829) testleri.

Sahte borsa reduceOnly kuralını Binance gibi uygular: açık reduceOnly emirlerin toplamı + yeni reduceOnly adet pozisyonu aşarsa ya da
pozisyon ters / yoksa -2022. Böylece "yetim emir" senaryosu gerçekçi biçimde yeniden üretilir. Hiçbir gerçek API çağrısı yok.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, ".")
import carry_bot as cb

basarisiz = []


def kontrol(ad, kosul, detay=""):
    print(f"  [{'OK' if kosul else 'HATA'}]   {ad}" + ("" if kosul else f"  {detay}"))
    if not kosul:
        basarisiz.append(ad)


class Red(Exception):
    def __init__(self, kod, m):
        super().__init__(f"APIError(code={kod}): {m}"); self.code = kod


class Ic:
    def __init__(self, poz):
        self.poz = dict(poz)             # sem -> adet
        self.acik = {}                   # sem -> [emir]
        self.algo = {}                   # sem -> [algo]
        self.gonderilen, self.iptal, self.algo_iptal = [], [], []
        self.zorla_red = 0               # bu kadar reduceOnly kapanışı nedensiz reddet (demo tuhaflığı senaryosu)
        self._id = 1000

    def _ro_toplam(self, sem, yon):
        return sum(float(o["origQty"]) for o in self.acik.get(sem, []) if o.get("reduceOnly") and o["side"] == yon)

    def futures_create_order(self, **kw):
        sem, yon, q = kw["symbol"], kw["side"], float(kw["quantity"])
        ro = str(kw.get("reduceOnly")).lower() == "true"
        a = self.poz.get(sem, 0.0)
        if ro:
            dogru = (a > 0 and yon == "SELL") or (a < 0 and yon == "BUY")
            if not dogru or self._ro_toplam(sem, yon) + q > abs(a) + 1e-9:
                raise Red(-2022, "ReduceOnly Order is rejected.")
            if kw["type"] == "MARKET" and self.zorla_red > 0:
                self.zorla_red -= 1
                raise Red(-2022, "ReduceOnly Order is rejected.")
        self._id += 1
        self.gonderilen.append(dict(kw))
        if kw["type"] == "MARKET":
            self.poz[sem] = round(a + (q if yon == "BUY" else -q), 10)
            return {"orderId": self._id, "status": "FILLED"}
        self.acik.setdefault(sem, []).append({"orderId": self._id, "symbol": sem, "side": yon, "origQty": str(q), "type": kw["type"],
                                              "reduceOnly": ro, "clientOrderId": kw.get("newClientOrderId", "x-Cb7ytekJ" + str(self._id))})
        return {"orderId": self._id, "status": "NEW"}

    def futures_get_open_orders(self, symbol=None):
        return list(self.acik.get(symbol, []))

    def futures_cancel_order(self, symbol, orderId):
        self.iptal.append((symbol, orderId))
        self.acik[symbol] = [o for o in self.acik.get(symbol, []) if o["orderId"] != orderId]

    def futures_get_open_algo_orders(self, symbol=None):
        return list(self.algo.get(symbol, []))

    def futures_cancel_algo_order(self, symbol, algoId):
        self.algo_iptal.append((symbol, algoId))
        self.algo[symbol] = [o for o in self.algo.get(symbol, []) if o["algoId"] != algoId]

    def futures_create_algo_order(self, **kw):
        self._id += 1
        self.algo.setdefault(kw["symbol"], []).append({"algoId": self._id, "clientAlgoId": "x-Cb7ytekJa" + str(self._id)})
        return {"algoId": self._id}

    def futures_get_algo_order(self, symbol, algoId):
        return {"algoStatus": "NEW", "actualOrderId": ""}

    def futures_symbol_ticker(self, symbol):
        return {"price": "0.26"}


class Cl:
    def __init__(self, poz):
        self.client = Ic(poz)

    def get_open_positions(self):
        return [{"symbol": s, "positionAmt": str(a), "entryPrice": "0.5"} for s, a in self.client.poz.items() if a]

    def close_position(self, symbol, side, quantity, verify_fill=True):
        return self.client.futures_create_order(symbol=symbol, side=side, type="MARKET", quantity=quantity, reduceOnly=True)

    def get_symbol_precision(self, symbol):
        return {"quantity_precision": 0, "price_precision": 5, "step": 1.0, "piyasa_step": 1.0}


def yetim(c, sem, q, cid="x-Cb7ytekJyetim", side="SELL"):
    c.client._id += 1
    c.client.acik.setdefault(sem, []).append({"orderId": c.client._id, "symbol": sem, "side": side, "origQty": str(q), "type": "LIMIT",
                                              "reduceOnly": True, "clientOrderId": cid})
    return c.client._id


print("1) guvenli_kapat")
c = Cl({"AKEUSDT": 400.0})
kontrol("normal kapanış", cb.guvenli_kapat(c, {}, "AKEUSDT", "SELL", 400) == "kapandi" and c.client.poz["AKEUSDT"] == 0)

c = Cl({"AKEUSDT": 400.0})
y = yetim(c, "AKEUSDT", 400)                                    # kaydı düşmüş eski TP: reduceOnly toplamı pozisyonu dolduruyor
u = yetim(c, "AKEUSDT", 10, cid="android_al", side="BUY")       # kullanıcının ekleme limiti
o_ = yetim(c, "AKEUSDT", 10, cid="OLAY1AKE", side="BUY")        # olay modülünün emri
c.client.poz["AKEUSDT"] = 420.0
c.client.algo["AKEUSDT"] = [{"algoId": 77, "clientAlgoId": "x-Cb7ytekJfel"}, {"algoId": 78, "clientAlgoId": "android_sl"}]
d = {"kar_al": {"AKEUSDT": 1}, "merdiven": {"AKEUSDT": {"oid": 2}}, "felaket": {"AKEUSDT": 77}, "dilimler": {}}
r = cb.guvenli_kapat(c, d, "AKEUSDT", "SELL", 420)
kontrol("YETİM emir -2022'ye yol açıyordu; temizlenip TAM adetle kapandı", r == "temizlikle" and c.client.poz["AKEUSDT"] == 0, (r, c.client.poz))
kontrol("yalnız botun emirleri iptal edildi (kullanıcı + olay yerinde)", ("AKEUSDT", y) in c.client.iptal
        and ("AKEUSDT", u) not in c.client.iptal and ("AKEUSDT", o_) not in c.client.iptal)
kontrol("botun algo stop'u iptal, kullanıcınınki yerinde", c.client.algo_iptal == [("AKEUSDT", 77)])
kontrol("kayıtlar düşüldü (sonraki kurulum temiz)", "AKEUSDT" not in d["kar_al"] and "AKEUSDT" not in d["merdiven"] and "AKEUSDT" not in d["felaket"])

c = Cl({"AKEUSDT": 400.0}); yetim(c, "AKEUSDT", 30, cid="android_tp")   # kullanıcının reduceOnly TP'si de yer kaplıyor
r = cb.guvenli_kapat(c, {}, "AKEUSDT", "SELL", 400)
kontrol("kullanıcının reduceOnly emri yer kaplıyorsa: dokunulmaz, TAM adet reduceOnly'siz kapanır", r == "reduceonlysuz"
        and c.client.poz["AKEUSDT"] == 0 and c.client.iptal == [], (r, c.client.iptal))
c = Cl({"AKEUSDT": 400.0}); c.client.zorla_red = 2                # nedeni bilinmeyen tekrar eden red
r = cb.guvenli_kapat(c, {}, "AKEUSDT", "SELL", 400)
son = c.client.gonderilen[-1]
kontrol("iki kez red -> TAM adetle reduceOnly'siz piyasa emri", r == "reduceonlysuz" and c.client.poz["AKEUSDT"] == 0
        and "reduceOnly" not in son and son["quantity"] == 400, (r, son))

c = Cl({"AKEUSDT": 0.0})
kontrol("pozisyon zaten yoksa 'yok' (ters işlem açılmaz)", cb.guvenli_kapat(c, {}, "AKEUSDT", "SELL", 400) == "yok" and c.client.gonderilen == [])
c = Cl({"AKEUSDT": -50.0})
kontrol("pozisyon ters yöndeyse 'yok' (short'a SELL gitmez)", cb.guvenli_kapat(c, {}, "AKEUSDT", "SELL", 50) == "yok" and c.client.gonderilen == [])
c = Cl({"AKEUSDT": 300.0})
kontrol("adet borsadan taze okunur (400 istendi, 300 var -> 300 kapanır)",
        cb.guvenli_kapat(c, {}, "AKEUSDT", "SELL", 400) == "temizlikle" and c.client.poz["AKEUSDT"] == 0)


class Patlak(Cl):
    def close_position(self, *a, **k):
        raise Red(-1003, "Too many requests")


try:
    cb.guvenli_kapat(Patlak({"AKEUSDT": 5.0}), {}, "AKEUSDT", "SELL", 5); yukseldi = False
except Red:
    yukseldi = True
kontrol("-1003 gibi başka hata: istisna yükselir, emir gönderilmez", yukseldi)

print("2) felaket_simdi_kapat")
bil = []
_eski_bildir = cb._bildir
cb._bildir = lambda m, **k: bil.append((m, k))
c = Cl({"AKEUSDT": 400.0}); yetim(c, "AKEUSDT", 400)
d = {"dilimler": {"0": {"AKEUSDT": 100.0, "BUSDT": -5.0}}}
kontrol("yetim emre rağmen kapandı -> True, dilimden çıktı", cb.felaket_simdi_kapat(c, d, "AKEUSDT", 400) is True
        and "AKEUSDT" not in d["dilimler"]["0"] and c.client.poz["AKEUSDT"] == 0)
kontrol("bildirimde ilk denemenin reddedildiği yazıyor", "reddedildi" in bil[-1][0], bil[-1])
c = Cl({"AKEUSDT": 400.0})
kontrol("normal kapanışta bildirim sade", cb.felaket_simdi_kapat(c, {"dilimler": {}}, "AKEUSDT", 400) is True and "reddedildi" not in bil[-1][0])
p = Patlak({"AKEUSDT": 5.0})
kontrol("kapanamazsa False + ACİL bildirim", cb.felaket_simdi_kapat(p, {"dilimler": {}}, "AKEUSDT", 5) is False and bil[-1][1].get("acil") is True)

print("3) kar_al_kur: yetim emir TP'yi engellemez; stop'la kapanana TP denenmez")
_ayar = (cb.KAR_AL_ORAN, cb.LONG_24S, cb.LONG_24S_PIYASA, cb.LONG_FELAKET, cb.MERDIVEN, cb._kapanis_24s, cb.piyasa_24s, cb.GIRIS_DILIM,
         cb.TP_LOG if hasattr(cb, "TP_LOG") else None)
cb.KAR_AL_ORAN, cb.LONG_FELAKET, cb.MERDIVEN, cb.GIRIS_DILIM = 0.10, 0.0, 0.0, False
cb.LONG_24S, cb.LONG_24S_PIYASA = 0.45, 0.03
_d = tempfile.mkdtemp(); _cwd = os.getcwd(); os.chdir(_d)
try:
    cb._kapanis_24s = lambda client, sem: -0.10           # stop koşulu YOK
    cb.piyasa_24s = lambda client: -0.01
    c = Cl({"XUSDT": 100.0}); yetim(c, "XUSDT", 100)
    d = {"dilimler": {}, "kar_al": {}, "merdiven": {}, "felaket": {}}
    n = cb.kar_al_kur(c, d)
    tp = [g for g in c.client.gonderilen if g["type"] == "LIMIT"]
    kontrol("yetim emir varken TP: ilk deneme -2022 -> temizlik -> yeniden denemede kondu", n == 1 and len(tp) == 1 and tp[0]["quantity"] == 100
            and d["kar_al"].get("XUSDT"), (n, tp))
    cb._kapanis_24s = lambda client, sem: -0.48           # koşullu stop: coin −%48, piyasa −%10
    cb.piyasa_24s = lambda client: -0.10
    c = Cl({"AKEUSDT": 400.0}); yetim(c, "AKEUSDT", 400)
    d = {"dilimler": {"0": {"AKEUSDT": 200.0}}, "kar_al": {}, "merdiven": {}, "felaket": {}}
    n = cb.kar_al_kur(c, d)
    kontrol("AKE senaryosu: stop yetim emre rağmen KAPATTI", c.client.poz["AKEUSDT"] == 0 and "AKEUSDT" not in d["dilimler"]["0"])
    kontrol("kapanan pozisyona TP denenmedi (sahte 'KONULAMADI' yok)", not [g for g in c.client.gonderilen if g["type"] == "LIMIT"]
            and "AKEUSDT" not in d["kar_al"])

    # MADDE 840: TP iki denemede de -2022 (kullanıcının reduceOnly emri yer kaplıyor, bot ona dokunmaz). Temizlik botun felaket
    # stop'unu da siler; eskiden pozisyon tur sonunda stop'suz kalıyordu ve hiçbir yerde raporlanmıyordu.
    c = Cl({"SUSDT": -100.0}); yetim(c, "SUSDT", 100, cid="android_tp", side="BUY")
    d = {"dilimler": {}, "kar_al": {}, "merdiven": {}, "felaket": {}}
    n = cb.kar_al_kur(c, d)
    bot_algo = [o for o in c.client.algo.get("SUSDT", []) if o["clientAlgoId"].startswith("x-Cb7ytekJ")]
    kontrol("madde 840: TP iki kez -2022 -> TP yok ama felaket stop'u borsada ve kayıtta duruyor",
            n == 0 and len(bot_algo) == 1 and d["felaket"].get("SUSDT"), (n, c.client.algo, d["felaket"]))
    kontrol("madde 840: kullanıcının emrine dokunulmadı", [o["clientOrderId"] for o in c.client.acik["SUSDT"]] == ["android_tp"])
finally:
    os.chdir(_cwd)
    (cb.KAR_AL_ORAN, cb.LONG_24S, cb.LONG_24S_PIYASA, cb.LONG_FELAKET, cb.MERDIVEN, cb._kapanis_24s, cb.piyasa_24s, cb.GIRIS_DILIM, _) = _ayar
    cb._bildir = _eski_bildir

if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tüm -2022 sağlamlaştırma testleri geçti.")
