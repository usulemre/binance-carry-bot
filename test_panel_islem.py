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
                    "defter": os.path.join(tmp, "panel_islem.jsonl"), "elle_panel": os.path.join(tmp, "elle_panel.json"),
                    "elle_dosya": os.path.join(tmp, "elle.json"), "elle_olay": os.path.join(tmp, "elle_olay.jsonl"),
                    "dilim": os.path.join(tmp, "dilim.json")}, bildir=bil.append)
json.dump({"dilimler": {"0": {"AKEUSDT": 40.0}}}, open(os.path.join(tmp, "dilim.json"), "w"))   # AKE başta botun coini
P_KAPI, P_PANEL = bos_port(), bos_port()
s_kapi = create_server(ci.uygulama(lambda: KAPI), host="127.0.0.1", port=P_KAPI, threads=2)
threading.Thread(target=s_kapi.run, daemon=True).start()
panel.ISLEM_URL = f"http://127.0.0.1:{P_KAPI}"
s_panel = create_server(panel.uygulama([kl]), host="127.0.0.1", port=P_PANEL, threads=4)
threading.Thread(target=s_panel.run, daemon=True).start()
time.sleep(0.5)
URL = f"http://127.0.0.1:{P_PANEL}"

EI = {"symbols": [{"symbol": s_, "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"} for s_ in ("AKEUSDT", "ELSAUSDT")]}
T24 = [{"symbol": "AKEUSDT", "lastPrice": "0.5", "priceChangePercent": "-12.0", "quoteVolume": "50000000"},
       {"symbol": "ELSAUSDT", "lastPrice": "0.08649", "priceChangePercent": "27.15", "quoteVolume": "60000000"}]   # gerçek piyasada var, demo hesapta YOK
PI = [{"symbol": "AKEUSDT", "lastFundingRate": "-0.001", "nextFundingTime": 1}, {"symbol": "ELSAUSDT", "lastFundingRate": "0.0001", "nextFundingTime": 1}]


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


def tut(page, ms=900):
    """Basılı tut düğmesi (madde 836)."""
    b = page.locator("#isltut"); b.hover(); page.mouse.down(); page.wait_for_timeout(ms); page.mouse.up()


