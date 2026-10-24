#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 488 — İKİ TABANDA İLK TUR: tabanlar değişince çıkış eksenlerinin optimumu kaydı mı?

T2'de short tarafı 3 bacak + %8 tavan, long kademe payı 0,80 — son TP'ler ve short kademesi bu yapıya göre
ayarlanmamış. Her kol iki tabana da uygulanır (arastirma_tabanlar.py).
KOLLAR: TL70 (son long TP 0,70) · TS25 (son short TP 0,25) · MS12 / MS18 (short kademe −%12 / −%18) · H5 (havuz 5) ·
CI (tavan iki tarafa: long'a da %8).
ÖN KAYIT madde 470 ile aynı, her kol KENDİ tabanına karşı.
"""
import arastirma_tabanlar as TB

TB.kur({"TL70": {"TPL": "0.70"}, "TS25": {"TPS": "0.25"}, "MS12": {"MERDS_ESIK": "0.12"}, "MS18": {"MERDS_ESIK": "0.18"},
        "H5": {"HAVUZ": "5"}, "CI": {"CAP_ORTAK": "0.08", "CAP_TARAF": "iki"}}, onek="E")

if __name__ == "__main__":
    TB.calistir()
