#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EKİM 2026 GERÇEK-VERİ OOS — İZLEME LİSTESİ (madde 492, ön kayıt; madde 587'de güncellendi).

Bu oturumda Tem-Eyl 2026'da tekrar tekrar tabandan iyi görünen ama ön kaydı geçemeyen kollar, YENİ veride (Ekim 2026,
hiçbir seçimde kullanılmadı) TEK seferde ölçülür. Deneme sayısı artmadan "son dönemde mi çalışıyor, şans mı" sorusu.

ÖN KAYIT (veri gelmeden yazıldı):
  - Ölçüt: 2026-10-01..31 aylık getiri ve günlük Sharpe, iki hiza ortalaması, kendi tabanına karşı.
  - T2 vs T1: T2 Ekim'de T1'den KÖTÜ değilse (aylık fark ≥ −1 puan) ve dd'si sığsa → T2 kanıtı güçlenir (kullanıcıya).
  - ASIL SORU (madde 497-519): OK1_T4 vs ZSR15P67 — T4 Ekim'de T1'den kötü değilse (aylık fark ≥ −1 puan) T4 açılması için
    son doğrulama TAMAM (kullanıcıya bildirilir); kötüyse fark ve sebebi (hangi parça: T3 / T3F / T4) raporlanır.
  - İzleme kolları: yalnız tek ay olduğundan KARAR VERMEZ; tabanı geçen kol "Kasım'da tekrar" listesinde kalır, geçemeyen
    listeden düşer.

MADDE 587 GÜNCELLEMESİ (2026-10-26, Ekim funding verisi henüz YAYIMLANMADI — ön kayıt niteliği korunuyor):
  (a) Madde 527'nin motor düzeltmesi (MERD_SIRA=1: aynı barda kademe + son TP) bu betiğe hiç işlenmemişti; T1 ve T2
      tabanları dahil BÜTÜN kollar artık MERD_SIRA=1 ile koşar. Eski kuralla ölçmek merdivenli kolları şişirirdi.
  (b) ANA BLOK eklendi — madde 534'ten beri kod varsayılanı T4, isteğe bağlı profiller T6 (madde 575) ve T7K (madde 585).
      Ana blok bu dört kitabı protokolle AYNI koşulda ölçer: canlı gibi giriş (TEK_GIRIS=1) + 5 bp + MERD_SIRA=1,
      iki seviye (2.000 $ D8 / 3.500 $ D2) × iki hiza. Tanımlar madde 568 / 584 betikleriyle birebir.
  (c) Ana blok kuralları (tek ay KARAR VERMEZ; yalnız kanıtı güçlendirir/zayıflatır):
      - T4 vs T1: aylık fark ≥ −1 puan → T4 için Ekim doğrulaması TAMAM (madde 492'nin asıl sorusu, gerçekçi koşulda).
      - T6 vs T4 ve T7K vs T4: Ekim aylık farkı, AYNI serilerin geçmiş aylık fark dağılımında (2022-07 → 2026-09)
        %10 yüzdeliğin ALTINDAYSA "UYARI", değilse "olağan". (Madde 412'nin yöntemi.)
      - T7K'nın amacı kötü gün olduğu için ayrıca Ekim'in en kötü günü ve −%3 altı gün sayısı T4 ile yan yana yazılır.
ADIMLAR (Kasım başı, funding verisi yayınlanınca):
  1) python3 indir_ek_ay.py 2026-10 && python3 yeniden_kur.py   (zemin + paneller)
  2) sinyal panelleri: PEN=60 AD=bar60 python3 canli_sinyal_kur.py && PEN=96 AD=bar96 python3 canli_sinyal_kur.py
     (T1/T4 60 sa, T6/T7K short tarafı 96 sa ister) ; metrik paneli: python3 indir_metrik_surdurulebilir.py panel
  3) defter paneli için: python3 indir_bookdepth.py <ekim aday listesi> ... (DR50 kolu için; yoksa o kol atlanır)
  4) python3 izleme_ekim_oos.py kos_ana && python3 izleme_ekim_oos.py analiz_ana     (ana blok: T1 / T4 / T6 / T7K)
     python3 izleme_ekim_oos.py kos && python3 izleme_ekim_oos.py analiz             (izleme kolları, madde 492)
  Kuru koşu: AY=2026-09 ile herhangi bir tamamlanmış ay üzerinde aynı hesap yapılabilir (o ay örnek İÇİDİR, karar vermez).
