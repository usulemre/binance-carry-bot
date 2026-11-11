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
    ("stop_tut", re.compile(r"KOŞULLU 24 SA STOP: \S+ .*tutuluyor")),   # madde 742: stop şartı coinde var, piyasada yok
    ("delist", re.compile(r"DELİST: \S+ (listeden çıkıyor|kapanmalı)")),
    ("saglik", re.compile(r"SAĞLIK KAPISI KAPALI")),
    ("postonly", re.compile(r"code=-5022")),   # madde 753: kovalamada post-only reddi — normal, bot piyasa emrine geçer
    ("hata", re.compile(r"\[(?:ERROR|CRITICAL)\]|tur başarısız|KAPATILAMADI")),   # madde 742: her ERROR satırı
    ("tp", re.compile(r"(?:KÂR AL|MERDİVEN) doldu")),
    ("uyari", re.compile(r"PİYASA emrine düşülüyor")),
    ("tur", re.compile(r"\| dilim \d+/\d+ yenilendi \|")),
    ("ayar", re.compile(r"önerilen ayar etkin|ÖNERİLEN AYAR: kitap")),
    ("basla", re.compile(r"carry_bot başladı")),
]
_STOP_TUT_SEM = re.compile(r"KOŞULLU 24 SA STOP: (\S+)")
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


def log_satirlari(klasor: str, son_bayt: int) -> list[str] | None:
    """MADDE 743: carry_bot.log'un son `son_bayt`'ı. logrotate (haftalık, copytruncate) pazar 00:00'da dosyayı
    boşaltır; güncel dosya kısa kalırsa eksik kısım bir önceki dosyadan (carry_bot.log.1 ya da .1.gz) tamamlanır.
    Yoksa panel rotasyondan sonra ayarı ve bütün olayları kaybediyordu. Hiçbiri okunamazsa None."""
    yol = os.path.join(klasor, "carry_bot.log")
    veri, okundu = b"", False
    try:
        with open(yol, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - son_bayt)); veri = f.read(); okundu = True
    except OSError:
        pass
    if len(veri) < son_bayt:
        eski = b""
        for ad, ac in (("carry_bot.log.1", open), ("carry_bot.log.1.gz", None)):
            try:
                if ac is None:
                    import gzip
                    with gzip.open(os.path.join(klasor, ad), "rb") as f:
                        eski = f.read()
                else:
                    with open(os.path.join(klasor, ad), "rb") as f:
                        eski = f.read()
                okundu = True
                break
            except (OSError, EOFError):
                continue
        if eski:
            eski = eski[-(son_bayt - len(veri)):]
            veri = eski + (b"" if eski.endswith(b"\n") or not veri else b"\n") + veri
    return veri.decode("utf-8", "replace").splitlines() if okundu else None


