# ARAŞTIRMA 713 — FUNDING FIRSATININ ÖMRÜ VE POZİSYON GETİRİSİ

Bu çalışma yalnız ölçüm ve muhasebe karşı-olgusudur. Strateji, parametre ve canlı bot değiştirilmedi. Ön kayıt KAR_HARITASI madde 713'te, sonuçlar görülmeden yazıldı ve depoya gönderildi.

- **Araç:** `arastirma_m713_firsat_omru.py`. Tek çalıştırma, rc 0. Tam çıktı her çalıştırmada yeniden üretilir.
- **Veri:** madde 711 tam geçmiş defteri (P3T2, iki hiza, 2020-07 → 2026-10).
  - Defter, önerilen ayarın resmi çalıştırmasıyla (EK_T7KKS) birebir aynı. Değişiklik yokken byte-parity sağlandı.
  - Pozisyon tanımı madde 712'dekiyle aynı: aynı hiza, sembol ve yönde kesintisiz günler. 15.456 pozisyon (6.918 long, 8.538 short), 110.669 pozisyon-gün.
- **Motor:** bu araştırmada yeni motor çalıştırması yok. Tutma süresinin motor sonuçları zaten var (215 / 264 / 522 / 679 / 496 / 520). Karşı-olgular muhasebe yöntemiyle hesaplandı (bölüm 5).
- **Birim:** "sy" sermaye-yıl başına demek, bütün değerler % puan ve 1,0x doz. Yaş 0, giriş günü.

## 1. 712'nin dört fikri: değerlendirme ve seçim

| # | Fikir | Yenilik | Veri yeterliliği | Geçmişle çakışma | Beklenen bilgi değeri | Test maliyeti |
|---|---|---|---|---|---|---|
| 1 | Funding yarı ömrü (2–3 g) ile long tutma süresi (medyan 7 g) uyuşmuyor | Orta. Tutma süresi denendi; pozisyon yaşına göre ayrışım ve nakitte kapama denenmedi | Yeterli (defter + ham funding) | 215 / 264 / 522 / 679 (5 g yerinde, doz düğmesi) · 496 RED · 520 RED (ağırlık yeni girene devredilince yoğunlaşma) | **Yüksek.** Funding'in sönmesinin pozisyonun değerini düşürüp düşürmediğini doğrudan söyler | Düşük (muhasebe) |
| 2 | Short tarafta aşırı pozitif funding'li pozisyonlar | Düşük-orta | Yeterli | 603 short rezerv RED · 386 spot şartı · REZ_ESIK_S | Orta (kazanç funding'den değil TP'den) | Yüksek (motor + yeni düğme) |
| 3 | Aylık "aşırı negatif funding coin" sayısı izleme göstergesi | Orta | 76 ay; öngörü testi için zayıf | 690 / 694 / 695: gerçek zamanlı göstergeler öngörü kanıtlayamadı | Düşük-orta (izleme amaçlı) | Düşük |
| 4 | Kuraklık savunması funding yerine TP ve fiyata odaklansın | Düşük | Yeterli | 696 / 697 / 703 / 705 çoğu RED; 697 E50 izleme önerisi açık | Düşük | Yüksek |

**Seçilen:** fikir 1. En yüksek bilgi değeri ve en düşük maliyet onda. Daha önce denenmemiş tarafı, avantajı sönen tek pozisyonu kapatıp sermayeyi nakitte bırakmak; 520'deki yoğunlaşma etkisi burada yok.

## 2. Gerçekleşen sonuç: pozisyon yaşına göre getiri

**[ÖLÇÜM] LONG:**

| Yaş (gün) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7–9 | 10–14 | 15+ |
|---|---|---|---|---|---|---|---|---|---|---|
| Sermaye payı % | 2,1 | 6,0 | 8,0 | 9,2 | 10,1 | 9,0 | 6,2 | 13,0 | 13,2 | 23,2 |
| Funding / sy | 183 | 145 | 89 | 72 | 62 | 70 | 90 | 95 | 90 | 92 |
| TP / sy | 248 | 201 | 161 | 180 | 118 | 146 | 219 | 143 | 134 | 93 |
| TP hariç fiyat / sy | −172 | −232 | −131 | +65 | −16 | −39 | +49 | −110 | +118 | +15 |
| Komisyon / sy | 37 | 10 | 5 | 3 | 3 | 8 | 9 | 6 | 5 | 4 |
| **Net / sy** | **222** | **94** | **114** | **313** | **159** | **169** | **347** | **121** | **332** | **193** |
| TP olan gün payı % | 1,4 | 2,2 | 2,0 | 2,0 | 1,5 | 1,4 | 2,3 | 1,6 | 1,8 | 1,6 |

**[ÖLÇÜM] SHORT:**

