"""carry_izleme testleri — SAHTE hesap verisiyle.

Bu aracın işi backtest varsayımlarını gerçek veriyle karşılaştırmak.
Kendisi yanlış okursa yanlış güven verir - bu yüzden test edilir.

EN KRİTİK TEST: funding TERS yönde akıyorsa (yani ödüyorsak) araç
bunu ALARM olarak vermeli. Bu, stratejinin işaretinin ters olduğu
anlamına gelir ve gerçek parayla en pahalı hatadır.
"""
import io
import sys
import time
from contextlib import redirect_stdout

sys.path.insert(0, '.')
import carry_izleme as ci

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


class SahteIc:
    def __init__(self, funding, komisyon, pnl, maker_orani=0.9, hacim=100000.0,
                 islem_sayisi=50):
        self._f, self._k, self._p = funding, komisyon, pnl
        self._mo, self._hacim, self._n = maker_orani, hacim, islem_sayisi

    def futures_income_history(self, startTime, endTime, limit):
        if startTime > endTime - 1000:
            return []
        t = endTime - 1000
        return [{"time": t, "incomeType": "FUNDING_FEE", "income": str(self._f), "symbol": "AUSDT"},
                {"time": t, "incomeType": "COMMISSION", "income": str(self._k), "symbol": "AUSDT"},
                {"time": t, "incomeType": "REALIZED_PNL", "income": str(self._p), "symbol": "AUSDT"}]

    def futures_account_trades(self, symbol, startTime, endTime, limit):
        n = self._n
        mk = int(n * self._mo)
        return [{"maker": i < mk, "quoteQty": str(self._hacim / n)} for i in range(n)]


class SahteClient:
    def __init__(self, bakiye=10000.0, long_usd=5000.0, short_usd=5000.0, **kw):
        self.client = SahteIc(**kw)
        self.mode = "sahte"
        self._b = bakiye
        self._l, self._s = long_usd, short_usd

    def get_account_balance_usdt(self):
        return self._b

    def get_open_positions(self):
        out = []
        if self._l > 0:
            out.append({"symbol": "AUSDT", "positionAmt": str(self._l / 100),
                        "entryPrice": "100"})
        if self._s > 0:
            out.append({"symbol": "BUSDT", "positionAmt": str(-self._s / 100),
                        "entryPrice": "100"})
        return out


def calistir(c, gun=7):
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        sonuc = ci.rapor(c, gun)
    return tampon.getvalue(), sonuc


print("1) NORMAL DURUM — funding geliyor, maker yüksek")
c = SahteClient(funding=50.0, komisyon=-20.0, pnl=30.0, maker_orani=0.95)
cikti, s = calistir(c)
kontrol("funding pozitif okundu", abs(s["funding"] - 50.0) < 1e-9, f"({s['funding']})")
kontrol("net doğru hesaplandı", abs(s["net"] - 60.0) < 1e-9, f"({s['net']})")
kontrol("funding GELİR olarak raporlandı", "GELİR olarak geldi" in cikti)
kontrol("maker oranı beklentiyi karşılıyor", "beklenti karşılanıyor" in cikti)
kontrol("ters funding alarmı VERİLMEDİ", "FUNDING ÖDÜYORUZ" not in cikti)

print("\n2) KRİTİK — funding TERS yönde (işaret hatası)")
c = SahteClient(funding=-40.0, komisyon=-20.0, pnl=10.0)
cikti, s = calistir(c)
kontrol("ters funding ALARMI veriliyor", "FUNDING ÖDÜYORUZ" in cikti)
kontrol("işaret testine yönlendiriyor", "İŞARET YÖNÜ" in cikti)
kontrol("negatif funding doğru okundu", s["funding"] < 0)

print("\n3) LİMİT EMİRLER DOLMUYOR (maker oranı düşük)")
c = SahteClient(funding=50.0, komisyon=-20.0, pnl=10.0, maker_orani=0.2)
cikti, s = calistir(c)
kontrol("düşük maker oranı UYARI veriyor", "YARIDAN AZI maker" in cikti)
kontrol("çözüm öneriliyor (LIMIT_OFSET)", "LIMIT_OFSET" in cikti)

print("\n4) KOMİSYON VARSAYIMI BOZULMUŞ")
# hacim 100.000, komisyon 400 -> %0.4, varsayımın 20 katı
c = SahteClient(funding=50.0, komisyon=-400.0, pnl=10.0, hacim=100000.0)
cikti, s = calistir(c)
kontrol("yüksek komisyon UYARI veriyor", "KATI" in cikti)
kontrol("BNB indirimi öneriliyor", "BNB" in cikti)

print("\n5) NÖTRLÜK BOZULMUŞ (tek yönlü portföy)")
c = SahteClient(funding=10.0, komisyon=-5.0, pnl=0.0,
                long_usd=9000.0, short_usd=1000.0)
