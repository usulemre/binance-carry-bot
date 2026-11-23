# -*- coding: utf-8 -*-
"""MADDE 851 — elle pozisyonları AYRI al-sat hesabına taşı, botun payını bota geri ver (BOT DURMUŞKEN çalıştırılır).

  kuru   : planı yazar, hiçbir emir göndermez, hiçbir dosya değiştirmez
  uygula : 1) al-sat hesabında spot → USDⓈ-M 5.000 USDT (Futures bakiyesi 3.000'den azsa)
           2) al-sat hesabında kullanıcının payını (adet, yön) 2x kaldıraçla PİYASA emriyle açar
           3) bot hesabında aynı adedi kapatır (yalnız al-satta açılabilenler; botun payı kalır), panel_ TP/SL/emirlerini iptal eder
           4) elle K/Z'yi günceller ve DONDURUR (kalıcı düzeltme), elle işaretlerini temizler
           5) BLESS / AKE / ICNT botun payını emir defterinden çıkarılan dilimlerine + referans fiyatlarına geri yazar,
              hedef adedi borsadakiyle karşılaştırır, kâr al / kademe / felaket'i kurar
Kullanıcı onayı: 2026-11-23 "Hepsini sen yap"."""
import json
import logging
import os
import shutil
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("tasima")
import config
import carry_bot as cb
import carry_elle as CE
import carry_elle_kz as K
from exchange_client import ExchangeClient

MOD = sys.argv[1] if len(sys.argv) > 1 else "kuru"
KALDIRAC = 2
# emir defterinden (madde 851 incelemesi): hangi dilim, hangi pay, referans (GIRIS emrinin ref fiyatı)
DILIM = {"AKEUSDT": [("0", 1.0, 0.005256)],
         "ICNTUSDT": [("10", 37 / 75, 0.4481), ("11", 38 / 75, 0.426)],
         "BLESSUSDT": [("14", 4180 / 11675, 0.01324), ("0", 4076 / 11675, 0.01214), ("1", 3419 / 11675, 0.01438)]}

ak, sk = os.getenv("ALSAT_API_KEY", "").strip(), os.getenv("ALSAT_API_SECRET", "").strip()
assert ak and sk and ak != config.API_KEY, "al-sat anahtarı yok ya da botunkiyle aynı — DUR"
bot = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
als = ExchangeClient(ak, sk, mode=os.getenv("ALSAT_MODE", "demo"), ozel_anahtar=False)


def pozlar(c) -> dict:
    out = {}
    for p in c.get_open_positions():
        q = float(p.get("positionAmt") or 0)
        if q:
            out[p["symbol"]] = out.get(p["symbol"], 0.0) + q
    return out


simdi = time.time()
st = K.guncelle(bot, simdi=simdi)
P = pozlar(bot)
plan = []
for s, L in sorted(st["aralik"].items()):
    a = next((x for x in L if not x.get("bit")), None)
    if not a or not float(a.get("q_k") or 0):
        continue
    qk, qb = float(a["q_k"]), float(a.get("q_bot") or 0)
    fark = P.get(s, 0.0) - (qk + qb)
    assert abs(fark) < 1e-6 * max(1, abs(qk)), f"{s}: borsa {P.get(s)} ≠ senin {qk} + bot {qb} — DUR"
    plan.append((s, qk, qb))
PA = pozlar(als)
assert not PA, f"al-sat hesabında zaten pozisyon var ({PA}) — iki kez çalıştırma? DUR"
for s in DILIM:
    q_bot = next((qb for s_, _, qb in plan if s_ == s), None)
    assert q_bot, f"{s}: botun payı bulunamadı — DUR"
durum = cb.dilim_durum_oku()
for s in DILIM:
    assert not any(s in (h or {}) for h in durum["dilimler"].values()), f"{s} zaten dilimde — DUR"

log.info("PLAN: %d pozisyon al-sat hesabına", len(plan))
for s, qk, qb in plan:
    log.info("  %-12s %s %g adet%s", s, "LONG " if qk > 0 else "SHORT", abs(qk), f"   (botun payı {qb:g} kalır)" if qb else "")
ac_emir = {}
for s, _, _ in plan:
    acik = [o for o in bot.client.futures_get_open_orders(symbol=s) or [] if str(o.get("clientOrderId") or "").startswith("panel_")]
    try:
        r = bot.client.futures_get_open_algo_orders(symbol=s); r = r.get("orders", r) if isinstance(r, dict) else r
    except Exception:
        r = []
    alg = [o for o in r or [] if str(o.get("clientAlgoId") or "").startswith("panel_")]
    if acik or alg:
        ac_emir[s] = (acik, alg)
log.info("bot hesabında panel emirleri (iptal edilecek): %s", {s: (len(a), [(o.get("orderType") or o.get("type"), o.get("triggerPrice")) for o in g])
                                                              for s, (a, g) in ac_emir.items()} or "yok")
fb = {b["asset"]: float(b["balance"]) for b in als.client.futures_account_balance()}
log.info("al-sat Futures bakiyesi: %s", fb.get("USDT", 0.0))
if MOD != "uygula":
    log.info("KURU — hiçbir şey değiştirilmedi")
    sys.exit(0)

# 1) teminat
if fb.get("USDT", 0.0) < 3000:
    r = als.client.futures_account_transfer(asset="USDT", amount=5000, type=1)
    log.info("spot → Futures 5.000 USDT: %s", r)
    time.sleep(2)
    fb = {b["asset"]: float(b["balance"]) for b in als.client.futures_account_balance()}
    assert fb.get("USDT", 0.0) >= 3000, f"aktarım sonrası bakiye {fb} — DUR"

