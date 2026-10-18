"""PUMP SHORT: bir gunde >=ESIK yukselen coini ERTESI gun shortla (madde 195).

Kullanicinin gozlemi: "+%50 ustu gunluk yukselmis coinler bir sonraki gun
shortla kazandiriyor" (78 gunluk test).

MUHAFAZAKAR varsayimlar:
  - sinyal bar i kapanisinda okunur, giris bar i+1 KAPANISINDA (sizinti yok)
  - ucret tek yon 5bp (taker/piyasa emri), giris+cikis 10bp
  - funding pozisyon tutuldugu barlarda odenir/alinir (short'ta lehimize)
  - ayni anda coklu sinyal: sermaye bolunur, brut BRUT'u asmaz
  - uygun evren filtresi AYNEN (hacim>=100M, yas>=90g, donuk haric, TradFi haric)
"""
import sys, os, warnings, pickle; warnings.filterwarnings('ignore')
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import numpy as np, pandas as pd
from g import C, cv, fv, U
M = pickle.load(open('/tmp/metrik_panel.pkl','rb'))
_OI = M['sum_open_interest_value'].reindex(index=C.index, columns=C.columns).values
import carry_denetim as D

ESIK = float(os.environ.get("ESIK", "0.50"))   # gunluk yukselis esigi
GERI = int(os.environ.get("GERI", "6"))        # "bir gun" = 6 bar (4s)
TUT  = int(os.environ.get("TUT", "6"))         # tutma (bar)
BRUT = float(os.environ.get("BRUT", "0.50"))
MAKS = int(os.environ.get("MAKS", "4"))        # ayni anda en fazla pozisyon
YON  = os.environ.get("YON", "long")           # short | long
TARAF= os.environ.get("TARAF","dus")           # "cik"=yukselen ara, "dus"=dusen ara
UCRET= float(os.environ.get("UCRET", "0.0005"))
SAAT = os.environ.get("SAAT", "")   # "" = her bar; "0" veya "0,4,20" = sadece o UTC saatleri
_SAATLER = set(int(x) for x in SAAT.split(",")) if SAAT else set()
FILT = os.environ.get("FILT", "")              # "fnd+": sadece funding POZITIF olanlar


def calis(faz=0):
    T, nk = C.shape
    poz = np.zeros(nk); kalan = np.zeros(nk, int)
    eq = [1.0]; tar = [C.index[1200]]
    say = 0; fnd_top = 0.0; fiy_top = 0.0
    S = pickle.load(open('/tmp/panel.pkl','rb'))['sk'].values   # gunluk funding orani
    for i in range(1200 + faz, T - 1):
        kalan[poz != 0] -= 1
        bit = (poz != 0) & (kalan <= 0)
        if bit.any():
            eq[-1] *= 1 - np.abs(poz[bit]).sum() * UCRET
            poz[bit] = 0.0
        # sinyal: bar i'de son GERI barda >= ESIK yukselmis
        if SAAT != "" and C.index[i].hour not in _SAATLER:
            g = np.zeros(nk, bool)
        else:
            g = U[i] & np.isfinite(cv[i]) & np.isfinite(cv[i - GERI])
        # MADDE 201: sinyal FIYAT degil ACIK POZISYON degisimi
        _o0, _o1 = _OI[i - GERI], _OI[i]
        art = np.where(g & np.isfinite(_o0) & (_o0 > 0) & np.isfinite(_o1),
                       _o1 / np.where(_o0 > 0, _o0, np.nan) - 1, np.nan)
        if TARAF == "dus":
            ada = np.flatnonzero(np.isfinite(art) & (art <= -ESIK) & (poz == 0))
        else:
            ada = np.flatnonzero(np.isfinite(art) & (art >= ESIK) & (poz == 0))
        if FILT == "fnd+":
            ada = np.array([k for k in ada if np.isfinite(S[i, k]) and S[i, k] > 0], dtype=int)
        elif FILT == "fnd-":
            ada = np.array([k for k in ada if np.isfinite(S[i, k]) and S[i, k] < 0], dtype=int)
        if len(ada):
            ada = ada[np.argsort(art[ada] if TARAF=='dus' else -art[ada])][:MAKS]
            bos = MAKS - int((poz != 0).sum())
            ada = ada[:max(0, bos)]
            if len(ada):
                w = BRUT / MAKS
                yon = -1.0 if YON == "short" else 1.0
                eq[-1] *= 1 - w * len(ada) * UCRET
                poz[ada] = yon * w
                kalan[ada] = TUT
                say += len(ada)
        gec = np.isfinite(cv[i]) & np.isfinite(cv[i + 1])
        br = np.where(gec, (cv[i+1] - cv[i]) / np.where(cv[i] == 0, np.nan, cv[i]), 0.0)
        br = np.nan_to_num(br)
        fon = -poz * np.nan_to_num(fv[i+1])
        fnd_top += float(np.nansum(fon)); fiy_top += float(np.nansum(poz * br))
        eq.append(eq[-1] * (1 + float(np.nansum(poz * br)) + float(np.nansum(fon))))
        tar.append(C.index[i+1])
    return pd.Series(eq, index=tar), say, fnd_top, fiy_top


if __name__ == "__main__":
    gs = []; sy = 0; ft = 0.0; pt = 0.0
    _fz = [0] if SAAT != '' else list(range(0, TUT, max(1, TUT // max(1, TUT // 2))))
    for f in _fz:
        e, s, a, b = calis(f); gs.append(e.pct_change()); sy += s; ft += a; pt += b
    n = len(gs)
    g = pd.concat(gs, axis=1).mean(axis=1).dropna()
    E = (1 + g).cumprod()
    yil = (len(C) - 1200) / (6 * 365.25)
    out = []
    for p, m in [('tam', E.index >= '2022-01-01'), ('22-24', E.index < '2025-01-01'),
                 ('25-26', E.index >= '2025-01-01')]:
        ee = E[m] / E[m].iloc[0]; o = D.ozet(ee)
        out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E, open(os.environ.get('CIKTI','/tmp/dumpE.pkl'),'wb'))
    print(f"OI {TARAF}/{YON} SAAT{SAAT or 'hepsi':<5} ESIK%{ESIK*100:.0f} GERI{GERI} TUT{TUT} MAKS{MAKS} {YON:<5} {FILT:<4} "
          f"sinyal/yil {sy/n/yil:.0f} | funding {ft/n/yil*100:+.1f}p fiyat {pt/n/yil*100:+.1f}p | "
          + ' | '.join(out), flush=True)
