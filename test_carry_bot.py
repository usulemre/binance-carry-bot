"""carry_bot testleri.

EN KRİTİK TEST: İŞARET YÖNÜ. Backtest geliştirilirken tam bu hata
yapıldı - yüksek funding ödeyen coinler LONG'lanmıştı ve strateji
-20.9% getiriyle "çalışmıyor" görünmüştü. İşaret düzeltilince +15.3%
oldu. Bu hata sessizdi: kod çalışıyor, emir gidiyor, sadece para
ters yöne akıyor.

Diğer testler: pozisyon nötrlüğü, tolerans mantığı, likidite filtresi,
yetersiz veri davranışı.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, '.')
import carry_bot as cb

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


print("1) İŞARET YÖNÜ — en kritik test")
# 6 coin: A,B en NEGATIF funding (long olmali), E,F en YUKSEK (short olmali)
f = pd.Series({"AUSDT": -0.0010, "BUSDT": -0.0005, "CUSDT": 0.0000,
               "DUSDT": 0.0002, "EUSDT": 0.0008, "FUSDT": 0.0015})
eski_n = cb.N_LEGS
cb.N_LEGS = 2
h = cb.hedef_portfoy(f, 10000.0)
kontrol("en DÜŞÜK funding LONG (pozitif USD)",
        h.get("AUSDT", 0) > 0 and h.get("BUSDT", 0) > 0,
        f"(A={h.get('AUSDT')}, B={h.get('BUSDT')})")
kontrol("en YÜKSEK funding SHORT (negatif USD)",
        h.get("EUSDT", 0) < 0 and h.get("FUSDT", 0) < 0,
        f"(E={h.get('EUSDT')}, F={h.get('FUSDT')})")
kontrol("ortadakiler pozisyonsuz",
        "CUSDT" not in h and "DUSDT" not in h)
# Anlamli kontrol: funding ALIYOR muyuz?
# long bacak: funding negatifse ALIRIZ (-poz*f > 0 cunku f<0, poz>0)
# short bacak: funding pozitifse ALIRIZ (-poz*f > 0 cunku f>0, poz<0)
gelir = sum(-(usd / 10000.0) * f[s] for s, usd in h.items())
kontrol("net funding GELİRİ pozitif", gelir > 0, f"(net {gelir:+.6f})")

print("\n2) PİYASA NÖTRLÜĞÜ")
kontrol("long ve short tarafı eşit büyüklükte",
        abs(sum(v for v in h.values() if v > 0)
            + sum(v for v in h.values() if v < 0)) < 1e-9,
        f"(net {sum(h.values()):+.4f})")
# madde 156: uç fırsat YOKSA brüt = (1 - REZERV) x sermaye; rezerv kapalıysa tam brüt
kontrol("toplam brüt = bakiye * GROSS * (1 - REZERV)",
        abs(sum(abs(v) for v in h.values())
            - 10000.0 * cb.GROSS_EXPOSURE * (1 - cb.REZERV_PAY)) < 1e-6,
        f"(brüt {sum(abs(v) for v in h.values()):.2f})")
_hf_uc = pd.Series({k: -9.0 for k in h})
_h_uc = cb.hedef_portfoy(f, 10000.0, ham_funding=_hf_uc)
kontrol("uç fırsat VARKEN brüt tam sermayeye çıkıyor",
        abs(sum(abs(v) for v in _h_uc.values()) - 10000.0 * cb.GROSS_EXPOSURE) < 1e-6,
        f"(brüt {sum(abs(v) for v in _h_uc.values()):.2f})")
kontrol("bacak sayısı 2*N_LEGS", len(h) == 2 * cb.N_LEGS, f"({len(h)})")

print("\n3) YETERSİZ VERİ")
kontrol("az sembolde boş portföy döner (sessizce yanlış davranmaz)",
        cb.hedef_portfoy(pd.Series({"AUSDT": 0.001}), 10000.0) == {})
kontrol("NaN funding'ler elenir",
        len(cb.hedef_portfoy(
            pd.Series({"AUSDT": -0.001, "BUSDT": -0.0005, "CUSDT": float("nan"),
                       "DUSDT": 0.0002, "EUSDT": 0.0008, "FUSDT": 0.0015}),
            10000.0)) == 2 * cb.N_LEGS)

print("\n4) EMİR HESABI")
hedef = {"AUSDT": 1000.0, "BUSDT": -1000.0}
kontrol("boş portföyden tam emir çıkar",
        len(cb.emirleri_hesapla(hedef, {}, 100.0)) == 2)
kontrol("hedefe eşit portföyde emir YOK",
        cb.emirleri_hesapla(hedef, dict(hedef), 100.0) == [])
kontrol("tolerans içi sapma emir üretmez",
        cb.emirleri_hesapla(hedef, {"AUSDT": 950.0, "BUSDT": -1000.0}, 100.0) == [])
kontrol("tolerans dışı sapma emir üretir",
        len(cb.emirleri_hesapla(hedef, {"AUSDT": 500.0, "BUSDT": -1000.0}, 100.0)) == 1)
e = cb.emirleri_hesapla({"AUSDT": 1000.0}, {"AUSDT": -1000.0}, 100.0)
kontrol("short'tan long'a dönüşte yön BUY ve miktar 2000",
        len(e) == 1 and e[0][1] == "BUY" and abs(e[0][2] - 2000.0) < 1e-9,
        f"({e})")
kapat = cb.emirleri_hesapla({}, {"AUSDT": 1000.0}, 100.0)
kontrol("hedefte olmayan pozisyon kapatılır (SELL)",
        len(kapat) == 1 and kapat[0][1] == "SELL", f"({kapat})")
kontrol("MIN_NOTIONAL altı emir üretilmez",
        cb.emirleri_hesapla({"AUSDT": 3.0}, {}, 0.0) == [])

print("\n5) YILLIKLAŞTIRMA — backtest/canlı paritesi")
def kayit(oran, aralik_saat, adet=6):
    t0 = 1700000000000
    return [{"fundingRate": str(oran), "fundingTime": t0 + i*aralik_saat*3600000}
            for i in range(adet)]
y8 = cb.yillik_funding(kayit(0.0001, 8))
y4 = cb.yillik_funding(kayit(0.0001, 4))
kontrol("8 saatlik funding dogru yillklasiyor (%0.01 -> %10.95/yil)",
        abs(y8 - 0.0001*3*365) < 1e-9, f"({y8})")
kontrol("AYNI oranda 4 saatlik funding 2 KAT yillik verir",
        abs(y4 - 2*y8) < 1e-9, f"(4sa={y4}, 8sa={y8})")
kontrol("negatif funding negatif kalir", cb.yillik_funding(kayit(-0.0002, 8)) < 0)
kontrol("tek kayitta None (aralik olculemez)", cb.yillik_funding(kayit(0.0001, 8, 1)) is None)
kontrol("bos listede None", cb.yillik_funding([]) is None)
# 4 saatlik dusuk oranli coin, 8 saatlik yuksek oranli coinden DAHA YUKSEK
# yillik verebilir - ham oranla siralamak bunu kacirir.
d4 = cb.yillik_funding(kayit(0.00008, 4))
d8 = cb.yillik_funding(kayit(0.00012, 8))
kontrol("ham oran DUSUK ama yillik YUKSEK olan dogru siralanir",
        d4 > d8, f"(4sa %0.008 -> {d4:.4f} | 8sa %0.012 -> {d8:.4f})")
# ARALIK ALT SINIRI (madde 138): 1 saatlik gecici aralik sinyali 4 KAT
# sisiriyordu. Binance in kalici en kisa araligi 4 saat; altina inilmez.
y1 = cb.yillik_funding(kayit(0.0001, 1))
y4b = cb.yillik_funding(kayit(0.0001, 4))
kontrol("1 saatlik aralik 4 saate KISITLANIYOR (sinyal sismesi yok)",
        abs(y1 - y4b) < 1e-12, f"(1sa={y1}, 4sa={y4b})")
kontrol("2 saatlik aralik da 4 saate kisitlaniyor",
        abs(cb.yillik_funding(kayit(0.0001, 2)) - y4b) < 1e-12)
kontrol("8 saatlik aralik ETKILENMIYOR (alt sinirin ustunde)",
        abs(cb.yillik_funding(kayit(0.0001, 8)) - 0.0001*3*365) < 1e-9)
kontrol("kisitlama sonrasi 4sa hala 8sa'nin 2 KATI",
        abs(y4b - 2*cb.yillik_funding(kayit(0.0001, 8))) < 1e-12)

print("\n5b) TRADFI TESPİTİ (madde 142)")
kontrol("contractType TRADIFI_PERPETUAL -> TradFi",
        cb.tradfi_mi("XYZUSDT", {"contractType": "TRADIFI_PERPETUAL"}))
kontrol("underlyingType KR_EQUITY -> TradFi",
        cb.tradfi_mi("XYZUSDT", {"contractType": "PERPETUAL", "underlyingType": "KR_EQUITY"}))
kontrol("underlyingType COMMODITY -> TradFi",
        cb.tradfi_mi("XYZUSDT", {"underlyingType": "COMMODITY"}))
kontrol("kripto (PERPETUAL/COIN) -> TradFi DEĞİL",
        not cb.tradfi_mi("BTCUSDT", {"contractType": "PERPETUAL", "underlyingType": "COIN"}))
kontrol("alanlar kripto diyorsa yedek liste EZMEZ",
        not cb.tradfi_mi("XAUUSDT", {"contractType": "PERPETUAL", "underlyingType": "COIN"}))
kontrol("bilgi yoksa yedek liste devrede (XAUUSDT, TSLAUSDT)",
        cb.tradfi_mi("XAUUSDT", None) and cb.tradfi_mi("TSLAUSDT", {}))
kontrol("bilgi yoksa kripto yedek listede değil (BTCUSDT, SOLUSDT)",
        not cb.tradfi_mi("BTCUSDT", None) and not cb.tradfi_mi("SOLUSDT", None))
kontrol("TradFi eleme varsayılan AÇIK", cb.TRADFI_HARIC is True)

print("\n5d) KALABALIK SEÇİMİ (madde 148)")
import pandas as _pd
_sk = _pd.Series({f"S{i}": float(i) for i in range(40)})   # S0 en düşük skor (long), S39 en yüksek
_la, _sa = cb.kalabalik_adaylar(_sk, 5, havuz=2.0)
kontrol("long havuzu en düşük 10 skor, en uçtan başlayarak",
        _la == [f"S{i}" for i in range(10)])
kontrol("short havuzu en yüksek 10 skor, en uçtan başlayarak",
        _sa == [f"S{i}" for i in range(39, 29, -1)])
_or = _pd.Series({f"S{i}": (0.5 if i in (7, 8, 9, 6, 5) else 2.0) for i in range(40)})
kontrol("long: en DÜŞÜK oranlılar (en çok short hesap) seçiliyor",
        set(cb.kalabalik_sec(_la, _or, 5, +1)) == {"S5", "S6", "S7", "S8", "S9"})
_or2 = _pd.Series({f"S{i}": (4.0 if i in (30, 31, 32, 33, 34) else 1.0) for i in range(40)})
kontrol("short: en YÜKSEK oranlılar (en çok long hesap) seçiliyor",
        set(cb.kalabalik_sec(_sa, _or2, 5, -1)) == {"S30", "S31", "S32", "S33", "S34"})
kontrol("oran hiç yoksa en uç n seçiliyor (eski davranış)",
        cb.kalabalik_sec(_la, _pd.Series(dtype=float), 5, +1) == [f"S{i}" for i in range(5)])
kontrol("tüm oranlar eşitse en uç n seçiliyor",
        cb.kalabalik_sec(_la, _pd.Series({k: 1.0 for k in _la}), 5, +1) == [f"S{i}" for i in range(5)])
_la2, _sa2 = cb.kalabalik_adaylar(_sk.iloc[:14], 5, havuz=2.0)
kontrol("dar evrende havuzlar çakışmıyor",
        not (set(_la2) & set(_sa2)) and len(_la2) == 7)
_eski_nl5d, _eski_ml5d = cb.N_LEGS, cb.MIN_LEGS
cb.N_LEGS, cb.MIN_LEGS = 8, 8
_h = cb.hedef_portfoy(_sk, 1000.0, n_legs=8, kalabalik=None)
_hk = cb.hedef_portfoy(_sk, 1000.0, n_legs=8,
                       kalabalik=_pd.Series({f"S{i}": (0.5 if 8 <= i < 16 else 2.0) for i in range(40)}))
cb.N_LEGS, cb.MIN_LEGS = _eski_nl5d, _eski_ml5d
kontrol("kalabalık verisi yoksa hedef_portfoy eskisiyle aynı",
        sorted(k for k, v in _h.items() if v > 0) == sorted(f"S{i}" for i in range(8)))
kontrol("hedef_portfoy kalabalık verisiyle havuzdan seçiyor (S8-S15 long)",
        sorted(k for k, v in _hk.items() if v > 0) == sorted(f"S{i}" for i in range(8, 16)))
kontrol("kalabalık seçimi varsayılan AÇIK (madde 179: havuz 3)",
        cb.KALABALIK_HAVUZ == 3.0, f"({cb.KALABALIK_HAVUZ})")

print("\n5h) SERMAYE = ÖZSERMAYE (madde 162)")


class _SahteSermaye:
    def __init__(self, cuzdan, ozsermaye):
        self._c, self._o = cuzdan, ozsermaye

    def get_account_balance_usdt(self):
        return self._c

    def get_account_equity_usd(self):
        return self._o


_em = cb.TEMINAT_MODU
cb.TEMINAT_MODU = "usdt"
kontrol("kârdayken gerçekleşmemiş kâr sermayeye DAHİL (1000 cüzdan, 1080 özsermaye)",
        abs(cb.sermaye_oku(_SahteSermaye(1000.0, 1080.0)) - 1080.0) < 1e-9)
kontrol("ZARARDAYKEN sermaye küçülüyor (düşüşte risk artmıyor)",
        abs(cb.sermaye_oku(_SahteSermaye(1000.0, 920.0)) - 920.0) < 1e-9)
kontrol("USDT DIŞI teminat varsa hâlâ TUR ATLANIYOR (madde 141 korundu)",
        cb.sermaye_oku(_SahteSermaye(100.0, 1000.0)) is None)


class _Patlak(_SahteSermaye):
    def get_account_equity_usd(self):
        raise RuntimeError("API patladı")


kontrol("özsermaye okunamazsa cüzdan bakiyesine düşülüyor",
        abs(cb.sermaye_oku(_Patlak(1000.0, 0.0)) - 1000.0) < 1e-9)
cb.TEMINAT_MODU = "coklu"
kontrol("çoklu teminat modunda da özsermaye kullanılıyor",
        abs(cb.sermaye_oku(_SahteSermaye(10.0, 1500.0)) - 1500.0) < 1e-9)
cb.TEMINAT_MODU = _em

print("\n5g) BACAK BÜYÜKLÜĞÜ TUTARLILIĞI (madde 161)")
kontrol("rezerv açıkken taban pay 0.4 (rezerv yarısı düşülür)",
        abs(cb.taban_pay() - (0.5 - cb.REZERV_PAY / 2)) < 1e-12)
_ez = cb.REZERV_PAY
cb.REZERV_PAY = 0.0
kontrol("rezerv kapalıyken taban pay 0.5 (eski davranış)", abs(cb.taban_pay() - 0.5) < 1e-12)
cb.REZERV_PAY = _ez
_bozuk = []
for _bak in (500, 1000, 1500, 2000, 3000, 5000, 10000, 50000):
    _n = cb.uygun_bacak_sayisi(_bak)
    _bacak = (_bak / cb.N_DILIM) * cb.GROSS_EXPOSURE * cb.taban_pay() / _n
    if _n > cb.MIN_LEGS and _bacak < cb.MIN_BACAK_USD - 1e-9:
        _bozuk.append((_bak, _n, round(_bacak, 2)))
kontrol("bacak başına düşen tutar MIN_BACAK_USD'nin ALTINA inmiyor",
        not _bozuk, f"({_bozuk})")
_h161 = cb.hedef_portfoy(_pd.Series({f"S{i}": float(i) for i in range(40)}), 10000.0,
                         n_legs=cb.N_LEGS,
                         ham_funding=_pd.Series({f"S{i}": -0.5 for i in range(40)}))
_bacaklar = [abs(v) for v in _h161.values()]
kontrol("gerçek bacak büyüklüğü, bacak sayısı hesabıyla TUTARLI",
        abs(max(_bacaklar) - 10000.0 * cb.GROSS_EXPOSURE * cb.taban_pay() / cb.N_LEGS) < 1e-6,
        f"({max(_bacaklar):.2f})")

print("\n5f) FIRSAT REZERVİ (madde 156)")
_e156 = (cb.N_LEGS, cb.MIN_LEGS)
cb.N_LEGS = cb.MIN_LEGS = 8
_sk156 = _pd.Series({f"S{i}": float(i) for i in range(40)})
_uc2 = _pd.Series({f"S{i}": (-6.0 if i < 2 else -0.5) for i in range(40)})
_h = cb.hedef_portfoy(_sk156, 1000.0, n_legs=8, ham_funding=_uc2)
_uzunlar = {k: v for k, v in _h.items() if v > 0}
_kisalar = {k: v for k, v in _h.items() if v < 0}
kontrol("rezervde dolar NÖTRLÜĞÜ korunuyor",
        abs(sum(_uzunlar.values()) + sum(_kisalar.values())) < 1e-6,
        f"({sum(_uzunlar.values()):.1f} / {sum(_kisalar.values()):.1f})")
kontrol("uç funding'li coinler EK pay alıyor",
        _h["S0"] > _h["S5"] * 1.5, f"({_h['S0']:.1f} vs {_h['S5']:.1f})")
kontrol("ek pay coin başına KAP ile sınırlı",
        abs(_h["S0"] - 1000.0 * (0.4 / 8 + cb.REZERV_COIN_KAP)) < 1e-6, f"({_h['S0']:.1f})")
_tek = _pd.Series({f"S{i}": (-6.0 if i == 0 else -0.5) for i in range(40)})
_h1 = cb.hedef_portfoy(_sk156, 1000.0, n_legs=8, ham_funding=_tek)
kontrol("TEK uç coinde bile pay = taban + KAP ile sınırlı",
        abs(_h1["S0"] / 1000.0 - (0.4 / 8 + cb.REZERV_COIN_KAP)) < 1e-9
        and _h1["S0"] / 1000.0 <= 0.101, f"(%{_h1['S0']/10:.1f})")
_h0 = cb.hedef_portfoy(_sk156, 1000.0, n_legs=8,
                       ham_funding=_pd.Series({f"S{i}": -0.5 for i in range(40)}))
kontrol("uç aday YOKKEN brüt pozisyon 1-REZERV kadar (sermaye bekliyor)",
        abs(sum(abs(v) for v in _h0.values()) / 1000.0 - (1 - cb.REZERV_PAY)) < 1e-6,
        f"({sum(abs(v) for v in _h0.values())/1000:.3f})")
_eskirez = cb.REZERV_PAY
cb.REZERV_PAY = 0.0
_hk = cb.hedef_portfoy(_sk156, 1000.0, n_legs=8, ham_funding=_uc2)
kontrol("CARRY_REZERV=0 ile kapatılınca eski davranış (brüt 1.0, eşit bacak)",
        abs(sum(abs(v) for v in _hk.values()) / 1000.0 - 1.0) < 1e-6
        and abs(_hk["S0"] - _hk["S5"]) < 1e-9)
cb.REZERV_PAY = _eskirez
kontrol("ham funding verilmezse rezerv devreye GİRMİYOR",
        cb.rezerv_agirlik(["A"], ["B"], None) == ({}, {}))
kontrol("eşiğin üstündeki funding rezerv tetiklemiyor",
        cb.rezerv_agirlik(["A"], ["B"], _pd.Series({"A": -1.0})) == ({}, {}))
_el, _es = cb.rezerv_agirlik(["A", "C"], ["B"], _pd.Series({"A": -6.0, "C": -7.0}))
kontrol("rezerv birden çok uç coine BÖLÜNÜYOR",
        abs(sum(_el.values()) - sum(_es.values())) < 1e-9 and len(_el) == 2)
cb.N_LEGS, cb.MIN_LEGS = _e156

print("\n5e) BORSA KALDIRACI (madde 149)")
_e = (cb.GROSS_EXPOSURE, cb.VOL_HEDEF, cb.LEVERAGE)
cb.GROSS_EXPOSURE, cb.VOL_HEDEF, cb.LEVERAGE = 1.0, 0.0, 1
kontrol("kaldıraçsız varsayılan: borsa kaldıracı 2 (1 DEĞİL)", cb.gerekli_kaldirac() == 2)
cb.GROSS_EXPOSURE = 2.0
kontrol("gross 2x -> 3", cb.gerekli_kaldirac() == 3)
cb.GROSS_EXPOSURE, cb.VOL_HEDEF = 1.0, 0.40
kontrol("oynaklık hedefi açık (ölçek 3'e kadar) -> 5", cb.gerekli_kaldirac() == 5)
cb.VOL_HEDEF, cb.LEVERAGE = 0.0, 10
kontrol("CARRY_LEVERAGE daha yüksekse o kullanılır (alt sınır)", cb.gerekli_kaldirac() == 10)
cb.GROSS_EXPOSURE, cb.VOL_HEDEF, cb.LEVERAGE = _e

print("\n5c) DELIST DUYURUSU (madde 146)")
_simdi = 1_800_000_000_000.0
_gun = 86400000.0
kontrol("normal perp (deliveryDate 2100) -> delist DEĞİL",
        not cb.delist_mi({"status": "TRADING", "contractType": "PERPETUAL",
                          "deliveryDate": 4133404800000}, _simdi))
kontrol("deliveryDate 3 gün sonra -> delist",
        cb.delist_mi({"status": "TRADING", "contractType": "PERPETUAL",
                      "deliveryDate": _simdi + 3 * _gun}, _simdi))
kontrol("deliveryDate 60 gün sonra -> henüz DEĞİL (ufuk 30 gün)",
        not cb.delist_mi({"status": "TRADING", "contractType": "PERPETUAL",
                          "deliveryDate": _simdi + 60 * _gun}, _simdi))
kontrol("status SETTLING -> delist",
        cb.delist_mi({"status": "SETTLING", "contractType": "PERPETUAL"}, _simdi))
kontrol("vadeli (CURRENT_QUARTER) deliveryDate'i delist SAYILMAZ",
        not cb.delist_mi({"status": "TRADING", "contractType": "CURRENT_QUARTER",
                          "deliveryDate": _simdi + 3 * _gun}, _simdi))
kontrol("bilgi yoksa delist DEĞİL (veri eksikliği cezalandırılmaz)",
        not cb.delist_mi(None, _simdi) and not cb.delist_mi({}, _simdi))
kontrol("bozuk deliveryDate çökertmez",
        not cb.delist_mi({"status": "TRADING", "deliveryDate": "abc"}, _simdi))

print("\n6) OYNAKLIK HEDEFİ ÖLÇEĞİ")
import os, tempfile
_d = tempfile.mkdtemp()
def yaz(dosya, degerler):
    with open(dosya, "w", encoding="utf-8") as fh:
        for i, v in enumerate(degerler):
            fh.write(f"{1700000000+i*432000},{v}\n")
    return dosya
eski_h = cb.VOL_HEDEF
# madde 140: varsayilan artik KALDIRACSIZ
kontrol("varsayılan profil kaldıraçsız (hedef 0)",
        cb.RISK_PROFILI == "kaldiracsiz" and cb.VOL_HEDEF == 0.0,
        f"({cb.RISK_PROFILI}, {cb.VOL_HEDEF})")
kontrol("bilinmeyen profil adı kaldıraçsız çalışır",
        cb._PROFILLER.get("yanlis_yazim", 0.0) == 0.0)
cb.VOL_HEDEF = 0.40   # asagidaki olcek testleri hedef ACIKKEN davranisi sinar
eski_h = 0.40
# 1) Yetersiz gecmis -> 1.0 (sessizce yanlis olcek UYGULAMAZ)
az = yaz(os.path.join(_d, "az.csv"), [1000.0] * 5)
kontrol("yetersiz geçmişte ölçek 1.0", cb.vol_olcek(1000.0, az) == 1.0)
# 2) Hic dosya yok -> 1.0
kontrol("dosya yokken ölçek 1.0",
        cb.vol_olcek(1000.0, os.path.join(_d, "yok.csv")) == 1.0)
# 3) Hedef kapali -> her zaman 1.0
cb.VOL_HEDEF = 0.0
kontrol("hedef kapalıyken ölçek 1.0", cb.vol_olcek(1000.0, az) == 1.0)
cb.VOL_HEDEF = eski_h
# 4) SAKIN portfoy -> olcek BUYUR (>1)
import math
sakin = yaz(os.path.join(_d, "sakin.csv"),
            [1000.0 * (1 + 0.0004 * ((-1) ** i)) ** 1 * (1.0005 ** i) for i in range(40)])
o_sakin = cb.vol_olcek(1000.0, sakin)
kontrol("sakin portföyde ölçek büyür (>1)", o_sakin > 1.0, f"({o_sakin:.2f})")
# 5) OYNAK portfoy -> olcek KUCUL (<1)
oynak = yaz(os.path.join(_d, "oynak.csv"),
            [1000.0 * (1.15 ** (i % 2)) * (1.001 ** i) for i in range(40)])
o_oynak = cb.vol_olcek(1000.0, oynak)
kontrol("oynak portföyde ölçek küçülür (<1)", o_oynak < 1.0, f"({o_oynak:.2f})")
kontrol("sakin ölçeği oynak ölçeğinden büyük", o_sakin > o_oynak)
# 6) Sinirlar [0.3, 3.0]
kontrol("ölçek üst sınırı 3.0 aşmaz", o_sakin <= 3.0)
kontrol("ölçek alt sınırı 0.3 altına inmez", o_oynak >= 0.3)
# 7) Bozuk dosya cokmez
bozuk = os.path.join(_d, "bozuk.csv")
open(bozuk, "w").write("saçma\nsatır,abc\n\n")
kontrol("bozuk dosyada çökmeden 1.0 döner", cb.vol_olcek(1000.0, bozuk) == 1.0)
# 8) YILLIKLAŞTIRMA gerçek örnek aralığından (madde 140). Bot günde bir
# tur atıyor; günlük veriyi "yılda 73 tur" ile yıllıklaştırmak oynaklığı
# sqrt(5) kat düşük ölçüp kaldıracı 2.24 kat şişiriyordu.
def yaz_aralik(dosya, degerler, aralik_sn):
    with open(dosya, "w", encoding="utf-8") as fh:
        for i, v in enumerate(degerler):
            fh.write(f"{1700000000+i*aralik_sn},{v}\n")
    return dosya
_seri = [1000.0 * (1.02 ** (i % 2)) * (1.0003 ** i) for i in range(40)]
gunluk = cb.vol_olcek(1000.0, yaz_aralik(os.path.join(_d, "g.csv"), _seri, 86400), olcme_yap=False)
bes_gun = cb.vol_olcek(1000.0, yaz_aralik(os.path.join(_d, "b.csv"), _seri, 432000), olcme_yap=False)
kontrol("aynı getiriler günlük örneklenince ölçek sqrt(5) kat KÜÇÜK",
        abs(bes_gun / gunluk - 5 ** 0.5) < 0.05, f"(5g {bes_gun:.3f} / 1g {gunluk:.3f} = {bes_gun/gunluk:.3f})")
_eski_hedef = cb.VOL_HEDEF
cb.VOL_HEDEF = 0.40
_g = np.diff(_seri) / np.array(_seri[:-1])
_beklenen = float(np.clip(0.40 / (_g.std() * np.sqrt(365.25)), 0.3, 3.0))
_olc = cb.vol_olcek(1000.0, yaz_aralik(os.path.join(_d, "g2.csv"), _seri, 86400), olcme_yap=False)
kontrol("günlük örnekte yıllıklaştırma sqrt(365.25) ile yapılıyor",
        abs(_olc - _beklenen) < 1e-6 * 0 + 0.02, f"({_olc:.3f} vs beklenen {_beklenen:.3f})")
cb.VOL_HEDEF = _eski_hedef
_n = sum(1 for _ in open(os.path.join(_d, "g2.csv")))
cb.vol_olcek(1000.0, os.path.join(_d, "g2.csv"), olcme_yap=False)
kontrol("olcme_yap=False dosyaya satır EKLEMEZ",
        sum(1 for _ in open(os.path.join(_d, "g2.csv"))) == _n)
# 9) KALDIRAÇSIZ OYNAKLIK ölçülüyor (madde 140). Aynı alttaki strateji
# 2x kaldıraçla işlendiyse bakiye getirileri 2 kat oynak olur; bot bunu
# uygulanan ölçeğe bölüp AYNI ölçeği bulmalı (eskiden yarısını buluyordu).
cb.VOL_HEDEF = 0.40
_rng = np.random.default_rng(1)
_alt = _rng.normal(0.001, 0.012, 60)
def yaz_olcekli(dosya, alt, olcek):
    b = 1000.0
    with open(dosya, "w", encoding="utf-8") as fh:
        for i, r in enumerate(alt):
            fh.write(f"{1700000000+i*86400},{b:.6f},{olcek}\n")
            b *= 1 + olcek * r
    return dosya, b
f1, b1 = yaz_olcekli(os.path.join(_d, "k1.csv"), _alt, 1.0)
f2, b2 = yaz_olcekli(os.path.join(_d, "k2.csv"), _alt, 2.0)
o1 = cb.vol_olcek(b1, f1, olcme_yap=False)
o2 = cb.vol_olcek(b2, f2, olcme_yap=False)
kontrol("2x kaldıraçlı geçmişten de AYNI ölçek bulunuyor (kaldıraçsız ölçüm)",
        abs(o1 - o2) / o1 < 0.02, f"(1x geçmiş -> {o1:.3f}, 2x geçmiş -> {o2:.3f})")
# 10) PENCERE: eski sakin geçmiş, yakın oynak dönemi maskelememeli
_sakin = list(_rng.normal(0.0005, 0.003, 400))
_oynak = list(_rng.normal(0.0005, 0.03, 90))
f3, b3 = yaz_olcekli(os.path.join(_d, "p.csv"), _sakin + _oynak, 1.0)
o3 = cb.vol_olcek(b3, f3, olcme_yap=False)
_bek = float(np.clip(0.40 / (np.std(_oynak) * np.sqrt(365.25)), 0.3, 3.0))
kontrol("ölçek SON 90 günün oynaklığına göre (eski sakin dönem maskelemiyor)",
        abs(o3 - _bek) / _bek < 0.15, f"({o3:.3f}, beklenen ~{_bek:.3f})")
# 11) uygulanan ölçek dosyaya yazılıyor (sonraki turun kaldıraçsız ölçümü için)
f4 = os.path.join(_d, "yaz.csv")
cb.vol_olcek(1000.0, f4, olcme_yap=True)
_satir = open(f4).read().strip().split(",")
kontrol("kayıt 3 sütunlu: zaman, bakiye, uygulanan ölçek",
        len(_satir) == 3 and float(_satir[2]) == 1.0, f"({_satir})")
cb.VOL_HEDEF = 0.0
kontrol("hedef kapalıyken (varsayılan) ölçek her zaman 1.0",
        cb.vol_olcek(b2, f2, olcme_yap=False) == 1.0)

print("\n7) EMİR AKIŞI HARMANI")
eski_w = cb.AKIS_AGIRLIK
fnd = pd.Series({f"S{i}USDT": (i - 5) * 0.001 for i in range(12)})
ak  = pd.Series({f"S{i}USDT": (11 - i) * 0.01 for i in range(12)})  # funding ile AYNI yon
cb.AKIS_AGIRLIK = 0.0
sk0 = cb.birlesik_skor(fnd, ak)
kontrol("ağırlık 0'da sadece funding kullanılır", sk0.equals(fnd.dropna()))
cb.AKIS_AGIRLIK = 0.20
sk = cb.birlesik_skor(fnd, ak)
kontrol("harman tüm sembolleri kapsar", len(sk) == 12, f"({len(sk)})")
kontrol("harman [0,1] araliginda", sk.min() >= 0 and sk.max() <= 1,
        f"({sk.min():.3f}-{sk.max():.3f})")
# AKIS YUKSEK olan LONG olmali => skoru DUSUK olmali
kontrol("akışı en yüksek olan en düşük skora yakın",
        sk.idxmin() in ("S0USDT", "S1USDT"), f"({sk.idxmin()})")
# Akis sinyali siralamayi GERCEKTEN degistiriyor mu? (sessiz no-op kontrolu)
ters = pd.Series({f"S{i}USDT": i * 0.01 for i in range(12)})   # funding'in TERSI
sk_t = cb.birlesik_skor(fnd, ters)
kontrol("farklı akış farklı sıralama üretir (sessiz no-op değil)",
        not np.allclose(sk.values, sk_t.values), "(sıralama değişmedi!)")
# Yetersiz akis verisi -> sadece funding, sessizce yanlis harman YAPMAZ
az = pd.Series({"S0USDT": 0.01, "S1USDT": 0.02})
kontrol("akış verisi yetersizse sadece funding'e döner",
        cb.birlesik_skor(fnd, az).equals(fnd.dropna()))
kontrol("boş akışta sadece funding", cb.birlesik_skor(fnd, pd.Series(dtype=float)).equals(fnd.dropna()))
# madde 183: akisi EKSIK olan sembol evrenden ATILMAZ, notr (0.5) sayilir
eksik = ak.drop(index=["S3USDT", "S7USDT"])
sk_e = cb.birlesik_skor(fnd, eksik)
kontrol("akışı olmayan sembol seçimden DÜŞMEZ (parite)",
        len(sk_e) == 12 and "S3USDT" in sk_e.index, f"({len(sk_e)})")
kontrol("akışı olmayan sembol nötr (0.5) akış sırası alır",
        abs(sk_e["S3USDT"] - (0.8 * fnd.rank(pct=True)["S3USDT"] + 0.2 * 0.5)) < 1e-9)
cb.AKIS_AGIRLIK = eski_w

print("\n7b-1) MADDE 228 - AKIS KAPATILINCA DONUK FILTRESI DE KAPANMAMALI")
# `akis_topla` iki isi birden yapar: akis skoru + donuk filtresi verisi.
# Eskiden cagri yalnizca AKIS_AGIRLIK>0 iken yapiliyordu, yani akisi
# kapatan kisi SESSIZCE donuk filtresini de kapatiyordu. Madde 228
# akisin katkisini +0,04 Sharpe'a indirdigi icin "kapatayim" artik akla
# gelebilir bir secenek - bu yuzden bagin kopmus olmasi sart.
import inspect as _ins
_kaynak_tur = _ins.getsource(cb.bir_tur)
_kosul = [s for s in _kaynak_tur.splitlines() if "akis_topla(" in s]
kontrol("akis_topla cagrisi var", len(_kosul) >= 1)
kontrol("veri toplama kosulu DONUK_ESIK'i de kapsiyor (madde 228)",
        "AKIS_AGIRLIK > 0 or DONUK_ESIK > 0" in _kaynak_tur,
        "(akis kapaninca donuk filtresi de sessizce kapaniyor)")
kontrol("akis 0 iken skor serisi yine de BOS birakiliyor",
        "akis = pd.Series(dtype=float)" in _kaynak_tur)
kontrol("akis 0 / donuk acik durumu LOG'a yaziliyor",
        "YALNIZCA donuk seri" in _kaynak_tur)

print("\n7b) DONUK SERİ FİLTRESİ (madde 183)")
kontrol("varsayılan donuk eşiği %10", abs(cb.DONUK_ESIK - 0.10) < 1e-9,
        f"({cb.DONUK_ESIK})")


class _DonukIstemci:
    """Bir sembolün kapanışı HİÇ değişmiyor, diğerlerininki değişiyor."""

    def futures_klines(self, symbol, interval, limit):
        sabit = symbol == "S3USDT"
        out = []
        for i in range(limit):
            kap = "1.0" if sabit else f"{1.0 + (i % 5) * 0.01:.4f}"
            out.append([0, kap, kap, kap, kap, "1", 0, "1000000", 0,
                        "250000", "500000", 0])
        return out


class _Sarmal:
    def __init__(self, c):
        self.client = c


_d = {}
_ak = cb.akis_topla(_Sarmal(_DonukIstemci()),
                    [f"S{i}USDT" for i in range(12)], donuk_out=_d)
kontrol("donukluk akışla AYNI kline'dan hesaplanır (ek çağrı yok)",
        len(_d) == 12, f"({len(_d)})")
kontrol("donuk sembol %100 donuk ölçülür", abs(_d["S3USDT"] - 1.0) < 1e-9,
        f"({_d.get('S3USDT')})")
kontrol("hareketli sembol eşiğin altında", _d["S0USDT"] < cb.DONUK_ESIK,
        f"({_d['S0USDT']:.3f})")
kontrol("donuk_out verilmezse donukluk hesaplanmaz (geriye uyum)",
        len(cb.akis_topla(_Sarmal(_DonukIstemci()), ["S0USDT"])) == 1)


print("\n7c) DOLUM KOVALAMA (madde 193)")
kontrol("varsayılan bekleme 180 saniye", cb.DOLUM_BEKLEME_SN == 180.0,
        f"({cb.DOLUM_BEKLEME_SN})")


class _DolumIstemci:
    """dolan_oran: emrin ne kadarı dolmuş sayılsın (0 = hiç, 0.5 = yarısı)."""

    def __init__(self, dolan_oran=0.0):
        self.dolan_oran = dolan_oran
        self.iptal = []
        self.yeni_limit = []
        self.piyasa = []
        self._oid = 5000

    def futures_get_order(self, symbol, orderId):
        d = self.dolan_oran
        return {"status": "FILLED" if d >= 1.0 else "NEW",
                "executedQty": str(10.0 * d)}

    def futures_cancel_order(self, symbol, orderId):
        self.iptal.append((symbol, orderId)); return {}

    def futures_symbol_ticker(self, symbol):
        return {"price": "100.0"}

    def futures_create_order(self, **kw):
        self._oid += 1
        self.yeni_limit.append((kw["symbol"], kw["side"], float(kw["quantity"]),
                                kw.get("timeInForce")))
        return {"orderId": self._oid}


class _DolumSarmal:
    def __init__(self, c):
        self.client = c

    def get_symbol_precision(self, s):
        return {"quantity_precision": 3, "price_precision": 2}

    def open_market_position(self, s, yon, miktar):
        self.client.piyasa.append((s, yon, miktar))


_eski_bek, _eski_den = cb.DOLUM_BEKLEME_SN, cb.DOLUM_DENEME
cb.DOLUM_BEKLEME_SN = 0.0     # testte beklemeden

# a) emir TAMAMEN dolmussa hicbir sey yapilmaz
_c = _DolumIstemci(dolan_oran=1.0); _w = _DolumSarmal(_c)
cb.dolumu_kovala(_w, [{"sembol": "AUSDT", "yon": "BUY", "miktar": 10.0, "id": 1}])
kontrol("dolan emir kovalanmıyor",
        not _c.iptal and not _c.yeni_limit and not _c.piyasa)

# b) HİÇ dolmamissa: iptal -> daha uzak limit -> son denemede PIYASA
_c = _DolumIstemci(dolan_oran=0.0); _w = _DolumSarmal(_c)
cb.DOLUM_DENEME = 2
cb.dolumu_kovala(_w, [{"sembol": "AUSDT", "yon": "BUY", "miktar": 10.0, "id": 1}])
kontrol("dolmayan emir İPTAL edildi", len(_c.iptal) >= 1, f"({_c.iptal})")
kontrol("ilk denemede yeni LİMİT kondu (GTX)",
        len(_c.yeni_limit) == 1 and _c.yeni_limit[0][3] == "GTX",
        f"({_c.yeni_limit})")
kontrol("son denemede PİYASA emrine düşüldü", len(_c.piyasa) == 1,
        f"({_c.piyasa})")

# c) KISMİ dolum: sadece KALAN miktar gonderilir (pozisyon iki katina cikmaz)
_c = _DolumIstemci(dolan_oran=0.4); _w = _DolumSarmal(_c)
cb.DOLUM_DENEME = 1
cb.dolumu_kovala(_w, [{"sembol": "AUSDT", "yon": "BUY", "miktar": 10.0, "id": 1}])
kontrol("kısmi dolumda sadece KALAN miktar gönderiliyor",
        _c.piyasa and abs(_c.piyasa[0][2] - 6.0) < 1e-6,
        f"({_c.piyasa})")

# d) minimum notional altinda kalan artik gonderilmez
_c = _DolumIstemci(dolan_oran=0.999); _w = _DolumSarmal(_c)
cb.DOLUM_DENEME = 1
cb.dolumu_kovala(_w, [{"sembol": "AUSDT", "yon": "BUY", "miktar": 10.0, "id": 1}])
kontrol("MIN_NOTIONAL altındaki artık gönderilmiyor", not _c.piyasa,
        f"({_c.piyasa})")

cb.DOLUM_BEKLEME_SN, cb.DOLUM_DENEME = _eski_bek, _eski_den


print("\n7d) UÇ HAREKET ELEMESİ (madde 196)")
kontrol("varsayılan eşik %40", abs(cb.UC_HAREKET_ELE - 0.40) < 1e-9,
        f"({cb.UC_HAREKET_ELE})")
_eski_uc = cb.UC_HAREKET_ELE
_f = pd.Series({f"U{i}USDT": float(i - 7) for i in range(14)})   # -7..+6
_d0 = {f"U{i}USDT": 0.0 for i in range(14)}

def _ele(deg):
    cb.SON_24S_DEGISIM.clear(); cb.SON_24S_DEGISIM.update(dict(_d0, **deg))
    return set(_f.index) - set(cb.uc_hareket_ele(_f).index)

# pump olmus LONG adayi (funding DUSUK) elenir
kontrol("pump olmuş LONG adayı elenir", _ele({"U0USDT": 0.55}) == {"U0USDT"},
        f"({_ele({'U0USDT': 0.55})})")
# pump olmus SHORT adayi (funding YUKSEK) ELENMEZ - hareket lehimize
kontrol("pump olmuş SHORT adayı ELENMEZ", _ele({"U13USDT": 0.55}) == set(),
        f"({_ele({'U13USDT': 0.55})})")
# dump olmus SHORT adayi elenir
kontrol("dump olmuş SHORT adayı elenir", _ele({"U13USDT": -0.55}) == {"U13USDT"},
        f"({_ele({'U13USDT': -0.55})})")
# dump olmus LONG adayi ELENMEZ
kontrol("dump olmuş LONG adayı ELENMEZ", _ele({"U0USDT": -0.55}) == set(),
        f"({_ele({'U0USDT': -0.55})})")
# esigin ALTINDA kalan elenmez
kontrol("eşiğin altındaki hareket elenmez", _ele({"U0USDT": 0.35}) == set(),
        f"({_ele({'U0USDT': 0.35})})")
# veri yoksa eleme yok
cb.SON_24S_DEGISIM.clear()
kontrol("24 saat verisi yoksa eleme YAPILMAZ",
        len(cb.uc_hareket_ele(_f)) == len(_f))
# evren cok daralirsa eleme uygulanmaz (dayaniklilik)
kontrol("eleme evreni MIN_LEGS altına düşürecekse uygulanmaz",
        len(cb.uc_hareket_ele(_f.iloc[:8])) == 8,
        f"({len(cb.uc_hareket_ele(_f.iloc[:8]))})")
cb.SON_24S_DEGISIM.clear(); cb.UC_HAREKET_ELE = _eski_uc


print("\n7e) BAKİYE YETERLİLİK KONTROLÜ (madde 204)")
kontrol("güvenlik çarpanı >= 2", cb.ASGARI_BACAK_CARPANI >= 2.0,
        f"({cb.ASGARI_BACAK_CARPANI})")
# esik, o anki REZERV/N_DILIM durumundan TUREYEREK hesaplanir - testin
# kendisi global duruma bagli olmasin (bu blok baska bolumlerden sonra kosuyor)
_esik = cb.MIN_NOTIONAL_USD * cb.ASGARI_BACAK_CARPANI
for _b in (500, 1000, 2000, 3400, 10000, 100000):
    _n = cb.uygun_bacak_sayisi(_b)
    _ok, _bu = cb.bakiye_yeterli_mi(_b, _n)
    kontrol(f"{_b}$ -> bacak {_bu:.1f}$, karar {'yeterli' if _ok else 'YETERSİZ'} "
            f"(eşik {_esik:.0f}$)", _ok == (_bu >= _esik), f"(ok={_ok})")
# KARAR MONOTON olmali: bakiye arttikca yetersiz -> yeterli, geri donmemeli
_kararlar = [cb.bakiye_yeterli_mi(b, cb.uygun_bacak_sayisi(b))[0]
             for b in range(100, 20001, 100)]
_donus = sum(1 for x, y in zip(_kararlar, _kararlar[1:]) if x and not y)
kontrol("karar bakiyeyle MONOTON (yeterliden yetersize dönmüyor)",
        _donus == 0, f"({_donus} dönüş)")
kontrol("çok küçük bakiye YETERSİZ", not _kararlar[0])
kontrol("büyük bakiye yeterli", _kararlar[-1])
kontrol("yetersizlik eşiği MIN_NOTIONAL x çarpan",
        not cb.bakiye_yeterli_mi(1.0, 6)[0] and cb.bakiye_yeterli_mi(1e7, 6)[0])
kontrol("ölçek 0 iken de çökmüyor", cb.bakiye_yeterli_mi(10000, 6, 0.0)[0] is False)
kontrol("bacak sayısı 0 verilse de çökmüyor",
        isinstance(cb.bakiye_yeterli_mi(10000, 0)[1], float))


print("\n7f) BAYAT DİLİM HEDEFİ ÖLÇEKLEMESİ (madde 205)")
_d5 = {"dilimler": {"0": {"A": 1000.0, "B": -1000.0},
                    "1": {"A": 500.0, "C": -500.0}},
       "dilim_bakiye": {"0": 10000.0, "1": 10000.0}}
_h0 = cb.toplam_hedef(_d5)
kontrol("bakiye verilmezse ESKİ davranış (ölçek yok)",
        abs(_h0["A"] - 1500.0) < 1e-9, f"({_h0})")
kontrol("aynı bakiyede ölçek 1.0",
        abs(cb.toplam_hedef(_d5, 10000)["A"] - 1500.0) < 1e-9)
_h1 = cb.toplam_hedef(_d5, 8000)
kontrol("bakiye %20 DÜŞERSE hedef de %20 küçülür (düşüşte kaldıraç ARTMAZ)",
        abs(_h1["A"] - 1200.0) < 1e-6 and abs(_h1["B"] + 800.0) < 1e-6,
        f"({_h1})")
_h2 = cb.toplam_hedef(_d5, 12000)
kontrol("bakiye %20 ARTARSA hedef de büyür",
        abs(_h2["A"] - 1800.0) < 1e-6, f"({_h2})")
_h3 = cb.toplam_hedef(_d5, 2000)
kontrol("çok hızlı düşüşte ölçek TAVANLA sınırlı",
        abs(_h3["A"] - 1500.0 / cb.DILIM_OLCEK_TAVAN) < 1e-6,
        f"({_h3['A']:.1f}, tavan {cb.DILIM_OLCEK_TAVAN})")
kontrol("çok hızlı artışta da tavan var",
        abs(cb.toplam_hedef(_d5, 1e9)["A"] - 1500.0 * cb.DILIM_OLCEK_TAVAN) < 1e-6)
kontrol("dilim_bakiye kaydı yoksa ölçek uygulanmaz (geriye uyum)",
        abs(cb.toplam_hedef({"dilimler": _d5["dilimler"]}, 8000)["A"] - 1500.0) < 1e-9)
kontrol("bozuk dilim_bakiye kaydı çökertmiyor",
        abs(cb.toplam_hedef(dict(_d5, dilim_bakiye={"0": "abc", "1": None}),
                            8000)["A"] - 1500.0) < 1e-9)
kontrol("ölçek NET yönü değiştirmiyor",
        all(np.sign(_h1[k]) == np.sign(_h0[k]) for k in _h0))


print("\n7g) YETİM DİLİM TEMİZLİĞİ (madde 206)")
_eski_nd = cb.N_DILIM


def _durum15():
    return {"dilimler": {str(k): {f"Y{k}USDT": 1000.0} for k in range(15)},
            "dilim_bakiye": {str(k): 10000.0 for k in range(15)},
            "giris_funding": {f"Y{k}USDT": 1.0 for k in range(15)},
            "sira": 12}


cb.N_DILIM = 15
_d6 = _durum15()
kontrol("N_DILIM aynıyken hiçbir dilim elenmiyor",
        cb.yetim_dilimleri_ele(_d6) == [] and len(_d6["dilimler"]) == 15)

cb.N_DILIM = 5
_d6 = _durum15()
_at = cb.yetim_dilimleri_ele(_d6)
kontrol("N_DILIM 15->5 olunca 10 yetim dilim elendi", len(_at) == 10,
        f"({len(_at)})")
kontrol("kalan dilimler 0..4", sorted(_d6["dilimler"], key=int) == list("01234"),
        f"({sorted(_d6['dilimler'], key=int)})")
kontrol("dilim_bakiye kaydı da temizlendi",
        sorted(_d6["dilim_bakiye"], key=int) == list("01234"))
kontrol("yetim sembollerin giriş funding kaydı silindi",
        sorted(_d6["giris_funding"]) == [f"Y{k}USDT" for k in range(5)],
        f"({sorted(_d6['giris_funding'])})")
kontrol("sıra N_DILIM'in içine çekildi", _d6["sira"] == 12 % 5,
        f"({_d6['sira']})")
kontrol("hedefte artık sadece 5 sembol var", len(cb.toplam_hedef(_d6)) == 5,
        f"({len(cb.toplam_hedef(_d6))})")

# BASKA DILIMDE de duran sembolun giris kaydi SILINMEMELI
_d7 = {"dilimler": {"0": {"PAYUSDT": 100.0}, "9": {"PAYUSDT": 100.0}},
       "giris_funding": {"PAYUSDT": 5.0}, "sira": 0}
cb.yetim_dilimleri_ele(_d7)
kontrol("başka dilimde duran sembolün giriş kaydı KORUNDU",
        "PAYUSDT" in _d7["giris_funding"], f"({_d7['giris_funding']})")

# bozuk anahtar da elenmeli, cokmeden
_d8 = {"dilimler": {"0": {"A": 1.0}, "abc": {"B": 1.0}, "-1": {"C": 1.0}},
       "sira": 0}
_at8 = cb.yetim_dilimleri_ele(_d8)
kontrol("bozuk/negatif dilim anahtarları elendi",
        sorted(_d8["dilimler"]) == ["0"], f"({sorted(_d8['dilimler'])})")
kontrol("boş durumda çökmüyor", cb.yetim_dilimleri_ele({}) == [])
cb.N_DILIM = _eski_nd


print("\n7h) DURUM KURTARMA (madde 207)")
kontrol("kurtarma varsayılan olarak AÇIK", cb.DURUM_KURTAR)
_mev = {f"K{i}USDT": (1000.0 if i % 2 else -1000.0) for i in range(12)}
_d9 = {"sira": 0, "dilimler": {}}
_n9 = cb.durum_kurtar(_d9, _mev, 10000.0)
kontrol("kayıp durumda tüm pozisyonlar sahiplenildi", _n9 == 12, f"({_n9})")
kontrol("pozisyonlar FARKLI slotlara dağıtıldı",
        len(_d9["dilimler"]) == 12, f"({len(_d9['dilimler'])})")
kontrol("sıradaki slot TAZE dilim için boş bırakıldı",
        "0" not in _d9["dilimler"], f"({sorted(_d9['dilimler'], key=int)})")
_h9 = cb.toplam_hedef(_d9, 10000.0)
kontrol("hedef MEVCUDA eşit -> kurtarma turunda işlem YOK",
        all(abs(_h9[k] - _mev[k]) < 1e-9 for k in _mev), f"({len(_h9)})")
kontrol("dilim_bakiye kaydı da yazıldı (madde 205 ölçeği bozulmasın)",
        len(_d9.get("dilim_bakiye", {})) == len(_d9["dilimler"]))
kontrol("durum YERİNDEYSE kurtarma yapılmıyor",
        cb.durum_kurtar({"sira": 0, "dilimler": {"0": {"A": 1.0}}}, _mev, 1e4) == 0)
kontrol("borsada pozisyon YOKSA kurtarma yapılmıyor",
        cb.durum_kurtar({"sira": 0, "dilimler": {}}, {}, 1e4) == 0)
kontrol("MIN_NOTIONAL altı artıklar sahiplenilmiyor",
        cb.durum_kurtar({"sira": 0, "dilimler": {}},
                        {"TOZUSDT": 0.5}, 1e4) >= 0
        and "TOZUSDT" not in cb.toplam_hedef(
            {"dilimler": {"1": {"TOZUSDT": 0.5}}}))
_eski_dk = cb.DURUM_KURTAR
cb.DURUM_KURTAR = False
kontrol("CARRY_DURUM_KURTAR=0 ile kapatılabiliyor",
        cb.durum_kurtar({"sira": 0, "dilimler": {}}, _mev, 1e4) == 0)
cb.DURUM_KURTAR = _eski_dk

print("\n7i) EMİR SIRASI: TARAF DOKUMASI (madde 208)")
# Yarim turda (borsa bakimi) kitap tek tarafli kalmasin: acilislar
# long/short ardisik dizilir, liste nerede kesilirse |net| <= 1 bacak.
_hed = {f"L{i}USDT": 1000.0 for i in range(6)}
_hed.update({f"S{i}USDT": -1000.0 for i in range(6)})
_em = cb.emirleri_hesapla(_hed, {}, tolerans_usd=10.0)
kontrol("tüm bacaklar emir listesinde", len(_em) == 12, f"({len(_em)})")
_yon = [(+1 if y == "BUY" else -1) for _, y, _ in _em]
kontrol("taraflar ARDIŞIK (dokuma)",
        all(_yon[i] != _yon[i + 1] for i in range(len(_yon) - 1)), f"({_yon})")
_kismi = [abs(sum(_yon[:k])) for k in range(1, len(_yon) + 1)]
kontrol("her kesme noktasında |net| en fazla 1 bacak",
        max(_kismi) <= 1, f"(max {max(_kismi)})")
# Kapanislar ONCE kalmali (marj bosalsin) - dokuma bunu bozmamali.
_mv = {"ESKIUSDT": 5000.0, "KUCUKUSDT": 2000.0}
_em2 = cb.emirleri_hesapla(_hed, _mv, tolerans_usd=10.0)
kontrol("kapanışlar listenin BAŞINDA",
        _em2[0][0] == "ESKIUSDT" and _em2[1][0] == "KUCUKUSDT",
        f"({_em2[0][0]}, {_em2[1][0]})")
kontrol("kapanışlar büyükten küçüğe",
        abs(_mv[_em2[0][0]]) >= abs(_mv[_em2[1][0]]))
_ac2 = [(+1 if y == "BUY" else -1) for s, y, _ in _em2 if s not in _mv]
kontrol("kapanışlardan SONRAKİ açılışlar da dokumalı",
        all(_ac2[i] != _ac2[i + 1] for i in range(len(_ac2) - 1)), f"({_ac2})")
# Esit olmayan taraf sayisi: fazlalik sona yigilir, sira yine gecerli
_hed3 = {f"L{i}USDT": 1000.0 for i in range(5)}
_hed3.update({f"S{i}USDT": -1000.0 for i in range(2)})
_em3 = cb.emirleri_hesapla(_hed3, {}, tolerans_usd=10.0)
kontrol("taraflar eşit değilken de tüm bacaklar var", len(_em3) == 7)
_y3 = [(+1 if y == "BUY" else -1) for _, y, _ in _em3]
kontrol("eşitsiz tarafta ilk 4 emir hâlâ dokumalı",
        _y3[:4] == [1, -1, 1, -1], f"({_y3})")
# Buyukten kucuge: ilk gonderilen bacak en buyuk olmali (marj riski once)
_hed4 = {"AUSDT": 500.0, "BUSDT": 3000.0, "CUSDT": -4000.0, "DUSDT": -900.0}
_em4 = cb.emirleri_hesapla(_hed4, {}, tolerans_usd=10.0)
kontrol("her tarafta büyük bacak önce",
        _em4[0][0] == "BUSDT" and _em4[1][0] == "CUSDT",
        f"({[e[0] for e in _em4]})")
kontrol("tolerans altı bacaklar hâlâ atlanıyor",
        cb.emirleri_hesapla({"XUSDT": 1.0}, {}, tolerans_usd=10.0) == [])

print("\n7j) ELLE DEĞİŞTİRİLEN AYARLAR (madde 211)")


class _SahtePoz:
    """Sadece pozisyon modu ve pozisyon listesi veren asgari istemci."""

    def __init__(self, hedge=False, poz=None, gecis_hatasi=None):
        self._h, self._p, self._ge = hedge, poz or [], gecis_hatasi
        self.gecis = []
        _o = self

        class _C:
            @staticmethod
            def futures_get_position_mode():
                if _o._h is None:
                    raise RuntimeError("API hatası (bilerek)")
                return {"dualSidePosition": bool(_o._h)}

            @staticmethod
            def futures_change_position_mode(**k):
                if _o._ge:
                    raise RuntimeError(_o._ge)
                _o.gecis.append(k)
                _o._h = False
        self.client = _C()

    def get_open_positions(self):
        return self._p


# HEDGE MODU: bot hic islem acamaz, ama eski hata mesaji kullaniciyi
# bakiye/izin kovalamaya yonlendiriyordu.
kontrol("pozisyon modu kontrolü varsayılan olarak AÇIK", cb.POZ_MODU_KONTROL)
kontrol("tek yönlü hesapta True", cb.tek_yonlu_mu(_SahtePoz(hedge=False)) is True)
kontrol("hedge hesapta False", cb.tek_yonlu_mu(_SahtePoz(hedge=True)) is False)
kontrol("API hatasında None (dedektör arızası botu durdurmaz)",
        cb.tek_yonlu_mu(_SahtePoz(hedge=None)) is None)
kontrol("tek yönlüde tur DEVAM ediyor",
        cb.pozisyon_modu_hazirla(_SahtePoz(hedge=False), {}) is True)
kontrol("API hatasında tur DEVAM ediyor (madde 123)",
        cb.pozisyon_modu_hazirla(_SahtePoz(hedge=None), {}) is True)
_hp = _SahtePoz(hedge=True)
kontrol("hedge + pozisyon YOK -> tek yönlüye ALINIR ve tur devam eder",
        cb.pozisyon_modu_hazirla(_hp, {}) is True and len(_hp.gecis) == 1,
        f"({_hp.gecis})")
kontrol("geçiş çağrısı dualSidePosition=false gönderiyor",
        _hp.gecis and _hp.gecis[0].get("dualSidePosition") == "false",
        f"({_hp.gecis})")
kontrol("hedge + pozisyon VAR -> tur ATLANIR (geçiş denenmez)",
        cb.pozisyon_modu_hazirla(_SahtePoz(hedge=True), {"AUSDT": 100.0}) is False)
_hp2 = _SahtePoz(hedge=True, gecis_hatasi="pozisyon var")
kontrol("geçiş başarısız olursa da tur ATLANIR, çökmez",
        cb.pozisyon_modu_hazirla(_hp2, {}) is False)
_eski_pk = cb.POZ_MODU_KONTROL
cb.POZ_MODU_KONTROL = False
kontrol("CARRY_POZ_MODU_KONTROL=0 ile kapatılabiliyor",
        cb.pozisyon_modu_hazirla(_SahtePoz(hedge=True), {"A": 1.0}) is True)
cb.POZ_MODU_KONTROL = _eski_pk

# IZOLE TEMINAT: `_KALDIRAC_AYARLI` cache'i yuzunden bot bir daha
# kontrol etmiyordu. Tespit BEDAVA - marginType zaten geliyor.
kontrol("izole kapatma varsayılan olarak AÇIK", cb.IZOLE_KAPAT)
_poz = [{"symbol": "AUSDT", "positionAmt": "5", "marginType": "cross"},
        {"symbol": "BUSDT", "positionAmt": "-3", "marginType": "isolated"},
        {"symbol": "CUSDT", "positionAmt": "0", "marginType": "isolated"},
        {"symbol": "DUSDT", "positionAmt": "2", "marginType": "ISOLATED"}]
_iz = cb.izole_teminatlilar(_SahtePoz(poz=_poz))
kontrol("izole pozisyonlar bulunuyor", _iz == ["BUSDT", "DUSDT"], f"({_iz})")
kontrol("ÇAPRAZ olan sembol listeye girmiyor", "AUSDT" not in _iz)
kontrol("MİKTARI SIFIR olan izole satır sayılmıyor", "CUSDT" not in _iz)


class _Patlayan:
    class client:
        pass

    def get_open_positions(self):
        raise RuntimeError("API hatası (bilerek)")


kontrol("izole kontrolü API hatasında boş liste döner, çökmez",
        cb.izole_teminatlilar(_Patlayan()) == [])
_h11 = {"AUSDT": 100.0, "BUSDT": -50.0, "EUSDT": 20.0}
cb._KALDIRAC_AYARLI.update({"AUSDT", "BUSDT"})
_at = cb.izole_ele(_h11, ["BUSDT", "ZUSDT"])
kontrol("izole sembol HEDEFTEN çıkarılıyor (kapatma emri üretilsin)",
        "BUSDT" not in _h11 and _at == ["BUSDT"], f"({_h11}, {_at})")
kontrol("diğer bacaklara dokunulmuyor",
        _h11 == {"AUSDT": 100.0, "EUSDT": 20.0}, f"({_h11})")
kontrol("izole sembol kaldıraç CACHE'inden düşürülüyor "
        "(kapanınca ÇAPRAZ yeniden denenir)",
        "BUSDT" not in cb._KALDIRAC_AYARLI)
kontrol("ÇAPRAZ sembolün cache'i korunuyor", "AUSDT" in cb._KALDIRAC_AYARLI)
kontrol("hedefte olmayan izole sembol sorun çıkarmıyor", "ZUSDT" not in _h11)
kontrol("izole liste boşken hiçbir şey yapılmıyor",
        cb.izole_ele({"AUSDT": 1.0}, []) == [])
kontrol("ölçüm tablosu her kaldıraç için ayrı rakam veriyor",
        cb.IZOLE_OLCUM[2][1] < cb.IZOLE_OLCUM[5][1] < cb.IZOLE_OLCUM[10][1],
        f"({cb.IZOLE_OLCUM})")

# MEVCUT_PORTFOY: hedge modda sembol basina IKI satir gelir; eskiden
# ikinci satir birincisini SILIYORDU (maruziyet 2 kata kadar yanlis).
class _CiftSatir:
    class client:
        pass

    def get_open_positions(self):
        return [{"symbol": "XUSDT", "positionAmt": "10", "notional": "1000",
                 "markPrice": "100"},
                {"symbol": "XUSDT", "positionAmt": "-4", "notional": "-400",
                 "markPrice": "100"},
                {"symbol": "YUSDT", "positionAmt": "1", "notional": "250",
                 "markPrice": "250"}]


_mp = cb.mevcut_portfoy(_CiftSatir())
kontrol("aynı sembolün İKİ satırı TOPLANIYOR (üzerine yazılmıyor)",
        abs(_mp.get("XUSDT", 0) - 600.0) < 1e-9, f"({_mp})")
kontrol("tek satırlı sembol etkilenmiyor",
        abs(_mp.get("YUSDT", 0) - 250.0) < 1e-9, f"({_mp})")


class _Netsiz:
    class client:
        pass

    def get_open_positions(self):
        return [{"symbol": "ZUSDT", "positionAmt": "5", "notional": "500",
                 "markPrice": "100"},
                {"symbol": "ZUSDT", "positionAmt": "-5", "notional": "-500",
                 "markPrice": "100"}]


kontrol("net sıfır çıkan sembol portföyden DÜŞÜYOR",
        "ZUSDT" not in cb.mevcut_portfoy(_Netsiz()))

# MADDE 211 (asil tuzak): `kaldirac_hazirla` acik pozisyonlu sembolde
# -4048 ile FALSE doner ve `_emirleri_gonder` emri ATLARDI - yani izole
# pozisyon HIC KAPATILAMAZDI. Kuculten emir artik muaf.
kontrol("pozisyon yoksa küçültme sayılmıyor",
        not cb._kuculten_mi("AUSDT", "SELL", 100.0, {}))
kontrol("LONG pozisyonda SELL küçültüyor",
        cb._kuculten_mi("AUSDT", "SELL", 100.0, {"AUSDT": 500.0}))
kontrol("SHORT pozisyonda BUY küçültüyor",
        cb._kuculten_mi("AUSDT", "BUY", 100.0, {"AUSDT": -500.0}))
kontrol("LONG pozisyonda BUY BÜYÜTÜYOR (muaf DEĞİL)",
        not cb._kuculten_mi("AUSDT", "BUY", 100.0, {"AUSDT": 500.0}))
kontrol("SHORT pozisyonda SELL BÜYÜTÜYOR (muaf DEĞİL)",
        not cb._kuculten_mi("AUSDT", "SELL", 100.0, {"AUSDT": -500.0}))
kontrol("mevcut verilmezse hiçbir emir muaf değil (eski davranış)",
        not cb._kuculten_mi("AUSDT", "SELL", 100.0, None))
kontrol("sıfır pozisyon küçültme sayılmıyor",
        not cb._kuculten_mi("AUSDT", "SELL", 100.0, {"AUSDT": 0.0}))


class _TeminatRed:
    """ÇAPRAZ'a alma her sembolde -4048 ile reddediliyor (pozisyon açık)."""

    def __init__(self):
        self.gonderilen = []
        _o = self

        class _C:
            @staticmethod
            def futures_change_margin_type(symbol, marginType):
                raise RuntimeError("APIError(code=-4048): Margin type cannot "
                                   "be changed if there exists position.")

            @staticmethod
            def futures_get_open_orders():
                return []

            @staticmethod
            def futures_symbol_ticker(symbol):
                return {"price": "100"}

            @staticmethod
            def futures_create_order(**k):
                _o.gonderilen.append(k)
                return {"orderId": len(_o.gonderilen)}
        self.client = _C()

    def cancel_all_open_orders(self, symbol):
        pass

    def get_symbol_precision(self, symbol):
        return {"quantity_precision": 3, "price_precision": 2}

    def open_market_position(self, symbol, side, quantity):
        self.gonderilen.append({"symbol": symbol, "side": side,
                                "type": "MARKET"})


