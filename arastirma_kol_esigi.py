#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 271 — KOLUN SHARPE EŞİĞİ: 40 turluk red serisinin tek sayılık açıklaması.

Madde 270 kullanıcının canlı botunun **doğru boyutta pozitif** olduğunu
ölçtü (±%40, poz başına %10 → yılda +%6,0, düşüş −%36,9). Madde 241 bu
kolu harman olarak reddetmişti ama **yanlış boyutta** (sabit %20, 3 gün,
stop yok → tek başına −%75..−%99 düşüş). Red gerekçesi artık geçersiz,
yani yeniden açmak için ÖLÇÜLMÜŞ bir sebep vardı. Açıldı.

KOL, DOĞRU BOYUTTA (ortak 1.504 gün, 2022-07-20 → 2026-08-31)
-------------------------------------------------------------
    ana kitap   yıllık +%112,46 · Sharpe 2,941 · maks düşüş −%14,54
    KOL         yıllık   +%9,60 · Sharpe 0,437 · maks düşüş −%36,92
    KORELASYON  **+0,0696**  (madde 200'ün <0,10 kapısını GEÇİYOR)
    kolun dönem ayrımı: 22-24 Sharpe +0,200 · 25-26 +0,584

HARMAN CEPHESİ — karar kuralı her payda RED
-------------------------------------------
    pay   yıllık    Sharpe   düşüş    22-24    25-26
    %0   +112,46    2,941   −14,54    2,463    3,384   (kontrol)
    %5   +106,38    2,950   −13,98    2,458    3,404
    %10  +100,39    2,945   −13,96    2,449    3,400
    %15   +94,49    2,922   −14,52    2,436    3,364
    %20   +88,69    2,879   −15,14    2,417    3,291

`karar_kurali.gecer_mi()` dört şartı tek tek döndürdü ve HİÇBİR pay
geçmedi. %5'te tam dönem Sharpe +0,009 İYİLEŞİYOR ve düşüş 0,55 puan
AZALIYOR — ama şart 1 (iki dönemde birden iyileşme) 22-24'te −0,005 ile
düşüyor, şart 3 (eşit riskte getiri) −0,15 puan veriyor.

BOOTSTRAP — %5'teki iyileşme GÜRÜLTÜ
------------------------------------
Eşleştirilmiş blok bootstrap (20 günlük blok, B=3.000-4.000):
    ΔSharpe            ort +0,0074 · **P(>0) %59,4** (yazı-tura)
    Δeşit-risk getiri  ort **−3,22 puan** · P(>0) %35,4
%10'da daha kötü: P(>0) %51,2 ve −7,75 puan.

ASIL ÇIKTI — YENİDEN KULLANILABİLİR EŞİK
----------------------------------------
Reddi bir eşiğe çevirdim: kolun oynaklığına DOKUNMADAN yıllık getirisine
sabit bir miktar ekleyip (yani Sharpe'ını yükseltip) kuralın hangi
Sharpe'ta geçtiğini aradım. Pay %5, korelasyon +0,0696:

    eklenen  kol Sharpe  P(ΔSharpe>0)  P(Δeşit-risk>0)  Δeşit-risk ort
      +0       0,437         %59,4          %35,4          −3,22
      +3       0,525         %66,9          %39,1          −2,67
     +10       0,732         **%80,8**      %48,3          −1,37
     +20       1,026         %94,2          %58,4          +0,50
     +30       1,321         %98,9          %68,2          +2,40
     +50       1,911         %99,9          **%83,1**      +6,25

ÜÇ AYRI EŞİK, ÜÇÜ DE FARKLI VE EN YÜKSEĞİ BAĞLAYICI:
  * **nokta tahmini**: Sharpe ≥ **0,53** (kural dört şartı geçiyor ama
    marjlar gürültünün içinde)
  * **ΔSharpe sağlam** (P≥%80): Sharpe ≥ **0,73**
  * **Δeşit-risk sağlam** (P≥%80): Sharpe ≥ **1,91**  <-- BAĞLAYICI

Yani: **korelasyonu 0,07 olan bir kolun bu kitaptan %5 pay alabilmesi
için Sharpe'ı ~1,9 olmalı.** Kullanıcının botu 0,437'de — eşiğe
yaklaşması için Sharpe'ını yaklaşık DÖRDE KATLAMASI gerekir, bir tık
iyileştirmesi değil.

BU, 40 TURLUK RED SERİSİNİN AÇIKLAMASI
--------------------------------------
Madde 200 "korelasyon <0,10 ise büyük Sharpe farkı tolere edilir"
diyordu. **Bu kural EKSİK:** düşük korelasyon şart ama yeterli değil;
adayın kendi Sharpe'ının da bir TABANI var ve o taban kitabın
Sharpe'ıyla büyüyor. Kitap 2,941'de olduğu için taban ~1,9 — ve 212,
215, 218, 241, 251, 263, 270'te denenen kolların hepsi bu tabanın
ALTINDAYDI. Red serisi bir şanssızlık değil, bir aritmetik.

Şart 3'ün (eşit riskte getiri) bağlayıcı olması madde 251'in bulgusuyla
birebir: *"şart 3 artık gürültülü bir veto değil, Sharpe ile PARA'yı
ayıran kapı."*

BENİM YÖNTEM HATAM (kayda geçti)
--------------------------------
Eşiği ilk ararken kolun getirisini `c` ile ÇARPTIM. Bu hem ortalamayı
hem oynaklığı büyütür, yani **Sharpe değişmez** — tablo dokuz satır
boyunca 0,437 yazdı ve hiçbiri geçmedi. Sharpe'ı yükseltmek için
oynaklığa dokunmadan getiri EKLEMEK gerekiyordu. Bir eşik ararken
değiştirdiğiniz şeyin gerçekten o ölçüyü oynattığını DOĞRULAYIN.

HÜKÜM: RED (her payda, nokta tahmininde ve bootstrap'ta). Ayar
DEĞİŞMEDİ. Ama kolun yeniden açma şartı artık bir SAYI:
`kol_gecer_mi(sharpe, korelasyon)`.
"""
from __future__ import annotations

ANA = {"getiri": 112.46, "sharpe": 2.941, "dusus": -14.54,
       "erken": 2.463, "gec": 3.384}
KOL = {"getiri": 9.60, "sharpe": 0.437, "dusus": -36.92,
       "erken": 0.200, "gec": 0.584}
KORELASYON = 0.0696
ORTAK_GUN = 1504

HARMAN = {   # pay -> (yıllık, Sharpe, düşüş, 22-24, 25-26)
    0.00: (112.46, 2.941, -14.54, 2.463, 3.384),
    0.05: (106.38, 2.950, -13.98, 2.458, 3.404),
    0.10: (100.39, 2.945, -13.96, 2.449, 3.400),
    0.15: (94.49, 2.922, -14.52, 2.436, 3.364),
    0.20: (88.69, 2.879, -15.14, 2.417, 3.291),
}

BOOTSTRAP = {   # pay -> (ΔSharpe ort, P(>0)%, Δeşit-risk ort, P(>0)%)
    0.05: (0.0074, 59.4, -3.22, 35.4),
    0.10: (0.0011, 51.2, -7.75, 28.9),
}

# Eşik taraması: eklenen yıllık puan -> (kol Sharpe, P(dSh>0), P(dER>0), dER ort)
ESIK_TARAMA = {
    0: (0.437, 59.4, 35.4, -3.22),
    3: (0.525, 66.9, 39.1, -2.67),
    10: (0.732, 80.8, 48.3, -1.37),
    20: (1.026, 94.2, 58.4, 0.50),
    30: (1.321, 98.9, 68.2, 2.40),
    50: (1.911, 99.9, 83.1, 6.25),
}

ESIK_NOKTA = 0.53        # dört şart nokta tahmininde geçiyor
ESIK_SHARPE_SAGLAM = 0.73    # P(ΔSharpe>0) >= %80
ESIK_ESITRISK_SAGLAM = 1.91  # P(Δeşit-risk>0) >= %80  <- BAĞLAYICI
PAY = 0.05
GUC_CITASI = 80.0

YONTEM_HATAM = ("eşiği ilk ararken kolun getirisini c ile ÇARPTIM; bu hem "
                "ortalamayı hem oynaklığı büyütür, Sharpe DEĞİŞMEZ (tablo "
                "dokuz satır 0,437 yazdı). Sharpe'ı yükseltmek için "
                "oynaklığa dokunmadan getiri EKLEMEK gerekiyordu.")

REDDEDILEN_KOLLAR = (212, 215, 218, 241, 251, 263, 270)


def korelasyon_kapisi_geciyor_mu() -> bool:
    """Madde 200: korelasyon < 0,10 ise büyük Sharpe farkı tolere edilir."""
    return KORELASYON < 0.10


def hicbir_pay_gecmiyor_mu() -> bool:
    """Harman cephesinde şart 1 (iki dönemde Sharpe) hiç geçmiyor mu?"""
    k = HARMAN[0.00]
    return all(not (v[3] > k[3] and v[4] > k[4])
               for p, v in HARMAN.items() if p > 0)


def bes_pay_iyilesmesi_gurultu_mu() -> bool:
    """%5'teki +0,009 Sharpe iyileşmesi gürültü mü?"""
    return BOOTSTRAP[0.05][1] < GUC_CITASI


def baglayici_esik() -> float:
    """Üç eşiğin en yükseği bağlayıcıdır."""
    return max(ESIK_NOKTA, ESIK_SHARPE_SAGLAM, ESIK_ESITRISK_SAGLAM)


def kol_gecer_mi(sharpe: float, korelasyon: float,
                 pay: float = PAY) -> dict:
    """Bir kol bu kitaptan pay alabilir mi? (madde 271'in eşiği)

    Eşik, ölçümün yapıldığı korelasyon (+0,0696) ve pay (%5) için
    kalibre edildi. Daha YÜKSEK korelasyon eşiği yükseltir, daha düşük
    pay düşürür; ikisi de bu tabloda ölçülmedi, bu yüzden fonksiyon
    yalnızca kalibrasyona yakın girdilerde güvenilir.
    """
    e = baglayici_esik()
    uyari = []
    if korelasyon >= 0.10:
        uyari.append("korelasyon madde 200'ün kapısını GEÇMİYOR")
    if abs(korelasyon - KORELASYON) > 0.05:
        uyari.append("korelasyon kalibrasyondan (+0,070) uzak; eşik yeniden "
                     "ölçülmeli")
    if abs(pay - PAY) > 0.001:
        uyari.append("pay kalibrasyondan (%5) farklı; eşik yeniden ölçülmeli")
    return {
        "gecer": bool(sharpe >= e and korelasyon < 0.10),
        "esik": e,
        "fark": round(sharpe - e, 3),
        "kat": round(e / sharpe, 2) if sharpe > 0 else None,
        "uyari": uyari,
    }


def madde_200_eksik_mi() -> str:
    return ("Madde 200 'korelasyon <0,10 ise büyük Sharpe farkı tolere "
            "edilir' diyordu; EKSİK. Düşük korelasyon şart ama yeterli "
            "değil: adayın kendi Sharpe'ının bir TABANI var ve o taban "
            "kitabın Sharpe'ıyla büyüyor. Kitap 2,941'de olduğu için taban "
            "~%.2f; madde %s'te denenen kolların hepsi bu tabanın "
            "ALTINDAYDI. Red serisi şanssızlık değil, ARİTMETİK."
            % (baglayici_esik(), "/".join(str(m) for m in REDDEDILEN_KOLLAR)))


def hukum() -> str:
    r = kol_gecer_mi(KOL["sharpe"], KORELASYON)
    return ("RED her payda. Kol Sharpe %.3f, bağlayıcı eşik %.2f -> eşiğe "
            "ulaşmak için Sharpe'ı %.1f KAT artması gerekir. Ayar DEĞİŞMEDİ."
            % (KOL["sharpe"], r["esik"], r["kat"]))


def yaz() -> None:
    print("MADDE 271 — KOLUN SHARPE EŞİĞİ\n")
    print("KOL (madde 270'in doğru boyutu), ortak %d gün:" % ORTAK_GUN)
    print("  ana kitap  yıllık +%%%.2f · Sharpe %.3f · düşüş %%%.2f"
          % (ANA["getiri"], ANA["sharpe"], ANA["dusus"]))
    print("  KOL        yıllık  +%%%.2f · Sharpe %.3f · düşüş %%%.2f"
          % (KOL["getiri"], KOL["sharpe"], KOL["dusus"]))
    print("  korelasyon %+.4f -> madde 200 kapısı: %s"
          % (KORELASYON, "GEÇER" if korelasyon_kapisi_geciyor_mu() else "RED"))
    print("\nHARMAN CEPHESİ (pay: yıllık / Sharpe / düşüş / 22-24 / 25-26):")
    for p in sorted(HARMAN):
        v = HARMAN[p]
        print("  %%%3.0f  %+8.2f  %.3f  %+7.2f  %.3f  %.3f"
              % (p * 100, v[0], v[1], v[2], v[3], v[4]))
    print("  -> hiçbir pay şart 1'i geçmiyor: %s" % hicbir_pay_gecmiyor_mu())
    print("\nBOOTSTRAP (%%5): ΔSharpe %+.4f P(>0) %%%.1f | Δeşit-risk %+.2f "
          "puan P(>0) %%%.1f -> gürültü mü: %s"
          % (BOOTSTRAP[0.05][0], BOOTSTRAP[0.05][1], BOOTSTRAP[0.05][2],
             BOOTSTRAP[0.05][3], bes_pay_iyilesmesi_gurultu_mu()))
    print("\nEŞİK TARAMASI (kola sabit getiri ekle, oynaklık sabit):")
    print("  eklenen | kol Sharpe | P(ΔSh>0) | P(ΔER>0) | ΔER ort")
    for ek in sorted(ESIK_TARAMA):
        v = ESIK_TARAMA[ek]
        print("  %+7d |   %+8.3f |   %%%5.1f  |   %%%5.1f  | %+7.2f"
              % (ek, v[0], v[1], v[2], v[3]))
    print("\nÜÇ EŞİK: nokta %.2f · ΔSharpe sağlam %.2f · Δeşit-risk sağlam "
          "%.2f (BAĞLAYICI)"
          % (ESIK_NOKTA, ESIK_SHARPE_SAGLAM, ESIK_ESITRISK_SAGLAM))
    print("\n%s" % madde_200_eksik_mi())
    print("\nYÖNTEM HATAM: %s" % YONTEM_HATAM)
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
