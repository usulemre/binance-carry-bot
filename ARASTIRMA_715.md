# ARAŞTIRMA 715 — Yeni Alpha Kaynağı Keşfi

**Karar: NO NEW TEST.**

- Strateji, parametre, üretim kodu ve canlı ayar değiştirilmedi. Motor çalıştırılmadı.
- 714'ün RED sonucu korunuyor; short yaşı ya da benzeri bir hipotez yeniden açılmadı.
- **Araç:** yalnız A adayı için ucuz bir ön araştırma yapıldı (`arastirma_m715_on_arastirma.py`, rc 0). Panel ve önerilen ayarın resmi günlük serisi (EK_T7KKS) kullanıldı.

## 1. İncelenen geçmiş araştırmalar

**Kâr kaynakları** (madde 690 / 711 / 712 / 713 ölçümleri; 1,0x, % puan):

| Kaynak | Ne biliniyor | Madde |
|---|---|---|
| Long fiyat (TP hariç) | Her yıl çoğunlukla negatif (2025 −82, 2026 −109). Long tarafın taşıdığı risk bu | 690, 711 |
| Short fiyat | Hedge. Yıla göre ± (2022 +43, 2024 −33) | 690, 711 |
| Long funding | 2025–26'da ana gelir kalemi (68 / 82). Her ay aşırı negatif funding'li 1–3 coinden geliyor, yarı ömür 2–3 gün | 712, 713 |
| Short funding | Küçük, sabit (~20 / sy) | 712–714 |
| Kademeli TP | Kârın ana motoru (her yıl 70–178). Fitilden geliyor; oynaklıkla esneklik 1,89 | 690–693 |
| Yeni coin / yaş | 2024–26'da net kârın %78'i 1 yaşından genç coinlerden. Kuraklıkta en kırılgan nokta | 693–698, 703, 705 |
| Rejim / coin hareketi | Hiçbir rejim negatif değil. Gerçek zamanlı tespit kapı olarak işe yaramıyor | 693, 695 |

**Okunan diğer aileler:**
- **Short yenileme:** 493–501, 511–513, 545–546, 553, 568 (40 sa üretimde). Short yapısı 521.
- **Tutma süresi:** 215, 264, 522, 679.
- **Momentum:** 237, 381–383, 411.
- **Funding zaman yapısı:** 516, 547–549, 556–557.
- **Olay stratejileri** (pump short, dump long, OI patlaması, tasfiye sonrası): 201, 241, 330'lar.
- **Diğer sinyaller:**
  - ML ile 18 özellikli kesitsel tahmin: 389
  - çift ticareti ve oynaklık sıkışması: 384
  - kalabalık / long-short oranı / top trader: 244, 627, 649
  - prim ve baz: 410, 413, 551, 581–583
  - fırsata göre brüt (BRUT_PRIM, üretimde): 239, 581–583
- **Dinamik doz:** 555, 597, 620, 685, 696, 697.
- **Ortak davranış ve BTC/ETH trend kolu:** 667, 686.
- **Ödeme anına göre icra saati:** madde 647 (5 dk veri, 324 bin ödeme olayı). Sonuç: kural yok, hiza serbest.
- **Yeni veri:** 387, 394, 550. MEXC V3 677 (Aralık'ta karar).
- **Son seri:** 690–714.

## 2. Aday listesi (en fazla 3)

Kullanıcının beş örnek alanından ikisi aday listesine alınmadı:
- **Eşzamanlı long / short fırsatlarında sermaye verimliliği:** bu, üretimdeki BRUT_PRIM'in kendisi (239, 581–583).
- **Göreli gücün zaman içindeki değişimi:** bu, kesitsel momentum ailesi (237, 381–383, 411; ML 389).

Kalan üç aday:

**A. Coinler arası liderlik / gecikmeli yayılım (lead-lag).** BTC'nin ya da büyük coinlerin hareketi, alt coinlerin sonraki hareketini öngörüyor mu?

**B. Funding aşırılığının sırası.** Funding fiyat hareketinden önce mi oluşuyor, sonra mı? Ve bu, pozisyonun değerini belirliyor mu?

**C. Ani oynaklık artışı → sonraki TP fırsatı / doz.**

## 3. Örtüşme ve yenilik değerlendirmesi

| Soru | A. Lead-lag | B. Funding–fiyat sırası | C. Oynaklık sıçraması |
|---|---|---|---|
| Gerçekten yeni mi? | **Proje içinde evet.** KAR_HARITASI'nda lider / gecikmeli yayılım taraması yok | **Hayır.** 201 (funding olayın fiyatıdır), 196 / 518 pompa filtresi, 383 momentum vetosu (dump sonrası long'u eler, RED), 556 / 557 funding eğimi (RED), 712 yarı ömür, 713 sönme–fiyat (UNKNOWN) | **Hayır.** 691 (TP ↔ tutulan coin oynaklığı r +0,69, TP sayısını belirliyor), 693 (yüksek oynaklık d → d+1 en iyi rejim, kapı önerilmez), 685 V20 / V60 iki yönlü oynaklık dozu (RED; 704 H4 bunun tersi) |
| Giriş anında ölçülebilir mi? | Evet (gecikmeli getiri) | Evet | Evet |
| Look-ahead / survivorship | Düşük. Delist dahil panel | Düşük | Düşük |
| Ekonomik olarak uygulanabilir mi? | **Zayıf.** Carry kitabı piyasa-nötr; yön sinyalinin carry'ye girdiği her denemede kitap bozuldu (383 yasası). Ayrı motor 237 / 384 duvarına çarpıyor. 4 sa veri ve 8 sa'lik bot turu, kısa ufuklu yayılımı yakalayamaz | Yeniden adlandırma; uygulanabilir hâli test edildi | TP / doz araştırmasının tekrarı |
| Mevcut kâr değişkeninin yeni adı mı? | Hayır | **Evet** (funding + fiyat filtresi) | **Evet** (TP ↔ oynaklık, dinamik doz) |
| Bağımsız OOS mümkün mü? | Evet (2025-01+) | — | — |