cikti, s = calistir(c)
kontrol("nötrlük sapması UYARI veriyor", "portföy tek yönlü kalmış" in cikti)
c2 = SahteClient(funding=10.0, komisyon=-5.0, pnl=0.0,
                 long_usd=5000.0, short_usd=5100.0)
cikti2, _ = calistir(c2)
kontrol("dengeli portföyde uyarı YOK", "tek yönlü kalmış" not in cikti2)

print("\n5b) KISA TUTMA ÖNERİSİ (madde 141) — sadece önkoşul ölçülünce")
# hacim 100.000, komisyon 20 -> %0.02, maker %95 -> öneri ÇIKMALI
c = SahteClient(funding=50.0, komisyon=-20.0, pnl=10.0, maker_orani=0.95)
cikti, _ = calistir(c)
# MADDE 179: tutma süresi yeniden ölçüldü ve 5 gün TEPE çıktı; araç
# artık "3 güne geç" ÖNERMİYOR, sadece ölçüm tablosunu gösteriyor.
kontrol("maker yüksek + komisyon düşük -> kısa tutma BİLGİSİ var",
        "KISA TUTMA" in cikti and "TEPE" in cikti, "(bilgi bloğu yok)")
kontrol("araç artık tutma süresini DEĞİŞTİRMEYİ önermiyor",
        "CARRY_REBALANCE_H=72" not in cikti)
c = SahteClient(funding=50.0, komisyon=-20.0, pnl=10.0, maker_orani=0.5)
cikti, _ = calistir(c)
kontrol("maker düşükse öneri YOK", "KISA TUTMA" not in cikti)
c = SahteClient(funding=50.0, komisyon=-60.0, pnl=10.0, maker_orani=0.95)
cikti, _ = calistir(c)
kontrol("komisyon yüksekse (%0.06) öneri YOK", "KISA TUTMA" not in cikti)

print("\n6) VERİ YOKKEN ÇÖKMÜYOR")
class Bos(SahteClient):
    def get_open_positions(self):
        return []
class BosIc(SahteIc):
    def futures_income_history(self, **kw):
        return []
    def futures_account_trades(self, **kw):
        return []
b = Bos(funding=0, komisyon=0, pnl=0)
b.client = BosIc(0, 0, 0)
try:
    cikti, s = calistir(b)
    kontrol("boş hesapta çökmeden rapor veriyor", True)
    kontrol("boş hesapta uyarı metni var", "bulunamadı" in cikti or s == {})
except Exception as e:
    kontrol("boş hesapta çökmeden rapor veriyor", False, str(e))

print("\n7) API HATASI DAYANIKLILIĞI")
class PatlakIc(SahteIc):
    def futures_income_history(self, **kw):
        raise RuntimeError("API patladı")
p = SahteClient(funding=0, komisyon=0, pnl=0)
p.client = PatlakIc(0, 0, 0)
try:
    cikti, s = calistir(p)
    kontrol("API hatasında çökmüyor", True)
except Exception as e:
    kontrol("API hatasında çökmüyor", False, str(e))

print("\n8) KÂR AL ULAŞMA ORANI RAPORU (madde 216)")
# Madde 214: karin TAMAMI kar-al hasadindan. Madde 216: TP orani 30 gunde
# %95 guc, toplam getiri %15. Rapor artik bunu gosteriyor.
import os as _os, tempfile as _tf, time as _time
import carry_bot as _cb
_eski = _cb.TP_DEFTER_DOSYA
_cb.TP_DEFTER_DOSYA = _os.path.join(_tf.mkdtemp(), "tp.csv")
c = SahteClient(funding=50.0, komisyon=-20.0, pnl=30.0, maker_orani=0.95)
cikti, s = calistir(c, gun=30)
kontrol("rapor TP bölümünü içeriyor", "KÂR AL ULAŞMA ORANI" in cikti)
kontrol("defter boşken UYARI değil BİLGİ veriliyor",
        "Dolum defteri BOŞ" in cikti)   # madde 292: iki defter var,
                                        # etiket "Dolum defteri" oldu
kontrol("beklenen oranlar gösteriliyor", "%8.8" in cikti or "%8,8" in cikti
        or "8.8" in cikti, "(beklenen LONG oranı yok)")
kontrol("güç rakamları raporda", "%100" in cikti and "%15" in cikti)
# yeterli dolum: uyari OLMAMALI
_n = int(_cb.N_DILIM / (_cb.REBALANCE_HOURS/24.0) * _cb.N_LEGS * 30)
for _i in range(max(1, int(_n * _cb.BEKLENEN_TP_LONG))):
    _cb._tp_kaydet(f"L{_i}USDT", "SELL")
