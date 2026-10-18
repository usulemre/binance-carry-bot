#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 268 — FUNDING MUHASEBESİ: potansiyeli madde 265'in on katı olan
varsayımın denetimi. SONUÇ: TEMİZ.

NEDEN BU EKSEN
--------------
Madde 265 giriş dolumunu (0,8 puan), 266 gün içi düşüşü, 267 TP dolumunu
doğruladı. Sırada motorun en büyük tek kalemi vardı: **funding
muhasebesi.** Madde 214'e göre brüt funding **+109,8 puan/yıl** ve ham
fiyatın −108,0'ı ile birbirini götürüyor. Bu demek ki funding'de
sistematik bir **yüzde bir** hata, dipteki sayıda ~1,1 puan; ızgara
hizalaması kaynaklı bir **1/15** hatası ise **~7 puan** olurdu — yani
madde 265'in bulduğu sapmanın dokuz katı.

ŞÜPHENİN SEBEBİ SOMUTTU: dilimler 8 saatte bir açılıyor (madde 264) ve
Binance funding'i de 8 saatte bir ödüyor (00:00/08:00/16:00 UTC). İki
ızgara çakışıyorsa, açılış anındaki ödeme ya iki kez sayılır ya hiç
sayılmaz.

YAPISAL OKUMA (kod)
-------------------
    g33.py:403   fu = np.where(cik, 0.0, -poz * fv[i+1])

ve `ODEME` paneli (`carry_backtest.panel_yukle`) bir ödemeyi
`searchsorted(C.index, t, "right") - 1` ile **tam bir kez** bir bara
yazıyor. Yani:
  * Bar i'de AÇILAN bacağa, bar i'ye yazılmış ödeme VERİLMEZ (fv[i+1]
    kullanılıyor) -> açılış anındaki ödeme yeni bacağa yazılmaz.
  * Çıkış barında funding sayılmaz (`np.where(cik, 0.0, ...)`).
İki uçta da ihtiyatlı. Ama bu projede okumak yetmez.

ÖLÇÜM — MUHASEBE KİMLİĞİ
------------------------
Soru: panel, ham ödemelerin TAMAMINI ve YALNIZ BİR KEZ mi taşıyor?
Test: her sembol için, panelde fiyatı olan ilk ve son bar arasında
      ham ödemelerin toplamı == ODEME panelinin toplamı.

    tüm panel (840 sembol)   ham −50,512322 · panel −50,399189
                             fark **+%0,224** · 741/840 sembol %0,1 içinde
    uygun evren (20 sembol)  ham +1,828971 · panel +1,832485
                             fark **+%0,192** · 16/20 sembol %0,1 içinde

Kalan sapma, kapsamın ilk/son barındaki sınır atfından geliyor ve
toplamı küçük olan sembollerde yüzde olarak büyük görünüyor (örn.
STRCUSDT ham −0,0119 panel +0,0097: mutlak fark 2,2e-02).

**HÜKÜM: funding muhasebesi TEMİZ.** Izgara çakışmasından kaynaklanan
ne çift sayım ne kayıp var; şüphelenilen ~7 puanlık hata YOK. Madde
214'ün +109,8'i ayakta.

İKİ HATA — İKİSİ DE SÜTUN ADI, İKİSİ DE AYNI TURDA
--------------------------------------------------
1. İlk denemede sütun seçimini `"ate" in c.lower()` ile yaptım; bu
   **"date"** sütununu da yakaladı ve `kol[0]` tarih oldu. Sonuç: 0
   sembol, "fark %0,0000" — **yanlış bir TEMİZ sonucu.** Sıfır örneklemle
   gelen bir "geçti" en kötü geçiştir.
2. Düzeltince `data_funding/` (sütun `rate`, 183 sembol) ile kıyasladım,
   oysa panel `data_funding_genis/`ten (sütun `funding`, 847 sembol)
   kurulmuş. İki FARKLI veri setini karşılaştırmış oldum ve **−%19,5**
   gibi sahte bir sapma, hatta FTTUSDT'de işaret değişimi gördüm. Doğru
   kaynakla fark **+%0,224**.

