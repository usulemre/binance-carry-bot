#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DOZ ÖLÇÜTÜ — MADDE 287'nin `coz()`/`net()` HESAPLAYICISI, GERİ YAZILDI.

MADDE 337: konteyner kaybında (madde 335) bu hesaplayıcı gitti. Projede
yalnız SONUÇLARI kaldı (`arastirma_kosulan_kitap_beklentisi.py`'de
`DOZ_PARITE`, `HIZA`; `arastirma_trend_13x3.py`'de net'ler). Yani
kitapta "net +168,83" gibi sayılar vardı ama onları ÜRETEN kod yoktu —
tam olarak madde 322/328'in "arkasında üretim olmayan kayıtlı sayı"
sınıfı. Bu dosya o üretimi geri koyuyor.

TANIM (madde 287)
    coz(g)      -> brüt k: 1 yıllık p95 düşüşü -%30 olan brüt
    net(g, k)   -> CAGR(k·g) - 0.79·k

0,79 KATSAYISI: madde 265'in ölçtüğü icra sapması, brütle ölçeklenir
(madde 273'ün notu: 1,30x'te 1,03 puan).

ÜÇ YÖNTEM, VE NEDEN ÜÇÜ BİRDEN DURUYOR
  - `KARISTIR` (tam karıştırma): madde 287'nin ORİJİNAL tanımı. Madde
    332 bunun **yolu ve kümelenmeyi yok ettiğini** gösterdi; yani ölçüt
    kuyruğu olduğundan İYİMSER görür. Kayıtlı bütün net sayıları bu
    yöntemle üretildiği için parite karşılaştırması ancak bununla
    yapılabilir — bu yüzden silinmedi.
  - `BLOK`  (blok bootstrap, blok 21): madde 262'nin kanonik yöntemi.
    Kümelenmeyi korur, dolayısıyla DOĞRU olan bu.
  - `YOL`   (gerçek seri üzerinde kayan 365 günlük pencereler): hiç
    bootstrap yok, yalnız gerçekleşen yollar. En az varsayım, en az
    örneklem.
Hangi yöntemin kullanıldığı her sonuçta YAZILIR. Bir ölçütü sessizce
değiştirmek, madde 300'ün "ölçü uyuşmazlığı" tuzağıdır.

KULLANIM
    python doz_olcutu.py referans_getiri.csv
    python doz_olcutu.py referans_getiri.csv --yontem blok

═══ BULGU: KAYITLI `net` SAYILARI YENİDEN ÜRETİLEMİYOR ═══

Bu hesaplayıcıyı tanıma göre yazdım ve kanonik seride koştum. Kayıt
`doz 1,505x / net +200,85` (madde 320) ve `1,507x / +201,69` (üretilen
seri) diyor. Hayatta kalan metindeki tanımın ÜÇ okunuşu üç ayrı sayı
veriyor:

    okunuş                                    doz      net
    p95(1y, TAM KARIŞTIRMA) = -%30          1,417x   +182,09
    TAM ÖRNEK maks düşüş = %20,70 (kısayol) 1,469x   +192,34
    p95(1y, BLOK 21) = -%30                 1,839x   +273,88
    kayıt                                   1,505x   +200,85

