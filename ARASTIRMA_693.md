# Araştırma 693 — Piyasa yolu, fitil avantajı ve rejim dayanıklılığı (1 Kasım 2026)

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem DEĞİŞMEDİ. Yeni filtre ya da kapı eklenmedi.
- **Araç:** `arastirma_m693_rejim.py`.
- **Motor kopyası:** `/tmp/g33_m693.py`, `g33.py`'nin değişmemiş kopyası. İki hizada da referansla **bayt bayt aynı**.
- **Koşular:** 6 motor koşusunun hepsi rc 0 ile bitti, tek işçiyle çalıştı. Bellek nedeniyle kesilen koşu yok.
- **Çıktı kontrolü:** beklenen 19 dosyanın hepsi var.
- **TP açık / kapalı serileri:** madde 692'den alındı (parite doğrulanmıştı).
- **Git:** strateji ve motor dosyalarında diff yok.

Etiketler: **ÖLÇÜM** doğrudan veriden · **VARSAYIM** model veya senaryo varsayımına dayanan · **HİPOTEZ** doğrulanmamış açıklama.

**Veri:**
- P3T2, 2.000 $, 1,0x, gerçekçi model; iki hiza ortalaması.
- Getiri serisi Ağustos 2020 – Eylül 2026; 16.619 pozisyon (madde 692 tanımı).
- 4 saatlik ve günlük OHLC.

**Rejim etiketleri NEDENSEL:**
- Gün d'nin etiketi d kapanışına kadarki veriyle hesaplanıyor ve d+1 getirisine uygulanıyor.
- Oynaklık, yol ve fitil eşikleri GENİŞLEYEN (yalnız geçmiş) dağılımdan; ilk 90 gün etiketsiz.
- Yön eşikleri önceden sabitlendi, optimize edilmedi:
  - BTC 30 günlük getiri ±%10;
  - evren medyanı ±%15;
  - kitabın long / short sepeti ±%20.
- "Yol" = verimlilik oranı (ER = |30 günlük net değişim| / Σ|günlük değişim|):
  - genişleyen üst tercil = kalıcı tek yön;
  - alt tercil = sık geri dönüş.
- Fitil payı = 1 − |kapanış − açılış| / (yüksek − düşük); günlük, 30 günlük ortalama.

**Önemli tarama sınırlaması [VARSAYIM]:**
- Bir rejimin CAGR'si ve maks DD'si, o rejimin günleri art arda eklenerek hesaplandı; gerçek bir takvim dönemi değil.
- 9 boyut × 2-3 rejim çoklu karşılaştırma demek; tek tek farklar tesadüf olabilir.

---

## 1. Gerçek tarihsel rejimler [ÖLÇÜM]

**Sütunlar:** TP / F / L / S = TP, funding, long fiyat ve short fiyat katkısı (yıllık puan). "TP değeri" = TP açık CAGR − TP kapalı CAGR.

