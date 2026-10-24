#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 494 — S_REB GERÇEKÇİLİK DENETİMİ (iki taban).

Madde 493'ün sıçraması (T1 +100 puan/yıl, eşitVol +59) şu iki modelleme varsayımına dayanıyor olabilir:
 (a) devam eden short'un girişi ara dengelemede sıfırlanıyor (TP/kademe yeniden kuruluyor) — canlı entryPrice'ı
     sıfırlamaz → TEK_GIRIS=1 (hesap düzeyi ağırlıklı ortalama giriş, canlı gibi);
 (b) devir maliyeti 2 bp (maker) — artan devirde kayma/taker → KOM 5 bp ve 10 bp.
Ayrıca DEVAM eden coinin dokunulmadığı varyant: ara dengelemede yeniden seçilen short'un girişi KORUNUR (SRK: yalnız
çıkan/giren değişir) — bu, motorun canlıya en yakın hali.
ÖN KAYIT: kolun kazancı (a)+(b) altında da eşitVol ≥ +8 ve IS ≥ +8 kalırsa → protokol; değilse model kalıntısı.
"""
import arastirma_tabanlar as TB

D = {"TG": {"TEK_GIRIS": "1"}, "TGK5": {"TEK_GIRIS": "1", "KOM": "0.0005"}}
for b in (6, 12):
    D[f"SR{b}_TG"] = {"S_REB": str(b), "TEK_GIRIS": "1"}
    D[f"SR{b}_TGK5"] = {"S_REB": str(b), "TEK_GIRIS": "1", "KOM": "0.0005"}
TB.kur(D, onek="V")

def analiz2():
    """Her S_REB kolunu AYNI maliyet/giriş varsayımındaki kontrolüne karşı ölçer."""
    import numpy as np
    K = TB.K
    for t in (1, 2):
        for kk in ("TG", "TGK5"):
            b = K.seri(f"V{t}_{kk}"); bIS, bOOS = b[b.index < "2025-01-01"], b[b.index >= "2025-01-01"]
            ob = K.olc(b)
            print(f"T{t} kontrol {kk:5s} yıllık {ob['yil']:+7.1f} Sh {b.mean()/b.std()*np.sqrt(365.25):.2f} dd {ob['dd']:.1f} −%5 {ob['g5']}")
            for sr in (6, 12):
                g = K.seri(f"V{t}_SR{sr}_{kk}"); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
                f = o["yil"] - K.YIL(b * (g.std() / b.std()))
                print(f"   SR{sr:<2d} yıllık {o['yil']:+7.1f} (fark {o['yil']-ob['yil']:+6.1f}) IS {K.YIL(IS)-K.YIL(bIS):+6.1f} "
                      f"OOS {K.YIL(OOS)-K.YIL(bOOS):+6.1f} Sh {g.mean()/g.std()*np.sqrt(365.25):.2f} dd {o['dd']:.1f} "
                      f"enkötü {o['enkotu']:.2f} −%5 {o['g5']} eşitVol {f:+6.1f}")

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "analiz2": analiz2()
    else: TB.calistir()
