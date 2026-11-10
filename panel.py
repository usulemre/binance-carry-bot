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


PIYASA_BAYAT_SN = 3600


def piyasa_oku(klasorler: list[str], simdi: float | None = None) -> dict | None:
    """MADDE 746: piyasa tarayıcısının çıktısı (tarayici.py → <kurulum>/defter/tarayici.json; anahtarsız, gerçek
    Binance). Birden çok kurulum varsa EN YENİ dosya. 1 saatten eskiyse `bayat` işaretlenir (zamanlayıcı durmuş olabilir)."""
    simdi = simdi or time.time(); en = None
    for kl in klasorler:
        try:
            with open(os.path.join(kl, "defter", "tarayici.json"), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and isinstance(d.get("coinler"), list) and (en is None or d.get("zaman", 0) > en.get("zaman", 0)):
            en = d
    if en is None:
        return None
    en["saat"] = _yerel(en.get("zaman", 0)).strftime("%H:%M")
    en["bayat"] = simdi - en.get("zaman", 0) > PIYASA_BAYAT_SN
    return en


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
    adj, onc, top_fark, fark_satir, duz, duzm = [], None, 0.0, [], 0, 0
    for k in df:
        k2 = dict(k); g = k.get("gun_getiri")
        if g is not None and onc is not None:
            et = gun_etiketi(k); taban = (onc.get("ozkaynak") or 0) * float(onc.get("sermaye_olcek", k.get("sermaye_olcek", 1.0)) or 1.0)
            if et in gun and taban > 0:
                demo_f = ((k.get("gelir_24s") or {}).get("FUNDING_FEE") or 0) * _gelir_payi(onc, k)
                df_ = gun[et] - demo_f; top_fark += df_
                k2["gun_getiri"] = g + df_ / taban; duz += 1
            else:
                duzm += 1
        fark_satir.append(top_fark); adj.append(k2); onc = k
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
        an = anlik_oku(kl)
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
    return {"kurulumlar": out, "paketler": paketler(), "piyasa": piyasa_oku(klasorler), "uretim": _yerel().strftime("%Y-%m-%d %H:%M")}


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
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#000;--kart:#0c0e12;--kart2:#16191f;--yazi:#eceef1;--soluk:#8b919a;--cizgi:#1d2129;--art:#2fd07a;--eks:#ff5d52;--vurgu:#6ea8fe;--uyari:#ff9f43;--mor:#b197fc;--ust:rgba(0,0,0,.82)}}
:root[data-theme="dark"]{--bg:#000;--kart:#0c0e12;--kart2:#16191f;--yazi:#eceef1;--soluk:#8b919a;--cizgi:#1d2129;--art:#2fd07a;--eks:#ff5d52;--vurgu:#6ea8fe;--uyari:#ff9f43;--mor:#b197fc;--ust:rgba(0,0,0,.82)}
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
@media(max-width:820px){nav.alt{position:fixed;left:10px;right:10px;bottom:calc(10px + env(safe-area-inset-bottom));margin:0;z-index:7;box-shadow:0 8px 30px rgba(0,0,0,.35);
  background:color-mix(in srgb,var(--kart) 88%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}nav.alt button{padding:11px 4px}}
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
.py-sec{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 10px}.py-sec button{border:1px solid var(--cizgi);background:none;color:var(--soluk);
 font:inherit;font-size:12.5px;font-weight:650;padding:6px 10px;border-radius:999px;cursor:pointer}.py-sec button.on{background:color-mix(in srgb,var(--vurgu) 16%,transparent);color:var(--vurgu);border-color:transparent}
.py-ara{width:100%;box-sizing:border-box;background:var(--bg);color:inherit;border:1px solid var(--cizgi);border-radius:10px;padding:8px 10px;font:inherit;font-size:14px;margin-bottom:8px}
.py-ikili{display:grid;grid-template-columns:1fr;gap:12px}@media(min-width:760px){.py-ikili{grid-template-columns:1fr 1fr}}
.py table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}.py td{text-align:left;padding:7px 4px;border-top:1px solid var(--cizgi)}
.py td.r{text-align:right;white-space:nowrap}.py .s{color:var(--soluk);font-size:11px}.py .etk{font-size:10px;font-weight:700;padding:1px 5px;border-radius:5px;margin-left:4px;vertical-align:1px}
.py .etk.L{background:color-mix(in srgb,var(--vurgu) 22%,transparent);color:var(--vurgu)}.py .etk.S{background:color-mix(in srgb,#f59e0b 22%,transparent);color:#f59e0b}
.py h3{font-size:13px;color:var(--soluk);margin:0 0 4px;font-weight:650}
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
const SAYFALAR = [["ozet","Özet"],["poz","Pozisyonlar"],["piyasa","Piyasa"],["gecmis","Geçmiş"],["olay","Olaylar"]];
let sayfa = (location.hash||"").slice(1); if (!SAYFALAR.some(x=>x[0]==sayfa)) sayfa = "ozet";
function sayfaSec(a){ if (a==sayfa) return; sayfa = a; history.replaceState(null, "", "#"+a); ciz(); scrollTo(0,0); }
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
// MADDE 740: yıllık takvim (GitHub tarzı): son 53 hafta, her kare bir gün, renk = günlük getiri
function yillik(k){
  const G = {}; (k.seri||[]).forEach(s=>{ if (s.gun!=null && s.tarih) G[s.tarih] = s.gun; });
  const bugun = new Date(); bugun.setHours(12,0,0,0);
  const bas = new Date(bugun); bas.setDate(bas.getDate() - 52*7 - ((bugun.getDay()+6)%7));
  let h = "", n = 0, top = 0;
  for (let d = new Date(bas); d <= bugun || (d.getDay()+6)%7 != 0; d.setDate(d.getDate()+1)){
    if (d > bugun){ h += `<i class="x"></i>`; continue; }
    const t = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`, v = G[t];
    if (v!=null){ n++; top = (1+top)*(1+v)-1; }
    h += `<i ${v!=null ? isi(v,0.03,"").replace('class=" ','class="') : ""} title="${t}${v!=null?"  "+yz(v):""}"></i>`;
  }
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
function kivilcim(s, p, f, renk){
  const M = MUM[s], simdi = Date.now();
  if (!M || M.bas !== gunBasi(simdi)) return `<div class="grbekle iskelet"></div>`;
  const nok = M.nok.filter(n => n[0] < simdi - 1e3);   // tamamlanan mumlar; son nokta anlık fiyat
  if (f) nok.push([simdi, f]);
  if (nok.length < 2) return `<div class="grbekle">gün yeni başladı (03:00)…</div>`;
  // madde 743: en küçük dikey aralık fiyatın %1'i (gün başında 2-3 mumluk oynama duvar gibi görünmesin)
  return cizgi(nok.map(n=>n[1]), 160, 64, renk, p.giris>0 ? p.giris : null, s, nok.map(n=>Math.min(1, (n[0]-M.bas)/GUN_MS)), true, 0.01 * (f || nok[nok.length-1][1]));
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
    ${kivilcim(s, p, f, renk)}${k ? hedefCubuk(k, p, f) : ""}${fundSatir(s, p, f)}`;
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
    return `<div class="${kucuk?"kk":""}" style="left:${r.x}%;top:${r.y}%;width:${r.w}%;height:${r.h}%;background:color-mix(in srgb,var(${renk}) ${yog}%,var(--kart2))">
      <b>${r.s.replace(/USDT$/,"")}${kucuk?"":` <small>${r.yon=="L"?"long":"short"}</small>`}</b><span>${yz(r.ky)}</span></div>`;
  }).join("");
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
function egriIc(k){
  if (egriMod=="bugun"){
    const E = bugunEgri(k);
    if (!E || E.seri.length < 2) return `<div class="bl"><span>bugün 03:00'ten beri · kitap</span><span>—</span></div><div class="bekle" style="padding:20px 0">gün içi kitap kaydı bekleniyor (5 dakikada bir)</div>`;
    const bsl = E.ilk - E.bas > 20*60e3 ? new Date(E.ilk).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"}) + " kaydından beri" : "03:00'ten beri";
    return `<div class="bl"><span>bugün ${bsl} · kitap</span><b class="rz ${sinif(E.son)}">${isaretli(E.son)}${E.oran!=null?" ("+yz(E.oran)+")":""}</b></div>
      ${cizgi(E.seri, 300, 70, css(E.son>=0?"--art":"--eks"), 0, "bugun", E.xs, true, Math.max(4, 0.004 * (k.kitap_canli || k.kitap || 1000)))}<div class="eksen"><span>03:00</span><span>09:00</span><span>15:00</span><span>21:00</span><span>03:00</span></div>`;
  }
  const kit = (k.seri||[]).map(s=>s.kitap).filter(v=>v!=null); if (k.kitap_canli!=null && kit.length) kit.push(k.kitap_canli);
  if (kit.length < 2) return `<div class="bl"><span>kitap · başlangıçtan</span></div><div class="bekle" style="padding:20px 0">en az 2 gün gerekli</div>`;
  const d = kit[kit.length-1]-kit[0];
  return `<div class="bl"><span>kitap · başlangıçtan (${(k.seri||[]).length} gün)</span><b class="rz ${sinif(d)}">${isaretli(d)}</b></div>${cizgi(kit, 300, 70, css(d>=0?"--art":"--eks"), kit[0], "kitap")}`;
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
  const fk = $("#fundsure"); if (fk) fk.innerHTML = fundKart(k);
  mumYukle(k);
  let top = 0; const taraf = {L:[0,0], S:[0,0]};
  for (const [s,p] of Object.entries(k.pozisyonlar||{})){
    const f = FIYAT[s], ok = k.poz_kaynak=="canlı" && f && p.giris>0 && p.miktar;
    const g = ok ? p.miktar * (f - p.giris) : (p.gerceklesmemis||0); top += g;
    const t = taraf[p.yon] || taraf.L; t[0] += ok ? Math.abs(p.miktar)*f : (p.usd||0); t[1] += g;
    const et = document.getElementById("t-"+s); if (et) et.innerHTML = kutuIc(s, p, k);
  }
  for (const y of ["L","S"]){ const e = document.getElementById("taraf-"+y); if (e) e.innerHTML = `${para(taraf[y][0])} · <span class="rz ${sinif(taraf[y][1])}">${isaretli(taraf[y][1])}</span>`; }
  const dn = $("#denge"); if (dn) dn.innerHTML = dengeIc(taraf);
  const ih = $("#isi"); if (ih) ih.innerHTML = isiHarita(k);
  const eg2 = $("#egri"); if (eg2 && egriMod=="bugun") eg2.innerHTML = egriIc(k);
  if (k.poz_kaynak!="canlı") return;
  const fark = top - (k.gerceklesmemis||0), eg = $("#gerc");
  if (eg){ eg.textContent = isaretli(top); eg.className = "rz " + sinif(top); }
  if (k.kitap_canli!=null){ akit("kitapd", k.kitap_canli + fark, para); akit("ustk", k.kitap_canli + fark, para); }
  if (k.kar_usd!=null){ const ku = k.kar_usd + fark, oran = k.kitap_bas ? ku/k.kitap_bas : null;
    const eku = $("#karusd"); if (eku){ eku.textContent = `${ok_(ku)} ${isaretli(ku)} (${yz(oran)})`; eku.className = "kar rz " + sinif(ku); }
    const euk = $("#ustkar"); if (euk){ euk.textContent = ` ${yz(oran)}`; euk.className = sinif(ku); } }
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
  const D = k.dokum, dg = D.diger_gelir||0, fark = kar - poz - D.gerceklesen - D.funding - D.komisyon - dg;
  const K = [["poz","Açık pozisyonlar", poz, "şu an açık coinlerin fiyat hareketi; kapanınca kesinleşir", "--vurgu", true],
             ["kap","Kapanan pozisyonlar", D.gerceklesen, "kapatılmış işlemlerin kesinleşmiş kâr / zararı", "--mor", false],
             ["fun","Funding", D.funding, "pozisyon taşıdığı için funding saatlerinde (çoğu coinde 8, bazılarında 4 saatte bir) alınan (+) / ödenen (−) ücret — stratejinin asıl geliri", "--art", true],
             ["kom","Komisyon", D.komisyon, "Binance işlem ücreti", "--uyari", true],
             ["dig","Diğer Binance kayıtları", dg, "sigorta fonu vb.", "--mor", false],
             ["bas","Başlangıç farkı", fark, "başlangıç kaydı alınırken açık pozisyonların o anki kârı (başlangıç tutarına zaten dahil) ve demo / gerçek fiyat farkı; sabit kalır", "--soluk", false]]
    .filter(x => x[5] || Math.abs(x[2]) >= 0.005);
  const tm = K.reduce((a,x)=>a+Math.abs(x[2]), 0) || 1;
  const cubuk = `<div class="cubuk">${K.map(x=>`<span style="width:${(Math.abs(x[2])/tm*100).toFixed(1)}%;background:${css(x[4])}" title="${x[1]}"></span>`).join("")}</div>`;
  // madde 744: demoda funding'i demo borsa kendi oranıyla öder; bot gerçek oranlara göre seçer -> "gerçek oranlarla olsaydı" (toplama girmez)
  const fg = D.funding_gercek, fgS = fg==null ? "" : `<div class="dk alt ${ACIK.has("fug")?"acik":""}" onclick="dkAc('fug')"><span class="n"></span><span class="a">↳ gerçek Binance oranlarıyla olsaydı <span class="ok">›</span></span><span class="v ${sinif(fg)}">${isaretli(fg)}</span><span class="ac">Bot coinleri gerçek Binance'in funding oranlarına bakarak seçer, ama pozisyonlar demo borsada olduğu için funding'i demo borsa kendi oranıyla öder (çoğu zaman gerçekle ilgisiz). Bu satır aynı pozisyonların gerçek oranlarla ne alacağını / ödeyeceğini gösterir (yaklaşık; 5 dk'lık pozisyon görüntüsüyle). Toplama girmez — canlı hesapta funding bu olurdu.</span></div>`;
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
  return `<div class="d">${ad} · ${A.gross.toFixed(2).replace(".",",")}x</div><span class="k" style="white-space:normal" title="${ac}">${st}</span>`;
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
    ${satir("Gerçek komisyon (model 5 bp)", bp(G.komisyon_bp), G.komisyon_bp==null?"":(G.komisyon_bp>6?"eks":""))}
    ${satir("GTX ilk deneme · kovalama · piyasaya düşen", `${G.gtx_ilk||0} · ${G.kovala||0} · ${G.piyasa_yedek||0}`, (G.piyasa_yedek||0)>0?"eks":"")}
  </table></div><div class="k" style="margin-top:6px">Referans (madde 695): TP dolum ≥ %90 güvenli, ≤ %80 alarm; dolum %70'te yıllık −29 puan.
  Kayma eksi = gönderim anındaki fiyattan daha iyi doldu. Yalnız kayıt; bot kararlarını etkilemez.</div>`;
}
function ozetSayfa(k, svc, sv){
  const cip = (e, d, c="") => `<div class="cip"><div class="e">${e}</div><div class="d ${c}">${d}</div></div>`;
  const kitap = k.kitap_canli!=null ? k.kitap_canli : k.kitap; AKIS.kitapd = AKIS.kitapd || {v: kitap};
  return `<div class="kart ozet">
    <div class="ust"><span class="k">Kitap</span>${svc?`<span class="durum ${svc}">● ${sv=="active"?"çalışıyor":sv}</span>`:""}</div>
    <div class="buyuk" id="kitapd">${para(AKIS.kitapd.v)}</div>
    ${k.kar_usd!=null?`<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span id="karusd" class="kar rz ${sinif(k.kar_usd)}">${ok_(k.kar_usd)} ${isaretli(k.kar_usd)} (${yz(k.kar_oran)})</span><span class="k">başlangıç ${para(k.kitap_bas)}</span></div>`:""}${fgAnahtar(k)}
    <div class="egri"><div style="display:flex;justify-content:flex-end"><div class="mod"><button data-m="bugun" class="${egriMod=="bugun"?"on":""}" onclick="egriSec('bugun')">Bugün</button><button data-m="tum" class="${egriMod=="tum"?"on":""}" onclick="egriSec('tum')">Başlangıçtan</button></div></div>
      <div id="egri">${egriIc(k)}</div></div>
    <div class="cipler">${cip(`Son gün${k.son_gun_tarih?" · "+(+k.son_gun_tarih.slice(8,10))+" "+AYAD[+k.son_gun_tarih.slice(5,7)-1].slice(0,3):""}`, yz(k.bugun), sinif(k.bugun))}${cip(k.g7==null&&k.gun_sayisi?`7 gün · ${k.gun_sayisi} gün veri`:"7 gün", yz(k.g7), sinif(k.g7))}${cip(k.g30==null&&k.gun_sayisi>=7?`30 gün · ${k.gun_sayisi} gün veri`:"30 gün", yz(k.g30), sinif(k.g30))}${cip("En büyük düşüş", yz(k.dd), k.dd<0?"eks":"")}</div>
    <div class="bilgi"><div class="cip"><div class="e">Ayar</div>${ayarKart(k)}</div><div class="cip"><div class="e">Sonraki dilim</div><div id="dilimsure">${dilimKart(k.dilim)}</div></div><div class="cip"><div class="e">Sonraki funding</div><div id="fundsure">${fundKart(k)}</div></div></div>
  </div>
  <div class="kart"><h2>Pozisyon haritası <span class="k">· kare boyu = büyüklük, renk = kâr / zarar</span></h2><div class="isi" id="isi">${isiHarita(k)}</div></div>
  ${k.dokum&&k.gerceklesmemis!=null?`<div class="kart"><h2>Kâr / zarar nereden geldi? <span class="k">· satıra dokun: açıklama</span></h2><div id="dokum">${dokumYaz(k, k.gerceklesmemis, k.kar_usd)}</div></div>`:""}`;
}
function pozSayfa(k){
  const P = Object.entries(k.pozisyonlar||{}); const L = P.filter(p=>p[1].yon=="L").sort((a,b)=>b[1].usd-a[1].usd), S = P.filter(p=>p[1].yon=="S").sort((a,b)=>b[1].usd-a[1].usd);
  const top = (A, i) => A.reduce((a,p)=>a+(i ? (p[1].gerceklesmemis||0) : (p[1].usd||0)), 0);
  const kutular = (A, y, ad) => A.length ? `<div class="taraf"><span>${ad} (${A.length})</span><b id="taraf-${y}">${para(top(A,0))} · <span class="rz ${sinif(top(A,1))}">${isaretli(top(A,1))}</span></b></div>
    <div class="kutular">${A.map(p=>`<div class="kutu ${y}" id="t-${p[0]}">${kutuIc(p[0], p[1], k)}</div>`).join("")}</div>` : "";
  return `<div class="kart"><h2>Pozisyonlar <span class="k">${k.poz_kaynak=="canlı"?"liste "+k.poz_zaman:"günlük defter "+(k.poz_zaman||"")}${k.gerceklesmemis!=null?` · gerçekleşmemiş <b id="gerc" class="rz ${sinif(k.gerceklesmemis)}">${isaretli(k.gerceklesmemis)}</b>`:""}</span></h2>
    ${P.length?`<div class="denge" id="denge">${dengeIc({L:[top(L,0),0], S:[top(S,0),0]})}</div>`:""}
    ${kutular(L, "L", "LONG") + kutular(S, "S", "SHORT") || "<div class='bos'>açık pozisyon yok</div>"}
    <div class="k">grafik: bugün 03:00'ten beri (15 dk, gün sonuna kadar uzar) · kesikli çizgi giriş fiyatı (grafik aralığındaysa) · renk pozisyonun kâr / zararı (short'ta fiyat düşerse yeşil) · çubuk kâr al hedefine kalan yol · funding: bir sonraki ödemede bu pozisyonun alacağı / ödeyeceği</div></div>`;
}
function gecmisSayfa(k){
  const grafikVar = (k.seri||[]).length >= 3;   // madde 734/737: 1-2 noktalık grafik bilgi vermez, yalnız yer kaplar
  return `<div class="kart"><h2>Günlük takvim <span class="k">· kazanç yeşil, kayıp kırmızı (koyuluk = büyüklük)</span></h2>${takvim(k)}
      ${k.dokum?`<div class="k" style="margin-top:6px">Başlangıçtan beri: funding ${isaretli(k.dokum.funding)}${k.dokum.funding_gercek!=null?` (gerçek oranlarla ${isaretli(k.dokum.funding_gercek)})`:""} · komisyon ${isaretli(k.dokum.komisyon)}</div>`
        :(k.funding_top||k.komisyon_top)?`<div class="k" style="margin-top:6px">Defter toplamı (yaklaşık): funding ${isaretli(k.funding_top)} · komisyon ${isaretli(k.komisyon_top)}</div>`:""}
      <div class="k" style="margin-top:4px">Her gün, Binance gününe (03:00 – 03:00) göre; bugünkü canlı sonuç Özet'te.</div></div>
    <div class="kart"><h2>Son 1 yıl</h2>${yillik(k)}</div>
    ${grafikVar?`<div class="iki"><div class="kart"><h2>Kitap ($)</h2><div class="grafik"><canvas id="g1"></canvas></div></div>
      <div class="kart"><h2>Günlük getiri</h2><div class="grafik"><canvas id="g2"></canvas></div></div></div>`
      :`<div class="kart bekle">Kitap ve günlük getiri grafikleri 3 günlük veri birikince görünür (şu an ${(k.seri||[]).length} gün).</div>`}
    <div class="kart"><h2>İcra · son 30 gün <span class="k">(emir defteri)</span></h2>${icraKart(k)}</div>`;
}
// MADDE 740: olaylar zaman çizelgesi — gün gün (Bugün / Dün / tarih), türe göre simge
const OLAY_SIMGE = {basla:"▶", ayar:"⚙", stop:"■", stop_tut:"□", delist:"!", saglik:"♥", hata:"✕", tp:"✓", uyari:"⚠", tur:"↻", islem:"⇄", funding:"$"};
const OLAY_AD = {basla:"başlama", ayar:"ayar", stop:"stop", stop_tut:"stop şartı: piyasa sakin, tutuldu", delist:"delist", saglik:"sağlık",
                 hata:"hata", tp:"kâr al doldu", uyari:"piyasa emrine düşüldü", tur:"dilim turu", islem:"işlem", funding:"funding ödemesi"};
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
  // madde 750: turdaki / gruptaki kısmi ve tam kapanışların gerçekleşen kârı olay satırına
  for (const g of out){ const kp = (g.islem||[]).filter(x=>x.kapanis_kar!=null); if (!kp.length) continue;
    const top = kp.reduce((a,x)=>a+x.kapanis_kar,0), tam = kp.filter(x=>x.tam).length, kis = kp.length - tam;
    const ne = [kis ? `${kis} kısmi` : "", tam ? `${tam} tam` : ""].filter(Boolean).join(" + ");
    g.metin += ` | ${ne} kapanış ${isaretli(top)} (${kp.map(x=>x.sembol).filter((v,i,a)=>a.indexOf(v)===i).join(", ")})`; g.kapanis = top; }
  // madde 749: funding ödemeleri (demo hesaba yatan · gerçek oranlarla olsaydı)
  const demo = k.mod=="demo";
  for (const f of (k.fundingler||[])){
    const a = f.demo!=null ? `demo hesaba ${isaretli(f.demo)} (${f.demo_n} poz)` : (demo ? "demo hesaba ödeme yok" : "");
    const b = demo && f.gercek!=null ? `gerçek oranlarla ${isaretli(f.gercek)} (${f.gercek_n} poz)` : "";
    out.push({zaman: f.zaman, tur: "funding", fon: f, metin: "Funding · " + [a, b].filter(Boolean).join(" · ")});
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
// MADDE 746: piyasa tarayıcısı — gerçek Binance, tüm USDⓈ-M coinler; dönem / hacim filtresi / arama. Botun tuttuğu coinler L / S etiketli.
const PIY = {d: localStorage.getItem("carry_py_d") || "d24", h: +(localStorage.getItem("carry_py_h") || 20), ara: "", n: 15};
const PIY_DONEM = [["d1","1 sa"],["d24","24 sa"],["d3","3 gün"],["d7","7 gün"],["d30","30 gün"],["fy","Funding"]];
function piySec(alan, v){ PIY[alan] = v; try{ localStorage.setItem("carry_py_"+alan, v); }catch(e){} ciz(); }
function piyAra(v){ PIY.ara = v.toUpperCase(); const el = $("#pyliste"); if (el) el.innerHTML = piyListe(PIY.k); }
// MADDE 747: Piyasa sekmesi açıkken telefon Binance'in herkese açık TÜM-COİN akışlarına bağlanır (anahtarsız):
// !miniTicker@arr (son fiyat, 24 sa açılış, hacim) + !markPrice@arr (işaret fiyatı, anlık funding). Sekmeden çıkınca kapanır.
// 1 sa / 3 / 7 / 30 g %, sunucunun referans fiyatlarıyla (10 dk'da bir) canlı fiyattan hesaplanır.
let PWS = null, PCANLI = {}, PZAMAN = 0, PCIZ = 0;
function piyBagla(){
  if (VERI_GOMULU || !window.WebSocket) return;
  if (sayfa !== "piyasa"){ if (PWS){ PWS.onclose = null; PWS.close(); PWS = null; } return; }
  if (PWS && PWS.readyState <= 1) return;
  PWS = new WebSocket("wss://fstream.binance.com/market/stream?streams=!miniTicker@arr/!markPrice@arr");
  PWS.onmessage = e => { try { const m = JSON.parse(e.data), d = m.data; if (!Array.isArray(d)) return;
    const mt = (m.stream||"").startsWith("!miniTicker");
    for (const x of d){ const c = PCANLI[x.s] || (PCANLI[x.s] = {});
      if (mt){ c.son = +x.c; c.ac = +x.o; c.q = +x.q; } else { c.isa = +x.p; if (x.r!=="" && x.r!=null) c.r = +x.r; } }
    PZAMAN = Date.now();
    if (Date.now() - PCIZ > 2000 && document.activeElement?.className !== "py-ara"){ PCIZ = Date.now(); const el = $("#pyliste"); if (el) el.innerHTML = piyListe(PIY.k); const z = $("#pyzaman"); if (z) z.innerHTML = piyZaman(); }
  } catch(_){} };
  PWS.onclose = () => { PWS = null; setTimeout(piyBagla, 5000); };
}
const piyCanli = () => Date.now() - PZAMAN < 15e3;
function piyZaman(){ const P = VERI.piyasa; return piyCanli() ? `<b style="color:var(--art)">● canlı</b>` : `${P.saat}${P.bayat ? " · <b style='color:var(--eks)'>BAYAT</b>" : ""}`; }
function piyGuncel(c){   // sunucu satırı + canlı akış → anlık değerler
  const l = PCANLI[c.s]; if (!l || !piyCanli()) return c;
  const f = l.isa || l.son || c.f, y = r => r ? Math.round((f / r - 1) * 1e4) / 100 : null, o = {...c, f};
  if (l.ac) o.d24 = y(l.ac);
  if (c.r1) o.d1 = y(c.r1); if (c.r3) o.d3 = y(c.r3); if (c.r7) o.d7 = y(c.r7); if (c.r30) o.d30 = y(c.r30);
  if (l.q) o.hacim = Math.round(l.q / 1e4) / 100;
  if (l.r != null){ o.fr = Math.round(l.r * 1e6) / 1e4; o.fy = Math.round(l.r * (24 / (c.ah||8)) * 365 * 1000) / 10; }
  return o;
}
function piyListe(k){
  const P = VERI.piyasa; if (!P) return "";
  k = k || {}; const tut = {};
  for (const [s, p] of Object.entries(k.pozisyonlar || {})) if (p.miktar) tut[s] = p.miktar > 0 ? "L" : "S";
  let L = P.coinler.map(piyGuncel).filter(c => c[PIY.d] != null && (c.hacim || 0) >= PIY.h);
  if (PIY.ara) L = L.filter(c => c.s.includes(PIY.ara));
  const yuz = v => v==null ? "—" : (v>0?"+":"") + v.toLocaleString("tr-TR",{maximumFractionDigits: Math.abs(v)<10?2:1}) + "%";
  const fon = c => c.fr==null ? "—" : (c.fr>0?"+":"") + c.fr.toLocaleString("tr-TR",{maximumFractionDigits:4}) + "%";
  const sat = c => { const ad = c.s.replace(/USDT$/,""), e = tut[c.s];
    return `<tr><td><b>${ad}</b>${e?`<span class="etk ${e}">bot ${e=="L"?"long":"short"}</span>`:""}<div class="s">${c.hacim.toLocaleString("tr-TR",{maximumFractionDigits:0})}M $ hacim${c.yas!=null && c.yas<60 ? " · "+c.yas+" g yeni" : ""}</div></td>
      <td class="r">${fiyatYaz(c.f)}<div class="s">fund. ${fon(c)} / ${c.ah} sa</div></td>
      <td class="r"><b class="${sinif(c[PIY.d])}">${PIY.d=="fy" ? yuz(c.fy) + "/yıl" : yuz(c[PIY.d])}</b><div class="s">${PIY.d=="d24" ? "7g " + yuz(c.d7) : "24s " + yuz(c.d24)}</div></td></tr>`; };
  const sir = L.slice().sort((a,b)=>b[PIY.d]-a[PIY.d]);
  if (PIY.ara) return `<table>${sir.slice(0,60).map(sat).join("") || "<tr><td class='s'>eşleşen coin yok</td></tr>"}</table>`;
  const [ust, alt] = PIY.d=="fy" ? ["En yüksek funding (long'lar ödüyor → short alır)", "En negatif funding (short'lar ödüyor → long alır)"]
                                  : ["En çok yükselen", "En çok düşen"];
  return `<div class="py-ikili"><div><h3>${ust}</h3><table>${sir.slice(0,PIY.n).map(sat).join("")}</table></div>
    <div><h3>${alt}</h3><table>${sir.slice(-PIY.n).reverse().map(sat).join("")}</table></div></div>
    <div class="s" style="margin-top:10px">${L.length} coin · ${PIY.n < L.length/2 ? `<span style="color:var(--vurgu);cursor:pointer" onclick="PIY.n+=15;ciz()">daha fazla göster</span>` : ""}</div>`;
}
function piyasaSayfa(k){
  const P = VERI.piyasa; PIY.k = k;
  if (!P) return `<div class="kart bos">Piyasa verisi yok. Sunucuda tarayıcı zamanlayıcısını aç:<br><code>sudo cp /opt/carry/deploy/carry-tarayici.* /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now carry-tarayici.timer</code></div>`;
  return `<div class="kart py"><h2>Piyasa <span class="s" style="font-weight:500">gerçek Binance · ${P.coinler.length} coin · <span id="pyzaman">${piyZaman()}</span></span></h2>
    <div class="py-sec">${PIY_DONEM.map(([a,ad])=>`<button class="${PIY.d==a?'on':''}" onclick="piySec('d','${a}')">${ad}</button>`).join("")}</div>
    <div class="py-sec">${[[0,"tüm hacimler"],[20,"≥ 20M $"],[70,"≥ 70M $ (bot eşiği)"]].map(([v,ad])=>`<button class="${PIY.h==v?'on':''}" onclick="piySec('h',${v})">${ad}</button>`).join("")}</div>
    <input class="py-ara" placeholder="coin ara (ör. JCT)" value="${PIY.ara}" oninput="piyAra(this.value)">
    <div id="pyliste">${piyListe(k)}</div>
    <div class="s" style="margin-top:10px">Yalnız bilgi; botun kararlarını etkilemez. "● canlı": fiyat, 24 sa, hacim ve funding Binance'ten anlık (telefon doğrudan bağlanır).
    1 sa ≈ son 60–70 dk; 3/7/30 gün = UTC gün kapanışından bugüne (referanslar 10 dk'da bir yenilenir). Funding/yıl = son oran × günlük ödeme sayısı × 365.</div></div>`;
}
function olaySayfa(k){
  const bugun = new Date(), t = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  const dun = new Date(bugun); dun.setDate(dun.getDate()-1);
  const ad = g => g==t(bugun) ? "Bugün" : g==t(dun) ? "Dün" : `${+g.slice(8,10)} ${AYAD[+g.slice(5,7)-1]} ${g.slice(0,4)}`;
  let h = "", onc = null;
  for (const o of olayIslem(k)){
    const g = (o.zaman||"").slice(0,10); if (g!==onc){ h += `<div class="gun">${g?ad(g):"—"}</div>`; onc = g; }
    h += `<div class="zo ${o.tur}"><span class="i i-${o.tur}">${OLAY_SIMGE[o.tur]||"•"}</span><div class="m"><div>${o.metin.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/\s*\|\s*/g," · ")}</div><div class="z">${(o.zaman||"").slice(11)} · ${OLAY_AD[o.tur]||o.tur}</div>${islemTablo(o)}${fonTablo(o)}</div></div>`;
  }
  const bek = (k.islemler||{}).bekleyen||0;
  if (bek) h = `<div style="color:var(--soluk);font-size:12px;margin-bottom:8px">${bek} emrin dolum bilgisi henüz eşlenmedi (birkaç dakika içinde görünür)</div>` + h;
  return `<div class="kart"><h2>Olaylar</h2>${h ? `<div class="zc">${h}</div>` : "<div class='bos'>olay yok</div>"}</div>
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
    <span>fark ${isaretli(g.fark)}${g.duzeltilmeyen ? ` · ${g.duzeltilmeyen} eski gün düzeltilemedi` : ""}</span></div>`;
}
function ciz(){
  const K = VERI.kurulumlar; $("#alt").textContent = K[secili] ? `${K[secili].ad} · ${K[secili].mod}` : "";
  $("#sekme").innerHTML = K.length > 1 ? K.map((k,i)=>`<button class="${i==secili?'on':''}" onclick="secili=${i};ciz()">${k.ad} · ${k.mod}</button>`).join("") : "";
  $("#nav").innerHTML = SAYFALAR.map(([a,ad])=>`<button class="${a==sayfa?'on':''}" onclick="sayfaSec('${a}')">${ad}</button>`).join("");
  const k = K[secili]; if(!k){ $("#icerik").innerHTML = "<div class='kart bos'>Henüz kurulum / defter yok.</div>"; return; }
  const sv = k.servis; const svc = sv=="active" ? "ok" : (sv=="—"||sv=="?" ? "" : "yok");
  const kitap = k.kitap_canli!=null ? k.kitap_canli : k.kitap; AKIS.ustk = AKIS.ustk || {v: kitap};
  $("#ustkitap").innerHTML = `<span id="ustk">${para(AKIS.ustk.v)}</span><span id="ustkar" class="${sinif(k.kar_usd)}"> ${yz(k.kar_oran)}</span>`;
  // MADDE 740: geniş ekran (tablet / yatay): Özet sekmesinde solda özet, sağda pozisyonlar
  const genis = innerWidth >= 1000;
  $("#icerik").innerHTML = sayfa=="piyasa" ? piyasaSayfa(k) : sayfa=="poz" ? pozSayfa(k) : sayfa=="gecmis" ? gecmisSayfa(k) : sayfa=="olay" ? olaySayfa(k)
    : (genis ? `<div class="genis"><div>${ozetSayfa(k, svc, sv)}</div><div>${pozSayfa(k)}</div></div>` : ozetSayfa(k, svc, sv));
  const yl = $("#yil"); if (yl) yl.scrollLeft = yl.scrollWidth;
  canliBagla(k); canliBoya(); piyBagla();
  grafikler.forEach(g=>g.destroy()); grafikler = [];
  if (!window.Chart || !$("#g1")) return;
  const x = k.seri.map(s=>s.tarih), izg = css("--cizgi"), sol = css("--soluk");
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  const ortak = {responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false}},
    scales:{x:{ticks:{color:sol,maxTicksLimit:innerWidth<600?4:8,maxRotation:0,autoSkip:true},grid:{display:false}},y:{ticks:{color:sol},grid:{color:izg}}}};
  grafikler.push(new Chart($("#g1"),{type:"line",data:{labels:x,datasets:[{data:k.seri.map(s=>s.kitap),borderColor:css("--vurgu"),borderWidth:2,pointRadius:0,fill:false,tension:.15}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>para(c.parsed.y)}}}}}));
  grafikler.push(new Chart($("#g2"),{type:"bar",data:{labels:x,datasets:[{data:k.seri.map(s=>s.gun==null?null:s.gun*100),
    backgroundColor:k.seri.map(s=>(s.gun||0)>=0?css("--art"):css("--eks")),borderRadius:4}]},
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
let _gen = innerWidth >= 1000; addEventListener("resize", ()=>{ const g = innerWidth >= 1000; if (g !== _gen){ _gen = g; if (VERI) ciz(); } });
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
