#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 671 testleri: panel salt okunur; anahtar sızdırmaz; şifre; güvenlik başlıkları; dış arayüz şifresiz reddedilir; özet doğru."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

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
kontrol("olay zamanı ve seviye ayıklandı", k["olaylar"][1]["zaman"] == "2026-10-02 08:00" and k["olaylar"][1]["metin"].startswith("KOŞULLU"), k["olaylar"][1])
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
out = os.path.join(tmp, "p.html")
kontrol("--disa-aktar", panel.main(["--klasor", kl, "--disa-aktar", out]) == 0 and os.path.getsize(out) > 5000)

print(f"\n{'HEPSİ GEÇTİ' if _h == 0 else f'{_h} HATA'}")
sys.exit(1 if _h else 0)
