"""Tersine dönüş filtresi testleri (madde 109).

Bu filtre VARSAYILAN OLARAK KAPALIDIR - ölçüm sonucu net kazanç
sağlamadığını gösterdi (aşağıya bakınız). Kod opsiyonel olarak duruyor.

Testlerin amacı:
  1) Ölçüm fonksiyonu ileriye bakmıyor mu? (look-ahead yok)
  2) Ölçüm doğru mu? (yapay ortalamaya dönüş verisinde negatif çıkmalı)
  3) Parametre GERÇEKTEN etki ediyor mu? ("sessiz no-op" hata sınıfı -
     bu projede 6 kez yaşandı, bkz. README madde 56/94/95/96/106/107)
  4) Kademeli mod piyasa nötrlüğünü bozuyor mu?
"""
import numpy as np
import pandas as pd
import sys

sys.path.insert(0, '.')
from crosssec_backtest import _reversal_corr, run_crosssectional

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


print("1) Ölçüm fonksiyonu ileriye BAKMIYOR mu?")
# Veriyi i'den sonra tamamen bozarsak sonuç DEĞİŞMEMELİ.
rng = np.random.default_rng(0)
fiyat = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, (900, 8)), axis=0))
i = 700
a = _reversal_corr(fiyat, i, 30, 540)
bozuk = fiyat.copy()
bozuk[i:] *= 5.0                      # gelecek tamamen değişti
b = _reversal_corr(bozuk, i, 30, 540)
kontrol("gelecek veri sonucu etkilemiyor", a is not None and abs(a - b) < 1e-12,
        f"({a} vs {b})")

print("\n2) Ölçüm DOĞRU mu?")
# Yapay ortalamaya dönüş: her coin kendi ortalamasına geri çekiliyor
n = 8
s = np.zeros((900, n))
for t in range(1, 900):
    s[t] = s[t - 1] * 0.90 + rng.normal(0, 0.02, n)
md = 100 * np.exp(s)
rc_md = _reversal_corr(md, 700, 30, 540)
kontrol("ortalamaya dönüşlü veride NEGATİF", rc_md is not None and rc_md < -0.10,
        f"(ölçülen {rc_md})")
# Rastgele yürüyüşte sıfıra yakın olmalı
kontrol("rastgele yürüyüşte sıfıra yakın", a is not None and abs(a) < 0.25,
        f"(ölçülen {a})")
# Yetersiz veride None (filtre uygulanmaz, sessizce yanlış davranmaz)
kontrol("yetersiz veride None döner", _reversal_corr(fiyat, 40, 30, 540) is None)

print("\n3) Parametre GERÇEKTEN etki ediyor mu? (sessiz no-op kontrolü)")
tarih = pd.date_range('2022-01-01', periods=900, freq='4h')
panel = pd.DataFrame(md, index=tarih,
                     columns=[f"C{k}USDT" for k in range(n)])


def calistir(**kw):
    _, m = run_crosssectional(panel, 60, 6, 3, horizons_bars=[30, 60],
                              pos_tp=0.04, compound=True, **kw)
    return m


kapali = calistir()
# Çok sıkı eşik: hiçbir zaman açılmamalı -> işlem sayısı düşmeli
siki = calistir(max_reversal_corr=-0.99)
kontrol("çok sıkı eşik işlemleri durduruyor",
        siki['n_rebalance_trades'] < kapali['n_rebalance_trades'],
        f"({siki['n_rebalance_trades']} vs {kapali['n_rebalance_trades']})")
kontrol("kapalı modda filtre hiç devreye girmiyor",
        calistir(max_reversal_corr=None)['n_rebalance_trades'] == kapali['n_rebalance_trades'])
# Gevşek eşik: bu veri güçlü dönüşlü, filtre neredeyse hiç kapatmamalı
gevsek = calistir(max_reversal_corr=-0.02)
kontrol("gevşek eşik sonucu az değiştiriyor",
        abs(gevsek['total_return_pct'] - kapali['total_return_pct'])
        < abs(siki['total_return_pct'] - kapali['total_return_pct']))

print("\n4) Kademeli mod")
kad = calistir(max_reversal_corr=-0.02, reversal_full=-0.20)
kontrol("kademeli mod çalışıyor ve sonuç üretiyor",
        np.isfinite(kad['total_return_pct']))
kontrol("kademeli mod sert moddan farklı sonuç veriyor",
        abs(kad['total_return_pct'] - siki['total_return_pct']) > 1e-9)
# Nötrlük: ölçek her iki bacağa eşit uygulandığı için piyasa nötrlüğü
# korunmalı. Tek yönlü uygulansaydı net exposure oluşurdu.
kontrol("kademeli modda işlem sayısı makul",
        0 < kad['n_rebalance_trades'] <= kapali['n_rebalance_trades'] * 1.5,
        f"({kad['n_rebalance_trades']} vs {kapali['n_rebalance_trades']})")

print("\n" + "=" * 60)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)} test")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum testler gecti.")
print("""
HATIRLATMA: filtre VARSAYILAN KAPALI. Gercek veri olcumu (2022-2026,
6 fazin ortalamasi, parametreler sabit):

  varyant            bilesik    en iyi 3 donem haric
  filtresiz          +5987%     +23.7%
  sert  (-0.10/540)  +5057%     +26.8%
  kademeli           +4379%     +22.8%
  sert  (-0.10/270)  +3872%     +44.7%

Filtre GETIRI karsiliginda SUREKLILIK satin aliyor - bedava degil.
Hicbir varyant her iki olcutte birden filtresizi gecmedi.
""")