# 2) al-satta aç
acilan = {}
for s, qk, qb in plan:
    try:
        try:
            als.client.futures_change_leverage(symbol=s, leverage=KALDIRAC)
        except Exception as e:
            log.warning("%s kaldıraç ayarlanamadı (%s) — devam", s, e)
        e = als.client.futures_create_order(symbol=s, side="BUY" if qk > 0 else "SELL", type="MARKET", quantity=abs(qk),
                                            newClientOrderId=f"tasima_{int(time.time()*1000)}"[:36])
        acilan[s] = e.get("orderId")
        log.info("AL-SAT açıldı %-12s %s %g (%s)", s, "BUY" if qk > 0 else "SELL", abs(qk), e.get("status"))
    except Exception as e:
        log.error("AL-SAT AÇILAMADI %s: %s — bu coin bot hesabında kalır", s, e)
time.sleep(2)
PA = pozlar(als)
for s in list(acilan):
    q = next(qk for s_, qk, _ in plan if s_ == s)
    if abs(PA.get(s, 0.0) - q) > 1e-9 * max(1, abs(q)):
        log.error("%s al-satta %s, beklenen %s — bot hesabında KAPATILMAYACAK", s, PA.get(s), q)
        acilan.pop(s)

# 3) bot hesabında kapat (yalnız açılabilenler)
for s, qk, qb in plan:
    if s not in acilan:
        continue
    acik, alg = ac_emir.get(s, ([], []))
    for o in acik:
        try:
            bot.client.futures_cancel_order(symbol=s, orderId=o["orderId"])
        except Exception as e:
            log.warning("%s panel emri iptal edilemedi: %s", s, e)
    for o in alg:
        try:
            bot.client.futures_cancel_algo_order(symbol=s, algoId=o["algoId"])
        except Exception as e:
            log.warning("%s panel TP/SL iptal edilemedi: %s", s, e)
    p = P[s]
    kw = dict(symbol=s, side="SELL" if qk > 0 else "BUY", type="MARKET", quantity=abs(qk), newClientOrderId=f"panel_tasima_{int(time.time()*1000)}"[:36])
    if (qk > 0) == (p > 0) and abs(qk) <= abs(p) + 1e-12:
        kw["reduceOnly"] = "true"
    try:
        e = bot.client.futures_create_order(**kw)
        log.info("BOT hesabında kapatıldı %-12s %s %g (%s)", s, kw["side"], abs(qk), e.get("status"))
    except Exception as e:
        log.error("BOT HESABINDA KAPATILAMADI %s: %s — ELLE BAKILMALI", s, e)
time.sleep(3)
P2 = pozlar(bot)
for s, qk, qb in plan:
    if s in acilan and abs(P2.get(s, 0.0) - qb) > 1e-9 * max(1, abs(qb) + abs(qk)):
        log.error("KONTROL %s bot hesabı %s, beklenen (botun payı) %s", s, P2.get(s, 0.0), qb)

# 4) elle K/Z son hal + dondur; işaretleri temizle
st = K.guncelle(bot, simdi=time.time())
st = K.dondur(st, int(time.time() * 1000))
log.info("elle K/Z donduruldu: toplam %+.4f $ (botun özkaynağından kalıcı düşülür)", st["toplam"])
kay = CE.kayit_oku(cb.ELLE_DOSYA)
for s in list(kay.get("elle") or {}):
    kay.setdefault("birakilan", {})[s] = int(time.time() * 1000)
kay["elle"] = {}
CE.kayit_yaz(cb.ELLE_DOSYA, kay)
if os.path.exists(cb.ELLE_PANEL_DOSYA):
    shutil.copy(cb.ELLE_PANEL_DOSYA, cb.ELLE_PANEL_DOSYA + f".yedek_m851_{int(time.time())}")
    CE.kayit_yaz(cb.ELLE_PANEL_DOSYA, {})

# 5) botun payını dilimlerine geri yaz
shutil.copy("carry_dilimler.json", f"carry_dilimler.json.yedek_m851_{int(time.time())}")
durum = cb.dilim_durum_oku()
for s, parcalar in DILIM.items():
    q_bot = P2.get(s, 0.0)
    for a, w, ref in parcalar:
        q = q_bot * w
        durum["dilimler"].setdefault(a, {})[s] = q * ref
        durum.setdefault("dilim_fiyat", {}).setdefault(a, {})[s] = ref
fiyat = cb.guncel_fiyatlar(bot, set(DILIM))
hedef = cb.toplam_hedef_tut(durum, fiyat)
for s in DILIM:
    hq = hedef.get(s, 0.0) / fiyat[s]
    log.info("  DİLİM KONTROL %-10s hedef adet %12.4f  borsa %12.4f  giriş %.6g", s, hq, P2.get(s, 0.0),
             cb.dilim_giris_ortalamasi(durum).get(s, (0, 0))[1])
    assert abs(hq - P2.get(s, 0.0)) <= 0.01 * abs(P2.get(s, 0.0)) + 1e-9, f"{s} hedef adet tutmuyor — dilim yazılmadı, DUR"
cb.dilim_durum_yaz(durum)
log.info("dilimler yazıldı")
if cb.koruma_acik():
    n = cb.kar_al_kur(bot, durum)
    cb.dilim_durum_yaz(durum)
    log.info("kâr al / kademe / felaket kuruldu: %s", n)
log.info("BİTTİ — al-satta %d pozisyon, bot hesabında botun payı. Sıradaki: CARRY_ELLE=0, carry-islem ayrı hesap, servisleri başlat.", len(acilan))
