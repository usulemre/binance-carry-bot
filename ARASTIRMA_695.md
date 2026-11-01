# Araştırma 695 — Strateji dayanıklılığı ve başarısızlık analizi (1 Kasım 2026)

> Amaç daha yüksek CAGR değil; mevcut stratejinin gerçek hayatta başarısız olabileceği koşulları bulmak.

## Değişmeyenler ve kontroller
Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**. Filtre, kapı ya da otomatik değişiklik eklenmedi;
sonuçlara bakarak hiçbir parametre değiştirilmedi.

- **Araç:** `arastirma_m695_dayaniklilik.py`.
  - Komutlar: `kos` motor koşuları, `analiz` analiz.
- **Motor kopyası:** `/tmp/g33_m695.py`.
  - `g33.py`'ye tek bir düğme ekliyor: `TP_DOLUM_P`, deterministik sözde-rastgele TP / kademe dolum olasılığı.
  - Düğme kapalıyken iki hizada da dondurulmuş referansla (`M357_EK_P3T2_2000_{0,1}`) **bayt bayt aynı**.
- **Dondurulmuş baz:**

  | CAGR | Sharpe | Maks DD | Calmar | En kötü gün | En kötü ay |
  |---|---|---|---|---|---|
  | %247,4 | 4,14 | −%13,3 | 18,6 | −%7,4 | −%6,6 |

