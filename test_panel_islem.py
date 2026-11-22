"""MADDE 834 — panelden işlem uçtan uca: gerçek Chromium -> panel (anahtarsız) -> carry_islem kapısı (SAHTE borsa).

Denenenler: işlem açıkken coin adı al / sat penceresini açar; önizleme; PIN'siz gönder düğmesi kapalı; yanlış PIN hatası;
doğru PIN'le emir (panel_ önekli, TP dahil); pozisyon görünür; %50 kapat (onay penceresi); TP / stop güncelleme; CSRF (başlıksız /
başka kökenli POST reddedilir); kapı çalışmıyorsa coin adı yine Binance'e gider. Playwright yoksa atlanır.
İsteğe bağlı: ISLEM_EKRAN=<yol> ile telefon ekran görüntüsü.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time

sys.path.insert(0, ".")
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("playwright yok - panel işlem tarayıcı testi ATLANDI")
    sys.exit(0)

os.environ["TZ"] = "UTC"; time.tzset()
import panel
import carry_islem as ci
import carry_elle as ce
from test_carry_islem import SahteClient     # noqa: E402  (aynı sahte borsa; içe aktarınca o test de koşar)

basarisiz = []


def kontrol(ad, kosul, detay=""):
    print(f"  [{'OK' if kosul else 'HATA'}]   {ad}" + ("" if kosul else f"  {detay}"))
    if not kosul:
        basarisiz.append(ad)


def bos_port():
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0)); return so.getsockname()[1]


tmp = tempfile.mkdtemp(); kl = os.path.join(tmp, "carry-d1"); os.makedirs(os.path.join(kl, "defter"))
open(os.path.join(kl, "carry_bot.py"), "w").write("")
open(os.path.join(kl, ".env"), "w").write("BINANCE_MODE=demo\n")
with open(os.path.join(kl, "defter", "gunluk.jsonl"), "w") as f:
    f.write(json.dumps({"tarih": "2026-11-01", "kitap": 1000, "gun_getiri": 0.0, "pozisyonlar": {}}) + "\n")

from waitress import create_server
SC = SahteClient()
bil = []
KAPI = ci.Kapi(SC, {"acik": True, "pin": "482913", "max_usd": 200.0, "mod": "demo", "canli_izin": False, "elle": True,
                    "defter": os.path.join(tmp, "panel_islem.jsonl")}, bildir=bil.append)
P_KAPI, P_PANEL = bos_port(), bos_port()
s_kapi = create_server(ci.uygulama(lambda: KAPI), host="127.0.0.1", port=P_KAPI, threads=2)
threading.Thread(target=s_kapi.run, daemon=True).start()
panel.ISLEM_URL = f"http://127.0.0.1:{P_KAPI}"
s_panel = create_server(panel.uygulama([kl]), host="127.0.0.1", port=P_PANEL, threads=4)
threading.Thread(target=s_panel.run, daemon=True).start()
time.sleep(0.5)
URL = f"http://127.0.0.1:{P_PANEL}"

EI = {"symbols": [{"symbol": "AKEUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"}]}
T24 = [{"symbol": "AKEUSDT", "lastPrice": "0.5", "priceChangePercent": "-12.0", "quoteVolume": "50000000"}]
PI = [{"symbol": "AKEUSDT", "lastFundingRate": "-0.001", "nextFundingTime": 1}]


def kur(page):
    def fapi(route):
        u = route.request.url
        if "klines" in u:      # 120 saatlik mum, şimdiye kadar, 0,46-0,52 arası dalga
            import math
            simdi = int(time.time() // 3600 * 3600 * 1000); body = []
            for i in range(120):
                t = simdi - (119 - i) * 3600_000; c = 0.49 + 0.03 * math.sin(i / 9); o_ = c - 0.004 * math.cos(i / 3)
                body.append([t, str(o_), str(max(o_, c) + 0.003), str(min(o_, c) - 0.003), str(c), "0", t + 3599_999])
        else:
            body = EI if "exchangeInfo" in u else T24 if "ticker/24hr" in u else PI if "premiumIndex" in u else []
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body), headers={"Access-Control-Allow-Origin": "*"})
    page.route("https://fapi.binance.com/**", fapi)
    page.route("https://cdnjs.cloudflare.com/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=""))
    page.route_web_socket("wss://fstream.binance.com/**", lambda ws: None)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page = ctx.new_page(); kur(page)
    hatalar = []; page.on("pageerror", lambda e: hatalar.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL + "/#piyasa"); page.wait_for_selector(".pyr a")
    page.wait_for_function("() => ISL_DURUM && ISL_DURUM.acik", timeout=5000)
    print("1) pencere")
    page.evaluate("() => piyasaBoya(true)")
    a = page.locator(".pyr a", has_text="AKE").first
    kontrol("işlem açıkken coin adı Binance'e değil pencereye gider", a.get_attribute("href") == "#piyasa")
    kontrol("altta açıklama: demo, 200 $, PIN", "demo hesap" in page.locator("#icerik").inner_text() and "200 $" in page.locator("#icerik").inner_text())
    a.click(); page.wait_for_selector(".isl")
    page.wait_for_selector("#isltah")
    kontrol("pencere açıldı: pozisyon yok -> doğrudan yeni emir, DEMO rozeti", "DEMO" in page.locator("#islic").inner_text()
            and page.locator(".isl .itab button").count() == 1)
    page.wait_for_selector("#islgraf svg rect", timeout=5000)
    kontrol("grafik: mumlar çizildi (120)", page.locator("#islgraf svg rect.igub, #islgraf svg rect.igdb").count() == 120)
    print("2) önizleme + PIN")
    page.locator(".isl .ichip button", has_text="100 $").click()
    page.locator(".isl .ichip button", has_text="+5%").first.click()
    kontrol("TP +%5 hesap fiyatından dolduruldu (0,525)", page.locator(".isl input").nth(1).input_value() in ("0.525", "0.525000"),
            page.locator(".isl input").nth(1).input_value())
    page.locator(".isl .ibtn.ikinci").click()
    page.wait_for_selector("#isloniz .iozt")
    kontrol("önizleme: adet 200, değer ≈ 100 $, TP'de kâr", "200" in page.locator("#isloniz").inner_text()
            and "TP" in page.locator("#isloniz").inner_text(), page.locator("#isloniz").inner_text())
    kontrol("canlı tahmin: adet + TP kârı + risk/ödül yok (stop yok)", "adet" in page.locator("#isltah").inner_text()
            and "TP'de" in page.locator("#isltah").inner_text())
    kontrol("grafikte plan TP çizgisi", page.locator("#islgraf g.igad.tp").count() >= 1)
    kontrol("PIN yokken gönder kapalı", page.locator("#islgonder").is_disabled())
    kontrol("önizleme hiçbir emir göndermedi", SC.client.emirler == [])
    page.fill("#islpin", "111111")
    page.locator("#islgonder").click()
    page.wait_for_selector(".isl .imsj.hata")
    kontrol("yanlış PIN hatası gösterildi, emir yok", "PIN yanlış" in page.locator(".isl .imsj").inner_text() and SC.client.emirler == [])
    print("3) emir")
    page.locator(".isl .ibtn.ikinci").click(); page.wait_for_selector("#isloniz .iozt")
    page.fill("#islpin", "482913")
    kontrol("doğru uzunlukta PIN ile gönder açık", not page.locator("#islgonder").is_disabled())
    page.locator("#islgonder").click()
    page.wait_for_selector(".isl .imsj", timeout=8000)
    kontrol("emir başarı mesajı", page.locator(".isl .imsj").get_attribute("class").endswith("ok"), page.locator(".isl .imsj").inner_text())
    e = SC.client.emirler[-1]
    kontrol("borsaya MARKET BUY 200 adet gitti", e["type"] == "MARKET" and e["side"] == "BUY" and e["quantity"] == 200, e)
    kontrol("emir panel_ önekli -> bot coini kullanıcıya bırakır", ce.emir_sahibi({"clientOrderId": e["newClientOrderId"]}) == "kullanici")
    kontrol("TP konuldu (0.52500)", any(x["type"] == "TAKE_PROFIT_MARKET" and x["triggerPrice"] == "0.52500" for x in SC.client.algolar))
    kontrol("Telegram bildirimi", bil and "AKE LONG" in bil[-1])
    page.wait_for_selector(".isl .ipoz", timeout=6000)
    kontrol("emirden sonra Pozisyon sekmesine geçti: LONG 200 adet, TP görünüyor",
            "LONG" in page.locator(".ipoz").inner_text() and "200" in page.locator(".ipoz").inner_text() and "0,525" in page.locator(".ipoz").inner_text(),
            page.locator(".ipoz").inner_text())
    page.evaluate("() => islGrafikCiz()")
    kontrol("grafikte GİRİŞ çizgisi + etiketi", page.locator("#islgraf line.igl.gir").count() == 1 and page.locator("#islgraf g.igad.gir").count() == 1)
    kontrol("grafikte TP çizgisi (kurulu emir)", page.locator("#islgraf line.igl.tp").count() >= 1)
    kontrol("grafikte alış işareti ▲ (dolum)", page.locator("#islgraf path.igal").count() >= 1)
    kontrol("likidasyon (0,21) grafik aralığının çok dışında: çizgi yok, kenarda ↓ etiketi", page.locator("#islgraf line.igl.lik").count() == 0
            and "↓" in page.locator("#islgraf g.ige.lik").text_content())
    print("4) yarısını kapat + TP / stop güncelle")
    page.locator(".isl .iseg button", has_text="%50").click()
    page.wait_for_function("() => document.querySelector('.isl .imsj') && document.querySelector('.isl .imsj').innerText.includes('Kapatıldı')", timeout=5000)
    kontrol("%50 kapat: SELL reduceOnly 100 adet", SC.client.emirler[-1]["side"] == "SELL" and SC.client.emirler[-1]["quantity"] == 100
            and SC.client.emirler[-1]["reduceOnly"] == "true")
    page.wait_for_function("() => document.querySelector('.ipoz') && document.querySelector('.ipoz').innerText.includes('100')", timeout=5000)
    page.locator(".isl input[placeholder='Stop fiyatı']").fill("0.45")
    kontrol("stop yazınca grafikte plan stop çizgisi", page.locator("#islgraf line.igl.sl").count() >= 1)
    page.locator(".isl .iseg button", has_text="TP / stop kaydet").click()
    page.wait_for_function("() => document.querySelector('.isl .imsj') && document.querySelector('.isl .imsj').innerText.includes('kaydedildi')", timeout=5000)
    kontrol("stop 0.45 kuruldu (100 adet)", any(x["type"] == "STOP_MARKET" and x["triggerPrice"] == "0.45000" and x["quantity"] == 100
                                               for x in SC.client.algolar))
    if os.getenv("ISLEM_EKRAN"):
        kok = os.getenv("ISLEM_EKRAN").rsplit(".", 1)[0]
        time.sleep(1.5); page.evaluate("() => { document.querySelector('.shp').scrollTop = 0; islGrafikCiz(); }")
        page.screenshot(path=kok + "_poz.png")
        page.locator(".isl .itab button", has_text="Ekle").click()
        page.locator(".isl input[placeholder='zarar durdur'], .isl .ipara input").first.fill("100")
        page.evaluate("() => { ISL.tp = 0.53; ISL.sl = 0.47; islCiz(); document.querySelector('.shp').scrollTop = 330; }")
        page.screenshot(path=kok + "_emir.png")
        page.locator(".isl .itab button", has_text="Pozisyon").click()
    kontrol("sayfada JS hatası yok", not hatalar, hatalar)
    print("5) CSRF")
    r = page.request.post(URL + "/api/islem/emir", data=json.dumps({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "482913"}),
                          headers={"Content-Type": "application/json"})
    kontrol("özel başlıksız POST reddedilir (403)", r.status == 403)
    r = page.request.post(URL + "/api/islem/emir", data=json.dumps({"sembol": "AKEUSDT", "yon": "L", "usd": 50, "pin": "482913"}),
                          headers={"Content-Type": "application/json", "X-Carry-Islem": "1", "Origin": "https://kotu.example"})
    kontrol("başka kökenli POST reddedilir (403)", r.status == 403)
    r = page.request.post(URL + "/api/islem/sil", data="{}", headers={"Content-Type": "application/json", "X-Carry-Islem": "1"})
    kontrol("bilinmeyen işlem 404", r.status == 404)
    n0 = len(SC.client.emirler)
    kontrol("CSRF denemelerinden hiç emir gitmedi", len(SC.client.emirler) == n0)
    print("6) kapı çalışmıyorsa")
    panel.ISLEM_URL = f"http://127.0.0.1:{bos_port()}"
    p2 = ctx.new_page(); kur(p2); p2.goto(URL + "/#piyasa"); p2.wait_for_selector(".pyr a")
    p2.wait_for_function("() => ISL_DURUM && ISL_DURUM.acik === false", timeout=5000)
    p2.evaluate("() => piyasaBoya(true)")
    kontrol("coin adı yine Binance'e gider", p2.locator(".pyr a", has_text="AKE").first.get_attribute("href").startswith("https://www.binance.com/"))
    kontrol("'panelden işlem kapalı' notu", "işlem kapalı" in p2.locator("#icerik").inner_text())
    br.close()
s_panel.close(); s_kapi.close()

if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Panelden işlem uçtan uca testi geçti.")
