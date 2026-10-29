#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 663 — ACİL DURDURMA: bütün emirleri iptal et, bütün pozisyonları kapat, dilim defterini boşalt.

Ne zaman: hesabın / sunucunun ele geçirildiğinden şüpheleniyorsanız, beklenmedik bir şey oluyorsa ya da botu tamamen bırakıyorsanız.
ÖNCE botu durdurun (yoksa bir sonraki turda yeniden açar):
    sudo systemctl stop carry                          (çoklu demo: sudo systemctl stop 'carry@*')
    cd /opt/carry && sudo -u carry .venv/bin/python acil_kapat.py          # yalnız LİSTELER (emir göndermez)
    cd /opt/carry && sudo -u carry .venv/bin/python acil_kapat.py --evet   # gerçekten kapatır
Pozisyonlar piyasa emriyle (reduceOnly) kapanır: ince coinlerde kayma olabilir. Anahtarın çalındığından şüpheleniyorsanız ayrıca
Binance'te API anahtarını SİLİN (Hesap → API Management) — bu, sunucudaki her şeyden önce gelir.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

import config
import carry_bot as cb
from exchange_client import ExchangeClient


def servis_acik() -> bool:
    try:
        r = subprocess.run(["systemctl", "is-active", "carry"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "active"
    except Exception:
        return False


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evet", action="store_true", help="gerçekten iptal et ve kapat (yoksa yalnız listeler)")
    ap.add_argument("--servis-kontrolu-yok", action="store_true", help="çalışan bot servisini kontrol etme (test)")
    a = ap.parse_args(argv)
    if a.evet and not a.servis_kontrolu_yok and servis_acik():
        print("!! 'carry' servisi ÇALIŞIYOR — önce: sudo systemctl stop carry  (yoksa bot pozisyonları yeniden açar)")
        return 2
    client = client or ExchangeClient(config.API_KEY, config.API_SECRET, mode=getattr(config, "MODE", "demo"))
    print(f"mod: {getattr(client, 'mode', '?')}")
    pozlar = [p for p in client.get_open_positions() if float(p.get("positionAmt", 0) or 0) != 0]
    print(f"açık pozisyon: {len(pozlar)}")
    for p in pozlar:
        print(f"  {p['symbol']:<16} {float(p['positionAmt']):>16}")
    if not a.evet:
        print("\n(yalnız liste — kapatmak için --evet)")
        return 0
    durum = cb.dilim_durum_oku()
    cb.kar_al_iptal(client, durum)                       # kayıtlı kâr al / kademe / felaket (algo) emirleri
    semboller = {p["symbol"] for p in pozlar}
    try:
        for e in client.client.futures_get_open_orders():
            semboller.add(e["symbol"])
    except Exception as e:
        print(f"!! açık emirler listelenemedi: {e}")
    hata = 0
    for s in sorted(semboller):
        try:
            client.client.futures_cancel_all_open_orders(symbol=s)
        except Exception as e:
            print(f"!! {s} emirleri iptal edilemedi: {e}"); hata += 1
    for p in pozlar:
        adet = float(p["positionAmt"])
        try:
            client.close_position(p["symbol"], "SELL" if adet > 0 else "BUY", abs(adet))
            print(f"  KAPANDI {p['symbol']}")
        except Exception as e:
            print(f"!! {p['symbol']} KAPATILAMADI: {e} — Binance'te elle kapatın"); hata += 1
    durum["dilimler"] = {}
    cb.dilim_durum_yaz(durum)
    print("\nbitti" + (f" — {hata} hata, Binance'i kontrol edin" if hata else " — bütün pozisyonlar kapandı, dilim defteri boşaltıldı"))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
