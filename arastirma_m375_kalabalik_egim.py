#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 375 — KALABALIK SIRASINA GÖRE AĞIRLIK EĞİMİ (ve sıkılaştırılmış arama protokolü).

ARAMA PROTOKOLÜ (madde 375'ten itibaren, kullanıcı "yine de devam" dedi):
Bu zeminde 80'e yakın aday ölçüldü; çoklu bakış riski büyük. Bundan
sonraki her aday için kanıt barı **%95** (eskiden %80), iki seviye ve iki
hiza zorunlu, ve doz-yanıt MONOTON olmalı (madde 288: monotonluk çoklu
bakışa karşı en güçlü tek savunma). Bar düşürülmez.

GEREKÇE: kalabalık oranı kitabın yük taşıyan bilgisi (madde 358: havuzda
rastgele seçim −77..−91 puan). Bot seçtiği 4 bacağa EŞİT ağırlık veriyor;
en kalabalık ile dördüncü aynı payı alıyor. Sıra konumuna göre eğim:
    w_j ~ 1 + e (n-1-2j)/(n-1)   (j=0 en kalabalık; taraf başına normalize)
g33: AGIRLIK=kalabalik, KAL_EGIM=e; e=0 parite birebir (maks fark 0,0).

KOLLAR: e = 0,3 / 0,6 / 0,9 (4 bacakta en kalabalık / en az: 1,3:0,7 ·
1,6:0,4 · 1,9:0,1).

ÖN KAYITLI KARAR: bir e, İKİ seviyede (2.000 / 3.500 $) İKİ hizada dört
şart + eşli bootstrap P >= %95 geçerse VE eşit-risk farkı e ile monoton
artıyorsa ayar önerilir. Aksi RED.
"""
import sys

import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {f"KE{int(e*10)}": ({"HAVUZ": "4", "AGIRLIK": "kalabalik", "KAL_EGIM": str(e)}, 4, _E)
            for e in (0.3, 0.6, 0.9)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
