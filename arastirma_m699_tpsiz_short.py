#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 699 — TP'SİZ UZUN SHORT'U KES (STP_GUN). KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Ön kayıt: KAR_HARITASI "Madde 699 ÖN KAYIT". Motor kopyası /tmp/g33_m699.py = g33.py + STP_GUN / STP_SOGUMA düğmeleri.
  python3 arastirma_m699_tpsiz_short.py kos | analiz
"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m699"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
KOLLAR = {"D7": {"STP_GUN": "7"}, "D10": {"STP_GUN": "10"}, "D14": {"STP_GUN": "14"}}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    def rep(a, b):
        nonlocal s; assert s.count(a) == 1, a; s = s.replace(a, b, 1)
    a = 'KAYIP_HAF=float(os.environ.get("KAYIP_HAF","0")); KAYIP_PEN=int(os.environ.get("KAYIP_PEN","180")); _KH=[None]\n'
    rep(a, a + '_STG=float(os.environ.get("STP_GUN","0")); _STSG=int(os.environ.get("STP_SOGUMA","30")); _STS=[0]\n')
    a = "    ek_say=np.zeros(nk,int); ilk_w=np.zeros(nk); ek24=np.zeros(nk,bool)\n"
    rep(a, a + "    _stb=np.zeros(nk); _stx=np.full(nk,-1)\n")
    a = "                _kb=_kh<=-KAYIP_HAF; g=g&~_kb; _ZES[0]+=int(_kb.sum())\n"
    rep(a, a + """            if _STG>0:
                _sx=(_stb>=_STG*6)&(poz<0); _stx=np.where(_sx,i+_STSG,_stx); _sb=_sx|(i<_stx); g=g&~_sb; _STS[0]+=int(_sx.sum())
""")
    a = "        r=_nsum(poz*br)+_nsum(np.where(cik,0.0,-poz*FVN[i+1]))\n"
    rep(a, a + "        if _STG>0:\n            _stb=np.where(poz<0,_stb+1,0.0); _stb=np.where(cik|merd,0.0,_stb)\n")
    a = '    if KAYIP_HAF>0: print(f"# KAYIP_HAF={KAYIP_HAF} PEN={KAYIP_PEN}: elenen aday (coin-dengeleme) {_ZES[0]}", flush=True)\n'
    rep(a, a + '    if _STG>0: print(f"# STP_GUN={_STG}: kesilen TPsiz uzun short (coin-dengeleme) {_STS[0]}", flush=True)\n')
    open("/tmp/g33_m699.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m699.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


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
    import arastirma_m695_dayaniklilik as T, arastirma_m685_dinamik_doz as Z
    eks = [f"{ad}_{h}" for ad in ["P0", *KOLLAR] for h in (0, 1) if not os.path.exists(f"{D}/E_{ad}_{h}.pkl")]
    print(f"[KONTROL] eksik koşu: {eks or 'yok'}")
    if eks: sys.exit(1)
    for ad in KOLLAR:
        say = [l.strip() for h in (0, 1) for l in open(f"{D}/E_{ad}_{h}.txt") if "STP_GUN" in l]
        print(f"[KONTROL] {ad}: {' | '.join(say)}")
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
    print("\n[ÖLÇÜM] P3T2 ve STP_GUN kolları (2.000 $, 1,0x):\n" + R_.round(2).to_string(index=False))
    YD = pd.DataFrame(Y).T; print("\n  yıllık %:\n" + YD.round(1).to_string())
    print("\n  yıllık fark (kol − P3T2):\n" + (YD - YD.loc["P3T2"]).drop("P3T2").round(1).to_string())
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if os.path.exists(f"{D}/sonuc.csv") else "EKSİK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
