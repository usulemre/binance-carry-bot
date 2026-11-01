# Araştırma 694 — Yeni listelenen coin avantajı ve evren sürdürülebilirliği (1 Kasım 2026)

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem DEĞİŞMEDİ. Filtre ya da kapı eklenmedi.
- **Araç:** `arastirma_m694_yeni_coin.py`.
- **Motor kopyası:** `/tmp/g33_m694.py`, `g33.py`'nin değişmemiş kopyası.
- **Parite:** iki hizada da referansla **bayt bayt aynı**. Ayrıca genç coinsiz koşu (Y365K), madde 693'ün aynı senaryosuyla bayt bayt aynı.
- **Koşular:** 20 motor koşusunun hepsi rc 0 ile bitti, tek işçiyle çalıştı.
- **Bellek kesintisi:** ilk denemede motor koşusu, eşzamanlı çalıştırdığım analiz yüzünden bellek yetersizliğinden sessizce öldü. O
  deneme başarılı SAYILMADI; bütün koşular analiz olmadan baştan yapıldı.
- **Çıktı kontrolü:** beklenen 42 dosyanın hepsi var.
- **Git:** strateji ve motor dosyalarında diff yok.

Etiketler: **ÖLÇÜM** doğrudan veriden · **VARSAYIM** model veya senaryo varsayımına dayanan · **HİPOTEZ** doğrulanmamış açıklama.

**Tanımlar ve yanlılık kontrolleri:**
- **Yaş:** coinin vadeli işlem verisinin başladığı günden o güne kadar geçen süre. O gün bilinen bir değer.
- **Yaş kesikliği:** veri 2020-01'de başlıyor, o tarihten önce listelenen coinlerin yaşı kesik. Bu yüzden analiz 2021-01 sonrası;
  kohortlar da yalnız 2021+ listelemeler.
- **Asgari yaş:** önerilen ayarda evrene girmek için asgari yaş 60 gün (YAS_GUN=60). Bot **ilk 60 günde hiç işlem yapmıyor**; "0-30 g"
  grubu bu yüzden boş, "31-90 g" grubu fiilen 60-90 gün.
- **Sağkalım:** evrende verisi dönem bitmeden kesilen (delist olan) coinler var. 2021+ listelenen 621 coinin 22'si; katkıları dahil.
  Binance'in bütün delist geçmişinin veri setinde eksiksiz olup olmadığı ayrıca doğrulanamadı [VARSAYIM].
- **Gelecek bilgisi:** coinler sonraki başarılarına göre değil, o günkü yaşlarına göre gruplandı. Karşı-olgu çıkarmaları rastgele ya da
  takvime göre yapıldı, coinin sonucuna göre değil.
- TradFi (hisse) sözleşmeleri ve D8 listesi analiz dışında.
- **Birimler:** puan = kitap getiri puanı (iki hiza ortalaması, bileşik değil); bp = baz puan.

---

## 1. Yeni coin avantajının kaynağı [ÖLÇÜM]

**2024-2026, yaş grubuna göre** (pozisyonlar o dönemde başlayanlar; vol = 30 günlük oynaklık; funding = yıllık %):

| Yaş | Net | TP | Funding | Long fiyat | Short fiyat | Net payı | Maruziyet payı | Maruziyet başı yıllık | Pozisyon | Poz. başı | TP oranı | Süre | MAE medyan | Vol medyan | Funding medyan [%10, %90] | Hacim medyan |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 31-90 g (fiilen 60-90) | 63,6 | 59,9 | 22,8 | −1,3 | −15,9 | %17,5 | %7,0 | **%452** | 591 | **37,2 bp** | **%31,3** | 5,6 g | −%12,9 | %174 | 6,6 [−204, +52] | 100 M$ |
| 91-180 g | 118,0 | 87,5 | 35,6 | −12,1 | +11,6 | %32,5 | %13,4 | %438 | 1.016 | 14,5 bp | %22,6 | 5,3 g | −%12,3 | %157 | 0,1 [−307, +43] | 91 M$ |
| 181-365 g | 102,5 | 110,7 | 50,3 | −41,5 | −12,1 | %28,2 | %16,7 | %306 | 1.633 | 14,3 bp | %20,6 | 5,3 g | −%10,4 | %146 | 2,9 [−160, +30] | 92 M$ |
| 1-2 yıl | 64,8 | 83,4 | 29,4 | −38,6 | −2,8 | %17,9 | %19,8 | %163 | 1.823 | 6,9 bp | %15,3 | 5,1 g | −%9,7 | %129 | 2,0 [−121, +20] | 98 M$ |
| > 2 yıl | 14,2 | 60,6 | 30,9 | **−65,5** | −1,2 | %3,9 | %43,1 | **%16** | 3.653 | 1,6 bp | %8,5 | 5,3 g | −%6,7 | %103 | 3,4 [−61, +16] | 131 M$ |

