#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 479 — EMİR DEFTERİYLE LONG SEÇİMİ (madde 477'nin risk ayarlı bulgusu).

Madde 477 eki: long'larda önceki günün defter derinliği (log ±%1 notional) EN İNCE beşte birlik risk ayarlı
getiride iki dönemde de EN İYİ (yıllıklaştırılmış gün Sharpe IS 2,23 / OOS 0,88; diğerleri OOS −0,9..−0,1).
Derinliği medyanının altına düşenler (cek) de aynı (2,60 / 1,07). Kitap long'u 16 adaylı funding havuzundan
kalabalık (ls) oranıyla seçiyor; burada sıra harmanı rank(ls) + DW·rank(defter) — yalnız long tarafı.
Veri 2023-01'den (öncesi nötr). KOLLAR: DR50/DR100 (incelik, DW 0,5/1,0) · CK50/CK100 (çekilme).
ÖN KAYIT madde 470 ile aynı (IS ≥ +8, OOS ≥ 0, eşitVol ≥ +8) — IS 2022'yi de kapsar (orada kol = taban).
"""
import os, sys, subprocess
import arastirma_m357_havuz4_adaylar as A
import arastirma_m346_prim as M
import arastirma_m470_merdiven_ince as W

A.CIKTI = "/tmp/m412"; M.CIKTI = "/tmp/m412"; A.SEVIYE = (2000,)
DEG = {"DR50": ("ls_derin", "0.5"), "DR100": ("ls_derin", "1.0"), "CK50": ("ls_cek", "0.5"), "CK100": ("ls_cek", "1.0")}
A.KOLLAR = {f"DF{a}": ({**W.T, "DW": dw, "_AD": ad}, 4, {2000: M.D8}) for a, (ad, dw) in DEG.items()}
W.A.KOLLAR = A.KOLLAR

def tek(kol, sev, h):
    ad = f"M357_{kol}_{sev}_{h}"; pkl = os.path.join(A.CIKTI, ad + ".pkl")
    if os.path.exists(pkl): return ad, "var"
    ek, bacak, evren = A.KOLLAR[kol]; ek = dict(ek); secim = ek.pop("_AD")
    env = dict(os.environ, **dict(M.TABAN, **ek), FAZ_KAY=str(h), SEMBOL_HARIC=",".join(evren[sev]), E_CIKTI=pkl)
    with open(os.path.join(A.CIKTI, ad + ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "g33.py", secim, str(bacak)], cwd=A.KOK, env=env,
                           stdout=f, stderr=subprocess.STDOUT, timeout=3000)
    return ad, f"cikis {r.returncode}"
A.tek = tek

if __name__ == "__main__":
    {"kos": A.kos, "analiz": W.analiz}[sys.argv[1]]()
