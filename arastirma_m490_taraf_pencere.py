#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 490 — TARAF BAZLI SİNYAL PENCERESİ (yeni yapı, iki taban).

Kitap iki tarafı AYNI 60 sa funding penceresiyle sıralıyor. Taraflar farklı mekanizma: long = kalabalık short'ların
ödediği negatif funding (sıkışma/pompa), short = kalabalık long'ların pozitif funding'i (yavaş erime). Pencere
topluluğu (madde 460) iki tarafa birlikte uygulanmıştı; taraf başına ayrı pencere hiç ölçülmedi.
KOLLAR: S24/S36/S96/S144 (short penceresi, long 60) · L48/L96 (long penceresi, short 60).
ÖN KAYIT madde 470 ile aynı, her kol kendi tabanına karşı.
"""
import arastirma_tabanlar as TB

P = lambda h: f"/tmp/sk_bar{h}.pkl"
TB.kur({**{f"S{h}": {"SK_DOSYA_S": P(h)} for h in (24, 36, 96, 144)},
        **{f"L{h}": {"SK_DOSYA": P(h), "SK_DOSYA_S": P(60)} for h in (48, 96)}}, onek="P")

if __name__ == "__main__":
    TB.calistir()
