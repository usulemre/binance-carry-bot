#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 474 — KADEME SONRASI DEVIR (MERD_DEVIR).

Dengelemede kademesi dolmuş (pompalamış) coin yeniden seçilirse motor/canlı onu TAM boya ve yeni girişe
döndürüyor — pompa tepesinde yeniden alım. KOLLAR: DV1 (tazeleme yok, kalan ⅓ eski giriş/TP ile sürer,
boşalan nakit) · DV2 (kademesi dolan coin o dengelemede aday değil, sıradaki aday girer).
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8).
"""
import sys
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"Y1": {"MERD_DEVIR": "1"}, "Y2": {"MERD_DEVIR": "2"}}
A.KOLLAR = {f"DV{a}": ({**W.T, **d}, 4, {2000: M.D8}) for a, d in DEG.items()}
W.A.KOLLAR = A.KOLLAR

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
