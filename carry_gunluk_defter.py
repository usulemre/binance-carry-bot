#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ÇOKLU DEMO DEFTERİ — her profil kendi demo hesabında, gün gün "ne aldı, % kaç kazandı" (kullanıcı isteği, 2026-10-28).

Kurulum: COKLU_DEMO.md. Her bot örneği ayrı klasörde (/opt/carry-T4, /opt/carry-T7KKS, ...) ve AYRI demo hesabında çalışır
(aynı hesapta iki bot aynı coinde birbirinin pozisyonunu bozar — check_bot_conflict.py).

İKİ KOMUT
  python3 carry_gunluk_defter.py topla
      Bu klasörün botunun hesabından günlük anlık görüntü alır ve `defter/gunluk.jsonl`'a bir satır ekler:
      tarih, toplam özkaynak (cüzdan + gerçekleşmemiş), açık pozisyonlar (coin, yön, büyüklük $, giriş, işaret fiyatı, kâr %),
      son 24 saatin gelirleri (funding, gerçekleşen kâr/zarar, komisyon — coin bazında), dünkü görüntüye göre AÇILAN / KAPANAN /
      BÜYÜYEN / KÜÇÜLEN pozisyonlar. Günde bir kez (cron 00:05 UTC) çalıştırın; aynı gün ikinci kez çalışırsa satırı günceller.
  python3 carry_gunluk_defter.py rapor --klasor /opt/carry-T4 --klasor /opt/carry-T7KKS ... [--cikti demo_defteri.html] [--pdf]
      Bütün örneklerin defterlerini okur, yan yana karşılaştırma + her profil için gün gün sayfa üretir (HTML; Playwright varsa PDF).
Profil adı her klasörün .env'indeki CARRY_PROFIL (+ CARRY_GROSS, CARRY_LONG_24S_PIYASA) değerlerinden okunur.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
import time

DEFTER_KLASOR = "defter"
DEFTER_DOSYA = os.path.join(DEFTER_KLASOR, "gunluk.jsonl")
GELIR_TURLERI = ("FUNDING_FEE", "REALIZED_PNL", "COMMISSION", "TRANSFER")


# ----------------------------------------------------------------------------------------------- topla
def _gelirler(client, bas_ms: int, bit_ms: int) -> list:
    """Gelir kayıtları (sayfalı). Hata olursa boş liste."""
    out, bas = [], bas_ms
    for _ in range(20):
        try:
            r = client.client.futures_income_history(startTime=bas, endTime=bit_ms, limit=1000)
        except Exception as ex:
            print(f"UYARI: gelir geçmişi okunamadı: {ex}", file=sys.stderr)
            return out
        if not r:
            break
        out.extend(r)
        if len(r) < 1000:
            break
        bas = int(r[-1]["time"]) + 1
    return out


def _pozisyonlar(client) -> dict:
    poz = {}
    for p in client.get_open_positions():
        try:
            m = float(p.get("positionAmt", 0))
        except (TypeError, ValueError):
            continue
        if abs(m) < 1e-12:
            continue
        giris = float(p.get("entryPrice") or 0)
        isaret = float(p.get("markPrice") or giris or 0)
        poz[p["symbol"]] = {
            "yon": "L" if m > 0 else "S",
            "miktar": m,
            "usd": round(abs(m) * isaret, 2),
            "giris": giris,
            "isaret": isaret,
            "kar_yuzde": round(((isaret / giris - 1) * (1 if m > 0 else -1) * 100) if giris > 0 else 0.0, 2),
            "gerceklesmemis": round(float(p.get("unRealizedProfit") or 0), 2),
        }
    return poz


