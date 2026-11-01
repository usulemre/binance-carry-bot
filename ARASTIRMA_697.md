# Araştırma 697 — Fırsat azlığında sermaye koruma, fırsat dönünce kaçırmama (1 Kasım 2026)

> Soru (kullanıcı): yeni coinler azaldığında botun sermayesi nasıl korunur, ve yeni coin fırsatları geri geldiğinde bot bunları kaçırmadan
> çalışabilir mi? Kural: **otomatik strateji değişikliği yok; önce alternatiflerin geçmişteki etkisi ölçülür.**

## Değişmeyenler ve kontroller
Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**. Filtre, kapı ya da otomatik değişiklik yok.

- **Araç:** `arastirma_m697_firsat.py`.
- **Ön kayıt:** KAR_HARITASI "Madde 697 ÖN KAYIT". Sonuçlar görülmeden yazıldı (commit c481469).
- **Motor kopyası:** `/tmp/g33_m690.py`. Madde 690'ın coin-gün defteri kopyası: fiyat, TP, stop ve komisyon ayrı yazılıyor.
- **Koşular:** 16 koşu (baz + 7 kuraklık dünyası, × 2 hiza), tek işçiyle, hepsi rc 0.
  - **Baz:** iki hizada ana motorla **bayt bayt aynı**.
  - **7 kuraklık dünyası:** her biri, madde 694'teki aynı senaryonun çıktısıyla **bayt bayt aynı**.
- **Defter tutarlılığı:** coin-gün defteri toplamı ile günlük kitap getirisinin korelasyonu 0,9999.
  - Baz: 733 / 736 puan.
  - Y365K: 360 / 361 puan.
  - Fark, gün içi bileşiklemeden geliyor.
- **Dönem:** 2021-01-01 → 2026-09-30.
- **Git:** strateji ve motor dosyalarında diff yok.

**Tanımlar:**
- **Genç:** coin yaşı < 365 gün.
- **n30:** botun evreninde (70M hacim, 60 gün yaş, TradFi / D8 hariç) 60-365 gün yaşında coin sayısı. 30 günlük ortalaması, bir gün gecikmeli;
  o gün bilinen bir değer.
- **Net:** fiyat + TP + funding − komisyon.
- **Kuraklık dünyaları:** L50_a/b, L75_a/b (2021+ listelemelerin %50 / %75'i rastgele çıkarıldı), DUR24 / DUR25 (2024-H1 / 2025-H1
  listelemeleri çıkarıldı), Y365K (hiç genç coin yok).

Etiketler: **ÖLÇÜM** veriden ya da motordan · **VARSAYIM** senaryo veya model varsayımı · **HİPOTEZ** doğrulanmamış açıklama.

---

## Kısa cevap

| Test | Bulgu |
|---|---|
| Listeleme akışı | **Kuraklık şu an gerçek [ÖLÇÜM]:** kripto listeleme 2025'te çeyrek başı 52-71, 2026'da 26 / 22 / 18. Ama son 30 / 60 / 90 günlük sayı kısa vadeli getiriyi öngörmüyor (eğilimden arındırılınca ρ ≈ 0,0-0,16). Etki yavaş: bir kohort ~1 yıl genç kalıyor. |
| Genç coin sermayesi | Genç coinler 2024-26'da sermayenin %37'si, kârın %78'i. Maruziyet başı yıllık getiri: genç %375, eski %62. Aynı ay, farklı dünya karşılaştırması: genç payı +10 puan → aylık getiri **+1,7 puan** (%90: +1,0…+2,5). |
| Eski coin alternatifi | **Faydalı.** Genç coin az (n30 < 6) iken eski coin pozisyonları her dünyada pozitif: maruziyet başı yıllık %48-92, Sharpe 1,3-2,4. Nakitten iyi. |
| Short squeeze | Genç short kuyruğu ağır ama ücreti ödeniyor. 60-180 gün short'larda +%100 aleyhte hareket olasılığı eski coinlerin ~10 katı (%0,96 vs %0,09). En kötü tek coin-gün kitapta −%8,7. Ama bu grup, short sermayesinin %18'iyle short kârının en büyük parçası (+141 puan). |
| Fırsat yoğunluğu | Getiri, uygun genç coin sayısı ~4'ün altına inince düşüyor: aylık −2,0…−2,6 puan (ay ortalamasına göre). 4-10 arası nötr, 10-15 arası +3 puan. Sermaye boşta kalmıyor (brüt 0,70-0,75); eski coinlere kayıyor. |
| Nakit mi, eski coin mi | **Tam nakit en kötü seçenek.** Getiri ve Sharpe düşüyor, düşüş bazen derinleşiyor. **Eski coin payını yarıya indirip genç coinlere dokunmamak** (E50) en iyi denge: tüm kitabı küçültmekle aynı korumayı veriyor, ama genç coin kazancını kaçırmıyor. |

