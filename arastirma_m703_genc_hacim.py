#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 703 — GENÇ COİNE AYRI HACİM EŞİĞİ. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Ön kayıt: KAR_HARITASI "Madde 703 ÖN KAYIT". Motor kopyası /tmp/g33_m703.py = g33.py + GENC_HACIM düğmesi.
  python3 arastirma_m703_genc_hacim.py kos | analiz
"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m703"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
KOLLAR = {"G50": {"GENC_HACIM": "5e7"}, "G30": {"GENC_HACIM": "3e7"}}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "# MADDE 665: KS_SOGUMA"; assert s.count(a) == 1
    s = s.replace(a, """# MADDE 703 (arastirma kopyasi): GENC_HACIM=x -> yasi 60-365 g arasi coinler x hacimle de evrene girer. 0 = parite.
_GHAC = float(os.environ.get("GENC_HACIM", "0")); _GHS = [0, 0]
if _GHAC > 0:
    import pickle as _pkgh, carry_denetim as _Dgh
    from tradfi_liste import TRADFI as _TFgh
    _Pgh = _pkgh.load(open('/tmp/panel.pkl', 'rb'))
    _ugh = _Dgh.uygunluk(_Pgh['C'], _Pgh['HAC'], _Pgh['YAS'], _Pgh['DON'], hacim=_GHAC, yas_bar=int(round(_YAS_GUN * 6)), donuk_esik=_DON)
    _ugh = _ugh & (_Pgh['YAS'] <= 365 * 6)
    _ugh = _ugh.copy(); _ugh[[c for c in _ugh.columns if c in _TFgh]] = False
    _ugh = _ugh.reindex(index=C.index, columns=C.columns).fillna(False).values
    _GHS[0] = int((_ugh & ~U).sum()); _GHS[1] = int(U.sum())
    U = U | _ugh
    print(f"# GENC_HACIM={_GHAC:.0e}: eklenen hucre {_GHS[0]} (taban {_GHS[1]})", flush=True)
""" + a, 1)
    open("/tmp/g33_m703.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out, GUNLUK_KATKI=f"{D}/gk_{ad}_{h}.pkl", GK_BAS="2019-01-01")
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m703.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    kopya()
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    for ad, ek in KOLLAR.items():
        for h in (0, 1): print(ad, h, _kos1(ad, ek, h), flush=True)


def analiz():
    import pickle
    import arastirma_m695_dayaniklilik as T, arastirma_m685_dinamik_doz as Z
    eks = [f"{ad}_{h}" for ad in ["P0", *KOLLAR] for h in (0, 1) if not os.path.exists(f"{D}/E_{ad}_{h}.pkl")]
    print(f"[KONTROL] eksik koşu: {eks or 'yok'}")
    if eks: sys.exit(1)
    for ad in KOLLAR:
        print(f"[KONTROL] {ad}: " + " | ".join(l.strip() for h in (0, 1) for l in open(f"{D}/E_{ad}_{h}.txt") if "GENC_HACIM" in l))
    P = Z.P; S = {"P3T2": P, **{ad: T.seri(ad, D).reindex(P.index) for ad in KOLLAR}}
    rows, Y, base = [], {}, None
    for ad, d in S.items():
        d = d.dropna(); o = Z.olc(d); k, er = Z.esit(d)
        s1, s2 = Z.sh(d[d.index < "2025-01-01"]), Z.sh(d[d.index >= "2025-01-01"])
        row = dict(kol=ad, ham=o["yil"], dd=o["dd"], en_kotu=o["ek"], gun_5_alti=int((d < -0.05).sum()), sh_le24=s1, sh_25=s2,
                   p1=Z.p1(d), k=k, esit_risk=er)
        if ad == "P3T2": base = row; row["karar"] = "—"
        else: row["karar"] = "ADAY" if (er >= base["esit_risk"] + 8 and s1 >= base["sh_le24"] and s2 >= base["sh_25"]) else "RED"
        rows.append(row); Y[ad] = T.yillik(d)
    R_ = pd.DataFrame(rows); R_.to_csv(f"{D}/sonuc.csv", index=False)
    print("\n[ÖLÇÜM] P3T2 ve GENC_HACIM kolları (2.000 $, 1,0x):\n" + R_.round(2).to_string(index=False))
    YD = pd.DataFrame(Y).T; print("\n  yıllık %:\n" + YD.round(1).to_string())
    print("\n  yıllık fark (kol − P3T2):\n" + (YD - YD.loc["P3T2"]).drop("P3T2").round(1).to_string())
    # eklenen coinlerin maruziyet payı ve katkısı (düşük hacim: maliyet iyimser olabilir)
    Pn = pickle.load(open("/tmp/panel.pkl", "rb")); HAC = Pn["HAC"].resample("D").last()
    for ad in KOLLAR:
        G = pd.concat([pd.read_pickle(f"{D}/gk_{ad}_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun)
        G["bw"] = G.ort_poz.abs() * G.bar / 6; G["k"] = G.fiyat + G.funding
        st = HAC.stack(); st.index.names = ["gun", "sembol"]; st.name = "hac"
        G = G.join(st, on=["gun", "sembol"]); dus = G.hac < 7e7
        print(f"  [ÖLÇÜM] {ad}: 70 M altı hacimli coinlerin brüt payı %{G.bw[dus].sum() / G.bw.sum() * 100:.1f} · katkısı "
              f"{G.k[dus].sum() / 2 * 100:+.1f} puan (maliyet hariç) · bu coinlerde ortalama 24 sa hacim {G.hac[dus].median() / 1e6:.0f} M $")
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if os.path.exists(f"{D}/sonuc.csv") else "EKSİK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
