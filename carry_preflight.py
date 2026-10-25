"""CARRY BOT — CANLIYA GEÇİŞ ÖNCESİ KONTROL (madde 217).

HİÇBİR EMİR GÖNDERMEZ. Sadece okur ve raporlar.

NEDEN AYRI BİR ARAÇ: `preflight.py` bu projenin ESKİ botları için yazıldı
(`config.ACTIVE_STRATEGY`, `.env`, 4h zaman dilimi, stop-loss/kaldıraç
tutarlılığı). Carry botunun hiçbirini kullanmıyor - hatta `.env`
ARAMAMASI gerekiyor (güvenlik kuralı: anahtar sadece ortam
değişkeninden). O aracı carry için çalıştırmak yanlış HATA veriyordu.

Bu araç madde 204-216'da bulunan gerçek canlı arızalarını kontrol eder -
hepsi backtest'te GÖRÜNMEYEN sınıftan:

  madde 204  bakiye bacak başına MIN_NOTIONAL'ı geçiyor mu
  madde 210  canlı sinyal TANIMI, beklentinin ölçüldüğü tanımla aynı mı
  madde 211  hesap TEK YÖNLÜ modda mı, izole teminatta pozisyon var mı
  madde 216  kâr al defteri yazılabiliyor mu
  madde 139  sağlık kapısı durumu
  madde 176  bacak büyüklüğü yüzünden kaç sembol eleniyor

KULLANIM:
    python carry_preflight.py           # borsaya bağlanır (sadece okur)
    python carry_preflight.py --yerel   # API'ye hiç dokunmaz
"""
from __future__ import annotations

import argparse
import os
import sys

TAMAM, UYARI, HATA = "TAMAM", "UYARI", "HATA"
_sayac = {TAMAM: 0, UYARI: 0, HATA: 0}
_satirlar: list[tuple[str, str, str]] = []


def kontrol(ad: str, durum: str, mesaj: str = "") -> None:
    _sayac[durum] = _sayac.get(durum, 0) + 1
    _satirlar.append((ad, durum, mesaj))
    isaret = {TAMAM: "  OK ", UYARI: "  !! ", HATA: "  XX "}[durum]
    print(f"{isaret}{ad:38s} {mesaj}")


