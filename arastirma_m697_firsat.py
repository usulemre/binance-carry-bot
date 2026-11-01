#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 697 — FIRSAT AZLIĞINDA SERMAYE KORUMA VE FIRSAT DÖNÜNCE YAKALAMA. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Otomatik strateji değişikliği YOK: alternatifler yalnız geçmişte ÖLÇÜLÜR. Ön kayıt: KAR_HARITASI "Madde 697 ÖN KAYIT".
Motor kopyası /tmp/g33_m690.py (madde 690: g33 + coin-gün defterinde tp / stop / komisyon ayrımı; E çıktısı bayt bayt aynı).
Dünyalar: BAZ + madde 694 kuraklık dünyaları (aynı SEMBOL_HARIC listeleri / YAS_GUN 365), bu kez ayrıntılı coin-gün defteriyle.
  python3 arastirma_m697_firsat.py kos      -> /tmp/m697/E_<dünya>_<hiza>.pkl + gk (tek işçi; ANALİZİ EŞZAMANLI ÇALIŞTIRMAYIN)
  python3 arastirma_m697_firsat.py analiz   -> /tmp/m697/*.csv + ekran raporu
"""
import os, sys, subprocess, pickle
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I, arastirma_m690_kar_kaynagi as A690, arastirma_m694_yeni_coin as A4
from tradfi_liste import TRADFI

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m697"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
DUNYA = ["Y365K", "L50_a", "L50_b", "L75_a", "L75_b", "DUR24", "DUR25"]


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out, GUNLUK_KATKI=f"{D}/gk_{ad}_{h}.pkl", GK_BAS="2019-01-01")
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m690.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    A690.kopya()
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    S, _ = A4.senaryolar()
    for ad in DUNYA:
        ek = {"YAS_GUN": "365"} if ad == "Y365K" else {"SEMBOL_HARIC": ",".join(M.D8 + S[ad])}
        for h in (0, 1):
            rc = _kos1(ad, ek, h)
            ayni = open(f"{D}/E_{ad}_{h}.pkl", "rb").read() == open(f"/tmp/m694/E_{ad}_{h}.pkl", "rb").read()
            print(ad, h, rc, "· 694 ile", "BAYT BAYT AYNI" if ayni else "FARKLI!", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
