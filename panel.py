# -*- coding: utf-8 -*-
"""MADDE 671 — PANEL: tarayıcıdan izleme (SALT OKUNUR). Bot'a / Binance'e hiçbir emir göndermez, API anahtarı YÜKLEMEZ.

Okuduğu dosyalar (her kurulum: /opt/carry, /opt/carry-*/): defter/gunluk.jsonl (günlük defter: kitap, getiri, funding,
pozisyonlar), carry_bot.log (önemli olaylar: stop, delist, sağlık, hata, başlama), servis durumu (systemctl).
GÜVENLİK: varsayılan 127.0.0.1'e bağlanır = İNTERNETTEN ERİŞİLEMEZ. Telefondan / bilgisayardan Tailscale ile açılır:
    sudo tailscale serve --bg 8050          -> https://<sunucu-adı>.<tailnet>.ts.net  (yalnız sizin cihazlarınız)
İsteğe bağlı ek şifre: .env'de CARRY_PANEL_SIFRE=... (kullanıcı adı: carry). Kurulum KURULUM_SUNUCU.md "Panel".
Elle:      .venv/bin/python panel.py                     (http://127.0.0.1:8050)
Anlık görüntü (tek HTML dosyası, sunucusuz):  .venv/bin/python panel.py --disa-aktar panel.html [--klasor DİZİN ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hmac
import json
import os
import re
import subprocess
import sys
import time

OLAY_DESENLERI = [
    ("stop", re.compile(r"(24 SA DÜŞÜŞ STOP'U|KOŞULLU 24 SA STOP: \S+ .*kapatılıyor)")),
    ("delist", re.compile(r"DELİST: \S+ (listeden çıkıyor|kapanmalı)")),
    ("saglik", re.compile(r"SAĞLIK KAPISI KAPALI")),
    ("hata", re.compile(r"tur başarısız|KAPATILAMADI")),
    ("ayar", re.compile(r"önerilen ayar etkin|ÖNERİLEN AYAR: kitap")),
    ("basla", re.compile(r"carry_bot başladı")),
]
try:   # MADDE 729: panel saatleri Türkiye saatiyle (sunucu ve log UTC). Değiştirmek: CARRY_PANEL_TZ=Europe/Berlin vb.
    from zoneinfo import ZoneInfo
    PANEL_TZ = ZoneInfo(os.getenv("CARRY_PANEL_TZ", "Europe/Istanbul"))
except Exception:      # tz verisi yoksa sunucu saatine düşülür
    PANEL_TZ = None


def _yerel(ts: float | None = None) -> dt.datetime:
    """Epoch saniye (None = şimdi) -> panel saat dilimi."""
    return dt.datetime.fromtimestamp(time.time() if ts is None else ts, PANEL_TZ)


def _log_zamani(s: str) -> str:
    """Log satırındaki 'YYYY-MM-DD HH:MM' (sunucunun yerel saati) -> panel saat dilimi; okunamazsa olduğu gibi."""
    try:
        return dt.datetime.strptime(s.replace("T", " "), "%Y-%m-%d %H:%M").astimezone(PANEL_TZ).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return s


_ZAMAN = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}):\d{2}(?:[,.]\d+)?\s*(?:\[?(?:INFO|WARNING|ERROR|CRITICAL|DEBUG)\]?)?")
_GIZLI = re.compile(r"(api[_-]?key|secret|signature|token)\S*", re.I)


_AYAR_ETKIN = re.compile(r"önerilen ayar etkin: profil (\S+) · gross ([\d.]+)x · koşullu stop ([\d.]+)")
_BASLADI = re.compile(r"carry_bot başladı \|.*?\| gross ([\d.]+)x")


def etkin_ayar(klasor: str, son_bayt: int = 5_000_000) -> dict | None:
    """MADDE 734: botun SON başlangıçta GERÇEKTE kullandığı ayar (log'dan). Defterdeki profil / doz .env'deki
    ham değerdir (ör. ONERILEN 1.0) — önerilen modda seçilen profil (T7K 1.15x + koşullu stop) orada görünmez."""
    try:
        with open(os.path.join(klasor, "carry_bot.log"), "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - son_bayt))
            satirlar = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for i in range(len(satirlar) - 1, -1, -1):
        m = _BASLADI.search(satirlar[i])
        if not m:
            continue
        out = {"profil": None, "gross": float(m.group(1)), "stop": None, "onerilen": False}
        for s in reversed(satirlar[max(0, i - 5):i]):   # önerilen mod: seçim satırı başlangıçtan hemen önce yazılır
            if _BASLADI.search(s) or "ÖNERİLEN AYAR" in s:   # önceki başlangıç / yeniden başlatma: bu başlangıca ait değil
                break
            a = _AYAR_ETKIN.search(s)
            if a:
                out.update(profil=a.group(1), gross=float(a.group(2)), stop=float(a.group(3)), onerilen=True)
                break
        return out
    return None


def kurulumlar(kok: str = "/opt") -> list[str]:
    out = [os.path.join(kok, "carry")] if os.path.exists(os.path.join(kok, "carry", "carry_bot.py")) else []
    out += [d for d in sorted(glob.glob(os.path.join(kok, "carry-*"))) if os.path.exists(os.path.join(d, "carry_bot.py"))]
    return out


def _env(klasor: str) -> dict:
    d = {}
    try:
        for l in open(os.path.join(klasor, ".env"), encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                if k.strip() in ("BINANCE_MODE", "CARRY_PROFIL", "CARRY_BILDIRIM_AD", "CARRY_SERMAYE_OLCEK",
                                 "CARRY_REBALANCE_H", "CARRY_N_DILIM", "CARRY_DILIM_LOG",
                                 "CARRY_MERDIVEN", "CARRY_MERDIVEN_SHORT", "CARRY_KAR_AL", "CARRY_KAR_AL_SHORT"):   # anahtarlar OKUNMAZ
                    d[k.strip()] = v.split("#")[0].strip()
    except OSError:
        pass
    return d


def defter_oku(klasor: str) -> list[dict]:
    yol = os.path.join(klasor, "defter", "gunluk.jsonl")
    out = []
    try:
        for l in open(yol, encoding="utf-8"):
            l = l.strip()
            if l:
                try:
                    out.append(json.loads(l))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def olaylar(klasor: str, en_cok: int = 40, son_bayt: int = 2_000_000) -> list[dict]:
    yol = os.path.join(klasor, "carry_bot.log")
    try:
        with open(yol, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - son_bayt))
            satirlar = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    out = []
    for s in satirlar:
        for tur, d in OLAY_DESENLERI:
            if d.search(s):
                m = _ZAMAN.match(s)
                metin = s[m.end():].strip(" -|") if m else s
                out.append({"zaman": _log_zamani(m.group(1)) if m else "", "tur": tur, "metin": _GIZLI.sub("***", metin)[:300]})
                break
    return out[-en_cok:][::-1]


def servis_durumu(klasor: str) -> str:
    b = os.path.basename(klasor.rstrip("/"))
    sv = "carry" if b == "carry" else "carry@" + b[len("carry-"):]
    try:
        return subprocess.run(["systemctl", "is-active", sv], capture_output=True, text=True, timeout=5).stdout.strip() or "?"
    except Exception:
        return "?"


def _kitap_ilerlet(kit: float | None, onc: dict | None, k: dict) -> float | None:
    """MADDE 731: kitap = başlangıç kitabı + kâr/zararın TAMAMI (+ transferin ölçekli payı).
    Defterdeki `kitap` özkaynak x CARRY_SERMAYE_OLCEK'tir; ölçek < 1 iken kâr/zararın yalnız o kadarını gösterir
    (2.000 $ kitapta 3 $ zarar -> 1,2 $). Pozisyonlar kitaba göre açıldığı için kâr/zararın hepsi kitabındır."""
    oz = k.get("ozkaynak")
    if kit is None or onc is None or oz is None or onc.get("ozkaynak") is None:
        return k.get("kitap", oz)
    t = (k.get("gelir_24s") or {}).get("TRANSFER", 0) or 0
    olcek = float(k.get("sermaye_olcek", 1.0) or 1.0)
    return round(kit + (oz - onc["ozkaynak"] - t) + t * olcek, 4)


def ozet(defter: list[dict]) -> dict:
    """Seri + göstergeler. Getiri zinciri günlük getiriden (transferler zaten ayıklanmış)."""
    seri, deg, kit, onc = [], 1.0, None, None
    for k in defter:
        g = k.get("gun_getiri")
        if g is not None:
            deg *= 1 + g
        kit = _kitap_ilerlet(kit, onc, k); onc = k
        seri.append({"tarih": k.get("tarih"), "kitap": kit, "gun": g, "deger": deg,
                     "funding": (k.get("gelir_24s") or {}).get("FUNDING_FEE", 0),
                     "komisyon": (k.get("gelir_24s") or {}).get("COMMISSION", 0)})
    zirve, dd = 1.0, 0.0
    for s in seri:
        zirve = max(zirve, s["deger"]); dd = min(dd, s["deger"] / zirve - 1)

    def _pencere(n):
        if len(seri) < 2:
            return None
        b = seri[max(0, len(seri) - 1 - n)]["deger"]
        return seri[-1]["deger"] / b - 1
    aylik = {}
    for s in seri:
        if s["gun"] is not None:
            a = s["tarih"][:7]; aylik[a] = (1 + aylik.get(a, 0.0)) * (1 + s["gun"]) - 1
    son = defter[-1] if defter else {}
    return {"seri": seri, "toplam": seri[-1]["deger"] - 1 if seri else None, "dd": dd, "g7": _pencere(7), "g30": _pencere(30),
            "bugun": seri[-1]["gun"] if seri else None, "kitap": seri[-1]["kitap"] if seri else None,
            "aylik": aylik, "pozisyonlar": son.get("pozisyonlar", {}), "son_tarih": son.get("tarih"),
            "profil": son.get("profil"), "doz": son.get("doz"),
            "funding_top": sum(s["funding"] or 0 for s in seri), "komisyon_top": sum(s["komisyon"] or 0 for s in seri)}


PAKET_DIR = os.getenv("CARRY_PAKET_DIR", "/opt/carry-rapor/paket")
_PAKET_AD = re.compile(r"^paket_\d{4}-\d{2}\.zip$")


def paketler(dizin: str | None = None) -> list[dict]:
    """MADDE 674: sunucunun aylık indirdiği veri paketleri (araştırma için; panelden indirilip sohbete yüklenir)."""
    dizin = dizin or PAKET_DIR
    try:
        adlar = sorted((f for f in os.listdir(dizin) if _PAKET_AD.match(f)), reverse=True)
    except OSError:
        return []
    return [{"ad": f, "mb": round(os.path.getsize(os.path.join(dizin, f)) / 1e6, 1)} for f in adlar]


def icra(klasor: str) -> dict | None:
    """MADDE 701: emir defterinden (defter/carry.db, SALT OKUNUR) son 30 günün icra metrikleri. Yoksa None."""
    try:
        import defter_db
        return defter_db.icra_ozet(db=os.path.join(klasor, "defter", "carry.db"))
    except Exception:
        return None


ANLIK_TAZE_SN = int(os.getenv("CARRY_PANEL_ANLIK_TAZE_SN", "900"))
"""MADDE 728: defter/anlik.json (carry_anlik.py, 5 dk'da bir) bu kadar saniyeden tazeyse pozisyon tablosu ondan gösterilir."""


def anlik_oku(klasor: str, simdi: float | None = None) -> dict | None:
    """Taze anlık pozisyon görüntüsü ya da None (yok / bozuk / bayat) — madde 728."""
    try:
        with open(os.path.join(klasor, "defter", "anlik.json"), encoding="utf-8") as f:
            a = json.load(f)
        yas = (simdi or time.time()) - float(a["zaman"])
        return a if 0 <= yas <= ANLIK_TAZE_SN and isinstance(a.get("pozisyonlar"), dict) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def sonraki_dilim(klasor: str, e: dict | None = None) -> dict | None:
    """MADDE 730: sıradaki dilim turunun zamanı. Bot her turun sonunda dilim durumunu yazar, sonra
    CARRY_REBALANCE_H / CARRY_N_DILIM saat uyur (carry_bot.main) -> dosyanın değişme zamanı + aralık. Yoksa None."""
    e = e if e is not None else _env(klasor)
    yol = e.get("CARRY_DILIM_LOG") or "carry_dilimler.json"
    yol = yol if os.path.isabs(yol) else os.path.join(klasor, yol)
    try:
        n = max(1, int(float(e.get("CARRY_N_DILIM") or 15)))
        aralik = float(e.get("CARRY_REBALANCE_H") or 120) * 3600.0 / n
        son = os.path.getmtime(yol)
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
        dolu = sum(1 for v in (d.get("dilimler") or {}).values() if v)
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return {"son": int(son), "zaman": int(son + aralik), "saat": _yerel(son + aralik).strftime("%H:%M"),
            "dolu": min(dolu, n), "n": n, "aralik_sa": round(aralik / 3600.0, 2)}


def hesap_ozet(defter: list[dict], an: dict | None) -> dict:
    """MADDE 730: hesap özkaynağı (canlıysa anlık, değilse son defter) ve başlangıçtan beri $ kâr/zarar (transferler hariç)."""
    if not defter and an is None:
        return {}
    oz = an.get("ozkaynak") if an else defter[-1].get("ozkaynak")
    out = {"ozkaynak": oz, "kitap_canli": an.get("kitap") if an else None}
    if not defter or oz is None or defter[0].get("ozkaynak") is None:
        return out
    transfer = sum((k.get("gelir_24s") or {}).get("TRANSFER", 0) or 0 for k in defter[1:])
    kit = None
    for i, k in enumerate(defter):
        kit = _kitap_ilerlet(kit, defter[i - 1] if i else None, k)
    bas = defter[0].get("kitap", defter[0]["ozkaynak"])
    if an and kit is not None and defter[-1].get("ozkaynak") is not None:
        out["kitap_canli"] = round(kit + oz - defter[-1]["ozkaynak"], 4)   # madde 731: son defter kitabı + o andan beri kâr/zarar
    out["kitap_bas"] = bas
    out["kar_usd"] = round(oz - defter[0]["ozkaynak"] - transfer, 2)
    out["kar_oran"] = round(out["kar_usd"] / bas, 6) if bas else None
    g = (an or {}).get("gelir_bas") or {}
    if g and g.get("bas") == defter[0].get("zaman"):   # madde 733: döküm (başlangıç aynı kayıttan olmalı)
        out["dokum"] = {"gerceklesen": round(g.get("REALIZED_PNL", 0), 2), "funding": round(g.get("FUNDING_FEE", 0), 2),
                        "komisyon": round(g.get("COMMISSION", 0), 2),
                        "diger_gelir": round(sum(v for t, v in g.items() if t not in ("bas", "son", "REALIZED_PNL", "FUNDING_FEE",
                                                                                      "COMMISSION", "TRANSFER")), 2)}
    return out


def kar_hedefleri(e: dict) -> dict:
    """MADDE 737: kâr al kademeleri (carry_bot varsayılanları: long %45 / %60, short %15 / %20; .env kazanır).
    Kademe 0 ise tek hedef KAR_AL olur."""
    def _f(ad, vars_):
        try:
            return float(e.get(ad) or vars_)
        except ValueError:
            return vars_
    kl, ks = _f("CARRY_KAR_AL", 0.60), _f("CARRY_KAR_AL_SHORT", 0.20)
    ml, ms = _f("CARRY_MERDIVEN", 0.45), _f("CARRY_MERDIVEN_SHORT", 0.15)
    return {"L": [x for x in (ml, kl) if x > 0], "S": [x for x in (ms, ks) if x > 0]}


def veri(klasorler: list[str], servis: bool = True) -> dict:
    out = []
    for kl in klasorler:
        e = _env(kl); b = os.path.basename(kl.rstrip("/"))
        ad = e.get("CARRY_BILDIRIM_AD") or (b[len("carry-"):] if b.startswith("carry-") else "ana")
        df = defter_oku(kl); o = ozet(df)
        o.update({"ad": ad, "mod": e.get("BINANCE_MODE", "demo"), "servis": servis_durumu(kl) if servis else "—",
                  "olaylar": olaylar(kl), "icra": icra(kl), "dilim": sonraki_dilim(kl, e),
                  "ayar": etkin_ayar(kl), "hedef": kar_hedefleri(e)})
        an = anlik_oku(kl)
        o.update(hesap_ozet(df, an))
        if an is not None:   # madde 728: canlı pozisyon tablosu
            o.update({"pozisyonlar": an["pozisyonlar"], "poz_kaynak": "canlı",
                      "poz_zaman": _yerel(an["zaman"]).strftime("%H:%M"),
                      "gerceklesmemis": an.get("gerceklesmemis_top")})
        else:
            o.update({"poz_kaynak": "günlük", "poz_zaman": o.get("son_tarih"), "gerceklesmemis": None})
        out.append(o)
    return {"kurulumlar": out, "paketler": paketler(), "uretim": _yerel().strftime("%Y-%m-%d %H:%M")}


SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carry Panel</title>
<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#0f1115">
<link rel="icon" href="ikon-192.png"><link rel="apple-touch-icon" href="ikon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Carry">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#f4f5f7;--kart:#fff;--kart2:#f8f9fb;--yazi:#16181d;--soluk:#6b7280;--cizgi:#e5e7eb;--art:#0f9d58;--eks:#d93025;--vurgu:#2563eb;--uyari:#b45309;--mor:#7c3aed}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0b0d11;--kart:#151820;--kart2:#1b1f29;--yazi:#e8eaed;--soluk:#9aa0a6;--cizgi:#262b36;--art:#34c172;--eks:#f2685c;--vurgu:#6ea8fe;--uyari:#f0a44b;--mor:#b197fc}}
:root[data-theme="dark"]{--bg:#0b0d11;--kart:#151820;--kart2:#1b1f29;--yazi:#e8eaed;--soluk:#9aa0a6;--cizgi:#262b36;--art:#34c172;--eks:#f2685c;--vurgu:#6ea8fe;--uyari:#f0a44b;--mor:#b197fc}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--yazi);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-tap-highlight-color:transparent}
.kap{max-width:1100px;margin:0 auto;padding:14px 14px 90px}
header{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-bottom:12px}
h1{font-size:17px;margin:0;letter-spacing:.2px}.k{color:var(--soluk);font-size:12px}
.canli{font-size:12px;color:var(--soluk);display:inline-flex;align-items:center;gap:6px}
.canli i{width:8px;height:8px;border-radius:50%;background:var(--soluk);display:inline-block}
.canli.on{color:var(--art)}.canli.on i{background:var(--art);animation:nabiz 1.6s infinite}
@keyframes nabiz{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--art) 60%,transparent)}70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}
.sekme{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}.sekme:empty{display:none}.sekme button{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);
padding:5px 12px;border-radius:999px;cursor:pointer;font:inherit;font-size:13px}.sekme button.on{border-color:var(--vurgu);color:var(--vurgu);font-weight:600}
nav.alt{display:flex;gap:4px;background:var(--kart);border:1px solid var(--cizgi);border-radius:14px;padding:4px;margin-bottom:14px}
nav.alt button{flex:1;border:0;background:none;color:var(--soluk);font:inherit;font-size:13px;font-weight:600;padding:8px 4px;border-radius:10px;cursor:pointer}
nav.alt button.on{background:color-mix(in srgb,var(--vurgu) 14%,transparent);color:var(--vurgu)}
@media(max-width:820px){nav.alt{position:fixed;left:10px;right:10px;bottom:calc(10px + env(safe-area-inset-bottom));margin:0;z-index:5;box-shadow:0 6px 24px rgba(0,0,0,.25)}
  nav.alt button{padding:10px 4px}}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:14px;padding:14px;margin-bottom:12px}