# ------------------------------------------------------------ 1) AYARLAR
def kontrol_ayarlar() -> None:
    print("\n1) AYARLAR — ölçülen yapılandırmayla aynı mı")
    import carry_bot as cb
    bekle = {
        "N_LEGS": (cb.N_LEGS, 5, "madde 222"),
        "N_DILIM": (cb.N_DILIM, 15, "madde 184"),
        "FUNDING_WINDOW_HOURS": (cb.FUNDING_WINDOW_HOURS, 48.0, "madde 209"),
        "REBALANCE_HOURS": (cb.REBALANCE_HOURS, 120.0, "madde 120"),
        "GROSS_EXPOSURE": (cb.GROSS_EXPOSURE, 1.0, "kaldıraçsız"),
        "KAR_AL_ORAN": (cb.KAR_AL_ORAN, 0.40, "madde 178"),
        "KAR_AL_SHORT": (cb.KAR_AL_SHORT, 0.20, "madde 189"),
        "UC_HAREKET_ELE": (cb.UC_HAREKET_ELE, 0.40, "madde 196"),
        "KALABALIK_HAVUZ": (cb.KALABALIK_HAVUZ, 4.0, "madde 352"),
        "REZERV_PAY": (cb.REZERV_PAY, 0.20, "madde 156"),
    }
    # MADDE 437/442: İKİ ÖLÇÜLMÜŞ PROFİL. T60 (varsayılan, madde 442): hacim 70M,
    # yaş 60, REZ 0,10, uç hareket kapalı, 60 sa, long TP 0,60, short +%200 stop.
    # BUGUN (eski kitap): CARRY_PROFIL=BUGUN + eski değerler .env'de açıkça.
    # Yaş 90'ın altı short felaket stop'u OLMADAN çalıştırılamaz (madde 427).
    # Not: `bekle` sözlüğünün temel değerleri BUGUN kitabınındır; T60 bunları ezer.
    profil = os.getenv("CARRY_PROFIL", "").strip().upper() or "T4"   # madde 534: varsayılan T4 (önce T60, madde 442)
    if profil == "BUGUN":
        bekle.update({
            "MIN_DAILY_VOLUME_USD": (cb.MIN_DAILY_VOLUME_USD, 1e8, "madde 401"),
            "MIN_LISTELEME_GUN": (cb.MIN_LISTELEME_GUN, 90, "madde 396"),
        })
        kontrol("profil", TAMAM, "CARRY_PROFIL=BUGUN (eski kitap; T60 madde 442'den beri varsayılan)")
    elif profil in ("T60", "T3", "T4"):
        bekle.update({
            "FUNDING_WINDOW_HOURS": (cb.FUNDING_WINDOW_HOURS, 60.0, "madde 429"),
            "KAR_AL_ORAN": (cb.KAR_AL_ORAN, 0.60, "madde 435-436"),
            "UC_HAREKET_ELE": (cb.UC_HAREKET_ELE, 0.0, "madde 429"),
            "REZERV_PAY": (cb.REZERV_PAY, 0.10, "madde 429"),
            "MIN_DAILY_VOLUME_USD": (cb.MIN_DAILY_VOLUME_USD, 7e7, "madde 429"),
            "MIN_LISTELEME_GUN": (cb.MIN_LISTELEME_GUN, 60, "madde 429/433"),
            "SHORT_FELAKET": (cb.SHORT_FELAKET, 2.0, "madde 428"),
            "LONG_24S": (cb.LONG_24S, 0.45, "madde 449-453"),
            "MERDIVEN": (cb.MERDIVEN, 0.45, "madde 463-465"),
            "MERDIVEN_PAY": (cb.MERDIVEN_PAY, 0.667, "madde 468-469"),
            "MERDIVEN_SHORT": (cb.MERDIVEN_SHORT, 0.15, "madde 466-469"),
            "SHORT_ARA_SAAT": (getattr(cb, "SHORT_ARA_SAAT", 0.0), 0.0, "madde 493-502 (T60'ta kapalı)"),
            "SHORT_TAVAN": (getattr(cb, "SHORT_TAVAN", 0.0), 0.0, "madde 500-502 (T60'ta kapalı)"),
        })
        if profil in ("T3", "T4"):
            # MADDE 501-505: T3 = T60 varsayılanı + short 2 g'de bir + short tavan %8 + kademe payı 0,80 (KULLANICI KARARI)
            bekle.update({
                "SHORT_ARA_SAAT": (getattr(cb, "SHORT_ARA_SAAT", 0.0), 48.0, "madde 497-502"),
                "SHORT_TAVAN": (getattr(cb, "SHORT_TAVAN", 0.0), 0.08, "madde 500-502"),
                "MERDIVEN_PAY": (cb.MERDIVEN_PAY, 0.80, "madde 504"),
            })
            if profil == "T4":
                bekle["EVREN_MIN"] = (getattr(cb, "EVREN_MIN", 0), 30, "madde 508")
            kontrol("profil", TAMAM, f"{profil} (kullanıcı kararı; ADAYLAR.md, madde 497-522"
                    + ("; varsayılan, madde 534)" if profil == "T4" else ")"))
        else:
            kontrol("profil", TAMAM, "T60 = eski varsayılan T1 (madde 442; madde 534'ten beri varsayılan T4)")
    else:
        kontrol("profil", HATA, f"CARRY_PROFIL={profil} tanımsız (BUGUN | T60 | T3 | T4)")
    if getattr(cb, "MIN_LISTELEME_GUN", 90) < 60:
        kontrol("yaş eşiği", HATA, f"CARRY_MIN_LISTING_DAYS={cb.MIN_LISTELEME_GUN} < 60: "
                "madde 427'de yaş 45 short sıkışmalarıyla hesabı sıfırladı")
    if getattr(cb, "MIN_LISTELEME_GUN", 90) < 90 and getattr(cb, "SHORT_FELAKET", 0) <= 0:
        kontrol("short felaket stop'u", HATA, "yaş eşiği 90'ın altında ama CARRY_SHORT_STOP=0: "
                "genç coin short'u sigortasız (madde 427-428)")
    # MADDE 374: ÖLÇÜLMÜŞ DOZ, AÇIK ONAYLA. Madde 368/369 2.000 $ için
    # 1,25x ve 1,55-1,60x'i gerçek serilerle ölçtü. Kapı (madde 276: önce
    # 1x canlı çeyrek) KOD değil SÜREÇ; kod yalnız şunu garanti eder:
    # kaldıraç sessizce değil, bilerek ve ölçülmüş bir değerde açılır.
    # CARRY_DOZ_ONAY, CARRY_GROSS ile AYNI değeri taşımalı.
    _doz = float(cb.GROSS_EXPOSURE)
    _onay = os.getenv("CARRY_DOZ_ONAY", "").strip()
    _olculmus = abs(_doz - 1.25) < 1e-9 or (1.55 - 1e-9 <= _doz <= 1.60 + 1e-9)
    if abs(_doz - 1.0) > 1e-9:
        if 1.5 - 1e-9 <= _doz < 1.55 - 1e-9:
            kontrol("doz", HATA,
                    f"CARRY_GROSS={_doz}: 2.000 $'da bacak ~20 $ = ETH grubunun asgari "
                    "emri; grup her turda girip çıkar (madde 369). En az 1,55 kullanın.")
        elif _olculmus and _onay and abs(float(_onay) - _doz) < 1e-9:
            bekle.pop("GROSS_EXPOSURE")
            kontrol("doz", TAMAM,
                    f"CARRY_GROSS={_doz} ölçülmüş doz, onaylı (madde 368/369; "
                    "beklenti CANLIYA_CIKIS.md §7 madde 372 tablosunda)")
        elif _olculmus:
            kontrol("doz", HATA,
                    f"CARRY_GROSS={_doz} ölçülmüş bir doz ama ONAY yok: bilerek "
                    f"açtığınızı CARRY_DOZ_ONAY={_doz} ile belirtin (madde 374)")
            bekle.pop("GROSS_EXPOSURE")
    sapan = [f"{k}={v[0]} (olmalı {v[1]}, {v[2]})"
             for k, v in bekle.items() if abs(float(v[0]) - float(v[1])) > 1e-9]
    if sapan:
        kontrol("ölçülen ayarlar", HATA,
                "SAPMA: " + "; ".join(sapan) + " — beklenti bu ayarla ölçülmedi")
    else:
        kontrol("ölçülen ayarlar", TAMAM,
                f"{min(cb.N_LEGS, cb.BACAK_TAVAN)}+{min(cb.N_LEGS, cb.BACAK_TAVAN)} bacak "
                f"(tavan, madde 341), {cb.N_DILIM} dilim, "
                f"pencere {cb.FUNDING_WINDOW_HOURS:.0f}sa")
    # ACMA listesi
    acik = []
    if getattr(cb, "VOL_HEDEF", 0):
        acik.append("CARRY_VOL_HEDEF (madde 165: 14-24 puan kaybettiriyor)")
    if getattr(cb, "SOLMA_AKTIF", False) or os.getenv("CARRY_SOLMA") in ("1", "true"):
        acik.append("CARRY_SOLMA (madde 167.3: +%55,9 -> +%40,9)")
    if acik:
        kontrol("açılmaması gereken ayarlar", HATA, "AÇIK: " + "; ".join(acik))
    else:
        kontrol("açılmaması gereken ayarlar", TAMAM, "hepsi kapalı")
    kontrol("tur aralığı", TAMAM,
            f"{cb.REBALANCE_HOURS / cb.N_DILIM:.0f} saat "
            f"(günde {24 / (cb.REBALANCE_HOURS / cb.N_DILIM):.0f} tur)")