| Boyut | Rejim | Gün % | CAGR | Sharpe | Maks DD | TP kapalı CAGR | TP değeri | TP | F | L | S | TP olayı / gün | TP oranı | Poz. süre (g) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kitap yolu | **kalıcı tek yön** | 31 | **%456** | 5,0 | −14,5 | %280 | **+176** | 146 | 51 | +44 | −56 | 11,5 | %16,9 | 5,4 |
| Kitap yolu | ara | 33 | %217 | 3,7 | −18,3 | %229 | −12 | 121 | 43 | −9 | −25 | 10,4 | %14,5 | 5,5 |
| Kitap yolu | sık geri dönüş | 31 | %152 | 3,7 | −14,2 | %137 | +15 | 87 | 33 | −53 | +40 | 7,6 | %12,6 | 5,9 |
| BTC yolu | kalıcı tek yön | 28 | %379 | 5,0 | −14,7 | %241 | +137 | 127 | 49 | +45 | −52 | 10,8 | %15,8 | 5,3 |
| BTC yolu | sık geri dönüş | 38 | %232 | 4,1 | −13,4 | %244 | −12 | 113 | 44 | −21 | −1 | 9,3 | %14,0 | 5,7 |
| BTC yolu | ara | 30 | %190 | 3,4 | −14,9 | %149 | +42 | 117 | 36 | −33 | +5 | 9,5 | %14,3 | 5,7 |
| BTC yönü | güçlü yükseliş | 32 | %309 | 4,6 | −12,9 | %281 | +28 | 112 | 24 | +77 | −59 | 9,4 | %16,1 | 5,7 |
| BTC yönü | güçlü düşüş | 20 | %274 | 4,0 | −13,8 | %143 | **+131** | 125 | 57 | −21 | −14 | 11,6 | %14,0 | 5,6 |
| BTC yönü | yatay | 48 | %206 | 3,9 | −14,9 | %189 | +16 | 115 | 47 | −54 | +19 | 9,2 | %14,2 | 5,7 |
| Evren yönü | güçlü yükseliş | 19 | %433 | 5,5 | −15,2 | %331 | +103 | 140 | 18 | +76 | −53 | 12,0 | %18,8 | 5,7 |
| Evren yönü | güçlü düşüş | 32 | %252 | 4,0 | −13,2 | %151 | +101 | 110 | 52 | −2 | −21 | 10,1 | %13,4 | 5,6 |
| Evren yönü | yatay | 50 | %196 | 3,8 | −12,5 | %202 | −6 | 111 | 44 | −40 | +9 | 8,6 | %14,2 | 5,6 |
| BTC oynaklığı | yüksek | 29 | %448 | 5,1 | −12,0 | %347 | +101 | 121 | 30 | +65 | −32 | 11,1 | %15,1 | 5,9 |
| BTC oynaklığı | düşük | 67 | %193 | 3,7 | −18,3 | %164 | +28 | 117 | 48 | −37 | −6 | 9,3 | %14,4 | 5,5 |
| Kitap oynaklığı | yüksek | 53 | %397 | 4,8 | −12,4 | %293 | +103 | 158 | 56 | −16 | −20 | 13,0 | %17,2 | 5,5 |
| Kitap oynaklığı | **düşük** | 43 | **%134** | 3,2 | −18,2 | %132 | +2 | 70 | 27 | +6 | −7 | 5,9 | %11,1 | 5,8 |
| Kitap fitili | yüksek fitil | 29 | %326 | 4,7 | −11,2 | %240 | +86 | 119 | 43 | +12 | −16 | 9,1 | %14,9 | 5,7 |
| Kitap fitili | ara | 32 | %218 | 3,8 | −10,8 | %137 | +82 | 117 | 49 | −16 | −21 | 9,3 | %14,7 | 5,6 |
| Kitap fitili | düşük fitil | 35 | %234 | 4,0 | −13,8 | %266 | **−33** | 118 | 36 | −12 | −5 | 10,8 | %14,3 | 5,5 |
| Long sepeti | güçlü yükseliş | 69 | %328 | 4,5 | −15,0 | %262 | +67 | 132 | 48 | +1 | −20 | 10,2 | %15,9 | 5,6 |
| Long sepeti | güçlü düşüş | 4 | %179 | 4,0 | −6,5 | %103 | +76 | 95 | 27 | +17 | −28 | 11,3 | %12,4 | 5,3 |
| Long sepeti | **yatay** | 27 | **%115** | 3,1 | −14,3 | %110 | +5 | 80 | 28 | −29 | +11 | 8,1 | %12,2 | 6,0 |
| Short sepeti | güçlü yükseliş | 23 | %365 | 5,0 | −11,6 | %212 | **+153** | 156 | 26 | +39 | −52 | 13,8 | %20,4 | 5,6 |
| Short sepeti | güçlü düşüş | 23 | %239 | 3,8 | −11,8 | %174 | +65 | 110 | 49 | −11 | −14 | 10,6 | %13,6 | 5,6 |
| Short sepeti | yatay | 54 | %212 | 3,9 | −13,3 | %215 | −3 | 101 | 46 | −24 | +6 | 7,6 | %12,9 | 5,7 |