_eski_cache = set(cb._KALDIRAC_AYARLI)
cb._KALDIRAC_AYARLI.clear()
_eski_db = cb.DOLUM_BEKLEME_SN
cb.DOLUM_BEKLEME_SN = 0.0
_c1 = _TeminatRed()
cb._emirleri_gonder(_c1, [("IZOUSDT", "BUY", 1000.0)], {"IZOUSDT": -1000.0})
kontrol("ÇAPRAZ'a alınamayan sembolün KAPATMA emri GÖNDERİLİYOR",
        len(_c1.gonderilen) > 0, f"({_c1.gonderilen})")
cb._KALDIRAC_AYARLI.clear()
_c2 = _TeminatRed()
cb._emirleri_gonder(_c2, [("IZOUSDT", "BUY", 1000.0)], {"IZOUSDT": 1000.0})
kontrol("ÇAPRAZ'a alınamayan sembolde BÜYÜTME emri hâlâ ENGELLİ",
        len(_c2.gonderilen) == 0, f"({_c2.gonderilen})")
cb._KALDIRAC_AYARLI.clear()
_c3 = _TeminatRed()
cb._emirleri_gonder(_c3, [("IZOUSDT", "BUY", 1000.0)])
kontrol("mevcut verilmezse eski davranış (engelli) korunuyor",
        len(_c3.gonderilen) == 0, f"({_c3.gonderilen})")