# ------------------------------------------------------- 2) SİNYAL PARİTESİ
def kontrol_parite() -> None:
    print("\n2) SİNYAL TANIMI PARİTESİ (madde 210) — beklenti geçerli mi")
    try:
        import carry_parite as cp
        k = cp.karar()
        if k["durum"] == "TAMAM":
            kontrol("sinyal tanımı", TAMAM,
                    f"pencere {k['pencere']:.0f}sa = referans ölçüm")
        else:
            kontrol("sinyal tanımı", HATA, "; ".join(k["sorunlar"]))
        for ar, (g, b) in k["sayim"].items():
            if g != b:
                kontrol(f"ödeme sayısı ({ar:.0f}sa sembol)", HATA,
                        f"{g} ödeme girmiş, {b} olmalı")
    except Exception as e:
        kontrol("sinyal tanımı", UYARI, f"kontrol edilemedi: {e}")


# ------------------------------------------------------------ 3) REFERANS
def kontrol_referans() -> None:
    print("\n3) BEKLENTİ — referans seri ve rapor eşiği tutarlı mı")
    try:
        import carry_rapor as cr
        import carry_sapma as cs
        ref = cs.referans_oku()
        n = len(ref) if ref is not None else 0
        if n < 500:
            kontrol("referans seri", HATA,
                    f"{n} gün - `referans_getiri.csv` eksik ya da bozuk")
            return
        ort = float(sum(ref) / n)
        fark = abs(ort - cr.BEKLENEN_GUNLUK)
        if fark > 0.00002:
            kontrol("referans / rapor tutarlılığı", HATA,
                    f"seri ortalaması {ort:.6f}, raporun beklentisi "
                    f"{cr.BEKLENEN_GUNLUK:.6f} - biri güncellenmemiş")
        else:
            kontrol("referans / rapor tutarlılığı", TAMAM,
                    f"{n} gün, günlük ortalama %{ort * 100:.4f}")
    except Exception as e:
        kontrol("referans seri", UYARI, f"okunamadı: {e}")


