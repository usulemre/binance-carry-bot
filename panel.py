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
                                 "CARRY_MERDIVEN", "CARRY_MERDIVEN_SHORT", "CARRY_KAR_AL", "CARRY_KAR_AL_SHORT",
                                 "CARRY_GIRIS_DILIM", "CARRY_SHORT_ARA_SAAT", "CARRY_ELLE_DOSYA", "CARRY_ELLE_PANEL"):   # madde 790: 788 bayrağı panelde okunmuyordu   # anahtarlar OKUNMAZ
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


def devir_uygula(klasor: str, an: dict | None) -> dict:
    """MADDE 828: zorunlu kapatıp aynı adetle yeniden açma (madde 827) borsada açık kârı GERÇEKLEŞMİŞE çevirdi. Panel bunu
    kapanış hiç olmamış gibi gösterir: coin başına kapanışta gerçekleşen `r` (defter/devir_duzeltme.json), pozisyon hâlâ
    açıkken "Kapanan"dan "Açık"a taşınır; giriş = borsa girişi − r / adet (≈ eski giriş). Toplam kâr (özsermaye) DEĞİŞMEZ.
    Pozisyon sonradan küçülürse taşınan pay, yeniden açılıştan beri görülen EN KÜÇÜK adet oranıyla azalır (kapanan kısım
    gerçekleşmişe döner, sonradan yeniden açılış onu diriltmez). `an` yerinde değiştirilir. Döner: {sembol: taşınan $}."""
    try:
        with open(os.path.join(klasor, "defter", "devir_duzeltme.json"), encoding="utf-8") as f:
            dv = json.load(f)
        t0, coin = float(dv["t_acilis"]), dv["coin"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    if not an or not isinstance(an.get("pozisyonlar"), dict):
        return {}
    try:
        with open(os.path.join(klasor, "defter", "anlik_poz.json"), encoding="utf-8") as f:
            gec = json.load(f).get("s") or {}
    except (OSError, ValueError, AttributeError):
        gec = {}
    out = {}
    for s, d in coin.items():
        p = an["pozisyonlar"].get(s)
        adet, r = float(d.get("adet") or 0), float(d.get("r") or 0)
        if not p or not adet or not r:
            continue
        oranlar = [float(k[1]) / adet for k in gec.get(s, []) if float(k[0]) >= t0] + [float(p.get("miktar") or 0) / adet]
        frac = max(0.0, min(1.0, min(oranlar)))
        q = float(p.get("miktar") or 0)
        if frac <= 0 or not q:
            continue
        adj = r * frac
        p["giris_borsa"] = p.get("giris")
        p["giris"] = float(p["giris"]) - adj / q
        p["gerceklesmemis"] = round(float(p.get("gerceklesmemis") or 0) + adj, 4)
        if p.get("isaret") and p["giris"] > 0:
            p["kar_yuzde"] = round((float(p["isaret"]) / p["giris"] - 1) * (1 if q > 0 else -1) * 100, 2)
        p["devir"] = round(adj, 4)
        out[s] = adj
    if out:
        an["gerceklesmemis_top"] = round(float(an.get("gerceklesmemis_top") or 0) + sum(out.values()), 2)
    return out


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


def cikis_takvimi(klasor: str, e: dict | None = None, sonraki: dict | None = None) -> dict | None:
    """MADDE 787: her coinin dilim paylarının ne zaman YENİLENECEĞİ (kullanıcı: "hangi parça hangi gün çıkacak görsem").
    Bot her turda `sira` numaralı dilimi yeniler ve sırayı bir artırır (carry_bot.bir_tur) → dilim j, k = (j − sira) mod N tur sonra
    yenilenir. Short'lar ayrıca SHORT_ARA_SAAT'te bir ara dengelemeyle değişir (short_ara_dengele: yenilenen dilimden adim, 2·adim …
    önceki dilimler). Pay = o dilimdeki ADET / coinin toplam adedi (madde 770: bacak adedi = usd / giriş referansı). Yenilenen dilim
    coini YENİDEN seçerse o pay kalır — yani bu "en erken çıkış" takvimi. Döner {sembol: [{"k", "zaman", "pay", "giris", "alis"}, ...]}
    (k sırasıyla; giris = parçanın referans giriş fiyatı, alis ≈ parçanın kurulduğu tur: long N tur, short ara dengeleme adımı kadar önce)."""
    e = e if e is not None else _env(klasor)
    yol = e.get("CARRY_DILIM_LOG") or "carry_dilimler.json"
    yol = yol if os.path.isabs(yol) else os.path.join(klasor, yol)
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
        n = max(1, int(float(e.get("CARRY_N_DILIM") or 15)))
        aralik = float(e.get("CARRY_REBALANCE_H") or 120) / n
        ara = float(e.get("CARRY_SHORT_ARA_SAAT") or 40)
        sira = int(d.get("sira", 0)) % n
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    adim = int(round(ara / aralik)) if aralik > 0 and ara > 0 else 0
    adim = adim if 0 < adim < n else 0
    t0 = (sonraki or {}).get("zaman")
    ref = d.get("dilim_fiyat") or {}
    adet = {}
    for j, h in (d.get("dilimler") or {}).items():
        try:
            jj = int(j) % n
        except (TypeError, ValueError):
            continue
        for sem, usd in (h or {}).items():
            try:
                usd = float(usd); r = float((ref.get(str(j)) or {}).get(sem) or 0)
            except (TypeError, ValueError):
                continue
            if usd == 0:
                continue
            q = abs(usd) / r if r > 0 else abs(usd)
            if usd > 0:
                k = (jj - sira) % n; geri = n               # long: dilim 5 g (N tur) önce kuruldu
            else:
                k = min(x for x in range(n) if (sira + x - jj) % n == 0 or (adim and (sira + x - jj) % n % adim == 0))
                geri = adim or n                             # short: son ara dengelemeden beri
            adet.setdefault(sem, []).append((k, q, r if r > 0 else None, geri))
    out = {}
    for sem, L in adet.items():
        top = sum(q for _, q, _, _ in L)
        if top <= 0:
            continue
        out[sem] = [{"k": k, "zaman": int(t0 + k * aralik * 3600) if t0 else None, "pay": round(q / top, 4),
                     "giris": r, "alis": int(t0 + (k - g) * aralik * 3600) if t0 else None}
                    for k, q, r, g in sorted(L, key=lambda x: (x[0], -x[1]))]
    return out


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


def elle_semboller(klasor: str) -> set:
    """MADDE 830: kullanıcının elle yönettiği semboller (carry_elle.json); yoksa boş."""
    yol = _env(klasor).get("CARRY_ELLE_DOSYA") or "carry_elle.json"
    yol = yol if os.path.isabs(yol) else os.path.join(klasor, yol)
    try:
        with open(yol, encoding="utf-8") as f:
            k = set((json.load(f) or {}).get("elle") or {})
    except (OSError, ValueError, AttributeError, TypeError):
        k = set()
    try:      # madde 838: panelden yeni alınan coin, bot bir sonraki kontrolü yapmadan da rozetli görünsün
        import carry_elle
        py = _env(klasor).get("CARRY_ELLE_PANEL") or os.path.join("defter", "carry_elle_panel.json")
        k |= carry_elle.panel_isaretleri(py if os.path.isabs(py) else os.path.join(klasor, py), yol)
    except Exception:
        pass
    return k


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
    # madde 784: demoda coin başına GERÇEK oranlı funding (carry_anlik gercek_funding.json "coin"); yoksa None.
    try:
        with open(os.path.join(klasor, "defter", "gercek_funding.json"), encoding="utf-8") as f:
            gc = json.load(f).get("coin")
        gc = gc if isinstance(gc, dict) and gc else None
    except (OSError, ValueError, AttributeError):
        gc = None
    elle = elle_semboller(klasor)   # madde 830
    out = []
    for s_ in set(c) | set(poz) | set(gc or {}):
        g = c.get(s_) or {}; p = poz.get(s_) or {}
        k = {"s": s_.removesuffix("USDT"), "kapanan": round(g.get("REALIZED_PNL", 0.0), 4), "funding": round(g.get("FUNDING_FEE", 0.0), 4),
             "komisyon": round(g.get("COMMISSION", 0.0), 4), "acik": round(float(p.get("gerceklesmemis") or 0.0), 4),
             "yon": p.get("yon")}
        if s_ in elle:
            k["elle"] = True
        if gc is not None:
            k["funding_demo"] = k["funding"]; k["funding"] = round(float(gc.get(s_, 0.0)), 4)
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
        o["cikis"] = cikis_takvimi(kl, e, o.get("dilim"))   # madde 787
        if o["cikis"]:   # madde 841: elle coinin çıkış süresi / kâr al girişi yoktur (bot dilimden çıkarmadan önce de gösterilmez)
            _elle = elle_semboller(kl)
            o["cikis"] = {s: L for s, L in o["cikis"].items() if s not in _elle}
        if (e.get("CARRY_GIRIS_DILIM") or "0") not in ("0", "false", "False") and o["cikis"]:   # madde 788: kâr al kendi dilim girişinden
            o["tp_giris"] = {sem: round(sum(x["pay"] * x["giris"] for x in L) / sum(x["pay"] for x in L), 10)
                             for sem, L in o["cikis"].items() if L and all(x.get("giris") for x in L)}
        kk = karar_kayma(kl)
        if kk is not None and o.get("icra"):
            o["icra"]["karar"] = kk
        an = anlik_oku(kl)
        _devir = devir_uygula(kl, an)   # madde 828: an yerinde (giriş / gerçekleşmemiş) düzeltilir
        o["coin_ozet"] = coin_ozet(kl, an)
        o.update(hesap_ozet(df, an))
        if _devir:   # taşınan tutar "Kapanan"dan düşer (Açık'a eklendi; toplam aynı)
            if o.get("dokum"):
                o["dokum"]["gerceklesen"] = round(o["dokum"]["gerceklesen"] - sum(_devir.values()), 2)
            for k_ in o.get("coin_ozet") or []:
                a_ = _devir.get(k_["s"] + "USDT")
                if a_:
                    k_["kapanan"] = round(k_["kapanan"] - a_, 4)
                    k_["toplam"] = round(k_["kapanan"] + k_["funding"] + k_["komisyon"] + k_["acik"], 4)
            o["devir"] = {"toplam": round(sum(_devir.values()), 2), "madde": 828}
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
:root{--bg:#f3f4f6;--kart:#fff;--kart2:#f3f4f7;--yazi:#111318;--soluk:#5d6472;--cizgi:#e5e7eb;--art:#0f9d58;--eks:#d93025;--vurgu:#2563eb;--uyari:#c2410c;--mor:#7c3aed;--ust:rgba(243,244,246,.86)}
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
/* MADDE 832: Piyasa sekmesi */
.pyk .gdon button{height:36px}
.pyr.pye{grid-template-columns:30px minmax(0,1.4fr) minmax(0,1fr) minmax(0,1fr);min-height:56px}.pyr .iyon2{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:11.5px;font-weight:700;color:#fff}.pyr .iyon2.L{background:var(--fa)}.pyr .iyon2.S{background:var(--fe)}
.pyeb{margin:14px 2px 8px}.pyet{display:flex;justify-content:space-between;align-items:baseline;font-size:15px}.pyeb .k2{color:var(--soluk);font-size:12.5px;margin-top:2px}.pyeb .art{color:var(--fa)}.pyeb .eks{color:var(--fe)}
#piyelle{border-bottom:1px solid var(--cizgi);padding-bottom:12px;margin-bottom:10px}#piyelle .pyeb{margin-top:4px}
.pybos{padding:14px 12px;border-radius:10px;background:var(--kart2);color:var(--soluk);font-size:13px}
.pyk{--fa:#0a7d45;--fe:#c42b20}@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .pyk{--fa:var(--art);--fe:var(--eks)}}:root[data-theme="dark"] .pyk{--fa:var(--art);--fe:var(--eks)}
.pya{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.pya input{flex:1 1 160px;min-width:0;height:44px;font-size:16px;border:1px solid var(--cizgi);border-radius:10px;background:var(--kart);color:var(--yazi);padding:0 10px;font:inherit}
.pyb{font-size:12px;color:var(--soluk);margin:14px 2px 6px;display:flex;justify-content:space-between;gap:8px}
.pyl{display:flex;flex-direction:column;gap:2px}
.pyr{position:relative;display:grid;grid-template-columns:28px minmax(0,1.3fr) minmax(0,1fr) 74px minmax(0,.9fr) 66px;gap:6px;align-items:center;min-height:48px;padding:4px 8px;border-radius:10px;background:var(--kart)}
.pyr:not(.ust) a::after{content:"";position:absolute;inset:0;border-radius:10px}.pyr:not(.ust):active{background:var(--kart2)}.pyr a:focus-visible{outline:none}.pyr a:focus-visible::after{outline:2px solid var(--vurgu);outline-offset:-2px}
.pyr .yd{position:relative;z-index:1;width:40px;height:40px;margin:0 -8px 0 -10px;border:0;background:none;color:var(--soluk);font-size:18px;cursor:pointer;padding:0;line-height:1;border-radius:10px}.pyr .yd:focus-visible{outline:2px solid var(--vurgu)}.pyr .yd.on{color:var(--uyari)}
.pyr a{color:var(--yazi);text-decoration:none;font-weight:650;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pyr .r{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.pyr .k2{color:var(--soluk);font-size:12px}
.pyr .rz{font-size:10.5px;font-weight:650;padding:1px 5px;border-radius:6px;margin-left:5px;background:var(--kart2);color:var(--soluk)}
.pyr .art{color:var(--art)}.pyr .eks{color:var(--eks)}
.pyr.ust{background:none;color:var(--soluk);font-size:11.5px;padding-top:0;padding-bottom:0}
.fl-a{animation:fla .8s}.fl-e{animation:fle .8s}
@keyframes fla{from{background:color-mix(in srgb,var(--art) 22%,transparent)}}@keyframes fle{from{background:color-mix(in srgb,var(--eks) 22%,transparent)}}
@media (max-width:600px){.pyr{grid-template-columns:24px minmax(0,1.2fr) minmax(0,1fr) 64px 58px}.pyr .hc{display:none}}
/* MADDE 834-836: panelden işlem penceresi — grafik önde, ayarla -> onayla (basılı tut), eylem başparmak bölgesinde */
.isl{padding:10px 16px 0 !important;--dy:#fff;--fa:#0a7d45;--fe:#c42b20}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .isl{--dy:#0F1115;--fa:var(--art);--fe:var(--eks)}}:root[data-theme="dark"] .isl{--dy:#0F1115;--fa:var(--art);--fe:var(--eks)}
.isl .ihd{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}.isl .iad{display:flex;align-items:center;gap:8px}.isl .iad b{font-size:19px;font-weight:700;letter-spacing:-.2px}
.isl .irz{font-size:12px;font-weight:650;color:color-mix(in srgb,var(--uyari) 78%,var(--yazi));background:color-mix(in srgb,var(--uyari) 13%,transparent);border-radius:999px;padding:2px 9px}
.isl .ifr{display:flex;align-items:baseline;gap:8px;margin-top:2px;font-variant-numeric:tabular-nums}.isl .ifr #islfiy{font-size:30px;font-weight:700;letter-spacing:-.6px}.isl .ifr .art,.isl .ifr .eks{font-weight:650;font-size:14px}
.isl .igk{margin:0 -16px;padding:0 8px 4px;border-bottom:1px solid var(--cizgi)}.isl .igb{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:0 8px 6px}
.isl .igr{width:100%;min-height:220px}.isl .igr svg{display:block;width:100%;height:auto;overflow:visible}.isl .igbos{height:220px;display:grid;place-items:center;color:var(--soluk);font-size:13px}
.isl .igiz{stroke:var(--cizgi);stroke-width:1}.isl .igt{fill:var(--soluk);font-size:10px}
.isl .igu{stroke:var(--art);stroke-width:1}.isl .igd{stroke:var(--eks);stroke-width:1}.isl .igub{fill:var(--art)}.isl .igdb{fill:var(--eks)}
.isl .igcu{stroke:var(--art);stroke-width:2}.isl .igcd{stroke:var(--eks);stroke-width:2}.isl .igua{stop-color:var(--art)}.isl .igda{stop-color:var(--eks)}
.isl .igl{stroke-width:1.4}.isl .igl.gir{stroke:var(--vurgu);stroke-width:2}.isl .igl.tp{stroke:var(--art)}.isl .igl.sl{stroke:var(--eks)}.isl .igl.lik{stroke:var(--uyari)}.isl .igl.lim{stroke:var(--mor)}
.isl .igl.plan{opacity:.6}.isl .igl.simdi{stroke:var(--yazi);opacity:.5;stroke-width:1}
.isl .ige rect{fill:var(--soluk)}.isl .ige text{fill:var(--dy);font-size:10.5px;font-weight:650;font-variant-numeric:tabular-nums}
.isl .ige.gir rect{fill:var(--vurgu)}.isl .ige.tp rect{fill:var(--art)}.isl .ige.sl rect{fill:var(--eks)}.isl .ige.lik rect{fill:var(--uyari)}.isl .ige.lim rect{fill:var(--mor)}.isl .ige.simdi rect{fill:var(--yazi)}.isl .ige.simdi text{fill:var(--bg)}
.isl .ige.plan rect{opacity:.7}
.isl .igad rect{fill:var(--kart);stroke-width:1.2}.isl .igad text{font-size:10px;font-weight:700}
.isl .igad.gir rect{stroke:var(--vurgu)}.isl .igad.gir text{fill:var(--vurgu)}.isl .igad.tp rect{stroke:var(--art)}.isl .igad.tp text{fill:var(--art)}
.isl .igad.sl rect{stroke:var(--eks)}.isl .igad.sl text{fill:var(--eks)}.isl .igad.lik rect{stroke:var(--uyari)}.isl .igad.lik text{fill:var(--uyari)}
.isl .igad.lim rect{stroke:var(--mor)}.isl .igad.lim text{fill:var(--mor)}.isl .igad.plan{opacity:.8}
.isl .igal{fill:var(--art);color:var(--art)}.isl .igsat{fill:var(--eks);color:var(--eks)}
.isl .ichip{display:flex;gap:4px;margin-top:8px}.isl .ichip button{flex:1;min-width:0;height:40px;border-radius:10px;border:0;background:var(--kart2);color:var(--soluk);font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.isl .ichip button.on{background:var(--yazi);color:var(--bg)}.isl .igb .ichip{margin:0}.isl .ichip.ar{flex:0 1 250px}.isl .ichip.gt{flex:0 0 84px}.isl .igb .ichip button{height:36px;font-size:12.5px;background:none}.isl .igb .ichip button.on{background:var(--kart2);color:var(--yazi)}
.isl .ichip.kisa{margin:0;flex:0 0 168px}.isl .ichip.kisa button{height:40px}
.isl .iseg{display:flex;gap:8px;margin-top:14px}.isl .iseg button{flex:1;min-width:0;height:42px;border-radius:12px;border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);font:inherit;font-weight:650;cursor:pointer}
.isl .iseg button.on{background:var(--yazi);color:var(--bg);border-color:var(--yazi)}.isl .iseg.yon button{height:48px;font-size:16px}
.isl .iseg.gor{background:var(--kart2);border-radius:12px;padding:3px;gap:3px}.isl .iseg.gor button{border:0;background:none;color:var(--soluk);height:36px}.isl .iseg.gor button.on{background:var(--kart);color:var(--yazi);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.isl .iseg button.L.on{background:var(--fa);border-color:var(--fa);color:var(--dy)}.isl .iseg button.S.on{background:var(--fe);border-color:var(--fe);color:var(--dy)}
.isl .iseg.kucuk button{height:38px;font-size:13.5px}.isl .iseg button.tehlike{color:var(--eks);border-color:color-mix(in srgb,var(--eks) 45%,transparent)}.isl .iseg button.birincil{background:var(--vurgu);border-color:var(--vurgu);color:var(--dy)}
.isl .isat{display:flex;justify-content:space-between;align-items:center;margin-top:14px}.isl .isat .ibas{margin:0}
.isl .ibas{display:block;font-size:12.5px;font-weight:600;color:var(--soluk);margin:16px 0 6px}
.isl input{width:100%;height:46px;border:1px solid var(--cizgi);border-radius:12px;background:var(--kart);color:var(--yazi);padding:0 12px;font:inherit;font-size:16px;font-variant-numeric:tabular-nums;margin-top:8px}
.isl input:focus{outline:none;border-color:var(--vurgu);box-shadow:0 0 0 3px color-mix(in srgb,var(--vurgu) 18%,transparent)}
.isl .ipara{position:relative}.isl .ipara input{font-size:20px;font-weight:650;height:52px}.isl .ipara span{position:absolute;right:14px;top:calc(50% + 4px);transform:translateY(-50%);color:var(--soluk);font-weight:600}
.isl .iki{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.isl .iacil{display:flex;justify-content:space-between;align-items:center;width:100%;height:44px;margin-top:14px;border:1px solid var(--cizgi);border-radius:12px;background:var(--kart);color:var(--yazi);font:inherit;font-weight:600;padding:0 14px;cursor:pointer}
.isl .iacil i{font-style:normal;font-size:12px;color:var(--soluk)}.isl .iacil.on i{color:var(--vurgu)}.isl .iacil:disabled{cursor:default;opacity:.8}
.isl #isltah{margin-top:12px}.isl .itg{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;background:var(--kart2);border-radius:12px;padding:10px 12px;font-size:13px;font-variant-numeric:tabular-nums}
.isl .itg div{display:flex;justify-content:space-between;gap:8px}.isl .itg span{color:var(--soluk)}
.isl .ion{font-size:12.5px;margin:8px 0 0;line-height:1.45}
.isl .ionay{margin-top:14px}.isl .iob{font-size:17px;font-weight:700;margin-bottom:10px}
.isl .iozt{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;background:var(--kart2);border-radius:14px;padding:12px 14px;font-variant-numeric:tabular-nums}
.isl .iozt div{display:flex;flex-direction:column;gap:2px}.isl .iozt .k{font-size:12px}
.isl .ipoz{background:var(--kart2);border-radius:16px;padding:14px;margin-top:14px}.isl .iph{display:flex;justify-content:space-between;align-items:center}
.isl .iyon{font-size:12px;font-weight:700;padding:3px 10px;border-radius:999px;color:var(--dy);margin-right:8px}.isl .iyon.L{background:var(--fa)}.isl .iyon.S{background:var(--fe)}.isl .iadet{font-weight:600}
.isl .ikz{font-size:22px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;line-height:1.15}.isl .ikz small{display:block;font-size:12.5px;font-weight:600}
.isl .ikg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px;font-size:14px;font-variant-numeric:tabular-nums}.isl .iku{display:flex;flex-direction:column;gap:2px}.isl .iku .k{font-size:12px}.isl .iku b{font-weight:600}
.isl .ilik{display:flex;align-items:center;gap:10px;margin-top:12px}.isl .ilikb{flex:1;height:6px;border-radius:99px;background:var(--cizgi);overflow:hidden}.isl .ilikb span{display:block;height:100%;border-radius:99px}
.isl .ilikb .ye{background:var(--art)}.isl .ilikb .tu{background:var(--uyari)}.isl .ilikb .kr{background:var(--eks)}
.isl .ibek{display:flex;justify-content:space-between;font-size:13px;padding:9px 2px;border-bottom:1px solid var(--cizgi)}
.isl .imsj{margin-top:12px;padding:10px 12px;border-radius:12px;font-size:13.5px;display:flex;align-items:center;gap:8px}.isl .imsj.ok{background:color-mix(in srgb,var(--art) 14%,transparent)}.isl .imsj.hata{background:color-mix(in srgb,var(--eks) 14%,transparent)}
.isl .idur{font-size:11.5px;font-weight:700;border-radius:999px;padding:2px 8px;color:var(--dy)}.isl .idur.ok{background:var(--fa)}.isl .idur.bek{background:var(--uyari)}
.isl .ialt{position:sticky;bottom:0;display:flex;gap:8px;margin:16px -16px 0;padding:10px 16px calc(12px + env(safe-area-inset-bottom));background:var(--kart);border-top:1px solid var(--cizgi);z-index:2}
.isl .ibtn{flex:1;height:52px;border-radius:14px;border:0;font:inherit;font-size:16px;font-weight:700;cursor:pointer;background:var(--vurgu);color:var(--dy);position:relative;overflow:hidden;touch-action:none;-webkit-user-select:none;user-select:none}
.isl .ibtn.L{background:var(--fa)}.isl .ibtn.S{background:var(--fe)}.isl .ibtn.tehlike{background:var(--fe)}.isl .ibtn.vurgu{background:var(--vurgu)}.isl .ibtn:disabled{opacity:.5;cursor:default}
.isl .ibtn.geri{flex:0 0 108px;background:var(--kart2);color:var(--yazi)}
.isl .ibtn.tut::before{content:"";position:absolute;inset:0;width:0;background:rgba(255,255,255,.28);transition:width 0s}.isl .ibtn.tut.dolu::before{width:100%;transition:width .7s linear}
.isl .ibtn.tut span{position:relative}.isl .isah{margin-top:12px;padding:10px 12px;border-radius:12px;font-size:13px;line-height:1.45}.isl .isah.sen{background:color-mix(in srgb,var(--vurgu) 12%,transparent)}.isl .isah.bot{background:color-mix(in srgb,var(--uyari) 14%,transparent)}
.isl .ibek{align-items:center}.isl .ibx{height:36px;padding:0 14px;border-radius:10px;border:1px solid color-mix(in srgb,var(--eks) 45%,transparent);background:var(--kart);color:var(--fe);font:inherit;font-weight:650;cursor:pointer}.isl .iacil.kucuk2{height:auto;min-height:44px;padding:8px 14px;margin-top:8px}.isl .iacil.kucuk2 i{text-align:right}.isl .art,.pyk .art{color:var(--fa)}.isl .eks,.pyk .eks{color:var(--fe)}.isl .shx{width:44px;height:44px}.isl .iuyr{color:var(--uyari);font-size:12.5px;margin:8px 0 0}
.isl .igl3{display:flex;gap:14px;font-size:11.5px;color:var(--soluk);padding:2px 8px 6px}.isl .ibtn:focus-visible,.isl button:focus-visible{outline:2px solid var(--vurgu);outline-offset:2px}
@media (prefers-reduced-motion:reduce){.isl .ibtn.tut.dolu::before{transition:none}}
@media (max-width:420px){.isl .ikg{grid-template-columns:repeat(2,minmax(0,1fr))}.isl .ichip.kisa{flex-basis:150px}}
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
const SAYFALAR = [["ozet","Özet"],["poz","Pozisyonlar"],["piyasa","Piyasa"],["gecmis","Geçmiş"],["olay","Olaylar"]];
// MADDE 757: D tasarımı — alt menü simgeleri
const NAV_SVG = {ozet:'<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>', poz:'<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="5" rx="1.5"/><path d="M3 20h12"/>',
  gecmis:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', piyasa:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/><path d="M8 13l2-2 2 2 3-3"/>', olay:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>'};
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
// MADDE 832: PİYASA — kullanıcının kendi işlemleri için bütün USDⓈ-M perpetual coinlerin canlı listesi (en çok yükselen / düşen,
// funding, izleme listesi). Veri tarayıcıdan Binance'in HERKESE AÇIK uçlarından gelir (gerçek piyasa; anahtarsız): ilk görüntü REST
// (/fapi/v1/ticker/24hr + premiumIndex + exchangeInfo), sonra saniyelik akış (!ticker@arr + !markPrice@arr@1s). Panel yine emir
// veremez; coin adı Binance'te o coinin sayfasını açar. İzleme listesi yalnız bu tarayıcıda (localStorage).
let PIY_DOKUN = 0; addEventListener("pointerdown", e=>{ if (e.target.closest && e.target.closest("#piyic")) PIY_DOKUN = Date.now(); }, {passive: true});
let PIY = {}, PIY_WS = null, PIY_ACIK = false, PIY_EVREN = null, PIY_ZAMAN = 0, PIY_ONCEKI = {}, PIY_HATA = "", PIY_SON_CIZ = 0;
const PIY_DEP = (a, v) => { try { return v===undefined ? JSON.parse(localStorage.getItem(a)) : localStorage.setItem(a, JSON.stringify(v)); } catch(_){ return null; } };
let PIY_IZLE = new Set(PIY_DEP("carry_izle") || []), PIY_HACIM = PIY_DEP("carry_piy_hacim") ?? 10e6, PIY_MOD = PIY_DEP("carry_piy_mod") || "deg", PIY_ARA = "";
// madde 833: dönem (1 / 3 / 7 / 30 gün). 1 gün = Binance'in kayan 24 sa değişimi; diğerleri günlük mumlardan (son 31 gün, coin başına
// bir istek, 30 dk önbellek): şimdiki fiyat / N gün önceki günlük kapanış - 1. Yalnız listede görünecek coinler için (hacim süzgeci +
// izleme listesi + arama) indirilir; 6 paralel istek. Coin N günden yeniyse "—" (sıralamaya girmez).
let PIY_DONEM = [1,3,7,30].includes(PIY_DEP("carry_piy_donem")) ? PIY_DEP("carry_piy_donem") : 1, PIY_GUN = {}, PIY_GYUK = {bek: 0, bit: 0, calis: false};
const PIY_DAD = {1: "24 sa", 3: "3 gün", 7: "1 hafta", 30: "1 ay"};
function piyDeg(o){
  if (PIY_DONEM == 1) return o.p;
  const g = PIY_GUN[o.s]; if (!g || !(o.f > 0)) return null;
  const i = g.c.length - 1 - PIY_DONEM; return i >= 0 && g.c[i] > 0 ? (o.f / g.c[i] - 1) * 100 : null;
}
async function piyGecmisYukle(){
  if (VERI_GOMULU || PIY_DONEM == 1 || PIY_GYUK.calis || sayfa != "piyasa") return;
  const A = Object.values(PIY).filter(o => o.f>0 && (!PIY_EVREN || PIY_EVREN.has(o.s)) && o.s.endsWith("USDT"));
  const S = A.filter(o => (o.q||0) >= PIY_HACIM || PIY_IZLE.has(o.s) || (PIY_ARA && o.s.includes(PIY_ARA))).map(o => o.s)
    .filter(s => !PIY_GUN[s] || Date.now() - PIY_GUN[s].t > 30 * 60e3);
  if (!S.length) return;
  PIY_GYUK = {bek: S.length, bit: 0, calis: true}; piyasaBoya(true);
  let i = 0;
  const isci = async () => { while (i < S.length){ const s = S[i++];
    try { const d = await (await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=1d&limit=31`, {cache:"no-store"})).json();
      if (Array.isArray(d)) PIY_GUN[s] = {t: Date.now(), c: d.map(x => +x[4])}; } catch(_){}
    PIY_GYUK.bit++; if (PIY_GYUK.bit % 20 == 0) piyasaBoya(true); } };
  await Promise.all([1,2,3,4,5,6].map(isci));
  PIY_GYUK.calis = false; piyasaBoya(true);
}
function piyDonem(d){ PIY_DONEM = d; PIY_MOD = "deg"; PIY_DEP("carry_piy_donem", d); PIY_DEP("carry_piy_mod", "deg"); ciz(); piyGecmisYukle(); }
async function piyasaIlk(){
  try {
    const [t, m, e] = await Promise.all(["ticker/24hr", "premiumIndex", PIY_EVREN ? null : "exchangeInfo"].map(u => u ? fetch("https://fapi.binance.com/fapi/v1/"+u, {cache:"no-store"}).then(r=>r.json()) : null));
    if (e && Array.isArray(e.symbols)) PIY_EVREN = new Set(e.symbols.filter(x=>x.contractType=="PERPETUAL" && x.quoteAsset=="USDT" && x.status=="TRADING").map(x=>x.symbol));
    if (Array.isArray(t)) for (const x of t) piyTicker({s:x.symbol, c:x.lastPrice, P:x.priceChangePercent, q:x.quoteVolume});
    if (Array.isArray(m)) for (const x of m) piyMark({s:x.symbol, r:x.lastFundingRate, T:x.nextFundingTime});
    PIY_HATA = ""; PIY_ZAMAN = Date.now();
  } catch(_){ PIY_HATA = "Binance'e ulaşılamadı"; }
  piyasaBoya(true); piyGecmisYukle();
}
function piyTicker(d){ if (!d || !d.s) return; const o = PIY[d.s] || (PIY[d.s] = {s: d.s});
  if (+d.c > 0){ if (o.f && +d.c !== o.f) PIY_ONCEKI[d.s] = +d.c > o.f ? 1 : -1; o.f = +d.c; }
  if (d.P!=null) o.p = +d.P; if (d.q!=null) o.q = +d.q; }
function piyMark(d){ if (!d || !d.s) return; const o = PIY[d.s] || (PIY[d.s] = {s: d.s}); if (d.r!=null && d.r!=="") o.r = +d.r; if (d.T) o.T = +d.T; }
function piyasaBagla(ac){
  PIY_ACIK = ac;
  if (VERI_GOMULU || !window.WebSocket) return;
  if (!ac){ if (PIY_WS){ PIY_WS.onclose = null; PIY_WS.close(); PIY_WS = null; } return; }
  if (PIY_WS && PIY_WS.readyState <= 1) return;
  if (!PIY_ZAMAN || Date.now() - PIY_ZAMAN > 60e3) piyasaIlk(); else setTimeout(piyGecmisYukle, 0);
  if (!ISL_DURUM || Date.now() - (islDurum.t||0) > 60e3){ islDurum.t = Date.now(); islDurum(); }   // madde 834
  PIY_WS = new WebSocket("wss://fstream.binance.com/market/stream?streams=!ticker@arr/!markPrice@arr@1s");
  PIY_WS.onmessage = e => { try { const m = JSON.parse(e.data), d = m.data, A = Array.isArray(d) ? d : [d];
    const tk = String(m.stream||"").startsWith("!ticker"); for (const x of A) tk ? piyTicker(x) : piyMark(x); PIY_ZAMAN = Date.now(); PIY_HATA = ""; } catch(_){} };
  PIY_WS.onclose = () => { PIY_WS = null; if (PIY_ACIK) setTimeout(()=>piyasaBagla(PIY_ACIK), 5000); };
}
function piyIzle(s){ PIY_IZLE.has(s) ? PIY_IZLE.delete(s) : PIY_IZLE.add(s); PIY_DEP("carry_izle", [...PIY_IZLE]); piyasaBoya(true); piyGecmisYukle(); }
function piyHacim(v){ PIY_HACIM = v; PIY_DEP("carry_piy_hacim", v); ciz(); piyGecmisYukle(); }
function piyMod(v){ PIY_MOD = v; PIY_DEP("carry_piy_mod", v); ciz(); }
function piyAra(v){ PIY_ARA = String(v||"").toUpperCase().replace(/[^A-Z0-9]/g, ""); piyasaBoya(true); clearTimeout(piyAra.z); piyAra.z = setTimeout(piyGecmisYukle, 400); }
const piyFiyat = f => f==null ? "—" : f >= 1000 ? f.toLocaleString("tr-TR", {maximumFractionDigits: 1}) : f >= 1 ? f.toLocaleString("tr-TR", {maximumFractionDigits: 4})
  : f.toLocaleString("tr-TR", {maximumSignificantDigits: 4});
const piyHac = q => q==null ? "—" : q >= 1e9 ? (q/1e9).toFixed(1).replace(".",",")+" Mr" : q >= 1e6 ? (q/1e6).toFixed(1).replace(".",",")+" M" : Math.round(q/1e3)+" B";
const piyYz = (v, b=2) => v==null || isNaN(v) ? "—" : (v>0?"+":"") + v.toFixed(b).replace(".",",") + "%";
function piyRozet(k){   // botun / senin bu coindeki durumun
  const R = {}; for (const [s,p] of Object.entries((k && k.pozisyonlar) || {})) R[s] = "bot " + (p.yon=="S" ? "S" : "L");
  for (const c of (k && k.coin_ozet) || []) if (c.elle) R[c.s.endsWith("USDT") ? c.s : c.s+"USDT"] = "✋ elle";
  return R;
}
function piySatir(o, R){
  const yd = PIY_IZLE.has(o.s), fl = PIY_ONCEKI[o.s], ad = o.s.replace(/USDT$/, "");
  return `<div class="pyr ${fl>0?"fl-a":fl<0?"fl-e":""}"><button class="yd ${yd?"on":""}" title="${yd?"izleme listesinden çıkar":"izleme listesine ekle"}" aria-label="${ad} ${yd?"izleme listesinden çıkar":"izleme listesine ekle"}" aria-pressed="${yd}" onclick="piyIzle('${o.s}')">${yd?"★":"☆"}</button>
    <span style="min-width:0;display:flex;align-items:center">${ISL_DURUM && ISL_DURUM.acik ? `<a href="#piyasa" onclick="islAc('${o.s}');return false" title="al / sat">${ad}</a>` : `<a href="https://www.binance.com/tr/futures/${o.s}" target="_blank" rel="noopener noreferrer" title="Binance'te aç">${ad}</a>`}${R[o.s]?`<span class="rz">${R[o.s]}</span>`:""}</span>
    <span class="r">${piyFiyat(o.f)}</span><span class="r ${o.d>0?"art":o.d<0?"eks":""}"><b>${piyYz(o.d)}</b></span>
    <span class="r k2 hc">${piyHac(o.q)}</span><span class="r k2 ${o.r>0?"":o.r<0?"eks":""}" title="son funding oranı (8 sa)">${o.r==null?"—":piyYz(o.r*100, 3)}</span></div>`;
}
function piyListe(k){
  const A = Object.values(PIY).filter(o => o.f>0 && o.p!=null && (!PIY_EVREN || PIY_EVREN.has(o.s)) && o.s.endsWith("USDT"));
  for (const o of A) o.d = piyDeg(o);
  const DA = PIY_DAD[PIY_DONEM];
  const R = piyRozet(k), ust = `<div class="pyr ust"><span></span><span>coin</span><span class="r">fiyat</span><span class="r">${DA}</span><span class="r hc">hacim</span><span class="r">funding</span></div>`;
  const blok = (bas, L, not) => `<div class="pyb"><span>${bas}</span><span>${not||""}</span></div><div class="pyl">${L.length ? ust + L.map(o=>piySatir(o, R)).join("") : `<div class="pybos">${Object.keys(PIY).length ? "Bu süzgeçte coin yok. Hacim sınırını düşürmeyi dene." : "Piyasa verisi yükleniyor…"}</div>`}</div>`;
  if (PIY_ARA){
    const L = A.filter(o => o.s.includes(PIY_ARA)).sort((a,b)=>(b.q||0)-(a.q||0)).slice(0, 40);
    return blok(`Arama: ${PIY_ARA}`, L, `${L.length} coin`);
  }
  const izl = A.filter(o => PIY_IZLE.has(o.s)).sort((a,b)=>(b.d??-1e9)-(a.d??-1e9));
  const H = A.filter(o => (o.q||0) >= PIY_HACIM), n = 15;
  const ana = PIY_MOD=="fund"
    ? blok("En yüksek funding (short'a ödeniyor)", H.filter(o=>o.r>0).sort((a,b)=>b.r-a.r).slice(0,n)) + blok("En negatif funding (long'a ödeniyor)", H.filter(o=>o.r<0).sort((a,b)=>a.r-b.r).slice(0,n))
    : blok(`En çok yükselen (${DA})`, H.filter(o=>o.d>0).sort((a,b)=>b.d-a.d).slice(0,n), piyYukNot()) + blok(`En çok düşen (${DA})`, H.filter(o=>o.d<0).sort((a,b)=>a.d-b.d).slice(0,n));
  return (izl.length ? blok("★ İzleme listem", izl, `${izl.length} coin`) : "") + ana;
}
function piyYukNot(){ return PIY_DONEM > 1 && PIY_GYUK.calis ? `geçmiş yükleniyor ${PIY_GYUK.bit}/${PIY_GYUK.bek}` : ""; }
function piyasaSayfa(k){
  const hb = (v, ad) => `<button class="${PIY_HACIM==v?"on":""}" onclick="piyHacim(${v})">${ad}</button>`, mb = (v, ad) => `<button class="${PIY_MOD==v?"on":""}" onclick="piyMod('${v}')">${ad}</button>`;
  return `<div class="kart pyk">
    <div class="dpb"><span class="gb">Piyasa</span><span class="k" id="piyd" role="status"></span></div>
    ${ISL_DURUM && ISL_DURUM.acik ? `<div id="piyelle">${elleHtml()}</div>` : ""}
    <div class="pya"><input id="piyara" type="search" aria-label="Coin ara" placeholder="Coin ara, örn. AKE" autocomplete="off" autocapitalize="characters" value="${PIY_ARA}" oninput="piyAra(this.value)">
      <div class="gdon">${[1,3,7,30].map(d=>`<button class="${PIY_MOD=="deg"&&PIY_DONEM==d?"on":""}" onclick="piyDonem(${d})">${PIY_DAD[d]}</button>`).join("")}${mb("fund","Funding")}</div></div>
    <div class="pya"><span class="k">hacim ≥</span><div class="gdon">${hb(1e6,"1 M$")}${hb(10e6,"10 M$")}${hb(50e6,"50 M$")}${hb(200e6,"200 M$")}</div></div>
    <div id="piyic">${piyListe(k)}</div>
    <div class="k" style="margin-top:10px">Gerçek Binance piyasası, saniyede bir güncellenir. ☆ ile izleme listene ekle (yalnız bu cihazda saklanır). ${ISL_DURUM && ISL_DURUM.acik ? `Coin adına dokununca <b>al / sat</b> penceresi açılır (${ISL_DURUM.mod=="live"?"CANLI hesap":"demo hesap"}, tek emir en fazla ${ISL_DURUM.max_usd} $, her emirde PIN).` : `Coin adına dokununca Binance'te açılır.${ISL_DURUM && ISL_DURUM.neden ? ` <span title="${ea(ISL_DURUM.neden)}">Panelden işlem kapalı.</span>` : ""}`}</div>
  </div>`;
}
// MADDE 839: POZİSYONLARIM — elle yönettiğin açık pozisyonlar (hesabın K/Z'si) + son 30 gün elle sonucu; 15 sn'de bir kapıdan.
let ELLE_OZ = null;
async function elleYukle(){
  if (VERI_GOMULU || !ISL_DURUM || !ISL_DURUM.acik || sayfa!="piyasa") return;
  elleYukle.t = Date.now(); const d = await islIstek("elle");
  ELLE_OZ = d.ok ? d : {hata: d.hata}; const el = $("#piyelle"); if (el) el.innerHTML = elleHtml();
}
function elleHtml(){
  const E = ELLE_OZ; if (!E) return `<div class="pyb"><span>Pozisyonlarım</span><span>yükleniyor…</span></div>`;
  if (E.hata) return `<div class="pyb"><span>Pozisyonlarım</span><span class="eks">${ea(E.hata)}</span></div>`;
  const S = E.sonuc || {}, P = E.pozisyonlar || [], top = P.reduce((a,x)=>a + x.kz, 0);
  const sonuc = S.kapanis ? `son 30 gün <b class="${sinif(S.net)}">${S.net>=0?"▲":"▼"} ${isaretli(S.net)}</b>, ${S.kapanis} kapanış, %${Math.round(S.kazanan / S.kapanis * 100)} kârlı` : "son 30 günde kapanan elle işlem yok";
  const satir = x => { const ad = x.sembol.replace(/USDT$/,""), uz = x.adet > 0, deger = Math.abs(x.adet) * x.giris, kp = deger ? x.kz / deger * 100 : 0;
    return `<div class="pyr pye"><span class="iyon2 ${uz?"L":"S"}">${uz?"L":"S"}</span>
      <span style="min-width:0;display:flex;flex-direction:column"><a href="#piyasa" onclick="islAc('${x.sembol}');return false">${ad}</a><span class="k2">${Math.abs(x.adet).toLocaleString("tr-TR")} adet @ ${piyFiyat(x.giris)}</span></span>
      <span class="r k2">${x.tp?`TP ${piyFiyat(x.tp)}`:""}${x.tp&&x.sl?"<br>":""}${x.sl?`stop ${piyFiyat(x.sl)}`:`<span class="uyr">stop yok</span>`}</span>
      <span class="r ${sinif(x.kz)}"><b>${x.kz>=0?"▲":"▼"} ${isaretli(x.kz)}</b><br><span class="k2">${(kp>=0?"+":"")+kp.toFixed(1).replace(".",",")}%</span></span></div>`; };
  return `<div class="pyeb"><div class="pyet"><b>Pozisyonlarım</b>${P.length ? `<b class="${sinif(top)}">${top>=0?"▲":"▼"} ${isaretli(top)}</b>` : ""}</div><div class="k2">${sonuc}</div></div>
    <div class="pyl">${P.length ? P.map(satir).join("") : `<div class="pybos">Elle açık pozisyonun yok. Aşağıdaki listeden bir coine dokunup işlem açabilirsin.</div>`}</div>`;
}
function piyasaBoya(zorla){
  if (sayfa!="piyasa") return;
  if (ISL_DURUM && ISL_DURUM.acik && Date.now() - (elleYukle.t||0) > 15e3) elleYukle();
  if (PIY_DONEM > 1 && Date.now() - (piyasaBoya.g||0) > 60e3){ piyasaBoya.g = Date.now(); setTimeout(piyGecmisYukle, 0); }   // 30 dk'yı geçen önbellek yenilenir
  const el = $("#piyic"), d = $("#piyd"); if (!el) return;
  if (d) d.textContent = PIY_HATA || (PIY_ZAMAN ? (Date.now()-PIY_ZAMAN < 10e3 ? "● canlı" : "bağlantı bekleniyor…") : "yükleniyor…");
  if (!zorla && Date.now() - PIY_SON_CIZ < 900) return;
  if (!zorla && Date.now() - PIY_DOKUN < 600) return;   // madde 837: parmak listedeyken yeniden çizme (dokunuş kaybolmasın)
  PIY_SON_CIZ = Date.now();
  const k = VERI && VERI.kurulumlar[secili]; el.innerHTML = piyListe(k); PIY_ONCEKI = {};
}
// MADDE 834: PANELDEN İŞLEM. Panel anahtarsız; istekler panel sunucusu üzerinden yalnız 127.0.0.1'deki carry-islem servisine gider.
// Her emir / kapat / TP-SL / iptal PIN ister (PIN yalnız bu pencere açıkken bellekte; kaydedilmez). Emirler `panel_` önekli gider ->
// bot coini kullanıcıya bırakır (madde 830). Hesap fiyatı (demo) piyasa listesindeki gerçek fiyattan farklı olabilir: önizleme hesabın
// işaret fiyatını gösterir.
let ISL_DURUM = null, ISL = null;
const ea = v => String(v==null?"":v).replace(/[&"<>']/g, c=>({"&":"&amp;",'"':"&quot;","<":"&lt;",">":"&gt;","'":"&#39;"}[c]));
async function islDurum(){
  if (VERI_GOMULU) return;
  try { const r = await fetch("api/islem/durum", {cache:"no-store"}); const d = await r.json(); ISL_DURUM = d && d.ok ? d : {acik:false, neden: d && d.hata}; }
  catch(_){ ISL_DURUM = {acik:false, neden:"işlem servisine ulaşılamadı"}; }
  if (sayfa=="piyasa" && VERI && !ISL) ciz();   // alt not + coin bağlantıları işlem durumuna göre
}
async function islIstek(yol, govde){
  const r = await fetch("api/islem/" + yol, govde ? {method:"POST", headers:{"Content-Type":"application/json","X-Carry-Islem":"1"}, body: JSON.stringify(govde), cache:"no-store"} : {cache:"no-store"});
  let d = null; try { d = await r.json(); } catch(_){}
  if (!d) d = {ok:false, hata:`sunucu yanıtı okunamadı (${r.status})`};
  return d;
}
function islAc(s, yon){
  const yer = k => { try { return localStorage.getItem(k); } catch(_){ return null; } };
  ISL = {s, yon: yon || "L", usd: Math.min(50, (ISL_DURUM||{}).max_usd||50), boyut: "usd", risk: 5, tip:"MARKET", fiyat:"", tp:"", sl:"", tpsl: false,
         pin:"", poz:null, oniz:null, msj:null, mesgul:false, gor: yon ? "emir" : "poz", adim: null,
         aralik: yer("carry_isl_ar") || "1h", gtur: yer("carry_isl_gt") || "mum"};
  const el = $("#sheet"); el.hidden = false;
  el.innerHTML = `<div class="shb" onclick="islKapat()"></div><div class="shp isl" role="dialog" aria-modal="true" tabindex="-1" aria-label="${s.replace(/USDT$/,"")} işlem"><div class="shh"></div><div id="islic"></div></div>`;
  document.body.style.overflow = "hidden"; islCiz(); islPozYukle(); islMumYukle();
  ISL.donus = document.activeElement; const sp = el.querySelector(".shp"); if (sp) sp.focus({preventScroll: true});   // ekran okuyucu / klavye pencereye
}
function islKapat(){ const d = ISL && ISL.donus; ISL = null; const el = $("#sheet"); el.hidden = true; el.innerHTML = ""; document.body.style.overflow = ""; if (d && d.focus) try { d.focus({preventScroll: true}); } catch(_){} }
addEventListener("keydown", e=>{ if (e.key === "Escape" && ISL){ if (ISL.adim){ ISL.adim = null; islCiz(); } else islKapat(); } });
async function islPozYukle(){ if (!ISL) return; const s = ISL.s; const d = await islIstek("pozisyon/" + s);
  if (ISL && ISL.s==s){ const ilk = !ISL.poz; ISL.poz = d.ok ? d : {hata: d.hata};
    if (ilk && d.ok){ const t = (d.tpsl||[]).find(x=>x.tur=="TP"), l = (d.tpsl||[]).find(x=>x.tur=="SL");
      if (d.pozisyon && d.pozisyon.adet){ if (t) ISL.tp = t.fiyat; if (l) ISL.sl = l.fiyat; } else if (ISL.gor=="poz") ISL.gor = "emir"; }
    islCiz(); } }
// MADDE 835-836: GRAFİK — gerçek Binance mumları (ya da çizgi); giriş, TP / stop, likidasyon, plan çizgileri, dolum işaretleri.
const ISL_AR = {"15m": ["15 dk", 96], "1h": ["1 sa", 120], "4h": ["4 sa", 120], "1d": ["1 gün", 120]};
let MUMI = {};
async function islMumYukle(zorla){
  if (!ISL || VERI_GOMULU) return; const s = ISL.s, a = ISL.aralik, k = s + "|" + a, M = MUMI[k];
  if (!zorla && M && Date.now() - M.t < 60e3) { islGrafikCiz(); return; }
  try { const d = await (await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=${a}&limit=${ISL_AR[a][1]}`, {cache:"no-store"})).json();
    if (Array.isArray(d)) MUMI[k] = {t: Date.now(), d: d.map(x=>[+x[0], +x[1], +x[2], +x[3], +x[4], +x[6]])}; } catch(_){}
  islGrafikCiz();
}
function islAralik(a){ if (!ISL) return; ISL.aralik = a; try { localStorage.setItem("carry_isl_ar", a); } catch(_){} islCiz(); islMumYukle(); }
function islGTur(t){ if (!ISL) return; ISL.gtur = t; try { localStorage.setItem("carry_isl_gt", t); } catch(_){} islCiz(); }
function islGrafik(W, H){
  const I = ISL, M = MUMI[I.s + "|" + I.aralik]; if (!M || !M.d.length) return `<div class="igbos">grafik yükleniyor…</div>`;
  const D = M.d.map(x=>x.slice()), f = (PIY[I.s]||{}).f;
  if (f > 0){ const z = D[D.length-1]; if (Date.now() < z[5]){ z[4] = f; z[2] = Math.max(z[2], f); z[3] = Math.min(z[3], f); } }
  const P = I.poz && I.poz.pozisyon, T = (I.poz && I.poz.tpsl) || [], cizgi = [];
  const ekle = (v, ad, cls, kesik) => { v = +v; if (v > 0) cizgi.push({v, ad, cls, kesik}); };
  if (P && P.adet){ ekle(P.giris, "Giriş", "gir"); if (P.likidasyon > 0) ekle(P.likidasyon, "Likidasyon", "lik", true); }
  for (const t of T) ekle(t.fiyat, t.tur=="TP" ? "TP" : "Stop", t.tur=="TP" ? "tp" : "sl", true);
  const varTP = T.some(t=>t.tur=="TP" && Math.abs(t.fiyat - I.tp) < 1e-12), varSL = T.some(t=>t.tur=="SL" && Math.abs(t.fiyat - I.sl) < 1e-12);
  if (+I.tp > 0 && !varTP) ekle(I.tp, "plan TP", "tp plan", true);
  if (+I.sl > 0 && !varSL) ekle(I.sl, "plan stop", "sl plan", true);
  if (I.gor=="emir" && I.tip=="LIMIT" && +I.fiyat > 0) ekle(I.fiyat, "Limit", "lim plan", true);
  const sag = 66, alt = 18, w = W - sag, h = H - alt, n = D.length, t0 = D[0][0], adimT = n > 1 ? (D[1][0] - D[0][0]) : 3600e3, t1 = D[n-1][0] + adimT;
  let lo = Math.min(...D.map(x=>x[3])), hi = Math.max(...D.map(x=>x[2]));
  for (const c of cizgi) if (c.v > lo * 0.7 && c.v < hi * 1.3){ lo = Math.min(lo, c.v); hi = Math.max(hi, c.v); }   // çok uzak çizgi ekseni ezmesin
  const pad = (hi - lo) * 0.08 || hi * 0.01; lo -= pad; hi += pad;
  const Y = v => h - (v - lo) / (hi - lo) * h, X = t => (t - t0) / (t1 - t0) * w, bw = Math.max(1, w / n * 0.66);
  let g = "";
  for (let i = 0; i <= 4; i++){ const v = lo + (hi - lo) * i / 4, y = Y(v); g += `<line x1="0" x2="${w}" y1="${y}" y2="${y}" class="igiz"/>`; }
  const TZ = a => { const d = new Date(a); return I.aralik=="1d" || I.aralik=="4h" ? `${d.getDate()}.${d.getMonth()+1}` : `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`; };
  for (let i = 1; i <= 3; i++){ const t = t0 + (t1 - t0) * i / 4; g += `<text x="${X(t)}" y="${H - 4}" class="igt" text-anchor="middle">${TZ(t)}</text>`; }
  if (I.gtur=="cizgi"){   // çizgi + alan: uzun vadeli bakışta sade
    const pts = D.map(x=>`${(X(x[0]) + (w / n) / 2).toFixed(1)},${Y(x[4]).toFixed(1)}`), yuk = D[n-1][4] >= D[0][1];
    g += `<defs><linearGradient id="igalan" x1="0" x2="0" y1="0" y2="1"><stop offset="0" class="${yuk?"igua":"igda"}" stop-opacity=".28"/><stop offset="1" class="${yuk?"igua":"igda"}" stop-opacity="0"/></linearGradient></defs>`
      + `<path d="M${pts[0].split(",")[0]},${h} L${pts.join(" L")} L${pts[n-1].split(",")[0]},${h} Z" fill="url(#igalan)"/><polyline points="${pts.join(" ")}" class="${yuk?"igcu":"igcd"}" fill="none"/>`;
  } else for (const [t, o, hh, l, c] of D){ const x = X(t) + (w / n) / 2, yu = c >= o; const y1 = Y(Math.max(o, c)), y2 = Y(Math.min(o, c));
    g += `<line x1="${x}" x2="${x}" y1="${Y(hh)}" y2="${Y(l)}" class="${yu?"igu":"igd"}"/><rect x="${x - bw/2}" y="${y1}" width="${bw}" height="${Math.max(1, y2 - y1)}" class="${yu?"igub":"igdb"}"/>`; }
  for (const tr of (I.poz && I.poz.islemler) || []){ if (tr.t < t0 || tr.t > t1 || !(tr.fiyat > 0)) continue;
    const x = X(tr.t), y = Y(tr.fiyat), al = tr.yon=="AL";
    g += `<path d="${al ? `M${x-5},${y+12} L${x+5},${y+12} L${x},${y+4} Z` : `M${x-5},${y-12} L${x+5},${y-12} L${x},${y-4} Z`}" class="${al?"igal":"igsat"}"><title>${tr.yon} ${tr.adet} @ ${piyFiyat(tr.fiyat)}</title></path>`; }
  const et = [];
  for (const c of cizgi){ const y = Y(c.v); if (y < -2 || y > h + 2){ et.push({y: y < 0 ? 6 : h - 6, c, disari: true}); continue; }
    g += `<line x1="0" x2="${w}" y1="${y}" y2="${y}" class="igl ${c.cls}" ${c.kesik?'stroke-dasharray="5 4"':""}/>`; et.push({y, c});
    const tw = c.ad.length * 6 + 10; g += `<g class="igad ${c.cls}"><rect x="2" y="${y - 8}" width="${tw}" height="16" rx="4"/><text x="7" y="${y + 4}">${c.ad}</text></g>`; }
  if (f > 0){ const y = Y(f); g += `<line x1="0" x2="${w}" y1="${y}" y2="${y}" class="igl simdi" stroke-dasharray="2 3"/>`; et.push({y, c: {v: f, ad: "", cls: "simdi"}}); }
  et.sort((a,b)=>a.y-b.y); for (let i = 1; i < et.length; i++) if (et[i].y - et[i-1].y < 15) et[i].y = et[i-1].y + 15;
  for (let i = et.length - 1; i >= 0; i--){ if (et[i].y > h - 7) et[i].y = h - 7; if (i < et.length - 1 && et[i+1].y - et[i].y < 15) et[i].y = et[i+1].y - 15; }
  for (const e of et){ const c = e.c; g += `<g class="ige ${c.cls}"><rect x="${w + 2}" y="${e.y - 7.5}" width="${sag - 3}" height="15" rx="3"/><text x="${w + 6}" y="${e.y + 4}">${e.disari ? (e.y < h/2 ? "↑" : "↓") : ""}${piyFiyat(c.v)}</text>${e.disari ? `<title>${c.ad} ${piyFiyat(c.v)} (grafik dışında)</title>` : ""}</g>`; }
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${I.s} fiyat grafiği">${g}</svg>`;
}
function islGrafikCiz(){ const el = $("#islgraf"); if (!el || !ISL) return; const W = Math.round(el.clientWidth || 320); el.innerHTML = islGrafik(W, 220);
  const fe = $("#islfiy"); if (fe){ const f = (PIY[ISL.s]||{}).f; if (f) fe.textContent = piyFiyat(f); } }
// MADDE 836: AKIŞ — 1) ayarla (canlı tahmin)  2) ONAY ekranı: özet + PIN + BASILI TUT (yanlışlıkla dokunuşla emir gitmez). Kapat / TP-stop / sil
// da aynı onay ekranından geçer. PIN pencere açık kaldıkça bellekte kalır (kaydedilmez). Boyut iki yolla: tutar ($) ya da RİSK ($): stop'a kadar
// kaybetmeyi göze aldığın tutar -> pozisyon büyüklüğü = risk × fiyat / |fiyat − stop| (en fazla izin verilen sınır).
function islSayi(v){ return String(v==null?"":v).trim().replace(/\s/g, "").replace(",", "."); }   // "0,45" -> "0.45" (Türkçe klavye)
const islGos = v => v===""||v==null ? "" : ea(String(v).replace(".", ","));   // kutuda Türkçe ondalık
function islAyar(k, v){
  if (!ISL) return; if (["usd","fiyat","tp","sl","risk"].includes(k)) v = islSayi(v); ISL[k] = v; if (k!="pin") ISL.oniz = null;
  if (["pin","usd","fiyat","tp","sl","risk"].includes(k)){ islTahmin(); islGrafikCiz(); islAltGuncelle(); } else islCiz(); }
function islGor(g){ if (!ISL) return; ISL.gor = g; ISL.msj = null; ISL.adim = null; islCiz(); }
function islYonSec(y){ if (!ISL) return; ISL.yon = y; ISL.gor = "emir"; ISL.adim = null; ISL.msj = null; ISL.oniz = null; islCiz(); }
function islRef(){ const I = ISL; return (I.tip=="LIMIT" && +I.fiyat>0 && I.gor=="emir") ? +I.fiyat : ((I.poz && I.poz.isaret) || (PIY[I.s]||{}).f); }
function islPozVar(){ const P = ISL.poz && ISL.poz.pozisyon; return !!(P && P.adet); }
function islYuzde(alan, y){
  if (!ISL) return; const P = ISL.poz && ISL.poz.pozisyon, uzun = ISL.gor=="poz" && islPozVar() ? P.adet > 0 : ISL.yon=="L", ref = islRef();
  if (!(ref>0)) return; const yon = alan=="tp" ? 1 : -1;
  ISL[alan] = +(ref * (1 + yon * (uzun?1:-1) * y / 100)).toPrecision(6); ISL.oniz = null; islCiz();
}
function islTPSL(){ return islPozVar() || !ISL.tpsl && ISL.boyut!="risk" ? {tp:"", sl:""} : {tp: ISL.tp, sl: ISL.sl}; }
function islBoyutUsd(){   // gönderilecek pozisyon büyüklüğü ($)
  const I = ISL, mx = (ISL_DURUM||{}).max_usd || 200;
  if (I.boyut!="risk") return +I.usd;
  const ref = islRef(), sl = +I.sl, r = +I.risk; if (!(ref>0 && sl>0 && r>0) || sl==ref) return 0;
  return Math.min(mx, Math.floor(r * ref / Math.abs(ref - sl) * 100 + 1e-6) / 100);   // kayan nokta artığı bir kuruş kaybettirmesin
}
function islTahminMetin(){
  const I = ISL, ref = islRef(), u = islBoyutUsd(); if (!(ref>0)) return "";
  if (I.boyut=="risk" && !(+I.sl>0)) return `<span class="uyr">Risk ile boyut için önce stop fiyatını gir.</span>`;
  if (!(u>0)) return "";
  const q = u / ref, sg = I.yon=="L" ? 1 : -1, T = islTPSL(), tp = +T.tp, sl = +T.sl;
  const kTP = tp>0 ? q * (tp - ref) * sg : null, kSL = sl>0 ? q * (sl - ref) * sg : null, kom = u * 0.0005;
  const sat = (a, b, cls="") => `<div><span>${a}</span><b class="${cls}">${b}</b></div>`;
  return `<div class="itg">${sat("Pozisyon", para(u) + (I.boyut=="risk" && u >= ((ISL_DURUM||{}).max_usd||200) ? " <span class='uyr'>(sınır)</span>" : ""))}${sat("Adet", "≈ " + (q >= 100 ? Math.round(q).toLocaleString("tr-TR") : (+q.toPrecision(4)).toLocaleString("tr-TR")))}
    ${kTP!=null ? sat("TP'de", "▲ " + isaretli(kTP), "art") : ""}${kSL!=null ? sat("Stop'ta", "▼ " + isaretli(kSL), "eks") : ""}
    ${kTP>0 && kSL<0 ? sat("Risk / ödül", "1 : " + (kTP / -kSL).toFixed(1).replace(".",",")) : ""}${sat("Komisyon", "≈ " + para(kom))}</div>`;
}
function islUyari(){   // sunucuya gitmeden önce yazarken uyar (sunucu yine de denetler)
  const I = ISL, P = I.poz && I.poz.pozisyon, uzun = I.gor=="poz" && islPozVar() ? P.adet > 0 : I.yon=="L", ref = I.gor=="poz" ? (I.poz && I.poz.isaret) : islRef(), m = (I.poz && I.poz.isaret) || ref;
  const tp = +I.tp, sl = +I.sl, U = [];
  if (!(ref > 0)) return "";
  if (tp > 0 && (uzun ? tp <= ref : tp >= ref)) U.push(`TP fiyatın ${uzun ? "üstünde" : "altında"} olmalı (şimdi ${piyFiyat(ref)}).`);
  if (sl > 0 && (uzun ? sl >= ref : sl <= ref)) U.push(`Stop fiyatın ${uzun ? "altında" : "üstünde"} olmalı (şimdi ${piyFiyat(ref)}).`);
  if (I.gor=="emir" && I.tip=="LIMIT" && +I.fiyat > 0 && m > 0 && Math.abs(+I.fiyat / m - 1) > 0.2) U.push("Limit fiyatı şimdiki fiyatın ±%20'si içinde olmalı.");
  if (I.gor=="emir" && I.boyut!="risk" && +I.usd > ((ISL_DURUM||{}).max_usd||200)) U.push(`Tek emir en fazla ${(ISL_DURUM||{}).max_usd||200} $.`);
  return U.map(x=>`<p class="iuyr" role="alert">⚠ ${x}</p>`).join("");
}
function islTahmin(){ const e = $("#isltah"); if (e) e.innerHTML = islTahminMetin(); const u = $("#isluyr"); if (u) u.innerHTML = islUyari(); }
function islAltGuncelle(){ const b = $("#islalt"); if (b) b.outerHTML = islAlt(); }
async function islDevam(){   // 1. adım -> onay ekranı (sunucu önizlemesi)
  if (!ISL || ISL.mesgul) return; const u = islBoyutUsd();
  if (!(u>0)){ ISL.msj = {hata: ISL.boyut=="risk" ? "Risk ile boyut için stop fiyatı ve risk tutarı gerekli." : "Tutar gir."}; islCiz(); return; }
  ISL.mesgul = true; ISL.msj = null; islCiz();
  const d = await islIstek("onizle", {sembol: ISL.s, yon: ISL.yon, usd: u, tip: ISL.tip, fiyat: ISL.fiyat, ...islTPSL()});
  if (!ISL) return; ISL.mesgul = false;
  if (!d.ok){ ISL.msj = {hata: d.hata}; islCiz(); return; }
  ISL.oniz = d; const O = d, sg = O.yon=="L" ? 1 : -1, f = (PIY[ISL.s]||{}).f;
  const S = [["Emir", `${O.yon=="L"?"Long":"Short"}, ${O.tip=="LIMIT"?"limit":"piyasa"}`], ["Adet", O.adet.toLocaleString("tr-TR")], ["Pozisyon", para(O.usd)],
             [O.tip=="LIMIT"?"Limit fiyatı":"Hesap fiyatı", piyFiyat(O.fiyat)]];
  if (O.tp) S.push(["TP", `${piyFiyat(O.tp)} <span class="art">▲ ${isaretli(O.adet*(O.tp-O.fiyat)*sg)}</span>`]);
  if (O.sl) S.push(["Stop", `${piyFiyat(O.sl)} <span class="eks">▼ ${isaretli(O.adet*(O.sl-O.fiyat)*sg)}</span>`]);
  S.push(["Komisyon", "≈ " + para(O.usd * 0.0005)]);
  const not = [];
  if (f && Math.abs(O.isaret/f-1) > 0.005) not.push(`Hesabın fiyatı piyasadaki gerçek fiyattan %${(Math.abs(O.isaret/f-1)*100).toFixed(1).replace(".",",")} farklı${O.mod=="live"?"":" (demo hesap)"}.`);
  if (O.not) not.push(O.not);
  const P0 = ISL.poz && ISL.poz.pozisyon, ters = islPozVar() && ((P0.adet > 0) != (O.yon=="L"));
  if (ters) not.push(`Hesap tek yönlü çalışır: bu emir önce mevcut ${P0.adet > 0 ? "long" : "short"} pozisyonu (${Math.abs(P0.adet).toLocaleString("tr-TR")} adet) azaltır; adet daha büyükse fazlası ters yönde pozisyon açar.`);
  else if (islPozVar()) not.push("Mevcut TP / stop toplam adede göre kendiliğinden güncellenir.");
  if (ISL.poz && ISL.poz.bot_tutuyor && !ISL.poz.elle) not.push("Bu coin şu an botun: emir gidince coin sana geçer, bot bu coindeki kendi emirlerini iptal eder ve coini bırakır.");
  ISL.adim = {tur: "emir", baslik: `${ISL.s.replace(/USDT$/,"")} ${ters ? (P0.adet > 0 ? "long'u azalt / çevir" : "short'u azalt / çevir") : O.yon=="L" ? "long aç" : "short aç"}`, satir: S, not, dugme: O.yon=="L" ? "Long aç" : "Short aç", renk: O.yon,
              govde: {sembol: ISL.s, yon: O.yon, usd: u, tip: ISL.tip, fiyat: ISL.fiyat, ...islTPSL()}};
  islCiz();
}
function islKapatOnay(oran){
  if (!ISL || !islPozVar()) return; const P = ISL.poz.pozisyon, f = ISL.poz.isaret || P.giris, q = Math.abs(P.adet) * oran;
  ISL.adim = {tur: "kapat", baslik: `${ISL.s.replace(/USDT$/,"")} ${oran>=1 ? "pozisyonu kapat" : "%" + oran*100 + " kapat"}`,
    satir: [["Kapanacak", `≈ ${(+q.toPrecision(5)).toLocaleString("tr-TR")} adet`], ["Değer", "≈ " + para(q * f)], ["Gerçekleşecek K/Z", `<span class="${sinif(P.kz)}">≈ ${isaretli(P.kz * oran)}</span>`],
            ["Fiyat", "piyasa fiyatından"]], not: oran>=1 ? ["Bu coinde panelden konan TP / stop / limit emirleri de silinir."] : ["Kalan adet için TP / stop aynı fiyatlarla yeniden kurulur."],
    dugme: oran>=1 ? "Tümünü kapat" : "Kapat", renk: "tehlike", yol: "kapat", govde: {sembol: ISL.s, oran}};
  ISL.msj = null; islCiz();
}
function islTPSLOnay(){
  if (!ISL || !islPozVar()) return; const tp = +ISL.tp || null, sl = +ISL.sl || null, P = ISL.poz.pozisyon, ref = ISL.poz.isaret;
  const ad = v => v ? `${piyFiyat(v)} <span class="k">${((v/ref-1)*100>=0?"+":"")}${((v/ref-1)*100).toFixed(1).replace(".",",")}%</span>` : "kaldırılır";
  ISL.adim = {tur: "tpsl", baslik: `${ISL.s.replace(/USDT$/,"")} TP / stop`, satir: [["TP", ad(tp)], ["Stop", ad(sl)], ["Kapsam", `pozisyonun tamamı, ${Math.abs(P.adet).toLocaleString("tr-TR")} adet`]],
    not: [], dugme: "Kaydet", renk: "vurgu", yol: "tpsl", govde: {sembol: ISL.s, tp: ISL.tp, sl: ISL.sl}};
  ISL.msj = null; islCiz();
}
function islEmirIptalOnay(oid, yon, adet, fiyat){
  if (!ISL) return;
  ISL.adim = {tur: "iptal", baslik: `${ISL.s.replace(/USDT$/,"")} bekleyen emri iptal`, satir: [["Emir", `limit ${yon=="BUY"?"alış":"satış"}`], ["Adet", (+adet).toLocaleString("tr-TR")], ["Fiyat", piyFiyat(+fiyat)]],
    not: [], dugme: "İptal et", renk: "tehlike", yol: "iptal", govde: {sembol: ISL.s, orderId: oid}};
  ISL.msj = null; islCiz();
}
function islBasaBas(){ if (!ISL || !islPozVar()) return; ISL.sl = ISL.poz.pozisyon.giris; ISL.oniz = null; islCiz(); }
function islSilOnay(){
  if (!ISL) return;
  ISL.adim = {tur: "iptal", baslik: `${ISL.s.replace(/USDT$/,"")} panel emirlerini sil`, satir: [["Silinecek", "panelden konan TP / stop / limit emirleri"], ["Dokunulmayan", "botun ve Binance uygulamasının emirleri"]],
    not: [], dugme: "Sil", renk: "tehlike", yol: "iptal", govde: {sembol: ISL.s}};
  ISL.msj = null; islCiz();
}
async function islOnayla(){   // basılı tutma tamamlanınca
  if (!ISL || !ISL.adim || ISL.mesgul) return;
  if (String(ISL.pin).length < 6){ ISL.msj = {hata: "İşlem PIN'ini gir."}; islCiz(); const p = $("#islpin"); if (p) p.focus(); return; }
  const A = ISL.adim, yol = A.tur=="emir" ? "emir" : A.yol; ISL.mesgul = true; islCiz();
  const d = await islIstek(yol, {...A.govde, pin: ISL.pin});
  if (!ISL) return; ISL.mesgul = false;
  if (!d.ok){ ISL.msj = {hata: d.hata}; islCiz(); return; }
  ISL.adim = null; ISL.oniz = null;
  ISL.msj = {ok: yol=="emir" ? `${d.emir.durum=="FILLED" ? "Doldu" : d.emir.durum=="NEW" ? "Emir bekliyor" : "Gönderildi"}: ${d.emir.tip=="LIMIT"?"limit":"piyasa"} ${d.emir.adet.toLocaleString("tr-TR")} adet`
                 + (d.tpsl && d.tpsl.length ? `, ${d.tpsl.map(x=>(x.tur=="SL"?"stop":x.tur)+" "+piyFiyat(x.fiyat)).join(", ")}` : "") + (d.tpsl_hata ? `. ⚠️ ${d.tpsl_hata}` : "")
             : yol=="kapat" ? `Kapatıldı: ${d.kapat.adet.toLocaleString("tr-TR")} adet` : yol=="tpsl" ? "TP / stop kaydedildi" : `Silindi: ${d.iptal} emir`, durum: yol=="emir" ? d.emir.durum : ""};
  islCiz();
  setTimeout(async ()=>{ if (!ISL) return; await islPozYukle(); if (ISL && yol=="emir" && islPozVar()){ ISL.gor = "poz"; islCiz(); } }, 1200);
}
// basılı tut: 0,7 sn (fare / dokunuş / klavye: Boşluk-Enter basılı)
let ISL_TUT = null;
function islTutBasla(e){ if (!ISL || !ISL.adim || ISL.mesgul || ISL_TUT) return; if (e && e.type=="keydown" && e.repeat) return; if (e && e.cancelable) e.preventDefault();
  const b = $("#isltut"); if (!b) return; b.classList.add("dolu");
  ISL_TUT = setTimeout(()=>{ ISL_TUT = null; b.classList.remove("dolu"); try { navigator.vibrate && navigator.vibrate(18); } catch(_){} islOnayla(); }, 700); }
function islTutBirak(){ if (!ISL_TUT) return; clearTimeout(ISL_TUT); ISL_TUT = null; const b = $("#isltut"); if (b) b.classList.remove("dolu"); }
function islAlt(){   // sabit alt çubuk: başparmak bölgesinde ana eylem
  const I = ISL; if (!I) return "";
  if (I.adim) return `<div class="ialt" id="islalt"><button class="ibtn geri" onclick="ISL.adim=null;ISL.msj=null;islCiz()">Düzenle</button>
      <button id="isltut" class="ibtn tut ${I.adim.renk}" ${I.mesgul?"disabled":""} onpointerdown="islTutBasla(event)" onpointerup="islTutBirak()" onpointerleave="islTutBirak()" onpointercancel="islTutBirak()"
        onkeydown="if(event.key==' '||event.key=='Enter')islTutBasla(event)" onkeyup="islTutBirak()" oncontextmenu="return false"><span>${I.mesgul ? "Gönderiliyor…" : "Basılı tut: " + I.adim.dugme}</span></button></div>`;
  if (I.gor=="poz" && islPozVar()) return `<div class="ialt" id="islalt"><button class="ibtn S" onclick="islYonSec('S')">Short</button><button class="ibtn L" onclick="islYonSec('L')">Long</button></div>`;
  const u = islBoyutUsd();
  return `<div class="ialt" id="islalt"><button id="isldevam" class="ibtn ${I.yon}" onclick="islDevam()" ${I.mesgul?"disabled":""}>${I.mesgul ? "Kontrol ediliyor…" : `${I.yon=="L"?"Long":"Short"} ${u>0 ? para(u) : ""}`}</button></div>`;
}
function islCiz(){
  const el = $("#islic"); if (!el || !ISL) return;
  const I = ISL, ad = I.s.replace(/USDT$/,""), D = ISL_DURUM || {}, PR = I.poz, pz = PR && PR.pozisyon, o = PIY[I.s] || {}, f = o.f;
  const fg = v => v==null||v===""||isNaN(v)||!(+v>0) ? "—" : piyFiyat(+v);
  const seg = (alan, v, ad2, cls="") => `<button class="${cls} ${I[alan]==v?"on":""}" onclick="islAyar('${alan}','${v}')">${ad2}</button>`;
  const hz = (alan, L) => `<div class="ichip">${L.map(y=>`<button onclick="islYuzde('${alan}',${y})">${alan=="tp"?"+":"−"}${y}%</button>`).join("")}</div>`;
  const uzak = (v, ref) => v>0 && ref>0 ? ` <span class="k">${((v/ref-1)*100>=0?"+":"")}${((v/ref-1)*100).toFixed(1).replace(".",",")}%</span>` : "";
  const varPoz = islPozVar(), uzun = varPoz && pz.adet > 0;
  let h = `<div class="ihd"><div><div class="iad"><b>${ad}</b><span class="irz">${D.mod=="live"?"Canlı":"Demo"}</span></div>
      <div class="ifr"><span id="islfiy">${fg(f)}</span><span class="${sinif(o.p)}">${o.p>0?"▲":o.p<0?"▼":""} ${piyYz(o.p)}</span><span class="k">24 sa</span></div></div>
      <button class="shx" onclick="islKapat()" aria-label="Kapat">✕</button></div>`;
  // grafik
  h += `<div class="igk"><div class="igb"><div class="ichip ar">${Object.entries(ISL_AR).map(([a,[t]])=>`<button class="${I.aralik==a?"on":""}" onclick="islAralik('${a}')">${t}</button>`).join("")}</div>
      <div class="ichip gt"><button class="${I.gtur!="cizgi"?"on":""}" onclick="islGTur('mum')" aria-label="mum grafik" title="mum">▮▯</button><button class="${I.gtur=="cizgi"?"on":""}" onclick="islGTur('cizgi')" aria-label="çizgi grafik" title="çizgi">∿</button></div></div>
      <div id="islgraf" class="igr"></div>${(PR && PR.islemler && PR.islemler.length) ? `<div class="igl3"><span><b class="igal">▲</b> alışların</span><span><b class="igsat">▼</b> satışların</span><span>son 7 gün</span></div>` : ""}</div>`;
  // madde 839: kimin coini? (bot / sen) — işlemden önce net
  if (PR && !PR.hata && !I.adim){
    if (PR.elle) h += `<div class="isah sen">✋ Bu coin sende. Bot ekleme, kapatma, TP ya da stop yapmıyor; pozisyonu tamamen kapatınca bota döner.</div>`;
    else if (PR.bot_tutuyor) h += `<div class="isah bot">Bu coin şu an botun. İşlem yaparsan coin sana geçer ve bot bu coini bırakır.</div>`;
  }
  // ONAY ekranı
  if (I.adim){ const A = I.adim;
    h += `<div class="ionay"><div class="iob">${A.baslik}</div><div class="iozt">${A.satir.map(([a,b])=>`<div><span class="k">${a}</span><b>${b}</b></div>`).join("")}</div>
      ${A.not.map(n=>`<p class="ion">${ea(n)}</p>`).join("")}
      <label class="ibas" for="islpin">İşlem PIN'i</label><input id="islpin" type="password" inputmode="numeric" autocomplete="off" value="${ea(I.pin)}" oninput="islAyar('pin',this.value)" placeholder="sunucuda belirlediğin PIN">
      <p class="ion k">Göndermek için alttaki düğmeyi basılı tut.</p></div>`;
  } else {
    if (varPoz) h += `<div class="iseg gor"><button class="${I.gor=="poz"?"on":""}" onclick="islGor('poz')">Pozisyon</button><button class="${I.gor=="emir"?"on":""}" onclick="islGor('emir')">Yeni emir</button></div>`;
    if (!PR) h += `<div class="k" style="padding:12px 2px">Pozisyon okunuyor…</div>`;
    else if (PR.hata) h += `<div class="imsj hata">Pozisyon okunamadı: ${ea(PR.hata)}</div>`;
    if (varPoz && I.gor=="poz"){
      const deger = Math.abs(pz.adet) * (PR.isaret || pz.giris), kzp = pz.giris>0 ? pz.kz / (Math.abs(pz.adet) * pz.giris) * 100 : null;
      const tTP = PR.tpsl.find(x=>x.tur=="TP"), tSL = PR.tpsl.find(x=>x.tur=="SL");
      const likU = pz.likidasyon>0 && PR.isaret ? Math.abs(PR.isaret / pz.likidasyon - 1) * 100 : null;
      const kut = (e, d) => `<div class="iku"><span class="k">${e}</span><b>${d}</b></div>`;
      h += `<div class="ipoz"><div class="iph"><div><span class="iyon ${uzun?"L":"S"}">${uzun?"Long":"Short"}</span><span class="iadet">${Math.abs(pz.adet).toLocaleString("tr-TR")} adet</span></div>
          <div class="ikz ${sinif(pz.kz)}">${pz.kz>=0?"▲":"▼"} ${isaretli(pz.kz)}<small>${kzp==null?"":(kzp>=0?"+":"")+kzp.toFixed(2).replace(".",",")+"%"}</small></div></div>
        <div class="ikg">${kut("Giriş", fg(pz.giris))}${kut("Şimdi", fg(PR.isaret) + uzak(PR.isaret, pz.giris))}${kut("Değer", para(deger))}
          ${kut("TP", tTP ? fg(tTP.fiyat) + uzak(tTP.fiyat, PR.isaret) : "<span class='k'>yok</span>")}${kut("Stop", tSL ? fg(tSL.fiyat) + uzak(tSL.fiyat, PR.isaret) : "<span class='uyr'>yok</span>")}
          ${kut("Likidasyon", pz.likidasyon>0 ? fg(pz.likidasyon) : "—")}</div>
        ${likU!=null ? `<div class="ilik"><div class="ilikb"><span style="width:${Math.max(4, Math.min(100, likU / 50 * 100)).toFixed(0)}%" class="${likU<10?"kr":likU<30?"tu":"ye"}"></span></div><span class="k">likidasyona %${likU.toFixed(0)} uzak</span></div>` : ""}</div>
        <div class="ibas">Kapat</div><div class="iseg kucuk"><button onclick="islKapatOnay(0.25)">%25</button><button onclick="islKapatOnay(0.5)">%50</button><button class="tehlike" onclick="islKapatOnay(1)">Tümü</button></div>
        <div class="ibas">TP / stop</div>
        <div class="iki"><div><input inputmode="decimal" placeholder="TP fiyatı" aria-label="TP fiyatı" value="${islGos(I.tp)}" oninput="islAyar('tp',this.value)">${hz("tp",[3,5,10])}</div>
          <div><input inputmode="decimal" placeholder="Stop fiyatı" aria-label="Stop fiyatı" value="${islGos(I.sl)}" oninput="islAyar('sl',this.value)">${hz("sl",[3,5,10])}</div></div>
        ${(uzun ? PR.isaret > pz.giris : PR.isaret < pz.giris) ? `<button class="iacil kucuk2" onclick="islBasaBas()"><span>Stop'u girişe çek</span><i>kârdayken zararsız çıkış · ${fg(pz.giris)}</i></button>` : ""}
        <div id="isluyr">${islUyari()}</div>
        <div class="iseg kucuk"><button class="birincil" onclick="islTPSLOnay()">TP / stop kaydet</button>${PR.bekleyen.some(x=>x.panel)||PR.tpsl.some(x=>x.panel)?`<button onclick="islSilOnay()">Panel emirlerini sil</button>`:""}</div>
        ${PR.bekleyen.length ? `<div class="ibas">Bekleyen emirler</div>${PR.bekleyen.map(x=>`<div class="ibek"><span>${x.tip=="LIMIT"?"Limit":x.tip} ${x.yon=="BUY"?"alış":"satış"}, ${x.adet} @ ${fg(x.fiyat)}</span>${x.panel ? `<button class="ibx" onclick="islEmirIptalOnay('${x.orderId}','${x.yon}',${x.adet},${x.fiyat})">İptal</button>` : "<span class='k'>bot / uygulama</span>"}</div>`).join("")}` : ""}`;
    } else if (PR && !PR.hata){
      const riskMod = I.boyut=="risk", tpslAcik = I.tpsl || riskMod;
      h += `<div class="iseg yon">${seg("yon","L","Long","L")}${seg("yon","S","Short","S")}</div>
        <div class="isat"><span class="ibas">Emir tipi</span><div class="ichip kisa">${seg("tip","MARKET","Piyasa")}${seg("tip","LIMIT","Limit")}</div></div>
        ${I.tip=="LIMIT" ? `<input inputmode="decimal" placeholder="Limit fiyatı (şimdi ${fg(PR.isaret)})" aria-label="Limit fiyatı" value="${islGos(I.fiyat)}" oninput="islAyar('fiyat',this.value)">` : ""}
        <div class="isat"><span class="ibas">Boyut</span><div class="ichip kisa">${seg("boyut","usd","Tutar")}${seg("boyut","risk","Risk")}</div></div>
        ${riskMod ? `<div class="ipara"><input inputmode="decimal" aria-label="Risk tutarı" value="${islGos(I.risk)}" oninput="islAyar('risk',this.value)"><span>$ risk</span></div>
            <div class="ichip">${[2,5,10,20].map(v=>`<button class="${+I.risk==v?"on":""}" onclick="islAyar('risk',${v});islCiz()">${v} $</button>`).join("")}</div>
            <p class="ion k">Stop'a kadar en fazla bu kadar kaybedersin; pozisyon büyüklüğü buna göre hesaplanır.</p>`
          : `<div class="ipara"><input inputmode="decimal" aria-label="Tutar" value="${islGos(I.usd)}" oninput="islAyar('usd',this.value)"><span>$</span></div>
            <div class="ichip">${[25,50,100,200].filter(v=>v<=(D.max_usd||200)).map(v=>`<button class="${+I.usd==v?"on":""}" onclick="islAyar('usd',${v});islCiz()">${v} $</button>`).join("")}</div>`}
        ${varPoz ? (riskMod ? `<input inputmode="decimal" placeholder="Stop fiyatı (risk buna göre)" aria-label="Stop fiyatı" value="${islGos(I.sl)}" oninput="islAyar('sl',this.value)">${hz("sl",[3,5,10])}` : "")
            + `<p class="ion k">Ekleme sonrası mevcut TP / stop toplam adede göre güncellenir; fiyatlarını Pozisyon'dan değiştirirsin.</p>`
          : `<button class="iacil ${tpslAcik?"on":""}" onclick="ISL.tpsl=!ISL.tpsl;ISL.oniz=null;islCiz()" ${riskMod?"disabled":""}><span>TP / stop ekle</span><i>${tpslAcik?"açık":"kapalı"}</i></button>
            ${tpslAcik ? `<div class="iki"><div><input inputmode="decimal" placeholder="TP fiyatı" aria-label="TP fiyatı" value="${islGos(I.tp)}" oninput="islAyar('tp',this.value)">${hz("tp",[3,5,10])}</div>
              <div><input inputmode="decimal" placeholder="Stop fiyatı" aria-label="Stop fiyatı" value="${islGos(I.sl)}" oninput="islAyar('sl',this.value)">${hz("sl",[3,5,10])}</div></div>` : ""}`}
        <div id="isluyr">${islUyari()}</div><div id="isltah">${islTahminMetin()}</div>`;
    }
  }
  if (I.msj) h += `<div class="imsj ${I.msj.ok?"ok":"hata"}" role="status">${I.msj.durum=="FILLED"?'<span class="idur ok">Doldu</span>':I.msj.durum=="NEW"?'<span class="idur bek">Bekliyor</span>':""}${ea(I.msj.ok||I.msj.hata)}</div>`;
  h += islAlt();
  el.innerHTML = h; islGrafikCiz();
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
// MADDE 788: kâr al'ın giriş referansı — CARRY_GIRIS_DILIM=1 ise botun kendi dilim girişi (açık parçaların ortalaması), yoksa Binance girişi
function tpGiris(k, s, p){ const d = s && (k.tp_giris||{})[s]; return d && d > 0 ? d : p.giris; }
// MADDE 737: kâr al hedefine ilerleme. Long: giriş -> giriş x (1 + kademe); short: giriş -> giriş x (1 − kademe).
function hedefCubuk(k, p, f, s){
  const H = (k.hedef||{})[p.miktar>0 ? "L" : "S"] || [], tg = tpGiris(k, s, p);
  if (!H.length || !(tg>0) || !f) return "";
  const yon = p.miktar>0 ? 1 : -1, hareket = (f/tg - 1) * yon;
  let i = H.findIndex(h => hareket < h); const gecti = i < 0; if (gecti) i = H.length - 1;
  const h = H[i], hf = tg * (1 + yon*h), ilerl = Math.max(0, Math.min(1, hareket / h));
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
    ${kivilcim(s, p, f, renk, KUTU_W)}${k ? hedefCubuk(k, p, f, s) : ""}${fundSatir(s, p, f)}${k ? stopSatir(k, s, p) : ""}`;
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
      ${kivilcim(s, p, f, renk, Math.max(200, Math.round((($("#icerik")||{}).clientWidth || innerWidth - 28) - 52)), 90)}${hedefCubuk(k, p, f, s)}${fundSatir(s, p, f)}${stopSatir(k, s, p)}</div>` : ""}`;
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
  if (ISL && Date.now() - (islGrafikCiz.t||0) > 2000){ islGrafikCiz.t = Date.now(); islGrafikCiz(); if (Date.now() - ((MUMI[ISL.s+"|"+ISL.aralik]||{}).t||0) > 60e3) islMumYukle(); }   // madde 835
  piyasaBoya(false);   // madde 832
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
  const fg = gz ? D.funding : D.funding_gercek, fgS = fg==null ? "" : gz ? `<div class="dk alt ${ACIK.has("fug")?"acik":""}" onclick="dkAc('fug')"><span class="n"></span><span class="a">↳ demo hesabın ödediği <span class="ok">›</span></span><span class="v ${sinif(fg)}">${isaretli(fg)}</span><span class="ac">Demo borsa funding'i kendi oranıyla öder (gerçekle ilgisiz). Toplama girmez; yalnız bilgi.</span></div>` : `<div class="dk alt ${ACIK.has("fug")?"acik":""}" onclick="dkAc('fug')"><span class="n"></span><span class="a">↳ gerçek Binance oranlarıyla olsaydı <span class="ok">›</span></span><span class="v ${sinif(fg)}">${isaretli(fg)}</span><span class="ac">Bot coinleri gerçek Binance'in funding oranlarına bakarak seçer, ama pozisyonlar demo borsada olduğu için funding'i demo borsa kendi oranıyla öder (çoğu zaman gerçekle ilgisiz). Bu satır aynı pozisyonların gerçek oranlarla ne alacağını / ödeyeceğini gösterir (yaklaşık; 5 dk'lık pozisyon görüntüsüyle). Toplama girmez — canlı hesapta funding bu olurdu.</span></div>`;
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
  // madde 784: seçici kaldırıldı — her yerde canlı (gerçek Binance) funding; yalnız açıklama
  return `<span class="fgk"><button class="on fgi" onclick="const a=document.getElementById('fgacik'); a.hidden=!a.hidden" aria-label="funding açıklaması">canlı funding ⓘ</button></span>
    <div id="fgacik" class="fgacik" hidden>Paneldeki tüm funding, kitap ve kâr rakamları gerçek Binance funding oranlarıyla (canlı hesapta alınacak tutar). Demo borsa funding'i kendi oranıyla öder; demo hesaba yatan ile fark ${isaretli(g.fark)}.${g.duzeltilmeyen ? ` İlk ${g.duzeltilmeyen} günün gün gün dağılımı tahmini (o günlerin gerçek-oran kırılımı yok); toplam kesin.` : ""}</div>`;
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
function sheetKapat(){ SHEET = null; CIKIS_TUM = false; const el = $("#sheet"); el.hidden = true; el.innerHTML = ""; document.body.style.overflow = ""; }
addEventListener("keydown", e=>{ if (e.key === "Escape" && SHEET) sheetKapat(); });
function sheetIc(s, p, k){
  const {f, ky, g, usd} = pozDeger(s, p), renk = css((g||0) >= 0 ? "--art" : "--eks"), uzun = p.miktar > 0;
  const M = MUM[s], acilis = M && M.bas===gunBasi() && M.nok.length ? M.nok[0][1] : null, bg = acilis && f ? (f/acilis - 1) : null;
  const W = Math.max(240, Math.min(560, innerWidth) - 48);
  const F = FUND[s], fr = F && p.miktar ? -p.miktar * f * F.r : null;
  const D = k.stop_durum, sv = uzun && D && !D.kapali ? (D.coin||{})[s.replace(/USDT$/,"")] : null, ec = D ? D.esik_coin : 0.45;
  const pyz = v => v==null ? "—" : (v>=0?"+":"−") + "%" + Math.abs(v*100).toFixed(1).replace(".",",");
  const kutu = (e, d) => `<div class="shk"><div class="k">${e}</div><div class="shd">${d}</div></div>`;
  const tg = tpGiris(k, s, p), H = (k.hedef||{})[uzun ? "L" : "S"] || [], h0 = H.length && tg>0 ? tg * (1 + (uzun?1:-1) * H[0]) : null;
  const h1 = H.length > 1 && tg>0 ? tg * (1 + (uzun?1:-1) * H[1]) : null;   // madde 790: kademe VE kâr al ayrı
  const stop = sv==null ? "" : `<div class="shs"><div class="shr"><span class="k">Koşullu stop · coin 24 sa</span><span>${pyz(sv)} / <b>−%${Math.round(ec*100)}</b></span></div>
      <div class="shc"><span style="width:${Math.min(100, Math.max(0, -sv/ec*100)).toFixed(0)}%;background:${css(sv<=-ec?"--eks":sv<=-ec*0.5?"--uyari":"--soluk")}"></span></div>
      <div class="shr" style="margin-top:10px"><span class="k">Piyasa medyanı 24 sa</span><span class="${D.piyasa_sart?"uyr":""}">${pyz(D.medyan)} / −%${Math.round(D.esik_piyasa*100)} · ${D.piyasa_sart?"şart var":"şart yok"}</span></div></div>`;
  const neden = sv!=null && sv <= -ec*0.5 ? `<p class="shn"><b>Neden hâlâ açık?</b> Stop iki şart birden sağlanınca çalışır: coin 24 saatte −%${Math.round(ec*100)} ve piyasa medyanı −%${Math.round(D.esik_piyasa*100)}. ${D.piyasa_sart ? `Piyasa şartı var, ama ${s.replace(/USDT$/,"")}'nin düşüşü henüz −%${Math.round(ec*100)}'e ulaşmadı.` : "Şu an piyasa şartı yok (tek coin düşüşü; araştırmada bu durumda tutmak daha iyi çıktı, madde 621)."} İkisi birlikte gerçekleşirse bot sıradaki dilim turunda kapatır.</p>` : "";
  return `<div class="shu"><div><div style="display:flex;align-items:center;gap:8px"><span class="gb">${s.replace(/USDT$/,"")}</span><span class="dst ${uzun?"l":"s"}">${uzun?"LONG":"SHORT"}</span></div>
      <div class="shf">${fiyatYaz(f)}</div><div class="${sinif(g)}" style="font-weight:600;font-size:13.5px">${g>=0?"▲":"▼"} ${ky==null?"":(ky>=0?"+":"−")+Math.abs(ky).toFixed(1).replace(".",",")+"%"} · ${isaretli(g)}${bg!=null?` <span class="k">· bugün ${yz(bg)}</span>`:""}</div></div>
      <button class="shx" onclick="sheetKapat()" aria-label="Kapat">✕</button></div>
    <div class="shg">${kivilcim(s, p, f, renk, W, 110)}</div>
    <div class="shkg">${kutu("Giriş", fiyatYaz(p.giris))}${kutu("Büyüklük", para(usd))}${kutu("Funding", F ? `%${(F.r*100).toFixed(4).replace(".",",")} · <span class="${sinif(fr)}">${fr>=0?"alıyor":"ödüyor"}</span>` : "—")}${kutu(h1 ? "Kademe · kâr al" : "Kâr al hedefi", h0 ? `${fiyatYaz(h0)} <span class="k">${uzun?"+":"−"}%${Math.round(H[0]*100)}</span>${h1 ? `<br>${fiyatYaz(h1)} <span class="k">${uzun?"+":"−"}%${Math.round(H[1]*100)}</span>` : ""}` : "—")}</div>
    ${stop}${neden}${cikisIc(s, usd, k)}`;
}
// MADDE 787: çıkış takvimi (A tasarımı) — parça parça: ne zaman alındı → ne zaman satılacak, şu anki değer ve kâr/zarar
let CIKIS_TUM = false;
function cikisTum(){ CIKIS_TUM = !CIKIS_TUM; if (SHEET) { const k = VERI.kurulumlar[secili]; const el = $("#sheetic"); if (el && k.pozisyonlar[SHEET]) el.innerHTML = sheetIc(SHEET, k.pozisyonlar[SHEET], k); } }
function cikisIc(s, usd, k){
  // MADDE 790: kullanıcı "tasarımdan dolayı pek anlaşılır değil". Parçalar TUR başına tek satır (aynı turda yenilenen 2-3 parça ayrı satır
  // değil; madde 791: "N alım (M dilim payı)", satırda "1 emir, 3 dilime bölündü"), "satılacak" yerine "süresi dolar" (short'ta kapanış ALIŞTIR), yeniden seçilirse kalacağı en başta, "tamamen biter" → "hiç seçilmezse".
  const L = (k.cikis||{})[s], p = (k.pozisyonlar||{})[s]; if (!L || !L.length || !p) return "";
  const {f} = pozDeger(s, p), uzun = p.miktar > 0, ad = s.replace(/USDT$/,""), q = Math.abs(p.miktar||0);
  const GUNK = ["Paz","Pzt","Sal","Çar","Per","Cum","Cmt"], bugun = new Date(new Date().toDateString());
  const gunfark = t => Math.round((new Date(new Date(t*1000).toDateString()) - bugun)/864e5);
  const gunAd = t => { const g = gunfark(t), d = new Date(t*1000); return g==0 ? "Bugün" : g==1 ? "Yarın" : GUNK[d.getDay()] + " " + d.getDate(); };
  const turT = t => t - 480;   // takvim zamanı tur BİTİŞİ (~8 dk); kullanıcı turu başlangıç saatiyle tanıyor (01:47 / 09:47 / 17:47)
  const saat = t => new Date(turT(t)*1000).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"});
  const P = L.map(x=>{ const qq = q * x.pay, deg = (usd||0) * x.pay, kz = x.giris && f ? (uzun ? 1 : -1) * qq * (f - x.giris) : null; return {...x, qq, deg, kz}; });
  const T = {}; P.forEach(x=>{ const a = x.zaman || 0; (T[a] = T[a] || {zaman: x.zaman, P: []}).P.push(x); });
  const turlar = Object.values(T).sort((a,b)=>(a.zaman||0)-(b.zaman||0)).map(t=>{
    const deg = t.P.reduce((a,x)=>a+x.deg,0), pay = t.P.reduce((a,x)=>a+x.pay,0), qq = t.P.reduce((a,x)=>a+x.qq,0);
    const gq = t.P.filter(x=>x.giris), giris = gq.length ? gq.reduce((a,x)=>a+x.qq*x.giris,0) / gq.reduce((a,x)=>a+x.qq,0) : null;
    const kz = t.P.some(x=>x.kz!=null) ? t.P.reduce((a,x)=>a+(x.kz||0),0) : null, alis = t.P.map(x=>x.alis).filter(Boolean);
    return {zaman: t.zaman, n: t.P.length, deg, pay, giris, kz, alis: alis.length ? Math.min(...alis) : null};
  });
  const ilk = turlar[0], son = turlar[turlar.length-1], g24 = turlar.filter(t=>t.zaman && ilk.zaman && t.zaman - ilk.zaman < 86400);
  const kapanis = uzun ? "satılır" : "geri alınır (short kapanır)";
  const kut = (e, d, a) => `<div class="shk"><div class="k">${e}</div><div style="font-weight:700;font-size:14px">${d}</div><div class="k">${a}</div></div>`;
  const satir = (t, i) => `<div style="display:flex;justify-content:space-between;gap:10px;background:var(--kart);border-radius:12px;padding:10px 12px;${i?"":"outline:1.5px solid color-mix(in srgb,var(--vurgu) 45%,transparent)"}">
      <div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:14px;font-weight:700">${t.zaman ? `${gunAd(turT(t.zaman))} ${saat(t.zaman)} turu` : "Tur saati bilinmiyor"}</span>
        <span class="k">${t.n > 1 ? `1 emir, ${t.n} dilime bölündü` : "1 emir"}${t.alis ? ` · açılış ${gunAd(turT(t.alis)).toLowerCase()} ${saat(t.alis)}` : ""}${t.giris ? ` · giriş ${fiyatYaz(t.giris)}` : ""}</span></div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px;flex:none"><span style="font-size:14px;font-weight:600">${para(t.deg)} <span class="k">· %${Math.max(1, Math.round(t.pay*100))}</span></span>
        ${t.kz==null ? "" : `<span class="${sinif(t.kz)}" style="font-size:12px;font-weight:600">${isaretli(t.kz)}</span>`}</div></div>`;
  const sinir = CIKIS_TUM ? 1e9 : 4, gor = turlar.slice(0, sinir), kalan = turlar.slice(sinir);
  const kalanDeg = kalan.reduce((a,t)=>a+t.deg,0), kalanKz = kalan.reduce((a,t)=>a+(t.kz||0),0);
  return `<div class="shs" style="margin-top:12px;padding:14px">
    <div style="font-size:16px;font-weight:700">Alımların süresi ne zaman doluyor?</div>
    <p class="shn" style="margin-top:6px">${ad} pozisyonu <b>${turlar.length} alımdan</b>${P.length > turlar.length ? ` (${P.length} dilim payı)` : ""} oluşuyor. ${P.length > turlar.length ? `Her alım borsaya <b>tek emir</b> olarak gider; bot onu kendi defterinde o turda yenilenen ${uzun ? "dilimlere" : "3 dilime (sıradaki + short ara dengelemesiyle 5 ve 10 tur önceki)"} paylaştırır. ` : ""}${uzun ? "Long alımların süresi <b>5 günde</b>" : "Short alımların süresi <b>40 saatte</b>"} dolar. Süresi dolan alım için bot o turda karar verir:</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
      <div class="shk"><div style="font-weight:700;font-size:13px;color:var(--art)">${ad} yine seçilirse</div><div class="k" style="margin-top:3px">alım <b>kalır</b>, hiçbir işlem olmaz, olaylarda görünmez</div></div>
      <div class="shk"><div style="font-weight:700;font-size:13px;color:var(--uyari)">seçilmezse</div><div class="k" style="margin-top:3px">o alım ${kapanis}; olaylarda "${uzun?"long":"short"} azaltıldı" yazar</div></div></div>
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px">${kut("Sıradaki tur", ilk.zaman ? gunAd(turT(ilk.zaman)).toLowerCase()+" "+saat(ilk.zaman) : "—", `1 alım · ${para(ilk.deg)}`)}${kut("24 saatte", g24.length+" alım", para(g24.reduce((a,t)=>a+t.deg,0)))}${kut("Hiç seçilmezse biter", son.zaman ? gunAd(turT(son.zaman)) : "—", son.zaman ? saat(son.zaman) : "")}</div>
    <div style="height:1px;background:var(--cizgi);margin:14px 0 2px"></div>
    <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:600;color:var(--soluk)"><span>SÜRESİ DOLAN ALIM</span><span>DEĞER · K/Z</span></div>
    <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">${gor.map(satir).join("")}</div>
    ${kalan.length ? `<div class="k" style="margin-top:10px">+${kalan.length} tur daha · ${para(kalanDeg)} · <span class="${sinif(kalanKz)}">${isaretli(kalanKz)}</span></div>` : ""}
    ${turlar.length>4 ? `<button onclick="cikisTum()" style="width:100%;height:44px;margin-top:10px;border-radius:12px;border:0;background:var(--kart);color:var(--vurgu);font:inherit;font-size:14px;font-weight:600">${CIKIS_TUM ? "Daha az göster" : `${turlar.length} turun hepsini göster`}</button>` : ""}
    <p class="shn" style="background:var(--kart);border-radius:12px;padding:10px 12px">Fiyat kademe ya da kâr al seviyesine gelirse borsadaki emir turu beklemeden, o an dolar (yukarıdaki kutu).</p></div>`;
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
      ${k.dokum?`<div class="k" style="margin-top:6px">Başlangıçtan beri: funding ${k.dokum.funding_gercek!=null?`${isaretli(k.dokum.funding_gercek)} <span class="k">(canlı · demo hesaba yatan ${isaretli(k.dokum.funding)})</span>`:isaretli(k.dokum.funding)} · komisyon ${isaretli(k.dokum.komisyon)}</div>`
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
  const sat = L.map(x=>`<tr><td class="l"><b>${x.s}</b>${x.elle?`<span class="yon" title="elle yönetiyorsun — bot dokunmuyor">✋ elle</span>`:""}${x.yon?`<span class="yon">${MOBIL() ? x.yon : (x.yon=="L"?"long açık":"short açık")}</span>`:""}</td><td>${h(x.kapanan)}</td><td>${h(x.funding)}</td><td>${h(x.komisyon)}</td><td>${h(x.acik)}</td><td><b>${h(x.toplam)}</b></td></tr>`).join("");
  const T = C.reduce((a,x)=>({kp:a.kp+x.kapanan, f:a.f+x.funding, km:a.km+x.komisyon, a:a.a+x.acik, t:a.t+x.toplam}), {kp:0,f:0,km:0,a:0,t:0});
  return `<div class="kart"><h2>Coin bazında kâr / zarar <span class="k">· başlangıçtan beri, en kötüden en iyiye</span></h2>
    <div class="tablo yatay"><table class="coin"><tr class="k"><td class="l">coin</td><td>kapanan</td><td>funding</td><td>komisyon</td><td>açık</td><td>toplam</td></tr>${sat}
    <tr><td class="l"><b>Toplam (${C.length} coin)</b></td><td>${h(T.kp)}</td><td>${h(T.f)}</td><td>${h(T.km)}</td><td>${h(T.a)}</td><td><b>${h(T.t)}</b></td></tr></table></div>
    ${C.length>10?`<div class="isl"><span class="ac" onclick="olayAc('${id}')">${ac?"▾ en kötü / en iyi 5'e dön":`▸ tüm coinler (${C.length})`}</span></div>`:""}
    <div class="k" style="margin-top:6px">Kapanan, funding ve komisyon borsanın gelir kayıtlarından${k.mod=="demo"?(C.some(x=>x.funding_demo!=null)?" (funding: canlı / gerçek Binance oranlarıyla)":" (funding: demo hesabın aldığı)"):""}; açık = şu anki gerçekleşmemiş kâr / zarar.${MOBIL()?" Telefonda komisyon sütunu gizli (toplama dahil).":""}</div></div>`;
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
    const x = f.demo!=null ? `demo hesaba ${isaretli(f.demo)}` : (demo ? "demo hesaba yatmadı" : "");
    const y = demo && f.gercek!=null ? `gerçek oranlarla ${isaretli(f.gercek)}` : "";
    // madde 760: "toplam" olduğu ve demo hesaba yatıp yatmadığı açık yazılsın
    const sa = f.saat.slice().sort().map(h=>h+":00").join(", ");
    out.push({zaman: f.zaman, tur: "funding", fon: f, metin: `Saatlik funding · ${f.n} ödemenin toplamı ${demo && f.gercek!=null ? isaretli(f.gercek) : (f.demo!=null ? isaretli(f.demo) : "")} | ${f.coin.map(c=>c.s).join(", ")} · saat ${sa} · ` + (demo ? (f.demo!=null ? `demo hesaba yatan ${isaretli(f.demo)} · gerçek oranlarla ${isaretli(f.gercek)}` : "gerçek Binance oranlarıyla hesaplandı, demo hesaba yatmadı") : "")});
  }
  for (const f of ana){
    const a = f.demo!=null ? `demo hesaba ${isaretli(f.demo)} (${f.demo_n} poz)` : (demo ? "demo hesaba yatmadı" : "");
    const b = demo && f.gercek!=null ? `gerçek oranlarla ${isaretli(f.gercek)} (${f.gercek_n} poz)` : "";
    out.push({zaman: f.zaman, tur: "funding", fon: f, metin: `Funding · ${Math.max(f.gercek_n||0, f.demo_n||0)} pozisyon ${demo && f.gercek!=null ? isaretli(f.gercek) : (f.demo!=null ? isaretli(f.demo) : "")} | ` + [a, b].filter(Boolean).join(" · ")});
  }
  return out.sort((a,b)=>(b.zaman||"").localeCompare(a.zaman||""));
}
function islemTablo(o){
  // MADDE 751: her işlem tek satır grubu — ne oldu (açıldı / eklendi / azaltıldı / kapandı), ne kadar, ve ÖNCE → SONRA
  if (!o.islem || !o.islem.length) return "";
  const id = "isl" + o.zaman + o.tur, ac = ACIK.has(id);
  // madde 769: kapanışta toz kalırsa (ör. ARB short kapatıldı, +0,06 $ ters yönde artık) "kapandı" say, yönü ÖNCEKİ pozisyondan al
  const tip = x => { let ps = x.poz_sonra; const po = x.poz_once, al = x.yon==="BUY";
    if (ps && po && x.usd_sonra!=null && x.usd_sonra < 1 && (x.usd_once||0) > 5 && ((po>0)!==al)) ps = 0;
    const yon = po ? (po>0 ? "long" : "short") : (ps ? (ps>0 ? "long" : "short") : (al ? "long" : "short"));
    let ne;
    // madde 783: yön dönerse (ör. AKE long 4.729 → short −1.695: bir dilim long tutarken yeni dilimler short seçti, net ters
    // döndü) eskiden "long eklendi" yazıyordu. Artık "long kapandı → short açıldı"; renk yeni yönden.
    if (po && ps && (po>0)!==(ps>0)) return {yon: ps>0 ? "long" : "short", ne: "", ekle: false,
                                             etiket: `${po>0 ? "long" : "short"} kapandı → ${ps>0 ? "long" : "short"} açıldı`};
    if (po===0) ne = "açıldı"; else if (ps===0) ne = "kapandı";
    else if (ps!=null) ne = ((ps>0)===al) ? "eklendi" : "azaltıldı"; else ne = al ? "alındı" : "satıldı";
    return {yon, ne, ekle: ne=="açıldı"||ne=="eklendi"}; };
  const sat = o.islem.map(x=>{ const t = tip(x), L = t.yon=="long";
    const once = x.usd_once!=null ? (x.usd_once===0 ? "0 $" : para(x.usd_once)) : null, sonra = x.poz_sonra===0 ? "0 $" : (x.usd_sonra!=null ? para(x.usd_sonra) : "…");
    const ort = (x.ort_once && x.ort_sonra && Math.abs(x.ort_once/x.ort_sonra-1) > 1e-6) ? ` · ort. ${fiyatYaz(x.ort_once)} → ${fiyatYaz(x.ort_sonra)}`
              : (x.ort_sonra && t.ne=="açıldı" ? "" : (x.ort_sonra ? ` · ort. ${fiyatYaz(x.ort_sonra)}` : ""));
    return `<div style="padding:9px 0;border-top:1px solid var(--cizgi)">
      <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
        <span><b>${x.sembol}</b> <span style="font-size:12px;font-weight:650;color:${L?'var(--vurgu)':'#f59e0b'}">${t.etiket || (t.yon + " " + t.ne)}</span></span>
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
// MADDE 784: kullanıcı "her yerde canlıyı görmek" istiyor — demo (ham) seçeneği kaldırıldı, FG hep açık.
const FG = true;
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
  piyasaBagla(sayfa=="piyasa");   // madde 832: akış yalnız Piyasa sekmesi açıkken
  const piyOdak = document.activeElement && document.activeElement.id=="piyara";
  $("#icerik").innerHTML = sayfa=="poz" ? pozSayfa(k) : sayfa=="piyasa" ? piyasaSayfa(k) : sayfa=="gecmis" ? gecmisSayfa(k) : sayfa=="olay" ? olaySayfa(k)
    : (genis ? `<div class="genis"><div>${ozetSayfa(k, svc, sv)}</div><div>${pozSayfa(k)}</div></div>` : ozetSayfa(k, svc, sv));
  if (piyOdak){ const i = $("#piyara"); if (i){ i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }   // 60 sn yenilemede yazı kesilmesin
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


ISLEM_URL = os.getenv("CARRY_ISLEM_URL", "http://127.0.0.1:8051")
"""MADDE 834: işlem kapısı (carry-islem servisi). Yalnız yerel adres kabul edilir."""


def _islem_ilet(metod: str, yol: str, govde: bytes | None = None):
    """İsteği yerel işlem kapısına iletir; yanıtı aynen döner. Kapı çalışmıyorsa anlaşılır hata."""
    import urllib.error
    import urllib.request
    from flask import Response, jsonify
    if not re.match(r"^http://(127\.0\.0\.1|localhost|\[::1\]):\d+$", ISLEM_URL):
        return jsonify({"ok": False, "hata": "işlem kapısı yalnız yerel adreste olabilir"}), 500
    req = urllib.request.Request(f"{ISLEM_URL}/{yol}", data=govde, method=metod,
                                 headers={"Content-Type": "application/json"} if govde is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return Response(r.read(), status=r.status, mimetype="application/json")
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code, mimetype="application/json")
    except (urllib.error.URLError, OSError, TimeoutError):
        return jsonify({"ok": False, "hata": "işlem servisi çalışmıyor (sunucuda carry-islem)"}), 503


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

    # MADDE 834: panelden işlem — panel ANAHTARSIZ kalır; istekler yalnız 127.0.0.1'deki carry-islem servisine iletilir (carry_islem.py).
    # POST'larda özel başlık (X-Carry-Islem) + aynı köken şartı: başka bir siteden tarayıcı üzerinden emir tetiklenemez (CSRF).
    @app.get("/api/islem/durum")
    def islem_durum():
        return _islem_ilet("GET", "durum")

    @app.get("/api/islem/elle")
    def islem_elle():
        return _islem_ilet("GET", "elle")

    @app.get("/api/islem/pozisyon/<sem>")
    def islem_poz(sem):
        if not re.match(r"^[A-Z0-9]{2,20}USDT$", sem or ""):
            return jsonify({"ok": False, "hata": "geçersiz sembol"}), 400
        return _islem_ilet("GET", f"pozisyon/{sem}")

    @app.post("/api/islem/<yol>")
    def islem_post(yol):
        if yol not in ("onizle", "emir", "tpsl", "kapat", "iptal"):
            return jsonify({"ok": False, "hata": "bilinmeyen işlem"}), 404
        if request.headers.get("X-Carry-Islem") != "1" or not request.is_json:
            return jsonify({"ok": False, "hata": "geçersiz istek"}), 403
        org = request.headers.get("Origin")
        if org and org.split("://", 1)[-1].rstrip("/") != request.host:
            return jsonify({"ok": False, "hata": "başka kökenden istek reddedildi"}), 403
        return _islem_ilet("POST", yol, request.get_data(cache=False)[:4096])

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
