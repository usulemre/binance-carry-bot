# -*- coding: utf-8 -*-
"""MADDE 670 — TELEGRAM BİLDİRİMLERİ (isteğe bağlı; ayarlanmazsa hiçbir şey yapmaz).

Telefonunuza şu durumlarda mesaj gelir:
  - bot başladı / önerilen ayar eşiği geçildi, yeniden başladı
  - koşullu 24 sa stop ya da 24 sa düşüş stop'u bir long'u kapattı (ya da KAPATAMADI)
  - delist: bir coin listeden çıkmadan kapatıldı (ya da KAPATILAMADI)
  - sağlık kapısı kapandı (edge zayıfladı)
  - tur üst üste başarısız (bağlantı, anahtar, Binance hatası)
  - her gün: özkaynak, günlük getiri, funding, komisyon, pozisyon sayısı (+ PDF rapor)
  - nabız (nabiz.py, saatlik): bot durmuş ya da 12 saattir tur atmamışsa
Kurulum (KURULUM_SUNUCU.md "Telegram"): @BotFather -> /newbot -> TOKEN; bota bir mesaj atın; chat id:
    .venv/bin/python bildirim.py --chat-id-bul
.env:  TELEGRAM_TOKEN=...   TELEGRAM_CHAT_ID=...   (isteğe bağlı CARRY_BILDIRIM_AD=demo-1)
Deneme: .venv/bin/python bildirim.py --dene

GÜVENLİK: mesajlar YALNIZ dışarı gider (bot Telegram'dan komut ALMAZ — telefon çalınsa bile kimse botu yönetemez).
Mesajda API anahtarı yoktur. Bildirim hiçbir zaman işlemi durdurmaz: her hata yutulur (en kötü ihtimalle mesaj gelmez).
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time

logger = logging.getLogger("bildirim")
API = "https://api.telegram.org/bot{token}/{metod}"
SINIR = 4000                       # Telegram 4096 karakter
DURUM_DOSYA = os.getenv("CARRY_BILDIRIM_DURUM", "bildirim_durum.json")


def ayarli() -> bool:
    return bool(os.getenv("TELEGRAM_TOKEN", "").strip() and os.getenv("TELEGRAM_CHAT_ID", "").strip())


def kurulum_adi() -> str:
    ad = os.getenv("CARRY_BILDIRIM_AD", "").strip()
    if ad:
        return ad
    kl = os.path.basename(os.getcwd().rstrip("/"))
    mod = os.getenv("BINANCE_MODE", "demo")
    return f"{kl.replace('carry-', '') if kl.startswith('carry-') else mod}"


def _durum_oku() -> dict:
    try:
        with open(DURUM_DOSYA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _durum_yaz(d: dict) -> None:
    try:
        tmp = DURUM_DOSYA + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, DURUM_DOSYA)
    except Exception:
        pass


def kisilmali(anahtar: str | None, sure_sn: float, simdi: float | None = None) -> bool:
    """Aynı anahtarlı mesaj son `sure_sn` içinde gönderildiyse True (tekrarı bastır)."""
    if not anahtar or sure_sn <= 0:
        return False
    son = _durum_oku().get(anahtar)
    return son is not None and (simdi or time.time()) - float(son) < sure_sn


def _isaretle(anahtar: str | None, simdi: float | None = None) -> None:
    if not anahtar:
        return
    d = _durum_oku()
    d[anahtar] = simdi or time.time()
    # eski anahtarları temizle (30 gün)
    sinir = (simdi or time.time()) - 30 * 86400
    _durum_yaz({k: v for k, v in d.items() if float(v) >= sinir})


def gonder(metin: str, dosya: str | None = None, anahtar: str | None = None, kisma_sn: float = 0,
           acil: bool = False, _requests=None) -> bool:
    """Mesaj (ve isteğe bağlı dosya) gönderir. Ayarsızsa / kısılmışsa / hata olursa False; ASLA istisna fırlatmaz."""
    try:
        if not ayarli() or kisilmali(anahtar, kisma_sn):
            return False
        req = _requests
        if req is None:
            import requests as req
        token = os.getenv("TELEGRAM_TOKEN").strip(); chat = os.getenv("TELEGRAM_CHAT_ID").strip()
        bas = ("🚨 " if acil else "") + f"[{kurulum_adi()}] "
        govde = (bas + metin)[:SINIR]
        if dosya and os.path.exists(dosya):
            with open(dosya, "rb") as f:
                r = req.post(API.format(token=token, metod="sendDocument"),
                             data={"chat_id": chat, "caption": govde[:1000]},
                             files={"document": (os.path.basename(dosya), f)}, timeout=30)
        else:
            r = req.post(API.format(token=token, metod="sendMessage"),
                         data={"chat_id": chat, "text": govde, "disable_notification": not acil,
                               "disable_web_page_preview": True}, timeout=10)
        ok = getattr(r, "status_code", 0) == 200
        if ok:
            _isaretle(anahtar)
        else:
            # token'ı loga YAZMA (hata gövdesi token içermez; URL içerir -> URL'yi yazmıyoruz)
            logger.warning("telegram bildirimi gönderilemedi (HTTP %s)", getattr(r, "status_code", "?"))
        return ok
    except Exception as e:
        logger.warning("telegram bildirimi gönderilemedi (%s)", type(e).__name__)
        return False


def dis_nabiz(basarisiz: bool = False, mesaj: str = "", _requests=None) -> bool:
    """MADDE 680: DIŞ NABIZ (healthchecks.io ya da uyumlu servis). Bot her turdan sonra CARRY_HC_URL'ye ping atar; servis belirlenen
    sürede ping görmezse (sunucu çöktü / kapandı / internet gitti / bot takıldı) SİZE kendisi haber verir — sunucu içindeki nabız
    sunucu ölünce uyarı gönderemez, bu gönderir. Başarısız turda <url>/fail. Ayarsızsa hiçbir şey yapmaz; asla hata fırlatmaz."""
    try:
        url = os.getenv("CARRY_HC_URL", "").strip().rstrip("/")
        if not url.startswith("https://"):
            return False
        req = _requests
        if req is None:
            import requests as req
        r = req.post(url + ("/fail" if basarisiz else ""), data=mesaj[:1000].encode("utf-8"), timeout=10)
        return getattr(r, "status_code", 0) == 200
    except Exception:
        return False


def gunluk_ozet_metni(k: dict) -> str:
    """carry_gunluk_defter.topla() kaydından kısa günlük özet."""
    g = k.get("gun_getiri")
    gs = "—" if g is None else f"{g * 100:+.2f}%"
    gel = k.get("gelir_24s", {})
    poz = k.get("pozisyonlar", {}) or {}
    nl = sum(1 for v in poz.values() if v.get("yon") == "L"); ns = sum(1 for v in poz.values() if v.get("yon") == "S")
    dg = k.get("degisim", {}) or {}
    s = (f"📒 {k.get('tarih')} günlük\n"
         f"kitap {k.get('kitap', k.get('ozkaynak', 0)):,.2f} $ · gün {gs}\n"
         f"funding {gel.get('FUNDING_FEE', 0):+.2f} $ · gerçekleşen {gel.get('REALIZED_PNL', 0):+.2f} $ · "
         f"komisyon {gel.get('COMMISSION', 0):+.2f} $\n"
         f"pozisyon {nl} long / {ns} short · ayar {k.get('profil')} {k.get('doz')}x")
    if abs(gel.get("TRANSFER", 0) or 0) > 0.005:
        s += f"\ntransfer {gel['TRANSFER']:+.2f} $ (getiriye sayılmadı)"
    if dg.get("acilan") or dg.get("kapanan"):
        s += f"\naçılan: {', '.join(dg.get('acilan', [])) or '—'} · kapanan: {', '.join(dg.get('kapanan', [])) or '—'}"
    return s


def _chat_id_bul() -> int:
    import requests
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_TOKEN .env'de yok"); return 1
    r = requests.get(API.format(token=token, metod="getUpdates"), timeout=10).json()
    ids = {(u.get("message") or {}).get("chat", {}).get("id") for u in r.get("result", [])} - {None}
    if not ids:
        print("mesaj bulunamadı: Telegram'da botunuza bir mesaj (ör. 'merhaba') atıp tekrar deneyin"); return 1
    for i in ids:
        print(f"TELEGRAM_CHAT_ID={i}")
    return 0


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    if "--chat-id-bul" in sys.argv:
        sys.exit(_chat_id_bul())
    if "--dene" in sys.argv:
        if not ayarli():
            print("TELEGRAM_TOKEN / TELEGRAM_CHAT_ID .env'de yok"); sys.exit(1)
        ok = gonder(f"✅ deneme mesajı — {socket.gethostname()} bildirimleri çalışıyor")
        print("gönderildi" if ok else "GÖNDERİLEMEDİ (token / chat id / internet)"); sys.exit(0 if ok else 1)
    print(__doc__)