2021-2026 tablosu da aynı sırayı gösteriyor: maruziyet başı %419 → %62, TP oranı %29 → %8 (`/tmp/m694/yas_grup_2021-2026.csv`).

- **Bileşen farkı:**
  - Genç coinlerde TP katkısı neredeyse net katkıya eşit; tutuş (long ve short fiyat) küçük.
  - Yaşlı coinlerde TP kazancını long fiyat kaybı yiyor. 2 yaşından büyük coinler: TP +60,6, long fiyat −65,5, net +14,2.
- **Yaş mı, özellik mi? Tabakalama** (2021+; `/tmp/m694/tabakalama.csv`):
  - Aynı oynaklık, lehte funding ve hacim tercili içinde genç coin pozisyonu her tercilde yaşlıdan daha iyi: **18 tabakanın 18'inde**,
    fark +1,4 ile +21 bp.
  - Fark en çok yüksek oynaklıkta (long +18,4 bp) ve yüksek hacimde (+17-21 bp).
- **Regresyon** (pozisyon başı net bp; OLS; t değerleri bağımsızlık varsaydığı için iyimser):
  - Long: genç katsayısı 11,6 bp; oynaklık, funding ve log hacim eklenince **10,8 bp**, yani neredeyse değişmiyor.
  - Short: 10,5 → **6,8 bp**. Farkın bir kısmını oynaklık açıklıyor (t 9,5).
  - Bütün modellerde R² %0,2-2,4: pozisyon sonucu bu değişkenlerle çok az açıklanıyor.
- **Sonuç:**
  - [ÖLÇÜM] Yeni coin avantajı ölçülen oynaklık, funding ve hacim farklarıyla açıklanamıyor; yaşla ilişkili ölçülmemiş bir özellik
    var.
  - [HİPOTEZ] Aday açıklamalar: listeleme sonrası fiyat keşfi, yeni coinlerde dağınık konumlanma ve sıkışmalar, düşen arz kilidi
    dinamikleri. Hiçbiri test edilmedi; nedensellik iddiası yok.

## 2. Listeleme kohortları [ÖLÇÜM]

**Dönem karşılaştırması** (yalnız penceresi tam gözlenen coinler):

| Pencere | Dönem | Coin | Botun işlem yaptığı | Coin başı net (puan) | Toplam net | TP toplamı | Funding toplamı | Zararlı (işlem görenler) | Fiyat getirisi medyan | Vol medyan | Funding medyan | Delist |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30 g | 2021-23 | 183 | %0 | 0 | 0 | 0 | 0 | — | −%15 | %160 | 10,4 | %10,9 |
| 30 g | 2024-26 | 438 | %0 | 0 | 0 | 0 | 0 | — | −%21 | %183 | 4,2 | %0,5 |
| 90 g | 2021-23 | 183 | %51 | 0,11 | 19,2 | 21,3 | 3,0 | %46 | −%31 | %143 | 9,4 | |
| 90 g | 2024-26 | 423 | **%35** | 0,16 | 65,9 | 52,1 | 21,6 | %43 | −%44 | %167 | 6,0 | |
| 180 g | 2021-23 | 183 | %77 | 0,39 | 72,1 | 52,6 | 9,1 | %43 | −%28 | %130 | 9,2 | |
| 180 g | 2024-26 | 399 | %62 | 0,44 | 173,8 | 110,0 | 53,3 | %43 | −%61 | %153 | 3,8 | |
| 365 g | 2021-23 | 183 | %87 | 0,62 | 114,2 | 87,9 | 17,5 | %48 | −%40 | %123 | 10,5 | |
| 365 g | 2024-26 | 317 | %82 | 0,57 | 179,3 | 152,4 | 68,2 | %44 | **−%79** | %140 | **2,7** | |

