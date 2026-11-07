# -*- coding: utf-8 -*-
"""MADDE 728 — ANLIK POZİSYON GÖRÜNTÜSÜ (panel için, SALT OKUR).

Panel güvenlik gereği Binance'e bağlanmaz; pozisyonları günlük defterden (günde bir, 00:05 UTC) okuyordu, yani kâr / zarar
sütunu gün içinde hiç oynamıyordu. Bu betik açık pozisyonları ve işaret fiyatlarını okuyup `defter/anlik.json`'a yazar;
panel bu dosya tazeyse (PANEL: ANLIK_TAZE_SN) pozisyon tablosunu buradan gösterir, değilse günlük deftere döner.

HİÇBİR EMİR GÖNDERMEZ: yalnız get_open_positions + get_account_equity_usd. Günlük defter, rapor ve getiri serisi değişmez.
Sunucuda carry-anlik.timer ile 5 dakikada bir çalışır (deploy/carry-anlik.*). Elle:
    cd /opt/carry && sudo -u carry .venv/bin/python carry_anlik.py
"""
from __future__ import annotations

import json
import os
import sys
import time

from carry_gunluk_defter import DEFTER_DOSYA, DEFTER_KLASOR, _pozisyonlar

ANLIK_DOSYA = os.path.join(DEFTER_KLASOR, "anlik.json")
BIRIKIM_DOSYA = os.path.join(DEFTER_KLASOR, "gelir_birikim.json")
ORTUSME_MS = 10 * 60 * 1000   # geç düşen gelir kaydı kaçmasın: son 10 dk yeniden sorulur, tranId ile tekilleşir


def _ilk_zaman(defter_dosya: str) -> int | None:
    """Günlük defterin İLK satırının zamanı (= panelin 'başlangıç'ı)."""
    try:
        with open(defter_dosya, encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    return int(json.loads(l)["zaman"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def _atomik_yaz(dosya: str, veri: dict) -> None:
    os.makedirs(os.path.dirname(dosya) or ".", exist_ok=True)
    gecici = dosya + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:   # yarım dosya okunmasın: önce geçici, sonra tek adımda değiştir
        json.dump(veri, f, ensure_ascii=False)
    os.replace(gecici, dosya)


def gelir_birikim(client, bas_s: int, simdi: float, dosya: str = BIRIKIM_DOSYA) -> dict:
    """MADDE 733: başlangıçtan beri gelir türü toplamları (funding, komisyon, gerçekleşen, transfer), ARTIMLI.
    Her çalışmada yalnız son kayıttan bu yana sorulur (10 dk örtüşme + tranId tekilleştirme). Borsa okunamazsa
    istisna yukarı çıkar ve birikim DEĞİŞMEZ (eksik sayılmaz)."""
    bas_ms = int(bas_s) * 1000
    try:
        with open(dosya, encoding="utf-8") as f:
            b = json.load(f)
        if b.get("bas_ms") != bas_ms:
            raise ValueError("başlangıç değişti")
    except (OSError, ValueError, AttributeError):
        b = {"bas_ms": bas_ms, "son_ms": bas_ms, "toplam": {}, "idler": {}}
    bit_ms = int(simdi * 1000)
    idler = dict(b.get("idler") or {})   # kimlik -> kayıt zamanı (ms); yalnız örtüşme penceresindekiler saklanır
    toplam = dict(b.get("toplam", {}))
    s = max(bas_ms, int(b["son_ms"]) - ORTUSME_MS)
    son = bit_ms
    for _ in range(50):
        r = client.client.futures_income_history(startTime=s, endTime=bit_ms, limit=1000)
        for g in r:
            kimlik = f"{g.get('tranId')}:{g.get('incomeType')}:{g.get('symbol')}"
            if kimlik in idler:
                continue
            idler[kimlik] = int(g["time"])
            t = g.get("incomeType") or "?"
            toplam[t] = toplam.get(t, 0.0) + float(g.get("income") or 0)
        if len(r) < 1000:
            break
        s = int(r[-1]["time"]) + 1
    else:
        son = s - 1   # 50 sayfa yetmedi: kalanı sonraki çalışmada
    idler = {k: t for k, t in idler.items() if t >= son - 2 * ORTUSME_MS}
    b = {"bas_ms": bas_ms, "son_ms": son, "toplam": {k: round(v, 6) for k, v in toplam.items()}, "idler": idler}
    _atomik_yaz(dosya, b)
    return b


def yaz(client=None, simdi: float | None = None, dosya: str = ANLIK_DOSYA,
        defter_dosya: str = DEFTER_DOSYA, birikim_dosya: str | None = None) -> dict:
    if client is None:
        import config
        from exchange_client import ExchangeClient
        client = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    simdi = simdi or time.time()
    poz = _pozisyonlar(client)
    oz = float(client.get_account_equity_usd())
    olcek = float(os.getenv("CARRY_SERMAYE_OLCEK", "1.0") or 1.0)
    kayit = {
        "zaman": int(simdi),
        "ozkaynak": round(oz, 4),
        "kitap": round(oz * olcek, 4),
        "pozisyonlar": poz,
        "gerceklesmemis_top": round(sum(p["gerceklesmemis"] for p in poz.values()), 2),
    }
    bas = _ilk_zaman(defter_dosya)
    if bas is not None:   # madde 733: panel döküm satırı (pozisyonlar · gerçekleşen · funding · komisyon)
        bd = birikim_dosya or os.path.join(os.path.dirname(dosya) or ".", "gelir_birikim.json")
        try:
            g = gelir_birikim(client, bas, simdi, bd)
            kayit["gelir_bas"] = {"bas": bas, "son": g["son_ms"] // 1000, **g["toplam"]}
        except Exception as ex:
            print(f"UYARI: gelir birikimi güncellenemedi: {ex}", file=sys.stderr)
    _atomik_yaz(dosya, kayit)
    return kayit


def main() -> int:
    try:
        k = yaz()
    except Exception as ex:
        print(f"anlık görüntü alınamadı: {ex}", file=sys.stderr)
        return 1
    print(f"{len(k['pozisyonlar'])} pozisyon · gerçekleşmemiş {k['gerceklesmemis_top']:+.2f} $ · kitap {k['kitap']:,.2f} $")
    return 0


if __name__ == "__main__":
    sys.exit(main())
