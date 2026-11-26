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


def giris_duzelt(klasor: str, an: dict | None) -> dict:
    """MADDE 851: taşımada (elle → ayrı al-sat hesabı) kullanıcının payı bot hesabında kapatıldı; Binance azaltmada ortalama girişi
    DEĞİŞTİRMEZ, botun kalan payı karışık ortalamayla görünürdü. defter/giris_duzeltme.json {"coin": {sembol: {"giris", "adet"}}}:
    borsadaki adet kayıttakine EŞİTKEN pozisyon botun kendi girişiyle gösterilir; fark "Kapanan"dan "Açık"a taşınır (toplam aynı).
    Adet değişince (bot ekledi / azalttı) düzeltme kendiliğinden biter. `an` yerinde değişir. Döner: {sembol: taşınan $}."""
    try:
        with open(os.path.join(klasor, "defter", "giris_duzeltme.json"), encoding="utf-8") as f:
            coin = json.load(f)["coin"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    if not an or not isinstance(an.get("pozisyonlar"), dict):
        return {}
    out = {}
    for s, d in coin.items():
        p = an["pozisyonlar"].get(s)
        try:
            g, adet = float(d["giris"]), float(d["adet"])
        except (KeyError, TypeError, ValueError):
            continue
        if not p or g <= 0 or abs(float(p.get("miktar") or 0) - adet) > 1e-9 * max(1.0, abs(adet)) or not p.get("isaret"):
            continue
        yeni = adet * (float(p["isaret"]) - g)
        adj = yeni - float(p.get("gerceklesmemis") or 0)
        p["giris_borsa"] = p.get("giris")
        p["giris"] = g
        p["gerceklesmemis"] = round(yeni, 4)
        p["kar_yuzde"] = round((float(p["isaret"]) / g - 1) * (1 if adet > 0 else -1) * 100, 2)
        out[s] = round(adj, 4)
    if an.get("gerceklesmemis_top") is not None and out:
        an["gerceklesmemis_top"] = round(float(an["gerceklesmemis_top"]) + sum(out.values()), 2)
    return out


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


def elle_ayir(o: dict, an: dict | None) -> None:
    """MADDE 849: anlık görüntü özkaynağı artık BOTUN (elle K/Z düşülmüş). Döküm ve coin tablosundaki borsa gelirleri ise hesabın
    tamamı — elle aralıklardaki payı (carry_elle_kz özeti) buradan düşülür ki parçalar botun kârına eşit kalsın. Devralınan
    pozisyonun devir anına kadarki kâr/zararı (`devir`) botun gerçekleşenine yazılır. Elle özeti `o["elle"]`."""
    E = (an or {}).get("elle")
    if not E:
        return
    T = E.get("toplam") or {}
    d = o.get("dokum")
    if d:   # madde 851: yalnız KULLANICININ bileşenleri düşülür (botun payı botta kalır)
        d["gerceklesen"] = round(d["gerceklesen"] - T.get("Rk", 0), 2)
        d["funding"] = round(d["funding"] - T.get("Fk", 0), 2)
        d["komisyon"] = round(d["komisyon"] - T.get("C", 0), 2)
    for k_ in o.get("coin_ozet") or []:
        e = (E.get("sembol") or {}).get(k_["s"] + "USDT")
        if not e:
            continue
        k_["kapanan"] = round(k_["kapanan"] - e["Rk"], 4)
        k_["funding"] = round(k_["funding"] - e["Fk"], 4)
        if "funding_demo" in k_:
            k_["funding_demo"] = round(k_["funding_demo"] - e["Fk"], 4)
        k_["komisyon"] = round(k_["komisyon"] - e["C"], 4)
        k_["acik"] = round(k_["acik"] - e["Uk"], 4)
        k_["elle_kz"] = round(e["kz"], 4)
        k_["toplam"] = round(k_["kapanan"] + k_["funding"] + k_["komisyon"] + k_["acik"], 4)
    o["elle"] = {"kz": round(T.get("kz", 0), 2), "acik_sembol": E.get("acik_sembol") or [],
                 "hesap_ozkaynak": an.get("ozkaynak_hesap"), "sembol": {s: round(v["kz"], 2) for s, v in (E.get("sembol") or {}).items()}}


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
        for _s, _v in giris_duzelt(kl, an).items():   # madde 851: taşıma sonrası botun kendi girişi (aynı "Kapanan → Açık" taşıması)
            _devir[_s] = round(_devir.get(_s, 0.0) + _v, 4)
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
        elle_ayir(o, an)   # madde 849
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


SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><script>/* iOS: kutuya odaklanınca otomatik yakınlaştırmayı kapat (iOS elle iki parmak yakınlaştırmaya yine izin verir) */if(/iP(hone|ad|od)/.test(navigator.userAgent)||navigator.platform=="MacIntel"&&navigator.maxTouchPoints>1)document.querySelector("meta[name=viewport]").content="width=device-width,initial-scale=1,maximum-scale=1"</script>
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
:root{--bg:#f3f4f6;--kart:#fff;--kart2:#f3f4f7;--yazi:#111318;--soluk:#5d6472;--cizgi:#e5e7eb;--art:#0a7d45;--eks:#c42b20;--vurgu:#2563eb;--uyari:#c2410c;--mor:#7c3aed;--ust:rgba(243,244,246,.86)}
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
header.kucuk>div:first-child{display:flex;align-items:center;gap:12px;min-width:0}header.kucuk #ustkitap{padding:3px 10px;border-radius:999px;background:var(--kart2);font-size:14px;white-space:nowrap}
.sag{display:flex;align-items:center;gap:8px}
.hmb{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);border-radius:10px;width:36px;height:36px;font-size:18px;cursor:pointer;display:inline-grid;place-items:center;padding:0;margin-right:8px;vertical-align:middle}
#menu{position:fixed;inset:0;z-index:30}#menu .mb{position:absolute;inset:0;background:rgba(0,0,0,.45)}
#menu .mp{position:absolute;top:0;left:0;bottom:0;width:min(300px,82vw);background:var(--kart);padding:18px 14px;box-shadow:0 0 30px rgba(0,0,0,.3);display:flex;flex-direction:column;gap:10px}
#menu .mh{font-size:12px;color:var(--soluk);margin:4px 4px 2px}
#menu .ms{display:flex;align-items:center;gap:12px;width:100%;min-height:64px;padding:12px 14px;border-radius:14px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--yazi);font:inherit;text-align:left;cursor:pointer}
#menu .ms.on{border-color:var(--vurgu);background:color-mix(in srgb,var(--vurgu) 14%,var(--kart2))}#menu .ms b{display:block;font-size:16px}#menu .ms span.k{font-size:12.5px}#menu .ms i{font-style:normal;font-size:24px}
#menu .mp{overflow-y:auto;padding-top:max(18px,env(safe-area-inset-top));padding-bottom:max(22px,calc(env(safe-area-inset-bottom) + 12px))}#menu .mtp{display:flex;justify-content:space-between;align-items:center;margin:0 2px 4px}#menu .mtp b{font-size:20px}
#menu .mh{margin-top:8px;text-transform:uppercase;letter-spacing:.5px;font-weight:600;font-size:11px}#menu .mz{display:block;margin-top:4px;font-size:13px;color:var(--soluk);font-variant-numeric:tabular-nums}#menu .mz b{display:inline;font-size:14px;color:var(--yazi)}
#menu .mtm{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;background:var(--kart2);border-radius:12px;padding:3px}#menu .mtm button{height:44px;border:0;border-radius:9px;background:none;color:var(--soluk);font:inherit;font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px}#menu .mtm button.on{background:var(--kart);color:var(--yazi);box-shadow:0 1px 3px rgba(0,0,0,.2)}#menu .mtm i{font-style:normal}
#menu .mal{margin-top:auto;padding:12px 4px 4px;border-top:1px solid var(--cizgi);display:flex;flex-direction:column;gap:4px;font-size:12px}
.tema{border:1px solid var(--cizgi);background:var(--kart);color:var(--soluk);border-radius:999px;width:30px;height:30px;font-size:14px;cursor:pointer;display:grid;place-items:center;padding:0}
.canli{font-size:12px;color:var(--soluk);display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.canli i{width:8px;height:8px;border-radius:50%;background:var(--soluk);display:inline-block}
.canli.on{color:var(--art)}.canli.gec{color:var(--uyari)}.canli.gec i{background:var(--uyari)}.canli.yok{color:var(--eks)}.canli.yok i{background:var(--eks)}.canli.on i{background:var(--art);animation:nabiz 1.6s infinite}
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
.fgk .fgi{padding:3px 6px;min-height:32px}.fgacik{flex-basis:100%;font-size:12px;color:var(--soluk);line-height:1.45;margin:-4px 0 10px}
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
.shp{position:absolute;left:0;right:0;bottom:0;max-height:88vh;max-height:calc(100% - max(16px, env(safe-area-inset-top) + 8px));overflow:auto;background:var(--kart);border-radius:24px 24px 0 0;padding:10px 20px calc(20px + env(safe-area-inset-bottom));box-shadow:0 -12px 40px rgba(0,0,0,.4);max-width:600px;margin:0 auto;animation:shy .22s ease-out}
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
.ogun{font-size:11.5px;font-weight:650;color:var(--soluk);letter-spacing:.5px;margin:20px 0 6px;display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}.ogt{letter-spacing:0;font-weight:500;font-size:12px}.otut{font-weight:650;font-variant-numeric:tabular-nums}.otut.art{color:var(--art)}.otut.eks{color:var(--eks)}
.ofs{margin-top:6px}.ofs>div{display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:8px;align-items:baseline;padding:6px 0;border-top:1px solid var(--cizgi);font-size:12.5px}.ofs>div>span:nth-child(2){color:var(--soluk);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.okart{background:var(--kart2);border-radius:16px;overflow:hidden}.orow{display:flex;gap:12px;padding:11px 14px;border-top:1px solid var(--cizgi)}.okart .orow:first-child{border-top:0}
.onk{--r:var(--soluk);width:26px;height:26px;border-radius:50%;flex:none;display:grid;place-items:center;font-size:12.5px;font-weight:700;color:var(--r);background:color-mix(in srgb,var(--r) 16%,transparent)}.om{flex:1;min-width:0}
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
  .coin .yon{font-size:11px;color:var(--soluk);font-weight:700;margin-left:4px}}
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
.takvim .g .v{font-size:12.5px;font-weight:700;margin-top:4px;white-space:nowrap}.takvim .g .vk{display:none}@media (max-width:440px){.takvim .g .vt{display:none}.takvim .g .vk{display:inline}}
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
/* madde 872: bot özet / ayrıntı */
.nrd{display:flex;flex-direction:column;gap:2px}.nrr{display:grid;grid-template-columns:72px minmax(0,1fr) auto;gap:10px;align-items:center;min-height:30px}
.nrl{font-size:13px;color:var(--soluk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.nrr b{font-size:13.5px;font-variant-numeric:tabular-nums;text-align:right;min-width:86px}
.nrb{position:relative;height:10px;border-radius:5px;background:var(--kart2)}.nrb::after{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--soluk);opacity:.5}
.nrb i{position:absolute;top:0;bottom:0;border-radius:5px}.nrb i.p{left:50%;background:var(--art)}.nrb i.n{right:50%;background:var(--eks)}
.nrt{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--cizgi);margin-top:6px;padding-top:8px;font-size:13.5px;font-weight:600}.nrt b{font-size:15px;font-variant-numeric:tabular-nums}
.nrr b.art,.nrt b.art{color:var(--art)}.nrr b.eks,.nrt b.eks{color:var(--eks)}
.nsor{flex:none;height:36px;padding:0 10px;border-radius:999px;border:1px solid var(--cizgi);background:var(--kart);color:var(--vurgu);font:inherit;font-size:12px;font-weight:600;cursor:pointer}
/* madde 870: coin logoları */
.pkav{position:relative;overflow:hidden;flex:none}.pkav img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:50%;opacity:0;transition:opacity .2s}
.pkav.ik{color:transparent!important;background:#fff!important}.pkav.ik img{opacity:1}
.pkav.kucuk{width:22px;height:22px;font-size:9px}.pkav.dik{width:32px;height:32px;font-size:11px}.ctad{display:inline-flex;align-items:center;gap:6px;vertical-align:middle}.iad{display:flex;align-items:center;gap:8px}.pkav.ihik{width:30px;height:30px;font-size:11px}
.apr{grid-template-columns:36px minmax(0,1fr) auto!important}.apik{position:relative;width:36px;height:36px}.apik .pkav{width:36px;height:36px;font-size:12px}
.apik .iyon2{position:absolute;right:-4px;bottom:-3px;width:17px!important;height:17px!important;border-radius:6px!important;font-size:9.5px!important;border:2px solid var(--kart2)}
/* madde 869: işlem penceresi */
.idonk{margin-top:16px;border-top:1px solid var(--cizgi);padding-top:4px}.idonb{width:100%;display:flex;justify-content:space-between;align-items:center;gap:8px;min-height:44px;border:0;background:none;color:var(--yazi);font:inherit;font-size:14px;font-weight:600;cursor:pointer;padding:0 2px}.idonb .k{font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.isl .imsj{margin-top:12px}
/* madde 868: diğer sayfalar */
.asdk{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:10px 0 4px}.asdk>div{padding:8px 10px;border-radius:10px;background:var(--kart2);display:flex;flex-direction:column;gap:1px}.asdk span{font-size:11.5px;color:var(--soluk)}.asdk b{font-size:14px;font-variant-numeric:tabular-nums}.asdk .art{color:var(--art)}.asdk .eks{color:var(--eks)}
.ofil{flex-wrap:nowrap!important;overflow-x:auto;scrollbar-width:none;-webkit-mask-image:var(--kay-mask,none);mask-image:var(--kay-mask,none);margin-left:-18px!important;margin-right:-18px!important;padding:0 18px}.ofil::-webkit-scrollbar{display:none}.ofil button{flex:none;height:36px!important;white-space:nowrap}
.ob>span:first-child{overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.oa{overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.orow{cursor:pointer}
.orow.oacik .oa,.orow.oacik .ob>span:first-child{-webkit-line-clamp:unset;display:block}
.dfil{flex-wrap:nowrap}.dfil .gdon{min-width:0}.dsir{flex:none;white-space:nowrap}
.acl{padding:14px}.acr{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"n t" "a t";gap:2px 10px;align-items:center;padding:9px 12px;border-radius:12px;background:var(--kart2);margin-top:5px}
.acn{grid-area:n;display:flex;align-items:center;gap:6px;font-size:14.5px}.aca{grid-area:a;font-size:11.5px;color:var(--soluk);font-variant-numeric:tabular-nums}.aca .nw{white-space:nowrap}.aca .art{color:var(--art)}.aca .eks{color:var(--eks)}
.act{grid-area:t;font-size:14.5px;font-variant-numeric:tabular-nums;white-space:nowrap}.act.art{color:var(--art)}.act.eks{color:var(--eks)}
.acay{text-align:center;color:var(--soluk);font-size:12px;padding:4px 0 0;letter-spacing:3px}
.icg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.ick{background:var(--kart2);border-radius:12px;padding:10px 12px;display:flex;flex-direction:column;gap:2px;box-shadow:inset 3px 0 0 transparent}
.ick span{font-size:12px;color:var(--soluk)}.ick b{font-size:19px;font-variant-numeric:tabular-nums}.ick i{font-style:normal;font-size:11.5px;color:var(--soluk)}
.ick.iyi{box-shadow:inset 3px 0 0 var(--art)}.ick.iyi b{color:var(--art)}.ick.kotu{box-shadow:inset 3px 0 0 var(--eks)}.ick.kotu b{color:var(--eks)}.ick.orta{box-shadow:inset 3px 0 0 var(--uyari)}
.icy{margin-top:12px}.icyb{display:flex;height:10px;border-radius:6px;overflow:hidden;gap:2px}.icyb i,.icyl i{background:var(--soluk)}.icy .ia{background:var(--art)}.icy .ib{background:var(--vurgu)}.icy .ic{background:var(--eks)}
.icyl{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:6px;font-size:12px}.icyl>span{white-space:nowrap;display:inline-flex;align-items:center;gap:5px}.icyl>span>i{width:8px;height:8px;border-radius:2px;display:inline-block}
.icd{margin-top:8px}.icd>div{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:1px solid var(--cizgi);font-size:13px}.icd>div>span{color:var(--soluk);flex:0 1 45%}.icd>div b{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}.icd p{margin:8px 0 0;line-height:1.45}
.cxo{margin-top:12px;background:var(--kart);border-radius:12px;padding:2px 12px}.cxo>div{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"a b" "a c";align-items:center;column-gap:10px;padding:8px 0;border-top:1px solid var(--cizgi)}.cxo>div:first-child{border-top:0}
.cxo span{grid-area:a;font-size:13px;color:var(--soluk)}.cxo b{grid-area:b;text-align:right;font-size:14px}.cxo i{grid-area:c;text-align:right;font-style:normal;font-size:11.5px;color:var(--soluk)}.shdk{margin-top:10px}.shdk .idonb{flex-wrap:wrap;row-gap:2px;padding:8px 2px}.shdk .idonb>span:first-child{white-space:nowrap}.shdk .idonb .k{white-space:normal;overflow:visible;text-align:left;flex:1 1 220px}.shdk .idonb .k b{font-weight:650}
.asdg{grid-column:1/-1;margin-top:12px;padding-top:12px;border-top:1px solid var(--cizgi)}.asdg .opzb{margin-top:0}.opz{display:block;color:inherit;text-decoration:none;-webkit-tap-highlight-color:transparent}.opzh{display:flex;justify-content:space-between;align-items:center;gap:8px}.opzh b{font-size:15px}.opzh .k b{font-size:13.5px}
.opzb{display:flex;height:12px;border-radius:7px;overflow:hidden;gap:2px;margin-top:12px;background:var(--kart2)}.opzb i,.opzl i{background:var(--vurgu)}.opz i.s{background:#f59e0b}
.opzl{display:flex;justify-content:space-between;gap:8px;margin-top:7px;font-size:12.5px;color:var(--soluk)}.opzl b{color:var(--yazi);font-variant-numeric:tabular-nums}.opzl>span{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}.opzl i{width:8px;height:8px;border-radius:2px;display:inline-block}
.apuy .apub{margin-left:auto;flex:none;height:36px;padding:0 12px;border-radius:10px;border:0;background:var(--uyari);color:var(--kart);font:inherit;font-size:13px;font-weight:700;cursor:pointer}
.tsor{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;margin-top:6px}.tsor button,.tsor input{height:40px;min-width:0;padding:0 2px;border-radius:10px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--yazi);font:inherit;font-size:14px;font-weight:600}.tsor button.on{border-color:var(--vurgu);background:color-mix(in srgb,var(--vurgu) 16%,var(--kart2));color:var(--vurgu)}.isl .tsor input{width:100%;height:40px;margin:0;padding:0 2px;text-align:center}
.tsoz{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-top:12px;padding:10px 12px;border-radius:12px;background:var(--kart2);font-size:13px}.tsoz b{font-size:16px;font-variant-numeric:tabular-nums}
.tsl{display:flex;flex-direction:column;gap:6px;margin-top:10px}.tsr{display:grid;grid-template-columns:22px auto minmax(0,1fr) auto;gap:10px;align-items:center;width:100%;padding:10px 12px;border-radius:12px;border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);font:inherit;text-align:left;cursor:pointer}
.tsr.on{border-color:color-mix(in srgb,var(--vurgu) 55%,transparent);background:color-mix(in srgb,var(--vurgu) 7%,var(--kart))}.tsr:disabled{cursor:default}.tsc{width:22px;height:22px;border-radius:7px;border:1.5px solid var(--cizgi);display:grid;place-items:center;font-size:13px;font-weight:800;color:#fff}.tsr.on .tsc{background:var(--vurgu);border-color:var(--vurgu)}
.tsm{display:flex;flex-direction:column;gap:2px;min-width:0}.tsm>b{font-size:14.5px;display:flex;align-items:center;gap:6px}.tsm .k{font-size:12px}.tsk{font-weight:650;font-size:13.5px;font-variant-numeric:tabular-nums;white-space:nowrap}.tsk.art{color:var(--art)}.tsk.eks{color:var(--eks)}.tsok{font-size:12px;color:var(--art);font-weight:650}.tshat{font-size:12px;color:var(--eks)}
#tspin{width:100%;height:46px;margin-top:6px;padding:0 12px;border-radius:12px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--yazi);font:inherit;font-size:16px}
.kaydevam{--kay-mask:linear-gradient(90deg,#000 calc(100% - 36px),transparent)}
[role=button][tabindex]:focus-visible{outline:2px solid var(--vurgu);outline-offset:2px;border-radius:8px}
.kpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:10px 0 4px}.kpi>div{background:var(--kart2);border-radius:10px;padding:7px 8px;display:flex;flex-direction:column;gap:1px;min-width:0}.kpi span{font-size:11px;color:var(--soluk)}.kpi b{font-size:13.5px;font-variant-numeric:tabular-nums;white-space:nowrap}.kpi b.art{color:var(--art)}.kpi b.eks{color:var(--eks)}.kpi i{font-style:normal;font-size:11px;color:var(--soluk);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media (max-width:380px){.kpi{grid-template-columns:repeat(2,minmax(0,1fr))}}
.asfn{cursor:pointer;grid-column:1/-1;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;align-items:baseline;margin-top:10px;padding:10px 12px;border-radius:12px;background:var(--kart2);font-size:13px}.asfn>b{font-size:14px;font-variant-numeric:tabular-nums;white-space:nowrap}.asfn b.art{color:var(--art)}.asfn b.eks{color:var(--eks)}
.isl .igl.alm{stroke:var(--mor)}.isl .ige.alm rect{fill:var(--mor)}.isl .igad.alm rect{stroke:var(--mor)}.isl .igad.alm text{fill:var(--mor)}
.apfn{display:block;font-size:11.5px;color:var(--soluk);margin-top:1px}.apfn b{font-weight:600;font-variant-numeric:tabular-nums}.apfn b.art{color:var(--art)}.apfn b.eks{color:var(--eks)}
.igel{margin-top:12px;padding-top:10px;border-top:1px solid var(--cizgi);font-size:13px}.igel>div{display:flex;justify-content:space-between;gap:8px;padding:3px 0}.igel b{font-variant-numeric:tabular-nums}.igel b.art{color:var(--art)}.igel b.eks{color:var(--eks)}.igelb{font-weight:650}.igelt{border-top:1px dashed var(--cizgi);margin-top:4px;padding-top:6px!important;font-weight:700;font-size:14px}
.ruk{margin-top:6px;border-top:1px solid var(--cizgi)}.ruh{display:flex;align-items:center;gap:8px}.ruh .gayr{flex:1;padding:12px 0}.rus{flex:none;width:46px;height:28px;border-radius:999px;border:1px solid var(--cizgi);background:var(--kart2);position:relative;cursor:pointer;padding:0}.rus i{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:var(--soluk);transition:left .15s}.rus.on{background:var(--art);border-color:var(--art)}.rus.on i{left:21px;background:#fff}
.rua{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid var(--cizgi)}.rua>span:first-child{display:flex;flex-direction:column;font-size:13.5px;min-width:0}.rua small{color:var(--soluk);font-size:11.5px}.ruv{display:flex;align-items:center;gap:3px;font-variant-numeric:tabular-nums;color:var(--soluk)}.ruv input{width:78px;height:38px;border-radius:10px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--yazi);font:inherit;font-size:15px;text-align:right;padding:0 10px}
.assr{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin:8px 0 2px}.assr select{height:36px;padding:0 30px 0 12px;border-radius:10px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--yazi);font:inherit;font-size:13.5px;-webkit-appearance:none;appearance:none;background-image:linear-gradient(45deg,transparent 50%,var(--soluk) 50%),linear-gradient(135deg,var(--soluk) 50%,transparent 50%);background-position:calc(100% - 15px) 15px,calc(100% - 10px) 15px;background-size:5px 5px;background-repeat:no-repeat}
.inot{margin-top:12px;padding:12px;border-radius:14px;background:var(--kart2);border:1px solid var(--cizgi)}.inoth{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:650;font-size:14px}.inoth button{background:none;border:0;color:var(--vurgu);font:inherit;font-size:13px;padding:6px 2px;cursor:pointer}.inotm{margin-top:6px;font-size:14px;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere}.isl .inot textarea,.isl .ionay textarea{width:100%;box-sizing:border-box;margin-top:8px;padding:10px 12px;border-radius:12px;border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);font:inherit;font-size:15px;line-height:1.4;resize:vertical}.isl .ionay textarea{background:var(--kart2)}.inot .iseg{margin-top:8px}
.apn{font-size:12px;line-height:1}.acnt{grid-column:1/-1;font-size:12.5px;color:var(--soluk);margin-top:3px;line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;white-space:pre-wrap;overflow-wrap:anywhere;cursor:pointer}.acnt.acik{-webkit-line-clamp:unset;display:block}
.iiz{margin-top:12px;padding:12px;border-radius:14px;background:var(--kart2);border:1px solid var(--cizgi)}.iiz .iseg{margin-top:10px}.iiz .ichip button,.isl .iiz input,.iiz .iacil{background:var(--kart)}
.ialm{margin-top:12px}.ialr{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:center;padding:7px 0;border-top:1px solid var(--cizgi)}.ialr>span:nth-child(2){display:flex;flex-direction:column;min-width:0;cursor:pointer}.ialr .k{font-size:11.5px}.ialr .art{color:var(--art)}.ialr .eks{color:var(--eks)}.ialr button{width:36px;height:36px;border-radius:10px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--soluk);font:inherit}.ialr.cal{opacity:.8}.ialm .ichip{margin-top:8px}.ialf{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;margin-top:8px}.isl .ialf input{margin:0;width:100%}.isl .ialf .ibtn{flex:none;height:44px;padding:0 16px;width:auto;font-size:15px}.ialm .say{margin-left:6px;font-size:12px;font-weight:700;color:var(--soluk);background:var(--kart2);border-radius:999px;padding:1px 8px}
.asalm{padding:12px 14px}.asalm .gayr{margin-top:6px}
#almtoast{position:fixed;left:50%;transform:translateX(-50%);top:calc(10px + env(safe-area-inset-top));z-index:1000;display:flex;flex-direction:column;gap:8px;width:min(440px,calc(100vw - 24px))}.almt{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:12px 12px 12px 14px;border-radius:14px;background:var(--kart);border:1px solid var(--cizgi);border-left:4px solid var(--mor);box-shadow:0 8px 30px rgba(0,0,0,.35);cursor:pointer;font-size:14px}.almt>span:nth-child(2){display:flex;flex-direction:column;min-width:0}.almt .k{font-size:12px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}@media (max-width:380px){.almt{padding:9px 10px;gap:8px;font-size:13px}.almt .k{-webkit-line-clamp:1}}.almt.yuk{border-left-color:var(--art)}.almt.dus{border-left-color:var(--eks)}.almt button{width:34px;height:34px;border-radius:10px;border:0;background:var(--kart2);color:var(--soluk);font:inherit}
.asrk{padding:12px 14px}.asrkh{cursor:pointer;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;align-items:baseline;font-size:13px}.asrkh>b{font-size:14.5px;font-variant-numeric:tabular-nums;white-space:nowrap}.asrk b.art{color:var(--art)}.asrk b.eks{color:var(--eks)}.asrk b.uy{color:var(--uyari)}.asrc{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:12px}.asrs{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:1px 10px;padding:9px 0;border-top:1px solid var(--cizgi);margin-top:10px;font-size:13.5px}.asrs+.asrs{margin-top:0}.asrs>b{font-variant-numeric:tabular-nums;white-space:nowrap}.asrs .k{grid-column:1/-1;font-size:12px}
.asfl{grid-column:1/-1;margin-top:8px;display:flex;flex-direction:column}.asfl>div{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:center;padding:7px 0;border-top:1px solid var(--cizgi)}.asfl>div>span:nth-child(2){display:flex;flex-direction:column;min-width:0}.asfl .k{font-size:11.5px}.asfr{display:flex;flex-direction:column;align-items:flex-end}.asfr b{font-size:13px;font-variant-numeric:tabular-nums}.asfl b.art{color:var(--art)}.asfl b.eks{color:var(--eks)}
.actop{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;padding:10px 12px 2px;margin-top:6px;border-top:1px solid var(--cizgi);font-size:13px;font-weight:650}.actop .aca{font-weight:500}
/* madde 866: sade piyasa */
.pk2{padding:14px}
.pkara{display:flex;align-items:center;gap:8px;padding:0 12px;height:46px;border-radius:14px;background:var(--kart2);border:1px solid var(--cizgi)}.pkara>span:first-child{font-size:18px;color:var(--soluk)}
.pkara input{flex:1;min-width:0;border:0!important;background:none!important;outline:none;font:inherit;font-size:15px;color:var(--yazi);padding:0!important;height:44px;box-shadow:none!important}.pkara #piyd{white-space:nowrap;font-size:11.5px}
.pksek{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;-webkit-mask-image:var(--kay-mask,none);mask-image:var(--kay-mask,none);margin:12px -14px 0;padding:0 14px}.pksek::-webkit-scrollbar{display:none}
.pksek button{flex:none;height:36px;padding:0 14px;border-radius:999px;border:1px solid var(--cizgi);background:none;color:var(--soluk);font:inherit;font-size:13.5px;font-weight:600;cursor:pointer;white-space:nowrap}
.pksek button.on{background:var(--yazi);border-color:var(--yazi);color:var(--bg)}
.pkay{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px}
.pkdon{display:flex;background:var(--kart2);border-radius:10px;padding:2px}.pkdon button{height:32px;min-width:42px;padding:0 10px;border:0;border-radius:8px;background:none;color:var(--soluk);font:inherit;font-size:13px;font-weight:600;cursor:pointer}.pkdon button.on{background:var(--kart);color:var(--yazi);box-shadow:0 1px 3px rgba(0,0,0,.2)}
.pkhac{font-size:12.5px;color:var(--soluk);display:flex;align-items:center;gap:6px;white-space:nowrap}.pkay{min-width:0}.pkhac{flex:none}.pkhac select{max-width:96px;height:34px;border-radius:10px;border:1px solid var(--cizgi);background:var(--kart2);color:var(--yazi);font:inherit;font-size:13px;font-weight:600;padding:0 8px}
.pkb{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--soluk);margin:14px 2px 8px}
.pkl{display:flex;flex-direction:column;gap:4px}
.pkr{display:grid;grid-template-columns:36px minmax(0,1fr) auto 36px;gap:10px;align-items:center;padding:8px 4px 8px 10px;border-radius:12px;background:var(--kart2);cursor:pointer;-webkit-tap-highlight-color:transparent;transition:background .5s}
.pkr:active{filter:brightness(1.08);transform:scale(.995)}.pkr:focus-visible{outline:2px solid var(--vurgu);outline-offset:1px}
.pk2 .pkd.fy{box-shadow:0 0 0 2px color-mix(in srgb,var(--art) 55%,transparent)}.pk2 .pkd.fa{box-shadow:0 0 0 2px color-mix(in srgb,var(--eks) 55%,transparent)}
.pkr.pyok{opacity:.55}
.pkav{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:800;letter-spacing:-.3px;color:hsl(var(--h) 75% 25%);background:hsl(var(--h) 80% 91%)}
:root[data-theme="dark"] .pkav{color:hsl(var(--h) 80% 75%);background:hsl(var(--h) 45% 20%)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .pkav{color:hsl(var(--h) 80% 75%);background:hsl(var(--h) 45% 20%)}}
.pkm{min-width:0;display:flex;flex-direction:column;gap:2px}.pkt{display:flex;align-items:center;flex-wrap:wrap;gap:3px 5px;min-width:0}.pkt b{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pks{font-size:12px;color:var(--soluk);font-variant-numeric:tabular-nums;line-height:1.35}.pks i{font-style:normal;opacity:.5}.pks .art{color:var(--art)}.pks .eks{color:var(--eks)}
.pkz{flex:none;font-size:10.5px;font-weight:650;padding:1px 6px;border-radius:999px;background:var(--kart);color:var(--soluk);white-space:nowrap}.pkz.sen{color:#fff;min-width:16px;text-align:center;padding:1px 5px}.pkz.sen.L{background:#0a7d45}.pkz.sen.S{background:#c42b20}.pkz.yok{background:none;border:1px dashed var(--cizgi)}
.pkd{min-width:76px;text-align:center;font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;padding:7px 8px;border-radius:10px;background:var(--kart);white-space:nowrap}
.pk2 .pkd.art{color:#fff!important;background:#0a7d45}.pk2 .pkd.eks{color:#fff!important;background:#c42b20}
.pky{width:36px;height:40px;border:0;background:none;color:var(--soluk);font-size:19px;cursor:pointer;padding:0}.pky.on{color:#f5a524}
.pkdaha{width:100%;margin-top:8px;height:42px;border-radius:12px;border:1px dashed var(--cizgi);background:none;color:var(--vurgu);font:inherit;font-weight:600;cursor:pointer}
.pkbos{padding:22px 14px;text-align:center;border-radius:12px;background:var(--kart2);color:var(--soluk);font-size:13.5px;line-height:1.5}
.pknot{margin-top:12px;font-size:11.5px;color:var(--soluk);line-height:1.5}
@media (max-width:380px){.pkhac>span{display:none}.pkdon button{min-width:32px;padding:0 6px}}
@media (max-width:360px){.pkr{grid-template-columns:30px minmax(0,1fr) auto 32px;gap:8px;padding-left:8px}.pkav{width:30px;height:30px;font-size:11px}.pkd{min-width:66px;font-size:13px;padding:6px}.pky{width:32px}}
/* madde 865: mobil ekran testleri (320–430 px) düzeltmeleri */
.pfa{display:none}
.pyr .rz{white-space:nowrap;flex:none}
.gdon{overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}.gdon::-webkit-scrollbar{display:none}.gdon button{white-space:nowrap;flex:none}
@media (max-width:400px){.pyl .pyr,.pyr.ust{grid-template-columns:22px minmax(0,1fr) 68px 60px!important;gap:6px;padding:4px 6px}.pyr .pfc{display:none}.pfa{display:block;font-size:11.5px;color:var(--soluk);font-weight:500;font-variant-numeric:tabular-nums}
  .pyr>span:nth-child(2){flex-direction:column;align-items:flex-start!important;justify-content:center}.pyr>span:nth-child(2)>a{max-width:100%}.pyr .rz{margin-left:0!important;margin-top:1px}
  .pyr>span:nth-child(2){display:grid!important;grid-template-columns:auto auto;justify-content:start;column-gap:5px}.pyr>span:nth-child(2) .pfa{grid-column:1/-1}
  .pya .gdon{max-width:100%}.pyk .gdon button{padding:0 11px}}
.abr{grid-column:2;min-width:0}.abh{grid-row:span 2}
@media (max-width:380px){.asbak{grid-template-columns:84px minmax(0,1fr)!important;gap:4px 12px!important;padding:12px!important}.abh{width:84px!important;height:84px!important;grid-row:auto}.abt{font-size:22px!important}
  .abr{grid-column:1/-1;margin-top:4px}.abkz span{display:block}}
.ipr{grid-template-columns:26px minmax(0,1fr) auto!important;grid-template-areas:"n m k" "n t s";row-gap:4px!important}
.ipr .iprn{grid-area:n}.ipr .iprm{grid-area:m}.ipr .iprk{grid-area:k;align-self:start}.ipr .iprtp{grid-area:t;margin-top:0!important}.ipr .iprs{grid-area:s;justify-self:end;padding:6px 14px!important}
@media (max-width:360px){.apr .k2{white-space:normal!important;text-overflow:clip!important}.ipr{grid-template-columns:minmax(0,1fr) auto!important;grid-template-areas:"m k" "t s"}.ipr .iprn{display:none}}
.tema{width:36px!important;height:36px!important;flex:none}.hmb{flex:none}
.gdon button,.mod button{min-height:34px}.aygez button{min-width:40px;min-height:36px}.dgr .mod button,.dozet .mod button{padding:6px 12px!important}
.abh2{font-size:10.5px!important}
.nw{white-space:nowrap}h1{white-space:nowrap}
@media (max-width:400px){.apr .k2{white-space:normal!important;text-overflow:clip!important}header.kucuk h1 img{display:none}header.kucuk #ustkitap{font-size:13px;padding:3px 8px}header.kucuk .canli>span{display:none}
  .abc span{font-size:11px;padding:2px 8px;white-space:nowrap;flex:none}.abc{gap:4px!important;flex-wrap:wrap!important}.dpb .gb{font-size:19px}}
.pyl .pyr>span:nth-child(2)>a{padding:8px 0;margin:-8px 0}.ipr .iprtp{min-height:32px}
#piyelle.as-sayfa{border:0;padding:0;margin:0}
.asbak.kart{margin:0 0 12px}
.apk{padding:14px}.apkh{display:flex;justify-content:space-between;align-items:center;font-size:16px}.apkh>div{display:flex;align-items:center;gap:8px}.apkh .say,.opzh .say{margin-left:6px;font-size:12px;font-weight:700;color:var(--soluk);background:var(--kart2);border-radius:999px;padding:1px 8px}.apkh .art{color:var(--art)}.apkh .eks{color:var(--eks)}
.apko{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12.5px;color:var(--soluk);margin:6px 0 10px}.apko .art{color:var(--art);font-weight:600}.apko .eks{color:var(--eks);font-weight:600}.apko b.art,.apko b.eks{font-weight:700}
.apuy{display:flex;gap:8px;align-items:flex-start;padding:10px 12px;border-radius:12px;margin-bottom:10px;font-size:12.5px;line-height:1.45;color:var(--uyari);background:color-mix(in srgb,var(--uyari) 11%,transparent)}.apuy span{color:var(--yazi)}
.apl{display:flex;flex-direction:column;gap:6px}
.apr{position:relative;display:grid;grid-template-columns:24px minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px 12px 11px 14px;border-radius:12px;background:var(--kart2);color:inherit;text-decoration:none;overflow:hidden;-webkit-tap-highlight-color:transparent}.apr:active{transform:scale(.99);filter:brightness(1.06)}
.apr .ass{position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--cizgi)}.apr .ass.art{background:var(--art)}.apr .ass.eks{background:var(--eks)}
.apr .iyon2{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:11.5px;font-weight:700;color:#fff}.apr .iyon2.L{background:#0a7d45}.apr .iyon2.S{background:#c42b20}
.aprm{min-width:0;display:flex;flex-direction:column;gap:2px}.aprt{display:flex;align-items:center;gap:2px;font-size:15px;min-width:0}.aprt b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}@media (max-width:350px){.aprt{flex-wrap:wrap;row-gap:2px}.aprt b{flex:none;overflow:visible;text-overflow:clip}}.apr .k2{font-size:12px;color:var(--soluk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}
.aps{font-size:10.5px;font-weight:600;color:var(--uyari);border:1px solid color-mix(in srgb,var(--uyari) 45%,transparent);border-radius:999px;padding:0 6px;margin-left:6px;white-space:nowrap}
.aptp{font-size:11.5px;color:var(--soluk);font-variant-numeric:tabular-nums}
.aprk{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.aprk b{display:block;font-size:15px}.aprk span{font-size:12px;opacity:.85}.aprk.art{color:var(--art)}.aprk.eks{color:var(--eks)}
.apk .elkb{margin-top:12px}
.iprtp{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;margin-top:6px;padding:3px 0;border:0;background:none;font:inherit;font-size:11.5px;cursor:pointer;color:var(--soluk);text-align:left}.iprtp .art{color:var(--art)}.iprtp .eks{color:var(--eks)}.iprtp i{font-style:normal;color:var(--vurgu)}.ipd{padding:14px;border-radius:14px;border:1px solid var(--vurgu);background:var(--kart2);margin:4px 0 12px}.ipdh{display:flex;justify-content:space-between;align-items:center;font-size:15px;margin-bottom:4px}.ipd .k2{color:var(--soluk);font-size:12px}.ipd input{width:100%;box-sizing:border-box}.ipdb{width:100%;margin-top:10px}
.iprl{display:flex;flex-direction:column;gap:6px;margin:4px 0 12px}.ipr{display:grid;grid-template-columns:26px minmax(0,1fr) auto auto;gap:10px;align-items:center;padding:10px;border-radius:12px;background:var(--kart2);border-left:3px solid var(--cizgi)}.ipr.art{border-left-color:var(--art)}.ipr.eks{border-left-color:var(--eks)}.iprn{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700;background:var(--kart);color:var(--soluk)}.iprm{min-width:0}.iprt{color:var(--yazi);font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.iprr{font-size:10.5px;font-weight:600;color:var(--art);background:color-mix(in srgb,var(--art) 14%,transparent);border-radius:999px;padding:1px 6px;margin-left:4px}.ipr .k2{color:var(--soluk);font-size:12px;font-variant-numeric:tabular-nums}.ipr .k2 b{color:var(--yazi);font-weight:600}.iprb{height:3px;border-radius:2px;background:var(--cizgi);margin-top:5px;overflow:hidden}.iprb span{display:block;height:100%;background:var(--soluk);opacity:.6}.iprk{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.iprk b{display:block;font-size:14px}.iprk span{font-size:11.5px;opacity:.85}.ipr.art .iprk{color:var(--art)}.ipr.eks .iprk{color:var(--eks)}.iprs{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);border-radius:10px;padding:8px 12px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;min-height:36px}.iprs:active{transform:scale(.97)}.pyn{display:inline-block;font-size:10.5px;font-weight:600;color:var(--vurgu);background:color-mix(in srgb,var(--vurgu) 12%,transparent);border-radius:999px;padding:0 6px;margin-left:4px}
.asbak{display:grid;grid-template-columns:118px minmax(0,1fr);gap:6px 16px;align-items:center;margin:8px 0 6px;padding:14px;border-radius:16px;background:linear-gradient(135deg,var(--kart2),var(--kart));border:1px solid var(--cizgi)}.abh{width:118px;height:118px}.abh1{font-size:20px;font-weight:700;fill:var(--yazi);font-variant-numeric:tabular-nums}.abh2{font-size:9px;fill:var(--soluk)}.abk{min-width:0}.abu{font-size:12px;color:var(--soluk);text-transform:uppercase;letter-spacing:.06em}.abt{font-size:26px;font-weight:700;line-height:1.15;font-variant-numeric:tabular-nums;white-space:nowrap}.abkz{font-size:13px;font-weight:600;margin:2px 0 8px;font-variant-numeric:tabular-nums}.abkz span{color:var(--soluk);font-weight:400}.abkz.art{color:var(--art)}.abkz.eks{color:var(--eks)}.abs{display:flex;align-items:center;gap:8px;padding:5px 0;border-top:1px solid var(--cizgi)}.abs i{width:10px;height:10px;border-radius:3px;flex:none}.abs span{flex:1;min-width:0;font-size:13.5px;display:flex;flex-direction:column}.abs small{color:var(--soluk);font-size:11px}.abs b{font-size:14.5px;font-variant-numeric:tabular-nums;white-space:nowrap}.abc{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.abc span{font-size:11.5px;color:var(--soluk);background:var(--bg);border:1px solid var(--cizgi);border-radius:999px;padding:3px 9px;font-variant-numeric:tabular-nums}
@media (max-width:380px){.asbak{grid-template-columns:92px minmax(0,1fr);gap:6px 12px;padding:12px}.abh{width:92px;height:92px}.abt{font-size:22px}}
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
.pyr .rz{font-size:10.5px;font-weight:650;padding:1px 5px;border-radius:6px;margin-left:5px;background:var(--kart2);color:var(--soluk)}.pyr .rz.yok{background:none;border:1px dashed var(--cizgi);font-weight:600}
.pyr .art{color:var(--art)}.pyr .eks{color:var(--eks)}
.pyr.ust{background:none;color:var(--soluk);font-size:11.5px;padding-top:0;padding-bottom:0}
.fl-a{animation:fla .8s}.fl-e{animation:fle .8s}
@keyframes fla{from{background:color-mix(in srgb,var(--art) 22%,transparent)}}@keyframes fle{from{background:color-mix(in srgb,var(--eks) 22%,transparent)}}
@media (max-width:600px){.pyr{grid-template-columns:24px minmax(0,1.2fr) minmax(0,1fr) 64px 58px}.pyr .hc{display:none}}
/* MADDE 834-836: panelden işlem penceresi — grafik önde, ayarla -> onayla (basılı tut), eylem başparmak bölgesinde */
.shp.isl{padding:10px 16px 0 !important}.isl{--dy:#fff;--fa:#0a7d45;--fe:#c42b20}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .isl{--dy:#0F1115;--fa:var(--art);--fe:var(--eks)}}:root[data-theme="dark"] .isl{--dy:#0F1115;--fa:var(--art);--fe:var(--eks)}
.isl .ihd{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}.isl .ihd>div:first-child{min-width:0;flex:1}.isl .ihd .shx{flex:none}.isl .ifr{flex-wrap:wrap}.isl .iad{display:flex;align-items:center;gap:8px}.isl .iad b{font-size:19px;font-weight:700;letter-spacing:-.2px}
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
.isl .iki{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px}.isl .iki input{min-width:0}.isl .ichip button{padding:0 2px}
.isl .iacil{display:flex;justify-content:space-between;align-items:center;width:100%;height:44px;margin-top:14px;border:1px solid var(--cizgi);border-radius:12px;background:var(--kart);color:var(--yazi);font:inherit;font-weight:600;padding:0 14px;cursor:pointer}
.isl .iacil i{font-style:normal;font-size:12px;color:var(--soluk)}.isl .iacil.on i{color:var(--vurgu)}.isl .iacil i.oner{color:var(--uyari)}.isl .iacil:disabled{cursor:default;opacity:.8}
.isl #isltah{margin-top:12px}.isl .itg{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;background:var(--kart2);border-radius:12px;padding:10px 12px;font-size:13px;font-variant-numeric:tabular-nums}
.isl .itg div{display:flex;justify-content:space-between;gap:8px}.isl .itg span{color:var(--soluk)}
.isl .ion{font-size:12.5px;margin:8px 0 0;line-height:1.45}
.isl .ionay{margin-top:14px}.isl .iob{font-size:17px;font-weight:700;margin-bottom:10px}
.isl .iozt{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;background:var(--kart2);border-radius:14px;padding:12px 14px;font-variant-numeric:tabular-nums}
.isl .iozt div{display:flex;flex-direction:column;gap:2px}.isl .iozt .k{font-size:12px}
.isl .ipoz{background:var(--kart2);border-radius:16px;padding:14px;margin-top:14px}.isl .iph{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px 10px}.isl .iph>div:first-child{min-width:0}.isl .ikz{margin-left:auto}
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
.dnm{margin-top:12px;padding:6px 12px;border-radius:12px;background:var(--kart2);font-size:13px}.dnm .dnh,.dnm .dnr{display:grid;grid-template-columns:62px 58px minmax(0,1fr) 54px;gap:8px;align-items:center}.dnm .dnh{font-size:11px;color:var(--soluk);padding:4px 0;margin:0}.dnr{padding:7px 0;border-top:1px solid var(--cizgi)}.dna{font-weight:600;line-height:1.2}.dnz{min-width:0}.dnb{position:relative;display:block;height:6px;border-radius:3px;background:var(--cizgi)}.dnb i{position:absolute;top:-3px;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:var(--vurgu);border:2px solid var(--kart2)}.dnu{display:flex;justify-content:space-between;font-size:11px;color:var(--soluk);margin-top:3px;gap:4px}.dns{width:54px;height:22px}
.asg{width:100%;height:auto;display:block;margin:4px 0 6px}.asgt{font-size:11px;fill:var(--soluk)}.ash{font-size:12.5px;font-weight:600;color:var(--soluk);margin-top:12px}
.asoz{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}.asb{font-size:20px;font-weight:700;margin-top:2px}.asb .k{font-size:12px;font-weight:500}
.elp{margin-top:12px;padding:12px 14px;border-radius:12px;background:var(--kart2);font-size:13.5px}.elh{font-weight:700;margin-bottom:6px}.elr{display:flex;justify-content:space-between;gap:10px;padding:5px 0;line-height:1.4}.elr .r{text-align:right}.eld{margin-top:8px}.eld summary{cursor:pointer;color:var(--soluk);font-size:13px;padding:4px 0}
.elk{margin-top:12px;padding:12px 14px;border-radius:12px;font-size:13.5px;line-height:1.5;background:color-mix(in srgb,var(--vurgu) 12%,transparent)}.elk li{margin:3px 0}.elkb{margin-top:10px;width:100%;min-height:44px;border:0;border-radius:10px;font:inherit;font-weight:600;background:var(--vurgu);color:var(--bg);cursor:pointer}
.isl .ibtn.tut span{position:relative}.isl .isah{margin-top:12px;padding:10px 12px;border-radius:12px;font-size:13px;line-height:1.45}.isl .isah.sen{background:color-mix(in srgb,var(--vurgu) 12%,transparent)}.isl .isah.bot{background:color-mix(in srgb,var(--uyari) 14%,transparent)}.isl .isah.yok{background:var(--kart2);font-size:13.5px}.isl .ibtn.ikinci,.isl .ibtn.ikinci:disabled{background:var(--kart2);color:var(--soluk);opacity:1}
.isl .ibek{align-items:center}.isl .ibx{height:36px;padding:0 14px;border-radius:10px;border:1px solid color-mix(in srgb,var(--eks) 45%,transparent);background:var(--kart);color:var(--fe);font:inherit;font-weight:650;cursor:pointer}.isl .iacil.kucuk2{height:auto;min-height:44px;padding:8px 14px;margin-top:8px}.isl .iacil.kucuk2 i{text-align:right}.isl .art,.pyk .art{color:var(--fa)}.isl .eks,.pyk .eks{color:var(--fe)}.isl .shx{width:44px;height:44px}.isl .iuyr{color:var(--uyari);font-size:12.5px;margin:8px 0 0}
.isl .igl3{display:flex;gap:14px;font-size:11.5px;color:var(--soluk);padding:2px 8px 6px}.isl .ibtn:focus-visible,.isl button:focus-visible{outline:2px solid var(--vurgu);outline-offset:2px}
@media (prefers-reduced-motion:reduce){.isl .ibtn.tut.dolu::before{transition:none}}
@media (max-width:420px){.isl .ikg{grid-template-columns:repeat(2,minmax(0,1fr))}.isl .ichip.kisa{flex-basis:150px}}
/* iOS Safari 16 px altı kutuya dokununca sayfayı büyütür ve geri küçültmez: tüm form öğeleri en az 16 px */
input,select,textarea{font-size:max(16px,1em)}.tsor input,.ruv input,.pkara input,.isl .inot textarea,.isl .ionay textarea,.assr select,.pkhac select{font-size:16px}.assr select{min-width:0;max-width:100%;text-overflow:ellipsis}.assr label{flex:none}
/* Piyasa: sekmeler yana kaymasın, alt satıra geçsin; dönem + hacim satırı dar ekranda kırılsın */
.pksek{flex-wrap:wrap;overflow:visible;margin:12px 0 0;padding:0;-webkit-mask-image:none;mask-image:none}.pksek button{flex:1 1 auto;padding:0 12px}.pkay{flex-wrap:wrap;row-gap:8px}.pkdon{flex:1 1 auto;min-width:0;max-width:100%}.pkdon button{flex:1 1 0;min-width:0;padding:0 4px}.pkhac{margin-left:auto}
@media (max-width:340px){.pk2{padding:12px 10px}.pkr{grid-template-columns:minmax(0,1fr) auto 28px;gap:6px;padding-left:10px}.pkr>.pkav{display:none}.pkd{min-width:0;font-size:12.5px;padding:6px 5px}.pky{width:28px}.pks{font-size:11.5px}}
</style></head><body><div class="kap">
<header id="ust"><div><h1><button class="hmb" id="hmb" onclick="menuAc()" aria-label="Menü: Bot / Al-Sat" aria-haspopup="true">☰</button><img src="ikon-192.png" alt=""><span id="baslik">Carry</span></h1><div class="k" id="alt"></div><div id="ustkitap"></div></div>
  <div class="sag"><span class="canli" id="canliust"><i></i><span>bağlanıyor</span></span><button class="tema" id="tema" onclick="temaDegis()" aria-label="tema">◐</button></div></header>
<div id="cek">↓ yenilemek için bırak</div>
<div class="sekme" id="sekme"></div>
<nav class="alt" id="nav"></nav>
<div id="sheet" hidden></div>
<div id="menu" hidden></div>
<div id="icerik"><div class="kart"><div class="iskelet" style="height:34px;width:60%"></div><div class="iskelet" style="height:70px;margin-top:14px"></div>
  <div class="iskelet" style="height:44px;margin-top:10px"></div></div><div class="kart"><div class="iskelet" style="height:160px"></div></div></div></div>
<script>
const VERI_GOMULU = /*VERI*/null;
const $ = s => document.querySelector(s);
const yz = (v, d=2) => v==null ? "—" : (v>=0?"+":"") + (v*100).toFixed(d).replace(".",",") + "%";
const para = v => v==null ? "—" : v.toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2}) + "\u00a0$";   // madde 907: "$" alt satıra düşmesin
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
// MADDE 851: iki ayrı alan — BOT (eski panel, elle yok) ve AL-SAT (bottan ayrı hesap). Üstteki ☰ menüden seçilir.
const SAYFA_BOT = [["ozet","Özet"],["poz","Pozisyonlar"],["gecmis","Geçmiş"],["olay","Olaylar"]];
const SAYFA_AS = [["alsat","Pozisyonlarım"],["piyasa","Piyasa"],["asgecmis","Geçmiş"]];
let ALAN = (()=>{ const h = (location.hash||"").slice(1); if (SAYFA_AS.some(x=>x[0]==h)) return "alsat"; if (SAYFA_BOT.some(x=>x[0]==h)) return "bot";
  try { return localStorage.getItem("carry_alan") == "alsat" ? "alsat" : "bot"; } catch(_){ return "bot"; } })();
let SAYFALAR = ALAN == "alsat" ? SAYFA_AS : SAYFA_BOT;
function alanSec(a){ ALAN = a; SAYFALAR = a == "alsat" ? SAYFA_AS : SAYFA_BOT; try { localStorage.setItem("carry_alan", a); } catch(_){}
  menuKapat(); if (ISL) islKapat(); if (SHEET) sheetKapat(); sayfa = SAYFALAR[0][0]; history.replaceState(null, "", "#"+sayfa); if (VERI) ciz(); scrollTo(0,0); }
// madde 879: menü — alan kartlarında canlı özet (bot kitabı / al-sat özkaynağı, pozisyon sayısı), tema seçimi, bağlantı durumu
function menuAc(){ const m = $("#menu"); m.hidden = false;
  const k = VERI && VERI.kurulumlar && VERI.kurulumlar[secili], E = ELLE_OZ && !ELLE_OZ.hata ? ELLE_OZ : null;
  const botOz = k ? `<span class="mz"><b>${para(k.kitap_canli!=null ? k.kitap_canli : k.kitap)}</b> <span class="${sinif(k.kar_oran)}">${yz(k.kar_oran)}</span> · ${Object.keys(k.pozisyonlar||{}).length} pozisyon</span>` : "";
  const asOz = E && E.hesap && E.hesap.ozkaynak!=null ? `<span class="mz"><b>${para(E.hesap.ozkaynak)}</b> · ${(E.pozisyonlar||[]).length} pozisyon</span>` : "";
  const b = (a, i, ad, alt, oz) => `<button class="ms ${ALAN==a?"on":""}" onclick="alanSec('${a}')" aria-current="${ALAN==a}"><i aria-hidden="true">${i}</i><span><b>${ad}</b><span class="k">${alt}</span>${oz}</span></button>`;
  const T = [["oto","◐","Otomatik"],["koyu","☾","Koyu"],["acik","☀","Açık"]];
  const cn = $("#canliust");
  m.innerHTML = `<div class="mb" onclick="menuKapat()"></div><div class="mp" role="dialog" aria-label="Menü">
    <div class="mtp"><b>Carry</b><button class="shx" onclick="menuKapat()" aria-label="Menüyü kapat">✕</button></div>
    <div class="mh">Alan</div>
    ${b("bot", "🤖", "Bot", "carry botu" + (k ? ` · ${k.mod=="live"?"canlı":"demo"}` : ""), botOz)}${b("alsat", "💱", "Al-Sat", "kendi alım satımın — bottan ayrı", asOz)}
    <div class="mh">Görünüm</div>
    <div class="mtm" role="radiogroup" aria-label="Tema">${T.map(([t,i,ad])=>`<button role="radio" aria-checked="${tema==t}" class="${tema==t?"on":""}" onclick="temaSec('${t}')"><i aria-hidden="true">${i}</i>${ad}</button>`).join("")}</div>
    <div class="mal">${cn ? cn.outerHTML.replace('id="canliust"', "") : ""}<span class="k">Fiyatlar Binance'ten canlı · tema bu cihazda saklanır</span></div></div>`;
  const on = m.querySelector(".ms.on"); if (on) on.focus(); }
function temaSec(t){ tema = t; try { localStorage.setItem("carry_tema", t); } catch(_){} temaUygula(); if (VERI) ciz(); if (!$("#menu").hidden) menuAc(); }
function menuKapat(){ const m = $("#menu"); if (m){ m.hidden = true; m.innerHTML = ""; } }
addEventListener("keydown", e=>{ if (e.key === "Escape" && !$("#menu").hidden) menuKapat(); });
// MADDE 757: D tasarımı — alt menü simgeleri
const NAV_SVG = {ozet:'<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>', poz:'<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="5" rx="1.5"/><path d="M3 20h12"/>',
  gecmis:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', alsat:'<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><path d="M16 15h2"/>', asgecmis:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', piyasa:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/><path d="M8 13l2-2 2 2 3-3"/>', olay:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>'};
let sayfa = (location.hash||"").slice(1); if (!SAYFALAR.some(x=>x[0]==sayfa)) sayfa = SAYFALAR[0][0];
const MOBIL = () => innerWidth < 700;   // madde 754: telefonda sıkı liste ve sade metinler
function sayfaSec(a){ if (a==sayfa) return; sayfa = a; history.replaceState(null, "", "#"+a); ciz(); scrollTo(0,0); }
// madde 753: adres çubuğunda / yer iminde #gecmis vb. değişince sekme de değişsin
addEventListener("hashchange", ()=>{ const h = (location.hash||"").slice(1); if (h==sayfa || !VERI) return;
  if (!SAYFALAR.some(x=>x[0]==h)){ const a = SAYFA_AS.some(x=>x[0]==h) ? "alsat" : SAYFA_BOT.some(x=>x[0]==h) ? "bot" : null; if (!a) return; ALAN = a; SAYFALAR = a=="alsat" ? SAYFA_AS : SAYFA_BOT; }
  sayfa = h; ciz(); scrollTo(0,0); });
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
    h += `<div ${isi(s.gun,0.03,"g"+(s.canli?" canlig":""))} title="${ipucu}"><div class="n">${d}${s.canli?" ●":""}</div><div class="v"><span class="vt">${yz(s.gun)}</span><span class="vk">${(s.gun>=0?"+":"−") + Math.abs(s.gun*100).toFixed(1).replace(".",",")}</span></div></div>`;   // madde 876: dar ekranda kısa (−4,3)
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
let PIY_SEKME = PIY_DEP("carry_piy_sekme") || (PIY_MOD=="fund" ? "fund" : "yuk"), PIY_N = 25;
// madde 833: dönem (1 / 3 / 7 / 30 gün). 1 gün = Binance'in kayan 24 sa değişimi; diğerleri günlük mumlardan (son 31 gün, coin başına
// bir istek, 30 dk önbellek): şimdiki fiyat / N gün önceki günlük kapanış - 1. Yalnız listede görünecek coinler için (hacim süzgeci +
// izleme listesi + arama) indirilir; 6 paralel istek. Coin N günden yeniyse "—" (sıralamaya girmez).
// madde 873: 0 = "Bugün" — Binance günlük mumunun açılışından (00:00 UTC = 03:00 TR) beri; TradingView'in ve Binance uygulamasının
// gün değişimiyle aynı. Kayan 24 sa (Binance ticker'ı) gece yarısından değil 24 saat önceki fiyattan ölçer, o yüzden farklı çıkar.
// Gün açılışı PIY_AC'ta (coin -> {ot: mumun açılış zamanı, o: açılış fiyatı}); gün dönünce (ot eskiyince) yeniden indirilir.
let PIY_DONEM = [0,1,3,7,30].includes(PIY_DEP("carry_piy_donem2")) ? PIY_DEP("carry_piy_donem2") : 0, PIY_GUN = {}, PIY_AC = {}, PIY_GYUK = {bek: 0, bit: 0, calis: false};
const PIY_DAD = {0: "bugün", 1: "24 sa", 3: "3 gün", 7: "1 hafta", 30: "1 ay"};
const PIY_DBAS = {0: "Bugün (03:00'dan beri)", 1: "Son 24 saatte", 3: "Son 3 günde", 7: "Son 1 haftada", 30: "Son 1 ayda"};
const piyGunBas = () => Math.floor(Date.now() / 864e5) * 864e5;
const piyAcTaze = s => PIY_AC[s] && PIY_AC[s].ot == piyGunBas();
function piyBugun(o){ const a = PIY_AC[o.s]; return a && a.ot == piyGunBas() && a.o > 0 && o.f > 0 ? (o.f / a.o - 1) * 100 : null; }
function piyDeg(o){
  if (PIY_DONEM == 1) return o.p;
  if (PIY_DONEM == 0) return piyBugun(o);
  const g = PIY_GUN[o.s]; if (!g || !(o.f > 0)) return null;
  const i = g.c.length - 1 - PIY_DONEM; return i >= 0 && g.c[i] > 0 ? (o.f / g.c[i] - 1) * 100 : null;
}
async function piyGecmisYukle(){
  if (VERI_GOMULU || PIY_DONEM == 1 || PIY_GYUK.calis || sayfa != "piyasa") return;
  const A = Object.values(PIY).filter(o => o.f>0 && (!PIY_EVREN || PIY_EVREN.has(o.s)) && o.s.endsWith("USDT"));
  const S = A.filter(o => (o.q||0) >= PIY_HACIM || PIY_IZLE.has(o.s) || (PIY_ARA && o.s.includes(PIY_ARA))).map(o => o.s)
    .filter(s => PIY_DONEM == 0 ? !piyAcTaze(s) : (!PIY_GUN[s] || Date.now() - PIY_GUN[s].t > 30 * 60e3));
  if (!S.length) return;
  PIY_GYUK = {bek: S.length, bit: 0, calis: true}; piyasaBoya(true);
  let i = 0;
  const isci = async () => { while (i < S.length){ const s = S[i++];
    try { const d = await (await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=1d&limit=31`, {cache:"no-store"})).json();
      if (Array.isArray(d) && d.length){ PIY_GUN[s] = {t: Date.now(), c: d.map(x => +x[4])}; const z = d[d.length-1]; PIY_AC[s] = {ot: +z[0], o: +z[1]}; } } catch(_){}
    PIY_GYUK.bit++; if (PIY_GYUK.bit % 20 == 0) piyasaBoya(true); } };
  await Promise.all(Array.from({length: 10}, isci));   // madde 892: 10 paralel (≈110 coin ~2-3 sn; ağırlık 1/istek, sınırın çok altında)
  PIY_GYUK.calis = false; piyasaBoya(true);
}
function piyDonem(d){ PIY_DONEM = d; PIY_N = 25; PIY_DEP("carry_piy_donem2", d); ciz(); piyGecmisYukle(); }
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
  if (!(ISL_DURUM||{}).ayri) for (const c of (k && k.coin_ozet) || []) if (c.elle) R[c.s.endsWith("USDT") ? c.s : c.s+"USDT"] = "✋ elle";
  return R;
}
// MADDE 870: coin logosu — sunucudan (ikon/<COIN>.png); yüklenemezse harfli yuvarlak. Yüklenen / bulunamayan bellekte tutulur ki
// saniyede bir yeniden çizilen listelerde harf ↔ logo yanıp sönmesin.
const IKON_OK = new Set(), IKON_YOK = new Set();
function coinIkon(ad, cls = ""){
  let h = 0; for (const c of ad) h = (h * 31 + c.charCodeAt(0)) % 360;
  const ok = IKON_OK.has(ad), img = IKON_YOK.has(ad) ? "" : `<img src="ikon/${encodeURIComponent(ad)}.png" alt="" loading="lazy" decoding="async" onload="IKON_OK.add('${ad}');this.parentNode.classList.add('ik')" onerror="IKON_YOK.add('${ad}');this.remove()">`;
  return `<span class="pkav ${ok ? "ik" : ""} ${cls}" style="--h:${h}" aria-hidden="true">${ea(ad.slice(0,2))}${img}</span>`;
}
function piySatir(o, R){   // madde 866: kart satır — tamamına dokun = al / sat; ☆ sağda
  const yd = PIY_IZLE.has(o.s), fl = PIY_ONCEKI[o.s], ad = o.s.replace(/USDT$/, ""), isl = ISL_DURUM && ISL_DURUM.acik, yok = isl && islYok(o.s);
  const benim = ((ELLE_OZ && ELLE_OZ.pozisyonlar) || []).find(x=>x.sembol == o.s);
  const fon = PIY_SEKME == "fund", ana = fon ? (o.r==null ? null : o.r*100) : o.d, anaM = ana==null ? "—" : fon ? piyYz(ana, 3) : piyYz(ana);
  const rz = (benim ? `<span class="pkz sen ${benim.adet>0?"L":"S"}" title="bu coinde ${benim.adet>0?"long":"short"} pozisyonun var">${benim.adet>0?"L":"S"}</span>` : "") + (R[o.s] && !(ISL_DURUM||{}).ayri ? `<span class="pkz">${R[o.s]}</span>` : "") + (yok ? `<span class="pkz yok" title="${ISL_DURUM.mod=="live"?"bu hesapta":"demo hesapta"} işlem görmüyor">yok</span>` : "");
  const alt = `<span class="nw">${piyFiyat(o.f)}</span> <i>·</i> <span class="nw">${piyHac(o.q)}$</span>` + (fon ? ` <i>·</i> <span class="nw ${sinif(o.d)}">${piyYz(o.d)}</span>` : (o.r!=null && Math.abs(o.r) >= 0.0003 ? ` <i>·</i> <span class="nw ${o.r<0?"eks":""}" title="funding (8 sa)">fon ${piyYz(o.r*100, 3)}</span>` : ""));
  const ac = isl ? `islAc('${o.s}')` : `window.open('https://www.binance.com/tr/futures/${o.s}','_blank','noopener')`;
  return `<div class="pkr ${yok?"pyok":""}" role="button" tabindex="0" onclick="${ac}" onkeydown="if(event.key=='Enter')${ac}" aria-label="${ad} ${isl?"al / sat":"Binance'te aç"}">
    ${coinIkon(ad)}
    <span class="pkm"><span class="pkt"><b>${ea(ad)}</b>${rz}</span><span class="pks">${alt}</span></span>
    <span class="pkd ${ana==null?"":ana>0?"art":ana<0?"eks":""} ${fl>0?"fy":fl<0?"fa":""}">${anaM}</span>
    <button class="pky ${yd?"on":""}" onclick="event.stopPropagation();piyIzle('${o.s}')" aria-pressed="${yd}" aria-label="${ad} ${yd?"izleme listesinden çıkar":"izleme listesine ekle"}">${yd?"★":"☆"}</button></div>`;
}
function piyListe(k){   // madde 866: tek liste — seçili sekme (yükselen / düşen / işlem / funding / izlediklerim) ya da arama
  const A = Object.values(PIY).filter(o => o.f>0 && o.p!=null && (!PIY_EVREN || PIY_EVREN.has(o.s)) && o.s.endsWith("USDT"));
  for (const o of A) o.d = piyDeg(o);
  const R = piyRozet(k), H = A.filter(o => (o.q||0) >= PIY_HACIM);
  const bos = m => `<div class="pkbos">${Object.keys(PIY).length ? m : "Piyasa verisi yükleniyor…"}</div>`;
  let L, bas, m;
  if (PIY_ARA){ L = A.filter(o => o.s.includes(PIY_ARA)).sort((a,b)=>(b.q||0)-(a.q||0)); bas = `“${PIY_ARA}” için ${L.length} sonuç`; m = "Bu adla coin yok."; }
  else if (PIY_SEKME == "izle"){ L = A.filter(o => PIY_IZLE.has(o.s)).sort((a,b)=>(b.d??-1e9)-(a.d??-1e9)); bas = `${L.length} coin · ${PIY_DAD[PIY_DONEM]} değişim`; m = "Henüz izlediğin coin yok. Listelerde coinin yanındaki ☆ işaretine dokun."; }
  else if (PIY_SEKME == "dus"){ L = H.filter(o=>o.d<0).sort((a,b)=>a.d-b.d); bas = `${PIY_DBAS[PIY_DONEM]} en çok düşenler`; m = "Bu süzgeçte düşen coin yok."; }
  else if (PIY_SEKME == "hac"){ L = H.slice().sort((a,b)=>(b.q||0)-(a.q||0)); bas = "24 saatte en çok işlem gören"; m = "Bu süzgeçte coin yok."; }
  else if (PIY_SEKME == "fund"){ L = H.filter(o=>o.r!=null && o.r!=0).sort((a,b)=>Math.abs(b.r)-Math.abs(a.r)); bas = "Funding en uç olanlar · artı: short'a ödenir, eksi: long'a"; m = "Bu süzgeçte coin yok."; }
  else { L = H.filter(o=>o.d>0).sort((a,b)=>b.d-a.d); bas = `${PIY_DBAS[PIY_DONEM]} en çok yükselenler`; m = "Bu süzgeçte yükselen coin yok."; }
  const n = L.length, G = L.slice(0, PIY_N), yuk = piyYukNot();
  return `<div class="pkb"><span>${bas}</span>${yuk ? `<span>${yuk}</span>` : ""}</div>
    <div class="pkl">${n ? G.map(o=>piySatir(o, R)).join("") : bos(m + (PIY_SEKME!="izle" && !PIY_ARA && PIY_HACIM > 1e6 ? " Hacim sınırını düşürmeyi dene." : ""))}</div>
    ${n > G.length ? `<button class="pkdaha" onclick="PIY_N+=25;piyasaBoya(true)">Daha fazla göster (${n - G.length})</button>` : ""}`;
}
function piyYukNot(){ return PIY_DONEM != 1 && PIY_GYUK.calis ? `${PIY_DONEM ? "geçmiş" : "gün açılışı"} yükleniyor ${PIY_GYUK.bit}/${PIY_GYUK.bek}` : ""; }
function piyasaSayfa(k){   // madde 866: sade — arama, tek sekme satırı, tek ayar satırı, tek liste
  const SK = [["yuk","Yükselenler"],["dus","Düşenler"],["hac","En çok işlem"],["fund","Funding"],["izle",`★ İzlediklerim${PIY_IZLE.size ? ` ${PIY_IZLE.size}` : ""}`]];
  const donemli = PIY_SEKME=="yuk" || PIY_SEKME=="dus" || PIY_SEKME=="izle";
  const D = ISL_DURUM;
  return `<div class="kart pyk pk2">
    <div class="pkara"><span aria-hidden="true">⌕</span><input id="piyara" type="search" aria-label="Coin ara" placeholder="Coin ara" autocomplete="off" autocapitalize="characters" value="${PIY_ARA}" oninput="piyAra(this.value);piySekmeGoster()">
      <span class="k" id="piyd" role="status"></span></div>
    <div id="piysk" ${PIY_ARA ? "hidden" : ""}>
    <div class="pksek" role="tablist">${SK.map(([v,ad])=>`<button role="tab" aria-selected="${PIY_SEKME==v}" class="${PIY_SEKME==v?"on":""}" onclick="piySekme('${v}')">${ad}</button>`).join("")}</div>
    <div class="pkay">${donemli ? `<div class="pkdon">${[0,1,3,7,30].map(d=>`<button class="${PIY_DONEM==d?"on":""}" onclick="piyDonem(${d})" title="${PIY_DBAS[d]}">${{0:"Bugün",1:"24s",3:"3g",7:"1h",30:"1a"}[d]}</button>`).join("")}</div>` : `<span></span>`}
      ${PIY_SEKME!="izle" ? `<label class="pkhac"><span>hacim ≥</span><select onchange="piyHacim(+this.value)" aria-label="en düşük 24 sa hacim">${[[1e6,"1 M$"],[10e6,"10 M$"],[50e6,"50 M$"],[200e6,"200 M$"]].map(([v,a])=>`<option value="${v}" ${PIY_HACIM==v?"selected":""}>${a}</option>`).join("")}</select></label>` : ""}</div>
    </div>
    <div id="piyic">${piyListe(k)}</div>
    <div class="pknot">Gerçek Binance fiyatları, canlı. ${D && D.acik ? `Coine dokun → <b>al / sat</b> (${D.mod=="live"?"canlı":"demo"} hesap).` : "Coine dokununca Binance'te açılır."} ☆ listesi bu cihazda saklanır.</div>
  </div>`;
}
function piySekme(v){ PIY_SEKME = v; PIY_N = 25; PIY_DEP("carry_piy_sekme", v); if (v=="fund") PIY_MOD = "fund"; else PIY_MOD = "deg"; PIY_DEP("carry_piy_mod", PIY_MOD); ciz(); piyGecmisYukle(); }
function piySekmeGoster(){ const e = $("#piysk"); if (e) e.hidden = !!PIY_ARA; }
// MADDE 851: AL-SAT alanı — Pozisyonlarım (bottan ayrı hesap). Hesap bağlanana kadar (geçiş) bot hesabındaki elle pozisyonlar burada.
function alsatSayfa(k){   // madde 864: tek başlık (üst çubukta Al-Sat); bakiye kartı + pozisyonlar kartı
  const D = ISL_DURUM;
  if (!D) return `<div class="kart"><div class="iskelet" style="height:120px"></div></div><div class="kart"><div class="iskelet" style="height:34px;width:60%"></div><div class="iskelet" style="height:70px;margin-top:14px"></div></div>`;
  const gecis = D.acik && D.gecis ? `<div class="isah bot">Al-sat hesabı henüz bağlanmadı. Taşıma bitene kadar bu pozisyonlar botun hesabında duruyor: <b>yeni pozisyon açılamaz</b>, mevcutları kapatabilir, TP / stop koyabilirsin.</div>` : "";
  return `${gecis}${D.acik ? `<div id="piyelle" class="as-sayfa">${elleHtml()}</div>` : `<div class="kart bos">${D.neden ? ea(D.neden) : "işlem kapalı"}</div>`}`;
}
// MADDE 852: AL-SAT GEÇMİŞİ — günlük kazanç / kayıp çubukları + hesap eğrisi + gün tablosu (ayrı hesap; kapı /gecmis, 60 sn önbellek)
let AS_GEC = null;
async function asGecmisYukle(){
  if (VERI_GOMULU || asGecmisYukle.calis) return; asGecmisYukle.calis = true;
  const once = AS_GEC ? JSON.stringify({...AS_GEC, _t: 0, egri: null}) : null;
  try { const d = await islIstek("gecmis"); AS_GEC = d.ok ? {...d, _t: Date.now()} : {hata: d.hata, _t: Date.now()}; }
  finally { asGecmisYukle.calis = false; }
  // madde 856: değişmediyse çizme; değiştiyse yalnız içerik (kaydırma yeri korunur)
  if (sayfa == "asgecmis" && VERI && !ISL && JSON.stringify({...AS_GEC, _t: 0, egri: null}) !== once){
    const y = scrollY, el = $("#icerik"); if (el) el.innerHTML = asGecmisSayfa(); scrollTo(0, y); }
}
function asEgri(E){
  if (!E || E.length < 2) return `<div class="k">Hesap eğrisi birkaç saat içinde oluşur (özkaynak 5 dk'da bir kaydediliyor).</div>`;
  const W = 600, H = 150, sol = 4, alt = 18, t0 = E[0][0], t1 = E[E.length-1][0], v = E.map(x=>x[1]);
  let lo = Math.min(...v), hi = Math.max(...v); const pad = (hi - lo) * 0.12 || Math.max(1, hi * 0.002); lo -= pad; hi += pad;
  const X = t => sol + (t - t0) / Math.max(1, t1 - t0) * (W - sol * 2), Y = y => (H - alt) - (y - lo) / (hi - lo) * (H - alt - 6);
  const yuk = v[v.length-1] >= v[0], renk = css(yuk ? "--art" : "--eks"), ilk = Y(v[0]);
  const yol = E.map((x,i)=>`${i?"L":"M"}${X(x[0]).toFixed(1)} ${Y(x[1]).toFixed(1)}`).join("");
  const tz = t => new Date(t).toLocaleString("tr-TR", {day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"});
  const hit = E.map((x,i)=>{ const a = i ? (X(E[i-1][0]) + X(x[0])) / 2 : sol, b = i < E.length-1 ? (X(x[0]) + X(E[i+1][0])) / 2 : W - sol;
    return `<rect x="${a.toFixed(1)}" y="0" width="${Math.max(1, b - a).toFixed(1)}" height="${H - alt}" fill="transparent"><title>${tz(x[0])} · ${para(x[1])}</title></rect>`; }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="asg" role="img" aria-label="Al-sat hesap eğrisi">
    <line x1="${sol}" x2="${W - sol}" y1="${ilk.toFixed(1)}" y2="${ilk.toFixed(1)}" stroke="${css("--cizgi")}" stroke-dasharray="3 4"/>
    <path d="${yol}" fill="none" stroke="${renk}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${X(t1).toFixed(1)}" cy="${Y(v[v.length-1]).toFixed(1)}" r="4" fill="${renk}" stroke="${css("--kart")}" stroke-width="2"/>
    <text x="${sol}" y="${H - 4}" class="asgt">${tz(t0)}</text><text x="${W - sol}" y="${H - 4}" class="asgt" text-anchor="end">şimdi</text>${hit}</svg>`;
}
// madde 855: al-sat verisini botun Geçmiş bileşenlerinin beklediği biçime çevirir (seri: tarih / kitap / gün getirisi)
function asK(A){
  const G = A.gunler || [], bugun = G.length ? G[G.length-1].t : null, seri = [], aylik = {};
  if (G.length) seri.push({tarih: new Date(Date.parse(G[0].t + "T00:00:00Z") - 864e5).toISOString().slice(0,10), kitap: A.baslangic});
  let onc = A.baslangic;
  for (const g of G){ seri.push({tarih: g.t, kitap: g.oz, gun: onc > 0 ? g.kz / onc : null, canli: g.t === bugun}); onc = g.oz; }
  for (let i = 1; i < seri.length; i++){ const a = seri[i].tarih.slice(0,7), bas = seri.slice(0, i).reverse().find(x=>x.tarih.slice(0,7) < a);
    const b0 = bas ? bas.kitap : seri[0].kitap; if (b0 > 0) aylik[a] = seri[i].kitap / b0 - 1; }
  return {seri, kitap_canli: null, aylik, coin_ozet: A.coin_ozet || [], mod: (ISL_DURUM||{}).mod, _baslik: "Geçmiş",
          _canliNot: "canlı · gece 03:00'te kesinleşir", _bosMetin: "Al-sat hesabında henüz gün yok."};
}
function asGecmisSayfa(A){   // madde 868: bot Geçmiş'i gibi sade — özet + başlangıçtan beri; takvim / yıl / coinler katlı
  const D = ISL_DURUM;
  if (D && !D.ayri) return `<div class="kart bos">Geçmiş, al-sat ayrı hesabı bağlıyken görünür.</div>`;
  if (!AS_GEC || Date.now() - (AS_GEC._t||0) > 60e3) asGecmisYukle();
  if (!AS_GEC) return `<div class="kart"><div class="iskelet" style="height:34px;width:60%"></div><div class="iskelet" style="height:150px;margin-top:14px"></div></div>`;
  if (AS_GEC.hata) return `<div class="kart bos">${ea(AS_GEC.hata)}</div>`;
  const P = asGecmisParca(A || asGecmisCanliVeri()), ac = ACIK.has("asay"), n = (AS_GEC.coin_ozet||[]).length;
  return `<div id="as-ust">${P.ust}</div><div id="as-oz">${P.oz}</div>
    <div id="as-coin">${P.coin}</div>${P.kap}
    <div class="kart" style="padding:0"><button class="gayr" onclick="olayAc('asay')">${ac?"▾":"▸"} Ayrıntılar <span class="k">takvim · son 1 yıl</span></button></div>
    ${!ac ? "" : `<div class="kart"><h2>Günlük takvim</h2><div id="as-tak">${P.tak}</div>
      <div class="k" style="margin-top:6px">Gün gece 03:00'te başlar · yeşil kazanç, kırmızı kayıp · ● bugün</div></div>
    <div class="kart"><h2>Son 1 yıl</h2>${yillik(asK(A || AS_GEC))}</div>`}`;
}
// MADDE 895: kapanan işlemler — özet (adet, kârlı oranı, ortalama kazanç / kayıp, en iyi / en kötü) + son 8, gerisi dokununca.
// Tutar NET (komisyon dahil); bir emrin parça dolumları tek satır.
function asKapanis(L){
  if (!L.length) return "";
  const ac = ACIK.has("askap"), G = ac ? L : L.slice(0, 8), kaz = L.filter(x=>x.net > 0), kay = L.filter(x=>x.net <= 0);
  const ort = a => a.length ? a.reduce((t,x)=>t+x.net, 0) / a.length : null, T = L.reduce((t,x)=>t+x.net, 0);
  const iyi = L.reduce((p,x)=>x.net>p.net?x:p), kot = L.reduce((p,x)=>x.net<p.net?x:p);
  const tarih = t => { const d = new Date(t), b = new Date(); const g = Math.round((new Date(b.toDateString()) - new Date(d.toDateString()))/864e5);
    return (g==0 ? "bugün" : g==1 ? "dün" : `${d.getDate()} ${AYAD[d.getMonth()].slice(0,3)}`) + " " + d.toLocaleTimeString("tr-TR", {hour:"2-digit", minute:"2-digit"}); };
  const sat = x => `<div class="acr"><span class="acn">${coinIkon(x.s, "kucuk")}<b>${ea(x.s)}</b></span><span class="aca">${tarih(x.t)}${x.n > 1 ? ` · ${x.n} dolum` : ""}${Math.abs(x.net - x.kz) >= 0.005 ? ` · komisyon ${isaretli(x.net - x.kz)}` : ""}</span><b class="act ${sinif(x.net)}">${isaretli(x.net)}</b>${x.not ? `<span class="acnt" role="button" tabindex="0" onclick="this.classList.toggle('acik')">📝 ${ea(x.not)}</span>` : ""}</div>`;
  return `<div class="kart acl"><div class="apkh"><div><b>Kapanan işlemler</b><span class="say">${L.length}</span></div><b class="${sinif(T)}">${isaretli(T)}</b></div>
    <div class="apko"><span class="art">${kaz.length} kârlı</span><span class="eks">${kay.length} zararlı</span><span>%${Math.round(kaz.length / L.length * 100)} isabet · son 90 gün, komisyon dahil</span></div>
    <div class="kpi"><div><span>ort. kazanç</span><b class="art">${ort(kaz)==null ? "—" : isaretli(ort(kaz))}</b></div><div><span>ort. kayıp</span><b class="eks">${ort(kay)==null ? "—" : isaretli(ort(kay))}</b></div>
      <div><span>en iyi</span><b class="${sinif(iyi.net)}">${isaretli(iyi.net)}</b><i>${ea(iyi.s)}</i></div><div><span>en kötü</span><b class="${sinif(kot.net)}">${isaretli(kot.net)}</b><i>${ea(kot.s)}</i></div></div>
    ${G.map(sat).join("")}
    ${L.length > 8 ? `<button class="pkdaha" onclick="olayAc('askap')">${ac ? "Yalnız son 8" : `Tümü (${L.length})`}</button>` : ""}</div>`;
}
// madde 891: kalem çubukları (bot Özet "nereden geldi" ile aynı görünüm): sıfır ortada, kazanç sağa yeşil, kayıp sola kırmızı
function kalemCubuk(K){
  const mx = Math.max(...K.map(x=>Math.abs(x[1])), 1e-9);
  return `<div class="nrd" style="margin-top:12px">${K.map(([a,v])=>{ const w = Math.max(Math.abs(v)/mx*50, Math.abs(v)>=0.005?1.5:0);
    return `<div class="nrr"><span class="nrl">${a}</span><span class="nrb"><i class="${v>=0?"p":"n"}" style="width:${w.toFixed(1)}%"></i></span><b class="${sinif(v)}">${isaretli(v)}</b></div>`; }).join("")}</div>`;
}
function asGecmisParca(A){
  const O = A.ozet || {}, K = asK(A);
  const yzd = v => v==null ? "" : ` (${(v>=0?"+":"−")}%${Math.abs(v*100).toFixed(2).replace(".",",")})`;
  const oz = `<div class="kart"><div class="k">Başlangıçtan beri</div><div class="asb ${sinif(A.toplam)}">${A.toplam>=0?"▲":"▼"}\u00a0${isaretli(A.toplam)}<span class="k">${yzd(A.oran)}</span></div>
    <div class="k" style="margin-top:4px">${para(A.baslangic)} → <b style="color:var(--yazi)">${para(A.ozkaynak)}</b></div>
    ${kalemCubuk([["Kapanan", O.gerceklesen||0], ["Açık", A.acik||0], ["Funding", O.funding||0], ["Komisyon", O.komisyon||0]])}
    <div class="ash">Hesap eğrisi</div>${asEgri(A.egri)}</div>`;
  return {ust: gecmisSade(K), oz, tak: takvim(K), coin: asCoinListe(A.coin_ozet || []), kap: asKapanis(A.kapanislar || [])};
}
// madde 868: coin bazında sonuç — tablo yerine kart satırlar (telefonda 5 sütun sığmıyordu); en kötü / en iyi 4, gerisi dokununca
function asCoinListe(C){
  if (!C.length) return "";
  const ac = ACIK.has("ascoin"), S = C.slice().sort((a,b)=>a.toplam-b.toplam), L = ac || S.length <= 8 ? S : [...S.slice(0,4), ...S.slice(-4)];
  const T = S.reduce((a,x)=>a + x.toplam, 0), kaz = S.filter(x=>x.toplam > 0.005).length;
  const k = v => Math.abs(v) < 0.005 ? "" : `<span class="${sinif(v)}">${isaretli(v)}</span>`;
  const sat = x => { const p = [["kapanan", x.kapanan], ["funding", x.funding], ["komisyon", x.komisyon], ["açık", x.acik]].filter(([,v])=>Math.abs(v) >= 0.005);
    return `<div class="acr"><span class="acn">${coinIkon(x.s, "kucuk")}<b>${ea(x.s)}</b>${x.yon ? `<span class="pkz sen ${x.yon}">${x.yon}</span>` : ""}</span>
      <span class="aca">${p.map(([a,v])=>`<span class="nw">${a} ${k(v)}</span>`).join(" · ") || "—"}</span><b class="act ${sinif(x.toplam)}">${isaretli(x.toplam)}</b></div>`; };
  return `<div class="kart acl"><div class="apkh"><div><b>Coinler</b><span class="say">${S.length}</span></div><b class="${sinif(T)}">${isaretli(T)}</b></div>
    <div class="apko"><span class="art">${kaz} kârda</span><span class="eks">${S.length - kaz} zararda</span><span>başlangıçtan beri, açık pozisyon dahil</span></div>
    ${L.map((x,i)=>(!ac && S.length > 8 && i==4 ? `<div class="acay">· · ·</div>` : "") + sat(x)).join("")}
    ${S.length > 8 ? `<button class="pkdaha" onclick="olayAc('ascoin')">${ac ? "Yalnız en kötü / en iyi 4" : `Tüm coinler (${S.length})`}</button>` : ""}</div>`;
}
// madde 857: Geçmiş CANLI — açık K/Z'yi Pozisyonlarım'ın işaret fiyatı akışıyla yeniden hesaplar (özkaynak = cüzdan + canlı açık K/Z)
function asGecmisCanliVeri(){
  const A = AS_GEC, P = (ELLE_OZ && !ELLE_OZ.hata && ELLE_OZ.pozisyonlar) || null;
  if (!A || A.hata || !P) return A;
  const ac = {}; for (const x of P) ac[x.sembol.replace(/USDT$/,"")] = asKz(x);
  const acik = Object.values(ac).reduce((a,v)=>a+v, 0), fark = acik - (A.acik||0);
  if (Math.abs(fark) < 1e-9) return A;
  const G = (A.gunler||[]).map((g,i,arr)=> i == arr.length-1 ? {...g, kz: g.kz + fark, oz: g.oz + fark} : g);
  const coin = (A.coin_ozet||[]).map(c=>{ const a = ac[c.s] != null ? ac[c.s] : c.acik; return {...c, acik: a, toplam: c.kapanan + c.funding + c.komisyon + a}; }).sort((a,b)=>a.toplam-b.toplam);
  const oz = A.ozkaynak + fark, toplam = A.toplam + fark;
  return {...A, acik, ozkaynak: oz, toplam, oran: A.baslangic > 0 ? toplam / A.baslangic : A.oran, gunler: G, coin_ozet: coin,
          egri: [...(A.egri||[]).slice(0, -1), [Date.now(), oz]]};
}
function asGecmisCanli(){   // 2 sn'de bir: yalnız değişen bölümler (sayfa baştan çizilmez)
  if (sayfa != "asgecmis" || !AS_GEC || AS_GEC.hata || Date.now() - (asGecmisCanli.t||0) < 2000) return;
  asGecmisCanli.t = Date.now();
  const P = asGecmisParca(asGecmisCanliVeri());
  for (const [id, h] of [["as-ust", P.ust], ["as-oz", P.oz], ["as-tak", P.tak], ["as-coin", P.coin]]){ const el = document.getElementById(id); if (el && el.innerHTML !== h) el.innerHTML = h; }
}
// MADDE 839: POZİSYONLARIM — elle yönettiğin açık pozisyonlar (hesabın K/Z'si) + son 30 gün elle sonucu; 15 sn'de bir kapıdan.
let ELLE_OZ = null;
async function elleYukle(){
  if (VERI_GOMULU || !ISL_DURUM || !ISL_DURUM.acik) return;   // madde 844: her sayfada (Pozisyonlar listesi de kullanır)
  elleYukle.t = Date.now(); const d = await islIstek("elle");
  if (!d.ok && d.ag && ELLE_OZ && !ELLE_OZ.hata) ELLE_OZ.baglanti = d.hata;   // madde 887: ağ koptu -> son veriyi tut, üstte uyar
  else ELLE_OZ = d.ok ? d : {hata: d.hata};
  const el = $("#piyelle"); if (el) el.innerHTML = elleHtml();
  if (elleBirlestir() && VERI && sayfa != "piyasa" && !ISL) ciz();
}
// MADDE 844: elle pozisyonlar Pozisyonlar listesinde HEMEN görünsün. Liste 5 dk'lık anlık görüntüden (carry-anlik) gelir; kapının /elle
// yanıtı (15 sn'de bir, canlı) elle coinler için onu ezer: yeni açılan eklenir, kapanan çıkarılır, adet / giriş / K/Z canlı olur.
// Kapı yalnız ana kurulumun hesabına bağlı. Yanıt 90 sn'den eskiyse dokunulmaz. Değişiklik olduysa true.
function elleBirlestir(){
  if (!VERI || !ELLE_OZ || !ELLE_OZ.pozisyonlar || Date.now() - (elleYukle.t||0) > 90e3) return false;
  return false;   // madde 851: al-sat kendi alanında — bot listesine hiç birleştirilmez (bot listesi anlık görüntüden, botun payıyla)
  const K = VERI.kurulumlar || [], k = K.find(x => x.ad == "ana") || K[0]; if (!k) return false;
  const P = k.pozisyonlar = k.pozisyonlar || {}, once = JSON.stringify(P), canli = new Set();
  for (const x of ELLE_OZ.pozisyonlar){
    if (!x.adet) continue;
    const isaret = x.giris + x.kz / x.adet, uzun = x.adet > 0;
    P[x.sembol] = {...(P[x.sembol]||{}), yon: uzun ? "L" : "S", miktar: x.adet, giris: x.giris, isaret, usd: Math.round(Math.abs(x.adet) * isaret * 100) / 100,
                   gerceklesmemis: Math.round(x.kz * 100) / 100, kar_yuzde: x.giris ? Math.round((isaret / x.giris - 1) * (uzun ? 1 : -1) * 1e4) / 100 : 0, elle_canli: true};
    canli.add(x.sembol);
  }
  for (const s of Object.keys(P)) if (!canli.has(s) && elleMi(k, s)) delete P[s];   // elle coin kapandı: görüntü yenilenmeden de listeden çıkar
  return JSON.stringify(P) !== once;
}
// MADDE 843: "kaçtan aldım" — elle pozisyonun senin dolumların ve bottan devralınan kısmı (kapı /elle "pay")
const elleZaman = t => { const d = new Date(t), b = new Date(); const g = d.toDateString()==b.toDateString() ? "bugün" : d.toLocaleDateString("tr-TR",{day:"numeric",month:"short"});
  return g + " " + d.toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"}); };
const elleAdet = q => Math.abs(q).toLocaleString("tr-TR", {maximumFractionDigits: 4});
function elleBul(s){ return ((ELLE_OZ && ELLE_OZ.pozisyonlar) || []).find(x => x.sembol === s); }
function elleKisa(x){   // Pozisyonlarım satırı: "senin 5.963 @ 0,01677 · bottan 8.331 @ 0,01332"
  const P = x.pay, n = (x.parcalar||[]).length;
  if (!P || !P.devralinan) return `${elleAdet(x.adet)} adet @ ${piyFiyat(x.giris)}${n > 1 ? ` <span class="pyn">${n} alım</span>` : ""}`;
  return `senin ${elleAdet(P.benim_adet)}${P.benim_giris?` @ ${piyFiyat(P.benim_giris)}`:""} · bottan ${elleAdet(P.devralinan)}${P.devralinan_giris?` @ ${piyFiyat(P.devralinan_giris)}`:""}`;
}
function ellePayHtml(s, p, f){   // madde 846: sade özet — ne aldın, kaçtan, şu an ne durumda; dolumlar katlanır
  const x = elleBul(s), P = x && x.pay, yon = p.miktar > 0 ? "long" : "short";
  if (!x) { if (ISL_DURUM && ISL_DURUM.acik && Date.now() - (elleYukle.t||0) > 15e3) elleYukle(); return ISL_DURUM && ISL_DURUM.acik ? `<div class="elp k">işlemlerin yükleniyor…</div>` : ""; }
  const sat = (ad, q, g, kz) => { const v = kz != null ? kz : (g && f ? q * (f - g) : null), y = g && f ? (f / g - 1) * (q > 0 ? 1 : -1) * 100 : null;
    return `<div class="elr"><span><b>${ad}</b><br><span class="k">${para(Math.abs(q) * (g || f))} ${yon} · giriş ${g ? fiyatYaz(g) : "bilinmiyor"}</span></span>
      <span class="r">${v == null ? "—" : `<b class="${sinif(v)}">${isaretli(v)}</b>${y == null ? "" : `<br><span class="k">${(y>=0?"+":"−")}%${Math.abs(y).toFixed(1).replace(".",",")}</span>`}`}</span></div>`; };
  const M = x.muhasebe;   // madde 850: botun muhasebesiyle aynı hesap (carry_elle_kz) — devralınan kısım devir anından sonra senin
  if (M){
    const kzc = f && x.adet ? M.kz + (x.adet * f - x.adet * (x.giris + x.kz / x.adet)) : M.kz;   // canlı fiyatla
    const rows = `<div class="elr"><span><b>Senin kâr/zararın</b><br><span class="k">${para(Math.abs(p.miktar) * (f || x.giris))} ${yon} · ${elleZaman(M.bas)} itibarıyla · funding ${isaretli(M.funding)} · komisyon ${isaretli(M.komisyon)}</span></span>
        <span class="r"><b class="${sinif(kzc)}" style="font-size:16px">${isaretli(kzc)}</b></span></div>`
      + (M.q_bot ? `<div class="elr"><span><b>Botun payı</b><br><span class="k">${elleAdet(M.q_bot)} adet${M.e_bot ? ` · giriş ${fiyatYaz(M.e_bot)}` : ""} — botta kalıyor, sana geçmedi. Kapat yalnız SENİN payını kapatır; taşımada bu kısım botun dilimine geri döner.</span></span><span class="r"></span></div>` : "")
      + (x.borsa ? `<div class="elr k" style="border-top:1px solid var(--cizgi);padding-top:6px"><span>Borsada toplam ${elleAdet(x.borsa.adet)} adet (Binance ortalaması ${fiyatYaz(x.borsa.giris)})</span><span class="r ${sinif(x.borsa.kz)}">${isaretli(x.borsa.kz)}</span></div>` : "");
    const koruma2 = `<div class="elr" style="border-top:1px solid var(--cizgi);padding-top:6px"><span class="k">Kâr al · stop</span><span class="r">${x.tp ? `TP ${fiyatYaz(x.tp)}` : "TP yok"} · ${x.sl ? `stop ${fiyatYaz(x.sl)}` : `<b class="uyr">stop yok</b>`}</span></div>`;
    const D2 = (P && P.dolum || []).map(d => `<div class="elr"><span class="k">${elleZaman(d.t)}</span><span class="r"><b class="${d.yon=="AL"?"art":"eks"}">${d.yon}</b> ${para(d.adet * d.fiyat)} · ${fiyatYaz(d.fiyat)}</span></div>`).join("");
    return `<div class="elp">${rows}${koruma2}${D2 ? `<details class="eld"><summary>İşlem geçmişi (${P.dolum.length})</summary>${D2}</details>` : ""}</div>`;
  }
  const ikili = P && P.devralinan && P.benim_adet;
  const govde = ikili
    ? sat("Senin aldığın", P.benim_adet, P.benim_giris) + sat("Bottan gelen", P.devralinan, P.devralinan_giris)
      + `<div class="elr k" style="border-top:1px solid var(--cizgi);padding-top:6px"><span>Toplam (Binance ortalaması ${fiyatYaz(x.giris)})</span><span class="r ${sinif(x.kz)}">${isaretli(x.kz)}</span></div>`
    : sat(P && P.devralinan && !P.benim_adet ? "Bottan gelen" : "Senin pozisyonun", p.miktar, x.giris, x.kz);
  const koruma = `<div class="elr" style="border-top:1px solid var(--cizgi);padding-top:6px"><span class="k">Kâr al · stop</span><span class="r">${x.tp ? `TP ${fiyatYaz(x.tp)}` : "TP yok"} · ${x.sl ? `stop ${fiyatYaz(x.sl)}` : `<b class="uyr">stop yok</b>`}</span></div>`;
  const D = (P && P.dolum || []).map(d => `<div class="elr"><span class="k">${elleZaman(d.t)}</span><span class="r"><b class="${d.yon=="AL"?"art":"eks"}">${d.yon}</b> ${para(d.adet * d.fiyat)} · ${fiyatYaz(d.fiyat)}</span></div>`).join("");
  return `<div class="elp">${govde}${koruma}${D ? `<details class="eld"><summary>İşlem geçmişi (${P.dolum.length})</summary>${D}</details>` : ""}</div>`;
}
// MADDE 856: Al-Sat pozisyonları CANLI — kendi işaret fiyatı akışı (saniyede bir); K/Z = adet × (işaret − giriş) (Binance açık K/Z tanımı)
let AS_WS = null, AS_WSK = "", AS_F = {}, AS_ZAMAN = 0, AS_FR = {};
function asAkisBagla(){
  const S = (ALAN == "alsat" || (RU.acik && (ISL_DURUM||{}).ayri)) && !VERI_GOMULU && window.WebSocket ? ((ELLE_OZ && ELLE_OZ.pozisyonlar) || []).map(x=>x.sembol).sort() : [];   // madde 906: risk uyarısı açıksa her sayfada
  const k = S.join(",");
  if (!S.length){ if (AS_WS){ AS_WS.onclose = null; AS_WS.close(); AS_WS = null; AS_WSK = ""; } return; }
  if (k === AS_WSK && AS_WS && AS_WS.readyState <= 1) return;
  if (AS_WS){ AS_WS.onclose = null; AS_WS.close(); }
  AS_WSK = k; const ws = new WebSocket("wss://fstream.binance.com/market/stream?streams=" + S.map(s=>s.toLowerCase()+"@markPrice@1s").join("/")); AS_WS = ws;
  ws.onmessage = e => { try { const d = JSON.parse(e.data).data; if (d && d.s && +d.p > 0){ AS_F[d.s] = +d.p; AS_ZAMAN = Date.now(); if (d.r != null && d.r !== "" && d.T) AS_FR[d.s] = {r: +d.r, T: +d.T}; } } catch(_){} };
  ws.onclose = () => { if (AS_WS === ws){ AS_WS = null; AS_WSK = ""; setTimeout(asAkisBagla, 4000); } };
}
const asKz = x => { const f = AS_F[x.sembol]; return f > 0 && x.adet && x.giris > 0 ? x.adet * (f - x.giris) : x.kz; };
function asCanliBoya(){   // canliBoya her saniye: Pozisyonlarım satırları + üstteki hesap değeri
  if (ALAN != "alsat" || !ELLE_OZ || !ELLE_OZ.pozisyonlar) return;
  asAkisBagla();
  if (sayfa == "alsat"){   // yalnız rakamlar yerinde (her saniye listeyi baştan çizmek dokunuşu kaçırtırdı)
    const tmp = document.createElement("div"); tmp.innerHTML = elleHtml();
    for (const id of ["astop", "asbak", ...(Date.now() - AS_RK_T > 1500 ? ["asrk"] : []), ...ELLE_OZ.pozisyonlar.flatMap(x=>["askz-" + x.sembol, "ass-" + x.sembol, "asnet-" + x.sembol])]){
      const a = document.getElementById(id), b = tmp.querySelector("#" + CSS.escape(id));
      if (a && b && a.innerHTML !== b.innerHTML){ a.innerHTML = b.innerHTML; a.className = b.className; } } }
  const H = ELLE_OZ.hesap, u = $("#ustkitap");
  asGecmisCanli();   // madde 857
  if (u && H && H.ozkaynak != null){ const fark = ELLE_OZ.pozisyonlar.reduce((a,x)=>a + asKz(x) - x.kz, 0); u.innerHTML = `<span>${para(H.ozkaynak + fark)}</span>`; }
}
// MADDE 860: Al-Sat bakiye özeti — toplam bakiye (özkaynak), pozisyonlara bağlı teminat (+ toplam pozisyon büyüklüğü), boşta bakiye.
// Açık K/Z işaret fiyatı akışıyla canlı: özkaynak ve boşta bakiye canlı K/Z farkı kadar kayar (Binance'te kullanılabilir bakiye de açık K/Z'yi içerir).
function asBakiye(E, P){   // madde 861: görsel — halka (pozisyonlarda / boşta) + büyük bakiye + açıklamalı satırlar
  const H = E && E.hesap; if (!H || H.ozkaynak == null) return "";
  const fark = P.reduce((a,x)=>a + x.kz, 0) - (E.pozisyonlar||[]).reduce((a,x)=>a + x.kz, 0);
  const oz = H.ozkaynak + fark, acik = (H.acik||0) + fark, tem = (H.teminat||0) + (H.emir_teminat||0);
  const bos = H.bosta != null ? Math.max(0, H.bosta + fark) : Math.max(0, oz - tem);
  const pay = tem + bos > 0 ? tem / (tem + bos) : 0, yz = v => "%" + Math.round(v * 100);
  const R = 42, C = 2 * Math.PI * R, d = pay * C, kal = oz > 0 && H.buyukluk ? H.buyukluk / oz : null;
  const renkT = pay > 0.8 ? "var(--eks)" : pay > 0.6 ? "var(--uyari)" : "var(--vurgu)";
  const halka = `<svg viewBox="0 0 100 100" class="abh" role="img" aria-label="Bakiyenin ${yz(pay)} pozisyonlarda">
    <circle cx="50" cy="50" r="${R}" fill="none" stroke="var(--art)" stroke-opacity=".85" stroke-width="11"/>
    ${pay > 0 ? `<circle cx="50" cy="50" r="${R}" fill="none" stroke="${renkT}" stroke-width="11" stroke-dasharray="${d.toFixed(2)} ${(C - d).toFixed(2)}" transform="rotate(-90 50 50)" stroke-linecap="${pay < 0.995 ? "butt" : "round"}"/>` : ""}
    <text x="50" y="49" text-anchor="middle" class="abh1">${yz(pay)}</text><text x="50" y="64" text-anchor="middle" class="abh2">kullanımda</text></svg>`;
  const satir = (renk, ad, v, alt) => `<div class="abs"><i style="background:${renk}"></i><span>${ad}<small>${alt}</small></span><b>${para(v)}</b></div>`;
  return `<div class="asbak kart" id="asbak">${halka}<div class="abk">
      <div class="abu">Toplam bakiye</div><div class="abt">${para(oz)}</div>
      <div class="abkz ${sinif(acik)}">${acik>=0?"▲":"▼"}\u00a0${isaretli(acik)} <span>açık K/Z${H.cuzdan != null ? ` · cüzdan ${para(H.cuzdan)}` : ""}</span></div>
    </div><div class="abr">
      ${satir(renkT, "Pozisyonlarda", tem, yz(pay) + " · teminat")}
      ${satir("var(--art)", "Boşta", bos, yz(1 - pay) + " · yeni işleme hazır")}
    </div>
    ${asDenge(P)}
    ${asFunding(P)}
    <div class="abc">${H.buyukluk ? `<span>büyüklük ${para(H.buyukluk)}</span>` : ""}${kal != null ? `<span>kaldıraç ${kal.toFixed(2).replace(".",",")}x</span>` : ""}</div></div>`;
}
// MADDE 896: Al-Sat sıradaki funding — işaret akışındaki oran (r) ve ödeme zamanı (T); en yakın ödeme anındaki coinlerin toplamı
// (+ alırsın / − ödersin = −adet × işaret × oran) ve 24 saatlik tahmin (her coin kendi ödeme sıklığıyla, oran sabit varsayılır).
function asFunding(P){
  const L = (P||[]).map(x=>({x, F: AS_FR[x.sembol], f: AS_F[x.sembol]})).filter(o=>o.F && o.f > 0 && o.x.adet);
  if (!L.length) return "";
  const T0 = Math.min(...L.map(o=>o.F.T)), S = L.filter(o=>Math.abs(o.F.T - T0) < 60e3);
  const tut = o => -o.x.adet * o.f * o.F.r, sira = S.reduce((a,o)=>a + tut(o), 0);
  const kal = Math.max(0, T0 - Date.now()), sa = Math.floor(kal / 3600e3), dk = Math.floor(kal % 3600e3 / 60e3);
  if (!FON_ARA) fonAraYukle();
  const gun = L.reduce((a,o)=>a + tut(o) * 24 / ((FON_ARA||{})[o.x.sembol] || 8), 0);
  const ac = ACIK.has("asfn"), gunT = o => tut(o) * 24 / ((FON_ARA||{})[o.x.sembol] || 8);
  const liste = !ac ? "" : `<div class="asfl">${L.slice().sort((a,b)=>gunT(a)-gunT(b)).map(o=>{ const ad = o.x.sembol.replace(/USDT$/,""), ara = (FON_ARA||{})[o.x.sembol] || 8;
      return `<div>${coinIkon(ad, "kucuk")}<span><b>${ea(ad)}</b><span class="k">${o.F.r < 0 ? "−" : ""}%${Math.abs(o.F.r*100).toFixed(4).replace(".",",")} · ${ara} sa'de bir · ${new Date(o.F.T).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"})}</span></span><span class="asfr"><b class="${sinif(tut(o))}">${isaretli(tut(o))}</b><span class="k">günde ${isaretli(gunT(o))}</span></span></div>`; }).join("")}</div>`;
  return `<div class="asfn" role="button" tabindex="0" aria-expanded="${ac}" onclick="olayAc('asfn')"><span>Sıradaki funding <span class="k">· ${sa ? sa + " sa " : ""}${dk} dk sonra · ${S.length} coin</span></span><b class="${sinif(sira)}">${sira>=0?"alırsın":"ödersin"} ${isaretli(sira)}</b>
    <span class="k" style="grid-column:1/-1">gerçek piyasanın şu anki oranlarıyla 24 saatte ≈ <b class="${sinif(gun)}">${isaretli(gun)}</b>${FON_ARA ? "" : " (ödeme aralıkları yükleniyor)"} · <span style="color:var(--vurgu)">${ac ? "▾ gizle" : "▸ coin coin"}</span></span>${liste}</div>`;
}
// ödeme aralığı: /fapi/v1/fundingInfo yalnız 8 saatten farklı olanları listeler (1 / 4 sa); günde bir kez
let FON_ARA = null;
async function fonAraYukle(){ if (fonAraYukle.y || VERI_GOMULU) return; fonAraYukle.y = true;
  try { const d = await (await fetch("https://fapi.binance.com/fapi/v1/fundingInfo", {cache:"no-store"})).json();
    const m = {}; if (Array.isArray(d)) for (const x of d) if (x.symbol && +x.fundingIntervalHours > 0) m[x.symbol] = +x.fundingIntervalHours; FON_ARA = m; }
  catch(_){ setTimeout(()=>{ fonAraYukle.y = false; }, 60e3); } }
// MADDE 898: Al-Sat RİSK / SENARYO — "piyasa %X yükselirse / düşerse ne olur", hesabın kaç %'lik ortak harekette likide olacağı,
// coin coin likidasyon uzaklığı ve o coin tek başına %X ters giderse kayıp. Bakım teminatı (MM) borsanın verdiği likidasyon fiyatlarından
// tahmin edilir: çapraz teminatta her coinin likidasyon fiyatı "diğerleri sabitken özkaynak = MM" noktasıdır -> MM ≈ öz + adet × (lik − fiyat);
// coinlerin medyanı alınır, harekette pozisyon büyüklüğüyle orantılı büyür. Tahmindir: funding, kademeli MM oranları ve demo/gerçek farkı yok sayılır.
let AS_SEN = (()=>{ try { return +localStorage.getItem("carry_as_sen") || 25; } catch(_){ return 25; } })(), AS_RK_T = 0;
function asSen(v){ AS_SEN = v; AS_RK_T = 0; try { localStorage.setItem("carry_as_sen", v); } catch(_){} ciz(); }
function asRiskHesap(oz, P){
  const L = P.filter(x=>x.adet).map(x=>({x, f: AS_F[x.sembol] > 0 ? AS_F[x.sembol] : x.giris + (x.adet ? x.kz / x.adet : 0)})).filter(o=>o.f > 0);
  const A = L.reduce((a,o)=>a + o.x.adet * o.f, 0), N = L.reduce((a,o)=>a + Math.abs(o.x.adet) * o.f, 0);
  const mmL = L.filter(o=>o.x.likidasyon > 0).map(o=>oz + o.x.adet * (o.x.likidasyon - o.f)).filter(v=>v >= 0 && v < oz).sort((a,b)=>a-b);
  const MM = mmL.length ? mmL[Math.floor(mmL.length / 2)] : 0, m = N > 0 ? MM / N : 0;
  const ozR = r => oz + A * r, mmR = r => m * L.reduce((a,o)=>a + Math.abs(o.x.adet) * o.f * Math.max(0, 1 + r), 0);
  const esik = yon => {   // yon +1 yükseliş, -1 düşüş; ilk likide olunan oran (en çok %500 / %99)
    const ust = yon > 0 ? 5 : 0.99, olur = r => ozR(yon * r) <= mmR(yon * r);
    if (!olur(ust)) return null; let a = 0, b = ust;
    for (let i = 0; i < 40; i++){ const c = (a + b) / 2; olur(c) ? b = c : a = c; } return b; };
  return {L, A, N, MM, m, ozR, mmR, yuk: esik(1), dus: esik(-1)};
}
function asRisk(E, P){
  const H = E && E.hesap; if (!H || H.ozkaynak == null || !P || !P.length) return "";
  const fark = P.reduce((a,x)=>a + x.kz, 0) - (E.pozisyonlar||[]).reduce((a,x)=>a + x.kz, 0), oz = H.ozkaynak + fark;
  const R = asRiskHesap(oz, P); if (!R.L.length) return "";
  const X = AS_SEN / 100, kYuk = R.A * X, kDus = -R.A * X, ac = ACIK.has("asrk"), yz = v => "%" + Math.round(v * 100);
  const tehlike = R.A < 0 ? {ad: "yükselirse", k: kYuk, e: R.yuk, r: X} : {ad: "düşerse", k: kDus, e: R.dus, r: -X};
  const esikMetin = tehlike.e != null ? `hesap ≈ ${yz(tehlike.e)} ${R.A < 0 ? "yükselişte" : "düşüşte"} likide olur` : "ortak harekette likidasyon görünmüyor";
  const lik = o => o.x.likidasyon > 0 ? Math.abs(o.x.likidasyon / o.f - 1) : null;
  const yakin = R.L.filter(o=>lik(o) != null).sort((a,b)=>lik(a) - lik(b))[0];
  const ozet = `<div class="asrkh" role="button" tabindex="0" aria-expanded="${ac}" onclick="olayAc('asrk')"><span><b>Ne olur?</b> <span class="k">· piyasa %${AS_SEN} ${tehlike.ad}</span></span><b class="${sinif(tehlike.k)}">${isaretli(tehlike.k)}</b>
    <span class="k" style="grid-column:1/-1">${esikMetin}${yakin ? ` · likidasyona en yakın ${ea(yakin.x.sembol.replace(/USDT$/,""))} ${yz(lik(yakin))} uzak` : ""} · <span style="color:var(--vurgu)">${ac ? "▾ gizle" : "▸ ayrıntı"}</span></span></div>`;
  if (!ac) return `<div class="kart asrk" id="asrk" onpointerdown="AS_RK_T=Date.now()">${ozet}</div>`;
  const sat = (ad, k, r) => { const o2 = R.ozR(r), lk = o2 <= R.mmR(r);
    return `<div class="asrs"><span>Piyasa %${AS_SEN} ${ad}</span><b class="${sinif(k)}">${isaretli(k)}</b><span class="k">bakiye ${para(oz)} → <b class="${lk ? "eks" : ""}">${lk ? "likide olur" : para(o2)}</b></span></div>`; };
  const tek = o => -Math.abs(o.x.adet) * o.f * X;
  const liste = R.L.slice().sort((a,b)=>(lik(a) ?? 9e9) - (lik(b) ?? 9e9)).map(o=>{ const ad = o.x.sembol.replace(/USDT$/,""), u = lik(o), uz = o.x.adet > 0;
    return `<div>${coinIkon(ad, "kucuk")}<span><b>${ea(ad)} <span class="pkz sen ${uz?"L":"S"}">${uz?"L":"S"}</span></b><span class="k">${u != null ? `likidasyon ${piyFiyat(o.x.likidasyon)} · <b class="${u < 0.15 ? "eks" : u < 0.4 ? "uy" : ""}">${yz(u)} ${uz ? "aşağıda" : "yukarıda"}</b>` : "likidasyon yok"}</span></span>
      <span class="asfr"><b class="eks">${isaretli(tek(o))}</b><span class="k">tek başına %${AS_SEN} ters</span></span></div>`; }).join("");
  return `<div class="kart asrk" id="asrk" onpointerdown="AS_RK_T=Date.now()">${ozet}
    <div class="tsor asrc" role="group" aria-label="Hareket büyüklüğü">${[10,25,50,100].map(v=>`<button class="${AS_SEN==v?"on":""}" aria-pressed="${AS_SEN==v}" onclick="asSen(${v})">%${v}</button>`).join("")}</div>
    ${sat("yükselirse", kYuk, X)}${sat("düşerse", kDus, -X)}
    <div class="asfl">${liste}</div>
    <p class="k" style="margin:10px 2px 0;line-height:1.45">Tahmin: tüm coinler aynı oranda hareket eder varsayılır; bakım teminatı borsanın likidasyon fiyatlarından çıkarıldı (≈\u00a0${para(R.MM)}). Funding, komisyon ve kayma dahil değil. Coin satırındaki likidasyon fiyatı diğer coinler yerinde kalırsa geçerlidir.</p></div>`;
}
// madde 883: Al-Sat long / short dengesi (Bot Özet'teki çubuğun aynısı) — bakiye kartının altında
function asDenge(P){
  if (!P || !P.length) return "";
  let L = 0, S = 0, nl = 0, ns = 0;
  for (const x of P){ const f = AS_F[x.sembol] > 0 ? AS_F[x.sembol] : x.giris + (x.adet ? x.kz / x.adet : 0), v = Math.abs(x.adet) * (f || 0); if (x.adet > 0){ L += v; nl++; } else { S += v; ns++; } }
  const T = L + S || 1;
  return `<div class="opz asdg" id="asdg"><div class="opzb"><i class="l" style="flex:${L.toFixed(2)}"></i><i class="s" style="flex:${S.toFixed(2)}"></i></div>
    <div class="opzl"><span><i class="l"></i>Long ${nl} · <b>${para(L)}</b></span><span>Short ${ns} · <b>${para(S)}</b><i class="s"></i></span></div>
    <div class="k" style="margin-top:4px;font-size:12px">net ${L>=S?"long":"short"} ${para(Math.abs(L - S))} (%${Math.round(Math.abs(L - S) / T * 100)})</div></div>`;
}
// MADDE 884: TOPLU STOP — stopsuz pozisyonlara tek seferde stop. Oran şimdiki işaret fiyatından (short'ta üstüne, long'da altına);
// mevcut TP korunur (tpsl ucuna TP de gönderilir). PIN + basılı tut; coin coin sırayla /tpsl, her satırda sonuç. Yeni uç yok.
let TS = null;
function tsAc(){
  const E = ELLE_OZ; if (!E || E.hata) return;
  const P = (E.pozisyonlar||[]).filter(x=>x.adet);
  const stopVar = x => !!x.sl || !!x.iz || (x.parca_sl && x.parca_sl >= (x.parcalar||[]).length);
  TS = {oran: 10, pin: "", sec: new Set(P.filter(x=>!stopVar(x)).map(x=>x.sembol)), P, stopVar, sonuc: {}, mesgul: false, bitti: false};
  const el = $("#sheet"); el.hidden = false;
  el.innerHTML = `<div class="shb" onclick="tsKapat()"></div><div class="shp isl" role="dialog" aria-modal="true" tabindex="-1" aria-label="Toplu stop"><div class="shh"></div><div id="tsic"></div></div>`;
  document.body.style.overflow = "hidden"; tsCiz();
}
function tsKapat(){ TS = null; const el = $("#sheet"); el.hidden = true; el.innerHTML = ""; document.body.style.overflow = ""; elleYukle(); }
function tsFiyat(x){ return AS_F[x.sembol] > 0 ? AS_F[x.sembol] : x.giris + (x.adet ? x.kz / x.adet : 0); }
function tsStop(x){ const f = tsFiyat(x), o = TS.oran / 100; return +(f * (x.adet > 0 ? 1 - o : 1 + o)).toPrecision(6); }
function tsKayip(x){ return (tsStop(x) - x.giris) * x.adet; }   // girişe göre tetiklenince gerçekleşecek K/Z
function tsOran(v){ v = parseFloat(String(v).replace(",", ".")); if (!(v > 0) || v > 50) return; TS.oran = v; tsCiz(); }
function tsSec(s){ if (TS.mesgul || TS.bitti) return; TS.sec.has(s) ? TS.sec.delete(s) : TS.sec.add(s); tsCiz(); }
function tsCiz(){
  const el = $("#tsic"); if (!el || !TS) return;
  const L = TS.P.slice().sort((a,b)=>(TS.sec.has(b.sembol)?1:0)-(TS.sec.has(a.sembol)?1:0) || Math.abs(b.adet*b.giris)-Math.abs(a.adet*a.giris));
  const S = L.filter(x=>TS.sec.has(x.sembol)), top = S.reduce((a,x)=>a+tsKayip(x), 0);
  const satir = x => { const s = x.sembol, ad = s.replace(/USDT$/,""), on = TS.sec.has(s), uz = x.adet > 0, R = TS.sonuc[s];
    const durum = R ? (R.ok ? `<span class="tsok">✓ kuruldu</span>` : `<span class="tshat">${ea(R.hata||"hata")}</span>`) : TS.stopVar(x) ? `<span class="k">stop var${x.sl ? " " + piyFiyat(x.sl) : " (alımlarda)"}</span>` : "";
    return `<button class="tsr ${on?"on":""}" onclick="tsSec('${s}')" aria-pressed="${on}" ${TS.mesgul||TS.bitti?"disabled":""}>
      <span class="tsc">${on?"✓":""}</span>${coinIkon(ad, "kucuk")}
      <span class="tsm"><b>${ea(ad)} <span class="pkz sen ${uz?"L":"S"}">${uz?"L":"S"}</span></b><span class="k">${piyFiyat(tsFiyat(x))} → <b>${on ? piyFiyat(tsStop(x)) : "—"}</b>${x.tp ? ` · TP ${piyFiyat(x.tp)} korunur` : ""}</span>${durum}</span>
      <span class="tsk ${on ? sinif(tsKayip(x)) : ""}">${on ? isaretli(tsKayip(x)) : ""}</span></button>`; };
  const n = S.length, gonder = TS.bitti ? "" : `<label class="ibas" for="tspin" style="margin-top:14px">İşlem PIN'i</label><input id="tspin" type="password" inputmode="numeric" autocomplete="off" value="${ea(TS.pin)}" oninput="TS.pin=this.value" placeholder="sunucuda belirlediğin PIN" ${TS.mesgul?"disabled":""}>`;
  el.innerHTML = `<div class="ihd"><div><div style="font-size:19px;font-weight:750">Toplu stop</div><div class="k">${TS.P.length} pozisyon · ${n} seçili</div></div><button class="shx" onclick="tsKapat()" aria-label="Kapat">✕</button></div>
    <div class="ibas" style="margin-top:14px">Stop mesafesi <span class="k">şimdiki fiyattan · short'ta üstüne, long'da altına</span></div>
    <div class="tsor">${[3,5,8,10,15,20].map(v=>`<button class="${TS.oran==v?"on":""}" onclick="tsOran(${v})" ${TS.mesgul||TS.bitti?"disabled":""}>%${v}</button>`).join("")}<input aria-label="özel oran (%)" inputmode="decimal" placeholder="%" value="${[3,5,8,10,15,20].includes(TS.oran) ? "" : islGos(TS.oran)}" onchange="tsOran(this.value)" ${TS.mesgul||TS.bitti?"disabled":""}></div>
    <div class="tsoz"><span>${n} stop tetiklenirse (girişe göre)</span><b class="${sinif(top)}">${n ? isaretli(top) : "—"}</b></div>
    <div class="tsl">${L.map(satir).join("")}</div>
    <p class="k" style="margin:10px 2px 0;line-height:1.45">Stop işaret fiyatına bağlı STOP_MARKET emridir; tetiklenince pozisyonun tamamı piyasadan kapanır. Varsa pozisyon TP'si yerinde kalır; alımlara ayrı koyduğun TP / stop'lara dokunulmaz.</p>
    ${TS.msj ? `<div class="imsj ${TS.msj.ok?"ok":"hata"}" role="status">${ea(TS.msj.ok||TS.msj.hata)}</div>` : ""}
    ${gonder}
    <div class="ialt">${TS.bitti ? `<button class="ibtn" onclick="tsKapat()">Kapat</button>`
      : `<button id="tstut" class="ibtn tut tehlike" ${TS.mesgul||!n?"disabled":""} onpointerdown="tsTutBasla(event)" onpointerup="tsTutBirak()" onpointerleave="tsTutBirak()" onpointercancel="tsTutBirak()" onkeydown="if(event.key==' '||event.key=='Enter')tsTutBasla(event)" onkeyup="tsTutBirak()" oncontextmenu="return false"><span>${TS.mesgul ? `Kuruluyor… ${Object.keys(TS.sonuc).length}/${n}` : n ? `Basılı tut: ${n} stop kur` : "Coin seç"}</span></button>`}</div>`;
}
let TS_TUT = null;
function tsTutBasla(e){ if (!TS || TS.mesgul || TS_TUT || !TS.sec.size) return; if (e && e.type=="keydown" && e.repeat) return; if (e && e.cancelable) e.preventDefault();
  const b = $("#tstut"); if (!b) return; b.classList.add("dolu");
  TS_TUT = setTimeout(()=>{ TS_TUT = null; b.classList.remove("dolu"); try { navigator.vibrate && navigator.vibrate(18); } catch(_){} tsGonder(); }, 700); }
function tsTutBirak(){ if (!TS_TUT) return; clearTimeout(TS_TUT); TS_TUT = null; const b = $("#tstut"); if (b) b.classList.remove("dolu"); }
async function tsGonder(){
  if (!TS || TS.mesgul) return;
  if (String(TS.pin).length < 6){ TS.msj = {hata: "İşlem PIN'ini gir."}; tsCiz(); const p = $("#tspin"); if (p) p.focus(); return; }
  TS.mesgul = true; TS.msj = null; TS.sonuc = {}; tsCiz();
  const S = TS.P.filter(x=>TS.sec.has(x.sembol));
  for (const x of S){ if (!TS) return;
    const d = await islIstek("tpsl", {sembol: x.sembol, tp: x.tp || "", sl: tsStop(x), pin: TS.pin});
    if (!TS) return; TS.sonuc[x.sembol] = d.ok ? {ok: true} : {hata: d.hata};
    if (!d.ok && (d.ag || /PIN/i.test(d.hata||""))) break;   // yanlış PIN ya da bağlantı koptu: kalanları deneme
    tsCiz(); }
  const ok = Object.values(TS.sonuc).filter(v=>v.ok).length, hat = Object.keys(TS.sonuc).length - ok;
  TS.mesgul = false; TS.bitti = ok > 0;
  TS.msj = hat ? {hata: `${ok} stop kuruldu, ${hat} coinde hata (satırlarda).`} : {ok: `${ok} stop kuruldu.`};
  tsCiz();
}
addEventListener("keydown", e=>{ if (e.key === "Escape" && TS && !TS.mesgul) tsKapat(); });
// MADDE 902: pozisyonun gerçek sonucu = fiyat K/Z (canlı) + açıldığından beri funding + komisyon + kısmi kapanışlarda gerçekleşen
const asNet = x => x.kz + (x.gelir ? x.gelir.fon + x.gelir.kom + x.gelir.gercek : 0);
// MADDE 905: Pozisyonlarım sıralaması (bu tarayıcıda hatırlanır). Canlı rakamlar yerinde güncellenir; sıra liste yeniden çizilince (≈15 sn) yenilenir.
const AS_SIRALAR = [["zarar", "En çok zarar"], ["kar", "En çok kâr"], ["buyuk", "En büyük"], ["lik", "Likidasyona yakın"], ["fon", "En çok funding ödeyen"], ["yeni", "En yeni"], ["ad", "Ada göre"]];
let AS_SIRA = (()=>{ try { const v = localStorage.getItem("carry_as_sira"); return AS_SIRALAR.some(x=>x[0]==v) ? v : "zarar"; } catch(_){ return "zarar"; } })();
function asSiraSec(v){ AS_SIRA = v; try { localStorage.setItem("carry_as_sira", v); } catch(_){} ciz(); }
function asSirala(P){
  const f = x => AS_F[x.sembol] > 0 ? AS_F[x.sembol] : x.giris + (x.adet ? x.kz / x.adet : 0);
  const lik = x => x.likidasyon > 0 && f(x) > 0 ? Math.abs(x.likidasyon / f(x) - 1) : 9e9;
  const yeni = x => Math.max(0, ...(x.parcalar||[]).map(p=>p.t||0), (x.gelir||{}).t || 0);
  const K = {zarar: x => x.kz, kar: x => -x.kz, buyuk: x => -Math.abs(x.adet) * f(x), lik, fon: x => (x.gelir||{}).fon ?? 0, yeni: x => -yeni(x)}[AS_SIRA];
  return P.slice().sort(K ? (a,b)=>K(a) - K(b) || a.sembol.localeCompare(b.sembol) : (a,b)=>a.sembol.localeCompare(b.sembol));
}
function asSiraHtml(){
  return `<div class="assr"><label for="assira" class="k">Sırala</label><select id="assira" onchange="asSiraSec(this.value)">${AS_SIRALAR.map(([k,a])=>`<option value="${k}" ${AS_SIRA==k?"selected":""}>${a}</option>`).join("")}</select></div>`;
}
function elleHtml(){   // madde 864: yeniden tasarım — özet şerit, tek stop uyarısı, iki satırlı pozisyon kartları
  const E = ELLE_OZ, yuk = `<div class="kart apk"><div class="apkh"><b>Açık pozisyonlar</b></div>`;
  if (!E) return yuk + `<div class="iskelet" style="height:56px;margin-top:10px"></div><div class="iskelet" style="height:56px;margin-top:8px"></div></div>`;
  if (E.hata) return yuk + `<div class="imsj hata" style="margin-top:10px">${ea(E.hata)}</div></div>`;
  const S = E.sonuc || {}, P = (E.pozisyonlar || []).map(x=>({...x, kz: asKz(x)})), top = P.reduce((a,x)=>a + x.kz, 0);   // madde 856: canlı
  const kar = P.filter(x=>x.kz >= 0).length, stopsuz = P.filter(x=>!x.sl && !x.iz && !(x.parca_sl >= (x.parcalar||[]).length && x.parca_sl)).length;
  const stopsuzHepsi = stopsuz === P.length;   // hepsinde yoksa satır rozeti tekrar etmesin, tek uyarı yeter
  const sonuc = S.kapanis ? `son 30 gün <b class="${sinif(S.net)}">${isaretli(S.net)}</b> · ${S.kapanis} kapanış · %${Math.round(S.kazanan / S.kapanis * 100)} kârlı` : "son 30 günde kapanan işlem yok";
  const satir = x => { const ad = x.sembol.replace(/USDT$/,""), uz = x.adet > 0, f = AS_F[x.sembol] > 0 ? AS_F[x.sembol] : x.giris + (x.adet ? x.kz / x.adet : 0);
    const deger = Math.abs(x.adet) * (f || x.giris), kp = x.giris > 0 ? x.kz / (Math.abs(x.adet) * x.giris) * 100 : 0, n = (x.parcalar||[]).length;
    const stopVar = x.sl || x.parca_sl || x.iz, tpsl = [x.tp ? `TP ${piyFiyat(x.tp)}` : x.parca_tp ? `TP ${x.parca_tp}/${n} alım` : "", x.sl ? `stop ${piyFiyat(x.sl)}` : x.parca_sl ? `stop ${x.parca_sl}/${n} alım` : "", x.iz ? `iz süren %${islGos(x.iz)}` : ""].filter(Boolean);
    return `<a class="apr" href="#piyasa" onclick="islAc('${x.sembol}');return false"><i class="ass ${sinif(x.kz)}" id="ass-${x.sembol}"></i>
      <span class="apik">${coinIkon(ad)}<span class="iyon2 ${uz?"L":"S"}">${uz?"L":"S"}</span></span>
      <span class="aprm"><span class="aprt"><b>${ad}</b>${n > 1 ? `<span class="pyn">${n} alım</span>` : ""}${x.not ? `<span class="apn" title="${ea(x.not)}" aria-label="not var">📝</span>` : ""}${stopVar || stopsuzHepsi ? "" : `<span class="aps" title="stop yok">stop yok</span>`}</span>
        <span class="k2">${x.pay && x.pay.devralinan ? `${elleKisa(x)}` : `<span class="nw">${para(deger)}</span> · <span class="nw">${elleAdet(x.adet)} @ ${piyFiyat(x.giris)}</span>`}</span>${tpsl.length ? `<span class="aptp">${tpsl.join(" · ")}</span>` : ""}${x.gelir && Math.abs(x.gelir.fon) >= 0.01 ? `<span class="apfn"><span class="nw">funding <b class="${sinif(x.gelir.fon)}">${isaretli(x.gelir.fon)}</b></span> · <span class="nw">net <b class="${sinif(asNet(x))}" id="asnet-${x.sembol}">${isaretli(asNet(x))}</b></span></span>` : ""}</span>
      <span class="aprk ${sinif(x.kz)}" id="askz-${x.sembol}"><b>${x.kz>=0?"▲":"▼"}\u00a0${isaretli(x.kz)}</b><span>${(kp>=0?"+":"")+kp.toFixed(1).replace(".",",")+"%"}</span></span></a>`; };
  return `${E.baglanti ? `<div class="imsj hata" role="status" style="margin:8px 0">⚠ Bağlantı yok — gösterilenler son alınan veriler. ${ea(E.baglanti.split(".")[0])}.</div>` : ""}${asBakiye(E, P)}${asRisk(E, P)}<div class="kart apk"><div class="apkh"><div><b>Açık pozisyonlar</b>${P.length ? `<span class="say">${P.length}</span>` : ""}</div>${P.length ? `<b id="astop" class="${sinif(top)}">${top>=0?"▲":"▼"}\u00a0${isaretli(top)}</b>` : ""}</div>
    ${P.length ? `<div class="apko"><span class="art">${kar} kârda</span><span class="eks">${P.length - kar} zararda</span><span>${sonuc}</span></div>` : `<div class="apko"><span>${sonuc}</span></div>`}
    ${stopsuz ? `<div class="apuy">⚠ <span><b>${stopsuz === P.length ? `Hiçbir pozisyonda` : `${stopsuz} pozisyonda`} stop yok.</b> Coine dokunup tek tek ya da hepsine birden koyabilirsin.</span><button class="apub" onclick="tsAc()">Toplu stop koy</button></div>` : ""}
    ${P.length > 2 ? asSiraHtml() : ""}
    <div class="apl">${P.length ? asSirala(P).map(satir).join("") : `<div class="pybos">Açık pozisyonun yok. Piyasadan bir coin seçip işlem açabilirsin.</div>`}</div>
    ${ISL_DURUM && ISL_DURUM.acik && !ISL_DURUM.gecis ? `<button class="elkb" onclick="sayfaSec('piyasa')">＋ Piyasadan coin seç · al / sat</button>` : ""}</div>${asAlarmHtml()}`;
}
function piyasaBoya(zorla){
  if (sayfa!="piyasa") return;
  if (ISL_DURUM && ISL_DURUM.acik && Date.now() - (elleYukle.t||0) > 15e3) elleYukle();
  if (PIY_DONEM != 1 && Date.now() - (piyasaBoya.g||0) > 60e3){ piyasaBoya.g = Date.now(); setTimeout(piyGecmisYukle, 0); }   // 30 dk'yı geçen önbellek yenilenir
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
let ISL_DURUM = null, ISL = null, ISL_SEM = null;   // ISL_SEM: hesapta işlem gören sözleşmeler (madde 847)
const islYok = s => !!(ISL_SEM && !ISL_SEM.has(s));
const ea = v => String(v==null?"":v).replace(/[&"<>']/g, c=>({"&":"&amp;",'"':"&quot;","<":"&lt;",">":"&gt;","'":"&#39;"}[c]));
async function islDurum(){
  if (VERI_GOMULU) return;
  try { const r = await fetch("api/islem/durum", {cache:"no-store"}); const d = await r.json(); ISL_DURUM = d && d.ok ? d : {acik:false, neden: d && d.hata};
    ISL_SEM = ISL_DURUM.semboller && ISL_DURUM.semboller.length ? new Set(ISL_DURUM.semboller) : null; }
  catch(_){ ISL_DURUM = {acik:false, neden:"işlem servisine ulaşılamadı"}; }
  if ((sayfa=="piyasa" || sayfa=="alsat") && VERI && !ISL) ciz();   // alt not + coin bağlantıları işlem durumuna göre
}
async function islIstek(yol, govde){
  // madde 887: ağ hatası / zaman aşımı yakalanır (eskiden fırlıyordu: ekran iskelette, emir düğmesi "Gönderiliyor…"da takılı kalıyordu).
  // POST'ta istek sunucuya ulaşmış olabilir -> "durum bilinmiyor, kontrol et" denir; otomatik yeniden denenmez (çift emir olmasın).
  const ab = typeof AbortController == "function" ? new AbortController() : null, zt = ab && setTimeout(()=>ab.abort(), govde ? 30e3 : 20e3);
  let r;
  try { r = await fetch("api/islem/" + yol, {...(govde ? {method:"POST", headers:{"Content-Type":"application/json","X-Carry-Islem":"1"}, body: JSON.stringify(govde)} : {}), cache:"no-store", signal: ab && ab.signal}); }
  catch(e){ return {ok:false, ag:true, hata: govde && yol != "onizle" ? "Sunucuya ulaşılamadı ya da yanıt gelmedi. İşlem gitmiş olabilir: pozisyonu ve açık emirleri yenileyip kontrol et, sonra gerekirse tekrar dene."
                                                       : `İşlem servisine ulaşılamadı${e && e.name=="AbortError" ? " (zaman aşımı)" : ""}. Bağlantını kontrol et; birkaç saniye sonra yeniden denenecek.`}; }
  finally { if (zt) clearTimeout(zt); }
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
  islFiyatGetir(s); islAkisBagla(s);   // madde 853
  ISL.donus = document.activeElement; const sp = el.querySelector(".shp"); if (sp) sp.focus({preventScroll: true});   // ekran okuyucu / klavye pencereye
}
function islKapat(){ islAkisKapat(); const d = ISL && ISL.donus; ISL = null; const el = $("#sheet"); el.hidden = true; el.innerHTML = ""; document.body.style.overflow = ""; if (d && d.focus) try { d.focus({preventScroll: true}); } catch(_){} }
addEventListener("keydown", e=>{ if (e.key === "Escape" && ISL){ if (ISL.adim){ ISL.adim = null; islCiz(); } else islKapat(); } });
async function islPozYukle(){ if (!ISL) return; const s = ISL.s; const d = await islIstek("pozisyon/" + s);
  if (ISL && ISL.s==s){ const ilk = !ISL.poz; ISL.poz = d.ok ? d : {hata: d.hata, kod: d.kod};
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
  if (f > 0){ let z = D[D.length-1];
    if (Date.now() > z[5] && D.length > 1){   // madde 874: son mum kapandı, yenisi henüz indirilmedi -> canlı fiyatla yeni mum aç (grafik donmasın)
      const adim = z[0] - D[D.length-2][0]; z = [z[0] + adim, z[4], z[4], z[4], z[4], z[5] + adim]; D.push(z); D.shift();
      if (Date.now() - (M.yeni||0) > 5e3){ M.yeni = Date.now(); setTimeout(()=>islMumYukle(true), 1500); } }
    if (Date.now() <= z[5]){ z[4] = f; z[2] = Math.max(z[2], f); z[3] = Math.min(z[3], f); } }
  const P = I.poz && I.poz.pozisyon, T = (I.poz && I.poz.tpsl) || [], cizgi = [];
  const ekle = (v, ad, cls, kesik) => { v = +v; if (v > 0) cizgi.push({v, ad, cls, kesik}); };
  if (P && P.adet){ ekle(P.giris, "Giriş", "gir"); if (P.likidasyon > 0) ekle(P.likidasyon, "Likidasyon", "lik", true); }
  for (const t of T) if (t.tur == "IZ"){ if (t.aktif) ekle(t.aktif, "İz başlar", "alm", true); } else ekle(t.fiyat, t.tur=="TP" ? "TP" : "Stop", t.tur=="TP" ? "tp" : "sl", true);
  const varTP = T.some(t=>t.tur=="TP" && Math.abs(t.fiyat - I.tp) < 1e-12), varSL = T.some(t=>t.tur=="SL" && Math.abs(t.fiyat - I.sl) < 1e-12);
  if (+I.tp > 0 && !varTP) ekle(I.tp, "plan TP", "tp plan", true);
  if (+I.sl > 0 && !varSL) ekle(I.sl, "plan stop", "sl plan", true);
  if (I.gor=="emir" && I.tip=="LIMIT" && +I.fiyat > 0) ekle(I.fiyat, "Limit", "lim plan", true);
  for (const a of ALM) if (a.s == I.s) ekle(a.f, "Alarm", "alm", true);   // madde 900
  const sag = 66, alt = 18, w = W - sag, h = H - alt, n = D.length, t0 = D[0][0], adimT = n > 1 ? (D[1][0] - D[0][0]) : 3600e3, t1 = D[n-1][0] + adimT;
  let lo = Math.min(...D.map(x=>x[3])), hi = Math.max(...D.map(x=>x[2]));
  for (const c of cizgi) if (c.v > lo * 0.7 && c.v < hi * 1.3){ lo = Math.min(lo, c.v); hi = Math.max(hi, c.v); }   // çok uzak çizgi ekseni ezmesin
  const pad = (hi - lo) * 0.08 || hi * 0.01; lo -= pad; hi += pad;
  const Y = v => h - (v - lo) / (hi - lo) * h, X = t => (t - t0) / (t1 - t0) * w, bw = Math.max(1, w / n * 0.66);
  let g = "";
  for (let i = 0; i <= 4; i++){ const v = lo + (hi - lo) * i / 4, y = Y(v); g += `<line x1="0" x2="${w}" y1="${y}" y2="${y}" class="igiz"/>`; }
  const TZ = a => { const d = new Date(a), sa = `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;   // madde 874: 1 sa (5 gün) tarihle
    return I.aralik=="1d" || I.aralik=="4h" ? `${d.getDate()}.${d.getMonth()+1}` : I.aralik=="1h" ? `${d.getDate()}.${d.getMonth()+1} ${sa}` : sa; };
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
// MADDE 853: pencere açılınca fiyat HEMEN (REST) ve pencere açıkken o coinin kendi canlı akışı — Piyasa sekmesi açık olmasa da
let ISL_WS = null;
function islFiyatBoya(){ if (!ISL) return; const o = PIY[ISL.s] || {}, fe = $("#islfiy"), ye = $("#islyz");
  if (fe && o.f > 0) fe.textContent = piyFiyat(o.f);
  const b = piyBugun(o), v = b ?? o.p, ke = $("#islyzk");
  if (ye && v != null){ ye.className = sinif(v); ye.textContent = `${v>0?"▲":v<0?"▼":""}\u00a0${piyYz(v)}`; if (ke) ke.textContent = b != null ? "bugün" : "24 sa"; } }
async function islFiyatGetir(s){
  if (VERI_GOMULU) return;
  try { const d = await (await fetch(`https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=${s}`, {cache:"no-store"})).json();
    if (d && d.symbol) { piyTicker({s: d.symbol, c: d.lastPrice, P: d.priceChangePercent, q: d.quoteVolume}); if (ISL && ISL.s == s){ islFiyatBoya(); islTahmin && islTahmin(); } } } catch(_){}
  if (!piyAcTaze(s)) try { const k = await (await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=1d&limit=1`, {cache:"no-store"})).json();   // madde 873
    if (Array.isArray(k) && k.length){ PIY_AC[s] = {ot: +k[0][0], o: +k[0][1]}; if (ISL && ISL.s == s) islFiyatBoya(); } } catch(_){}
}
// MADDE 900: FİYAT ALARMI — panel tarafında (emir değil). Coin + hedef fiyat; kurulduğu andaki fiyata göre yön (yukarı / aşağı) belirlenir,
// gerçek piyasa işaret fiyatı (fstream markPrice@1s) hedefi geçince: sayfada uyarı, tarayıcı bildirimi (izin verilirse), titreşim, kısa ses.
// Tetiklenen alarm silinir, son 10'u "çalanlar" listesinde kalır. Kayıt bu tarayıcıda (localStorage); yalnız panel açıkken çalışır.
const almOku = k => { try { return JSON.parse(localStorage.getItem(k) || "[]") || []; } catch(_){ return []; } };
let ALM = almOku("carry_alarm"), ALM_CAL = almOku("carry_alarm_cal"), ALM_F = {}, ALM_WS = null, ALM_WSK = "";
function almKaydet(){ try { localStorage.setItem("carry_alarm", JSON.stringify(ALM)); localStorage.setItem("carry_alarm_cal", JSON.stringify(ALM_CAL.slice(0, 10))); } catch(_){} }
const almFiyat = s => ALM_F[s] > 0 ? ALM_F[s] : AS_F[s] > 0 ? AS_F[s] : (PIY[s]||{}).f > 0 ? PIY[s].f : null;
function almBagla(){
  const S = VERI_GOMULU || !window.WebSocket ? [] : [...new Set(ALM.map(a=>a.s))].sort(), k = S.join(",");
  if (!S.length){ if (ALM_WS){ ALM_WS.onclose = null; ALM_WS.close(); ALM_WS = null; ALM_WSK = ""; } return; }
  if (k === ALM_WSK && ALM_WS && ALM_WS.readyState <= 1) return;
  if (ALM_WS){ ALM_WS.onclose = null; ALM_WS.close(); }
  ALM_WSK = k; const ws = new WebSocket("wss://fstream.binance.com/market/stream?streams=" + S.map(x=>x.toLowerCase()+"@markPrice@1s").join("/")); ALM_WS = ws;
  ws.onmessage = e => { try { const d = JSON.parse(e.data).data; if (d && d.s && +d.p > 0){ ALM_F[d.s] = +d.p; almDenetle(d.s, +d.p); } } catch(_){} };
  ws.onclose = () => { if (ALM_WS === ws){ ALM_WS = null; ALM_WSK = ""; setTimeout(almBagla, 4000); } };
}
function almDenetle(s, p){
  const cal = ALM.filter(a=>a.s == s && (a.yon > 0 ? p >= a.f : p <= a.f)); if (!cal.length) return;
  ALM = ALM.filter(a=>!cal.includes(a));
  for (const a of cal){ ALM_CAL.unshift({...a, p, tc: Date.now()}); almCal(a, p); }
  ALM_CAL = ALM_CAL.slice(0, 10); almKaydet(); almBagla();
  if (ISL && ISL.s == s) islCiz(); else if (sayfa == "alsat") ciz();
}
function almCal(a, p){
  const ad = a.s.replace(/USDT$/,""), m = `${ad} ${a.yon > 0 ? "yükseldi" : "düştü"}: ${piyFiyat(p)} (alarm ${piyFiyat(a.f)})`;
  let el = $("#almtoast"); if (!el){ el = document.createElement("div"); el.id = "almtoast"; el.setAttribute("role", "alert"); document.body.appendChild(el); }
  const d = document.createElement("div"); d.className = "almt " + (a.yon > 0 ? "yuk" : "dus");
  d.innerHTML = `<span>🔔</span><span><b>${ea(m)}</b><span class="k">dokun: ${ea(ad)} penceresini aç</span></span><button aria-label="Kapat">✕</button>`;
  d.onclick = e => { d.remove(); if (!e.target.closest("button")) islAc(a.s); };
  el.prepend(d); [...el.children].slice(2).forEach(x=>x.remove()); setTimeout(()=>d.remove(), 60e3);
  try { navigator.vibrate && navigator.vibrate([200, 100, 200]); } catch(_){}
  try { const C = new (window.AudioContext || window.webkitAudioContext)(), o = C.createOscillator(), g = C.createGain();
    o.frequency.value = a.yon > 0 ? 880 : 520; g.gain.setValueAtTime(0.12, C.currentTime); g.gain.exponentialRampToValueAtTime(0.001, C.currentTime + 0.6);
    o.connect(g).connect(C.destination); o.start(); o.stop(C.currentTime + 0.6); } catch(_){}
  try { if (window.Notification && Notification.permission == "granted"){ const n = new Notification("Fiyat alarmı · " + ad, {body: m, tag: "alm-" + a.id, icon: "panel_varlik/ikon-192.png"}); n.onclick = () => { focus(); islAc(a.s); n.close(); }; } } catch(_){}
}
function almKur(s, v){
  v = parseFloat(islSayi(v)); const p = almFiyat(s);
  if (!(v > 0)) return "Fiyat gir.";
  if (!p) return "Şu anki fiyat henüz gelmedi, birkaç saniye sonra dene.";
  if (Math.abs(v / p - 1) < 0.0005) return "Alarm fiyatı şu anki fiyata çok yakın.";
  if (ALM.filter(a=>a.s == s).length >= 5) return "Bir coine en fazla 5 alarm.";
  ALM.push({id: Date.now().toString(36) + Math.random().toString(36).slice(2, 5), s, f: v, yon: v > p ? 1 : -1, t: Date.now(), p0: p}); almKaydet(); almBagla();
  try { if (window.Notification && Notification.permission == "default") Notification.requestPermission(); } catch(_){}
  return null;
}
function almSil(id){ ALM = ALM.filter(a=>a.id != id); almKaydet(); almBagla(); if (ISL) islCiz(); if (sayfa == "alsat") ciz(); }
function islAlmKur(){ if (!ISL) return; const h = almKur(ISL.s, ISL.alm); ISL.almMsj = h; if (!h) ISL.alm = ""; islCiz(); }
function islAlmYuzde(y){ if (!ISL) return; const p = almFiyat(ISL.s); if (!p) return; ISL.alm = String(+(p * (1 + y / 100)).toPrecision(6)); ISL.almMsj = null; islCiz(); }
const almUzak = a => { const p = almFiyat(a.s); return p ? (a.f / p - 1) * 100 : null; };
const almUzakMetin = a => { const u = almUzak(a); return u == null ? "" : `${u >= 0 ? "+" : ""}${u.toFixed(1).replace(".",",")}% uzakta`; };
function islAlmHtml(){
  const s = ISL.s, L = ALM.filter(a=>a.s == s).sort((a,b)=>b.f - a.f), ac = ISL.almAc || L.length;
  const bil = window.Notification ? Notification.permission : "yok";
  return `<div class="ialm"><button class="idonb" onclick="ISL.almAc=!ISL.almAc;islCiz()" aria-expanded="${!!ac}"><span>${ac?"▾":"▸"} 🔔 Fiyat alarmı${L.length ? ` <span class="say">${L.length}</span>` : ""}</span><span class="k">emir değil, haber verir</span></button>
    ${!ac ? "" : `${L.map(a=>`<div class="ialr"><span class="${a.yon>0?"art":"eks"}">${a.yon>0?"▲":"▼"}</span><span><b>${piyFiyat(a.f)}</b><span class="k" id="alu-${a.id}">${almUzakMetin(a)}</span></span><button onclick="almSil('${a.id}')" aria-label="Alarmı sil">✕</button></div>`).join("")}
      <div class="ichip">${[-10,-5,-2,2,5,10].map(y=>`<button onclick="islAlmYuzde(${y})">${y>0?"+":"−"}${Math.abs(y)}%</button>`).join("")}</div>
      <div class="ialf"><input inputmode="decimal" placeholder="alarm fiyatı" aria-label="alarm fiyatı" value="${ea(ISL.alm||"")}" oninput="ISL.alm=this.value" onkeydown="if(event.key=='Enter')islAlmKur()"><button class="ibtn" onclick="islAlmKur()">Alarm kur</button></div>
      ${ISL.almMsj ? `<div class="imsj hata">${ea(ISL.almMsj)}</div>` : ""}
      <p class="k" style="margin:6px 2px 0;line-height:1.4">Gerçek piyasa işaret fiyatı hedefi geçince sayfada uyarı${bil=="granted" ? ", tarayıcı bildirimi" : ""} ve ses. Panel açıkken çalışır (bu tarayıcıda saklanır).${bil=="denied" ? " Tarayıcı bildirimleri kapalı." : bil=="default" ? " İlk alarmda bildirim izni istenir." : ""}</p>`}</div>`;
}
// MADDE 906: RİSK UYARILARI — panel tarafında (emir değil), fiyat alarmıyla aynı uyarı yolu (sayfa uyarısı + bildirim + titreşim + ses).
// 1) pozisyon zararı her `kz` $ kademesini aşınca  2) fiyat 15 dk içinde pozisyona karşı %`hiz` gidince (30 dk'da bir)
// 3) hesabın açık K/Z'si her `hesap` $ kademesini aşınca  4) likidasyona %`lik`, yarısı ve beşte biri kala.
// Kademe durumu tarayıcıda saklanır; ilk görülen durum sessizce taban olur (sayfa açılınca mevcut zararlar için uyarı yağmaz).
const RU_VAR = {acik: true, kz: 250, hiz: 10, hesap: 1000, lik: 50};
let RU = (()=>{ try { return {...RU_VAR, ...(JSON.parse(localStorage.getItem("carry_risk_uyari") || "{}") || {})}; } catch(_){ return {...RU_VAR}; } })();
let RU_D = (()=>{ try { return JSON.parse(localStorage.getItem("carry_risk_durum") || "{}") || {}; } catch(_){ return {}; } })(), RU_IZ = {};
function ruKaydet(){ try { localStorage.setItem("carry_risk_uyari", JSON.stringify(RU)); localStorage.setItem("carry_risk_durum", JSON.stringify(RU_D)); } catch(_){} }
function ruAyar(k, v){ if (k == "acik") RU.acik = !!v; else { v = parseFloat(islSayi(v)); if (!(v > 0)) return; RU[k] = v; } RU_D = {}; ruKaydet(); almCanliBoya.k = null; }
function ruCal(s, baslik, metin, tur){
  ALM_CAL.unshift({id: "r" + Date.now().toString(36), s: s || "", tur: "risk", baslik, metin, tc: Date.now()}); ALM_CAL = ALM_CAL.slice(0, 10); almKaydet();
  const ad = s ? s.replace(/USDT$/,"") : "";
  let el = $("#almtoast"); if (!el){ el = document.createElement("div"); el.id = "almtoast"; el.setAttribute("role", "alert"); document.body.appendChild(el); }
  const d = document.createElement("div"); d.className = "almt dus";
  d.innerHTML = `<span>⚠️</span><span><b>${ea(baslik)}</b><span class="k">${ea(metin)}${s ? " · dokun: penceresini aç" : ""}</span></span><button aria-label="Kapat">✕</button>`;
  d.onclick = e => { d.remove(); if (!e.target.closest("button") && s) islAc(s); };
  el.prepend(d); [...el.children].slice(2).forEach(x=>x.remove()); setTimeout(()=>d.remove(), 90e3);
  try { navigator.vibrate && navigator.vibrate([300, 120, 300, 120, 300]); } catch(_){}
  try { const C = new (window.AudioContext || window.webkitAudioContext)(); for (const [i, fr] of [[0, 660], [0.25, 440]]){ const o = C.createOscillator(), g = C.createGain();
    o.frequency.value = fr; g.gain.setValueAtTime(0.14, C.currentTime + i); g.gain.exponentialRampToValueAtTime(0.001, C.currentTime + i + 0.22); o.connect(g).connect(C.destination); o.start(C.currentTime + i); o.stop(C.currentTime + i + 0.24); } } catch(_){}
  try { if (window.Notification && Notification.permission == "granted"){ const n = new Notification("⚠️ " + baslik, {body: metin, tag: "ru-" + tur + "-" + ad, icon: "panel_varlik/ikon-192.png"}); n.onclick = () => { focus(); if (s) islAc(s); n.close(); }; } } catch(_){}
}
function ruKademe(anahtar, k, cal){   // k: şu anki kademe (0 = eşik altı). Yükselince uyar; iki kademe düşünce taban iner (yeniden uyarabilsin)
  const o = RU_D[anahtar];
  if (o == null){ RU_D[anahtar] = k; return true; }
  if (k > o){ RU_D[anahtar] = k; cal(); return true; }
  if (k < o - 1){ RU_D[anahtar] = k + 1; return true; }
  return false;
}
function riskDenetle(){
  const E = ELLE_OZ; if (!RU.acik || !E || E.hata || !E.pozisyonlar || !(ISL_DURUM||{}).ayri) return;
  const P = E.pozisyonlar.filter(x=>x.adet), simdi = Date.now(); let deg = false;
  for (const x of P){
    const s = x.sembol, ad = s.replace(/USDT$/,""), f = AS_F[s] > 0 ? AS_F[s] : null, kz = asKz(x), sh = x.adet < 0;
    if (RU.kz > 0) deg = ruKademe("kz:" + s, kz < 0 ? Math.floor(-kz / RU.kz) : 0, () => ruCal(s, `${ad} zararı ${isaretli(kz)}`, `${sh ? "short" : "long"} · eşik her ${para(RU.kz)} · ${f ? "fiyat " + piyFiyat(f) : ""}`, "kz")) || deg;
    if (f){
      const L = RU_IZ[s] = (RU_IZ[s] || []).filter(o=>simdi - o[0] < 15 * 60e3); if (!L.length || simdi - L[L.length-1][0] > 5e3) L.push([simdi, f]);
      const uc = sh ? Math.min(...L.map(o=>o[1])) : Math.max(...L.map(o=>o[1])), ters = sh ? f / uc - 1 : 1 - f / uc;
      if (RU.hiz > 0 && L.length > 3 && ters * 100 >= RU.hiz && simdi - (RU_D["hiz:" + s] || 0) > 30 * 60e3){ RU_D["hiz:" + s] = simdi; deg = true;
        ruCal(s, `${ad} 15 dk'da %${(ters * 100).toFixed(1).replace(".",",")} ${sh ? "yükseldi" : "düştü"}`, `pozisyonuna karşı · ${piyFiyat(uc)} → ${piyFiyat(f)} · K/Z ${isaretli(kz)}`, "hiz"); }
      if (RU.lik > 0 && x.likidasyon > 0){ const u = Math.abs(x.likidasyon / f - 1) * 100, k = u <= RU.lik / 5 ? 3 : u <= RU.lik / 2 ? 2 : u <= RU.lik ? 1 : 0;
        deg = ruKademe("lik:" + s, k, () => ruCal(s, `${ad} likidasyona %${Math.round(u)} kaldı`, `likidasyon ${piyFiyat(x.likidasyon)} · fiyat ${piyFiyat(f)}`, "lik")) || deg; }
    }
  }
  for (const k of Object.keys(RU_D)) if (/^(kz|lik):/.test(k) && !P.some(x=>k.endsWith(":" + x.sembol))){ delete RU_D[k]; deg = true; }   // kapanan pozisyon
  if (RU.hesap > 0 && P.length){ const T = P.reduce((a,x)=>a + asKz(x), 0);
    deg = ruKademe("hesap", T < 0 ? Math.floor(-T / RU.hesap) : 0, () => ruCal("", `Hesabın açık zararı ${isaretli(T)}`, `${P.length} pozisyon · eşik her ${para(RU.hesap)}`, "hesap")) || deg; }
  if (deg) ruKaydet();
}
function ruHtml(){
  const ac = ACIK.has("asru"), g = (k, ad, birim, alt) => `<label class="rua"><span>${ad}<small>${alt}</small></span><span class="ruv">${birim == "%" ? "%" : ""}<input inputmode="decimal" value="${islGos(RU[k])}" onchange="ruAyar('${k}',this.value)" aria-label="${ad}">${birim == "$" ? " $" : ""}</span></label>`;
  return `<div class="ruk"><div class="ruh"><button class="gayr" onclick="olayAc('asru')" aria-expanded="${ac}">${ac?"▾":"▸"} Risk uyarıları <span class="k">${RU.acik ? `açık · zarar her ${para(RU.kz)}, %${islGos(RU.hiz)} / 15 dk` : "kapalı"}</span></button>
      <button class="rus ${RU.acik?"on":""}" role="switch" aria-checked="${RU.acik}" aria-label="Risk uyarıları" onclick="ruAyar('acik',${!RU.acik});ciz()"><i></i></button></div>
    ${!ac ? "" : `${g("kz", "Pozisyon zararı", "$", "her bu kadar zararda bir kez")}${g("hiz", "Hızlı ters hareket", "%", "15 dakika içinde, pozisyonuna karşı")}${g("hesap", "Hesabın toplam zararı", "$", "açık K/Z, her bu kadarda bir kez")}${g("lik", "Likidasyona yaklaşma", "%", "bu kadar, yarısı ve beşte biri kala")}
      <p class="k" style="margin:6px 2px 0;line-height:1.4">Emir değil, haber verir. Panel açıkken çalışır; sayfa açıldığında mevcut durum taban alınır, ondan sonraki kötüleşmelerde uyarır.</p>`}</div>`;
}
function asAlarmHtml(){   // Al-Sat ana sayfasında tüm alarmlar + son çalanlar
  if (!(ISL_DURUM||{}).ayri && !ALM.length && !ALM_CAL.length) return "";
  const L = ALM.slice().sort((a,b)=>Math.abs(almUzak(a) ?? 1e9) - Math.abs(almUzak(b) ?? 1e9)), ac = ACIK.has("asalm");
  const sat = a => { const ad = a.s.replace(/USDT$/,"");
    return `<div class="ialr">${coinIkon(ad, "kucuk")}<span role="button" tabindex="0" onclick="islAc('${a.s}')"><b>${ea(ad)} <span class="${a.yon>0?"art":"eks"}">${a.yon>0?"▲":"▼"}\u00a0${piyFiyat(a.f)}</span></b><span class="k" id="asalu-${a.id}">${almUzakMetin(a)}</span></span><button onclick="almSil('${a.id}')" aria-label="${ea(ad)} alarmını sil">✕</button></div>`; };
  return `<div class="kart asalm" id="asalm"><div class="apkh"><div><b>🔔 Alarmlar</b>${ALM.length ? `<span class="say">${ALM.length}</span>` : ""}</div></div>
    ${ALM.length ? L.map(sat).join("") : `<div class="k" style="padding:6px 0">Bekleyen fiyat alarmı yok. Coin penceresinden kurabilirsin.</div>`}
    ${(ISL_DURUM||{}).ayri ? ruHtml() : ""}
    ${ALM_CAL.length ? `<button class="gayr" onclick="olayAc('asalm')">${ac?"▾":"▸"} Son çalanlar <span class="k">${ALM_CAL.length}</span></button>${!ac ? "" : ALM_CAL.map(a=>a.tur == "risk" ? `<div class="ialr cal">${a.s ? coinIkon(a.s.replace(/USDT$/,""), "kucuk") : `<span>⚠️</span>`}<span><b>${ea(a.baslik)}</b><span class="k">${new Date(a.tc).toLocaleString("tr-TR",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})} · ${ea(a.metin)}</span></span></div>` : `<div class="ialr cal">${coinIkon(a.s.replace(/USDT$/,""), "kucuk")}<span><b>${ea(a.s.replace(/USDT$/,""))} ${a.yon>0?"▲":"▼"}\u00a0${piyFiyat(a.f)}</b><span class="k">${new Date(a.tc).toLocaleString("tr-TR",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})} · ${piyFiyat(a.p)}</span></span></div>`).join("")}` : ""}</div>`;
}
function almCanliBoya(){ almBagla();
  const k = ALM.map(a=>a.id).join(",") + "|" + ALM_CAL.length + "|" + ACIK.has("asalm") + "|" + ACIK.has("asru") + "|" + JSON.stringify(RU) + "|" + !!(ISL_DURUM||{}).ayri;   // alarm kur / çal / sil sonrası Al-Sat kartı yerinde yenilenir
  if (sayfa == "alsat" && k !== almCanliBoya.k){ const el = $("#asalm"), h = asAlarmHtml(), apk = document.querySelector("#piyelle .apk");
    if (el) el.outerHTML = h; else if (h && apk) apk.insertAdjacentHTML("afterend", h);
    if (el || !h || apk) almCanliBoya.k = k; }
  for (const a of ALM) for (const id of ["alu-" + a.id, "asalu-" + a.id]){ const e = document.getElementById(id); if (e){ const t = almUzakMetin(a); if (e.textContent !== t) e.textContent = t; } } }
function islAkisBagla(s){
  islAkisKapat(); if (VERI_GOMULU || !window.WebSocket || !s) return;
  const ws = new WebSocket(`wss://fstream.binance.com/market/stream?streams=${s.toLowerCase()}@ticker`); ISL_WS = ws;   // madde 832: /market adresi
  ws.onmessage = e => { try { const m = JSON.parse(e.data), d = m.data || m; if (d && d.s){ piyTicker(d); if (ISL && ISL.s == d.s) islFiyatBoya(); } } catch(_){} };
  ws.onclose = () => { if (ISL_WS === ws){ ISL_WS = null; if (ISL && ISL.s == s) setTimeout(()=>{ if (ISL && ISL.s == s && !ISL_WS) islAkisBagla(s); }, 4000); } };
}
function islAkisKapat(){ if (ISL_WS){ const w = ISL_WS; ISL_WS = null; w.onclose = null; try { w.close(); } catch(_){} } }
function islGrafikCiz(){ const el = $("#islgraf"); if (!el || !ISL) return; const W = Math.round(el.clientWidth || 320); el.innerHTML = islGrafik(W, 220);
  islFiyatBoya(); }
// MADDE 836: AKIŞ — 1) ayarla (canlı tahmin)  2) ONAY ekranı: özet + PIN + BASILI TUT (yanlışlıkla dokunuşla emir gitmez). Kapat / TP-stop / sil
// da aynı onay ekranından geçer. PIN pencere açık kaldıkça bellekte kalır (kaydedilmez). Boyut iki yolla: tutar ($) ya da RİSK ($): stop'a kadar
// kaybetmeyi göze aldığın tutar -> pozisyon büyüklüğü = risk × fiyat / |fiyat − stop| (en fazla izin verilen sınır).
function islSayi(v){ return String(v==null?"":v).trim().replace(/\s/g, "").replace(",", "."); }   // "0,45" -> "0.45" (Türkçe klavye)
const islGos = v => v===""||v==null ? "" : ea(String(v).replace(".", ","));   // kutuda Türkçe ondalık
function islAyar(k, v){
  if (k=="yon" && ISL && ISL.yon != v){ ISL.tp = ""; ISL.sl = ""; }   // madde 858: yön değişince eski TP / stop ters tarafta kalırdı
  if (!ISL) return; if (["usd","fiyat","tp","sl","risk"].includes(k)) v = islSayi(v); ISL[k] = v; if (k!="pin") ISL.oniz = null;
  if (["pin","usd","fiyat","tp","sl","risk"].includes(k)){ islTahmin(); islGrafikCiz(); islAltGuncelle(); } else islCiz(); }
function islTPSLSifirla(){   // madde 858: TP / stop kutuları görünüm değişince taşınmasın (yeni emirdeki long stop'u short pozisyona yazılmasın)
  const T = (ISL.poz && ISL.poz.tpsl) || [], t = T.find(x=>x.tur=="TP"), l = T.find(x=>x.tur=="SL");
  if (ISL.gor=="poz" && islPozVar()){ ISL.tp = t ? t.fiyat : ""; ISL.sl = l ? l.fiyat : ""; } else { ISL.tp = ""; ISL.sl = ""; }
  ISL.oniz = null;
}
function islGor(g){ if (!ISL) return; const d = ISL.gor != g; ISL.gor = g; ISL.msj = null; ISL.adim = null; if (d) islTPSLSifirla(); islCiz(); }
function islYonSec(y){ if (!ISL) return; const d = ISL.gor != "emir" || ISL.yon != y; ISL.yon = y; ISL.gor = "emir"; ISL.adim = null; ISL.msj = null; if (d) islTPSLSifirla(); islCiz(); }
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
    ${kTP>0 && kSL<0 ? sat("Risk / ödül", "1 : " + (kTP / -kSL).toFixed(1).replace(".",",")) : ""}${sat("Komisyon", "≈\u00a0" + para(kom))}</div>`;
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
// MADDE 899: EMİR SONRASI ETKİ — onay ekranında aynı yöne eklemede yeni ortalama giriş ve toplam adet; zarardaki pozisyona
// eklemede uyarı (şu anki zarar, kaçıncı alım); her emirde "Ne olur?" kartının (madde 898) emir öncesi / sonrası karşılaştırması:
// piyasa %AS_SEN ters giderse K/Z ve hesabın likide olduğu ortak hareket. Yalnız gösterim; emir akışına dokunmaz.
function islEkEtki(O){
  const sg = O.yon == "L" ? 1 : -1, P0 = ISL.poz && ISL.poz.pozisyon, var0 = islPozVar(), satir = [], not = [];
  const a0 = var0 ? P0.adet : 0, a1 = a0 + sg * O.adet, ayni = var0 && (a0 > 0) == (sg > 0);
  const g1 = !a1 ? 0 : ayni ? (a0 * P0.giris + sg * O.adet * O.fiyat) / a1 : var0 && (a0 > 0) == (a1 > 0) ? P0.giris : O.fiyat;
  if (ayni){
    satir.push(["Ortalama giriş", `${piyFiyat(P0.giris)} → <b>${piyFiyat(g1)}</b>`], ["Toplam", `${elleAdet(a0)} → <b>${elleAdet(a1)}</b> adet <span class="k">≈\u00a0${para(Math.abs(a1) * O.isaret)}</span>`]);
    const kz0 = a0 * (O.isaret - P0.giris), n = (ISL.poz.parcalar || []).length || 1;
    if (kz0 < 0 && P0.giris > 0) not.push(`Zarardaki pozisyona ekliyorsun: şu an ${isaretli(kz0)} (%${(Math.abs(kz0) / (Math.abs(a0) * P0.giris) * 100).toFixed(1).replace(".",",")}). Bu ${n + 1}. alım olur; fiyat aynı yöne gitmeye devam ederse zarar daha büyük adetle büyür.`);
  }
  const E = ELLE_OZ, H = E && E.hesap;
  if (H && H.ozkaynak != null && E.pozisyonlar){
    const P = E.pozisyonlar.map(x=>({...x, kz: asKz(x)})), oz = H.ozkaynak + P.reduce((a,x,i)=>a + x.kz - E.pozisyonlar[i].kz, 0);
    const P2 = P.filter(x=>x.sembol != O.sembol);
    if (a1) P2.push({sembol: O.sembol, adet: a1, giris: g1, kz: a1 * ((AS_F[O.sembol] > 0 ? AS_F[O.sembol] : O.isaret) - g1), likidasyon: 0});
    const R1 = asRiskHesap(oz, P), R2 = asRiskHesap(oz, P2), X = AS_SEN / 100, yuk = R2.A < 0 || (!R2.A && R1.A < 0);
    if (R2.L.length){
      const k = R => (yuk ? 1 : -1) * R.A * X, e = R => yuk ? R.yuk : R.dus, yz = v => v == null ? "yok" : "%" + Math.round(v * 100);
      satir.push([`Piyasa %${AS_SEN} ${yuk ? "yükselirse" : "düşerse"}`, `<span class="${sinif(k(R1))}">${R1.L.length ? isaretli(k(R1)) : "—"}</span> → <b class="${sinif(k(R2))}">${isaretli(k(R2))}</b>`],
                 ["Hesap likide olur", `${yz(e(R1))} ${yuk ? "yükselişte" : "düşüşte"} → <b class="${e(R2) != null && (e(R1) == null || e(R2) < e(R1) - 0.005) ? "eks" : ""}">${yz(e(R2))}</b>`]);
    }
  }
  return satir.length || not.length ? {satir, not} : null;
}
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
  S.push(["Komisyon", "≈\u00a0" + para(O.usd * 0.0005)]);
  const not = [], Ek = islEkEtki(O);   // madde 899
  if (Ek){ S.push(...Ek.satir); not.push(...Ek.not); }
  if (f && Math.abs(O.isaret/f-1) > 0.005) not.push(`Hesabın fiyatı piyasadaki gerçek fiyattan %${(Math.abs(O.isaret/f-1)*100).toFixed(1).replace(".",",")} farklı${O.mod=="live"?"":" (demo hesap)"}.`);
  if (O.not) not.push(O.not);
  const P0 = ISL.poz && ISL.poz.pozisyon, ters = islPozVar() && ((P0.adet > 0) != (O.yon=="L"));
  if (ters) not.push(`Hesap tek yönlü çalışır: bu emir önce mevcut ${P0.adet > 0 ? "long" : "short"} pozisyonu (${Math.abs(P0.adet).toLocaleString("tr-TR")} adet) azaltır; adet daha büyükse fazlası ters yönde pozisyon açar.`);
  else if (islPozVar() && (ISL.poz.tpsl||[]).length) not.push("Mevcut TP / stop toplam adede göre kendiliğinden güncellenir.");
  if (!ters && !O.sl && !(islPozVar() && ((ISL.poz.tpsl||[]).some(x=>x.tur=="SL" || x.tur=="IZ")))) not.push("Bu emirde stop yok: fiyat ters giderse zarar kendiliğinden sınırlanmaz. Düzenle'ye dönüp \"TP / stop ekle\"den koyabilirsin.");   // madde 885
  if (ISL.poz && ISL.poz.bot_tutuyor && !ISL.poz.elle) not.push("Bu coin şu an botun: emir gidince coin sana geçer, bot bu coindeki kendi emirlerini iptal eder ve coini bırakır.");
  ISL.adim = {tur: "emir", baslik: `${ISL.s.replace(/USDT$/,"")} ${ters ? (P0.adet > 0 ? "long'u azalt / çevir" : "short'u azalt / çevir") : O.yon=="L" ? "long aç" : "short aç"}`, satir: S, not, dugme: O.yon=="L" ? "Long aç" : "Short aç", renk: O.yon,
              govde: {sembol: ISL.s, yon: O.yon, usd: u, tip: ISL.tip, fiyat: ISL.fiyat, ...islTPSL()}};
  islCiz();
}
// MADDE 862: ALIM PARÇALARI — aynı coine farklı fiyatlardan yapılan her alım ayrı satır: kendi girişi, adedi, canlı K/Z'si, kendi Sat düğmesi.
// Binance coin başına tek pozisyon tutar; parçaları kapı dolum geçmişinden kurar (azaltmalar: panelden seçilen parça, yoksa en eski).
const parcaIsaret = s => (AS_F[s] > 0) ? AS_F[s] : (ISL && ISL.poz && ISL.poz.isaret) || null;
const parcaKz = (x, m) => m > 0 && x.fiyat > 0 ? x.adet * (m - x.fiyat) : null;
const parcaZaman = t => t ? new Date(t).toLocaleString("tr-TR", {day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"}) : "eski";
function parcaKzHtml(x, m){
  const k = parcaKz(x, m); if (k == null) return "—";
  const yz = k / (Math.abs(x.adet) * x.fiyat) * 100;
  return `<b>${k>=0?"▲":"▼"}\u00a0${isaretli(k)}</b><span>${(yz>=0?"+":"")}${yz.toFixed(1).replace(".",",")}%</span>`;
}
function islParcaHtml(){
  const L = ISL && ISL.poz && ISL.poz.parcalar; if (!L || L.length < 2) return "";
  const m = parcaIsaret(ISL.s), top = Math.abs(L.reduce((a,x)=>a + x.adet, 0)) || 1;
  const enIyi = Math.max(...L.map(x=>parcaKz(x, m) ?? -Infinity));
  return `<div class="ibas">Alımların <span class="k">· ${L.length} parça, her biri ayrı satılabilir</span></div><div class="iprl">${L.map((x,i)=>{
    const k = parcaKz(x, m), uz = x.adet > 0, w = Math.max(3, Math.abs(x.adet) / top * 100);
    return `<div class="ipr ${k==null?"":sinif(k)}"><div class="iprn">${i+1}</div>
      <div class="iprm"><div class="iprt">${x.eski ? "önceki alımlar" : parcaZaman(x.t)}${k!=null && k === enIyi && L.length > 2 ? ` <span class="iprr">en kârlı</span>` : ""}</div>
        <div class="k2">${elleAdet(x.adet)} adet @ <b>${piyFiyat(x.fiyat)}</b></div><div class="iprb"><span style="width:${w.toFixed(0)}%"></span></div></div>
        <button class="iprtp" onclick="islParcaTpslAc('${ea(x.id)}')" aria-label="${i+1}. alımın TP ve stop'u">${x.tp||x.sl
          ? `${x.tp?`<span class="art">TP ${piyFiyat(x.tp)}</span>`:""}${x.sl?`<span class="eks">stop ${piyFiyat(x.sl)}</span>`:`<span class="uyr">stop yok</span>`}<i>düzenle</i>`
          : `<span class="k">＋ TP / stop koy</span>`}</button>
      <div class="iprk" id="ipr-${ea(x.id)}">${parcaKzHtml(x, m)}</div>
      <button class="iprs" onclick="islParcaOnay('${ea(x.id)}')">${uz ? "Sat" : "Kapat"}</button></div>`; }).join("")}</div>`;
}
function islParcaBoya(){   // her saniye: yalnız K/Z rakamları (düğmeye dokunuş kaybolmasın)
  const L = ISL && !ISL.adim && ISL.gor=="poz" && ISL.poz && ISL.poz.parcalar; if (!L || L.length < 2) return;
  const m = parcaIsaret(ISL.s);
  for (const x of L){ const el = document.getElementById("ipr-" + x.id); if (!el) continue; const h = parcaKzHtml(x, m);
    if (el.innerHTML !== h) el.innerHTML = h; const k = parcaKz(x, m), sat = el.parentElement; if (sat && k != null){ sat.classList.toggle("art", k >= 0); sat.classList.toggle("eks", k < 0); } }
}
setInterval(islParcaBoya, 1000);
// MADDE 863: PARÇA BAŞINA TP / STOP — düzenleyici (yüzde kısayolları o alımın GİRİŞ fiyatına göre), sonra PIN + basılı tut
function islParcaTpslAc(id){
  const x = ISL && ISL.poz && (ISL.poz.parcalar||[]).find(p=>p.id == id); if (!x) return;
  ISL.pd = {id, tp: x.tp || "", sl: x.sl || ""}; ISL.msj = null; islCiz();
  const e = $("#ipd"); if (e) e.scrollIntoView({block: "start", behavior: "smooth"});
}
function islPdAyar(k, v){ if (!ISL || !ISL.pd) return; ISL.pd[k] = islSayi(v); const t = $("#ipdtah"); if (t) t.innerHTML = islPdTahmin(); }
function islPdYuzde(k, y){
  const x = islPdParca(); if (!x || !ISL.pd) return; const uz = x.adet > 0, yon = k=="tp" ? 1 : -1;
  ISL.pd[k] = +(x.fiyat * (1 + yon * (uz?1:-1) * y / 100)).toPrecision(6); islCiz();
}
const islPdParca = () => ISL && ISL.pd && ISL.poz && (ISL.poz.parcalar||[]).find(p=>p.id == ISL.pd.id);
function islPdTahmin(){
  const x = islPdParca(); if (!x) return ""; const P = ISL.pd, tp = +P.tp, sl = +P.sl, m = parcaIsaret(ISL.s), uz = x.adet > 0, U = [];
  if (tp > 0 && m && (uz ? tp <= m : tp >= m)) U.push(`TP şimdiki fiyatın ${uz?"üstünde":"altında"} olmalı (${piyFiyat(m)}).`);
  if (sl > 0 && m && (uz ? sl >= m : sl <= m)) U.push(`Stop şimdiki fiyatın ${uz?"altında":"üstünde"} olmalı (${piyFiyat(m)}).`);
  const k = v => x.adet * (v - x.fiyat), yz = v => ((v / x.fiyat - 1) * 100 * (uz?1:-1));
  const sat = (a, v) => `<div><span>${a}</span><b class="${sinif(k(v))}">${k(v)>=0?"▲":"▼"}\u00a0${isaretli(k(v))} <small>${(yz(v)>=0?"+":"")}${yz(v).toFixed(1).replace(".",",")}%</small></b></div>`;
  return `<div class="itg">${tp>0 ? sat("TP'de bu alım", tp) : ""}${sl>0 ? sat("Stop'ta bu alım", sl) : ""}${!(tp>0) && !(sl>0) ? `<div><span>TP ve stop boş</span><b class="k">kaydedersen bu alımınkiler kaldırılır</b></div>` : ""}</div>`
    + U.map(u=>`<p class="iuyr" role="alert">⚠ ${u}</p>`).join("");
}
function islPdHtml(){
  const x = islPdParca(); if (!x) { ISL.pd = null; return ""; }
  const L = ISL.poz.parcalar, i = L.indexOf(x) + 1, uz = x.adet > 0, P = ISL.pd;
  const hz = (k, Y) => `<div class="ichip">${Y.map(y=>`<button onclick="islPdYuzde('${k}',${y})">${(k=="tp") == uz ? "+" : "−"}${y}%</button>`).join("")}</div>`;
  return `<div class="ipd" id="ipd"><div class="ipdh"><b>${i}. alım · TP / stop</b><button class="shx" onclick="ISL.pd=null;islCiz()" aria-label="Vazgeç">✕</button></div>
    <div class="k2">${x.eski ? "önceki alımlar" : parcaZaman(x.t)} · ${elleAdet(x.adet)} adet @ <b>${piyFiyat(x.fiyat)}</b> · yüzdeler bu alımın girişine göre</div>
    <label class="ibas" for="ipdtp">TP (kâr al)</label><input id="ipdtp" inputmode="decimal" value="${ea(P.tp)}" oninput="islPdAyar('tp',this.value)" placeholder="boş: TP yok">${hz("tp", [5,10,20,30])}
    <label class="ibas" for="ipdsl">Stop</label><input id="ipdsl" inputmode="decimal" value="${ea(P.sl)}" oninput="islPdAyar('sl',this.value)" placeholder="boş: stop yok">${hz("sl", [3,5,10,20])}
    <div id="ipdtah">${islPdTahmin()}</div>
    <p class="ion k">Yalnız bu alımın adedi (${elleAdet(x.adet)}) için. Diğer alımların ve pozisyonun genel TP / stop'u değişmez.</p>
    <button class="ibtn vurgu ipdb" onclick="islPdDevam()">Devam</button></div>`;
}
function islPdDevam(){
  const x = islPdParca(); if (!x) return; const P = ISL.pd, i = ISL.poz.parcalar.indexOf(x) + 1, tp = +P.tp || null, sl = +P.sl || null;
  const ad = v => v ? `${piyFiyat(v)} <span class="${sinif(x.adet * (v - x.fiyat))}">${isaretli(x.adet * (v - x.fiyat))}</span>` : "kaldırılır";
  ISL.adim = {tur: "tpsl", baslik: `${ISL.s.replace(/USDT$/,"")} · ${i}. alımın TP / stop'u`,
    satir: [["Alım", `${elleAdet(x.adet)} adet @ ${piyFiyat(x.fiyat)}`], ["TP", ad(tp)], ["Stop", ad(sl)], ["Kapsam", "yalnız bu alım"]],
    not: ["Tetiklenince yalnız bu alımın adedi piyasa fiyatından kapanır."], dugme: "Kaydet", renk: "vurgu", yol: "tpsl",
    govde: {sembol: ISL.s, parca: x.id, tp: P.tp, sl: P.sl}, pd: true};
  ISL.msj = null; islCiz();
}
function islParcaOnay(id){
  const L = ISL && ISL.poz && ISL.poz.parcalar, x = L && L.find(p=>p.id == id); if (!x) return;
  const m = parcaIsaret(ISL.s), k = parcaKz(x, m), i = L.indexOf(x) + 1, uz = x.adet > 0;
  ISL.adim = {tur: "kapat", baslik: `${ISL.s.replace(/USDT$/,"")} · ${i}. alımı ${uz ? "sat" : "kapat"}`,
    satir: [["Alım", x.eski ? "önceki alımlar" : parcaZaman(x.t)], ["Adet", elleAdet(x.adet)], ["Giriş", piyFiyat(x.fiyat)], ["Şimdi", m ? piyFiyat(m) : "—"],
            ["Bu alımın K/Z'si", k == null ? "—" : `<span class="${sinif(k)}">≈\u00a0${isaretli(k)}</span>`], ["Fiyat", "piyasa fiyatından"]],
    not: [L.length > 1 ? "Diğer alımların açık kalır; TP / stop kalan adede göre yeniden kurulur." : "Bu son parça: pozisyon tamamen kapanır.",
          "Binance gerçekleşen K/Z'yi ortalama girişten yazar; rakam burada gördüğünden farklı görünebilir, toplam aynıdır."],
    dugme: uz ? "Bu alımı sat" : "Bu alımı kapat", renk: "tehlike", yol: "kapat", govde: {sembol: ISL.s, oran: 1, parca: x.id}};
  ISL.msj = null; islCiz();
}
function islKapatOnay(oran){
  if (!ISL || !islPozVar()) return; const P = ISL.poz.pozisyon, f = ISL.poz.isaret || P.giris, q = Math.abs(P.adet) * oran;
  ISL.adim = {tur: "kapat", baslik: `${ISL.s.replace(/USDT$/,"")} ${oran>=1 ? "pozisyonu kapat" : "%" + oran*100 + " kapat"}`,
    satir: [["Kapanacak", `≈ ${(+q.toPrecision(5)).toLocaleString("tr-TR")} adet`], ["Değer", "≈\u00a0" + para(q * f)], ["Gerçekleşecek K/Z", `<span class="${sinif(P.kz)}">≈\u00a0${isaretli(P.kz * oran)}</span>`],
            ["Fiyat", "piyasa fiyatından"]], not: oran>=1 ? ["Bu coinde panelden konan TP / stop / limit emirleri de silinir."] : ["Kalan adet için TP / stop aynı fiyatlarla yeniden kurulur."],
    dugme: oran>=1 ? "Tümünü kapat" : "Kapat", renk: "tehlike", yol: "kapat", govde: {sembol: ISL.s, oran}};
  ISL.msj = null; islCiz();
}
// MADDE 901: İZ SÜREN STOP — fiyat kâr yönünde gittikçe stop arkasından gelir; gördüğü en iyi fiyattan %oran geri dönünce pozisyonun
// tamamı piyasadan kapanır (Binance TRAILING_STOP_MARKET, işaret fiyatı, reduceOnly). İsteğe bağlı başlama fiyatı: iz ancak fiyat oraya
// gelince başlar (long'da üstte, short'ta altta). Eklemede / kısmi kapanışta yeni adetle yeniden kurulur (iz sıfırdan başlar).
// MADDE 902: coin penceresinde pozisyonun gerçek sonucu (açıldığından beri): fiyat + funding + komisyon + kısmi kapanış = net
function islGelirHtml(PR, pz){
  const G = PR.gelir; if (!G) return "";
  const net = pz.kz + G.fon + G.kom + G.gercek, gun = Math.max(1 / 24, (Date.now() - G.t) / 864e5);
  const sat = (a, v, alt) => `<div><span>${a}${alt ? ` <span class="k">${alt}</span>` : ""}</span><b class="${sinif(v)}">${isaretli(v)}</b></div>`;
  return `<div class="igel"><div class="igelb"><span>Bu pozisyonun gerçek sonucu</span><span class="k">${gun < 1 ? Math.round(gun * 24) + " saattir" : gun.toFixed(1).replace(".",",") + " gündür"} açık</span></div>
    ${sat("Fiyat K/Z", pz.kz, "açık")}${sat("Funding", G.fon, Math.abs(G.fon) >= 0.01 ? `günde ≈\u00a0${isaretli(G.fon / gun)}` : "")}${sat("Komisyon", G.kom)}${Math.abs(G.gercek) >= 0.01 ? sat("Kısmi kapanışlar", G.gercek, "gerçekleşen") : ""}
    <div class="igelt"><span>Net</span><b class="${sinif(net)}">${isaretli(net)}</b></div></div>`;
}
// MADDE 904: İŞLEM GÜNLÜĞÜ — pozisyona not ("neden girdim, planım ne"). Sunucuda saklanır (her cihazda aynı); kapanınca Geçmiş'te sonucun yanında.
function islNotHtml(){
  if (!(ISL_DURUM||{}).ayri) return "";
  const N = ISL.poz.not, duz = ISL.notDuz;
  if (!N && !duz) return `<button class="iacil kucuk2" onclick="ISL.notDuz=true;islCiz();setTimeout(()=>{ const t = $('#islnot'); if (t) t.focus(); }, 0)"><span>📝 Not ekle</span><i>neden girdin, planın ne?</i></button>`;
  if (!duz) return `<div class="inot"><div class="inoth"><span>📝 Notun</span><button onclick="ISL.notDuz=true;ISL.notMetin=ISL.poz.not;islCiz()">düzenle</button></div><div class="inotm">${ea(N)}</div></div>`;
  const v = ISL.notMetin ?? N ?? "";
  return `<div class="inot"><div class="inoth"><span>📝 Not <span class="k">· isteğe bağlı, sadece sen görürsün</span></span></div>
    <textarea id="islnot" rows="3" maxlength="1000" placeholder="Neden girdin? Planın ne? (hedef, stop, ne olursa çıkarsın…)" oninput="ISL.notMetin=this.value">${ea(v)}</textarea>
    ${ISL.notMsj ? `<div class="imsj ${ISL.notMsj.ok?"ok":"hata"}" role="status">${ea(ISL.notMsj.ok||ISL.notMsj.hata)}</div>` : ""}
    <div class="iseg kucuk"><button class="birincil" onclick="islNotKaydet()" ${ISL.notMesgul?"disabled":""}>${ISL.notMesgul ? "Kaydediliyor…" : "Notu kaydet"}</button><button onclick="ISL.notDuz=false;ISL.notMetin=null;ISL.notMsj=null;islCiz()">Vazgeç</button></div></div>`;
}
async function islNotKaydet(){
  if (!ISL || ISL.notMesgul) return; const s = ISL.s, m = String(ISL.notMetin ?? ISL.poz.not ?? "").trim();
  if (!m && !ISL.poz.not){ ISL.notMsj = {hata: "Bir şey yaz."}; islCiz(); return; }
  ISL.notMesgul = true; ISL.notMsj = null; islCiz();
  const d = await islIstek("not", {sembol: s, metin: m});
  if (!ISL || ISL.s != s) return; ISL.notMesgul = false;
  if (!d.ok){ ISL.notMsj = {hata: d.hata}; islCiz(); return; }
  ISL.poz.not = d.not ? d.not.metin : null; ISL.notDuz = false; ISL.notMetin = null; ISL.notMsj = null; islCiz();
  const P = ELLE_OZ && (ELLE_OZ.pozisyonlar||[]).find(x=>x.sembol == s); if (P) P.not = ISL.poz.not || undefined;
}
function islIzHtml(){
  const PR = ISL.poz, pz = PR.pozisyon, uz = pz.adet > 0, Z = PR.tpsl.find(x=>x.tur=="IZ"), ac = ISL.izAc || false;
  const ref = PR.isaret || pz.giris, gecerli = v => v > 0 && (uz ? v > ref : v < ref);
  const ust = Z ? `<span class="art">%${islGos(Z.oran)}</span> geri dönüşte kapanır${Z.aktif ? ` · ${piyFiyat(Z.aktif)}'den başlar` : ""}` : `<span class="k">yok · kâr ${uz ? "yükseldikçe" : "düştükçe"} stop arkandan gelir</span>`;
  if (!ac) return `<button class="iacil kucuk2" onclick="ISL.izAc=true;ISL.iz=ISL.iz||${Z ? Z.oran : 3};ISL.izA=ISL.izA??${Z && Z.aktif ? Z.aktif : '""'};islCiz()"><span>İz süren stop</span><i>${ust}</i></button>`;
  const o = +ISL.iz || 0, a = +ISL.izA || 0;
  const tet = o > 0 ? (a && gecerli(a) ? a : ref) * (uz ? 1 - o / 100 : 1 + o / 100) : null, kz = tet ? pz.adet * (tet - pz.giris) : null;
  return `<div class="iiz"><div class="ibas" style="margin-top:0">İz süren stop ${Z ? `<span class="k">· şu an ${ust}</span>` : ""}</div>
    <div class="k" style="font-size:12px;margin:2px 0 6px">${uz ? "Fiyatın gördüğü en yüksekten" : "Fiyatın gördüğü en düşükten"} bu kadar ${uz ? "düşünce" : "yükselince"} pozisyonun tamamı kapanır. Başlama fiyatı boşsa iz hemen başlar.</div>
    <div class="ichip">${[1,2,3,5,8].map(v=>`<button class="${o==v?"on":""}" onclick="ISL.iz=${v};islCiz()">%${v}</button>`).join("")}</div>
    <div class="iki" style="margin-top:8px"><div><input inputmode="decimal" placeholder="oran % (0,1–10)" aria-label="geri dönüş oranı yüzde" value="${islGos(ISL.iz)}" oninput="ISL.iz=islSayi(this.value);islIzTahmin()"></div>
      <div><input inputmode="decimal" placeholder="başlama fiyatı" aria-label="başlama fiyatı" value="${islGos(ISL.izA)}" oninput="ISL.izA=islSayi(this.value);islIzTahmin()"></div></div>
    ${(uz ? pz.giris > ref : pz.giris < ref) ? `<button class="iacil kucuk2" onclick="ISL.izA=${pz.giris};islCiz()"><span>Kâra geçince başlasın</span><i>başlama = giriş ${piyFiyat(pz.giris)}</i></button>` : ""}
    <div class="k" id="iztah" style="font-size:12.5px;margin-top:6px">${islIzTahminMetin()}</div>
    <div class="iseg kucuk"><button class="birincil" onclick="islIzOnay()">${Z ? "İz süreni güncelle" : "İz süren stop koy"}</button>${Z ? `<button onclick="islIzOnay(true)">Kaldır</button>` : ""}<button onclick="ISL.izAc=false;islCiz()">Vazgeç</button></div></div>`;
}
function islIzTahminMetin(){
  if (!ISL || !islPozVar()) return ""; const PR = ISL.poz, pz = PR.pozisyon, uz = pz.adet > 0, ref = PR.isaret || pz.giris, o = +ISL.iz || 0, a = +ISL.izA || 0;
  if (!(o >= 0.1 && o <= 10)) return `<span class="uyr">Oran %0,1 ile %10 arasında olmalı.</span>`;
  if (a && !(uz ? a > ref : a < ref)) return `<span class="uyr">Başlama fiyatı ${uz ? "şimdiki fiyatın üstünde" : "şimdiki fiyatın altında"} olmalı (kâr yönünde); boş bırakırsan hemen başlar.</span>`;
  const tet = (a || ref) * (uz ? 1 - o / 100 : 1 + o / 100), kz = pz.adet * (tet - pz.giris);
  return `${a ? `Fiyat ${piyFiyat(a)}'e gelince başlar; o an` : "Şimdi başlasa"} tetik ≈ <b>${piyFiyat(tet)}</b> → K/Z ≈ <b class="${sinif(kz)}">${isaretli(kz)}</b>. Fiyat lehine gittikçe tetik de kayar.`;
}
function islIzTahmin(){ const e = $("#iztah"); if (e) e.innerHTML = islIzTahminMetin(); }
function islIzOnay(kaldir){
  if (!ISL || !islPozVar()) return; const PR = ISL.poz, pz = PR.pozisyon, o = +ISL.iz || 0, a = +ISL.izA || 0, uz = pz.adet > 0, ref = PR.isaret || pz.giris;
  if (!kaldir && (!(o >= 0.1 && o <= 10) || (a && !(uz ? a > ref : a < ref)))){ islIzTahmin(); return; }
  const tet = (a || ref) * (uz ? 1 - o / 100 : 1 + o / 100);
  ISL.adim = kaldir ? {tur: "iz", baslik: `${ISL.s.replace(/USDT$/,"")} iz süren stop'u kaldır`, satir: [["İz süren stop", "kaldırılır"], ["Dokunulmayan", "TP / stop ve alımların TP / stop'u"]], not: [],
      dugme: "Kaldır", renk: "tehlike", yol: "iz", govde: {sembol: ISL.s, oran: ""}}
    : {tur: "iz", baslik: `${ISL.s.replace(/USDT$/,"")} iz süren stop`, satir: [["Geri dönüş", `%${islGos(o)}`], ["Başlama", a ? piyFiyat(a) : "hemen (şimdiki fiyattan)"],
        [a ? "Başlayınca tetik" : "Şimdiki tetik", `≈ ${piyFiyat(tet)} <span class="${sinif(pz.adet * (tet - pz.giris))}">${isaretli(pz.adet * (tet - pz.giris))}</span>`],
        ["Kapsam", `pozisyonun tamamı, ${Math.abs(pz.adet).toLocaleString("tr-TR")} adet`]],
      not: [`${uz ? "Long: fiyatın en yükseğinden" : "Short: fiyatın en düşüğünden"} %${islGos(o)} geri dönünce piyasadan kapanır (işaret fiyatı). Normal TP / stop'un varsa onlar da yerinde kalır; hangisi önce tetiklenirse.`,
            "Pozisyona ekleme yaparsan ya da bir kısmını kapatırsan iz süren stop yeni adetle yeniden kurulur; iz o andan başlar."],
      dugme: "Kaydet", renk: "vurgu", yol: "iz", govde: {sembol: ISL.s, oran: o, aktif: a || ""}};
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
  const pdIdi = A.pd; ISL.adim = null; ISL.oniz = null; if (pdIdi) ISL.pd = null; if (yol == "iz") ISL.izAc = false;
  ISL.msj = {ok: pdIdi ? "Bu alımın TP / stop'u kaydedildi" : yol=="emir" ? `${d.emir.durum=="FILLED" ? "Doldu" : d.emir.durum=="NEW" ? "Emir bekliyor" : "Gönderildi"}: ${d.emir.tip=="LIMIT"?"limit":"piyasa"} ${d.emir.adet.toLocaleString("tr-TR")} adet`
                 + (d.tpsl && d.tpsl.length ? `, ${d.tpsl.map(x=>(x.tur=="SL"?"stop":x.tur)+" "+piyFiyat(x.fiyat)).join(", ")}` : "") + (d.tpsl_hata ? `. ⚠️ ${d.tpsl_hata}` : "")
             : yol=="kapat" ? `Kapatıldı: ${d.kapat.adet.toLocaleString("tr-TR")} adet` : yol=="tpsl" ? "TP / stop kaydedildi" : yol=="iz" ? (d.iz ? `İz süren stop kuruldu: %${islGos(d.iz.oran)}` : "İz süren stop kaldırıldı") : `Silindi: ${d.iptal} emir`, durum: yol=="emir" ? d.emir.durum : ""};
  islCiz();
  const yNot = yol=="emir" && String(ISL.yeniNot||"").trim(), yS = ISL.s; if (yol=="emir") ISL.yeniNot = "";
  setTimeout(async ()=>{ if (!ISL) return;
    if (yNot && d.emir.durum=="FILLED"){ const n = await islIstek("not", {sembol: yS, metin: yNot}); if (ISL && !n.ok) ISL.msj = {...ISL.msj, ok: (ISL.msj||{}).ok + ` · not kaydedilemedi: ${n.hata}`}; }   // madde 904
    await islPozYukle(); if (ISL && yol=="emir" && islPozVar()){ ISL.gor = "poz"; islCiz(); } }, 1200);
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
  if (I.gor=="poz" && islPozVar()){ const uz = I.poz.pozisyon.adet > 0;   // madde 869: alt düğmeler pozisyona göre ne yaptığını söyler
    return `<div class="ialt" id="islalt">${uz ? `<button class="ibtn S" onclick="islYonSec('S')">Azalt / çevir</button><button class="ibtn L" onclick="islYonSec('L')">＋ Long ekle</button>`
      : `<button class="ibtn S" onclick="islYonSec('S')">＋ Short ekle</button><button class="ibtn L" onclick="islYonSec('L')">Azalt / çevir</button>`}</div>`; }
  if ((I.poz && I.poz.kod == 404) || (!islPozVar() && islYok(I.s))) return `<div class="ialt" id="islalt"><button class="ibtn ikinci" disabled>${(ISL_DURUM||{}).mod=="live"?"Bu hesapta işlem görmüyor":"Demo hesapta işlem görmüyor"}</button></div>`;
  const u = islBoyutUsd();
  return `<div class="ialt" id="islalt"><button id="isldevam" class="ibtn ${I.yon}" onclick="islDevam()" ${I.mesgul?"disabled":""}>${I.mesgul ? "Kontrol ediliyor…" : `${I.yon=="L"?"Long":"Short"} ${u>0 ? para(u) : ""}`}</button></div>`;
}
function islMsjHtml(){ const I = ISL; return !I || !I.msj ? "" : `<div class="imsj ${I.msj.ok?"ok":"hata"}" role="status">${I.msj.durum=="FILLED"?'<span class="idur ok">Doldu</span>':I.msj.durum=="NEW"?'<span class="idur bek">Bekliyor</span>':""}${ea(I.msj.ok||I.msj.hata)}</div>`; }
function islCiz(){
  const el = $("#islic"); if (!el || !ISL) return;
  const I = ISL, ad = I.s.replace(/USDT$/,""), D = ISL_DURUM || {}, PR = I.poz, pz = PR && PR.pozisyon, o = PIY[I.s] || {}, f = o.f;
  const fg = v => v==null||v===""||isNaN(v)||!(+v>0) ? "—" : piyFiyat(+v);
  const seg = (alan, v, ad2, cls="") => `<button class="${cls} ${I[alan]==v?"on":""}" onclick="islAyar('${alan}','${v}')">${ad2}</button>`;
  const _uz = I.gor=="poz" && islPozVar() ? I.poz.pozisyon.adet > 0 : I.yon=="L";   // madde 858: kısayol işareti yöne göre (short'ta TP aşağı, stop yukarı)
  const hz = (alan, L) => `<div class="ichip">${L.map(y=>`<button onclick="islYuzde('${alan}',${y})">${(alan=="tp") == _uz ? "+" : "−"}${y}%</button>`).join("")}</div>`;
  const uzak = (v, ref) => v>0 && ref>0 ? ` <span class="k">${((v/ref-1)*100>=0?"+":"")}${((v/ref-1)*100).toFixed(1).replace(".",",")}%</span>` : "";
  const varPoz = islPozVar(), uzun = varPoz && pz.adet > 0;
  let h = `<div class="ihd"><div><div class="iad">${coinIkon(ad, "ihik")}<b>${ad}</b><span class="irz">${D.mod=="live"?"Canlı":"Demo"}</span></div>
      <div class="ifr"><span id="islfiy">${f>0 ? fg(f) : `<span class="k" style="font-size:16px">fiyat geliyor…</span>`}</span><span id="islyz" class="${sinif(piyBugun(o) ?? o.p)}">${(piyBugun(o) ?? o.p)!=null ? `${(piyBugun(o) ?? o.p)>0?"▲":(piyBugun(o) ?? o.p)<0?"▼":""} ${piyYz(piyBugun(o) ?? o.p)}` : ""}</span><span class="k" id="islyzk">${piyBugun(o)!=null ? "bugün" : "24 sa"}</span></div></div>
      <button class="shx" onclick="islKapat()" aria-label="Kapat">✕</button></div>`;
  // grafik
  h += `<div class="igk"><div class="igb"><div class="ichip ar">${Object.entries(ISL_AR).map(([a,[t]])=>`<button class="${I.aralik==a?"on":""}" onclick="islAralik('${a}')">${t}</button>`).join("")}</div>
      <div class="ichip gt"><button class="${I.gtur!="cizgi"?"on":""}" onclick="islGTur('mum')" aria-label="mum grafik" title="mum">▮▯</button><button class="${I.gtur=="cizgi"?"on":""}" onclick="islGTur('cizgi')" aria-label="çizgi grafik" title="çizgi">∿</button></div></div>
      <div id="islgraf" class="igr"></div>${(PR && PR.islemler && PR.islemler.length) ? `<div class="igl3"><span><b class="igal">▲</b> alışların</span><span><b class="igsat">▼</b> satışların</span><span>son 7 gün</span></div>` : ""}</div>`;
  // madde 869: dönem tablosu en altta katlı (pozisyon / emir formu grafiğin hemen altında)
  // madde 839: kimin coini? (bot / sen) — işlemden önce net
  if (PR && !PR.hata && !I.adim){
    if (PR.elle && !(ISL_DURUM||{}).ayri) h += PR.bot_pay ? `<div class="isah bot">Burada yalnız <b>senin payın</b> görünüyor. Borsadaki ${elleAdet(PR.bot_pay)} adet botun — kapat yalnız seninkini kapatır; taşımada botun payı ona geri döner.</div>`
      : `<div class="isah sen">✋ Bu pozisyon senin. Al-sat hesabı bağlanınca oraya taşınacak.</div>`;
    else if (PR.bot_tutuyor) h += `<div class="isah bot">Bu coin şu an botun. İşlem yaparsan coin sana geçer ve bot bu coini bırakır.</div>`;
  }
  // ONAY ekranı
  if (I.adim){ const A = I.adim;
    h += `<div class="ionay"><div class="iob">${A.baslik}</div><div class="iozt">${A.satir.map(([a,b])=>`<div><span class="k">${a}</span><b>${b}</b></div>`).join("")}</div>
      ${A.not.map(n=>`<p class="ion">${ea(n)}</p>`).join("")}
      ${A.tur=="emir" && !islPozVar() && (ISL_DURUM||{}).ayri ? `<label class="ibas" for="islynot">📝 Not <span class="k">· isteğe bağlı: neden giriyorsun, planın ne?</span></label><textarea id="islynot" rows="2" maxlength="1000" oninput="ISL.yeniNot=this.value">${ea(ISL.yeniNot||"")}</textarea>` : ""}
      <label class="ibas" for="islpin">İşlem PIN'i</label><input id="islpin" type="password" inputmode="numeric" autocomplete="off" value="${ea(I.pin)}" oninput="islAyar('pin',this.value)" placeholder="sunucuda belirlediğin PIN">
      <p class="ion k">Göndermek için alttaki düğmeyi basılı tut.</p></div>`;
  } else {
    if (varPoz) h += `<div class="iseg gor"><button class="${I.gor=="poz"?"on":""}" onclick="islGor('poz')">Pozisyon</button><button class="${I.gor=="emir"?"on":""}" onclick="islGor('emir')">Ekle / azalt</button></div>`;
    if (I.msj) h += islMsjHtml();
    if (!PR) h += `<div class="k" style="padding:12px 2px">Pozisyon okunuyor…</div>`;
    else if (PR.hata && PR.kod == 404) h += `<div class="isah yok"><b>${ad} ${D.mod=="live"?"bu hesapta":"demo hesapta"} işlem görmüyor.</b><br>${D.mod=="live" ? "" : "Binance'in demo ortamında gerçek piyasadaki her coin yok, özellikle yeni listelenenler. "}Grafiği ve fiyatı izleyebilirsin; işlem açılamaz.</div>`;
    else if (PR.hata) h += `<div class="imsj hata">Pozisyon okunamadı: ${ea(PR.hata)}</div>`;
    if (varPoz && I.gor=="poz"){
      const deger = Math.abs(pz.adet) * (PR.isaret || pz.giris), kzp = pz.giris>0 ? pz.kz / (Math.abs(pz.adet) * pz.giris) * 100 : null;
      const tTP = PR.tpsl.find(x=>x.tur=="TP"), tSL = PR.tpsl.find(x=>x.tur=="SL");
      const likU = pz.likidasyon>0 && PR.isaret ? Math.abs(PR.isaret / pz.likidasyon - 1) * 100 : null;
      const kut = (e, d) => `<div class="iku"><span class="k">${e}</span><b>${d}</b></div>`;
      h += `<div class="ipoz"><div class="iph"><div><span class="iyon ${uzun?"L":"S"}">${uzun?"Long":"Short"}</span><span class="iadet">${Math.abs(pz.adet).toLocaleString("tr-TR")}\u00a0adet</span></div>
          <div class="ikz ${sinif(pz.kz)}">${pz.kz>=0?"▲":"▼"}\u00a0${isaretli(pz.kz)}<small>${kzp==null?"":(kzp>=0?"+":"")+kzp.toFixed(2).replace(".",",")+"%"}</small></div></div>
        <div class="ikg">${kut("Giriş", fg(pz.giris))}${kut("Şimdi", fg(PR.isaret) + uzak(PR.isaret, pz.giris))}${kut("Değer", para(deger))}
          ${kut("TP", tTP ? fg(tTP.fiyat) + uzak(tTP.fiyat, PR.isaret) : "<span class='k'>yok</span>")}${kut("Stop", tSL ? fg(tSL.fiyat) + uzak(tSL.fiyat, PR.isaret) : PR.tpsl.some(x=>x.tur=="IZ") ? `<span class="k">iz süren %${islGos(PR.tpsl.find(x=>x.tur=="IZ").oran)}</span>` : "<span class='uyr'>yok</span>")}
          ${kut("Likidasyon", pz.likidasyon>0 ? fg(pz.likidasyon) : "—")}</div>
        ${likU!=null ? `<div class="ilik"><div class="ilikb"><span style="width:${Math.max(4, Math.min(100, likU / 50 * 100)).toFixed(0)}%" class="${likU<10?"kr":likU<30?"tu":"ye"}"></span></div><span class="k">likidasyona %${likU.toFixed(0)} uzak</span></div>` : ""}${islGelirHtml(PR, pz)}</div>
        ${islNotHtml()}
        <div class="ibas">Kapat</div><div class="iseg kucuk"><button onclick="islKapatOnay(0.25)">%25</button><button onclick="islKapatOnay(0.5)">%50</button><button class="tehlike" onclick="islKapatOnay(1)">Tümü</button></div>
        <div class="ibas">${(PR.parcalar||[]).length > 1 ? "Pozisyonun tamamı için TP / stop" : "TP / stop"}</div>
        <div class="iki"><div><input inputmode="decimal" placeholder="TP fiyatı" aria-label="TP fiyatı" value="${islGos(I.tp)}" oninput="islAyar('tp',this.value)">${hz("tp",[3,5,10])}</div>
          <div><input inputmode="decimal" placeholder="Stop fiyatı" aria-label="Stop fiyatı" value="${islGos(I.sl)}" oninput="islAyar('sl',this.value)">${hz("sl",[3,5,10])}</div></div>
        ${(uzun ? PR.isaret > pz.giris : PR.isaret < pz.giris) ? `<button class="iacil kucuk2" onclick="islBasaBas()"><span>Stop'u girişe çek</span><i>kârdayken zararsız çıkış · ${fg(pz.giris)}</i></button>` : ""}
        <div id="isluyr">${islUyari()}</div>
        ${islIzHtml()}
        <div class="iseg kucuk"><button class="birincil" onclick="islTPSLOnay()">TP / stop kaydet</button>${PR.bekleyen.some(x=>x.panel)||PR.tpsl.some(x=>x.panel)?`<button onclick="islSilOnay()">Panel emirlerini sil</button>`:""}</div>
        ${PR.bekleyen.length ? `<div class="ibas">Bekleyen emirler</div>${PR.bekleyen.map(x=>`<div class="ibek"><span>${x.tip=="LIMIT"?"Limit":x.tip} ${x.yon=="BUY"?"alış":"satış"}, ${x.adet} @ ${fg(x.fiyat)}</span>${x.panel ? `<button class="ibx" onclick="islEmirIptalOnay('${x.orderId}','${x.yon}',${x.adet},${x.fiyat})">İptal</button>` : "<span class='k'>bot / uygulama</span>"}</div>`).join("")}` : ""}
        ${ISL.pd ? islPdHtml() : islParcaHtml()}`;
    } else if (PR && !PR.hata){
      const riskMod = I.boyut=="risk", tpslAcik = I.tpsl || riskMod;
      h += `<div class="iseg yon">${seg("yon","L","Long","L")}${seg("yon","S","Short","S")}</div>
        <div class="isat"><span class="ibas">Emir tipi</span><div class="ichip kisa">${seg("tip","MARKET","Piyasa")}${seg("tip","LIMIT","Limit")}</div></div>
        ${I.tip=="LIMIT" ? `<input inputmode="decimal" placeholder="Limit fiyatı (şimdi ${fg(PR.isaret)})" aria-label="Limit fiyatı" value="${islGos(I.fiyat)}" oninput="islAyar('fiyat',this.value)">` : ""}
        <div class="isat"><span class="ibas">Boyut${(ELLE_OZ && ELLE_OZ.hesap && ELLE_OZ.hesap.bosta!=null) ? ` <span class="k" style="font-weight:500">· boşta ${para(ELLE_OZ.hesap.bosta)}</span>` : ""}</span><div class="ichip kisa">${seg("boyut","usd","Tutar")}${seg("boyut","risk","Risk")}</div></div>
        ${riskMod ? `<div class="ipara"><input inputmode="decimal" aria-label="Risk tutarı" value="${islGos(I.risk)}" oninput="islAyar('risk',this.value)"><span>$ risk</span></div>
            <div class="ichip">${[2,5,10,20].map(v=>`<button class="${+I.risk==v?"on":""}" onclick="islAyar('risk',${v});islCiz()">${v} $</button>`).join("")}</div>
            <p class="ion k">Stop'a kadar en fazla bu kadar kaybedersin; pozisyon büyüklüğü buna göre hesaplanır.</p>`
          : `<div class="ipara"><input inputmode="decimal" aria-label="Tutar" value="${islGos(I.usd)}" oninput="islAyar('usd',this.value)"><span>$</span></div>
            <div class="ichip">${[25,50,100,200].filter(v=>v<=(D.max_usd||200)).map(v=>`<button class="${+I.usd==v?"on":""}" onclick="islAyar('usd',${v});islCiz()">${v} $</button>`).join("")}</div>`}
        ${varPoz ? (riskMod ? `<input inputmode="decimal" placeholder="Stop fiyatı (risk buna göre)" aria-label="Stop fiyatı" value="${islGos(I.sl)}" oninput="islAyar('sl',this.value)">${hz("sl",[3,5,10])}` : "")
            + `<p class="ion k">Ekleme sonrası mevcut TP / stop toplam adede göre güncellenir; fiyatlarını Pozisyon'dan değiştirirsin.</p>`
          : `<button class="iacil ${tpslAcik?"on":""}" onclick="ISL.tpsl=!ISL.tpsl;ISL.oniz=null;islCiz()" ${riskMod?"disabled":""}><span>TP / stop ekle</span><i class="${tpslAcik?"":"oner"}">${tpslAcik?"açık":"kapalı · stop önerilir"}</i></button>
            ${tpslAcik ? `<div class="iki"><div><input inputmode="decimal" placeholder="TP fiyatı" aria-label="TP fiyatı" value="${islGos(I.tp)}" oninput="islAyar('tp',this.value)">${hz("tp",[3,5,10])}</div>
              <div><input inputmode="decimal" placeholder="Stop fiyatı" aria-label="Stop fiyatı" value="${islGos(I.sl)}" oninput="islAyar('sl',this.value)">${hz("sl",[3,5,10])}</div></div>` : ""}`}
        <div id="isluyr">${islUyari()}</div><div id="isltah">${islTahminMetin()}</div>`;
    }
  }
  if (I.msj && I.adim) h += islMsjHtml();
  if (!I.adim) h += islAlmHtml();   // madde 900
  if (!I.adim) h += `<div class="idonk"><button class="idonb" onclick="ISL.donAc=!ISL.donAc;islCiz()" aria-expanded="${!!ISL.donAc}"><span>${ISL.donAc?"▾":"▸"} Fiyat değişimleri</span><span class="k">24 sa · 3 gün · 1 hafta · 1 ay</span></button>${ISL.donAc ? donemHtml(I.s, f) : ""}</div>`;
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
  return `<div class="fund"><span class="${v<=-ec?'eks':'uyr'}">stop: 24 sa ${(v*100).toFixed(1).replace(".",",")}% / eşik −\u2060%${Math.round(ec*100)}</span> · piyasa ${D.piyasa_sart?'<b class="eks">şart var</b>':'şart yok'}</div>`;
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
  const A = Object.entries(k.pozisyonlar||{}).filter(([s])=>!elleMi(k, s)).map(([s,p])=>{   // madde 849: yalnız bot
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
    if (elleMi(k, s)) continue;   // madde 849: elle pozisyon botun kâr/zararına girmez
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
// madde 888: "canlı" göstergesi o an EKRANDAKİ verinin kaynağına bakar (eskiden Al-Sat'ta da botun akışına bakıyordu):
// bot -> bot akışı; Al-Sat Piyasa -> piyasa akışı; Pozisyonlarım/Geçmiş -> al-sat fiyat akışı (pozisyon yoksa kapı yanıtı).
// Akış 5 sn'den fazla susarsa sarı "N sn önce", 60 sn'yi geçerse kırmızı "bağlantı yok".
function canliKaynak(){
  if (ALAN != "alsat") return [wsZaman, 5000];
  if (sayfa == "piyasa") return [PIY_ZAMAN, 10000];
  if (AS_WSK) return [AS_ZAMAN || 0, 5000];
  return [ELLE_OZ && !ELLE_OZ.hata && !ELLE_OZ.baglanti ? (elleYukle.t || 0) : 0, 40000];
}
function canliDurum(){
  const [z, esik] = canliKaynak(), g = Date.now() - z, on = !VERI_GOMULU && z > 0 && g < esik, e = $("#canliust");
  const metin = on ? "canlı" : VERI_GOMULU ? (VERI ? VERI.uretim.slice(11) : "") : !z ? "bağlanıyor" : g < 60e3 ? `${Math.round(g/1000)} sn önce` : "bağlantı yok";
  if (e){ e.className = "canli" + (on ? " on" : z && g >= 60e3 ? " yok" : z ? " gec" : ""); e.lastElementChild.textContent = metin; }
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
  const P = Object.entries(k.pozisyonlar||{}).filter(([s])=>!elleMi(k, s)); let T = null;   // madde 849: yalnız bot
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
  kayIsaret();   // madde 890 (yeniden çizimden sonra da doğru kalsın; iki öğe, ucuz)
  if (ISL && Date.now() - (islGrafikCiz.t||0) > 2000){ islGrafikCiz.t = Date.now(); islGrafikCiz(); if (Date.now() - ((MUMI[ISL.s+"|"+ISL.aralik]||{}).t||0) > 60e3) islMumYukle(); }   // madde 835
  if (ISL && !ISL.adim && Date.now() - (donemBoya.t||0) > 5000){ donemBoya.t = Date.now(); donemBoya(ISL.s); }   // madde 848
  asCanliBoya();   // madde 856
  almCanliBoya();   // madde 900
  if (ALAN != "alsat") asAkisBagla();   // madde 906 (Al-Sat'ta asCanliBoya bağlar)
  riskDenetle();   // madde 906
  piyasaBoya(false);   // madde 832
  if (sayfa != "piyasa" && ISL_DURUM && ISL_DURUM.acik && Date.now() - (elleYukle.t||0) > 15e3) elleYukle();   // madde 844
  fundTakip();
  const on = canliDurum();
  const k = VERI && VERI.kurulumlar[secili]; if (!k) return;
  const ds = $("#dilimsure"); if (ds) ds.innerHTML = dilimKart(k.dilim);
  const dd2 = $("#dilimd"); if (dd2) dd2.innerHTML = dilimMetin(k.dilim);
  const fd2 = $("#fundd"); if (fd2) fd2.innerHTML = fundMetin(k);
  const dc = $("#dcumle"); if (dc) dc.innerHTML = durumCumle(k);
  const fk = $("#fundsure"); if (fk) fk.innerHTML = fundKart(k);
  mumYukle(k);
  let top = 0; const taraf = {L:[0,0], S:[0,0]}, eT = [0,0];
  for (const [s,p] of Object.entries(k.pozisyonlar||{})){
    const f = FIYAT[s], ok = k.poz_kaynak=="canlı" && f && p.giris>0 && p.miktar;
    const g = ok ? p.miktar * (f - p.giris) : (p.gerceklesmemis||0), el = elleMi(k, s);   // madde 849
    if (!el){ top += g; const t = taraf[p.yon] || taraf.L; t[0] += ok ? Math.abs(p.miktar)*f : (p.usd||0); t[1] += g; }
    else { eT[0] += ok ? Math.abs(p.miktar)*f : (p.usd||0); eT[1] += g; }
    const et = document.getElementById("t-"+s); if (et) et.innerHTML = et.classList.contains("drow") ? satirD(s, p, k) : et.classList.contains("sat") ? satirIc(s, p, k) : kutuIc(s, p, k);
  }
  for (const y of ["L","S"]){ const e = document.getElementById("taraf-"+y); if (e) e.innerHTML = `${para(taraf[y][0])} · <span class="${sinif(taraf[y][1])}">${taraf[y][1]>=0?"▲":"▼"}\u00a0${isaretli(taraf[y][1])}</span>`; }
  { const e = document.getElementById("taraf-E"); if (e) e.innerHTML = `${para(eT[0])} · <span class="${sinif(eT[1])}">${eT[1]>=0?"▲":"▼"}\u00a0${isaretli(eT[1])}</span>`; }
  if (SHEET){ const si = $("#sheetic"), sp = (k.pozisyonlar||{})[SHEET]; if (si && sp) si.innerHTML = sheetIc(SHEET, sp, k); else if (!sp) sheetKapat(); }
  if (sayfa=="gecmis"){ const gs = $("#gsade"); if (gs) gs.innerHTML = gecmisSade(k); }   // madde 757: geçmiş de saniyelik canlı
  const dn = $("#denge"); if (dn) dn.innerHTML = dengeIc(taraf);
  const ih = $("#isi"); if (ih){ ih.innerHTML = isiHarita(k); isiSigdir(); }
  const eg2 = $("#egri"); if (eg2) eg2.innerHTML = egriIc(k);
  if (k.poz_kaynak!="canlı") return;
  const fark = top - (k.gerceklesmemis||0), eg = $("#gerc");
  if (eg){ eg.textContent = `${top>=0?"▲":"▼"}\u00a0${isaretli(top)}`; eg.className = sinif(top); }
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
  // madde 742: "koşullu stop %3" pozisyon %3 zararda kapanır sanılıyordu. Kural: coin 24 sa'te −\u2060%45 VE piyasa medyanı −\u2060%3.
  const ce = A.coin_esik!=null ? A.coin_esik : 0.45;
  const st = A.stop!=null ? `stop: coin −\u2060%${Math.round(ce*100)} ve piyasa −\u2060%${Math.round(A.stop*100)}` : "koşullu stop yok";
  const ac = A.stop!=null ? `24 saatlik koşullu stop: long, coin 24 saatte −\u2060%${Math.round(ce*100)} düştüğünde VE piyasanın ortanca 24 sa getirisi −\u2060%${Math.round(A.stop*100)} ya da daha kötüyken kapanır. Tek coin çöküşünde (piyasa sakinken) kapanmaz.` : "";
  return `<div class="d">${ad} · ${A.gross.toFixed(2).replace(".",",")}x</div><span class="k" style="white-space:normal" title="${ac}">${st}</span>${stopDurum(k)}`;
}
// MADDE 753: koşullu stop şu an ne kadar yakın — piyasa medyanı (botun evreni, son kapanmış 4 sa mumu) ve eşiğe en yakın long'lar
function stopDurum(k){
  const D = k.stop_durum; if (!D || D.kapali || !k.ayar || k.ayar.stop==null) return "";
  const ep = D.esik_piyasa, ec = D.esik_coin, med = D.medyan;
  const pyz = v => v==null ? "—" : (v>=0?"+":"−") + "\u2060%" + Math.abs(v*100).toFixed(1).replace(".",",");
  const yakin = Object.entries(D.coin||{}).filter(([,v])=>v <= -ec*0.5).sort((a,b)=>a[1]-b[1]).slice(0,3);
  const ps = D.piyasa_sart ? `<b class="eks">şart var</b>` : `<span class="art">şart yok</span>`;
  const cl2 = yakin.length ? yakin.map(([s,v])=>`<span class="${v<=-ec?'eks':'uyr'}">${s} ${pyz(v)}</span>`).join(", ") + ` / −\u2060%${Math.round(ec*100)}` : "eşiğe yakın long yok";
  return `<div class="k" style="white-space:normal;margin-top:3px;line-height:1.45" title="Bot her dilim turunda bakar. Long, coin 24 sa ≤ −\u2060%${Math.round(ec*100)} VE piyasa medyanı ≤ −\u2060%${Math.round(ep*100)} ise kapanır. Ölçüm saatte bir (botla aynı yöntem: son kapanmış 4 sa mumu, ${D.n} coinlik evren).">piyasa ${pyz(med)} / −\u2060%${Math.round(ep*100)} · ${ps}<br>${cl2} <span style="opacity:.7">· ${D.saat_ad}${D.bayat?" ESKİ":""}</span></div>`;
}
function dilimKart(D){
  if (!D) return `<div class="d">—</div>`;
  const kalan = D.zaman - Date.now()/1000;
  const sure = kalan <= 0 ? (kalan > -1800 ? "şimdi" : "gecikti") : (kalan >= 3600 ? `${Math.floor(kalan/3600)} sa ${Math.floor(kalan%3600/60)} dk` : `${Math.ceil(kalan/60)} dk`);
  return `<div class="halkali">${halka(D.dolu, D.n)}<div style="min-width:0"><div class="d ${kalan<=-1800?'eks':''}">${sure}</div><span class="k">saat ${D.saat}</span></div></div>`;
}
// madde 877: icra kartı — 4 ana gösterge kutucuk (durum rengiyle), giriş yolu tek çubuk, ayrıntı ve referans katlı
function icraKart(k){
  const I = k.icra;
  if (!I) return `<div class="k">Henüz emir kaydı yok. Bot emir gönderdikçe dolar.</div>`;
  const T = I.tp || {}, G = I.giris || {}, K = I.karar;
  const yzd = v => v==null ? "—" : "%" + (v*100).toFixed(0);
  const bp = v => v==null ? "—" : (v>=0?"+":"−") + Math.abs(v).toFixed(1).replace(".",",") + " bp";
  const dr = T.dolum_orani, kay = K ? K.bp : G.kayma_bp;
  const kutu = (ad, v, durum, alt) => `<div class="ick ${durum}"><span>${ad}</span><b>${v}</b><i>${alt}</i></div>`;
  const yol = [["ilk deneme", G.gtx_ilk||0, "ia"], ["kovalama", G.kovala||0, "ib"], ["piyasaya düştü", G.piyasa_yedek||0, "ic"]], top = yol.reduce((a,x)=>a+x[1], 0);
  const ac = ACIK.has("icra");
  return `<div class="icg">
      ${kutu("TP dolumu", yzd(dr), dr==null ? "" : dr>=0.9 ? "iyi" : dr<=0.8 ? "kotu" : "orta", dr==null ? "ölçüm yok" : dr>=0.9 ? "güvenli (≥ %90)" : dr<=0.8 ? "alarm (≤ %80)" : "izle")}
      ${kutu("Maker payı", yzd(G.maker_pay), "", "limitte dolan giriş")}
      ${kutu("Toplam kayma", bp(kay), kay==null ? "" : kay>5 ? "kotu" : kay<=0 ? "iyi" : "orta", "karar fiyatına göre · eksi iyi")}
      ${kutu("Komisyon", bp(G.komisyon_bp), G.komisyon_bp==null ? "" : G.komisyon_bp>6 ? "kotu" : "iyi", "model 5 bp")}
    </div>
    ${top ? `<div class="icy"><div class="icyb">${yol.map(([a,n,c])=>n ? `<i class="${c}" style="flex:${n}" title="${a} ${n}"></i>` : "").join("")}</div>
      <div class="icyl">${yol.map(([a,n,c])=>`<span><i class="${c}"></i>${a} <b>${n}</b> <span class="k">${yzd(n/top)}</span></span>`).join("")}</div></div>` : ""}
    <button class="nsor" style="margin-top:12px" onclick="olayAc('icra')" aria-expanded="${ac}">${ac ? "▾ ayrıntıyı gizle" : "▸ ayrıntı · nasıl okunur? ⓘ"}</button>
    ${ac ? `<div class="icd">
      <div><span>TP / kademe emri</span><b>${T.konan||0} konan · ${T.tam||0} tam · ${T.kismi||0} kısmi</b></div>
      <div><span>TP dolumu ölçümü</span><b>${T.dokunan||0} dokunan / ${T.olculen||0} ölçülen</b></div>
      <div><span>Kısmi dolum payı</span><b>${yzd(T.kismi_pay)}</b></div>
      <div><span>Kayma (gönderim fiyatına göre)</span><b>${bp(G.kayma_bp)}</b></div>
      ${K ? `<div><span>TOPLAM kayma kırılımı</span><b>ilk ${bp(K.giris)} · kovala ${bp(K.kovala)} · piyasa ${bp(K.piyasa)} <span class="k">(${K.n} dolum)</span></b></div>` : ""}
      <p class="k">TP dolumu ≥ %90 güvenli, ≤ %80 alarm (dolum %70'te yıllık −29 puan). Kayma eksi = daha iyi doldu. "Gönderim fiyatına göre" her emri
      gönderildiği anla, "karar fiyatına göre" turun ilk emrindeki fiyatla kıyaslar: beklerken fiyatın kaçması ve piyasa emrine düşme dahil, asıl maliyet bu
      (backtest girişe +5 bp varsayar). Yalnız kayıt; bot kararlarını etkilemez.</p></div>` : ""}`;
}
// MADDE 757: D TASARIMI — ÖZET. Üstte tek cümlelik durum, büyük kitap, zaman seçici grafiğin yanında, yalnız dikkat isteyen
// şey renkli kartla (varsayılan nötr), "nereden geldi" tek çubuk + 4 kalem, sıradaki dilim / funding tek satır.
function dikkatler(k){
  const out = [], sv = k.servis;
  if (sv && sv!=="active" && sv!=="—" && sv!=="?") out.push({sev:"eks", baslik:"Bot çalışmıyor", metin:`Servis durumu: ${sv}. Sunucuyu kontrol et.`});
  const D = k.stop_durum, P = k.pozisyonlar || {};
  if (D && !D.kapali){
    const ec = D.esik_coin, pyz = v => v==null ? "—" : (v>=0?"+":"−") + "\u2060%" + Math.abs(v*100).toFixed(1).replace(".",",");
    for (const [s,p] of Object.entries(P)){
      const v = (D.coin||{})[s.replace(/USDT$/,"")]; if (p.miktar<=0 || v==null || v > -ec*0.8) continue;
      const c = s.replace(/USDT$/,"");
      out.push({sev: v <= -ec ? "eks" : "uyari", sem: s, baslik:`Stop şartına yakın: ${c}`,
        metin:`Piyasa ${pyz(D.medyan)} (eşik −\u2060%${Math.round(D.esik_piyasa*100)}, ${D.piyasa_sart?"şart var":"şart yok"}). ${c} 24 saatte ${pyz(v)}; −\u2060%${Math.round(ec*100)} olursa${D.piyasa_sart?"":" ve piyasa da eşiği geçerse"} sıradaki turda kapanır.`});
    }
  }
  if (k.poz_kaynak && k.poz_kaynak!=="canlı") out.push({sev:"uyari", baslik:"Canlı pozisyon verisi yok", metin:"Pozisyonlar günlük defterden gösteriliyor (anlık görüntü servisi gecikmiş olabilir)."});
  return out;
}
function dikkatHtml(k){
  return dikkatler(k).map(d=>`<div class="ddk ${d.sev}"${d.sem?` onclick="sheetAc('${d.sem}')" role="button" tabindex="0"`:""}><div class="ddb"><b>${d.baslik}</b>${d.sem?'<span class="k">ayrıntı ›</span>':""}</div><div class="ddm">${d.metin}</div></div>`).join("");
}
function durumCumle(k){   // madde 758: kısa — bugünkü tutar hemen altta, tekrar etmez
  const sv = k.servis, ok = !sv || sv==="active" || sv==="—" || sv==="?", n = dikkatler(k).length;
  return `<span class="dnok ${ok?"":"yok"}"></span>${ok ? "Bot çalışıyor" : '<b class="eks">Bot çalışmıyor</b>'} · ${n ? `<span class="uyr">${n} konu dikkat istiyor</span>` : "her şey yolunda"}`;
}
function daltHtml(k, kar){
  const B = bugunKZ(k), ok = v => v>=0 ? "▲" : "▼", ko = k.kitap_bas ? kar / k.kitap_bas : null;
  return `${B ? `<span class="${sinif(B.usd)}">${ok(B.usd)} ${isaretli(B.usd)} (${yz(B.oran)}) bugün</span>` : ""}${kar!=null ? `<span class="${sinif(kar)}">${ok(kar)} ${isaretli(kar)}${ko!=null?` (${yz(ko)})`:""} başlangıçtan</span>` : ""}`;
}
function nerdenHtml(k, poz, kar){   // madde 872: her kalem kendi satırında, sıfır çizgisinden kazanç sağa (yeşil) kayıp sola (kırmızı)
  const D = k.dokum; if (!D || poz==null || kar==null) return "";
  const gz = FG && k.gercek && D.funding_gercek!=null, F = gz ? D.funding_gercek : D.funding, dg = D.diger_gelir||0;
  const fark = kar - poz - D.gerceklesen - F - D.komisyon - dg;
  const K = [["Kapanan", D.gerceklesen], ["Funding", F], ["Açık", poz], ["Komisyon", D.komisyon]];
  const mx = Math.max(...K.map(x=>Math.abs(x[1])), 1e-9);
  return `<div class="nrd">${K.map(([a,v])=>{ const w = Math.max(Math.abs(v) / mx * 50, Math.abs(v) >= 0.005 ? 1.5 : 0);
      return `<div class="nrr"><span class="nrl">${a}</span><span class="nrb"><i class="${v>=0?"p":"n"}" style="width:${w.toFixed(1)}%"></i></span><b class="${sinif(v)}">${isaretli(v)}</b></div>`; }).join("")}
    <div class="nrt"><span>Toplam</span><b class="${sinif(kar)}">${isaretli(kar)}</b></div></div>
    ${Math.abs(fark) >= 3 || dg ? `<div class="k" style="margin-top:6px" title="Başlangıç kaydı anı ve demo / gerçek fiyat farkı">başlangıç farkı ${isaretli(fark)}${dg?` · diğer ${isaretli(dg)}`:""}</div>` : ""}`;
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
  const A = k.ayar, ayar = A ? `profil ${A.profil||k.profil||"—"} · ${A.gross.toFixed(2).replace(".",",")}x hedef` : (k.profil||"");
  const ch = (m, ad) => `<button data-m="${m}" class="${egriMod==m?"on":""}" onclick="egriSec('${m}')">${ad}</button>`;
  return `<div class="dhero">
    <div class="dcumle" id="dcumle">${durumCumle(k)}</div>
    <div class="dbuyuk" id="kitapd">${para(AKIS.kitapd.v)}</div>
    <div class="dalt" id="dalt">${daltHtml(k, k.kar_usd)}</div>
    <div class="dgr"><div class="mod">${ch("bugun","1G")}${ch("hafta","1H")}${ch("tum","Tümü")}</div><div id="egri">${egriIc(k)}</div></div>
  </div>
  <div id="dikkat">${dikkatHtml(k)}</div>
  ${k.dokum&&k.gerceklesmemis!=null?`<div class="kart dnerden"><div class="dnh"><span class="dnk">Başlangıçtan beri nereden geldi</span>${fgKucuk(k)}</div><div id="nerden">${nerdenHtml(k, k.gerceklesmemis, k.kar_usd)}</div></div>`:""}
  ${ozetPoz(k)}
  <div class="dikili"><div class="kart"><div class="k">Sıradaki dilim</div><div class="dkv" id="dilimd">${dilimMetin(k.dilim)}</div><div class="k">${ayar}</div></div>
    <div class="kart"><div class="k">Sıradaki funding</div><div class="dkv" id="fundd">${fundMetin(k)}</div><div class="k">canlı oranla</div></div></div>`;
}
// madde 881: Özet'te pozisyon dengesi — long / short büyüklüğü tek çubukta, sayılar, net ve açık K/Z; dokununca Pozisyonlar
function ozetPoz(k){
  const P = Object.entries(k.pozisyonlar||{}); if (!P.length) return "";
  let L = 0, S = 0, nl = 0, ns = 0, g = 0;
  for (const [s, p] of P){ const d = pozDeger(s, p); if (p.miktar > 0){ L += d.usd||0; nl++; } else { S += d.usd||0; ns++; } g += d.g||0; }
  const T = L + S || 1, kit = k.kitap_canli!=null ? k.kitap_canli : k.kitap;
  return `<a class="kart opz" href="#poz" onclick="sayfaSec('poz');return false">
    <div class="opzh"><span><b>Pozisyonlar</b><span class="say">${P.length}</span></span><span class="k">açık <b class="${sinif(g)}">${isaretli(g)}</b> ›</span></div>
    <div class="opzb"><i class="l" style="flex:${L.toFixed(2)}"></i><i class="s" style="flex:${S.toFixed(2)}"></i></div>
    <div class="opzl"><span><i class="l"></i>Long ${nl} · <b>${para(L)}</b></span><span>Short ${ns} · <b>${para(S)}</b><i class="s"></i></span></div>
    <div class="k" style="margin-top:6px">net ${L>=S?"long":"short"} ${para(Math.abs(L - S))} (%${Math.round(Math.abs(L - S) / T * 100)})${kit > 0 ? ` · toplam ${((L + S) / kit).toFixed(2).replace(".",",")}x kitap` : ""}</div></a>`;
}
// MADDE 757: D TASARIMI — POZİSYONLAR. Filtre (Tümü / Long / Short) + sıralama, long ve short ayrı bölüm, satırda büyüklük,
// mini grafik ve ▲▼ kâr / zarar; dokununca alttan açılan sayfada ayrıntı (grafik, giriş, funding, hedef, stop).
let POZ_F = (()=>{ try { const f = localStorage.getItem("carry_pf") || "tum"; return f=="E" ? "tum" : f; } catch(_){ return "tum"; } })();
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
// MADDE 848: dönem özeti — 24 sa / 3 gün / 1 hafta / 1 ay / 3 ay tek bakışta (değişim, en düşük–en yüksek aralığında fiyatın yeri, minik grafik)
let DONEM = {};
const DONEM_L = [["24 sa", 24, "s"], ["3 gün", 72, "s"], ["1 hafta", 168, "s"], ["1 ay", 30, "g"], ["3 ay", 90, "g"]];
async function donemYukle(s){
  if (VERI_GOMULU) return; const D = DONEM[s]; if (D && (D.yuk || Date.now() - D.t < 300e3)) return;
  DONEM[s] = {...(D||{}), yuk: true};
  try { const [h, d] = await Promise.all(["1h&limit=168", "1d&limit=90"].map(q => fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${s}&interval=${q}`, {cache:"no-store"}).then(r => r.json())));
    DONEM[s] = Array.isArray(h) && Array.isArray(d) ? {t: Date.now(), s: h.map(x => [+x[1], +x[2], +x[3], +x[4]]), g: d.map(x => [+x[1], +x[2], +x[3], +x[4]])} : {t: Date.now() - 240e3, hata: true};
  } catch(_){ DONEM[s] = {t: Date.now() - 240e3, hata: true}; }
  donemBoya(s);
}
function donemBoya(s){ const el = document.getElementById("dnm-" + s); if (el) el.outerHTML = donemHtml(s);
  const kk = document.getElementById("dnk-" + s); if (kk) kk.innerHTML = donemKisa(s); }
// madde 878: bot pozisyon penceresinde dönem tablosu katlı; kapalıyken tek satır özet (24 sa · 1 hafta · 1 ay)
let SH_DON = (()=>{ try { return localStorage.getItem("carry_sh_don") == "1"; } catch(_){ return false; } })();
function shDon(){ SH_DON = !SH_DON; try { localStorage.setItem("carry_sh_don", SH_DON ? "1" : "0"); } catch(_){}
  if (SHEET){ const k = VERI.kurulumlar[secili], el = $("#sheetic"); if (el && k.pozisyonlar[SHEET]) el.innerHTML = sheetIc(SHEET, k.pozisyonlar[SHEET], k); } }
function donemKisa(s, f){
  f = f || (PIY[s]||{}).f || FIYAT[s]; const D = DONEM[s];
  if (!D || !D.s){ donemYukle(s); return "24 sa · 1 hafta · 1 ay"; }
  return [["24 sa", 24, "s"], ["1 hafta", 168, "s"], ["1 ay", 30, "g"]].map(([ad, n, tur]) => { const B = D[tur].slice(-n), acl = B.length ? B[0][0] : 0;
    const deg = acl > 0 && f > 0 ? (f / acl - 1) * 100 : null;
    return `${ad} <b class="${sinif(deg)}">${deg == null ? "—" : (deg >= 0 ? "+" : "−") + "\u2060%" + Math.abs(deg).toFixed(1).replace(".", ",")}</b>`; }).join(" · ");
}
function donemHtml(s, f){
  f = f || (PIY[s]||{}).f; const D = DONEM[s];
  if (!D || !D.s){ donemYukle(s); return `<div class="dnm k" id="dnm-${s}">${D && D.hata ? "dönem verisi alınamadı" : "günlük · haftalık · aylık yükleniyor…"}</div>`; }
  if (Date.now() - D.t > 300e3) donemYukle(s);
  const satir = ([ad, n, tur]) => {
    const B = D[tur].slice(-n); if (!B.length) return "";
    const son = f > 0 ? f : B[B.length-1][3], acl = B[0][0], hi = Math.max(son, ...B.map(x => x[1])), lo = Math.min(son, ...B.map(x => x[2]));
    const deg = acl > 0 ? (son / acl - 1) * 100 : null, yer = hi > lo ? (son - lo) / (hi - lo) * 100 : 50;
    const kisa = B.length < n * 0.9 ? ` <span class="k">(${tur == "g" ? B.length + " gün" : Math.round(B.length / 24) + " gün"})</span>` : "";
    const C = B.map(x => x[3]); C[C.length-1] = son; const cl = Math.min(...C), ch = Math.max(...C);
    const yol = C.map((v, i) => `${i ? "L" : "M"}${(1 + i / Math.max(1, C.length - 1) * 58).toFixed(1)} ${(21 - (ch > cl ? (v - cl) / (ch - cl) : .5) * 18).toFixed(1)}`).join("");
    return `<div class="dnr"><span class="dna">${ad}${kisa}</span>
      <b class="${sinif(deg)}">${deg == null ? "—" : (deg >= 0 ? "+" : "−") + "\u2060%" + Math.abs(deg).toFixed(1).replace(".", ",")}</b>
      <span class="dnz"><span class="dnb"><i style="left:${yer.toFixed(0)}%"></i></span><span class="dnu"><span>${piyFiyat(lo)}</span><span>${piyFiyat(hi)}</span></span></span>
      <svg viewBox="0 0 60 24" class="dns" aria-hidden="true"><path d="${yol}" fill="none" stroke="${css(deg >= 0 ? "--art" : "--eks")}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></div>`; };
  return `<div class="dnm" id="dnm-${s}"><div class="dnh"><span>Dönem</span><span>değişim</span><span>en düşük · <b>şimdi</b> · en yüksek</span><span></span></div>${DONEM_L.map(satir).join("")}</div>`;
}
// MADDE 842: elle coin mü (coin_ozet "elle" bayrağı: carry_elle.json + panel işaretleri)
function elleMi(k, s){ return !!(k && k.pozisyonlar && k.pozisyonlar[s] && (k.pozisyonlar[s].elle_canli || k.pozisyonlar[s].elle)); }   // madde 851: anlık görüntü bayrağı
function elleKutu(s, p, f){   // madde 846: tek cümle + tek düğme
  return `${ellePayHtml(s, p, f)}<div class="elk">✋ <b>Bunu sen yönetiyorsun.</b> Bot bu coine dokunmuyor: kâr al, stop ya da süre yok. Tamamen kapatınca 30 dk sonra coin bota döner.
    ${typeof islAc === "function" && ISL_DURUM && ISL_DURUM.acik ? `<button class="elkb" onclick="sheetKapat();islAc('${s}')">Kapat · TP · stop koy</button>` : ""}</div>`;
}
function satirD(s, p, k){
  const {f, ky, g, usd} = pozDeger(s, p), renk = css((g||0) >= 0 ? "--art" : "--eks"), sv = stopYakin(k, s, p), ec = (k.stop_durum||{}).esik_coin;
  const pc = v => (v>=0?"+":"−") + Math.abs(v).toFixed(1).replace(".",",") + "%";
  return `${coinIkon(s.replace(/USDT$/,""), "dik")}<div class="dc"><div class="da"><b>${s.replace(/USDT$/,"")}</b>${elleMi(k, s)?`<span class="dst" title="elle yönetiyorsun — bot dokunmuyor">✋ elle</span>`:""}${sv!=null && !elleMi(k, s)?`<span class="dst ${sv<=-ec?"e":""}">stop ${(sv*100).toFixed(1).replace(".",",")} / −${Math.round(ec*100)}</span>`:""}</div><div class="du">${para(usd)}</div></div>
    ${minik(s, p, f, renk)}<div class="dv"><b class="${sinif(g)}">${g==null?"—":(g>=0?"▲ ":"▼ ")+isaretli(g)}</b><span class="${sinif(ky)}">${ky==null?"":pc(ky)}</span></div>`;
}
function pozSayfa(k){
  const PT = Object.entries(k.pozisyonlar||{}).map(([s,p])=>[s, p, pozDeger(s,p)]);
  const P = PT.filter(x=>!elleMi(k, x[0])), PE = PT.filter(x=>elleMi(k, x[0]));   // madde 849: elle pozisyonlar botun toplamına girmez
  const sira = (A) => A.sort((a,b)=> POZ_S=="kz" ? (a[2].g||0) - (b[2].g||0) : (b[2].usd||0) - (a[2].usd||0));
  const L = sira(P.filter(x=>x[1].yon=="L")), S = sira(P.filter(x=>x[1].yon=="S")), E = sira(PE);
  const top = (A, i) => A.reduce((a,x)=>a+(i ? (x[2].g||0) : (x[2].usd||0)), 0), tum = top(P,1);
  const bolum = (A, y, ad) => !A.length || (POZ_F!="tum" && POZ_F!=y) ? "" : `<div class="dbol"><span>${ad} · ${A.length} · <span id="taraf-${y}">${para(top(A,0))} · <span class="${sinif(top(A,1))}">${top(A,1)>=0?"▲":"▼"}\u00a0${isaretli(top(A,1))}</span></span></span></div>
    <div class="dlis">${A.map(x=>`<div class="drow ${y}" id="t-${x[0]}" onclick="sheetAc('${x[0]}')" role="button" tabindex="0">${satirD(x[0], x[1], k)}</div>`).join("")}</div>`;
  const fb = (f, ad) => `<button class="${POZ_F==f?"on":""}" onclick="pozFiltre('${f}')">${ad}</button>`;
  return `<div class="kart dpoz">
    <div class="dpb"><span class="gb">Pozisyonlar</span>${k.gerceklesmemis!=null?`<b id="gerc" class="${sinif(tum)}">${tum>=0?"▲":"▼"}\u00a0${isaretli(tum)}</b>`:""}</div>
    ${P.length?`<div class="denge" id="denge">${dengeIc({L:[top(L,0),0], S:[top(S,0),0]})}</div>`:""}
    <div class="dfil"><div class="gdon">${fb("tum",`Tümü ${P.length}`)}${fb("L","Long")}${fb("S","Short")}</div><button class="dsir" onclick="pozSira()" aria-label="sıralama: ${POZ_S=="kz"?"kâr / zarar":"büyüklük"}">↕ ${POZ_S=="kz"?"K/Z":"büyüklük"}</button></div>
    ${bolum(L,"L","LONG") + bolum(S,"S","SHORT") || "<div class='bos'>açık pozisyon yok</div>"}
    <div class="k" style="margin-top:10px">${k.poz_kaynak=="canlı"?"liste "+k.poz_zaman:"günlük defter "+(k.poz_zaman||"")} · satıra dokun: grafik, giriş, funding, hedef, stop</div></div>`;
}
// MADDE 757: pozisyon ayrıntısı — alttan açılan sayfa (bottom sheet); canlı fiyatla saniyede bir güncellenir
let SHEET = null;
function sheetAc(s){ SHEET = s; const k = VERI.kurulumlar[secili]; if (!k.pozisyonlar[s]) return;
  // madde 845: elle coin ayrıntısı açılınca alış fiyatı / dolumlar hemen tazelenir
  if (elleMi(k, s) && ISL_DURUM && ISL_DURUM.acik && Date.now() - (elleYukle.t||0) > 5e3) elleYukle();
  const el = $("#sheet"); el.hidden = false; el.innerHTML = `<div class="shb" onclick="sheetKapat()"></div><div class="shp" role="dialog" aria-label="${s.replace(/USDT$/,"")} ayrıntı"><div class="shh"></div><div id="sheetic">${sheetIc(s, k.pozisyonlar[s], k)}</div></div>`; document.body.style.overflow = "hidden"; }
function sheetKapat(){ SHEET = null; CIKIS_TUM = false; const el = $("#sheet"); el.hidden = true; el.innerHTML = ""; document.body.style.overflow = ""; }
addEventListener("keydown", e=>{ if (e.key === "Escape" && SHEET) sheetKapat(); });
function sheetIc(s, p, k){
  const {f, ky, g, usd} = pozDeger(s, p), renk = css((g||0) >= 0 ? "--art" : "--eks"), uzun = p.miktar > 0;
  const M = MUM[s], acilis = M && M.bas===gunBasi() && M.nok.length ? M.nok[0][1] : null, bg = acilis && f ? (f/acilis - 1) : null;
  const W = Math.max(240, Math.min(560, innerWidth) - 48);
  const F = FUND[s], fr = F && p.miktar ? -p.miktar * f * F.r : null;
  const D = k.stop_durum, sv = uzun && D && !D.kapali ? (D.coin||{})[s.replace(/USDT$/,"")] : null, ec = D ? D.esik_coin : 0.45;
  const pyz = v => v==null ? "—" : (v>=0?"+":"−") + "\u2060%" + Math.abs(v*100).toFixed(1).replace(".",",");
  const kutu = (e, d) => `<div class="shk"><div class="k">${e}</div><div class="shd">${d}</div></div>`;
  const elle = elleMi(k, s);   // madde 842
  const tg = elle ? null : tpGiris(k, s, p), H = (k.hedef||{})[uzun ? "L" : "S"] || [], h0 = H.length && tg>0 ? tg * (1 + (uzun?1:-1) * H[0]) : null;
  const h1 = H.length > 1 && tg>0 ? tg * (1 + (uzun?1:-1) * H[1]) : null;   // madde 790: kademe VE kâr al ayrı
  const stop = sv==null || elle ? "" : `<div class="shs"><div class="shr"><span class="k">Koşullu stop · coin 24 sa</span><span>${pyz(sv)} / <b>−\u2060%${Math.round(ec*100)}</b></span></div>
      <div class="shc"><span style="width:${Math.min(100, Math.max(0, -sv/ec*100)).toFixed(0)}%;background:${css(sv<=-ec?"--eks":sv<=-ec*0.5?"--uyari":"--soluk")}"></span></div>
      <div class="shr" style="margin-top:10px"><span class="k">Piyasa medyanı 24 sa</span><span class="${D.piyasa_sart?"uyr":""}">${pyz(D.medyan)} / −\u2060%${Math.round(D.esik_piyasa*100)} · ${D.piyasa_sart?"şart var":"şart yok"}</span></div></div>`;
  const neden = sv!=null && !elle && sv <= -ec*0.5 ? `<p class="shn"><b>Neden hâlâ açık?</b> Stop iki şart birden sağlanınca çalışır: coin 24 saatte −\u2060%${Math.round(ec*100)} ve piyasa medyanı −\u2060%${Math.round(D.esik_piyasa*100)}. ${D.piyasa_sart ? `Piyasa şartı var, ama ${s.replace(/USDT$/,"")}'nin düşüşü henüz −\u2060%${Math.round(ec*100)}'e ulaşmadı.` : "Şu an piyasa şartı yok (tek coin düşüşü; araştırmada bu durumda tutmak daha iyi çıktı, madde 621)."} İkisi birlikte gerçekleşirse bot sıradaki dilim turunda kapatır.</p>` : "";
  return `<div class="shu"><div><div style="display:flex;align-items:center;gap:8px">${coinIkon(s.replace(/USDT$/,""), "ihik")}<span class="gb">${s.replace(/USDT$/,"")}</span><span class="dst ${uzun?"l":"s"}">${uzun?"LONG":"SHORT"}</span></div>
      <div class="shf">${fiyatYaz(f)}</div><div style="font-weight:600;font-size:13.5px"><span class="k" style="font-weight:500">pozisyon</span> <span class="nw ${sinif(g)}">${g>=0?"▲":"▼"} ${ky==null?"":(ky>=0?"+":"−")+Math.abs(ky).toFixed(1).replace(".",",")+"%"} · ${isaretli(g)}</span>${bg!=null?` <span class="nw"><span class="k" style="font-weight:500">· coin bugün</span> <span class="${sinif(bg)}">${yz(bg)}</span></span>`:""}</div></div>
      <button class="shx" onclick="sheetKapat()" aria-label="Kapat">✕</button></div>
    <div class="shg">${kivilcim(s, p, f, renk, W, 110)}</div>
    <div class="idonk shdk"><button class="idonb" onclick="shDon()" aria-expanded="${SH_DON}"><span>${SH_DON?"▾":"▸"} Fiyat değişimi</span><span class="k" id="dnk-${s}">${SH_DON ? "" : donemKisa(s, f)}</span></button>${SH_DON ? donemHtml(s, f) : ""}</div>
    <div class="shkg">${kutu("Giriş", fiyatYaz(p.giris))}${kutu("Büyüklük", para(usd))}${kutu("Funding", F ? `%${(F.r*100).toFixed(4).replace(".",",")}<br><span class="${sinif(fr)}" style="font-size:12.5px">${fr>=0?"alıyor":"ödüyor"}${fr!=null ? ` · ${isaretli(fr)}` : ""}</span>` : "—")}${elle ? kutu("Yöneten", "✋ sen") : kutu(h1 ? "Kademe · kâr al" : "Kâr al hedefi", h0 ? `${fiyatYaz(h0)} <span class="k">${uzun?"+":"−"}%${Math.round(H[0]*100)}</span>${h1 ? `<br>${fiyatYaz(h1)} <span class="k">${uzun?"+":"−"}%${Math.round(H[1]*100)}</span>` : ""}` : "—")}</div>
    ${stop}${neden}${elle ? elleKutu(s, p, f) : cikisIc(s, usd, k)}`;
}
// MADDE 787: çıkış takvimi (A tasarımı) — parça parça: ne zaman alındı → ne zaman satılacak, şu anki değer ve kâr/zarar
let CIKIS_TUM = false, CIKIS_ACK = false;
function cikisAck(){ CIKIS_ACK = !CIKIS_ACK; CIKIS_TUM = !CIKIS_TUM; cikisTum(); }
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
  const satir = (t, i) => `<div style="display:flex;justify-content:space-between;gap:10px;background:var(--kart);border-radius:12px;padding:10px 12px;${i?"":"outline:1.5px solid color-mix(in srgb,var(--vurgu) 45%,transparent)"}">
      <div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:14px;font-weight:700">${t.zaman ? `${gunAd(turT(t.zaman))} ${saat(t.zaman)} turu` : "Tur saati bilinmiyor"}</span>
        <span class="k">${t.n > 1 ? `1 emir, ${t.n} dilime bölündü` : "1 emir"}${t.alis ? ` · açılış ${gunAd(turT(t.alis)).toLowerCase()} ${saat(t.alis)}` : ""}${t.giris ? ` · giriş ${fiyatYaz(t.giris)}` : ""}</span></div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px;flex:none"><span style="font-size:14px;font-weight:600">${para(t.deg)} <span class="k">· %${Math.max(1, Math.round(t.pay*100))}</span></span>
        ${t.kz==null ? "" : `<span class="${sinif(t.kz)}" style="font-size:12px;font-weight:600">${isaretli(t.kz)}</span>`}</div></div>`;
  const sinir = CIKIS_TUM ? 1e9 : 4, gor = turlar.slice(0, sinir), kalan = turlar.slice(sinir);
  const kalanDeg = kalan.reduce((a,t)=>a+t.deg,0), kalanKz = kalan.reduce((a,t)=>a+(t.kz||0),0);
  return `<div class="shs" style="margin-top:12px;padding:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><div style="font-size:16px;font-weight:700">Alımların süresi ne zaman doluyor?</div>
      <button class="nsor" onclick="cikisAck()" aria-expanded="${CIKIS_ACK}">${CIKIS_ACK ? "kapat" : "nasıl? ⓘ"}</button></div>
    ${CIKIS_ACK ? `<p class="shn" style="margin-top:6px">${ad} pozisyonu <b>${turlar.length} alımdan</b>${P.length > turlar.length ? ` (${P.length} dilim payı)` : ""} oluşuyor. ${P.length > turlar.length ? `Her alım borsaya <b>tek emir</b> olarak gider; bot onu kendi defterinde o turda yenilenen ${uzun ? "dilimlere" : "3 dilime (sıradaki + short ara dengelemesiyle 5 ve 10 tur önceki)"} paylaştırır. ` : ""}${uzun ? "Long alımların süresi <b>5 günde</b>" : "Short alımların süresi <b>40 saatte</b>"} dolar. Süresi dolan alım için bot o turda karar verir:</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
      <div class="shk"><div style="font-weight:700;font-size:13px;color:var(--art)">${ad} yine seçilirse</div><div class="k" style="margin-top:3px">alım <b>kalır</b>, hiçbir işlem olmaz, olaylarda görünmez</div></div>
      <div class="shk"><div style="font-weight:700;font-size:13px;color:var(--uyari)">seçilmezse</div><div class="k" style="margin-top:3px">o alım ${kapanis}; olaylarda "${uzun?"long":"short"} azaltıldı" yazar</div></div></div>
      <p class="shn" style="background:var(--kart);border-radius:12px;padding:10px 12px">Fiyat kademe ya da kâr al seviyesine gelirse borsadaki emir turu beklemeden, o an dolar (yukarıdaki kutu).</p>` : `<div class="k" style="margin-top:4px">${turlar.length} alım · her biri kendi turunda yeniden seçilmezse kapanır</div>`}
    <div class="cxo">
      <div><span>Sıradaki tur</span><b>${ilk.zaman ? gunAd(turT(ilk.zaman)) + " " + saat(ilk.zaman) : "—"}</b><i>1 alım · ${para(ilk.deg)}</i></div>
      <div><span>24 saat içinde</span><b>${g24.length} alım</b><i>${para(g24.reduce((a,t)=>a+t.deg,0))}</i></div>
      <div><span>Hiç seçilmezse biter</span><b>${son.zaman ? gunAd(turT(son.zaman)) + " " + saat(son.zaman) : "—"}</b><i>tüm pozisyon</i></div></div>
    <div style="height:1px;background:var(--cizgi);margin:14px 0 2px"></div>
    <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:600;color:var(--soluk)"><span>SÜRESİ DOLAN ALIM</span><span>DEĞER · K/Z</span></div>
    <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">${gor.map(satir).join("")}</div>
    ${kalan.length ? `<div class="k" style="margin-top:10px">+${kalan.length} tur daha · ${para(kalanDeg)} · <span class="${sinif(kalanKz)}">${isaretli(kalanKz)}</span></div>` : ""}
    ${turlar.length>4 ? `<button onclick="cikisTum()" style="width:100%;height:44px;margin-top:10px;border-radius:12px;border:0;background:var(--kart);color:var(--vurgu);font:inherit;font-size:14px;font-weight:600">${CIKIS_TUM ? "Daha az göster" : `${turlar.length} turun hepsini göster`}</button>` : ""}
</div>`;
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
  if (!G.length) return `<div class="kart bos">${k._bosMetin || "Henüz tamamlanmış gün yok. İlk gün sonu kaydı 03:05'te."}</div>`;
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
  const not = g => g.canli ? (k._canliNot || "canlı · yarın 03:05'te kesinleşir") : g.kesinlesiyor ? "gün kapandı · kayıt 03:05'te yazılıyor" : (g.ilk && birim=="gün") ? "başlangıç günü" : "";
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
    <div class="gust"><span class="gb">${k._baslik || "Geçmiş"}</span><div class="gdon">${dk("hafta")}${dk("ay")}${dk("tum")}</div></div>
    <div class="gk">${baslik} · toplam kâr / zarar</div>
    <div class="gt n">${top<0?"−":"+"}${Math.abs(top).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2})}\u00a0<small>$</small></div>
    <div class="go n ${sinif(top)}">${top>=0?"▲":"▼"}\u00a0%${Math.abs((oran||0)*100).toFixed(2).replace(".",",")} · ${D.length} ${birim}</div>
    <div class="gcub" style="height:${H}px"><b style="top:${sifir}px"></b>${cub}</div><div class="galt n">${alt}</div>
    <div class="gliste">${liste}</div></div>`;
}
function gecmisSayfa(k){
  const grafikVar = (k.seri||[]).length >= 3;   // madde 734/737: 1-2 noktalık grafik bilgi vermez, yalnız yer kaplar
  const ac = ACIK.has("gecay");   // madde 756: eski ayrıntılar (takvim, yıllık, grafikler, coinler, icra) kapalı bölümde
  return `<div id="gsade">${gecmisSade(k)}</div>` + `<div class="kart" style="padding:0"><button class="gayr" onclick="olayAc('gecay')">${ac?"▾":"▸"} Ayrıntılar <span class="k">takvim · coinler · icra</span></button></div>` + (!ac ? "" : `<div class="kart"><h2>Günlük takvim <span class="k">· % getiri, koyu = büyük</span></h2>${takvim(k)}
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
// madde 875: tablo yerine kart liste (Al-Sat Geçmiş'teki gibi) — telefonda yana kaydırma ve gizli sütun yok; her coin tek satır:
// logo + ad + yön, altında sıfır olmayan kalemler, sağda toplam. Varsayılan en kötü / en iyi 5.
function coinTablo(k){
  const C = k.coin_ozet; if (!C || !C.length) return "";
  const id = "coinler", ac = ACIK.has(id), S = C.slice().sort((a,b)=>a.toplam-b.toplam), uzun = S.length > 10, L = ac || !uzun ? S : [...S.slice(0,5), ...S.slice(-5)];
  const T = S.reduce((a,x)=>({kp:a.kp+x.kapanan, f:a.f+x.funding, km:a.km+x.komisyon, a:a.a+x.acik, t:a.t+x.toplam}), {kp:0,f:0,km:0,a:0,t:0});
  const kaz = S.filter(x=>x.toplam > 0.005).length;
  const h = v => `<span class="${sinif(v)}">${isaretli(v)}</span>`;
  const kal = x => [["kapanan", x.kapanan], ["funding", x.funding], ["komisyon", x.komisyon], ["açık", x.acik]].filter(([,v])=>Math.abs(v) >= 0.005);
  const sat = x => { const ad = String(x.s).replace(/USDT$/,"");
    return `<div class="acr"><span class="acn">${coinIkon(ad, "kucuk")}<b>${ea(ad)}</b>${x.yon ? `<span class="pkz sen ${x.yon}" title="${x.yon=="L"?"long":"short"} açık">${x.yon}</span>` : ""}${x.elle ? `<span class="pkz" title="elle yönetiyorsun — bot dokunmuyor">✋ elle</span>` : ""}</span>
      <span class="aca">${kal(x).map(([a,v])=>`<span class="nw">${a} ${h(v)}</span>`).join(" · ") || "—"}</span><b class="act ${sinif(x.toplam)}">${isaretli(x.toplam)}</b></div>`; };
  return `<div class="kart acl"><div class="apkh"><div><b>Coinler</b><span class="say">${S.length}</span></div><b class="${sinif(T.t)}">${isaretli(T.t)}</b></div>
    <div class="apko"><span class="art">${kaz} kârda</span><span class="eks">${S.length - kaz} zararda</span><span>başlangıçtan beri, açık pozisyon dahil</span></div>
    ${L.map((x,i)=>(!ac && uzun && i==5 ? `<div class="acay">· · ·</div>` : "") + sat(x)).join("")}
    <div class="actop"><span>Toplam</span><span class="aca">${kal({kapanan:T.kp, funding:T.f, komisyon:T.km, acik:T.a}).map(([a,v])=>`<span class="nw">${a} ${h(v)}</span>`).join(" · ")}</span></div>
    ${uzun ? `<button class="pkdaha" onclick="olayAc('${id}')">${ac ? "Yalnız en kötü / en iyi 5" : `Tüm coinler (${S.length})`}</button>` : ""}
    <div class="k" style="margin-top:8px">Kapanan, funding ve komisyon borsanın gelir kayıtlarından${k.mod=="demo"?(C.some(x=>x.funding_demo!=null)?" (funding: canlı / gerçek Binance oranlarıyla)":" (funding: demo hesabın aldığı)"):""}; açık = şu anki gerçekleşmemiş kâr / zarar.</div></div>`;
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
        <span class="ctad">${coinIkon(String(x.sembol).replace(/USDT$/,""), "kucuk")}<b>${x.sembol}</b> <span style="font-size:12px;font-weight:650;color:${L?'var(--vurgu)':'#f59e0b'}">${t.etiket || (t.yon + " " + t.ne)}</span></span>
        <span style="font-weight:650">${t.ekle?"+":"−"}${para(x.usd)}</span></div>
      <div class="s">${x.adet.toLocaleString("tr-TR",{maximumFractionDigits:4})} adet × ${fiyatYaz(x.fiyat)} · ${x.tur}${x.maker===true?" · maker":x.maker===false?" · taker":""}</div>
      <div style="font-size:12.5px;margin-top:2px">${x.kayit_yok && x.poz_sonra==null ? `<span class="s">pozisyon kaydı yok</span>` : (once!=null ? `pozisyon ${once} → <b>${sonra}</b>` : `pozisyon şimdi <b>${sonra}</b>`) + ort}${x.kapanis_kar!=null ? ` · kâr <b class="${sinif(x.kapanis_kar)}">${isaretli(x.kapanis_kar)}</b>` : ""}</div></div>`; }).join("");
  return `<div class="isl"><span class="ac" role="button" tabindex="0" aria-expanded="${ac}" onclick="olayAc('${id}')">${ac?"▾":"▸"} işlemler (${o.islem.length})</span>${ac ? `<div style="margin-top:4px">${sat}</div>` : ""}</div>`;
}
function fonTablo(o){
  const f = o.fon; if (!f || !f.coin || !f.coin.length) return "";
  const id = "fon" + o.zaman, ac = ACIK.has(id), demo = VERI.kurulumlar[secili].mod=="demo";
  const h = v => v==null ? `<span class="s">—</span>` : `<span class="${sinif(v)}">${isaretli(v)}</span>`;
  const sat = f.coin.map(c=>`<tr><td><span class="ctad">${coinIkon(String(c.s).replace(/USDT$/,""), "kucuk")}<b>${c.s}</b></span></td><td class="r">${h(c.demo)}</td>${demo?`<td class="r">${h(c.gercek)}</td>`:""}</tr>`).join("");
  return `<div class="isl"><span class="ac" role="button" tabindex="0" aria-expanded="${ac}" onclick="olayAc('${id}')">${ac?"▾":"▸"} coinler (${f.coin.length})</span>${ac ? `<table><tr class="s"><td>coin</td><td class="r">${demo?"demo hesap":"ödeme"}</td>${demo?`<td class="r">gerçek oranla</td>`:""}</tr>${sat}</table>` : ""}</div>`;
}
// madde 890: yana kayan çip satırlarında (Olaylar filtreleri, Piyasa sekmeleri) sağda devamı varsa kenar solar
function kayIsaret(){ for (const el of document.querySelectorAll(".ofil,.pksek")) el.classList.toggle("kaydevam", el.scrollWidth - el.clientWidth - el.scrollLeft > 4); }
addEventListener("scroll", e=>{ const t = e.target; if (t && t.classList && (t.classList.contains("ofil") || t.classList.contains("pksek"))) kayIsaret(); }, true);
addEventListener("resize", ()=>kayIsaret());
// madde 894: klavye — role=button olan div / span'lar Enter ya da Boşluk ile tıklanır (gerçek <button> değiller)
addEventListener("keydown", e=>{ if (e.key !== "Enter" && e.key !== " ") return; const t = e.target;
  if (!t || !t.getAttribute || t.getAttribute("role") !== "button" || /^(BUTTON|A|INPUT|SELECT|TEXTAREA)$/.test(t.tagName)) return;
  if (t.onkeydown) return;   // kendi klavye işleyicisi olanlar (pkr satırı vb.)
  e.preventDefault(); t.click(); });
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
  const esc = x => (x||"").replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/(\d) (\$|%|adet|USDT)/g, "$1\u00a0$2").replace(/(^|[\s(\/=:])([-−+])(?=[\d%])/g, "$1$2\u2060");   // madde 907: sayılar satır sonunda bölünmesin
  const T = olayIslem(k), say = {tum: T.length}; for (const o of T){ const g = OLAY_GRUP[o.tur]; if (g) say[g] = (say[g]||0) + 1; }
  // madde 882: "Tümü"de bir günün funding ödemeleri TEK satır (gün toplamı; dokununca saat saat). Funding filtresinde tek tek.
  const demo = k.mod=="demo", fTut = o => o.fon ? (demo && o.fon.gercek!=null ? o.fon.gercek : o.fon.demo) : null;
  let L = OLAY_F=="tum" ? [] : T.filter(o=>OLAY_GRUP[o.tur]===OLAY_F);
  if (OLAY_F=="tum"){ const FG_ = {};
    for (const o of T){ if (o.tur!=="funding"){ L.push(o); continue; }
      const g = (o.zaman||"").slice(0,10); let x = FG_[g];
      if (!x){ x = FG_[g] = {tur: "fgrup", zaman: o.zaman, alt: []}; L.push(x); }
      x.alt.push(o); }
    for (const x of Object.values(FG_)){ x.top = x.alt.reduce((a,o)=>a+(fTut(o)||0), 0); }
  }
  const gunTop = {}; for (const o of T){ const g = (o.zaman||"").slice(0,10), G = gunTop[g] || (gunTop[g] = {f: 0, k: 0, fv: false, kv: false});
    if (o.tur==="funding"){ G.f += fTut(o)||0; G.fv = true; } if (o.kapanis!=null){ G.k += o.kapanis; G.kv = true; } }
  const tutar = v => v==null ? "" : `<span class="otut ${sinif(v)}">${isaretli(v)}</span>`;
  let h = "", onc = null, acik = false;
  for (const o of L){
    const g = (o.zaman||"").slice(0,10);
    if (g!==onc){ if (acik) h += "</div>"; const G = gunTop[g] || {};
      h += `<div class="ogun"><span>${g?ad(g):"—"}</span><span class="ogt">${[G.fv ? `funding ${tutar(G.f)}` : "", G.kv ? `kapanış ${tutar(G.k)}` : ""].filter(Boolean).join(" · ")}</span></div><div class="okart">`; onc = g; acik = true; }
    const rk = css(OLAY_RENK[o.tur]||"--soluk");
    if (o.tur==="fgrup"){ const id = "fg" + g, ac = ACIK.has(id);
      h += `<div class="orow"><span class="onk" style="--r:${css("--art")}">$</span><div class="om">
        <div class="ob"><span>Funding · ${o.alt.length} ödeme</span><span class="oz">${tutar(o.top)}</span></div>
        <div class="oa">${demo ? "gerçek Binance oranlarıyla · " : ""}son ${(o.zaman||"").slice(11)}</div>
        <div class="isl"><span class="ac" role="button" tabindex="0" aria-expanded="${ac}" onclick="olayAc('${id}')">${ac?"▾":"▸"} ödemeler (${o.alt.length})</span>${ac ? `<div class="ofs">${o.alt.map(x=>`<div><span class="oz">${(x.zaman||"").slice(11)}</span><span>${x.fon && x.fon.saat ? `saatlik ×${x.fon.n}` : `${Math.max((x.fon||{}).gercek_n||0, (x.fon||{}).demo_n||0)} pozisyon`}</span>${tutar(fTut(x))}</div>`).join("")}</div>` : ""}</div></div></div>`;
      continue; }
    // madde 883: kapanışlı satırda tutar başlıkta (saatin yanında), kapanış ayrıntısı alt satırın başında
    const par = (o.metin||"").split(/\s*\|\s*/), bas = par[0], ap = par.slice(1), alt = [...ap.filter(x=>/kapanış/.test(x)), ...ap.filter(x=>!/kapanış/.test(x))].join(" · ");
    h += `<div class="orow" role="button" tabindex="0" onclick="if(!event.target.closest('a,button,.ac,table'))this.classList.toggle('oacik')"><span class="onk" style="--r:${rk}">${OLAY_SIMGE[o.tur]||"•"}</span><div class="om">
      <div class="ob"><span>${esc(o.tur==="tur" ? bas.replace(/ yenilendi$/, " turu") : bas)}</span><span class="oz">${o.kapanis!=null ? tutar(o.kapanis) + " · " : ""}${(o.zaman||"").slice(11)}</span></div>
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
  $("#baslik").textContent = ALAN == "alsat" ? "Al-Sat" : "Carry";
  if (ALAN == "alsat"){ const H = ELLE_OZ && ELLE_OZ.hesap; $("#alt").textContent = ISL_DURUM ? (ISL_DURUM.ayri ? `ayrı hesap · ${ISL_DURUM.mod}` : "hesap bağlanmadı") : "";
    $("#ustkitap").innerHTML = H && H.ozkaynak!=null ? `<span>${para(H.ozkaynak)}</span>` : ""; }
  else $("#ustkitap").innerHTML = `<span id="ustk">${para(AKIS.ustk.v)}</span><span id="ustkar" class="${sinif(k.kar_usd)}"> ${yz(k.kar_oran)}</span>`;
  // MADDE 740: geniş ekran (tablet / yatay): Özet sekmesinde solda özet, sağda pozisyonlar
  const genis = innerWidth >= 1000;
  piyasaBagla(sayfa=="piyasa");   // madde 832: akış yalnız Piyasa sekmesi açıkken
  const piyOdak = document.activeElement && document.activeElement.id=="piyara";
  $("#icerik").innerHTML = sayfa=="poz" ? pozSayfa(k) : sayfa=="piyasa" ? piyasaSayfa(k) : sayfa=="alsat" ? alsatSayfa(k) : sayfa=="asgecmis" ? asGecmisSayfa() : sayfa=="gecmis" ? gecmisSayfa(k) : sayfa=="olay" ? olaySayfa(k)
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
    scales:{x:{ticks:{color:sol,maxTicksLimit:innerWidth<600?4:8,maxRotation:0,autoSkip:true,callback(v){ const l = String(this.getLabelForValue(v)||"");   // madde 876: "6 Kas"
      return /^\d{4}-\d\d-\d\d/.test(l) ? `${+l.slice(8,10)} ${AYAD[+l.slice(5,7)-1].slice(0,3)}` : l; }},grid:{display:false}},y:{ticks:{color:sol},grid:{color:izg}}}};
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
// madde 867: yana kayan bir alanın (sekme satırı, süzgeç düğmeleri, etiketler, tablo, grafik) içinde başlayan kaydırma sayfa DEĞİŞTİRMEZ
function yanaKayanIcinde(el){
  if (!el || !el.closest) return false;
  if (el.closest(".yatay,.tablo,.pksek,.pkdon,.gdon,.abc,.ichip,.iseg,#sheet,svg,canvas,input,select,textarea")) return true;
  for (let p = el; p && p !== document.body; p = p.parentElement){
    if (p.scrollWidth > p.clientWidth + 2){ const o = getComputedStyle(p).overflowX; if (o == "auto" || o == "scroll") return true; } }
  return false;
}
addEventListener("touchstart", e=>{ const t = e.touches[0]; dokB = {x:t.clientX, y:t.clientY, ust: scrollY<=0, yatay: !!ISL || yanaKayanIcinde(e.target)}; }, {passive:true});
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
  // madde 856: işlem kapısı durumu + Pozisyonlarım bot verisini (≈2 sn) BEKLEMEDEN, onunla aynı anda istenir
  if (!ISL_DURUM || Date.now() - (islDurum.t||0) > 60e3){ islDurum.t = Date.now(); islDurum().then(()=>{ if (ISL_DURUM && ISL_DURUM.acik && Date.now() - (elleYukle.t||0) > 15e3) elleYukle(); }); }
  // madde 844: yeni veri gelince elle pozisyonlar yeniden birleştirilir
  try { const r = await fetch("api/veri", {cache:"no-store"}); const ilk = !VERI; VERI = gorunum(await r.json()); elleBirlestir();
    if (ilk || ALAN != "alsat" || ISL) ciz(); } catch(e){ $("#alt").textContent = "veri alınamadı"; }   // madde 856: Al-Sat'ta 60 sn'lik bot yenilemesi sayfayı baştan çizmez
  // madde 845: işlem kapısı durumu sayfa açılışında da sorulur (eskiden yalnız Piyasa sekmesinde) — yoksa elle pozisyonların alış fiyatı /
  // dolumları Piyasa açılmadan hiç yüklenmiyordu. Açıksa elle özeti hemen yüklenir.
  if (ALAN == "alsat" && !ISL && VERI && ELLE_OZ && !$("#piyelle") && sayfa == "alsat") ciz();
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

    @app.get("/ikon/<ad>.png")      # madde 870: coin logosu (sunucu indirir, diskte saklar; CSP dış resme izin vermez)
    def coin_logo(ad):
        from flask import abort, send_file
        import coin_ikon
        v = coin_ikon.ikon(ad)
        if not v:
            abort(404)
        r = send_file(v[0], mimetype=v[1], max_age=7 * 86400)
        return r

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

    @app.get("/api/islem/gecmis")
    def islem_gecmis():
        return _islem_ilet("GET", "gecmis")

    @app.get("/api/islem/pozisyon/<sem>")
    def islem_poz(sem):
        if not re.match(r"^[A-Z0-9]{2,20}USDT$", sem or ""):
            return jsonify({"ok": False, "hata": "geçersiz sembol"}), 400
        return _islem_ilet("GET", f"pozisyon/{sem}")

    @app.post("/api/islem/<yol>")
    def islem_post(yol):
        if yol not in ("onizle", "emir", "tpsl", "iz", "not", "kapat", "iptal"):
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
