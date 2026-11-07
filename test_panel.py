#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 671 testleri: panel salt okunur; anahtar sızdırmaz; şifre; güvenlik başlıkları; dış arayüz şifresiz reddedilir; özet doğru."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

os.environ["TZ"] = "UTC"; __import__("time").tzset()   # madde 729: sunucu gibi UTC; panel Türkiye saatiyle (+3) gösterir
import panel
tmp = tempfile.mkdtemp(); kl = os.path.join(tmp, "carry-d1"); os.makedirs(os.path.join(kl, "defter"))
open(os.path.join(kl, "carry_bot.py"), "w").write("")
open(os.path.join(kl, ".env"), "w").write("BINANCE_MODE=demo\nBINANCE_API_KEY=GIZLIANAHTAR\nBINANCE_API_SECRET=GIZLISIR\nTELEGRAM_TOKEN=GIZLITOKEN\n")
gun = [None, 0.10, -0.05, 0.02]
with open(os.path.join(kl, "defter", "gunluk.jsonl"), "w") as f:
    for i, g in enumerate(gun):
        f.write(json.dumps({"tarih": f"2026-10-{i+1:02d}", "kitap": 1000 + i, "gun_getiri": g, "profil": "T7K", "doz": "1.15",
                            "gelir_24s": {"FUNDING_FEE": 1.0, "COMMISSION": -0.2},
                            "pozisyonlar": {"AUSDT": {"yon": "L", "usd": 100, "kar_yuzde": 1.5}}}) + "\n")
    f.write("{bozuk satır\n")
open(os.path.join(kl, "carry_bot.log"), "w").write(
    "2026-10-02 08:00:01,123 [WARNING] KOŞULLU 24 SA STOP: XUSDT 24 sa -30.0%, piyasa -5.0% -> kapatılıyor\n"
    "2026-10-02 08:00:02,000 [INFO] KOŞULLU 24 SA STOP: YUSDT 24 sa -25.0% ama piyasa -1.0% (eşik −3%) -> tutuluyor\n"
    "2026-10-03 00:00:00,000 [ERROR] tur başarısız: APIError api_key=abc123 signature=deadbeef\n"
    "2026-10-03 01:00:00,000 [INFO] sıradan satır\n")
v = panel.veri([kl], servis=False); k = v["kurulumlar"][0]
kontrol("ad ve mod", k["ad"] == "d1" and k["mod"] == "demo")
kontrol("bozuk defter satırı atlanır", len(k["seri"]) == 4)
kontrol("toplam getiri zinciri", abs(k["toplam"] - (1.10 * 0.95 * 1.02 - 1)) < 1e-9, k["toplam"])
kontrol("en büyük düşüş -5%", abs(k["dd"] + 0.05) < 1e-9, k["dd"])
kontrol("aylık", abs(k["aylik"]["2026-10"] - (1.10 * 0.95 * 1.02 - 1)) < 1e-9)
kontrol("funding / komisyon toplamı", abs(k["funding_top"] - 4.0) < 1e-9 and abs(k["komisyon_top"] + 0.8) < 1e-9)
tur = [o["tur"] for o in k["olaylar"]]
kontrol("olaylar: stop ve hata var, tutulan stop / sıradan satır yok", tur == ["hata", "stop"], tur)
kontrol("olay zamanı ve seviye ayıklandı", k["olaylar"][1]["zaman"] == "2026-10-02 11:00" and k["olaylar"][1]["metin"].startswith("KOŞULLU"), k["olaylar"][1])
js = json.dumps(v, ensure_ascii=False)
kontrol("anahtar / token / imza SIZMAZ", not any(x in js for x in ("GIZLIANAHTAR", "GIZLISIR", "GIZLITOKEN", "abc123", "deadbeef")), js[:300])
kontrol("boş klasör çökmez", panel.veri([os.path.join(tmp, "yok")], servis=False)["kurulumlar"][0]["toplam"] is None)
h = panel.statik_html(v)
kontrol("statik HTML veriyi gömer, </script> kaçışlı", '"d1"' in h and "</script>" not in json.dumps(v).replace("</", "<\\/"))

app = panel.uygulama([kl]).test_client()
r = app.get("/")
kontrol("sayfa 200 + güvenlik başlıkları", r.status_code == 200 and r.headers.get("X-Frame-Options") == "DENY"
        and "default-src 'none'" in r.headers.get("Content-Security-Policy", ""))