- **Veri kapsamı:** 2020-07-19 → 2026-09-30, 4 saatlik bar, iki hiza ortalaması.
  - 2026 kısmi yıl (9 ay).
  - Yaş analizleri 2021+ (veri 2020-01'de başladığı için yaş kesik).
- **Koşular:** 66 motor koşusunun hepsi (32 senaryo × 2 hiza + parite × 2) rc 0 ile bitti, tek işçiyle çalıştı.
  - Arka plan görevi 2 saat sınırında 63. koşuda kesildi.
  - Kesilen koşunun (G_NET5 hiza 1) yarım dosyası silindi ve **sayılmadı**; o koşu baştan koşuldu.
  - Analiz, motor koşuları bittikten sonra tek başına çalıştı.
- **Çıktı kontrolü:** 32 senaryo, eksik 0, parite AYNI / AYNI. Tablolar `/tmp/m695/*.csv` dosyalarında.
- **Git:** strateji ve motor dosyalarında diff yok.

Etiketler:
- **ÖLÇÜM:** doğrudan veriden ya da motordan.
- **VARSAYIM:** şok büyüklüğü, dolum modeli ya da senaryo tasarımı.
- **HİPOTEZ:** doğrulanmamış açıklama.

**Sınıflar:**
- **ROBUST:** makul streste getiri ve risk kabul edilebilir kalıyor.
- **WEAK:** strateji yaşıyor ama belirgin bozuluyor.
- **FRAGILE:** gerçekçi bir koşulda strateji büyük ölçüde çöküyor.
- **UNKNOWN:** veri ya da yöntem karar vermeye yetmiyor.

Önceki araştırmalar **tekrar koşulmadı**; referans verildi:
- 691: kayma ve delme.
- 692: TP yok.
- 693 / 694: genç coin yok, listeleme −%25 / −%50 / −%75.

---

## Özet tablo

| Test | Sınıf | Tek cümle |
|---|---|---|
| A. Listeleme kuraklığı | **FRAGILE** (30 g: WEAK) | 2025-H1'de 180 gün listeleme olmasa 2025 yılı %267 → %80; 694'te listeleme −%75 ise 2024-26 CAGR %65-69 |
| B. Blok bootstrap | **ROBUST** (geçmiş içinde) | 1 yıl ufukta CAGR p5 %90-105, zarar olasılığı ~%0, DD>%30 olasılığı ≤%0,02 |
| C. Walk-forward | **UNKNOWN** | Geçmişe göre seçim bazı yenemiyor (CAGR 198 / 187 vs 207); bağımsız OOS yok |
| D. Coin yaşı atfı | **ROBUST** (bulgu) | Genç coin üstünlüğü her rejimde ve her oynaklık grubunda; A riskinin kökü |
| E. İcra stresi | **dolum %97 / %90: ROBUST** · **%80 / %70: WEAK** · **kısmi dolum / ters seçilim: UNKNOWN** | %70 dolumda CAGR −29 puan, en kötü gün −%7,4 → −%14,5 |
| F. Piyasa stresi | **BTC yönü / likidite: ROBUST** · **short sıkışması / funding dönüşü: WEAK** · **tasfiye: ROBUST** | BTC korelasyonu +0,02; varsayımsal 3 short +%100 tek gün −%21-26 |
| G. Yoğunlaşma | **WEAK** | En iyi 1 coin (TRB) çıkınca −22 puan; ilk 10 çıkınca CAGR %135, Sharpe 2,97 |
| H. Parametre duyarlılığı | **ROBUST** (YAS_GUN kırılma noktası: **FRAGILE** tarafı) | 20 komşunun 19'u bazın ±%20'sinde, hiçbirinde Sharpe < 3 yok; YAS_GUN 30 → DD −%35 |

---

## A. Yeni listeleme kuraklığı — FRAGILE

**Tasarım [VARSAYIM]:**
- 2025-01-01'den başlayan N gün içinde listelenen coinler (TradFi ve D8 hariç) evrenden tamamen çıkarıldı.
- Duruş hiç olmamış gibi değil, o coinler hiç gelmemiş gibi modellendi.
- Motor sermayeyi kalan coinlere kendisi dağıtıyor; eski coinlerin yer doldurma kapasitesi böylece ölçülüyor.
- 2025-01 seçimi, en yoğun listeleme dönemi olduğu için kötü durum. Ayrıca 17 çeyrek başlangıcı × 4 süre ile statik ızgara da kuruldu
  (yeniden dağıtım yok).

**Motor sonuçları [ÖLÇÜM]:**

| Senaryo | CAGR | Sharpe | Maks DD | Calmar | En kötü gün | En kötü ay | 2025 % | 2026 % | Duruştan sonraki 18 ay CAGR |
|---|---|---|---|---|---|---|---|---|---|
| BAZ | 247,4 | 4,14 | −13,3 | 18,6 | −7,4 | −6,6 | 267 | 283 | %425 |
| 30 g duruş | 218,4 | 3,90 | −13,3 | 16,4 | −7,4 | −6,6 | 177 | 196 | %280 |
| 60 g duruş | 217,3 | 3,89 | −13,3 | 16,3 | −7,4 | −6,6 | 162 | 206 | %253 |
| 90 g duruş | 204,2 | 3,77 | −13,3 | 15,3 | −7,7 | −6,6 | 117 | 185 | %196 |
| 180 g duruş | 198,1 | 3,77 | −15,9 | 12,5 | −7,4 | −7,8 | 80 | 203 | %168 |

- 2020-2024 yılları birebir aynı; senaryo yalnız sonrasını etkiliyor.
- **Sermaye kullanımı:** brüt ort 0,72 / 0,72 / 0,72 / 0,72; aynı gün tutulan coin 13,3 → 12,9.
  - **Sermaye boşta kalmıyor;** eski coinlere kayıyor ama orada daha az kazanıyor.
- **Long / short:** long katkısı 511 → 435 puan, short 335 → 313. Kaybın ~%75'i long tarafında.
- **Tek bir 30 günlük boşluk bile** 2025'i 90 puan düşürüyor. Bunun nedeni: o 30 günde gelen coinler sonraki ~1 yılın kârının büyük kısmını
  taşıyor; bot onları 60. günden sonra ~1 yıl tutuyor.

**Statik ızgara [ÖLÇÜM]:**
- Duruştan sonraki 18 ay CAGR oranı (senaryo / baz), medyan ve en kötü:
  - 30 g: 0,95 / 0,54
  - 90 g: 0,91 / 0,35
  - 180 g: 0,72 / 0,21
- 2025-01 180 g için statik %166, motor %168. Motorun yeniden dağıtımı neredeyse hiç telafi etmiyor.

**Referans (694, tekrar koşulmadı):**
- Kalıcı listeleme −%25 → 2024-26 CAGR %141-186; −%50 → %104-107; −%75 → %65-69.
- Genç coin yok → %51.
- Eski coinler aynı brüt maruziyette maruziyet başı getiriyi %187 → %97'ye indiriyor.

**Sınıf:** 30 gün WEAK; 90-180 gün ve kalıcı azalma FRAGILE.

**Güvenilirlik:** orta-yüksek. Motor gerçek; senaryo varsayımsal. Gelecekte bir listeleme kuraklığının olasılığı ölçülemez.

---

## B. Durağan blok bootstrap — ROBUST (geçmiş dağılım içinde)

**Yöntem:**
- Politis-Romano durağan blok bootstrap: günlük getiriler, ortalama 10 ve 30 günlük bloklarla.
- 10.000 simülasyon, 1 yıllık ufuk.
- Bloklar günlük bağımlılığı ve oynaklık kümelenmesini kısmen korur.

| Seri (blok) | CAGR p5 | CAGR med | Sharpe p5 | DD med | DD p5 | DD p1 | En kötü 30 g p5 | Zarar olasılığı | DD>%20 | DD>%30 |
|---|---|---|---|---|---|---|---|---|---|---|
| BAZ 2020-26 (10) | 101 | 243 | 2,53 | −11,5 | −17,4 | −21,3 | −9,9 | %0,00 | %1,8 | %0,02 |
| BAZ 2020-26 (30) | 90 | 235 | 2,39 | −11,5 | −15,7 | −19,0 | −8,5 | %0,00 | %0,6 | %0,01 |
| BAZ 2024-26 (10) | 105 | 245 | 2,46 | −11,9 | −17,8 | −21,5 | −10,0 | %0,01 | %2,0 | %0,01 |
| **BAZ yalnız 2022** (10) | **7** | 62 | 0,40 | −14,8 | −25,2 | −31,3 | −14,0 | **%2,7** | **%17,5** | %1,5 |
| BAZ yalnız 2022 (30) | 14 | 62 | 0,62 | −13,3 | −21,6 | −26,0 | −11,9 | %1,2 | %8,5 | %0,2 |
| **Genç coin yok** 2024-26 (10) | **−2** | 51 | 0,05 | −16,0 | −28,4 | −35,1 | −14,4 | **%6,0** | **%25,9** | %3,2 |
| Maker dolum %80 (10) | 86 | 224 | 2,16 | −12,7 | −19,8 | −24,3 | −11,3 | %0,01 | %4,6 | %0,08 |
| TP yok (692) (10) | 53 | 197 | 1,33 | −16,3 | −26,9 | −32,3 | −15,9 | %0,18 | %25,4 | %2,1 |

**Yorum:**
- Geçmişin karışımı tekrarlanırsa, 1 yılda zarar etme olasılığı pratikte sıfır.
- Ama bootstrap **yeni bir rejim üretemez**.
- Yalnız 2022 gibi bir yıl tekrarlanırsa beklenen CAGR ~%60, DD>%20 olasılığı %8-17.
- Genç coin akışı kesilirse 1 yıllık CAGR'nin %5 kötü ucu sıfırın altında, DD>%20 olasılığı %26-31.
- Yani B'deki rahatlık, A'daki koşulun sürmesine bağlı.

**VARSAYIM:** geçmiş günlük getirilerin dağılımı geleceği temsil eder.

**Güvenilirlik:** orta. İstatistik sağlam; temsil varsayımı zayıf.

---

## C. Walk-forward — UNKNOWN

**Tasarım:**
- Aday kümesi: baz + H bölümündeki 20 komşu ayar, toplam 21.
- Her yılın başında yalnız o tarihe kadarki veriye göre en yüksek Sharpe'lı aday seçilip o yıl uygulandı.
- İki pencere türü: genişleyen ve kayan 2 yıl.
- İlk seçim yılı 2022.

| Kip | WF CAGR | WF Sharpe | WF Maks DD | WF Calmar | Baz CAGR (aynı dönem) | Baz Sharpe | Baz DD |
|---|---|---|---|---|---|---|---|
| Genişleyen | 197,7 | 3,57 | −15,4 | 12,9 | 207,0 | 3,68 | −13,3 |
| Kayan 2 yıl | 186,7 | 3,51 | −15,4 | 12,2 | 207,0 | 3,68 | −13,3 |

- **Yıl yıl WF / baz (genişleyen):** 2022 67 / 63 · 2023 316 / 309 · 2024 98 / 118 · 2025 253 / 267 · 2026 266 / 283.
- **Seçilen ayarın o yılki sırası (21 aday içinde):** 5, 2, 20, 17, 13.
  - Geçmiş Sharpe sırası ile o yılın sırası arasındaki korelasyon −0,21 … 0,60.
  - **Geçmiş performans, komşu ayarlar arasında bir sonraki yılı öngörmüyor.**
  - Bu iyi bir işaret: komşular arasındaki fark büyük ölçüde gürültü ve plato düz.
- **Neden UNKNOWN:**
  - Baz ayar 2020-2026 verisinin **tamamı** üzerinde geliştirildi; adaylar da onun komşuları.
  - Dolayısıyla bu walk-forward **bağımsız OOS değil**; yalnız yerel seçim gürültüsünü ölçüyor.
  - WF'nin baza göre ~%5-10 düşük kalması, "parametre yeniden seçilseydi" ödenecek bedel için kaba bir alt sınır.
- **İlk gerçek OOS ayı:** parametre dondurulduktan sonra 2026-10 (izleme_ekim_oos; veri 2 Kasım'da).

**Güvenilirlik:** düşük. Yöntem gereği karar veremez.

---

## D. Coin yaşı atfı — ROBUST (bulgu tutarlı; nedensellik iddiası yok)

**Kaynak:** 693'teki pozisyon epizotları (2021+, 15.917 pozisyon), 693'ün rejim etiketleri.

| Yaş | Poz | TP oranı % | Poz başı net bp | TP bp | Funding bp | MFE med % | MAE med % | Sermaye payı % | Sermaye başı yıllık % |
|---|---|---|---|---|---|---|---|---|---|
| 60-90 g | 874 | 28,7 | 31,4 | 31,8 | 8,3 | 11,5 | −11,5 | 6,6 | 494 |
| 90-180 g | 1.869 | 21,4 | 16,6 | 22,6 | 3,6 | 10,8 | −10,7 | 11,2 | 329 |
| 180-365 g | 3.065 | 19,3 | 13,3 | 19,2 | 4,0 | 10,6 | −10,6 | 18,4 | 263 |
| 1-2 yıl | 4.371 | 14,2 | 8,0 | 14,4 | 2,0 | 8,5 | −8,7 | 27,6 | 150 |
| > 2 yıl | 5.738 | 7,6 | 4,2 | 7,2 | 2,4 | 6,0 | −6,3 | 36,1 | 80 |

**Kontroller [ÖLÇÜM], poz başı net bp:**
- **BTC yönüne göre:**
  - Güçlü düşüşte bütün yaşlar 10-15 bp, fark yok.
  - Güçlü yükselişte genç 20-26 bp, > 2 yıl 1,6 bp.
  - Yatayda 60-90 g 45,6 bp, > 2 yıl 3,1 bp.
- **Kitap oynaklığına göre:** genç coin düşük ve yüksek oynaklıkta benzer (28 / 33 bp). > 2 yıl yüksek oynaklıkta 1,9 bp'ye düşüyor.
- **Hacim, funding ve coin oynaklığı kontrolü:** 694'te 18 / 18 tabakada genç coin daha iyiydi; tekrar edilmedi.

**HİPOTEZ:** genç coin primi fiyat keşfi aşamasındaki iki yönlü oynaklıktan (TP) ve yüksek funding'den geliyor. Neden-sonuç kurulmadı.

**Sermaye verimliliği [ÖLÇÜM]:** sermayenin %36'sı > 2 yıl coinlerde ve yıllık ~%80 kazanıyor. Sermayenin %18'i < 180 gün coinlerde ve
~%330-490 kazanıyor.

**Güvenilirlik:** yüksek, ölçüm. Bu bulgu bir güç değil, **bağımlılık**; A ve G'nin kökü.

---

## E. İcra stresi — dolum ≥%90 ROBUST · %80-70 WEAK · kısmi dolum ve ters seçilim UNKNOWN

**Model [VARSAYIM]:**
- Fiyat limite dokunduğunda TP / kademe emri p olasılıkla doluyor (deterministik sözde-rastgele, koşular arası tekrarlanabilir).
- Dolmazsa emir bekliyor ve sonraki dokunuşta yine p olasılıkla doluyor.
- Dolmayan pay için her işleme 10 bp taker kayması ekleniyor: `KOM = 5 bp + (1−p)·10 bp`.
- TP dolum olasılığı ayrı modellendi; giriş ve çıkış maliyeti KOM ile.

| Dolum | CAGR | Sharpe | Maks DD | Calmar | En kötü gün | En kötü ay | Zarar ayı % | Long / short puan | Fark |
|---|---|---|---|---|---|---|---|---|---|
| %100 (baz) | 247,4 | 4,14 | −13,3 | 18,6 | −7,4 | −6,6 | 14,7 | 511 / 335 | — |
| %97 | 243,7 | 4,10 | −13,4 | 18,2 | −7,4 | −6,7 | 14,7 | 510 / 332 | −3,8 |
| %90 | 242,9 | 4,05 | −14,6 | 16,7 | −7,4 | −6,9 | 14,7 | 522 / 325 | −4,6 |
| %80 | 230,0 | 3,77 | −15,3 | 15,1 | **−14,5** | −7,1 | 14,7 | 522 / 314 | −17,4 |
| %70 | 218,4 | 3,53 | −15,7 | 13,9 | **−14,5** | −8,4 | 21,3 | 521 / 304 | −29,1 |

- **Yıllık:** %70 dolumda 2021 472 → 386, 2023 310 → 250, 2022 63 → 51. Diğer yıllar gürültü düzeyinde (±20).
- **Kuyruk riski:** %80 ve altında **en kötü gün iki katına çıkıyor** (−%7,4 → −%14,5).
  - **HİPOTEZ:** bir sıçramada short TP'si dolmuyor, pozisyon büyük kalıyor ve geri dönüşü değil devamını yaşıyor.
  - Bu, dolum kaybının ortalamadan çok kuyrukta acıttığını gösteriyor.
- **Sermaye kullanımı:** brüt 0,72 → 0,73, coin-gün 13,3 → 13,1. Dolmayan TP pozisyonu biraz daha uzun açık tutuyor.
- **Referans (691):**
  - Ek 20 bp kayma: CAGR −5,8.
  - 20 bp delme şartı: −4,1.
  - 691'de gerçek dolum verisi yoktu.
- **UNKNOWN kalanlar:**
  - Kısmi dolum.
  - Emir bekleme süresi ve kuyruk sırası.
  - Ters seçilim: limitin tam da fiyat geri dönmeyecekken dolması. 693'te TP barlarının %71'i seviyenin gerisinde kapanıyor, bu da ters
    seçilimin sınırlı olabileceğine işaret ediyor; ama gerçek emir defteri verisi yok.
  - Genç coinlerde spread (694'te de ölçülemedi).

**Güvenilirlik:** orta. Mekanizma motorda; dolum olasılığı tamamen varsayım.

---

## F. Piyasa stresi — BTC ve likidite ROBUST · sıkışma ve funding dönüşü WEAK · tasfiye ROBUST

**Yöntem:**
- 2021+ her günün gerçek pozisyon ağırlıkları alındı.
- Her coinin nedensel 90 günlük BTC betası ile şok uygulandı, tek günlük kitap etkisi özkaynak %'si olarak ölçüldü.
- Şok büyüklükleri **VARSAYIM**.
- Funding dönüşü satırı tek gün değil, sonraki **30 günün kümülatif** etkisi.

| Şok | Medyan | En kötü %5 | En kötü | En iyi |
|---|---|---|---|---|
| BTC −%20 | −0,8 | −4,4 | −10,1 | +7,9 |
| BTC −%40 | −1,4 | −8,5 | −16,1 | +14,9 |
| BTC +%20 | +0,8 | −3,4 | −7,9 | +10,1 |
| BTC +%40 | +1,5 | −6,7 | −15,8 | +20,1 |
| BTC −%30 + korelasyon artışı (long beta ×1,5, short ×0,5) | −13,8 | −23,0 | −31,1 | −1,9 |
| Short sıkışması: en büyük 3 short +%100 | −20,6 | −23,6 | −26,3 | −4,7 |
| Long çöküşü: en büyük 3 long −%50 + BTC −%10 | −9,9 | −15,9 | −20,9 | −1,1 |
| Likidite kaybı: brütün %2'si | −1,5 | −1,7 | −1,9 | −0,7 |
| Likidite kaybı: brütün %5'i | −3,7 | −4,3 | −4,8 | −1,7 |
| Funding tersine (30 g, −2× gerçekleşen funding) | −3,5 | −23,6 | −34,7 | −0,6 |

**Gerçek en sert günler [ÖLÇÜM]:**
- **En sert 10 BTC düşüş günü (−%11 … −%15):** kitap aynı gün en kötü −%5,3 (2022-05-09), medyan ~−%1; 7 günde en kötü −%5,3.
- **En sert 10 BTC yükseliş günü:** kitap aynı gün en kötü −%1,5; 7 günde en kötü −%1,5.
- 2026-02-05 (BTC −%14) kitap +%0,3, 7 günde +%11,8.

**Faktör [ÖLÇÜM]:**
- Kitap ↔ BTC günlük korelasyon +0,02 (beta +0,013); ↔ alt evren medyanı +0,01.
- Long bacak ↔ short bacak −0,61 (short işaretli). Hedge güçlü ama tam değil.
- **Kitap maruziyeti:** brüt ort 0,72, maks 0,96; net ort +0,04 (%5-%95: −0,05 … +0,12).
- **Alt korelasyonu artınca:** tutulan coinlerin BTC ile 30 günlük korelasyonu yüksek dönemlerde kitap günlük ort 28,5 bp (düşükken 41,4 bp).
  - Getiri düşüyor ama zarara dönmüyor.

**Tasfiye ve teminat:**
- 1,0x doz ve brüt ≤ ~0,9 özkaynak ile, çapraz teminatta tasfiye ancak özkaynağın neredeyse tamamı kaybedilirse olur.
- Tablodaki en kötü senaryo günü −%34,7, yani **tasfiye yok**.
- İzole 1x short'ta tek pozisyon fiyat ~+%95-100'de tasfiye olur; bu, o pozisyon değeri kadar kayıp demek.
- Short sıkışması satırından çıkan kaba tahmin: en büyük short'lar tek tek ~%7 ağırlıkta (3 short +%100 → medyan −%20,6). Yani en büyük
  pozisyonun tek tasfiyesi kitapta ~−%7 eder; küçük pozisyonlarda daha az.

**Yorum:**
- Strateji BTC yönüne karşı fiilen nötr, gerçek çöküş günleri bunu doğruluyor.
- Asıl açık **tekil coin şoku**: genç coinlerde 24 saatte +%100 nadir değil (694: çöküş / sıçrama 4-15×).
  - En büyük 3 short aynı gün ikiye katlanırsa kitap −%21-26 kaybeder.
  - Bu, tarihte gözlenen en kötü günün (−%7,4) 3 katı. Üç büyük short'un aynı gün +%100 yapması tarihte gözlenmedi [VARSAYIM].
- **Funding dönüşü:** funding'in aniden 30 gün boyunca tersine dönmesi en kötü dönemde −%35 eder. 690'a göre funding en istikrarlı
  bileşen; bu senaryo aşırı uç.

**Güvenilirlik:** orta. Pozisyonlar gerçek; şoklar varsayım; beta günlük ve kuyrukta eksik tahmin olabilir.

---

## G. Yoğunlaşma — WEAK

**Tasarım:** tam örneğe göre en yüksek net katkılı coinler evrenden çıkarıldı. Bu geriye bakan bir seçim, yani bilerek en kötü durum.

| Senaryo | CAGR | Sharpe | Maks DD | Calmar | En kötü gün | En kötü ay | Zarar ayı % | Long / short | Fark |
|---|---|---|---|---|---|---|---|---|---|
| BAZ | 247,4 | 4,14 | −13,3 | 18,6 | −7,4 | −6,6 | 14,7 | 511 / 335 | — |
| −1 (TRB) | 225,8 | 3,99 | −13,4 | 16,9 | −7,4 | −6,0 | 16,0 | 471 / 334 | −21,7 |
| −3 | 192,7 | 3,66 | −13,4 | 14,4 | −7,0 | −6,3 | 13,3 | 413 / 325 | −54,8 |
| −5 | 172,0 | 3,41 | −13,5 | 12,7 | −7,0 | −6,3 | 13,3 | 366 / 328 | −75,5 |
| −10 | 135,1 | 2,97 | −16,1 | 8,4 | −7,0 | −6,7 | 21,3 | 299 / 303 | −112,3 |

- **Çıkarılan coinler sırasıyla:** TRB, SOL, PIPPIN, RIVER, BNB, CRV, THETA, GALA, INJ, WAVES.
- **Yıllık:**
  - TRB çıkınca 2023 %310 → %166. Tek coin o yılın kârının ~yarısı.
  - İlk 10 çıkınca 2020 %92 → %30, 2022 %63 → %30; 2024-26 ise %106-184.
  - Bütün yıllar pozitif kalıyor.
- **Sermaye kullanımı:** değişmiyor (brüt 0,71-0,72); sermaye diğer coinlere kayıyor.
- **En kârlı aylar çıkarılınca** (kalan günler birleştirilerek):
  - 1 ay (2021-02): %229.
  - 3 ay: %201.
  - 5 ay: %178.
  - 10 ay: %133, Sharpe 3,07.
- **Long / short (komisyon hariç):** +511 / +335 puan.
  - Short her yıl pozitif (2023'te yalnız +1,7).
  - Long 2022'de −19.
  - İki bacak birbirini farklı yıllarda taşıyor.
- **Ortak faktör:** F'deki BTC ve alt korelasyonu ~0. Ortak faktör piyasa yönü değil, **genç ve oynak coin akışı** (D).
- **691 referansı:** etkin coin sayısı ~151.

**Sınıf:** WEAK, FRAGILE değil.
- Geriye bakan en kötü seçimde bile strateji %135 ve Sharpe ~3 ile yaşıyor.
- Ama tek bir coin bir yılın yarısını taşıyabiliyor; yıllık sonuç tek coine çok duyarlı.

**Güvenilirlik:** yüksek, motor ölçümü.

---

## H. Parametre duyarlılığı — ROBUST (YAS_GUN'de tek taraflı uçurum)

**Tasarım:** her parametre tek tek, mevcut değerin iki yanında. Yeni optimum aranmadı, hiçbir değer önerilmiyor.

| Parametre | Değer | CAGR | Sharpe | Maks DD | Calmar | En kötü gün | En kötü ay | Fark |
|---|---|---|---|---|---|---|---|---|
| — | mevcut | 247,4 | 4,14 | −13,3 | 18,6 | −7,4 | −6,6 | — |
| TPL | 0,50 / 0,70 (0,60) | 243 / 248 | 4,13 / 4,12 | −13,2 / −13,2 | 18,4 / 18,7 | −7,4 / −7,4 | −6,9 / −6,4 | −4 / +0 |
| TPS | 0,15 / 0,25 (0,20) | 249 / 245 | 4,15 / 4,13 | −13,3 / −13,3 | 18,7 / 18,4 | −7,4 / −7,4 | −6,6 / −6,8 | +1 / −2 |
| MERD_ESIK | 0,35 / 0,55 (0,45) | 214 / 252 | 4,10 / 3,96 | −13,4 / **−17,1** | 16,0 / 14,7 | −6,6 / **−12,3** | −6,8 / −7,7 | −34 / +4 |
| MERD_PAY | 0,70 / 0,90 (0,80) | 246 / 246 | 4,10 / 4,15 | −13,8 / −13,4 | 17,8 / 18,4 | −7,4 / −7,4 | −6,3 / −6,7 | −1 / −1 |
| MERDS_ESIK | 0,12 / 0,18 (0,15) | 251 / 249 | 4,16 / 4,13 | −15,4 / −13,3 | 16,3 / 18,7 | −7,4 / −7,5 | −7,6 / −5,6 | +3 / +1 |
| REB_GUN | 4 / 6 (5) | 267 / 226 | 4,02 / 4,16 | −15,5 / −13,3 | 17,2 / 17,1 | −7,7 / −5,5 | −8,4 / −5,6 | +19 / −21 |
| HAVUZ | 3 / 5 (4) | 231 / 238 | 3,93 / 4,07 | −15,3 / −14,1 | 15,1 / 16,9 | −9,0 / −7,3 | −8,9 / −6,2 | −17 / −10 |
| **YAS_GUN** | **30** / 90 (60) | **197** / 208 | **3,34** / 3,90 | **−35,3** / −12,4 | **5,6** / 16,8 | **−16,8** / −7,4 | **−20,5** / −5,7 | −50 / −40 |
| HACIM_ESIK | 5e7 / 1e8 (7e7) | 251 / 214 | 4,15 / 3,82 | −15,5 / −14,9 | 16,3 / 14,3 | −6,5 / −7,6 | −7,5 / −6,3 | +4 / −34 |
| SLL24 | 0,35 / 0,55 (0,45) | 246 / 248 | 4,14 / 4,13 | −13,5 / −14,8 | 18,3 / 16,7 | −7,4 / −7,4 | −9,7 / −8,3 | −1 / +0 |

**Plato [ÖLÇÜM]:**
- 20 komşunun 19'u CAGR'de bazın ±%20'si içinde.
- Hiçbir komşuda Sharpe 3'ün altına düşmüyor.
- 8 komşu bazdan biraz iyi. Baz tam veriyle seçildiği için bu aşırı uyum değil, gürültü işareti.
- Plato düz olduğu için yeni optimum aramak anlamsız.

**Kırılma noktaları [ÖLÇÜM]:**
- **YAS_GUN 30:** Maks DD −%13 → −%35, en kötü ay −%20,5, 2024 %118 → %82, 2025 %267 → %119.
  - Çok genç (30-60 gün) coinler, getiriyi değil riski artırıyor.
  - Mevcut 60 günlük eşik bu uçurumun hemen yanında.
  - YAS_GUN 90 ise getiriyi 40 puan düşürüyor ama riski artırmıyor.
  - Yani eşik **tek taraflı kırılgan**: aşağı yönde hata pahalı.
- **MERD_ESIK 0,55:** CAGR aynı, ama en kötü gün −%12,3, DD −%17. Kademe eşiğini gevşetmek kuyruğu kalınlaştırıyor.
- **HACIM_ESIK 1e8:** −34 puan, short katkısı 335 → 279. Hacim eşiği yükselirse genç coinler evrene geç giriyor (D ile tutarlı).
- **REB_GUN ±1:** ±20 puan. Yönü tutarlı ama risk tarafında anlamlı bir fark yok.

**Güvenilirlik:** yüksek, motor ölçümü. Yalnız tek boyutlu tarama; parametre etkileşimleri test edilmedi.

---

## Stratejinin en büyük 5 riski

1. **Yeni listeleme akışına bağımlılık (A, D) — FRAGILE.**
   - 2024-26 net kârın %78'i < 1 yaş coinlerden geliyor.
   - 180 günlük listeleme boşluğu bir yılı %267 → %80'e indiriyor; kalıcı −%75 azalma 2024-26 CAGR'yi %65-69'a düşürüyor.
   - Eski coinler yeri dolduramıyor. Binance'in listeleme politikası tamamen dış etken.
2. **Coin yoğunlaşması (G) — WEAK.**
   - Tek coin (TRB) 2023 kârının yarısı; ilk 10 coin çıkınca −112 puan.
   - Canlıda belirli bir yıl, "o yılın TRB'si" çıkmazsa beklenenin çok altında kalabilir.
3. **TP / kademe dolum gerçekliği (E) — WEAK / UNKNOWN.**
   - Kârın ana bileşeni dokunan limitlerin dolmasına dayanıyor.
   - %70 dolum → −29 puan; %80 ve altında en kötü gün iki katı.
   - Kısmi dolum, kuyruk sırası, ters seçilim ve genç coin spread'i hiç ölçülmedi.
4. **Tekil coin şoku ve genç coin kuyruğu (F, H).**
   - Gözlenmiş en kötü gün −%7,4. Ama aynı gün 3 büyük short'un ikiye katlanması tek günde −%21-26 eder.
   - YAS_GUN 30 testi, çok genç coinlerin DD'yi −%35'e çıkardığını gösteriyor; mevcut eşik bu uçuruma 30 gün uzaklıkta.
5. **Bağımsız OOS yokluğu ve rejim temsil riski (B, C).**
   - Parametreler tam veride geliştirildi; walk-forward bunu düzeltemez.
   - Bootstrap 2022 benzeri yıl için medyan ~%62 ve DD>%20 olasılığı %8-17; genç coin akışı yoksa 1 yılda zarar olasılığı %5-6.
   - Gerçek OOS performansı 2026-10'dan itibaren ölçülecek.

## Stratejinin en güçlü 5 özelliği

1. **Piyasa yönüne karşı nötr (F):**
   - BTC ile günlük korelasyon +0,02, net maruziyet ort +0,04.
   - Gerçek en sert 10 BTC çöküş günü: kitap en kötü −%5,3, medyan ~−%1.
   - Hiçbir senaryoda tasfiye yok.
2. **Düz parametre platosu (H, C):**
   - 20 komşunun 19'u ±%20 içinde, hiçbirinde Sharpe < 3 yok.
   - Komşular arasında geçmiş sıra geleceği öngörmüyor; sonuç tek bir "şanslı" ayara dayanmıyor.
3. **Maliyet ve dolum toleransı orta stresle sınırlı (E, 691):**
   - %90 dolum −4,6 puan; ek 20 bp kayma −5,8; 20 bp delme −4,1.
4. **Geçmiş dağılım içinde istikrar (B):**
   - 1 yıl ufukta CAGR p5 %90-105, zarar olasılığı ~%0, DD>%30 olasılığı ≤%0,02.
5. **Yayılmış kâr kaynağı (G):**
   - Long ve short ikisi de pozitif (+511 / +335) ve farklı yıllarda birbirini taşıyor.
   - En kârlı 10 ay çıkarılınca bile %133.
   - Geriye bakan en kötü coin çıkarmada bile her yıl pozitif.

---

## Demo sürecinde ölçülmesi gereken metrikler

Her biri için backtest referansı ve sapma kontrolü verildi. Bunlar **izleme** metrikleri; otomatik kapı değil.

| Alan | Metrik | Referans / neden |
|---|---|---|
| İcra | TP / kademe limiti: dokunma sayısı, tam dolum, kısmi dolum, dolum süresi | E'deki p varsayımını gerçek veriyle değiştirmek. ≥%90 güvenli, ≤%80 alarm |
| İcra | Giriş / çıkış başına gerçekleşen kayma (mark'a göre bp), maker / taker payı, gerçek komisyon | Baz KOM 5 bp; 691'de +20 bp = −5,8 puan |
| İcra | Dolan TP'den sonraki 1-6 barda fiyatın yönü | Ters seçilim (E'de UNKNOWN) |
| İcra | Genç coinlerde (< 180 g) emir anı spread'i | 694 / 695'te ölçülemedi |
| Evren | Ayda yeni listelenen USDT perp sayısı (TradFi hariç) | 2024-26 ~160 / yıl; −%50 ise CAGR ~%105 |
| Evren | Sermayenin < 1 yaş coinlerdeki payı ve kâr payı | Baz: maruziyet ~%37, kâr ~%78 |
| Yoğunlaşma | Kâr payı: en büyük 1 / 3 coin; etkin coin sayısı | Tek coin > yarı kâr G'deki kırılganlık işareti |
| Kitap | Brüt maruziyet, net maruziyet, aynı gün coin sayısı | Brüt ort 0,72 (maks 0,96), net ort +0,04, coin ~13 |
| Kitap | Kitap ↔ BTC 30 günlük korelasyonu ve betası | Baz +0,02 / +0,013 |
| Kitap | En büyük 3 short'un toplam ağırlığı | F'deki tek gün −%21-26 senaryosunun canlı karşılığı |
| Getiri | Funding gelirinin backtest ile aynı günlerdeki farkı; işaret dönüşleri | 690: funding en istikrarlı bileşen |
| Getiri | Günlük PnL vs aynı günün backtest replay'i (takip farkı) | Model riskini doğrudan ölçer |
| Risk | En kötü gün, en kötü ay, DD | Baz −%7,4 / −%6,6 / −%13,3; bootstrap DD p5 −%17 |
| Teminat | Hesap teminat oranı, bakım teminatı, izole pozisyonlarda tasfiyeye uzaklık | Tasfiye riski F'de yok ama canlıda doğrulanmalı |
| Operasyon | API hatası, kaçan rebalance, gecikmeli emir sayısı | Backtest'te sıfır varsayılıyor |

---

## Sınırlar
- Kısmi dolum, emir defteri derinliği, spread ve ters seçilim için veri yok; E ve F'deki bu kısımlar varsayım.
- Parametre etkileşimleri (çok boyutlu tarama) yapılmadı; optimum aranmadığı için bilerek.
- Bootstrap rejim değişimini üretemez; walk-forward bağımsız OOS değil.
- Delist geçmişinin veri setinde eksiksiz olduğu doğrulanamadı (694 ile aynı) [VARSAYIM].
- 2026 yılı 9 aylık; yıllık %'ler o yıl için kısmi dönem getirisi.
