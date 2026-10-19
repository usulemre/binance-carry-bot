# ⚠ MADDE 344 DÜZELTMESİ — BU DOSYA CANLI KAYIT DEĞİL

**Madde 343'ün öncülü yanlıştı.** `canli_kayit_2026-09-12_10-03_ikinci_bot.log`
gerçek bir canlı koşu değil; **test koşularının `bot.log`'a sızan
çıktısı.** Dosya, aşağıdaki 12 satırlık bloğun **48 kez** tekrarından
ibaret (+ 23 satır `AAAUSDT` süre doldu):

| kanıt | değer |
|---|---|
| semboller | yalnız `BTCUSDT` ve `AAAUSDT` (ikincisi gerçek sembol değil) |
| BTC giriş fiyatı | **192/192 satırda 100,0** · SL 95 · TP 110 · miktar 1,0 |
| zaman damgası | bir bloktaki 12 olay **aynı milisaniyede** |
| yeniden üretim | `test_position_protection.py` + `test_signal_bot_scaling.py` boş bir klasörde koşturuldu → **aynı 12 satır, aynı metinler** |

48 ERROR "emir DOLMADI" ve 48 "TP emri reddedildi" bir borsa olgusu
değil; `FakeExchange`'in bilerek reddettiği emirleri test eden
senaryolar. **Yani carry botunun maker dolum riski hakkında bu dosya
HİÇBİR ŞEY söylemiyor** — madde 343'ün "DER" bölümü de geçersiz.
"Uygulanabilirlik güveni MEDIUM, canlıda ölçülmedi" cümlesi olduğu gibi
duruyor: eldeki canlı icra verisi **sıfır**.

## Kök neden ve onarım

`main.py` (elenen sinyal botu) `logging.FileHandler(config.LOG_FILE)`'ı
**import anında** kuruyordu. Onu import eden iki test her koşuda gerçek
`bot.log`'a sahte emir olayları yazıyordu. Onarım: log kurulumu
`_log_kur()`'a taşındı ve yalnız `__main__`'de çağrılıyor.
Regresyon testi `test_log_kirliligi.py` — eski kodda **düşüyor**
(`FileHandler kuruldu: True`), yenide geçiyor.

`carry_bot.py` bu hatayı TAŞIMIYOR: log dosyasını yalnız `main()`
içinde açıyor.

**Yasa: bir kaydın "canlı" olduğunu, içeriğine bakmadan adından ve
konumundan çıkarma.** 343, dosyayı arşivlerken sayıları saydı ama tek
bir fiyata bakmadı; BTC'nin 100 $ olduğu ilk satırda görünüyordu.

Dosya denetim izi olarak silinmedi.

---

# MADDE 343 — ELDEKİ TEK GERÇEK CANLI KAYIT (ve neden arşivlendi)

`canli_kayit_2026-09-12_10-03_ikinci_bot.log` — 71 KB, **21 günlük
gerçek canlı koşu**, kullanıcının **ikinci** botundan (ortalamaya
dönüş / ATR stop'lu, carry botu DEĞİL).

`.gitignore` `bot.log`'u dışlıyor ve canlı churn için bu doğru. Ama bu
dosya churn değil: **bu projede eldeki tek canlı icra kaydı** ve
konteynerle birlikte gidecekti. Bu yüzden ayrı bir adla arşivlendi.

## NİYE ÖNEMLİ

Carry kitabının en büyük ölçülmemiş riski belgenin kendi ifadesiyle:
*"uygulanabilirlik güveni MEDIUM (maker doluluğu simülasyonda %97;
**canlıda ölçülmedi**)"*. Bu kayıt o boşluğa bakan tek veri.

Sayılan olaylar (192 ERROR, 96 WARNING, 311 INFO):

| olay | adet |
|---|---|
| `emir DOLMADI` | **48** |
| `TP emri reddedildi` | **48** |
| `SÜRE DOLDU` → `kapatılıyor` | 71 |

## NE DER, NE DEMEZ — DİKKAT

**DEMEZ:** "carry botunun maker doluluğu şu kadar." Bu başka bir bot,
başka emir tipi, başka evren. Ölçülmüş bir sabiti başka yapılandırmaya
taşımak onu ölçülmemiş bir tahmine çevirir (madde 305'in yasası).

**DER:** borsa düzeyinde iki olgu var ve ikisi de carry botunu
ilgilendirir — (1) emirler fiilen dolmayabiliyor, (2) dolmayan emrin
ardından TP kurulamıyor ve pozisyon korumasız/yarım kalıyor. 48/48
eşitliği bunların **aynı 48 olay** olduğunu düşündürüyor: emir dolmaz →
TP kurulamaz. Carry botu GTX post-only maker giriş kullanıyor, yani
dolmama riski ona DAHA çok ait.

## AÇIK EKSEN (ölçülmedi)

Bu kayıttan şunlar çıkarılabilir ama ÇIKARILMADI: dolmama oranı
(payda: toplam emir denemesi), reddin saat/oynaklık dağılımı, ve
carry'nin `DOLUM_BEKLEME_SN=180` / `DOLUM_DENEME=2` ayarlarının bu
gerçeklikte ne verdiği. Payda log'da açıkça yok; çıkarmak için
`carry_izleme.py`'nin okuduğu biçime dönüştürmek gerekir.