r = app.get("/api/veri"); kontrol("api 200 JSON", r.status_code == 200 and r.get_json()["kurulumlar"][0]["ad"] == "d1")
kontrol("yazma yolu yok (POST 405)", app.post("/api/veri").status_code == 405)
os.environ["CARRY_PANEL_SIFRE"] = "s3cret"
app = panel.uygulama([kl]).test_client()
kontrol("şifre: yoksa 401", app.get("/api/veri").status_code == 401)
import base64
yanlis = {"Authorization": "Basic " + base64.b64encode(b"carry:x").decode()}
dogru = {"Authorization": "Basic " + base64.b64encode(b"carry:s3cret").decode()}
kontrol("şifre: yanlış 401, doğru 200", app.get("/", headers=yanlis).status_code == 401 and app.get("/", headers=dogru).status_code == 200)
os.environ.pop("CARRY_PANEL_SIFRE")
kontrol("dış arayüz şifresiz REDDEDİLİR", panel.main(["--klasor", kl, "--host", "0.0.0.0"]) == 2)
kontrol("günlük takvim (yeşil / kırmızı) sayfada", "function takvim(" in panel.SAYFA and "Günlük takvim" in panel.SAYFA and ".hp" in panel.SAYFA)
out = os.path.join(tmp, "p.html")
kontrol("--disa-aktar", panel.main(["--klasor", kl, "--disa-aktar", out]) == 0 and os.path.getsize(out) > 5000)

# madde 674: aylık veri paketleri
pd_ = os.path.join(tmp, "paket"); os.makedirs(pd_)
open(os.path.join(pd_, "paket_2026-10.zip"), "wb").write(b"PK" + b"0" * 1000)
open(os.path.join(pd_, "gizli.env"), "w").write("BINANCE_API_KEY=X")
panel.PAKET_DIR = pd_
kontrol("paket listesi yalnız paket_YYYY-MM.zip", [p["ad"] for p in panel.paketler()] == ["paket_2026-10.zip"])
app = panel.uygulama([kl]).test_client()
r = app.get("/paket/paket_2026-10.zip")
kontrol("paket indirilir", r.status_code == 200 and r.data.startswith(b"PK") and "attachment" in r.headers.get("Content-Disposition", ""))
kontrol("başka dosya / yol gezintisi 404", app.get("/paket/gizli.env").status_code == 404
        and app.get("/paket/..%2F.env").status_code == 404 and app.get("/paket/paket_2026-11.zip").status_code == 404)
kontrol("api'de paketler", app.get("/api/veri").get_json()["paketler"][0]["ad"] == "paket_2026-10.zip")
# madde 680: PWA
r = app.get("/manifest.webmanifest"); m = r.get_json(force=True)
kontrol("PWA manifest", r.status_code == 200 and m["display"] == "standalone" and len(m["icons"]) == 2)
kontrol("PWA simgeler PNG", app.get("/ikon-192.png").data[:4] == b"\x89PNG" and app.get("/ikon-512.png").status_code == 200
        and app.get("/ikon-64.png").status_code == 404)
sw = app.get("/sw.js").data.decode()
kontrol("service worker veri / paket önbelleğe ALMAZ", "/api/" in sw and "/paket/" in sw and app.get("/sw.js").mimetype == "application/javascript")
kontrol("sayfada manifest bağlantısı", b'rel="manifest"' in app.get("/").data)
kontrol("CSP worker / manifest izni", "worker-src 'self'" in app.get("/").headers["Content-Security-Policy"])
# MADDE 729: Türkiye saati
kontrol("log saati UTC -> Türkiye (+3)", panel._log_zamani("2026-11-06 21:33") == "2026-11-07 00:33", panel._log_zamani("2026-11-06 21:33"))
kontrol("canlı saat Türkiye (+3)", panel._yerel(1_794_000_000).strftime("%H:%M") == "00:20", panel._yerel(1_794_000_000).strftime("%H:%M"))
kontrol("okunamayan log saati olduğu gibi", panel._log_zamani("bozuk") == "bozuk")

# MADDE 728: anlık pozisyon görüntüsü
import time as _t
kontrol("anlık dosya yoksa günlük defter", k["poz_kaynak"] == "günlük" and k["pozisyonlar"]["AUSDT"]["kar_yuzde"] == 1.5, k.get("poz_kaynak"))
_an = os.path.join(kl, "defter", "anlik.json")
json.dump({"zaman": int(_t.time()) - 60, "pozisyonlar": {"BUSDT": {"yon": "S", "usd": 50, "kar_yuzde": -2.25}},
           "gerceklesmemis_top": -1.12}, open(_an, "w"))
