#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 829 — SALT OKUR teşhis: "-2022 ReduceOnly Order is rejected" (AKEUSDT, 20 Kas 09:55 UTC+3).

Hiç emir GÖNDERMEZ / iptal ETMEZ. Bot çalışırken de güvenle çalışır:
    cd /opt/carry && sudo -u carry .venv/bin/python teshis_reduceonly.py [SEMBOL] [GUN]
    (varsayılan AKEUSDT 2026-11-20)

Bakılanlar:
  1) Her açık pozisyon için borsadaki açık reduceOnly emirlerin TOPLAM adedi; toplam > pozisyon ise
     yeni reduceOnly emir (piyasa kapanışı dahil) -2022 ile reddedilebilir.
  2) Borsada olup botun durumunda (kar_al / merdiven / felaket) KAYITLI OLMAYAN "yetim" emirler —
     kar_al_iptal iptal hatasını sessizce yutup kaydı siliyor; yetim emir iptal edilmeden kalır.
  3) Sembolün o günkü işlemleri (gerçekleşen kapanış ne zaman, hangi fiyattan) ve tüm emir geçmişi.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import config
import carry_bot as cb
from exchange_client import ExchangeClient


def _ts(ms) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, timezone(timedelta(hours=3))).strftime("%m-%d %H:%M:%S")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sem = argv[0] if argv else "AKEUSDT"
    gun = argv[1] if len(argv) > 1 else "2026-11-20"
    c = ExchangeClient(config.API_KEY, config.API_SECRET, mode=getattr(config, "MODE", "demo"))
    durum = cb.dilim_durum_oku()
    kayitli = set()
    for k in ("kar_al", "felaket"):
        kayitli |= {str(v) for v in (durum.get(k) or {}).values()}
    kayitli |= {str(v.get("oid")) for v in (durum.get("merdiven") or {}).values()}

    poz = {p["symbol"]: float(p["positionAmt"]) for p in c.get_open_positions()}
    acik = c.client.futures_get_open_orders()
    ro = defaultdict(float)
    print(f"== 1-2) açık pozisyon {len(poz)}, açık normal emir {len(acik)}")
    yetim = 0
    for e in acik:
        if str(e.get("reduceOnly")).lower() == "true":
            ro[e["symbol"]] += float(e["origQty"]) - float(e.get("executedQty", 0) or 0)
        if str(e["orderId"]) not in kayitli:
            yetim += 1
            print(f"  YETİM  {e['symbol']:<14} {e['type']:<7} {e['side']:<4} adet {e['origQty']:>12} fiyat {e['price']:>12} "
                  f"reduceOnly={e.get('reduceOnly')} açıldı {_ts(e['time'])}")
    for s, q in sorted(ro.items()):
        p = abs(poz.get(s, 0.0))
        if q > p * 1.001:
            print(f"  FAZLA  {s:<14} açık reduceOnly toplam {q:g} > pozisyon {p:g}  → yeni reduceOnly -2022 riski")
    f = getattr(c.client, "futures_get_open_algo_orders", None)
    if f:
        try:
            algo = f()
            algo = algo.get("orders", algo) if isinstance(algo, dict) else algo
            for e in algo or []:
                if str(e.get("algoId")) not in kayitli:
                    yetim += 1
                    print(f"  YETİM ALGO {e.get('symbol'):<14} {e.get('orderType', e.get('type'))} {e.get('side')} "
                          f"adet {e.get('quantity')} tetik {e.get('triggerPrice')}")
        except Exception as ex:
            print(f"  (algo emirleri okunamadı: {ex})")
    print(f"  yetim emir sayısı: {yetim}  (0 olmalı)")

    t0 = int(datetime.fromisoformat(gun).replace(tzinfo=timezone(timedelta(hours=3))).timestamp() * 1000)
    t1 = t0 + 2 * 86400 * 1000
    print(f"\n== 3) {sem} emir geçmişi {gun} 00:00 (+3) itibaren 48 sa")
    try:
        for e in c.client.futures_get_all_orders(symbol=sem, startTime=t0, endTime=t1, limit=200):
            print(f"  {_ts(e['time'])} {e['type']:<7} {e['side']:<4} adet {e['origQty']:>12} dolan {e['executedQty']:>12} "
                  f"durum {e['status']:<9} reduceOnly={e.get('reduceOnly')} oid {e['orderId']}")
    except Exception as ex:
        print(f"  okunamadı: {ex}")
    print(f"\n== {sem} gerçekleşen işlemler")
    try:
        for t in c.client.futures_account_trades(symbol=sem, startTime=t0, endTime=t1, limit=500):
            print(f"  {_ts(t['time'])} {t['side']:<4} adet {t['qty']:>12} fiyat {t['price']:>12} realizedPnl {t['realizedPnl']:>10}")
    except Exception as ex:
        print(f"  okunamadı: {ex}")
    print(f"\nşu an {sem} pozisyonu: {poz.get(sem, 0.0)}  açık reduceOnly toplam: {ro.get(sem, 0.0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