.kart h2{font-size:13px;margin:0 0 10px;color:var(--soluk);font-weight:600;display:flex;flex-wrap:wrap;gap:6px;align-items:baseline}
.art{color:var(--art)}.eks{color:var(--eks)}
.iki{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:820px){.iki{grid-template-columns:1fr}}
.iki>.kart{margin-bottom:0}.iki{margin-bottom:12px}
.ozet .ust{display:flex;justify-content:space-between;align-items:center}
.ozet .buyuk{font-size:32px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.5px;margin:2px 0 0}
.ozet .kar{font-size:15px;font-weight:650;font-variant-numeric:tabular-nums}
.ozet svg.kitapc{width:100%;height:56px;display:block;margin:10px 0 4px}
.cipler{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}
.cip{background:var(--kart2);border-radius:10px;padding:7px 8px;min-width:0}
.cip .e{font-size:11px;color:var(--soluk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.cip .d{font-size:15px;font-weight:650;font-variant-numeric:tabular-nums}
.bilgi{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}
.bilgi .cip .d{font-size:14px}
@media(max-width:420px){.cipler{grid-template-columns:repeat(2,1fr)}}
.durum{font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--cizgi);font-weight:600}.durum.ok{color:var(--art);border-color:var(--art)}.durum.yok{color:var(--eks);border-color:var(--eks)}
.cubuk{display:flex;height:8px;border-radius:99px;overflow:hidden;background:var(--kart2);margin:2px 0 10px}
.cubuk span{display:block;height:100%}
.dk{display:flex;align-items:center;gap:8px;padding:8px 0;border-top:1px solid var(--cizgi);cursor:pointer;font-variant-numeric:tabular-nums}
.dk .n{width:9px;height:9px;border-radius:3px;flex:none}.dk .a{flex:1}.dk .v{font-weight:650}
.dk .ac{display:none;flex-basis:100%;color:var(--soluk);font-size:12px;padding:2px 0 0 17px}.dk.acik .ac{display:block}
.dkw{display:flex;flex-wrap:wrap;align-items:center}.dk .ok{color:var(--soluk);font-size:11px;transition:transform .15s}.dk.acik .ok{transform:rotate(90deg)}
.dk.top{cursor:default;font-weight:700}
.grafik{position:relative;height:190px}
.taraf{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;color:var(--soluk);font-weight:600;margin:4px 2px 8px}
.taraf b{font-variant-numeric:tabular-nums}
.kutular{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:8px;margin-bottom:12px}
.kutu{background:var(--kart);border:1px solid var(--cizgi);border-left:3px solid var(--vurgu);border-radius:12px;padding:10px 10px 8px;min-width:0}
.kutu.S{border-left-color:var(--uyari)}
.kutu .ad{font-weight:700;font-size:15px;display:flex;justify-content:space-between;align-items:baseline;gap:6px}
.kutu .f{font-size:17px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:2px;border-radius:5px;padding:0 3px;margin-left:-3px;display:inline-block}
.kutu .gr{font-size:11px;color:var(--soluk);font-variant-numeric:tabular-nums}
.kutu .y{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:2px}.kutu .y small{font-size:11px;font-weight:500}
.kutu svg{width:100%;height:64px;display:block;margin-top:8px;overflow:visible}
.grbekle{height:64px;margin-top:8px;display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--soluk);border-radius:8px;background:var(--kart2)}
.hedef{margin-top:6px}.hedef .c{height:4px;border-radius:9px;background:var(--kart2);overflow:hidden}.hedef .c span{display:block;height:100%;background:var(--art);border-radius:9px}
.hedef .t{font-size:10.5px;color:var(--soluk);margin-top:3px;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.yukari{animation:yk .9s ease-out}.asagi{animation:as .9s ease-out}
@keyframes yk{0%{background:color-mix(in srgb,var(--art) 45%,transparent)}100%{background:transparent}}
@keyframes as{0%{background:color-mix(in srgb,var(--eks) 45%,transparent)}100%{background:transparent}}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}td,th{padding:5px 6px;border-bottom:1px solid var(--cizgi);text-align:right;font-size:13px}
th{color:var(--soluk);font-weight:500}td.l,th.l{text-align:left}.tablo{overflow-x:auto}
.olay{display:flex;gap:8px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--cizgi);font-size:13px}.olay:last-child{border-bottom:0}.olay .z{color:var(--soluk);white-space:nowrap;font-size:12px}
.rozet{flex:none;margin-top:1px;display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600;border:1px solid currentColor;white-space:nowrap}
.r-stop,.r-hata{color:var(--eks)}.r-delist,.r-saglik{color:var(--uyari)}.r-ayar,.r-basla{color:var(--vurgu)}
.bos{color:var(--soluk);padding:18px 0;text-align:center}
.takvim{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}
.takvim .bas{font-size:11px;color:var(--soluk);text-align:center;padding-bottom:2px}
.takvim .g{border-radius:8px;padding:5px 4px 6px;min-height:50px;border:1px solid var(--cizgi);font-variant-numeric:tabular-nums;text-align:center;overflow:hidden}
.takvim .g .n{font-size:11px;color:var(--soluk);text-align:left;line-height:1}
.takvim .g .v{font-size:13px;font-weight:650;margin-top:4px;white-space:nowrap}
.takvim .g.bosg{border:none}.takvim .g.yok{opacity:.35}.takvim .g.yok .v{visibility:hidden}
.takvim .g.hp{background:color-mix(in srgb,var(--art) var(--p),transparent);border-color:transparent}
.takvim .g.hn{background:color-mix(in srgb,var(--eks) var(--p),transparent);border-color:transparent}
@media(max-width:520px){.takvim .g{min-height:42px;padding:4px 2px}.takvim .g .v{font-size:11px}}
.aygez{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}
.aygez button{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);border-radius:8px;padding:2px 10px;cursor:pointer;font:inherit}
.aygez button:disabled{opacity:.35;cursor:default}.aygez b{font-size:14px}
.bekle{color:var(--soluk);font-size:13px;text-align:center;padding:26px 0}
</style></head><body><div class="kap">
<header><div><h1>Carry Panel</h1><div class="k" id="alt"></div></div><span class="canli" id="canliust"><i></i><span>bağlanıyor</span></span></header>
<div class="sekme" id="sekme"></div>
<nav class="alt" id="nav"></nav>
<div id="icerik"></div></div>
<script>
const VERI_GOMULU = /*VERI*/null;
const $ = s => document.querySelector(s);
const yz = (v, d=2) => v==null ? "—" : (v>=0?"+":"") + (v*100).toFixed(d).replace(".",",") + "%";
const para = v => v==null ? "—" : v.toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2}) + " $";
const isaretli = v => v==null ? "—" : (v>=0?"+":"") + para(v);
const sinif = v => v==null ? "" : (v>=0 ? "art" : "eks");
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let VERI, secili = 0, grafikler = [], ayIdx = {};
// MADDE 737: sekmeler (telefonda altta sabit). Seçim adres çubuğunda (#poz) saklanır, yenilemede korunur.
const SAYFALAR = [["ozet","Özet"],["poz","Pozisyonlar"],["gecmis","Geçmiş"],["olay","Olaylar"]];
let sayfa = (location.hash||"").slice(1); if (!SAYFALAR.some(x=>x[0]==sayfa)) sayfa = "ozet";
function sayfaSec(a){ sayfa = a; history.replaceState(null, "", "#"+a); ciz(); scrollTo(0,0); }
const AYAD = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
// PDF'teki gibi: kazanç yeşil, kayıp kırmızı; ton koyuluğu büyüklükle (gün: |%3| ve üstü tam ton)
const ton = (v, tam) => Math.round(14 + 56 * Math.min(1, Math.abs(v) / tam)) + "%";
const isiS = v => v==null || Math.abs(v) < 0.0005 ? "" : (v>0 ? "hp" : "hn");
const isi = (v, tam, ek="") => { const c = isiS(v); return c ? `class="${ek} ${c}" style="--p:${ton(v,tam)}"` : `class="${ek}"`; };
function takvim(k){
  const S = k.seri || []; const G = S.map((s,j)=>({...s, j})).filter(s=>s.gun!=null && s.tarih);
  if (!G.length) return "<div class='bos'>henüz günlük getiri yok</div>";
  const aylar = [...new Set(G.map(s=>s.tarih.slice(0,7)))].sort();
  let i = ayIdx[secili]; if (i==null || i<0 || i>=aylar.length) i = aylar.length - 1;
  const a = aylar[i], [y, m] = a.split("-").map(Number), M = G.filter(s=>s.tarih.startsWith(a));
  const gun = {}; M.forEach(s=>{ gun[+s.tarih.slice(8,10)] = s; });
  const bas = (new Date(y, m-1, 1).getDay() + 6) % 7, n = new Date(y, m, 0).getDate();
  let h = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"].map(d=>`<div class="bas">${d}</div>`).join("");
  for (let b=0; b<bas; b++) h += `<div class="g bosg"></div>`;
  for (let d=1; d<=n; d++){
    const s = gun[d];
    if (!s){ h += `<div class="g yok"><div class="n">${d}</div><div class="v">·</div></div>`; continue; }
    const onc = s.j>0 ? S[s.j-1].kitap : null, usd = onc!=null ? onc * s.gun : null;
    const ipucu = `${s.tarih}  ${yz(s.gun)}` + (usd!=null ? `  (${isaretli(usd)})` : "");
    h += `<div ${isi(s.gun,0.03,"g")} title="${ipucu}"><div class="n">${d}</div><div class="v">${yz(s.gun)}</div></div>`;
  }
  const g = M.map(s=>s.gun), art_ = g.filter(v=>v>0).length, eks_ = g.filter(v=>v<0).length;
  const eniyi = M.reduce((p,c)=>c.gun>p.gun?c:p), enkotu = M.reduce((p,c)=>c.gun<p.gun?c:p);
  const ayg = (k.aylik||{})[a];
  return `<div class="aygez"><button ${i<=0?"disabled":""} onclick="ayIdx[secili]=${i-1};ciz()" aria-label="önceki ay">‹</button>
    <b>${AYAD[m-1]} ${y} · <span class="${sinif(ayg)}">${yz(ayg)}</span></b>
    <button ${i>=aylar.length-1?"disabled":""} onclick="ayIdx[secili]=${i+1};ciz()" aria-label="sonraki ay">›</button></div>
    <div class="takvim">${h}</div>
    <div class="k" style="margin-top:8px">kazanç günü <b class="art">${art_}</b> · kayıp günü <b class="eks">${eks_}</b> / ${g.length} ·
    en iyi ${+eniyi.tarih.slice(8,10)} ${AYAD[m-1]} <span class="${sinif(eniyi.gun)}">${yz(eniyi.gun)}</span> · en kötü ${+enkotu.tarih.slice(8,10)} ${AYAD[m-1]} <span class="${sinif(enkotu.gun)}">${yz(enkotu.gun)}</span></div>`;
}
// MADDE 732: ANLIK FİYAT. Pozisyon listesi (miktar, giriş) sunucudan; işaret fiyatı tarayıcıdan Binance'in HERKESE AÇIK
// akışından (wss://fstream.binance.com/market — eski /stream adresi bağlanıp veri göndermiyor; anahtarsız, saniyede bir). Panel yine emir veremez, anahtar görmez.
let WS = null, WSK = "", FIYAT = {}, ONCEKI = {}, wsZaman = 0;
function canliBagla(k){
  if (VERI_GOMULU || !window.WebSocket) return;
  const P = k && k.poz_kaynak=="canlı" ? Object.entries(k.pozisyonlar||{}).filter(p=>p[1].giris>0 && p[1].miktar) : [];
  const anahtar = P.map(p=>p[0]).sort().join(",");
  if (anahtar===WSK && WS && WS.readyState<=1) return;
  if (WS){ WS.onclose = null; WS.close(); WS = null; }
  WSK = anahtar; if (!anahtar) return;
  WS = new WebSocket("wss://fstream.binance.com/market/stream?streams=" + P.map(p=>p[0].toLowerCase()+"@markPrice@1s").join("/"));
  WS.onmessage = e => { try { const d = JSON.parse(e.data).data; if (d && d.s && +d.p>0){ FIYAT[d.s] = +d.p; wsZaman = Date.now(); } } catch(_){} };
  WS.onclose = () => { WS = null; WSK = ""; setTimeout(()=>canliBagla(VERI && VERI.kurulumlar[secili]), 5000); };
}
// MADDE 736: pozisyon kutuları (TradingView benzeri). Son 24 sa 15 dk mum kapanışları tarayıcıdan Binance'in herkese açık
// REST'inden (anahtarsız, 15 dk'da bir), son nokta anlık işaret fiyatı. Kesikli çizgi = giriş fiyatı; renk = pozisyonun kârı.
let MUM = {}, mumZaman = 0, mumAnahtar = "";
async function mumYukle(k){
  const S = Object.keys((k && k.pozisyonlar) || {}), a = S.slice().sort().join(",");
  if (VERI_GOMULU || !S.length || (a===mumAnahtar && Date.now()-mumZaman < 15*60e3)) return;
  mumAnahtar = a; mumZaman = Date.now();
  let gelen = 0;
  await Promise.all(S.map(async s => { try {
    const d = await (await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=15m&limit=96`, {cache:"no-store"})).json();
    if (Array.isArray(d) && d.length){ MUM[s] = d.map(x=>+x[4]).filter(v=>v>0); gelen++; }
  } catch(_){} }));
  if (gelen < S.length) mumZaman = Date.now() - 14*60e3;   // madde 738: eksik geldiyse 1 dk sonra yeniden dene
  canliBoya();
}
const fiyatYaz = v => v==null ? "—" : v.toLocaleString("tr-TR", v>=1000 ? {minimumFractionDigits:2,maximumFractionDigits:2} : {minimumSignificantDigits:5,maximumSignificantDigits:5});
function cizgi(seri, W, H, renk, yatay, kimlik="c"){
  // seri: sayılar; yatay: kesikli referans çizgisi (giriş fiyatı / başlangıç kitabı)
  if (!seri || seri.length < 2) return `<svg viewBox="0 0 ${W} ${H}"></svg>`;
  const hepsi = yatay!=null ? seri.concat([yatay]) : seri;
  let lo = Math.min(...hepsi), hi = Math.max(...hepsi); if (hi-lo < Math.abs(hi)*1e-6 + 1e-12){ hi += Math.abs(hi)*1e-3 + 1e-9; lo -= Math.abs(lo)*1e-3 + 1e-9; }
  const x = i => (i/(seri.length-1)) * (W-6), y = v => H-3 - (v-lo)/(hi-lo) * (H-6);
  const yol = seri.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const sx = x(seri.length-1), sy = y(seri[seri.length-1]);
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <defs><linearGradient id="gd-${kimlik}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${renk}" stop-opacity=".38"/><stop offset="1" stop-color="${renk}" stop-opacity="0"/></linearGradient></defs>
    <path d="${yol}L${sx.toFixed(1)},${H}L0,${H}Z" fill="url(#gd-${kimlik})"/>
    ${yatay!=null?`<line x1="0" x2="${W}" y1="${y(yatay).toFixed(1)}" y2="${y(yatay).toFixed(1)}" stroke="${css("--soluk")}" stroke-dasharray="3 3" stroke-width="1" vector-effect="non-scaling-stroke"/>`:""}
    <path d="${yol}" fill="none" stroke="${renk}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="3" fill="${renk}"/></svg>`;
}
function kivilcim(s, p, f, renk){
  const seri = (MUM[s]||[]).slice(); if (f){ if (seri.length) seri[seri.length-1] = f; else seri.push(f); }
  if (seri.length < 2) return `<div class="grbekle">grafik yükleniyor…</div>`;
  return cizgi(seri, 160, 64, renk, p.giris>0 ? p.giris : null, s);
}
// MADDE 737: kâr al hedefine ilerleme. Long: giriş -> giriş x (1 + kademe); short: giriş -> giriş x (1 − kademe).
function hedefCubuk(k, p, f){
  const H = (k.hedef||{})[p.miktar>0 ? "L" : "S"] || [];
  if (!H.length || !(p.giris>0) || !f) return "";
  const yon = p.miktar>0 ? 1 : -1, hareket = (f/p.giris - 1) * yon;
  let i = H.findIndex(h => hareket < h); const gecti = i < 0; if (gecti) i = H.length - 1;
  const h = H[i], hf = p.giris * (1 + yon*h), ilerl = Math.max(0, Math.min(1, hareket / h));
  const etiket = gecti ? `son hedef ${fiyatYaz(hf)} geçildi` : `${i?"2. hedef":"hedef"} ${fiyatYaz(hf)} (${yon>0?"+":"−"}%${Math.round(h*100)}) · %${Math.round(ilerl*100)} yol`;
  return `<div class="hedef"><div class="c"><span style="width:${(ilerl*100).toFixed(1)}%"></span></div><div class="t">${etiket}</div></div>`;
}
function kutuIc(s, p, k){
  const f = FIYAT[s] || p.isaret, ok = f && p.giris>0 && p.miktar;
  const ky = ok ? (f/p.giris - 1) * (p.miktar>0 ? 1 : -1) * 100 : p.kar_yuzde;
  const g = ok ? p.miktar * (f - p.giris) : p.gerceklesmemis, usd = ok ? Math.abs(p.miktar) * f : p.usd;
  const renk = css((ky||0) >= 0 ? "--art" : "--eks");
  const o = ONCEKI[s], flas = (o && f && f!==o) ? (f>o ? "yukari" : "asagi") : ""; ONCEKI[s] = f;
  return `<div class="ad"><span>${s.replace(/USDT$/,"")}</span><span class="k">${para(usd)}</span></div>
    <div class="f ${flas}">${fiyatYaz(f)}</div><div class="gr">giriş ${fiyatYaz(p.giris)}</div>
    <div class="y ${sinif(ky)}">${ky==null?"—":(ky>=0?"+":"")+ky.toFixed(2).replace(".",",")+"%"} <small>${g==null?"":isaretli(g)}</small></div>
    ${kivilcim(s, p, f, renk)}${k ? hedefCubuk(k, p, f) : ""}`;
}
function canliDurum(){
  const on = !VERI_GOMULU && Date.now() - wsZaman < 5000, e = $("#canliust");
  if (e){ e.className = "canli" + (on ? " on" : ""); e.lastElementChild.textContent = on ? "canlı" : (VERI ? "güncellendi " + VERI.uretim.slice(11) : "bağlanıyor"); }
  return on;
}
function canliBoya(){
  const on = canliDurum();
  const k = VERI && VERI.kurulumlar[secili]; if (!k) return;
  const ds = $("#dilimsure"); if (ds) ds.innerHTML = dilimKart(k.dilim);
  if (k.poz_kaynak!="canlı") return;
  let top = 0; const taraf = {L:[0,0], S:[0,0]};
  for (const [s,p] of Object.entries(k.pozisyonlar||{})){
    const f = FIYAT[s], ok = f && p.giris>0 && p.miktar;
    const g = ok ? p.miktar * (f - p.giris) : (p.gerceklesmemis||0); top += g;
    const t = taraf[p.yon] || taraf.L; t[0] += ok ? Math.abs(p.miktar)*f : (p.usd||0); t[1] += g;
    const et = document.getElementById("t-"+s); if (et) et.innerHTML = kutuIc(s, p, k);
  }
  for (const y of ["L","S"]){ const e = document.getElementById("taraf-"+y); if (e) e.innerHTML = `${para(taraf[y][0])} · <span class="${sinif(taraf[y][1])}">${isaretli(taraf[y][1])}</span>`; }
  const fark = top - (k.gerceklesmemis||0), eg = $("#gerc");
  if (eg){ eg.textContent = isaretli(top); eg.className = sinif(top); }
  const ekd = $("#kitapd"); if (ekd && k.kitap_canli!=null) ekd.textContent = para(k.kitap_canli + fark);
  const eku = $("#karusd"); if (eku && k.kar_usd!=null){ const ku = k.kar_usd + fark; eku.textContent = `${isaretli(ku)} (${yz(k.kitap_bas ? ku/k.kitap_bas : null)})`; eku.className = "kar " + sinif(ku); }
  const ed = $("#dokum"); if (ed && k.kar_usd!=null) ed.innerHTML = dokumYaz(k, top, k.kar_usd + fark);
}
// MADDE 733/737: başlangıçtan $ = açık pozisyonlar + kapanan + funding + komisyon + diğer + başlangıç farkı.
// Kalemler tek satır; dokununca açıklama açılır (seçim saniyelik yenilemede korunur). Üstte kalemlerin payı (renkli çubuk).
const ACIK = new Set();
function dkAc(a){ ACIK.has(a) ? ACIK.delete(a) : ACIK.add(a); const k = VERI.kurulumlar[secili]; canliBoya(); if (k.poz_kaynak!="canlı"){ const ed=$("#dokum"); if(ed) ed.innerHTML = dokumYaz(k, k.gerceklesmemis, k.kar_usd); } }
function dokumYaz(k, poz, kar){
  const D = k.dokum, dg = D.diger_gelir||0, fark = kar - poz - D.gerceklesen - D.funding - D.komisyon - dg;
  const K = [["poz","Açık pozisyonlar", poz, "şu an açık coinlerin fiyat hareketi; kapanınca kesinleşir", "--vurgu", true],
             ["kap","Kapanan pozisyonlar", D.gerceklesen, "kapatılmış işlemlerin kesinleşmiş kâr / zararı", "--mor", false],
             ["fun","Funding", D.funding, "pozisyon taşıdığı için 8 saatte bir alınan (+) / ödenen (−) ücret — stratejinin asıl geliri", "--art", true],
             ["kom","Komisyon", D.komisyon, "Binance işlem ücreti", "--uyari", true],
             ["dig","Diğer Binance kayıtları", dg, "sigorta fonu vb.", "--mor", false],
             ["bas","Başlangıç farkı", fark, "başlangıç kaydı alınırken açık pozisyonların o anki kârı (başlangıç tutarına zaten dahil) ve demo / gerçek fiyat farkı; sabit kalır", "--soluk", false]]
    .filter(x => x[5] || Math.abs(x[2]) >= 0.005);
  const tm = K.reduce((a,x)=>a+Math.abs(x[2]), 0) || 1;
  const cubuk = `<div class="cubuk">${K.map(x=>`<span style="width:${(Math.abs(x[2])/tm*100).toFixed(1)}%;background:${css(x[4])}" title="${x[1]}"></span>`).join("")}</div>`;
  return cubuk + K.map(x=>`<div class="dk dkw ${ACIK.has(x[0])?"acik":""}" onclick="dkAc('${x[0]}')"><span class="n" style="background:${css(x[4])}"></span><span class="a">${x[1]} <span class="ok">›</span></span><span class="v ${sinif(x[2])}">${isaretli(x[2])}</span><span class="ac">${x[3]}</span></div>`).join("")
    + `<div class="dk top"><span class="a">Toplam (başlangıçtan beri)</span><span class="v ${sinif(kar)}">${isaretli(kar)}</span></div>`;
}
function ayarKart(k){
  const A = k.ayar;
  if (!A) return `<div class="d">${k.profil||"—"}${k.doz?" · "+k.doz+"x":""}</div>`;
  const ad = A.profil || k.profil || "—";
  return `<div class="d">${ad} · ${A.gross.toFixed(2).replace(".",",")}x</div><div class="k">${A.stop!=null?`koşullu stop %${(A.stop*100).toFixed(0)}`:"koşullu stop yok"}${A.onerilen?" · önerilen":""}</div>`;
}
function dilimKart(D){
  if (!D) return `<div class="d">—</div>`;
  const kalan = D.zaman - Date.now()/1000;
  const sure = kalan <= 0 ? (kalan > -1800 ? "şimdi" : "gecikti") : (kalan >= 3600 ? `${Math.floor(kalan/3600)} sa ${Math.floor(kalan%3600/60)} dk` : `${Math.ceil(kalan/60)} dk`);
  return `<div class="d ${kalan<=-1800?'eks':''}">${sure}</div><div class="k">${D.saat} · ${D.dolu}/${D.n} dilim dolu</div>`;
}
function icraKart(k){
  const I = k.icra;
  if (!I) return `<div class="k">Henüz emir kaydı yok. Bot emir gönderdikçe dolar.</div>`;
  const T = I.tp || {}, G = I.giris || {};
  const yzd = v => v==null ? "—" : (v*100).toFixed(0) + "%";
  const bp = v => v==null ? "—" : (v>=0?"+":"") + v.toFixed(1).replace(".",",") + " bp";
  const dr = T.dolum_orani, drc = dr==null ? "" : (dr>=0.9 ? "art" : dr<=0.8 ? "eks" : "");
  const satir = (a, b, c="") => `<tr><td class="l">${a}</td><td class="${c}">${b}</td></tr>`;
  return `<div class="tablo"><table>
    ${satir("TP dolum oranı (fiyat değince dolan)", `${yzd(dr)} <span class="k">(${T.dokunan||0} dokunan / ${T.olculen||0} ölçülen)</span>`, drc)}
    ${satir("TP / kademe emri", `${T.konan||0} konan · ${T.tam||0} tam · ${T.kismi||0} kısmi`)}
    ${satir("Kısmi dolum payı", yzd(T.kismi_pay))}
    ${satir("Giriş: maker payı", yzd(G.maker_pay))}
    ${satir("Giriş: kayma (gönderim fiyatına göre)", bp(G.kayma_bp), G.kayma_bp==null?"":(G.kayma_bp>5?"eks":""))}
    ${satir("Gerçek komisyon (model 5 bp)", bp(G.komisyon_bp), G.komisyon_bp==null?"":(G.komisyon_bp>6?"eks":""))}
    ${satir("GTX ilk deneme · kovalama · piyasaya düşen", `${G.gtx_ilk||0} · ${G.kovala||0} · ${G.piyasa_yedek||0}`, (G.piyasa_yedek||0)>0?"eks":"")}
  </table></div><div class="k" style="margin-top:6px">Referans (madde 695): TP dolum ≥ %90 güvenli, ≤ %80 alarm; dolum %70'te yıllık −29 puan.
  Kayma eksi = gönderim anındaki fiyattan daha iyi doldu. Yalnız kayıt; bot kararlarını etkilemez.</div>`;
}
function ozetSayfa(k, svc, sv){
  const S = k.seri || [], kit = S.map(s=>s.kitap).filter(v=>v!=null);
  if (k.kitap_canli!=null && kit.length) kit.push(k.kitap_canli);
  const cip = (e, d, c="") => `<div class="cip"><div class="e">${e}</div><div class="d ${c}">${d}</div></div>`;
  return `<div class="kart ozet">
    <div class="ust"><span class="k">Kitap</span>${svc?`<span class="durum ${svc}">${sv=="active"?"çalışıyor":sv}</span>`:""}</div>
    <div class="buyuk" id="kitapd">${para(k.kitap_canli!=null?k.kitap_canli:k.kitap)}</div>
    ${k.kar_usd!=null?`<div><span id="karusd" class="kar ${sinif(k.kar_usd)}">${isaretli(k.kar_usd)} (${yz(k.kar_oran)})</span> <span class="k">başlangıç ${para(k.kitap_bas)}</span></div>`:""}
    ${kit.length>=2?`<svg class="kitapc" viewBox="0 0 300 56" preserveAspectRatio="none">${cizgi(kit, 300, 56, css((kit[kit.length-1]-kit[0])>=0?"--art":"--eks"), kit[0], "kitap").replace(/^<svg[^>]*>|<\/svg>$/g,"")}</svg>`:""}
    <div class="cipler">${cip(`Son gün${k.son_tarih?" · "+k.son_tarih.slice(8,10)+" "+AYAD[+k.son_tarih.slice(5,7)-1].slice(0,3):""}`, yz(k.bugun), sinif(k.bugun))}${cip("7 gün", yz(k.g7), sinif(k.g7))}${cip("30 gün", yz(k.g30), sinif(k.g30))}${cip("En büyük düşüş", yz(k.dd), k.dd<0?"eks":"")}</div>
    <div class="bilgi"><div class="cip"><div class="e">Ayar</div>${ayarKart(k)}</div><div class="cip"><div class="e">Sonraki dilim</div><div id="dilimsure">${dilimKart(k.dilim)}</div></div></div>
  </div>
  ${k.dokum&&k.gerceklesmemis!=null?`<div class="kart"><h2>Kâr / zarar nereden geldi? <span class="k">· satıra dokun: açıklama</span></h2><div id="dokum">${dokumYaz(k, k.gerceklesmemis, k.kar_usd)}</div></div>`:""}`;
}
function pozSayfa(k){
  const P = Object.entries(k.pozisyonlar||{}); const L = P.filter(p=>p[1].yon=="L").sort((a,b)=>b[1].usd-a[1].usd), S = P.filter(p=>p[1].yon=="S").sort((a,b)=>b[1].usd-a[1].usd);
  const top = (A, i) => A.reduce((a,p)=>a+(i ? (p[1].gerceklesmemis||0) : (p[1].usd||0)), 0);
  const kutular = (A, y, ad) => A.length ? `<div class="taraf"><span>${ad} (${A.length})</span><b id="taraf-${y}">${para(top(A,0))} · <span class="${sinif(top(A,1))}">${isaretli(top(A,1))}</span></b></div>
    <div class="kutular">${A.map(p=>`<div class="kutu ${y}" id="t-${p[0]}">${kutuIc(p[0], p[1], k)}</div>`).join("")}</div>` : "";
  return `<div class="kart"><h2>Pozisyonlar <span class="k">${k.poz_kaynak=="canlı"?"liste "+k.poz_zaman:"günlük defter "+(k.poz_zaman||"")}${k.gerceklesmemis!=null?` · gerçekleşmemiş <b id="gerc" class="${sinif(k.gerceklesmemis)}">${isaretli(k.gerceklesmemis)}</b>`:""}</span></h2>
    ${kutular(L, "L", "LONG") + kutular(S, "S", "SHORT") || "<div class='bos'>açık pozisyon yok</div>"}
    <div class="k">grafik: son 24 saat (15 dk) · kesikli çizgi giriş fiyatı · renk pozisyonun kâr / zararı (short'ta fiyat düşerse yeşil) · alttaki çubuk kâr al hedefine kalan yol</div></div>`;
}
function gecmisSayfa(k){
  const grafikVar = (k.seri||[]).length >= 3;   // madde 734/737: 1-2 noktalık grafik bilgi vermez, yalnız yer kaplar
  return `<div class="kart"><h2>Günlük takvim <span class="k">· kazanç yeşil, kayıp kırmızı (koyuluk = büyüklük)</span></h2>${takvim(k)}
      ${(k.funding_top||k.komisyon_top)?`<div class="k" style="margin-top:6px">Defter toplamı: funding ${isaretli(k.funding_top)} · komisyon ${isaretli(k.komisyon_top)}</div>`:""}</div>
    ${grafikVar?`<div class="iki"><div class="kart"><h2>Kitap ($)</h2><div class="grafik"><canvas id="g1"></canvas></div></div>
      <div class="kart"><h2>Günlük getiri</h2><div class="grafik"><canvas id="g2"></canvas></div></div></div>`
      :`<div class="kart bekle">Kitap ve günlük getiri grafikleri 3 günlük veri birikince görünür (şu an ${(k.seri||[]).length} gün).</div>`}
    <div class="kart"><h2>İcra · son 30 gün <span class="k">(emir defteri)</span></h2>${icraKart(k)}</div>`;
}
function olaySayfa(k){
  return `<div class="kart"><h2>Olaylar</h2>${(k.olaylar||[]).map(o=>`<div class="olay"><span class="rozet r-${o.tur}">${o.tur}</span><div><div>${o.metin.replace(/</g,"&lt;").replace(/\s*\|\s*/g," · ")}</div><div class="z">${o.zaman}</div></div></div>`).join("") || "<div class='bos'>olay yok</div>"}</div>
  ${(VERI.paketler||[]).length && !VERI_GOMULU ? `<div class="kart"><h2>Aylık veri paketleri <span class="k">(araştırma: indirip sohbete yükleyin)</span></h2>${VERI.paketler.map(p=>`<div class="olay"><a href="paket/${p.ad}" style="color:var(--vurgu)">${p.ad}</a><span class="z">${p.mb} MB</span></div>`).join("")}</div>` : ""}`;
}
function ciz(){
  const K = VERI.kurulumlar; $("#alt").textContent = K[secili] ? `${K[secili].ad} · ${K[secili].mod}` : "";
  $("#sekme").innerHTML = K.length > 1 ? K.map((k,i)=>`<button class="${i==secili?'on':''}" onclick="secili=${i};ciz()">${k.ad} · ${k.mod}</button>`).join("") : "";
  $("#nav").innerHTML = SAYFALAR.map(([a,ad])=>`<button class="${a==sayfa?'on':''}" onclick="sayfaSec('${a}')">${ad}</button>`).join("");
  const k = K[secili]; if(!k){ $("#icerik").innerHTML = "<div class='kart bos'>Henüz kurulum / defter yok.</div>"; return; }
  const sv = k.servis; const svc = sv=="active" ? "ok" : (sv=="—"||sv=="?" ? "" : "yok");
  $("#icerik").innerHTML = sayfa=="poz" ? pozSayfa(k) : sayfa=="gecmis" ? gecmisSayfa(k) : sayfa=="olay" ? olaySayfa(k) : ozetSayfa(k, svc, sv);
  canliBagla(k); canliBoya(); mumYukle(k);
  grafikler.forEach(g=>g.destroy()); grafikler = [];
  if (!window.Chart || !$("#g1")) return;
  const x = k.seri.map(s=>s.tarih), izg = css("--cizgi"), sol = css("--soluk");
  const ortak = {responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false}},
    scales:{x:{ticks:{color:sol,maxTicksLimit:innerWidth<600?4:8,maxRotation:0,autoSkip:true},grid:{display:false}},y:{ticks:{color:sol},grid:{color:izg}}}};
  grafikler.push(new Chart($("#g1"),{type:"line",data:{labels:x,datasets:[{data:k.seri.map(s=>s.kitap),borderColor:css("--vurgu"),borderWidth:2,pointRadius:0,fill:false,tension:.15}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>para(c.parsed.y)}}}}}));
  grafikler.push(new Chart($("#g2"),{type:"bar",data:{labels:x,datasets:[{data:k.seri.map(s=>s.gun==null?null:s.gun*100),
    backgroundColor:k.seri.map(s=>(s.gun||0)>=0?css("--art"):css("--eks"))}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>(c.parsed.y>=0?"+":"")+c.parsed.y.toFixed(2).replace(".",",")+"%"}}},
      scales:{...ortak.scales,y:{ticks:{color:sol,callback:v=>v+"%"},grid:{color:izg}}}}}));
}
async function yukle(){
  if (VERI_GOMULU){ VERI = VERI_GOMULU; ciz(); return; }
  try { const r = await fetch("api/veri", {cache:"no-store"}); VERI = await r.json(); ciz(); } catch(e){ $("#alt").textContent = "veri alınamadı"; }
}
yukle(); if(!VERI_GOMULU){ setInterval(yukle, 60000); setInterval(canliBoya, 1000); }
if(!VERI_GOMULU && "serviceWorker" in navigator){ try{ navigator.serviceWorker.register("sw.js"); }catch(e){} }
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ()=>VERI && ciz());
</script></body></html>"""


SW_JS = """const K="carry-kabuk-v2";
self.addEventListener("install",e=>{e.waitUntil(caches.open(K).then(c=>c.addAll(["./","ikon-192.png","ikon-512.png"])));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(a=>Promise.all(a.filter(x=>x!==K).map(x=>caches.delete(x)))));self.clients.claim();});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);
  if(u.origin!==location.origin||e.request.method!=="GET"||u.pathname.includes("/api/")||u.pathname.includes("/paket/"))return;   // madde 738: Binance vb. dış istekler SW'den GEÇMEZ   // veri ve paket önbelleğe ALINMAZ
  e.respondWith(fetch(e.request).then(r=>{const k=r.clone();caches.open(K).then(c=>c.put(e.request,k));return r;}).catch(()=>caches.match(e.request)));});
