"""MADDE 870: coin logoları (panel için).

Panelin CSP'si dış resimlere izin vermez (img-src 'self'); logolar sunucuda indirilip panelden `/ikon/<COIN>.png` ile verilir.
Kaynak sırası: Binance'in resmi varlık logoları (spot listesi + piyasa listesi), yoksa CoinGecko piyasa listesi (piyasa değerine
göre sıralı; aynı sembolde en büyük coin). Hiçbirinde yoksa panel harfli yuvarlağı gösterir.

Harita (sembol -> logo adresi) günde bir arka planda yenilenir: <DIZIN>/harita.json. İndirilen logolar <DIZIN>/<COIN>.<uzantı>;
bulunamayanlar <COIN>.yok (7 gün sonra yeniden denenir). Yalnız PNG / JPEG / WEBP / GIF kabul edilir (SVG betik taşıyabilir).
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time

logger = logging.getLogger("coin_ikon")

# panel servisi salt okunur (/opt): systemd CacheDirectory=carry-ikon -> $CACHE_DIRECTORY (/var/cache/carry-ikon)
DIZIN = os.environ.get("CACHE_DIRECTORY") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "defter", "ikon")
HARITA = os.path.join(DIZIN, "harita.json")
TAZE_SN = 86400
YOK_SN = 7 * 86400
EN_BUYUK = 400_000
UA = {"User-Agent": "Mozilla/5.0 (carry-panel)"}
AD_RE = re.compile(r"^[A-Z0-9]{1,24}$")
CARPAN_RE = re.compile(r"^(1000000|100000|10000|1000|100|1M)(?=[A-Z])")
TUR = {b"\x89PNG": ("png", "image/png"), b"\xff\xd8\xff": ("jpg", "image/jpeg"), b"GIF8": ("gif", "image/gif"), b"RIFF": ("webp", "image/webp")}

_kilit = threading.Lock()
_durum = {"m": None, "t": 0.0, "calisiyor": False}


def taban(ad: str) -> str:
    """1000PEPE -> PEPE, 1MBABYDOGE -> BABYDOGE (vadeli sözleşmelerin çarpanlı adları)."""
    return CARPAN_RE.sub("", ad)


def _json(url: str):
    import requests
    r = requests.get(url, headers=UA, timeout=25)
    r.raise_for_status()
    return r.json()


def harita_kur() -> dict:
    """Sembol -> logo adresi. Önce CoinGecko (düşük öncelik), üstüne Binance (resmi) yazılır."""
    m: dict[str, str] = {}
    for sayfa in range(1, 13):   # ~3000 coin; ücretsiz uç dakikada ~10 istek -> sayfalar arası bekleme
        try:
            L = _json(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page={sayfa}")
        except Exception as e:
            logger.info("coingecko sayfa %s alınamadı: %s", sayfa, str(e)[:120])
            if "429" in str(e):
                time.sleep(65)
                continue
            break
        if not L:
            break
        for x in L:
            s, u = str(x.get("symbol") or "").upper(), x.get("image")
            if s and u and AD_RE.match(s):
                m.setdefault(s, u)
        time.sleep(7)
    b = 0
    for url, alan_ad, alan_logo in (("https://www.binance.com/bapi/asset/v2/public/asset/asset/get-all-asset", "assetCode", "logoUrl"),
                                    ("https://www.binance.com/bapi/composite/v1/public/marketing/symbol/list", "name", "logo")):
        try:
            for x in (_json(url).get("data") or []):
                s, u = str(x.get(alan_ad) or "").upper(), x.get(alan_logo)
                if s and u and AD_RE.match(s):
                    m[s] = u; b += 1
        except Exception as e:
            logger.info("binance logo listesi alınamadı: %s", str(e)[:120])
    if m:
        os.makedirs(DIZIN, exist_ok=True)
        with open(HARITA + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"t": int(time.time()), "m": m}, f)
        os.replace(HARITA + ".tmp", HARITA)
        logger.info("coin logo haritası: %d sembol (%d binance)", len(m), b)
    return m


def _arka_kur() -> None:
    try:
        m = harita_kur()
        if m:
            with _kilit:
                _durum.update(m=m, t=time.time())
    finally:
        _durum["calisiyor"] = False


def harita() -> dict:
    """Bellekteki / diskteki harita; eskiyse (ya da yoksa) arka planda yenilemeyi başlatır, beklemez."""
    with _kilit:
        if _durum["m"] is None:
            try:
                with open(HARITA, encoding="utf-8") as f:
                    d = json.load(f)
                _durum.update(m=d.get("m") or {}, t=float(d.get("t") or 0))
            except (OSError, ValueError):
                _durum.update(m={}, t=0.0)
        if time.time() - _durum["t"] > TAZE_SN and not _durum["calisiyor"]:
            _durum["calisiyor"] = True
            threading.Thread(target=_arka_kur, name="coin-ikon", daemon=True).start()
        return _durum["m"] or {}


def ikon(ad: str) -> tuple[str, str] | None:
    """(dosya yolu, içerik türü) ya da None. İlk istekte indirir, sonra diskten."""
    ad = str(ad or "").upper()
    if not AD_RE.match(ad):
        return None
    os.makedirs(DIZIN, exist_ok=True)
    for uz, tur in {v[0]: v[1] for v in TUR.values()}.items():
        y = os.path.join(DIZIN, f"{ad}.{uz}")
        if os.path.exists(y):
            return y, tur
    yok = os.path.join(DIZIN, f"{ad}.yok")
    if os.path.exists(yok) and time.time() - os.path.getmtime(yok) < YOK_SN:
        return None
    m = harita()
    url = m.get(ad) or m.get(taban(ad))
    if not url:
        if m:    # harita varken bulunamadı -> bir süre sorma (harita henüz kurulmadıysa işaretleme)
            open(yok, "w").close()
        return None
    try:
        import requests
        r = requests.get(url, headers=UA, timeout=15, stream=True)
        r.raise_for_status()
        veri = r.raw.read(EN_BUYUK + 1, decode_content=True)
    except Exception as e:
        logger.info("logo indirilemedi %s: %s", ad, str(e)[:120])
        return None
    tt = next((v for k, v in TUR.items() if veri.startswith(k)), None)
    if not tt or len(veri) > EN_BUYUK or (tt[0] == "webp" and veri[8:12] != b"WEBP"):
        open(yok, "w").close()
        return None
    y = os.path.join(DIZIN, f"{ad}.{tt[0]}")
    with open(y + ".tmp", "wb") as f:
        f.write(veri)
    os.replace(y + ".tmp", y)
    return y, tt[1]
