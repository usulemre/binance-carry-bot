#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 772-773 — kullanıcı (ONE neden küçüldü sorusundan sonra): "Test yapalım en iyi saati ve kalabalık için". Yalnız araştırma.
Taban P3T2 (/tmp/m_ekim/M357_EK_T7KKS_2000_{0,1}). Motor g33.py DEĞİŞMEDEN, yalnız ortam:
  772 L48 / L72: long sinyal penceresi 48 / 72 sa (SK_DOSYA; canli_sinyal_kur.py VERI_EK=uzun TABAN=4, AD=m772_48/72). Short 96 sa kalır.
  773 KL: long tarafında kalabalık seçimi KAPALI (HAVUZ_L=1: long = funding sırasının ilk n'i; short havuzu 4 kalır).
  python3 arastirma_m772_pencere_kalabalik.py kos | analiz"""
import os, sys, subprocess
import arastirma_m346_prim as M, izleme_ekim_oos as I
OUT = "/tmp/m772"; R = os.path.dirname(os.path.abspath(__file__))
ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
KOLLAR = {"KL": {"HAVUZ_L": "1"}, "L48": {"SK_DOSYA": "/tmp/sk_m772_48.pkl"}, "L72": {"SK_DOSYA": "/tmp/sk_m772_72.pkl"}}
ADLAR = {"KL": "773 long kalabalık KAPALI", "L48": "772 long pencere 48 sa", "L72": "772 long pencere 72 sa"}


def kos():
    os.makedirs(OUT, exist_ok=True)
    for ad, ek in KOLLAR.items():
        for h in (0, 1):
            e = f"{OUT}/M357_EK_{ad}_2000_{h}.pkl"
            if os.path.exists(e): print(ad, h, "var"); continue
            env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
            with open(e.replace(".pkl", ".txt"), "w") as f:
                r = subprocess.run([sys.executable, os.path.join(R, "g33.py"), "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(e + ".tmp")
            if ok: os.replace(e + ".tmp", e)
            print(ad, h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    seri = {}
    M.CIKTI = "/tmp/m_ekim"; seri["taban P3T2 (long 60 sa, kalabalık açık)"] = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = OUT
    for a in KOLLAR:
        if all(os.path.exists(f"{OUT}/M357_EK_{a}_2000_{h}.pkl") for h in (0, 1)):
            seri[ADLAR[a]] = sum(M.gunluk(f"M357_EK_{a}_2000_{h}") for h in (0, 1)) / 2
        else:
            print(a, "EKSİK KOŞU — sayılmaz")
    for ad, s in seri.items():
        s = s[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); k, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:40s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · "
              f"Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · eşit risk {er:.1f} (doz {k:.2f}) | ×1,15 yıllar "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))


if __name__ == "__main__":
    kos() if sys.argv[1] == "kos" else analiz()
