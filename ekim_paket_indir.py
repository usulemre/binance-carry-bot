#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 673 — YENİ AY VERİ PAKETİ (Binance'e erişilen HERHANGİ bir bilgisayarda çalışır; yalnız Python 3, ek paket GEREKMEZ).

Neden: araştırma ortamından data.binance.vision'a erişilemiyor. Ekim OOS kontrolü (madde 492 / 587 / 617 / 650, ön kayıtlı) için
Ekim'in ham verisini siz kendi bilgisayarınızdan indirip tek bir zip olarak sohbete yüklersiniz; birleştirme ve ölçüm orada yapılır.

Kullanım (Windows / Mac / Linux; ay bittikten 2-3 gün sonra, Binance aylık dosyaları yayınlayınca):
    python ekim_paket_indir.py              -> geçen ay (ör. Kasım başında 2026-10)
    python ekim_paket_indir.py 2026-10
Çıktı: paket_2026-10.zip (~50-150 MB). İndirilen: 4 sa mumlar + funding (aylık) ve günlük metrikler (açık pozisyon, long/short
oranları), oos_semboller.txt'deki ~820 sembol için. Yalnız herkese açık piyasa verisi; hesap / anahtar YOK. Süre ~10-20 dk.
"""
from __future__ import annotations

import calendar
import json
import datetime as dt
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

B = "https://data.binance.vision/data/futures/um"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FAPI = "https://fapi.binance.com/fapi/v1/exchangeInfo"
YENI_METRIK_GUN = 120          # yeni sembolde günlük metrik geçmişi (kalabalık sinyali için yeter)
_TRADFI_TIP = {"EQUITY", "CN_EQUITY", "KR_EQUITY", "HK_EQUITY", "JP_EQUITY", "COMMODITY", "INDEX", "FOREX", "ETF", "BOND", "PREMARKET"}
R = os.path.dirname(os.path.abspath(__file__))


def gecen_ay() -> str:
    b = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    return b.strftime("%Y-%m")


def indir(url: str, deneme: int = 3) -> bytes | None:
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "carry-oos"}), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return None


def isler(semboller: list[str], ay: str, metrikli: set | None = None) -> list[tuple[str, str]]:
    """metrikli: günlük metrik indirilecek semboller (zeminde metrik geçmişi olanlar; None = hepsi)."""
    y, m = map(int, ay.split("-"))
    gunler = [f"{ay}-{d:02d}" for d in range(1, calendar.monthrange(y, m)[1] + 1)]
    out = []
    for s in semboller:
        out.append((f"{B}/monthly/klines/{s}/4h/{s}-4h-{ay}.zip", f"{s}/k{ay}.zip"))
        out.append((f"{B}/monthly/fundingRate/{s}/{s}-fundingRate-{ay}.zip", f"{s}/f{ay}.zip"))
        if metrikli is None or s in metrikli:
            out += [(f"{B}/daily/metrics/{s}/{s}-metrics-{g}.zip", f"{s}/m{g}.zip") for g in gunler]
    return out


def s3_liste(prefix: str) -> list[str]:
    """data.binance.vision S3 dizin listesi (alt önekler ve dosyalar, önek kırpılmış)."""
    import re
    out, marker = [], ""
    while True:
        x = indir(f"{S3}?delimiter=/&prefix={prefix}&marker={marker}")
        if x is None:
            return out
        x = x.decode("utf-8", "replace")
        out += [p[len(prefix):].strip("/") for p in re.findall(r"<Prefix>([^<]+)</Prefix>", x)[1:]]
        out += [k[len(prefix):] for k in re.findall(r"<Key>([^<]+)</Key>", x)]
        if "<IsTruncated>true" not in x:
            return out
        marker = re.search(r"<NextMarker>([^<]+)", x).group(1)


def yeni_semboller(eski: set, bilgi: dict | None) -> tuple[list[str], list[str]]:
    """MADDE 675: zeminde olmayan USDT perp'ler -> (kripto, tradfi), exchangeInfo'nun underlyingType'ına göre. exchangeInfo YOKSA
    (Binance API'sine erişilemeyen ortam) yeni sembol EKLENMEZ: yeni hisse / emtia perp'leri kripto sanılıp zemine girmesin."""
    if bilgi and bilgi.get("symbols"):
        ss = [x for x in bilgi["symbols"] if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT"
              and x["symbol"] not in eski]
        kr = sorted(x["symbol"] for x in ss if str(x.get("underlyingType", "COIN")).upper() not in _TRADFI_TIP)
        tf = sorted(x["symbol"] for x in ss if str(x.get("underlyingType", "COIN")).upper() in _TRADFI_TIP)
        return kr, tf
    return [], []


def yeni_isler(s: str, ay: str) -> list[tuple[str, str]]:
    """Yeni sembolün listelendiği aydan `ay`a kadar aylık mum + funding; son YENI_METRIK_GUN günün metrikleri."""
    aylar = sorted({f[len(s) + 4:len(s) + 11] for f in s3_liste(f"data/futures/um/monthly/klines/{s}/4h/")
                    if f.endswith(".zip") and not f.endswith("CHECKSUM")})
    aylar = [a for a in aylar if a <= ay]
    out = []
    for a in aylar:
        out.append((f"{B}/monthly/klines/{s}/4h/{s}-4h-{a}.zip", f"{s}/k{a}.zip"))
        out.append((f"{B}/monthly/fundingRate/{s}/{s}-fundingRate-{a}.zip", f"{s}/f{a}.zip"))
    if aylar:
        y, m = map(int, ay.split("-"))
        son = dt.date(y, m, calendar.monthrange(y, m)[1])
        bas = max(dt.date.fromisoformat(aylar[0] + "-01"), son - dt.timedelta(days=YENI_METRIK_GUN - 1))
        g = bas
        while g <= son:
            out.append((f"{B}/daily/metrics/{s}/{s}-metrics-{g}.zip", f"{s}/m{g}.zip")); g += dt.timedelta(days=1)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    argv = list(argv); bayrak = [a for a in argv if a.startswith("--")]; argv = [a for a in argv if not a.startswith("--")]
    ay = argv[0] if argv else gecen_ay()
    argv = bayrak
    satir = [l.split() for l in open(os.path.join(R, "oos_semboller.txt"), encoding="utf-8") if l.strip()]
    semboller = [x[0] for x in satir]; metrikli = {x[0] for x in satir if x[1:] == ["m"]}
    cikti = os.path.join(os.getcwd(), f"paket_{ay}.zip")
    if os.path.exists(cikti):                 # madde 674: sunucu zamanlayıcısı her gün dener; hazırsa dokunma
        try:
            if "MANIFEST.txt" in zipfile.ZipFile(cikti).namelist():
                print(f"{os.path.basename(cikti)} zaten var"); return 0
        except zipfile.BadZipFile:
            pass
    # yayın kontrolü: BTC'nin aylık funding dosyası yoksa ay henüz yayınlanmamış
    if indir(f"{B}/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{ay}.zip") is None:
        print(f"!! {ay} aylık dosyaları henüz yayınlanmamış (Binance genelde ayın 1-3'ünde yayınlar). Yarın tekrar deneyin.")
        return 1
    ii = isler(semboller, ay, metrikli)
    # MADDE 675: Binance API'sine erişilebiliyorsa sembol bilgisi (yeni listelemelerin TradFi olup olmadığı) pakete girer
    bilgi_ham = indir(FAPI, deneme=2)
    try:
        bilgi = json.loads(bilgi_ham) if bilgi_ham else None
    except ValueError:
        bilgi = None
    yeni, yeni_tf = ([], [])
    if "--yeni-yok" not in argv:
        yeni, yeni_tf = yeni_semboller(set(semboller), bilgi)
        for s_ in yeni:
            ii += yeni_isler(s_, ay)
        if bilgi is None:
            print("not: Binance API'sine (exchangeInfo) erişilemedi -> yeni listelenen coinler bu pakete girmedi (mevcut coinler tam)")
        print(f"yeni sembol: {len(yeni)} kripto ({', '.join(yeni[:12])}{' ...' if len(yeni) > 12 else ''}) · {len(yeni_tf)} TradFi (atlandı)")
    print(f"{ay}: {len(semboller)} sembol, {len(ii)} dosya indiriliyor -> {cikti}")
    sayac = {"k": 0, "f": 0, "m": 0, "yok": 0}
    with zipfile.ZipFile(cikti, "w", zipfile.ZIP_STORED) as zf, ThreadPoolExecutor(16) as ex:
        for n, ((url, ad), veri) in enumerate(zip(ii, ex.map(lambda x: indir(x[0]), ii))):
            if veri is None:
                sayac["yok"] += 1
            else:
                zf.writestr(ad, veri); sayac[ad.split("/")[1][0]] += 1
            if n % 2000 == 0:
                print(f"  {n}/{len(ii)}  {sayac}", flush=True)
        if bilgi:
            zf.writestr("exchangeInfo.json", bilgi_ham)
        zf.writestr("MANIFEST.txt", f"ay={ay}\nsembol={len(semboller)}\n{sayac}\nzaman={dt.datetime.now().isoformat()}\n"
                                    f"yeni={','.join(yeni)}\ntradfi_yeni={','.join(yeni_tf)}\n")
    if sayac["f"] < min(100, len(semboller) // 2):
        print(f"!! funding dosyası çok az ({sayac}): internet / Binance erişimini kontrol edin")
        os.remove(cikti)
        return 1
    print(f"BİTTİ: {sayac} — '{os.path.basename(cikti)}' dosyasını sohbete yükleyin.")
    if "--bildir" in argv:                    # madde 674: sunucuda Telegram'a haber
        try:
            sys.path.insert(0, R); import bildirim
            for l in open(os.path.join(R, ".env"), encoding="utf-8"):      # YALNIZ TELEGRAM_* (anahtarlar okunmaz)
                k, _, v = l.strip().partition("=")
                if k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID") and v and not os.getenv(k):
                    os.environ[k] = v.split("#")[0].strip()
            os.environ.setdefault("CARRY_BILDIRIM_AD", "veri")
            bildirim.gonder(f"📦 {ay} veri paketi hazır ({os.path.getsize(cikti) / 1e6:.0f} MB) — panelden indirip araştırma sohbetine yükleyin")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
