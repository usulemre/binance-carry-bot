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
kontrol("funding / komisyon toplamı (ilk satırın penceresi başlangıç öncesi, sayılmaz — madde 742)", abs(k["funding_top"] - 3.0) < 1e-9 and abs(k["komisyon_top"] + 0.6) < 1e-9, (k["funding_top"], k["komisyon_top"]))
tur = [o["tur"] for o in k["olaylar"]]
kontrol("olaylar: stop, tutulan stop (madde 742) ve hata var, sıradan satır yok", tur == ["hata", "stop_tut", "stop"], tur)
kontrol("olay zamanı ve seviye ayıklandı", k["olaylar"][2]["zaman"] == "2026-10-02 11:00" and k["olaylar"][2]["metin"].startswith("KOŞULLU"), k["olaylar"][2])
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
# MADDE 738: SW dış istekleri (Binance) yakalamaz; sürüm değişti (eski SW eski CSP ile Binance'i engelliyordu)
_swj = app.get("/sw.js").data.decode()
kontrol("SW dış kaynaklı isteğe karışmaz", "u.origin!==location.origin" in _swj and "carry-kabuk-v3" in _swj)
# MADDE 740: gömülü yazı tipi + dosyadan simge; CSP font-src 'self'; önbelleğe alınabilir
_f = app.get("/font/inter-latin.woff2")
kontrol("yazı tipi sunuluyor (woff2, önbelleklenir)", _f.status_code == 200 and _f.data[:4] == b"wOF2" and "no-store" not in _f.headers.get("Cache-Control", ""), _f.headers.get("Cache-Control"))
kontrol("izin verilmeyen font yolu 404", app.get("/font/..%2Fpanel.py").status_code == 404 and app.get("/font/x.woff2").status_code == 404)
kontrol("CSP font-src self", "font-src 'self'" in app.get("/").headers["Content-Security-Policy"])
kontrol("sayfa hâlâ önbelleğe ALINMAZ", app.get("/").headers.get("Cache-Control") == "no-store")
kontrol("SW yazı tipini kabuğa alır", "font/inter-latin.woff2" in _swj)
_sy2 = app.get("/").data
kontrol("sayfada ısı haritası, funding, yıllık takvim, tema", all(x in _sy2 for x in (b"isiHarita", b"fundSatir", b"yillik(", b"temaDegis", b"bugunEgri")))
# MADDE 732: anlık fiyat (tarayıcı -> Binance herkese açık akış)
_csp = app.get("/").headers["Content-Security-Policy"]
kontrol("CSP yalnız Binance herkese açık akışı / REST", "connect-src 'self' wss://fstream.binance.com https://fapi.binance.com;" in _csp, _csp)
_sy = app.get("/").data
kontrol("sayfada markPrice akışı ve canlı hücre kimlikleri", b"@markPrice@1s" in _sy and b'id="t-${p[0]}"' in _sy and b"fapi/v1/klines" in _sy and b'id="gerc"' in _sy)

# MADDE 742: panel düzeltmeleri
# (a) getirinin ait olduğu gün: 00:05 UTC'de yazılan satır ÖNCEKİ günündür; kurulum satırı aynı gün, getirisiz
_z = lambda s: int(__import__("calendar").timegm(__import__("time").strptime(s, "%Y-%m-%d %H:%M")))
_d41 = [{"tarih": "2026-11-06", "zaman": _z("2026-11-06 20:22"), "ozkaynak": 1000.0, "gun_getiri": None,
         "gelir_24s": {"FUNDING_FEE": 5.0, "COMMISSION": -9.0}},
        {"tarih": "2026-11-07", "zaman": _z("2026-11-07 00:05"), "ozkaynak": 999.0, "gun_getiri": -0.001,
         "gelir_24s": {"FUNDING_FEE": 6.0, "COMMISSION": -9.6}},
        {"tarih": "2026-11-08", "zaman": _z("2026-11-08 00:05"), "ozkaynak": 1004.0, "gun_getiri": 0.005,
         "gelir_24s": {"FUNDING_FEE": 2.4, "COMMISSION": -2.4}}]
