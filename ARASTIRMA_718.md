# ARAŞTIRMA 718 — BAĞIMSIZ ALPHA MOTORLARI

Kullanıcının başlığı "Strateji Araştırması 717"; 717 numarası Hyperliquid testine verildiği için bu çalışma 718.

**Karar: NO NEW STRATEGY.** Likidasyon ailesi için **VERİ BEKLİYOR**.

- Test açılmadı. Üretim kodu, strateji, sermaye dağılımı ve canlı ayarlar değişmedi.
- Bu çalışmada yalnız veri envanteri çıkarıldı; getiri ölçülmedi.

## 1. Kategoriler

Kullanıcının istediği ayrım:
- Aynı stratejinin farklı parametresi
- Mevcut stratejiye yeni bir filtre
- Gerçekten farklı bir alpha kaynağı
- Bağımsız çalışabilecek alternatif strateji

Yalnız son ikisine bakıldı. Aşağıdaki beş aileden hiçbiri mevcut carry kitabının filtresi ya da parametresi olarak önerilmiyor.

## 2. Veri envanteri

data.binance.vision ve bu ortamdaki dosyalar 2026-11-03'te kontrol edildi.

| Veri | Durum | Dönem / kapsam | Not |
|---|---|---|---|
| Perp 4 sa mum, hacim, taker | VAR | 2020-01 → 2026-10, 853 sembol, delist dahil | Ana zemin |
| Funding (gerçek ödeme zamanı) | VAR | 2020-01 → 2026-10 | %99,7 tam (madde 687) |
| OI, long/short oranı, top trader, taker oranı (metrics) | VAR | 2022-02-23 → 2026-10; ortalama sembol sayısı 2022 105 · 2023 160 · 2024 234 · 2025 298 · 2026 275 | 2020–21 YOK; bağımsız örnek kısa |
| Prim endeksi (perp − spot sepeti) | VAR (arşiv) | premiumIndexKlines | 550 / 551 / 581'de kullanıldı |
| Spot 4 sa mum | VAR (arşiv) | spot/daily/klines | Spot listeleme günü tablosu da var (705) |
| Çeyreklik vadeli | VAR, yalnız BTC / ETH | — | 220 |
| **USDⓈ-M likidasyon kayıtları** | **YOK** | Arşivde `futures/um/daily/liquidationSnapshot/` klasörü boş. Yalnız COIN-M (cm) için var | Geçmiş likidasyon verisi yok; fapi bu ortamda 451 |
| MEXC funding | VAR | 2025-06 → | 676 / 677 |
| Hyperliquid funding | VAR | 2023-05 → | 717 |
| MEXC / diğer borsa fiyat mumları (saat altı) | Bu ortamda yok | — | API'den sınırlı geçmiş |

## 3. Aileler: örtüşme ve yenilik

| Aile | Geçmiş araştırma | Bağımsız mı? | Veri | Değerlendirme |
|---|---|---|---|---|
| **A. Likidasyon kaynaklı hareketler** | 395 E10 "tasfiye sonrası" (OI −%25 ve fiyat −%10 vekili): IS'te güçlü, OOS'ta gün kümelenmesiyle şişmiş; harmanda RED, "rejim aracı". 201 olay ailesi (funding olayın fiyatı) | Gerçek likidasyon kümeleri ile proje içinde yeni; vekil ölçüm denendi | **Geçmiş veri YOK** (UM arşivi boş) | **VERİ BEKLİYOR** |
| **B. OI–fiyat uyumsuzluğu** | 649 (OI 7 g / 1 g, OI − fiyat, taker oranı: hepsi RED) · 201 OI patlaması short (fiyat +58,6 / funding −80,4 → net −21,8) · 395 E10 · 389 ML (OI değişimi dahil 18 özellik, RED) · 244 (IC güçlü, P&L ters) | Hayır; dört ayrı denemede ölçüldü | 2022-02 → | **Tekrar** — önerilmez |
| **C. Spot–perp baz** | 220 çeyreklik baz: net +%2,2 / yıl, yalnız BTC / ETH, RED · 550 / 551 prim endeksi (perp − spot sepeti) → funding tahmini · 581–583 prim çarpanı (BRUT_PRIM, üretimde) · 386 spot şartı | Hayır. Baz ile funding aynı kaldıraç primini fiyatlıyor (220, 201); baz arbitrajı = funding carry | VAR | **Yeniden adlandırma** — önerilmez |
| **D. Borsalar arası fiyat / keşif** | Funding farkı: 676 / 677 / 717 (V3, iki borsada ters sonuç). Fiyat keşfi: 715 (BTC → alt, 4 sa / 1 g'de kenar yok) | Fiyat arbitrajı farklı bir kaynak, ama gerçek arbitraj saniyeler içinde kapanır. İki borsada envanter, transfer ve gecikme gerekir. 8 saatlik bot yapısıyla uygulanamaz | Saat altı çapraz borsa fiyatı yok | **Uygulanamaz** (bu altyapıyla) |
| **E. Bağımsız trend takibi** | 686 BTC / ETH 60 g trend kolu: tek başına %19 / yıl, Sh 0,99, carry ile kor. −0,06, carry'nin en kötü 20 gününde +%0,66 → gerçek hedge, ama eşit riskte harman RED (carry'nin derin düşüşleri alt / tek coin çöküşleri, BTC trendi yakalamıyor) · 384 kırılım (sıkışma) RED · 237 / 381 / 411 kesitsel momentum (tek rejim) · 395 180 g kırılım olayı | Bağımsızlık ölçüldü (kor. −0,06) ama "ikinci motor" olarak getiri eşit riskte geri kazanılamadı | VAR | **Tekrar** — yeni bir zaman ufku ya da kırılım tanımı denemek, 686 / 384'ün parametre taraması olur |

