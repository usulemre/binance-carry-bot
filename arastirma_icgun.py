#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 266 — GÜN İÇİ DÜŞÜŞ ve LİKİDASYON: motorda "YOK" yazdığım riskin ilk ÖLÇÜMÜ.

40+ turdur şu iki cümleyi yazdım: *"motor likidasyonu modellemiyor"* ve
*"yayınlanan düşüş rakamlarında bu YOK"* (madde 225/227/261). İkisi de
doğruydu ama hiçbiri SAYI değildi. Madde 265'in dakika verisi o sayıyı
mümkün kıldı.

İKİ SORU
--------
(1) Yayınlanan düşüş GÜNLÜK kapanışlardan hesaplanıyor. Gün içindeki
    gerçek yol ne kadar daha kötü?
(2) Çapraz teminatta likidasyon hangi düşüşte gelir, ve doz tablosunun
    hangi satırında bu bağlayıcı olur?

YÖNTEM (ön kayıt)
-----------------
Dakika verisi (madde 265: `data_1m/`, 18 sembol, 2026-07-01 → 2026-08-31,
89.280 dakika). Kitabın YAPISI birebir kuruldu: 5+5 nötr bacak, **15
örtüşen dilim**, her 8 saatte bir yeni dilim, 5 gün tutma, brüt 1,0,
bacak başına eşit para. Seçim RASTGELE (40 tohum) — çünkü ölçülen şey
stratejinin getirisi değil, **gözlem sıklığının** düşüş ölçümüne etkisi.

BULGU 1 — GÜN İÇİ DÜŞÜŞ, GÜNLÜK KAPANIŞIN ~1,5 KATI
---------------------------------------------------
    ölçü        | 1 dakika | 1 gün (kapanış)
    ortalama    |  −%16,15 |  −%10,37
    medyan      |  −%14,14 |  −%9,07
    EN KÖTÜ     |  −%41,41 |  −%26,61

    BÜYÜTME (1dk / 1g): medyan **1,49** · ortalama 1,80 · p90 **2,72**
                        · maksimum **8,15**

Yani **büyütme sabit bir çarpan değil, kuyruk olayı.** Yolların yarısında
1,5 kat, onda birinde 2,7 kattan fazla.

BULGU 2 — HİPOTEZİM YANLIŞ ÇIKTI: DİBİ KASKAD YAPMIYOR
------------------------------------------------------
Dakika verisinde çarpıcı bir olay var: **2026-08-22 05:10'da yedi sembol
aynı dakikada çöküyor** (PUMP −%14,25 · WLD −%12,80 · ZEC −%10,13 · ADA
−%9,40 · LINK −%9,10), hepsi gerçek ciroyla — veri hatası değil, piyasa
çapında bir likidasyon kaskadı. "Dibi bu yapıyor olmalı" dedim.

**Yanlıştı.** O saatte (05:00-06:00) nötr sepetin kaybı medyan yalnızca
**−%0,31** (en kötü tohumda −%1,68). Sebebi mekanizmanın kendisi:
piyasa çapında bir çöküş tam olarak nötr kitabın KORUNDUĞU şeydir —
longlar düşerken shortlar kazanır.

Dibi yapan şey **tek sembollük (idiyosinkratik) hareket**: 40 tohumun
**22'si** 2026-08-09'da dibe vuruyor (CYSUSDT'nin −%12,58'lik dakikası).
**Nötr kitabın gün içi riski piyasa riskinde değil, TEK İSİM riskinde.**
Bu, madde 236'nın "zararlar ve kazançlar aynı popülasyonda" bulgusunun
zaman ekseni karşılığı.

BULGU 3 — LİKİDASYON, ÇAPRAZ TEMİNATTA BAĞLAYICI DEĞİL
------------------------------------------------------
Çapraz teminatta likidasyon: öz kaynak <= bakım marjı, yani
    1 + g·r <= mmr·g   ->   r <= (mmr·g − 1) / g
(g = brüt, r = kaldıraçsız portföy hareketi, mmr = bakım marjı oranı.)

    brüt  | mmr %0,5 | mmr %1,0 | mmr %2,5
    1,00x |  −%99,5  |  −%99,0  |  −%97,5
    1,50x |  −%66,2  |  −%65,7  |  −%64,2
    2,00x |  −%49,5  |  −%49,0  |  −%47,5
    2,50x |  −%39,5  |  −%39,0  |  −%37,5
    3,00x |  −%32,8  |  −%32,3  |  −%30,8