k2 = panel.veri([kl], servis=False)["kurulumlar"][0]
kontrol("taze anlık dosya: canlı tablo", k2["poz_kaynak"] == "canlı" and list(k2["pozisyonlar"]) == ["BUSDT"] and k2["gerceklesmemis"] == -1.12, k2.get("pozisyonlar"))
kontrol("canlı tablo getiri serisini DEĞİŞTİRMEZ", k2["seri"] == k["seri"] and k2["toplam"] == k["toplam"])
json.dump({"zaman": int(_t.time()) - panel.ANLIK_TAZE_SN - 5, "pozisyonlar": {"BUSDT": {}}}, open(_an, "w"))
kontrol("bayat anlık dosya: günlük deftere döner", panel.veri([kl], servis=False)["kurulumlar"][0]["poz_kaynak"] == "günlük")
open(_an, "w").write("{yarim")
kontrol("bozuk anlık dosya çökmez, günlük deftere döner", panel.veri([kl], servis=False)["kurulumlar"][0]["poz_kaynak"] == "günlük")
os.remove(_an)

# MADDE 730: hesap özkaynağı + sonraki dilim
_df = [{"tarih": "2026-11-06", "ozkaynak": 4991.53}, {"tarih": "2026-11-07", "ozkaynak": 4988.82, "gelir_24s": {"TRANSFER": 0}}]
_h1 = panel.hesap_ozet(_df, None)
kontrol("özkaynak ve başlangıçtan $ (defter)", _h1["ozkaynak"] == 4988.82 and _h1["kar_usd"] == -2.71 and _h1["kitap_canli"] is None, _h1)
_h2 = panel.hesap_ozet(_df, {"ozkaynak": 4988.76, "kitap": 1998.99})
kontrol("canlı özkaynak anlık dosyadan", _h2["ozkaynak"] == 4988.76 and _h2["kar_usd"] == -2.77, _h2)
# MADDE 731: kitap = 2.000 $ + kâr/zararın tamamı (ölçek 0,4 iken de)
_dk = [{"tarih": "2026-11-06", "ozkaynak": 4991.53, "kitap": 2000.11, "sermaye_olcek": 0.4007},
       {"tarih": "2026-11-07", "ozkaynak": 4988.82, "kitap": 1999.02, "sermaye_olcek": 0.4007, "gelir_24s": {"TRANSFER": 0}}]
_h3 = panel.hesap_ozet(_dk, {"ozkaynak": 4988.37, "kitap": 1998.84})
kontrol("canlı kitap = başlangıç + tüm kâr/zarar", abs(_h3["kitap_canli"] - (2000.11 - 3.16)) < 0.01 and _h3["kitap_bas"] == 2000.11
        and _h3["kar_usd"] == -3.16 and abs(_h3["kar_oran"] + 0.00158) < 1e-5, _h3)
_s3 = panel.ozet(_dk)["seri"]
kontrol("kitap serisi tüm kâr/zararı taşır", _s3[0]["kitap"] == 2000.11 and abs(_s3[1]["kitap"] - 1997.40) < 0.01, _s3)
_dk[1]["gelir_24s"]["TRANSFER"] = 1000.0; _dk[1]["ozkaynak"] += 1000.0
kontrol("transfer kitaba ölçekli payıyla girer", abs(panel.ozet(_dk)["seri"][1]["kitap"] - (1997.40 + 400.7)) < 0.01)
kontrol("ölçek 1: kitap = özkaynak", panel.ozet([{"ozkaynak": 100.0}, {"ozkaynak": 103.0, "gelir_24s": {"TRANSFER": 2}}])["seri"][1]["kitap"] == 103.0)
_df[1]["gelir_24s"]["TRANSFER"] = 100.0; _df[1]["ozkaynak"] = 5088.82
kontrol("transfer başlangıçtan kâra sayılmaz", panel.hesap_ozet(_df, None)["kar_usd"] == -2.71)
kontrol("defter / anlık yoksa boş", panel.hesap_ozet([], None) == {})
_dl = os.path.join(kl, "carry_dilimler.json")
kontrol("dilim dosyası yoksa None", panel.sonraki_dilim(kl, {}) is None)
json.dump({"sira": 2, "dilimler": {"0": {"A": 1}, "1": {"B": -1}, "2": {}}}, open(_dl, "w"))
os.utime(_dl, (1_794_000_000, 1_794_000_000))
_d = panel.sonraki_dilim(kl, {})
kontrol("sonraki dilim = son yazım + 120/15 sa", _d["zaman"] == 1_794_000_000 + 8 * 3600 and _d["saat"] == "08:20" and _d["dolu"] == 2 and _d["n"] == 15, _d)
_d = panel.sonraki_dilim(kl, {"CARRY_N_DILIM": "10", "CARRY_REBALANCE_H": "60"})
kontrol(".env dilim ayarı uygulanır", _d["zaman"] == 1_794_000_000 + 6 * 3600 and _d["n"] == 10, _d)
kontrol("panel verisinde dilim", panel.veri([kl], servis=False)["kurulumlar"][0]["dilim"]["dolu"] == 2)
kontrol("sayfada sonraki dilim kartı", b"Sonraki dilim" in app.get("/").data)
os.remove(_dl)
# MADDE 733: döküm satırı
_dk = [{"tarih": "2026-11-06", "zaman": 100, "ozkaynak": 4991.53, "kitap": 2000.11, "sermaye_olcek": 0.4007},
       {"tarih": "2026-11-07", "zaman": 200, "ozkaynak": 4988.82, "kitap": 1999.02, "sermaye_olcek": 0.4007}]
