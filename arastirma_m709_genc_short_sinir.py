#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 709 — GENÇ SHORT SAYI SINIRI. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ. Ön kayıt: KAR_HARITASI "Madde 709 ÖN KAYIT".
Motor kopyası /tmp/g33_m709.py = g33.py + GENC_SHORT_K düğmesi. Zemin Ekim 2026 dahil (madde 707).
  python3 arastirma_m709_genc_short_sinir.py kos | analiz
"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I
import arastirma_m708_taraf_sogumasi as B

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m709"; os.makedirs(D, exist_ok=True)
ENV = B.ENV; REF = B.REF
KOLLAR = {"K2": {"GENC_SHORT_K": "2"}, "K3": {"GENC_SHORT_K": "3"}}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    def rep(a, b):
        nonlocal s; assert s.count(a) == 1, a; s = s.replace(a, b, 1)
    a = '_YAS_S = float(os.environ.get("YAS_S_GUN", "0")); YASLI_S = None\n'
    rep(a, a + """_GSK=int(os.environ.get("GENC_SHORT_K","0")); _GSV=None; _GSS=[0]
if _GSK>0:
    import pickle as _pkgs
    _GSV=(_pkgs.load(open('/tmp/panel.pkl','rb'))['YAS'].reindex(index=C.index,columns=C.columns)<365*6).fillna(False).values
""")
    a = "            if KAYIP_HAF>0 and _KH[0] is not None:\n"
    rep(a, """            if _GSV is not None:
                # MADDE 709: short adaylari (medyan ustu) icinde genc olanlardan yalniz en yuksek sinyalli GENC_SHORT_K kalir.
                _srg=np.where(g,S[i],np.nan); _mdg=np.nanmedian(_srg) if np.isfinite(_srg).any() else 0.0
                _gs=np.flatnonzero(g&(_srg>_mdg)&_GSV[i])
                if len(_gs)>_GSK:
                    _sir=_gs[np.argsort(-_srg[_gs])]; _el=_sir[_GSK:]
                    g=g.copy(); g[_el]=False; _GSS[0]+=len(_el)
""" + a)
    a = '    if KAYIP_HAF>0: print(f"# KAYIP_HAF={KAYIP_HAF} PEN={KAYIP_PEN}: elenen aday (coin-dengeleme) {_ZES[0]}", flush=True)\n'
    rep(a, a + '    if _GSV is not None: print(f"# GENC_SHORT_K={_GSK}: elenen genc short adayi (coin-dengeleme) {_GSS[0]}", flush=True)\n')
    open("/tmp/g33_m709.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m709.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


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
    B.D = D; B.KOLLAR = KOLLAR
    import builtins
    _o = builtins.open
    B.analiz.__globals__["D"] = D; B.analiz.__globals__["KOLLAR"] = KOLLAR
    # 708'in analizi aynı ölçütle; düğme satırı GENC_SHORT_K
    import arastirma_m695_dayaniklilik as T, arastirma_m685_dinamik_doz as Z
    eks = [f"{ad}_{h}" for ad in ["P0", *KOLLAR] for h in (0, 1) if not os.path.exists(f"{D}/E_{ad}_{h}.pkl")]
    print(f"[KONTROL] eksik koşu: {eks or 'yok'}")
    if eks: sys.exit(1)
    for ad in KOLLAR:
        print(f"[KONTROL] {ad}: " + " | ".join(l.strip() for h in (0, 1) for l in open(f"{D}/E_{ad}_{h}.txt") if "GENC_SHORT_K" in l))
    tam = {ad: T.seri(ad, D) for ad in ["P0", *KOLLAR]}; P = Z.P
    rows, Y, base = [], {}, None
    for ad in ["P0", *KOLLAR]:
        d = tam[ad].reindex(P.index).dropna(); o = Z.olc(d); k, er = Z.esit(d)
        s1, s2 = Z.sh(d[d.index < "2025-01-01"]), Z.sh(d[d.index >= "2025-01-01"])
        ek = tam[ad]["2026-10"]; e = (1 + ek).cumprod()
        row = dict(kol="P3T2" if ad == "P0" else ad, ham=o["yil"], dd=o["dd"], en_kotu=o["ek"], gun_5_alti=int((d < -0.05).sum()), sh_le24=s1,
                   sh_25=s2, p1=Z.p1(d), k=k, esit_risk=er, ekim_1x=((1 + ek).prod() - 1) * 100, ekim_dd=((e / e.cummax()) - 1).min() * 100)
        if ad == "P0": base = row; row["karar"] = "—"
        else: row["karar"] = "ADAY" if (er >= base["esit_risk"] + 8 and s1 >= base["sh_le24"] and s2 >= base["sh_25"]) else "RED"
        rows.append(row); Y[row["kol"]] = T.yillik(d)
    R_ = pd.DataFrame(rows); R_.to_csv(f"{D}/sonuc.csv", index=False)
    print("\n[ÖLÇÜM] karar dönemi 2020-07 → 2026-09; Ekim 2026 yalnız bilgi:\n" + R_.round(2).to_string(index=False))
    YD = pd.DataFrame(Y).T; print("\n  yıllık fark (kol − P3T2):\n" + (YD - YD.loc["P3T2"]).drop("P3T2").round(1).to_string())
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if os.path.exists(f"{D}/sonuc.csv") else "EKSİK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