Tablonun tamamı: `/tmp/m693/rejim_tablo.csv`.

- **En iyi rejimler:** kitabın tuttuğu coinlerde **kalıcı tek yönlü hareket** (%456), evrende güçlü yükseliş (%433), yüksek BTC ve kitap
  oynaklığı (%397-448).
- **En zayıf rejimler:** long sepeti yatay (%115), düşük kitap oynaklığı (%134), kitap yolunda sık geri dönüş (%152).
- **Hiçbir rejimde CAGR negatif değil.** En kötü maks DD −18,3 (düşük BTC ve kitap oynaklığı).
- **BTC ile kitap rejimi farklı şeyler ölçüyor.** BTC'nin kendi yönü ve yolu, kitabın kendi coinlerinin özelliklerinden daha zayıf
  ayırt ediyor (BTC yolu %379'a karşı %232; kitap yolu %456'ya karşı %152).

## 2. Fiyat yolu analizi [ÖLÇÜM]

**Bar içi MFE / MAE** (girişe göre; long / short):

| | MFE medyan | MFE %90 | MAE medyan | MAE %10 | Çıkış getirisi medyan |
|---|---|---|---|---|---|
| Long | %11,0 | %57,9 | −%13,1 | −%32,4 | −%4,0 |
| Short | %6,7 | %21,5 | −%5,5 | −%21,4 | +%1,0 |

- **Aşırı seviyeden geri dönüş:** MFE ≥ %20 olan 3.382 pozisyonun %48'i kapanışta kazancın yarısından fazlasını geri verdi. TP'lilerde
  bu oran %32, **TP'sizlerde %65.**
- **Seviyeye değip geri dönme:** TP / kademe seviyesine ulaşan 4 saatlik barların **%71'i seviyenin gerisinde kapandı.** 24 saat sonra
  kapanış hâlâ seviyenin gerisinde: **%67** (long ve short aynı).
  - TP çoğunlukla geri dönen fitili satıyor. Bu madde 692'nin fitil bulgusunu gerçek veriyle destekliyor.

**Giriş ÖNCESİ (nedensel) 30 günlük coin özelliği → TP başarısı** (tercil; `/tmp/m693/yol_tercil.csv`):

| Özellik | Yön | TP oranı (düşük / orta / yüksek tercil) | Pozisyon başı net, bp (düşük / orta / yüksek) |
|---|---|---|---|
| Gün içi aralık | long | %8,9 / %9,9 / %15,8 | 12,7 / 9,8 / 20,0 |
| Gün içi aralık | short | **%6,4 / %14,6 / %31,3** | 0,8 / 6,1 / 15,4 |
| Oynaklık | short | %6,6 / %14,6 / %31,1 | 0,8 / 6,0 / 15,7 |
| Verimlilik (ER) | long | %9,9 / %10,1 / %14,6 | 11,6 / 12,8 / 18,3 |
| Verimlilik (ER) | short | %13,6 / %17,2 / %21,6 | 5,4 / 8,4 / 8,6 |
| Fitil payı | long | %11,7 / %9,3 / %13,5 | 16,4 / 8,6 / 17,5 |
| Fitil payı | short | %18,1 / %17,3 / %16,9 | 7,7 / 9,7 / 5,0 |

- TP başarısını aralık ve oynaklık güçlü biçimde öngörüyor.
- Yüksek ER (girişten önce kalıcı hareket eden coin) TP oranını DÜŞÜRMÜYOR, artırıyor.
- Coinin geçmiş fitil payı TP başarısını öngörmüyor (sıra tutarsız).

## 3. Trend ve geri dönüş ayrımı [ÖLÇÜM]