# -------------------------------------------------------------- 4) DEFTER
def kontrol_defterler() -> None:
    print("\n4) DEFTERLER — yazılabiliyor mu (madde 216)")
    import carry_bot as cb
    for ad, yol in (("kâr al defteri", cb.TP_DEFTER_DOSYA),
                    ("bakiye geçmişi", cb.VOL_GECMIS_DOSYA),
                    ("dilim durumu", cb.DILIM_DURUM_DOSYA)):
        d = os.path.dirname(os.path.abspath(yol)) or "."
        if not os.path.isdir(d):
            kontrol(ad, HATA, f"dizin yok: {d}")
        elif not os.access(d, os.W_OK):
            kontrol(ad, HATA, f"yazma izni yok: {d}")
        else:
            var = "var" if os.path.exists(yol) else "henüz yok (normal)"
            kontrol(ad, TAMAM, f"{os.path.basename(yol)} — {var}")


# ---------------------------------------------------------- 5) BORSA (API)
def kontrol_borsa() -> None:
    print("\n5) BORSA — hesap durumu (sadece OKUR)")
    try:
        import config
        import carry_bot as cb
        from exchange_client import ExchangeClient
    except Exception as e:
        kontrol("modüller", HATA, str(e))
        return
    if not (getattr(config, "API_KEY", "") and getattr(config, "API_SECRET", "")):
        kontrol("API anahtarı", HATA,
                "BINANCE_API_KEY / BINANCE_API_SECRET ortam değişkeni YOK. "
                "Anahtar dosyaya YAZILMAZ - `export` ile verin.")
        return
    kontrol("API anahtarı", TAMAM, "ortam değişkeninden okundu (dosyada değil)")
    try:
        client = ExchangeClient(config.API_KEY, config.API_SECRET,
                                mode=getattr(config, "MODE", "demo"))
    except Exception as e:
        kontrol("bağlantı", HATA, str(e))
        return
    if str(getattr(client, "mode", "")).lower() != "live":
        kontrol("mod", UYARI, f"{client.mode} — gerçek para DEĞİL")
    else:
        kontrol("mod", TAMAM, "live (gerçek para)")

    # MADDE 211: pozisyon modu
    try:
        tek = cb.tek_yonlu_mu(client)
        if tek is True:
            kontrol("pozisyon modu (madde 211)", TAMAM, "TEK YÖNLÜ")
        elif tek is False:
            kontrol("pozisyon modu (madde 211)", HATA,
                    "HEDGE (çift yönlü) - bot bu modda HİÇ işlem açamaz "
                    "(-4061). Pozisyonları kapatıp Tek Yönlü'ye alın.")
        else:
            kontrol("pozisyon modu (madde 211)", UYARI, "okunamadı")
    except Exception as e:
        kontrol("pozisyon modu (madde 211)", UYARI, str(e))

    # MADDE 211: izole teminat
    try:
        izole = cb.izole_teminatlilar(client)
        if izole:
            kontrol("teminat modu (madde 211)", HATA,
                    f"İZOLE pozisyon: {', '.join(izole[:6])} - bu stratejide "
                    f"ölümcül (yıllık ~%23 sermaye). ÇAPRAZ'a alın.")
        else:
            kontrol("teminat modu (madde 211)", TAMAM, "izole pozisyon yok")
    except Exception as e:
        kontrol("teminat modu (madde 211)", UYARI, str(e))

    # MADDE 204: bakiye yeterliliği
    try:
        bakiye = cb.sermaye_oku(client)
        if bakiye is None:
            kontrol("bakiye (madde 204)", HATA,
                    "sermaye okunamadı - USDT dışı teminat olabilir "
                    "(CARRY_TEMINAT_MODU=coklu)")
        else:
            yeter, bacak = cb.bakiye_yeterli_mi(bakiye, cb.N_LEGS, 1.0)
            asgari = (cb.MIN_NOTIONAL_USD * cb.ASGARI_BACAK_CARPANI
                      * cb.N_DILIM * cb.N_LEGS
                      / max(1e-9, cb.GROSS_EXPOSURE * cb.taban_pay()))
            if not yeter:
                kontrol("bakiye (madde 204)", HATA,
                        f"{bakiye:.0f}$ ile bacak {bacak:.1f}$; asgari "
                        f"{asgari:.0f}$ gerekiyor. Bot bu bakiyede SESSİZCE "
                        f"hiç işlem açmaz.")
            elif bakiye < 3 * asgari:
                kontrol("bakiye (madde 204)", UYARI,
                        f"{bakiye:.0f}$ (bacak {bacak:.1f}$) - çalışır ama "
                        f"madde 176: küçük bacak sembol eletir, getiri ORANI "
                        f"düşer. Rahat aralık {3*asgari:.0f}$ üstü.")
            else:
                kontrol("bakiye (madde 204)", TAMAM,
                        f"{bakiye:.0f}$ -> bacak {bacak:.1f}$")
    except Exception as e:
        kontrol("bakiye (madde 204)", UYARI, str(e))

    # MADDE 176: evren ve eleme
    try:
        sem = cb.evren_sec(client)
        if not sem:
            kontrol("evren (madde 133)", HATA, "boş - ticker/filtre sorunu")
        else:
            bakiye = cb.sermaye_oku(client) or 0.0
            bacak = (bakiye / max(1, cb.N_DILIM)) * cb.GROSS_EXPOSURE \
                * cb.taban_pay() / max(1, cb.N_LEGS)
            islem = cb.islem_yapilabilir(client, sem, bacak) if bacak > 0 else sem
            elenen = len(sem) - len(islem)
            pay = elenen / max(1, len(sem))
            if pay > 0.20:
                kontrol("evren (madde 176)", HATA,
                        f"{len(sem)} sembolün {elenen}'i (%{pay*100:.0f}) bacak "
                        f"büyüklüğü yüzünden elendi. %20 eleme getiriyi "
                        f"+%55,9'dan +%35,6'ya düşürüyor - bakiye artırın.")
            elif elenen:
                kontrol("evren (madde 176)", UYARI,
                        f"{len(islem)}/{len(sem)} sembol işlem yapılabilir "
                        f"({elenen} elendi, %{pay*100:.0f})")
            else:
                kontrol("evren (madde 176)", TAMAM, f"{len(sem)} sembol, eleme yok")
    except Exception as e:
        kontrol("evren", UYARI, str(e))

    # MADDE 139: sağlık kapısı
    try:
        sem = cb.evren_sec(client)
        acik, durum, gerekce = cb.saglik_kontrol(client, list(sem), yaz=False)
        if acik:
            kontrol("sağlık kapısı (madde 139)", TAMAM, f"AÇIK ({durum})")
        else:
            kontrol("sağlık kapısı (madde 139)", HATA,
                    f"KAPALI ({durum}): {gerekce} - bot pozisyon açmaz")
    except Exception as e:
        kontrol("sağlık kapısı (madde 139)", UYARI, str(e))


