"""CARRY ÇÜRÜTME DENETİMİ — sızıntısız motor + plasebo/bootstrap/IC altyapısı.

Bu modül `carry_genis.py`'yi DOĞRULAMAK için değil, ÇÜRÜTMEK için
yazıldı. İki iş yapar:

1. `panel_yukle_temiz()` — `carry_genis.panel_yukle()`'deki üç
   gelecek-bilgisi kaynağını kapatır (madde 134.11'de listelendi).
2. `bt2()` — aynı backtest mantığı, ama:
   - `cv[i+1]` bakmaz (delist edilecek sembolü önceden elemez)
   - sembol bazlı P&L, long/short bacak getirisi, devir hızı,
     işlem sayısı kaydeder
   - maliyet çarpanı ve rastgeleleştirme (plasebo) kancası var

ÖNEMLİ: burada parametre aranmaz. Tek bir ayar test edilir:
12+12 bacak, hacim>=100M, yaş>=90 gün, 30 bar (5 gün) rebalance.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))

# ---- SABİT AYAR (denetim boyunca DEĞİŞTİRİLMEZ) ----
N_LEGS = 12
REB = 30              # bar (5 gün)
HACIM_ESIK = 1e8
YAS_ESIK_BAR = 540    # 90 gün x 6 bar
FUNDING_PENCERE = 18  # bar (3 gün)
KOM_TEK_YON = 0.0006  # %0.04 komisyon + %0.02 kayma (tek yön)


# ------------------------------------------------------------ PANEL (TEMİZ)
def panel_yukle_temiz(fiyat_dir="data_genis", funding_dir="data_funding_genis"):
    """Gelecek bilgisi kullanmayan panel.

    KAPATILAN SIZINTILAR (carry_genis.panel_yukle'ye göre):
      S1: `len(d) < min_bar` -> sembolün TOPLAM uzunluğuna bakıyordu.
          Kısa ömürlü olacağını baştan bilmek demek. KALDIRILDI;
          yerine nedensel yaş filtresi (YAS >= 540 bar) yeterli.
      S2: donuk seri filtresi `(c.diff()==0).mean()` TÜM geçmişe
          bakıyordu - sembol 2026'daki davranışı yüzünden 2023'ten
          eleniyordu. GENİŞLEYEN (expanding) hale getirildi.
      S3: funding ödeme aralığı `median` TÜM geçmişten alınıyordu.
          GENİŞLEYEN medyana çevrildi.
    """
    cl, hc, fu = {}, {}, {}
    for yol in sorted(glob.glob(os.path.join(R, fiyat_dir, "*_4h.csv"))):
        s = os.path.basename(yol).replace("_4h.csv", "")
        fy = os.path.join(R, funding_dir, f"{s}.csv")
        if not os.path.exists(fy):
            continue
        try:
            d = pd.read_csv(yol, parse_dates=["date"]).set_index("date")
            f = pd.read_csv(fy, parse_dates=["date"])
        except Exception:
            continue
        if len(f) < 3:
            continue
        cl[s] = d["close"]
        hc[s] = d["quote_volume"]
        f["date"] = f["date"].dt.floor("h")
        fu[s] = f.drop_duplicates("date").set_index("date").sort_index()["funding"]

    C = pd.DataFrame(cl).sort_index()
    C = C[C.index.year >= int(os.environ.get("BAS_YIL", "2022"))]   # madde 497: uzun geçmiş için 2020
    kol = list(C.columns)
    ham = pd.DataFrame({s: fu[s] for s in kol}).sort_index()
    HACIM = pd.DataFrame({s: hc[s] for s in kol}).reindex(C.index).rolling(6).sum()
    YAS = C.notna().cumsum().where(C.notna())

    # S2 DÜZELTME: donukluk, sadece O ANA KADARKİ geçmişten
    var = C.notna()
    ayni = (C.diff() == 0) & var
    DONUK = ayni.cumsum() / var.cumsum().replace(0, np.nan)

    # S3 DÜZELTME: ödeme aralığı genişleyen medyan (saat).
    # Ödeme damgalarının farkları -> her sembol için o ana kadarki medyan.
    ARALIK = pd.DataFrame(index=C.index, columns=kol, dtype=float)
    for s in kol:
        t = ham[s].dropna().index
        if len(t) < 3:
            ARALIK[s] = 8.0
            continue
        dh = pd.Series(t).diff().dt.total_seconds().div(3600)
        med = dh.expanding(min_periods=2).median()
        med.index = t
        ARALIK[s] = med.reindex(ARALIK.index, method="ffill")
    ARALIK = ARALIK.where((ARALIK > 0) & np.isfinite(ARALIK), 8.0).ffill().fillna(8.0)

    # ÖDEME paneli (gerçekten ödenen), bar aralarına düşenler toplanır
    ODEME = ham.reindex(ham.index.union(C.index)).reindex(C.index).fillna(0.0)
    dis = ham.index.difference(C.index)
    if len(dis):
        kova = pd.Series(C.index.searchsorted(dis, side="right") - 1, index=dis)
        ek = ham.loc[dis].groupby(kova.values).sum()
        ek = ek[ek.index >= 0]
        if len(ek):
            ODEME.iloc[ek.index] += ek.reindex(columns=ODEME.columns).fillna(0).values
    ODEME = ODEME.where(C.notna(), 0.0)

    # SİNYAL: GÜNLÜK oran (MADDE 297 DÜZELTMESİ).
    # Burada eskiden "yıllıklaştırılmış oran" yazıyordu; kod ham oranı
    # `24/ARALIK` ile çarpıyor, yani 8 saatlik oranı 3'le çarpıp GÜNLÜĞE
    # çeviriyor - yıllığa değil (ona 365 katı gerekirdi). Strateji monoton
    # bir dönüşüme duyarsız olduğu için bu bir strateji hatası DEĞİL, ama
    # madde 297'de bir RAPOR hatasına yol açtı: USUSDT'nin funding'ini
    # +%0,09 diye yazacaktım, gerçek değer +%31,5/yıl. Yıllık istiyorsan
    # 365 ile çarp.
    SINYAL = (ham.reindex(ham.index.union(C.index)).ffill(limit=4)
              .reindex(C.index) * (24.0 / ARALIK))
    SINYAL = SINYAL.where(C.notna())
    return C, SINYAL, ODEME, HACIM, YAS, DONUK


def uygunluk(C, HACIM, YAS, DONUK, hacim=HACIM_ESIK, yas_bar=YAS_ESIK_BAR,
             donuk_esik=0.10):
    """Canlı botun da hesaplayabileceği uygunluk maskesi (nedensel)."""
    return (C.notna() & (HACIM >= hacim) & (YAS >= yas_bar)
            & (DONUK.fillna(0) < donuk_esik))


# ------------------------------------------------------------------ MOTOR
def bt2(C, ODEME, skor, uygun, n=N_LEGS, reb=REB, lag=1, bas=1200,
        kom=KOM_TEK_YON, min_bacak=8, plasebo=None, rng=None,
        sembol_pnl=False, delist_kesinti=0.0):
    """Sızıntısız backtest.

    plasebo:
      None    -> gerçek strateji
      'skor'  -> skor değerleri sembollere rastgele dağıtılır (B)
      'sec'   -> rastgele n long + n short (C)
      'yon'   -> gerçek seçim, YÖNLER rastgele (D)

    delist_kesinti: pozisyonda tutulan bir sembolün fiyatı kaybolursa
      uygulanacak zarar (0.20 = %20). Delist gerçekçiliği testi için.
    """
    rng = rng or np.random.default_rng(0)
    cv, fv = C.values, ODEME.values
    UY = uygun.values
    idx, kol = C.index, list(C.columns)
    nk = len(kol)
    poz = np.zeros(nk)
    eq, tar, bek = [1.0], [idx[bas]], None
    fk = 0.0
    kayit = {"islem": 0, "devir": 0.0, "rebalance": 0, "bacak": [],
             "long_ret": [], "short_ret": [], "funding_bar": [], "fiyat_bar": []}
    spnl = np.zeros(nk) if sembol_pnl else None
    olu = np.zeros(nk, dtype=bool)

    for i in range(bas, len(C) - 1):
        if bek is not None and bek[0] == i:
            y = bek[1]
            devir = np.abs(y - poz).sum()
            eq[-1] *= (1 - devir * kom)
            kayit["devir"] += devir
            kayit["islem"] += int((np.abs(y - poz) > 1e-12).sum())
            poz, bek = y, None
        if (i - bas) % reb == 0:
            s = skor.iloc[i]
            # SIZINTI KAPALI: cv[i+1] BAKILMIYOR
            g = s.notna().values & np.isfinite(cv[i]) & UY[i]
            m = int(g.sum())
            nn = min(n, m // 2)
            if nn >= min_bacak:
                kayit["rebalance"] += 1
                kayit["bacak"].append(nn)
                idxg = np.flatnonzero(g)
                if plasebo == "sec":
                    sec = rng.permutation(idxg)
                    L, S = sec[:nn], sec[nn:2 * nn]
                else:
                    sv = np.where(g, s.values, np.nan)
                    if plasebo == "skor":
                        sv[idxg] = rng.permutation(sv[idxg])
                    sira = np.argsort(np.where(np.isnan(sv), np.inf, sv))
                    L, S = sira[:nn], sira[m - nn:m]
                if plasebo == "yon" and rng.random() < 0.5:
                    L, S = S, L
                y = np.zeros(nk)
                y[L] = 0.5 / nn
                y[S] = -0.5 / nn
                bek = (i + lag, y)

        ham_br = (cv[i + 1] - cv[i]) / np.where(cv[i] == 0, np.nan, cv[i])
        gecerli = np.isfinite(cv[i]) & np.isfinite(cv[i + 1])
        br = np.where(gecerli, ham_br, 0.0)
        # DELIST: pozisyondayken fiyat kayboluyorsa kesinti uygula
        if delist_kesinti > 0:
            kayb = np.isfinite(cv[i]) & ~np.isfinite(cv[i + 1]) & (poz != 0) & ~olu
            if kayb.any():
                br = np.where(kayb, -delist_kesinti * np.sign(poz), br)
                olu |= kayb
        fiyat = float(np.nansum(poz * np.nan_to_num(br)))
        f = np.nan_to_num(fv[i + 1])
        fnd = float(np.nansum(-poz * f)) if f.any() else 0.0
        fk += fnd
        if sembol_pnl:
            spnl += poz * np.nan_to_num(br) - poz * f
        lm, sm = poz > 0, poz < 0
        kayit["long_ret"].append(float(np.nansum(poz[lm] * np.nan_to_num(br)[lm])))
        kayit["short_ret"].append(float(np.nansum(poz[sm] * np.nan_to_num(br)[sm])))
        kayit["funding_bar"].append(fnd)
        kayit["fiyat_bar"].append(fiyat)
        eq.append(eq[-1] * (1 + fiyat + fnd))
        tar.append(idx[i + 1])

    e = pd.Series(eq, index=tar)
    o = ozet(e)
    o.update({"funding_toplam": fk * 100, "islem": kayit["islem"],
              "rebalance": kayit["rebalance"], "devir": kayit["devir"],
              "ort_bacak": float(np.mean(kayit["bacak"])) if kayit["bacak"] else 0.0})
    kayit["egri"] = e
    if sembol_pnl:
        kayit["sembol_pnl"] = pd.Series(spnl, index=kol)
    return o, kayit


def ozet(e: pd.Series) -> dict:
    gun = max((e.index[-1] - e.index[0]).days, 1)
    son = float(e.iloc[-1])
    yl = (max(son, 1e-9) ** (365.25 / gun) - 1) * 100
    g = e.pct_change().dropna()
    sh = float(g.mean() / g.std() * np.sqrt(365.25 * 6)) if g.std() > 0 else 0.0
    dd = float(((e / e.cummax()) - 1).min() * 100)
    return {"yillik": yl, "sharpe": sh, "maxdd": dd, "son": son, "n_bar": len(g)}
