#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 527 — MOTOR DENETİMİ: AYNI BARDA KADEME + SON TP (uzun zemin; önce ./zemin_sec.sh uzun).

Madde 526'da tuhaflık: kademe payı 0,999 (≈ tek TP +%45/−%15) ile gerçek tek TP 0,45/0,15 arasında yıllık ~97 puan fark.
Sebep: bir barda fiyat hem kademeyi (+%45) hem son TP'yi (+%60) geçerse motor (eski kural) pozisyonun TAMAMINI +%60'tan
kapatıyor; gerçekte fiyat önce +%45'ten geçer ve bekleyen kademe limiti orada dolar. Pompa barlarında İYİMSER yanlılık —
merdivenin kendisinin (madde 463-469) ve T4'ün ölçümlerini de etkileyebilir.
KOLLAR (MERD_SIRA=1, düzeltilmiş): T1 (canlı) · M0 (merdivensiz T60) · T4 · T4P100. Eskileriyle (MERD_SIRA=0) yan yana.
"""
import sys
import arastirma_m497_uzun_gecmis as U
import arastirma_m509_t4_uzun as B
import arastirma_tabanlar as TB

S1 = {"MERD_SIRA": "1"}
M0 = U.KOL.get("U_M0") or {k: v for k, v in TB.T1.items() if k not in ("MERD_ESIK", "MERD_PAY", "MERDS_ESIK")}
U.KOL = {"U_T1": TB.T1, "U_M0": M0, "U_T3FN30": B.T4, "U_T4P100": {**B.T4, "MERD_PAY": "0.999"},
         "Q_T1": {**TB.T1, **S1}, "Q_T4": {**B.T4, **S1}, "Q_T4P100": {**B.T4, "MERD_PAY": "0.999", **S1}}
U.A.KOLLAR = {k: (v, 4, {2000: U.M.D8}) for k, v in U.KOL.items()}


def analiz():
    import arastirma_m499_sreb_durdur as D
    D.analiz()


if __name__ == "__main__":
    {"kos": U.A.kos, "analiz": analiz}[sys.argv[1]]()
