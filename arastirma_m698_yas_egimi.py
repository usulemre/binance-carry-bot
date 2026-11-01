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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