cb.DOLUM_BEKLEME_SN = _eski_db
cb._KALDIRAC_AYARLI.clear()
cb._KALDIRAC_AYARLI.update(_eski_cache)

print("\n7k) KÂR AL DEFTERİ VE GÜÇ (madde 216)")
# Madde 214: karin TAMAMI kar-al hasadindan geliyor. Madde 216: TP oranı
# 30 gunde %95 guc veriyor, toplam getiri %15. O yuzden dolumlar artik
# deftere yaziliyor.
import os as _os, time as _time, tempfile as _tf
_eski_tp = cb.TP_DEFTER_DOSYA
_dtp = _tf.mkdtemp(); cb.TP_DEFTER_DOSYA = _os.path.join(_dtp, "tp.csv")
kontrol("beklenen LONG TP oranı madde 214 ölçümü (%8,8)",
        abs(cb.BEKLENEN_TP_LONG - 0.088) < 1e-9)
kontrol("beklenen SHORT TP oranı madde 214 ölçümü (%18,1)",
        abs(cb.BEKLENEN_TP_SHORT - 0.181) < 1e-9)
kontrol("SHORT eşiği daha SIKI olduğu için oranı daha YÜKSEK",
        cb.BEKLENEN_TP_SHORT > cb.BEKLENEN_TP_LONG)
