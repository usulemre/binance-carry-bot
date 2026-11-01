#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 701 testleri: emir defteri YALNIZ KAYIT — bot emirleri kayıt açık / kapalı / bozuk iken BİREBİR aynı; kayıt, dolum eşleme
(maker / komisyon / kısmi), TP dokunma ve panel özeti doğru; hiçbir hata dışarı sızmaz."""
import os, sys, tempfile, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defter_db as D

_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

T = tempfile.mkdtemp(); db = os.path.join(T, "defter", "carry.db"); t0 = 1_800_000_000.0

# ------------------------------------------------------------------ kayıt ve hata yalıtımı
kontrol("kayıt yazılır", D.emir_kaydet("TP", "AUSDT", "SELL", 10, limit=110, oid=1, giris=100, db=db, simdi=t0))
bozuk = os.path.join(T, "dosya"); open(bozuk, "w").write("x")
kontrol("yazılamayan yol: False döner, hata FIRLATMAZ", D.emir_kaydet("TP", "A", "SELL", 1, db=os.path.join(bozuk, "x.db")) is False)
_kilit = sqlite3.connect(db, isolation_level=None); _kilit.execute("BEGIN EXCLUSIVE")
_t = time.time(); _ok = D.emir_kaydet("TP", "KUSDT", "SELL", 1, db=db)
kontrol("başka süreç kilitliyken kayıt ≤ ~0,5 sn'de vazgeçer, bot beklemez", _ok is False and time.time() - _t < 1.5, time.time() - _t)
_kilit.execute("ROLLBACK"); _kilit.close()
kontrol("emir_durum bozuk girdi: hata fırlatmaz", D.emir_durum("A", None, None, db=db) is False and D.emir_durum("A", 1, "x", db=db) is False)

# ------------------------------------------------------------------ senaryo: 4 TP, 3 giriş
D.emir_kaydet("TP", "BUSDT", "BUY", 5, limit=90, oid=2, giris=100, db=db, simdi=t0)      # short TP, dolmadan iptal, fiyat değdi
D.emir_kaydet("TP", "CUSDT", "SELL", 4, limit=150, oid=3, giris=100, db=db, simdi=t0)    # dolmadan iptal, fiyat DEĞMEDİ
D.emir_kaydet("TP", "EUSDT", "SELL", 8, limit=120, oid=7, giris=100, db=db, simdi=t0)    # kısmi doldu, kalanı iptal
D.emir_kaydet("GIRIS", "AUSDT", "BUY", 10, limit=99.95, ref=100, oid=4, deneme=0, db=db, simdi=t0)
D.emir_kaydet("PIYASA_YEDEK", "BUSDT", "SELL", 5, ref=100, oid=5, db=db, simdi=t0)
D.emir_kaydet("FELAKET", "BUSDT", "BUY", 5, limit="300", oid=6, db=db, simdi=t0)

class _Ic:
    cagri = []
    E = {1: dict(status="FILLED", executedQty="10", avgPrice="110", updateTime=(t0 + 3600) * 1000),
         2: dict(status="CANCELED", executedQty="0", avgPrice="0", updateTime=(t0 + 7200) * 1000),
         3: dict(status="CANCELED", executedQty="0", avgPrice="0", updateTime=(t0 + 7200) * 1000),
         7: dict(status="CANCELED", executedQty="3", avgPrice="120", updateTime=(t0 + 7200) * 1000),
         4: dict(status="FILLED", executedQty="10", avgPrice="99.95", updateTime=(t0 + 60) * 1000),
         5: dict(status="FILLED", executedQty="5", avgPrice="99.90", updateTime=(t0 + 60) * 1000)}
    def futures_get_order(self, symbol, orderId):
        self.cagri.append(("get", symbol, orderId)); return self.E[orderId]
    def futures_account_trades(self, symbol, orderId):
        self.cagri.append(("tr", symbol, orderId))
        if orderId == 4: return [dict(qty="6", maker=True, commission="0.12", commissionAsset="USDT"),
                                 dict(qty="4", maker=False, commission="0.20", commissionAsset="USDT")]
        if orderId == 5: return [dict(qty="5", maker=False, commission="0.25", commissionAsset="USDT")]
        return [dict(qty=self.E[orderId]["executedQty"], maker=True, commission="0", commissionAsset="USDT")]
    def futures_klines(self, symbol, interval, startTime, endTime, limit):
        self.cagri.append(("kl", symbol))
        return {"BUSDT": [[0, 0, 101, 89.5, 95]], "CUSDT": [[0, 0, 140, 99, 120]]}[symbol]
class _C: client = _Ic()

kontrol("çok yeni emirler eşlenmez (10 dk bekler)", D.emir_esle(_C(), db=db, simdi=t0 + 60) == 0)
n = D.emir_esle(_C(), db=db, simdi=t0 + 8000)
kontrol("eşleme: 6 emir okundu (FELAKET algo emri hariç)", n == 6, n)
kontrol("eşleme API çağrısı sınırı: en_cok", D.emir_esle(_C(), db=db, simdi=t0 + 8000, en_cok=0) == 0)
c = sqlite3.connect(db)
r4 = c.execute("SELECT maker_adet, komisyon, eslendi FROM emir WHERE oid='4'").fetchone()
kontrol("maker adedi ve komisyon toplandı", r4 == (6.0, 0.32, 1), r4)
kontrol("bitmiş emir tekrar okunmaz", D.emir_esle(_C(), db=db, simdi=t0 + 9000) == 0)
d = D.tp_dokunma(_C(), db=db, simdi=t0 + 9000)
dk = dict(c.execute("SELECT oid, dokundu FROM emir WHERE tur='TP'").fetchall())
kontrol("TP dokunma: dolan=1, değen=1, değmeyen=0, kısmi=1", dk == {"1": 1, "2": 1, "3": 0, "7": 1}, dk)
kontrol("dokunma yalnız dolmamış 2 TP için mum okudu", d == 2, d)
c.close()

O = D.icra_ozet(db=db, simdi=t0 + 9000)
tp = O["tp"]; g = O["giris"]
kontrol("TP: 4 konan, 1 tam, 1 kısmi, 3 dokunan / 4 ölçülen", (tp["konan"], tp["tam"], tp["kismi"], tp["dokunan"], tp["olculen"]) == (4, 1, 1, 3, 4), tp)
kontrol("TP dolum oranı = dokunup dolan / dokunan = 2/3", abs(tp["dolum_orani"] - 2 / 3) < 1e-9, tp["dolum_orani"])
kontrol("kısmi pay 1/2", abs(tp["kismi_pay"] - 0.5) < 1e-9)
kontrol("giriş maker payı (notional) = 6·99,95 / (10·99,95 + 5·99,90)", abs(g["maker_pay"] - 6 * 99.95 / (10 * 99.95 + 5 * 99.90)) < 1e-9, g["maker_pay"])
bek = ((99.95 / 100 - 1) * 1e4 * 999.5 + (-(99.90 / 100 - 1)) * 1e4 * 499.5) / (999.5 + 499.5)
kontrol("kayma bp: BUY ucuz alınca eksi, SELL ucuz satınca artı (maliyet)", abs(g["kayma_bp"] - bek) < 1e-9, (g["kayma_bp"], bek))
kontrol("komisyon bp", abs(g["komisyon_bp"] - 0.57 / (999.5 + 499.5) * 1e4) < 1e-9, g["komisyon_bp"])
kontrol("tür sayımı (FELAKET dahil)", O["tur"] == {"TP": 4, "GIRIS": 1, "PIYASA_YEDEK": 1, "FELAKET": 1}, O["tur"])
kontrol("veri yoksa None", D.icra_ozet(db=os.path.join(T, "yok.db")) is None)
kontrol("salt okunur açılış dosyayı DEĞİŞTİRMEZ", (lambda m: (D.icra_ozet(db=db), os.path.getmtime(db) == m)[1])(os.path.getmtime(db)))

# ------------------------------------------------------------------ botta: emirler kayıt açık / kapalı / bozuk iken BİREBİR aynı
import carry_bot as cb
class _Bot:
    def __init__(s, gtx_red=False):
        s.gonderilen = []; dis = s
        class _Cc:
            @staticmethod
            def futures_symbol_ticker(symbol): return {"price": "100"}
            @staticmethod
            def futures_get_open_orders(): return []
            @staticmethod
            def futures_create_order(**k):
                dis.gonderilen.append(k)
                if gtx_red and k.get("timeInForce") == "GTX": raise RuntimeError("GTX reddedildi")
                return {"orderId": len(dis.gonderilen)}
        s.client = _Cc()
    def get_symbol_precision(s, symbol): return {"quantity_precision": 3, "price_precision": 2}
    def open_market_position(s, symbol, side, quantity):
        s.gonderilen.append({"symbol": symbol, "side": side, "type": "MARKET", "quantity": quantity}); return {"orderId": 99}

_eski = (cb.kaldirac_hazirla, cb.DOLUM_BEKLEME_SN, cb.EMIR_DB, cb.EMIR_DEFTER, cb.PIYASA_YEDEK, cb._ED.emir_kaydet)
cb.kaldirac_hazirla = lambda c, s: True; cb.DOLUM_BEKLEME_SN = 0.0; cb.PIYASA_YEDEK = True
EMR = [("AUSDT", "BUY", 1000.0), ("BUSDT", "SELL", 500.0)]
def kos(defter, red, bozuk=False):
    cb.EMIR_DEFTER = defter; cb.EMIR_DB = os.path.join(T, f"bot_{defter}_{red}_{bozuk}.db")
    if bozuk:
        def _patla(*a, **k): raise RuntimeError("disk dolu")
        cb._ED.emir_kaydet = _patla
    else:
        cb._ED.emir_kaydet = _eski[5]
    b = _Bot(gtx_red=red); n = cb._emirleri_gonder(b, EMR, {}); return n, b.gonderilen
for red in (False, True):
    a = kos(False, red); b_ = kos(True, red); z = kos(True, red, bozuk=True)
    kontrol(f"emirler kayıt kapalı / açık / bozuk iken BİREBİR aynı (GTX {'red → piyasa' if red else 'geçer'})",
            a == b_ == z, (a, b_, z))
cb.EMIR_DEFTER = True; cb.EMIR_DB = os.path.join(T, "bot_say.db"); cb._ED.emir_kaydet = _eski[5]
cb._emirleri_gonder(_Bot(), EMR, {})
cb._emirleri_gonder(_Bot(gtx_red=True), EMR, {})
rr = sqlite3.connect(cb.EMIR_DB).execute("SELECT tur, sembol, yon, adet, limit_fiyat, ref_fiyat, oid FROM emir ORDER BY id").fetchall()
kontrol("botta kayıt: 2 GIRIS (limit + ref + oid) ve 2 PIYASA_YEDEK", [r[0] for r in rr] == ["GIRIS", "GIRIS", "PIYASA_YEDEK", "PIYASA_YEDEK"]
        and rr[0][4] is not None and rr[0][5] == 100.0 and rr[0][6] == "1" and rr[2][6] == "99", rr)
cb.kaldirac_hazirla, cb.DOLUM_BEKLEME_SN, cb.EMIR_DB, cb.EMIR_DEFTER, cb.PIYASA_YEDEK, cb._ED.emir_kaydet = _eski

print("\nHEPSİ GEÇTİ" if _h == 0 else f"\n{_h} HATA"); sys.exit(1 if _h else 0)