**Kategoriler** birbirini dışlıyor; eşikler önceden belirlendi: ±%5, ilk TP / kademe olayından 5 gün sonraki kapanış.

| Kategori | Pozisyon | Pay | Net puan | Fiyat | Funding | Süre (g) | MFE medyan |
|---|---|---|---|---|---|---|---|
| TP'ye ulaşamayan | 14.157 | %85,2 | **−486,1** | −628,0 | +141,9 | 5,6 | %6,6 |
| TP öncesi geri dönüş yaşayan (önce ≥ %5 ters) | 1.229 | %7,4 | **+795,5** | +708,2 | +87,3 | 7,9 | %30,9 |
| TP sonrası trend devam (5 g sonra ≥ %5 lehte) | 405 | %2,4 | +236,2 | +229,4 | +6,8 | 4,1 | %30,4 |
| TP sonrası ters yön (5 g sonra ≥ %5 aleyhte) | 513 | %3,1 | +176,6 | +161,3 | +15,3 | 5,6 | %25,3 |
| TP'li, sonrası nötr | 315 | %1,9 | +149,3 | +146,1 | +3,1 | 4,6 | %24,7 |

- **TP'li pozisyonlar, önce × sonra** (net puan): önce ters yok → sonra devam 20,6 · nötr 29,8 · ters 54,3. Önce ≥ %5 ters → sonra devam
  30,5 · nötr 15,5 · ters 49,2.
- **İlk TP olayından 5 gün sonra kapanış**, satış fiyatına göre medyan **−%2,5** (long −%8,1, short −%1,1). 5 gün içinde lehte en iyi
  hareket medyan +%13,3.
  - Satıştan sonra fiyat çoğunlukla geri geliyor. Ama 5 gün içinde lehte yeni bir zirve yapma olasılığı da yüksek.
- **TP açık ile kapalı, aynı aylar** (74 ay):
  - Aylık fark ortalama +0,67, medyan +1,38 puan. TP aylarının **%73'ünde** kazandırıyor.
  - En kötü ay **2025-04: −59,4 puan.** TP kapalıyken o ay +%70, açıkken +%11.
  - O ayın en büyük TP coini ALPACA (TP 8,3 puan). [HİPOTEZ] Kaybın kaynağı tek coinin olağanüstü sıçraması.
  - 2025-04 hariç aylık ortalama fark **+1,5 puan.**
  - TP kapalı senaryonun 2025 üstünlüğü (madde 692) büyük ölçüde bu tek aydan geliyor.

## 4. Fitil testinin bağımsız doğrulaması

### 4a. Madde 692 sentetik fitil testinin sınırlamaları [VARSAYIM]
1. Yalnız TP / kademe kontrolündeki yüksek / düşük değer kırpıldı. Fiyat yolu, kapanışlar, stoplar, seçim ve tutuş P&L'i gerçek kaldı.
   Gerçekte fitili kısa bir piyasada kapanışlar, oynaklık ve seçim de değişirdi.
2. Kırpma bütün coinlere ve barlara eşit oranda uygulandı; gerçekte fitil coin ve rejime göre değişir.
3. Fitilsiz (F0) senaryoda TP yalnız gövdenin seviyeyi geçtiği barlarda doluyor; bunlar seçilmiş biçimde süren hareketler. "TP'siz
   durumdan kötü" sonucu kısmen bu seçimden geliyor: F0 rastgele değil, en kötü satış anlarını bırakıyor.
4. Dolum fiyatı seviye (ya da açılış) olarak kaldı. Kırpılmış dünyada daha iyi ya da kötü fiyattan dolum modellenmedi.

Bu yüzden F50 / F0 sonuçları **"TP'nin değeri fitile bağlı"** iddiasının yönünü gösterir, büyüklüğünü değil.

### 4b. Gerçek tarihsel gözlem (sentetik değişiklik yok) [ÖLÇÜM]
**Aylık gruplar** (kitabın tuttuğu coinlerin özelliklerine göre; ay ortalaması %; "fark" = TP açık − kapalı):

