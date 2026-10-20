#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 376 — BUGÜNÜN KİTABININ BİLEŞEN ABLASYONU (her parça kapatılarak).

Kullanıcı: "yaptığımız her şeyi baştan daha doğru şekilde yeniden test et".
Madde 228'in yasası: bir bileşenin optimumda olması YÜK TAŞIDIĞI anlamına
gelmez; değeri ölçmek için onu KAPATIP bakmak gerekir. Bugünkü kitap
(15x4, HAVUZ 4, ls, 48 sa, TPL 0,40/TPS 0,20, UCELE 0,40, REZERV 0,20,
AKIS 0,20, yaş 90 gün, donuk filtre 0,10) hiç bütünüyle ablate edilmedi.

KOLLAR (motor düğmeleri koddan doğrulandı):
    TPOFF   TP=0 TPL=0 TPS=0   kâr al hasadı kapalı (madde 290'ın yöntemi)
    UCOFF   UCELE=0            uç hareket elemesi kapalı (madde 196)
    REZOFF  REZERV=0           fırsat rezervi kapalı (madde 156)
    AKISOFF AKIS=0             emir akışı payı kapalı (madde 117/228)
    YASOFF  YAS_GUN=0          listeleme yaşı filtresi kapalı (madde 133/228)
    DONOFF  DONUK_ESIK=1.0     donuk seri filtresi kapalı (madde 183)
Yeniden kullanılan (yeni koşu yok): kalabalık seçimi kapalı = madde 361
`uc`; HAVUZ 3 = madde 346 K_*.

ÖN KAYITLI KARAR (madde 375 protokolü, koşudan ÖNCE yazıldı):
  Bir bileşenin ÇIKARILMASI yalnız, kapatılmış kol kontrolü İKİ seviyede
  İKİ hizada dört şart + eşli bootstrap P >= %95 ile geçerse önerilir.
  Aksi hâlde bileşen kalır ve ölçülen DEĞERİ (kontrol − kol, eşit risk)
  kayda geçer: bir bileşen "taşıyor" sayılır, ancak kontrol kolu dört
  hücrede de P(kontrol > kol) >= %95 ile yeniyorsa; arada kalan "nötr".
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
_H = {"HAVUZ": "4"}
A.KOLLAR = {
    "TPOFF":   (dict(_H, TP="0", TPL="0", TPS="0"), 4, _E),
    "UCOFF":   (dict(_H, UCELE="0"), 4, _E),
    "REZOFF":  (dict(_H, REZERV="0"), 4, _E),
    "AKISOFF": (dict(_H, AKIS="0"), 4, _E),
    "YASOFF":  (dict(_H, YAS_GUN="0"), 4, _E),
    "DONOFF":  (dict(_H, DONUK_ESIK="1.0"), 4, _E),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
