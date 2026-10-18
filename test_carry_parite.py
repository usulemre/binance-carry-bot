"""SİNYAL TANIMI PARİTESİ TESTLERİ (madde 210).

Bu dosyanın varlık sebebi: madde 209'da canlı bot ile backtest AYNI
SİNYALİ kullanmayı bırakmıştı (canlı 8 saatlik pencere, backtest 3
günlük ortalama) ve 519 testin HİÇBİRİ bunu yakalamadı. Beklenti
+%93 olarak raporlanıyordu ama o rakam botun kullandığı sinyalle hiç
ölçülmemişti.

Buradaki testler o hatayı ve iki kardeşini (kapsayıcı pencere sınırı,
kayıt sayısını kırpan formül) GERİ KONULDUĞUNDA kırmızıya döner.
"""
import sys

import numpy as np
import pandas as pd

import carry_bot as cb
import carry_parite as cp

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad} {detay}")
        basarisiz.append(ad)


def _kayit(n, aralik_saat, oranlar, t0=1_700_000_000_000):
    adim = int(aralik_saat * 3600000)
    return [{"fundingTime": t0 + i * adim, "fundingRate": str(oranlar[i])}
            for i in range(n)]


def _panel(n=60, aralik_saat=8.0, oran=None, t0="2024-01-01"):
    """Sahte ödeme tablosu (carry_parite'nin beklediği biçim)."""
    if oran is None:
        oran = np.linspace(-0.001, 0.001, n)
    t = pd.date_range(t0, periods=n, freq=f"{int(aralik_saat)}h")
    return pd.DataFrame({"date": t, "funding": np.asarray(oran, float)})


print("1) ÖDEME SAYISI CANLI KODDAN GERİ ÇIKIYOR")
# Sayim, yillik_funding'in DONUSUNDEN hesaplanir - burada yeniden
# uygulanmaz. Yoksa canli koddaki degisiklik kacirilirdi.
for pen in (8.0, 48.0, 72.0):
    for ar in (1.0, 2.0, 4.0, 8.0):
        g = cp.odeme_sayisi(pen, ar)
        b = cp.odeme_sayisi_beklenen(pen, ar)
        kontrol(f"pencere {pen:.0f}sa / aralık {ar:.0f}sa -> {b} ödeme",
                g == b, f"({g})")

print("\n2) MADDE 209 HATA 1: PENCERE AYRIŞMASI")
kontrol("referans pencere sabiti canlı ayarla AYNI",
        cp.REFERANS_PENCERE_SAAT == cb.FUNDING_WINDOW_HOURS,
        f"(referans {cp.REFERANS_PENCERE_SAAT}, canlı {cb.FUNDING_WINDOW_HOURS})")
_k = cp.karar()
kontrol("mevcut ayarla karar TAMAM", _k["durum"] == "TAMAM",
        f"({_k['sorunlar']})")
_k8 = cp.karar(8.0)
kontrol("pencere 8 saate çekilirse karar BOZUK", _k8["durum"] == "BOZUK")
kontrol("gerekçe pencere ayrışmasını ADIYLA söylüyor",
        any("PENCERE AYRIŞMIŞ" in x for x in _k8["sorunlar"]),
        f"({_k8['sorunlar']})")
kontrol("gerekçe beklentinin geçersiz olduğunu söylüyor",
        any("ÖLÇÜLMEDİ" in x for x in _k8["sorunlar"]))
_k72 = cp.karar(72.0)
kontrol("panelin 72 saati de BOZUK sayılıyor (referans 48)",
        _k72["durum"] == "BOZUK",
        "referans pencere neyse o geçerli, panelin penceresi değil")

print("\n3) MADDE 209 HATA 2: PENCERE SINIRI KAPSAYICI OLURSA")
_orij = cb.yillik_funding


