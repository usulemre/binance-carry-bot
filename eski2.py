"""KULLANICININ ESKI BOTU: kesitsel ortalamaya donus.

Kurallar (kullanicinin tarifi):
  - En cok YUKSELENI short, en cok DUSENI long
  - Coin basina ana paranin %25'i (2 pozisyon = brut %50)
  - %25 stop
  - Gunluk yenileme, bilesik (kazanc tekrar yatirilir)

MUHAFAZAKAR varsayimlar:
  - giris SONRAKI bar kapanisinda (sizinti yok)
  - stop bar ici H/L ile; bar ACILISI stopun otesindeyse ACILISTAN dolar
  - piyasa emri: tek yon 5bp (taker), giris+cikis = 10bp
  - funding pozisyon tutuldugu barlarda odenir/alinir
  - stop olan pozisyonun koltugu ertesi gune kadar BOS
"""
import sys, os, warnings, pickle; warnings.filterwarnings('ignore')
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/home/claude/binance_bot/binance_bot')
import numpy as np, pandas as pd
from g import C, cv, fv, U, HV, LV
import carry_denetim as D
OV = pickle.load(open('/tmp/hlo.pkl','rb'))['O'].values

GERI  = int(os.environ.get("GERI","6"))     # sinyal penceresi (bar). 6 = 1 gun
TUT   = int(os.environ.get("TUT","6"))      # tutma (bar)
PAY   = float(os.environ.get("PAY","0.25")) # coin basina sermaye payi
STOP  = float(os.environ.get("STOP","0.25"))
UCRET = float(os.environ.get("UCRET","0.0005"))
N     = int(os.environ.get("N","1"))        # her taraftan kac coin
YON   = os.environ.get("YON","donus")       # donus | momentum | rast
TOHUM = int(os.environ.get("TOHUM","0"))
BAS   = int(os.environ.get("BAS","1200"))


def calis(faz=0):
    rng = np.random.default_rng(TOHUM)
    T, nk = C.shape
    poz = np.zeros(nk); giris = np.full(nk, np.nan); kalan = np.zeros(nk, int)
    eq = [1.0]; tar = [C.index[BAS]]
    say_stop = 0; say_islem = 0
    AY = {}          # yil -> [long_pnl, short_pnl, long_adet, short_adet]
    for i in range(BAS + faz, T - 1):
        # --- suresi dolan / stop olan koltuklari bosalt, yenisini sec
        kalan[poz != 0] -= 1
        bit = (poz != 0) & (kalan <= 0)
        if bit.any():
            eq[-1] *= 1 - np.abs(poz[bit]).sum() * UCRET
            poz[bit] = 0.0; giris[bit] = np.nan
        if (i - BAS - faz) % TUT == 0:
            g = U[i] & np.isfinite(cv[i]) & np.isfinite(cv[i - GERI])
            ix = np.flatnonzero(g & (poz == 0))
            if len(ix) >= 2 * N:
                r = cv[i][ix] / cv[i - GERI][ix] - 1
                o = np.argsort(r)
                if YON == "rast":
                    o = rng.permutation(len(ix))
                dus, cik = ix[o[:N]], ix[o[-N:]]
                al, sat = (dus, cik) if YON != "momentum" else (cik, dus)
                yeni = np.zeros(nk)
                yeni[al] = PAY; yeni[sat] = -PAY
                acil = (yeni != 0) & (poz == 0)
                if acil.any():
                    eq[-1] *= 1 - np.abs(yeni[acil]).sum() * UCRET
                    poz[acil] = yeni[acil]; giris[acil] = cv[i][acil]
                    kalan[acil] = TUT; say_islem += int(acil.sum())
        # --- barin getirisi, stop kontrolu
        br = np.zeros(nk); stop_oldu = np.zeros(nk, bool)
        for k in np.flatnonzero(poz != 0):
            e = giris[k]
            if not (np.isfinite(e) and e > 0 and np.isfinite(cv[i, k])):
                continue
            uzun = poz[k] > 0
            sev = e * (1 - STOP) if uzun else e * (1 + STOP)
            h, l, op = HV[i+1, k], LV[i+1, k], OV[i+1, k]
            if np.isfinite(h) and np.isfinite(l):
                vur = (l <= sev) if uzun else (h >= sev)
                if vur:
                    ff = sev
                    if np.isfinite(op):   # acilis stopun otesindeyse ACILISTAN
                        ff = min(sev, op) if uzun else max(sev, op)
                    br[k] = ff / cv[i, k] - 1
                    stop_oldu[k] = True; say_stop += 1
                    continue
            if np.isfinite(cv[i+1, k]):
                br[k] = cv[i+1, k] / cv[i, k] - 1
        fon = np.where(stop_oldu, 0.0, -poz * np.nan_to_num(fv[i+1]))
        _pl = poz * br + fon
        _y = C.index[i+1].year
        _c = AY.setdefault(_y, [0.0, 0.0, 0, 0])
        _L = poz > 0; _S = poz < 0
        _c[0] += float(np.nansum(_pl[_L])); _c[1] += float(np.nansum(_pl[_S]))
        _c[2] += int(_L.sum()); _c[3] += int(_S.sum())
        eq.append(eq[-1] * (1 + float(np.nansum(poz * br)) + float(np.nansum(fon))))
        tar.append(C.index[i+1])
        if stop_oldu.any():
            eq[-1] *= 1 - np.abs(poz[stop_oldu]).sum() * UCRET
            poz[stop_oldu] = 0.0; giris[stop_oldu] = np.nan; kalan[stop_oldu] = 0
    return pd.Series(eq, index=tar), say_stop, say_islem, AY


