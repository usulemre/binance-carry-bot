#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 688 — FUNDING İYİMSERLİĞİ (denetim ek testi 2). KAYNAK KOD DEĞİŞMEZ: g33.py okunur, /tmp/g33_m688.py olarak kopyalanıp
yalnız funding satırları değiştirilir (FUND_MOD ortam değişkeni):
  A  mevcut yöntem (parite kontrolü: g33.py ile bayt bayt aynı E dosyası beklenir)
  B  giriş anındaki ödeme çıkarılır: o bar yeni AÇILAN / BÜYÜTÜLEN kısım, bar açılışında TAM damgalı ödemeyi almaz (istenen nötr koşu;
     bar içi çıkışlara hâlâ ödeme yazılmaz -> en kötümser)
  C  zaman damgası doğru: T anındaki ödemeyi T'den ÖNCE açık olan kısım alır (bar içinde TP / stop ile çıkan dahil); yeni kısım almaz;
     bar arasına düşen (1 / 4 sa aralıklı) ödemeler bar boyunca tutulan kısma
Kullanım: python3 arastirma_m688_funding_notr.py hazirla | kos | analiz
"""
import os, re, sys, pickle, subprocess
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
import arastirma_m346_prim as M, izleme_ekim_oos as I

R = os.path.dirname(os.path.abspath(__file__)); D = "/tmp/m688"; os.makedirs(D, exist_ok=True)
_KS = {"SLL24_KAP": "1", "SLL24_PIY": "0.03", "SLL24_KAP_TAZE": "2"}
KOL = {"P3T2": {**I._T7K, **_KS}, "T4": I._T4}
REF = {"P3T2": "/tmp/m622/M357_EK_P3T2_2000_{h}.pkl", "T4": "/tmp/m_ekim_kuru/M357_EK_T4_2000_{h}.pkl"}


def hazirla():
    # (1) bar açılışında TAM damgalı funding ödemesi (g33'ün FVN'i = bu + bar arasına düşenler)
    Z = pickle.load(open("/tmp/zemin.pkl", "rb")); C = Z["C"]; ham = {}
    for s in C.columns:
        y = os.path.join(R, "data_funding_uzun", f"{s}.csv")
        if os.path.exists(y):
            f = pd.read_csv(y, parse_dates=["date"]); f["date"] = f["date"].dt.floor("h")
            ham[s] = f.drop_duplicates("date").set_index("date")["funding"]
    EX = pd.DataFrame(ham).reindex(index=C.index, columns=C.columns).fillna(0.0).where(C.notna(), 0.0)
    pickle.dump(np.nan_to_num(EX.values), open("/tmp/fv_tam.pkl", "wb"))
    fark = np.nan_to_num(Z["ODE"].values) - np.nan_to_num(EX.values)
    print(f"tam damgalı ödeme toplamı {np.abs(EX.values).sum():.3f} · bar arası ek {np.abs(fark).sum():.3f} · negatif ek hücre {(fark < -1e-12).sum()}")
    # (2) motor kopyası
    s = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
    s = s.replace("FVN=np.nan_to_num(fv)\n", "FVN=np.nan_to_num(fv)\n_FMOD=os.environ.get('FUND_MOD','A')\n"
                  "_FVEX=pickle.load(open('/tmp/fv_tam.pkl','rb')) if _FMOD!='A' else None\n_FVAR=(FVN-_FVEX) if _FMOD!='A' else None\n", 1)
    a = "    for i in range(bas,len(C)-1):\n"; assert s.count(a) == 1
    s = s.replace(a, a + "        _poz0=poz.copy()\n", 1)
    a = "        fu=np.where(cik,0.0,-poz*FVN[i+1]); pr=poz*br\n"; assert s.count(a) == 1
    s = s.replace(a, """        if _FMOD=='A':
            _FF=np.where(cik,0.0,-poz*FVN[i+1])
        else:
            _yeni=np.where(np.sign(poz)==np.sign(_poz0),np.sign(poz)*np.maximum(np.abs(poz)-np.abs(_poz0),0.0),poz)
            if _FMOD=='B':
                _FF=np.where(cik,0.0,-poz*FVN[i+1]+_yeni*_FVEX[i+1])
            else:
                _FF=-(poz-_yeni)*_FVEX[i+1]+np.where(cik,0.0,-poz*_FVAR[i+1])
        fu=_FF; pr=poz*br