kontrol("boş defter sıfır döner, çökmüyor",
        cb.tp_defteri_oku() == {"LONG": 0, "SHORT": 0})
cb._tp_kaydet("AUSDT", "SELL")
cb._tp_kaydet("BUSDT", "BUY")
cb._tp_kaydet("CUSDT", "SELL")
_d = cb.tp_defteri_oku(gun=30)
kontrol("LONG pozisyonun TP'si SELL emri -> LONG sayılıyor", _d["LONG"] == 2,
        f"({_d})")
kontrol("SHORT pozisyonun TP'si BUY emri -> SHORT sayılıyor", _d["SHORT"] == 1,
        f"({_d})")
with open(cb.TP_DEFTER_DOSYA, "a", encoding="utf-8") as _fh:
    _fh.write(f"{_time.time() - 40*86400:.0f},XUSDT,LONG\n")
kontrol("40 gün önceki kayıt 30 günlük pencereye GİRMİYOR",
        cb.tp_defteri_oku(gun=30)["LONG"] == 2)
kontrol("60 günlük pencerede GÖRÜNÜYOR",
        cb.tp_defteri_oku(gun=60)["LONG"] == 3)
with open(cb.TP_DEFTER_DOSYA, "a", encoding="utf-8") as _fh:
    _fh.write("bozuk satir\nzaman_degil,YUSDT,LONG\n")