def etkin_ayar(klasor: str, son_bayt: int = 5_000_000) -> dict | None:
    """MADDE 734: botun SON başlangıçta GERÇEKTE kullandığı ayar (log'dan). Defterdeki profil / doz .env'deki
    ham değerdir (ör. ONERILEN 1.0) — önerilen modda seçilen profil (T7K 1.15x + koşullu stop) orada görünmez."""
    satirlar = log_satirlari(klasor, son_bayt)
    if satirlar is None:
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
                if k.strip() in ("BINANCE_MODE", "CARRY_PROFIL", "CARRY_BILDIRIM_AD", "CARRY_SERMAYE_OLCEK", "CARRY_LONG_24S",
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


def olaylar(klasor: str, en_cok: int = 80, son_bayt: int = 2_000_000) -> list[dict]:
    satirlar = log_satirlari(klasor, son_bayt)
    if satirlar is None:
        return []
    out, tutulan = [], set()
    for s in satirlar:
        for tur, d in OLAY_DESENLERI:
            if d.search(s):
                m = _ZAMAN.match(s)
                zaman = _log_zamani(m.group(1)) if m else ""
                if tur == "stop_tut":   # madde 742: aynı coinin "tutuluyor" kararı her turda / yeniden başlamada tekrarlanır: günde bir
                    a = (zaman[:10], (_STOP_TUT_SEM.search(s) or [None, s])[1])
                    if a in tutulan:
                        break
                    tutulan.add(a)
                metin = s[m.end():].strip(" -|") if m else s
                out.append({"zaman": zaman, "tur": tur, "metin": _GIZLI.sub("***", metin)[:300]})
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


def gun_etiketi(k: dict) -> str | None:
    """MADDE 742: bir defter satırındaki gun_getiri'nin AİT OLDUĞU gün. Defter 00:05 UTC'de yazılır ve `tarih`i yazıldığı
    gündür, getirisi ise BİR ÖNCEKİ günü kapsar (7 Kas tarihli satır = 6 Kas'ın sonucu). Zaman varsa (zaman − 1 sa)'in
    UTC günü, yoksa defter tarihi."""
    z = k.get("zaman")
    if z:
        try:
            return dt.datetime.fromtimestamp(int(z) - 3600, dt.timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError, TypeError):
            pass
    return k.get("tarih")


def _gelir_payi(onc: dict | None, k: dict) -> float:
    """MADDE 742: gelir_24s her satırda SON 24 SAATİ kapsar. Satırlar 24 sa'ten sık yazılırsa (kurulum günü, elle çalıştırma)
    pencereler üst üste biner ve toplam ÇİFT sayar. Satırın yalnız önceki satırdan bu yana geçen kısmı sayılır (oransal);
    ilk satırın penceresi başlangıçtan ÖNCEdir, sayılmaz."""
    if onc is None:
        return 0.0
    try:
        return max(0.0, min(1.0, (float(k["zaman"]) - float(onc["zaman"])) / 86400.0))
    except (KeyError, TypeError, ValueError):
        return 1.0


def ozet(defter: list[dict]) -> dict:
    """Seri + göstergeler. Getiri zinciri günlük getiriden (transferler zaten ayıklanmış). `tarih` = getirinin ait olduğu
    gün (madde 742); aynı güne düşen iki getiri (gün içi elle çalıştırma) tek günde birleşir."""
    seri, deg, kit, onc = [], 1.0, None, None
    for k in defter:
        g = k.get("gun_getiri")
        if g is not None:
            deg *= 1 + g
        kit = _kitap_ilerlet(kit, onc, k)
        pay = _gelir_payi(onc, k); onc = k
        gel = k.get("gelir_24s") or {}
        f, c = (gel.get("FUNDING_FEE") or 0) * pay, (gel.get("COMMISSION") or 0) * pay
        et = gun_etiketi(k)
        if g is not None and seri and seri[-1]["gun"] is not None and seri[-1]["tarih"] == et:
            s0 = seri[-1]
            s0.update(gun=(1 + s0["gun"]) * (1 + g) - 1, kitap=kit, deger=deg, funding=s0["funding"] + f, komisyon=s0["komisyon"] + c)
            continue
        seri.append({"tarih": et, "kitap": kit, "gun": g, "deger": deg, "funding": f, "komisyon": c})
    zirve, dd = 1.0, 0.0
    for s in seri:
        zirve = max(zirve, s["deger"]); dd = min(dd, s["deger"] / zirve - 1)
    gunler = [s for s in seri if s["gun"] is not None]

    def _pencere(n):
        # madde 742: n günden az veri varken "7 gün / 30 gün" toplamla aynı sayıyı gösterip yanıltmasın
        if len(gunler) < n:
            return None
        b = seri[max(0, len(seri) - 1 - n)]["deger"]
        return seri[-1]["deger"] / b - 1
    aylik = {}
    for s in gunler:
        a = s["tarih"][:7]; aylik[a] = (1 + aylik.get(a, 0.0)) * (1 + s["gun"]) - 1
    son = defter[-1] if defter else {}
    return {"seri": seri, "toplam": seri[-1]["deger"] - 1 if seri else None, "dd": dd, "g7": _pencere(7), "g30": _pencere(30),
            "bugun": gunler[-1]["gun"] if gunler else None, "son_gun_tarih": gunler[-1]["tarih"] if gunler else None,
            "gun_sayisi": len(gunler), "kitap": seri[-1]["kitap"] if seri else None,
            "aylik": aylik, "pozisyonlar": son.get("pozisyonlar", {}), "son_tarih": son.get("tarih"),
            "profil": son.get("profil"), "doz": son.get("doz"),
            "funding_top": sum(s["funding"] or 0 for s in seri), "komisyon_top": sum(s["komisyon"] or 0 for s in seri)}


PAKET_DIR = os.getenv("CARRY_PAKET_DIR", "/opt/carry-rapor/paket")
VARLIK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel_varlik")   # madde 740: simge + yazı tipi
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


ISLEM_GORUNTU_SN = 1200
"""MADDE 745: işlemden sonraki pozisyon görüntüsü en çok bu kadar sonra olabilir (carry_anlik 5 dk'da bir). Daha geçse
(geçmiş kaydı başlamadan önceki işlem ya da görüntü servisi aksadı) ortalama GÖSTERİLMEZ — yanlış (daha sonraki) değer yerine."""
_TUR_AD = {"GIRIS": "limit", "KOVALA": "limit", "PIYASA": "piyasa", "PIYASA_YEDEK": "piyasa", "TP": "kâr al",
           "KADEME": "kâr al kademe", "FELAKET": "felaket stop"}


def kapanis_kar(yon: str, adet: float, fiyat: float, once, sonra) -> dict | None:
    """MADDE 750: işlem mevcut pozisyonu (kısmen ya da tamamen) kapattıysa kapanan adet ve gerçekleşen kâr (komisyonsuz,
    ≈ Binance realizedPnl). Ortalama giriş: işlemden önceki görüntü (`once` = [t, adet, giriş]); yoksa küçültmede Binance
    ortalamayı değiştirmediği için sonraki görüntünün girişi. Pozisyon bilinmiyorsa None."""
    al = yon == "BUY"
    if once is not None and once[1] and once[2]:
        onceki, giris = float(once[1]), float(once[2])
    elif sonra is not None and sonra[1] and sonra[2] and ((al and sonra[1] < 0) or (not al and sonra[1] > 0)):
        onceki, giris = float(sonra[1]) + (-adet if al else adet), float(sonra[2])   # küçültme: önce = sonra ∓ adet
    else:
        return None
    if (onceki > 0) == al:                 # aynı yönde ekleme: kapanış yok
        return None
    kapanan = min(adet, abs(onceki))
    kar = kapanan * (fiyat - giris) * (1 if onceki > 0 else -1)
    return {"kapanan": round(kapanan, 8), "kapanis_kar": round(kar, 4), "tam": kapanan >= abs(onceki) * 0.999}


def islemler(klasor: str, gun: float = 7, simdi: float | None = None) -> dict:
    """MADDE 745: son `gun` günün DOLAN emirleri (emir defteri, SALT OKUNUR) + her işlemden sonra coinin pozisyonu ve
    ORTALAMA girişi (defter/anlik_poz.json: carry_anlik 5 dk'da bir, yalnız değişince yazar; ortalama Binance'in kendi
    entryPrice'ı). Dolum bilgisi henüz eşlenmemiş emir sayısı `bekleyen`de (carry_anlik birkaç dk içinde eşler)."""
    import bisect, sqlite3
    simdi = simdi or time.time(); out = {"liste": [], "bekleyen": 0}
    db = os.path.join(klasor, "defter", "carry.db")
    if not os.path.exists(db):
        return out
    try:
        with open(os.path.join(klasor, "defter", "anlik_poz.json"), encoding="utf-8") as f:
            gec = json.load(f).get("s") or {}
    except (OSError, ValueError, AttributeError):
        gec = {}
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        try:
            satir = c.execute("SELECT zaman, sembol, tur, yon, dolan, ort_fiyat, maker_adet, komisyon, kapanis, durum FROM emir "
                              "WHERE zaman>? ORDER BY zaman", (simdi - gun * 86400,)).fetchall()
        finally:
            c.close()
    except Exception:
        return out
    dolum_t: dict[str, list[float]] = {}   # madde 750: sembol başına dolum zamanları (önceki görüntü hâlâ geçerli mi?)
    for z, sem, tur, yon, dolan, ort, maker, kom, kap, durum in satir:
        if dolan and ort:
            dolum_t.setdefault(sem, []).append(float(kap or z))
    for z, sem, tur, yon, dolan, ort, maker, kom, kap, durum in satir:
        if not dolan or not ort:
            if durum is None and tur in ("GIRIS", "KOVALA", "PIYASA", "PIYASA_YEDEK") and simdi - z < 86400:
                out["bekleyen"] += 1
            continue
        t = float(kap or z)
        h = gec.get(sem) or []
        i = bisect.bisect_left([x[0] for x in h], t - 1)
        sonra = h[i] if i < len(h) else None
        if sonra is not None and sonra[0] - t > ISLEM_GORUNTU_SN:   # görüntü işlemden çok sonra: arada başka işlem olmuş olabilir
            sonra = None; k_eski = True
        else:
            k_eski = False
        k = {"t": int(t), "zaman": _yerel(t).strftime("%Y-%m-%d %H:%M"), "sembol": str(sem).removesuffix("USDT"),
             "tur": _TUR_AD.get(tur, tur), "yon": yon, "adet": float(dolan), "fiyat": float(ort),
             "usd": round(float(dolan) * float(ort), 2), "kom": None if kom is None else round(float(kom), 4),
             "maker": None if maker is None else bool(float(maker) >= 0.999 * float(dolan))}
        if k_eski or (not h and t < simdi - ISLEM_GORUNTU_SN):
            k["kayit_yok"] = True
        if sonra is not None:
            k.update({"poz_sonra": sonra[1], "ort_sonra": sonra[2] or None, "usd_sonra": round(abs(sonra[1]) * float(ort), 2)})
        once = h[i - 1] if i > 0 else None
        if once is not None and any(once[0] < x < t - 1 for x in dolum_t.get(sem, [])):
            once = None                    # görüntüyle bu işlem arasında başka dolum var: önceki pozisyon bilinmiyor
        kap_ = kapanis_kar(yon, float(dolan), float(ort), once, sonra)
        if kap_ is not None:
            k.update(kap_)
        # madde 751: işlemden ÖNCEKİ durum (önce → sonra satırı için). Görüntü yoksa ve sonraki pozisyon tam bu işlem kadarsa
        # pozisyon yeni açılmıştır (önce 0).
        if once is not None:
            k.update({"poz_once": once[1], "ort_once": once[2] or None, "usd_once": round(abs(once[1]) * float(ort), 2)})
        elif sonra is not None and abs(abs(sonra[1]) - float(dolan)) <= 1e-9 * max(1.0, float(dolan)):
            k.update({"poz_once": 0.0, "ort_once": None, "usd_once": 0.0})
        out["liste"].append(k)
    out["liste"].reverse()
    return out


def fundingler(klasor: str, gun: float = 7, simdi: float | None = None) -> list[dict]:
    """MADDE 749: funding ödemeleri (defter/funding_olay.json; carry_anlik 5 dk'da bir). Her ödeme anı (dakika) için
    demo hesaba yatan (d) ve gerçek Binance oranlarıyla olsaydı (g); coin coin. Yeniden eskiye."""
    simdi = simdi or time.time()
    try:
        with open(os.path.join(klasor, "defter", "funding_olay.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return []
    D, G = d.get("d") or {}, d.get("g") or {}
    out = []
    for t in sorted(set(D) | set(G), key=int, reverse=True):
        if int(t) / 1000 < simdi - gun * 86400:
            continue
        dm, gr = D.get(t) or {}, G.get(t) or {}
        coin = [{"s": s_.removesuffix("USDT"), "demo": dm.get(s_), "gercek": gr.get(s_)} for s_ in sorted(set(dm) | set(gr))]
        coin.sort(key=lambda c: -abs((c["demo"] or 0) if c["demo"] is not None else (c["gercek"] or 0)))
        out.append({"t": int(t) // 1000, "zaman": _yerel(int(t) / 1000).strftime("%Y-%m-%d %H:%M"),
                    "demo": round(sum(dm.values()), 4) if dm else None, "demo_n": len(dm),
                    "gercek": round(sum(gr.values()), 4) if gr else None, "gercek_n": len(gr), "coin": coin})
    return out


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


def gun_egri(klasor: str, simdi: float | None = None) -> dict | None:
    """MADDE 742: bugünün (00:00 UTC = 03:00 TR) kitap eğrisi — defter/anlik_gun.json (carry_anlik.py, 5 dk'da bir:
    özkaynak − başlangıçtan beri transfer). Değerler günün ilk noktasına göre $ fark. Kapanan işlemler, funding ve komisyon
    dahildir (eski eğri yalnız ŞU AN açık pozisyonları 03:00'ten beri tutulmuş sayıyordu: gün içinde açılanlar şişiyordu).
    Dosya yok / bozuk / başka güne ait ise None."""
    simdi = time.time() if simdi is None else simdi
    bas = int(simdi) // 86400 * 86400
    try:
        with open(os.path.join(klasor, "defter", "anlik_gun.json"), encoding="utf-8") as f:
            d = json.load(f)
        nok = [(int(t), float(v)) for t, v in d["nok"] if int(t) >= bas]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if d.get("gun") != dt.datetime.fromtimestamp(bas, dt.timezone.utc).strftime("%Y-%m-%d") or not nok:
        return None
    ref = nok[0][1]
    return {"bas": bas, "ilk": nok[0][0], "nok": [[t, round(v - ref, 4)] for t, v in nok]}


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
        gf = (an or {}).get("gercek_funding") or {}
        if gf.get("bas") == defter[0].get("zaman") and gf.get("toplam") is not None:   # madde 744: gerçek oranlarla olsaydı
            out["dokum"]["funding_gercek"] = round(float(gf["toplam"]), 2)
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


def gercek_gorunum(df: list[dict], o: dict, klasor: str) -> dict | None:
    """MADDE 748: demo kurulumda "gerçek funding ile" görünüm. Demo borsa funding'i KENDİ oranıyla öder (gerçekle ilgisiz);
    carry_anlik gerçek Binance oranlarıyla aynı pozisyonların funding'ini hesaplar (madde 744; gün kırılımı 748).
    Kitap / kâr: (gerçek − demo) funding farkı eklenir. Günlük getiri: o günün demo funding'i çıkar, gerçeği eklenir
    (yalnız gerçek gün kırılımı olan günler; olmayan gün değişmez, `duzeltilmeyen` sayılır). Gerçek veri yoksa None."""
    d = o.get("dokum") or {}
    if d.get("funding_gercek") is None or d.get("funding") is None:
        return None
    try:
        with open(os.path.join(klasor, "defter", "gercek_funding.json"), encoding="utf-8") as f:
            gun = json.load(f).get("gun") or {}
    except (OSError, ValueError, AttributeError):
        gun = {}
    fark = d["funding_gercek"] - d["funding"]
    # madde 759: iki geçiş. (1) gün kırılımı olan günlerin farkı ve demo funding toplamı; (2) kırılımı OLMAYAN günlere
    # kalan fark eşit dağıtılır — önceden bu kalan (ilk günler, ~10 $) "bugün"e yükleniyor, Geçmiş'te bugün şişiyordu.
    # Bugünün (son gün sonu kaydından sonraki) farkı = gerçek bugün − demo bugün; o kısım günlere dağıtılmaz.
    satir, onc, top_fark, demo_top, duz, duzm = [], None, 0.0, 0.0, 0, 0
    for k in df:
        g = k.get("gun_getiri"); bilgi = None
        if g is not None and onc is not None:
            et = gun_etiketi(k); taban = (onc.get("ozkaynak") or 0) * float(onc.get("sermaye_olcek", k.get("sermaye_olcek", 1.0)) or 1.0)
            demo_f = ((k.get("gelir_24s") or {}).get("FUNDING_FEE") or 0) * _gelir_payi(onc, k); demo_top += demo_f
            if taban > 0:
                if et in gun:
                    bilgi = ("d", gun[et] - demo_f, taban); top_fark += gun[et] - demo_f; duz += 1
                else:
                    bilgi = ("m", 0.0, taban); duzm += 1
        satir.append((k, bilgi)); onc = k
    son_et = gun_etiketi(df[-1]) if df else None
    bugun_fark = (sum(v_ for g_, v_ in gun.items() if son_et and g_ > son_et) - (d["funding"] - demo_top)) if df else 0.0
    kalan = fark - top_fark - bugun_fark
    pay = kalan / duzm if duzm else 0.0
    adj, fark_satir, birikim = [], [], 0.0
    for k, bilgi in satir:
        k2 = dict(k)
        if bilgi is not None:
            df_ = bilgi[1] if bilgi[0] == "d" else pay
            birikim += df_; k2["gun_getiri"] = k["gun_getiri"] + df_ / bilgi[2]
        fark_satir.append(birikim); adj.append(k2)
    v = ozet(adj)
    for s_, f_ in zip(v["seri"], fark_satir):   # kitap eğrisi de gerçek funding farkıyla
        if s_.get("kitap") is not None:
            s_["kitap"] = round(s_["kitap"] + f_, 4)
    out = {k: v[k] for k in ("seri", "toplam", "dd", "g7", "g30", "bugun", "aylik")}
    if o.get("kitap_canli") is not None:
        out["kitap_canli"] = round(o["kitap_canli"] + fark, 4)
    if o.get("kar_usd") is not None:
        out["kar_usd"] = round(o["kar_usd"] + fark, 2)
        out["kar_oran"] = round(out["kar_usd"] / o["kitap_bas"], 6) if o.get("kitap_bas") else None
    out.update(fark=round(fark, 2), duzeltilen=duz, duzeltilmeyen=duzm)
    return out


def baslangic_kesim(df: list[dict], olay: list[dict]) -> str | None:
    """MADDE 753: şu anki kurulumun başlangıcı (panel saatiyle 'YYYY-MM-DD HH:MM'). Defterin ilk satırından önceki SON
    'carry_bot başladı' olayı (yoksa ilk satırın zamanı). Bundan eski olay / işlem / funding (eski demo denemeleri,
    başka hesapla yapılmış kurulumlar) panelde gösterilmez."""
    if not df or not df[0].get("zaman"):
        return None
    ilk = _yerel(float(df[0]["zaman"])).strftime("%Y-%m-%d %H:%M")
    bas = [o["zaman"] for o in olay if o.get("tur") == "basla" and o.get("zaman") and o["zaman"] <= ilk]
    return max(bas) if bas else ilk


STOP_BAYAT_SN = 3 * 3600


def stop_oku(klasor: str, simdi: float | None = None) -> dict | None:
    """MADDE 753: koşullu stop durumu (carry_anlik saatte bir yazar: piyasa medyanı, long başına 24 sa). 3 saatten eskiyse bayat."""
    simdi = simdi or time.time()
    try:
        with open(os.path.join(klasor, "defter", "stop_durum.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not d.get("zaman"):
        return None
    d["saat_ad"] = _yerel(d["zaman"]).strftime("%H:%M"); d["bayat"] = simdi - d["zaman"] > STOP_BAYAT_SN
    d["coin"] = {k.removesuffix("USDT"): v for k, v in (d.get("coin") or {}).items()}
    return d


def coin_ozet(klasor: str, an: dict | None) -> list[dict] | None:
    """MADDE 753: coin başına başlangıçtan beri kâr / zarar — kapanan (REALIZED_PNL), funding, komisyon (borsa gelir kayıtları,
    carry_anlik gelir_birikim 'coin') + şu an açık pozisyonun gerçekleşmemiş kârı. Kayıt yoksa None."""
    try:
        with open(os.path.join(klasor, "defter", "gelir_birikim.json"), encoding="utf-8") as f:
            c = json.load(f).get("coin")
    except (OSError, ValueError, AttributeError):
        return None
    if c is None:
        return None
    poz = (an or {}).get("pozisyonlar") or {}
    out = []
    for s_ in set(c) | set(poz):
        g = c.get(s_) or {}; p = poz.get(s_) or {}
        k = {"s": s_.removesuffix("USDT"), "kapanan": round(g.get("REALIZED_PNL", 0.0), 4), "funding": round(g.get("FUNDING_FEE", 0.0), 4),
             "komisyon": round(g.get("COMMISSION", 0.0), 4), "acik": round(float(p.get("gerceklesmemis") or 0.0), 4),
             "yon": p.get("yon")}
        k["toplam"] = round(k["kapanan"] + k["funding"] + k["komisyon"] + k["acik"], 4)
        out.append(k)
    return sorted(out, key=lambda x: x["toplam"])


def karar_kayma(klasor: str, gun: float = 30, simdi: float | None = None) -> dict | None:
    """MADDE 753: giriş dolumlarının KARAR fiyatına (turun ilk GTX emrindeki referans) göre kayması, bp (+ = aleyhte).
    İcra özetindeki kayma her emri kendi gönderim fiyatıyla kıyaslar; kovalama / piyasaya düşme sırasında fiyatın kaçması
    orada görünmez, burada görünür. Tutar ağırlıklı ortalama; yol başına (ilk deneme / kovala / piyasa) ayrıca."""
    import sqlite3
    db = os.path.join(klasor, "defter", "carry.db")
    if not os.path.exists(db):
        return None
    simdi = simdi or time.time()
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        try:
            R = c.execute("SELECT zaman, sembol, tur, yon, ref_fiyat, ort_fiyat, dolan FROM emir WHERE tur IN "
                          "('GIRIS','KOVALA','PIYASA','PIYASA_YEDEK') AND zaman>? ORDER BY id", (simdi - gun * 86400 - 3600,)).fetchall()
        finally:
            c.close()
    except Exception:
        return None
    ilk, yol = {}, {"GIRIS": [], "KOVALA": [], "PIYASA": []}
    for z, sem, tur, yon, ref, ort, dol in R:
        if tur == "GIRIS" and ref:
            ilk[(sem, yon)] = (z, float(ref))
        if dol and ort and (sem, yon) in ilk and z >= simdi - gun * 86400:
            z0, r0 = ilk[(sem, yon)]
            if z - z0 < 1500 and r0 > 0:
                bp = (1 if yon == "BUY" else -1) * (float(ort) / r0 - 1) * 1e4
                yol["PIYASA" if tur.startswith("PIYASA") else tur].append((bp, float(dol) * float(ort)))
    hep = [x for v in yol.values() for x in v]
    if not hep:
        return None
    ag = lambda L: round(sum(b * u for b, u in L) / sum(u for _, u in L), 1) if L and sum(u for _, u in L) > 0 else None
    return {"bp": ag(hep), "n": len(hep), **{k.lower(): ag(v) for k, v in yol.items()}, **{k.lower() + "_n": len(v) for k, v in yol.items()}}


def veri(klasorler: list[str], servis: bool = True) -> dict:
    out = []
    for kl in klasorler:
        e = _env(kl); b = os.path.basename(kl.rstrip("/"))
        ad = e.get("CARRY_BILDIRIM_AD") or (b[len("carry-"):] if b.startswith("carry-") else "ana")
        df = defter_oku(kl); o = ozet(df)
        o.update({"ad": ad, "mod": e.get("BINANCE_MODE", "demo"), "servis": servis_durumu(kl) if servis else "—",
                  "olaylar": olaylar(kl), "islemler": islemler(kl), "fundingler": fundingler(kl), "icra": icra(kl), "dilim": sonraki_dilim(kl, e),
                  "ayar": etkin_ayar(kl), "hedef": kar_hedefleri(e), "gun_egri": gun_egri(kl)})
        if o["ayar"] is not None:   # madde 742: koşullu stopun coin eşiği (carry_bot CARRY_LONG_24S, varsayılan 0,45)
            try:
                o["ayar"]["coin_esik"] = float(e.get("CARRY_LONG_24S") or 0.45)
            except ValueError:
                o["ayar"]["coin_esik"] = 0.45
        kes = baslangic_kesim(df, o["olaylar"])   # madde 753: eski kurulumların olayları gösterilmez
        if kes:
            o["baslangic"] = kes
            o["olaylar"] = [x for x in o["olaylar"] if (x.get("zaman") or "") >= kes]
            o["islemler"]["liste"] = [x for x in o["islemler"]["liste"] if x["zaman"] >= kes]
            o["fundingler"] = [x for x in o["fundingler"] if x["zaman"] >= kes]
        o["stop_durum"] = stop_oku(kl)
        kk = karar_kayma(kl)
        if kk is not None and o.get("icra"):
            o["icra"]["karar"] = kk
        an = anlik_oku(kl)
        o["coin_ozet"] = coin_ozet(kl, an)
        o.update(hesap_ozet(df, an))
        if an is not None:   # madde 728: canlı pozisyon tablosu
            o.update({"pozisyonlar": an["pozisyonlar"], "poz_kaynak": "canlı",
                      "poz_zaman": _yerel(an["zaman"]).strftime("%H:%M"),
                      "gerceklesmemis": an.get("gerceklesmemis_top"), "demo_funding": an.get("demo_funding")})
        else:
            o.update({"poz_kaynak": "günlük", "poz_zaman": o.get("son_tarih"), "gerceklesmemis": None})
        if o["mod"] == "demo":
            o["gercek"] = gercek_gorunum(df, o, kl)
        out.append(o)
    return {"kurulumlar": out, "paketler": paketler(), "uretim": _yerel().strftime("%Y-%m-%d %H:%M")}


SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carry Panel</title>
<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#000000"><meta name="apple-mobile-web-app-status-bar-style" content="black">
<link rel="icon" href="ikon-192.png"><link rel="apple-touch-icon" href="ikon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Carry">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
@font-face{font-family:Inter;font-style:normal;font-weight:400 800;font-display:swap;src:url(font/inter-latin-ext.woff2) format("woff2");
  unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:Inter;font-style:normal;font-weight:400 800;font-display:swap;src:url(font/inter-latin.woff2) format("woff2");
  unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
:root{--bg:#f3f4f6;--kart:#fff;--kart2:#f3f4f7;--yazi:#111318;--soluk:#6b7280;--cizgi:#e5e7eb;--art:#0f9d58;--eks:#d93025;--vurgu:#2563eb;--uyari:#c2410c;--mor:#7c3aed;--ust:rgba(243,244,246,.86)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0F1115;--kart:#15181D;--kart2:#1C2027;--yazi:#E8EAED;--soluk:#9AA0A9;--cizgi:#22262E;--art:#3DD68C;--eks:#F2675F;--vurgu:#7AA7FF;--uyari:#F5A524;--mor:#B197FC;--ust:rgba(15,17,21,.86)}}
:root[data-theme="dark"]{--bg:#0F1115;--kart:#15181D;--kart2:#1C2027;--yazi:#E8EAED;--soluk:#9AA0A9;--cizgi:#22262E;--art:#3DD68C;--eks:#F2675F;--vurgu:#7AA7FF;--uyari:#F5A524;--mor:#B197FC;--ust:rgba(15,17,21,.86)}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--yazi);font:14px/1.45 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-feature-settings:"cv11","ss01";-webkit-tap-highlight-color:transparent;overscroll-behavior-y:contain}
.kap{max-width:1180px;margin:0 auto;padding:0 14px 96px}
header{position:sticky;top:0;z-index:6;display:flex;gap:10px;align-items:center;justify-content:space-between;padding:12px 0 10px;margin:0 -14px 6px;padding-left:14px;padding-right:14px;
  background:var(--ust);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);transition:padding .2s}
header.kucuk{padding-top:8px;padding-bottom:8px;border-bottom:1px solid var(--cizgi)}
h1{font-size:17px;margin:0;letter-spacing:-.2px;font-weight:750;display:flex;align-items:center;gap:8px}h1 img{width:22px;height:22px;border-radius:6px}
.k{color:var(--soluk);font-size:12px}
#ustkitap{display:none;font-weight:700;font-variant-numeric:tabular-nums;font-size:15px}header.kucuk #ustkitap{display:block}header.kucuk #alt{display:none}
.sag{display:flex;align-items:center;gap:8px}
.tema{border:1px solid var(--cizgi);background:var(--kart);color:var(--soluk);border-radius:999px;width:30px;height:30px;font-size:14px;cursor:pointer;display:grid;place-items:center;padding:0}
.canli{font-size:12px;color:var(--soluk);display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.canli i{width:8px;height:8px;border-radius:50%;background:var(--soluk);display:inline-block}
.canli.on{color:var(--art)}.canli.on i{background:var(--art);animation:nabiz 1.6s infinite}
@keyframes nabiz{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--art) 60%,transparent)}70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}
.sekme{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}.sekme:empty{display:none}.sekme button{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);
padding:5px 12px;border-radius:999px;cursor:pointer;font:inherit;font-size:13px}.sekme button.on{border-color:var(--vurgu);color:var(--vurgu);font-weight:600}
nav.alt{display:flex;gap:4px;background:var(--kart);border:1px solid var(--cizgi);border-radius:16px;padding:4px;margin-bottom:14px}
nav.alt button{flex:1;border:0;background:none;color:var(--soluk);font:inherit;font-size:13px;font-weight:650;padding:8px 4px;border-radius:12px;cursor:pointer;transition:background .15s,color .15s}
nav.alt button.on{background:color-mix(in srgb,var(--vurgu) 16%,transparent);color:var(--vurgu)}
nav.alt button{display:flex;align-items:center;justify-content:center;gap:7px;position:relative}nav.alt svg{width:18px;height:18px;flex:none}
nav.alt .nok{position:absolute;top:6px;right:calc(50% - 22px);width:8px;height:8px;border-radius:50%;background:var(--uyari)}
@media(max-width:820px){nav.alt{position:fixed;left:0;right:0;bottom:0;margin:0;z-index:7;border-radius:0;border:0;border-top:1px solid var(--cizgi);
  padding:6px 4px calc(6px + env(safe-area-inset-bottom));background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
  nav.alt button{flex-direction:column;gap:3px;font-size:11px;font-weight:550;padding:6px 2px}nav.alt button.on{background:none;color:var(--yazi)}nav.alt svg{width:22px;height:22px}
  nav.alt .nok{top:3px;right:calc(50% - 16px)}}
@media(min-width:821px){nav.alt{position:sticky;top:58px;z-index:5}}
#cek{height:0;overflow:hidden;display:flex;align-items:center;justify-content:center;color:var(--soluk);font-size:12px;transition:height .2s}
#icerik{transition:opacity .15s}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:16px;padding:14px;margin-bottom:12px}
.kart h2{font-size:13px;margin:0 0 10px;color:var(--soluk);font-weight:650;display:flex;flex-wrap:wrap;gap:6px;align-items:baseline}
.art{color:var(--art)}.eks{color:var(--eks)}
.rz{display:inline-block;padding:1px 7px;border-radius:7px;font-variant-numeric:tabular-nums;background:color-mix(in srgb,currentColor 14%,transparent)}
.iki{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}@media(max-width:820px){.iki{grid-template-columns:1fr}}.iki>.kart{margin-bottom:0}
.genis{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:12px;align-items:start}
.ozet .ust{display:flex;justify-content:space-between;align-items:center}
.ozet .buyuk{font-size:34px;font-weight:750;font-variant-numeric:tabular-nums;letter-spacing:-1px;margin:2px 0 2px;line-height:1.15}
.ozet .kar{font-size:14px;font-weight:650}
.mod{display:inline-flex;background:var(--kart2);border-radius:9px;padding:2px;gap:2px}.mod button{border:0;background:none;color:var(--soluk);font:inherit;font-size:11.5px;font-weight:650;padding:3px 9px;border-radius:7px;cursor:pointer}
.mod button.on{background:var(--kart);color:var(--yazi);box-shadow:0 1px 2px rgba(0,0,0,.25)}
.egri{margin:10px 0 2px}.egri .bl{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;color:var(--soluk)}
.egri svg{width:100%;height:70px;display:block;margin-top:4px;overflow:visible}
.eksen{display:flex;justify-content:space-between;font-size:10px;color:var(--soluk);margin-top:2px;font-variant-numeric:tabular-nums}
.cipler{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}
.cip{background:var(--kart2);border-radius:11px;padding:8px 9px;min-width:0}
.cip .e{font-size:11px;color:var(--soluk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.cip .d{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cip .k{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.bilgi{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:6px}.bilgi .cip .d{font-size:14px}
.halkali{display:flex;align-items:center;gap:8px}.halkali svg{flex:none;width:34px;height:34px}
@media(max-width:460px){.cipler{grid-template-columns:repeat(2,1fr)}.bilgi{grid-template-columns:1fr 1fr}.bilgi .cip:first-child{grid-column:1/3}}
.durum{font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--cizgi);font-weight:650}.durum.ok{color:var(--art);border-color:color-mix(in srgb,var(--art) 50%,transparent)}.durum.yok{color:var(--eks);border-color:var(--eks)}
.cubuk{display:flex;height:8px;border-radius:99px;overflow:hidden;background:var(--kart2);margin:2px 0 10px;gap:2px}
.cubuk span{display:block;height:100%;border-radius:2px;transition:width .4s}
.dk{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:9px 0;border-top:1px solid var(--cizgi);cursor:pointer;font-variant-numeric:tabular-nums}
.dk .n{width:9px;height:9px;border-radius:3px;flex:none}.dk .a{flex:1}.dk .v{font-weight:700}
.dk .ac{display:none;flex-basis:100%;color:var(--soluk);font-size:12px;padding:0 0 0 17px}.dk.acik .ac{display:block}
.dk .ok{color:var(--soluk);font-size:11px;display:inline-block;transition:transform .15s}.dk.acik .ok{transform:rotate(90deg)}
.dk.top{cursor:default;font-weight:750}
.dk.alt{border-top:0;padding-top:0;color:var(--soluk);font-size:12.5px}.dk.alt .a{padding-left:17px}.dk.alt .v{font-weight:650}
.isi{position:relative;height:190px;border-radius:12px;overflow:hidden}
.isi div{position:absolute;padding:6px 7px;overflow:hidden;border:2px solid var(--kart);border-radius:9px;display:flex;flex-direction:column;justify-content:space-between;transition:background .4s}
.isi b{font-size:12.5px;font-weight:750;white-space:nowrap}.isi span{font-size:11.5px;font-weight:650;font-variant-numeric:tabular-nums;white-space:nowrap}
.isi small{font-size:10px;opacity:.75;white-space:nowrap}
.isi div.kk{flex-direction:row;align-items:center;gap:5px;justify-content:flex-start;padding:2px 6px}.isi div.kk b,.isi div.kk span{font-size:11px}
.grafik{position:relative;height:190px}
.denge{margin:2px 0 12px}.denge .c{display:flex;height:10px;border-radius:99px;overflow:hidden;gap:2px}
.denge .c span{display:block;height:100%;transition:width .4s}.denge .t{display:flex;justify-content:space-between;font-size:12px;margin-top:5px;font-variant-numeric:tabular-nums}
.taraf{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;color:var(--soluk);font-weight:650;margin:4px 2px 8px;gap:8px}
.taraf b{font-variant-numeric:tabular-nums;font-weight:650}
.kutular{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:8px;margin-bottom:12px}
.kutu{background:var(--kart);border:1px solid var(--cizgi);border-left:3px solid var(--vurgu);border-radius:13px;padding:10px 10px 8px;min-width:0}
.kutu.S{border-left-color:var(--uyari)}
.kutu .ad{font-weight:750;font-size:15px;display:flex;justify-content:space-between;align-items:baseline;gap:6px}
.kutu .f{font-size:18px;font-weight:650;font-variant-numeric:tabular-nums;margin-top:2px;border-radius:5px;padding:0 3px;margin-left:-3px;display:inline-block;letter-spacing:-.3px}
.kutu .gr{font-size:11px;color:var(--soluk);font-variant-numeric:tabular-nums;display:flex;justify-content:space-between;gap:4px}
.kutu .y{font-size:14px;font-weight:750;margin-top:4px;display:flex;align-items:center;gap:5px;flex-wrap:wrap}.kutu .y small{font-size:11px;font-weight:600;font-variant-numeric:tabular-nums}
.kutu svg{width:100%;height:64px;display:block;margin-top:8px;overflow:visible}
.uyr{color:var(--uyari)}
/* MADDE 757: D tasarımı — Özet */
.dozet{padding:18px}.dhero{padding:6px 4px 14px}
.dcumle{font-size:14px;color:var(--soluk);display:flex;align-items:center;gap:7px;flex-wrap:wrap}.dcumle .uyr{font-weight:600}
.dnok{width:8px;height:8px;border-radius:50%;background:var(--art);box-shadow:0 0 0 4px color-mix(in srgb,var(--art) 18%,transparent)}.dnok.yok{background:var(--eks);box-shadow:none}
.dgr{margin-top:18px}.dgr .mod{display:flex;width:max-content;margin-left:auto}.dgr .mod button{font-size:12px;padding:4px 12px}.dgr svg{width:100%;height:84px;display:block;margin-top:8px;overflow:visible}
.dnh{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}.dnh .dnk{margin:0}
.fgk{display:inline-flex;align-items:center;background:var(--kart2);border-radius:8px;padding:2px;gap:1px}
.fgk button{border:0;background:none;color:var(--soluk);font:inherit;font-size:11px;font-weight:600;padding:3px 8px;border-radius:6px;cursor:pointer}.fgk button.on{background:var(--kart);color:var(--yazi)}
.fgk .fgi{padding:3px 6px}.fgacik{flex-basis:100%;font-size:12px;color:var(--soluk);line-height:1.45;margin:-4px 0 10px}
.dikili{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.dikili .kart{margin-bottom:12px;padding:12px 14px}.dkv{font-size:17px;font-weight:650;margin:3px 0 2px;font-variant-numeric:tabular-nums}.dkv .k{font-weight:500;margin-left:4px}
.dbuyuk{margin-top:10px;font-size:44px;font-weight:700;letter-spacing:-1.6px;line-height:1.05;margin-top:2px;font-variant-numeric:tabular-nums}
.dalt{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
.dozet .mod button{font-size:12px;padding:4px 11px}
.ddk{margin-bottom:12px;border-radius:16px;padding:12px 14px;border:1px solid;cursor:default}.ddk[role=button]{cursor:pointer}
.ddk.uyari{background:color-mix(in srgb,var(--uyari) 9%,var(--kart));border-color:color-mix(in srgb,var(--uyari) 30%,transparent)}
.ddk.eks{background:color-mix(in srgb,var(--eks) 10%,var(--kart));border-color:color-mix(in srgb,var(--eks) 35%,transparent)}
.ddb{display:flex;justify-content:space-between;align-items:center;font-size:13.5px}.ddk.uyari b{color:var(--uyari)}.ddk.eks b{color:var(--eks)}
.ddm{font-size:12.5px;margin-top:4px;line-height:1.45;opacity:.85}
.dnerden{padding:14px}.dnk{font-size:12.5px;color:var(--soluk);font-weight:600}
.dnb{display:flex;height:10px;border-radius:99px;overflow:hidden;gap:2px}.dnb span{display:block;height:100%}
.dng{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));row-gap:6px;column-gap:14px;margin-top:10px;font-size:12.5px;font-variant-numeric:tabular-nums}
.dng>span{display:flex;justify-content:space-between;gap:6px}.dng b{white-space:nowrap}.dng i{display:inline-block;width:8px;height:8px;border-radius:3px;margin-right:6px}
.dsira{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-size:12.5px;color:var(--soluk)}.dsira b{color:var(--yazi);font-variant-numeric:tabular-nums}
/* MADDE 757: D tasarımı — Pozisyonlar ve ayrıntı sayfası */
.dpoz{padding:18px}.dpb{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}.dpb b{font-size:13.5px;font-variant-numeric:tabular-nums}
.dfil{display:flex;align-items:center;gap:8px;margin:14px 0 4px}.dsir{margin-left:auto;height:36px;padding:0 12px;border-radius:10px;border:1px solid var(--cizgi);background:none;color:var(--yazi);font:inherit;font-size:12.5px;font-weight:600;cursor:pointer}
.dbol{display:flex;justify-content:space-between;font-size:11.5px;color:var(--soluk);letter-spacing:.3px;font-weight:600;padding:16px 2px 6px;font-variant-numeric:tabular-nums}
.drow{display:flex;align-items:center;gap:12px;padding:10px 2px;border-top:1px solid var(--cizgi);cursor:pointer;-webkit-user-select:none;user-select:none}.dlis .drow:first-child{border-top:0}
.drow:active{background:var(--kart2)}.drow .dc{flex:1;min-width:0}.drow .da{display:flex;align-items:center;gap:6px}.drow .da b{font-size:15px;font-weight:650}
.drow .du{font-size:12px;color:var(--soluk);margin-top:2px;font-variant-numeric:tabular-nums}.dsp{width:60px;height:24px;flex:none;overflow:visible}
.drow .dv{text-align:right;width:92px;flex:none;font-variant-numeric:tabular-nums}.drow .dv b{display:block;font-size:14.5px;font-weight:650}.drow .dv span{font-size:12px}
.dst{font-size:10.5px;font-weight:650;color:var(--uyari);background:color-mix(in srgb,var(--uyari) 14%,transparent);border-radius:6px;padding:1px 6px;white-space:nowrap}
.dst.e{color:var(--eks);background:color-mix(in srgb,var(--eks) 14%,transparent)}.dst.l{color:var(--vurgu);background:none;border:1px solid color-mix(in srgb,var(--vurgu) 40%,transparent)}.dst.s{color:var(--uyari);background:none;border:1px solid color-mix(in srgb,var(--uyari) 40%,transparent)}
#sheet{position:fixed;inset:0;z-index:20}.shb{position:absolute;inset:0;background:rgba(0,0,0,.5)}
.shp{position:absolute;left:0;right:0;bottom:0;max-height:88vh;overflow:auto;background:var(--kart);border-radius:24px 24px 0 0;padding:10px 20px calc(20px + env(safe-area-inset-bottom));box-shadow:0 -12px 40px rgba(0,0,0,.4);max-width:600px;margin:0 auto;animation:shy .22s ease-out}
@keyframes shy{from{transform:translateY(40px);opacity:.4}to{transform:none;opacity:1}}
.shh{width:40px;height:5px;border-radius:99px;background:var(--cizgi);margin:0 auto 14px}.shu{display:flex;justify-content:space-between;align-items:flex-start}
.shf{font-size:30px;font-weight:700;letter-spacing:-.5px;margin-top:4px;font-variant-numeric:tabular-nums}
.shx{width:38px;height:38px;border-radius:50%;border:0;background:var(--kart2);color:var(--yazi);font-size:15px;cursor:pointer;flex:none}
.shg{margin-top:12px}.shg svg{width:100%;height:110px;display:block;overflow:visible}
.shkg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}.shk{background:var(--kart2);border-radius:14px;padding:10px 12px}
.shd{font-size:15px;font-weight:650;margin-top:2px;font-variant-numeric:tabular-nums}
.shs{background:var(--kart2);border-radius:14px;padding:12px;margin-top:8px}.shr{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;font-variant-numeric:tabular-nums}
.shc{height:6px;border-radius:99px;background:var(--cizgi);margin-top:8px;overflow:hidden}.shc span{display:block;height:100%;border-radius:99px}
.shn{font-size:13px;line-height:1.5;margin:12px 0 0;opacity:.9}
/* MADDE 757: D tasarımı — Olaylar */
.dolay{padding:18px}.ofil{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
.ofil button{height:32px;padding:0 12px;border-radius:99px;border:1px solid var(--cizgi);background:none;color:var(--yazi);font:inherit;font-size:12.5px;font-weight:600;cursor:pointer;opacity:.85}
.ofil button.on{background:var(--yazi);color:var(--bg);border-color:var(--yazi);opacity:1}
.ogun{font-size:11.5px;font-weight:650;color:var(--soluk);letter-spacing:.5px;margin:20px 0 6px}
.okart{background:var(--kart2);border-radius:16px;overflow:hidden}.orow{display:flex;gap:12px;padding:11px 14px;border-top:1px solid var(--cizgi)}.okart .orow:first-child{border-top:0}
.onk{width:8px;height:8px;border-radius:50%;margin-top:6px;flex:none}.om{flex:1;min-width:0}
.ob{display:flex;justify-content:space-between;gap:8px;font-size:14px;font-weight:600}.oz{font-size:12px;color:var(--soluk);font-weight:500;flex:none;font-variant-numeric:tabular-nums}
.oa{font-size:12.5px;color:var(--soluk);margin-top:2px;line-height:1.4;font-variant-numeric:tabular-nums}
/* MADDE 756: sade geçmiş */
.gsade{padding:18px 18px 6px}.gsade .n{font-variant-numeric:tabular-nums}.gust{display:flex;justify-content:space-between;align-items:center}
.gb{font-size:22px;font-weight:650;letter-spacing:-.4px}
.gdon{display:flex;gap:2px;background:var(--kart2);border-radius:99px;padding:3px}
.gdon button{height:30px;padding:0 13px;border-radius:99px;border:0;background:none;color:var(--soluk);font:inherit;font-size:12.5px;font-weight:550;cursor:pointer}
.gdon button.on{background:var(--yazi);color:var(--bg);font-weight:650}
.gk{font-size:13px;color:var(--soluk);margin-top:26px}
.gt{font-size:50px;font-weight:650;letter-spacing:-2px;line-height:1.05;margin-top:6px}.gt small{font-size:26px;color:var(--soluk);letter-spacing:-.5px}
.go{font-size:14px;margin-top:6px}
.gcub{position:relative;display:flex;gap:10px;margin-top:28px}.gcub>b{position:absolute;left:0;right:0;height:1px;background:var(--cizgi)}
.gc{flex:1;position:relative;min-width:0}.gc i{position:absolute;left:12%;right:12%;border-radius:7px;box-sizing:border-box}
.gc .ge{position:absolute;left:-6px;right:-6px;text-align:center;font-size:11px;font-weight:650;white-space:nowrap}
.galt{display:flex;gap:10px;margin-top:8px}.galt span{flex:1;text-align:center;font-size:11.5px;color:var(--soluk);min-width:0;white-space:nowrap}.galt .bg{color:var(--yazi)}
.gliste{margin-top:22px}.gs{display:flex;justify-content:space-between;align-items:center;padding:13px 0;border-top:1px solid var(--cizgi)}
.ga{font-size:15px;font-weight:500}.gn{font-size:12px;color:var(--soluk);margin-top:2px}.gv{font-size:15px;font-weight:650}
.gayr{width:100%;text-align:left;background:none;border:0;color:var(--yazi);font:inherit;font-size:14px;font-weight:600;padding:14px;cursor:pointer}
/* MADDE 754: mobil — sıkı pozisyon listesi (dokununca ayrıntı) */
.liste{border:1px solid var(--cizgi);border-radius:13px;overflow:hidden;margin-bottom:12px;background:var(--kart)}
.sat{border-top:1px solid var(--cizgi);border-left:3px solid var(--vurgu)}.sat:first-child{border-top:0}.sat.S{border-left-color:var(--uyari)}
.sat .ust{display:grid;grid-template-columns:minmax(0,1fr) auto 70px 64px;align-items:center;gap:8px;padding:11px 10px 11px 9px;cursor:pointer;font-variant-numeric:tabular-nums;-webkit-user-select:none;user-select:none}
.sat .ust .c{display:flex;align-items:center;gap:6px;min-width:0}.sat .ust b{font-size:14.5px;font-weight:750;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sat .ust .yb{font-size:10px;font-weight:700;color:var(--soluk);border:1px solid var(--cizgi);border-radius:5px;padding:0 4px;line-height:15px}
.sat .ust .w{font-size:11px;font-weight:800;color:#fff;background:var(--uyari);border-radius:5px;padding:0 4px;line-height:15px}.sat .ust .w.e{background:var(--eks)}
.sat .ust .u{font-size:12px;color:var(--soluk);text-align:right;white-space:nowrap}
.sat .ust .p{text-align:right;font-weight:750;font-size:13px;white-space:nowrap}.sat .ust .g{text-align:right;font-size:12.5px;font-weight:650;white-space:nowrap}
.sat .ust .ok2{display:none}.sat.acik{background:var(--kart2)}
.sat .det{padding:0 10px 11px 9px}.sat .det .f{font-size:17px;font-weight:650;font-variant-numeric:tabular-nums;letter-spacing:-.3px}
.sat .det .gr{font-size:11.5px;color:var(--soluk);font-variant-numeric:tabular-nums;display:flex;justify-content:space-between;gap:6px;margin-top:1px}
.sat .det svg{width:100%;height:90px;display:block;margin-top:8px;overflow:visible}
.sat .det .fund,.sat .det .hedef .t{white-space:normal;font-size:11.5px}
.fgac{cursor:pointer;color:var(--vurgu)}.fgacik{flex-basis:100%;font-size:12px;color:var(--soluk);line-height:1.4}
@media(max-width:699px){.isi{height:230px}.coin td,.coin th{padding:6px 4px;font-size:12px;white-space:nowrap}.coin td:nth-child(4){display:none}
  .coin .yon{font-size:10px;color:var(--soluk);font-weight:700;margin-left:4px}}
@media(min-width:700px){.coin .yon{font-size:11px;color:var(--soluk);margin-left:4px}}.takvim .g.canlig{outline:1.5px dashed var(--vurgu);outline-offset:-2px}
.fund{font-size:10.5px;margin-top:6px;font-variant-numeric:tabular-nums;color:var(--soluk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hedef{margin-top:6px}.hedef .c{height:4px;border-radius:9px;background:var(--kart2);overflow:hidden}.hedef .c span{display:block;height:100%;background:var(--art);border-radius:9px;transition:width .4s}
.hedef .t{font-size:10.5px;color:var(--soluk);margin-top:3px;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.yukari{animation:yk .9s ease-out}.asagi{animation:as .9s ease-out}
@keyframes yk{0%{background:color-mix(in srgb,var(--art) 45%,transparent)}100%{background:transparent}}
@keyframes as{0%{background:color-mix(in srgb,var(--eks) 45%,transparent)}100%{background:transparent}}
.uc{animation:uc 1.8s ease-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes uc{0%{opacity:.55;transform:scale(1)}100%{opacity:0;transform:scale(3.2)}}
.iskelet{position:relative;overflow:hidden;background:var(--kart2);border-radius:10px}
.iskelet::after{content:"";position:absolute;inset:0;transform:translateX(-100%);background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--yazi) 7%,transparent),transparent);animation:parla 1.3s infinite}
@keyframes parla{100%{transform:translateX(100%)}}
.grbekle{height:64px;margin-top:8px;display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--soluk)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}td,th{padding:6px;border-bottom:1px solid var(--cizgi);text-align:right;font-size:13px}
th{color:var(--soluk);font-weight:500}td.l,th.l{text-align:left}.tablo{overflow-x:auto}tr:last-child td{border-bottom:0}
.zc{position:relative;padding-left:4px}
.zc .gun{font-size:12px;font-weight:700;color:var(--soluk);margin:12px 0 6px;text-transform:uppercase;letter-spacing:.5px}.zc .gun:first-child{margin-top:0}
.zo{display:flex;gap:10px;position:relative;padding:0 0 12px}
.zo::before{content:"";position:absolute;left:12px;top:26px;bottom:0;width:2px;background:var(--cizgi)}.zo:last-child::before{display:none}
.zo .i{flex:none;width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:800;color:#fff;z-index:1}
.zo .m{font-size:13px;min-width:0;padding-top:3px}.zo .z{color:var(--soluk);font-size:11.5px;margin-top:1px}
.i-stop,.i-hata{background:var(--eks)}.i-delist,.i-saglik,.i-uyari{background:var(--uyari)}.i-ayar{background:var(--mor)}.i-basla{background:var(--vurgu)}
.i-tp,.i-funding{background:var(--art)}.i-tur{background:var(--soluk)}.i-islem{background:var(--vurgu)}
.isl{margin-top:6px}.isl .ac{color:var(--vurgu);font-size:12px;cursor:pointer;user-select:none}
.isl table{width:100%;border-collapse:collapse;font-size:12px;margin-top:4px;font-variant-numeric:tabular-nums}
.isl td{text-align:left;padding:4px 6px 4px 0;border-top:1px solid var(--cizgi);vertical-align:top}.isl td.r{text-align:right;white-space:nowrap}
.isl .s{color:var(--soluk);font-size:11px}.i-stop_tut{background:color-mix(in srgb,var(--eks) 40%,var(--kart2))}
.zo.hata .m>div:first-child{color:var(--eks)}
.bos{color:var(--soluk);padding:18px 0;text-align:center}
.takvim{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}
.takvim .bas{font-size:11px;color:var(--soluk);text-align:center;padding-bottom:2px}
.takvim .g{border-radius:9px;padding:5px 4px 6px;min-height:50px;border:1px solid var(--cizgi);font-variant-numeric:tabular-nums;text-align:center;overflow:hidden}
.takvim .g .n{font-size:11px;color:var(--soluk);text-align:left;line-height:1}
.takvim .g .v{font-size:12.5px;font-weight:700;margin-top:4px;white-space:nowrap}
.takvim .g.bosg{border:none}.takvim .g.yok{opacity:.3}.takvim .g.yok .v{visibility:hidden}
.takvim .g.hp,.yil i.hp{background:color-mix(in srgb,var(--art) var(--p),transparent);border-color:transparent}
.takvim .g.hn,.yil i.hn{background:color-mix(in srgb,var(--eks) var(--p),transparent);border-color:transparent}
@media(max-width:520px){.takvim .g{min-height:42px;padding:4px 2px}.takvim .g .v{font-size:10.5px}}
.aygez{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}
.aygez button{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);border-radius:9px;padding:2px 11px;cursor:pointer;font:inherit}
.aygez button:disabled{opacity:.35;cursor:default}.aygez b{font-size:14px}
.yil{overflow-x:auto;padding-bottom:4px}.yil .ic{display:grid;grid-template-rows:repeat(7,9px);grid-auto-flow:column;grid-auto-columns:9px;gap:2px;width:max-content}
.yil i{display:block;border-radius:2px;background:var(--kart2)}.yil i.x{visibility:hidden}
.bekle{color:var(--soluk);font-size:13px;text-align:center;padding:26px 0}
</style></head><body><div class="kap">
<header id="ust"><div><h1><img src="ikon-192.png" alt="">Carry</h1><div class="k" id="alt"></div><div id="ustkitap"></div></div>
  <div class="sag"><span class="canli" id="canliust"><i></i><span>bağlanıyor</span></span><button class="tema" id="tema" onclick="temaDegis()" aria-label="tema">◐</button></div></header>
<div id="cek">↓ yenilemek için bırak</div>
<div class="sekme" id="sekme"></div>
<nav class="alt" id="nav"></nav>
<div id="sheet" hidden></div>
<div id="icerik"><div class="kart"><div class="iskelet" style="height:34px;width:60%"></div><div class="iskelet" style="height:70px;margin-top:14px"></div>
  <div class="iskelet" style="height:44px;margin-top:10px"></div></div><div class="kart"><div class="iskelet" style="height:160px"></div></div></div></div>
<script>
const VERI_GOMULU = /*VERI*/null;
const $ = s => document.querySelector(s);
const yz = (v, d=2) => v==null ? "—" : (v>=0?"+":"") + (v*100).toFixed(d).replace(".",",") + "%";
const para = v => v==null ? "—" : v.toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2}) + " $";
const isaretli = v => v==null ? "—" : (v>=0?"+":"") + para(v);
const ok_ = v => v==null ? "" : (v>=0 ? "▲" : "▼");
const sinif = v => v==null ? "" : (v>=0 ? "art" : "eks");
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let VERI, secili = 0, grafikler = [], ayIdx = {}, egriMod = "bugun";
// MADDE 740: tema (oto / koyu = tam siyah / açık), cihazda saklanır; durum çubuğu rengi temaya uyar
const TEMALAR = ["oto","koyu","acik"];
let tema = localStorage.getItem("carry_tema") || "oto";
function temaUygula(){
  const el = document.documentElement;
  if (tema=="koyu") el.dataset.theme = "dark"; else if (tema=="acik") el.dataset.theme = "light"; else delete el.dataset.theme;
  const m = document.querySelector('meta[name="theme-color"]'); if (m) m.content = css("--bg") || "#000";
  const b = $("#tema"); if (b) b.textContent = tema=="koyu" ? "☾" : tema=="acik" ? "☀" : "◐";
}
function temaDegis(){ tema = TEMALAR[(TEMALAR.indexOf(tema)+1) % 3]; localStorage.setItem("carry_tema", tema); temaUygula(); if (VERI) ciz(); }
temaUygula();
// MADDE 737: sekmeler (telefonda altta sabit). Seçim adres çubuğunda (#poz) saklanır, yenilemede korunur.
const SAYFALAR = [["ozet","Özet"],["poz","Pozisyonlar"],["gecmis","Geçmiş"],["olay","Olaylar"]];
// MADDE 757: D tasarımı — alt menü simgeleri
const NAV_SVG = {ozet:'<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>', poz:'<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="5" rx="1.5"/><path d="M3 20h12"/>',
  gecmis:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', olay:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>'};
let sayfa = (location.hash||"").slice(1); if (!SAYFALAR.some(x=>x[0]==sayfa)) sayfa = "ozet";
const MOBIL = () => innerWidth < 700;   // madde 754: telefonda sıkı liste ve sade metinler
function sayfaSec(a){ if (a==sayfa) return; sayfa = a; history.replaceState(null, "", "#"+a); ciz(); scrollTo(0,0); }
// madde 753: adres çubuğunda / yer iminde #gecmis vb. değişince sekme de değişsin
addEventListener("hashchange", ()=>{ const h = (location.hash||"").slice(1); if (SAYFALAR.some(x=>x[0]==h) && h!=sayfa && VERI){ sayfa = h; ciz(); scrollTo(0,0); } });
const AYAD = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
// PDF'teki gibi: kazanç yeşil, kayıp kırmızı; ton koyuluğu büyüklükle (gün: |%3| ve üstü tam ton)
const ton = (v, tam) => Math.round(14 + 56 * Math.min(1, Math.abs(v) / tam)) + "%";
const isiS = v => v==null || Math.abs(v) < 0.0005 ? "" : (v>0 ? "hp" : "hn");
const isi = (v, tam, ek="") => { const c = isiS(v); return c ? `class="${ek} ${c}" style="--p:${ton(v,tam)}"` : `class="${ek}"`; };
// MADDE 740: akan rakam — değer değişince 450 ms'de yeni değere akar (sayfa yeniden çizilse de son değerden devam eder)
const AKIS = {};
function akit(id, hedef, bicim){
  const el = document.getElementById(id); if (!el || hedef==null) return;
  const a = AKIS[id] || {v: hedef};
  if (a.v === hedef && !a.raf){ el.textContent = bicim(hedef); AKIS[id] = a; return; }
  const bas = a.cur != null ? a.cur : a.v, t0 = performance.now(); cancelAnimationFrame(a.raf);
  const adim = t => { const u = Math.min(1, (t - t0) / 450), e = 1 - Math.pow(1-u, 3), v = bas + (hedef - bas) * e;
    a.cur = v; const e2 = document.getElementById(id); if (e2) e2.textContent = bicim(v);
    if (u < 1) a.raf = requestAnimationFrame(adim); else { a.raf = 0; a.cur = null; } };
  a.v = hedef; AKIS[id] = a; a.raf = requestAnimationFrame(adim);
}
// MADDE 753: Geçmiş'te bugün (Binance günü, 03:00'ten beri) CANLI olarak — defter günde bir (03:05) yazıldığı için
// takvim / ay toplamı / grafikler son kaydın anında kalıyordu (dipte alınan kayıt ayı olduğundan kötü gösteriyordu).
function seriCanli(k){
  const S = k.seri || [], B = bugunKZ(k);
  if (!B || S.some(x=>x.tarih===B.tarih)) return S;
  const ek = B.dunEk ? [{tarih: B.dunEk.tarih, gun: B.dunEk.oran, kitap: B.bas, canli: true, kesin: false}] : [];
  return [...S, ...ek, {tarih: B.tarih, gun: B.oran, kitap: B.simdi, canli: true}];
}
// MADDE 759: TEK "BUGÜN" HESABI — Özet ve Geçmiş aynı sayıyı gösterir. Bugün = şimdiki kitap − dünün gün sonu kaydı
// (defter, 03:05). Dünün kaydı henüz yazılmadıysa (03:00–03:05 ya da gecikme) gün başı kitabı gün içi eğriden alınır
// ve dün ayrı "kesinleşiyor" günü olarak gösterilir — önceden dünün kazancı da "bugün"e katılıyordu.
function bugunKZ(k){
  const S = (k.seri||[]).filter(x=>x.kitap!=null), son = S[S.length-1];
  if (!son || k.kitap_canli==null) return null;
  const simdi = k.kitap_canli + canliFark(k), bas0 = gunBasi(), bugun = new Date(bas0).toISOString().slice(0,10), dun = new Date(bas0 - 864e5).toISOString().slice(0,10);
  if (son.tarih >= dun) return {usd: simdi - son.kitap, oran: son.kitap > 0 ? (simdi - son.kitap) / son.kitap : null, bas: son.kitap, simdi, tarih: bugun, dunEk: null};
  const E = bugunEgri(k);
  if (!E) return {usd: simdi - son.kitap, oran: son.kitap > 0 ? (simdi - son.kitap) / son.kitap : null, bas: son.kitap, simdi, tarih: bugun, dunEk: null};
  const gb = simdi - E.son;
  return {usd: E.son, oran: gb > 0 ? E.son / gb : null, bas: gb, simdi, tarih: bugun,
          dunEk: {tarih: dun, usd: gb - son.kitap, oran: son.kitap > 0 ? (gb - son.kitap) / son.kitap : null, bas: son.kitap}};
}
function takvim(k){
  const S = seriCanli(k); const G = S.map((s,j)=>({...s, j})).filter(s=>s.gun!=null && s.tarih);
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
    const ipucu = `${s.tarih}  ${yz(s.gun)}` + (usd!=null ? `  (${isaretli(usd)})` : "") + (s.canli ? "  · bugün, canlı (gün sonunda kesinleşir)" : "");
    h += `<div ${isi(s.gun,0.03,"g"+(s.canli?" canlig":""))} title="${ipucu}"><div class="n">${d}${s.canli?" ●":""}</div><div class="v">${yz(s.gun)}</div></div>`;
  }
  const g = M.map(s=>s.gun), art_ = g.filter(v=>v>0).length, eks_ = g.filter(v=>v<0).length;
  const eniyi = M.reduce((p,c)=>c.gun>p.gun?c:p), enkotu = M.reduce((p,c)=>c.gun<p.gun?c:p);
  // madde 753: canlı günü içeren ayın toplamı KİTAPTAN (ay başı kitabı → şu anki kitap). Günlük yüzdeleri çarpmak defterin
  // 00:05 kaydıyla gün içi eğrinin 00:00 başlangıcı arasındaki farkı ve (gerçek funding görünümünde) gün kırılımı olmayan
  // eski günleri biriktirir; başlıktaki kitapla çelişirdi. Geçmiş aylar defterin günlük zinciriyle.
  const gercekS = S.filter(x=>!x.canli), onc_ = gercekS.filter(x=>x.tarih < a + "-01"), ayBas = (onc_.length ? onc_[onc_.length-1] : gercekS[0] || {}).kitap;
  const ayg = M.some(x=>x.canli) && k.kitap_canli!=null && ayBas ? k.kitap_canli / ayBas - 1 : (k.aylik||{})[a];
  return `<div class="aygez"><button ${i<=0?"disabled":""} onclick="ayIdx[secili]=${i-1};ciz()" aria-label="önceki ay">‹</button>
    <b>${AYAD[m-1]} ${y} · <span class="${sinif(ayg)}">${yz(ayg)}</span></b>
    <button ${i>=aylar.length-1?"disabled":""} onclick="ayIdx[secili]=${i+1};ciz()" aria-label="sonraki ay">›</button></div>
    <div class="takvim">${h}</div>
    <div class="k" style="margin-top:8px">kazanç günü <b class="art">${art_}</b> · kayıp günü <b class="eks">${eks_}</b> / ${g.length} ·
    en iyi ${+eniyi.tarih.slice(8,10)} ${AYAD[m-1]} <span class="${sinif(eniyi.gun)}">${yz(eniyi.gun)}</span> · en kötü ${+enkotu.tarih.slice(8,10)} ${AYAD[m-1]} <span class="${sinif(enkotu.gun)}">${yz(enkotu.gun)}</span></div>`;
}
// MADDE 740: yıllık takvim (GitHub tarzı): son 53 hafta, her kare bir gün, renk = günlük getiri
function yillik(k){
  const G = {}; seriCanli(k).forEach(s=>{ if (s.gun!=null && s.tarih) G[s.tarih] = s.gun; });
  const bugun = new Date(); bugun.setHours(12,0,0,0);
  const bas = new Date(bugun); bas.setDate(bas.getDate() - 52*7 - ((bugun.getDay()+6)%7));
  let h = "", n = 0, top = 0;
  for (let d = new Date(bas); d <= bugun || (d.getDay()+6)%7 != 0; d.setDate(d.getDate()+1)){
    if (d > bugun){ h += `<i class="x"></i>`; continue; }
    const t = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`, v = G[t];
    if (v!=null){ n++; top = (1+top)*(1+v)-1; }
    h += `<i ${v!=null ? isi(v,0.03,"").replace('class=" ','class="') : ""} title="${t}${v!=null?"  "+yz(v):""}"></i>`;
  }
  const S0 = (k.seri||[])[0];   // madde 753: tüm geçmiş pencere içindeyse dönem toplamı kitaptan (başlıktaki kitapla aynı)
  if (S0 && S0.kitap && k.kitap_canli!=null && S0.tarih >= `${bas.getFullYear()}-${String(bas.getMonth()+1).padStart(2,"0")}-${String(bas.getDate()).padStart(2,"0")}`) top = k.kitap_canli / S0.kitap - 1;
  return `<div class="yil yatay" id="yil"><div class="ic">${h}</div></div><div class="k" style="margin-top:6px">${n} işlem günü · bu dönemde ${yz(n?top:null)}</div>`;
}
// MADDE 732: ANLIK FİYAT. Pozisyon listesi (miktar, giriş) sunucudan; işaret fiyatı tarayıcıdan Binance'in HERKESE AÇIK
// akışından (wss://fstream.binance.com/market — eski /stream adresi bağlanıp veri göndermiyor; anahtarsız, saniyede bir). Panel yine emir veremez, anahtar görmez.
// MADDE 740: aynı akış funding oranını (r) ve sonraki funding zamanını (T) da verir.
let WS = null, WSK = "", FIYAT = {}, FUND = {}, ONCEKI = {}, wsZaman = 0;
function canliBagla(k){
  if (VERI_GOMULU || !window.WebSocket) return;
  const P = k && k.poz_kaynak=="canlı" ? Object.entries(k.pozisyonlar||{}).filter(p=>p[1].giris>0 && p[1].miktar) : [];
  const anahtar = P.map(p=>p[0]).sort().join(",");
  if (anahtar===WSK && WS && WS.readyState<=1) return;
  if (WS){ WS.onclose = null; WS.close(); WS = null; }
  WSK = anahtar; if (!anahtar) return;
  WS = new WebSocket("wss://fstream.binance.com/market/stream?streams=" + P.map(p=>p[0].toLowerCase()+"@markPrice@1s").join("/"));
  WS.onmessage = e => { try { const d = JSON.parse(e.data).data; if (d && d.s && +d.p>0){ FIYAT[d.s] = +d.p; wsZaman = Date.now();
    if (d.r!=null && d.T) FUND[d.s] = {r: +d.r, T: +d.T}; } } catch(_){} };
  WS.onclose = () => { WS = null; WSK = ""; setTimeout(()=>canliBagla(VERI && VERI.kurulumlar[secili]), 5000); };
}
// MADDE 739: GÜNLÜK grafik (TradingView "bugün" gibi). Gün Binance gün başında (00:00 UTC = 03:00 TR) başlar; yatay eksen
// tam gün (03:00 -> ertesi 03:00), çizgi gün ilerledikçe soldan sağa uzar. 15 dk mumlar her 15 dk sınırında yeniden alınır,
// son nokta anlık fiyat. MUM[s] = {bas, nok: [[ms, fiyat], ...]}.
const GUN_MS = 86400e3, MUM_MS = 900e3;
let MUM = {}, mumDilim = -1, mumAnahtar = "", mumYukleniyor = false;
const gunBasi = (t=Date.now()) => Math.floor(t / GUN_MS) * GUN_MS;
async function mumYukle(k){
  const S = Object.keys((k && k.pozisyonlar) || {}), a = S.slice().sort().join(",");
  const dilim = Math.floor((Date.now() - 5e3) / MUM_MS);   // mum kapandıktan 5 sn sonra
  if (VERI_GOMULU || !S.length || mumYukleniyor || (a===mumAnahtar && dilim===mumDilim)) return;
  mumYukleniyor = true; const bas = gunBasi(); let gelen = 0;
  await Promise.all(S.map(async s => { try {
    const d = await (await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=15m&startTime=${bas}&limit=96`, {cache:"no-store"})).json();
    if (Array.isArray(d)){
      const nok = d.length ? [[+d[0][0], +d[0][1]]].concat(d.map(x=>[Math.min(+x[6]+1, Date.now()), +x[4]])) : [];
      MUM[s] = {bas, nok: nok.filter(n=>n[1]>0)}; gelen++;
    }
  } catch(_){} }));
  mumYukleniyor = false;
  if (gelen === S.length){ mumAnahtar = a; mumDilim = dilim; }   // eksikse bir sonraki saniyelik turda yeniden dener
  else setTimeout(()=>{ mumAnahtar = ""; }, 60e3);
  canliBoya();
}
const fiyatYaz = v => v==null ? "—" : v.toLocaleString("tr-TR", v>=1000 ? {minimumFractionDigits:2,maximumFractionDigits:2} : {minimumSignificantDigits:5,maximumSignificantDigits:5});
function cizgi(seri, W, H, renk, yatay, kimlik="c", xs=null, yatayAralikta=false, minAralik=0){
  // seri: sayılar; xs: 0..1 yatay konumlar (yoksa eşit aralık); yatay: kesikli referans çizgisi (giriş fiyatı / başlangıç kitabı)
  // yatayAralikta: referans y ölçeğini genişletmez, yalnız aralıktaysa çizilir (günlük grafik: giriş uzaksa çizgi ezilmesin)
  if (!seri || seri.length < 2) return `<svg viewBox="0 0 ${W} ${H}"></svg>`;
  const hepsi = yatay!=null && !yatayAralikta ? seri.concat([yatay]) : seri;
  let lo = Math.min(...hepsi), hi = Math.max(...hepsi); if (hi-lo < Math.abs(hi)*1e-6 + 1e-12){ hi += Math.abs(hi)*1e-3 + 1e-9; lo -= Math.abs(lo)*1e-3 + 1e-9; }
  // madde 743: en küçük dikey aralık — gün başında birkaç kuruşluk oynama tüm yüksekliğe yayılıp duvar gibi görünmesin
  if (hi - lo < minAralik){ const m = (hi + lo) / 2; lo = m - minAralik/2; hi = m + minAralik/2; }
  if (yatay!=null && yatayAralikta && (yatay < lo || yatay > hi)) yatay = null;
  const x = i => (xs ? xs[i] : i/(seri.length-1)) * (W-6), y = v => H-3 - (v-lo)/(hi-lo) * (H-6);
  const yol = seri.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const sx = x(seri.length-1), sy = y(seri[seri.length-1]);
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <defs><linearGradient id="gd-${kimlik}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${renk}" stop-opacity=".38"/><stop offset="1" stop-color="${renk}" stop-opacity="0"/></linearGradient></defs>
    <path d="${yol}L${sx.toFixed(1)},${H}L${x(0).toFixed(1)},${H}Z" fill="url(#gd-${kimlik})"/>
    ${yatay!=null?`<line x1="0" x2="${W}" y1="${y(yatay).toFixed(1)}" y2="${y(yatay).toFixed(1)}" stroke="${css("--soluk")}" stroke-dasharray="3 3" stroke-width="1" vector-effect="non-scaling-stroke"/>`:""}
    <path d="${yol}" fill="none" stroke="${renk}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"/>
    <circle class="uc" cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="3" fill="${renk}"/><circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="3" fill="${renk}"/></svg>`;
}
function kivilcim(s, p, f, renk, W=160, H=64){   // madde 755: W/H = gösterildiği alanın gerçek ölçüsü (esnetilmesin)
  const M = MUM[s], simdi = Date.now();
  if (!M || M.bas !== gunBasi(simdi)) return `<div class="grbekle iskelet"></div>`;
  const nok = M.nok.filter(n => n[0] < simdi - 1e3);   // tamamlanan mumlar; son nokta anlık fiyat
  if (f) nok.push([simdi, f]);
  if (nok.length < 2) return `<div class="grbekle">gün yeni başladı (03:00)…</div>`;
  // madde 743: en küçük dikey aralık fiyatın %1'i (gün başında 2-3 mumluk oynama duvar gibi görünmesin)
  return cizgi(nok.map(n=>n[1]), W, H, renk, p.giris>0 ? p.giris : null, s, nok.map(n=>Math.min(1, (n[0]-M.bas)/GUN_MS)), true, 0.01 * (f || nok[nok.length-1][1]));
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
// MADDE 740: funding — bu pozisyon bir sonraki ödemede ne alır / öder. Ödeme = −miktar × işaret × oran (long, oran > 0 iken öder).
function fundSatir(s, p, f){
  const F = FUND[s]; if (!F || !p.miktar) return `<div class="fund">funding —</div>`;
  const t = -p.miktar * (f||p.isaret) * F.r, al = t >= 0;
  return `<div class="fund">funding ${(F.r*100).toFixed(4).replace(".",",")}% · <span class="${al?"art":"eks"}">${al?"alıyoruz":"ödüyoruz"} ${isaretli(t)}</span></div>`;
}
let KUTU_W = 160;   // madde 755: kart içi grafik genişliği (ilk kart çizilince ölçülür)
function kutuIc(s, p, k){
  const f = FIYAT[s] || p.isaret, ok = f && p.giris>0 && p.miktar;
  const ky = ok ? (f/p.giris - 1) * (p.miktar>0 ? 1 : -1) * 100 : p.kar_yuzde;
  const g = ok ? p.miktar * (f - p.giris) : p.gerceklesmemis, usd = ok ? Math.abs(p.miktar) * f : p.usd;
  const renk = css((ky||0) >= 0 ? "--art" : "--eks");
  const o = ONCEKI[s], flas = (o && f && f!==o) ? (f>o ? "yukari" : "asagi") : ""; ONCEKI[s] = f;
  const M = MUM[s], acilis = M && M.bas===gunBasi() && M.nok.length ? M.nok[0][1] : null, bg = acilis && f ? (f/acilis - 1) : null;
  return `<div class="ad"><span>${s.replace(/USDT$/,"")}</span><span class="k">${para(usd)}</span></div>
    <div class="f ${flas}">${fiyatYaz(f)}</div><div class="gr"><span>giriş ${fiyatYaz(p.giris)}</span>${bg!=null?`<span class="${sinif(bg)}">bugün ${yz(bg)}</span>`:""}</div>
    <div class="y ${sinif(ky)}"><span class="rz">${ok_(ky)} ${ky==null?"—":Math.abs(ky).toFixed(2).replace(".",",")+"%"}</span><small>${g==null?"":isaretli(g)}</small></div>
    ${kivilcim(s, p, f, renk, KUTU_W)}${k ? hedefCubuk(k, p, f) : ""}${fundSatir(s, p, f)}${k ? stopSatir(k, s, p) : ""}`;
}
// MADDE 754: telefonda pozisyon = tek satır (coin, yön, büyüklük, kâr %, $); dokununca kutudaki ayrıntılar açılır
function satirIc(s, p, k){
  const f = FIYAT[s] || p.isaret, ok = f && p.giris>0 && p.miktar;
  const ky = ok ? (f/p.giris - 1) * (p.miktar>0 ? 1 : -1) * 100 : p.kar_yuzde;
  const g = ok ? p.miktar * (f - p.giris) : p.gerceklesmemis, usd = ok ? Math.abs(p.miktar) * f : p.usd;
  const D = k.stop_durum, sv = D && !D.kapali && p.miktar>0 ? (D.coin||{})[s.replace(/USDT$/,"")] : null;
  const uy = sv!=null && sv <= -D.esik_coin*0.5 ? `<span class="w ${sv<=-D.esik_coin?'e':''}" title="koşullu stop'a yakın">!</span>` : "";
  const ac = ACIK.has("p"+s), renk = css((ky||0) >= 0 ? "--art" : "--eks");
  const M = MUM[s], acilis = M && M.bas===gunBasi() && M.nok.length ? M.nok[0][1] : null, bg = acilis && f ? (f/acilis - 1) : null;
  return `<div class="ust" onclick="pozAc('${s}')"><span class="c"><b>${s.replace(/USDT$/,"")}</b><span class="yb">${p.miktar>0?"L":"S"}</span>${uy}</span>
      <span class="u">${para(usd)}</span><span class="p"><span class="rz ${sinif(ky)}">${ky==null?"—":(ky>=0?"+":"−")+Math.abs(ky).toFixed(1).replace(".",",")+"%"}</span></span><span class="g ${sinif(g)}">${g==null?"":isaretli(g)}</span></div>
    ${ac ? `<div class="det"><div class="f">${fiyatYaz(f)}</div><div class="gr"><span>giriş ${fiyatYaz(p.giris)}</span>${bg!=null?`<span class="${sinif(bg)}">bugün ${yz(bg)}</span>`:""}</div>
      ${kivilcim(s, p, f, renk, Math.max(200, Math.round((($("#icerik")||{}).clientWidth || innerWidth - 28) - 52)), 90)}${hedefCubuk(k, p, f)}${fundSatir(s, p, f)}${stopSatir(k, s, p)}</div>` : ""}`;
}
function pozAc(s){ ACIK.has("p"+s) ? ACIK.delete("p"+s) : ACIK.add("p"+s); const e = document.getElementById("t-"+s), k = VERI.kurulumlar[secili];
  if (e && k.pozisyonlar[s]){ e.classList.toggle("acik", ACIK.has("p"+s)); e.innerHTML = satirIc(s, k.pozisyonlar[s], k); } }
// madde 753: long kutusunda koşullu stop'a yakınlık (coin 24 sa eşiğin yarısını geçtiyse)
function stopSatir(k, s, p){
  const D = k.stop_durum; if (!D || D.kapali || p.miktar<=0) return "";
  const v = (D.coin||{})[s.replace(/USDT$/,"")], ec = D.esik_coin; if (v==null || v > -ec*0.5) return "";
  return `<div class="fund"><span class="${v<=-ec?'eks':'uyr'}">stop: 24 sa ${(v*100).toFixed(1).replace(".",",")}% / eşik −%${Math.round(ec*100)}</span> · piyasa ${D.piyasa_sart?'<b class="eks">şart var</b>':'şart yok'}</div>`;
}
// MADDE 740: ısı haritası (kare boyu = pozisyon $, renk = kâr %); "squarified" yerleşim
function kareler(A, W, H){
  const top = A.reduce((a,x)=>a+x.v, 0) || 1, out = []; let x = 0, y = 0, w = W, h = H;
  let kalan = A.map(a=>({...a, a: a.v/top*W*H}));
  const kotu = (r, k) => { const s = r.reduce((a,b)=>a+b.a,0), mx = Math.max(...r.map(z=>z.a)), mn = Math.min(...r.map(z=>z.a)); return Math.max(k*k*mx/(s*s), s*s/(k*k*mn)); };
  while (kalan.length){
    const kenar = Math.min(w, h); let sira = [kalan[0]], i = 1;
    while (i < kalan.length && kotu(sira.concat([kalan[i]]), kenar) <= kotu(sira, kenar)){ sira.push(kalan[i]); i++; }
    const s = sira.reduce((a,b)=>a+b.a, 0);
    if (w >= h){ const rw = s/h; let yy = y; sira.forEach(r=>{ const rh = r.a/rw; out.push({...r, x, y: yy, w: rw, h: rh}); yy += rh; }); x += rw; w -= rw; }
    else { const rh = s/w; let xx = x; sira.forEach(r=>{ const rw = r.a/rh; out.push({...r, x: xx, y, w: rw, h: rh}); xx += rw; }); y += rh; h -= rh; }
    kalan = kalan.slice(sira.length);
  }
  return out;
}
function isiHarita(k){
  const A = Object.entries(k.pozisyonlar||{}).map(([s,p])=>{
    const f = FIYAT[s] || p.isaret, ok = f && p.giris>0 && p.miktar;
    return {s, yon: p.yon, v: ok ? Math.abs(p.miktar)*f : (p.usd||0), ky: ok ? (f/p.giris-1)*(p.miktar>0?1:-1) : (p.kar_yuzde||0)/100, g: ok ? p.miktar*(f-p.giris) : p.gerceklesmemis};
  }).filter(a=>a.v>0).sort((a,b)=>b.v-a.v);
  if (!A.length) return "<div class='bos'>açık pozisyon yok</div>";
  return kareler(A, 100, 100).map(r=>{
    const yog = Math.round(18 + 62 * Math.min(1, Math.abs(r.ky)/0.08)), renk = r.ky>=0 ? "--art" : "--eks";
    const kucuk = r.h < 24 || r.w < 22;   // küçük kare: tek satır, yön etiketi yok
    // madde 754: telefonda küçük karede yazı taşıyordu ("1000PEPE s") — çizimden sonra isiSigdir() gerçek genişliği ölçüp sığmayanı gizler
    const ad = r.s.replace(/USDT$/,""), ip = `${ad} ${r.yon=="L"?"long":"short"} ${yz(r.ky)}`;
    return `<div class="${kucuk?"kk":""}" title="${ip}" style="left:${r.x}%;top:${r.y}%;width:${r.w}%;height:${r.h}%;background:color-mix(in srgb,var(${renk}) ${yog}%,var(--kart2))">
      <b>${ad}${kucuk?"":` <small>${r.yon=="L"?"long":"short"}</small>`}</b><span>${yz(r.ky)}</span></div>`;
  }).join("");
}
function isiSigdir(){
  const ih = $("#isi"); if (!ih) return;
  for (const d of ih.children){
    const b = d.querySelector("b"), sp = d.querySelector("span"), sm = d.querySelector("small"); if (!b) continue;
    const ic = d.clientWidth - 12, tasar = e => e && e.style.display!="none" && e.scrollWidth > ic;
    if (sm && b.scrollWidth > ic) sm.remove();
    if (d.classList.contains("kk")){ if (d.scrollWidth > d.clientWidth + 1 && sp) sp.style.display = "none"; }
    else if (tasar(sp)) sp.style.display = "none";
    if (tasar(b) || d.clientHeight < 18) { b.style.display = "none"; if (sp) sp.style.display = "none"; }
  }
}
// MADDE 742: canlı fiyatla açık pozisyonların şu anki kâr/zararı ile son anlık görüntüdeki (5 dk) farkı. Canlı değilse 0.
function canliFark(k){
  if (k.poz_kaynak!="canlı" || Date.now() - wsZaman >= 5000) return 0;
  let top = 0;
  for (const [s,p] of Object.entries(k.pozisyonlar||{})){
    const f = FIYAT[s]; top += (f && p.giris>0 && p.miktar) ? p.miktar * (f - p.giris) : (p.gerceklesmemis||0);
  }
  return top - (k.gerceklesmemis||0);
}
// MADDE 742: portföyün BUGÜNKÜ eğrisi = KİTABIN gün başından beri değişimi (sunucu 5 dk'da bir kaydeder: anlik_gun.json) +
// son kayıttan beri canlı fiyat farkı. Kapanan işlemler, funding ve komisyon dahil. (Madde 740'taki eski eğri şu an açık
// pozisyonları 03:00'ten beri tutulmuş sayıyordu: gün içinde açılan coinin alınmadan önceki yükselişi kâra yazılıyordu.)
function bugunEgri(k){
  const G = k.gun_egri, bas = gunBasi(), simdi = Date.now();
  if (!G || !G.nok || !G.nok.length || G.bas*1000 !== bas) return null;
  const nok = G.nok.map(n=>[n[0]*1000, n[1]]), fark = canliFark(k);
  if (fark || nok.length === 1) nok.push([simdi, nok[nok.length-1][1] + fark]);
  const son = nok[nok.length-1][1], kit = k.kitap_canli!=null ? k.kitap_canli + fark : null;
  return {seri: nok.map(n=>n[1]), xs: nok.map(n=>Math.min(1,(n[0]-bas)/GUN_MS)), son, ilk: G.ilk*1000, bas,
          oran: kit!=null && kit - son > 0 ? son / (kit - son) : null};
}
const EGRI_W = () => Math.max(200, Math.round((($("#egri")||{}).clientWidth) || (($("#icerik")||{}).clientWidth || innerWidth - 28) - 30));
function egriIc(k){
  if (egriMod=="bugun"){
    const E = bugunEgri(k);
    if (!E || E.seri.length < 2) return `<div class="bl"><span>bugün 03:00'ten beri · kitap</span><span>—</span></div><div class="bekle" style="padding:20px 0">gün içi kitap kaydı bekleniyor (5 dakikada bir)</div>`;
    const bsl = E.ilk - E.bas > 20*60e3 ? new Date(E.ilk).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"}) + " kaydından beri" : "03:00'ten beri";
    return `${E.ilk - E.bas > 20*60e3 ? `<div class="bl"><span>${bsl}</span></div>` : ""}
      ${cizgi(E.seri, EGRI_W(), 70, css(E.son>=0?"--art":"--eks"), 0, "bugun", E.xs, true, Math.max(4, 0.004 * (k.kitap_canli || k.kitap || 1000)))}<div class="eksen"><span>03:00</span><span>09:00</span><span>15:00</span><span>21:00</span><span>03:00</span></div>`;
  }
  const SS = egriMod=="hafta" ? (k.seri||[]).slice(-8) : (k.seri||[]);   // madde 757: 1H = son 7 gün sonu + şimdi
  const kit = SS.map(s=>s.kitap).filter(v=>v!=null); if (k.kitap_canli!=null && kit.length) kit.push(k.kitap_canli + canliFark(k));
  if (kit.length < 2) return `<div class="bl"><span>kitap · başlangıçtan</span></div><div class="bekle" style="padding:20px 0">en az 2 gün gerekli</div>`;
  const d = kit[kit.length-1]-kit[0];
  return `<div class="bl"><span>${egriMod=="hafta" ? "son 7 gün" : `başlangıçtan (${(k.seri||[]).length} gün)`}</span><b class="${sinif(d)}">${isaretli(d)}</b></div>${cizgi(kit, EGRI_W(), 70, css(d>=0?"--art":"--eks"), kit[0], "kitap")}`;
}
function egriSec(m){ egriMod = m; const k = VERI.kurulumlar[secili]; document.querySelectorAll(".mod button").forEach(b=>b.classList.toggle("on", b.dataset.m==m)); const e = $("#egri"); if (e) e.innerHTML = egriIc(k); }
function canliDurum(){
  const on = !VERI_GOMULU && Date.now() - wsZaman < 5000, e = $("#canliust");
  if (e){ e.className = "canli" + (on ? " on" : ""); e.lastElementChild.textContent = on ? "canlı" : (VERI ? VERI.uretim.slice(11) : "bağlanıyor"); }
  return on;
}
function halka(dolu, n){
  const r = 14, c = 2*Math.PI*r, o = c * (1 - dolu/Math.max(1,n));
  return `<svg viewBox="0 0 34 34"><circle cx="17" cy="17" r="${r}" fill="none" stroke="${css("--cizgi")}" stroke-width="4"/>
    <circle cx="17" cy="17" r="${r}" fill="none" stroke="${css("--vurgu")}" stroke-width="4" stroke-linecap="round" stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${o.toFixed(1)}" transform="rotate(-90 17 17)"/>
    <text x="17" y="21" text-anchor="middle" font-size="10" font-weight="700" fill="${css("--yazi")}">${dolu}</text></svg>`;
}
// MADDE 748: sayaç gerçek Binance'in sıradaki funding saatine bakar; tahmin YALNIZ o saatte ödeyen pozisyonların toplamı
// (eskiden hepsi toplanıyordu: saatlik ödeyen tek coin varken bile bütün kitabın funding'i gösteriliyordu). Demoda altta
// demo hesabın kendi sıradaki ödemesi (sunucu demo borsadan okur; demo takvimi / oranı gerçekten farklı olabilir).
const sureYaz = sn => sn >= 3600 ? `${Math.floor(sn/3600)} sa ${Math.floor(sn%3600/60)} dk` : `${Math.floor(sn/60)} dk ${Math.floor(sn%60)} sn`;
const saatYaz = ms => new Date(ms).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"});
function fundKart(k){
  const P = Object.entries(k.pozisyonlar||{}); let T = null;
  for (const [s] of P){ const F = FUND[s]; if (F && F.T) T = T==null ? F.T : Math.min(T, F.T); }
  if (T == null) return `<div class="d">—</div><div class="k">akış bekleniyor</div>`;
  let top = 0, n = 0;
  for (const [s,p] of P){ const F = FUND[s]; if (F && Math.abs(F.T - T) < 60e3){ n++; top += -p.miktar * (FIYAT[s]||p.isaret) * F.r; } }
  const demo = k.mod=="demo", D = k.demo_funding;
  let alt = "";
  if (demo && D && D.T){
    const dk = D.T*1000 - Date.now();
    alt = `<span class="k" style="white-space:normal" title="Demo borsa funding'i kendi saat ve oranıyla öder; demo hesaba bu saatte yatar.">demo hesap: ${saatYaz(D.T*1000)}${dk > 0 ? " · " + sureYaz(dk/1000) : " · işleniyor"} · <b class="${sinif(D.tahmin)}">${isaretli(D.tahmin)}</b></span>`;
  }
  return `<div class="d">${sureYaz(Math.max(0, (T - Date.now())/1000))}</div><span class="k" style="white-space:normal" title="${n} pozisyon bu saatte öder (gerçek Binance oranıyla tahmin)">${demo?"gerçek: ":""}${saatYaz(T)} · ${n} poz · <b class="${sinif(top)}">${isaretli(top)}</b></span>${alt}`;
}
// MADDE 746: funding ödemesi gelince veriyi hemen yeniden iste (dakikalık yenilemeyi bekleme). Sunucu ödemeden sonra
// 0:40 / 2 / 4 / 7 / 11. dakikalarda ek okuma yapar (carry-anlik-funding.timer); tarayıcı o okumaların ardından çeker.
let FUND_T = null, FUND_PLAN = [];
function fundTakip(){
  let T = null; for (const F of Object.values(FUND)) if (F && F.T) T = T==null ? F.T : Math.min(T, F.T);
  if (T == null) return;
  if (FUND_T != null && T > FUND_T){   // bir funding anı geçti (akış sonrakine döndü)
    const t0 = FUND_T; FUND_PLAN.forEach(clearTimeout);
    FUND_PLAN = [55, 135, 255, 435, 675].map(sn => setTimeout(yukle, Math.max(0, t0 + sn*1000 - Date.now())));
  }
  FUND_T = T;
}
function canliBoya(){
  fundTakip();
  const on = canliDurum();
  const k = VERI && VERI.kurulumlar[secili]; if (!k) return;
  const ds = $("#dilimsure"); if (ds) ds.innerHTML = dilimKart(k.dilim);
  const dd2 = $("#dilimd"); if (dd2) dd2.innerHTML = dilimMetin(k.dilim);
  const fd2 = $("#fundd"); if (fd2) fd2.innerHTML = fundMetin(k);
  const dc = $("#dcumle"); if (dc) dc.innerHTML = durumCumle(k);
  const fk = $("#fundsure"); if (fk) fk.innerHTML = fundKart(k);
  mumYukle(k);
  let top = 0; const taraf = {L:[0,0], S:[0,0]};
  for (const [s,p] of Object.entries(k.pozisyonlar||{})){
    const f = FIYAT[s], ok = k.poz_kaynak=="canlı" && f && p.giris>0 && p.miktar;
    const g = ok ? p.miktar * (f - p.giris) : (p.gerceklesmemis||0); top += g;
    const t = taraf[p.yon] || taraf.L; t[0] += ok ? Math.abs(p.miktar)*f : (p.usd||0); t[1] += g;
    const et = document.getElementById("t-"+s); if (et) et.innerHTML = et.classList.contains("drow") ? satirD(s, p, k) : et.classList.contains("sat") ? satirIc(s, p, k) : kutuIc(s, p, k);
  }
  for (const y of ["L","S"]){ const e = document.getElementById("taraf-"+y); if (e) e.innerHTML = `${para(taraf[y][0])} · <span class="${sinif(taraf[y][1])}">${taraf[y][1]>=0?"▲":"▼"} ${isaretli(taraf[y][1])}</span>`; }
  if (SHEET){ const si = $("#sheetic"), sp = (k.pozisyonlar||{})[SHEET]; if (si && sp) si.innerHTML = sheetIc(SHEET, sp, k); else if (!sp) sheetKapat(); }
  if (sayfa=="gecmis"){ const gs = $("#gsade"); if (gs) gs.innerHTML = gecmisSade(k); }   // madde 757: geçmiş de saniyelik canlı
  const dn = $("#denge"); if (dn) dn.innerHTML = dengeIc(taraf);
  const ih = $("#isi"); if (ih){ ih.innerHTML = isiHarita(k); isiSigdir(); }
  const eg2 = $("#egri"); if (eg2) eg2.innerHTML = egriIc(k);
  if (k.poz_kaynak!="canlı") return;
  const fark = top - (k.gerceklesmemis||0), eg = $("#gerc");
  if (eg){ eg.textContent = `${top>=0?"▲":"▼"} ${isaretli(top)}`; eg.className = sinif(top); }
  if (k.kitap_canli!=null){ akit("kitapd", k.kitap_canli + fark, para); akit("ustk", k.kitap_canli + fark, para); }
  if (k.kar_usd!=null){ const ku = k.kar_usd + fark, oran = k.kitap_bas ? ku/k.kitap_bas : null;
    const eku = $("#karusd"); if (eku){ eku.textContent = `${ok_(ku)} ${isaretli(ku)} (${yz(oran)})`; eku.className = "kar rz " + sinif(ku); }
    const euk = $("#ustkar"); if (euk){ euk.textContent = ` ${yz(oran)}`; euk.className = sinif(ku); }
    const da = $("#dalt"); if (da) da.innerHTML = daltHtml(k, ku);
    const nd = $("#nerden"); if (nd) nd.innerHTML = nerdenHtml(k, top, ku); }
  const ed = $("#dokum"); if (ed && k.kar_usd!=null) ed.innerHTML = dokumYaz(k, top, k.kar_usd + fark);
}
function dengeIc(T){
  const t = (T.L[0] + T.S[0]) || 1, l = T.L[0]/t*100;
  return `<div class="c"><span style="width:${l.toFixed(1)}%;background:var(--vurgu)"></span><span style="width:${(100-l).toFixed(1)}%;background:var(--uyari)"></span></div>
    <div class="t"><span><b style="color:var(--vurgu)">Long</b> ${para(T.L[0])} · %${Math.round(l)}</span><span>%${Math.round(100-l)} · ${para(T.S[0])} <b style="color:var(--uyari)">Short</b></span></div>`;
}
// MADDE 733/737: başlangıçtan $ = açık pozisyonlar + kapanan + funding + komisyon + diğer + başlangıç farkı.
// Kalemler tek satır; dokununca açıklama açılır (seçim saniyelik yenilemede korunur). Üstte kalemlerin payı (renkli çubuk).
const ACIK = new Set();
function dkAc(a){ ACIK.has(a) ? ACIK.delete(a) : ACIK.add(a); const k = VERI.kurulumlar[secili]; canliBoya(); if (k.poz_kaynak!="canlı"){ const ed=$("#dokum"); if(ed) ed.innerHTML = dokumYaz(k, k.gerceklesmemis, k.kar_usd); } }
function dokumYaz(k, poz, kar){
  // madde 752: "gerçek funding" görünümünde toplam gerçek funding'le; döküm de aynı funding'i kullanmalı (yoksa fark
  // "başlangıç farkı"na düşüyordu). Demo hesabın ödediği alt satırda.
  const D = k.dokum, gz = FG && k.gercek && D.funding_gercek!=null, F = gz ? D.funding_gercek : D.funding;
  const dg = D.diger_gelir||0, fark = kar - poz - D.gerceklesen - F - D.komisyon - dg;
  const K = [["poz","Açık pozisyonlar", poz, "şu an açık coinlerin fiyat hareketi; kapanınca kesinleşir", "--vurgu", true],
             ["kap","Kapanan pozisyonlar", D.gerceklesen, "kapatılmış işlemlerin kesinleşmiş kâr / zararı", "--mor", false],
             ["fun", gz ? "Funding (gerçek oranla)" : "Funding", F, "pozisyon taşıdığı için funding saatlerinde (çoğu coinde 8, bazılarında 4 saatte bir) alınan (+) / ödenen (−) ücret — stratejinin asıl geliri", "--art", true],
             ["kom","Komisyon", D.komisyon, "Binance işlem ücreti", "--uyari", true],
             ["dig","Diğer Binance kayıtları", dg, "sigorta fonu vb.", "--mor", false],
             ["bas","Başlangıç farkı", fark, "başlangıç kaydı alınırken açık pozisyonların o anki kârı ve ölçüm zamanlaması; demoda ayrıca demo / gerçek fiyat farkı (açık pozisyonlar gerçek fiyatla, toplam demo hesaptan). Küçük oynar; gerçek hesapta ~0", "--soluk", false]]
    .filter(x => x[5] || Math.abs(x[2]) >= 0.005);
  const tm = K.reduce((a,x)=>a+Math.abs(x[2]), 0) || 1;
  const cubuk = `<div class="cubuk">${K.map(x=>`<span style="width:${(Math.abs(x[2])/tm*100).toFixed(1)}%;background:${css(x[4])}" title="${x[1]}"></span>`).join("")}</div>`;
  // madde 744: demoda funding'i demo borsa kendi oranıyla öder; bot gerçek oranlara göre seçer -> "gerçek oranlarla olsaydı" (toplama girmez)
  const fg = gz ? D.funding : D.funding_gercek, fgS = fg==null ? "" : gz ? `<div class="dk alt ${ACIK.has("fug")?"acik":""}" onclick="dkAc('fug')"><span class="n"></span><span class="a">↳ demo hesabın ödediği <span class="ok">›</span></span><span class="v ${sinif(fg)}">${isaretli(fg)}</span><span class="ac">Demo borsa funding'i kendi oranıyla öder (gerçekle ilgisiz). Toplama girmez; "demo (ham)" görünümünde toplam bununla hesaplanır.</span></div>` : `<div class="dk alt ${ACIK.has("fug")?"acik":""}" onclick="dkAc('fug')"><span class="n"></span><span class="a">↳ gerçek Binance oranlarıyla olsaydı <span class="ok">›</span></span><span class="v ${sinif(fg)}">${isaretli(fg)}</span><span class="ac">Bot coinleri gerçek Binance'in funding oranlarına bakarak seçer, ama pozisyonlar demo borsada olduğu için funding'i demo borsa kendi oranıyla öder (çoğu zaman gerçekle ilgisiz). Bu satır aynı pozisyonların gerçek oranlarla ne alacağını / ödeyeceğini gösterir (yaklaşık; 5 dk'lık pozisyon görüntüsüyle). Toplama girmez — canlı hesapta funding bu olurdu.</span></div>`;
  return cubuk + K.map(x=>`<div class="dk ${ACIK.has(x[0])?"acik":""}" onclick="dkAc('${x[0]}')"><span class="n" style="background:${css(x[4])}"></span><span class="a">${x[1]} <span class="ok">›</span></span><span class="v ${sinif(x[2])}">${isaretli(x[2])}</span><span class="ac">${x[3]}</span></div>` + (x[0]=="fun" ? fgS : "")).join("")
    + `<div class="dk top"><span class="a">Toplam (başlangıçtan beri)</span><span class="v rz ${sinif(kar)}">${isaretli(kar)}</span></div>`;
}
function ayarKart(k){
  const A = k.ayar;
  if (!A) return `<div class="d">${k.profil||"—"}${k.doz?" · "+k.doz+"x":""}</div>`;
  const ad = A.profil || k.profil || "—";
  // madde 742: "koşullu stop %3" pozisyon %3 zararda kapanır sanılıyordu. Kural: coin 24 sa'te −%45 VE piyasa medyanı −%3.
  const ce = A.coin_esik!=null ? A.coin_esik : 0.45;
  const st = A.stop!=null ? `stop: coin −%${Math.round(ce*100)} ve piyasa −%${Math.round(A.stop*100)}` : "koşullu stop yok";
  const ac = A.stop!=null ? `24 saatlik koşullu stop: long, coin 24 saatte −%${Math.round(ce*100)} düştüğünde VE piyasanın ortanca 24 sa getirisi −%${Math.round(A.stop*100)} ya da daha kötüyken kapanır. Tek coin çöküşünde (piyasa sakinken) kapanmaz.` : "";
  return `<div class="d">${ad} · ${A.gross.toFixed(2).replace(".",",")}x</div><span class="k" style="white-space:normal" title="${ac}">${st}</span>${stopDurum(k)}`;
}
// MADDE 753: koşullu stop şu an ne kadar yakın — piyasa medyanı (botun evreni, son kapanmış 4 sa mumu) ve eşiğe en yakın long'lar
function stopDurum(k){
  const D = k.stop_durum; if (!D || D.kapali || !k.ayar || k.ayar.stop==null) return "";
  const ep = D.esik_piyasa, ec = D.esik_coin, med = D.medyan;
  const pyz = v => v==null ? "—" : (v>=0?"+":"−") + "%" + Math.abs(v*100).toFixed(1).replace(".",",");
  const yakin = Object.entries(D.coin||{}).filter(([,v])=>v <= -ec*0.5).sort((a,b)=>a[1]-b[1]).slice(0,3);
  const ps = D.piyasa_sart ? `<b class="eks">şart var</b>` : `<span class="art">şart yok</span>`;
  const cl2 = yakin.length ? yakin.map(([s,v])=>`<span class="${v<=-ec?'eks':'uyr'}">${s} ${pyz(v)}</span>`).join(", ") + ` / −%${Math.round(ec*100)}` : "eşiğe yakın long yok";
  return `<div class="k" style="white-space:normal;margin-top:3px;line-height:1.45" title="Bot her dilim turunda bakar. Long, coin 24 sa ≤ −%${Math.round(ec*100)} VE piyasa medyanı ≤ −%${Math.round(ep*100)} ise kapanır. Ölçüm saatte bir (botla aynı yöntem: son kapanmış 4 sa mumu, ${D.n} coinlik evren).">piyasa ${pyz(med)} / −%${Math.round(ep*100)} · ${ps}<br>${cl2} <span style="opacity:.7">· ${D.saat_ad}${D.bayat?" ESKİ":""}</span></div>`;
}
function dilimKart(D){
  if (!D) return `<div class="d">—</div>`;
  const kalan = D.zaman - Date.now()/1000;
  const sure = kalan <= 0 ? (kalan > -1800 ? "şimdi" : "gecikti") : (kalan >= 3600 ? `${Math.floor(kalan/3600)} sa ${Math.floor(kalan%3600/60)} dk` : `${Math.ceil(kalan/60)} dk`);
  return `<div class="halkali">${halka(D.dolu, D.n)}<div style="min-width:0"><div class="d ${kalan<=-1800?'eks':''}">${sure}</div><span class="k">saat ${D.saat}</span></div></div>`;
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
    ${I.karar ? satir("Giriş: TOPLAM kayma (karar fiyatına göre)", `${bp(I.karar.bp)} <span class="k">(ilk deneme ${bp(I.karar.giris)} · kovala ${bp(I.karar.kovala)} · piyasa ${bp(I.karar.piyasa)} · ${I.karar.n} dolum)</span>`, I.karar.bp>5?"eks":"") : ""}
    ${satir("Gerçek komisyon (model 5 bp)", bp(G.komisyon_bp), G.komisyon_bp==null?"":(G.komisyon_bp>6?"eks":""))}
    ${satir("GTX ilk deneme · kovalama · piyasaya düşen", `${G.gtx_ilk||0} · ${G.kovala||0} · ${G.piyasa_yedek||0}`, (G.piyasa_yedek||0)>0?"eks":"")}
  </table></div><div class="k" style="margin-top:6px">Referans (madde 695): TP dolum ≥ %90 güvenli, ≤ %80 alarm; dolum %70'te yıllık −29 puan.
  Kayma eksi = daha iyi doldu. "Gönderim fiyatına göre" her emri kendi gönderildiği anla kıyaslar; "karar fiyatına göre" turun ilk emrindeki
  fiyatla — beklerken fiyatın kaçması ve piyasa emrine düşme dahil, asıl maliyet bu (backtest girişe +5 bp varsayar). Yalnız kayıt; bot kararlarını etkilemez.</div>`;
}
// MADDE 757: D TASARIMI — ÖZET. Üstte tek cümlelik durum, büyük kitap, zaman seçici grafiğin yanında, yalnız dikkat isteyen
// şey renkli kartla (varsayılan nötr), "nereden geldi" tek çubuk + 4 kalem, sıradaki dilim / funding tek satır.
function dikkatler(k){
  const out = [], sv = k.servis;
  if (sv && sv!=="active" && sv!=="—" && sv!=="?") out.push({sev:"eks", baslik:"Bot çalışmıyor", metin:`Servis durumu: ${sv}. Sunucuyu kontrol et.`});
  const D = k.stop_durum, P = k.pozisyonlar || {};
  if (D && !D.kapali){
    const ec = D.esik_coin, pyz = v => v==null ? "—" : (v>=0?"+":"−") + "%" + Math.abs(v*100).toFixed(1).replace(".",",");
    for (const [s,p] of Object.entries(P)){
      const v = (D.coin||{})[s.replace(/USDT$/,"")]; if (p.miktar<=0 || v==null || v > -ec*0.8) continue;
      const c = s.replace(/USDT$/,"");
      out.push({sev: v <= -ec ? "eks" : "uyari", sem: s, baslik:`Stop şartına yakın: ${c}`,
        metin:`Piyasa ${pyz(D.medyan)} (eşik −%${Math.round(D.esik_piyasa*100)}, ${D.piyasa_sart?"şart var":"şart yok"}). ${c} 24 saatte ${pyz(v)}; −%${Math.round(ec*100)} olursa${D.piyasa_sart?"":" ve piyasa da eşiği geçerse"} sıradaki turda kapanır.`});
    }
  }
  if (k.poz_kaynak && k.poz_kaynak!=="canlı") out.push({sev:"uyari", baslik:"Canlı pozisyon verisi yok", metin:"Pozisyonlar günlük defterden gösteriliyor (anlık görüntü servisi gecikmiş olabilir)."});
  return out;
}
function dikkatHtml(k){
  return dikkatler(k).map(d=>`<div class="ddk ${d.sev}"${d.sem?` onclick="sheetAc('${d.sem}')" role="button"`:""}><div class="ddb"><b>${d.baslik}</b>${d.sem?'<span class="k">ayrıntı ›</span>':""}</div><div class="ddm">${d.metin}</div></div>`).join("");
}
function durumCumle(k){   // madde 758: kısa — bugünkü tutar hemen altta, tekrar etmez
  const sv = k.servis, ok = !sv || sv==="active" || sv==="—" || sv==="?", n = dikkatler(k).length;
  return `<span class="dnok ${ok?"":"yok"}"></span>${ok ? "Bot çalışıyor" : '<b class="eks">Bot çalışmıyor</b>'} · ${n ? `<span class="uyr">${n} konu dikkat istiyor</span>` : "her şey yolunda"}`;
}
function daltHtml(k, kar){
  const B = bugunKZ(k), ok = v => v>=0 ? "▲" : "▼", ko = k.kitap_bas ? kar / k.kitap_bas : null;
  return `${B ? `<span class="${sinif(B.usd)}">${ok(B.usd)} ${isaretli(B.usd)} (${yz(B.oran)}) bugün</span>` : ""}${kar!=null ? `<span class="${sinif(kar)}">${ok(kar)} ${isaretli(kar)}${ko!=null?` (${yz(ko)})`:""} başlangıçtan</span>` : ""}`;
}
function nerdenHtml(k, poz, kar){
  const D = k.dokum; if (!D || poz==null || kar==null) return "";
  const gz = FG && k.gercek && D.funding_gercek!=null, F = gz ? D.funding_gercek : D.funding, dg = D.diger_gelir||0;
  const fark = kar - poz - D.gerceklesen - F - D.komisyon - dg;
  const K = [["Kapanan", D.gerceklesen, "--vurgu"], ["Funding", F, "--art"], ["Açık", poz, "--eks"], ["Komisyon", D.komisyon, "--uyari"]];
  const tm = K.reduce((a,x)=>a+Math.abs(x[1]), 0) || 1;
  return `<div class="dnb">${K.map(x=>`<span style="flex:${Math.max(0.6, Math.abs(x[1])/tm*100).toFixed(1)};background:${css(x[2])}"></span>`).join("")}</div>
    <div class="dng">${K.map(x=>`<span><span class="k"><i style="background:${css(x[2])}"></i>${x[0]}</span><b class="${sinif(x[1])}">${isaretli(x[1])}</b></span>`).join("")}</div>
    ${Math.abs(fark) >= 3 || dg ? `<div class="k" style="margin-top:8px" title="Başlangıç kaydı anı ve demo / gerçek fiyat farkı">başlangıç farkı ${isaretli(fark)}${dg?` · diğer ${isaretli(dg)}`:""}</div>` : ""}`;
}
function fgKucuk(k){   // madde 758: gerçek / demo funding seçici — küçük, ayrıntı dokununca
  if (!k.gercek) return "";
  const g = k.gercek;
  return `<span class="fgk"><button class="${FG?"on":""}" onclick="fgSec(true)">gerçek</button><button class="${!FG?"on":""}" onclick="fgSec(false)">demo</button><button class="fgi" onclick="const a=document.getElementById('fgacik'); a.hidden=!a.hidden" aria-label="funding açıklaması">ⓘ</button></span>
    <div id="fgacik" class="fgacik" hidden>Demo borsa funding'i kendi oranıyla öder. "Gerçek" aynı pozisyonların gerçek Binance oranlarıyla alacağını gösterir (fark ${isaretli(g.fark)}); kitap ve kâr da buna göre.${g.duzeltilmeyen ? ` İlk ${g.duzeltilmeyen} günün günlük getirisi demo funding'le kaldı.` : ""}</div>`;
}
function dilimMetin(D){
  if (!D) return "—"; const kalan = D.zaman - Date.now()/1000;
  return (kalan <= 0 ? (kalan > -1800 ? "şimdi" : "gecikti") : sureYaz(kalan)) + ` <span class="k">${D.dolu}/${D.n}</span>`;
}
function fundMetin(k){
  let T = null; for (const s of Object.keys(k.pozisyonlar||{})){ const F = FUND[s]; if (F && F.T) T = T==null ? F.T : Math.min(T, F.T); }
  return T==null ? "—" : sureYaz(Math.max(0, (T - Date.now())/1000));
}
function ozetSayfa(k, svc, sv){   // madde 758: sade — kahraman alan kartsız, bölümler ayrı kartlarda, tekrar yok
  const kitap = k.kitap_canli!=null ? k.kitap_canli : k.kitap; AKIS.kitapd = AKIS.kitapd || {v: kitap};
  const A = k.ayar, ayar = A ? `${A.profil||k.profil||"—"} · ${A.gross.toFixed(2).replace(".",",")}x` : (k.profil||"");
  const ch = (m, ad) => `<button data-m="${m}" class="${egriMod==m?"on":""}" onclick="egriSec('${m}')">${ad}</button>`;
  return `<div class="dhero">
    <div class="dcumle" id="dcumle">${durumCumle(k)}</div>
    <div class="dbuyuk" id="kitapd">${para(AKIS.kitapd.v)}</div>
    <div class="dalt" id="dalt">${daltHtml(k, k.kar_usd)}</div>
    <div class="dgr"><div class="mod">${ch("bugun","1G")}${ch("hafta","1H")}${ch("tum","Tümü")}</div><div id="egri">${egriIc(k)}</div></div>
  </div>
  <div id="dikkat">${dikkatHtml(k)}</div>
  ${k.dokum&&k.gerceklesmemis!=null?`<div class="kart dnerden"><div class="dnh"><span class="dnk">Başlangıçtan beri nereden geldi</span>${fgKucuk(k)}</div><div id="nerden">${nerdenHtml(k, k.gerceklesmemis, k.kar_usd)}</div></div>`:""}
  <div class="dikili"><div class="kart"><div class="k">Sıradaki dilim</div><div class="dkv" id="dilimd">${dilimMetin(k.dilim)}</div><div class="k">${ayar}</div></div>
    <div class="kart"><div class="k">Sıradaki funding</div><div class="dkv" id="fundd">${fundMetin(k)}</div><div class="k">canlı oranla</div></div></div>`;
}
// MADDE 757: D TASARIMI — POZİSYONLAR. Filtre (Tümü / Long / Short) + sıralama, long ve short ayrı bölüm, satırda büyüklük,
// mini grafik ve ▲▼ kâr / zarar; dokununca alttan açılan sayfada ayrıntı (grafik, giriş, funding, hedef, stop).
let POZ_F = (()=>{ try { return localStorage.getItem("carry_pf") || "tum"; } catch(_){ return "tum"; } })();
let POZ_S = (()=>{ try { return localStorage.getItem("carry_ps") || "kz"; } catch(_){ return "kz"; } })();
function pozFiltre(f){ POZ_F = f; try { localStorage.setItem("carry_pf", f); } catch(_){} ciz(); }
function pozSira(){ POZ_S = POZ_S=="kz" ? "buyuk" : "kz"; try { localStorage.setItem("carry_ps", POZ_S); } catch(_){} ciz(); }
function pozDeger(s, p){
  const f = FIYAT[s] || p.isaret, ok = f && p.giris>0 && p.miktar;
  return {f, ky: ok ? (f/p.giris - 1) * (p.miktar>0 ? 1 : -1) * 100 : p.kar_yuzde, g: ok ? p.miktar * (f - p.giris) : p.gerceklesmemis, usd: ok ? Math.abs(p.miktar) * f : p.usd};
}
function stopYakin(k, s, p){
  const D = k.stop_durum; if (!D || D.kapali || p.miktar<=0) return null;
  const v = (D.coin||{})[s.replace(/USDT$/,"")]; return v!=null && v <= -D.esik_coin*0.5 ? v : null;
}
function minik(s, p, f, renk){   // satır içi mini grafik: yalnız çizgi (60x24)
  const M = MUM[s]; if (!M || M.bas !== gunBasi() || !M.nok.length) return `<svg class="dsp" viewBox="0 0 60 24" aria-hidden="true"></svg>`;
  const v = M.nok.map(n=>n[1]); if (f) v.push(f); if (v.length < 2) return `<svg class="dsp" viewBox="0 0 60 24" aria-hidden="true"></svg>`;
  let lo = Math.min(...v), hi = Math.max(...v); const m = Math.max(hi - lo, 0.01 * (f || v[v.length-1])); const o = (lo + hi) / 2; lo = o - m/2; hi = o + m/2;
  const d = v.map((x,i)=>`${i?"L":"M"}${(1 + i/(v.length-1)*58).toFixed(1)} ${(22 - (x-lo)/(hi-lo)*20).toFixed(1)}`).join("");
  return `<svg class="dsp" viewBox="0 0 60 24" aria-hidden="true"><path d="${d}" fill="none" stroke="${renk}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
function satirD(s, p, k){
  const {f, ky, g, usd} = pozDeger(s, p), renk = css((g||0) >= 0 ? "--art" : "--eks"), sv = stopYakin(k, s, p), ec = (k.stop_durum||{}).esik_coin;
  const pc = v => (v>=0?"+":"−") + Math.abs(v).toFixed(1).replace(".",",") + "%";
  return `<div class="dc"><div class="da"><b>${s.replace(/USDT$/,"")}</b>${sv!=null?`<span class="dst ${sv<=-ec?"e":""}">stop ${(sv*100).toFixed(1).replace(".",",")} / −${Math.round(ec*100)}</span>`:""}</div><div class="du">${para(usd)}</div></div>
    ${minik(s, p, f, renk)}<div class="dv"><b class="${sinif(g)}">${g==null?"—":(g>=0?"▲ ":"▼ ")+isaretli(g)}</b><span class="${sinif(ky)}">${ky==null?"":pc(ky)}</span></div>`;
}
function pozSayfa(k){
  const P = Object.entries(k.pozisyonlar||{}).map(([s,p])=>[s, p, pozDeger(s,p)]);
  const sira = (A) => A.sort((a,b)=> POZ_S=="kz" ? (a[2].g||0) - (b[2].g||0) : (b[2].usd||0) - (a[2].usd||0));
  const L = sira(P.filter(x=>x[1].yon=="L")), S = sira(P.filter(x=>x[1].yon=="S"));
  const top = (A, i) => A.reduce((a,x)=>a+(i ? (x[2].g||0) : (x[2].usd||0)), 0), tum = top(P,1);
  const bolum = (A, y, ad) => !A.length || (POZ_F!="tum" && POZ_F!=y) ? "" : `<div class="dbol"><span>${ad} · ${A.length} · <span id="taraf-${y}">${para(top(A,0))} · <span class="${sinif(top(A,1))}">${top(A,1)>=0?"▲":"▼"} ${isaretli(top(A,1))}</span></span></span></div>
    <div class="dlis">${A.map(x=>`<div class="drow ${y}" id="t-${x[0]}" onclick="sheetAc('${x[0]}')" role="button">${satirD(x[0], x[1], k)}</div>`).join("")}</div>`;
  const fb = (f, ad) => `<button class="${POZ_F==f?"on":""}" onclick="pozFiltre('${f}')">${ad}</button>`;
  return `<div class="kart dpoz">
    <div class="dpb"><span class="gb">Pozisyonlar</span>${k.gerceklesmemis!=null?`<b id="gerc" class="${sinif(tum)}">${tum>=0?"▲":"▼"} ${isaretli(tum)}</b>`:""}</div>
    ${P.length?`<div class="denge" id="denge">${dengeIc({L:[top(L,0),0], S:[top(S,0),0]})}</div>`:""}
    <div class="dfil"><div class="gdon">${fb("tum",`Tümü ${P.length}`)}${fb("L","Long")}${fb("S","Short")}</div><button class="dsir" onclick="pozSira()">Sırala: ${POZ_S=="kz"?"K/Z":"büyüklük"}</button></div>
    ${bolum(L,"L","LONG") + bolum(S,"S","SHORT") || "<div class='bos'>açık pozisyon yok</div>"}
    <div class="k" style="margin-top:10px">${k.poz_kaynak=="canlı"?"liste "+k.poz_zaman:"günlük defter "+(k.poz_zaman||"")} · satıra dokun: grafik, giriş, funding, hedef, stop</div></div>`;
}
// MADDE 757: pozisyon ayrıntısı — alttan açılan sayfa (bottom sheet); canlı fiyatla saniyede bir güncellenir
let SHEET = null;
function sheetAc(s){ SHEET = s; const k = VERI.kurulumlar[secili]; if (!k.pozisyonlar[s]) return; const el = $("#sheet"); el.hidden = false; el.innerHTML = `<div class="shb" onclick="sheetKapat()"></div><div class="shp" role="dialog" aria-label="${s.replace(/USDT$/,"")} ayrıntı"><div class="shh"></div><div id="sheetic">${sheetIc(s, k.pozisyonlar[s], k)}</div></div>`; document.body.style.overflow = "hidden"; }
function sheetKapat(){ SHEET = null; const el = $("#sheet"); el.hidden = true; el.innerHTML = ""; document.body.style.overflow = ""; }
addEventListener("keydown", e=>{ if (e.key === "Escape" && SHEET) sheetKapat(); });
function sheetIc(s, p, k){
  const {f, ky, g, usd} = pozDeger(s, p), renk = css((g||0) >= 0 ? "--art" : "--eks"), uzun = p.miktar > 0;
  const M = MUM[s], acilis = M && M.bas===gunBasi() && M.nok.length ? M.nok[0][1] : null, bg = acilis && f ? (f/acilis - 1) : null;
  const W = Math.max(240, Math.min(560, innerWidth) - 48);
  const F = FUND[s], fr = F && p.miktar ? -p.miktar * f * F.r : null;
  const D = k.stop_durum, sv = uzun && D && !D.kapali ? (D.coin||{})[s.replace(/USDT$/,"")] : null, ec = D ? D.esik_coin : 0.45;
  const pyz = v => v==null ? "—" : (v>=0?"+":"−") + "%" + Math.abs(v*100).toFixed(1).replace(".",",");
  const kutu = (e, d) => `<div class="shk"><div class="k">${e}</div><div class="shd">${d}</div></div>`;
  const H = (k.hedef||{})[uzun ? "L" : "S"] || [], h0 = H.length && p.giris>0 ? p.giris * (1 + (uzun?1:-1) * H[0]) : null;
  const stop = sv==null ? "" : `<div class="shs"><div class="shr"><span class="k">Koşullu stop · coin 24 sa</span><span>${pyz(sv)} / <b>−%${Math.round(ec*100)}</b></span></div>
      <div class="shc"><span style="width:${Math.min(100, Math.max(0, -sv/ec*100)).toFixed(0)}%;background:${css(sv<=-ec?"--eks":sv<=-ec*0.5?"--uyari":"--soluk")}"></span></div>
      <div class="shr" style="margin-top:10px"><span class="k">Piyasa medyanı 24 sa</span><span class="${D.piyasa_sart?"uyr":""}">${pyz(D.medyan)} / −%${Math.round(D.esik_piyasa*100)} · ${D.piyasa_sart?"şart var":"şart yok"}</span></div></div>`;
  const neden = sv!=null && sv <= -ec*0.5 ? `<p class="shn"><b>Neden hâlâ açık?</b> Stop iki şart birden sağlanınca çalışır: coin 24 saatte −%${Math.round(ec*100)} ve piyasa medyanı −%${Math.round(D.esik_piyasa*100)}. ${D.piyasa_sart ? `Piyasa şartı var, ama ${s.replace(/USDT$/,"")}'nin düşüşü henüz −%${Math.round(ec*100)}'e ulaşmadı.` : "Şu an piyasa şartı yok (tek coin düşüşü; araştırmada bu durumda tutmak daha iyi çıktı, madde 621)."} İkisi birlikte gerçekleşirse bot sıradaki dilim turunda kapatır.</p>` : "";
  return `<div class="shu"><div><div style="display:flex;align-items:center;gap:8px"><span class="gb">${s.replace(/USDT$/,"")}</span><span class="dst ${uzun?"l":"s"}">${uzun?"LONG":"SHORT"}</span></div>
      <div class="shf">${fiyatYaz(f)}</div><div class="${sinif(g)}" style="font-weight:600;font-size:13.5px">${g>=0?"▲":"▼"} ${ky==null?"":(ky>=0?"+":"−")+Math.abs(ky).toFixed(1).replace(".",",")+"%"} · ${isaretli(g)}${bg!=null?` <span class="k">· bugün ${yz(bg)}</span>`:""}</div></div>
      <button class="shx" onclick="sheetKapat()" aria-label="Kapat">✕</button></div>
    <div class="shg">${kivilcim(s, p, f, renk, W, 110)}</div>
    <div class="shkg">${kutu("Giriş", fiyatYaz(p.giris))}${kutu("Büyüklük", para(usd))}${kutu("Funding", F ? `%${(F.r*100).toFixed(4).replace(".",",")} · <span class="${sinif(fr)}">${fr>=0?"alıyor":"ödüyor"}</span>` : "—")}${kutu("Kâr al hedefi", h0 ? `${fiyatYaz(h0)} <span class="k">${uzun?"+":"−"}%${Math.round(H[0]*100)}</span>` : "—")}</div>
    ${stop}${neden}`;
}
// MADDE 756: SADE GEÇMİŞ — büyük toplam, Hafta / Ay / Tümü, tek grafik (günlük çubuklar), gün listesi. Tutarlar kitap
// zincirinden (gün = gün sonu kitabı − önceki gün sonu; bugün = şimdiki kitap − dünkü gün sonu): liste toplamı = büyük toplam.
let GEC_DONEM = (()=>{ try { return localStorage.getItem("carry_gec") || "ay"; } catch(_){ return "ay"; } })();
function gecDonem(d){ GEC_DONEM = d; try { localStorage.setItem("carry_gec", d); } catch(_){} ciz(); }
const GUN_AD = ["Pazar","Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi"];
function gecGunler(k){
  const S = seriCanli(k), out = [];
  for (let i = 1; i < S.length; i++){
    const o = S[i-1].kitap, n = S[i].kitap; if (o==null || n==null || !S[i].tarih) continue;
    out.push({t: S[i].tarih, usd: n - o, oran: o > 0 ? (n - o) / o : null, bas: o, canli: !!S[i].canli && S[i].kesin !== false, kesinlesiyor: S[i].kesin === false, ilk: i === 1});
  }
  return out;
}
function gecmisSade(k){
  const G = gecGunler(k);
  if (!G.length) return `<div class="kart bos">Henüz tamamlanmış gün yok. İlk gün sonu kaydı 03:05'te.</div>`;
  const son = G[G.length-1].t, ay = son.slice(0,7);
  const kes = GEC_DONEM=="hafta" ? new Date(Date.parse(son+"T00:00:00Z") - 6*864e5).toISOString().slice(0,10) : GEC_DONEM=="ay" ? ay+"-01" : "";
  let D = G.filter(g=>g.t >= kes);
  let birim = "gün";
  if (D.length > 31){   // Tümü uzun: ay ay
    const A = {}; for (const g of D){ const a = g.t.slice(0,7); (A[a] = A[a] || {t: a, usd: 0, bas: g.bas, canli: false}).usd += g.usd; A[a].canli = A[a].canli || g.canli; }
    D = Object.values(A).map(a=>({...a, oran: a.bas > 0 ? a.usd / a.bas : null})); birim = "ay";
  }
  const top = D.reduce((a,g)=>a+g.usd, 0), bas = D[0].bas, oran = bas > 0 ? top / bas : null;
  const ad = g => birim=="ay" ? `${AYAD[+g.t.slice(5,7)-1]} ${g.t.slice(0,4)}` : g.canli ? "Bugün" : `${GUN_AD[new Date(g.t+"T00:00:00Z").getUTCDay()]} ${+g.t.slice(8,10)} ${AYAD[+g.t.slice(5,7)-1]}`;
  const kisa = g => birim=="ay" ? AYAD[+g.t.slice(5,7)-1].slice(0,3) : g.canli ? "bugün" : String(+g.t.slice(8,10));
  const not = g => g.canli ? "canlı · yarın 03:05'te kesinleşir" : g.kesinlesiyor ? "gün kapandı · kayıt 03:05'te yazılıyor" : (g.ilk && birim=="gün") ? "başlangıç günü" : "";
  const baslik = GEC_DONEM=="hafta" ? "Son 7 gün" : GEC_DONEM=="ay" ? `${AYAD[+ay.slice(5,7)-1]}` : "Başlangıçtan beri";
  // çubuklar: sıfır çizgisi en büyük kazanç / kayıp oranına göre; 170 px
  const H = 170, mp = Math.max(0, ...D.map(g=>g.usd)), mn = Math.max(0, ...D.map(g=>-g.usd)), et = D.length <= 12;
  const ic = H - (et ? 36 : 8), olc = (mp + mn) > 0 ? ic / (mp + mn) : 0, sifir = (et ? 18 : 4) + mp * olc;
  const cub = D.map(g=>{ const b = Math.max(3, Math.abs(g.usd) * olc), art = g.usd >= 0, r = css(art ? "--art" : "--eks");
    const tp = art ? sifir - b : sifir, eT = art ? sifir - b - 16 : sifir + b + 3;
    return `<div class="gc"><span class="ge n ${art?"art":"eks"}" style="top:${eT}px">${et ? (art?"+":"−") + Math.abs(g.usd).toFixed(0) : ""}</span>
      <i style="top:${tp}px;height:${b}px;background:${g.canli ? `color-mix(in srgb, ${r} 35%, transparent)` : r};${g.canli ? `border:1.5px dashed ${r}` : ""}" title="${ad(g)} ${isaretli(g.usd)}"></i></div>`; }).join("");
  const adim = Math.ceil(D.length / 8);
  const alt = D.map((g,i)=>`<span class="${g.canli?"bg":""}">${(i % adim === 0 || i === D.length-1) ? kisa(g) : ""}</span>`).join("");
  const liste = D.slice().reverse().map(g=>`<div class="gs"><div><div class="ga">${ad(g)}</div>${not(g)?`<div class="gn">${not(g)}</div>`:""}</div>
    <div style="text-align:right"><div class="gv n ${sinif(g.usd)}">${isaretli(g.usd)}</div><div class="gn n">${yz(g.oran)}</div></div></div>`).join("");
  const dk = d => `<button class="${GEC_DONEM==d?"on":""}" onclick="gecDonem('${d}')">${{hafta:"Hafta", ay:"Ay", tum:"Tümü"}[d]}</button>`;
  return `<div class="kart gsade">
    <div class="gust"><span class="gb">Geçmiş</span><div class="gdon">${dk("hafta")}${dk("ay")}${dk("tum")}</div></div>
    <div class="gk">${baslik} · toplam kâr / zarar</div>
    <div class="gt n">${top<0?"−":"+"}${Math.abs(top).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2})} <small>$</small></div>
    <div class="go n ${sinif(top)}">${top>=0?"▲":"▼"} %${Math.abs((oran||0)*100).toFixed(2).replace(".",",")} · ${D.length} ${birim}</div>
    <div class="gcub" style="height:${H}px"><b style="top:${sifir}px"></b>${cub}</div><div class="galt n">${alt}</div>
    <div class="gliste">${liste}</div></div>`;
}
function gecmisSayfa(k){
  const grafikVar = (k.seri||[]).length >= 3;   // madde 734/737: 1-2 noktalık grafik bilgi vermez, yalnız yer kaplar
  const ac = ACIK.has("gecay");   // madde 756: eski ayrıntılar (takvim, yıllık, grafikler, coinler, icra) kapalı bölümde
  return `<div id="gsade">${gecmisSade(k)}</div>` + `<div class="kart" style="padding:0"><button class="gayr" onclick="olayAc('gecay')">${ac?"▾":"▸"} Ayrıntılar <span class="k">takvim · coinler · icra</span></button></div>` + (!ac ? "" : `<div class="kart"><h2>Günlük takvim <span class="k">· kazanç yeşil, kayıp kırmızı (koyuluk = büyüklük)</span></h2>${takvim(k)}
      ${k.dokum?`<div class="k" style="margin-top:6px">Başlangıçtan beri: funding ${isaretli(k.dokum.funding)}${k.dokum.funding_gercek!=null?` (gerçek oranlarla ${isaretli(k.dokum.funding_gercek)})`:""} · komisyon ${isaretli(k.dokum.komisyon)}</div>`
        :(k.funding_top||k.komisyon_top)?`<div class="k" style="margin-top:6px">Defter toplamı (yaklaşık): funding ${isaretli(k.funding_top)} · komisyon ${isaretli(k.komisyon_top)}</div>`:""}
      <div class="k" style="margin-top:4px">Her gün, Binance gününe (03:00 – 03:00) göre. ● işaretli gün bugün: canlı, gün sonunda (03:05) kesinleşir.</div></div>
    <div class="kart"><h2>Son 1 yıl</h2>${yillik(k)}</div>
    ${grafikVar?`<div class="iki"><div class="kart"><h2>Kitap ($)</h2><div class="grafik"><canvas id="g1"></canvas></div></div>
      <div class="kart"><h2>Günlük getiri</h2><div class="grafik"><canvas id="g2"></canvas></div></div></div>`
      :`<div class="kart bekle">Kitap ve günlük getiri grafikleri 3 günlük veri birikince görünür (şu an ${(k.seri||[]).length} gün).</div>`}
    ${coinTablo(k)}
    <div class="kart"><h2>İcra · son 30 gün <span class="k">(emir defteri)</span></h2>${icraKart(k)}</div>`);
}
// MADDE 753: coin bazında başlangıçtan beri kâr / zarar (borsa gelir kayıtları + açık pozisyon)
function coinTablo(k){
  const C = k.coin_ozet; if (!C || !C.length) return "";
  const id = "coinler", ac = ACIK.has(id), L = ac ? C : [...C.slice(0,5), ...C.slice(-5).filter(x=>!C.slice(0,5).includes(x))];
  const h = v => Math.abs(v) < 0.005 ? `<span class="k">0</span>` : `<span class="${sinif(v)}">${isaretli(v)}</span>`;
  const sat = L.map(x=>`<tr><td class="l"><b>${x.s}</b>${x.yon?`<span class="yon">${MOBIL() ? x.yon : (x.yon=="L"?"long açık":"short açık")}</span>`:""}</td><td>${h(x.kapanan)}</td><td>${h(x.funding)}</td><td>${h(x.komisyon)}</td><td>${h(x.acik)}</td><td><b>${h(x.toplam)}</b></td></tr>`).join("");
  const T = C.reduce((a,x)=>({kp:a.kp+x.kapanan, f:a.f+x.funding, km:a.km+x.komisyon, a:a.a+x.acik, t:a.t+x.toplam}), {kp:0,f:0,km:0,a:0,t:0});
  return `<div class="kart"><h2>Coin bazında kâr / zarar <span class="k">· başlangıçtan beri, en kötüden en iyiye</span></h2>
    <div class="tablo yatay"><table class="coin"><tr class="k"><td class="l">coin</td><td>kapanan</td><td>funding</td><td>komisyon</td><td>açık</td><td>toplam</td></tr>${sat}
    <tr><td class="l"><b>Toplam (${C.length} coin)</b></td><td>${h(T.kp)}</td><td>${h(T.f)}</td><td>${h(T.km)}</td><td>${h(T.a)}</td><td><b>${h(T.t)}</b></td></tr></table></div>
    ${C.length>10?`<div class="isl"><span class="ac" onclick="olayAc('${id}')">${ac?"▾ en kötü / en iyi 5'e dön":`▸ tüm coinler (${C.length})`}</span></div>`:""}
    <div class="k" style="margin-top:6px">Kapanan, funding ve komisyon borsanın gelir kayıtlarından${k.mod=="demo"?" (funding: demo hesabın aldığı)":""}; açık = şu anki gerçekleşmemiş kâr / zarar.${MOBIL()?" Telefonda komisyon sütunu gizli (toplama dahil).":""}</div></div>`;
}
// MADDE 740: olaylar zaman çizelgesi — gün gün (Bugün / Dün / tarih), türe göre simge
const OLAY_SIMGE = {basla:"▶", ayar:"⚙", stop:"■", stop_tut:"□", delist:"!", saglik:"♥", hata:"✕", tp:"✓", uyari:"⚠", tur:"↻", islem:"⇄", funding:"$", postonly:"↺"};
const OLAY_AD = {basla:"başlama", ayar:"ayar", stop:"stop", stop_tut:"stop şartı: piyasa sakin, tutuldu", delist:"delist", saglik:"sağlık",
                 hata:"hata", tp:"kâr al doldu", uyari:"piyasa emrine düşüldü", tur:"dilim turu", islem:"işlem", funding:"funding ödemesi",
                 postonly:"post-only emir reddedildi — normal, bot piyasa emrine geçer"};
// MADDE 745: her dilim turunun altında o turun işlemleri (coin, yön, adet, dolum fiyatı, limit / piyasa) ve işlemden sonra
// coinin pozisyonu ve ORTALAMA girişi (Binance entryPrice, 5 dk'lık görüntüden). Tura bağlanmayan dolumlar (kâr al vb.) ayrı olay.
const dk_ = s => Date.UTC(+s.slice(0,4), +s.slice(5,7)-1, +s.slice(8,10), +s.slice(11,13), +s.slice(14,16)) / 60000;
function olayIslem(k){
  const L = ((k.islemler||{}).liste||[]).map(x=>({...x, m: dk_(x.zaman)})), kul = new Set(), out = [];
  for (const o of (k.olaylar||[])){
    if (o.tur==="tur" && o.zaman){ const m = dk_(o.zaman);
      const b = L.filter((x,i)=>!kul.has(i) && x.m>=m-5 && x.m<=m+25 && kul.add(i)); out.push(b.length ? {...o, islem: b} : o);
    } else out.push(o);
  }
  const kalan = L.filter((x,i)=>!kul.has(i)); let grup = null;
  for (const x of kalan){   // liste yeniden eskiye; 10 dk içindekiler tek olay
    if (grup && grup.m - x.m <= 10){ grup.islem.push(x); continue; }
    grup = {zaman: x.zaman, tur: "islem", m: x.m, islem: [x]}; out.push(grup);
  }
  for (const g of out) if (g.tur==="islem") g.metin = g.islem.length==1 ? `${g.islem[0].sembol} · ${g.islem[0].tur}` : `${g.islem.length} işlem`;
  // madde 754: ham log satırları kısa Türkçe cümle (özellikle telefonda dört satıra yayılıyordu)
  const ss = v => (+v).toLocaleString("tr-TR", {maximumFractionDigits: 0});
  for (const o of out){
    const m = o.tur==="tur" && /bakiye ([\d.]+) USDT \| dilim (\d+\/\d+) yenilendi \| (\d+) pozisyon \| LONG funding ort %(-?[\d.]+)\/yıl \| SHORT %(-?[\d.]+)\/yıl/.exec(o.metin||"");
    if (m) o.metin = `Dilim ${m[2]} yenilendi | ${m[3]} pozisyon · bakiye ${ss(m[1])} $ · funding yıllık long ${ss(m[4])}% / short ${ss(m[5])}%` + (o.metin.split("/yıl").slice(2).join("/yıl") || "");
    const u = o.tur==="uyari" && /(\d+) emir dolmadı/.exec(o.metin||"");
    if (u) o.metin = `${u[1]} emir limitte dolmadı, piyasa emriyle tamamlandı`;
  }
  // madde 750: turdaki / gruptaki kısmi ve tam kapanışların gerçekleşen kârı olay satırına
  for (const g of out){ const kp = (g.islem||[]).filter(x=>x.kapanis_kar!=null); if (!kp.length) continue;
    const top = kp.reduce((a,x)=>a+x.kapanis_kar,0), tam = kp.filter(x=>x.tam).length, kis = kp.length - tam;
    const ne = [kis ? `${kis} kısmi` : "", tam ? `${tam} tam` : ""].filter(Boolean).join(" + ");
    g.metin += ` | ${ne} kapanış ${isaretli(top)} (${kp.map(x=>x.sembol).filter((v,i,a)=>a.indexOf(v)===i).join(", ")})`; g.kapanis = top; }
  // madde 749: funding ödemeleri (demo hesaba yatan · gerçek oranlarla olsaydı)
  const demo = k.mod=="demo";
  // madde 753: yalnız saatlik ödeyen coinlerin (HOT, INIT…) ödemeleri (UTC saati 4'e bölünmeyen saatler) günde TEK satır
  const ara = {}, ana = [];
  for (const f of (k.fundingler||[])){
    const uh = new Date(f.t*1000).getUTCHours();
    if (uh % 4 === 0) { ana.push(f); continue; }
    const g = (f.zaman||"").slice(0,10), a = ara[g] || (ara[g] = {zaman: f.zaman, n: 0, demo: null, demo_n: 0, gercek: null, gercek_n: 0, coin: {}, saat: []});
    a.n++; a.saat.push(f.zaman.slice(11,13)); if (f.zaman > a.zaman) a.zaman = f.zaman;
    if (f.demo!=null){ a.demo = (a.demo||0) + f.demo; a.demo_n = Math.max(a.demo_n, f.demo_n); }
    if (f.gercek!=null){ a.gercek = (a.gercek||0) + f.gercek; a.gercek_n = Math.max(a.gercek_n, f.gercek_n); }
    for (const c of (f.coin||[])){ const x = a.coin[c.s] || (a.coin[c.s] = {s: c.s, demo: null, gercek: null});
      if (c.demo!=null) x.demo = (x.demo||0) + c.demo; if (c.gercek!=null) x.gercek = (x.gercek||0) + c.gercek; }
  }
  for (const a of Object.values(ara)){
    const f = {...a, coin: Object.values(a.coin).sort((p,q)=>Math.abs(q.gercek??q.demo??0)-Math.abs(p.gercek??p.demo??0))};
    const x = f.demo!=null ? `demo hesaba ${isaretli(f.demo)}` : (demo ? "demo hesaba ödeme yok" : "");
    const y = demo && f.gercek!=null ? `gerçek oranlarla ${isaretli(f.gercek)}` : "";
    out.push({zaman: f.zaman, tur: "funding", fon: f, metin: `Saatlik funding · ${f.n} ödeme | ${f.coin.map(c=>c.s).join(", ")} · ` + [x, y].filter(Boolean).join(" · ")});
  }
  for (const f of ana){
    const a = f.demo!=null ? `demo hesaba ${isaretli(f.demo)} (${f.demo_n} poz)` : (demo ? "demo hesaba ödeme yok" : "");
    const b = demo && f.gercek!=null ? `gerçek oranlarla ${isaretli(f.gercek)} (${f.gercek_n} poz)` : "";
    out.push({zaman: f.zaman, tur: "funding", fon: f, metin: `Funding · ${Math.max(f.gercek_n||0, f.demo_n||0)} pozisyon | ` + [a, b].filter(Boolean).join(" · ")});
  }
  return out.sort((a,b)=>(b.zaman||"").localeCompare(a.zaman||""));
}
function islemTablo(o){
  // MADDE 751: her işlem tek satır grubu — ne oldu (açıldı / eklendi / azaltıldı / kapandı), ne kadar, ve ÖNCE → SONRA
  if (!o.islem || !o.islem.length) return "";
  const id = "isl" + o.zaman + o.tur, ac = ACIK.has(id);
  const tip = x => { const ps = x.poz_sonra, po = x.poz_once, al = x.yon==="BUY";
    const yon = ps ? (ps>0 ? "long" : "short") : (po ? (po>0 ? "long" : "short") : (al ? "long" : "short"));
    let ne;
    if (po===0) ne = "açıldı"; else if (ps===0) ne = "kapandı";
    else if (ps!=null) ne = ((ps>0)===al) ? "eklendi" : "azaltıldı"; else ne = al ? "alındı" : "satıldı";
    return {yon, ne, ekle: ne=="açıldı"||ne=="eklendi"}; };
  const sat = o.islem.map(x=>{ const t = tip(x), L = t.yon=="long";
    const once = x.usd_once!=null ? (x.usd_once===0 ? "0 $" : para(x.usd_once)) : null, sonra = x.poz_sonra===0 ? "0 $" : (x.usd_sonra!=null ? para(x.usd_sonra) : "…");
    const ort = (x.ort_once && x.ort_sonra && Math.abs(x.ort_once/x.ort_sonra-1) > 1e-6) ? ` · ort. ${fiyatYaz(x.ort_once)} → ${fiyatYaz(x.ort_sonra)}`
              : (x.ort_sonra && t.ne=="açıldı" ? "" : (x.ort_sonra ? ` · ort. ${fiyatYaz(x.ort_sonra)}` : ""));
    return `<div style="padding:9px 0;border-top:1px solid var(--cizgi)">
      <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
        <span><b>${x.sembol}</b> <span style="font-size:12px;font-weight:650;color:${L?'var(--vurgu)':'#f59e0b'}">${t.yon} ${t.ne}</span></span>
        <span style="font-weight:650">${t.ekle?"+":"−"}${para(x.usd)}</span></div>
      <div class="s">${x.adet.toLocaleString("tr-TR",{maximumFractionDigits:4})} adet × ${fiyatYaz(x.fiyat)} · ${x.tur}${x.maker===true?" · maker":x.maker===false?" · taker":""}</div>
      <div style="font-size:12.5px;margin-top:2px">${x.kayit_yok && x.poz_sonra==null ? `<span class="s">pozisyon kaydı yok</span>` : (once!=null ? `pozisyon ${once} → <b>${sonra}</b>` : `pozisyon şimdi <b>${sonra}</b>`) + ort}${x.kapanis_kar!=null ? ` · kâr <b class="${sinif(x.kapanis_kar)}">${isaretli(x.kapanis_kar)}</b>` : ""}</div></div>`; }).join("");
  return `<div class="isl"><span class="ac" onclick="olayAc('${id}')">${ac?"▾":"▸"} işlemler (${o.islem.length})</span>${ac ? `<div style="margin-top:4px">${sat}</div>` : ""}</div>`;
}
function fonTablo(o){
  const f = o.fon; if (!f || !f.coin || !f.coin.length) return "";
  const id = "fon" + o.zaman, ac = ACIK.has(id), demo = VERI.kurulumlar[secili].mod=="demo";
  const h = v => v==null ? `<span class="s">—</span>` : `<span class="${sinif(v)}">${isaretli(v)}</span>`;
  const sat = f.coin.map(c=>`<tr><td><b>${c.s}</b></td><td class="r">${h(c.demo)}</td>${demo?`<td class="r">${h(c.gercek)}</td>`:""}</tr>`).join("");
  return `<div class="isl"><span class="ac" onclick="olayAc('${id}')">${ac?"▾":"▸"} coinler (${f.coin.length})</span>${ac ? `<table><tr class="s"><td>coin</td><td class="r">${demo?"demo hesap":"ödeme"}</td>${demo?`<td class="r">gerçek oranla</td>`:""}</tr>${sat}</table>` : ""}</div>`;
}
function olayAc(id){ ACIK.has(id) ? ACIK.delete(id) : ACIK.add(id); ciz(); }
// MADDE 757: D TASARIMI — OLAYLAR. Filtre (Tümü / Dikkat / Dilimler / Kapanışlar / Funding), her gün tek kart, nokta rengi
// önem derecesine göre (kırmızı stop/hata, turuncu dikkat, mavi dilim, yeşil kapanış, gri funding / bilgi).
let OLAY_F = "tum";
function olayFiltre(f){ OLAY_F = f; ciz(); }
const OLAY_GRUP = {stop:"dikkat", stop_tut:"dikkat", hata:"dikkat", delist:"dikkat", saglik:"dikkat", tur:"tur", tp:"kapanis", islem:"kapanis", funding:"funding"};
const OLAY_RENK = {stop:"--eks", hata:"--eks", stop_tut:"--uyari", delist:"--uyari", saglik:"--uyari", tur:"--vurgu", tp:"--art", islem:"--art"};
function olaySayfa(k){
  const bugun = new Date(), t = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  const dun = new Date(bugun); dun.setDate(dun.getDate()-1);
  const ad = g => g==t(bugun) ? "BUGÜN" : g==t(dun) ? "DÜN" : `${+g.slice(8,10)} ${AYAD[+g.slice(5,7)-1].toLocaleUpperCase("tr-TR")} ${g.slice(0,4)}`;
  const esc = x => (x||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");
  const T = olayIslem(k), say = {tum: T.length}; for (const o of T){ const g = OLAY_GRUP[o.tur]; if (g) say[g] = (say[g]||0) + 1; }
  const L = OLAY_F=="tum" ? T : T.filter(o=>OLAY_GRUP[o.tur]===OLAY_F);
  let h = "", onc = null, acik = false;
  for (const o of L){
    const g = (o.zaman||"").slice(0,10);
    if (g!==onc){ if (acik) h += "</div>"; h += `<div class="ogun">${g?ad(g):"—"}</div><div class="okart">`; onc = g; acik = true; }
    const par = (o.metin||"").split(/\s*\|\s*/), bas = par[0], alt = par.slice(1).join(" · ");
    h += `<div class="orow"><span class="onk" style="background:${css(OLAY_RENK[o.tur]||"--soluk")}"></span><div class="om">
      <div class="ob"><span>${esc(bas)}</span><span class="oz">${(o.zaman||"").slice(11)}</span></div>
      ${alt?`<div class="oa">${esc(alt)}</div>`:""}${islemTablo(o)}${fonTablo(o)}</div></div>`;
  }
  if (acik) h += "</div>";
  const fb = (f, adi) => `<button class="${OLAY_F==f?"on":""}" onclick="olayFiltre('${f}')">${adi}${say[f] && f!="tum" ? ` ${say[f]}` : ""}</button>`;
  const bek = (k.islemler||{}).bekleyen||0;
  return `<div class="kart dolay"><span class="gb">Olaylar</span>
    <div class="ofil">${fb("tum","Tümü")}${fb("dikkat","Dikkat")}${fb("tur","Dilimler")}${fb("kapanis","Kapanışlar")}${fb("funding","Funding")}</div>
    ${bek?`<div class="k" style="margin-top:10px">${bek} emrin dolum bilgisi henüz eşlenmedi (birkaç dakika içinde görünür)</div>`:""}
    ${h || "<div class='bos'>bu filtrede olay yok</div>"}</div>
  ${(VERI.paketler||[]).length && !VERI_GOMULU ? `<div class="kart"><h2>Aylık veri paketleri <span class="k">(araştırma: indirip sohbete yükleyin)</span></h2>${VERI.paketler.map(p=>`<div class="zo"><span class="i i-basla">↓</span><div class="m"><a href="paket/${p.ad}" style="color:var(--vurgu)">${p.ad}</a><div class="z">${p.mb} MB</div></div></div>`).join("")}</div>` : ""}`;
}
// MADDE 748: demo kurulumda "gerçek funding ile" görünüm (varsayılan AÇIK): kitap, kâr, günlük getiri ve 7/30 gün / düşüş
// demonun kendi funding'i yerine gerçek Binance oranlarıyla. Ham demo değerleri k._demo'da; anahtar Özet'te.
let FG = (()=>{ try { return localStorage.getItem("carry_fg") !== "0"; } catch(_) { return true; } })();
function gorunum(V){
  for (const k of (V.kurulumlar||[])){
    if (!k.gercek) continue;
    const alan = ["seri","toplam","dd","g7","g30","bugun","aylik","kitap_canli","kar_usd","kar_oran"];
    k._demo = Object.fromEntries(alan.map(a=>[a, k[a]]));
    k._gercek = Object.fromEntries(alan.filter(a=>a in k.gercek).map(a=>[a, k.gercek[a]]));
    Object.assign(k, FG ? k._gercek : {});
  }
  return V;
}
function fgSec(v){
  FG = v; try { localStorage.setItem("carry_fg", v ? "1" : "0"); } catch(_){}
  for (const k of (VERI.kurulumlar||[])) if (k._demo) Object.assign(k, k._demo, FG ? k._gercek : {});
  AKIS.ustk = null; AKIS.kitapd = null; ciz();
}
function fgAnahtar(k){
  if (!k.gercek) return "";
  const g = k.gercek;
  return `<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:6px 0 2px;font-size:12px;color:var(--soluk)">funding:
    <button class="${FG?'on':''}" style="border-radius:999px;border:1px solid var(--cizgi);background:${FG?'color-mix(in srgb,var(--vurgu) 16%,transparent)':'none'};color:${FG?'var(--vurgu)':'var(--soluk)'};font:inherit;padding:4px 10px;cursor:pointer" onclick="fgSec(true)">gerçek Binance</button>
    <button style="border-radius:999px;border:1px solid var(--cizgi);background:${!FG?'color-mix(in srgb,var(--vurgu) 16%,transparent)':'none'};color:${!FG?'var(--vurgu)':'var(--soluk)'};font:inherit;padding:4px 10px;cursor:pointer" onclick="fgSec(false)">demo (ham)</button>
    <span class="fgac" onclick="const a=this.nextElementSibling; a.hidden=!a.hidden">fark ${isaretli(g.fark)} ⓘ</span>
    <span class="fgacik" hidden>Demo borsa funding'i kendi oranıyla öder; "gerçek Binance" aynı pozisyonların gerçek oranlarla alacağını gösterir (fark ${isaretli(g.fark)}).${g.duzeltilmeyen ? ` İlk ${g.duzeltilmeyen} günün günlük getirisi demo funding'le kaldı (gerçek oranın gün kırılımı o günler için yok); toplam kitap ve kâr yine gerçek oranla.` : ""}</span></div>`;
}
function ciz(){
  const K = VERI.kurulumlar; $("#alt").textContent = K[secili] ? `${K[secili].ad} · ${K[secili].mod}` : "";
  $("#sekme").innerHTML = K.length > 1 ? K.map((k,i)=>`<button class="${i==secili?'on':''}" onclick="secili=${i};ciz()">${k.ad} · ${k.mod}</button>`).join("") : "";
  const nd = K[secili] ? dikkatler(K[secili]).length : 0;
  $("#nav").innerHTML = SAYFALAR.map(([a,ad])=>`<button class="${a==sayfa?'on':''}" onclick="sayfaSec('${a}')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${NAV_SVG[a]}</svg>${ad}${a=="olay"&&nd?'<span class="nok"></span>':""}</button>`).join("");
  const k = K[secili]; if(!k){ $("#icerik").innerHTML = "<div class='kart bos'>Henüz kurulum / defter yok.</div>"; return; }
  const sv = k.servis; const svc = sv=="active" ? "ok" : (sv=="—"||sv=="?" ? "" : "yok");
  const kitap = k.kitap_canli!=null ? k.kitap_canli : k.kitap; AKIS.ustk = AKIS.ustk || {v: kitap};
  $("#ustkitap").innerHTML = `<span id="ustk">${para(AKIS.ustk.v)}</span><span id="ustkar" class="${sinif(k.kar_usd)}"> ${yz(k.kar_oran)}</span>`;
  // MADDE 740: geniş ekran (tablet / yatay): Özet sekmesinde solda özet, sağda pozisyonlar
  const genis = innerWidth >= 1000;
  $("#icerik").innerHTML = sayfa=="poz" ? pozSayfa(k) : sayfa=="gecmis" ? gecmisSayfa(k) : sayfa=="olay" ? olaySayfa(k)
    : (genis ? `<div class="genis"><div>${ozetSayfa(k, svc, sv)}</div><div>${pozSayfa(k)}</div></div>` : ozetSayfa(k, svc, sv));
  const yl = $("#yil"); if (yl) yl.scrollLeft = yl.scrollWidth;
  isiSigdir();
  const kt = document.querySelector(".kutu"); if (kt){ const w = Math.round(kt.clientWidth - 20); if (w > 80 && Math.abs(w - KUTU_W) > 4){ KUTU_W = w; canliBoya(); } }
  const eg0 = $("#egri"); if (eg0 && egriMod) eg0.innerHTML = egriIc(k);
  canliBagla(k); canliBoya();
  grafikler.forEach(g=>g.destroy()); grafikler = [];
  if (!window.Chart || !$("#g1")) return;
  const SC = seriCanli(k), x = SC.map(s=>s.canli ? s.tarih + " (canlı)" : s.tarih), izg = css("--cizgi"), sol = css("--soluk");
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  const ortak = {responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false}},
    scales:{x:{ticks:{color:sol,maxTicksLimit:innerWidth<600?4:8,maxRotation:0,autoSkip:true},grid:{display:false}},y:{ticks:{color:sol},grid:{color:izg}}}};
  grafikler.push(new Chart($("#g1"),{type:"line",data:{labels:x,datasets:[{data:SC.map(s=>s.kitap),borderColor:css("--vurgu"),borderWidth:2,pointRadius:0,fill:false,tension:.15}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>para(c.parsed.y)}}}}}));
  grafikler.push(new Chart($("#g2"),{type:"bar",data:{labels:x,datasets:[{data:SC.map(s=>s.gun==null?null:s.gun*100),
    backgroundColor:SC.map(s=>{ const c = css((s.gun||0)>=0?"--art":"--eks"); return s.canli ? `color-mix(in srgb, ${c} 45%, transparent)` : c; }),borderRadius:4}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>(c.parsed.y>=0?"+":"")+c.parsed.y.toFixed(2).replace(".",",")+"%"}}},
      scales:{...ortak.scales,y:{ticks:{color:sol,callback:v=>(+v.toFixed(2)).toLocaleString("tr-TR")+"%"},grid:{color:izg}}}}}));
}
// MADDE 740: kaydırınca küçülen başlık; sağa / sola kaydırarak sekme; en üstte aşağı çekince yenile
addEventListener("scroll", ()=>{ const u = $("#ust"); if (u) u.classList.toggle("kucuk", scrollY > 90); }, {passive:true});
let dokB = null;
addEventListener("touchstart", e=>{ const t = e.touches[0]; dokB = {x:t.clientX, y:t.clientY, ust: scrollY<=0, yatay: !!e.target.closest(".yatay,.tablo")}; }, {passive:true});
addEventListener("touchmove", e=>{ if (!dokB || !dokB.ust) return; const dy = e.touches[0].clientY - dokB.y, dx = Math.abs(e.touches[0].clientX - dokB.x);
  const c = $("#cek"); if (c && dy > 0 && dy > dx){ c.style.height = Math.min(48, dy/2.2) + "px"; c.textContent = dy > 110 ? "↻ bırakınca yenilenir" : "↓ yenilemek için çek"; } }, {passive:true});