def yaz_ozet() -> int:
    print("\n" + "=" * 70)
    print(f"SONUÇ: {_sayac[TAMAM]} tamam · {_sayac[UYARI]} uyarı · "
          f"{_sayac[HATA]} HATA")
    if _sayac[HATA]:
        print("\nCANLIYA GEÇMEYİN. Düzeltilmesi gerekenler:")
        for ad, durum, mesaj in _satirlar:
            if durum == HATA:
                print(f"  - {ad}: {mesaj}")
    elif _sayac[UYARI]:
        print("\nGeçebilirsiniz ama uyarıları okuyun:")
        for ad, durum, mesaj in _satirlar:
            if durum == UYARI:
                print(f"  - {ad}: {mesaj}")
    else:
        print("\nHer şey yerinde. Sıradaki adım: `python carry_bot.py --dry-run`")
    print("=" * 70)
    return 1 if _sayac[HATA] else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yerel", action="store_true",
                    help="borsaya HİÇ bağlanma, sadece yerel kontroller")
    a = ap.parse_args()
    print("=" * 70)
    print("CARRY BOT PREFLIGHT (madde 217) — hiçbir emir gönderilmez")
    print("=" * 70)
    kontrol_ayarlar()
    kontrol_parite()
    kontrol_referans()
    kontrol_defterler()
    if a.yerel:
        print("\n5) BORSA — --yerel verildiği için ATLANDI")
    else:
        kontrol_borsa()
    return yaz_ozet()


if __name__ == "__main__":
    sys.exit(main())
