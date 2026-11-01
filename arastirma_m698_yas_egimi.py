#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 698 — YAŞ EĞİMİ (seçilen genç bacaklara daha çok ağırlık). KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ; canlıya bağlanmaz.
Ön kayıt: KAR_HARITASI "Madde 698 ÖN KAYIT". Motor kopyası /tmp/g33_m698.py = g33.py + YAS_EGIM / YAS_EGIM_GUN / YAS_EGIM_TARAF düğmeleri.
  python3 arastirma_m698_yas_egimi.py kos      (tek işçi)
  python3 arastirma_m698_yas_egimi.py analiz
"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I, arastirma_m694_yeni_coin as A4

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m698"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
KOLLAR = {"A15": {"YAS_EGIM": "1.5"}, "A20": {"YAS_EGIM": "2"}, "L20": {"YAS_EGIM": "2", "YAS_EGIM_TARAF": "long"},
          "S20": {"YAS_EGIM": "2", "YAS_EGIM_TARAF": "short"}, "A20G": {"YAS_EGIM": "2", "YAS_EGIM_GUN": "180"}}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = '_YAS_S = float(os.environ.get("YAS_S_GUN", "0")); YASLI_S = None\n'; assert s.count(a) == 1
    s = s.replace(a, a + """_YEG=float(os.environ.get("YAS_EGIM","0")); _YEGG=float(os.environ.get("YAS_EGIM_GUN","365")); _YEGT=os.environ.get("YAS_EGIM_TARAF","iki").strip(); _YEGV=None; _YEGS=[0,0]
if _YEG>0:
    import pickle as _pk3
    _PY3=_pk3.load(open('/tmp/panel.pkl','rb'))['YAS'].reindex(index=C.index,columns=C.columns)
    _YEGV=(_PY3<_YEGG*6).fillna(False).values
""", 1)
    a = '                if REZERV>0 and REZ_TARAF in ("short","iki"):\n'; assert s.count(a) == 1
    s = s.replace(a, """                if _YEGV is not None:
                    _YEGS[1]+=1
                    for _sg in ((1.0,) if _YEGT=="long" else (-1.0,) if _YEGT=="short" else (1.0,-1.0)):
                        _sd=(np.sign(y)==_sg); _gm=_sd&_YEGV[i]
                        if _gm.any() and (_sd&~_gm).any():
                            _t=y[_sd].sum(); y=np.where(_gm,y*_YEG,y); y=np.where(_sd,y*_t/y[_sd].sum(),y); _YEGS[0]+=1
""" + a, 1)
    a = "def _dol(sev,uzun,i,k):\n"
    open("/tmp/g33_m698.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m698.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


def kos():
    kopya()
    for h in (0, 1):
        rc = _kos1("P0", {}, h)
        ayni = open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read()
        print(f"parite hiza {h}: rc {rc} · {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}", flush=True)
        if not ayni: sys.exit(1)
    for ad, ek in KOLLAR.items():
        for h in (0, 1): print(ad, h, _kos1(ad, ek, h), flush=True)
    S, _ = A4.senaryolar(); exc = {"SEMBOL_HARIC": ",".join(M.D8 + S["L75_a"])}
    for ad, ek in (("L75a_A20", {**exc, **KOLLAR["A20"]}),):
        for h in (0, 1): print(ad, h, _kos1(ad, ek, h), flush=True)


def analiz():
    import arastirma_m695_dayaniklilik as T, arastirma_m685_dinamik_doz as Z
    eks = [ad for ad in ["P0", *KOLLAR, "L75a_A20"] for h in (0, 1) if not os.path.exists(f"{D}/E_{ad}_{h}.pkl")]
    print(f"[KONTROL] eksik koşu: {eks or 'yok'}")
    if eks: sys.exit(1)
    ok = all(open(f"{D}/E_P0_{h}.pkl", "rb").read() == open(REF.format(h=h), "rb").read() for h in (0, 1))
    print(f"[KONTROL] parite (düğme kapalı) iki hiza: {'bayt bayt aynı' if ok else 'FARKLI!'}")
    for ad in KOLLAR:
        fark = any(open(f"{D}/E_{ad}_{h}.pkl", "rb").read() != open(REF.format(h=h), "rb").read() for h in (0, 1))
        print(f"[KONTROL] {ad}: tabandan {'farklı (düğme etkili)' if fark else 'AYNI — düğme etkisiz!'}")
    P = Z.P
    S = {"P3T2": P}
    for ad in KOLLAR: S[ad] = T.seri(ad, D).reindex(P.index)
    rows = []; Y = {}
    base = None
    for ad, d in S.items():
        d = d.dropna(); o = Z.olc(d); k, er = Z.esit(d)
        s1, s2 = Z.sh(d[d.index < "2025-01-01"]), Z.sh(d[d.index >= "2025-01-01"])
        e = (1 + d).cumprod(); r365 = e / e.shift(365) - 1
        row = dict(kol=ad, ham=o["yil"], dd=o["dd"], en_kotu=o["ek"], gun_5_alti=int((d < -0.05).sum()), sh_le24=s1, sh_25=s2,
                   sh_tum=Z.sh(d), p1=Z.p1(d), k=k, esit_risk=er)
        if ad == "P3T2": base = row; row["karar"] = "—"
        else:
            row["karar"] = "ADAY" if (er >= base["esit_risk"] + 8 and s1 >= base["sh_le24"] and s2 >= base["sh_25"]) else "RED"
        rows.append(row); Y[ad] = T.yillik(d)
    R = pd.DataFrame(rows); R.to_csv(f"{D}/sonuc.csv", index=False)
    print("\n[ÖLÇÜM] P3T2 ve yaş eğimi kolları (2.000 $, 1,0x; eşit risk = T4 1,0x riskine k ile ölçek):")
    print(R.round(2).to_string(index=False))
    print("\n  yıllık %:\n" + pd.DataFrame(Y).T.round(1).to_string())
    YD = pd.DataFrame(Y).T; print("\n  yıllık fark (kol − P3T2, puan):\n" + (YD - YD.loc["P3T2"]).drop("P3T2").round(1).to_string())
    # kuraklık dünyası
    l0 = T.seri("L75_a", "/tmp/m694"); l1 = T.seri("L75a_A20", D)
    for ad, d in (("L75_a baz", l0), ("L75_a + A20", l1)):
        d = d[d.index >= "2021-01-01"]; o = T.olc(d)
        print(f"  [EK] {ad}: CAGR {o['cagr']:.1f} · Sharpe {o['sharpe']:.2f} · DD {o['maks_dd']:.1f} · en kötü gün {o['en_kotu_gun']:.2f}")
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if os.path.exists(f"{D}/sonuc.csv") else "EKSİK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
