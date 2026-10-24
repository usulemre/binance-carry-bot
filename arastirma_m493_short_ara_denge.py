#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 493 — SHORT TARAFININ ARA DENGELEMESİ (S_REB, yeni yapı, iki taban).

Long kârı pompadan (TP/kademe 5 gün içinde), short kârı yavaş funding erimesinden. Short bacak 5 gün boyunca aynı
coinlerde kalıyor; funding'i sönmüş short'u erken değiştirip yeni uç funding'e geçmek short tarafını tazeler.
(Tutma 4 g / short maks 2-3 g kapatıp NAKİTTE bekliyordu — RED; burada yerine YENİ aday girer.) Long'lara dokunulmaz.
KOLLAR: SR6 / SR12 / SR18 (short her 1 / 2 / 3 günde yeniden seçilir; tam dengeleme 5 g).
ÖN KAYIT madde 470 ile aynı, her kol kendi tabanına karşı.
"""
import arastirma_tabanlar as TB

TB.kur({f"SR{b}": {"S_REB": str(b)} for b in (6, 12, 18)}, onek="D")

if __name__ == "__main__":
    TB.calistir()