Hiçbiri tutmuyor. `TAM ÖRNEK maks düşüş = %21,37` hedefi 1,519x /
+202,32 veriyor — kayda 0,012 uzak. **Ama o hedefi SEÇMEDİM:** cevabı
veren hedefi aramak, ölçütü sonuca uydurmaktır ve bu projenin kendi
yasalarının yasakladığı şeydir (madde 300'ün ölçü-uyuşmazlığı, madde
276'nın "hücreyi bandın ortasından al" kuralı). %21,37 kanonik
rejim ölçümünün p1 düşüşüdür ve oradan geldiği İDDİA EDİLEBİLİR, ama
kayıtta öyle yazmıyor.

**SONUÇ — ve bu bir kâr iddiasını doğrudan etkiliyor:** kitaptaki
bütün `net` sayıları (+200,85 · +168,83 · +177,07 · +176,37 ·
+159,48 · +174,00 …) artık madde 322/328'in sınıfındadır:
**arkasında üretim olmayan kayıtlı sayı.** Karar için kullanılamazlar;
kullanılmak isteniyorsa ölçüt ÖNCE yeniden türetilmeli ve pariteyle
doğrulanmalı. Yeniden üretilebilen ölçüler bunlar: CAGR, Sharpe,
maks düşüş, ve dört şartlı kural (`karar_kurali.gecer_mi`, KOD).

Bu önemli, çünkü "kâr daha fazlaydı" hatırasının kaynağı bu birimdir:
+168,83 bir getiri yüzdesi DEĞİL, doza kaldıraçlanmış net değerdir.
Aynı kitabın 1x getirisi +%117,0'dır.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

TOLERANS_DUSUS = 30.0      # % — madde 227: kullanıcının verdiği tolerans
UFUK_GUN = 365
SAPMA_KATSAYI = 0.79       # madde 265, brütle ölçeklenir
KANONIK_TEKRAR = 20000
KANONIK_TOHUM = 11
KANONIK_BLOK = 21
YONTEMLER = ("karistir", "blok", "yol")


def _yol_dusus(yollar: np.ndarray) -> np.ndarray:
    """Her satır bir yol: (1+r) kümülatifinin tepeden en derin sapması, %."""
    k = np.cumprod(1.0 + yollar, axis=1)
    tepe = np.maximum.accumulate(k, axis=1)
    return (k / tepe - 1.0).min(axis=1) * 100.0


def _ornekle(g: np.ndarray, yontem: str, tekrar: int, tohum: int,
             blok: int = KANONIK_BLOK, ufuk: int = UFUK_GUN) -> np.ndarray:
    rng = np.random.default_rng(tohum)
    n = len(g)
    if yontem == "karistir":
        return g[rng.integers(0, n, size=(tekrar, ufuk))]
    if yontem == "blok":
        nb = int(np.ceil(ufuk / blok))
        bas = rng.integers(0, max(1, n - blok), size=(tekrar, nb))
        ofs = np.arange(blok)
        idx = (bas[:, :, None] + ofs[None, None, :]).reshape(tekrar, -1)
        return g[np.minimum(idx[:, :ufuk], n - 1)]
    if yontem == "yol":
        if n <= ufuk:
            return g[None, :]
        return np.lib.stride_tricks.sliding_window_view(g, ufuk)
    raise ValueError("yontem: %s" % (YONTEMLER,))


def p95_dusus(g: np.ndarray, k: float, yontem: str = "karistir",
              tekrar: int = KANONIK_TEKRAR, tohum: int = KANONIK_TOHUM,
              blok: int = KANONIK_BLOK) -> float:
    """k brütünde 1 yıllık düşüşün p95'i (POZİTİF puan olarak)."""
    yollar = _ornekle(np.asarray(g, dtype=float), yontem, tekrar, tohum, blok)
    return float(-np.percentile(_yol_dusus(yollar * k), 5.0))


def cagr(g: np.ndarray, k: float = 1.0) -> float:
    """k brütünde yıllıklaştırılmış bileşik getiri, % (günlük seri)."""
    g = np.asarray(g, dtype=float)
    top = np.prod(1.0 + g * k)
    if top <= 0:
        return float("-inf")          # kaldıraç seriyi sıfırın altına itti
    return (top ** (365.25 / len(g)) - 1.0) * 100.0


def coz(g, yontem: str = "karistir", hedef: float = TOLERANS_DUSUS,
        tekrar: int = KANONIK_TEKRAR, tohum: int = KANONIK_TOHUM,
        blok: int = KANONIK_BLOK, alt: float = 0.2, ust: float = 6.0,
        tur: int = 40) -> float:
    """p95 düşüşü `hedef`e eşitleyen brüt k (ikiye bölme).

    p95 düşüş k'da MONOTON artar (yol çarpanla ölçeklenir), bu yüzden
    ikiye bölme güvenli. Bir uç hedefi geçmiyorsa o uç döner — ve
    çağıran bunu sınır olarak görür, kazanç olarak değil.
    """
    g = np.asarray(g, dtype=float)
    if p95_dusus(g, ust, yontem, tekrar, tohum, blok) < hedef:
        return ust
    if p95_dusus(g, alt, yontem, tekrar, tohum, blok) > hedef:
        return alt
    for _ in range(tur):
        ort = 0.5 * (alt + ust)
        if p95_dusus(g, ort, yontem, tekrar, tohum, blok) < hedef:
            alt = ort
        else:
            ust = ort
    return 0.5 * (alt + ust)


def net(g, k: float = None, yontem: str = "karistir", **kw) -> float:
    """MADDE 287: net(x,k) = CAGR(k·x) − 0.79·k."""
    if k is None:
        k = coz(g, yontem, **kw)
    return cagr(g, k) - SAPMA_KATSAYI * k


def olc(g, yontem: str = "karistir", **kw) -> dict:
    k = coz(g, yontem, **kw)
    return {"yontem": yontem, "cagr_1x": cagr(g, 1.0), "doz": k,
            "cagr_dozda": cagr(g, k), "net": cagr(g, k) - SAPMA_KATSAYI * k,
            "p95_dusus_dozda": p95_dusus(g, k, yontem)}


def seri_oku(yol: str) -> np.ndarray:
    d = pd.read_csv(yol)
    kol = "getiri" if "getiri" in d.columns else d.columns[-1]
    return d[kol].astype(float).values


if __name__ == "__main__":
    yol = sys.argv[1] if len(sys.argv) > 1 else "referans_getiri.csv"
    yontem = "karistir"
    if "--yontem" in sys.argv:
        yontem = sys.argv[sys.argv.index("--yontem") + 1]
    g = seri_oku(yol)
    print("%s  (%d gun)" % (yol, len(g)))
    for y in ((yontem,) if "--yontem" in sys.argv else YONTEMLER):
        o = olc(g, y)
        print("  %-9s doz %.3fx  CAGR(1x) %+.2f  CAGR(doz) %+.2f  "
              "net %+.2f  p95dd -%.1f"
              % (o["yontem"], o["doz"], o["cagr_1x"], o["cagr_dozda"],
                 o["net"], o["p95_dusus_dozda"]))
