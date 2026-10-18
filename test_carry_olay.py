"""carry_olay.py testleri (madde 166).

En kritik iki test:
  1. ZAMANLAMA - ödemeye 30 dakika kalan sembol ADAY OLMAMALI. Ölçüldü:
     T−1dk'da +34..+58 bp, T−30dk'da −20..−44 bp. Erken girmek
     stratejiyi ters çevirir.
  2. TERS YÖN - ana kitaba ters emir AÇILMAMALI; yoksa tek yönlü modda
     ana botun bacağını kapatır.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carry_olay as co
import carry_bot as cb

gecen = basarisiz = 0


def kontrol(ad, kosul, ek=""):
    global gecen, basarisiz
    if kosul:
        gecen += 1
        print(f"  [OK]   {ad}")
    else:
        basarisiz += 1
        print(f"  [HATA] {ad} {ek}")


SIMDI = 1_700_000_000_000


def m(sem, oran, kalan_sn):
    return {"symbol": sem, "lastFundingRate": str(oran),
            "nextFundingTime": SIMDI + int(kalan_sn * 1000)}


print("1) ZAMANLAMA — stratejinin tamamı burada")
mark = [m("AUSDT", -0.01, 30), m("BUSDT", -0.01, 1800), m("CUSDT", -0.01, -60)]
a = co.adaylar(mark, SIMDI)
ad = {x[0] for x in a}
kontrol("30 saniye kalan sembol ADAY", "AUSDT" in ad, f"({ad})")
kontrol("30 DAKİKA kalan sembol aday DEĞİL (erken giriş zarar ediyor)",
        "BUSDT" not in ad, f"({ad})")
kontrol("ödeme anı GEÇMİŞ sembol aday değil (ödemeyi alamayız)",
        "CUSDT" not in ad, f"({ad})")
kontrol("varsayılan pencere 60 saniye (tabloya göre tasarım)",
        co.ONCE_SN == 60, f"({co.ONCE_SN})")

print("\n2) EŞİK VE YÖN")
mark = [m("AUSDT", -0.03, 30), m("BUSDT", +0.03, 30), m("CUSDT", -0.0005, 30)]
a = co.adaylar(mark, SIMDI)
d = {x[0]: x[1] for x in a}
kontrol("negatif funding -> LONG (funding ALIRIZ)", d.get("AUSDT") == 1, f"({d})")
kontrol("pozitif funding -> SHORT", d.get("BUSDT") == -1, f"({d})")
kontrol("eşiğin altındaki oran elenir", "CUSDT" not in d, f"({d})")

print("\n3) SEÇİM SINIRI")
cok = [m(f"L{i}USDT", -0.01 - i * 0.001, 30) for i in range(20)]
cok += [m(f"S{i}USDT", +0.01 + i * 0.001, 30) for i in range(20)]
s = co.secim(co.adaylar(cok, SIMDI), maks=12)
uz = [x for x in s if x[1] > 0]
ks = [x for x in s if x[1] < 0]
kontrol("her tarafta en fazla MAKS bacak", len(uz) == 12 and len(ks) == 12,
        f"({len(uz)}+{len(ks)})")
# Sınırda kayan nokta karşılaştırması yapılmaz: seçilen KÜMEYİ doğrula.
_bek = {f"L{i}USDT" for i in range(8, 20)}       # en negatif 12 sembol
kontrol("LONG tarafta EN NEGATİF 12 sembol seçiliyor",
        {x[0] for x in uz} == _bek, f"({sorted(x[0] for x in uz)})")
_bek_s = {f"S{i}USDT" for i in range(8, 20)}
kontrol("SHORT tarafta EN POZİTİF 12 sembol seçiliyor",
        {x[0] for x in ks} == _bek_s, f"({sorted(x[0] for x in ks)})")

print("\n4) ANA KİTABA TERS EMİR AÇILMIYOR (%4.1'lik tehlikeli vaka)")
sec = [("AUSDT", 1, -0.03), ("BUSDT", -1, 0.03), ("CUSDT", 1, -0.03)]
kalan, elenen = co.ters_ele(sec, {"AUSDT": -500.0, "BUSDT": -300.0})
kontrol("ana kitap SHORT iken LONG olay emri ELENİR",
        "AUSDT" in elenen, f"({elenen})")
kontrol("AYNI yöndeki olay emri geçer (sadece geçici büyüme)",
        "BUSDT" in {x[0] for x in kalan}, f"({kalan})")
kontrol("ana kitapta pozisyon YOKSA emir geçer",
        "CUSDT" in {x[0] for x in kalan}, f"({kalan})")

print("\n5) BACAK BÜYÜKLÜĞÜ SABİT (−%99 hatasının testi)")
b12 = co.bacak_usd(10000.0, n_secili=24, pay=0.20, maks=12)
b2 = co.bacak_usd(10000.0, n_secili=2, pay=0.20, maks=12)
kontrol("bacak = sermaye*pay/(2*maks)", abs(b12 - 10000 * 0.2 / 24) < 1e-9, f"({b12})")
kontrol("SİNYAL AZALINCA bacak BÜYÜMÜYOR (yoğunlaşma yok)",
        abs(b2 - b12) < 1e-9, f"(2 sinyal: {b2}, 24 sinyal: {b12})")
kontrol("2 sinyalde toplam maruziyet kitabın %2'sinden küçük",
        2 * b2 / 10000.0 < 0.02, f"({2*b2/10000.0:.4f})")
kontrol("tam dolu kitapta toplam maruziyet = pay",
        abs(24 * b12 / 10000.0 - 0.20) < 1e-9)

print("\n6) EMİR ETİKETİ — ana bot bu emirlere DOKUNMAMALI")
et = co.emir_etiketi("AUSDT", SIMDI)
kontrol("etiket OLAY öneki taşıyor", et.startswith("OLAY"), f"({et})")
kontrol("etiket borsa sınırını aşmıyor (<=36)", len(et) <= 36, f"({len(et)})")
kontrol("olay emri tanınıyor", co.olay_emri_mi({"clientOrderId": et}))
kontrol("ana botun emri olay emri SAYILMIYOR",
        not co.olay_emri_mi({"clientOrderId": "x-abc123"}))
kontrol("clientOrderId yoksa çökmüyor", not co.olay_emri_mi({}))
kontrol("carry_bot aynı kararı veriyor",
        cb._olay_emri_mi({"clientOrderId": et})
        and not cb._olay_emri_mi({"clientOrderId": "yok"}))

print("\n7) KİLİT — ana bot ve olay modülü aynı dakikada kitaba dokunmaz")
y = tempfile.mktemp(suffix=".json")
kontrol("kilit yokken kilit_var False", not co.kilit_var(y))
co.kilit_yaz(y, ["AUSDT"])
kontrol("kilit yazılınca True", co.kilit_var(y))
kontrol("BAYAT kilit yok sayılıyor (ana bot sonsuza kadar bloke olmaz)",
        not co.kilit_var(y, azami_yas_sn=-1))
co.kilit_sil(y)
kontrol("kilit silinince False", not co.kilit_var(y))
kontrol("olmayan kilidi silmek çökertmiyor", co.kilit_sil(y) is None)

print("\n8) LİMİT FİYAT — post-only DOĞRU tarafta")
kontrol("ALIŞ limiti fiyatın ALTINDA", float(co._limit(100.0, 1, 2)) < 100.0,
        f"({co._limit(100.0, 1, 2)})")
kontrol("SATIŞ limiti fiyatın ÜSTÜNDE", float(co._limit(100.0, -1, 2)) > 100.0,
        f"({co._limit(100.0, -1, 2)})")
kontrol("mesafe OFS kadar",
        abs(float(co._limit(100.0, 1, 6)) - 100.0 * (1 - co.OFS)) < 1e-6)


class _SahteIc:
    def __init__(self):
        self.emirler = []

    def futures_symbol_ticker(self, symbol):
        return {"price": "100.0"}

    def futures_create_order(self, **kw):
        self.emirler.append(kw)
        return {"orderId": len(self.emirler)}


class _Sahte:
    def __init__(self, poz=None):
        self.client = _SahteIc()
        self._poz = poz or []

    def get_symbol_precision(self, s):
        return {"quantity_precision": 3, "price_precision": 2}

    def get_open_positions(self):
        return self._poz

    def get_account_equity_usd(self):
        return 10000.0


print("\n9) EMİR GÖNDERİMİ")
c = _Sahte()
acilan = co.ac(c, [("AUSDT", 1, -0.03), ("BUSDT", -1, 0.03)], 200.0, SIMDI)
kw = {e["symbol"]: e for e in c.client.emirler}
kontrol("iki bacak da gönderildi", len(acilan) == 2, f"({acilan})")
kontrol("emirler GTX (post-only)",
        all(e["timeInForce"] == "GTX" for e in c.client.emirler))
kontrol("LONG bacak BUY, SHORT bacak SELL",
        kw["AUSDT"]["side"] == "BUY" and kw["BUSDT"]["side"] == "SELL")
kontrol("her emir OLAY etiketi taşıyor",
        all(str(e["newClientOrderId"]).startswith("OLAY") for e in c.client.emirler))
kontrol("miktar bacak/fiyat", abs(float(kw["AUSDT"]["quantity"]) - 2.0) < 1e-9,
        f"({kw['AUSDT']['quantity']})")
c2 = _Sahte()
kontrol("minNotional altındaki bacak gönderilmiyor",
        co.ac(c2, [("AUSDT", 1, -0.03)], 1.0, SIMDI) == {})

print("\n10) DOLAN BACAK — ana botun pozisyonuyla KARIŞMIYOR")
c = _Sahte(poz=[{"symbol": "AUSDT", "positionAmt": "50.0"}])
# ana bot AUSDT'de 50 adet tutuyor olabilir; bizim payımız açtığımız 2 adedi AŞAMAZ
d = co.dolanlar(c, {"AUSDT": (1, 2.0)})
kontrol("bizim payımız açtığımız miktarla SINIRLI", d["AUSDT"][1] == 2.0, f"({d})")
c = _Sahte(poz=[{"symbol": "AUSDT", "positionAmt": "-50.0"}])
kontrol("TERS yönde pozisyon varsa bizim bacağımız sayılmaz",
        co.dolanlar(c, {"AUSDT": (1, 2.0)}) == {})
c = _Sahte(poz=[{"symbol": "AUSDT", "positionAmt": "1.0"}])
kontrol("kısmi dolum doğru ölçülüyor",
        co.dolanlar(c, {"AUSDT": (1, 2.0)})["AUSDT"][1] == 1.0)

print("\n11) ÇIKIŞ")
c = _Sahte(poz=[{"symbol": "AUSDT", "positionAmt": "2.0"}])
co.kapat(c, {"AUSDT": (1, 2.0)})
e = c.client.emirler[-1]
kontrol("çıkış TERS yönde", e["side"] == "SELL", f"({e['side']})")
kontrol("çıkış reduce-only (yeni pozisyon açamaz)", e.get("reduceOnly") is True)
kontrol("çıkış limiti fiyatın ÜSTÜNDE (post-only satış)",
        float(e["price"]) > 100.0, f"({e['price']})")

print("\n" + "=" * 56)
print(f"GEÇEN: {gecen}   BAŞARISIZ: {basarisiz}")
if basarisiz:
    sys.exit(1)
print("Tum olay modulu testleri gecti.")