- **İlk yıl katkısının zamanlaması:** ilk 30 günde %0 (asgari yaş kuralı), ilk 90 günde %20, ilk 180 günde %63. Her iki dönemde de aynı
  (%17 / %63 ve %22 / %63).
- **Davranış değişti mi?**
  - **Coin başı katkı değişmedi:** ilk yıl 0,62'ye karşı 0,57 puan. Zararlı coin oranı %44-48.
  - **Değişenler:**
    - listeleme sayısı (TradFi hariç yılda ~60 → ~160);
    - yeni coinlerin ilk yıldaki fiyat düşüşü (medyan −%40 → −%79);
    - yeni coinlerin funding'i (yıllık %10,5 → %2,7);
    - ilk yıl oynaklığı (%123 → %140);
    - botun işlem yaptığı yeni coin oranı (ilk 90 günde %51 → %35).
  - Toplam katkının artması (114 → 179 puan), coin başına değil, **coin sayısına** dayanıyor.
- **Çeyreklik kohortlar:** büyük dağılım. 2025Q1 kohortunun ilk yılı 74,5 puan, 2025Q2'ninki 8,1 (`/tmp/m694/kohort_ceyrek.csv`). Aylık
  kohortlar `kohort_ay.csv`'de. Tek tek kohortlar gürültülü.

## 3. Listeleme akışı değişirse

### 3A. Tarihsel karşı-olgu (motor; coinler evrenden çıkarıldı) [ÖLÇÜM; senaryo VARSAYIM]
**Yöntem:**
- Çıkarma havuzu: 2021+ listelenen 621 coin.
- Her oran için iki rastgele çekiliş (_a, _b) yapıldı. Çıkarılan coin hiç listelenmemiş sayılıyor; boşalan yer diğer coinlere gidiyor.
- 6 aylık duruş: o yarıyılda listelenen bütün coinler çıkarıldı.
- 2020 ve büyük ölçüde 2021 değişmiyor, çünkü o yılların coinleri havuzda değil.

| Senaryo | Çıkan coin | CAGR | Sharpe | Maks DD | 2024-26 CAGR | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| Baz (mevcut akış) | 0 | %247,5 | 4,14 | −13,3 | %247,6 | 63 | 310 | 118 | 267 | 283 |
| Listeleme −%25 (a) | 155 | %208,8 | 3,9 | −14,9 | %186,1 | 69 | 246 | 118 | 226 | 153 |
| Listeleme −%25 (b) | 155 | %182,7 | 3,6 | −14,6 | %141,2 | 66 | 235 | 55 | 139 | 203 |
| Listeleme −%50 (a) | 310 | %159,8 | 3,5 | −16,8 | %104,1 | 67 | 184 | 167 | 115 | 24 |
| Listeleme −%50 (b) | 310 | %167,6 | 3,7 | −19,5 | %107,3 | 47 | 278 | 103 | 52 | 140 |
| Listeleme −%75 (a) | 466 | %136,4 | 3,3 | −16,9 | %69,1 | 68 | 175 | 61 | 19 | 122 |
| Listeleme −%75 (b) | 466 | %113,3 | 2,9 | −22,3 | %65,4 | 28 | 143 | 65 | 27 | 91 |
| 6 ay duruş: 2024 ilk yarı | 40 | %245,1 | 4,1 | −13,3 | %242,4 | 63 | 310 | 103 | 278 | 284 |
| 6 ay duruş: 2025 ilk yarı | 115 | %198,1 | 3,8 | −15,9 | %146,1 | 63 | 310 | 118 | **80** | 203 |
| 1 yaşından genç coin yok (asgari yaş 365 g) | — | %73,4 | 2,3 | −21,2 | %50,5 | 50 | 168 | 94 | 19 | 34 |