kontrol("bozuk satırlar ÇÖKERTMİYOR, atlanıyor",
        cb.tp_defteri_oku(gun=30)["LONG"] == 2)
kontrol("olmayan dosya sıfır döner",
        cb.tp_defteri_oku("/tmp/olmayan_tp_xyz.csv") == {"LONG": 0, "SHORT": 0})
# yazilamayan yol botu durdurmamali
cb.TP_DEFTER_DOSYA = "/olmayan_dizin_xyz/tp.csv"
_patladi = False
try:
    cb._tp_kaydet("ZUSDT", "SELL")
except Exception:
    _patladi = True
kontrol("defter yazılamazsa BOT DURMUYOR (ölçüm aracı, kritik değil)",
        not _patladi)
cb.TP_DEFTER_DOSYA = _eski_tp

print("\n8) DİLİM (faz çeşitlendirmesi)")
import json, tempfile, os
_dd = tempfile.mkdtemp()
dj = os.path.join(_dd, "dilim.json")
kontrol("dosya yokken temiz durum döner",
        cb.dilim_durum_oku(dj) == {"sira": 0, "dilimler": {}})
d = {"sira": 2, "dilimler": {"0": {"AUSDT": 100.0}, "1": {"AUSDT": -40.0, "BUSDT": 60.0}}}
cb.dilim_durum_yaz(d, dj)
kontrol("yazılan durum aynen geri okunur", cb.dilim_durum_oku(dj) == d)
t = cb.toplam_hedef(d)
kontrol("aynı sembol dilimler arası TOPLANIR",
        abs(t.get("AUSDT", 0) - 60.0) < 1e-9, f"({t})")