## 4. Ön değerlendirmeye alınabilecek tek aday: A (likidasyon)

- **Hipotez [HİPOTEZ]:** Bir coinde kısa sürede yoğun zorunlu kapanış (likidasyon kümesi), aşırı tepki yaratır. Uzun likidasyon dalgası sonrası fiyat 1–3 günde kısmen geri döner, ya da tersine devam eder. Bu etki funding'den bağımsız bir fiyat davranışıdır.
- **Ekonomik gerekçe:** Likidasyon emirleri fiyata duyarsız piyasa emirleridir. Likidite sağlayan taraf bu aşırı hareketin karşı tarafında prim alabilir; ama bu, 201'deki "funding = olayın fiyatı" yasasıyla çatışabilir.
- **Veri gereksinimi:** Coin bazında likidasyon miktarı ve yönü, saat altı çözünürlükte. **Binance USDⓈ-M için geçmiş arşiv yok.** Yalnız canlı akış (`!forceOrder@arr`) var; o da sembol başına saniyede yalnız son likidasyonu verir, yani eksik bir örneklem.
- **Örtüşme:** 395 E10 aynı olayın vekiliydi (OI düşüşü ve fiyat düşüşü). OOS işlem t'si gün kümelenmesiyle şişmişti; gün başına t +2,06; plasebo benzer. Gerçek likidasyon verisi bu vekilden daha iyi bir ölçüm olurdu, ama yön ve büyüklük konusunda önsel olasılık düşük.
- **RED kriteri (veri gelirse yazılacak ön kayıt için taslak):**
  - Bağımsız OOS'ta, gün başına toplanmış getiri t ≥ 2.
  - Aynı fiyat hareketi ama düşük likidasyon plasebosunu en az 0,5 Sharpe geçmeli.
  - 5 bp maliyet ve gerçekçi dolumdan sonra pozitif.
  - Carry ile günlük korelasyon ≤ 0,3.
  - Long ve short ayrı raporlanır.
  - Tek coin ya da tek gün katkısı çıkarılınca işaret değişmemeli.
- **Ne gerekir:** Sunucuda, botun dışında, salt okunur bir toplayıcı (`!forceOrder@arr` WebSocket → günlük dosya).
  - Emir göndermez, anahtar gerektirmez.
  - Bu bir üretim değişikliği değil, ayrı bir veri işi; yine de kullanıcı onayı ister.
  - Anlamlı bir örneklem için en az 6–12 ay birikim gerekir: yüzlerce küme olayı ve en az iki farklı piyasa rejimi.
  - Bu ortamdan Binance API'sine erişim yok (451); toplayıcı ancak sunucuda çalışabilir.

## 5. Değerlendirme kriterleri, özet

| Kriter | A | B | C | D | E |
|---|---|---|---|---|---|
| Mevcut stratejiden bağımsız mı? | muhtemel | ölçüldü, değil | değil (aynı prim) | evet | evet (kor. −0,06) |
| Tarihsel veri var mı? | **yok** | 2022+ | var | yok (saat altı) | var |
| Look-ahead riski | düşük | düşük | düşük | — | düşük |
| Survivorship kontrolü | — | var (delist dahil) | var | — | var |
| Maliyet sonrası avantaj | bilinmiyor | yok (649, 201) | net küçük (220) | uygulanamaz | var ama harmanda geri kazanılmıyor (686) |
| Bağımsız OOS | birikimden sonra | denendi | denendi | — | denendi |
| Karar | **VERİ BEKLİYOR** | tekrar | yeniden adlandırma | uygulanamaz | tekrar |

## 6. Karar

**NO NEW STRATEGY.** Bugünkü veriyle test edilebilir, gerçekten yeni ve geçmiş RED'lerin tekrarı olmayan bağımsız bir strateji yok.

**VERİ BEKLİYOR (A, likidasyon):**
- Kullanıcı onaylarsa sunucuya botun dışında, salt okunur bir likidasyon toplayıcısı kurulabilir.
- Veri birikince (en az 6–12 ay), bölüm 4'teki RED kriterleriyle ön kayıt yazılır ve tek test açılır.
- Onay yoksa konu kapanır.

**İkinci strateji arayışı için not:** 686'nın ölçümü önemli. Bağımsız bir trend kolu gerçek bir hedge (kötü günlerde kazanıyor), ama carry'nin bağlayıcı riski haftalara yayılan tek coin / alt çöküşleri. BTC / ETH trendi bunları yakalamıyor. Bu yüzden ikinci bir motorun değeri, ancak carry'nin kendi kuyruk tipine (alt / tek coin çöküşü) karşı kazanıyorsa eşit riskte görünür. Bu, gelecekteki adaylar için bir eleme sorusu olarak kayda geçiyor.
