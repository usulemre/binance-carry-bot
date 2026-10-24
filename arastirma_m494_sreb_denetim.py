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

D = {}
for b in (6, 12):
    D[f"SR{b}_TG"] = {"S_REB": str(b), "TEK_GIRIS": "1"}
    D[f"SR{b}_K5"] = {"S_REB": str(b), "KOM": "0.0005"}
    D[f"SR{b}_TGK5"] = {"S_REB": str(b), "TEK_GIRIS": "1", "KOM": "0.0005"}
    D[f"SR{b}_TGK10"] = {"S_REB": str(b), "TEK_GIRIS": "1", "KOM": "0.0010"}
D["TG"] = {"TEK_GIRIS": "1"}; D["K5"] = {"KOM": "0.0005"}; D["TGK5"] = {"TEK_GIRIS": "1", "KOM": "0.0005"}
D["TGK10"] = {"TEK_GIRIS": "1", "KOM": "0.0010"}
TB.kur(D, onek="V")

if __name__ == "__main__":
    TB.calistir()