_an3 = {"ozkaynak": 4988.43, "kitap": 1998.8, "gelir_bas": {"bas": 100, "son": 300, "FUNDING_FEE": 0.0923, "COMMISSION": -0.0415,
                                                             "TRANSFER": 50.0, "INSURANCE_CLEAR": -0.01}}
_d3 = panel.hesap_ozet(_dk, _an3).get("dokum")
kontrol("döküm: funding / komisyon / gerçekleşen, transfer hariç", _d3 == {"gerceklesen": 0, "funding": 0.09, "komisyon": -0.04, "diger_gelir": -0.01}, _d3)
_an3["gelir_bas"]["bas"] = 99
kontrol("başlangıç farklı kayıttansa döküm yok", "dokum" not in panel.hesap_ozet(_dk, _an3))
kontrol("anlık yoksa döküm yok", "dokum" not in panel.hesap_ozet(_dk, None))
kontrol("sayfada döküm satırı", b"dokumYaz" in app.get("/").data)
# MADDE 734: etkin ayar log'dan
_kl2 = tempfile.mkdtemp()
kontrol("log yoksa etkin ayar None", panel.etkin_ayar(_kl2) is None)
open(os.path.join(_kl2, "carry_bot.log"), "w", encoding="utf-8").write(
    "2026-11-06 20:14:56,734 [INFO] önerilen ayar etkin: profil T5 · gross 1.00x · koşullu stop 0.05 (kitap 9000 $)\n"
    "2026-11-06 20:14:56,737 [INFO] carry_bot başladı | mod=demo | 5+5 bacak | 15 dilim | gross 1.0x | akış 20%\n"
    "2026-11-06 20:50:17,342 [INFO] önerilen ayar etkin: profil T7K · gross 1.15x · koşullu stop 0.03 (kitap 2000.04 $)\n"
    "2026-11-06 20:50:18,347 [INFO] carry_bot başladı | mod=demo | 4+4 bacak (en çok 5+5) | 15 dilim | her dilim 120sa'te bir (tur: 8sa) | gross 1.15x | akış 20%\n"
    "2026-11-06 20:51:10,177 [INFO] bakiye 2000.03 USDT | dilim 2/15 yenilendi\n")
_a = panel.etkin_ayar(_kl2)
kontrol("SON başlangıçtaki önerilen ayar", _a == {"profil": "T7K", "gross": 1.15, "stop": 0.03, "onerilen": True}, _a)
open(os.path.join(_kl2, "carry_bot.log"), "a", encoding="utf-8").write(
    "2026-11-07 10:00:00,000 [INFO] carry_bot başladı | mod=demo | 5+5 bacak | 15 dilim | gross 1.30x | akış 20%\n")
_a = panel.etkin_ayar(_kl2)
kontrol("sabit profil: önceki önerilen satırı karışmaz", _a == {"profil": None, "gross": 1.3, "stop": None, "onerilen": False}, _a)
_sy = app.get("/").data
kontrol("sayfada ayar kartı, eski 'ayar ONERILEN' başlığı yok", b"ayarKart" in _sy and b"Kitap ($) \xc2\xb7 ayar" not in _sy)
# MADDE 732: anlık fiyat (tarayıcı -> Binance herkese açık akış)
_csp = app.get("/").headers["Content-Security-Policy"]
kontrol("CSP yalnız Binance herkese açık akışı / REST", "connect-src 'self' wss://fstream.binance.com https://fapi.binance.com;" in _csp, _csp)
_sy = app.get("/").data
kontrol("sayfada markPrice akışı ve canlı hücre kimlikleri", b"@markPrice@1s" in _sy and b'id="t-${p[0]}"' in _sy and b"fapi/v1/klines" in _sy and b'id="gerc"' in _sy)

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
