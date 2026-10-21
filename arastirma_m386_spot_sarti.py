#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 386 — SPOT ŞARTI: SPOTU OLMAYAN COİNİ CARRY'DE SHORT'LAMA.

MEKANİZMA: spot piyasası olmayan perp'te nakit-taşıma arbitrajcısı (spot al +
perp sat) yok; yüksek funding bastırılamaz, ama aynı sebepten sıkışma da
karşılanmaz. Veri: data.binance.vision spot 1d aylık kline anahtarları
(`indir_spot_varlik.py` -> data_spot_varlik.json; 850 perp'in 475'inin spotu
var). Nedensel: t anında "spot var" = bir ÖNCEKİ ayda spot kline var.

TEŞHİS (koşudan önce, panel, sk üst/alt %5, 5 gün tutma, 00 UTC):
  OOS 2025-26 yüksek-funding short adaylarının %72'si SPOTSUZ.
  short spotlu: ort +4,02% med +2,98 p1 −63 ort/sd 0,19
  short spotsuz: ort +1,81% med +7,14 p1 −154 ort/sd 0,04
  IS'te fark küçük (spotsuz n=344): 0,45 vs 0,87 ort, ort/sd 0,02 vs 0,04.
  Uyarı: teşhis OOS'u gördü — bu yüzden kanıt barı %95 ve iki dönem ayrı raporlanır.

KOLLAR (g33 SPOT_SART): SPS = spotsuz coin SHORT adayı olamaz ;
                        SPI = spotsuz coin hiç aday olamaz.
KARAR (madde 375 protokolü, koşudan ÖNCE): iki seviye (2.000 D8 / 3.500 D2) x
iki hiza, her hücrede dört şart + eşli bootstrap P >= %95. Ayrıca 22-24 ve
25-26 Sharpe farkı ikisi de >= 0 olmalı (teşhis OOS'u gördüğü için).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"SPS": ({"HAVUZ": "4", "SPOT_SART": "short"}, 4, _E),
            "SPI": ({"HAVUZ": "4", "SPOT_SART": "iki"}, 4, _E)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
