# ARAŞTIRMA 716 — Bekleyen Bulguların Takibi ve Kanıt Denetimi

**Sonuç: NO ACTION.** Bugün (2026-11-02) hiçbir konu karar verilebilir durumda değil.

- Strateji, üretim kodu ve parametreler değişmedi. Yeni alpha testi açılmadı, yeni eşik tanımlanmadı.
- Tek yeni ölçüm: V3'ün Ekim serisi ile tabanın karşılaştırması (bölüm 2; `arastirma_m716_v3_katki.py`, rc 0). Mevcut motor çıktılarından yapıldı; yeni motor koşusu yok.

## 1. Kasım 2026 gerçek veri kontrolü

**Mevcut kanıt.**
- Madde 707 (Ekim, kurallar dondurulduktan sonraki ilk gerçek ay):
  - Önerilen ayar (2.000 $, ×1,15) −%4,96. T4 −%8,37.
  - Madde 650 kuralına göre: önerilen ile T4 farkı +3,41 / +4,90 (2.000 $ / 3.500 $). Geçmiş %10 yüzdeliği −2,70 / −3,12 → şart 1 tutmadı.
  - En kötü gün −4,52 / −3,85; T4 −4,29 / −3,41 → şart 2 tuttu.
  - İki şart birlikte hiçbir seviyede tutmadı → **DEVAM**.
- 710 / 711, Ekim'in neden zararlı olduğunu teşhis etti. Bu teşhis Kasım kararına girdi değil.

