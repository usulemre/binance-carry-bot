# -*- coding: utf-8 -*-
"""MADDE 830 — ELLE MÜDAHALE: kullanıcı Binance'ten (uygulama / web) bir coinde işlem yaparsa bot o coini kullanıcıya bırakır.

Kullanıcı isteği (2026-11-22): "bot aynen çalışsın; ben bir pozisyonu satıp short'a çevirirsem müdahale ettiğim için onu
işaretlesin, ben kapatana kadar dilimlerde ona dokunmasın." Kâr / zarar panelde birleşik görünür.

NASIL AYIRT EDİLİR
  Botun bütün emirleri python-binance üzerinden gider; kütüphane her emre `x-Cb7ytekJ…` önekli clientOrderId /
  clientAlgoId verir (CONTRACT_ORDER_PREFIX). Olay modülü `OLAY` öneki kullanır. Binance'in kendi kapanışları
  (likidasyon, ADL, delist / settlement) `autoclose` / `adl_` / `settlement` / `delivery` içerir. Bunların DIŞINDA
  dolan bir emir (uygulamadan `android_…` / `ios_…` / `web_…` …) = KULLANICI. Botun felaket stop'u (algo) tetiklenince
  doğan emir ayrıca algo kaydındaki `actualOrderId` ile tanınır (öneki ne olursa olsun bot sayılır).

  Bot her turun BAŞINDA, son kontrolden beri pozisyonu / dilimi / elle işareti olan her sembolün emir geçmişine bakar.
  Kullanıcı dolumu görürse sembolü işaretler, sembolde botun KENDİ açık emirlerini (kâr al / kademe / felaket) iptal eder,
  kullanıcının emirlerine dokunmaz ve bildirir. İşaretli sembol: evrene girmez, dilimlerden çıkarılır, emir / kâr al /
  stop / delist kapatması yapılmaz, bayat emir temizliği o sembolün emirlerine dokunmaz.

BIRAKMA
  Borsada adet 0 olunca VE son kullanıcı dolumunun üzerinden ELLE_BEKLEME_SN geçince işaret kalkar (kullanıcı long'u
  kapatıp short'u açarken arada bir tur denk gelirse sembol bota geri dönmesin). Bırakmadan önceki kullanıcı dolumları
  yeniden işaret sebebi sayılmaz.

GÜVENLİK
  * İlk çalıştırmada (kayıt yok) yalnız zaman damgası yazılır; geçmiş emirler yüzünden hiçbir şey işaretlenmez.
  * Bir sembolün emir geçmişi okunamazsa o sembol için karar verilmez (eski işaret korunur, yeni işaret konmaz).
  * Pozisyonlar okunamazsa hiçbir şey değişmez; kayıttaki işaretler aynen döner.
  * Varsayılan KAPALI (CARRY_ELLE=0): bu modül hiç çağrılmaz, bot birebir eski davranışta.
"""
from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

ONEK_BOT = ("x-Cb7ytekJ", "OLAY")
"""Botun (ve olay modülünün) emir kimliği önekleri."""
ONEK_BOT_ANA = "x-Cb7ytekJ"
"""Yalnız ana botun öneki (işaret konunca iptal edilen emirler; olay modülünün emirlerine dokunulmaz)."""
SISTEM_ISARET = ("autoclose", "adl_", "settlement", "delivery")
"""Binance'in kendi kapanış emirleri (likidasyon / ADL / delist) — müdahale sayılmaz."""
ARALIK_PAYI_MS = 5 * 60 * 1000
"""Emir geçmişi son kontrolden bu kadar önce başlatılır (saat kayması / gecikme payı)."""


def emir_sahibi(o: dict, bot_gercek: set | frozenset = frozenset()) -> str:
    """'bot' / 'sistem' / 'kullanici'."""
    if str(o.get("orderId")) in bot_gercek:
        return "bot"
    cid = str(o.get("clientOrderId") or "")
    if cid.startswith(ONEK_BOT):
        return "bot"
    if any(k in cid.lower() for k in SISTEM_ISARET):
        return "sistem"
    return "kullanici"


def _dolan(o: dict) -> float:
    try:
        return float(o.get("executedQty") or 0)
    except (TypeError, ValueError):
        return 0.0


def _zaman(o: dict) -> int:
    try:
        return int(max(float(o.get("updateTime") or 0), float(o.get("time") or 0)))
    except (TypeError, ValueError):
        return 0


def kayit_oku(dosya: str) -> dict:
    try:
        with open(dosya, encoding="utf-8") as fh:
            d = json.load(fh)
        if isinstance(d, dict):
            d.setdefault("elle", {}); d.setdefault("birakilan", {})
            return d
    except (OSError, ValueError):
        pass
    return {"elle": {}, "birakilan": {}}


def kayit_yaz(dosya: str, d: dict) -> None:
    tmp = dosya + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        os.replace(tmp, dosya)
    except OSError as e:
        logger.warning("elle kaydı yazılamadı: %s", e)


