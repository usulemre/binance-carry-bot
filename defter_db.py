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


# MADDE 701: EMİR DEFTERİ — botun gönderdiği her emir + borsadan okunan dolumu (yalnız KAYIT; bot kararlarını etkilemez).
# Demo metrikleri (madde 695): TP'nin fiyat dokununca dolma oranı, kısmi dolum, kayma, maker payı, gerçek komisyon.
SEMA_EMIR = """
CREATE TABLE IF NOT EXISTS emir (id INTEGER PRIMARY KEY AUTOINCREMENT, zaman REAL, sembol TEXT, tur TEXT, yon TEXT, adet REAL,
    limit_fiyat REAL, ref_fiyat REAL, giris REAL, deneme INTEGER, oid TEXT, durum TEXT, dolan REAL, ort_fiyat REAL,
    kapanis REAL, maker_adet REAL, komisyon REAL, kom_varlik TEXT, eslendi INTEGER DEFAULT 0, dokundu INTEGER, guncel REAL);
CREATE INDEX IF NOT EXISTS emir_oid ON emir (sembol, oid);
CREATE INDEX IF NOT EXISTS emir_zaman ON emir (zaman);
"""
EMIR_TURLERI = ("GIRIS", "KOVALA", "PIYASA", "PIYASA_YEDEK", "TP", "KADEME", "FELAKET")
_BITMIS = ("FILLED", "CANCELED", "EXPIRED", "REJECTED", "EXPIRED_IN_MATCH")


def _f(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


class _emir_baglan:
    """Kısa ömürlü bağlantı: aç → yaz → commit → KAPAT (kilit tutulmaz). Kilit 0,5 sn'de çözülmezse kayıt atlanır;
    bot turu hiçbir zaman defter yüzünden beklemez."""
    def __init__(self, db: str):
        self.db = db

    def __enter__(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db) or ".", exist_ok=True)
        self.c = sqlite3.connect(self.db, timeout=0.5)
        self.c.executescript(SEMA_EMIR)
        return self.c

    def __exit__(self, et, ev, tb):
        try:
            if et is None:
                self.c.commit()
        finally:
            self.c.close()
        return False


def emir_kaydet(tur: str, sembol: str, yon: str, adet, limit=None, ref=None, oid=None, giris=None, deneme=None,
                db: str = DB, simdi: float | None = None) -> bool:
    """Gönderilen bir emri yazar. ASLA hata fırlatmaz (defter bir ölçüm aracı; bot akışı değişmez)."""
    try:
        import time as _t
        with _emir_baglan(db) as c:
            c.execute("INSERT INTO emir (zaman,sembol,tur,yon,adet,limit_fiyat,ref_fiyat,giris,deneme,oid) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (simdi or _t.time(), str(sembol), str(tur), str(yon), _f(adet), _f(limit), _f(ref), _f(giris),
                       None if deneme is None else int(deneme), None if oid is None else str(oid)))
        return True
    except Exception:
        return False


def emir_durum(sembol: str, oid, e: dict, db: str = DB, simdi: float | None = None) -> bool:
    """Borsadan zaten okunmuş bir emir cevabını (futures_get_order) kayda işler. Ek API çağrısı YAPMAZ. Hata fırlatmaz."""
    try:
        import time as _t
        if oid is None or not isinstance(e, dict):
            return False
        st = str(e.get("status", "")).upper()
        with _emir_baglan(db) as c:
            c.execute("UPDATE emir SET durum=?, dolan=?, ort_fiyat=COALESCE(?,ort_fiyat), kapanis=COALESCE(?,kapanis), guncel=? "
                      "WHERE sembol=? AND oid=?",
                      (st, _f(e.get("executedQty")), _f(e.get("avgPrice")) or None,
                       (_f(e.get("updateTime")) or 0) / 1000 or None if st in _BITMIS else None, simdi or _t.time(),
                       str(sembol), str(oid)))
        return True
    except Exception:
        return False


def emir_esle(client, en_cok: int = 40, db: str = DB, simdi: float | None = None) -> int:
    """Dolumu henüz eşleşmemiş emirlerin durumunu ve gerçekleşen işlemlerini (maker/taker, komisyon) borsadan OKUR.
    Tur sonunda çağrılır; en çok `en_cok` emir (API yükü sınırlı). Hata fırlatmaz; eşleşen emir sayısını döner."""
    import time as _t
    simdi = simdi or _t.time(); n = 0
    try:
        with _emir_baglan(db) as c:
            satir = c.execute("SELECT id, sembol, oid FROM emir WHERE eslendi=0 AND oid IS NOT NULL AND tur!='FELAKET' "
                              "AND zaman>? AND (zaman<? OR durum IN ('FILLED','CANCELED','EXPIRED','REJECTED')) "
                              "ORDER BY zaman LIMIT ?", (simdi - 3 * 86400, simdi - 600, int(en_cok))).fetchall()
    except Exception:
        return 0
    for rid, sem, oid in satir:
        try:
            e = client.client.futures_get_order(symbol=sem, orderId=int(oid))
            st = str(e.get("status", "")).upper(); dolan = _f(e.get("executedQty")) or 0.0
            maker = kom = None; varlik = None
            if dolan > 0:
                tr = client.client.futures_account_trades(symbol=sem, orderId=int(oid)) or []
                maker = sum(_f(t.get("qty")) or 0 for t in tr if t.get("maker"))
                kom = sum(_f(t.get("commission")) or 0 for t in tr)
                varlik = ",".join(sorted({str(t.get("commissionAsset")) for t in tr if t.get("commissionAsset")})) or None
            with _emir_baglan(db) as c:
                c.execute("UPDATE emir SET durum=?, dolan=?, ort_fiyat=?, kapanis=?, maker_adet=?, komisyon=?, kom_varlik=?, "
                          "eslendi=?, guncel=? WHERE id=?",
                          (st, dolan, _f(e.get("avgPrice")) or None, (_f(e.get("updateTime")) or 0) / 1000 or None,
                           maker, kom, varlik, 1 if st in _BITMIS else 0, simdi, rid))
            n += 1
        except Exception:
            continue
    return n


