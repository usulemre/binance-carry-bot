#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 491 — KADEME GERİ ALIMI (yeni yapı: merdivenin ızgara hali, iki taban).

Merdiven pompanın tepesine yakın ⅔-%80'i satıyor; pompa-dump coini sık sık girişe geri dönüyor (madde 446 imzası).
Geri dönünce satılan payı GİRİŞ fiyatından geri al ve kademeyi yeniden kur: aynı salınımı tekrar hasat et, bu arada
funding'i tam boyda topla. Madde 250 (aleyhte bacağa ekleme kötü) ile farkı: ekleme yok — pozisyon yalnız
ORİJİNAL boyuna döner ve yalnız kâr kilitlendikten sonra. 24 sa düşüş stop'u açık kalır.
KOLLAR: G (iki taraf) · GL (yalnız long) · GS (yalnız short).
ÖN KAYIT madde 470 ile aynı, her kol kendi tabanına karşı.
"""
import arastirma_tabanlar as TB

TB.kur({"G": {"MERD_GERI": "1"}, "GL": {"MERD_GERI": "1", "MERD_GERI_TARAF": "long"},
        "GS": {"MERD_GERI": "1", "MERD_GERI_TARAF": "short"}}, onek="K")

if __name__ == "__main__":
    TB.calistir()