def baslat(dosya: str, simdi_ms: int | None = None) -> bool:
    """Bot açılışında: kayıt yoksa takip zamanını ŞİMDİ'ye kurar (açılıştan sonraki kullanıcı işlemleri ilk turda yakalansın).
    Kayıt varsa dokunmaz. Kurduysa True."""
    st = kayit_oku(dosya)
    if st.get("son_kontrol_ms") is not None:
        return False
    st["son_kontrol_ms"] = int(simdi_ms if simdi_ms is not None else time.time() * 1000)
    kayit_yaz(dosya, st)
    logger.info("elle müdahale takibi başladı: bundan sonraki Binance işlemlerin bir sonraki turda tanınır")
    return True


def isaretliler(dosya: str) -> set:
    return set(kayit_oku(dosya).get("elle") or {})


def _olay_yaz(dosya: str | None, olay: dict) -> None:
    if not dosya:
        return
    try:
        with open(dosya, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(olay, ensure_ascii=False) + "\n")
    except OSError:
        pass


def bot_adet(durum: dict, sem: str) -> float:
    """Dilim defterine göre botun o semboldeki adedi (usd / giriş referansı); referansı olmayan bacak sayılmaz."""
    top = 0.0
    ref = durum.get("dilim_fiyat") or {}
    for a, h in (durum.get("dilimler") or {}).items():
        v = (h or {}).get(sem)
        q = (ref.get(str(a)) or {}).get(sem)
        if v and q:
            top += float(v) / float(q)
    return top


def dilimden_cikar(durum: dict, semboller) -> list[str]:
    """İşaretli sembolleri dilim defterinin bütün bölümlerinden çıkarır (idempotent). Çıkarılanları döner."""
    semboller = set(semboller or ())
    if not semboller:
        return []
    cikan = set()
    for h in (durum.get("dilimler") or {}).values():
        for s in semboller & set(h or {}):
            h.pop(s, None); cikan.add(s)
    for r in (durum.get("dilim_fiyat") or {}).values():
        for s in semboller & set(r or {}):
            r.pop(s, None)
    for k in ("kar_al", "merdiven", "felaket", "merdiven_yapildi", "merdiven_parca", "giris_funding"):
        d = durum.get(k)
        if isinstance(d, dict):
            for s in semboller & set(d):
                d.pop(s, None); cikan.add(s)
    return sorted(cikan)


def _bot_emirlerini_iptal(ic, sem: str) -> int:
    """Sembolde ana botun açık emirlerini (normal + algo) iptal eder; kullanıcının ve olay modülünün emirlerine dokunmaz."""
    n = 0
    try:
        for o in ic.futures_get_open_orders(symbol=sem) or []:
            if str(o.get("clientOrderId") or "").startswith(ONEK_BOT_ANA):
                try:
                    ic.futures_cancel_order(symbol=sem, orderId=o["orderId"]); n += 1
                except Exception as e:
                    logger.warning("elle: %s bot emri %s iptal edilemedi: %s", sem, o.get("orderId"), e)
    except Exception as e:
        logger.warning("elle: %s açık emirleri okunamadı: %s", sem, e)
    f = getattr(ic, "futures_get_open_algo_orders", None)
    if f is not None:
        try:
            r = f(symbol=sem)
            r = r.get("orders", r) if isinstance(r, dict) else r
            for o in r or []:
                if str(o.get("clientAlgoId") or "").startswith(ONEK_BOT_ANA):
                    try:
                        ic.futures_cancel_algo_order(symbol=sem, algoId=o["algoId"]); n += 1
                    except Exception as e:
                        logger.warning("elle: %s bot algo emri %s iptal edilemedi: %s", sem, o.get("algoId"), e)
        except Exception as e:
            logger.warning("elle: %s algo emirleri okunamadı: %s", sem, e)
    return n