def _son_satir(dosya: str):
    if not os.path.exists(dosya):
        return None
    son = None
    with open(dosya, encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l:
                son = json.loads(l)
    return son


def degisimler(dun: dict, bugun: dict) -> dict:
    """Dünkü ve bugünkü pozisyon sözlüklerinden açılan / kapanan / büyüyen / küçülen / yön değiştiren."""
    acilan, kapanan, buyuyen, kuculen = [], [], [], []
    for s, p in bugun.items():
        d = dun.get(s)
        if d is None or d["yon"] != p["yon"]:
            acilan.append(f"{s} {p['yon']}")
            if d is not None:
                kapanan.append(f"{s} {d['yon']}")
        else:
            r = abs(p["miktar"]) / max(abs(d["miktar"]), 1e-12)
            if r > 1.1: buyuyen.append(f"{s} {p['yon']}")
            elif r < 0.9: kuculen.append(f"{s} {p['yon']}")
    for s, d in dun.items():
        if s not in bugun:
            kapanan.append(f"{s} {d['yon']}")
    return {"acilan": sorted(acilan), "kapanan": sorted(kapanan), "buyuyen": sorted(buyuyen), "kuculen": sorted(kuculen)}


def topla(client=None, simdi: float | None = None, dosya: str = DEFTER_DOSYA) -> dict:
    if client is None:
        import config
        from exchange_client import ExchangeClient
        client = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    simdi = simdi or time.time()
    tarih = dt.datetime.fromtimestamp(simdi, dt.timezone.utc).strftime("%Y-%m-%d")
    oz = float(client.get_account_equity_usd())
    poz = _pozisyonlar(client)
    bit = int(simdi * 1000); bas = bit - 24 * 3600 * 1000
    gel = _gelirler(client, bas, bit)
    ozet = {t: 0.0 for t in GELIR_TURLERI}; coin = {}
    for g in gel:
        t = g.get("incomeType")
        if t not in ozet:
            continue
        v = float(g.get("income") or 0); ozet[t] += v
        if t != "TRANSFER" and g.get("symbol"):
            c = coin.setdefault(g["symbol"], {k: 0.0 for k in GELIR_TURLERI if k != "TRANSFER"}); c[t] += v
    os.makedirs(os.path.dirname(dosya) or ".", exist_ok=True)
    satirlar = [l.rstrip("\n") for l in open(dosya, encoding="utf-8") if l.strip()] if os.path.exists(dosya) else []
    if satirlar and json.loads(satirlar[-1]).get("tarih") == tarih:   # aynı gün tekrar çalıştı: o günün satırı yenilenir
        satirlar = satirlar[:-1]
    dun = json.loads(satirlar[-1]) if satirlar else None
    kayit = {
        "tarih": tarih, "zaman": int(simdi), "ozkaynak": round(oz, 4),
        "profil": os.getenv("CARRY_PROFIL", "") or "T4", "doz": os.getenv("CARRY_GROSS", "1.0"),
        "kosullu_stop": os.getenv("CARRY_LONG_24S_PIYASA", "0"),
        "pozisyonlar": poz,
        "gelir_24s": {k: round(v, 4) for k, v in ozet.items()},
        "gelir_coin": {s: {k: round(v, 4) for k, v in c.items()} for s, c in coin.items()},
        "degisim": degisimler(dun["pozisyonlar"] if dun else {}, poz),
    }
    # günlük getiri: transferleri ayıkla (yatırma / çekme getiri değildir)
    olcek = float(os.getenv("CARRY_SERMAYE_OLCEK", "1.0") or 1.0)
    kayit["sermaye_olcek"] = olcek
    kayit["kitap"] = round(oz * olcek, 4)          # botun kullandığı sermaye (rapor bunu gösterir)
    if dun and dun.get("ozkaynak"):
        # kitap getirisi: kâr / zarar, botun KULLANDIĞI sermayeye (dünkü özkaynak × ölçek) bölünür
        kayit["gun_getiri"] = round((oz - ozet["TRANSFER"] - dun["ozkaynak"]) / (dun["ozkaynak"] * dun.get("sermaye_olcek", olcek)), 6)
    else:
        kayit["gun_getiri"] = None
    with open(dosya, "w", encoding="utf-8") as f:
        for l in satirlar:
            f.write(l + "\n")
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    _g = "—" if kayit["gun_getiri"] is None else f"{kayit['gun_getiri'] * 100:+.2f}%"
    print(f"{tarih} {kayit['profil']}: özkaynak {oz:,.2f} $ · gün {_g} · {len(poz)} pozisyon · funding {ozet['FUNDING_FEE']:+.2f} $")
    return kayit


# ----------------------------------------------------------------------------------------------- rapor
def _env_oku(klasor: str) -> dict:
    d = {}
    yol = os.path.join(klasor, ".env")
    if os.path.exists(yol):
        for l in open(yol, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1); d[k.strip()] = v.split("#")[0].strip()
    return d


def _ad(klasor: str, satirlar: list) -> str:
    e = _env_oku(klasor)
    p = e.get("CARRY_PROFIL") or (satirlar[-1].get("profil") if satirlar else "") or "T4"
    doz = e.get("CARRY_GROSS") or (satirlar[-1].get("doz") if satirlar else "1.0")
    ks = e.get("CARRY_LONG_24S_PIYASA") or (satirlar[-1].get("kosullu_stop") if satirlar else "0")
    ad = p
    if doz and abs(float(doz) - 1.0) > 1e-9: ad += f" {float(doz):.2f}x".replace(".", ",")
    if ks and float(ks) > 0: ad += " + koşullu stop"
    return ad


def _yuzde(x, d=2):
    return "—" if x is None else (f"{x*100:+.{d}f}".replace(".", ",").replace("-", "−") + "%")


def _para(x):
    return f"{x:,.0f}".replace(",", ".") + " $"


def _sinif(x):
    return "" if x is None else ("pos" if x > 0.0005 else "neg" if x < -0.0005 else "")


CSS = """body{font-family:Arial,Helvetica,sans-serif;color:#1d2433;margin:24px;font-size:12px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:24px 0 6px;border-bottom:2px solid #1f5f8b;padding-bottom:3px}
.alt{color:#5a6475;margin:0 0 12px} table{border-collapse:collapse;margin:6px 0 14px;width:100%}
th,td{border-bottom:1px solid #e2e6ee;padding:4px 6px;text-align:right;vertical-align:top} th{background:#f3f5f9;font-weight:600}
td.l,th.l{text-align:left} .pos{color:#1d7a4c;font-weight:600} .neg{color:#b3392f;font-weight:600} .k{font-size:11px;color:#5a6475}
.sayfa{page-break-before:always}"""


def rapor(klasorler: list, cikti: str = "demo_defteri.html", pdf: bool = False) -> str:
    kitap = []
    for k in klasorler:
        yol = os.path.join(k, DEFTER_DOSYA)
        satir = [json.loads(l) for l in open(yol, encoding="utf-8") if l.strip()] if os.path.exists(yol) else []
        kitap.append((_ad(k, satir), satir))
    tarihler = sorted({s["tarih"] for _, sat in kitap for s in sat})
    h = [f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>Demo Defteri</title><style>{CSS}</style></head><body>"]
    h.append(f"<h1>Demo Defteri — profiller yan yana</h1><p class='alt'>{len(kitap)} bot, her biri ayrı demo hesabında · "
             f"{tarihler[0] if tarihler else '—'} → {tarihler[-1] if tarihler else '—'} · günlük anlık görüntü (UTC 00:05)</p>")
    # özet
    h.append("<h2>Özet</h2><table><tr><th class='l'>Bot</th><th>Gün</th><th>Başlangıç</th><th>Son</th><th>Toplam</th>"
             "<th>En iyi gün</th><th>En kötü gün</th><th>Kazançlı / zararlı gün</th><th>Funding toplamı</th><th>Komisyon toplamı</th></tr>")
    for ad, sat in kitap:
        if not sat:
            h.append(f"<tr><td class='l'>{html.escape(ad)}</td><td colspan='9'>henüz kayıt yok</td></tr>"); continue
        g = [s["gun_getiri"] for s in sat if s.get("gun_getiri") is not None]
        top = 1.0
        for x in g: top *= 1 + x
        top -= 1
        fnd = sum(s["gelir_24s"]["FUNDING_FEE"] for s in sat); kom = sum(s["gelir_24s"]["COMMISSION"] for s in sat)
        h.append(f"<tr><td class='l'>{html.escape(ad)}</td><td>{len(sat)}</td><td>{_para(sat[0].get('kitap', sat[0]['ozkaynak']))}</td>"
                 f"<td>{_para(sat[0].get('kitap', sat[0]['ozkaynak']) * (1 + top))}</td><td class='{_sinif(top)}'>{_yuzde(top)}</td>"
                 f"<td class='pos'>{_yuzde(max(g) if g else None)}</td><td class='neg'>{_yuzde(min(g) if g else None)}</td>"
                 f"<td>{sum(x > 0 for x in g)} / {sum(x < 0 for x in g)}</td><td>{fnd:+,.2f} $</td><td>{kom:+,.2f} $</td></tr>")
    h.append("</table>")
    # gün gün karşılaştırma
    h.append("<h2>Gün gün getiri</h2><table><tr><th class='l'>Tarih</th>" + "".join(f"<th>{html.escape(a)}</th>" for a, _ in kitap) + "</tr>")
    idx = [{s["tarih"]: s for s in sat} for _, sat in kitap]
    for t in tarihler:
        h.append(f"<tr><td class='l'>{t}</td>" + "".join(
            f"<td class='{_sinif(d.get(t, {}).get('gun_getiri'))}'>{_yuzde(d.get(t, {}).get('gun_getiri'))}"
            f"<br><span class='k'>{_para(d[t].get('kitap', d[t]['ozkaynak'])) if t in d else ''}</span></td>" for d in idx) + "</tr>")
    h.append("</table>")
    # her profil: gün gün ne aldı
    for ad, sat in kitap:
        h.append(f"<div class='sayfa'><h2>{html.escape(ad)} — gün gün</h2>")
        for s in reversed(sat):
            dg = s["degisim"]; poz = s["pozisyonlar"]
            L = sorted([(k, v) for k, v in poz.items() if v["yon"] == "L"], key=lambda x: -x[1]["usd"])
            S = sorted([(k, v) for k, v in poz.items() if v["yon"] == "S"], key=lambda x: -x[1]["usd"])
            h.append(f"<h3 style='font-size:13px;margin:14px 0 2px'>{s['tarih']} · kitap {_para(s.get('kitap', s['ozkaynak']))} · gün "
                     f"<span class='{_sinif(s.get('gun_getiri'))}'>{_yuzde(s.get('gun_getiri'))}</span> · funding "
                     f"{s['gelir_24s']['FUNDING_FEE']:+.2f} $ · gerçekleşen {s['gelir_24s']['REALIZED_PNL']:+.2f} $ · komisyon "
                     f"{s['gelir_24s']['COMMISSION']:+.2f} $</h3>")
            h.append(f"<p class='k'>Açılan: {', '.join(dg['acilan']) or '—'} · Kapanan: {', '.join(dg['kapanan']) or '—'} · "
                     f"Büyüyen: {', '.join(dg['buyuyen']) or '—'} · Küçülen: {', '.join(dg['kuculen']) or '—'}</p>")
            h.append("<table><tr><th class='l'>Long</th><th>$</th><th>kâr %</th><th class='l'>Short</th><th>$</th><th>kâr %</th></tr>")
            for i in range(max(len(L), len(S))):
                a = L[i] if i < len(L) else None; b = S[i] if i < len(S) else None
                c1 = f"<td class='l'>{a[0]}</td><td>{_para(a[1]['usd'])}</td><td class='{_sinif(a[1]['kar_yuzde']/100)}'>{a[1]['kar_yuzde']:+.1f}%</td>" if a else "<td></td><td></td><td></td>"
                c2 = f"<td class='l'>{b[0]}</td><td>{_para(b[1]['usd'])}</td><td class='{_sinif(b[1]['kar_yuzde']/100)}'>{b[1]['kar_yuzde']:+.1f}%</td>" if b else "<td></td><td></td><td></td>"
                h.append(f"<tr>{c1}{c2}</tr>")
            h.append("</table>")
        h.append("</div>")
    h.append("<p class='k'>Demo hesap verisidir (gerçek para değil). Günlük getiri = (özkaynak − transferler) / dünkü özkaynak − 1.</p></body></html>")
    open(cikti, "w", encoding="utf-8").write("".join(h))
    print(f"rapor: {cikti}")
    if pdf:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch(); s = b.new_page(); s.goto("file://" + os.path.abspath(cikti))
                s.pdf(path=os.path.splitext(cikti)[0] + ".pdf", format="A4", print_background=True); b.close()
            print(f"pdf: {os.path.splitext(cikti)[0]}.pdf")
        except Exception as ex:
            print(f"PDF üretilemedi ({ex}); HTML'i tarayıcıda açıp yazdırabilirsiniz.")
    return cikti


def rapor_gonder(klasorler: list, cikti: str) -> bool:
    """MADDE 670: raporu (PDF yoksa HTML) Telegram'a gönderir. Ayar ortamda yoksa ana kurulumun .env'inden YALNIZ
    TELEGRAM_* okunur (rapor servisi Binance anahtarlarını yüklemez)."""
    import bildirim
    for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"):
        if not os.getenv(k):
            for kl in klasorler:
                v = _env_oku(kl).get(k)
                if v:
                    os.environ[k] = v; break
    os.environ.setdefault("CARRY_BILDIRIM_AD", "rapor")
    pdf = os.path.splitext(cikti)[0] + ".pdf"
    dosya = pdf if os.path.exists(pdf) and os.path.getmtime(pdf) >= os.path.getmtime(cikti) - 60 else cikti
    return bildirim.gonder(f"📄 günlük demo raporu ({len(klasorler)} kurulum)", dosya=dosya)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("topla")
    r = alt.add_parser("rapor"); r.add_argument("--klasor", action="append", required=True)
    r.add_argument("--cikti", default="demo_defteri.html"); r.add_argument("--pdf", action="store_true")
    r.add_argument("--telegram", action="store_true", help="raporu Telegram'a da gönder (madde 670; ayarsızsa sessizce atlanır)")
    a = ap.parse_args()
    if a.komut == "topla":
        _k = topla()
        try:                                   # MADDE 680: aynı kayıt SQLite'a da (defter/carry.db; sorgu: defter_db.py)
            import defter_db
            defter_db.yaz(_k, os.path.join(os.path.dirname(DEFTER_DOSYA), "carry.db"))
        except Exception as e:
            print(f"veritabanına yazılamadı ({e}) — jsonl defter etkilenmedi")
        try:                                   # MADDE 670: günlük özet telefona (ayarsızsa hiçbir şey yapmaz)
            import bildirim
            bildirim.gonder(bildirim.gunluk_ozet_metni(_k), anahtar=f"gunluk_{_k['tarih']}", kisma_sn=20 * 3600)
        except Exception:
            pass
    else:
        rapor(a.klasor, a.cikti, a.pdf)
        if a.telegram:
            rapor_gonder(a.klasor, a.cikti)