def _kapsayici(kayitlar, saat=None):
    """Madde 209'dan ÖNCEKİ hâl: `>=` ile kapsayıcı sınır."""
    if len(kayitlar) < 2:
        return None
    z = sorted(int(k["fundingTime"]) for k in kayitlar)
    f = [(z[i + 1] - z[i]) / 3600000.0 for i in range(len(z) - 1)]
    f = [x for x in f if 0.5 <= x <= 24]
    if not f:
        return None
    ar = max(sorted(f)[len(f) // 2], 4.0)
    sec = kayitlar
    if saat and saat > 0:
        son = max(int(k["fundingTime"]) for k in kayitlar)
        kes = son - int(saat * 3600000)
        ic = [k for k in kayitlar if int(k["fundingTime"]) >= kes]
        if ic:
            sec = ic
    ort = sum(float(k["fundingRate"]) for k in sec) / len(sec)
    return ort * (24.0 / ar) * 365.0


cb.yillik_funding = _kapsayici
_kk = cp.karar(48.0)
kontrol("kapsayıcı sınır geri konursa karar BOZUK", _kk["durum"] == "BOZUK")
kontrol("her aralıkta ödeme sayısı BİR FAZLA çıkıyor",
        len([x for x in _kk["sorunlar"] if "ÖDEME SAYISI" in x]) == 4,
        f"({len(_kk['sorunlar'])} sorun)")
kontrol("8sa sembolde 6 yerine 7 ödeme tespit ediliyor",
        any("8sa sembolde 7 ödeme" in x for x in _kk["sorunlar"]),
        f"({_kk['sorunlar'][:1]})")
cb.yillik_funding = _orij
kontrol("gerçek fonksiyon geri yüklendi, karar yine TAMAM",
        cp.karar()["durum"] == "TAMAM")

print("\n4) MADDE 209 HATA 3: KAYIT SAYISI PENCEREYİ KIRPARSA")
_os = cp.odeme_sayisi


def _kirpan(pencere, aralik_saat, n=400):
    """Madde 209'dan ÖNCEKİ formül: n = saat/2 + 4, üst sınır 100."""
    t0 = 1_700_000_000_000
    adim = int(aralik_saat * 3600000)
    nk = max(4, min(100, int(pencere / 2) + 4))
    kayit = [{"fundingTime": t0 + i * adim,
              "fundingRate": ("1.0" if i == n - 1 else "0.0")}
             for i in range(n)][-nk:]
    y = cb.yillik_funding(kayit, pencere)
    if not y or y <= 0:
        return 0
    return int(round((24.0 / max(aralik_saat, 4.0)) * 365.0 / y))


cp.odeme_sayisi = _kirpan
_kc = cp.karar(48.0)
kontrol("kırpan formül geri konursa karar BOZUK", _kc["durum"] == "BOZUK")
kontrol("kırpma SAATLİK ödeyende yakalanıyor (48 yerine 28)",
        any("1sa sembolde 28 ödeme" in x for x in _kc["sorunlar"]),
        f"({_kc['sorunlar']})")
kontrol("8 saatlik sembolde kırpma YOK (doğru şekilde şikâyet etmiyor)",
        not any("8sa sembolde" in x for x in _kc["sorunlar"]))
cp.odeme_sayisi = _os

print("\n5) CANLI SİNYAL GERÇEK FONKSİYONU ÇAĞIRIYOR")
_p = _panel(40, 8.0, [0.0001] * 39 + [-0.01])
_bar = pd.date_range(_p["date"].iloc[0].ceil("4h"),
                     _p["date"].iloc[-1].floor("4h"), freq="4h")
_cs = cp.canli_sinyal(_p, _bar, 48.0)
kontrol("her bar için değer üretiliyor", _cs.notna().sum() > 0.5 * len(_bar),
        f"({_cs.notna().sum()}/{len(_bar)})")
_cagri = [0]
_gercek = cb.yillik_funding


def _sayan(*a, **k):
    _cagri[0] += 1
    return _gercek(*a, **k)


cb.yillik_funding = _sayan
cp.canli_sinyal(_p, _bar, 48.0)
cb.yillik_funding = _gercek
kontrol("carry_bot.yillik_funding GERÇEKTEN çağrılıyor (kopya yok)",
        _cagri[0] > 0, f"({_cagri[0]} çağrı)")
# son barda uc funding gorunuyor mu (pencere 8sa -> sadece son odeme)
_son8 = cp.canli_sinyal(_p, _bar, 8.0).dropna().iloc[-1]
_son48 = _cs.dropna().iloc[-1]
kontrol("8sa pencere uç ödemeyi 48sa'den DAHA GÜÇLÜ gösteriyor",
        _son8 < _son48 < 0, f"(8sa {_son8:.2f}, 48sa {_son48:.2f})")

print("\n6) BACKTEST SİNYALİ PANELİN KURULUMUNU İZLİYOR")
_bs = cp.backtest_sinyal(_p, _bar, cp.PANEL_BAR)
kontrol("panel sinyali üretiliyor", _bs.notna().sum() > 0)
kontrol("panel rolling penceresi 18 bar (carry_denetim.FUNDING_PENCERE)",
        cp.PANEL_BAR == 18, f"({cp.PANEL_BAR})")
try:
    import carry_denetim as _cd
    kontrol("PANEL_BAR gerçekten carry_denetim ile aynı",
            cp.PANEL_BAR == _cd.FUNDING_PENCERE,
            f"(parite {cp.PANEL_BAR}, denetim {_cd.FUNDING_PENCERE})")
except Exception as _e:
    kontrol("carry_denetim okunabildi", False, f"({_e})")
# ilk 18 barda min_periods yuzunden NaN olmali (bakisiz baslangic)
kontrol("ilk barlarda NaN (geçmiş yetersiz - ileriye bakmıyor)",
        not np.isfinite(_bs.iloc[0]))

print("\n7) KESİTSEL PARİTE ÖLÇÜMÜ")
# Ayni pencerede referans paritesi TAM 1.0 olmali
_p2 = {f"T{i}USDT": _panel(60, 8.0, np.sin(np.arange(60) / 3.0 + i) * 0.001)
       for i in range(5)}
import os
import tempfile
_d = tempfile.mkdtemp()
for s, v in _p2.items():
    v.to_csv(os.path.join(_d, f"{s}.csv"), index=False)
_r = cp.referans_parite(list(_p2), _d, cp.REFERANS_PENCERE_SAAT)
kontrol("referans pencerede sıralama paritesi TAM 1.0",
        abs(_r["kor"] - 1.0) < 1e-9, f"({_r['kor']:.6f})")
_r8 = cp.referans_parite(list(_p2), _d, 8.0)
kontrol("8 saatte sıralama paritesi DÜŞÜYOR", _r8["kor"] < 0.95,
        f"({_r8['kor']:.4f})")
kontrol("düşüş BOZUK olarak sınıflanıyor", _r8["durum"] == "BOZUK",
        f"({_r8['durum']})")
_az = cp.parite_olc(["T0USDT"], _d)
kontrol("tek sembolle VERI_YOK döner, çökmüyor", _az["durum"] == "VERI_YOK")
kontrol("olmayan sembol None döner", cp.odemeleri_oku("YOKUSDT", _d) is None)

print("\n8) RAPOR METNİ")
_m = cp.yaz(0, None, _d)
kontrol("rapor ŞART 1/2/3'ü ayrı ayrı gösteriyor",
        "ŞART 1" in _m and "ŞART 2" in _m and "ŞART 3" in _m)
kontrol("rapor KARAR satırı içeriyor", "KARAR:" in _m)
kontrol("rapor panel korelasyonunu BİLGİ olarak ayırıyor",
        "KARARA GİRMEZ" in _m)
_m8 = cp.yaz(0, 8.0, _d)
kontrol("bozuk ayarda rapor BOZUK diyor", "KARAR: BOZUK" in _m8)
kontrol("bozuk ayarda çevre değişkenini ADIYLA söylüyor",
        "CARRY_FUNDING_WINDOW_H" in _m8)
kontrol("veri yokken de çökmüyor",
        "ŞART 2" in cp.yaz(0, None, tempfile.mkdtemp()))

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum parite testleri gecti.")
print("""
NE DOGRULANDI: canli botun sinyal TANIMI, beklentinin olculdugu
tanimla ayni mi. Madde 209'da ayrismisti ve hicbir test gormedi -
`carry_sapma.py` gerceklesen GETIRIYI karsilastiriyor, tanimi degil.

NE DOGRULANMADI: tanimin DOGRU olup olmadigi. Bu testler sadece
canli kod ile olculen yapilandirmanin AYNI oldugunu soyler. Hangi
pencerenin en iyi oldugu ayri bir olcumdur (madde 209.4).
""")