def guncelle(client, durum: dict, dosya: str, simdi_ms: int | None = None, bildir=None, dry_run: bool = False,
             bekleme_sn: float = 1800.0, olay_dosya: str | None = None) -> set:
    """Kullanıcı müdahalelerini bulur, işaretler / bırakır. İşaretli sembol kümesini döner.

    `durum` yalnız OKUNUR (felaket algo kimlikleri, dilim sembolleri, botun adedi); dilimden çıkarma `dilimden_cikar` ile
    botun kendi akışında yapılır. Kuru çalışmada kayıt yazılmaz, emir iptal edilmez, bildirim gitmez."""
    simdi_ms = int(simdi_ms if simdi_ms is not None else time.time() * 1000)
    st = kayit_oku(dosya)
    elle, birak = st["elle"], st["birakilan"]
    ic = client.client
    try:
        pozlar = {}
        for p in client.get_open_positions():
            a = float(p.get("positionAmt") or 0)
            if abs(a) > 1e-12:
                pozlar[p["symbol"]] = pozlar.get(p["symbol"], 0.0) + a
    except Exception as e:
        logger.warning("elle: pozisyonlar okunamadı (%s) - işaretler değişmedi", e)
        return set(elle)
    son = st.get("son_kontrol_ms")
    if son is None:
        logger.info("elle müdahale takibi başladı (ilk kontrol: geçmiş emirler değerlendirilmez)")
        if not dry_run:
            st["son_kontrol_ms"] = simdi_ms
            kayit_yaz(dosya, st)
        return set(elle)
    dilim_sem = {s for h in (durum.get("dilimler") or {}).values() for s in (h or {})}
    aday = sorted(set(pozlar) | dilim_sem | set(elle))
    bot_gercek = set()
    for sem, aid in (durum.get("felaket") or {}).items():
        if sem in aday and aid is not None:
            try:
                g = ic.futures_get_algo_order(symbol=sem, algoId=aid)
                if str(g.get("actualOrderId") or "").strip() not in ("", "0"):
                    bot_gercek.add(str(g["actualOrderId"]))
            except Exception:
                pass
    bas = max(int(son) - ARALIK_PAYI_MS, simdi_ms - int(6.5 * 86400 * 1000))   # allOrders en çok 7 günlük aralık verir
    yeni, biraklan = [], []
    for sem in aday:
        try:
            emirler = ic.futures_get_all_orders(symbol=sem, startTime=bas, limit=500) or []
        except Exception as e:
            logger.warning("elle: %s emir geçmişi okunamadı (%s) - bu tur karar yok", sem, e)
            continue
        esik = int(birak.get(sem, 0))
        el = [o for o in emirler if _dolan(o) > 0 and _zaman(o) >= bas and _zaman(o) > esik
              and emir_sahibi(o, bot_gercek) == "kullanici"]
        if not el:
            continue
        son_el = max(_zaman(o) for o in el)
        if sem in elle:
            elle[sem]["son_el"] = max(int(elle[sem].get("son_el", 0)), son_el)
            continue
        ilk = min(el, key=_zaman)
        elle[sem] = {"t": simdi_ms, "son_el": son_el, "ilk_emir": str(ilk.get("clientOrderId") or ""),
                     "ilk_yon": ilk.get("side"), "poz": pozlar.get(sem, 0.0), "bot_adet": round(bot_adet(durum, sem), 10)}
        birak.pop(sem, None)
        yeni.append(sem)
    for sem in list(elle):
        if sem in yeni:
            continue
        if abs(pozlar.get(sem, 0.0)) <= 1e-12 and simdi_ms - int(elle[sem].get("son_el", 0)) >= bekleme_sn * 1000:
            biraklan.append(sem)
    if dry_run:
        for sem in yeni:
            logger.info("  [DRY] ELLE: %s kullanıcı müdahalesi bulundu - işaretlenirdi", sem)
        for sem in biraklan:
            logger.info("  [DRY] ELLE: %s kullanıcı kapatmış - bota geri dönerdi", sem)
        return (set(elle) - set(biraklan))
    for sem in yeni:
        n = _bot_emirlerini_iptal(ic, sem)
        k = elle[sem]
        logger.warning("ELLE MÜDAHALE: %s kullanıcı işlemi (%s, ilk emir %s) - sembol kullanıcıya bırakıldı; botun %d emri "
                       "iptal edildi, dilimlerden çıkarılıyor (bot adedi %s, borsa adedi %s)", sem, k["ilk_yon"],
                       k["ilk_emir"], n, k["bot_adet"], k["poz"])
        if bildir:
            bildir(f"✋ {sem}: elle işlem gördüm — bu coin artık sende. Bot ekleme / kapatma / kâr al / stop yapmayacak; "
                   f"pozisyonu tamamen kapatınca bota geri döner.", anahtar=f"elle_{sem}", kisma_sn=600)
        _olay_yaz(olay_dosya, {"olay": "isaret", "t": simdi_ms, "sembol": sem, **k})
    for sem in biraklan:
        k = elle.pop(sem)
        birak[sem] = simdi_ms
        logger.info("ELLE: %s kullanıcı tarafından kapatılmış - sembol bota geri döndü", sem)
        if bildir:
            bildir(f"↩️ {sem}: pozisyonu kapattın — coin bota geri döndü.", anahtar=f"elle_birak_{sem}", kisma_sn=600)
        _olay_yaz(olay_dosya, {"olay": "birak", "t": simdi_ms, "sembol": sem, "isaret_t": k.get("t")})
    for sem in list(birak):        # eski bırakma kayıtları (7 gün) temizlenir
        if simdi_ms - int(birak[sem]) > 7 * 86400 * 1000:
            birak.pop(sem, None)
    st["son_kontrol_ms"] = simdi_ms
    kayit_yaz(dosya, st)
    return set(elle)