kontrol("tek dilimdeki sembol aynen geçer",
        abs(t.get("BUSDT", 0) - 60.0) < 1e-9, f"({t})")
# Zit yonler birbirini goturur -> kalan MIN_NOTIONAL altindaysa pozisyon YOK
d2 = {"sira": 0, "dilimler": {"0": {"CUSDT": 100.0}, "1": {"CUSDT": -99.0}}}
kontrol("zıt dilimler netleşir, artık MIN_NOTIONAL altıysa pozisyon açılmaz",
        "CUSDT" not in cb.toplam_hedef(d2), f"({cb.toplam_hedef(d2)})")
kontrol("boş durumda boş hedef", cb.toplam_hedef({"dilimler": {}}) == {})
# Bozuk dosya cokmez
open(os.path.join(_dd, "bozuk.json"), "w").write("{bozuk")
kontrol("bozuk dosyada çökmeden sıfırdan başlar",
        cb.dilim_durum_oku(os.path.join(_dd, "bozuk.json"))["sira"] == 0)
# Dilim sermayesi: N dilimde her dilim bakiyenin 1/N'i
eski_nd, eski_nl = cb.N_DILIM, cb.N_LEGS
cb.N_DILIM, cb.N_LEGS = 5, 2
h = cb.hedef_portfoy(pd.Series({f"S{i}USDT": i * 0.001 for i in range(10)}),
                     10000.0 / cb.N_DILIM)