"""
import os, sys
import numpy as np
import arastirma_tabanlar as TB
import arastirma_m346_prim as M

AY = os.environ.get("AY", "2026-10")
AY_BAS = AY + "-01"
AY_SON = str((np.datetime64(AY, "M") + np.timedelta64(1, "M")).astype("datetime64[D]"))
SIRA = {"MERD_SIRA": "1"}                                          # madde 527 düzeltmesi, madde 587 (a)
# Motor var olan .pkl'yi yeniden koşmaz (arastirma_m357 tek()): kuru koşu AYRI klasöre yazmalı, yoksa Kasım'da bayat
# (Ekim'siz) seriler okunur. Kuru koşu: AY=2026-09 IZLEME_CIKTI=/tmp/m_ekim_kuru
CIKTI = os.environ.get("IZLEME_CIKTI", "/tmp/m_ekim"); os.makedirs(CIKTI, exist_ok=True)
TB.A.CIKTI = CIKTI; M.CIKTI = CIKTI
TB.T1 = {**TB.T1, **SIRA}; TB.T2 = {**TB.T2, **SIRA}               # kur() tabanları modül değişkeninden okur
IZLE = {  # ad -> (taban no, değişiklik)
    "K_G": (None, {"MERD_GERI": "1"}),                 # madde 491, iki tabanda
    "K_GS": (None, {"MERD_GERI": "1", "MERD_GERI_TARAF": "short"}),
    "E_MS18": (2, {"MERDS_ESIK": "0.18"}),             # madde 488 (T2 +4,1)
    "SR6": (None, {"S_REB": "6"}), "SR12": (None, {"S_REB": "12"}),   # madde 493-495 (2025-26 rejim etkisi)
    # madde 497-519: ASIL ADAY T4 ve parçaları (T1 tabanına uygulanır; T2 tabanındaki kopyaları bilgi amaçlı)
    "T3": (None, {"S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short"}),
    "T3F": (None, {"S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80"}),
    "T4": (None, {"S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}),
}
TB.kur({a: d for a, (t, d) in IZLE.items()}, onek="OK")
DEFTER = os.path.exists("/tmp/derin_panel.pkl")

# --- ANA BLOK (madde 587 b): madde 568 / 584 tanımlarıyla birebir ---
G = {**TB.T1, "TEK_GIRIS": "1", "KOM": "0.0005"}                  # TB.T1 zaten MERD_SIRA=1 taşıyor
_T4 = {**G, "S_REB": "12", "CAP_ORTAK": "0.08", "CAP_TARAF": "short", "MERD_PAY": "0.80", "HACIM_MIN_EVREN": "30"}
_T6 = {**_T4, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "CAP_ORTAK": "1.0"}
_T7K = {**_T4, "S_REB": "10", "SK_DOSYA_S": "/tmp/sk_bar96.pkl", "BRUT_PRIM": "1", "BRUT_ALT": "0.7", "BRUT_UST": "1.0"}
EV = {2000: M.D8, 3500: M.D2}
ANA = {"EK_T1": (G, 4, EV), "EK_T4": (_T4, 4, EV), "EK_T6": (_T6, 4, EV), "EK_T7K": (_T7K, 4, EV)}


def kos():
    TB.A.kos()
    if DEFTER:   # madde 479 DR50/CK50 — seçim 'ls_derin'/'ls_cek' ile; ayrı çağrı
        import arastirma_m479_defter_secim as D
        D.A.CIKTI = CIKTI; D.M.CIKTI = CIKTI; D.A.kos()


def kos_ana():
    eski = (TB.A.KOLLAR, TB.A.SEVIYE)
    TB.A.KOLLAR, TB.A.SEVIYE = ANA, (2000, 3500)
    try:
        TB.A.kos()
    finally:
        TB.A.KOLLAR, TB.A.SEVIYE = eski


def _ay(g):
    return g[(g.index >= AY_BAS) & (g.index < AY_SON)]


def _aylik(g):
    return (1 + g).groupby(g.index.to_period("M")).prod() - 1


def analiz():
    def ay(ad):
        g = _ay(M.gunluk(ad))
        return ((1 + g).prod() - 1) * 100, g.mean() / g.std() * np.sqrt(365.25) if len(g) > 5 else np.nan, len(g)
    print(f"[{AY}, MERD_SIRA=1]")
    print(f"{'kol':22s} {'ay %':>7s} {'Sh':>6s} {'gün':>4s} {'taban farkı':>11s}")
    tab = {1: "ZSR15P67", 2: "BRP80_CAP_A43"}
    ref = {}
    for t, ad in tab.items():
        r = [ay(f"M357_{ad}_2000_{h}") for h in (0, 1)]; ref[t] = np.mean([x[0] for x in r])
        print(f"{ad:22s} {ref[t]:+7.2f} {np.mean([x[1] for x in r]):6.2f} {r[0][2]:4d}")
    for ad, t in TB._KOL.items():
        try:
            r = [ay(f"M357_{ad}_2000_{h}") for h in (0, 1)]
        except Exception:
            continue
        m = np.mean([x[0] for x in r]); print(f"{ad:22s} {m:+7.2f} {np.mean([x[1] for x in r]):6.2f} {r[0][2]:4d} {m-ref[t]:+11.2f}")
    print(f"\nT2 - T1 {AY}: {ref[2]-ref[1]:+.2f} puan → " + ("T2 kanıtı GÜÇLENDİ" if ref[2] - ref[1] >= -1 else "T2 bu ay geride"))


def analiz_ana():
    print(f"ANA BLOK [{AY}] — canlı gibi giriş + 5 bp + MERD_SIRA=1, iki hiza ortalaması")
    print(f"{'kol':8s} {'bakiye':>6s} {'ay %':>7s} {'Sh':>6s} {'en kötü':>8s} {'-%3':>4s} {'gün':>4s} | "
          f"{'T4 farkı':>8s} {'geçmiş %10':>10s} {'yüzdelik':>8s}  hüküm")
    for sev in (2000, 3500):
        seri = {k: [M.gunluk(f"M357_{k}_{sev}_{h}") for h in (0, 1)] for k in ANA}
        ay = {k: [_ay(g) for g in v] for k, v in seri.items()}
        if not len(ay["EK_T4"][0]):
            print(f"{sev}: {AY} için veri yok — zemin uzatılmamış"); continue
        top = {k: np.mean([((1 + g).prod() - 1) * 100 for g in v]) for k, v in ay.items()}
        for k in ANA:
            sh = np.mean([g.mean() / g.std() * np.sqrt(365.25) if len(g) > 5 else np.nan for g in ay[k]])
            ek = min(g.min() for g in ay[k]) * 100
            n3 = np.mean([int((g < -0.03).sum()) for g in ay[k]])
            sat = f"{k[3:]:8s} {sev:6d} {top[k]:+7.2f} {sh:6.2f} {ek:+8.2f} {n3:4.1f} {len(ay[k][0]):4d} |"
            if k == "EK_T4":
                print(sat); continue
            fark = top[k] - top["EK_T4"]
            # geçmiş aylık fark dağılımı: ilgili ay ve sonrası HARİÇ, aynı seriler, iki hiza ortalaması
            d = sum(_aylik(seri[k][h]) - _aylik(seri["EK_T4"][h]) for h in (0, 1)) / 2 * 100
            gecmis = d[[str(p) < AY for p in d.index]].dropna().values
            p10 = np.percentile(gecmis, 10); yuz = (gecmis < fark).mean() * 100
            if k == "EK_T1":
                huk = (f"T4 için {AY} doğrulaması TAMAM" if -fark >= -1 else "T4 bu ay T1'in gerisinde (fark < −1)")
                print(sat + f" {fark:+8.2f} {p10:+10.2f} {yuz:7.0f}%  T4−T1 {-fark:+.2f} → {huk}")
            else:
                print(sat + f" {fark:+8.2f} {p10:+10.2f} {yuz:7.0f}%  " + ("UYARI" if fark < p10 else "olağan"))


if __name__ == "__main__":
    {"kos": kos, "analiz": analiz, "kos_ana": kos_ana, "analiz_ana": analiz_ana}[sys.argv[1]]()
