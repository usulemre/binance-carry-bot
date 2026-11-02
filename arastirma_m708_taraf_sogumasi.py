#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 708 — TARAF DEĞİŞİM SOĞUMASI. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ. Ön kayıt: KAR_HARITASI "Madde 708 ÖN KAYIT".
Motor kopyası /tmp/g33_m708.py = g33.py + TARAF_SOG (gün) düğmesi. Zemin: Ekim 2026 dahil (madde 707).
  python3 arastirma_m708_taraf_sogumasi.py kos | analiz
"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m708"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m_ekim/M357_EK_T7KKS_2000_{h}.pkl"      # Ekim dahil zeminde önerilen ayar (madde 707)
KOLLAR = {"N7": {"TARAF_SOG": "7"}, "N14": {"TARAF_SOG": "14"}}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    def rep(a, b):
        nonlocal s; assert s.count(a) == 1, a; s = s.replace(a, b, 1)
    a = 'KAYIP_HAF=float(os.environ.get("KAYIP_HAF","0")); KAYIP_PEN=int(os.environ.get("KAYIP_PEN","180")); _KH=[None]\n'
    rep(a, a + '_TSG=float(os.environ.get("TARAF_SOG","0")); _TSS=[0]\n')
    a = "    ek_say=np.zeros(nk,int); ilk_w=np.zeros(nk); ek24=np.zeros(nk,bool)\n"
    rep(a, a + "    _sonS=np.full(nk,-10**9); _sonL=np.full(nk,-10**9)\n")
    a = "            if KAYIP_HAF>0 and _KH[0] is not None:\n"
    rep(a, """            if _TSG>0:
                # MADDE 708: son TARAF_SOG gun icinde bu dilimde ters tarafta tutulan coin, yeni tarafin adayi olmaz.
                _srt=np.where(g,S[i],np.nan); _mdt=np.nanmedian(_srt) if np.isfinite(_srt).any() else 0.0
                _yS=(i-_sonS)<=_TSG*6; _yL=(i-_sonL)<=_TSG*6
                _el=g&((_yS&(_srt<_mdt)&~(poz<0))|(_yL&(_srt>_mdt)&~(poz>0)))
                g=g&~_el; _TSS[0]+=int(_el.sum())
""" + a)
    a = "        r=_nsum(poz*br)+_nsum(np.where(cik,0.0,-poz*FVN[i+1]))\n"
    rep(a, a + "        if _TSG>0:\n            _sonS=np.where(poz<0,i,_sonS); _sonL=np.where(poz>0,i,_sonL)\n")
    a = '    if KAYIP_HAF>0: print(f"# KAYIP_HAF={KAYIP_HAF} PEN={KAYIP_PEN}: elenen aday (coin-dengeleme) {_ZES[0]}", flush=True)\n'
    rep(a, a + '    if _TSG>0: print(f"# TARAF_SOG={_TSG}: elenen ters taraf adayi (coin-dengeleme) {_TSS[0]}", flush=True)\n')
    open("/tmp/g33_m708.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m708.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


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
        print(f"[KONTROL] {ad}: " + " | ".join(l.strip() for h in (0, 1) for l in open(f"{D}/E_{ad}_{h}.txt") if "TARAF_SOG" in l))
    tam = {ad: T.seri(ad, D) for ad in ["P0", *KOLLAR]}
    P = Z.P                                                     # 2020-07 → 2026-09 (karar dönemi; 685 / 596 ile aynı)
    rows, Y, base = [], {}, None
    for ad in ["P0", *KOLLAR]:
        d = tam[ad].reindex(P.index).dropna(); o = Z.olc(d); k, er = Z.esit(d)
        s1, s2 = Z.sh(d[d.index < "2025-01-01"]), Z.sh(d[d.index >= "2025-01-01"])
        ek = tam[ad]["2026-10"]; e = (1 + ek).cumprod()
        row = dict(kol="P3T2" if ad == "P0" else ad, ham=o["yil"], dd=o["dd"], en_kotu=o["ek"], sh_le24=s1, sh_25=s2, p1=Z.p1(d), k=k,
                   esit_risk=er, ekim_1x=((1 + ek).prod() - 1) * 100, ekim_dd=((e / e.cummax()) - 1).min() * 100)
        if ad == "P0": base = row; row["karar"] = "—"
        else: row["karar"] = "ADAY" if (er >= base["esit_risk"] + 8 and s1 >= base["sh_le24"] and s2 >= base["sh_25"]) else "RED"
        rows.append(row); Y[row["kol"]] = T.yillik(d)
    R_ = pd.DataFrame(rows); R_.to_csv(f"{D}/sonuc.csv", index=False)
    print("\n[ÖLÇÜM] karar dönemi 2020-07 → 2026-09; Ekim 2026 yalnız bilgi (karara girmez):\n" + R_.round(2).to_string(index=False))
    YD = pd.DataFrame(Y).T; print("\n  yıllık fark (kol − P3T2):\n" + (YD - YD.loc["P3T2"]).drop("P3T2").round(1).to_string())
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if os.path.exists(f"{D}/sonuc.csv") else "EKSİK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