| Yaş (gün) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7–9 | 10–14 | 15+ |
|---|---|---|---|---|---|---|---|---|---|---|
| Sermaye payı % | 7,6 | 19,0 | 14,0 | 9,6 | 7,6 | 5,8 | 4,7 | 9,8 | 8,5 | 13,5 |
| Funding / sy | 18 | 20 | 21 | 21 | 19 | 23 | 24 | 23 | 23 | 21 |
| TP / sy | 255 | 217 | 171 | 150 | 198 | 168 | 171 | 128 | 142 | 141 |
| TP hariç fiyat / sy | −155 | +12 | −10 | −1 | −10 | −16 | −101 | −17 | −89 | −78 |
| **Net / sy** | **79** | **237** | **164** | **156** | **193** | **161** | **80** | **121** | **65** | **73** |
| TP olan gün payı % | 4,0 | 7,1 | 5,3 | 5,3 | 5,2 | 4,8 | 4,5 | 3,8 | 3,9 | 3,9 |

**[ÖLÇÜM] Yıl bazında net / sy, yaş 0–2 ile yaş ≥ 3:**

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Long 0–2 g | 251 | 139 | −122 | 160 | 172 | 145 | 185 |
| Long ≥ 3 g | 317 | 425 | −41 | 422 | 116 | 163 | 233 |
| Long ≥ 3 g sermaye payı % | 89 | 86 | 85 | 86 | 82 | 81 | 79 |
| Short 0–2 g | 8 | 89 | 243 | 57 | 120 | 271 | 400 |
| Short ≥ 3 g | 100 | 205 | 194 | −50 | 71 | 142 | 174 |

**[ÖLÇÜM] Gruplara göre long net / sy (yaş 0 → 3 → 10–14):**
- **Genç coinler:** 374 → 420 → 608.
- **Eski coinler:** 113 → 232 → 127.
- **Giriş carry'si en uç olanlar:** 149 → 595 → 145.
  - Funding / sy 508 → 199 → 222: avantaj eriyor ama net düşmüyor.

## 3. Giriş avantajı ve sonraki günlerde gerçekleşen funding

**[ÖLÇÜM] Long funding / sy, girişten itibaren birikimli:**
- İlk 1 gün 183
- İlk 2 gün 155
- İlk 3 gün 122
- İlk 5 gün 92
- İlk 7 gün 88

Sermaye ağırlıklı giriş carry'si 82, medyanı 4. İlk günlerdeki fazla funding 5–7 günde giriş seviyesine iniyor; bu 712'deki 2–3 günlük yarı ömürle tutarlı.

**[ÖLÇÜM] Short:** funding / sy 18–20 arasında sabit; sönme yok.

## 4. Sönme ile fiyat yönü

Örneklem: giriş carry'si pozitif olan ve en az 4 gün tutulan long pozisyonlar (n 3.824). Ölçü betimseldir, aynı dönemi kapsar.

**[ÖLÇÜM]**
- Medyan sönme %73.
- Sönme ile 0–3. gün fiyat getirisi arasındaki Spearman korelasyonu −0,10. 3. günden çıkışa kadarki fiyat getirisiyle +0,11.
- Yıl bazında (sönme ile 0–3. gün fiyatı): 2020 +0,00 · 2021 +0,07 · 2022 −0,08 · 2023 −0,24 · 2024 −0,09 · 2025 −0,17 · 2026 −0,09.

| Sönme çeyreği | Medyan fiyat, 0→3 g | Medyan fiyat, 3 g→çıkış |
|---|---|---|
| Az söndü | +%0,6 | −%4,7 |
| 2 | −%1,1 | −%2,1 |
| 3 | −%3,6 | −%2,6 |
| Çok söndü | −%1,8 | −%0,6 |

[VARSAYIM] Funding'in hızlı sönmesi ilk günlerde biraz daha kötü fiyatla birlikte geliyor, sonrasında tersine dönüyor. İlişki zayıf, karar kuralına dönüşecek güçte değil.

## 5. Karşı-olgu: erken kapatma (muhasebe)

**Kurgu:**
- Kapanan sermaye nakitte kalır; getirisi 0 sayılır (fırsat maliyeti).
- Kapanış gününe |ağırlık| × 5 bp ek komisyon yazılır.
- Kapanıştan sonraki günlerin defter katkısı (TP ve kademe dahil) çıkarılır.
- Karar yalnız geçmiş bilgiyle verilir.
- Motor çalıştırılmadı. Gerçek motorda serbest kalan koltuk sonraki dengelemede dolacağı için sonuç farklı olabilir; bu yüzden bu yöntemle en iyi sınıf PROMISING olabilir.

**[ÖLÇÜM]**