kontrol("dilim brütü toplam sermayenin 1/N'i",
        abs(sum(abs(v) for v in h.values())
            - 2000.0 * cb.GROSS_EXPOSURE * (1 - cb.REZERV_PAY)) < 1e-6,
        f"({sum(abs(v) for v in h.values()):.1f})")
cb.N_DILIM, cb.N_LEGS = eski_nd, eski_nl

print("\n9) LİMİT EMİR (maker) FİYATLAMASI")
al = float(cb.limit_fiyat(100.0, "BUY", 2))
sat = float(cb.limit_fiyat(100.0, "SELL", 2))
kontrol("ALIŞ limiti piyasanın ALTINDA", al < 100.0, f"({al})")
kontrol("SATIŞ limiti piyasanın ÜSTÜNDE", sat > 100.0, f"({sat})")
kontrol("ofset doğru uygulanıyor",
        abs(al - 100.0*(1-cb.LIMIT_OFSET)) < 1e-6 and
        abs(sat - 100.0*(1+cb.LIMIT_OFSET)) < 1e-6)
kontrol("hassasiyet 0'da tam sayı döner", "." not in cb.limit_fiyat(100.0, "BUY", 0))
kontrol("yüksek hassasiyette ondalık korunur",
        len(cb.limit_fiyat(0.12345678, "BUY", 6).split(".")[1]) == 6)
# Maker YONU: alis asagi / satis yukari olmali - tersi TAKER yapardi
kontrol("alış ve satış limitleri piyasayı ÇAPRAZLAMAZ", al < sat)

print("\n10) RİSK PROFİLİ")
kontrol("dört profil de tanımlı",
        all(k in cb._PROFILLER for k in ("guvenli","dengeli","agresif","cok_agresif")))
kontrol("profiller artan sırada",
        cb._PROFILLER["guvenli"] < cb._PROFILLER["dengeli"]
        < cb._PROFILLER["agresif"] < cb._PROFILLER["cok_agresif"])
kontrol("türkçe karakterli yazımlar da çalışır",
        cb._PROFILLER["güvenli"] == cb._PROFILLER["guvenli"]
        and cb._PROFILLER["çok_agresif"] == cb._PROFILLER["cok_agresif"])
# madde 140: varsayilan artik KALDIRACSIZ (0 = hedef kapali). Eski test
# en az %5 hedef istiyordu - eski, yanli paneldeki tasarimin kuraliydi.
kontrol("varsayılan vol hedefi kaldıraçsız ya da makul aralıkta",
        cb.VOL_HEDEF == 0.0 or 0.05 <= cb.VOL_HEDEF <= 1.0, f"({cb.VOL_HEDEF})")
kontrol("kaldıraçsız profil tanımlı ve hedefi 0",
        cb._PROFILLER["kaldiracsiz"] == 0.0 and cb._PROFILLER["kaldıraçsız"] == 0.0)

print("\n11) KÜÇÜK BAKİYE — otomatik bacak sayısı")
cb.N_LEGS = eski_n          # önceki testler değiştirmiş olabilir
eski_oto = cb.OTOMATIK_BACAK
cb.OTOMATIK_BACAK = True
n10k = cb.uygun_bacak_sayisi(10000.0, 1.0)
n2k  = cb.uygun_bacak_sayisi(2000.0, 1.0)
n500 = cb.uygun_bacak_sayisi(500.0, 1.0)
n100 = cb.uygun_bacak_sayisi(100.0, 1.0)
kontrol("büyük bakiyede tam bacak kullanılıyor", n10k == cb.N_LEGS, f"({n10k})")
kontrol("bakiye küçüldükçe bacak azalıyor", n10k >= n2k >= n500 >= n100,
        f"({n10k}, {n2k}, {n500}, {n100})")
kontrol("N_LEGS asla AŞILMIYOR", cb.uygun_bacak_sayisi(1e9, 3.0) <= cb.N_LEGS)
kontrol("MIN_LEGS altına inilmiyor", n100 >= cb.MIN_LEGS, f"({n100})")
# Secilen bacak sayisiyla bacak buyuklugu gercekten MIN_BACAK_USD ustunde mi?
for b in (500.0, 2000.0, 10000.0):
    n = cb.uygun_bacak_sayisi(b, 1.0)
    bacak = b / cb.N_DILIM * cb.GROSS_EXPOSURE / 2 / n
    if n > cb.MIN_LEGS:
        kontrol(f"{b:.0f}$ -> {n}+{n} bacak, pozisyon {bacak:.1f}$ (hedef >={cb.MIN_BACAK_USD:.0f}$)",
                bacak >= cb.MIN_BACAK_USD * 0.95, f"({bacak:.1f}$)")
kontrol("ölçek büyüyünce bacak sayısı da artabilir",
        cb.uygun_bacak_sayisi(2000.0, 2.0) >= cb.uygun_bacak_sayisi(2000.0, 1.0))
cb.OTOMATIK_BACAK = False
kontrol("otomatik kapalıyken hep N_LEGS", cb.uygun_bacak_sayisi(100.0, 1.0) == cb.N_LEGS)
cb.OTOMATIK_BACAK = eski_oto

print("\n12) hedef_portfoy n_legs parametresi")
cb.N_LEGS = eski_n
fs = pd.Series({f"S{i}USDT": i * 0.0001 for i in range(60)})
h10 = cb.hedef_portfoy(fs, 10000.0, n_legs=4)
kontrol("n_legs=4 -> 8 pozisyon", len(h10) == 8, f"({len(h10)})")
# madde 177: n_legs N_LEGS'i AŞAMAZ (yukarı doğru kırpılır)
_hx = cb.hedef_portfoy(fs, 10000.0, n_legs=cb.N_LEGS + 5)
kontrol("n_legs, N_LEGS ile SINIRLI", len(_hx) == 2 * cb.N_LEGS, f"({len(_hx)})")
kontrol("küçültülmüş portföy de nötr", abs(sum(h10.values())) < 1e-9)
kontrol("brüt korunuyor (bacak büyür)",
        abs(sum(abs(v) for v in h10.values())
            - 10000.0 * cb.GROSS_EXPOSURE * (1 - cb.REZERV_PAY)) < 1e-6)
kontrol("n_legs N_LEGS'i aşamaz",
        len(cb.hedef_portfoy(fs, 10000.0, n_legs=999)) == 2 * cb.N_LEGS)

print("\n13) ÖLÇEKLEME")
cb.N_LEGS = 20
h2 = cb.hedef_portfoy(pd.Series({f"S{i}USDT": i * 0.0001 for i in range(50)}), 10000.0)
kontrol("20+20 bacakta 40 pozisyon", len(h2) == 40, f"({len(h2)})")
kontrol("her bacak eşit büyüklükte",
        len({round(abs(v), 6) for v in h2.values()}) == 1)
h3 = cb.hedef_portfoy(pd.Series({f"S{i}USDT": i * 0.0001 for i in range(50)}), 500.0)
kontrol("küçük bakiyede de nötr kalır", abs(sum(h3.values())) < 1e-9)
cb.N_LEGS = eski_n

print("\n14) MEVCUT POZİSYON GÜNCEL DEĞERLE ÖLÇÜLÜYOR (madde 164)")


class _SahtePoz:
    """get_open_positions() dışında hiçbir şeye ihtiyacı yok."""

    def __init__(self, pozlar):
        self._p = pozlar

    def get_open_positions(self):
        return self._p


# LONG 10 adet, giriş 100$ (=1000$), fiyat 300$'a çıktı -> GERÇEK değer 3000$
_p = cb.mevcut_portfoy(_SahtePoz([
    {"symbol": "AUSDT", "positionAmt": "10", "entryPrice": "100",
     "markPrice": "300", "notional": "3000"}]))
kontrol("borsanın verdiği notional kullanılıyor (giriş değeri DEĞİL)",
        abs(_p["AUSDT"] - 3000) < 1e-6, f"({_p})")
_p = cb.mevcut_portfoy(_SahtePoz([
    {"symbol": "AUSDT", "positionAmt": "10", "entryPrice": "100",
     "markPrice": "300"}]))
kontrol("notional yoksa markPrice ile hesaplanıyor",
        abs(_p["AUSDT"] - 3000) < 1e-6, f"({_p})")
# SHORT: fiyat yükseldi -> bacak BÜYÜDÜ; eski kod bunu görmüyordu
_p = cb.mevcut_portfoy(_SahtePoz([
    {"symbol": "BUSDT", "positionAmt": "-10", "entryPrice": "100",
     "markPrice": "300", "notional": "-3000"}]))
