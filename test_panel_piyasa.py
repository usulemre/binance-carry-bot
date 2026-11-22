"""MADDE 832 — panel Piyasa sekmesi uçtan uca (gerçek tarayıcı, Playwright + Chromium).

Binance uçları SAHTE (route / routeWebSocket ile): hiçbir gerçek ağ isteği yok. Playwright yoksa test atlanır (sunucuda gerekmez).
Denenenler: ilk görüntü (REST) sıralaması, hacim filtresi, perpetual-olmayan / USDT-olmayan eleme, bot rozeti, saniyelik akışla
fiyat + sıralama güncellemesi, izleme listesi (ekle / yenilemede kalır / çıkar), arama, funding modu, sekmeden çıkınca akışın
kapanması, telefonda yatay taşma olmaması. İsteğe bağlı: PIYASA_EKRAN=<yol> ile telefon ekran görüntüsü.
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
    print("playwright yok - piyasa sekmesi tarayıcı testi ATLANDI")
    sys.exit(0)

os.environ["TZ"] = "UTC"; time.tzset()
import panel

basarisiz = []


def kontrol(ad, kosul, detay=""):
    print(f"  [{'OK' if kosul else 'HATA'}]   {ad}" + ("" if kosul else f"  {detay}"))
    if not kosul:
        basarisiz.append(ad)


tmp = tempfile.mkdtemp(); kl = os.path.join(tmp, "carry-d1"); os.makedirs(os.path.join(kl, "defter"))
open(os.path.join(kl, "carry_bot.py"), "w").write("")
open(os.path.join(kl, ".env"), "w").write("BINANCE_MODE=demo\n")
with open(os.path.join(kl, "defter", "gunluk.jsonl"), "w") as f:
    for i in range(3):
        f.write(json.dumps({"tarih": f"2026-11-{i+1:02d}", "kitap": 1000 + i, "gun_getiri": 0.001, "profil": "T7K", "doz": "1.15",
                            "pozisyonlar": {"AAAUSDT": {"yon": "L", "usd": 100, "kar_yuzde": 1.5}}}) + "\n")

with socket.socket() as so:
    so.bind(("127.0.0.1", 0)); PORT = so.getsockname()[1]
from waitress import create_server
srv = create_server(panel.uygulama([kl]), host="127.0.0.1", port=PORT, threads=2)
threading.Thread(target=srv.run, daemon=True).start()
time.sleep(0.5)

# coin, fiyat, 24s %, hacim $, funding
COIN = [("AAAUSDT", 1.0, 25.0, 30e6, 0.0001), ("BBBUSDT", 2.0, 12.0, 80e6, 0.0005), ("CCCUSDT", 3.0, -18.0, 40e6, -0.0020),
        ("DDDUSDT", 4.0, -5.0, 20e6, 0.0001), ("EEEUSDT", 5.0, 40.0, 2e6, 0.0030),      # EEE: hacim düşük (10 M filtresinde yok)
        ("BTCUSDT", 90000.0, 1.0, 9e9, 0.0001), ("FFFUSDC", 1.0, 90.0, 90e6, 0.0),      # USDC: elenir
        ("GGGUSDT", 1.0, 70.0, 90e6, 0.0)]                                                # GGG: perpetual değil (delivery): elenir
EI = {"symbols": [{"symbol": s, "contractType": "CURRENT_QUARTER" if s == "GGGUSDT" else "PERPETUAL",
                   "quoteAsset": "USDC" if s.endswith("USDC") else "USDT", "status": "TRADING"} for s, *_ in COIN]}
T24 = [{"symbol": s, "lastPrice": str(f), "priceChangePercent": str(p), "quoteVolume": str(q)} for s, f, p, q, r in COIN]
PI = [{"symbol": s, "lastFundingRate": str(r), "nextFundingTime": 1_800_000_000_000} for s, f, p, q, r in COIN]
wss = []
kline_istek = []


def mumlar(sem):
    """31 günlük kapanış: 3 gün önce (indeks 27) ve 7 gün önce (indeks 23) belirli değerler; BTC yeni listelenmiş (2 mum)."""
    taban = {s: f for s, f, *_ in COIN}[sem]
    c = [taban] * 31
    if sem == "AAAUSDT":
        c[27] = 0.5; c[23] = 2.0          # 3 gün: +%100, 1 hafta: -%50
    if sem == "CCCUSDT":
        c[27] = 6.0; c[23] = 1.0          # 3 gün: -%50, 1 hafta: +%200
    if sem == "BTCUSDT":
        c = [90000.0, 90000.0]
    return [[0, "0", "0", "0", str(x)] for x in c]


def kur(page):
    def fapi(route):
        u = route.request.url
        if "klines" in u:
            sem = u.split("symbol=")[1].split("&")[0]
            if "interval=1d" in u:
                kline_istek.append(sem)
            body = mumlar(sem)
        else:
            body = EI if "exchangeInfo" in u else T24 if "ticker/24hr" in u else PI if "premiumIndex" in u else []
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body),
                      headers={"Access-Control-Allow-Origin": "*"})
    page.route("https://fapi.binance.com/**", fapi)
    page.route("https://cdnjs.cloudflare.com/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=""))
    page.route_web_socket("wss://fstream.binance.com/**", lambda ws: wss.append(ws))


def satirlar(page, bolum_bas):
    return page.evaluate("""(b) => { const B = [...document.querySelectorAll('.pyb')].find(x => x.textContent.includes(b));
      if (!B) return null; const L = B.nextElementSibling; return [...L.querySelectorAll('.pyr:not(.ust) a')].map(a => a.textContent); }""", bolum_bas)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    ctx = br.new_context(viewport={"width": 1200, "height": 1600})
    page = ctx.new_page(); kur(page)
    hatalar = []; page.on("pageerror", lambda e: hatalar.append(str(e)))
    page.goto(f"http://127.0.0.1:{PORT}/#piyasa")
    page.wait_for_selector(".pyr a", timeout=10000)
    print("1) ilk görüntü")
    kontrol("sekme menüde var ve seçili", page.locator("#nav button.on").inner_text().strip().endswith("Piyasa"))
    y = satirlar(page, "En çok yükselen"); d = satirlar(page, "En çok düşen")
    kontrol("yükselenler sırası (10 M$ filtresi)", y[:3] == ["AAA", "BBB", "BTC"], f"({y})")
    kontrol("düşenler sırası", d[:2] == ["CCC", "DDD"], f"({d})")
    kontrol("düşük hacimli coin 10 M$ filtresinde yok", "EEE" not in y + d)
    kontrol("USDC çifti ve perpetual olmayan sözleşme elendi", not ({"FFFUSDC", "FFF", "GGG"} & set(y + d)), f"({y})")
    kontrol("yükselenlerde yalnız artıda, düşenlerde yalnız ekside olanlar", "CCC" not in y and "BBB" not in d and "BTC" not in d, f"({y}, {d})")
    kontrol("botun pozisyonu rozetli (bot L)", "bot L" in page.locator(".pyr", has_text="AAA").first.inner_text())
    kontrol("coin adı Binance'te o coinin sayfasını açıyor",
            page.locator(".pyr a", has_text="BBB").first.get_attribute("href") == "https://www.binance.com/tr/futures/BBBUSDT")
    kontrol("funding gösteriliyor (BBB +0,050%)", "+0,050%" in page.locator(".pyr", has_text="BBB").first.inner_text())
    print("2) canlı akış")
    page.wait_for_function("() => true"); time.sleep(0.3)
    kontrol("akış bağlandı (!ticker@arr + !markPrice@arr@1s)", wss and "!ticker@arr" in wss[0].url and "!markPrice@arr@1s" in wss[0].url,
            f"({[w.url for w in wss]})")
    wss[0].send(json.dumps({"stream": "!ticker@arr", "data": [{"e": "24hrTicker", "s": "DDDUSDT", "c": "6.5", "P": "60.0", "q": "25000000"}]}))
    wss[0].send(json.dumps({"stream": "!markPrice@arr@1s", "data": [{"e": "markPriceUpdate", "s": "DDDUSDT", "p": "6.5", "r": "0.0042", "T": 1}]}))
    page.wait_for_function("() => [...document.querySelectorAll('.pyb')][0].nextElementSibling.querySelector('.pyr:not(.ust) a').textContent=='DDD'",
                           timeout=5000)
    y = satirlar(page, "En çok yükselen")
    kontrol("akıştaki %60 ile DDD yükselenlerin başına geçti", y[0] == "DDD", f"({y})")
    kontrol("fiyat ve funding akıştan güncellendi", "6,5" in page.locator(".pyr", has_text="DDD").first.inner_text()
            and "+0,420%" in page.locator(".pyr", has_text="DDD").first.inner_text())
    kontrol("durum: canlı", "canlı" in page.locator("#piyd").inner_text())
    print("3) hacim filtresi")
    page.locator(".gdon button", has_text="1 M$").click()
    kontrol("1 M$ seçince düşük hacimli EEE listeye girdi (DDD %60'tan sonra)", satirlar(page, "En çok yükselen")[:2] == ["DDD", "EEE"],
        f"({satirlar(page, 'En çok yükselen')})")
    page.locator(".gdon button", has_text="10 M$").click()
    print("4) izleme listesi")
    page.locator(".pyr", has_text="CCC").first.locator("button.yd").click()
    kontrol("madde 837: yıldız düğmesi aria-pressed ve 40 px", page.locator(".pyr", has_text="CCC").first.locator("button.yd").get_attribute("aria-pressed") == "true"
            and page.locator(".pyr", has_text="CCC").first.locator("button.yd").bounding_box()["height"] >= 40)
    kontrol("☆ ile CCC izleme listesine eklendi", satirlar(page, "İzleme listem") == ["CCC"])
    page.reload(); page.wait_for_selector(".pyr a")
    kontrol("yenilemeden sonra izleme listesi duruyor", satirlar(page, "İzleme listem") == ["CCC"])
    page.locator(".pyb", has_text="İzleme listem").locator("xpath=following-sibling::div[1]").locator("button.yd").first.click()
    kontrol("★ ile listeden çıkarıldı", satirlar(page, "İzleme listem") is None)
    print("5) arama ve funding modu")
    page.fill("#piyara", "bt")
    kontrol("arama: yalnız BTC", satirlar(page, "Arama") == ["BTC"], f"({satirlar(page, 'Arama')})")
    page.fill("#piyara", "")
    page.locator(".gdon button", has_text="Funding").click()
    f1 = satirlar(page, "En yüksek funding"); f2 = satirlar(page, "En negatif funding")
    kontrol("funding modu: en yüksek BBB, en negatif CCC", f1[0] == "BBB" and f2[0] == "CCC", f"({f1}, {f2})")
    page.locator(".gdon button", has_text="24 sa").click()
    print("5b) dönem: 3 gün / 1 hafta / 1 ay")
    kontrol("24 sa'te günlük mum indirilmedi", kline_istek == [], f"({kline_istek})")
    page.locator(".gdon button", has_text="3 gün").click()
    page.wait_for_function("() => !PIY_GYUK.calis && Object.keys(PIY_GUN).length > 0", timeout=10000)
    y3 = satirlar(page, "En çok yükselen (3 gün)"); d3 = satirlar(page, "En çok düşen (3 gün)")
    kontrol("3 gün: AAA +%100 yükselenlerde, CCC -%50 düşenlerde", y3 == ["AAA"] and d3 == ["CCC"], f"({y3}, {d3})")
    kontrol("3 gün: sütun başlığı ve değer", "+100,00%" in page.locator(".pyr", has_text="AAA").first.inner_text()
            and page.locator(".pyr.ust").first.inner_text().find("3 gün") >= 0)
    kontrol("yalnız listede görünecek coinler indirildi (düşük hacimli EEE yok, USDC yok)",
            "EEEUSDT" not in kline_istek and "FFFUSDC" not in kline_istek and "AAAUSDT" in kline_istek, f"({kline_istek})")
    n0 = len(kline_istek)
    page.locator(".gdon button", has_text="1 hafta").click(); time.sleep(0.5)
    y7 = satirlar(page, "En çok yükselen (1 hafta)"); d7 = satirlar(page, "En çok düşen (1 hafta)")
    kontrol("1 hafta: CCC +%200 yükselenlerde, AAA -%50 düşenlerde", y7 == ["CCC"] and d7 == ["AAA"], f"({y7}, {d7})")
    kontrol("dönem değişince yeniden indirmedi (30 dk önbellek)", len(kline_istek) == n0, f"({len(kline_istek)} vs {n0})")
    page.locator(".gdon button", has_text="1 ay").click(); time.sleep(0.3)
    kontrol("1 ay: 30 günde değişmeyen coinler yükselen / düşen listesinde yok",
            satirlar(page, "En çok yükselen (1 ay)") == [] and satirlar(page, "En çok düşen (1 ay)") == [],
            f"({satirlar(page, 'En çok yükselen (1 ay)')}, {satirlar(page, 'En çok düşen (1 ay)')})")
    page.fill("#piyara", "btc"); time.sleep(0.8)
    kontrol("yeni listelenmiş coinde 1 ay değişimi '—'", "—" in page.locator(".pyr", has_text="BTC").first.inner_text())
    page.fill("#piyara", "")
    page.reload(); page.wait_for_selector("#piyic")
    kontrol("dönem seçimi yenilemede korunur", page.locator(".gdon button.on", has_text="1 ay").count() == 1)
    page.locator(".gdon button", has_text="24 sa").click()
    print("6) sekmeden çıkınca akış kapanır")
    w0 = len(wss)
    page.locator("#nav button", has_text="Özet").click(); time.sleep(0.5)
    kapali = page.evaluate("() => PIY_WS === null")
    kontrol("Özet'e geçince piyasa akışı kapandı", kapali)
    page.locator("#nav button", has_text="Piyasa").click(); page.wait_for_selector(".pyr a"); time.sleep(0.5)
    kontrol("Piyasa'ya dönünce yeniden bağlandı", len(wss) > w0)
    kontrol("sayfada JS hatası yok", not hatalar, f"({hatalar})")
    print("7) telefon")
    tel = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    p2 = tel.new_page(); kur(p2); p2.goto(f"http://127.0.0.1:{PORT}/#piyasa"); p2.wait_for_selector(".pyr a")
    tasma = p2.evaluate("() => document.documentElement.scrollWidth - innerWidth")
    kontrol("telefonda yatay taşma yok", tasma <= 0, f"({tasma}px)")
    kontrol("telefonda hacim sütunu gizli, fiyat / % / funding görünür",
            p2.locator(".pyr:not(.ust) .hc").first.is_hidden() and p2.locator(".pyr:not(.ust) .r").nth(0).is_visible())
    if os.getenv("PIYASA_EKRAN"):
        p2.screenshot(path=os.getenv("PIYASA_EKRAN"), full_page=True)
    br.close()
srv.close()

if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Piyasa sekmesi tarayıcı testi geçti.")