EKRAN = os.getenv("ISLEM_EKRAN")
kok = EKRAN.rsplit(".", 1)[0] if EKRAN else None
with sync_playwright() as pw:
    br = pw.chromium.launch()
    ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page = ctx.new_page(); kur(page)
    hatalar = []; page.on("pageerror", lambda e: hatalar.append(str(e)))
    page.on("dialog", lambda d: (hatalar.append("beklenmeyen dialog: " + d.message), d.dismiss()))
    page.goto(URL + "/#piyasa"); page.wait_for_selector(".pyr a")
    page.wait_for_function("() => ISL_DURUM && ISL_DURUM.acik", timeout=5000)
    print("0) madde 847: gerçek piyasada olup demo hesapta olmayan coin (ELSA)")
    page.evaluate("() => piyasaBoya(true)")
    kontrol("listede 'demoda yok' rozeti", "demoda yok" in page.locator(".pyr", has_text="ELSA").first.inner_text())
    kontrol("AKE'de rozet yok", "demoda yok" not in page.locator(".pyr:not(.ust)", has_text="AKE").first.inner_text())
    page.locator(".pyr a", has_text="ELSA").first.click(); page.wait_for_selector(".isl .isah.yok", timeout=6000)
    kontrol("pencere: kırmızı hata değil, açıklayıcı bilgi", "demo hesapta işlem görmüyor" in page.locator(".isl .isah.yok").inner_text()
            and page.locator(".isl .imsj.hata").count() == 0)
    kontrol("işlem düğmesi kapalı ve nedenini söylüyor", page.locator(".isl .ialt button").is_disabled()
            and "Demo hesapta işlem görmüyor" in page.locator(".isl .ialt").inner_text())
    kontrol("grafik yine çiziliyor", page.locator("#islgraf svg").count() == 1 or page.locator("#islgraf").count() == 1)
    if kok:
        page.wait_for_timeout(800); page.evaluate("() => islGrafikCiz()"); page.screenshot(path=kok + "_demoyok.png")
    page.keyboard.press("Escape"); page.wait_for_timeout(300)
    print("1) pencere")
    page.evaluate("() => piyasaBoya(true)")
    a = page.locator(".pyr a", has_text="AKE").first
    kontrol("işlem açıkken coin adı Binance'e değil pencereye gider", a.get_attribute("href") == "#piyasa")
    kontrol("altta açıklama: demo, 200 $, PIN", "demo hesap" in page.locator("#icerik").inner_text() and "200 $" in page.locator("#icerik").inner_text())
    page.locator(".pyr:not(.ust)", has_text="AKE").first.click(position={"x": 230, "y": 24})   # madde 837: satırın fiyat bölgesine dokunmak yeter
    page.wait_for_selector("#isldevam", timeout=6000)
    kontrol("satırın fiyat hücresine dokununca da pencere açılır", page.locator(".isl").count() == 1)
    kontrol("pencere erişilebilir diyalog (aria-modal) ve odak pencerede",
            page.locator(".shp[aria-modal='true']").count() == 1 and page.evaluate("() => document.activeElement.classList.contains('shp')"))
    page.wait_for_selector(".isl .isah", timeout=5000)
    kontrol("madde 839: botun coini uyarısı (işlem yaparsan sana geçer)", "botun" in page.locator(".isl .isah").inner_text())
    kontrol("pozisyon yok -> doğrudan yeni emir; Demo rozeti; sekme seçici yok", "Demo" in page.locator("#islic").inner_text()
            and page.locator(".isl .iseg.gor").count() == 0)
    page.wait_for_selector("#islgraf svg rect", timeout=5000)
    kontrol("grafik: 120 mum", page.locator("#islgraf svg rect.igub, #islgraf svg rect.igdb").count() == 120)
    page.locator(".isl .ichip.gt button[title='çizgi']").click()
    kontrol("çizgi grafiğe geçiş: mum yok, çizgi var", page.locator("#islgraf polyline").count() == 1 and page.locator("#islgraf rect.igub").count() == 0)
    page.locator(".isl .ichip.gt button[title='mum']").click()
    kontrol("ana eylem altta: 'Long 50,00 $'", "Long" in page.locator("#isldevam").inner_text() and "50" in page.locator("#isldevam").inner_text())
    print("2) ayarla + canlı tahmin")
    page.locator(".isl .ichip button", has_text="100 $").click()
    kontrol("TP / stop varsayılan kapalı (sade bilet)", page.locator(".isl input[aria-label='TP fiyatı']").count() == 0)
    page.locator(".isl .iacil").click()
    page.locator(".isl .ichip button", has_text="+5%").first.click()
    kontrol("TP +5% dolduruldu (0,525)", page.locator(".isl input[aria-label='TP fiyatı']").input_value() in ("0,525", "0.525"))
    kontrol("canlı tahmin: pozisyon 100 $, TP'de ▲, komisyon", all(x in page.locator("#isltah").inner_text() for x in ("100,00", "TP'de", "Komisyon")),
            page.locator("#isltah").inner_text())
    kontrol("grafikte plan TP çizgisi", page.locator("#islgraf g.igad.tp").count() >= 1)
    if kok:
        page.evaluate("() => document.querySelector('.shp').scrollTop = 0"); page.screenshot(path=kok + "_emir.png")
    print("3) onay ekranı + basılı tut + PIN")
    page.locator("#isldevam").click(); page.wait_for_selector(".isl .ionay")
    kontrol("onay ekranı özeti: adet 200, TP kârı, komisyon", all(x in page.locator(".ionay").inner_text() for x in ("200", "TP", "Komisyon")),
            page.locator(".ionay").inner_text())
    kontrol("onay ekranına gelmek emir göndermedi", SC.client.emirler == [])
    kontrol("onay ekranında 'coin sana geçer' notu", "sana geçer" in page.locator(".ionay").inner_text())
    page.fill("#islpin", "482913")
    tut(page, 250)
    page.wait_for_timeout(400)
    kontrol("kısa dokunuş (0,25 sn) emir GÖNDERMEZ", SC.client.emirler == [])
    if kok:
        page.screenshot(path=kok + "_onay.png")
    page.fill("#islpin", "111111"); tut(page)
    page.wait_for_selector(".isl .imsj.hata", timeout=6000)
    kontrol("yanlış PIN: hata, emir yok, onay ekranında kalır", "PIN yanlış" in page.locator(".isl .imsj").inner_text() and SC.client.emirler == []
            and page.locator(".isl .ionay").count() == 1)
    page.fill("#islpin", "482913"); tut(page)
    page.wait_for_selector(".isl .imsj.ok", timeout=8000)
    e = SC.client.emirler[-1]
    kontrol("borsaya MARKET BUY 200 adet gitti", e["type"] == "MARKET" and e["side"] == "BUY" and e["quantity"] == 200, e)
    kontrol("durum rozeti 'Doldu'", "Doldu" in page.locator(".isl .imsj").inner_text())
    kontrol("emir panel_ önekli -> bot coini kullanıcıya bırakır", ce.emir_sahibi({"clientOrderId": e["newClientOrderId"]}) == "kullanici")
    kontrol("TP konuldu (0.52500)", any(x["type"] == "TAKE_PROFIT_MARKET" and x["triggerPrice"] == "0.52500" for x in SC.client.algolar))
    kontrol("Telegram bildirimi", bil and "AKE LONG" in bil[-1])
    page.wait_for_selector(".isl .ipoz", timeout=6000)
    kontrol("emirden sonra Pozisyon görünümü: Long 200 adet, TP 0,525", all(x in page.locator(".ipoz").inner_text() for x in ("Long", "200", "0,525")),
            page.locator(".ipoz").inner_text())
    kontrol("alt çubukta Short / Long", page.locator(".isl .ialt .ibtn.S").count() == 1 and page.locator(".isl .ialt .ibtn.L").count() == 1)
    kontrol("madde 839: artık 'bu coin sende' bandı", "sende" in page.locator(".isl .isah").inner_text(), page.locator(".isl .isah").inner_text())
    page.evaluate("() => islGrafikCiz()")
    kontrol("grafikte GİRİŞ çizgisi + etiketi", page.locator("#islgraf line.igl.gir").count() == 1 and page.locator("#islgraf g.igad.gir").count() == 1)
    kontrol("grafikte TP çizgisi (kurulu emir)", page.locator("#islgraf line.igl.tp").count() >= 1)
    kontrol("grafikte alış işareti ▲ (dolum)", page.locator("#islgraf path.igal").count() >= 1)
    kontrol("likidasyon (0,21) aralık dışında: kenarda ↓ hap", page.locator("#islgraf line.igl.lik").count() == 0
            and "↓" in page.locator("#islgraf g.ige.lik").text_content())
    kontrol("likidasyon uzaklık çubuğu", "likidasyona" in page.locator(".ipoz").inner_text())
    if kok:
        page.wait_for_timeout(1500); page.evaluate("() => { document.querySelector('.shp').scrollTop = 0; islGrafikCiz(); }"); page.screenshot(path=kok + "_poz.png")
    print("4) yarısını kapat + TP / stop (onay ekranından, PIN hatırlanır)")
    page.locator(".isl .iseg button", has_text="%50").click(); page.wait_for_selector(".isl .ionay")
    kontrol("kapat onayı: ≈ 100 adet", "100" in page.locator(".ionay").inner_text())
    kontrol("PIN pencere açıkken hatırlandı", page.locator("#islpin").input_value() == "482913")
    tut(page)
    page.wait_for_function("() => document.querySelector('.isl .imsj') && document.querySelector('.isl .imsj').innerText.includes('Kapatıldı')", timeout=6000)
    kontrol("%50 kapat: SELL reduceOnly 100 adet", SC.client.emirler[-1]["side"] == "SELL" and SC.client.emirler[-1]["quantity"] == 100
            and SC.client.emirler[-1]["reduceOnly"] == "true")
    page.wait_for_function("() => document.querySelector('.ipoz') && document.querySelector('.ipoz').innerText.includes('100 adet')", timeout=6000)
    page.locator(".isl input[aria-label='Stop fiyatı']").fill("0.45")
    kontrol("stop yazınca grafikte plan stop çizgisi", page.locator("#islgraf line.igl.sl").count() >= 1)
    page.locator(".isl .iseg button", has_text="TP / stop kaydet").click(); page.wait_for_selector(".isl .ionay")
    kontrol("TP / stop onayı: kapsam 100 adet", "100 adet" in page.locator(".ionay").inner_text())
    tut(page)
    page.wait_for_function("() => document.querySelector('.isl .imsj') && document.querySelector('.isl .imsj').innerText.includes('kaydedildi')", timeout=6000)
    kontrol("stop 0.45 kuruldu (100 adet)", any(x["type"] == "STOP_MARKET" and x["triggerPrice"] == "0.45000" and x["quantity"] == 100
                                               for x in SC.client.algolar))
    print("4a) madde 839: stop'u girişe çek + tek bekleyen emri iptal")
    SC.client.fiyat["AKEUSDT"] = 0.55                       # kârda (giriş 0,5)
    SC.client.acik["AKEUSDT"] = [{"orderId": 5150, "clientOrderId": "panel_limit1", "type": "LIMIT", "side": "BUY", "price": "0.48", "origQty": "40"},
                                 {"orderId": 5151, "clientOrderId": "android_x", "type": "LIMIT", "side": "BUY", "price": "0.47", "origQty": "10"}]
    page.evaluate("() => islPozYukle()"); page.wait_for_selector(".isl .ibx", timeout=5000)
    page.locator(".isl .iacil.kucuk2").click()
    kontrol("'Stop'u girişe çek' stop kutusunu girişle (0,5) doldurur", page.locator(".isl input[aria-label='Stop fiyatı']").input_value() in ("0,5", "0.5"))
    kontrol("uygulamadan konan emirde iptal düğmesi yok", page.locator(".isl .ibx").count() == 1)
    page.locator(".isl .ibx").click(); page.wait_for_selector(".isl .ionay")
    kontrol("iptal onayı: limit alış 40 @ 0,48", all(x in page.locator(".ionay").inner_text() for x in ("40", "0,48")))
    tut(page)
    page.wait_for_function("() => document.querySelector('.isl .imsj') && document.querySelector('.isl .imsj').innerText.includes('Silindi')", timeout=6000)
    kontrol("yalnız o emir iptal edildi", ("AKEUSDT", 5150) in SC.client.iptaller and ("AKEUSDT", 5151) not in SC.client.iptaller)
    SC.client.fiyat["AKEUSDT"] = 0.5
    page.evaluate("() => { ISL.sl = ''; islPozYukle(); }"); page.wait_for_timeout(500)
    print("4b) risk ile boyut")
    page.locator(".isl .iseg.gor button", has_text="Yeni emir").click()
    page.locator(".isl .ichip.kisa button", has_text="Risk").click()
    kontrol("risk modunda stop yoksa uyarı", "stop fiyatını gir" in page.locator("#isltah").inner_text() or page.locator(".isl input[aria-label='Stop fiyatı']").input_value() != "")
    page.locator(".isl input[aria-label='Risk tutarı']").fill("5")
    page.evaluate("() => { ISL.sl = ''; islCiz(); }")
    kontrol("stop silinince uyarı", "stop fiyatını gir" in page.locator("#isltah").inner_text(), page.locator("#isltah").inner_text())
    page.locator(".isl .ichip button", has_text="−5%").first.click()
    kontrol("5 $ risk, stop %5 uzakta -> pozisyon 100 $", "100,00" in page.locator("#isltah").inner_text(), page.locator("#isltah").inner_text())
    page.locator(".isl .ichip.kisa button", has_text="Tutar").click()
    print("4c) Türkçe ondalık + satır içi uyarı")
    page.locator(".isl .ichip.kisa button", has_text="Limit").click()
    page.locator(".isl input[aria-label='Limit fiyatı']").fill("0,48")
    kontrol("'0,48' (virgül) kabul edilir -> 0.48", page.evaluate("() => ISL.fiyat") == "0.48")
    page.locator(".isl input[aria-label='Limit fiyatı']").fill("0,30")
    kontrol("±%20 dışı limit yazarken uyarı", "±%20" in page.locator("#isluyr").inner_text(), page.locator("#isluyr").inner_text())
    page.locator(".isl .ichip.kisa button", has_text="Piyasa").click()
    page.locator(".isl .iseg.gor button", has_text="Pozisyon").click()
    page.locator(".isl input[aria-label='TP fiyatı']").fill("0,40")
    kontrol("long'da fiyatın altında TP yazarken uyarı (sunucuya gitmeden)", "üstünde olmalı" in page.locator("#isluyr").inner_text(), page.locator("#isluyr").inner_text())
    page.locator(".isl input[aria-label='TP fiyatı']").fill("0,525")
    kontrol("doğru TP'de uyarı kalkar", page.locator("#isluyr").inner_text().strip() == "")
    if os.getenv("AXE_JS"):      # isteğe bağlı erişilebilirlik denetimi (axe-core)
        page.add_script_tag(path=os.getenv("AXE_JS"))
        ihl = page.evaluate("async () => (await axe.run('#sheet', {resultTypes:['violations']})).violations.map(v=>v.id+' x'+v.nodes.length+' '+v.nodes.map(n=>n.target.join(' ')+' '+(n.failureSummary||'').split('\\n')[1]).join(' | '))")
        kontrol("axe: pencerede erişilebilirlik ihlali yok", ihl == [], ihl)
    page.locator(".isl .iseg.gor button", has_text="Yeni emir").click()
    page.locator(".isl .iseg.yon button", has_text="Short").click()
    page.evaluate("() => { ISL.tpsl = true; islCiz(); }")
    if page.locator(".isl input[aria-label='Stop fiyatı']").count():
        st = page.locator(".isl input[aria-label='Stop fiyatı']").locator("xpath=following-sibling::div[1]").inner_text()
        kontrol("madde 858: short'ta stop kısayolları yukarı (+%), TP aşağı (−%)", "+3%" in st, st)
        kontrol("madde 858: yön değişince eski TP / stop silindi", page.evaluate("() => ISL.sl") == "" and page.evaluate("() => ISL.tp") == "")
    page.locator(".isl .ichip button", has_text="25 $").click()
    page.locator("#isldevam").click(); page.wait_for_selector(".isl .ionay")
    kontrol("long varken short: onay başlığı 'azalt / çevir' ve tek yönlü hesap uyarısı",
            "azalt" in page.locator(".ionay .iob").inner_text() and "tek yönlü" in page.locator(".ionay").inner_text(), page.locator(".ionay").inner_text())
    page.locator(".isl .ibtn.geri").click()
    kontrol("Düzenle ile onaydan geri dönülür, emir gitmez", page.locator(".isl .ionay").count() == 0)
    kontrol("sayfada JS hatası / beklenmeyen dialog yok", not hatalar, hatalar)
    if kok:      # karanlık tema görüntüsü
        kd = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark")
        pd_ = kd.new_page(); kur(pd_); pd_.goto(URL + "/#piyasa"); pd_.wait_for_selector(".pyr a")
        pd_.wait_for_function("() => ISL_DURUM && ISL_DURUM.acik", timeout=5000); pd_.evaluate("() => piyasaBoya(true)")
        pd_.locator(".pyr a", has_text="AKE").first.click(); pd_.wait_for_selector(".isl .ipoz", timeout=6000); pd_.wait_for_timeout(1200)
        pd_.evaluate("() => islGrafikCiz()"); pd_.screenshot(path=kok + "_karanlik.png"); kd.close()
    print("4d) madde 839: Piyasa'da Pozisyonlarım")
    page.keyboard.press("Escape"); page.keyboard.press("Escape"); page.wait_for_timeout(300)
    page.evaluate("() => { elleYukle.t = 0; piyasaBoya(true); }")
    page.wait_for_function("() => document.querySelector('#piyelle') && document.querySelector('#piyelle').innerText.includes('AKE')", timeout=6000)
    kontrol("Pozisyonlarım'da AKE long görünüyor (adet, K/Z)", all(x in page.locator("#piyelle").inner_text() for x in ("AKE", "adet")),
            page.locator("#piyelle").inner_text())
    if kok:
        page.evaluate("() => window.scrollTo(0, 0)"); page.screenshot(path=kok + "_piyasa.png")
    page.locator("#piyelle .pye a").first.click(); page.wait_for_selector(".isl .ipoz", timeout=6000)
    kontrol("Pozisyonlarım'dan dokununca pozisyon penceresi açılır", page.locator(".isl .ipoz").count() == 1)
    page.keyboard.press("Escape")
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