"""
IKON_192 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAADUElEQVR42u3dsW0UQRTHYYwuRwTIogCaoAoaQBc7pwzyiy0aoAqaoAB0XRBYcnLIXnZmZ9689/0ihJCxuE//2ZWP27t37z+8kfb21j+BABJAAkgASQAJIAEkgCSABJAAEkASQAJIAAkgCSABJIAEkACSABJAAkgASQAJIAEkgCSABJAAEkASQAJIATr5J8jap59fb3/z95cfff+WO5/SWoTOQYwcYeX0bPwzANEzwhBAFfV0NARQUT29DAFUV08XQwDJAgkgzTqDGr8CQLJAAkgAaULny3XuN+Cn8ehYoNp6Pv/53vjVWn44D5DtcYSh4whTi56WU6zxzWUAJdmefYba35roLa2pjq1fH7+N1GOBsl30bN+hXm+LBijbJfMWQx3fVO8uLNvd1uPD/dMv/LceevbrGZYFSkJnih6ADI+LaHrm6bFAji2ADM/UHGH0WCB0LBA9K+qxQK6XATI8jjB6FtVjgRxbABkeRxg9i+oBiB5HWKLWomOBYs3PinosUAg9i9KxQI4tgBafn9X1OMKm6UlAxwI5tgBacH4y6QGIHoAEkPkBiJ6KegASQOYHIHoAkiNM5gcgegASQOanxvwARA9AAsj8AERPRT0ACSDzAxA9AMkRJvMDED2DO+V4dSu/hHNb73FPLwxDR0bmJyegja9r44tKT85roO2v6/lyDfiIdQu0hp7GnTA/CQF1mZMtrzc9Ce/Ceh1Gz1/Ha19lgQ69jrllZH5SARp2FfykgZ5UR9jIeyj3a9lu4yO/ouYnOiB6AHKauAZaRM/zJAyQZ35C34V1+YTl4xjRE3qBen0+98hBUpQFOu7T3XsxMj9BAQ17Lkmdp3cVugsb+VSbx4d7DlIt0NxnIvmpxdqAgjxR69Vvg56IgAI+j+2f3xI9EQFFfprf+XKFJjSgas+CLNIpph503MbTAxA9mniEueixQPRoBiB6AKJHMwDRA1BT/6uBHoD2m6AnQUf9KOPlswwdC7R/XegBaNxFkuoCurVCD0D7DdED0H5D9LgLkwJcRAsgCSABJIAEkACSABJAAkgASQAJIAEkgCSABJAAEkASQAJIAAkgCSABJIAEkACSABJAAkgASQAJIAEkgCSABJAAEkASQAJIAAkg1e0vEmVbz2lwGEEAAAAASUVORK5CYII="
IKON_512 = "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"


def statik_html(v: dict) -> str:
    return SAYFA.replace("/*VERI*/null", json.dumps(v, ensure_ascii=False).replace("</", "<\\/"))


def uygulama(klasorler: list[str]):
    from flask import Flask, Response, jsonify, request
    app = Flask(__name__)
    sifre = os.getenv("CARRY_PANEL_SIFRE", "")

    @app.before_request
    def _kimlik():
        if sifre:
            a = request.authorization
            if not a or a.username != "carry" or not hmac.compare_digest(a.password or "", sifre):
                return Response("şifre gerekli", 401, {"WWW-Authenticate": 'Basic realm="carry"'})

    @app.after_request
    def _basliklar(r):
        r.headers["X-Frame-Options"] = "DENY"
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["Cache-Control"] = "no-store"
        r.headers["Content-Security-Policy"] = ("default-src 'none'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                                                "style-src 'unsafe-inline'; connect-src 'self' wss://fstream.binance.com https://fapi.binance.com; img-src 'self' data:; manifest-src 'self'; worker-src 'self'")
        return r

    # MADDE 680: PWA — telefonda "Ana ekrana ekle" ile uygulama gibi açılır (Tailscale HTTPS adresinde). Önbellek YALNIZ kabuk
    # (sayfa + simgeler); veri (/api/veri) hiçbir zaman önbelleğe alınmaz -> çevrimdışıyken eski rakam gösterilmez.
    @app.get("/manifest.webmanifest")
    def manifest():
        m = {"name": "Carry Panel", "short_name": "Carry", "start_url": "./", "scope": "./", "display": "standalone",
             "background_color": "#0f1115", "theme_color": "#0f1115",
             "icons": [{"src": "ikon-192.png", "sizes": "192x192", "type": "image/png"},
                       {"src": "ikon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}
        return Response(json.dumps(m), mimetype="application/manifest+json")

    @app.get("/ikon-<int:n>.png")
    def ikon(n):
        import base64
        from flask import abort
        if n not in (192, 512):
            abort(404)
        return Response(base64.b64decode(IKON_192 if n == 192 else IKON_512), mimetype="image/png")

    @app.get("/sw.js")
    def sw():
        return Response(SW_JS, mimetype="application/javascript", headers={"Service-Worker-Allowed": "./"})

    @app.get("/")
    def ana():
        return Response(SAYFA, mimetype="text/html")

    @app.get("/api/veri")
    def api():
        return jsonify(veri(klasorler))

    @app.get("/paket/<ad>")
    def paket(ad):
        from flask import abort, send_from_directory
        if not _PAKET_AD.match(ad):          # yalnız paket_YYYY-MM.zip; yol gezintisi yok
            abort(404)
        return send_from_directory(PAKET_DIR, ad, as_attachment=True)

    return app


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--klasor", action="append", help="kurulum klasörü (varsayılan: /opt/carry ve /opt/carry-*)")
    ap.add_argument("--host", default=os.getenv("CARRY_PANEL_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("CARRY_PANEL_PORT", "8050")))
    ap.add_argument("--disa-aktar", metavar="HTML", help="tek dosyalık anlık görüntü yaz ve çık")
    a = ap.parse_args(argv)
    klasorler = a.klasor or kurulumlar() or [os.path.dirname(os.path.abspath(__file__))]
    if a.disa_aktar:
        open(a.disa_aktar, "w", encoding="utf-8").write(statik_html(veri(klasorler)))
        print(f"panel: {a.disa_aktar}")
        return 0
    if a.host not in ("127.0.0.1", "localhost", "::1") and not os.getenv("CARRY_PANEL_SIFRE"):
        print("!! panel dış arayüze açılıyor ama CARRY_PANEL_SIFRE yok — reddedildi (127.0.0.1 + tailscale serve kullanın)")
        return 2
    from waitress import serve
    print(f"panel: http://{a.host}:{a.port}  (salt okunur)")
    serve(uygulama(klasorler), host=a.host, port=a.port, threads=4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