| Özellik | Sınıflandırma | Grup | Ay | TP açık | TP kapalı | Fark | Zarar ayı | TP kazandırdı |
|---|---|---|---|---|---|---|---|---|
| Fitil payı | eşzamanlı (betimleyici) | yüksek | 37 | 11,6 | 8,8 | **+2,8** | %11 | %81 |
| Fitil payı | eşzamanlı | düşük | 37 | 10,1 | 11,5 | **−1,4** | %14 | %65 |
| Fitil payı | önceki ay (nedensel) | yüksek | 31 | 11,6 | 9,9 | +1,8 | %6 | %77 |
| Fitil payı | önceki ay (nedensel) | düşük | 36 | 8,3 | 8,8 | −0,5 | %19 | %67 |
| Trend sürekliliği (ER) | eşzamanlı | yüksek | 37 | **13,7** | 11,6 | +2,1 | %8 | %73 |
| Trend sürekliliği (ER) | eşzamanlı | düşük | 37 | **7,9** | 8,7 | −0,8 | %16 | %73 |
| Trend sürekliliği (ER) | önceki ay (nedensel) | yüksek | 33 | 11,7 | 10,5 | +1,3 | %6 | %73 |
| Trend sürekliliği (ER) | önceki ay (nedensel) | düşük | 34 | 8,0 | 8,2 | −0,2 | %21 | %71 |
| Gün içi aralık | eşzamanlı | yüksek | 37 | 13,9 | 13,9 | 0,0 | %8 | %70 |
| Gün içi aralık | eşzamanlı | düşük | 37 | 7,7 | 6,4 | +1,4 | %16 | %76 |

**Fitil × trend sürekliliği** (eşzamanlı, ay ortalaması %):

| | Kalıcı (yüksek ER) | Geri dönüşlü (düşük ER) |
|---|---|---|
| Yüksek fitil | TP açık **15,8** / kapalı 12,8 / fark +3,0 (25 ay) | **2,7** / 0,4 / +2,3 (12 ay) |
| Düşük fitil | 9,3 / 9,1 / +0,2 (12 ay) | 10,5 / 12,7 / **−2,3** (25 ay) |

**Açıklayıcılık** (aylık, eşzamanlı, n = 74):
- TP açık getirisi: fitil R² 0,05 · ER 0,17 · fitil + ER + oynaklık 0,22 · + long sepeti getirisi 0,36.
- TP açık − kapalı fark: bütün kombinasyonlarda R² ≤ **0,05.**

## 5. Yeni coin bağımlılığı (2024-2026)