| | CAGR % | Sharpe | Maks DD % | En kötü gün % | Sh ≤2024 | Sh 2025+ | Eşit risk (doz / yıllık %) | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Taban P3T2 | 239,3 | 4,05 | −13,3 | −7,41 | 4,03 | 4,14 | 1,15 / 315 | 472 | 63 | 309 | 118 | 267 | 267 |
| Kol A: yaş 3 sonunda kapat | 84,5 | 2,36 | −16,9 | −5,73 | 1,84 | 3,54 | 0,85 / 70 | 80 | 102 | 15 | 51 | 167 | 131 |
| Kol B: avantaj sönünce kapat | 158,1 | 3,35 | −20,2 | −6,16 | 3,32 | 3,46 | sağlanamıyor (0,80x'te bile DD T4 sınırını aşıyor) | 236 | 110 | 161 | 84 | 205 | 150 |

**Kol A:** 6.741 pozisyon erken kapanıyor, 650 sermaye-gün serbest kalıyor. Tabana göre kayıp:
- funding −152,3
- TP −229,9
- fiyat −6,2
- ek komisyon −16,3
- Net fark −374,5 puan. Ondan en büyük etkilenen coin (TRB) çıkarılınca −329,9; işaret aynı.
- Yalnız 2022'de kol lehine (+22,7); diğer bütün yıllar aleyhine.

**Kol B:** 4.380 pozisyon kapanıyor, 345 sermaye-gün serbest kalıyor. Tabana göre kayıp:
- funding −38,7
- TP −103,5
- fiyat −30,7
- ek komisyon −10,5
- Net fark −165,5 puan. Ondan en büyük etkilenen coin (RIVER) çıkarılınca −136,5; işaret aynı.
- Yalnız 2022'de kol lehine (+26,1).

**İşlem sayısı:** taban 15.456 pozisyon. Kol A buna 6.741, Kol B 4.380 erken kapanış ekliyor.

## 6. Yorum

- **[ÖLÇÜM] Long tarafta funding gerçekten 2–3 günde eriyor, ama pozisyonun değeri erimiyor.**
  - Funding / sy, yaş 0'da 183 iken yaş 3–4'te 62–72'ye iniyor.
  - Net / sy ise yaş ≥ 3'te yaş 0–2'den yüksek: 7 yılın 6'sında (yalnız 2024'te düşük).
  - Long sermayesinin %79–89'u yaşı ≥ 3 olan pozisyonlarda; kârın büyük kısmı TP'den ve sonraki fiyat hareketinden geliyor.
- **[ÖLÇÜM] Erken kapatmak iki kolda da büyük kayıp.** Kaybın çoğu kaçırılan TP'den geliyor; bu, madde 692'nin "TP'nin %91'i ilk 7 günde" bulgusuyla tutarlı.
- **[HİPOTEZ, ölçülmedi] Short tarafta tersi görünüyor.** Net / sy yaş 0–2'de daha yüksek: 2022–2026'nın 5 yılında. Short'larda funding sönmüyor; erken yaş avantajı TP'den geliyor. Bu bir ön kayıt hipotezi değildi, sınıflandırılmadı. S_REB (madde 493) ve 521 ile çakışma kontrolü yapılmadan yeni araştırma konusu yapılmamalı.

## 7. Sınıflandırma

| Hipotez / kol | Sonuç | Sınıf |
|---|---|---|
| H713: long net / sy, yaş ≥ 3'te yaş 0–2'nin yarısından az | Tersi: 6 / 7 yılda yaş ≥ 3 daha iyi | **RED** |
| Kol A: yaş 3 sonunda kapat (nakit) | CAGR 239 → 85, Sharpe 4,05 → 2,36, eşit risk 315 → 70 | **RED** |
| Kol B: funding avantajı sönünce kapat (nakit) | CAGR 239 → 158, Sharpe 4,05 → 3,35, DD −13 → −20, eşit risk sağlanamıyor | **RED** |
| Sönme ile fiyat yönü ilişkisi | Spearman −0,10 / +0,11, yıllarda tutarsız | **UNKNOWN** (zayıf, betimsel) |

Sonuç, tek bir coine ya da tek bir yıla bağlı değil: en büyük katkılı coin çıkınca işaret değişmiyor, yıllar da aynı yönde.

## 8. Veri ve sınırlamalar

- **Çözünürlük günlük.** Gün içinde kapatılıp yeniden açılan pozisyon tek pozisyon sayılıyor. Yaş 0 kısmi bir gün; giriş komisyonu bu güne yükleniyor, bu yüzden yaş 0'da net / sy düşük görünüyor.
- **Yaş ≥ 3'e ulaşan pozisyonlar, dengelemede yeniden seçilmiş olanlar.** Seçim karar anındaki bilgiyle yapılıyor, gelecek bilgisi yok. Ama pozisyonlar arası bir seçilim etkisi taşıyor.
- **Karşı-olgu muhasebe yöntemiyle.** Sermaye yeniden dağıtılmadı, bileşik etki ve yol bağımlılığı yaklaşık. Defter bileşenleri ile motorun günlük getirisi arasındaki korelasyon 0,998 (madde 690).
- **Gerçekleşen funding = motorun hesapladığı funding.** Motor gerçek Binance ödeme saatlerini kullanıyor (madde 268); bu hesap ekstresi değil.
- **TP hariç fiyat yaş kovalarında çok oynak.** Bu kalemde tek bir kovadan sonuç çıkarılmamalı.

Üretim stratejisine hiçbir değişiklik önerilmiyor. Long tutma süresi ile ilgili mevcut bulgular (5 gün yerinde) güçlendi.