- **Duruştan sonraki 18 ay:** 2025 ilk yarı duruşunda CAGR %425 → **%168**; 2024 ilk yarı duruşunda %138 → %119. Akışın en yoğun
  olduğu dönemdeki duruş çok pahalı.
- **İki çekiliş arasındaki fark büyük:** −%25'te 2024-26 CAGR %186'ya karşı %141. Sonuç, kaybolan listelemelerin hangileri olduğuna çok
  bağlı (kâr sağ kuyruklu).

### 3B. Senaryo analizi (doğrusal model; tarihsel sonuç DEĞİL) [VARSAYIM]
**Model:** yıllık puan = yaşlı coin katkısı + genç coin katkısı × akış çarpanı × kalite çarpanı. Kalibrasyon 2024-26 statik ayrıştırması:
genç 103,5, yaşlı 28,7 puan / yıl. Boşalan sermaye yeniden dağıtılmıyor; bileşik değil.

| Senaryo | Yıllık puan | Değişim |
|---|---|---|
| Mevcut akış | 132,2 | — |
| Listeleme −%25 | 106,4 | −%20 |
| Listeleme −%50 | 80,5 | −%39 |
| Listeleme −%75 | 54,6 | −%59 |
| 6 ay duruş (yıllık ~%50 genç katkı kaybı varsayımı) | 80,5 | −%39 |
| Akış aynı, ilk yıl oynaklığı düşük tercile iner | 57,0 | −%57 |

- **Oynaklık senaryosunun kalibrasyonu:** genç coin pozisyonlarında giriş oynaklığı tercilleri (2024+) poz başı 5,0 / 11,7 / 38,8 bp.
  Bütün genç pozisyonlar düşük tercilin kalitesine inerse genç katkı ×0,27.
- Motor karşı-olgusu (3A) bileşik etkiyle bu doğrusal modelden **daha sert.** Örneğin −%50'de 2024-26 CAGR %248 → %104-107 (−%57).

## 4. Eski coinler yerini doldurabilir mi? [ÖLÇÜM]

Motor: genç coinsiz senaryo (Y365K) ile baz, 2021+.

| | Brüt maruziyet | Günlük coin | Fiyat | Funding | Fiyat + funding (komisyon hariç) | Maruziyet başı yıllık |
|---|---|---|---|---|---|---|
| Baz 2021+ | 0,720 | 13,7 | 530,7 | 245,5 | 776,2 | %187 |
| Genç coin yok 2021+ | **0,723** | 12,1 | 244,2 | 154,2 | 398,4 | **%97** |
| Baz 2024+ | 0,729 | 15,2 | 213,3 | 166,8 | 380,0 | %189 |
| Genç coin yok 2024+ | 0,725 | 13,5 | 53,8 | 87,3 | 141,1 | **%71** |

- **Dilim bacakları:** baz 285.076 bacak, TP ile kapanan %3,31, bacak başı net 8,4 bp. Genç coinsizde 279.194 bacak, TP %2,23, bacak başı
  4,4 bp.
- **Motor daha AZ işlem yapmıyor:** aynı brüt maruziyeti (0,72) ve neredeyse aynı bacak sayısını koruyor. **Aynı miktarda işlemi daha
  düşük kaliteli fırsatlarda** yapıyor: maruziyet başı getiri yarıya, 2024+ dönemde üçte bire iniyor.
- **Eski coinlerin özellikleri** (evren, coin-gün medyanı, yıllık %):

  | Yıl | Oynaklık genç / > 2 yıl | Funding genç / > 2 yıl |
  |---|---|---|
  | 2021 | 153 / 68 | 25,6 / 10,7 |
  | 2022 | 111 / 86 | 0,0 / 2,3 |
  | 2023 | 88 / 67 | 7,8 / 8,2 |
  | 2024 | 112 / 86 | 11,0 / 10,6 |
  | 2025 | 128 / 87 | 6,5 / 4,5 |
  | 2026 | 93 / 64 | 6,5 / 0,0 |

  Eski coinler sürekli daha az oynak; funding farkı küçük ve değişken.
