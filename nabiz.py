# -*- coding: utf-8 -*-
"""MADDE 670 — NABIZ: bot çalışıyor mu? (saatlik; carry-nabiz.timer). Sorun varsa Telegram'a ACİL mesaj, düzelince "düzeldi".

Her kurulum için (/opt/carry ve /opt/carry-*/):
  1) servis etkin ama ÇALIŞMIYOR (çöktü / durduruldu)           -> uyarı
  2) servis çalışıyor ama CARRY_NABIZ_SAAT (12) saattir tur yok  -> uyarı (takıldı / ağ yok / Binance reddediyor)
Ayrıca disk %90 doluysa uyarı (log / defter yazılamazsa bot da durur).
Bot 8 saatte bir tur atar; 12 saat eşiği bir turun kaçmasına tolerans tanır. Aynı sorun için en çok 12 saatte bir mesaj.
Servisi BİLEREK durduruyorsanız `sudo systemctl disable --now carry` yapın: devre dışı servis için uyarı gelmez.
Anahtarı henüz girilmemiş (.env'de BURAYA) kurulum atlanır. Telegram ayarı her kurulumun .env'inden okunur (YALNIZ TELEGRAM_*).
Elle:  sudo -u carry /opt/carry/.venv/bin/python /opt/carry/nabiz.py --yazdir
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import time

ESIK_SAAT = float(os.getenv("CARRY_NABIZ_SAAT", "12"))
KISMA_SN = 12 * 3600
TAZE_DOSYALAR = ("carry_equity.csv", "carry_bot.log", "carry_dilimler.json")


def env_oku(klasor: str) -> dict:
    d = {}
    try:
        for l in open(os.path.join(klasor, ".env"), encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1); d[k.strip()] = v.split("#")[0].strip()
    except OSError:
        pass
    return d


def kurulumlar(kok: str = "/opt") -> list[tuple[str, str]]:
    """(klasör, servis adı)."""
    out = []
    if os.path.exists(os.path.join(kok, "carry", "carry_bot.py")):
        out.append((os.path.join(kok, "carry"), "carry"))
    for d in sorted(glob.glob(os.path.join(kok, "carry-*"))):
        if os.path.exists(os.path.join(d, "carry_bot.py")):
            out.append((d, "carry@" + os.path.basename(d)[len("carry-"):]))
    return out


def _systemctl(komut: str, servis: str) -> str:
    try:
        return subprocess.run(["systemctl", komut, servis], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "?"


def son_tur_saat(klasor: str, simdi: float | None = None) -> float | None:
    """En taze çalışma dosyasının yaşı (saat); hiçbiri yoksa None."""
    m = [os.path.getmtime(os.path.join(klasor, f)) for f in TAZE_DOSYALAR if os.path.exists(os.path.join(klasor, f))]
    return None if not m else ((simdi or time.time()) - max(m)) / 3600.0


def kontrol(klasor: str, servis: str, systemctl=_systemctl, simdi: float | None = None) -> list[str]:
    """Sorun listesi (boş = sağlıklı). Atlanacak kurulumda None değil [] döner."""
    e = env_oku(klasor)
    if e.get("BINANCE_API_KEY", "BURAYA") in ("", "BURAYA"):
        return []
    if systemctl("is-enabled", servis) not in ("enabled", "enabled-runtime"):
        return []
    sorun = []
    durum = systemctl("is-active", servis)
    if durum != "active":
        sorun.append(f"servis {servis} ÇALIŞMIYOR ({durum}) — journalctl -u {servis} -n 50")
    else:
        y = son_tur_saat(klasor, simdi)
        if y is not None and y > ESIK_SAAT:
            sorun.append(f"{y:.0f} saattir tur yok (eşik {ESIK_SAAT:.0f} sa) — bot takılmış olabilir: journalctl -u {servis} -n 50")
    return sorun


def disk_sorunu(yol: str = "/opt") -> str | None:
    try:
        u = shutil.disk_usage(yol)
        oran = u.used / u.total
        return f"disk %{oran * 100:.0f} dolu ({u.free / 1e9:.1f} GB boş)" if oran >= 0.90 else None
    except Exception:
        return None


def _durum_yolu(klasor: str) -> str:
    return os.path.join(klasor, "nabiz_durum.json")


def _durum(klasor: str) -> dict:
    try:
        return json.load(open(_durum_yolu(klasor), encoding="utf-8"))
    except Exception:
        return {}


def calistir(kok: str = "/opt", gonder=None, systemctl=_systemctl, yazdir: bool = False, simdi: float | None = None) -> int:
    """Sorunlu kurulum sayısı. gonder(klasor_env, metin, acil) -> bool (test için değiştirilebilir)."""
    simdi = simdi or time.time()
    if gonder is None:
        gonder = _telegram
    kotu = 0
    disk = disk_sorunu(kok)
    for kl, sv in kurulumlar(kok):
        sorun = kontrol(kl, sv, systemctl, simdi)
        if disk and kl.endswith("/carry"):
            sorun.append(disk)
        d = _durum(kl); ad = os.path.basename(kl)
        if yazdir:
            print(f"{ad:<20} {'SORUN: ' + ' | '.join(sorun) if sorun else 'tamam'}")
        if sorun:
            kotu += 1
            if simdi - float(d.get("son_uyari", 0)) >= KISMA_SN:
                if gonder(kl, "NABIZ: " + " · ".join(sorun), True):
                    d["son_uyari"] = simdi
            d["sorunlu"] = True
        elif d.get("sorunlu"):
            if gonder(kl, "✅ NABIZ: düzeldi, bot yine tur atıyor", False):
                d = {}
        try:
            json.dump(d, open(_durum_yolu(kl), "w", encoding="utf-8"))
        except OSError:
            pass
    return kotu


def _telegram(klasor: str, metin: str, acil: bool) -> bool:
    e = env_oku(klasor)
    for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "CARRY_BILDIRIM_AD"):
        if e.get(k):
            os.environ[k] = e[k]
        else:
            os.environ.pop(k, None)
    if not os.environ.get("CARRY_BILDIRIM_AD"):
        b = os.path.basename(klasor)
        os.environ["CARRY_BILDIRIM_AD"] = b[len("carry-"):] if b.startswith("carry-") else e.get("BINANCE_MODE", "demo")
    import bildirim
    return bildirim.gonder(metin, acil=acil)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    calistir(yazdir="--yazdir" in sys.argv)
    sys.exit(0)
