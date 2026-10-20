#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 383 — ÇOK UFUKLU MOMENTUM VETOSU (carry seçiminde).

Madde 381 (örnek dışında doğrulandı): kriptoda kesitsel olarak yükselen
coin yükselmeye, düşen düşmeye devam ediyor (1 gün..3 ay; OOS Sharpe
1,27). Carry botu funding'e göre seçtiği için bazen tam bu coinlere TERS
pozisyon alıyor olabilir. Momentum ayrı kitap olarak eklenmedi (madde
382); burada FİLTRE olarak: beş ufkun (1/3/7/30/90 gün) ortalama sırası
üst MOM_Q dilimindeyse SHORT adayı, alt dilimindeyse LONG adayı olamaz.
Mevcut UCELE (madde 196) TERS mantıkla çalışıyor (pump long adayı olamaz)
ve bu kitapta nötr çıktı (madde 376) → bir kol UCELE kapalıyken.

g33: MOM_Q, MOM_DOSYA (/tmp/mom5_panel.pkl); MOM_Q=0 parite birebir.

KOLLAR: MQ10, MQ20, MQ30 (UCELE 0,40 ile) · MQ20_UC0 (UCELE kapalı).
ÖN KAYITLI KARAR (madde 375): iki seviye, iki hiza, dört şart + P >= %95,
ve MQ10 -> MQ20 -> MQ30 eşit-risk farkında monoton (en az ilk adım).
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {
    "MQ10": ({"HAVUZ": "4", "MOM_Q": "0.10"}, 4, _E),
    "MQ20": ({"HAVUZ": "4", "MOM_Q": "0.20"}, 4, _E),
    "MQ30": ({"HAVUZ": "4", "MOM_Q": "0.30"}, 4, _E),
    "MQ20_UC0": ({"HAVUZ": "4", "MOM_Q": "0.20", "UCELE": "0"}, 4, _E),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
