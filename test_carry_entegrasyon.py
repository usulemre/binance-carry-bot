"""carry_bot UÇTAN UCA entegrasyon testi — SAHTE borsa ile tam tur.

NEDEN: `test_carry_bot.py` parçaları ayrı ayrı test ediyor. Ama parçalar
tek tek doğru olup BİRLEŞİMİ yanlış olabilir - bu projede tam da bu
sınıfta 6 hata yaşandı (README madde 56/94/95/96/106/107 "sessiz no-op").

Bu test sahte bir Binance istemcisiyle `bir_tur()` fonksiyonunu BAŞTAN
SONA çalıştırır ve şunları doğrular:
  - gerçekten emir gönderiliyor mu (hiç emir gitmemesi sessiz bir arıza)
  - emirler DOĞRU YÖNDE mi (funding yüksek olan short'lanıyor mu)
  - dilim döngüsü ilerliyor mu, durum kaydediliyor mu
  - --dry-run GERÇEKTEN emir göndermiyor mu
  - ikinci turda gereksiz işlem yapılıyor mu (tolerans çalışıyor mu)
  - hata durumunda (API patlaması) bot çöküyor mu

Hiçbir gerçek API çağrısı yapılmaz, hiçbir para riske atılmaz.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import tempfile

sys.path.insert(0, '.')
import json
import zlib
import pandas as pd
import carry_bot as cb

# MADDE 177: bu dosyadaki senaryolar 12+12 varsayımıyla yazıldı (hangi
# sahte sembolün seçileceği, kaç emir çıkacağı buna bağlı). Varsayılan
# 6'ya indirildi; senaryoların VARSAYIMINI sabitliyoruz ki test ettikleri
# davranış (kalabalık seçimi, rezerv, emir yeniden denemesi) ölçülebilsin.
# Varsayılanın kendisi ayrıca test ediliyor (aşağıda "0) VARSAYILAN").
_GERCEK_N_LEGS = cb.N_LEGS
_GERCEK_MIN_LEGS = cb.MIN_LEGS
cb.N_LEGS = 12
cb.MIN_LEGS = 8
# madde 193: dolum kovalama gercek botta 180 saniye bekler - testte KAPALI.
# Varsayilanin kendisi "0) VARSAYILAN" bolumunde ayrica test ediliyor,
# kovalama mantigi da test_carry_bot.py'de sahte istemciyle.
_GERCEK_DOLUM_BEKLEME = cb.DOLUM_BEKLEME_SN
cb.DOLUM_BEKLEME_SN = 0.0

basarisiz = []


def beklenen_bacak(bakiye=10000.0):
    """MADDE 356: tur kodunun KENDİ kuralıyla bu bakiyede açılacak bacak
    sayısı. Testler eskiden cb.N_LEGS bekliyordu; madde 341'in tavanından
    (BACAK_TAVAN=4) beri bu yanlıştı ve 5 kontrol sessizce kırıktı.
    Test 12/8 bacak varsaydığı için burada 8 çıkar - canlıda 4 (aşağıda
    "0b" bölümünde gerçek varsayılanlarla ayrıca ölçülüyor)."""
    return min(cb.N_LEGS, max(cb.MIN_LEGS, cb.uygun_bacak_sayisi(bakiye)))



def kontrol(ad, kosul, detay="", her_zaman=False):
    """MADDE 333: `her_zaman=True` ise detay GECSE DE basilir.

    Neden: 2026-10-18'de 11e blogu tam pakette BIR KEZ dustu, ayni kodla
    sonraki kosuda gecti. Dusen kosunun sayilari elde YOKTU, cunku bu
    fonksiyon detayi yalnizca HATA'da basiyordu - yani kararsiz bir
    kontrol, teshis icin gereken tek veriyi gizliyordu. Izole olcum
    sonradan blogu DETERMINISTIK gosterdi (20/20 tekrar ve 8 saatlik
    izgaranin 16/16 noktasi birebir ayni: uc 55,6 · dig 22,2 · oran
    2,500 · 24 emir), yani sebep blokta ya da saatte DEGIL, paketin
    ortasindaki durumda - ve o durumu ancak sayilar her kosuda basilirsa
    yakalayabiliriz. YASA: kararsiz bir kontrolun olcumu HER KOSUDA
    kayda gecer; yalnizca duserken basilan sayi, dustugunde zaten yok.
    """
    if kosul:
        print(f"  [OK]   {ad}" + (f"  {detay}" if her_zaman and detay else ""))
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


# --------------------------------------------------------------- SAHTE BORSA
class SahteIcClient:
    """python-binance `client` nesnesinin ihtiyaç duyulan kısmı."""

    def __init__(self, n_sembol=80, funding_bozuk=None, yeni_semboller=None,
                 exchange_info_patlat=False, saglik_bozuk=False,
                 saglik_ters=False,
                 gecmis_patlat=False, tradfi_semboller=None,
                 delist_semboller=None):
        self.tradfi = set(tradfi_semboller or ())
        self.delist = set(delist_semboller or ())
        self.kaldirac = {}         # madde 149: sembol -> ayarlanan borsa kaldıracı
        self.hedge_modu = False    # madde 211: cift yonlu pozisyon modu
        self.poz_modu_gecis = []   # futures_change_position_mode cagrilari
        self.izole_semboller = set()   # madde 211: marginType=isolated donenler
        self.teminat = {}          # sembol -> marginType
        self.teminat_patlat = set()
        self.zaten_capraz = set()
        self.gtx_red = {}          # madde 160: sembol -> kaç GTX denemesi reddedilsin
        self.gtx_fiyatlar = {}     # sembol -> denenen limit fiyatları
        self.piyasa_emirleri = []  # piyasa emrine düşenler
        self.uc_funding = {}       # madde 156: sembol -> 8 saatlik uç funding oranı
        self.ls_oran = {}          # madde 148: sembol -> long/short hesap oranı
        self.ls_patlat = False
        self.ls_cagri = 0
        self.saglik_bozuk = saglik_bozuk
        self.saglik_ters = saglik_ters   # madde 262: DETERMİNİSTİK ölü edge
        self.gecmis_patlat = gecmis_patlat
        self.gecmis_cagri = 0
        self.n = n_sembol
        self.funding_bozuk = funding_bozuk or set()
        # madde 133: listelenme yaşı filtresi için. Burada geçen semboller
        # "dün listelenmiş" sayılır ve elenmelidir.
        self.yeni_semboller = set(yeni_semboller or ())
        self.exchange_info_patlat = exchange_info_patlat
        self.gonderilen = []          # (sembol, yon, tip, miktar)
        self.kar_al_emirleri = {}     # oid -> (sembol, yon, fiyat, miktar)
        self.emir_durumu = {}         # oid -> NEW / FILLED / CANCELED
        self.iptal_kar_al = []
        self.son_kar_al_kw = []
        self.felaket_emirleri = {}    # algoId -> (sembol, yon, tetik, miktar, kw)
        self.felaket_durumu = {}      # algoId -> NEW / TRIGGERED / CANCELED
        self._aid = 50000
        self._oid = 100000
        self.iptal_edilen = []
        # madde 163: borsada ASILI DURAN emirler (dolmamış GTX, kâr al...).
        # Gerçek borsada bunlar sembol portföyden çıksa da kitapta kalır.
        self.acik_emir_sembol = set()
        self.olay_emir_sembol = set()   # madde 166
        self.acik_emir_patlat = False
        self._fiyat = {f"C{i}USDT": 10.0 + i for i in range(self.n)}
        # funding: C0 en NEGATİF (long adayı), C79 en POZİTİF (short adayı)
        self._funding = {f"C{i}USDT": (i - self.n / 2) * 0.00002
                         for i in range(self.n)}

    def futures_ticker(self):
        # madde 133: canlı eşik 100M$ - sahte borsa da üstünde olmalı,
        # yoksa evren boş kalır ve tüm entegrasyon testi sessizce geçer.
        return [{"symbol": s, "quoteVolume": str(150_000_000 + i * 1000)}
                for i, s in enumerate(self._fiyat)]

    def futures_exchange_info(self):
        if self.exchange_info_patlat:
            raise RuntimeError("exchange_info patladı (bilerek)")
        import time as _t
        simdi = _t.time() * 1000.0
        return {"symbols": [
            {"symbol": s,
             "onboardDate": simdi - (1 if s in self.yeni_semboller else 400)
             * 86400000.0,
             "contractType": "TRADIFI_PERPETUAL" if s in self.tradfi else "PERPETUAL",
             "underlyingType": "EQUITY" if s in self.tradfi else "COIN",
             "status": "TRADING",
             "deliveryDate": (simdi + 3 * 86400000.0) if s in self.delist
             else 4133404800000}
            for s in self._fiyat]}

    def futures_funding_rate(self, symbol, limit=10, startTime=None,
                             endTime=None):
        if symbol in self.funding_bozuk:
            raise RuntimeError("API patladı (bilerek)")
        r = self.uc_funding.get(symbol, self._funding[symbol])
        if startTime is not None:
            self.gecmis_cagri += 1
            if self.gecmis_patlat:
                raise RuntimeError("funding geçmişi patladı (bilerek)")
        if startTime is None:
            t0 = 1700000000000
            return [{"fundingRate": str(r), "fundingTime": t0 + i * 8 * 3600000}
                    for i in range(6)]
        # SAĞLIK GEÇMİŞİ (madde 139): 8 saatte bir ödeme.
        #
        # MADDE 262 DÜZELTMESİ — BU KURGU TARİHE BAĞLI FLAKY'DİR.
        # Eski kurgu `saglik_bozuk` için her ödemede oranları semboller
        # arasında RASTGELE yeniden dağıtıyordu ("kalıcılık ölümü") ve
        # yorumu "blok bazlı karıştırma time.time() hizalamasına bağlı
        # flaky'liği çözer" diyordu. Hizalamayı çözdü, AMA İŞARETİ
        # ÇÖZMEDİ: kapı ölçütü "gölge bacakların funding geliri <= 0" ve
        # karıştırılmış veride bu gelir SIFIR ETRAFINDA RASTGELE bir
        # çekiliştir. Dört ayrı pencerede ölçtüm: −0,6bp · +1,5bp ·
        # +2,6bp · +0,2bp → DÖRTTE ÜÇÜ kapıyı KAPATMIYOR. 2026-10-04'te
        # bu sekiz testi birden düşürdü ve sebebi kodda bir gerileme
        # DEĞİLDİ, testin kendisiydi.
        #
        # Mekanizma testleri artık `saglik_ters` kullanıyor: sıralama
        # DETERMİNİSTİK olarak ters çevrilir (en negatif funding'li
        # sembol en pozitifin geçmişini görür), böylece seçici tam
        # yanlış bacakları seçer ve gölge gelir her tarihte ve her
        # hizalamada kesin olarak negatif olur. `saglik_bozuk`
        # (karıştırma) korundu ama artık DAĞILIM testinde kullanılıyor:
        # çoğu pencerede kapanmalı, hepsinde değil.
        out, t = [], (startTime // (8 * 3600000) + 1) * 8 * 3600000
        semler = list(self._funding)
        while t <= endTime and len(out) < limit:
            if self.saglik_ters:
                # ARDIŞIK bloklar arasında ters çevirme: blok k'da sıralama
                # düz, k+1'de ters. Kapı ölçütü "önceki bloğun sinyali
                # sonraki bloğun gelirini öngörür mü" olduğu için ilişki
                # HER ZAMAN ters döner -> gelir her tarihte kesin negatif.
                # (Sabit ters çevirme İŞE YARAMAZ: o sadece bir yeniden
                #  etiketlemedir, kalıcılığı hiç bozmaz - madde 262'de
                #  ölçtüm, altı tarihin altısında SAGLIKLI verdi.)
                i = semler.index(symbol)
                if (t // (8 * 3600000)) % 2 == 0:
                    i = len(semler) - 1 - i
                oran = self._funding[semler[i]]
            elif self.saglik_bozuk:
                p = np.random.default_rng(int(t // 3600000)).permutation(len(semler))
                oran = self._funding[semler[p[semler.index(symbol)]]]
            else:
                oran = r
            out.append({"fundingRate": str(oran), "fundingTime": t})
            t += 8 * 3600000
        return out

    def futures_get_position_mode(self):
        # madde 211: varsayilan TEK YONLU - eski davranis AYNEN korunur
        if getattr(self, "poz_modu_patlat", False):
            raise RuntimeError("pozisyon modu okunamadi (bilerek)")
        return {"dualSidePosition": bool(getattr(self, "hedge_modu", False))}

    def futures_change_position_mode(self, dualSidePosition):
        self.poz_modu_gecis.append(dualSidePosition)
        if getattr(self, "poz_gecis_patlat", False):
            raise RuntimeError("APIError(code=-4068): position side cannot be changed if there exists position.")
        self.hedge_modu = (str(dualSidePosition).lower() == "true")
        return {"code": 200}

    def futures_change_margin_type(self, symbol, marginType):
        if symbol in self.teminat_patlat:
            raise RuntimeError("APIError(code=-4048): Margin type cannot be changed if there exists position.")
        if symbol in self.zaten_capraz:
            raise RuntimeError("APIError(code=-4046): No need to change margin type.")
        self.teminat[symbol] = marginType
        return {"code": 200}

    def futures_global_longshort_ratio(self, symbol, period="5m", limit=1):
        # madde 148: varsayılan 1.0 (eşit) -> seçim eskisiyle AYNI kalır
        if self.ls_patlat:
            raise RuntimeError("long/short oranı patladı (bilerek)")
        self.ls_cagri += 1
        return [{"symbol": symbol, "longShortRatio": str(self.ls_oran.get(symbol, 1.0))}]

    def futures_klines(self, symbol, interval, limit):
        # taker payı sembole göre değişsin ki akış sinyali sabit olmasın
        # MADDE 360: eskiden hash(symbol) idi. Python metin hash'ini HER
        # SÜREÇTE rastgele tohumlar (PYTHONHASHSEED): akış verisi, dolayısıyla
        # seçilen bacaklar koşudan koşuya değişiyor ve rezerv testi ARALIKLI
        # düşüyordu (madde 333/356). crc32 süreçten bağımsızdır.
        pay = 0.45 + (zlib.crc32(symbol.encode()) % 100) / 1000.0
        hacim = 1_000_000.0
        # madde 183: kapanış HER BARDA DEĞİŞMELİ. Sabit fiyat verilirse
        # donuk seri filtresi (haklı olarak) tüm evreni eler; gerçek
        # borsada 4 saatlik barın kapanışı sabit kalmaz.
        out = []
        for i in range(limit):
            kap = f"{1.0 + (i % 7) * 0.001:.6f}"
            out.append([0, kap, kap, kap, kap, "1", 0, str(hacim), 0,
                        str(hacim * pay * 0.5), str(hacim * pay), 0])
        return out

    def futures_symbol_ticker(self, symbol):
        return {"price": str(self._fiyat[symbol])}

    def futures_create_order(self, **kw):
        # madde 143: reduce-only KÂR AL emirleri alım-satım emri DEĞİLDİR;
        # ayrı tutulur ki "gereksiz işlem" sayımlarını şişirmesin.
        if kw.get("reduceOnly"):
            self.son_kar_al_kw.append(dict(kw))
            self._oid += 1
            self.kar_al_emirleri[self._oid] = (kw["symbol"], kw["side"],
                                                float(kw["price"]), float(kw["quantity"]))
            self.emir_durumu[self._oid] = "NEW"
            return {"orderId": self._oid}
        sem = kw["symbol"]
        if kw.get("timeInForce") == "GTX":
            self.gtx_fiyatlar.setdefault(sem, []).append(float(kw["price"]))
            kalan = self.gtx_red.get(sem, 0)
            if kalan > 0:
                self.gtx_red[sem] = kalan - 1
                raise RuntimeError("APIError(code=-5022): Order would immediately match and take.")
        self.gonderilen.append((sem, kw["side"], kw.get("type"),
                                float(kw["quantity"])))
        return {"orderId": len(self.gonderilen)}

    def futures_get_open_orders(self, symbol=None):
        """madde 163: borsadaki TÜM açık emirler (sembol verilmezse)."""
        if self.acik_emir_patlat:
            raise RuntimeError("APIError(code=-1003): too many requests")
        out = []
        for i, s in enumerate(sorted(self.acik_emir_sembol)):
            if symbol is not None and s != symbol:
                continue
            out.append({"symbol": s, "orderId": 900 + i,
                        "clientOrderId": "x-normal"})
        # madde 166: olay modülünün emirleri (ana bot bunlara dokunmamalı)
        for j, s in enumerate(sorted(self.olay_emir_sembol)):
            if symbol is not None and s != symbol:
                continue
            out.append({"symbol": s, "orderId": 8000 + j,
                        "clientOrderId": f"OLAY123{s[:6]}"})
        return out

    def futures_create_algo_order(self, **kw):
        """madde 437: short felaket stop'u (Binance algo emir API'si)."""
        self._aid += 1
        self.felaket_emirleri[self._aid] = (kw["symbol"], kw["side"], float(kw["triggerPrice"]),
                                            float(kw["quantity"]), dict(kw))
        self.felaket_durumu[self._aid] = "NEW"
        return {"algoId": self._aid, "algoStatus": "NEW"}

    def futures_get_algo_order(self, symbol, algoId):
        d = self.felaket_durumu.get(algoId, "CANCELED")
        return {"algoStatus": d, "actualOrderId": "777" if d == "TRIGGERED" else ""}

    def futures_cancel_algo_order(self, symbol, algoId):
        if self.felaket_durumu.get(algoId) == "NEW":
            self.felaket_durumu[algoId] = "CANCELED"

    def futures_get_order(self, symbol, orderId):
        return {"status": self.emir_durumu.get(orderId, "CANCELED")}

    def futures_cancel_order(self, symbol, orderId):
        if self.emir_durumu.get(orderId) == "NEW":
            self.emir_durumu[orderId] = "CANCELED"
        self.iptal_kar_al.append(orderId)
        if orderId >= 8000:          # madde 166: OLAY emri silindi (olmamalı)
            self.olay_emir_sembol.discard(symbol)
        elif orderId >= 900:
            self.acik_emir_sembol.discard(symbol)


class SahteClient:
    """ExchangeClient sarmalayıcısının ihtiyaç duyulan kısmı."""

    def __init__(self, bakiye=10000.0, diger_teminat=0.0, **kw):
        self.client = SahteIcClient(**kw)
        self.mode = "sahte"
        self._bakiye = bakiye
        # madde 141: BFUSD gibi USDT DIŞI teminat (USD değeri)
        self._diger = diger_teminat
        self._pozisyonlar = []

    def get_account_balance_usdt(self):
        return self._bakiye

    def get_account_equity_usd(self):
        return self._bakiye + self._diger

    def get_open_positions(self):
        return self._pozisyonlar

    def get_symbol_precision(self, symbol):
        return {"quantity_precision": 3, "price_precision": 2}

    def set_leverage(self, symbol, leverage):
        self.client.kaldirac[symbol] = leverage

    def open_market_position(self, symbol, side, quantity):
        self.client.piyasa_emirleri.append((symbol, side, quantity))
        self.client.gonderilen.append((symbol, side, "MARKET", quantity))

    def cancel_all_open_orders(self, symbol):
        self.client.iptal_edilen.append(symbol)
        self.client.acik_emir_sembol.discard(symbol)
        # GERCEK borsada toplu iptal OLAY emrini de silerdi - test bunu
        # taklit eder ki koruma calismazsa yakalansin.
        self.client.olay_emir_sembol.discard(symbol)

    def pozisyonlari_ayarla(self, hedef: dict):
        """Gönderilen emirler doldu varsayımıyla pozisyonları kur."""
        self._pozisyonlar = [
            {"symbol": s, "positionAmt": str(usd / self.client._fiyat[s]),
             "entryPrice": str(self.client._fiyat[s]),
             # madde 211: elle izoleye cekilmis semboller isaretlenebilsin
             "marginType": ("isolated" if s in self.client.izole_semboller
                            else "cross")}
            for s, usd in hedef.items()]


def temiz_ortam():
    d = tempfile.mkdtemp()
    cb.DILIM_DURUM_DOSYA = os.path.join(d, "dilim.json")
    cb.VOL_GECMIS_DOSYA = os.path.join(d, "eq.csv")
    cb.SAGLIK_DOSYA = os.path.join(d, "saglik.json")
    # MADDE 303: madde 301'in kaydettigi SIZINTI kapatildi. Bu uc satir
    # yillardir buradaydi ama madde 214'un TP_DEFTER_DOSYA'si ve madde
    # 292'nin TP_KURULUM_DOSYA'si listeye hic girmemisti: takim o iki
    # defteri PROJE DIZININE yaziyor ve kosular arasinda buyutuyordu.
    # Madde 301'de olculdu ve o gun ZARARSIZDI (bir_tur onlari yalniz
    # YAZIYOR, okuyan tek yer carry_izleme) - ama "su an okunmayan bir
    # dosya yarin okunur" (madde 301 yasa 4). Artik fikstur, urunun
    # yazdigi BUTUN dosyalari gecici dizine yonlendiriyor.
    cb.TP_DEFTER_DOSYA = os.path.join(d, "tp.csv")
    cb.TP_KURULUM_DOSYA = os.path.join(d, "tp_kurulum.csv")
    cb.PRIM_DOSYA = os.path.join(d, "prim.csv")
    cb.KALABALIK_ONBELLEK_DOSYA = os.path.join(d, "kalabalik.json")   # madde 363
    return d


# ------------------------------------------------------------------ TESTLER
print("0) VARSAYILAN AYARLAR (madde 222)")
# MADDE 222: bacak 6 -> 5. Madde 177'nin tablosu 48sa pencere (209), uc
# hareket elemesi (196), asimetrik TP (189) ve 15 dilimden (184) ONCE
# olculmustu; dort kabul yuzeyi kaydirdi ve optimum 5'e indi.
kontrol("varsayılan bacak sayısı 5 (madde 222; 6 ve 12 ESKİ)",
        _GERCEK_N_LEGS == 5, f"({_GERCEK_N_LEGS})")
kontrol("MIN_LEGS varsayılanı N_LEGS'i engellemiyor",
        _GERCEK_MIN_LEGS <= _GERCEK_N_LEGS,
        f"(MIN {_GERCEK_MIN_LEGS} > N {_GERCEK_N_LEGS})")
# madde 184: dilim sayisi 15, tur araligi 8 saat (funding araligiyla ayni)
kontrol("varsayılan dilim sayısı 15 (5 değil)", cb.N_DILIM == 15,
        f"({cb.N_DILIM})")
kontrol("tur aralığı 8 saat", abs(cb.REBALANCE_HOURS / cb.N_DILIM - 8.0) < 1e-9,
        f"({cb.REBALANCE_HOURS / cb.N_DILIM} saat)")
_gerekli = (cb.MIN_BACAK_USD * cb.N_DILIM * _GERCEK_N_LEGS
            / cb.taban_pay() / cb.GROSS_EXPOSURE)
# MADDE 222: 5 bacakta aynı bakiyede bacak %20 büyük -> gereken bakiye düşer
# MADDE 442: rezerv 0,20 -> 0,10, taban pay 0,40 -> 0,45: ~2.800$ -> ~2.500$
kontrol("tam bacak için gereken bakiye ~2.500$ (madde 442; rezerv 0,20'de ~2.800$)",
        2400 <= _gerekli <= 2600, f"({_gerekli:.0f}$)")
cb.N_LEGS, cb.MIN_LEGS = _GERCEK_N_LEGS, _GERCEK_MIN_LEGS   # gercek varsayilan
_kucuk = cb.uygun_bacak_sayisi(1200)
cb.N_LEGS, cb.MIN_LEGS = 12, 8      # testin geri kalani 12 bacak varsayiyor
kontrol("dolum kovalama varsayılan olarak AÇIK (180 sn)",
        _GERCEK_DOLUM_BEKLEME == 180.0, f"({_GERCEK_DOLUM_BEKLEME})")
kontrol("dolum kovalama en az 2 deneme yapıyor", cb.DOLUM_DENEME >= 2,
        f"({cb.DOLUM_DENEME})")
kontrol("küçük bakiyede bacak sayısı kendiliğinden düşüyor",
        _kucuk < _GERCEK_N_LEGS, f"({_kucuk})")

print("1) KURU ÇALIŞMA (--dry-run) hiç emir göndermemeli")
temiz_ortam()
c = SahteClient()
sonuc = cb.bir_tur(c, dry_run=True)
kontrol("dry-run'da BORSAYA emir gitmedi", c.client.gonderilen == [],
        f"({len(c.client.gonderilen)} emir gitti!)")
kontrol("dry-run yine de plan üretti", sonuc.get("emir", 0) > 0,
        f"({sonuc})")
kontrol("dry-run dilim durumunu KAYDETMEDİ",
        not os.path.exists(cb.DILIM_DURUM_DOSYA))

print("\n2) CANLI TUR gerçekten emir gönderiyor mu")
temiz_ortam()
c = SahteClient()
s1 = cb.bir_tur(c, dry_run=False)
kontrol("emir gönderildi (hiç emir gitmemesi sessiz arıza olurdu)",
        len(c.client.gonderilen) > 0, f"({len(c.client.gonderilen)})")
kontrol("gönderilen emir sayısı planla uyuşuyor",
        s1.get("basarili", 0) == len(c.client.gonderilen),
        f"(plan {s1.get('basarili')}, gerçek {len(c.client.gonderilen)})")
kontrol("emirler LIMIT tipinde (maker)",
        all(e[2] == "LIMIT" for e in c.client.gonderilen) or not cb.LIMIT_EMIR,
        f"({set(e[2] for e in c.client.gonderilen)})")
kontrol("dilim durumu KAYDEDİLDİ", os.path.exists(cb.DILIM_DURUM_DOSYA))

print("\n3) EMİR YÖNÜ — funding yüksek olan SHORT'lanıyor mu")
# C0 en negatif funding -> LONG (BUY), C79 en pozitif -> SHORT (SELL)
yonler = {e[0]: e[1] for e in c.client.gonderilen}
dusuk = [f"C{i}USDT" for i in range(5)]
yuksek = [f"C{i}USDT" for i in range(75, 80)]
alinan_dusuk = [yonler[s] for s in dusuk if s in yonler]
alinan_yuksek = [yonler[s] for s in yuksek if s in yonler]
kontrol("en DÜŞÜK funding'liler BUY (long)",
        alinan_dusuk and all(y == "BUY" for y in alinan_dusuk),
        f"({alinan_dusuk})")
kontrol("en YÜKSEK funding'liler SELL (short)",
        alinan_yuksek and all(y == "SELL" for y in alinan_yuksek),
        f"({alinan_yuksek})")

print("\n4) İKİNCİ TUR — tolerans gereksiz işlemi engelliyor mu")
durum = cb.dilim_durum_oku()
c.pozisyonlari_ayarla(cb.toplam_hedef(durum))
onceki = len(c.client.gonderilen)
cb.bir_tur(c, dry_run=False)
yeni_emir = len(c.client.gonderilen) - onceki
# NOT: dilimli yapıda ilk N tur portföyü KADEMELİ büyütür (her tur bir
# dilim daha eklenir), bu yüzden emir sayısı hemen düşmez. Kritik olan
# aynı turu TEKRARLAYINCA yeni emir çıkmaması - yani tolerans çalışması.
kontrol("ikinci tur dilim ekledi (emir üretti)", yeni_emir > 0, f"({yeni_emir})")
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
durum_once = cb.dilim_durum_oku()
onceki2 = len(c.client.gonderilen)
# Aynı dilimi aynı veriyle tekrar yaz -> hedef değişmemeli -> emir olmamalı
durum_once["sira"] = (durum_once["sira"] - 1) % cb.N_DILIM
cb.dilim_durum_yaz(durum_once)
cb.bir_tur(c, dry_run=False)
kontrol("AYNI dilim aynı veriyle tekrarlanınca emir ÜRETMİYOR (tolerans)",
        len(c.client.gonderilen) - onceki2 == 0,
        f"({len(c.client.gonderilen) - onceki2} gereksiz emir)")

print("\n5) DİLİM DÖNGÜSÜ ilerliyor mu")
temiz_ortam()
c = SahteClient()
siralar = []
for _ in range(cb.N_DILIM + 2):
    r = cb.bir_tur(c, dry_run=False)
    siralar.append(r.get("dilim"))
    c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
kontrol("dilim sırası her turda ilerliyor",
        siralar[:cb.N_DILIM] == list(range(cb.N_DILIM)), f"({siralar})")
kontrol("N tur sonra başa dönüyor",
        siralar[cb.N_DILIM] == 0, f"({siralar})")
d = cb.dilim_durum_oku()
kontrol("tüm dilimler doldu", len(d["dilimler"]) == cb.N_DILIM,
        f"({len(d['dilimler'])})")

print("\n6) PORTFÖY BÜTÜNLÜĞÜ (tam dolu döngüde)")
hedef = cb.toplam_hedef(d)
uzun = sum(v for v in hedef.values() if v > 0)
kisa = -sum(v for v in hedef.values() if v < 0)
kontrol("long ve short tarafı dengeli (fark <%5)",
        abs(uzun - kisa) / max(uzun, kisa, 1) < 0.05,
        f"(long {uzun:.0f}, short {kisa:.0f})")
brut = sum(abs(v) for v in hedef.values())
kontrol("brüt pozisyon makul aralıkta (0.5x-4x bakiye)",
        0.5 * c._bakiye <= brut <= 4 * c._bakiye,
        f"(brüt {brut:.0f}, bakiye {c._bakiye:.0f})")

print("\n7) HATA DAYANIKLILIĞI")
temiz_ortam()
bozuk = {f"C{i}USDT" for i in range(0, 80, 3)}   # sembollerin 1/3'ü patlıyor
c = SahteClient(funding_bozuk=bozuk)
try:
    r = cb.bir_tur(c, dry_run=True)
    kontrol("bazı semboller API hatası verse de tur tamamlanıyor", True)
    # 53 sembol kaldı, 60 gerekiyordu -> bacak KÜÇÜLTÜLEREK devam etmeli
    kontrol("yetersiz sembolde bacak küçültülerek devam ediliyor",
            r.get("emir", 0) > 0, f"({r})")
    kontrol("küçültülmüş portföy hâlâ dengeli",
            abs(sum(r.get("hedef", {}).values())) < 1.0,
            f"(net {sum(r.get('hedef', {}).values()):.2f})")
except Exception as e:
    kontrol("bazı semboller API hatası verse de tur tamamlanıyor", False, str(e))
temiz_ortam()
c2 = SahteClient(n_sembol=20)        # 10+10 bacak -> MIN_LEGS'in üstünde
r2 = cb.bir_tur(c2, dry_run=False)
kontrol("20 sembolde küçülterek devam ediyor (taraf başına beklenen bacak)",
        len(c2.client.gonderilen) == 2 * beklenen_bacak(), f"({len(c2.client.gonderilen)} emir)")
kontrol("küçültülmüş portföy de dengeli",
        abs(sum(r2.get("hedef", {}).values())) < 1.0,
        f"(net {sum(r2.get('hedef', {}).values()):.2f})")
temiz_ortam()
c3 = SahteClient(n_sembol=10)        # 5+5 -> MIN_LEGS(8) ALTINDA
r3 = cb.bir_tur(c3, dry_run=False)
kontrol("MIN_LEGS altında HİÇ emir göndermiyor (yoğunlaşma koruması)",
        c3.client.gonderilen == [], f"({len(c3.client.gonderilen)} emir)")

print("\n8) EVREN FİLTRELERİ (madde 133)")
temiz_ortam()
# 8a) yeni listelenenler elenir
yeniler = {f"C{i}USDT" for i in range(0, 80, 2)}      # yarısı "dün listelendi"
c4 = SahteClient(n_sembol=80, yeni_semboller=yeniler)
ev = cb.evren_sec(c4)
kontrol("yeni listelenen semboller evrene ALINMIYOR",
        ev and not (set(ev) & yeniler), f"({len(set(ev) & yeniler)} yeni sızdı)")
kontrol("eski semboller evrende KALIYOR", len(ev) == 40, f"({len(ev)})")

# 8b) exchange_info alınamazsa filtre devre dışı ama bot DURMUYOR.
# Bu, projenin 7 kez yakaladığı "sessiz duruş" sınıfının tam örneği:
# veri gelmiyor diye evreni boşaltmak, botu hiç işlem yapmaz hale getirir.
c5 = SahteClient(n_sembol=80, yeni_semboller=yeniler,
                 exchange_info_patlat=True)
ev5 = cb.evren_sec(c5)
kontrol("exchange_info patlarsa evren BOŞALMIYOR (sessiz duruş yok)",
        len(ev5) == 80, f"({len(ev5)})")

# 8c) hacim eşiğinin altındakiler elenir
class DusukHacim(SahteIcClient):
    def futures_ticker(self):
        # ilk 40'ı eşik altında bırak
        return [{"symbol": s,
                 "quoteVolume": str(1_000_000 if i < 40 else 150_000_000)}
                for i, s in enumerate(self._fiyat)]

c6 = SahteClient(n_sembol=80)
c6.client = DusukHacim(n_sembol=80)
ev6 = cb.evren_sec(c6)
kontrol("hacim eşiği altındakiler ELENİYOR", len(ev6) == 40, f"({len(ev6)})")

# 8d) filtre eşiği gerçekten okunuyor mu (sabit kodlanmış değil)
_eski = cb.MIN_DAILY_VOLUME_USD
cb.MIN_DAILY_VOLUME_USD = 1_000_000_000.0
kontrol("eşik yükseltilince evren boşalıyor (eşik CANLI okunuyor)",
        cb.evren_sec(c6) == [])
cb.MIN_DAILY_VOLUME_USD = _eski

_eskiy = cb.MIN_LISTELEME_GUN
cb.MIN_LISTELEME_GUN = 0
kontrol("yaş filtresi 0 ile KAPATILABİLİYOR",
        len(cb.evren_sec(c4)) == 80, f"({len(cb.evren_sec(c4))})")
cb.MIN_LISTELEME_GUN = _eskiy

print("\n9) EDGE SAĞLIK KAPISI (madde 139)")
import json as _json
_eski_mod = cb.SAGLIK_MODU

# 9a) sağlıklı borsada dedektör GERÇEKTEN ölçüyor mu (ısınmada kalmıyor)
temiz_ortam(); cb.SAGLIK_MODU = "durdur"
c = SahteClient()
r = cb.bir_tur(c, dry_run=False)
kontrol("sağlıklı funding'de durum SAGLIKLI (ISINMA değil - gerçekten ölçüyor)",
        r.get("saglik") == "SAGLIKLI", f"({r.get('saglik')})")
kontrol("sağlıklıyken normal işlem yapılıyor",
        len(c.client.gonderilen) > 0 and r.get("kapi") != "KAPALI")
kontrol("funding geçmişi gerçekten çekildi", c.client.gecmis_cagri > 0,
        f"({c.client.gecmis_cagri} çağrı)")
kontrol("kapı durumu dosyaya yazıldı", os.path.exists(cb.SAGLIK_DOSYA))

# 9b) edge ölünce: mevcut pozisyonların HEPSİ kapatılıyor mu
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
acik_poz = {p["symbol"]: float(p["positionAmt"]) for p in c.get_open_positions()}
c.client.saglik_ters = True
c.client.gonderilen = []
r = cb.bir_tur(c, dry_run=False)
kontrol("kalıcılık ölünce durum BOZUK", r.get("saglik") == "BOZUK", f"({r.get('saglik')})")
kontrol("kapı KAPALI", r.get("kapi") == "KAPALI", f"({r})")
gonderilen = {e[0]: e[1] for e in c.client.gonderilen}
kontrol("açık pozisyonların HEPSİNE kapatma emri gitti",
        set(gonderilen) == set(acik_poz),
        f"({len(gonderilen)} emir / {len(acik_poz)} pozisyon)")
ters = all((gonderilen[s] == "SELL") == (acik_poz[s] > 0) for s in gonderilen)
kontrol("kapatma emirleri pozisyonun TERSİ yönde", ters)
kontrol("yeni pozisyon AÇILMADI (sadece kapatma)",
        set(gonderilen) <= set(acik_poz))
kontrol("dilimler sıfırlandı (yeniden açılınca bayat hedef dirilmesin)",
        cb.dilim_durum_oku().get("dilimler") == {})
kontrol("kapı dosyada kapalı",
        _json.load(open(cb.SAGLIK_DOSYA)).get("acik") is False)

# 9c) ertesi tur hâlâ bozuk: kapalı kalıyor, yeni pozisyon açmıyor
c.pozisyonlari_ayarla({})
c.client.gonderilen = []
r = cb.bir_tur(c, dry_run=False)
kontrol("kapalıyken ertesi turda da işlem AÇILMADI",
        c.client.gonderilen == [] and r.get("kapi") == "KAPALI",
        f"({len(c.client.gonderilen)} emir)")

# 9d) mod=uyar: bozukken bile işlem akışı DEĞİŞMEZ
temiz_ortam(); cb.SAGLIK_MODU = "uyar"
c = SahteClient(saglik_ters=True)
r = cb.bir_tur(c, dry_run=False)
kontrol("uyar modunda bozuk tespit ediliyor", r.get("saglik") == "BOZUK", f"({r.get('saglik')})")
kontrol("uyar modunda yine de işlem yapılıyor", len(c.client.gonderilen) > 0)

# 9e) kuru çalışma kapıyı DEĞİŞTİRMEZ
temiz_ortam(); cb.SAGLIK_MODU = "durdur"
c = SahteClient(saglik_ters=True)
r = cb.bir_tur(c, dry_run=True)
kontrol("dry-run'da bozuk tespit ediliyor", r.get("saglik") == "BOZUK")
kontrol("dry-run'da BORSAYA emir gitmedi", c.client.gonderilen == [])
kontrol("dry-run kapı dosyasını YAZMADI", not os.path.exists(cb.SAGLIK_DOSYA))

# 9f) geçmiş API'si patlarsa bot DURMUYOR (sessiz duruş yok)
temiz_ortam()
c = SahteClient(gecmis_patlat=True)
r = cb.bir_tur(c, dry_run=False)
kontrol("geçmiş alınamazsa durum ISINMA", r.get("saglik") == "ISINMA", f"({r.get('saglik')})")
kontrol("geçmiş alınamazsa bot yine de işlem yapıyor", len(c.client.gonderilen) > 0)

# 9g) mod=kapali: hiç API çağrısı yapılmıyor
temiz_ortam(); cb.SAGLIK_MODU = "kapali"
c = SahteClient(saglik_ters=True)
r = cb.bir_tur(c, dry_run=False)
kontrol("kapali modda funding geçmişi hiç çekilmedi", c.client.gecmis_cagri == 0,
        f"({c.client.gecmis_cagri})")
kontrol("kapali modda normal işlem", len(c.client.gonderilen) > 0)
cb.SAGLIK_MODU = _eski_mod

# 9h) MADDE 262: iki ölü-edge kurgusunun DAVRANIŞI kayda geçiyor.
# `saglik_ters` DETERMİNİSTİK olmalı (her tarihte kapatır); `saglik_bozuk`
# (karıştırma) rastgele bir çekiliştir ve her tarihte kapatmaz - sekiz
# testin 2026-10-04'te birden düşmesinin sebebi buydu. Mekanizma
# testlerinin hangisine dayanabileceği artık ÖLÇÜLÜYOR, varsayılmıyor.
temiz_ortam(); cb.SAGLIK_MODU = "durdur"
_simdi = int(time.time() * 1000)
_tarihler = [_simdi - k * 30 * 86400000 for k in range(6)]
_ters_durum, _bozuk_durum = [], []
for _t262 in _tarihler:
    _c = SahteClient(saglik_ters=True)
    _sem = list(_c.client._funding)[:60]
    _ters_durum.append(cb.saglik_kontrol(
        _c, _sem, simdi_ms=_t262, dosya="/tmp/sg262_ters.json", yaz=False)[1])
    _c = SahteClient(saglik_bozuk=True)
    _bozuk_durum.append(cb.saglik_kontrol(
        _c, _sem, simdi_ms=_t262, dosya="/tmp/sg262_bozuk.json", yaz=False)[1])
kontrol("madde 262: TERS edge altı tarihin HEPSİNDE kapıyı kapatıyor",
        all(d == "BOZUK" for d in _ters_durum), f"({_ters_durum})")
kontrol("madde 262: KARIŞTIRMA kurgusu her tarihte kapatmıyor (flaky - kayda geçti)",
        not all(d == "BOZUK" for d in _bozuk_durum), f"({_bozuk_durum})")
kontrol("madde 262: karıştırma kurgusu ATIL da değil (en az bir tarihte kapatıyor)",
        any(d == "BOZUK" for d in _bozuk_durum), f"({_bozuk_durum})")
for _f in ("/tmp/sg262_ters.json", "/tmp/sg262_bozuk.json"):
    if os.path.exists(_f):
        os.remove(_f)

print("\n10) TEMİNAT MODU — BFUSD gibi USDT dışı teminat (madde 141)")
_eski_tm = cb.TEMINAT_MODU
temiz_ortam(); cb.TEMINAT_MODU = "usdt"
c = SahteClient(bakiye=10000.0)
r = cb.bir_tur(c, dry_run=False)
kontrol("sadece USDT varken normal işlem", len(c.client.gonderilen) > 0 and "atlandi" not in r)

temiz_ortam()
c = SahteClient(bakiye=20.0, diger_teminat=9980.0)      # teminatın çoğu BFUSD
r = cb.bir_tur(c, dry_run=False)
kontrol("USDT modunda BFUSD tespit edilince tur ATLANIYOR (sessizce ~0 boyutlama yok)",
        r.get("atlandi") == "teminat" and c.client.gonderilen == [], f"({r})")

temiz_ortam(); cb.TEMINAT_MODU = "coklu"
c = SahteClient(bakiye=20.0, diger_teminat=9980.0)
r = cb.bir_tur(c, dry_run=False)
kontrol("çoklu modda BFUSD teminatıyla işlem yapılıyor", len(c.client.gonderilen) > 0, f"({r})")
kontrol("çoklu modda sermaye TOPLAM teminattan okunuyor",
        abs(r.get("bakiye", 0) - 10000.0) < 1e-6, f"({r.get('bakiye')})")
tr = SahteClient(bakiye=10000.0); temiz_ortam(); cb.TEMINAT_MODU = "usdt"
r_usdt = cb.bir_tur(tr, dry_run=False)
_hac = lambda cl: sum(m * cl.client._fiyat[s_] for s_, _, _, m in cl.client.gonderilen)
kontrol("çoklu modda pozisyon büyüklüğü, aynı sermayeli USDT hesabıyla aynı",
        abs(_hac(c) - _hac(tr)) / _hac(tr) < 0.01, f"({_hac(c):.0f} vs {_hac(tr):.0f})")
cb.TEMINAT_MODU = _eski_tm

print("\n11) TRADFI (hisse/emtia perp) ELEME (madde 142)")
temiz_ortam()
_tf = {f"C{i}USDT" for i in range(0, 80, 4)}
c = SahteClient(tradfi_semboller=_tf)
ev = cb.evren_sec(c)
kontrol("TRADIFI_PERPETUAL semboller evrene ALINMIYOR",
        not (set(ev) & _tf), f"({len(set(ev) & _tf)} sızdı)")
kontrol("kripto semboller evrende kalıyor", len(ev) == 60, f"({len(ev)})")
_eski_tf = cb.TRADFI_HARIC; cb.TRADFI_HARIC = False
kontrol("CARRY_TRADFI_HARIC=0 ile kapatılabiliyor", len(cb.evren_sec(c)) == 80)
cb.TRADFI_HARIC = _eski_tf
c.client.gonderilen = []
r = cb.bir_tur(c, dry_run=False)
kontrol("tam turda TradFi sembole HİÇ emir gitmedi",
        not ({e[0] for e in c.client.gonderilen} & _tf) and len(c.client.gonderilen) > 0)

print("\n11b) DELİSTİ DUYURULMUŞ SEMBOL (madde 146)")
temiz_ortam()
# C0-C3 en negatif funding = long adayları; C76-C79 short adayları
_dl = {"C0USDT", "C1USDT", "C78USDT", "C79USDT"}
c = SahteClient(delist_semboller=_dl)
ev = cb.evren_sec(c)
kontrol("delisti duyurulan semboller evrene ALINMIYOR",
        not (set(ev) & _dl), f"({len(set(ev) & _dl)} sızdı)")
kontrol("diğer semboller evrende kalıyor", len(ev) == 76, f"({len(ev)})")
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
kontrol("tam turda delist sembolüne AÇILIŞ emri gitmedi",
        not ({e[0] for e in c.client.gonderilen} & _dl) and len(c.client.gonderilen) > 0)
kontrol("delist sembolleri yerine başka coin seçildi (bacak boş kalmadı)",
        len({e[0] for e in c.client.gonderilen}) == 2 * beklenen_bacak(),
        f"({len({e[0] for e in c.client.gonderilen})})")

print("\n11c) KALABALIK SEÇİMİ (madde 148)")
temiz_ortam()
c = SahteClient()
# long havuzu en negatif funding'liler (~C0..C23): C10-C40 short-kalabalık (oran 0.5)
# short havuzu en pozitifler (~C56..C79): C40-C69 long-kalabalık (oran 3.0)
for i in range(80):
    s_ = f"C{i}USDT"
    c.client.ls_oran[s_] = 0.5 if 10 <= i < 40 else (3.0 if 40 <= i < 70 else 1.0)
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
_al = {e[0] for e in c.client.gonderilen if e[1] == "BUY"}
_sat = {e[0] for e in c.client.gonderilen if e[1] == "SELL"}
# Aday sayısı = 2 taraf x HAVUZ x N_LEGS. Sabit "4 x N_LEGS" sınırı
# havuz 2.0 varsayıyordu; madde 179'da 3.0 olunca kırıldı. Sınır artık
# FORMÜLDEN türetiliyor - havuz değişince test de doğru kalsın.
_azami = int(2 * cb.KALABALIK_HAVUZ * cb.N_LEGS)
kontrol("oran sadece ADAYLAR için çekildi (tüm evren değil)",
        0 < c.client.ls_cagri <= _azami,
        f"({c.client.ls_cagri} çağrı, azami {_azami}, evren {c.client.n})")
kontrol("LONG bacakların hepsi short-kalabalık (oran 0.5)",
        len(_al) == beklenen_bacak() and all(c.client.ls_oran[x] == 0.5 for x in _al),
        f"({sorted(_al)})")
kontrol("SHORT bacakların hepsi long-kalabalık (oran 3.0)",
        len(_sat) == beklenen_bacak() and all(c.client.ls_oran[x] == 3.0 for x in _sat),
        f"({sorted(_sat)})")
kontrol("en uç funding'li ama kalabalık OLMAYAN C0-C9 long'lanmadı",
        not (_al & {f"C{i}USDT" for i in range(10)}))

temiz_ortam()
c2 = SahteClient(); c2.client.ls_patlat = True
c2.client.gonderilen = []
cb.bir_tur(c2, dry_run=False)
_al2 = {e[0] for e in c2.client.gonderilen if e[1] == "BUY"}
temiz_ortam()
c3 = SahteClient(); _eski_kh = cb.KALABALIK_HAVUZ; cb.KALABALIK_HAVUZ = 1.0
c3.client.gonderilen = []
cb.bir_tur(c3, dry_run=False)
cb.KALABALIK_HAVUZ = _eski_kh
_al3 = {e[0] for e in c3.client.gonderilen if e[1] == "BUY"}
kontrol("oran API'si patlarsa bot DURMUYOR, eski seçime (en uç n) düşüyor",
        len(_al2) == beklenen_bacak() and _al2 == _al3, f"({len(_al2)} long)")
kontrol("CARRY_KALABALIK_HAVUZ=1 ile kapatılabiliyor (oran hiç çekilmiyor)",
        c3.client.ls_cagri == 0)

print("\n11c2) ORAN API'Sİ SUSARSA SON BİLİNEN ORAN (madde 363)")
# Aynı kalabalık senaryosu (C10-C40 short-kalabalık, C40-C70 long-kalabalık):
# önce taze oranla bir tur (önbellek dolar), sonra API patlar.
def _kalabalik_istemci():
    c_ = SahteClient()
    for i in range(80):
        c_.client.ls_oran[f"C{i}USDT"] = 0.5 if 10 <= i < 40 else (3.0 if 40 <= i < 70 else 1.0)
    c_.client.gonderilen = []
    return c_
temiz_ortam()
_ca = _kalabalik_istemci(); cb.bir_tur(_ca, dry_run=False)
_al_taze = {e[0] for e in _ca.client.gonderilen if e[1] == "BUY"}
kontrol("taze turda önbellek dosyası yazıldı",
        os.path.exists(cb.KALABALIK_ONBELLEK_DOSYA))
_ob_dosya = cb.KALABALIK_ONBELLEK_DOSYA
# (a) API patlıyor, önbellek TAZE -> kalabalık seçimi korunur
cb.DILIM_DURUM_DOSYA = os.path.join(tempfile.mkdtemp(), "dilim.json")
_cb2 = _kalabalik_istemci(); _cb2.client.ls_patlat = True
cb.bir_tur(_cb2, dry_run=False)
_al_ob = {e[0] for e in _cb2.client.gonderilen if e[1] == "BUY"}
kontrol("API susunca 24 sa içindeki önbellekle kalabalık seçimi KORUNUYOR",
        _al_ob == _al_taze and all(_cb2.client.ls_oran[x] == 0.5 for x in _al_ob),
        f"({sorted(_al_ob)} vs {sorted(_al_taze)})")
# (b) önbellek BAYAT (25 sa) -> eski yedek (en uç n)
with open(_ob_dosya, encoding="utf-8") as _fh:
    _ob = json.load(_fh)
_ob = {k: [v[0], v[1] - 25 * 3600] for k, v in _ob.items()}
with open(_ob_dosya, "w", encoding="utf-8") as _fh:
    json.dump(_ob, _fh)
cb.DILIM_DURUM_DOSYA = os.path.join(tempfile.mkdtemp(), "dilim.json")
_cc = _kalabalik_istemci(); _cc.client.ls_patlat = True
cb.bir_tur(_cc, dry_run=False)
_al_bayat = {e[0] for e in _cc.client.gonderilen if e[1] == "BUY"}
kontrol("24 saatten eski önbellek KULLANILMIYOR (en uç n yedeğine düşüyor)",
        _al_bayat != _al_taze and not all(_cc.client.ls_oran[x] == 0.5 for x in _al_bayat),
        f"({sorted(_al_bayat)})")
# (c) CARRY_KALABALIK_BAYAT_SAAT=0 -> önbellek okunmaz
_eski_bs = cb.KALABALIK_BAYAT_SAAT; cb.KALABALIK_BAYAT_SAAT = 0
_s0, _n0 = cb.kalabalik_onbellekle_tamamla(pd.Series(dtype=float), ["C10USDT"],
                                            dosya=_ob_dosya)
cb.KALABALIK_BAYAT_SAAT = _eski_bs
kontrol("CARRY_KALABALIK_BAYAT_SAAT=0 ile önbellek kapalı", _n0 == 0 and len(_s0) == 0)

print("\n11d) ÇAPRAZ TEMİNAT VE BORSA KALDIRACI (madde 149)")
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
_emir = {e[0] for e in c.client.gonderilen}
kontrol("emir giden HER sembol ÇAPRAZ teminata alındı",
        len(_emir) > 0 and all(c.client.teminat.get(x) == "CROSSED" for x in _emir))
kontrol("borsa kaldıracı gereken seviyede (kaldıraçsızda 2x, 1x DEĞİL)",
        all(c.client.kaldirac.get(x) == cb.gerekli_kaldirac() == 2 for x in _emir),
        f"({set(c.client.kaldirac.values())})")
_say = len(c.client.kaldirac); c.client.kaldirac.clear()
cb.bir_tur(c, dry_run=False)
kontrol("ayar süreç başına BİR kez yapılıyor (ikinci turda tekrar yok)",
        len(c.client.kaldirac) == 0 or set(c.client.kaldirac) - _emir == set(c.client.kaldirac))

temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
_hedef_sem = sorted(cb.toplam_hedef(cb.dilim_durum_oku()) or {})
c.client.teminat_patlat = {f"C{i}USDT" for i in range(80)}
c.client.zaten_capraz = {"C0USDT", "C1USDT", "C2USDT", "C3USDT", "C4USDT", "C5USDT",
                         "C79USDT", "C78USDT", "C77USDT", "C76USDT", "C75USDT", "C74USDT"}
c.client.teminat_patlat -= c.client.zaten_capraz
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
_emir = {e[0] for e in c.client.gonderilen}
kontrol("çapraz teminata ALINAMAYAN sembole emir gitmedi",
        not (_emir & c.client.teminat_patlat), f"({len(_emir & c.client.teminat_patlat)} sızdı)")
kontrol("çapraz teminata alınamayanda kaldıraç YÜKSELTİLMEDİ",
        not (set(c.client.kaldirac) & c.client.teminat_patlat))
kontrol("'zaten çapraz' (-4046) hatası çapraz sayılıyor, kaldıraç ayarlanıyor",
        all(c.client.kaldirac.get(x) == 2 for x in _emir) and len(_emir) > 0 and _emir <= c.client.zaten_capraz)
cb._KALDIRAC_AYARLI.clear()

print("\n11e) FIRSAT REZERVİ TAM TURDA (madde 156)")
_rez11e = cb.REZERV_PAY
cb.REZERV_PAY = 0.20   # madde 442: mekanizma eşikleri (1,5x) rezerv 0,20 ile yazıldı
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
_hac_normal = sum(m * c.client._fiyat[s_] for s_, _, _, m in c.client.gonderilen)
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c2 = SahteClient()
c2.client.uc_funding = {"C0USDT": -0.006, "C1USDT": -0.006}   # yıllık ~-%657
c2.client.gonderilen = []
cb.bir_tur(c2, dry_run=False)
_buyukluk = {}
for s_, yon, _, m in c2.client.gonderilen:
    _buyukluk[s_] = _buyukluk.get(s_, 0) + m * c2.client._fiyat[s_]
_uc_ort = (_buyukluk.get("C0USDT", 0) + _buyukluk.get("C1USDT", 0)) / 2
_dig = [v for k, v in _buyukluk.items() if k not in ("C0USDT", "C1USDT")
        and k in {e[0] for e in c2.client.gonderilen if e[1] == "BUY"}]
_dig_ort = sum(_dig) / max(1, len(_dig))
# MADDE 333: bu uc sayi HER KOSUDA basilir (bkz. kontrol() docstring).
print("       [tani] uc=%.1f dig=%.1f n_dig=%d n_emir=%d oran=%.3f"
      % (_uc_ort, _dig_ort, len(_dig), len(c2.client.gonderilen),
         _uc_ort / max(1e-9, _dig_ort)))
kontrol("uç funding'li coine DAHA BÜYÜK pozisyon açıldı",
        _uc_ort > 1.5 * _dig_ort,
        f"(oran {_uc_ort/max(1e-9,_dig_ort):.3f}; uc {_uc_ort:.1f} vs "
        f"dig {_dig_ort:.1f}; n_dig {len(_dig)}; "
        f"n_emir {len(c2.client.gonderilen)}) "
        f"[madde 333: izole olcumde oran HER ZAMAN 2,500 - sapma "
        f"paketin ORTASINDAKI duruma isaret eder]",
        her_zaman=True)
kontrol("uç yokken toplam pozisyon rezerv kadar KÜÇÜK (sermaye bekliyor)",
        _hac_normal < sum(_buyukluk.values()) * 0.95,
        f"({_hac_normal:.0f} vs {sum(_buyukluk.values()):.0f})")
_al2 = sum(v for k, v in _buyukluk.items() if k in {e[0] for e in c2.client.gonderilen if e[1] == "BUY"})
_sat2 = sum(v for k, v in _buyukluk.items() if k in {e[0] for e in c2.client.gonderilen if e[1] == "SELL"})
kontrol("rezerv açıkken portföy hâlâ NÖTR (long ~ short)",
        abs(_al2 - _sat2) / max(_al2, _sat2) < 0.02, f"({_al2:.0f} vs {_sat2:.0f})")

cb.REZERV_PAY = _rez11e
# MADDE 442: varsayılan rezerv 0,10'da da uç coin DAHA BÜYÜK (oran küçülür ama > 1)
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c3 = SahteClient()
c3.client.uc_funding = {"C0USDT": -0.006, "C1USDT": -0.006}
c3.client.gonderilen = []
cb.bir_tur(c3, dry_run=False)
_b3 = {}
for s_, yon, _, m in c3.client.gonderilen:
    _b3[s_] = _b3.get(s_, 0) + m * c3.client._fiyat[s_]
_u3 = (_b3.get("C0USDT", 0) + _b3.get("C1USDT", 0)) / 2
_d3 = [v for k, v in _b3.items() if k not in ("C0USDT", "C1USDT")
       and k in {e[0] for e in c3.client.gonderilen if e[1] == "BUY"}]
kontrol("rezerv 0,10 (T60 varsayılanı) ile de uç coine daha büyük pozisyon",
        _u3 > 1.2 * (sum(_d3) / max(1, len(_d3))),
        f"(uc {_u3:.1f} vs dig {sum(_d3) / max(1, len(_d3)):.1f})")

print("\n11f) EMİR REDDİNDE YENİDEN DENEME (madde 160)")
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
# C0: ilk deneme reddedilir -> 2. denemede geçmeli | C79: hepsi reddedilir -> piyasa emri
c.client.gtx_red = {"C0USDT": 1, "C79USDT": 9}
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
_f0 = c.client.gtx_fiyatlar.get("C0USDT", [])
kontrol("reddedilen emir DAHA UZAK fiyatla yeniden deneniyor",
        len(_f0) >= 2 and _f0[1] < _f0[0], f"({_f0[:3]})")
kontrol("2. denemede geçen bacak AÇILDI",
        "C0USDT" in {e[0] for e in c.client.gonderilen}, "(C0 yok)")
kontrol("limit hiç geçmezse PİYASA emrine düşülüyor",
        "C79USDT" in {x[0] for x in c.client.piyasa_emirleri},
        f"({c.client.piyasa_emirleri})")
kontrol("piyasa yedeği sadece GEREKTİĞİNDE kullanılıyor",
        len(c.client.piyasa_emirleri) == 1, f"({len(c.client.piyasa_emirleri)})")
kontrol("deneme sayısı sınırlı (sonsuz döngü yok)",
        len(c.client.gtx_fiyatlar.get("C79USDT", [])) == len(cb.GTX_DENEME_CARPANLARI),
        f"({len(c.client.gtx_fiyatlar.get('C79USDT', []))})")
_eski_py = cb.PIYASA_YEDEK
cb.PIYASA_YEDEK = False
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c2 = SahteClient(); c2.client.gtx_red = {"C79USDT": 9}; c2.client.gonderilen = []
cb.bir_tur(c2, dry_run=False)
kontrol("CARRY_PIYASA_YEDEK=0 ile piyasa emri KULLANILMIYOR",
        not c2.client.piyasa_emirleri and "C79USDT" not in {e[0] for e in c2.client.gonderilen})
cb.PIYASA_YEDEK = _eski_py

print("\n11g) BAYAT EMİR TEMİZLİĞİ (madde 163)")
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
# ZOMBI: portföyde olmayan, emir listesine GİRMEYECEK bir sembolde asılı emir.
# Eski kod bunu hiç iptal etmiyordu -> günler sonra dolup korumasız pozisyon açardı.
c.client.acik_emir_sembol = {"C40USDT"}
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
_ip = set(c.client.iptal_edilen)
kontrol("emir listesi DIŞINDAKİ bayat emir iptal ediliyor",
        "C40USDT" in _ip, f"(iptal: {sorted(_ip)[:6]})")
kontrol("bayat emir borsada kalmıyor",
        "C40USDT" not in c.client.acik_emir_sembol)
kontrol("işlem görecek semboller de temizleniyor (bayat limit fiyat riski)",
        len({e[0] for e in c.client.gonderilen} & _ip) > 0)
kontrol("zombi sembolde POZİSYON açılmıyor (sadece iptal)",
        "C40USDT" not in {e[0] for e in c.client.gonderilen})
# API listeyi veremezse: eski davranışa düş, tur ÇÖKMESİN
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c2 = SahteClient()
c2.client.acik_emir_patlat = True
c2.client.acik_emir_sembol = {"C40USDT"}
c2.client.gonderilen = []
_s = cb.bir_tur(c2, dry_run=False)
kontrol("açık emir listesi alınamazsa tur ÇÖKMÜYOR",
        isinstance(_s, dict) and _s.get("basarili", 0) > 0, f"({_s})")
kontrol("liste alınamazsa en azından işlem görecekler iptal ediliyor",
        len(c2.client.iptal_edilen) > 0)
# Doğrudan birim davranış: iptal edilen sembol kümesi = açık emirler ∪ emir listesi
temiz_ortam()
c3 = SahteClient()
c3.client.acik_emir_sembol = {"C1USDT", "C2USDT"}
cb.bayat_emirleri_temizle(c3, [("C3USDT", "BUY", 100.0)])
kontrol("temizlik AÇIK EMİRLER ∪ EMİR LİSTESİ kümesini kapsıyor",
        set(c3.client.iptal_edilen) == {"C1USDT", "C2USDT", "C3USDT"},
        f"({sorted(c3.client.iptal_edilen)})")

print("\n11h) OLAY MODÜLÜYLE BİRLİKTE ÇALIŞMA (madde 166)")
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
c.client.acik_emir_sembol = {"C40USDT"}
c.client.olay_emir_sembol = {"C41USDT"}       # olay modülünün bekleyen emri
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
kontrol("OLAY emri HAYATTA (ana bot dokunmadı)",
        "C41USDT" in c.client.olay_emir_sembol,
        f"({c.client.olay_emir_sembol})")
kontrol("normal bayat emir yine de silindi",
        "C40USDT" not in c.client.acik_emir_sembol)
# olay emri AYNI sembolde bir de normal emir varsa: normal silinir, olay kalır
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient()
c.client.acik_emir_sembol = {"C42USDT"}; c.client.olay_emir_sembol = {"C42USDT"}
cb.bir_tur(c, dry_run=False)
kontrol("aynı sembolde normal emir silinir, OLAY emri kalır",
        "C42USDT" in c.client.olay_emir_sembol
        and "C42USDT" not in c.client.acik_emir_sembol,
        f"(olay={c.client.olay_emir_sembol}, normal={c.client.acik_emir_sembol})")
# KİLİT: olay penceresi açıkken ana tur atlanmalı
import carry_olay as _co
_kilit = tempfile.mktemp(suffix=".json")
_eski_kilit = _co.KILIT; _co.KILIT = _kilit
_co.kilit_yaz(_kilit, ["C0USDT"])
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient(); c.client.gonderilen = []
_s = cb.bir_tur(c, dry_run=False)
kontrol("olay penceresi AÇIKKEN ana tur ATLANIYOR",
        _s.get("atlandi") == "olay_kilidi" and not c.client.gonderilen, f"({_s})")
_co.kilit_sil(_kilit)
temiz_ortam(); cb._KALDIRAC_AYARLI.clear()
c = SahteClient(); c.client.gonderilen = []
_s = cb.bir_tur(c, dry_run=False)
kontrol("kilit kalkınca ana tur normal çalışıyor",
        _s.get("basarili", 0) > 0, f"({_s})")
_co.KILIT = _eski_kilit

print("\n12) KÂR AL (madde 143)")
_eski_ka = cb.KAR_AL_ORAN
_eski_mr = cb.MERDIVEN
cb.MERDIVEN = 0.0   # madde 465: bu bölüm TEK TP emrini sınar; merdiven 12c'de ayrıca
cb.KAR_AL_ORAN = 0.70
temiz_ortam()
c = SahteClient()
cb.bir_tur(c, dry_run=False)
kontrol("pozisyon yokken kâr al emri KONMUYOR", c.client.kar_al_emirleri == {})
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
poz = {p["symbol"]: (float(p["positionAmt"]), float(p["entryPrice"])) for p in c.get_open_positions()}
c.client.gonderilen = []
cb.bir_tur(c, dry_run=False)
ka = {v[0]: v for v in c.client.kar_al_emirleri.values()
      if c.client.emir_durumu[[k for k, w in c.client.kar_al_emirleri.items() if w is v][0]] == "NEW"}
kontrol("açık HER pozisyona bir kâr al emri kondu", set(ka) == set(poz),
        f"({len(ka)} emir / {len(poz)} pozisyon)")
# madde 189: long ve short eşikleri AYRI (long %70 test ayarı, short kendi ayarı)
_kl, _ks_o = 1 + cb.KAR_AL_ORAN, 1 - cb.KAR_AL_SHORT
dogru = all((ka[s][1] == "SELL" and abs(ka[s][2] - poz[s][1] * _kl) < 0.02)
            if poz[s][0] > 0 else
            (ka[s][1] == "BUY" and abs(ka[s][2] - poz[s][1] * _ks_o) < 0.02)
            for s in ka)
kontrol(f"long -> giriş x{_kl:.2f} SATIŞ, short -> giriş x{_ks_o:.2f} ALIŞ", dogru)
kontrol("kâr al miktarı pozisyonun tamamı",
        all(abs(ka[s][3] - abs(poz[s][0])) < 1e-3 for s in ka))
kontrol("kâr al emirleri reduceOnly + bekleyen limit (GTC) olarak gidiyor",
        c.client.son_kar_al_kw and all(kw.get("reduceOnly") is True
            and kw.get("type") == "LIMIT" and kw.get("timeInForce") == "GTC"
            for kw in c.client.son_kar_al_kw), f"({c.client.son_kar_al_kw[:1]})")
# 3. tur: önceki turun kâr al emirleri İPTAL edilip YENİLERİ konmalı
onceki = {k for k, v in c.client.emir_durumu.items() if v == "NEW"}
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
yeni_ka = {k for k, v in c.client.emir_durumu.items() if v == "NEW"}
kontrol("önceki turun kâr al emirleri iptal edildi", onceki and
        all(c.client.emir_durumu[k] == "CANCELED" for k in onceki), f"({len(onceki)})")
kontrol("yerine güncel pozisyonlar için yenileri kondu",
        yeni_ka and not (yeni_ka & onceki) and
        {c.client.kar_al_emirleri[k][0] for k in yeni_ka}
        == {p["symbol"] for p in c.get_open_positions()})
# bir kâr al DOLDU -> o sembol TÜM dilimlerden çıkmalı
durum = cb.dilim_durum_oku()
dolan_oid, dolan_sem = next((k, v[0]) for k, v in c.client.kar_al_emirleri.items()
                            if c.client.emir_durumu[k] == "NEW")
c.client.emir_durumu[dolan_oid] = "FILLED"
dol = cb.kar_al_kontrol(c, durum)
kontrol("dolan kâr al tespit ediliyor", dol == [dolan_sem], f"({dol})")
kontrol("dolan sembol TÜM dilimlerden çıkarıldı (hemen yeniden açılmasın)",
        all(dolan_sem not in h for h in durum["dilimler"].values()))
# kuru çalışma kâr al emri KOYMAZ
temiz_ortam()
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
c.client.kar_al_emirleri.clear()
cb.bir_tur(c, dry_run=True)
kontrol("kuru çalışmada kâr al emri KONMUYOR", c.client.kar_al_emirleri == {})
# kapalı (0) iken hiç emir yok - madde 189: İKİSİ de kapatılmalı
_eski_kas = cb.KAR_AL_SHORT
cb.KAR_AL_ORAN = 0.0; cb.KAR_AL_SHORT = 0.0
cb.bir_tur(c, dry_run=False)
kontrol("CARRY_KAR_AL=0 iken kâr al emri konmuyor", c.client.kar_al_emirleri == {})
# madde 189: long/short eşikleri AYRI uygulanıyor mu
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT = 0.40, 0.20
c.client.kar_al_emirleri.clear()
cb.bir_tur(c, dry_run=False)
_poz = {p["symbol"]: float(p["positionAmt"]) for p in c.get_open_positions()}
_ent = {p["symbol"]: float(p["entryPrice"]) for p in c.get_open_positions()}
_ka = {v[0]: float(v[2]) for v in c.client.kar_al_emirleri.values()}
_uz = [(s_, f) for s_, f in _ka.items()
       if _poz.get(s_, 0) > 0 and _ent.get(s_, 0) > 0]
_ks = [(s_, f) for s_, f in _ka.items()
       if _poz.get(s_, 0) < 0 and _ent.get(s_, 0) > 0]
kontrol("long ve short bacaklara AYRI eşikle kâr al kondu",
        len(_uz) > 0 and len(_ks) > 0, f"(long {len(_uz)}, short {len(_ks)})")
if _uz and _ks:
    _ol = sum(f / _ent[s_] - 1 for s_, f in _uz) / len(_uz)
    _os = sum(1 - f / _ent[s_] for s_, f in _ks) / len(_ks)
    kontrol("long eşiği %40", abs(_ol - 0.40) < 0.02, f"(%{_ol*100:.1f})")
    kontrol("short eşiği %20 (long'dan DAHA SIKI)",
            abs(_os - 0.20) < 0.02 and _os < _ol, f"(%{_os*100:.1f})")
cb.KAR_AL_ORAN = 0.70; cb.KAR_AL_SHORT = _eski_kas
# sağlık kapısı kapanınca kâr al emirleri İPTAL
temiz_ortam(); _em = cb.SAGLIK_MODU; cb.SAGLIK_MODU = "durdur"
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
acik_ka = [k for k, v in c.client.emir_durumu.items() if v == "NEW"]
c.client.saglik_ters = True
cb.bir_tur(c, dry_run=False)
kontrol("sağlık kapısı kapanınca açık kâr al emirleri iptal edildi",
        acik_ka and all(c.client.emir_durumu[k] == "CANCELED" for k in acik_ka),
        f"({len(acik_ka)} emir)")
cb.SAGLIK_MODU = _em
cb.KAR_AL_ORAN = _eski_ka
cb.MERDIVEN = _eski_mr
cb.KAR_AL_SHORT = _eski_kas

print("\n12c) SHORT FELAKET STOP'U (madde 437)")
_eski = (cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET)
_e24 = cb.LONG_24S
cb.LONG_24S = 0.0   # madde 453: bu bölüm short/long-giriş stop'larını AYRI sınar
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = 0.60, 0.20, 2.0
temiz_ortam()
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
poz = {p["symbol"]: (float(p["positionAmt"]), float(p["entryPrice"])) for p in c.get_open_positions()}
fe = {v[0]: v for k, v in c.client.felaket_emirleri.items() if c.client.felaket_durumu[k] == "NEW"}
shortlar = {s_ for s_, (m, _) in poz.items() if m < 0}
kontrol("her SHORT pozisyona bir felaket stop'u kondu, long'lara HİÇ konmadı",
        shortlar and set(fe) == shortlar, f"({len(fe)} stop / {len(shortlar)} short)")
kontrol("stop BUY, tetik giriş x3,00 (+%200), miktar pozisyonun tamamı",
        all(fe[s_][1] == "BUY" and abs(fe[s_][2] / poz[s_][1] - 3.0) < 0.01
            and abs(fe[s_][3] - abs(poz[s_][0])) < 1e-3 for s_ in fe))
kontrol("stop algo API'sinden: CONDITIONAL + STOP_MARKET + reduceOnly + MARK_PRICE",
        all(v[4].get("algoType") == "CONDITIONAL" and v[4].get("type") == "STOP_MARKET"
            and v[4].get("reduceOnly") == "true" and v[4].get("workingType") == "MARK_PRICE"
            for v in fe.values()))
_ka = {v[0]: v for k, v in c.client.kar_al_emirleri.items() if c.client.emir_durumu[k] == "NEW"}
kontrol("kâr al emirleri stop'tan etkilenmedi (long %60 / short %20 her pozisyonda)",
        set(_ka) == set(poz) and all(
            abs(_ka[s_][2] / poz[s_][1] - (1.60 if poz[s_][0] > 0 else 0.80)) < 0.01 for s_ in _ka))
onceki = [k for k, v in c.client.felaket_durumu.items() if v == "NEW"]
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
kontrol("sonraki turda eski stop'lar iptal edilip yenileri kondu",
        onceki and all(c.client.felaket_durumu[k] == "CANCELED" for k in onceki)
        and any(v == "NEW" for v in c.client.felaket_durumu.values()))
durum = cb.dilim_durum_oku()
aid, sem_t = next((k, v[0]) for k, v in c.client.felaket_emirleri.items()
                  if c.client.felaket_durumu[k] == "NEW")
c.client.felaket_durumu[aid] = "TRIGGERED"
dol = cb.kar_al_kontrol(c, durum)
kontrol("tetiklenen stop tespit edildi", sem_t in dol, f"({dol})")
kontrol("tetiklenen sembol TÜM dilimlerden çıktı (yeniden açılmasın)",
        all(sem_t not in h for h in durum["dilimler"].values()))
# stop kapalıyken (0) hiç algo emri yok
temiz_ortam(); cb.SHORT_FELAKET = 0.0
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
kontrol("CARRY_SHORT_STOP=0 iken felaket stop'u konmuyor", c.client.felaket_emirleri == {})
# kâr al kapalı, yalnız stop açık -> stop yine konur, kâr al konmaz
temiz_ortam(); cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = 0.0, 0.0, 2.0
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
kontrol("kâr al kapalıyken de stop konuyor, kâr al konmuyor",
        c.client.felaket_emirleri and c.client.kar_al_emirleri == {})
# eski kütüphane: algo metodu yoksa ERROR ile sigortasız raporlanır, tur bozulmaz
temiz_ortam(); cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = 0.60, 0.20, 2.0
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
_m = type(c.client).futures_create_algo_order
del type(c.client).futures_create_algo_order
try:
    r = cb.bir_tur(c, dry_run=False)
    kontrol("algo API yoksa tur yine tamamlanıyor, kâr al konuyor",
            r and c.client.kar_al_emirleri, f"({r})")
finally:
    type(c.client).futures_create_algo_order = _m
# MADDE 445: LONG felaket stop'u (CARRY_LONG_STOP) - varsayılan kapalı, açılınca long'lara SELL x(1-X)
temiz_ortam(); _el = cb.LONG_FELAKET
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET, cb.LONG_FELAKET = 0.60, 0.20, 2.0, 0.40
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
poz = {p["symbol"]: (float(p["positionAmt"]), float(p["entryPrice"])) for p in c.get_open_positions()}
fe = {v[0]: v for k, v in c.client.felaket_emirleri.items() if c.client.felaket_durumu[k] == "NEW"}
kontrol("long stop açıkken HER pozisyona (long + short) felaket stop'u kondu",
        set(fe) == set(poz), f"({len(fe)} / {len(poz)})")
kontrol("long stop SELL, tetik giriş x0,60 (−%40); short stop BUY x3,00",
        all((fe[s_][1] == "SELL" and abs(fe[s_][2] / poz[s_][1] - 0.60) < 0.01) if poz[s_][0] > 0
            else (fe[s_][1] == "BUY" and abs(fe[s_][2] / poz[s_][1] - 3.0) < 0.01) for s_ in fe))
durum = cb.dilim_durum_oku()
_lsem = next(s_ for s_ in fe if poz[s_][0] > 0)
_aid = next(k for k, v in c.client.felaket_emirleri.items() if v[0] == _lsem and c.client.felaket_durumu[k] == "NEW")
c.client.felaket_durumu[_aid] = "TRIGGERED"
kontrol("tetiklenen LONG stop'u sembolü tüm dilimlerden çıkarıyor",
        _lsem in cb.kar_al_kontrol(c, durum) and all(_lsem not in h for h in durum["dilimler"].values()))
cb.LONG_FELAKET = _el
kontrol("CARRY_LONG_STOP varsayılanı KAPALI (kullanıcı tercihi, madde 445)", cb.LONG_FELAKET == 0.0)
# MADDE 453: 24 SA DÜŞÜŞ STOP'U (CARRY_LONG_24S, varsayılan 0,45)
cb.LONG_24S = _e24
kontrol("CARRY_LONG_24S varsayılanı 0,45 (madde 453)", abs(cb.LONG_24S - 0.45) < 1e-9)
temiz_ortam(); cb.LONG_FELAKET = 0.0
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = 0.60, 0.20, 2.0
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
cb.bir_tur(c, dry_run=False)
poz = {p["symbol"]: (float(p["positionAmt"]), float(p["entryPrice"])) for p in c.get_open_positions()}
fe = {v[0]: v for k, v in c.client.felaket_emirleri.items() if c.client.felaket_durumu[k] == "NEW"}
_ref = {s_: cb.long_24s_referans(c, s_) for s_ in poz if poz[s_][0] > 0}
kontrol("24 sa stop'u her LONG'a kondu (short'lar +%200 ile)", set(fe) == set(poz), f"({len(fe)}/{len(poz)})")
kontrol("long tetiği = 24 sa önceki kapanış x 0,55 (girişten bağımsız)",
        all(fe[s_][1] == "SELL" and _ref[s_] and abs(fe[s_][2] - _ref[s_] * 0.55) < 0.01 for s_ in _ref),
        f"({[(s_, fe[s_][2], _ref[s_]) for s_ in list(_ref)[:2]]})")
# fiyat seviyenin altındaysa: hemen kapat + dilimlerden çıkar
temiz_ortam()
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
_kapatilan = []
c.close_position = lambda sem, yon, adet, verify_fill=True: _kapatilan.append((sem, yon, adet))
_l1 = next(p["symbol"] for p in c.get_open_positions() if float(p["positionAmt"]) > 0)
_eski_tk = c.client.futures_symbol_ticker
c.client.futures_symbol_ticker = lambda symbol: {"price": "0.01"} if symbol == _l1 else _eski_tk(symbol)
cb.bir_tur(c, dry_run=False)
c.client.futures_symbol_ticker = _eski_tk
_d = cb.dilim_durum_oku()
kontrol("seviyenin altında bulunan long piyasa emriyle kapatıldı (SELL)",
        any(k[0] == _l1 and k[1] == "SELL" for k in _kapatilan), f"({_kapatilan[:3]})")
kontrol("kapatılan long tüm dilimlerden çıkarıldı",
        all(_l1 not in h for h in _d.get("dilimler", {}).values()))
# MADDE 465: LONG MERDİVEN KÂR ALMA
temiz_ortam(); _em = (cb.MERDIVEN, cb.MERDIVEN_PAY, cb.LONG_24S)
cb.MERDIVEN, cb.MERDIVEN_PAY, cb.LONG_24S = 0.45, 0.5, 0.0
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = 0.60, 0.20, 2.0
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
c.client.kar_al_emirleri.clear()
cb.bir_tur(c, dry_run=False)
poz = {p["symbol"]: (float(p["positionAmt"]), float(p["entryPrice"])) for p in c.get_open_positions()}
_acik = [(k, v) for k, v in c.client.kar_al_emirleri.items() if c.client.emir_durumu[k] == "NEW"]
_lng = [s_ for s_ in poz if poz[s_][0] > 0]; _sht = [s_ for s_ in poz if poz[s_][0] < 0]
def _emr(s_): return sorted([v for k, v in _acik if v[0] == s_], key=lambda v: v[2])
kontrol("merdiven: her long'a İKİ satış emri (+%45 ve +%60), miktarlar yarı yarıya",
        _lng and all(len(_emr(s_)) == 2 and abs(_emr(s_)[0][2] / poz[s_][1] - 1.45) < 0.01
                     and abs(_emr(s_)[1][2] / poz[s_][1] - 1.60) < 0.01
                     and abs(_emr(s_)[0][3] + _emr(s_)[1][3] - poz[s_][0]) < 1e-3
                     and abs(_emr(s_)[0][3] - poz[s_][0] / 2) < 0.02 * poz[s_][0] for s_ in _lng),
        f"({[(s_, _emr(s_)) for s_ in _lng[:1]]})")
kontrol("merdiven short'lara uygulanmıyor (tek TP, %20)",
        all(len(_emr(s_)) == 1 and abs(_emr(s_)[0][2] / poz[s_][1] - 0.80) < 0.01 for s_ in _sht))
durum = cb.dilim_durum_oku()
_ms = _lng[0]; _moid = durum["merdiven"][_ms]["oid"]
_once = sum(h.get(_ms, 0) for h in durum["dilimler"].values())
c.client.emir_durumu[_moid] = "FILLED"
_dol = cb.kar_al_kontrol(c, durum)
_sonra = sum(h.get(_ms, 0) for h in durum["dilimler"].values())
kontrol("kademe dolunca sembol dilimlerden ÇIKMIYOR (kâr al gibi değil)", _ms not in _dol and _sonra > 0)
kontrol("kademe dolunca toplam hedef yarıya iniyor", abs(_sonra - _once * 0.5) < 1e-6 * max(1, abs(_once)),
        f"({_once:.2f} -> {_sonra:.2f})")
cb.dilim_durum_yaz(durum)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
c.client.kar_al_emirleri.clear()
cb.bir_tur(c, dry_run=False)
_acik = [(k, v) for k, v in c.client.kar_al_emirleri.items() if c.client.emir_durumu[k] == "NEW"]
kontrol("aynı giriş için kademe İKİNCİ KEZ konmuyor (yalnız +%60 TP)",
        len([v for k, v in _acik if v[0] == _ms]) == 1
        and abs([v for k, v in _acik if v[0] == _ms][0][2] / poz[_ms][1] - 1.60) < 0.01,
        f"({[v for k, v in _acik if v[0] == _ms]})")
cb.MERDIVEN, cb.MERDIVEN_PAY, cb.LONG_24S = _em
kontrol("CARRY_MERDIVEN varsayılanı 0,45 / pay 0,5 (madde 465)",
        abs(cb.MERDIVEN - 0.45) < 1e-9 and abs(cb.MERDIVEN_PAY - 0.5) < 1e-9)
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = _eski
cb.LONG_24S = _e24
cb.KAR_AL_ORAN, cb.KAR_AL_SHORT, cb.SHORT_FELAKET = _eski
cb.LONG_24S = _e24

print("\n12b) KÂR AL PATLASA BİLE DİLİM DEFTERİ YAZILIR (madde 208)")
# Borsa bakiminda `get_open_positions()` hata firlatir; eskiden bu hata
# `dilim_durum_yaz`'i atlatiyor, pozisyonlar borsada acik ama defterde
# YOK kaliyor ve bir sonraki tur onlari KAPATIYORDU.
temiz_ortam()
_eski_kk = cb.kar_al_kur
def _patlayan_kar_al(client, durum):
    raise RuntimeError("borsa bakimda (-1001)")
cb.kar_al_kur = _patlayan_kar_al
c = SahteClient()
try:
    _s = cb.bir_tur(c, dry_run=False)
    _patladi = False
except Exception as _ex:
    _s, _patladi = None, True
cb.kar_al_kur = _eski_kk
kontrol("kâr al hatası turu ÇÖKERTMİYOR", not _patladi)
_dz = cb.dilim_durum_oku()
kontrol("taze dilim DEFTERE yazıldı (pozisyonlar yetim kalmadı)",
        bool(_dz.get("dilimler")), f"({sorted(_dz.get('dilimler', {}))})")
kontrol("sıra da ilerledi (aynı slot iki kez yazılmaz)",
        int(_dz.get("sira", 0)) == 1, f"({_dz.get('sira')})")
# Ikinci tur: acilan pozisyonlar hedefte OLMALI, yani kapatilmamali
c.pozisyonlari_ayarla(cb.toplam_hedef(_dz))
_hedef2 = cb.toplam_hedef(cb.dilim_durum_oku())
_poz2 = cb.mevcut_portfoy(c)
_kapanan = [s for s in _poz2 if s not in _hedef2]
kontrol("bir sonraki turda hiçbir pozisyon YETİM değil",
        not _kapanan, f"({_kapanan[:5]})")

print("\n12c) YARIM TUR: TARAF DOKUMASI CANLI YOLDA (madde 208)")
# Emir listesi bakim yuzunden ortada kesilse kitap nötr kalmali.
temiz_ortam()
c = SahteClient(); cb.bir_tur(c, dry_run=False)
_hd = cb.toplam_hedef(cb.dilim_durum_oku())
_emr = cb.emirleri_hesapla(_hd, {}, tolerans_usd=0.0)
_yn = [(+1 if y == "BUY" else -1) for _, y, _ in _emr]
_ktl = [abs(sum(_yn[:k])) for k in range(1, len(_yn) + 1)]
kontrol("gerçek hedefte de her kesme noktasında |net| <= 1 bacak",
        len(_yn) >= 4 and max(_ktl) <= 1, f"(max {max(_ktl) if _ktl else '-'} / {len(_yn)} emir)")
_usd = [u for _, _, u in _emr]
kontrol("dokuma emir sayısını DEĞİŞTİRMİYOR", len(_emr) == len(_hd),
        f"({len(_emr)} / {len(_hd)})")

print("\n12d) HEDGE POZİSYON MODU (madde 211)")
# Hedge modda her emir `positionSide` ister; bot gondermedigi icin
# emirler -4061 ile reddedilir ve reduce-only kar al hic kabul edilmez.
# Yani bot HIC ISLEM ACAMAZ - ama eski hata mesaji kullaniciyi
# bakiye/izin kovalamaya yonlendiriyordu.
temiz_ortam()
c = SahteClient()
c.client.hedge_modu = True
_s = cb.bir_tur(c, dry_run=False)
kontrol("hedge + pozisyon YOK -> tek yönlüye alınıp tur DEVAM ediyor",
        _s.get("atlandi") != "hedge_modu" and c.client.poz_modu_gecis,
        f"({_s.get('atlandi')}, geçiş {c.client.poz_modu_gecis})")
kontrol("geçişten sonra hesap tek yönlü", not c.client.hedge_modu)
kontrol("tur gerçekten emir gönderdi", len(c.client.gonderilen) > 0,
        f"({len(c.client.gonderilen)})")
# Pozisyon varken gecilemez: tur ATLANIR, sessiz durus YOK
temiz_ortam()
c = SahteClient(); cb.bir_tur(c, dry_run=False)
c.pozisyonlari_ayarla(cb.toplam_hedef(cb.dilim_durum_oku()))
c.client.hedge_modu = True
c.client.poz_gecis_patlat = True
_n0 = len(c.client.gonderilen)
_s2 = cb.bir_tur(c, dry_run=False)
kontrol("hedge + pozisyon VAR -> tur ATLANDI", _s2.get("atlandi") == "hedge_modu",
        f"({_s2})")
kontrol("atlanan turda HİÇ emir gönderilmedi",
        len(c.client.gonderilen) == _n0, f"({len(c.client.gonderilen) - _n0})")
# Mod okunamazsa tur DEVAM etmeli (dedektor arizasi botu durdurmaz)
temiz_ortam()
c = SahteClient(); c.client.poz_modu_patlat = True
_s3 = cb.bir_tur(c, dry_run=False)
kontrol("pozisyon modu OKUNAMAZSA tur devam ediyor (madde 123)",
        _s3.get("atlandi") != "hedge_modu", f"({_s3})")

print("\n12e) ELLE İZOLEYE ÇEKİLEN SEMBOL (madde 211)")
# `_KALDIRAC_AYARLI` surec basina cache: bir sembol bir kez CROSSED'a
# alindiktan sonra bot bir daha kontrol etmiyordu.
temiz_ortam()
c = SahteClient(); cb.bir_tur(c, dry_run=False)
_hd = cb.toplam_hedef(cb.dilim_durum_oku())
c.pozisyonlari_ayarla(_hd)
_kurban = sorted(_hd)[0]
c.client.izole_semboller.add(_kurban)
c.pozisyonlari_ayarla(_hd)          # marginType yeniden yazilsin
kontrol("izole sembol borsadan tespit ediliyor",
        cb.izole_teminatlilar(c) == [_kurban], f"({cb.izole_teminatlilar(c)})")
c.client.gonderilen.clear()
cb.bir_tur(c, dry_run=False)
_kapatma = [g for g in c.client.gonderilen if g[0] == _kurban]
kontrol("izole sembol için KAPATMA emri gönderildi", bool(_kapatma),
        f"({_kapatma})")
kontrol("kapatma yönü pozisyonun TERSİ",
        _kapatma and _kapatma[0][1] == ("SELL" if _hd[_kurban] > 0 else "BUY"),
        f"({_kapatma[:1]}, hedef {_hd[_kurban]:.0f})")
_hd2 = cb.toplam_hedef(cb.dilim_durum_oku())
cb.izole_ele(_hd2, cb.izole_teminatlilar(c))
kontrol("izole sembol HEDEFTEN çıkarılıyor (hedefte kalsa büyütülürdü)",
        _kurban not in _hd2, f"({_kurban} hâlâ hedefte)")
# KRITIK: `kaldirac_hazirla` acik pozisyonlu sembolde -4048 ile False
# doner; eskiden `_emirleri_gonder` emri ATLIYORDU, yani izole pozisyon
# HIC KAPATILAMIYORDU. Kapatma emrinin gectigini borsanin REDDETTIGI
# halde dogrula.
c.client.teminat_patlat.add(_kurban)
cb._KALDIRAC_AYARLI.discard(_kurban)
c.pozisyonlari_ayarla(_hd)
c.client.gonderilen.clear()
cb.bir_tur(c, dry_run=False)
kontrol("ÇAPRAZ'a ALINAMASA BİLE izole sembol kapatma emri gidiyor",
        bool([g for g in c.client.gonderilen if g[0] == _kurban]),
        f"({[g for g in c.client.gonderilen if g[0] == _kurban]})")
c.client.teminat_patlat.discard(_kurban)
_eski_ik = cb.IZOLE_KAPAT
cb.IZOLE_KAPAT = False
c.client.izole_semboller.clear()
c.pozisyonlari_ayarla(_hd)
kontrol("CARRY_IZOLE_KAPAT=0 ile izole tespiti devreden çıkıyor",
        cb.izole_teminatlilar(c) == [] and not cb.IZOLE_KAPAT)
cb.IZOLE_KAPAT = _eski_ik

print("\n" + "=" * 64)
# MADDE 356: bu blok EN SONDA durmalı. Paketin başında (0b) koşunca
# ortak bir durumu kirletip 11f'nin üç piyasa-yedeği kontrolünü düşürdü
# (blok çıkarılınca paket 139/139 geçti). Sonda kirletecek test kalmıyor.
print("\n99) GERÇEK VARSAYILANLA TAM TUR: taraf başına bacak = tavan (madde 341/356)")
_n12 = (cb.N_LEGS, cb.MIN_LEGS)
cb.N_LEGS, cb.MIN_LEGS = _GERCEK_N_LEGS, _GERCEK_MIN_LEGS
for _bk in (2000.0, 50000.0):
    temiz_ortam()
    _c = SahteClient(bakiye=_bk); _c.client.gonderilen = []
    cb.bir_tur(_c, dry_run=False)
    _la = {e[0] for e in _c.client.gonderilen if e[1] == "BUY"}
    _ls = {e[0] for e in _c.client.gonderilen if e[1] == "SELL"}
    kontrol(f"{_bk:,.0f} $: taraf başına {cb.BACAK_TAVAN} bacak (tavan) açılıyor",
            len(_la) == len(_ls) == min(cb.N_LEGS, cb.BACAK_TAVAN),
            f"(long {len(_la)}, short {len(_ls)})")
# Tur kodu bacağı min(N_LEGS, max(MIN_LEGS, n)) ile sıkıştırır: MIN_LEGS
# tavanı aşarsa tavan SESSİZCE yok sayılır (test ortamında 8 bacak böyle
# çıkıyordu). Varsayılanlar bu tuzağa düşmemeli.
kontrol("MIN_LEGS bacak tavanını AŞMIYOR (aşarsa tavan sessizce iptal olur)",
        cb.MIN_LEGS <= cb.BACAK_TAVAN, f"(MIN {cb.MIN_LEGS} > TAVAN {cb.BACAK_TAVAN})")
cb.N_LEGS, cb.MIN_LEGS = _n12


if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum entegrasyon testleri gecti.")
print("""
NE DOGRULANDI : botun MANTIGI - emir yonu, dilim dongusu, tolerans,
                portfoy dengesi, hata dayanikligi.
NE DOGRULANMADI: funding'in gercekten tahsil edildigi, limit emirlerin
                doldugu, gercek kayma. Bunlar ancak CANLI/demo hesapta
                olculebilir.
""")
