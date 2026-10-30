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
import datetime as dt
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

B = "https://data.binance.vision/data/futures/um"
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
        zf.writestr("MANIFEST.txt", f"ay={ay}\nsembol={len(semboller)}\n{sayac}\nzaman={dt.datetime.now().isoformat()}\n")
    if sayac["f"] < 100:
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
