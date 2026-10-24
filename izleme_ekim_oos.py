#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EKİM 2026 GERÇEK-VERİ OOS — İZLEME LİSTESİ (madde 492, ön kayıt).

Bu oturumda Tem-Eyl 2026'da tekrar tekrar tabandan iyi görünen ama ön kaydı geçemeyen kollar, YENİ veride (Ekim 2026,
hiçbir seçimde kullanılmadı) TEK seferde ölçülür. Deneme sayısı artmadan "son dönemde mi çalışıyor, şans mı" sorusu.

ÖN KAYIT (veri gelmeden yazıldı):
  - Ölçüt: 2026-10-01..31 aylık getiri ve günlük Sharpe, iki hiza ortalaması, kendi tabanına karşı.
  - T2 vs T1: T2 Ekim'de T1'den KÖTÜ değilse (aylık fark ≥ −1 puan) ve dd'si sığsa → T2 kanıtı güçlenir (kullanıcıya).
  - İzleme kolları: yalnız tek ay olduğundan KARAR VERMEZ; tabanı geçen kol "Kasım'da tekrar" listesinde kalır, geçemeyen
    listeden düşer.
ADIMLAR (Kasım başı, funding verisi yayınlanınca):
  1) python3 indir_ek_ay.py 2026-10 && python3 yeniden_kur.py   (zemin + paneller; sk_bar60/sk_bar48 yeniden üretilmeli)
  2) defter paneli için: python3 indir_bookdepth.py <ekim aday listesi> ... (DR50 kolu için; yoksa o kol atlanır)
  3) python3 izleme_ekim_oos.py kos && python3 izleme_ekim_oos.py analiz
"""
import os, sys
import numpy as np
import arastirma_tabanlar as TB
import arastirma_m346_prim as M

CIKTI = "/tmp/m_ekim"; os.makedirs(CIKTI, exist_ok=True)
TB.A.CIKTI = CIKTI; M.CIKTI = CIKTI
IZLE = {  # ad -> (taban no, değişiklik)
    "K_G": (None, {"MERD_GERI": "1"}),                 # madde 491, iki tabanda
    "K_GS": (None, {"MERD_GERI": "1", "MERD_GERI_TARAF": "short"}),
    "E_MS18": (2, {"MERDS_ESIK": "0.18"}),             # madde 488 (T2 +4,1)
}
TB.kur({a: d for a, (t, d) in IZLE.items()}, onek="OK")
DEFTER = os.path.exists("/tmp/derin_panel.pkl")

def kos():
    TB.A.kos()
    if DEFTER:   # madde 479 DR50/CK50 — seçim 'ls_derin'/'ls_cek' ile; ayrı çağrı
        import arastirma_m479_defter_secim as D
        D.A.CIKTI = CIKTI; D.M.CIKTI = CIKTI; D.A.kos()

def analiz():
    import pandas as pd
    def ay(ad):
        g = M.gunluk(ad); g = g[(g.index >= "2026-10-01") & (g.index < "2026-11-01")]
        return ((1 + g).prod() - 1) * 100, g.mean() / g.std() * np.sqrt(365.25) if len(g) > 5 else np.nan, len(g)
    print(f"{'kol':22s} {'Ekim %':>7s} {'Sh':>6s} {'gün':>4s} {'taban farkı':>11s}")
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
    print(f"\nT2 - T1 Ekim: {ref[2]-ref[1]:+.2f} puan → " + ("T2 kanıtı GÜÇLENDİ" if ref[2] - ref[1] >= -1 else "T2 Ekim'de geride"))

if __name__ == "__main__":
    {"kos": kos, "analiz": analiz}[sys.argv[1]]()
