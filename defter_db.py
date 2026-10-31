# -*- coding: utf-8 -*-
"""MADDE 680 — İŞLEM GÜNLÜĞÜ VERİTABANI (SQLite; Python'un kendi içinde, ek paket yok).

Günlük defterin (defter/gunluk.jsonl) her kaydı ayrıca defter/carry.db'ye yazılır; sorular saniyede cevaplanır:
    .venv/bin/python defter_db.py ozet                 # aylık getiri, funding, komisyon
    .venv/bin/python defter_db.py coin [30]            # son N günde coin bazında funding + gerçekleşen kâr (en iyi / en kötü)
    .venv/bin/python defter_db.py aktar                # var olan gunluk.jsonl'u veritabanına (bir kez; tekrar çalıştırmak güvenli)
    .venv/bin/python defter_db.py sql "SELECT ..."      # serbest sorgu
Tablolar: gunluk (tarih başına özkaynak / getiri / gelirler), pozisyon (tarih × sembol), gelir_coin (tarih × sembol gelirleri).
Veritabanı yalnız OKUMA amaçlıdır; bot kararlarını etkilemez. Bozulursa silinip `aktar` ile yeniden kurulur (kaynak jsonl).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

KLASOR = os.getenv("CARRY_DEFTER_KLASOR", "defter")
DB = os.path.join(KLASOR, "carry.db")
SEMA = """
CREATE TABLE IF NOT EXISTS gunluk (tarih TEXT PRIMARY KEY, ozkaynak REAL, kitap REAL, gun_getiri REAL, funding REAL,
    gerceklesen REAL, komisyon REAL, transfer REAL, profil TEXT, doz TEXT, pozisyon_sayisi INTEGER);
CREATE TABLE IF NOT EXISTS pozisyon (tarih TEXT, sembol TEXT, yon TEXT, usd REAL, giris REAL, isaret REAL, kar_yuzde REAL,
    PRIMARY KEY (tarih, sembol));
CREATE TABLE IF NOT EXISTS gelir_coin (tarih TEXT, sembol TEXT, funding REAL, gerceklesen REAL, komisyon REAL,
    PRIMARY KEY (tarih, sembol));
"""


def baglan(db: str = DB) -> sqlite3.Connection:
    import math
    os.makedirs(os.path.dirname(db) or ".", exist_ok=True)
    c = sqlite3.connect(db, timeout=10)
    c.executescript(SEMA)
    c.create_function("LN", 1, lambda x: math.log(x) if x and x > 0 else None)    # SQLite'ta yerleşik değil
    c.create_function("EXP", 1, lambda x: math.exp(x) if x is not None else None)
    return c


def yaz(k: dict, db: str = DB) -> None:
    """Bir günlük kaydı (carry_gunluk_defter.topla çıktısı) yazar; aynı gün tekrar gelirse o günün satırları yenilenir."""
    g = k.get("gelir_24s", {}) or {}
    poz = k.get("pozisyonlar", {}) or {}
    with baglan(db) as c:
        t = k["tarih"]
        c.execute("INSERT OR REPLACE INTO gunluk VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (t, k.get("ozkaynak"), k.get("kitap"), k.get("gun_getiri"), g.get("FUNDING_FEE"), g.get("REALIZED_PNL"),
                   g.get("COMMISSION"), g.get("TRANSFER"), k.get("profil"), str(k.get("doz")), len(poz)))
        c.execute("DELETE FROM pozisyon WHERE tarih=?", (t,)); c.execute("DELETE FROM gelir_coin WHERE tarih=?", (t,))
        c.executemany("INSERT INTO pozisyon VALUES (?,?,?,?,?,?,?)",
                      [(t, s, v.get("yon"), v.get("usd"), v.get("giris"), v.get("isaret"), v.get("kar_yuzde")) for s, v in poz.items()])
        c.executemany("INSERT INTO gelir_coin VALUES (?,?,?,?,?)",
                      [(t, s, v.get("FUNDING_FEE", 0), v.get("REALIZED_PNL", 0), v.get("COMMISSION", 0))
                       for s, v in (k.get("gelir_coin", {}) or {}).items()])


def aktar(jsonl: str = os.path.join(KLASOR, "gunluk.jsonl"), db: str = DB) -> int:
    n = 0
    if not os.path.exists(jsonl):
        return 0
    for l in open(jsonl, encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        try:
            yaz(json.loads(l), db); n += 1
        except (ValueError, KeyError):
            pass
    return n


def ozet(db: str = DB) -> list[tuple]:
    with baglan(db) as c:
        return c.execute("""SELECT substr(tarih,1,7) ay, COUNT(*) gun,
                   ROUND((EXP(SUM(LN(1+COALESCE(gun_getiri,0))))-1)*100, 2) getiri_yuzde,
                   ROUND(SUM(funding),2), ROUND(SUM(gerceklesen),2), ROUND(SUM(komisyon),2), ROUND(SUM(transfer),2)
                   FROM gunluk GROUP BY ay ORDER BY ay""").fetchall()


def coin(gun: int = 30, db: str = DB) -> list[tuple]:
    with baglan(db) as c:
        return c.execute("""SELECT sembol, ROUND(SUM(funding),2) f, ROUND(SUM(gerceklesen),2) g, ROUND(SUM(komisyon),2) k,
                   ROUND(SUM(funding+gerceklesen+komisyon),2) net FROM gelir_coin
                   WHERE tarih >= date((SELECT MAX(tarih) FROM gunluk), ?) GROUP BY sembol ORDER BY net DESC""",
                         (f"-{int(gun)} day",)).fetchall()


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "ozet"
    if komut == "aktar":
        print(f"{aktar()} gün aktarıldı -> {DB}")
    elif komut == "ozet":
        print(f"{'ay':8s} {'gün':>4s} {'getiri %':>9s} {'funding':>9s} {'gerçekl.':>9s} {'komisyon':>9s} {'transfer':>9s}")
        for r in ozet():
            print(f"{r[0]:8s} {r[1]:4d} {r[2] or 0:+9.2f} " + " ".join(f"{x or 0:+9.2f}" for x in r[3:]))
    elif komut == "coin":
        L = coin(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
        print(f"{'coin':14s} {'funding':>9s} {'gerçekl.':>9s} {'komisyon':>9s} {'net $':>9s}")
        for r in L[:10] + ([("...",)] if len(L) > 20 else []) + (L[-10:] if len(L) > 20 else L[10:]):
            print(r[0] if len(r) == 1 else f"{r[0]:14s} " + " ".join(f"{x:+9.2f}" for x in r[1:]))
    elif komut == "sql":
        with baglan() as c:
            for r in c.execute(sys.argv[2]).fetchall():
                print(r)
    else:
        print(__doc__)
