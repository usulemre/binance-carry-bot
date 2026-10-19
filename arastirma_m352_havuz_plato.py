#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 352 — MADDE 350'NİN TEK CİDDİ KOLU (HAVUZ 4) İÇİN PLATO TESTİ.

Madde 350: HAVUZ 4, 2.000 $'da iki hizada dört şart + P %92,6 / %94,3
(kaldıraçsız üstün: +7,4/+8,8 puan, düşüş 2,3/4,3 puan sığ); 3.500 $'da
hiza 0 geçti (%83,3), hiza 1 şart 1'den düştü (P %58,7). Yön monoton:
HAVUZ 2 kötü, 3 kontrol, 4 iyi.

Tek hücre karar değildir (madde 230/276): plato aranır, hücre bandın
ORTASINDAN alınır. Bu madde HAVUZ 5 ve 6'yı ekler.

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı):
  (a) Bir HAVUZ değeri bir seviyede "geçer" = iki hizada dört şart + P >= %80.
  (b) AYAR DEĞİŞİKLİĞİ yalnız: 2.000 $'da geçen değerler BİTİŞİK bir band
      oluşturur (4 dahil) VE seçilen değer 3.500 $'da en az bir hizada
      geçer ve hiçbir hizada eşit-risk farkı negatif değildir.
  (c) Seçilen değer bandın ORTASI (tek elemanlı band -> o değer, ama o
      zaman öneri "zayıf" olarak işaretlenir).
  10 kol x 2 seviye çoklu bakışı (madde 350) bu kuralda zaten fiyatlı:
  tek kol değil, BAND isteniyor.
"""
import sys

import arastirma_m350_15x4_tarama as T

T.KOLLAR = {"HAVUZ5": {"HAVUZ": "5"}, "HAVUZ6": {"HAVUZ": "6"}}

if __name__ == "__main__":
    {"kos": T.kos, "analiz": T.analiz}[sys.argv[1]]()
