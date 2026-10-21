#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 390 — ML SIKIŞMA OLASILIĞIYLA CARRY SHORT VETOSU.

Madde 389: sıra hedefi medyanı öğreniyor; para kuyruktan geçiyor. Kuyruğu
DOĞRUDAN hedefle: sınıflandırıcı (HistGradientBoosting, madde 389'un 18
özelliği), hedef = sonraki 5 günde 4 sa HIGH'ın girişin >= %30 üstüne
çıkması (short sıkışması). Yürüyen doğrulama (2023/24/25/26 yalnız önceki
veriyle eğitim). AUC: 0,656 / 0,615 / 0,709 / 0,802.
Teşhis (panel, sk üst %10 short adayı, 5 g): risk üst %20 vetosu
2023-24'te etkisiz (ort/sd −0,030 → −0,035), 2025-26'da 0,027 → 0,063,
p1 −134 → −103. Teşhis OOS'u gördü → %95 barı.

UYGULAMA: g33 MOM_Q/MOM_DOSYA veto yolu, panel V = 0,5 + 0,5 x sıra(olasılık)
(long vetosu hiç tetiklenmez; short vetosu sıra >= 1 − 2q). 00 UTC tahmini
o günün 4 sa barlarına taşınır (nedensel). 2023 öncesi tahmin yok → veto yok.
KOLLAR: q 0,05 / 0,10 / 0,15 (risk üst %10 / %20 / %30 short olamaz).
KARAR (madde 375): iki seviye x iki hiza, dört şart + eşli bootstrap P >= %95,
VE eşit-risk farkı dozla monoton.
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M

M.KANIT_BARI = 95.0
_E = {2000: M.D8, 3500: M.D2}
A.KOLLAR = {f"SQ{int(q*100):02d}": ({"HAVUZ": "4", "MOM_Q": str(q), "MOM_DOSYA": "/tmp/m390_veto_panel.pkl"}, 4, _E)
            for q in (0.05, 0.10, 0.15)}

if __name__ == "__main__":
    {"kos": A.kos, "analiz": A.analiz}[sys.argv[1]]()
