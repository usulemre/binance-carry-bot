#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 361 — KALABALIK VERİSİ GELMEZSE BOT NE KAYBEDER? (yedek: en uç n)

Madde 358: havuzda rastgele seçim `ls`'nin −77..−91 puan altında. Canlı
bot oran API'si adayların yarısından azına cevap verirse kalabalık
seçimini KAPATIP en uç funding'li n coine düşüyor (carry_bot.py,
kalabalik=None yolu). Bu yedek HAVUZ 4 kitabında ölçülmedi.

Motor kolu `uc`: ölçüt boş -> havuzdan en uç n (botun yedeğiyle aynı
sıra). Kontrol T350_HAVUZ4_*. Karar kuralı yok: bu bir aday değil, bir
ARIZA MODUNUN FİYATI. Ölçülen fark, oran API'sinin canlıda izlenmesi
gereken önemini belirler.
"""
import sys

import arastirma_m358_kalabalik_olcut as K

K.KOLLAR = ("uc",)

if __name__ == "__main__":
    {"kos": K.kos, "analiz": K.analiz}[sys.argv[1]]()
