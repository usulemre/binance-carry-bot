#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 373 — EVREN KANALINI KALDIRAÇSIZ AÇMAK: DAHA AZ DİLİM, DAHA BÜYÜK BACAK.

Madde 369: kaldıracın getirisinin bir kısmı EVRENDEN geliyor (bacak
>= 20 $ -> ETH/BCH/LTC/ETC/LINK/AAVE geri gelir). Bacak = bakiye x 0,4 /
(dilim x bacak); 2.000 $'da 15x4 = 13,33 $ (D8). Dilim azaltınca:
    10x4 -> 20,00 $ (D2, eşikte)   9x4 -> 22,22 $ (D2, eşiğin üstünde)
Bedeli faz çeşitlendirmesi (madde 120/184/325). Madde 326'nın iki-kanal
yasası gereği kanallar AYRI ölçülür:
    F10_D8   10 dilim, evren D8   -> yalnız FAZ BEDELİ
    F10_D2   10 dilim, evren D2   -> faz bedeli + evren kazancı
    F9_D2    9 dilim (eşit aralıklı liste), evren D2
Canlı kurulum: CARRY_N_DILIM=10 ya da 9 (bacak tavanı 4 aynı kalır).

ÖN KAYITLI KARAR (koşudan ÖNCE yazıldı): yalnız 2.000 $ seviyesi
anlamlı (3.500 $'da 15x4 zaten D2). F10_D2 ya da F9_D2 iki hizada dört
şart + P >= %80 geçerse "2.000-3.000 $ için CARRY_N_DILIM önerisi"
olarak kaydedilir (varsayılan değişmez: 3.000 $ üstünde 15 dilim D2'ye
zaten ulaşıyor). F10_D8 karar kolu değil, bedel ölçümü.
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

A.SEVIYE = (2000,)
A.KOLLAR = {
    "F10_D8": ({"HAVUZ": "4", "FAZ": "10"}, 4, {2000: M.D8}),
    "F10_D2": ({"HAVUZ": "4", "FAZ": "10"}, 4, {2000: M.D2}),
    "F9_D2":  ({"HAVUZ": "4", "FAZ": "9", "FAZ_LISTE": "0,3,7,10,13,17,20,23,27"}, 4, {2000: M.D2}),
}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