**[ÖLÇÜM] A için ön araştırma** (evren: 70 M hacim ve 60 gün yaş eşiğini geçen coinler; alt sepeti = medyan getiri):

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| 4 sa: BTC(t) ile alt(t+1) korelasyonu | −0,10 | −0,01 | −0,05 | −0,07 | +0,01 | −0,00 |
| 1 g: BTC(t) ile alt(t+1) korelasyonu | −0,04 | −0,07 | −0,10 | −0,08 | −0,04 | −0,00 |

- BTC'nin yönünde alt sepeti tutmak (maliyet hariç): 4 saatlik barda −7,6 bp, günlük barda −19,9 bp. Ortalama hareket bar başına 129 ve 347 bp. Devam yok, hafif ve sönen bir geri dönüş var.
- Kitabın ertesi gün getirisi ile bugünkü BTC getirisi arasındaki korelasyon +0,009 (n 2.295).
- **Yorum:** 4 saatlik ve günlük ufukta liderlik / yayılım kenarı yok.
  - Görülen geri dönüş, alt sepetin genel yönüne dair bir zamanlama sinyali; kesitsel değil.
  - 2025–26'da sıfıra inmiş.
  - Carry kitabının fiyat bacağıyla ilişkisi yok.

## 4. Veri ve metodoloji riskleri

- **Saat altı lead-lag test edilemedi.** Panel 4 saatlik. Saat altı lead-lag için 1 dakikalık veri gerekir; arşivden indirilebilir. Ama bot 8 saatte bir tur atıyor, saat altı kenar bu yapıda uygulanamaz.
- **Ön araştırmada yalnız medyan alt sepeti kullanıldı.** Coin bazlı beta etkileşimi ölçülmedi. 389'daki ML modeli 1–90 günlük getiriler, beta ve diğer 16 özellikle kesitsel tahminde RED çıkmıştı.
- **B ve C'yi test etmek, sonucu bilinen eksenlerde parametre taraması olur.** Bu, kullanıcının yasakladığı "farklı isimle tekrar" anlamına geliyor.

## 5. Karar: NO NEW TEST

**Gerekçe:**
- Üç adaydan yalnız A gerçekten yeni.
- A'nın ön ölçümü 4 saatlik ve günlük ufukta kenar göstermiyor; kitapla ilişkisi de yok.
- Uygulanabilir bir entegrasyon yolu yok:
  - yön sinyalini carry'ye karıştırmak: 383
  - ayrı bir kol açmak: 237 / 384 / 686
- B ve C mevcut kâr değişkenlerinin yeniden adlandırılmış hâli ve uygulanabilir biçimleri test edilmiş.
- Bu koşullarda açılacak bir test, geçmişe uyum riskini taşır ve bilgi değeri düşük olur.

**Açık kalan, yeni araştırma gerektirmeyen işler:**
- Kasım OOS (madde 650 kuralı).
- 677 MEXC V3 kararı (Ekim–Aralık toplamıyla).
- 697 E50 / 696 K1 ileriye dönük izleme kararı.
- Canlı icra verisinin birikmesi (madde 701 emir defteri). TP dolum oranı ve kayma gerçek veriyle ölçülebilir hale gelince, 691 / 695'te UNKNOWN kalan icra soruları ayrıca ele alınabilir.

## 6. Test

Test açılmadı; ön kayıt ve sonuç yok. Ön araştırmanın çıktısı `arastirma_m715_on_arastirma.py` ile yeniden üretilir.

## 7. KAR_HARITASI karar özeti

Madde 715: NO NEW TEST.
- 3 aday incelendi: A lead-lag, B funding–fiyat sırası, C oynaklık sıçraması.
- B ve C yeniden adlandırma (201 / 383 / 556–557 / 712–713; 685 / 691 / 693).
- A yeni, ama BTC → alt t+1 korelasyonu 4 sa ve 1 g'de −0,10..+0,01 (2025–26 ≈ 0). Kitap(t+1) ~ BTC(t) +0,009. Entegrasyon yolu yok (383 / 237 / 384).