- **Bazda eski coin pozisyonları** (> 2 yıl, 2021+): TP oranı %7,5, poz başı 4,2 bp. Genç coinlerde %21,4 ve 17,1 bp.

## 5. Yeni coinlerde riskler [ÖLÇÜM]

**4 saatlik coin-barları, 2021+, 10.000 coin-barda olay sayısı:**

| Yaş | 24 sa ≤ −%30 çöküş | 24 sa ≥ +%50 sıçrama | Açılış boşluğu > %5 | Funding ödemesi ≥ %0,5 | ≥ %1 |
|---|---|---|---|---|---|
| 0-30 g | **51,2** | **52,1** | 0,14 | **86,2** | 30,7 |
| 31-90 g | 21,8 | 21,6 | 0 | 39,4 | 15,1 |
| 91-180 g | 17,8 | 18,4 | 0 | 31,3 | 10,7 |
| 181-365 g | 21,5 | 17,3 | 0 | 24,3 | 9,3 |
| 1-2 yıl | 11,5 | 8,5 | 0 | 16,8 | 5,6 |
| > 2 yıl | 3,5 | 5,1 | 0 | 15,0 | 5,6 |

- **Çöküş ve sıçrama:** 1 yaşından genç coinlerde ani çöküş ve ani yükseliş (short sıkışması dahil) sıklığı, 2 yaşından büyüklere göre
  **4-15 kat.** Funding aşırılığı 2-6 kat. Bot ilk 60 günde işlem yapmadığı için en riskli dilim (0-30 g) dışarıda kalıyor.
- **Fiyat boşluğu:** pratikte yok (sürekli piyasa); yalnız listelemenin ilk günlerinde.
- **Delist:** 2021+ listelenen 621 coinden 22'sinin verisi dönem bitmeden kesildi (%3,5); ömür medyanı 466 gün. 9'u ilk yılında kesildi.
  Bu coinlerin toplam net katkısı −4,4 puan.
- **Likidite ve gerçekleşebilir emir büyüklüğü:**
  - Bot pozisyondayken coinin hacmi medyan: genç 99-110 M$, yaşlı 121-130 M$ (%5 dilimi 16-23 M$).
  - 100.000 $'lık kitapta tek pozisyon coin hacminin %95 dilimde ~1 bp'si. 2.000 $'da önemsiz.
  - **Spread ve emir defteri derinliği: VERİ YOK, ölçülemedi.**
- **TP'de kazandırıp taşımada kaybettiren coinler** (2021+ toplam; `tp_kazanip_tasimada_kaybeden.csv`):
  - 128 coin: TP +125,7, taşıma −329,0, net **−203,3 puan.**
  - En kötüleri KNC, EGLD, 1000SHIB, LINA, IOTX, TON, ANKR, LUNA.
  - Yaş anındaki ayrım için §1 tablosuna bakılmalı: yaşlı coinlerde TP kazancının büyük kısmını taşıma kaybı yiyor.
  - Not: "ilk işlemde genç" oranı (%96) 2021 başındaki yaş kesikliği yüzünden yanıltıcı; kullanılmamalı.

## 6. Gerçek zamanlı tespit edilebilirlik [ÖLÇÜM]

**Yöntem:**
- **Göstergeler** (o gün bilinen):
  - son 30 / 90 / 180 günün listeleme sayısı;
  - evrendeki 1 yaşından genç coin sayısı;
  - genç coinlerin medyan oynaklığı, funding'i ve log hacmi.
