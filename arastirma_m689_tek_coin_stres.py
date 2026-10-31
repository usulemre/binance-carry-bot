#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 689 — TEK COIN KUYRUK RİSKİ (denetim ek testi 1). Kaynak kod değişmez; yalnız okur.
Girdi: gerçek portföy defteri /tmp/m621/pozKS_{0,1}.pkl (önerilen ayarın T7K + koşullu stop koşusu, 1,0x; özkaynak payı olarak ağırlık),
fiyat paneli /tmp/panel.pkl. Önerilen doz 1,15x: ağırlıklar × 1,15. Bakiye 2.000 $.
Kullanım: python3 arastirma_m689_tek_coin_stres.py      (çıktı: /tmp/m689/*.csv + ekrana tablo)
VARSAYIMLAR (veriyle kanıtlanamayan): bakım teminatı oranı (MMR) altcoinler %2,5, çöken coin %5 (Binance küçük notional kademeleri
~%1-5); çapraz teminat; tasfiye = özkaynak ≤ Σ|notional| × MMR. Senaryo şokları ANLIK (gün içi toparlanma yok).
"""
import os, pickle
import numpy as np, pandas as pd

DOZ = 1.15; BAKIYE = 2000.0; MMR = 0.025; MMR_COIN = 0.05; ESIK_STOP = 0.45
O = "/tmp/m689"; os.makedirs(O, exist_ok=True)

P = pd.concat([pd.read_pickle(f"/tmp/m621/pozKS_{h}.pkl").assign(hiza=h) for h in (0, 1)])
P["w"] *= DOZ
C = pickle.load(open("/tmp/panel.pkl", "rb"))["C"]
U = pickle.load(open("/tmp/zemin.pkl", "rb"))["uy"]

# ---------------------------------------------------------------- 1) gerçek portföy durumları: en büyük long payı
g = P.groupby(["hiza", "zaman"])
durum = pd.DataFrame({"long": g.w.apply(lambda x: x[x > 0].sum()), "short": g.w.apply(lambda x: -x[x < 0].sum()),
                      "maxlong": g.w.max(), "n": g.size()})
durum["brut"] = durum.long + durum.short
durum["sembol"] = g.apply(lambda x: x.loc[x.w.idxmax(), "sembol"])
durum.to_csv(f"{O}/durumlar.csv")
sec = durum.sort_values("maxlong", ascending=False).drop_duplicates("sembol").head(5)
med = durum.iloc[(durum.maxlong - durum.maxlong.median()).abs().argsort()[:1]]
p99 = durum.iloc[(durum.maxlong - durum.maxlong.quantile(0.99)).abs().argsort()[:1]]
secilen = pd.concat([sec.assign(etiket="en büyük"), p99.assign(etiket="%99 dilim"), med.assign(etiket="medyan")])

# ---------------------------------------------------------------- 2) GERÇEKLEŞMİŞ olaylar: tutulan long'ların 24 sa ileri getirisi
c4 = C.reindex(P.zaman.unique()).index
fw = (C.shift(-6) / C - 1)               # 24 sa ileri getiri (bar kapanışından)
med_piy = (C.pct_change(6, fill_method=None).where(U)).median(axis=1).shift(-6)   # evren medyan 24 sa (aynı pencere)
L = P[P.w > 0].copy()
L["r24"] = fw.stack().reindex(pd.MultiIndex.from_arrays([L.zaman, L.sembol])).values
L["piyasa24"] = med_piy.reindex(L.zaman).values
L["etki_sabit"] = L.w * L.r24            # ağırlık 24 sa SABİT tutulsaydı (kademe / TP / stop yok sayılır)
L = L.dropna(subset=["r24"])
# GERÇEKLEŞEN etki: defterdeki gerçek ağırlıklarla bar bar (w_t × 4 sa getiri), sonraki 6 barın toplamı; kademe / TP / stop sonrası
# küçülen pozisyonu yansıtır (bar içi çıkış fiyatı yerine bar kapanışı -> yaklaşık)
r4 = (C.shift(-1) / C - 1)
P["r4"] = r4.stack().reindex(pd.MultiIndex.from_arrays([P.zaman, P.sembol])).values
P["pnl"] = P.w * P.r4
pn = P.pivot_table(index=["hiza", "zaman"], columns="sembol", values="pnl", aggfunc="sum").fillna(0.0)
gercek = []
for h in (0, 1):
    x = pn.loc[h].rolling(6).sum().shift(-5)          # t'den başlayan 24 sa
    st = x.stack(); st = st[st < -0.04]
    for (z, s_), v in st.items():
        gercek.append((h, z, s_, v))
G = pd.DataFrame(gercek, columns=["hiza", "zaman", "sembol", "etki_gercek"]).sort_values("etki_gercek")
G = G.drop_duplicates(["sembol"]).head(15); G.to_csv(f"{O}/gercek_en_kotu_coin_24s.csv", index=False)
L.nsmallest(30, "etki_sabit").to_csv(f"{O}/sabit_agirlik_en_kotu_long_24s.csv", index=False)
cokus = L[L.r24 <= -0.5]


def senaryo(st, coin_dus, diger_L=0.0, diger_S=0.0, stop=False, kayma=0.0, ikinci=0.0):
    """st: durum satırı (hiza, zaman). Dönen: özkaynak kaybı %, brüt önce / sonra, bakım teminatı / özkaynak, tasfiye, gün sonu $, toparlanma %."""
    h, z = st.name
    pz = P[(P.hiza == h) & (P.zaman == z)].set_index("sembol").w
    top = pz.idxmax(); w0 = pz[top]
    dus = coin_dus
    if stop and coin_dus <= -ESIK_STOP:          # koşullu stop çalışırsa eşikte (+ kayma) kapanır
        dus = -(ESIK_STOP + kayma)
    kayip = w0 * dus
    digerL = pz[(pz > 0) & (pz.index != top)]; digerS = pz[pz < 0]
    if ikinci:                                   # ikinci en büyük long da düşer
        t2 = digerL.idxmax(); kayip += digerL[t2] * ikinci; digerL = digerL.drop(t2)
    kayip += digerL.sum() * diger_L + (-digerS.sum()) * (-diger_S)   # short: fiyat düşerse kazanır
    oz = 1 + kayip
    brut0 = pz.abs().sum()
    yeni = pz.copy(); yeni[top] = 0 if stop and coin_dus <= -ESIK_STOP else w0 * (1 + coin_dus)
    yeni[digerL.index] = digerL * (1 + diger_L); yeni[digerS.index] = digerS * (1 + diger_S)
    bakim = (yeni.abs() * MMR).sum() + abs(yeni[top]) * (MMR_COIN - MMR)
    return dict(kayip=-kayip * 100, brut0=brut0, brut1=yeni.abs().sum() / oz, bakim_oran=bakim / oz * 100 if oz > 0 else np.inf,
                tasfiye=oz <= bakim, gunsonu=BAKIYE * oz, toparlanma=(1 / oz - 1) * 100 if oz > 0 else np.inf)


# piyasa çöküşü: BTC'nin en kötü 5 gününde likit evrenin medyan 24 sa getirisi (GERÇEK)
btc = C["BTCUSDT"].pct_change(6, fill_method=None)
kotu = btc.nsmallest(40).index; kotu = [t for i, t in enumerate(kotu) if all(abs((t - u).total_seconds()) > 86400 for u in kotu[:i])][:5]
alt = [float((C.pct_change(6, fill_method=None).loc[t].where(U.loc[t])).median()) for t in kotu]
ALT = float(np.nanmean(alt))

SEN = [  # (ad, etiket, kwargs)
    ("A1 −%50, piyasa yatay", "coin hareketi gerçek, anlık şok varsayımsal", dict(coin_dus=-0.50)),
    ("A2 −%80, piyasa yatay", "coin hareketi gerçek, anlık şok varsayımsal", dict(coin_dus=-0.80)),
    ("A3 −%95, piyasa yatay", "varsayımsal", dict(coin_dus=-0.95)),
    ("B1 −%50 + BTC çöküş günü (diğerleri gerçek medyan)", "piyasa girdisi gerçek, birleşim varsayımsal", dict(coin_dus=-0.50, diger_L=ALT, diger_S=ALT)),
    ("B2 −%80 + BTC çöküş, koşullu stop ÇALIŞIR (−%45 + %5 kayma)", "varsayımsal", dict(coin_dus=-0.80, diger_L=ALT, diger_S=ALT, stop=True, kayma=0.05)),
    ("B3 −%80 + BTC çöküş, stop ÇALIŞMAZ", "varsayımsal", dict(coin_dus=-0.80, diger_L=ALT, diger_S=ALT)),
    ("B4 −%95 + BTC çöküş, stop ÇALIŞMAZ", "varsayımsal", dict(coin_dus=-0.95, diger_L=ALT, diger_S=ALT)),
    ("C1 likidite kaybı: stop tetiklenir, dolum −%70'te", "varsayımsal", dict(coin_dus=-0.80, diger_L=ALT, diger_S=ALT, stop=True, kayma=0.25)),
    ("D1 −%80 + 2. büyük long −%50, piyasa yatay", "varsayımsal", dict(coin_dus=-0.80, ikinci=-0.50)),
    ("D2 −%80 + longlar −%20, shortlar −%5 (ayrışma: kalabalık shortlar düşmez)", "varsayımsal", dict(coin_dus=-0.80, diger_L=-0.20, diger_S=-0.05)),
    ("D3 −%95 + longlar −%30, shortlar 0", "varsayımsal", dict(coin_dus=-0.95, diger_L=-0.30, diger_S=0.0)),
]

if __name__ == "__main__":
    print(f"Doz {DOZ}x · bakiye {BAKIYE:.0f} $ · durum sayısı {len(durum)} (iki hiza)")
    print(f"En büyük tek long payı (özkaynağa göre, ×{DOZ}): medyan %{durum.maxlong.median()*100:.1f} · %99 %{durum.maxlong.quantile(.99)*100:.1f} · "
          f"maks %{durum.maxlong.max()*100:.1f}; brüt medyan {durum.brut.median():.2f}x")
    print("\nGERÇEKLEŞMİŞ: tutulan long'larda 24 sa içinde ≥ %50 düşüş:", len(cokus), "kayıt,",
          cokus.sembol.nunique(), "coin:", ", ".join(sorted(cokus.sembol.unique())[:15]))
    print("  ağırlık SABİT tutulsaydı en kötü 6 (coin başına bir kez):")
    for _, r in L.sort_values("etki_sabit").drop_duplicates("sembol").head(6).iterrows():
        print(f"   {r.zaman} {r.sembol:<12} pay %{r.w*100:4.1f} · coin {r.r24*100:+6.1f}% · piyasa {r.piyasa24*100:+5.1f}% · özkaynak {r.etki_sabit*100:+5.2f}%")
    print("  GERÇEKLEŞEN (defterdeki gerçek ağırlıklarla, 24 sa, coin başına en kötü) ilk 8:")
    for _, r in G.head(8).iterrows():
        print(f"   {r.zaman} {r.sembol:<12} hiza {r.hiza} · özkaynak etkisi {r.etki_gercek*100:+5.2f}%")
    print(f"\nPiyasa çöküş girdisi (GERÇEK): BTC'nin en kötü 5 günü {[str(t.date()) for t in kotu]} → likit evren medyan 24 sa "
          f"{[round(a*100,1) for a in alt]} → ortalama %{ALT*100:.1f}")
    rows = []
    for _, st in secilen.iterrows():
        for ad, et, kw in SEN:
            r = senaryo(st, **kw); r.update(durum=f"{st.name[1]} {st.sembol} (pay %{st.maxlong*100:.1f}, {st.etiket})", senaryo=ad, etiket=et); rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(f"{O}/senaryolar.csv", index=False)
    for d, g2 in T.groupby("durum", sort=False):
        print(f"\n=== {d}")
        print(f"   {'senaryo':<70} {'kayıp%':>7} {'brüt önce→sonra':>16} {'bakım/özk%':>10} {'tasfiye':>7} {'gün sonu $':>10} {'toparlanma%':>11}  etiket")
        for _, r in g2.iterrows():
            print(f"   {r.senaryo:<70} {r.kayip:7.1f} {r.brut0:7.2f}→{r.brut1:5.2f}x {r.bakim_oran:10.1f} {('EVET' if r.tasfiye else 'hayır'):>7} {r.gunsonu:10.0f} {r.toparlanma:11.1f}  {r.etiket}")
