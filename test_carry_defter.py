"""P&L muhasebe özdeşliği testleri (madde 135).

NEDEN BU TEST: madde 134'te "funding +146.6%, fiyat +35.3%" diye
rapor edilmişti ama net sonuç +%30/yıl idi. Üç rakam birbirine
dönüşmüyordu, çünkü ilk ikisi DOLAR DEĞİL bar bazlı getiri
oranlarının toplamıydı. Muhasebe hatası sessizdi: kod çalışıyor,
sayılar makul görünüyor, sadece birbirini tutmuyordu.

Bu test o sınıf hatanın tekrarını engeller:
    E_başlangıç + fiyat$ + funding$ - komisyon$ - kayma$ = E_final
özdeşliği hem HER BAR'da hem TOPLAMDA hem SEMBOL bazında tutmalı.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, '.')
import carry_defter as L

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


def sahte_panel(n_sem=40, n_bar=900, tohum=0):
    """Rastgele ama TUTARLI panel: fiyat, funding, hacim, yaş."""
    rng = np.random.default_rng(tohum)
    idx = pd.date_range("2023-01-01", periods=n_bar, freq="4h")
    kol = [f"C{i}USDT" for i in range(n_sem)]
    getiri = rng.normal(0, 0.02, (n_bar, n_sem))
    C = pd.DataFrame(100 * np.exp(np.cumsum(getiri, axis=0)), index=idx, columns=kol)
    # funding: sembole göre kalıcı fark + gürültü, 8 saatte bir (2 barda 1)
    taban = np.linspace(-0.0006, 0.0006, n_sem)
    ODE = pd.DataFrame(0.0, index=idx, columns=kol)
    ODE.iloc[::2] = taban + rng.normal(0, 0.0002, (len(ODE.iloc[::2]), n_sem))
    SIN = pd.DataFrame(np.tile(taban * 3, (n_bar, 1)), index=idx, columns=kol)
    uy = pd.DataFrame(True, index=idx, columns=kol)
    return C, ODE, SIN, uy


print("1) TOPLAM ÖZDEŞLİK")
C, ODE, SIN, uy = sahte_panel()
P, S, o = L.defter(C, ODE, SIN, uy, bas=100, baslangic_equity=10000.0)
toplam = (o["E0"] + o["fiyat_pnl"] + o["funding_pnl"] + o["komisyon"]
          + o["kayma"] + o["finansman"] + o["likidasyon"])
fark = abs(o["E_final"] - toplam)
kontrol("E0 + fiyat + funding - ücret = E_final (sent altı)",
        fark < 0.01, f"(fark {fark:.6f} USD)")
kontrol("fark makine hassasiyeti mertebesinde", fark < 1e-6,
        f"(fark {fark:.3e})")

print("\n2) HER BAR İÇİN ÖZDEŞLİK")
lhs = (P.E_bar_basi + P.ucret_komisyon + P.ucret_kayma
       + P.fiyat_pnl + P.funding_pnl)
hata = (P.E_bar_sonu - lhs).abs()
kontrol("hiçbir barda 1 sent üstü sapma yok",
        (hata > 0.01).sum() == 0, f"({int((hata > 0.01).sum())} bar)")
kontrol("maksimum bar hatası < 1e-6 USD", hata.max() < 1e-6,
        f"({hata.max():.3e})")

print("\n3) ZİNCİR SÜREKLİLİĞİ")
zin = (P.E_bar_basi.shift(-1) - P.E_bar_sonu).abs().dropna()
kontrol("bir barın sonu = sonraki barın başı (kopukluk yok)",
        zin.max() < 1e-9, f"(max {zin.max():.3e})")

print("\n4) SEMBOL TOPLAMI = PORTFÖY TOPLAMI")
for ad, pk, sk in [("fiyat", "fiyat_pnl", "fiyat_pnl"),
                   ("funding", "funding_pnl", "funding_pnl"),
                   ("komisyon", "ucret_komisyon", "komisyon"),
                   ("kayma", "ucret_kayma", "kayma")]:
    d = abs(float(P[pk].sum()) - float(S[sk].sum()))
    kontrol(f"{ad}: sembol toplamı portföyle aynı", d < 1e-6, f"({d:.3e})")
kontrol("sembol NET toplamı = E_final - E0",
        abs(S.net_pnl.sum() - (o["E_final"] - o["E0"])) < 1e-6,
        f"({S.net_pnl.sum() - (o['E_final'] - o['E0']):.3e})")

print("\n5) ÜCRET FORMÜLÜ")
reb = P[P.devir > 0]
bek = float((reb.devir * reb.E_bar_basi * (L.KOM_KOMISYON + L.KOM_KAYMA)).sum())
ger = float(-(reb.ucret_komisyon + reb.ucret_kayma).sum())
kontrol("ücret = devir x equity x oran", abs(bek - ger) < 1e-6,
        f"(beklenen {bek:.6f}, gerçek {ger:.6f})")
kontrol("komisyon/kayma oranı doğru bölünmüş",
        abs(float(-P.ucret_komisyon.sum()) / max(float(-P.ucret_kayma.sum()), 1e-9)
            - L.KOM_KOMISYON / L.KOM_KAYMA) < 1e-6)
kontrol("ücret rebalance OLMAYAN barlarda sıfır",
        float(P[P.devir == 0][["ucret_komisyon", "ucret_kayma"]].abs().sum().sum()) == 0.0)

print("\n6) ÜCRET, GETİRİDEN ÖNCE ALINIYOR (sıra kontrolü)")
# ücret oranı 0 ile pozitif arasındaki fark tam olarak ücret kadar olmalı DEĞİL
# (bileşiklenme var) ama sıfır ücrette final equity DAHA YÜKSEK olmalı
_, _, o0 = L.defter(C, ODE, SIN, uy, bas=100, kom_komisyon=0.0,
                    kom_kayma=0.0, baslangic_equity=10000.0)
kontrol("sıfır ücrette final equity daha yüksek",
        o0["E_final"] > o["E_final"],
        f"({o0['E_final']:.2f} vs {o['E_final']:.2f})")
kontrol("sıfır ücrette ücret kalemleri gerçekten sıfır",
        abs(o0["komisyon"]) < 1e-12 and abs(o0["kayma"]) < 1e-12)

print("\n7) ÖLÇEK BAĞIMSIZLIĞI (dolar defteri doğrusal olmalı)")
_, _, oB = L.defter(C, ODE, SIN, uy, bas=100, baslangic_equity=1_000_000.0)
oran = oB["E_final"] / o["E_final"]
kontrol("100x sermaye -> 100x final equity (oransal)",
        abs(oran - 100.0) < 1e-6, f"(oran {oran:.9f})")
kontrol("getiri yüzdesi sermayeden bağımsız",
        abs((oB["E_final"] / oB["E0"]) - (o["E_final"] / o["E0"])) < 1e-9)

print("\n8) TANIM AYRIMI: oran toplamı != bileşik getiri")
r_top = float((P.funding_pnl / P.E_ucret_sonrasi).sum()
              + (P.fiyat_pnl / P.E_ucret_sonrasi).sum())
bilesik = o["E_final"] / o["E0"] - 1
kontrol("oran toplamı ile bileşik getiri FARKLI (ikisi karıştırılmamalı)",
        abs(r_top - bilesik) > 1e-6,
        f"(oran toplamı {r_top:.4f}, bileşik {bilesik:.4f})")
kontrol("dolar P&L / E0, oran toplamından farklı",
        abs((o["fiyat_pnl"] + o["funding_pnl"]) / o["E0"] - r_top) > 1e-9)

print("\n" + "=" * 64)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum defter testleri gecti.")
print("""
NE DOGRULANDI: muhasebe OZDESLIGI - her bar, her sembol, toplam.
NE DOGRULANMADI: rakamlarin GERCEKLIGI. Defter, yanlis bir backtest'in
                 sonuclarini da kusursuz mutabakatla raporlayabilir.
                 Ozdeslik dogrulugun degil, TUTARLILIGIN kanitidir.
""")