def tp_dokunma(client, en_cok: int = 200, db: str = DB, simdi: float | None = None) -> int:
    """Kapanmış TP / kademe emirleri için fiyat limit seviyesine DEĞDİ Mİ? (madde 695'in asıl sorusu: dokununca dolma oranı)
    Dolmuşsa değmiştir; dolmadan iptal olduysa açık kaldığı süredeki 5 dk mumların uç değerine bakılır. Günde bir (defter işi)."""
    import time as _t
    simdi = simdi or _t.time(); n = 0
    try:
        with _emir_baglan(db) as c:
            c.execute("UPDATE emir SET dokundu=1 WHERE tur IN ('TP','KADEME') AND dokundu IS NULL AND COALESCE(dolan,0)>0")
            satir = c.execute("SELECT id, sembol, yon, limit_fiyat, zaman, kapanis FROM emir WHERE tur IN ('TP','KADEME') "
                              "AND dokundu IS NULL AND eslendi=1 AND kapanis IS NOT NULL AND limit_fiyat IS NOT NULL "
                              "AND kapanis<? ORDER BY zaman LIMIT ?", (simdi - 300, int(en_cok))).fetchall()
    except Exception:
        return 0
    for rid, sem, yon, lim, t0, t1 in satir:
        try:
            k = client.client.futures_klines(symbol=sem, interval="5m", startTime=int(t0 * 1000), endTime=int(t1 * 1000), limit=1000)
            if not k:
                continue
            dg = (max(float(x[2]) for x in k) >= lim) if str(yon).upper() == "SELL" else (min(float(x[3]) for x in k) <= lim)
            with _emir_baglan(db) as c:
                c.execute("UPDATE emir SET dokundu=? WHERE id=?", (1 if dg else 0, rid))
            n += 1
        except Exception:
            continue
    return n


def icra_ozet(gun: float = 30, db: str = DB, simdi: float | None = None) -> dict | None:
    """Panel için son `gun` günün icra metrikleri (SALT OKUNUR açılır). Veri yoksa None."""
    import time as _t
    if not os.path.exists(db):
        return None
    simdi = simdi or _t.time(); bas = simdi - gun * 86400
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        try:
            if not c.execute("SELECT name FROM sqlite_master WHERE name='emir'").fetchone():
                return None
            R = c.execute("SELECT tur, yon, adet, ref_fiyat, durum, dolan, ort_fiyat, maker_adet, komisyon, kom_varlik, dokundu, deneme "
                          "FROM emir WHERE zaman>=?", (bas,)).fetchall()
        finally:
            c.close()
    except Exception:
        return None
    if not R:
        return None
    out = {"emir": len(R), "tur": {}}
    for r in R:
        out["tur"][r[0]] = out["tur"].get(r[0], 0) + 1
    tp = [r for r in R if r[0] in ("TP", "KADEME")]
    tam = sum(1 for r in tp if r[4] == "FILLED")
    kismi = sum(1 for r in tp if (r[5] or 0) > 0 and r[4] != "FILLED")
    olc = [r for r in tp if r[10] is not None]; dok = [r for r in olc if r[10] == 1]
    dok_dolan = sum(1 for r in dok if (r[5] or 0) > 0)
    out["tp"] = {"konan": len(tp), "tam": tam, "kismi": kismi, "olculen": len(olc), "dokunan": len(dok),
                 "dolum_orani": (dok_dolan / len(dok)) if dok else None,
                 "kismi_pay": (kismi / (tam + kismi)) if (tam + kismi) else None}
    gr = [r for r in R if r[0] in ("GIRIS", "KOVALA", "PIYASA", "PIYASA_YEDEK") and (r[5] or 0) > 0 and r[6]]
    nos = sum(r[5] * r[6] for r in gr)
    mk = [r for r in gr if r[7] is not None]
    ky = [r for r in gr if r[3]]
    w = sum(r[5] * r[6] for r in ky)
    kom_usdt = [r for r in gr if r[8] is not None and (r[9] or "") == "USDT"]
    out["giris"] = {"dolan_emir": len(gr), "notional": nos,
                    "maker_pay": (sum(r[7] * r[6] for r in mk) / sum(r[5] * r[6] for r in mk)) if mk else None,
                    "kayma_bp": (sum((r[6] / r[3] - 1) * (1 if str(r[1]).upper() == "BUY" else -1) * 1e4 * r[5] * r[6] for r in ky) / w) if w else None,
                    "komisyon_bp": (sum(r[8] for r in kom_usdt) / sum(r[5] * r[6] for r in kom_usdt) * 1e4) if kom_usdt else None,
                    "gtx_ilk": sum(1 for r in R if r[0] == "GIRIS" and (r[11] or 0) == 0),
                    "kovala": out["tur"].get("KOVALA", 0), "piyasa_yedek": out["tur"].get("PIYASA_YEDEK", 0)}
    return out


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
