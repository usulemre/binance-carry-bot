#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 364 — İKİ YENİ EKSEN: TARAF BAŞINA HAVUZ VE ORANIN YUMUŞATILMASI.

Gerekçeler (projenin kendi ölçümlerinden):
  (1) Madde 358: kalabalık seçimi kitabın yük taşıyan parçası (plasebo
      −77..−91 puan). Madde 236: en iyi 250 bacağın TAMAMI long. Havuz
      iki tarafta hep AYNI genişlikteydi; taraf başına hiç denenmedi.
  (2) Madde 362: 24 saat bayat oran yalnız −5..−10 puan kaybettiriyor —
      oran YAVAŞ değişiyor. Bot 5 dakikalık ANLIK değeri kullanıyor;
      anlık değer gürültülüyse 1-2 günlük ortalama daha iyi seçici olabilir.

g33'e HAVUZ_L / HAVUZ_S ve LS_ORT eklendi; varsayılanda parite birebir
(maks fark 0,0).

KOLLAR (hepsi HAVUZ 4 tabanı, tek değişiklik):
    L6, L3   long havuzu 6 / 3 (short 4)
    S6, S3   short havuzu 6 / 3 (long 4)
    ORT6     oran 6 bar (1 gün) log-ortalaması
    ORT12    oran 12 bar (2 gün) log-ortalaması

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı): madde 357 ile aynı — bir seviyede
iki hizada dört şart + eşli bootstrap P >= %80; ayar değişikliği yalnız
iki seviyede (2.000 $, 3.500 $) de geçerse. 6 kol x 2 seviye çoklu bakış:
tek hücrede geçen bilgi, karar değil.
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {
    "L6":    ({"HAVUZ": "4", "HAVUZ_L": "6"}, 4, _E),
    "L3":    ({"HAVUZ": "4", "HAVUZ_L": "3"}, 4, _E),
    "S6":    ({"HAVUZ": "4", "HAVUZ_S": "6"}, 4, _E),
    "S3":    ({"HAVUZ": "4", "HAVUZ_S": "3"}, 4, _E),
    "ORT6":  ({"HAVUZ": "4", "LS_ORT": "6"}, 4, _E),
    "ORT12": ({"HAVUZ": "4", "LS_ORT": "12"}, 4, _E),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