_o41 = panel.ozet(_d41)
kontrol("gün etiketi: 7 Kas 00:05 satırı = 6 Kas, 8 Kas satırı = 7 Kas", [s["tarih"] for s in _o41["seri"]] == ["2026-11-06", "2026-11-06", "2026-11-07"], [s["tarih"] for s in _o41["seri"]])
kontrol("son gün = 7 Kas +0,5%", _o41["son_gun_tarih"] == "2026-11-07" and _o41["bugun"] == 0.005 and _o41["gun_sayisi"] == 2, _o41)
_pay = (_z("2026-11-07 00:05") - _z("2026-11-06 20:22")) / 86400
kontrol("üst üste binen 24 sa pencereleri çift sayılmaz (oransal), ilk satır sayılmaz",
        abs(_o41["funding_top"] - (6.0 * _pay + 2.4)) < 1e-9 and abs(_o41["komisyon_top"] - (-9.6 * _pay - 2.4)) < 1e-9, (_o41["funding_top"], _o41["komisyon_top"]))
kontrol("7 / 30 gün: yeterli gün yoksa boş (yanıltmasın)", _o41["g7"] is None and _o41["g30"] is None and abs(_o41["dd"] + 0.001) < 1e-9)
_d41.append({"tarih": "2026-11-08", "zaman": _z("2026-11-08 09:00"), "ozkaynak": 1006.0, "gun_getiri": 0.002})   # gün içi elle çalıştırma
_o41 = panel.ozet(_d41)
kontrol("aynı güne düşen iki getiri tek günde birleşir", len(_o41["seri"]) == 4 and _o41["seri"][-1]["tarih"] == "2026-11-08"
        and abs(_o41["seri"][-2]["gun"] - 0.005) < 1e-12, [(s["tarih"], s["gun"]) for s in _o41["seri"]])
_d42 = [{"tarih": f"2026-10-{i+1:02d}", "zaman": _z(f"2026-10-{i+1:02d} 00:05"), "ozkaynak": 100.0, "gun_getiri": None if i == 0 else 0.01} for i in range(9)]
_o42 = panel.ozet(_d42)
kontrol("7 gün: 8 günlük veride son 7 günün getirisi", abs(_o42["g7"] - (1.01 ** 7 - 1)) < 1e-9 and _o42["g30"] is None, _o42["g7"])
# (b) gün içi kitap eğrisi
_kl3 = tempfile.mkdtemp(); os.makedirs(os.path.join(_kl3, "defter"))
_gb = 1_794_009_600   # 2026-11-07 00:00 UTC
kontrol("gün eğrisi dosyası yoksa None", panel.gun_egri(_kl3, _gb + 3600) is None)
json.dump({"gun": "2026-11-07", "nok": [[_gb, 5000.0], [_gb + 300, 5001.5], [_gb + 600, 4999.0]]}, open(os.path.join(_kl3, "defter", "anlik_gun.json"), "w"))
_ge = panel.gun_egri(_kl3, _gb + 700)
kontrol("gün eğrisi: gün başına göre $ fark", _ge == {"bas": _gb, "ilk": _gb, "nok": [[_gb, 0.0], [_gb + 300, 1.5], [_gb + 600, -1.0]]}, _ge)
kontrol("başka günün dosyası kullanılmaz", panel.gun_egri(_kl3, _gb + 86400 + 60) is None)
open(os.path.join(_kl3, "defter", "anlik_gun.json"), "w").write("{bozuk")
kontrol("bozuk gün dosyası çökmez", panel.gun_egri(_kl3, _gb + 700) is None)
_sy3 = app.get("/").data.decode()
kontrol("bugün eğrisi kitaptan (gun_egri), açık pozisyonları 03:00'ten tutulmuş saymaz", "k.gun_egri" in _sy3 and "p.miktar * (f - N[0][1])" not in _sy3)
# (c) olaylar: her ERROR, kâr al, piyasa emri, dilim turu; tutulan stop günde bir
_kl4 = tempfile.mkdtemp()
open(os.path.join(_kl4, "carry_bot.log"), "w", encoding="utf-8").write(
    "2026-11-06 17:54:58,372 [ERROR] KÂR AL EMRİ KONULAMADI: 8/8 pozisyon KORUMASIZ (AUSDT)\n"
    "2026-11-06 18:14:45,801 [ERROR] TACUSDT ÇAPRAZ teminata alınamadı (APIError(code=-4067))\n"
    "2026-11-06 20:22:33,409 [INFO] KOŞULLU 24 SA STOP: AINUSDT 24 sa -60.2% ama piyasa +0.7% (eşik −3%) -> tutuluyor\n"
    "2026-11-06 20:58:06,956 [INFO] KOŞULLU 24 SA STOP: AINUSDT 24 sa -60.2% ama piyasa +0.7% (eşik −3%) -> tutuluyor\n"
    "2026-11-07 05:05:33,882 [WARNING] dolum kontrolü 2: 1 emir dolmadı - PİYASA emrine düşülüyor\n"
    "2026-11-07 05:06:00,000 [INFO] bakiye 2001.00 USDT | dilim 3/15 yenilendi | 12 pozisyon | LONG funding ort %-5/yıl\n"
    "2026-11-07 06:00:00,000 [INFO] KÂR AL doldu: AINUSDT - eski dilimlerden çıkarıldı\n"
    "2026-11-07 06:00:01,000 [INFO] MERDİVEN doldu (%50'i kapandı; long +%45 / short −%15): AINUSDT - hedefler küçültüldü\n"
    "2026-11-07 07:00:00,000 [INFO] evren: 30 sembol\n")
