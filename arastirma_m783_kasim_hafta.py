#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 783 — demo haftası (7-13 Kasım 2026) backtestte nasıldı? Ön kayıt KAR_HARITASI 783. KARAR VERMEZ.
Önce: VERI_EK=uzun python3 indir_ek_gun.py 2026-11-01 2026-11-13 → yeniden_kur.py → canli_sinyal_kur (60 / 96) → metrik paneli.
  python3 arastirma_m783_kasim_hafta.py kos | analiz"""
import os, sys, subprocess, pickle
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m783"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}


def kos():
    for h in (0, 1):
        e = f"{OUT}/M357_EK_KAS_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", GUNLUK_KATKI=f"{OUT}/gk_{h}.pkl", PYTHONPATH=R)
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    M.CIKTI = "/tmp/m_ekim"; eski = [M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)]
    M.CIKTI = OUT; yeni = [M.gunluk(f"M357_EK_KAS_2000_{h}") for h in (0, 1)]
    for h in (0, 1):
        a = yeni[h].reindex(eski[h][:"2026-10-30"].index); print(f"PARİTE hiza {h}: ≤ 30 Ekim en büyük günlük fark {np.abs(a - eski[h][:'2026-10-30']).max():.2e}")
    s = (yeni[0] + yeni[1]) / 2 * 1.15 * 100
    k = s["2026-11-01":"2026-11-13"]
    print("\nGünlük getiri (%, ×1,15, iki hiza ort.; UTC gün):")
    for d, v in k.items(): print(f"  {d:%d Kas}  {v:+.2f}   (hiza 0 {yeni[0][d] * 115:+.2f} · hiza 1 {yeni[1][d] * 115:+.2f})")
    h7 = k["2026-11-07":]
    print(f"\n1-13 Kasım toplam {((1 + k / 100).prod() - 1) * 100:+.2f}% · 7-13 Kasım (tam kitap) {((1 + h7 / 100).prod() - 1) * 100:+.2f}%")
    # rampa: demo 7 Kas 00:00 UTC'de başladı, 8 sa'te bir dilim (15 dilim = 5 gün) → gün içi ortalama açık pay
    pay = [min(1.0, (3 * g + 1.5) / 15) for g in range(len(h7))]
    rp = (1 + pd.Series(h7.values * np.array(pay), index=h7.index) / 100).prod() - 1
    print("rampa payları:", [round(p, 2) for p in pay], f"→ 7-13 Kasım RAMPA AYARLI {rp * 100:+.2f}%   | demo 13 Kas UTC sonu ≈ −2,76%")
    G = pd.concat([pd.read_pickle(f"{OUT}/gk_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun)
    G = G[(G.gun >= "2026-11-07") & (G.gun <= "2026-11-13")]; G["net"] = (G.fiyat + G.funding) / 2 * 115
    G["yon"] = np.where(G.ort_poz > 0, "long", "short")
    t = G.groupby("yon")[["net"]].sum(); f = G.groupby("yon").apply(lambda x: pd.Series({"fiyat": x.fiyat.sum() / 2 * 115, "funding": x.funding.sum() / 2 * 115}))
    print("\n7-13 Kasım katkı (% kitap, ×1,15):"); print(pd.concat([t, f], axis=1).round(2).to_string())
    c = G.groupby(["sembol", "yon"]).net.sum().sort_values()
    print("en kötü 8:", c.head(8).round(2).to_dict()); print("en iyi 6:", c.tail(6).round(2).to_dict())
    for sym in ("AKEUSDT", "INITUSDT", "ONEUSDT", "CYBERUSDT", "ZECUSDT", "ICNTUSDT"):
        x = G[G.sembol == sym]
        if len(x): print(" ", sym, x.groupby(["gun", "yon"]).net.sum().round(2).to_dict())
        else: print(" ", sym, "backtestte TUTULMADI")


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
