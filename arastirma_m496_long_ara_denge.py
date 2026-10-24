#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 496 — LONG TARAFININ ARA DENGELEMESİ (L_REB) ve iki tarafın birlikte (iki taban, canlı gibi giriş + 5 bp).

Madde 495: short'u sık yenilemek 2025-26'da güçlü, 2022-24'te nötr (rejim). Aynası hiç ölçülmedi: long tarafını
(pompa avı) sık yenilemek — sönmüş negatif funding'li long'u bırakıp yeni uç adaya geçmek. Long'da kâr TP/kademede
olduğundan ara dengeleme kademe durumunu korur (canlı gibi giriş: TEK_GIRIS=1).
KOLLAR (hepsi TEK_GIRIS=1, KOM 5 bp; kontrol aynı varsayımla): LR6 / LR12 · LR12SR12 (iki taraf 2 günde bir).
ÖN KAYIT madde 470 ile aynı, AYNI varsayımlı kontrolüne karşı (analiz2).
"""
import sys
import numpy as np
import arastirma_tabanlar as TB

V = {"TEK_GIRIS": "1", "KOM": "0.0005"}
TB.kur({"TGK5": V, "LR6": {**V, "L_REB": "6"}, "LR12": {**V, "L_REB": "12"},
        "LR12SR12": {**V, "L_REB": "12", "S_REB": "12"}}, onek="V")


def analiz2():
    K = TB.K
    for t in (1, 2):
        b = K.seri(f"V{t}_TGK5"); bIS, bOOS = b[b.index < "2025-01-01"], b[b.index >= "2025-01-01"]; ob = K.olc(b)
        print(f"T{t} kontrol TGK5 yıllık {ob['yil']:+7.1f} Sh {b.mean()/b.std()*np.sqrt(365.25):.2f} dd {ob['dd']:.1f} −%5 {ob['g5']}")
        for a in ("LR6", "LR12", "LR12SR12"):
            g = K.seri(f"V{t}_{a}"); o = K.olc(g); IS, OOS = g[g.index < "2025-01-01"], g[g.index >= "2025-01-01"]
            f = o["yil"] - K.YIL(b * (g.std() / b.std())); dIS = K.YIL(IS) - K.YIL(bIS); dOOS = K.YIL(OOS) - K.YIL(bOOS)
            print(f"   {a:9s} yıllık {o['yil']:+7.1f} (fark {o['yil']-ob['yil']:+6.1f}) IS {dIS:+6.1f} OOS {dOOS:+6.1f} "
                  f"Sh {g.mean()/g.std()*np.sqrt(365.25):.2f} dd {o['dd']:.1f} enkötü {o['enkotu']:.2f} −%5 {o['g5']} "
                  f"eşitVol {f:+6.1f} {'ADAY' if dIS >= 8 and dOOS >= 0 and f >= 8 else ''}")


if __name__ == "__main__":
    analiz2() if sys.argv[1] == "analiz2" else TB.calistir()
