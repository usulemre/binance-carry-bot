#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 771 — funding SİNYALİNDE ödeme aralığı: GÜNCEL aralık vs genişleyen medyan (motor zemini). Yalnız araştırma.
Kullanıcı: "saatlik funding'ler 8 / 4 saatliklerden daha iyi ödüyor". Motor sinyali = son ödeme × 24 / ARALIK, ARALIK = listelemeden beri
GENİŞLEYEN medyan (carry_denetim S3). 8 sa'ten 1 sa'e geçen coinin günlük oranı 8 KAT eksik sayılıyor. Kol B: ARALIK = son 9 ödeme
aralığının medyanı (nedensel, taban yok). Canlı bot: son ~73 kaydın medyanı, 4 sa taban (madde 138) — ikisinin arasında.
  python3 arastirma_m771_aralik_sinyal.py kur | kos | analiz"""
import os, sys, glob, pickle, subprocess
import numpy as np, pandas as pd
R = os.path.dirname(os.path.abspath(__file__)); OUT = "/tmp/m771"; MOTOR = f"{OUT}/g33_m771.py"


def ham_panel(C):
    fu = {}
    for s in C.columns:
        f = pd.read_csv(os.path.join(R, "data_funding_uzun", f"{s}.csv"), parse_dates=["date"])
        f["date"] = f["date"].dt.floor("h")
        fu[s] = f.drop_duplicates("date").set_index("date").sort_index()["funding"]
    return pd.DataFrame(fu).sort_index()


def aralik(ham, C, mod):
    A = pd.DataFrame(index=C.index, columns=C.columns, dtype=float)
    for s in C.columns:
        t = ham[s].dropna().index
        if len(t) < 3:
            A[s] = 8.0; continue
        dh = pd.Series(t).diff().dt.total_seconds().div(3600)
        med = dh.expanding(min_periods=2).median() if mod == "gen" else dh.rolling(9, min_periods=2).median()
        med.index = t
        A[s] = med.reindex(A.index, method="ffill")
    return A.where((A > 0) & np.isfinite(A), 8.0).ffill().fillna(8.0)


def sinyal(ham, C, A):
    import carry_denetim as D
    S = ham.reindex(ham.index.union(C.index)).ffill(limit=4).reindex(C.index) * (24.0 / A)
    return S.where(C.notna()).rolling(D.FUNDING_PENCERE, min_periods=6).mean()


def kur():
    os.makedirs(OUT, exist_ok=True)
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = Z["C"]
    ham = ham_panel(C)
    Ag, Ak = aralik(ham, C, "gen"), aralik(ham, C, "kisa")
    sk_g = sinyal(ham, C, Ag)
    fark = (sk_g - Z["sk"]).abs().where(Z["sk"].notna()).max().max()
    print(f"PARİTE: genişleyen medyanla yeniden kurulan sinyal vs zemin sk — en büyük mutlak fark {fark:.3g}")
    if not (fark < 1e-12):
        print("PARİTE TUTMADI — DUR"); sys.exit(1)
    sk_k = sinyal(ham, C, Ak)
    U = Z["uy"].fillna(False).astype(bool)
    for a, b in (("2020-01-01", "2024-12-31"), ("2025-01-01", "2026-10-31")):
        u = U.loc[a:b]; ag, ak = Ag.loc[a:b][u], Ak.loc[a:b][u]
        n = u.values.sum(); d = (ak < ag).values.sum(); y = (ak > ag).values.sum()
        print(f"{a[:4]}-{b[:4]} uygun hücre {n}: güncel aralık daha KISA %{d / n * 100:.2f} · daha UZUN %{y / n * 100:.2f}")
    Z["sk"] = sk_k
    pickle.dump(Z, open(f"{OUT}/zemin.pkl", "wb"))
    open(f"{OUT}/g.py", "w").write(open("/tmp/g.py").read().replace("/tmp/zemin.pkl", f"{OUT}/zemin.pkl"))
    m = open(os.path.join(R, "g33.py")).read()
    assert m.count("sys.path.insert(0,'/tmp')") == 1
    open(MOTOR, "w").write(m.replace("sys.path.insert(0,'/tmp')", f"sys.path.insert(0,'/tmp'); sys.path.insert(0,'{OUT}')"))
    print("zemin + motor yazıldı")


def kos():
    import arastirma_m346_prim as M, izleme_ekim_oos as I
    ENV = {**M.TABAN, **I._T7K, "SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2", "SEMBOL_HARIC": ",".join(M.D8)}
    for h in (0, 1):
        e = f"{OUT}/M357_EK_AR_2000_{h}.pkl"
        if os.path.exists(e): print(h, "var"); continue
        env = dict(os.environ, **ENV, FAZ_KAY=str(h), E_CIKTI=e + ".tmp", PYTHONPATH=R)
        with open(e.replace(".pkl", ".txt"), "w") as f:
            r = subprocess.run([sys.executable, MOTOR, "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0 and os.path.exists(e + ".tmp")
        if ok: os.replace(e + ".tmp", e)
        print(h, "rc", r.returncode, "TAMAM" if ok else "EKSİK — SAYILMAZ", flush=True)


def analiz():
    import arastirma_m346_prim as M, arastirma_m685_dinamik_doz as Z, arastirma_m695_dayaniklilik as T
    if not all(os.path.exists(f"{OUT}/M357_EK_AR_2000_{h}.pkl") for h in (0, 1)):
        print("EKSİK KOŞU — analiz yapılmaz"); return
    seri = {}
    M.CIKTI = "/tmp/m_ekim"; seri["taban (genişleyen medyan)"] = sum(M.gunluk(f"M357_EK_T7KKS_2000_{h}") for h in (0, 1)) / 2
    M.CIKTI = OUT; seri["güncel aralık (son 9 ödeme)"] = sum(M.gunluk(f"M357_EK_AR_2000_{h}") for h in (0, 1)) / 2
    for ad, s in seri.items():
        s = s[:"2026-10-31"]; o = T.olc(s); zs = s.reindex(Z.P.index).dropna(); k, er = Z.esit(zs)
        yl = s.groupby(s.index.year).apply(lambda x: ((1 + x * 1.15).prod() - 1) * 100)
        print(f"{ad:30s} yıllık {o['cagr']:.1f} · Sh {o['sharpe']:.2f} · dd {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f} · "
              f"Sh ≤2024 {Z.sh(s[:'2024-12-31']):.2f} · 2025+ {Z.sh(s['2025-01-01':]):.2f} · eşit risk {er:.1f} (doz {k:.2f}) | ×1,15 yıllar "
              + " ".join(f"{y}:{x:.0f}" for y, x in yl.items()))


if __name__ == "__main__":
    {"kur": kur, "kos": kos, "analiz": analiz}[sys.argv[1]]()