""", 1)
    a = "        r=_nsum(poz*br)+_nsum(np.where(cik,0.0,-poz*FVN[i+1]))\n"; assert s.count(a) == 1
    s = s.replace(a, "        r=_nsum(poz*br)+_nsum(_FF)\n", 1)
    open("/tmp/g33_m688.py", "w", encoding="utf-8").write(s)
    print("motor kopyası: /tmp/g33_m688.py (g33.py değişmedi)")


def _kos(a):
    ad, mod, h = a; out = f"{D}/M357_EK_{ad}{mod}_2000_{h}.pkl"
    if os.path.exists(out): return a, "var"
    env = dict(os.environ, **{**M.TABAN, **KOL[ad]}, FAZ_KAY=str(h), SEMBOL_HARIC=",".join(M.D8), E_CIKTI=out, FUND_MOD=mod)
    with open(out.replace(".pkl", ".txt"), "w") as f:
        r = subprocess.run([sys.executable, "/tmp/g33_m688.py", "ls", "4"], env=env, cwd=R, stdout=f, stderr=subprocess.STDOUT)
    return a, r.returncode


def kos():
    isler = [(ad, m, h) for m in "ABC" for ad in KOL for h in (0, 1)]
    # P3T2 koşusu ~3,5 GB bellek ister; 7 GB makinede iki P3T2 aynı anda bellek yetersizliğinden öldürülüyordu (-9) -> tek tek
    with ThreadPoolExecutor(int(os.environ.get("M688_ISCI", "1"))) as ex:
        for x in ex.map(_kos, isler): print(x, flush=True)
    for ad in KOL:
        for h in (0, 1):
            ayni = open(f"{D}/M357_EK_{ad}A_2000_{h}.pkl", "rb").read() == open(REF[ad].format(h=h), "rb").read()
            print(f"parite {ad} hiza {h}: A koşusu referansla {'BAYT BAYT AYNI' if ayni else 'FARKLI!'}")


def _seri(ad, mod):
    M.CIKTI = D; return sum(M.gunluk(f"M357_EK_{ad}{mod}_2000_{h}") for h in (0, 1)) / 2


def _yil_tablo(ad, mod):
    """g33 çıktısındaki YIL YIL tablosu (iki hiza ort.): yıl -> (funding, fiyat, tp) yıllık puan, long + short toplamı."""
    out = {}
    for h in (0, 1):
        t = open(f"{D}/M357_EK_{ad}{mod}_2000_{h}.txt", encoding="utf-8", errors="replace").read()
        bl = t.split("YIL YIL LONG vs SHORT")[1].split("TUTMA GUNUNE")[0]
        for l in bl.splitlines():
            p = l.split()
            if p and p[0].isdigit() and len(p) >= 9:
                y = int(p[0]); v = list(map(float, p[1:9]))
                f, fy, tp = v[0] + v[4], v[1] + v[5], v[2] + v[6]
                o = out.setdefault(y, [0.0, 0.0, 0.0]); o[0] += f / 2; o[1] += fy / 2; o[2] += tp / 2
    return out


def _olc(d):
    e = (1 + d).cumprod(); n = len(d)
    return (e.iloc[-1] ** (365.25 / n) - 1) * 100, d.mean() / d.std() * np.sqrt(365.25), (e / e.cummax() - 1).min() * 100


def analiz():
    S = {(ad, m): _seri(ad, m) for ad in KOL for m in "ABC"}
    print("TÜM DÖNEM (2.000 $, 1,0x, iki hiza ort.)  CAGR · Sharpe · maksDD · P3T2−T4 CAGR farkı")
    for m in "ABC":
        p = _olc(S[("P3T2", m)]); t = _olc(S[("T4", m)])
        print(f"  {m}: P3T2 {p[0]:+7.1f}% · {p[1]:.2f} · {p[2]:6.1f}% | T4 {t[0]:+7.1f}% · {t[1]:.2f} · {t[2]:6.1f}% | fark {p[0]-t[0]:+6.1f}")
    print("\nYIL YIL P3T2: CAGR (A / B / C) · Sharpe (A / B / C) · funding katkısı yıllık puan (A / B / C) · fiyat+tp (A)")
    Y = {m: _yil_tablo("P3T2", m) for m in "ABC"}; YT = {m: _yil_tablo("T4", m) for m in "ABC"}
    for y in sorted(Y["A"]):
        c = []; s_ = []
        for m in "ABC":
            d = S[("P3T2", m)]; d = d[pd.to_datetime(d.index).year == y]
            if len(d) < 20: break
            o = _olc(d); c.append(o[0]); s_.append(o[1])
        if len(c) < 3: continue
        f = [Y[m][y][0] for m in "ABC"]
        tt = [_olc(S[("T4", m)][pd.to_datetime(S[("T4", m)].index).year == y])[0] for m in "ABC"]
        print(f"  {y}: CAGR {c[0]:+6.0f} / {c[1]:+6.0f} / {c[2]:+6.0f} · Sh {s_[0]:.2f} / {s_[1]:.2f} / {s_[2]:.2f} · fnd {f[0]:+6.1f} / {f[1]:+6.1f} / "
              f"{f[2]:+6.1f} · fiyat {Y['A'][y][1]:+6.1f} tp {Y['A'][y][2]:+6.1f} · T4 farkı (A / B / C) {c[0]-tt[0]:+5.0f} / {c[1]-tt[1]:+5.0f} / {c[2]-tt[2]:+5.0f}")
    fa = sum(v[0] for v in Y["A"].values()); fb = sum(v[0] for v in Y["B"].values()); fc = sum(v[0] for v in Y["C"].values())
    print(f"\nfunding katkısı toplamı (yıllık puanların toplamı): A {fa:+.1f} · B {fb:+.1f} ({fb-fa:+.1f}) · C {fc:+.1f} ({fc-fa:+.1f})")


if __name__ == "__main__":
    {"hazirla": hazirla, "kos": kos, "analiz": analiz}[sys.argv[1]]()