- **Hedef:** sonraki 30 / 60 / 90 günün kitap getirisi.
- **Kronolojik ayrım:** eğitim 2021-01 – 2023-12 (ufuk kadar ambargo), test 2024-01 – sonu.
- **Anlamlılık:** dairesel kaydırma.
- **Ek kontroller:**
  - testte iki seri de doğrusal zaman eğiliminden arındırıldı;
  - zarar dönemlerini ayırt etme gücü ölçüldü (AUC).
- **Çoklu test:** 21 test; Bonferroni eşiği 0,0024.

| Gösterge | Ufuk | ρ eğitim | ρ test | p | ρ test (eğilimsiz) | Zarar AUC (zarar oranı) |
|---|---|---|---|---|---|---|
| Genç coin sayısı | 30 g | 0,34 | 0,41 | 0,017 | **−0,04** | 0,78 (%13) |
| Genç coin sayısı | 60 g | 0,47 | 0,56 | **<0,001** | 0,13 | 0,77 (%2,6) |
| Genç coin sayısı | 90 g | 0,51 | 0,67 | **<0,001** | 0,31 | — (zarar yok) |
| Son 180 g listeleme | 30 / 60 / 90 g | 0,20 / 0,35 / 0,43 | 0,37 / 0,47 / 0,49 | 0,15-0,17 | 0,24 / 0,33 / 0,34 | 0,73 / 0,62 / — |
| Genç coin oynaklığı | 30 / 60 / 90 g | ≈ 0 | ≈ 0 | > 0,85 | 0,08-0,17 | 0,47 / 0,39 |
| Genç coin funding'i | 30 / 60 / 90 g | 0,04 / 0,18 / 0,29 | −0,10 / −0,04 / −0,07 (işaret döndü) | > 0,5 | | 0,44 / 0,26 |
| Genç coin hacmi | 30 / 60 / 90 g | −0,13 / −0,17 / −0,11 | −0,30 / −0,39 / −0,46 | 0,04-0,23 | ≈ 0 | |

- **[ÖLÇÜM]** Yalnız "genç coin sayısı" 60 ve 90 günlük ufukta Bonferroni'yi geçiyor; işareti eğitim ve testte aynı.
- **[ÖLÇÜM]** Ortak zaman eğilimi çıkarılınca ilişki 30 günde sıfırlanıyor (−0,04), 60 / 90 günde zayıflıyor (0,13 / 0,31).
  - Genç coin sayısı da kitap getirisi de 2024-26'da birlikte arttı; ilişkinin önemli kısmı bu ortak eğilim.
  - 30 günlük zarar AUC'si 0,78 ama test dönemindeki zararlar 2024'te, genç coin sayısının düşük olduğu döneme toplanmış. Bağımsız
    blok sayısı az (30 günlük ufukta 32, 60 günlükte 15).
- **[ÖLÇÜM]** Genç coinlerin oynaklık, funding ve hacim göstergelerinin öngörü gücü yok. Funding'in işareti eğitimle test arasında döndü.
- **Sonuç:** Akıştaki bozulmanın ölçüsü (genç coin sayısı) gerçek zamanlı biliniyor ve getiriyle aynı yönde hareket ediyor. Ama bunun
  bağımsız öngörü gücü KANITLANMADI. Kapı ya da filtre önerilmez; izleme göstergesi olarak tutulabilir.

## 7. Cevaplar

