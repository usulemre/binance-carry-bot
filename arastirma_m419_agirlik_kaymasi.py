#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 419 — MODELLEME DENETİMİ: SABİT AĞIRLIK vs GERÇEKÇİ AĞIRLIK KAYMASI.

Motor bacak ağırlığını tutuş boyunca sabit tutuyordu (her 4 sa bedava yeniden
dengeleme). Gerçek hesapta coin miktarı sabit; ağırlık fiyatla kayar. Oynak ve
ortalamaya dönen coinlerde sabit ağırlık kazancı ŞİŞİRİR (H: −%89 sonrası
toparlanma tam ağırlıkla sayılıyordu). Bu bir aday değil, ÖLÇÜM DÜZELTMESİ:
fark büyükse yayımlanmış bütün sayılar yeniden ölçülür.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {"KAYMA": ({"HAVUZ": "4", "AGIRLIK_KAYMA": "1"}, 4, _E),
            "G2PKAYMA": ({"HAVUZ": "4", "YAS_GUN": "60", "UCELE": "0", "HACIM_ESIK": "7e7", "AGIRLIK_KAYMA": "1", **M.PRIM}, 4, _E)}
if __name__ == "__main__":
    A.kos()