addEventListener("touchend", e=>{ if (!dokB) return; const t = e.changedTouches[0], dx = t.clientX - dokB.x, dy = t.clientY - dokB.y, c = $("#cek");
  if (c) c.style.height = "0px";
  if (dokB.ust && dy > 110 && dy > Math.abs(dx)*1.5){ $("#icerik").style.opacity = .5; yukle().then(()=>{ $("#icerik").style.opacity = 1; }); }
  else if (!dokB.yatay && Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy)*2){
    const i = SAYFALAR.findIndex(x=>x[0]==sayfa), j = i + (dx < 0 ? 1 : -1);
    if (j >= 0 && j < SAYFALAR.length) sayfaSec(SAYFALAR[j][0]); }
  dokB = null; }, {passive:true});
let _gen = (innerWidth >= 1000) + "" + MOBIL(); addEventListener("resize", ()=>{ const g = (innerWidth >= 1000) + "" + MOBIL(); if (g !== _gen){ _gen = g; if (VERI) ciz(); } });
async function yukle(){
  if (VERI_GOMULU){ VERI = gorunum(VERI_GOMULU); ciz(); return; }
  try { const r = await fetch("api/veri", {cache:"no-store"}); VERI = gorunum(await r.json()); ciz(); } catch(e){ $("#alt").textContent = "veri alınamadı"; }
}
yukle(); if(!VERI_GOMULU){ setInterval(yukle, 60000); setInterval(canliBoya, 1000); }
if(!VERI_GOMULU && "serviceWorker" in navigator){ try{ navigator.serviceWorker.register("sw.js"); }catch(e){} }
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ()=>VERI && ciz());
</script></body></html>"""


SW_JS = """const K="carry-kabuk-v3";
self.addEventListener("install",e=>{e.waitUntil(caches.open(K).then(c=>c.addAll(["./","ikon-192.png","ikon-512.png","font/inter-latin.woff2","font/inter-latin-ext.woff2"])));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(a=>Promise.all(a.filter(x=>x!==K).map(x=>caches.delete(x)))));self.clients.claim();});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);
  if(u.origin!==location.origin||e.request.method!=="GET"||u.pathname.includes("/api/")||u.pathname.includes("/paket/"))return;   // madde 738: Binance vb. dış istekler SW'den GEÇMEZ   // veri ve paket önbelleğe ALINMAZ
  e.respondWith(fetch(e.request).then(r=>{const k=r.clone();caches.open(K).then(c=>c.put(e.request,k));return r;}).catch(()=>caches.match(e.request)));});