if __name__ == "__main__":
    gs = []; st = it = 0; TOP = {}
    for f in range(0, TUT, max(1, TUT // 3)):
        e, s, t, ay = calis(f); gs.append(e.pct_change()); st += s; it += t
        for _y, _v in ay.items():
            _t = TOP.setdefault(_y, [0.0, 0.0])
            _t[0] += _v[0]; _t[1] += _v[1]
    g = pd.concat(gs, axis=1).mean(axis=1).dropna()
    E = (1 + g).cumprod()
    out = []
    for p, m in [('tam', E.index >= '2022-01-01'), ('22-24', E.index < '2025-01-01'),
                 ('25-26', E.index >= '2025-01-01')]:
        e = E[m] / E[m].iloc[0]; o = D.ozet(e)
        out.append(f"{p} {o['yillik']:+.1f}% Sh {o['sharpe']:.2f} dd {o['maxdd']:.1f}")
    pickle.dump(E, open(f'/tmp/eskiE.pkl', 'wb'))
    _n = len(range(0, TUT, max(1, TUT // 3)))
    print("  LONG (dusen coini al) vs SHORT (cikan coini sat) - yillik puan:")
    print(f'    {"yil":<6}{"LONG":>10}{"SHORT":>10}{"TOPLAM":>10}')
    for _y in sorted(TOP):
        _l, _s2 = TOP[_y][0]/_n*100, TOP[_y][1]/_n*100
        print(f'    {_y:<6}{_l:>+10.1f}{_s2:>+10.1f}{_l+_s2:>+10.1f}')
    _tl = sum(v[0] for v in TOP.values())/_n*100
    _ts = sum(v[1] for v in TOP.values())/_n*100
    print(f'    {"TOPLAM":<6}{_tl:>+10.1f}{_ts:>+10.1f}{_tl+_ts:>+10.1f}')
    print(f"GERI{GERI} TUT{TUT} PAY{PAY} STOP{STOP} N{N} {YON:<8} stop%{st/max(1,it)*100:.0f} islem{it} | "
          + ' | '.join(out), flush=True)