**1. Yeni coinlerin avantajı tam olarak hangi özelliklerinden geliyor?**
- [ÖLÇÜM] Genç coinlerde TP oranı daha yüksek (%21-31'e karşı %8) ve tutuş kaybı yok. Yaşlı coinlerde TP kazancını long fiyat kaybı yiyor.
- Bu fark oynaklık, funding ve hacimle açıklanamıyor: aynı tercillerde de 18 tabakanın 18'inde genç coin daha iyi; regresyonda yaş
  katsayısı kontrollerle long'da hiç, short'ta üçte bir azalıyor.
- [HİPOTEZ] Kaynak, yeni listelenen coinin ölçülmeyen bir özelliği (fiyat keşfi, konumlanma, arz dinamikleri). Nedensellik gösterilmedi.

**2. Avantaj ilk 30, 90, 180 veya 365 günde mi yoğunlaşıyor?**
- [ÖLÇÜM] Bot ilk 60 günde işlem yapmıyor (asgari yaş kuralı). İlk yıl katkısının %20'si ilk 90 günde, %63'ü ilk 180 günde.
- Maruziyet başı getiri en yüksek 60-180 gün arasında (yıllık ~%440-450); 181-365 günde %306, 1-2 yılda %163, 2 yıl üstünde %16.

**3. Binance'in yeni vadeli listeleme akışı azalırsa getiri ne kadar etkilenir?**
- [ÖLÇÜM; senaryo VARSAYIM] Motor karşı-olgusunda 2024-26 CAGR %248'den:
  - listeleme −%25 → %141-186;
  - −%50 → %104-107;
  - −%75 → %65-69;
  - 1 yaşından genç coin hiç yok → %51.
- 2025 ilk yarısında 6 aylık bir duruş, sonraki 18 ayı %425'ten %168'e indiriyor.
- Etki doğrusal modelden (−%20 / −%39 / −%59) daha sert ve hangi coinlerin kaybolduğuna çok bağlı.

**4. Eski coinler yeni coinlerin yerini doldurabilir mi?**
- [ÖLÇÜM] Hayır, aynı kalitede değil. Motor aynı brüt maruziyeti ve aynı işlem sayısını koruyor, ama maruziyet başı getiri yarıya
  (2024+ dönemde üçte bire) iniyor. Eski coinlerde TP oranı ve oynaklık sürekli düşük.

**5. Yeni coinlerin yüksek getirisi hangi ek riskleri taşıyor?**
- [ÖLÇÜM] Ani çöküş ve sıçrama 4-15 kat, funding aşırılığı 2-6 kat. %3,5 delist (ilk yılında 9 coin; net −4,4 puan). Biraz daha düşük
  hacim.
- Fiyat boşluğu pratikte yok. Spread ve derinlik ölçülemedi.
- 128 coin TP'de kazandırıp taşımada kaybettirdi (net −203 puan).
- Bot en riskli ilk 60 günü asgari yaş kuralıyla zaten dışarıda bırakıyor.

**6. Listeleme akışındaki bozulma gerçek zamanlı önceden tespit edilebilir mi?**
- [ÖLÇÜM] Akışın kendisi gerçek zamanlı ölçülebiliyor (listeleme sayısı, genç coin sayısı). Ama sonraki 30-90 günün getirisini bağımsız
  öngördüğü kanıtlanmadı: zaman eğilimi çıkarılınca ilişki büyük ölçüde kayboluyor.
- Erken uyarı değil, **durum göstergesi** olarak izlenmeli.

**7. Uzun vadeli sürdürülebilirlik yeni listelemelere ne ölçüde bağımlı?**
- [ÖLÇÜM] Büyük ölçüde. 2024-26 net kârının %78'i 1 yaşından genç coinlerden. Yaşlı coinlerin maruziyet başı getirisi yıllık %16
  (> 2 yıl) ile %163 (1-2 yıl) arasında. Akış yarıya inerse son dönem getirisi kabaca yarıdan fazla düşüyor.
- [HİPOTEZ] Strateji fiilen bir "yeni listeleme hasadı". Binance'in listeleme hızı (2025-26'da çeyrekte 45-107 coin) ve yeni coinlerin
  davranışı, sistemin en önemli dış bağımlılığı.
- Bu bağımlılık backtestte sınanamaz; canlıda listeleme akışı ve genç coinlerin kitaba katkısı ayrı ayrı izlenmeli.

---
### Yeniden üretim
```bash
python3 arastirma_m694_yeni_coin.py kos      # parite (2) + 9 senaryo × 2 hiza, tek işçi (~50 dk); ANALİZİ EŞZAMANLI ÇALIŞTIRMAYIN (bellek)
python3 arastirma_m694_yeni_coin.py analiz   # -> /tmp/m694/*.csv + ekran raporu (~15 dk)
```
Önkoşul: madde 690, 691 (`kos_seviye`), 692, 693 (`analiz`) çıktıları.