"""


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
        r.headers["Cache-Control"] = r.headers.get("Cache-Control") if request.path.startswith(("/font/", "/ikon-")) else "no-store"
        r.headers["Content-Security-Policy"] = ("default-src 'none'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                                                "style-src 'unsafe-inline'; connect-src 'self' wss://fstream.binance.com https://fapi.binance.com; img-src 'self' data:; font-src 'self'; manifest-src 'self'; worker-src 'self'")
        return r

    # MADDE 680: PWA — telefonda "Ana ekrana ekle" ile uygulama gibi açılır (Tailscale HTTPS adresinde). Önbellek YALNIZ kabuk
    # (sayfa + simgeler); veri (/api/veri) hiçbir zaman önbelleğe alınmaz -> çevrimdışıyken eski rakam gösterilmez.
    @app.get("/manifest.webmanifest")
    def manifest():
        m = {"name": "Carry Panel", "short_name": "Carry", "start_url": "./", "scope": "./", "display": "standalone",
             "background_color": "#000000", "theme_color": "#000000", "description": "Carry bot izleme paneli (salt okunur)",
             "icons": [{"src": "ikon-192.png", "sizes": "192x192", "type": "image/png"},
                       {"src": "ikon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}
        return Response(json.dumps(m), mimetype="application/manifest+json")

    @app.get("/ikon-<int:n>.png")
    def ikon(n):
        from flask import abort, send_from_directory
        if n not in (192, 512):
            abort(404)
        return send_from_directory(VARLIK_DIR, f"ikon-{n}.png", mimetype="image/png", max_age=7 * 86400)

    # MADDE 740: gömülü yazı tipi (Inter, SIL OFL 1.1 — panel_varlik/OFL-Inter.txt); dışarıdan yüklenmez
    @app.get("/font/<ad>")
    def font(ad):
        from flask import abort, send_from_directory
        if ad not in ("inter-latin.woff2", "inter-latin-ext.woff2"):
            abort(404)
        return send_from_directory(VARLIK_DIR, ad, mimetype="font/woff2", max_age=30 * 86400)

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