Madde 261'in 1 yıllık p95 düşüşüne 1,49 büyütme uygulanınca:

    brüt  | p95 günlük | p95 ~dakika | likidasyon payı
    1,00x |    %21,0   |    %31,3    |  67,7 puan
    1,50x |    %30,5   |    %45,4    |  53,1 puan
    2,00x |    %39,4   |    %58,7    |  39,3 puan
    2,50x |    %47,3   |    %70,5    |  27,0 puan
    3,00x |    %54,0   |    %80,5    |  16,5 puan

**Sonuç: likidasyon 3x'e kadar bile ilk bağlayıcı kısıt DEĞİL.** Çapraz
teminatta bakım marjı öz kaynağın küçük bir yüzdesi olduğu için eşik
pratikte "hepsini kaybet" seviyesinde. Sizi ilk öldüren şey likidasyon
değil, **düşüşün kendisi**: 3x'te p95 bir yılda gün içi −%80 görmek
demek, ve bu toplam silinmeye 16,5 puan uzak.

AMA TEK İSİM KUYRUĞU BAĞLAYICI OLUYOR: ölçülen en kötü tohum **2 AYDA**
−%41,41 (brüt 1,0). 2,5x'in likidasyon eşiği −%39,0 → **o yol 2,5x'te
likide edilirdi.** p95 rahat görünürken kuyruk görünmüyor.

İKİ SAPMA, İKİ YÖNE — net bir düzeltme İDDİA EDİLMİYOR
------------------------------------------------------
* **Yukarı saptıran:** seçim RASTGELE. Gerçek kitabın filtreleri var
  (madde 196 pompa elemesi, 183 donuk seri, 133 listelenme yaşı, 100M$
  ciro) ve rastgele seçim BEATUSDT (2 ayda −%95,8) gibi isimleri
  ayıklamıyor. Yani 1,49 büyütme gerçek kitap için bir TAVAN olabilir.
* **Aşağı saptıran:** yalnızca 2 ay ve 18 sembol. Kuyruk olayları için
  2 ay kısa; 4,1 yıllık örnekte daha kötü dakikalar olabilir.
İki sapma zıt yönde olduğu için burada tek bir düzeltilmiş sayı
verilmiyor. Verilen şey: **yayınlanan düşüş rakamları gün içi yolu
GÖSTERMİYOR ve medyanda ~1,5 kat iyimser.**

