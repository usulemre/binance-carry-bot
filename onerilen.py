# -*- coding: utf-8 -*-
"""MADDE 656 — ÖNERİLEN AYAR OTOMATİK (kullanıcı kararı 2026-10-29: "test ortamı, demo hesap, canlı — hepsi önerilende çalışsın").

`CARRY_PROFIL` boşsa ya da `ONERILEN` ise bot (ve preflight) açılışta bakiyeyi okur, KAR_HARITASI 596 / 623 / 629'un ölçülmüş
ayarını seçer, ortamı ayarlar ve süreci aynı argümanlarla yeniden başlatır (os.execv; systemd için PID aynı kalır):
    kitap  <  3.500 $        T7K 1,15x + koşullu stop (0,03)
    3.500 – 12.500 $         T7K 1,10x + koşullu stop
    ≥ 12.500 $ (TAM evren)   T6  1,10x + koşullu stop
Kitap = özkaynak × CARRY_SERMAYE_OLCEK (demo ölçeği). Bakiye okunamazsa: T7K 1,0x + koşullu stop (kaldıraçsız; güvenli taraf).
.env'de AÇIKÇA verilen CARRY_GROSS / CARRY_LONG_24S_PIYASA korunur (bilerek verilmiş değer kazanır). Kapatmak: CARRY_ONERILEN=0 (o zaman
eski kod varsayılanı T4) ya da CARRY_PROFIL'i açıkça yazmak.
MADDE 657: bot her turdan (8 sa) sonra kitabı yeniden okur; bakiye eşiği %3 PAYLA geçtiyse (≈ 3.610 $ üstü / 3.400 $ altı, 12.890 / 12.130 $)
yeni ayarı seçmek için kendini yeniden başlatır (açık pozisyonlar ve dilim defteri olduğu gibi kalır; yalnız yeni dengelemeler yeni dozla).
Modül düzeyinde (testler, araştırma) hiçbir şey değişmez: çözümleme yalnız carry_bot.main() ve carry_preflight.main() içinde.
"""
from __future__ import annotations

import os
import shutil
import sys

ESIK_T6 = 12500.0
ESIK_110 = 3500.0
KS_ESIK = "0.03"
_ISARET = "_CARRY_ONERILEN_TAMAM"


def sec(kitap: float | None) -> tuple[str, str]:
    """(profil, gross) — madde 596 (T7K 1,15 < 3.500 $; üstünde 1,10), 629 (T6 1,10 yalnız ≳ 12.500 $)."""
    if not kitap or kitap <= 0:
        return "T7K", "1.0"
    if kitap >= ESIK_T6:
        return "T6", "1.10"
    if kitap >= ESIK_110:
        return "T7K", "1.10"
    return "T7K", "1.15"


def gerekli() -> bool:
    """Profil boş / ONERILEN, otomatik kapatılmamış ve bu süreçte henüz çözülmemiş mi."""
    p = os.getenv("CARRY_PROFIL", "").strip().upper()
    return (os.getenv(_ISARET) != "1" and os.getenv("CARRY_ONERILEN", "1").strip() != "0"
            and p in ("", "ONERILEN"))


def cozumle(kitap_oku, kok: str | None = None) -> dict:
    """kitap_oku() -> float | None. Ortamı ayarlar; ne seçildiğini döndürür (yeniden başlatmaz)."""
    try:
        kitap = kitap_oku()
    except Exception:
        kitap = None
    profil, gross = sec(kitap)
    _oto_gross = "CARRY_GROSS" not in os.environ; _oto_ks = "CARRY_LONG_24S_PIYASA" not in os.environ
    os.environ["CARRY_PROFIL"] = profil
    if "CARRY_GROSS" not in os.environ:
        os.environ["CARRY_GROSS"] = gross
        if gross != "1.0":
            os.environ["CARRY_DOZ_ONAY"] = gross
    if "CARRY_LONG_24S_PIYASA" not in os.environ:
        os.environ["CARRY_LONG_24S_PIYASA"] = KS_ESIK
    oto = ["CARRY_PROFIL"] + (["CARRY_GROSS", "CARRY_DOZ_ONAY"] if _oto_gross else []) + (["CARRY_LONG_24S_PIYASA"] if _oto_ks else [])
    os.environ["_CARRY_ONERILEN_OTO"] = ",".join(oto)
    os.environ[_ISARET] = "1"
    os.environ["CARRY_ONERILEN_KITAP"] = f"{kitap:.2f}" if kitap else "okunamadi"
    if profil == "T7K":   # madde 585: prim geçmişi yoksa tohumdan (yoksa çarpan ~90 g 1,0 kalır)
        kok = kok or os.path.dirname(os.path.abspath(__file__))
        hedef = os.path.join(kok, os.getenv("CARRY_PRIM_DOSYA", "carry_prim.csv"))
        tohum = os.path.join(kok, "carry_prim_tohum.csv")
        if not os.path.exists(hedef) and os.path.exists(tohum):
            try:
                shutil.copy(tohum, hedef)
            except OSError:
                pass
    return {"kitap": kitap, "profil": profil, "gross": os.environ["CARRY_GROSS"],
            "ks": os.environ["CARRY_LONG_24S_PIYASA"]}


PAY = 0.03


def esik_gecti(kitap: float | None) -> bool:
    """MADDE 657: otomatik çözülmüş bir süreçte kitap, şu anki seçimin eşiğini %3 payla geçti mi (geçtiyse yeniden seçim gerekir)."""
    if os.getenv(_ISARET) != "1" or not kitap or kitap <= 0:
        return False
    simdi = (os.getenv("CARRY_PROFIL", ""), os.getenv("CARRY_GROSS", "")) if "CARRY_GROSS" in os.getenv("_CARRY_ONERILEN_OTO", "") \
        else (os.getenv("CARRY_PROFIL", ""), None)
    def _s(k):
        p, g = sec(k)
        return (p, g) if simdi[1] is not None else (p, None)
    yeni = _s(kitap)
    return yeni != simdi and _s(kitap * (1 - PAY)) == yeni and _s(kitap * (1 + PAY)) == yeni


def sifirla() -> None:
    """Otomatik atanmış değerleri ve işareti siler: yeniden başlayan süreç seçimi baştan yapar (.env'deki açık değerler korunur)."""
    for k in os.getenv("_CARRY_ONERILEN_OTO", "").split(","):
        if k:
            os.environ.pop(k, None)
    for k in (_ISARET, "_CARRY_ONERILEN_OTO", "CARRY_ONERILEN_KITAP"):
        os.environ.pop(k, None)


def yeniden_baslat() -> None:
    """Modül sabitleri ortamdan okunduğu için süreç yeni ortamla baştan başlar."""
    sys.stdout.flush(); sys.stderr.flush()
    os.execv(sys.executable, [sys.executable] + sys.argv)
