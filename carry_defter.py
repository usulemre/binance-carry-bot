"""P&L MUHASEBE DEFTERİ — dolar bazlı, sent seviyesinde mutabakatlı.

NEDEN: madde 134.5'te "funding +146.6%, fiyat +35.3%" yazdım ama net
sonuç ~+30%/yıl. Bu üç rakam birbirine dönüşmüyordu çünkü İLK İKİSİ
DOLAR DEĞİL: her barın getiri ORANININ toplamıydı (Σ r_t), yani
bileşiklenmemiş ve o anki equity'ye göre ölçeklenmemiş bir sayı.

Bu modül aynı backtest'i DOLAR defteri tutarak çalıştırır ve şu
özdeşliği sent seviyesinde doğrular:

    başlangıç equity
      + fiyat P&L (mark-to-market)
      + funding nakit akışı
      - komisyon
      - kayma
      - diğer maliyetler
      = final equity

Bar sırası (bt2 ile BİREBİR aynı, sadece dolar cinsinden):
  1. rebalance varsa: ucret = E * devir * kom  ->  E -= ucret
  2. fiyat$   = E * Σ(poz * bar_getirisi)
  3. funding$ = E * Σ(-poz * odenen_oran)
  4. E_sonraki = E + fiyat$ + funding$

Adım 1'in adım 2-3'ten ÖNCE gelmesi önemli: ücret, getiri yazılmadan
önceki equity üzerinden alınır. bt2'de `eq[-1] *= (1-devir*kom)`
tam olarak bunu yapıyor.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# KOM bileşenleri (bt2'de tek sayı olarak birleştirilmişti)
# MADDE 234 — BU 6bp KASITLI KÖTÜMSERDİR, BAYAT DEĞİL. Motor 2bp/yön
# kullanıyor (GTX post-only maker giriş + reduce-only limit çıkış,
# ikisi de maker) ve beklenti +%112,5 o varsayımla ölçüldü. Buradaki
# 6bp, madde 134'ün ÇÜRÜTME denetiminin varsayımı: taker komisyonu +
# kayma. Madde 213'e göre 1bp ≈ 1,65 puan yıllık getiri, yani aradaki
# 4bp ≈ 6,6 puan - bilerek kötümser bir alt sınır.
# DÜZELTMEYE ÇALIŞMAYIN: bu araç "en kötü durumda bile kâr var mı"
# sorusunu yanıtlıyor, "beklenti ne" sorusunu değil.
KOM_KOMISYON = 0.0004   # %0.04 taker komisyonu, tek yön (kötümser)
KOM_KAYMA = 0.0002      # %0.02 kayma, tek yön (kötümser)
KOM_TOPLAM = KOM_KOMISYON + KOM_KAYMA


def defter(C, ODEME, skor, uygun, n=12, reb=30, lag=1, bas=1200,
           kom_komisyon=KOM_KOMISYON, kom_kayma=KOM_KAYMA,
           baslangic_equity=10000.0, min_bacak=8):
    """Dolar bazlı defter. bt2 ile aynı kararları verir.

    Döner: (portfoy_df, sembol_df, ozet_dict)
      portfoy_df: her bar için E_basi, fiyat$, funding$, ucret$, E_sonu
      sembol_df : her sembol için toplam fiyat$, funding$, ucret$
    """
    cv, fv = C.values, ODEME.values
    UY = uygun.values
    idx, kol = C.index, list(C.columns)
    nk = len(kol)

    poz = np.zeros(nk)                 # ağırlık (equity'nin kesri, işaretli)
    E = float(baslangic_equity)
    bek = None

    # sembol bazlı dolar birikimleri
    s_fiyat = np.zeros(nk)
    s_funding = np.zeros(nk)
    s_komisyon = np.zeros(nk)
    s_kayma = np.zeros(nk)
    s_islem = np.zeros(nk, dtype=int)

    satirlar = []
    brut_notional_top = 0.0
    bar_sayisi = 0

    for i in range(bas, len(C) - 1):
        E_bar_basi = E
        ucret_komisyon = ucret_kayma = 0.0
        devir = 0.0

        # --- 1) REBALANCE: ücret, getiri yazılmadan ÖNCEKİ equity üzerinden
        if bek is not None and bek[0] == i:
            y = bek[1]
            d_vec = np.abs(y - poz)
            devir = float(d_vec.sum())
            ucret_komisyon = E * devir * kom_komisyon
            ucret_kayma = E * devir * kom_kayma
            s_komisyon += E * d_vec * kom_komisyon
            s_kayma += E * d_vec * kom_kayma
            s_islem += (d_vec > 1e-12).astype(int)
            E -= (ucret_komisyon + ucret_kayma)
            poz, bek = y, None

        # --- yeni hedef seçimi (uygulama bir bar sonra)
        if (i - bas) % reb == 0:
            s = skor.iloc[i]
            g = s.notna().values & np.isfinite(cv[i]) & UY[i]
            m = int(g.sum())
            nn = min(n, m // 2)
            if nn >= min_bacak:
                sv = np.where(g, s.values, np.nan)
                sira = np.argsort(np.where(np.isnan(sv), np.inf, sv))
                L, S = sira[:nn], sira[m - nn:m]
                y = np.zeros(nk)
                y[L] = 0.5 / nn
                y[S] = -0.5 / nn
                bek = (i + lag, y)

        # --- 2) FİYAT P&L (mark-to-market), ücret sonrası equity üzerinden
        ham = (cv[i + 1] - cv[i]) / np.where(cv[i] == 0, np.nan, cv[i])
        gecerli = np.isfinite(cv[i]) & np.isfinite(cv[i + 1])
        br = np.where(gecerli, np.nan_to_num(ham), 0.0)
        fiyat_vec = E * poz * br
        fiyat_d = float(fiyat_vec.sum())
        s_fiyat += fiyat_vec

        # --- 3) FUNDING nakit akışı
        f = np.nan_to_num(fv[i + 1])
        funding_vec = E * (-poz) * f
        funding_d = float(funding_vec.sum())
        s_funding += funding_vec

        # --- 4) yeni equity
        E_sonu = E + fiyat_d + funding_d

        brut = float(np.abs(poz).sum()) * E
        brut_notional_top += brut
        bar_sayisi += 1

        satirlar.append({
            "tarih": idx[i + 1],
            "E_bar_basi": E_bar_basi,
            "ucret_komisyon": -ucret_komisyon,
            "ucret_kayma": -ucret_kayma,
            "E_ucret_sonrasi": E,
            "fiyat_pnl": fiyat_d,
            "funding_pnl": funding_d,
            "E_bar_sonu": E_sonu,
            "brut_notional": brut,
            "devir": devir,
        })
        E = E_sonu

    P = pd.DataFrame(satirlar).set_index("tarih")
    S = pd.DataFrame({
        "fiyat_pnl": s_fiyat, "funding_pnl": s_funding,
        "komisyon": -s_komisyon, "kayma": -s_kayma, "islem": s_islem,
    }, index=kol)
    S["net_pnl"] = S.fiyat_pnl + S.funding_pnl + S.komisyon + S.kayma
    S = S[(S.fiyat_pnl != 0) | (S.funding_pnl != 0) | (S.komisyon != 0)]

    ozet = {
        "E0": float(baslangic_equity),
        "fiyat_pnl": float(P.fiyat_pnl.sum()),
        "funding_pnl": float(P.funding_pnl.sum()),
        "komisyon": float(P.ucret_komisyon.sum()),
        "kayma": float(P.ucret_kayma.sum()),
        "finansman": 0.0,       # perpetual futures: funding DIŞINDA taşıma yok
        "likidasyon": 0.0,      # brüt 1x, kaldıraç yok -> zorunlu kapama yok
        "E_final": float(P.E_bar_sonu.iloc[-1]),
        "bar": bar_sayisi,
        "ort_brut_notional": brut_notional_top / max(bar_sayisi, 1),
        "toplam_devir": float(P.devir.sum()),
        "gun": (P.index[-1] - P.index[0]).days,
    }
    return P, S, ozet


def mutabakat_yazdir(P, S, o, etiket="TAM DÖNEM"):
    E0, Ef = o["E0"], o["E_final"]
    toplam = (E0 + o["fiyat_pnl"] + o["funding_pnl"] + o["komisyon"]
              + o["kayma"] + o["finansman"] + o["likidasyon"])
    fark = Ef - toplam

    print(f"\n{'=' * 74}")
    print(f"  MUTABAKAT TABLOSU — {etiket}")
    print(f"{'=' * 74}")
    print(f"  {'başlangıç equity':<34}{E0:>18,.6f} USD")
    print(f"  {'+ fiyat P&L (mark-to-market)':<34}{o['fiyat_pnl']:>+18,.6f} USD")
    print(f"  {'+ funding nakit akışı':<34}{o['funding_pnl']:>+18,.6f} USD")
    print(f"  {'- komisyon':<34}{o['komisyon']:>+18,.6f} USD")
    print(f"  {'- kayma':<34}{o['kayma']:>+18,.6f} USD")
    print(f"  {'- finansman/borç maliyeti':<34}{o['finansman']:>+18,.6f} USD")
    print(f"  {'- likidasyon/zorunlu kapama':<34}{o['likidasyon']:>+18,.6f} USD")
    print(f"  {'-' * 52}")
    print(f"  {'= hesaplanan final equity':<34}{toplam:>18,.6f} USD")
    print(f"  {'  gerçek final equity':<34}{Ef:>18,.6f} USD")
    print(f"  {'  FARK':<34}{fark:>+18.10f} USD")
    durum = "TUTUYOR (sent altı)" if abs(fark) < 0.01 else "TUTMUYOR"
    print(f"  {'  DURUM':<34}{durum:>18}")

    # sembol toplamları portföy toplamlarıyla uyuşuyor mu?
    print(f"\n  ÇAPRAZ KONTROL — sembol toplamı == portföy toplamı")
    for ad, pk, sk_ in [("fiyat P&L", "fiyat_pnl", "fiyat_pnl"),
                        ("funding P&L", "funding_pnl", "funding_pnl"),
                        ("komisyon", "ucret_komisyon", "komisyon"),
                        ("kayma", "ucret_kayma", "kayma")]:
        a, b = float(P[pk].sum()), float(S[sk_].sum())
        print(f"    {ad:<14}portföy {a:>+16,.6f} | sembol {b:>+16,.6f} | fark {a - b:>+.10f}")
    return fark
