#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 365 — KALABALIK ORANININ SÜTUNU: HESAP ORANININ KARDEŞLERİ.

Madde 358: `ls` (genel HESAP oranı) kitabın yük taşıyan seçicisi; üst
trader POZİSYON oranı (`top`) plasebo kadar kötü. Metrik panelinde hiç
ölçülmemiş iki kalabalık ölçüsü daha var:
    TTH   count_toptrader_long_short_ratio  (üst trader HESAP oranı)
    TAK   sum_taker_long_short_vol_ratio    (taker alım/satım hacmi)
    ORT   genel hesap + üst trader hesap, geometrik ortalama
Mekanizma beklentisi: `ls` HESAP sayıyor (kalabalığın kaç kişi olduğu);
üst trader HESAP oranı aynı türden, pozisyon oranı değil.

g33'e LS_KOL; boşken parite birebir (maks fark 0,0).

ÖN KAYITLI KARAR: madde 357 ile aynı (iki hiza, dört şart + P >= %80;
ayar değişikliği iki seviyede de geçerse).
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {
    "TTH": ({"HAVUZ": "4", "LS_KOL": "count_toptrader_long_short_ratio"}, 4, _E),
    "TAK": ({"HAVUZ": "4", "LS_KOL": "sum_taker_long_short_vol_ratio"}, 4, _E),
    "ORT": ({"HAVUZ": "4", "LS_KOL": "count_long_short_ratio+count_toptrader_long_short_ratio"}, 4, _E),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