Ders: bir denetimin kendi VERİ KAYNAĞI da denetlenmeli. "Panel neyden
kuruldu" sorusu, "panel doğru mu" sorusundan önce gelir. Ve n=0 ile
dönen bir doğrulama başarı değil, test hatasıdır — bu modül bu yüzden
`dogrula()` içinde örneklem sayısını da şart koşuyor.
"""
from __future__ import annotations

KAYNAK_DIZIN = "data_funding_genis"      # panelin GERÇEK kaynağı
KAYNAK_SUTUN = "funding"
ESKI_DIZIN = "data_funding"              # farklı/eski set, sütun "rate"

TUM_PANEL = {"sembol": 840, "ham": -50.512322, "panel": -50.399189,
             "fark_pct": 0.223970, "yuzde01_icinde": 741}
UYGUN_EVREN = {"sembol": 20, "ham": 1.828971, "panel": 1.832485,
               "fark_pct": 0.192139, "yuzde01_icinde": 16}

# Madde 214: brüt funding ve ham fiyat birbirini götürüyor
BRUT_FUNDING_PUAN = 109.8
IZGARA_HATASI_OLSAYDI_PUAN = BRUT_FUNDING_PUAN / 15.0   # ~7,3

HATALAR = (
    "sütun seçimi 'ate' kalıbıyla yapıldı -> 'date' sütunu yakalandı, "
    "n=0 ile YANLIŞ bir TEMİZ sonucu geldi",
    "panel data_funding_genis'ten kurulmuşken data_funding ile "
    "kıyaslandı -> sahte −%19,5 sapma ve FTTUSDT'de işaret değişimi",
)


def kimlik_tutuyor_mu(esik_pct: float = 1.0) -> bool:
    """Panel, ham ödemelerin tamamını yalnız bir kez mi taşıyor?"""
    return (abs(TUM_PANEL["fark_pct"]) < esik_pct
            and abs(UYGUN_EVREN["fark_pct"]) < esik_pct)


def ornek_yeterli_mi() -> bool:
    """n=0 ile gelen bir 'geçti' testin hatasıdır (madde 268'in 1. hatası)."""
    return TUM_PANEL["sembol"] > 100 and UYGUN_EVREN["sembol"] >= 10


def dogrula() -> bool:
    return kimlik_tutuyor_mu() and ornek_yeterli_mi()


def izgara_hatasi_var_mi() -> bool:
    """8 saatlik dilim ızgarası ile funding ızgarası çakışmasından
    kaynaklanan çift sayım / kayıp var mı?"""
    return not kimlik_tutuyor_mu()


def kacirilan_puan() -> float:
    """Ölçülen sapmanın yıllık puan karşılığı (brüt funding üzerinden)."""
    return BRUT_FUNDING_PUAN * UYGUN_EVREN["fark_pct"] / 100.0


def hukum() -> str:
    return ("Funding muhasebesi TEMİZ: ızgara çakışmasından ne çift sayım "
            "ne kayıp var, şüphelenilen ~%.1f puanlık hata YOK. "
            "Ayar DEĞİŞMEDİ." % IZGARA_HATASI_OLSAYDI_PUAN)


def yaz() -> None:
    print("MADDE 268 — FUNDING MUHASEBESİ DENETİMİ\n")
    print("şüphe: dilimler 8 saatte bir açılıyor, funding 8 saatte bir ödeniyor")
    print("ızgara hatası olsaydı bedeli: ~%.1f puan/yıl (brüt funding %.1f / 15)"
          % (IZGARA_HATASI_OLSAYDI_PUAN, BRUT_FUNDING_PUAN))
    print("\nMUHASEBE KİMLİĞİ (ham ödemeler == ODEME paneli):")
    for ad, d in (("tüm panel", TUM_PANEL), ("uygun evren", UYGUN_EVREN)):
        print("  %-12s %3d sembol | ham %+.6f panel %+.6f | fark %+.4f%% | %%0,1 içinde %d"
              % (ad, d["sembol"], d["ham"], d["panel"], d["fark_pct"],
                 d["yuzde01_icinde"]))
    print("\n  kimlik tutuyor mu: %s | örneklem yeterli mi: %s"
          % (kimlik_tutuyor_mu(), ornek_yeterli_mi()))
    print("  ızgara hatası var mı: %s" % izgara_hatasi_var_mi())
    print("  ölçülen sapmanın karşılığı: %.3f puan/yıl" % kacirilan_puan())
    print("\nBU TURDA YAPTIĞIM İKİ HATA (ikisi de sütun adı):")
    for i, h in enumerate(HATALAR, 1):
        print("  %d) %s" % (i, h))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