cikti2, _ = calistir(c, gun=30)
kontrol("beklenen kadar dolum varsa UYARI YOK",
        "beklenen aralıkta" in cikti2 and "YARISINDAN AZ" not in cikti2)
# cok az dolum: uyari OLMALI
_cb.TP_DEFTER_DOSYA = _os.path.join(_tf.mkdtemp(), "tp2.csv")
_cb._tp_kaydet("AUSDT", "SELL")
cikti3, _ = calistir(c, gun=30)
kontrol("dolum beklenenin yarısından azsa UYARI veriliyor",
        "YARISINDAN AZ" in cikti3)
kontrol("uyarı getiriden daha hızlı haber verdiğini söylüyor",
        "%95 güç" in cikti3 or "95" in cikti3)
_cb.TP_DEFTER_DOSYA = _eski

print("\n" + "=" * 60)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum izleme testleri gecti.")
print("""
BU ARAC NE YAPAR: borsanin KENDI kayitlarindan funding tahsilatini,
maker oranini ve gercek komisyonu okur; backtest varsayimlariyla
karsilastirir. Tahmin yapmaz.

BOT 3-5 GUN CALISTIKTAN SONRA calistirin:
    python carry_izleme.py --gun 7
""")

# ---------------------------------------------------------------- MADDE 292
# TP KONMA oranı: düşük dolumun İKİ ayrı sebebi ayırt ediliyor mu?
print("\nMADDE 292 - KONMA vs DOLUM AYRIMI")
_ku_eski = _cb.TP_KURULUM_DOSYA
_dk292 = _tf.mkdtemp()

# (a) konma oranı DÜŞÜK -> İCRA arızası denmeli, strateji suçlanmamalı
_cb.TP_KURULUM_DOSYA = _os.path.join(_dk292, "kur_bozuk.csv")
_now292 = _time.time()
with open(_cb.TP_KURULUM_DOSYA, "w", encoding="utf-8") as _f:
    for _i in range(5):
        _f.write("%.0f,50,30,20\n" % (_now292 - _i * 28800))
_cb.TP_DEFTER_DOSYA = _os.path.join(_dk292, "tp_bos.csv")
with open(_cb.TP_DEFTER_DOSYA, "w", encoding="utf-8") as _f:
    _f.write("%.0f,AAAUSDT,LONG\n" % (_now292 - 3600))
c = SahteClient(funding=50.0, komisyon=-20.0, pnl=30.0, maker_orani=0.95)
cikti, s = calistir(c, gun=30)
kontrol("madde 292: konma oranı raporlanıyor", "TP KONMA oranı" in cikti)
kontrol("madde 292: düşük konma İCRA arızası olarak adlandırılıyor",
        "İCRA arızasıdır" in cikti)
kontrol("madde 292: düşük konmada STRATEJİ suçlanmıyor",
        "Strateji şüpheli DEĞİL" in cikti
        and "Kâr motoru" not in cikti.split("İCRA arızasıdır")[1])

# (b) konma oranı TAM ama dolum düşük -> ŞİMDİ piyasa bulgusu denebilir
_cb.TP_KURULUM_DOSYA = _os.path.join(_dk292, "kur_tam.csv")
with open(_cb.TP_KURULUM_DOSYA, "w", encoding="utf-8") as _f:
    for _i in range(5):
        _f.write("%.0f,50,50,0\n" % (_now292 - _i * 28800))
cikti2, s2 = calistir(c, gun=30)
kontrol("madde 292: konma tamken düşük dolum PİYASA bulgusu sayılıyor",
        "piyasa/varsayım bulgusu" in cikti2 or "beklenen aralıkta" in cikti2)
kontrol("madde 292: konma tamken İCRA suçlaması YAPILMIYOR",
        "İCRA arızasıdır" not in cikti2)

# (c) ölçülemeyen tur oranı bozmuyor
_cb.TP_KURULUM_DOSYA = _os.path.join(_dk292, "kur_olculemedi.csv")
with open(_cb.TP_KURULUM_DOSYA, "w", encoding="utf-8") as _f:
    _f.write("%.0f,50,50,0\n" % (_now292 - 3600))
    _f.write("%.0f,-1,0,-1\n" % (_now292 - 7200))
_r292 = _cb.tp_kurulum_oku(_cb.TP_KURULUM_DOSYA, gun=30)
kontrol("madde 292: ölçülemeyen tur orana KATILMIYOR",
        _r292["oran"] == 1.0 and _r292["olculemedi"] == 1 and _r292["tur"] == 1)
cikti3, s3 = calistir(c, gun=30)
kontrol("madde 292: ölçülemeyen tur raporda AYRI gösteriliyor",
        "OKUNAMADI" in cikti3)
_cb.TP_KURULUM_DOSYA = _ku_eski