**Yöntem:**
- Yaş = coinin vadeli işlem verisinin başladığı günden o güne kadar geçen süre. O gün bilinen bir değer, geleceğe bakmıyor.
- Coinler başarılarına göre değil, o günkü yaşlarına göre sınıflandı.
- Evren, listeden çıkan coinleri de içeriyor (verisi 2026-09'dan önce biten 31 coin; toplam net katkıları +11,3 puan).
- 2021 öncesinde yaş kesik: veri 2020-01'de başlıyor, o tarihten önce listelenmiş coinler de "genç" görünüyor. Bu yüzden analiz 2024-26.

**[ÖLÇÜM] Yaş grubuna göre 2024-26** (puan; pozisyonlar o tarihte başlayanlar):

| Yaş | Net | TP | Funding | Fiyat | Net payı | Maruziyet payı | Maruziyet başı yıllık | Zararlı coin | Pozisyon | Poz. başı net (bp) | Zararlı poz. | TP oranı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| < 90 gün | 63,6 | 59,9 | 22,8 | −17,2 | %17,5 | %7,0 | %452 | %43 | 591 | **37,2** | %44 | %31,3 |
| 90-180 gün | 118,0 | 87,5 | 35,6 | −0,6 | %32,5 | %13,4 | %438 | %45 | 1.016 | 14,5 | %48 | %22,6 |
| 180-365 gün | 102,5 | 110,7 | 50,3 | −53,6 | %28,2 | %16,7 | %306 | %57 | 1.633 | 14,3 | %50 | %20,6 |
| 1-2 yıl | 64,8 | 83,4 | 29,4 | −41,4 | %17,9 | %19,8 | %163 | %63 | 1.823 | 6,9 | %54 | %15,3 |
| 2-4 yıl | 0,2 | 43,2 | 17,5 | −55,7 | **%0,1** | %18,7 | **%1** | %63 | 1.924 | 1,0 | %54 | %10,7 |
| > 4 yıl | 14,0 | 17,4 | 13,4 | −11,0 | %3,9 | %24,3 | %29 | %43 | 1.729 | 2,4 | %51 | %6,0 |

- **Yaş özeti:** 1 yaşından genç coinler 2024-26 net kârının **%78'ini** veriyor, maruziyetin ise %37'sini. 2 yaşından büyük coinler net
  kârın **%4'ünü**, maruziyetin %43'ünü.
- **Genç coinlerin payı zamanla arttı** (çeyreklik tablo `/tmp/m693/genc_ceyrek.csv`):
  - Maruziyet başı yıllık getiri: genç / yaşlı 2022 %127 / %57 → 2025 **%416 / %29** → 2026 %745 / %90.
  - Genç coin TP payı 2022-23'te %8-52, 2025'te %56-77.
- **Pozisyon başı:** yaş arttıkça TP oranı (%31 → %6) ve pozisyon başı net (37 → 1-2 bp) düzenli olarak düşüyor. Zararlı pozisyon oranı
  yaşla artıyor (%44 → %51-54).

**[ÖLÇÜM; senaryo VARSAYIM] Motor karşı-olgusu.** Evrene asgari listeleme yaşı kondu; boşalan yer daha yaşlı coinlere gidiyor.

| Senaryo | CAGR | Sharpe | Maks DD | 2024-26 CAGR | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| Baz (asgari yaş 60 g) | %247,5 | 4,14 | −13,3 | %247,6 | 472 | 63 | 310 | 118 | 267 | 283 |
| Asgari yaş 180 g | %138,2 | 3,21 | −13,4 | %124,4 | 284 | 56 | 209 | 89 | 90 | 157 |
| Asgari yaş 365 g | **%73,4** | 2,31 | −21,2 | **%50,5** | 146 | 50 | 168 | 94 | **18,5** | 33,6 |

- Asgari yaş 365 günde 2020 getirisi 0: veri 2020'de başladığı için o yıl hiçbir coin yeterince yaşlı değil.
- 2022 ve 2024'te fark küçük; 2025-26'da çok büyük.

## 6. Cevaplar

**1. Bot hangi gerçek piyasa rejiminde en iyi çalışıyor?**
- [ÖLÇÜM] Tutulan coinlerin kalıcı tek yönde hareket ettiği (CAGR %456, Sharpe 5,0), evrenin güçlü yükseldiği (%433) ve oynaklığın yüksek
  olduğu (%397-448) rejimlerde.
- En zayıf: long sepeti yatay (%115), düşük kitap oynaklığı (%134), tutulan coinlerde sık geri dönüş (%152). Hiçbir rejimde zarar yok.

**2. Kalıcı trend piyasaları gerçekten stratejinin zayıf noktası mı?**
- [ÖLÇÜM] **Hayır.** Hipotez bu biçimiyle yanlışlandı. Kalıcı tek yönlü rejimler en iyisi; sık geri dönüşlü rejimler en zayıfı (kitap:
  %456'ya karşı %152, BTC: %379'a karşı %232).
- Girişten önce kalıcı hareket eden coinlerin TP oranı daha yüksek. TP'nin değeri de en çok kalıcı rejimde (+176 CAGR puanı).
- **Gerçek zayıf nokta [ÖLÇÜM + HİPOTEZ]:** tek bir coinin olağanüstü, kesintisiz sıçraması. 2025-04'te ALPACA ayında TP, tutmaya göre
  59 puan kaybettirdi. Bu rejim düzeyinde değil, coin düzeyinde bir kuyruk olayı.

**3. Fitil ve geri dönüş davranışı getirinin ne kadarını açıklıyor?**
- [ÖLÇÜM] Az. Aylık getiride fitil R² 0,05; trend sürekliliği 0,17 ve yönü "süreklilik iyi"; ikisi ve oynaklık birlikte 0,22.
- TP'nin katma değerindeki aylık değişimi bu ölçüler ancak %4-5 açıklıyor.
- Pozisyon düzeyinde fitil gerçek bir mekanizma: TP barlarının %71'i seviyenin gerisinde kapanıyor. Ama getirinin aydan aya değişimini
  fitil değil, oynaklık ve long sepetinin yönü belirliyor.

**4. TP'nin katkısı hangi rejimde en çok artıyor?**
- [ÖLÇÜM] TP'nin değeri (açık − kapalı CAGR) şu rejimlerde en yüksek:
  - tutulan coinlerde kalıcı tek yön (+176);
  - short sepetinin güçlü yükseldiği dönem (+153);
  - BTC'nin kalıcı hareket ettiği (+137) ya da güçlü düştüğü (+131) dönem;
  - yüksek fitil (+86).
- Negatif olduğu rejimler: düşük fitil (−33), BTC sık geri dönüş (−12), kitap yolu ara (−12).
- Gerçek aylarda TP yüksek fitilli aylarda +2,8, düşük fitilli aylarda −1,4 puan fark yaratıyor (nedensel sınıflandırmada +1,8'e karşı
  −0,5).

**5. Yeni coinler olmadan stratejinin avantajı devam ediyor mu?**
- [ÖLÇÜM] **Büyük ölçüde hayır,** özellikle son iki yılda.
  - 2024-26'da 2 yaşından büyük coinler net kârın %4'ünü veriyor.
  - Motorda 1 yaşından genç coinler evrenden çıkarılınca CAGR %247 → %73, 2024-26'da %248 → %51, 2025'te %18,5. Maks DD −13'ten
    −21'e çıkıyor.
- Avantaj sıfıra inmiyor ama çok küçülüyor.
- [HİPOTEZ] Stratejinin kenarı ağırlıkla "yeni listelenen vadeli coinlerin ilk yılındaki fiyat ve funding davranışı." Binance'in listeleme
  akışı ya da yeni coinlerin davranışı değişirse bu, backtestte sınanmamış bir risktir.

**6. En kötü rejimler gerçek zamanlı tespit edilebilir mi?**
- [ÖLÇÜM] Zayıf biçimde.
  - Nedensel etiketler zaten gerçek zamanlı ve kalıcı (ertesi gün aynı rejim %70-93).
  - En kötü etiketler (kitap yolu sık geri dönüş, düşük kitap oynaklığı, short sepeti yatay) aktifken sonraki 30 günde zarar olasılığı
    %16-17; diğer günlerde %10-12, taban %13,5.
  - Aynı günlerde sonraki 30 günün ortalama getirisi yine +%8-10.
- En kötü 10 ayın başındaki etiketler tutarlı değil: 2022-05 düşük fitil ve kalıcı yol, 2023-02 yüksek fitil, 2024-08 sık geri dönüş.
- **Rejim, getirinin seviyesini öngörüyor ama zararı güvenilir biçimde öngörmüyor.** Kapı önerilmez.

---
### Yeniden üretim
```bash
python3 arastirma_m693_rejim.py kos      # parite (2) + asgari yaş 180 / 365 g (4 koşu), tek işçi (~15 dk)
python3 arastirma_m693_rejim.py analiz   # -> /tmp/m693/*.csv + ekran raporu (~10 dk)
```
Önkoşul: madde 690, 691 (`kos_seviye`), 692 (`kos`, `analiz`) çıktıları.