**Ana sonuç:**
- Fırsat azlığında sermayeyi korumanın, fırsatı kaçırmayan yolu **yalnız eski coin kolunu küçültmek**; genç coinler her zaman tam ağırlıkta kalır.
- Bütün kitabı küçültmek (madde 696'daki K1) dönüşte genç coin kazancını keser.
  - Gerçek dünyada genç coin sayısının dibi aştığı iki dönemde, sonraki 90 günde genç katkısı +19 ve +25 puan oldu.
- Bu bir ölçüm. Bota girmedi; karar kullanıcıya ait.

---

## T1. Listeleme akışı [ÖLÇÜM]

**Ham kripto listeleme sayısı** (TradFi / D8 hariç; paneldeki ilk veri günü):

| Yıl | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|
| Listeleme | 56 | 28 | 99 | 131 | 241 | 66 |

Çeyrek bazında: 2025 52 / 63 / 71 / 55 · **2026 26 / 22 / 18**.

**Veri boşluğu:**
- Panelde 2026 Eylül'de hiç yeni sembol yok. Zemin Eylül sonunun sembol listesiyle sabit (madde 675).
- Bu yüzden 2026-Q3 ve son 30 gün (L30 = 0) eksik sayılmış olabilir [VARSAYIM].
- 2026-Q1 / Q2'deki düşüş bu boşluktan bağımsız.
- **Kuraklık bugün gerçek:** listeleme 2025'e göre ~%60 az, kabaca L50-L75 dünyalarının düzeyinde.

**Sonraki kitap getirisiyle ilişki** (Spearman, 67 ay sonu; 90 günlük hedefte ardışık aylar örtüşüyor, anlamlılık abartılı):

| Gösterge | Sonraki 30 g | Sonraki 90 g | 90 g, 2021-23 | 90 g, 2024-26 |
|---|---|---|---|---|
| L30 (son 30 g sayı) | 0,19 | 0,31 | 0,19 | 0,29 |
| L60 | 0,20 | 0,35 | 0,25 | 0,35 |
| L90 | 0,22 | 0,40 | 0,30 | 0,43 |
| L30 / son 1 yıl normu | −0,02 | 0,08 | 0,11 | 0,05 |
| L60 / norm | 0,00 | 0,14 | 0,14 | 0,10 |
| L90 / norm | −0,00 | 0,16 | 0,17 | 0,13 |

- Ham sayının ilişkisi büyük ölçüde zaman eğiliminden geliyor: hem listeleme hem getiri 2024-26'da yüksek.
- Eğilimden arındırılınca ilişki neredeyse sıfır. 694 ile aynı sonuç.
- L90 çeyreklerine göre sonraki 90 günün medyanı tek yönlü değil: 25,9 / 16,7 / 40,0 / 30,4.
- L90 ile n30'un 0-180 gün sonraki değeri arasında korelasyon 0,10-0,19.
- **Yorum:** listeleme kuraklığı getiriyi yavaş etkiliyor.
  - Bot coini 60. günden sonra yaklaşık 1 yıl "genç" tutuyor.
  - Bu yüzden bugünkü düşük listelemenin etkisi 2025 kohortu yaşlandıkça, 2026 sonu ile 2027 boyunca görülür [HİPOTEZ].
  - 2026'nın %283'lük getirisi büyük ölçüde 2025 kohortundan geldi.
  - Bugün: L90 15 (son 1 yıl normunun 0,50'si), n30 5,2.

---

## T2. Genç coin sermayesi ↔ getiri [ÖLÇÜM]

| Baz dünya | Sermaye payı % (eski / genç) | Kâr payı % (eski / genç) | Maruziyet başı yıllık % (eski / genç) |
|---|---|---|---|
| 2021-23 | 66,7 / 33,3 | 52,6 / 47,4 | 139 / 250 |
| 2024-26 | 62,8 / 37,2 | 21,9 / 78,1 | 62 / 375 |

- **Gerçek dünya zaman serisi** (aylık; genç brüt payı ile getiri):
  - Aynı ay ρ 0,22; sonraki ay ρ 0,14.
  - Eğilimden arındırılmış pay ile sonraki ay ρ 0,06.
  - **Zamanlama sinyali olarak zayıf.**
- **Dünyalar arası, ay sabit etkili eğim** (aynı ay, 8 dünya, farklı genç coin miktarı; piyasa rejimi sabit tutulmuş oluyor):
  - Genç brüt payı **+10 puan → aylık getiri +1,68 puan** (%90 bootstrap +0,97 … +2,45).
  - **Yorum:** genç coinlerin değeri gerçek ve büyük; ama bunu önceden zamanlamak zor.

---

## T3. Eski coin alternatifi [ÖLÇÜM]

**Eski coin kolunun maruziyet başı yıllık net getirisi %** (komisyon dahil; dünya × n30 durumu):

| Dünya | n30 < 6 | 6-12 | > 12 | n30 < 6'da Sharpe | n30 < 6 gün sayısı |
|---|---|---|---|---|---|
| BAZ | **48** | 137 | 92 | 1,26 | 201 |
| DUR24 | 68 | 125 | 83 | 1,84 | 234 |
| DUR25 | 68 | 79 | 125 | 1,80 | 288 |
| L50_a | 90 | 44 | 294 | 2,24 | 958 |
| L50_b | 92 | 54 | 223 | 2,31 | 978 |
| L75_a | 71 | 86 | 296 | 1,93 | 1.479 |
| L75_b | 61 | 23 | 288 | 1,57 | 1.568 |
| Y365K | 88 | — | — | 2,39 | 2.099 |

- Eski coin kolu genç coin azken **her dünyada pozitif**: yıllık %48-92, Sharpe 1,3-2,4.
- Genç kolun aynı durumdaki getirisi daha yüksek (%164-483). Ama fırsat yokken eski coinlere kaymak **nakitte beklemekten iyi**.
- Baz dünyada eski kol yıl yıl: 2021 261 · 2022 58 · 2023 179 · 2024 74 · 2025 26 · 2026 92. En zayıf yılı 2025.

---

## T4. Genç coin short kuyruğu [ÖLÇÜM]
Madde 689 tek coin kuyruğunu long tarafında ölçmüştü; bu bölüm short tarafını ölçüyor.

**Short coin-günleri (baz, kitap %):**

| Yaş | Coin-gün | Short brüt payı % | Net puan | %0,1 kötü gün | En kötü gün | −%1'den kötü gün | −%2'den kötü gün |
|---|---|---|---|---|---|---|---|
| 60-180 g | 3.760 | 18,1 | **+141** | −2,70 | **−8,65** | 55 | 10 |
| 180-365 g | 3.475 | 15,4 | +59 | −2,06 | −3,09 | 40 | 4 |
| 1-2 yıl | 5.913 | 27,3 | +84 | −1,54 | −2,43 | 38 | 2 |
| > 2 yıl | 8.469 | 39,2 | +9 | −1,28 | −3,34 | 20 | 3 |

**Short epizotları (693): bar içi en büyük aleyhte hareket olasılığı:**

| Yaş | Epizot | Medyan | ≥ +%25 | ≥ +%50 | ≥ +%100 | Epizot net, en kötü %1 (kitap %) | En kötü (kitap %) | Ortalama (bp) |
|---|---|---|---|---|---|---|---|---|
| 60-180 g | 1.770 | %7,5 | %12,1 | %3,6 | **%0,96** | −1,23 | −4,16 | +9,3 |
| 180-365 g | 1.736 | %7,0 | %11,8 | %3,4 | %0,40 | −0,91 | −2,85 | +4,1 |
| 1-2 yıl | 2.451 | %5,8 | %6,7 | %1,1 | %0,16 | −0,89 | −2,13 | +3,8 |
| > 2 yıl | 3.296 | %4,2 | %3,3 | %0,5 | %0,09 | −0,62 | −1,59 | +0,6 |

**Diğer ölçümler:**
- **En kötü short coin-günleri:**
  - IOTX (2021-11-10, 91 günlük) −%8,65.
  - XRP (eski) −%3,34.
  - TAC −%3,09.
  - 1000RATS −%3,08.
- **Kümelenme:** genç short günlerinin %2,8'inde (55 / 1.987 gün) ≥ 2 genç short aynı gün kitapta her biri −%0,5'ten fazla kaybettirdi. ≥ 3 için
  12 gün.
- **Bacak toplamı:** genç short bacağının en kötü günü −%6,7; eski short bacağının en kötüsü −%5,7.

**Yorum:**
- Genç short'larda sıçrama riski ~10 kat sık ve en kötü günler ~2 kat derin.
- Ama bu grup pozisyon başına en kârlı short grubu.
- Kayıp pozisyon büyüklüğüyle sınırlı: tek coin en kötü −%8,7, bacak toplamı en kötü −%6,7, tasfiye yok (689 / 695).
- Referans: madde 664'te short için yaş eşiğini yükseltmek RED çıktı. Bu ölçüm, yeni bir kısıt önermiyor.

---

## T5. Fırsat yoğunluğu [ÖLÇÜM]
Aylık getiri, n30 kovalarına göre. 8 dünya × 69 ay; "ay etkisi" = o ayın dünyalar ortalamasından sapma, yani piyasa rejimi sabit.

| n30 | Ay × dünya | Ham aylık medyan % | Ay etkisinden sapma (puan) | Brüt |
|---|---|---|---|---|
| 0-2 | 109 | 3,5 | **−2,61** | 0,72 |
| 2-4 | 71 | 3,0 | **−2,04** | 0,70 |
| 4-6 | 77 | 5,9 | +0,17 | 0,75 |
| 6-8 | 77 | 4,0 | +0,11 | 0,73 |
| 8-10 | 45 | 6,0 | +1,04 | 0,72 |
| 10-15 | 55 | 8,5 | **+3,02** | 0,72 |
| 15+ | 118 | 9,5 | +1,65 | 0,68 |

- **Doğrusal eğim:** n30 +1 → aylık +0,35 puan (%90: +0,21 … +0,52).
- **Eşik:** aynı anda **~4'ten az** uygun genç coin varken getiri belirgin düşüyor; **~10'un üstünde** belirgin artıyor.
- **Brüt sabit:** sermaye boşta kalmıyor; eksilen genç coinlerin yerini eski coinler alıyor.
- **Bugün:** n30 = 5,2, yani 4-6 kovası. Gerçek evrenin toplam coin sayısı 38 (2021+ medyan 43); kitap aynı anda ~13 coin tutuyor.
- **Sınırlılık:** yalnız gerçek dünyaya bakınca (ay etkisi düzeltmesi yok) kovalar tek yönlü değil: 6,2 / 7,9 / 17,1 / 8,5 / 5,7. Rejim karışıyor.

---

## T6. Nakit mi, eski coin mi? [ÖLÇÜM; örtü VARSAYIM]

**Tasarım:**
- n30 eşiğin altındayken uygulanan kollar:

  | Kol | Ne yapıyor |
  |---|---|
  | E50 | Eski coin katkısı × 0,5; genç coinlere dokunulmuyor |
  | E0 | Eski coin katkısı × 0 (nakit); genç coinlere dokunulmuyor |
  | T50 | Tüm kitap × 0,5 (madde 696'daki K1 benzeri; genç dahil) |
  | T0 | Tüm kitap nakit |

- Geçiş maliyeti 10 bp × ilgili brüt × |Δ|.
- Boşalan sermaye %0 getiri.
- Örtü coin-gün düzeyinde. Küçülen pozisyonun TP / kademe davranışı orantılı varsayıldı; boşalan sermaye başka coine gitmiyor [VARSAYIM].

**Ön kayıtlı eşik n30 < 6** (baz dünyada günlerin %9,5'i):

| Kol | BAZ CAGR | BAZ DD | BAZ Sharpe | Kuraklık CAGR medyan | Kuraklık DD en kötü | Kuraklık DD medyan | Kuraklık Sharpe medyan | Kuraklık en kötü 365 g | Kaçan genç kazancı (BAZ, puan) |
|---|---|---|---|---|---|---|---|---|---|
| A0 baz | 242 | −13,3 | 4,06 | 150 | −22,3 | −16,9 | 3,41 | −9,7 | 0 |
| **E50 eski × 0,5** | 238 | −14,0 | **4,10** | 121 | −16,6 | −14,0 | **3,46** | −4,4 | **0** |
| E0 eski → nakit | 233 | −14,8 | 4,09 | 95 | −14,8 | −13,6 | 3,11 | −5,2 | 0 |
| T50 tüm × 0,5 | 230 | −14,2 | 4,07 | 113 | −16,1 | −14,2 | 3,51 | −4,3 | 14 |
| T0 tüm → nakit | 218 | −15,1 | 3,98 | 74 | −15,1 | −11,7 | 2,99 | −9,6 | 28 |

**Sonradan eşik n30 < 10** (madde 696'da sonuçlar görüldükten sonra bulunan eşik; **HİPOTEZ**; baz dünyada günlerin %37'si):

| Kol | BAZ CAGR | BAZ DD | BAZ Sharpe | Kuraklık CAGR medyan | Kuraklık DD en kötü | Kuraklık DD medyan | Kuraklık Sharpe medyan | Kuraklık en kötü 365 g | Kaçan genç kazancı (BAZ, puan) |
|---|---|---|---|---|---|---|---|---|---|
| A0 baz | 242 | −13,3 | 4,06 | 150 | −22,3 | −16,9 | 3,41 | −9,7 | 0 |
| **E50 eski × 0,5** | **208** | −12,4 | **4,15** | 116 | **−13,4** | −11,5 | 3,54 | −4,4 | **0** |
| E0 eski → nakit | 175 | −12,4 | 3,93 | 85 | **−23,8** | −11,3 | 3,03 | **−23,1** | 0 |
| T50 tüm × 0,5 | 180 | −12,4 | 4,01 | 94 | −11,8 | −10,0 | 3,62 | −4,3 | 57 |
| T0 tüm → nakit | 126 | −12,4 | 3,42 | 49 | −11,5 | −8,4 | 2,75 | −5,7 | 113 |

**Okuma:**
1. **Tam nakit (E0, T0) en kötü seçenek.**
   - Sharpe düşüyor (3,4 → 3,0 / 2,8).
   - E0'da düşük eşikte DD bile derinleşebiliyor: L75_a −%23,8, en kötü 365 gün −%23.
   - Nedeni şu [HİPOTEZ]: geriye yalnız birkaç genç coin kalıyor; kitap çeşitlenmesini kaybediyor ve genç coinlerin oynaklığı tek başına kalıyor.
   - **Eski coinler bir çeşitlendirme ve yastık işlevi görüyor.**
2. **E50 (eski coin yarıya, genç tam) en iyi denge.**
   - İki eşikte de kuraklık dünyalarında Sharpe'ı artırıyor.
   - DD'yi sığlaştırıyor: −22,3 → −16,6 (eşik 6) / −13,4 (eşik 10).
   - **Genç coin kazancından hiçbir şey kaçırmıyor.**
3. **Tüm kitabı küçültmek (T50) ile karşılaştırma:**
   - Kuraklıkta benzer koruma veriyor.
   - Ama baz dünyada 14 (eşik 6) / 57 puan (eşik 10) genç coin kazancını kaçırıyor.
   - Eşik 10'da E50'nin baz getirisi T50'den 28 puan yüksek (208 vs 180).
4. **Fırsat dönüşü (gerçek dünya, n30 < 6'dan çıkışlar):**

   | Çıkış | Sonraki 90 g genç katkı (puan) | Eski katkı (puan) | Kitap |
   |---|---|---|---|
   | 2022-07 | +0,6 | −2,0 | −%1,8 |
   | 2022-11 | **+18,9** | +1,2 | +%21,4 |
   | 2023-01 | **+24,5** | −10,3 | +%14,7 |
   | 2026-08 | +2,5 | +14,3 | +%17,8 |

   - Dönüşte kazancın büyük kısmı genç coinlerden geliyor.
   - n30 göstergesi ~1 ay gecikmeli olduğu için, bütün kitabı küçülten bir kural tam bu dönemde dozu düşük tutar.
   - Genç coinlere dokunmayan E kolları bu kazancı olduğu gibi alıyor.
5. **Bedel:**
   - E50 eşik 6'da baz dünyada −4 puan; ama DD −13,3 → −14,0 ve en uzun su altı 131 → 198 gün (2022'deki eski coin toparlanmasını yarım dozla yaşıyor).
   - Eşik 10'da −34 puan.
6. **Sınır (696 ile aynı):** hiçbir kol Y365K'nın en kötü 365 gününü pozitife çeviremiyor (en iyi −%4,3). Doz derinliği küçültür, işareti
   değiştirmez.

---

## Sonuç ve karar seçenekleri

**Ölçülen (sorunun cevabı):**
- Fırsat azlığında sermayeyi korumak ve fırsat dönünce kaçırmamak birlikte mümkün. Yol, **yalnız eski coin kolunu küçültmek, genç coinleri her
  zaman tam ağırlıkta tutmak.**
- **Nakitte beklemek eski coinlere yönelmekten kötü.** Eski coinler fırsat azlığında da pozitif (yıllık %48-92, Sharpe 1,3-2,4) ve kitabı
  çeşitlendiriyor.
- **Genç short riski** gerçek (~10 kat sık sıçrama) ama karşılığı alınıyor; yeni bir kısıt gerekmiyor (664 ile tutarlı).
- **Bugünkü durum:** kripto listeleme 2025'e göre ~%60 az. n30 = 5,2; eşik 6'nın da 10'un da altında.

**Karar seçenekleri** (bota hiçbiri otomatik girmedi):

| Seçenek | Ne yapar | Bilinen | Risk |
|---|---|---|---|
| Değiştirme | Mevcut haliyle devam | Kuraklıkta takvim yılı bazında zarar yok, DD −%16..−22 | Kuraklık 2027'ye uzarsa düşüş derinleşir |
| E50 @ n30 < 6 (ön kayıtlı) | n30 < 6 iken eski coin ağırlığı × 0,5, genç tam | Bazda −4 puan; kuraklık DD −22 → −17 | Koruma sınırlı |
| E50 @ n30 < 10 (sonradan) | n30 < 10 iken eski coin × 0,5 | Bazda −34 puan; kuraklık DD 7 / 7 ≥ −%13,4; Sharpe ↑ | Eşik sonradan seçildi → önce ileriye dönük izleme |

**Öneri:** E50'yi canlıya almadan önce Ekim-Aralık verisiyle ileriye dönük izlemek; "olsaydı" getirisini ve DD'yi aylık raporlamak.
- Bu izleme ön kayıtla yapılır, canlıya dokunmaz.
- İzlemeyi başlatmak kullanıcı kararı.
- Canlıya almak motor ve bot kodunda değişiklik gerektirir. Bunun için ayrıca kullanıcı onayı ve madde 650 tipi geri dönüş kuralı gerekir.

---

## Sınırlar
- Kuraklık dünyaları karşı-olgu. Piyasanın kendisinin (hacim, funding, oynaklık) değişmediği varsayıldı [VARSAYIM].
- T6 örtüsü motor içi etkileşimi modellemiyor. Gerçek uygulamada eski coin ağırlığını yarıya indiren bir motor koşusu gerekir.
- 2026 Eylül listelemeleri panelde yok (madde 675). Son 30 / 90 günlük sayı eksik olabilir.
- n30 < 10 eşiği madde 696'da sonuçlar görüldükten sonra bulundu. Bu nedenle bu raporda etiketli; seçim değil.
- Aylık panelde dünyalar bağımsız değil (aynı coinlerin alt kümeleri). Bootstrap güven aralıkları ay yeniden örneklemesiyle hesaplandı.