**Bekleyen veri.**
- Kasım ayının tamamı (bugün 2 Kasım).
- Binance aylık arşivi ayın 1–3'ünde yayınlıyor; Kasım dosyaları 1–3 Aralık'ta gelir.
- Arşivde eksik gün çıkarsa (Ekim'de 2026-10-28 vardı) madde 706'daki araçla ham işlemlerden yeniden kurulmalı. Bu adım raporda açıkça belirtilmeli.

**Karar kriteri (madde 650, değişmedi):**
- (1) Ay farkı (önerilen × doz − T4), geçmiş aylık farkların %10 yüzdeliğinin altında **VE**
- (2) ayın en kötü günü T4'ünkünden derin.
- İki seviyede de tutarsa → T4'e geri dönüş. Birinde tutarsa → UYARI. Hiçbirinde → DEVAM.

**Bugünkü durum:** Veri yok. Karar verilemez.

**Sonraki gerekli adım:** 3–5 Aralık arasında:
- `indir_ek_ay` (VERI_EK=uzun)
- gerekirse 706 araçları
- `yeniden_kur`, sinyaller 36 / 48 / 60 / 96 ve metrik paneli
- `AY=2026-11 izleme_ekim_oos.py kos_ana / analiz_ana`
- Bütünlük kontrolü: Kasım öncesi seri, Ekim zeminiyle birebir aynı olmalı. Bütün koşular rc 0 olmalı.
- **Ek veri riski (madde 675):** Ekim'de listelenen coinler 60 günlük yaş kuralıyla Aralık'ta aday olur. Kasım kararını etkilemez (1 Ekim + 60 g = 30 Kasım), ama Aralık kontrolünden önce paketin yeni sembolleri içermesi gerekir. Bu ortamda fapi 451 veriyor; exchangeInfo yalnız sunucudan alınabilir.
- **Zamanlanmış görev yok** (hesapta kayıtlı görev listesi boş). Aralık başında elle başlatılmalı ya da kullanıcı isterse görev kurulmalı.

## 2. MEXC V3

**Mevcut kanıt.**
- Ön kayıt madde 677: Sinyal = Binance + 0,5 × (Binance − MEXC); long 60 sa, short 96 sa; taban P3T2, 2.000 $, iki hiza.
- 676'daki ters yön o veride görüldüğü için ölçüm yalnız 2026-10 sonrası aylarla yapılıyor.

**[ÖLÇÜM] Ekim OOS (1,0x):**

| | V3 | Taban P3T2 |
|---|---|---|
| Ay getirisi | −3,65 | −4,27 |
| Günlük Sharpe | −0,91 | −1,16 |
| En kötü gün | −3,45 | −3,52 |

- Üç şartın üçü de bu ay V3 lehine. Tek ay yalnız bilgi.

**[ÖLÇÜM] Binance tabanından bağımsız katkı (bu çalışmada, mevcut seriler):**
- **Ekim:**
  - V3 ile tabanın günlük getiri korelasyonu 0,986.
  - Günlük fark ortalaması +2,2 bp (sd 35 bp). V3, 31 günün %58'inde daha iyi.
  - Farkın tabanla korelasyonu +0,13.
  - V3 Ekim'de neredeyse tabanın aynısı; +0,6 puanlık fark tek bir ay için gürültü düzeyinde.
- **676 penceresi (2025-06 → 2026-09, örnek içi):**
  - Aynı kural V3 +%373, taban +%793. Günlük korelasyon 0,79.
  - En kötü gün −7,89 / −5,25.
  - Aylık fark çoğunlukla aleyhte: 2025-12 −28,3 · 2026-01 −15,4 · 2026-04 −26,2. Lehte aylar 2026-03 +8,9 · 2026-07 +7,1.
  - Bu pencere karar için kullanılmıyor (ön kayıt), ama ön kayıt bir ADAY çıkarsa "676 penceresiyle çelişmediğinin raporlanmasını" şart koşuyor. **Bugünkü kanıt o pencerede V3'ün belirgin biçimde kötü olduğunu gösteriyor.** Aralık'ta ADAY şartı tutsa bile bu çelişki raporlanmak zorunda.

**Bekleyen veri.**
- Kasım ve Aralık 2026.
- Her ay MEXC funding'inin yeniden indirilmesi (`M676_TAZELE=1`, bu ortamdan erişim var). Ardından *_ozel panelleri ve V3 motoru, iki hiza, tek işçi.

**Karar kriteri (madde 677, değişmedi):** Ekim–Aralık toplamında üç şart birlikte tutmalı:
- 3 aylık getiri ≥ taban
- günlük Sharpe ≥ taban
- en kötü gün tabandan derin değil

Tutarsa → ADAY (676 penceresiyle çelişki raporu zorunlu). ADAY bota otomatik girmez.

**Bugünkü durum:** 1 / 3 ay. Karar verilemez. Üstünlük iddiası yok.

**Sonraki gerekli adım:**
- Aralık başında Kasım koşusu (bilgi).
- Ocak 2027 başında Aralık koşusu ve 3 aylık karar.

## 3. Madde 696 ve 697 (kuraklık savunması izleme önerileri)

**Mevcut kanıt.**
- **696:** Ön kayıtlı dört kol (K1–K4, eşik 6) RED.
  - "K1 eşiği 10" sonradan bulundu (HİPOTEZ, seçim değil): kuraklık dünyalarında DD 7 / 7 ≥ −%15, BAZ CAGR 206 (−%15).
  - Öneri: ileriye dönük izleme kullanıcı kararı; n30 demo metriği olarak eklenmeli (kapı değil).
- **697:** E50 (n30 < 6 iken yalnız eski coin ağırlığı × 0,5, genç tam):
  - BAZ 238 (−4); kuraklık DD en kötü −22,3 → −16,6; kaçan genç kazanç 0.
  - @10 sürümü sonradan bulundu (HİPOTEZ).
  - Öneri: "E50'yi Ekim–Aralık verisiyle ön kayıtlı ileriye dönük izleme (kullanıcı kararı); canlı değişiklik ayrıca onay ve geri dönüş kuralı ister".
- **704 H5:** E50'nin motor doğrulaması; puan 19 / 30, sıra dışı kaldı.

**[ÖLÇÜM] n30 göstergesinin bugünkü değeri** (evrende 60–365 g yaşında coin sayısı, 30 g ortalama; madde 710):
- 2026 Temmuz 5,3 · Ağustos 5,8 · Eylül 5,1 · Ekim 5,1.
- 2022'den beri en düşük düzeyde; 696 / 697'nin "kuraklık" bölgesinde.

**Bekleyen veri / karar.**
- İleriye dönük izleme için **ön kayıtlı bir protokol yazılmadı.** Yalnız "öneri" var, kullanıcı henüz karar vermedi.
- Yazılı bir ileri izleme kuralı yok: hangi kol, hangi eşik, hangi pencere, başarı ölçütü ne. Bu yüzden "önceden tanımlanmış karar koşulu oluştu mu" sorusunun cevabı: **koşul tanımlanmamış.**
- Bu çalışmada eşik uydurulmadı. @10 eşikleri sonradan seçildikleri için ileri izleme kuralına da otomatik dönüştürülmedi.

**Bugünkü durum:** **Kullanıcı kararı bekliyor**, veri değil. Gösterge kuraklık bölgesinde, ama bu bir karar şartı değil.

**Sonraki gerekli adım:** Kullanıcı iki seçenekten birini seçer:
- (a) İzleme yok: konu kapanır; n30 yalnız demo metriği olarak kalır.
- (b) İleri izleme: yalnız önceden kayıtlı kollar (696 K1@6, 697 E50@6) ve 677 tarzı bir 3 aylık kural, sonuçlar görülmeden ön kayda yazılır. Ekim verisi kural yazılmadan önce görüldüğü için pencere Kasım–Ocak olmalı.

## 4. Gerçek emir defteri (madde 701)

**Mevcut kanıt.**
- `defter_db.py` → `emir` tablosu (sunucuda `defter/carry.db`).
- Panelde "İcra · son 30 gün" kartı.
- `icra_ozet` şunları zaten hesaplıyor: TP konan / tam / kısmi / dokunan, dolum oranı, kısmi pay, giriş maker payı, kayma (bp), gerçek komisyon (bp), GTX ilk deneme / kovalama / piyasaya düşen sayıları.
- Kod incelemesinden bulgu: bot PARTIALLY_FILLED olan TP'yi tam dolmuş sayıyor; kalan miktar sonraki turda normal emirle kapanıyor (sıklığı ölçülecek).

**Bekleyen veri.**
- Sunucuda birikmiş emir kayıtları. **Bu araştırma ortamında carry.db yok.** Madde 701'in sunucuya kurulup kurulmadığı (`git pull` ve yeniden başlatma) buradan doğrulanamıyor.
- Bot ayarı değişmeden, demo ya da canlı hesapta kendiliğinden birikmesi gerekiyor.

**Ölçülecek metrikler.** Tanımlar emir tablosunun mevcut sütunlarıyla yazıldı:

| Metrik | Tanım | Karşılaştırılacak model varsayımı (önceden var olan) |
|---|---|---|
| TP dolum oranı | Fiyatın limite değdiği TP / KADEME emirlerinden (dokundu = 1) dolan payı (`icra_ozet.tp.dolum_orani`) | Backtest %100; 695 E: %97 / %90 ROBUST (−3,8 / −4,6), %80 / %70 WEAK (−17 / −29) |
| Kısmi dolum | dolan > 0 ve durum ≠ FILLED olan TP'ler / (tam + kısmi) (`kismi_pay`); kalan miktarın sonraki tur kapanış fiyatı | Backtest'te kısmi dolum yok |
| Maker / taker oranı | Giriş emirlerinde maker_adet × fiyat / dolan × fiyat (`maker_pay`); TP'de aynı oran (yeni sorgu, kod değişikliği gerekmez) | Model: giriş GTX (maker), TP limit (maker) |
| Emir bekleme süresi | FILLED emirlerde guncel − zaman (dakika). Giriş ve TP ayrı; medyan ve p90 | Model: girişte bar kapanışında anında dolum; TP aynı barda dolum |
| Model fiyatı − gerçekleşen fiyat | Giriş: (ort_fiyat / ref_fiyat − 1) × yön (`kayma_bp`). TP: (ort_fiyat / limit_fiyat − 1) × yön (maker'da ~0 beklenir) | 691: TP'de ek 5 / 10 / 20 bp maliyet → CAGR −1,5 / −3,0 / −5,8; 5 / 10 / 20 bp delinmeden dolmaz → −1,6 / −2,8 / −4,2 |
| Kayma ve işlem maliyeti | Kayma + gerçek komisyon (komisyon / notional, bp; `komisyon_bp`); PIYASA_YEDEK payı ayrıca | Model KOM 5 bp; 654: 8 bp / 10 bp'de üstünlük korunuyor; 519: T4'e göre ~29 bp'ye kadar önde |

Ölçüm yeterliliği için öneri (karar eşiği değil, örneklem büyüklüğü):
- TP dolum oranı için en az ~100 "dokunan" TP.
- Kayma ve maker payı için en az ~200 dolan giriş emri.
- Kayıt sayısı bu düzeylerin altındayken sonuçlar yalnız bilgi olarak raporlanmalı.

**Karar kriteri.** Yeni kriter yazılmadı. Gerçek değerler yalnız tablodaki önceden var olan model varsayımlarıyla karşılaştırılacak. Bir fark çıkarsa (ör. TP dolum %90'ın altında), bu "model varsayımı gözden geçirilsin" sinyali olur, otomatik değişiklik değil.

**Bugünkü durum:** Veri bu ortamda yok. Kaç kayıt biriktiği bilinmiyor.

**Sonraki gerekli adım:**
- Kullanıcı panelin "İcra" kartından ya da sunucudaki `defter/carry.db`'den kayıt sayısını kontrol eder.
- Yeterli örneklem oluşunca carry.db'nin salt okunur bir kopyası bu ortama aktarılır; `icra_ozet` ve yukarıdaki iki ek sorgu (TP maker payı, bekleme süresi) bu ortamda çalıştırılır. Üretim koduna dokunulmaz.

## 5. Özet: karar mı bekliyor, veri mi?

| Konu | Bekleyen | Ne zaman |
|---|---|---|
| Kasım OOS (madde 650 kuralı) | **Veri** (Kasım arşivi) | 3–5 Aralık |
| MEXC V3 (madde 677) | **Veri** (Kasım + Aralık); karar 3 ay sonunda | Ocak 2027 başı |
| 696 / 697 izleme | **Kullanıcı kararı** (ileri izleme yapılsın mı; yapılacaksa ön kayıt Kasım verisinden önce) | Kullanıcıya bağlı |
| Emir defteri | **Veri** (sunucuda birikme, yeterli örneklem) | Kayıt sayısına bağlı |

**NO ACTION:** Bugün strateji, parametre ya da canlı ayarda değişiklik gerektiren bir sonuç yok. Kullanıcıdan beklenen tek karar, 696 / 697 için ileri izleme yapılıp yapılmayacağı.
