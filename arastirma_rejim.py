"""MADDE 231: FUNDING PRIMI ZAMANLA ERIYOR MU? (rejim analizi)

Bu arac, kaldirac kararindan ONCE cevaplanmasi gereken soruyu olcer:
yayinlanan +%112,5 ILERIYE DONUK bir beklenti mi, geriye donuk bir
kalinti mi? Olculen: (1) stratejinin yil/yarim-yil performansi ve trend
testi, (2) HAM funding priminin ceyreklik seyri, (3) trend mi seviye
atlamasi mi, (4) rejim bazinda bootstrap.

SONUC (2026-10): prim ERIMIYOR, 2025Q1'de SEVIYE ATLADI (3,8 kat;
Mann-Whitney p=0,0005). Strateji iki rejimde de calisiyor (Sharpe 2,79
vs 3,15); degisen olcek. Yayinlanan sayi %60 dusuk + %40 yuksek prim
harmani, yani su anki rejimden kasten dusuk.
"""
import pickle, sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/claude/binance_bot/binance_bot")
import carry_denetim as D  # noqa: E402
import karar_kurali as K  # noqa: E402


def gunluk_seri(fazlar=(0, 1), kalip=None):
    """Kontrolun gunluk serisi.

    MADDE 258 - ISLETME KUSURU DUZELTILDI. Eskiden varsayilan
    `/tmp/g19E_%d.pkl` idi, yani SON kosumun dokumu. Madde 252'de bu beni
    yanlis yonlendirdi: bu arac tam kitap yerine o turun ciplak referansini
    okuyup +%64,5 gosterdi. Artik once SABITLENMIS kontrol dokumu
    (`/tmp/kontrol_E%d.pkl`) aranir; yoksa eski yola dusulur ve UYARI verilir.
    """
    import os
    import sys as _sys
    if kalip is None:
        sabit = "/tmp/kontrol_E%d.pkl"
        if all(os.path.exists(sabit % k) for k in fazlar):
            kalip = sabit
        else:
            kalip = "/tmp/g19E_%d.pkl"
            print("UYARI: sabit kontrol dokumu yok, SON kosumun dokumu "
                  "okunuyor (%s) - sayilar tam kitaba ait olmayabilir "
                  "(madde 258)" % kalip, file=_sys.stderr)
    es = [pickle.load(open(kalip % k, "rb")).pct_change() for k in fazlar]
    r4 = pd.concat(es, axis=1).mean(axis=1).dropna()
    return (1 + r4).resample("1D").prod().dropna() - 1


def ozet(v):
    e = (1 + v).cumprod()
    return dict(gun=len(v),
                yillik=(e.iloc[-1] ** (365.25 / len(v)) - 1) * 100,
                sharpe=v.mean() / v.std(ddof=1) * np.sqrt(365.25),
                dusus=(e / e.cummax() - 1).min() * 100,
                oynaklik=v.std(ddof=1) * np.sqrt(365.25) * 100)


def yil_bootstrap(x, n=4000, blok=21, tohum=11):
    x = np.asarray(x); nn = len(x); nb = (365 + blok - 1) // blok
    rng = np.random.default_rng(tohum); gs = []; ds = []
    for _ in range(n):
        st = rng.integers(0, max(1, nn - blok), size=nb)
        ix = np.concatenate([np.arange(s, min(s + blok, nn)) for s in st])[:365]
        e = np.cumprod(1 + x[ix])
        gs.append(e[-1] - 1); ds.append(-(e / np.maximum.accumulate(e) - 1).min())
    gs = np.array(gs) * 100; ds = np.array(ds) * 100
    return dict(getiri_ort=gs.mean(), getiri_p5=np.percentile(gs, 5),
                dusus_p5=-np.percentile(ds, 95), dusus_p1=-np.percentile(ds, 99))


def permutasyon_egim(v, n=20000, tohum=5):
    """Dogrusal egim + permutasyon p (iki yonlu)."""
    v = np.asarray(v, float); t = np.arange(len(v))
    eg = np.polyfit(t, v, 1)[0]
    rng = np.random.default_rng(tohum)
    c = sum(1 for _ in range(n)
            if abs(np.polyfit(t, rng.permutation(v), 1)[0]) >= abs(eg))
    return eg, c / n


def seviye_mi_trend_mi(v, kirilma):
    """Artik kareler toplamini karsilastirir. Kucuk olan daha iyi uyar."""
    v = np.asarray(v, float); t = np.arange(len(v))
    r1 = v - np.polyval(np.polyfit(t, v, 1), t)
    A = np.c_[np.ones(len(v)), (t >= kirilma).astype(float)]
    r2 = v - A @ np.linalg.lstsq(A, v, rcond=None)[0]
    return float((r1 ** 2).sum()), float((r2 ** 2).sum())


REJIM_KIRILMA = "2025-01-01"
REJIM = {   # madde 231'de olculdu
    "tum":   dict(yillik=112.5, sharpe=2.942, getiri_p5=41.1, dusus_p1=-21.4),
    "dusuk": dict(yillik=95.0,  sharpe=2.794, getiri_p5=24.2, dusus_p1=-22.3),
    "yuksek": dict(yillik=141.0, sharpe=3.147, getiri_p5=71.6, dusus_p1=-18.0),
}

if __name__ == "__main__":
    g = gunluk_seri()
    print("REJIME GORE (kirilma %s)" % REJIM_KIRILMA)
    for ad, v in [("tum ornek", g), ("dusuk prim", g[g.index < REJIM_KIRILMA]),
                  ("yuksek prim", g[g.index >= REJIM_KIRILMA])]:
        o = ozet(v); b = yil_bootstrap(v.values)
        print("  %-13s %4d gun  %+7.1f%%  Sh %.3f  dd %.1f%%  | 1y p5 %+.1f%%  p1 %.1f%%"
              % (ad, o["gun"], o["yillik"], o["sharpe"], o["dusus"],
                 b["getiri_p5"], b["dusus_p1"]))