HÜKÜM: ayar DEĞİŞMEDİ. Doz kararına bir kısıt EKLENDİ: dozun fiyatı
yalnızca "bir yılda −%X" değil, "gün içinde ~1,5X" ve 2,5x'te tek
sembollük bir kuyruk likidasyon mesafesinde.
"""
from __future__ import annotations

import numpy as np

# Ölçüm (40 tohum, brüt 1,0, dakika çözünürlüklü)
OLCUM = {
    "tohum": 40, "sembol": 18, "dakika": 89280,
    "dk1_ort": -16.15, "dk1_medyan": -14.14, "dk1_en_kotu": -41.41,
    "g1_ort": -10.37, "g1_medyan": -9.07, "g1_en_kotu": -26.61,
    "buyutme_ort": 1.803, "buyutme_medyan": 1.488,
    "buyutme_p90": 2.722, "buyutme_max": 8.153,
}
BUYUTME = OLCUM["buyutme_medyan"]

# Kaskad testi: hipotez ÇÜRÜDÜ
KASKAD = {
    "an": "2026-08-22 05:10",
    "sembol_sayisi": 7,
    "ornek": {"PUMPUSDT": -14.25, "WLDUSDT": -12.80, "ZECUSDT": -10.13,
              "ADAUSDT": -9.40, "LINKUSDT": -9.10},
    "sepet_kaybi_medyan": -0.31,
    "sepet_kaybi_en_kotu": -1.68,
    "dibi_yapan_gun": "2026-08-09",
    "dibi_yapan_tohum": 22,
}

# madde 261'in doz tablosu (1 yıl p95, GÜNLÜK kapanıştan)
P95_GUNLUK = {1.00: 21.0, 1.25: 25.7, 1.50: 30.5,
              2.00: 39.4, 2.50: 47.3, 3.00: 54.0}


def likidasyon_esigi(brut: float, mmr: float = 0.010) -> float:
    """Çapraz teminatta likidasyon eşiği: kaldıraçsız portföy hareketi (%).

    1 + g*r <= mmr*g  ->  r <= (mmr*g - 1)/g
    """
    return (mmr * brut - 1.0) / brut * 100.0


def p95_icgun(brut: float, buyutme: float = BUYUTME) -> float:
    """Doz tablosunun p95 düşüşünün gün içi tahmini (%, pozitif)."""
    return P95_GUNLUK[brut] * buyutme


def likidasyon_payi(brut: float, mmr: float = 0.010) -> float:
    """Kaldıraçlı cinsten likidasyona kalan puan."""
    return abs(likidasyon_esigi(brut, mmr)) * brut - p95_icgun(brut)


def likidasyon_baglayici_mi(brut: float, mmr: float = 0.010) -> bool:
    """p95 yolunda likidasyon gelir mi? (gelmezse pay > 0)"""
    return likidasyon_payi(brut, mmr) <= 0


def kuyruk_likide_eder_mi(brut: float, mmr: float = 0.010) -> bool:
    """ÖLÇÜLEN en kötü yol (2 ay, −%41,41) bu brütte likide edilir mi?"""
    return OLCUM["dk1_en_kotu"] <= likidasyon_esigi(brut, mmr)


def kaskad_hipotezi_tuttu_mu() -> bool:
    """"Dibi piyasa çapındaki kaskad yapıyor" hipotezi doğru muydu? HAYIR."""
    return abs(KASKAD["sepet_kaybi_medyan"]) > 5.0


def sapma_yonu() -> dict:
    return {
        "yukari": "rastgele seçim; gerçek kitabın filtreleri yok -> 1,49 bir TAVAN olabilir",
        "asagi": "yalnızca 2 ay / 18 sembol; kuyruk için kısa -> daha kötü dakikalar olabilir",
    }


def yaz() -> None:
    print("MADDE 266 — GÜN İÇİ DÜŞÜŞ ve LİKİDASYON\n")
    print("BÜYÜTME (1 dakika / 1 gün kapanış), 40 tohum:")
    print("  medyan %.3f · ortalama %.3f · p90 %.3f · maks %.3f"
          % (OLCUM["buyutme_medyan"], OLCUM["buyutme_ort"],
             OLCUM["buyutme_p90"], OLCUM["buyutme_max"]))
    print("  düşüş 1dk  ort %+.2f medyan %+.2f EN KÖTÜ %+.2f"
          % (OLCUM["dk1_ort"], OLCUM["dk1_medyan"], OLCUM["dk1_en_kotu"]))
    print("  düşüş 1g   ort %+.2f medyan %+.2f EN KÖTÜ %+.2f"
          % (OLCUM["g1_ort"], OLCUM["g1_medyan"], OLCUM["g1_en_kotu"]))
    print("\nKASKAD HİPOTEZİ (%s, %d sembol aynı dakikada):"
          % (KASKAD["an"], KASKAD["sembol_sayisi"]))
    print("  nötr sepet kaybı medyan %+.2f%% (en kötü %+.2f%%) -> hipotez %s"
          % (KASKAD["sepet_kaybi_medyan"], KASKAD["sepet_kaybi_en_kotu"],
             "TUTTU" if kaskad_hipotezi_tuttu_mu() else "ÇÜRÜDÜ"))
    print("  dibi yapan gün %s (%d/40 tohum) = TEK SEMBOL hareketi"
          % (KASKAD["dibi_yapan_gun"], KASKAD["dibi_yapan_tohum"]))
    print("\nDOZ TABLOSU + GÜN İÇİ + LİKİDASYON (mmr %1,0):")
    print("  brüt | p95 günlük | p95 ~dakika | likid. eşiği | pay (puan) | kuyruk likide eder?")
    for g in sorted(P95_GUNLUK):
        print("  %4.2fx |   %6.1f%%  |   %6.1f%%   |   %6.1f%%    |   %6.1f   | %s"
              % (g, P95_GUNLUK[g], p95_icgun(g), likidasyon_esigi(g),
                 likidasyon_payi(g), "EVET" if kuyruk_likide_eder_mi(g) else "hayır"))
    print("\nSAPMA YÖNLERİ (net düzeltme İDDİA EDİLMİYOR):")
    for k, v in sapma_yonu().items():
        print("  %-6s %s" % (k + ":", v))
    print("\nHÜKÜM: ayar DEĞİŞMEDİ; doz kararına kısıt eklendi.")


if __name__ == "__main__":
    yaz()
