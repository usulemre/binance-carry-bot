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

from carry_gunluk_defter import DEFTER_KLASOR, _pozisyonlar

ANLIK_DOSYA = os.path.join(DEFTER_KLASOR, "anlik.json")


def yaz(client=None, simdi: float | None = None, dosya: str = ANLIK_DOSYA) -> dict:
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
    os.makedirs(os.path.dirname(dosya) or ".", exist_ok=True)
    gecici = dosya + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:   # panel yarım dosya okumasın: önce geçici, sonra tek adımda değiştir
        json.dump(kayit, f, ensure_ascii=False)
    os.replace(gecici, dosya)
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
