#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 753 — "gerçek Binance oranlarıyla olsaydı" funding'inin BAĞIMSIZ doğrulaması (kullanıcı: "kesin doğru mu bilmem lazım").

carry_anlik'in hesapladığı her funding ödemesini (defter/funding_olay.json, "g") baştan, ayrı bir yoldan yeniden hesaplar:
  * oran ve işaret fiyatı: Binance'in HERKESE AÇIK resmi funding geçmişi (/fapi/v1/fundingRate) — anahtar yok, emir yok;
  * pozisyon: ödeme anından ÖNCEKİ son pozisyon görüntüsü (defter/anlik_poz.json; 5 dk'da bir, yalnız değişince yazılır);
  * tutar = −adet × işaret fiyatı × oran  (Binance'in funding formülü: pozisyon değeri × oran; long pozitif oranda öder).
Panelin kaydıyla karşılaştırır: ödeme ödeme fark, coin başına ve toplam. Demo hesaba fiilen yatan ("d") da yanında gösterilir.

Kullanım (sunucuda):  cd /opt/carry && .venv/bin/python funding_dogrula.py [--gun 7]
Sınır: pozisyon geçmişi madde 745'ten (2026-11-08) beri tutuluyor; ondan önceki ödemeler "pozisyon kaydı yok" sayılır.
"""
import argparse
import bisect
import json
import os
import sys
import time
import urllib.request

URL = os.getenv("CARRY_TARAYICI_URL", "https://fapi.binance.com")


def _al(yol: str):
    for i in range(3):
        try:
            r = urllib.request.Request(URL + yol, headers={"User-Agent": "carry-funding-dogrula"})
            with urllib.request.urlopen(r, timeout=15) as f:
                return json.loads(f.read())
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def resmi_oranlar(sem: str, bas_ms: int, bit_ms: int, al=_al) -> dict:
    """{fundingTime_ms: (oran, işaret fiyatı)} — Binance resmi funding geçmişi."""
    out, t = {}, bas_ms
    while t < bit_ms:
        d = al(f"/fapi/v1/fundingRate?symbol={sem}&startTime={t}&endTime={bit_ms}&limit=1000") or []
        if not d:
            break
        for x in d:
            out[int(x["fundingTime"])] = (float(x["fundingRate"]), float(x.get("markPrice") or 0))
        son = max(int(x["fundingTime"]) for x in d)
        if son <= t or len(d) < 1000:
            break
        t = son + 1
    return out


def pozisyon(gec: list, t_ms: int):
    """Ödeme anındaki adet: t'den ÖNCEKİ son görüntü. Görüntü yoksa None."""
    ts = [x[0] * 1000 for x in gec]
    i = bisect.bisect_right(ts, t_ms) - 1
    return None if i < 0 else float(gec[i][1])


def dogrula(klasor: str, gun: float = 7, simdi: float | None = None, al=_al) -> dict:
    simdi = simdi or time.time()
    d = json.load(open(os.path.join(klasor, "defter", "funding_olay.json"), encoding="utf-8"))
    pg = (json.load(open(os.path.join(klasor, "defter", "anlik_poz.json"), encoding="utf-8")).get("s") or {})
    G, D = d.get("g") or {}, d.get("d") or {}
    sinir = (simdi - gun * 86400) * 1000
    olay = [(int(t), s, float(v)) for t, c in G.items() if int(t) >= sinir for s, v in c.items()]
    semler = sorted({s for _, s, _ in olay})
    satirlar, coin = [], {}
    for s in semler:
        ts = [t for t, x, _ in olay if x == s]
        R = resmi_oranlar(s, min(ts) - 120_000, max(ts) + 120_000, al)
        for t, x, v in olay:
            if x != s:
                continue
            ft = min(R, key=lambda k: abs(k - t)) if R else None   # funding_olay dakikaya yuvarlı; resmi kayıt ms
            if ft is None or abs(ft - t) > 120_000:
                satirlar.append({"t": t, "s": s, "panel": v, "resmi": None, "neden": "resmi kayıt yok"}); continue
            oran, isaret = R[ft]
            q = pozisyon(pg.get(s) or [], ft)
            if q is None:
                satirlar.append({"t": t, "s": s, "panel": v, "resmi": None, "neden": "pozisyon kaydı yok"}); continue
            r = -q * isaret * oran
            satirlar.append({"t": t, "s": s, "panel": v, "resmi": r, "oran": oran, "adet": q, "isaret": isaret})
            c = coin.setdefault(s, [0.0, 0.0, 0]); c[0] += v; c[1] += r; c[2] += 1
    demo = sum(float(v) for t, c in D.items() if int(t) >= sinir for v in c.values())
    ok = [x for x in satirlar if x["resmi"] is not None]
    return {"satirlar": satirlar, "coin": coin, "panel": sum(x["panel"] for x in ok), "resmi": sum(x["resmi"] for x in ok),
            "olculemeyen": len(satirlar) - len(ok), "olculemeyen_panel": sum(x["panel"] for x in satirlar if x["resmi"] is None),
            "demo": demo}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--klasor", default="."); ap.add_argument("--gun", type=float, default=7)
    a = ap.parse_args()
    try:
        r = dogrula(a.klasor, a.gun)
    except OSError as e:
        print(f"dosya okunamadı: {e}"); sys.exit(1)
    print(f"{'coin':14s} {'ödeme':>5s} {'panel $':>10s} {'resmi $':>10s} {'fark $':>9s}")
    for s, (p, q, n) in sorted(r["coin"].items(), key=lambda x: -abs(x[1][1])):
        print(f"{s:14s} {n:5d} {p:10.4f} {q:10.4f} {p - q:9.4f}")
    fark = r["panel"] - r["resmi"]
    print(f"\nTOPLAM (ölçülen ödemeler): panel {r['panel']:+.4f} $ · Binance resmi oranla yeniden hesap {r['resmi']:+.4f} $ · "
          f"fark {fark:+.4f} $ ({(fark / r['resmi'] * 100) if r['resmi'] else 0:+.2f}%)")
    if r["olculemeyen"]:
        print(f"ölçülemeyen {r['olculemeyen']} ödeme (panel toplamı {r['olculemeyen_panel']:+.4f} $): pozisyon geçmişi / resmi kayıt yok")
    print(f"aynı dönemde demo hesaba fiilen yatan: {r['demo']:+.4f} $ (demo borsanın kendi oranı)")
    buyuk = sorted([x for x in r["satirlar"] if x["resmi"] is not None], key=lambda x: -abs(x["panel"] - x["resmi"]))[:5]
    if buyuk and abs(buyuk[0]["panel"] - buyuk[0]["resmi"]) > 0.005:
        print("\nen büyük 5 fark:")
        for x in buyuk:
            print(f"  {time.strftime('%m-%d %H:%M', time.localtime(x['t'] / 1000))} {x['s']:12s} panel {x['panel']:+.4f} resmi {x['resmi']:+.4f} "
                  f"(adet {x['adet']:g} × {x['isaret']:g} × oran {x['oran'] * 100:+.4f}%)")
