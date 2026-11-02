#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 705 — "GERÇEK YAŞ": yaş eşiği tokenin Binance spot geçmişine göre. KAYNAK KOD / STRATEJİ / PARAMETRE DEĞİŞMEZ.
Ön kayıt: KAR_HARITASI "Madde 705 ÖN KAYIT". Motor kopyası /tmp/g33_m705.py = g33.py + GERCEK_YAS (A / B) düğmesi.
  python3 arastirma_m705_gercek_yas.py kos | analiz
"""
import os, sys, subprocess
import numpy as np, pandas as pd
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m705"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
ENV = {**M.TABAN, **I._T7K, **_KS, "SEMBOL_HARIC": ",".join(M.D8)}
REF = "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl"
KOLLAR = {"A": {"GERCEK_YAS": "A"}, "B": {"GERCEK_YAS": "B"}}


def kopya():
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    a = "# MADDE 665: KS_SOGUMA"; assert s.count(a) == 1
    s = s.replace(a, """# MADDE 705 (arastirma kopyasi): GERCEK_YAS=A -> spotu perp'ten >=365 g once acilan coin 14 g perp yasindan uygun;
# GERCEK_YAS=B -> o barda spotu olmayan coin 90 g perp yasina kadar uygun degil. Bos = parite.
_GY = os.environ.get("GERCEK_YAS", "").strip(); _GYS = [0, 0]
if _GY in ("A", "B"):
    import json as _jgy, pickle as _pkgy, carry_denetim as _Dgy
    from tradfi_liste import TRADFI as _TFgy
    _Pgy = _pkgy.load(open('/tmp/panel.pkl', 'rb'))
    _spj = _jgy.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_spot_ilk_gun.json')))
    _sp = pd.Series({c: (pd.Timestamp(_spj[c]) if _spj.get(c) else pd.NaT) for c in C.columns})
    _pf = _Pgy['C'].apply(lambda x: x.first_valid_index()).reindex(C.columns)
    _YASgy = _Pgy['YAS'].reindex(index=C.index, columns=C.columns)
    if _GY == "A":
        _ok = (_sp.notna() & _pf.notna() & (_sp <= _pf - pd.Timedelta(days=365))).reindex(C.columns).fillna(False).values
        _u14 = _Dgy.uygunluk(_Pgy['C'], _Pgy['HAC'], _Pgy['YAS'], _Pgy['DON'], hacim=_HES, yas_bar=14 * 6, donuk_esik=_DON)
        _u14 = _u14.copy(); _u14[[c for c in _u14.columns if c in _TFgy]] = False
        _u14 = _u14.reindex(index=C.index, columns=C.columns).fillna(False).values & _ok[None, :]
        _GYS[0] = int((_u14 & ~U).sum()); U = U | _u14
    else:
        _spot_var = np.array([[False] * len(C.columns)] * 0)
        _spt = _sp.values.astype('datetime64[ns]'); _idx = C.index.values.astype('datetime64[ns]')
        _var = (~np.isnat(_spt))[None, :] & (_spt[None, :] <= _idx[:, None])
        _gen = (_YASgy.values < 90 * 6)
        _cik = U & ~_var & _gen
        _GYS[0] = -int(_cik.sum()); U = U & ~_cik
    _GYS[1] = int(U.sum())
    print(f"# GERCEK_YAS={_GY}: degisen hucre {_GYS[0]:+d} (yeni evren {_GYS[1]})", flush=True)
""" + a, 1)
    open("/tmp/g33_m705.py", "w", encoding="utf-8").write(s)


def _kos1(ad, ek, h):
    out = f"{D}/E_{ad}_{h}.pkl"
    if os.path.exists(out): return "var"
    env = dict(os.environ, **{**ENV, **ek}, FAZ_KAY=str(h), E_CIKTI=out, GUNLUK_KATKI=f"{D}/gk_{ad}_{h}.pkl", GK_BAS="2019-01-01")
    with open(out.replace(".pkl", ".txt"), "w") as f:
        return subprocess.run([sys.executable, "/tmp/g33_m705.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT).returncode


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
    import json
    import arastirma_m695_dayaniklilik as T, arastirma_m685_dinamik_doz as Z
    eks = [f"{ad}_{h}" for ad in ["P0", *KOLLAR] for h in (0, 1) if not os.path.exists(f"{D}/E_{ad}_{h}.pkl")]
    print(f"[KONTROL] eksik koşu: {eks or 'yok'}")
    if eks: sys.exit(1)
    for ad in KOLLAR:
        print(f"[KONTROL] {ad}: " + " | ".join(l.strip() for h in (0, 1) for l in open(f"{D}/E_{ad}_{h}.txt") if "GERCEK_YAS" in l))
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
    print("\n[ÖLÇÜM] P3T2 ve GERÇEK YAŞ kolları (2.000 $, 1,0x):\n" + R_.round(2).to_string(index=False))
    YD = pd.DataFrame(Y).T; print("\n  yıllık %:\n" + YD.round(1).to_string())
    print("\n  yıllık fark (kol − P3T2):\n" + (YD - YD.loc["P3T2"]).drop("P3T2").round(1).to_string())
    # etkilenen coinler: A'da spot-önce coinlerin 14-60 g penceresi; B'de spotsuz coinlerin 60-90 g penceresi (karar dışı tanı)
    import pickle
    Pn = pickle.load(open("/tmp/panel.pkl", "rb")); yas = (Pn["YAS"].resample("D").last() / 6).stack(); yas.index.names = ["gun", "sembol"]; yas.name = "yas"
    sp = json.load(open(os.path.join(R, "data_spot_ilk_gun.json")))
    pf = Pn["C"].apply(lambda x: x.first_valid_index())
    for ad in KOLLAR:
        G = pd.concat([pd.read_pickle(f"{D}/gk_{ad}_{h}.pkl") for h in (0, 1)]); G["gun"] = pd.to_datetime(G.gun)
        G = G.join(yas, on=["gun", "sembol"]); G["bw"] = G.ort_poz.abs() * G.bar / 6; G["k"] = G.fiyat + G.funding
        if ad == "A":
            once = {c for c, v in sp.items() if v and c in pf.index and pd.Timestamp(v) <= pf[c] - pd.Timedelta(days=365)}
            m = G.sembol.isin(once) & (G.yas < 60)
        else:
            m = G.yas.between(60, 90)
        top = G[m].groupby("sembol").k.sum().sort_values(ascending=False) / 2 * 100
        print(f"  [ÖLÇÜM] {ad}: etkilenen pencere brüt payı %{G.bw[m].sum() / G.bw.sum() * 100:.2f} · katkı {G.k[m].sum() / 2 * 100:+.1f} puan "
              f"(maliyet hariç) · coin {top.size} · en büyük 3: {', '.join(f'{s} {v:+.1f}' for s, v in top.head(3).items())}")
    print("\nÇIKTI KONTROLÜ:", "hepsi var" if os.path.exists(f"{D}/sonuc.csv") else "EKSİK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kos": kos()
    elif len(sys.argv) > 1 and sys.argv[1] == "analiz": analiz()
    else: print(__doc__)