_t4 = [o["tur"] for o in panel.olaylar(_kl4)]
kontrol("olaylar: ERROR satırları, kâr al, piyasa emri, dilim turu; tutulan stop günde bir",
        _t4 == ["tp", "tp", "tur", "uyari", "stop_tut", "hata", "hata"], _t4)
# (d) ayar kartı: koşullu stopun coin eşiği
open(os.path.join(kl, ".env"), "a").write("CARRY_LONG_24S=0.40\n")
open(os.path.join(kl, "carry_bot.log"), "a").write(
    "2026-11-06 20:50:17,342 [INFO] önerilen ayar etkin: profil T7K · gross 1.15x · koşullu stop 0.03 (kitap 2000.04 $)\n"
    "2026-11-06 20:50:18,347 [INFO] carry_bot başladı | mod=demo | 4+4 bacak | 15 dilim | gross 1.15x | akış 20%\n")
_ay = panel.veri([kl], servis=False)["kurulumlar"][0]["ayar"]
kontrol("ayarda koşullu stopun coin eşiği (.env)", _ay["coin_esik"] == 0.40 and _ay["stop"] == 0.03, _ay)
kontrol("ayar kartı stopu açık yazar ('koşullu stop %3' değil)", "stop: coin −%" in _sy3 and "koşullu stop %${" not in _sy3)

# MADDE 743: haftalık log rotasyonu (copytruncate) sonrası ayar ve olaylar kaybolmaz
import gzip
_kl5 = tempfile.mkdtemp()
_eski = ("2026-11-06 20:50:17,342 [INFO] önerilen ayar etkin: profil T7K · gross 1.15x · koşullu stop 0.03 (kitap 2000.04 $)\n"
         "2026-11-06 20:50:18,347 [INFO] carry_bot başladı | mod=demo | 4+4 bacak | 15 dilim | gross 1.15x | akış 20%\n"
         "2026-11-07 21:18:00,000 [INFO] KÂR AL doldu: AUSDT - eski dilimlerden çıkarıldı\n")
with gzip.open(os.path.join(_kl5, "carry_bot.log.1.gz"), "wt", encoding="utf-8") as f:
    f.write(_eski)
