#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 680 testleri: işlem günlüğü SQLite'a yazılır, aynı gün yenilenir, aylık özet bileşik getiriyi doğru verir, coin sorgusu."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defter_db as D
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1
T = tempfile.mkdtemp(); db = os.path.join(T, "carry.db"); jl = os.path.join(T, "gunluk.jsonl")
def kayit(t, g, f=1.0):
    return {"tarih": t, "ozkaynak": 1000, "kitap": 1000, "gun_getiri": g, "profil": "T7K", "doz": "1.15",
            "gelir_24s": {"FUNDING_FEE": f, "REALIZED_PNL": -0.5, "COMMISSION": -0.1, "TRANSFER": 0},
            "pozisyonlar": {"AUSDT": {"yon": "L", "usd": 100, "giris": 1, "isaret": 1.1, "kar_yuzde": 10}},
            "gelir_coin": {"AUSDT": {"FUNDING_FEE": f, "REALIZED_PNL": -0.5, "COMMISSION": -0.1}}}
with open(jl, "w") as fh:
    for t, g in [("2026-10-01", None), ("2026-10-02", 0.10), ("2026-10-03", -0.05), ("2026-11-01", 0.02)]:
        fh.write(json.dumps(kayit(t, g)) + "\n")
    fh.write("{bozuk\n")
kontrol("aktar: 4 gün (bozuk satır atlandı)", D.aktar(jl, db) == 4)
kontrol("aktar tekrar: çift kayıt yok", D.aktar(jl, db) == 4 and D.baglan(db).execute("SELECT COUNT(*) FROM gunluk").fetchone()[0] == 4)
o = {r[0]: r for r in D.ozet(db)}
kontrol("aylık bileşik getiri (1,10×0,95−1 = %4,5)", abs(o["2026-10"][2] - 4.5) < 1e-6, o)
kontrol("aylık funding toplamı", abs(o["2026-10"][3] - 3.0) < 1e-9 and o["2026-11"][1] == 1)
D.yaz(kayit("2026-11-01", 0.03, f=5.0), db)
c = D.baglan(db)
kontrol("aynı gün yeniden yazılınca yenilenir", c.execute("SELECT gun_getiri, funding FROM gunluk WHERE tarih='2026-11-01'").fetchone() == (0.03, 5.0)
        and c.execute("SELECT COUNT(*) FROM pozisyon WHERE tarih='2026-11-01'").fetchone()[0] == 1)
r = D.coin(30, db)
kontrol("coin sorgusu: son 30 gün net (10-02..11-01, 3 gün)", r[0][0] == "AUSDT" and abs(r[0][4] - (1 + 1 + 5 - 3 * 0.6)) < 1e-6, r)
print(f"\nSONUÇ: {_h} hata"); sys.exit(1 if _h else 0)