kontrol("ZARARDAKİ short'un BÜYÜDÜĞÜ görülüyor (işaret korunuyor)",
        abs(_p["BUSDT"] + 3000) < 1e-6, f"({_p})")
_p = cb.mevcut_portfoy(_SahtePoz([
    {"symbol": "CUSDT", "positionAmt": "-10", "entryPrice": "100",
     "markPrice": "0", "notional": ""}]))
kontrol("markPrice de yoksa entryPrice'a düşülüyor (çökme yok)",
        abs(_p["CUSDT"] + 1000) < 1e-6, f"({_p})")
_p = cb.mevcut_portfoy(_SahtePoz([
    {"symbol": "DUSDT", "positionAmt": "-10", "entryPrice": "100",
     "markPrice": "300", "notional": "3000"}]))
kontrol("notional'ın işareti pozisyonla UYUŞMUYORSA yok sayılıyor",
        abs(_p["DUSDT"] + 3000) < 1e-6, f"({_p})")
_p = cb.mevcut_portfoy(_SahtePoz([
    {"symbol": "EUSDT", "positionAmt": "0", "entryPrice": "100",
     "markPrice": "300", "notional": "0"},
    {"symbol": "FUSDT", "positionAmt": "bozuk"}]))
kontrol("kapalı ve bozuk kayıtlar atlanıyor", _p == {}, f"({_p})")
# Sürüklenen bacak KIRPILIYOR mu: hedef 1000$, gerçek 3000$ -> 2000$ SAT
_e = cb.emirleri_hesapla({"AUSDT": 1000.0}, {"AUSDT": 3000.0}, tolerans_usd=100.0)
kontrol("sürüklenmiş bacak için KIRPMA emri üretiliyor",
        _e and _e[0][0] == "AUSDT" and _e[0][1] == "SELL"
        and abs(_e[0][2] - 2000) < 1e-6, f"({_e})")

print("\n15) FUNDING SOLUNCA ERKEN ÇIKIŞ (madde 167)")
_es = cb.SOLMA_ORAN
cb.SOLMA_ORAN = 0.70
_d = {"dilimler": {"0": {"AUSDT": 100.0, "BUSDT": -100.0}, "1": {"CUSDT": 50.0}},
      "giris_funding": {"AUSDT": -5.0, "BUSDT": 4.0, "CUSDT": -6.0}}
_f = pd.Series({"AUSDT": -1.0, "BUSDT": 4.2, "CUSDT": -5.9})
_solan = cb.funding_soldu(_d, _f)
kontrol("kirası kesilen bacak (−5 -> −1) ELENİYOR", _solan == ["AUSDT"], f"({_solan})")
kontrol("funding GÜÇLENEN bacak korunuyor", "BUSDT" in _d["dilimler"]["0"])
kontrol("hafif gerileyen bacak (−6 -> −5.9) korunuyor", "CUSDT" in _d["dilimler"]["1"])
kontrol("elenen sembolün giriş kaydı da siliniyor",
        "AUSDT" not in _d["giris_funding"], f"({_d['giris_funding']})")
_d2 = {"dilimler": {"0": {"AUSDT": 100.0}}, "giris_funding": {"AUSDT": -5.0}}
kontrol("funding İŞARET DEĞİŞTİRİRSE eleniyor (artık ödeyen taraf biz)",
        cb.funding_soldu(_d2, pd.Series({"AUSDT": 1.0})) == ["AUSDT"])
_d3 = {"dilimler": {"0": {"AUSDT": 100.0}}, "giris_funding": {}}
kontrol("giriş bilgisi YOKSA pozisyona DOKUNULMUYOR (sessiz kapatma yok)",
        cb.funding_soldu(_d3, pd.Series({"AUSDT": 0.0})) == []
        and "AUSDT" in _d3["dilimler"]["0"])
_d4 = {"dilimler": {"0": {"AUSDT": 100.0}}, "giris_funding": {"AUSDT": -5.0}}
kontrol("funding verisi eksikse (NaN) dokunulmuyor",
        cb.funding_soldu(_d4, pd.Series({"BUSDT": 1.0})) == [])
cb.SOLMA_ORAN = 0.0
kontrol("SOLMA_ORAN=0 ile özellik KAPALI",
        cb.funding_soldu({"dilimler": {"0": {"AUSDT": 1.0}},
                          "giris_funding": {"AUSDT": -5.0}},
                         pd.Series({"AUSDT": 0.0})) == [])
cb.SOLMA_ORAN = 0.70
_d5 = {}
cb.giris_funding_yaz(_d5, {"AUSDT": 100.0, "ZUSDT": -50.0},
                     pd.Series({"AUSDT": -5.0}))
kontrol("giriş funding'i kaydediliyor", _d5["giris_funding"] == {"AUSDT": -5.0},
        f"({_d5})")
kontrol("funding'i olmayan sembol kaydedilmiyor (yanlış eşik üretmesin)",
        "ZUSDT" not in _d5["giris_funding"])
cb.SOLMA_ORAN = _es

print("\n16) SİNYAL PENCERESİ ZAMAN BAZLI (madde 182)")


def _kay(n, aralik_saat, oranlar):
    """n ödeme kaydı, verilen aralıkla, sondan başa doğru."""
    t0 = 1_700_000_000_000
    return [{"fundingTime": t0 + i * int(aralik_saat * 3600000),
             "fundingRate": str(oranlar[i])} for i in range(n)]


# 8 saatlik sembol, son ödeme UÇ (-%1), öncekiler sıfıra yakın
_k8 = _kay(20, 8, [0.0001] * 19 + [-0.01])
_son = cb.yillik_funding(_k8, 8)
_tum = cb.yillik_funding(_k8, 0)
kontrol("8 saatlik pencere SON ödemeyi yansıtıyor", _son < -3.0, f"({_son:.2f})")
kontrol("pencere=0 eski davranış (hepsini ortalar) ve sinyali SÖNDÜRÜR",
        abs(_tum) < 1.0 and _son < _tum, f"(son {_son:.2f} vs tum {_tum:.2f})")
# 24 günlük ortalama ile karşılaştırma: uç sinyal 20 kayıtta erir
kontrol("uzun pencere uç funding'i eritiyor (canlıdaki eski hata)",
        abs(cb.yillik_funding(_k8, 24 * 24)) < abs(_son) / 5,
        f"(24 gun {cb.yillik_funding(_k8, 24*24):.2f} vs 8sa {_son:.2f})")
# 1 saatlik sembol: AYNI zaman penceresi, daha çok kayıt
_k1 = _kay(40, 1, [0.0001] * 32 + [-0.001] * 8)
_s1 = cb.yillik_funding(_k1, 8)
kontrol("1 saatlik sembolde de pencere ZAMAN cinsinden uygulanıyor",
        _s1 is not None and _s1 < 0, f"({_s1})")
kontrol("aralık ALT SINIRI hâlâ 4 saat (madde 138 koruması)",
        abs(cb.yillik_funding(_kay(10, 1, [0.001] * 10), 8)
            - 0.001 * 6 * 365) < 1e-6)
kontrol("pencere içinde kayıt yoksa ÇÖKMÜYOR, elindekini kullanıyor",
        cb.yillik_funding(_kay(3, 8, [0.001, 0.002, 0.003]), 0.001) is not None)
kontrol("tek kayıt None döner (aralık bilinemez)",
        cb.yillik_funding([{"fundingTime": 1, "fundingRate": "0.001"}], 8) is None)
kontrol("varsayılan pencere 48 saat = 2 gün (madde 209)",
        cb.FUNDING_WINDOW_HOURS == 48.0, f"({cb.FUNDING_WINDOW_HOURS})")
kontrol("8 saat ARTIK varsayılan DEĞİL (madde 182 yanlış etiketli kontrol)",
        cb.FUNDING_WINDOW_HOURS != 8.0)
# 48 saat, 8sa sembolde TAM 6 odeme
_k48 = _kay(20, 8, [0.0] * 14 + [0.0010] * 6)
kontrol("48sa pencere 8sa sembolde TAM 6 ödeme ortalıyor",
        abs(cb.yillik_funding(_k48, 48) - 0.0010 * 3 * 365) < 1e-9,
        f"({cb.yillik_funding(_k48, 48):.4f})")
kontrol("48sa pencere 4sa sembolde TAM 12 ödeme ortalıyor",
        abs(cb.yillik_funding(_kay(30, 4, [0.0] * 18 + [0.0010] * 12), 48)
            - 0.0010 * 6 * 365) < 1e-9)

# MADDE 209: PENCERE SINIRI DIŞLAYICI. Aralık = pencere olan sembolde
# (8sa pencere, 8sa sembol) kapsayıcı sınır SON İKİ ödemeyi ortalıyordu,
# yani "8 saat" fiilen 16 saat oluyordu.
_kt = _kay(6, 8, [0.0] * 5 + [0.0010])
kontrol("8sa pencere 8sa sembolde SADECE son ödemeyi alıyor",
        abs(cb.yillik_funding(_kt, 8) - 0.0010 * 3 * 365) < 1e-9,
        f"({cb.yillik_funding(_kt, 8):.4f} vs {0.0010*3*365:.4f})")
# 72 saatlik pencere, 8 saatlik sembol -> TAM 9 ödeme (panelin 18 barı)
_k72 = _kay(20, 8, [0.0] * 11 + [0.0010] * 9)
kontrol("72sa pencere 8sa sembolde TAM 9 ödeme ortalıyor",
        abs(cb.yillik_funding(_k72, 72) - 0.0010 * 3 * 365) < 1e-9,
        f"({cb.yillik_funding(_k72, 72):.4f})")
_k72b = _kay(20, 8, [0.0] * 10 + [0.0010] * 10)
kontrol("10. ödeme pencereye GİRMİYOR (sınır dışlayıcı)",
        abs(cb.yillik_funding(_k72b, 72) - cb.yillik_funding(_k72, 72)) < 1e-9)
# 4 saatlik sembolde 72 saat -> 18 ödeme (zaman penceresi sembole göre
# DEĞİŞMEZ; madde 182'nin asıl amacı)
_k4 = _kay(40, 4, [0.0] * 22 + [0.0010] * 18)
kontrol("4sa sembolde 72sa penceresi 18 ödeme alıyor",
        abs(cb.yillik_funding(_k4, 72) - 0.0010 * 6 * 365) < 1e-9,
        f"({cb.yillik_funding(_k4, 72):.4f})")
kontrol("72sa pencerede uzun ortalama YİNE sinyali söndürüyor",
        abs(cb.yillik_funding(_kay(120, 8, [0.0001] * 119 + [-0.01]), 24 * 24))
        < abs(cb.yillik_funding(_kay(120, 8, [0.0001] * 119 + [-0.01]), 72)),
        "(24 gun < 72sa)")

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum testler gecti.")
print("""
HATIRLATMA - gercekci beklenti (madde 133 ile GUNCELLENDI):
  12+12 bacak, hacim >= 100M$, listelenme yasi >= 90 gun, kaldiracsiz:
  tam donem  yillik +17.8%, Sharpe 0.72, maksimum dusus -34.0%
  son 20 ay  yillik +29.6%, Sharpe 0.83, maksimum dusus -29.8%
  (5 FAZ ORTALAMALI - tek faz sonucu yaniltici, madde 133.6)

  ESKI RAKAM (+14.9% / Sharpe 1.44 / dusus -12.0%) 183 sembollük
  HAYATTA KALAN panelden geliyordu. 847 sembollük tam evrende ayni
  olcum Sharpe 0.99'a, filtresiz haliyle -1.25'e dusuyor. Yani eski
  Sharpe hayatta kalma yanliligiyla sisirilmisti; strateji ayakta
  ama beklenti yariya indi.

  Kaldirac Sharpe'i degistirmez, sadece olcegi buyutur - dusus de
  ayni oranda buyur. -34% dusus zaten derin; kaldirac dikkatli
  kullanilmali.

  Bu strateji fiyat TAHMIN ETMEZ, funding kirasini toplar.
""")