open(os.path.join(_kl5, "carry_bot.log"), "w").write("")   # rotasyon: güncel dosya boşaltıldı
kontrol("rotasyon sonrası etkin ayar .1.gz'den", panel.etkin_ayar(_kl5) == {"profil": "T7K", "gross": 1.15, "stop": 0.03, "onerilen": True}, panel.etkin_ayar(_kl5))
open(os.path.join(_kl5, "carry_bot.log"), "w").write("2026-11-08 00:05:00,000 [ERROR] tur başarısız: x\n")
kontrol("rotasyon sonrası olaylar: eski + yeni dosya", [o["tur"] for o in panel.olaylar(_kl5)] == ["hata", "tp", "basla", "ayar"], [o["tur"] for o in panel.olaylar(_kl5)])
os.remove(os.path.join(_kl5, "carry_bot.log.1.gz")); open(os.path.join(_kl5, "carry_bot.log.1"), "w").write(_eski)
kontrol("sıkıştırılmamış .1 de okunur", panel.etkin_ayar(_kl5)["gross"] == 1.15)
kontrol("son_bayt sınırı eski dosyaya da uygulanır", len("\n".join(panel.log_satirlari(_kl5, 120))) <= 121)
kontrol("hiç log yoksa None", panel.log_satirlari(tempfile.mkdtemp(), 1000) is None)
kontrol("bugün grafiğinde en küçük dikey aralık", "minAralik" in app.get("/").data.decode())

# MADDE 744: döküm satırında "gerçek oranlarla olsaydı"
_dk7 = [{"tarih": "2026-11-06", "zaman": 100, "ozkaynak": 5000.0, "kitap": 2000.0, "sermaye_olcek": 0.4}]
_an7 = {"ozkaynak": 5001.0, "kitap": 2000.4, "gelir_bas": {"bas": 100, "son": 300, "FUNDING_FEE": 0.1786},
        "gercek_funding": {"bas": 100, "toplam": 0.3953, "son": 300}}
kontrol("döküm: gerçek oranlı funding", panel.hesap_ozet(_dk7, _an7)["dokum"].get("funding_gercek") == 0.4, panel.hesap_ozet(_dk7, _an7)["dokum"])
_an7["gercek_funding"]["bas"] = 99
kontrol("başlangıç farklıysa gerçek oranlı satır yok", "funding_gercek" not in panel.hesap_ozet(_dk7, _an7)["dokum"])
_an7.pop("gercek_funding")
kontrol("canlı hesapta (satır yok) döküm yine çalışır", "funding_gercek" not in panel.hesap_ozet(_dk7, _an7)["dokum"])
kontrol("sayfada gerçek oran satırı, toplama girmez", "gerçek Binance oranlarıyla olsaydı" in app.get("/").data.decode() and "Toplama girmez" in app.get("/").data.decode())

# MADDE 745: olaylarda işlemler (emir defteri + pozisyon geçmişi), salt okunur
import defter_db as _DB, sqlite3 as _sq, time as _tm
_k745 = os.path.join(tmp, "carry-i1"); os.makedirs(os.path.join(_k745, "defter")); _db745 = os.path.join(_k745, "defter", "carry.db")
_t = _tm.time() - 3600
_DB.emir_kaydet("GIRIS", "CYBERUSDT", "BUY", 55.8, db=_db745, simdi=_t, oid="1")
_DB.emir_kaydet("PIYASA_YEDEK", "ONEUSDT", "SELL", 1500, db=_db745, simdi=_t + 60, oid="2")
_DB.emir_kaydet("GIRIS", "HYPEUSDT", "SELL", 1, db=_db745, simdi=_tm.time() - 200, oid="3")
_c = _sq.connect(_db745)
_c.execute("UPDATE emir SET durum='FILLED', dolan=55.8, ort_fiyat=0.3103, maker_adet=55.8, komisyon=0.003 WHERE oid='1'")
_c.execute("UPDATE emir SET durum='FILLED', dolan=1500, ort_fiyat=0.0115, maker_adet=0, komisyon=0.007 WHERE oid='2'"); _c.commit(); _c.close()
json.dump({"s": {"CYBERUSDT": [[int(_t) - 86400, 159.1, 0.3458], [int(_t) + 300, 214.9, 0.3365]]}},
          open(os.path.join(_k745, "defter", "anlik_poz.json"), "w"))
