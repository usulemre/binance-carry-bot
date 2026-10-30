#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 670 testleri: Telegram bildirimi (ayarsızsa sessiz, asla hata fırlatmaz, tekrar kısma, token loga yazılmaz),
botun stop / delist / tur hatası kancaları, günlük özet metni, nabız (servis düştü / takıldı / düzeldi / devre dışı atlanır)."""
import os, sys, json, tempfile, time, logging, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CARRY_PROFIL", "T4")
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

tmp = tempfile.mkdtemp()
os.environ["CARRY_BILDIRIM_DURUM"] = os.path.join(tmp, "bd.json")
import importlib, bildirim
importlib.reload(bildirim)

class R:
    def __init__(s, kod=200): s.status_code = kod
class Req:
    def __init__(s, kod=200, hata=None): s.cagri = []; s.kod = kod; s.hata = hata
    def post(s, url, data=None, files=None, timeout=None):
        if s.hata: raise s.hata
        s.cagri.append((url, data, files)); return R(s.kod)

for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"): os.environ.pop(k, None)
r = Req()
kontrol("ayarsız: gönderilmez, False", bildirim.gonder("x", _requests=r) is False and not r.cagri)
os.environ["TELEGRAM_TOKEN"] = "123:GIZLI"; os.environ["TELEGRAM_CHAT_ID"] = "42"; os.environ["CARRY_BILDIRIM_AD"] = "demo-1"
r = Req()
kontrol("ayarlı: sendMessage", bildirim.gonder("merhaba", _requests=r) and r.cagri and r.cagri[0][0].endswith("/sendMessage"))
kontrol("önek [demo-1] ve chat id", r.cagri[0][1]["text"].startswith("[demo-1] merhaba") and r.cagri[0][1]["chat_id"] == "42")
kontrol("normal mesaj sessiz bildirim", r.cagri[0][1]["disable_notification"] is True)
r = Req(); bildirim.gonder("çöktü", acil=True, _requests=r)
kontrol("acil: 🚨 ve sesli", r.cagri[0][1]["text"].startswith("🚨 [demo-1]") and r.cagri[0][1]["disable_notification"] is False)
r = Req(); bildirim.gonder("a" * 9000, _requests=r)
kontrol("4096 sınırı", len(r.cagri[0][1]["text"]) <= 4000)
r = Req()
a1 = bildirim.gonder("tekrar", anahtar="k1", kisma_sn=3600, _requests=r)
a2 = bildirim.gonder("tekrar", anahtar="k1", kisma_sn=3600, _requests=r)
kontrol("kısma: aynı anahtar 1 sa içinde bir kez", a1 and not a2 and len(r.cagri) == 1)
kontrol("başka anahtar kısılmaz", bildirim.gonder("b", anahtar="k2", kisma_sn=3600, _requests=r))
# başarısız gönderim kısma işareti koymaz (sonra yeniden denenir)
r = Req(kod=500); bildirim.gonder("c", anahtar="k3", kisma_sn=3600, _requests=r)
r2 = Req(); kontrol("HTTP 500 -> işaretlenmez, sonra tekrar denenir", bildirim.gonder("c", anahtar="k3", kisma_sn=3600, _requests=r2))
# istisna yutulur, token loga yazılmaz
akis = io.StringIO(); hnd = logging.StreamHandler(akis); logging.getLogger("bildirim").addHandler(hnd)
ok = bildirim.gonder("d", _requests=Req(hata=ConnectionError("https://api.telegram.org/bot123:GIZLI/sendMessage reset")))
logging.getLogger("bildirim").removeHandler(hnd)
kontrol("ağ hatası: istisna yok, False", ok is False)
kontrol("token loga YAZILMAZ", "GIZLI" not in akis.getvalue(), akis.getvalue())
# bozuk durum dosyası
open(os.environ["CARRY_BILDIRIM_DURUM"], "w").write("{bozuk")
kontrol("bozuk durum dosyası: yine gönderir", bildirim.gonder("e", anahtar="k9", kisma_sn=60, _requests=Req()))
# dosya gönderimi
pdf = os.path.join(tmp, "r.pdf"); open(pdf, "wb").write(b"%PDF")
r = Req(); bildirim.gonder("rapor", dosya=pdf, _requests=r)
kontrol("dosya: sendDocument", r.cagri[0][0].endswith("/sendDocument") and "document" in r.cagri[0][2])

# günlük özet
k = {"tarih": "2026-10-30", "ozkaynak": 2050.0, "kitap": 2050.0, "gun_getiri": 0.0123, "profil": "T7K", "doz": "1.15",
     "gelir_24s": {"FUNDING_FEE": 3.2, "REALIZED_PNL": -1.1, "COMMISSION": -0.4, "TRANSFER": -30.0},
     "pozisyonlar": {"AUSDT": {"yon": "L"}, "BUSDT": {"yon": "S"}, "CUSDT": {"yon": "S"}},
     "degisim": {"acilan": ["CUSDT"], "kapanan": []}}
m = bildirim.gunluk_ozet_metni(k)
kontrol("özet: getiri, funding, sayılar", "+1.23%" in m and "+3.20" in m and "1 long / 2 short" in m and "T7K 1.15x" in m, m)
kontrol("özet: transfer ayrı", "transfer -30.00" in m)
k["gun_getiri"] = None; kontrol("özet: ilk gün —", "gün —" in bildirim.gunluk_ozet_metni(k))

# bot kancaları
import carry_bot as cb
gel = []
cb._bildir = lambda metin, **kw: gel.append((metin, kw))
class C:
    def __init__(s, hata=False): s.hata = hata; s.client = s
    def close_position(s, *a):
        if s.hata: raise RuntimeError("x")
    def get_open_positions(s): return [{"symbol": "AAAUSDT", "positionAmt": "5"}]
    def futures_cancel_all_open_orders(s, symbol): pass
durum = {"dilimler": {"0": {"AAAUSDT": 1}}}
cb.felaket_simdi_kapat(C(), durum, "AAAUSDT", 5)
kontrol("stop kapandı -> bildirim", gel and "AAAUSDT" in gel[-1][0] and not gel[-1][1].get("acil"))
cb.felaket_simdi_kapat(C(hata=True), durum, "AAAUSDT", 5)
kontrol("stop KAPATILAMADI -> acil", gel[-1][1].get("acil") is True)
eski_bilgi = cb.sembol_bilgisi
cb.sembol_bilgisi = lambda c: {"AAAUSDT": {"symbol": "AAAUSDT", "status": "TRADING", "contractType": "PERPETUAL",
                                           "deliveryDate": time.time() * 1000 + 3600e3}}
n = len(gel); cb.delist_kapat(C(), {"dilimler": {}})
kontrol("delist kapandı -> bildirim", len(gel) == n + 1 and "DELİST" in gel[-1][0])
n = len(gel); cb.delist_kapat(C(), {"dilimler": {}}, dry_run=True)
kontrol("delist dry-run -> bildirim yok", len(gel) == n)
cb.sembol_bilgisi = eski_bilgi

# nabız
import nabiz
kok = os.path.join(tmp, "opt"); os.makedirs(os.path.join(kok, "carry")); os.makedirs(os.path.join(kok, "carry-d1"))
for d in ("carry", "carry-d1"):
    open(os.path.join(kok, d, "carry_bot.py"), "w").write("")
    open(os.path.join(kok, d, ".env"), "w").write("BINANCE_API_KEY=abc\nTELEGRAM_TOKEN=t\nTELEGRAM_CHAT_ID=1\n")
    open(os.path.join(kok, d, "carry_bot.log"), "w").write("x")
kontrol("kurulumlar bulunur", [s for _, s in nabiz.kurulumlar(kok)] == ["carry", "carry@d1"])
durumlar = {"carry": ("enabled", "active"), "carry@d1": ("enabled", "active")}
def sc(komut, servis):
    e, a = durumlar[servis]; return e if komut == "is-enabled" else a
giden = []
def gon(kl, metin, acil): giden.append((os.path.basename(kl), metin, acil)); return True
kontrol("hepsi sağlıklı: mesaj yok", nabiz.calistir(kok, gon, sc) == 0 and not giden)
durumlar["carry@d1"] = ("enabled", "failed")
kontrol("servis düştü: uyarı", nabiz.calistir(kok, gon, sc) == 1 and giden and giden[-1][0] == "carry-d1" and giden[-1][2])
n = len(giden); nabiz.calistir(kok, gon, sc)
kontrol("aynı sorun 12 sa içinde tekrar gönderilmez", len(giden) == n)
nabiz.calistir(kok, gon, sc, simdi=time.time() + 13 * 3600)
kontrol("12 sa sonra yeniden hatırlatır", sum(1 for g in giden[n:] if g[0] == "carry-d1") == 1)
for d in ("carry", "carry-d1"): open(os.path.join(kok, d, "carry_bot.log"), "w").write("x")
json.dump({}, open(os.path.join(kok, "carry", "nabiz_durum.json"), "w"))
durumlar["carry@d1"] = ("enabled", "active")
nabiz.calistir(kok, gon, sc)
kontrol("düzeldi mesajı", "düzeldi" in giden[-1][1] and not giden[-1][2])
n = len(giden); nabiz.calistir(kok, gon, sc)
kontrol("düzeldi bir kez", len(giden) == n)
eski = time.time() - 20 * 3600
os.utime(os.path.join(kok, "carry", "carry_bot.log"), (eski, eski))
nabiz.calistir(kok, gon, sc)
kontrol("20 sa tur yok: takıldı uyarısı", giden[-1][0] == "carry" and "tur yok" in giden[-1][1])
durumlar["carry"] = ("disabled", "inactive")
kontrol("devre dışı servis atlanır", nabiz.kontrol(os.path.join(kok, "carry"), "carry", sc) == [])
open(os.path.join(kok, "carry-d1", ".env"), "w").write("BINANCE_API_KEY=BURAYA\n")
durumlar["carry@d1"] = ("enabled", "failed")
kontrol("anahtarsız kurulum atlanır", nabiz.kontrol(os.path.join(kok, "carry-d1"), "carry@d1", sc) == [])

# nabız -> telegram: kurulumun .env'inden yalnız TELEGRAM_* (Binance anahtarı ortama girmez)
os.environ.pop("BINANCE_API_KEY", None)
cag = []
bildirim.gonder = lambda metin, **kw: cag.append((metin, os.environ.get("CARRY_BILDIRIM_AD"))) or True
nabiz._telegram(os.path.join(kok, "carry-d1"), "x", True)
open(os.path.join(kok, "carry", ".env"), "w").write("BINANCE_API_KEY=GIZLI\nTELEGRAM_TOKEN=t\nTELEGRAM_CHAT_ID=1\n")
nabiz._telegram(os.path.join(kok, "carry"), "y", True)
kontrol("nabız: kurulum adı önek", cag[0][1] == "d1" and cag[1][1] == "demo", cag)
kontrol("nabız: Binance anahtarı ortama girmez", "BINANCE_API_KEY" not in os.environ)

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