_i = panel.islemler(_k745)
_cy = [x for x in _i["liste"] if x["sembol"] == "CYBER"][0]; _on = [x for x in _i["liste"] if x["sembol"] == "ONE"][0]
kontrol("işlem: dolum fiyatı / adet / maker", _cy["fiyat"] == 0.3103 and _cy["adet"] == 55.8 and _cy["maker"] is True and _on["maker"] is False)
kontrol("işlem: SONRAKİ görüntüden ortalama ve pozisyon", _cy["ort_sonra"] == 0.3365 and _cy["poz_sonra"] == 214.9, _cy)
kontrol("işlem: geçmişi olmayan coinde ortalama yok (hata yok)", "ort_sonra" not in _on)
kontrol("işlem: eşlenmemiş emir 'bekleyen' sayılır, listede yok", _i["bekleyen"] == 1 and len(_i["liste"]) == 2, _i)
json.dump({"s": {"CYBERUSDT": [[int(_t) + 5000, 214.9, 0.3365]]}}, open(os.path.join(_k745, "defter", "anlik_poz.json"), "w"))
_cy2 = [x for x in panel.islemler(_k745)["liste"] if x["sembol"] == "CYBER"][0]
kontrol("işlem: geç görüntü (kayıt başlamadan önceki işlem) ortalama GÖSTERMEZ", "ort_sonra" not in _cy2 and _cy2.get("kayit_yok"), _cy2)
kontrol("işlem: yeni → eski sıralı", _i["liste"][0]["sembol"] == "ONE")
kontrol("işlem: veritabanı yoksa boş", panel.islemler(os.path.join(tmp, "yok")) == {"liste": [], "bekleyen": 0})
kontrol("sayfada işlem tablosu", "islemTablo" in app.get("/").data.decode())

# MADDE 746: funding sonrası hızlı yenileme
_sy6 = app.get("/").data.decode()
kontrol("funding anı geçince veri hemen yeniden istenir", "function fundTakip(" in _sy6 and "fundTakip();" in _sy6)
_tm = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy", "carry-anlik-funding.timer")).read()
kontrol("funding sonrası ek zamanlayıcı anlık servisi çalıştırır", "Unit=carry-anlik.service" in _tm and "*:00:40 UTC" in _tm)
kontrol("kurulum betiği ek zamanlayıcıyı kurar", "carry-anlik-funding.timer" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy", "sunucu_kur.sh")).read())

# MADDE 748: sayaç tahmini yalnız o saatte ödeyenler; demoda demo hesap satırı
_sy8 = app.get("/").data.decode()
kontrol("funding tahmini yalnız sıradaki saatte ödeyen pozisyonlar", "Math.abs(F.T - T) < 60e3" in _sy8)
kontrol("demoda demo hesabın sıradaki funding satırı", "demo hesap: " in _sy8 and "k.demo_funding" in _sy8)
json.dump({"zaman": int(__import__("time").time()) - 30, "pozisyonlar": {"BUSDT": {"yon": "S", "usd": 50, "miktar": -5, "giris": 10, "isaret": 10}},
           "gerceklesmemis_top": 0, "demo_funding": {"T": 1800003600, "tahmin": 0.12, "n": 3}}, open(os.path.join(kl, "defter", "anlik.json"), "w"))
kontrol("panel verisinde demo funding", panel.veri([kl], servis=False)["kurulumlar"][0].get("demo_funding", {}).get("n") == 3)
os.remove(os.path.join(kl, "defter", "anlik.json"))

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
