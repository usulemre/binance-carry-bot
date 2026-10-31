# Araştırma 692 — Sıçrama fırsatı kaybı ve pozisyon taşıma dayanıklılığı (1 Kasım 2026)

Ana strateji kodu, parametreler, backtest motorunun orijinal dosyaları ve canlı sistem DEĞİŞMEDİ. Hiçbir gösterge canlıya bağlanmadı.
Optimizasyon yapılmadı.
- Araç: `arastirma_m692_sicrama.py` (ayrı betik).
- Sentetik testler motorun kopyasıyla yapıldı (`/tmp/g33_m692.py`).
- **Parite:** düğmeler kapalıyken kopya iki hizada da `g33.py` referansıyla **bayt bayt aynı**.
- **Koşular:** 14 koşunun hepsi rc 0 ile bitti, tek işçiyle çalıştı. Bellek nedeniyle sonlanan koşu yok.
- **Çıktı kontrolü:** beklenen 28 dosyanın hepsi var.
- **Git:** `git diff` strateji ve motor dosyalarında değişiklik göstermiyor. Yalnız yeni betik ve bu rapor eklendi.

Etiketler: **ÖLÇÜM** doğrudan veriden · **VARSAYIM** model veya senaryo varsayımına dayanan · **HİPOTEZ** doğrulanmamış açıklama.

**Ortak veri:**
- Önerilen ayar P3T2 (T7K + koşullu stop), 2.000 $, 1,0x, gerçekçi model; iki hiza ortalaması; Temmuz 2020 – Eylül 2026.
- Madde 690 bacak defteri (305.691 dilim bacağı) ve günlük bileşenler; madde 691 seviye kayıtlı çıkış defteri; 4 saatlik OHLC.
- **Pozisyon tanımı:** bir coinin bir hizada aynı yönde kesintisiz tutulduğu dönem (TEK_GIRIS'te borsa hesabındaki tek pozisyon). Dilim
  bacaklarının birleşiminden 16.619 pozisyon çıktı.
- Puan = özkaynak oranı × 100, bileşik değil. CAGR = yıllık bileşik getiri.

---

## 0. Temel hipotez yanlışlanabilir miydi? Kısmen yanlışlandı

Hipotez: "Ana kâr kaynağı TP; asıl kırılganlık, TP fırsatının uzun süre gelmemesi."

En sert yanlışlama testi, TP ve kademeyi tamamen kapatmak (motor kopyası, `TP_YOK=1`). Stop, funding, seçim ve dilim yenilemesi aynen
kalıyor.

| | Baz | TP / kademe hiç yok |
|---|---|---|
| CAGR | %247 | **%203** |
| Toplam puan | 804 | 753 |
| Sharpe | 4,14 | 2,53 |
| Maks DD | −13,3 | −23,2 |
| Günlük oynaklık | 164 bp | 252 bp |

**[ÖLÇÜM; senaryo VARSAYIM]**
- TP olmadan da strateji yüksek kârlı.
- Madde 690'da "TP bileşeni" denen 717 puan, sıçrama barındaki fiyat hareketi. Bu hareketin büyük kısmını pozisyonu tutan kitap TP
  olmadan da kazanıyor.
- **TP mekanizmasının kendi katkısı:** +45 CAGR puanı, Sharpe +1,6, maks DD 10 puan daha az. Yani TP'nin asıl işi kârın kaynağı olmak
  değil, **kazancı kilitleyip riski yarıya indirmek.**

**Fitil testi (TP_KIRP)** başka bir şey gösteriyor. TP kontrolünde barın fitili kırpıldı; fiyat yolu ve tutuş P&L'i aynen kaldı.
- Fitil %50 kırpılınca CAGR **%170**, fitil hiç olmayınca **%135**.
- İkisi de **TP'nin tamamen kapalı olduğu durumdan (%203) KÖTÜ.**
- [HİPOTEZ] TP'nin değeri tamamen bar içi fitillerden (sıçrayıp geri dönen fiyattan) geliyor. Fitil yokken TP yalnız gövdesiyle seviyeyi
  geçen, yani süren hareketlerde satış yapıyor ve devamını kaçırıyor; o durumda TP zarar veriyor.

**Yeniden tanımlanan kırılganlık [HİPOTEZ]:** TP fırsatının gecikmesi, kitabı "TP'siz strateji" profiline indiriyor: getiri −%18, risk ×1,6.
Asıl tehlike, sıçramaların **fitil karakterini kaybetmesi.** Sıçrayıp dönen hareketler yerine kalıcı trendler gelirse TP mekanizması
nötr değil, zararlı hale gelir.

## 1. TP'ye ulaşma süresi

**Yöntem:**
- Potansiyel dokunuş: giriş barının kapanışına göre fiyat yolunda ilk kez +%45 / +%60 (long) ya da −%15 / −%20 (short) seviyesine
  dokunma; çıkıştan bağımsız, 14 güne kadar.
- Gerçekleşen: seviye kayıtlı defterde ilk TP / kademe olayı.

**[ÖLÇÜM] Pozisyonlar:**
- Süre medyan 5,0 gün · ortalama 5,7 · %90 dilimi 10,7 · maks 153,7.
- TP / kademe gerçekleşen pozisyon %14,8.
- Long: 7.366 pozisyon, süre medyan 6,0 gün, %11,5'inde TP, ilk olay medyan 3,2 günde.
- Short: 9.253 pozisyon, süre medyan 2,3 gün, %17,4'ünde TP, ilk olay medyan 1,5 günde.

| Gün | Hâlâ açık | 1. seviyeye dokundu (potansiyel) | 2. seviyeye dokundu (potansiyel) | TP / kademe gerçekleşti | Gerçekleşen olayların bu güne kadarki payı |
|---|---|---|---|---|---|
| 1 | %98,2 | %5,1 | %2,6 | %4,9 | %33,0 |
| 3 | %62,4 | %13,2 | %8,0 | %10,1 | %68,4 |
| 5 | %40,9 | %19,5 | %12,4 | %12,3 | %82,9 |
| 7 | %20,2 | %24,6 | %16,5 | %13,4 | **%90,7** |
| 10 | %11,1 | %30,2 | %21,4 | %14,1 | %94,8 |
| 14 | %5,7 | %35,9 | %26,5 | %14,4 | **%97,4** |

- TP'si gerçekleşen pozisyonlarda ilk olay 7 günden sonra olan pay %9,3; 14 günden sonra %2,6.
- **TP ya ilk günlerde gelir ya hiç gelmez:** pozisyonlar zaten 5-10 günde kapanıyor.

**[ÖLÇÜM] TP'ye ulaşamayan pozisyonlar** (puan, iki hiza ortalaması):

| | Pozisyon | Gerçekleşen fiyat | Funding | Net | Sermaye kullanımı (ağırlık-gün) | Açıkken en kötü kapanış (medyan / %10) |
|---|---|---|---|---|---|---|
| TP'siz | 14.157 (%85) | **−628** | +142 | **−486** | **%78** | −%6,8 / −%24,5 |
| TP'li | 2.462 (%15) | +1.245 | +113 | +1.358 | %22 | −%3,0 / −%24,4 |

- TP'siz long: fiyat −384, funding +116, net −269, sermayenin %41'i.
- TP'siz short: fiyat −244, funding +26, net −218, sermayenin %37'si.
- **Süre grupları** (`/tmp/m692/sure_grup.csv`): TP'siz pozisyonların zararı en çok 1-3 gün (−131) ve 5-7 gün (−186) gruplarında.
  14 günden uzun TP'siz pozisyonlar ise **net pozitif** (+71); burada funding (+58) fiyatı geçiyor.

**Sınırlamalar:**
- Potansiyel dokunuş ilk girişin kapanış fiyatına göre; motor referansı dilimlerin ortalama girişi.
- "Açıkken en kötü" 4 saatlik kapanışlarla ölçüldü (bar içi daha kötü olabilir).

## 2. Sıçramasız dönemler

### 2a. Gerçek tarih [ÖLÇÜM]
**Yöntem:** Kitabın tuttuğu coinlerin 30 günlük gerçekleşen oynaklığı (madde 691 kitap_vol) pencere ortalamasına göre tercillere ayrıldı;
değerler pencere başına medyan.

| Pencere / tercil | TP puan | TP olayı | Funding | Tutuş fiyatı | Getiri | Ort. pozisyon yaşı | 7 g'den yaşlı pay | Günlük oynaklık | En kötü gün | Zararlı pencere |
|---|---|---|---|---|---|---|---|---|---|---|
| 30 g düşük | 4,8 | 129 | 1,4 | +0,3 | 5,6 | 8,3 g | %37 | 129 bp | −2,3 | **%16,5** |
| 30 g orta | 7,2 | 264 | 1,7 | −1,2 | 7,4 | 7,2 g | %33 | 133 bp | −2,5 | %16,1 |
| 30 g yüksek | 14,8 | 433 | 3,7 | −4,6 | 13,6 | 6,3 g | %28 | 173 bp | −3,2 | %7,5 |
| 60 g düşük | 10,2 | 294 | 3,1 | +0,9 | 12,9 | 8,4 g | %37 | 134 bp | −2,7 | %6,3 |
| 60 g yüksek | 31,6 | 859 | 10,8 | −10,0 | 29,3 | 6,6 g | %29 | 193 bp | −3,7 | %0,7 |
| 90 g düşük | 16,9 | 435 | 5,2 | +1,0 | 20,8 | 8,2 g | %37 | 134 bp | −3,1 | %4,1 |
| 90 g yüksek | 46,9 | 1.316 | 18,0 | −14,1 | 43,7 | 6,5 g | %30 | 199 bp | −3,9 | %0,0 |

Soruların yanıtları (düşük oynaklık tercili, yüksek tercile göre):
- **TP işlem sayısı:** %65-70 azalıyor.
- **TP kârı:** %64-68 azalıyor.
- **Tutma süresi:** uzuyor; ortalama yaş 8,3 gün (6,3'e karşı), 7 günden yaşlı pay %37 (%28'e karşı).
- **Açık pozisyonlarda biriken zarar:** artmıyor. Tutuş fiyatı düşük oynaklıkta pozitif (+0,3 ile +1,0); yüksek oynaklıkta −4,6 ile −14,1.
- **Funding:** düşük oynaklıkta telafi edecek tutuş kaybı yok. Orta ve yüksek oynaklıkta tutuş kaybının %58-144'ünü karşılıyor.
- **Getiri:** 30 günlük getiri yarıdan aşağı iniyor (5,6'ya karşı 13,6); zararlı pencere oranı iki katına çıkıyor (%16,5'e karşı %7,5).
  Günlük oynaklık ve en kötü gün DAHA hafif.
- **Düşük oynaklıkta başlayan pozisyonlar:** TP oranı %11,4 (yüksekte %19,3), ilk olay 2,2 günde (1,7'ye karşı), işlem başı net 9,2 bp
  (13,4'e karşı), açıkken en kötü kapanış −%5,1 (−%7,7'ye karşı).

### 2b. Sentetik stres (motor kopyası; tam bileşik backtest) [ÖLÇÜM; senaryo VARSAYIM]
| Senaryo | CAGR | Fark | Sharpe | Maks DD | Günlük oynaklık | Aylık ort. | Zarar ayı | En kötü ay |
|---|---|---|---|---|---|---|---|---|
| Baz (model) | %247,5 | — | 4,14 | −13,3 | 164 bp | 10,7 | %12 | −6,4 |
| F50: fitil %50 kırpık | %169,9 | −77,6 | 3,31 | −18,0 | 165 bp | 8,6 | %20 | −10,0 |
| F0: fitil yok (yalnız gövde) | %134,9 | −112,6 | 2,88 | −19,0 | 164 bp | 7,5 | %23 | −12,1 |
| YOK: TP / kademe hiç yok | %202,9 | −44,6 | 2,53 | −23,2 | 252 bp | 10,0 | %23 | −6,9 |
| G3: TP 3 gün gecikmeli | %223,0 | −24,5 | 3,20 | −16,8 | 204 bp | 10,3 | %20 | −6,6 |
| G7: TP 7 gün gecikmeli | %208,8 | −38,7 | 2,66 | −21,0 | 240 bp | 10,1 | %21 | −6,6 |
| G14: TP 14 gün gecikmeli | %197,7 | −49,7 | 2,52 | −22,7 | 248 bp | 9,9 | %23 | −6,9 |

**Yıl yıl getiri (%):**

| Yıl | Baz | F50 | F0 | YOK | G3 | G7 | G14 |
|---|---|---|---|---|---|---|---|
| 2020 | 92 | 77 | 73 | 71 | 83 | 75 | 71 |
| 2021 | 472 | 304 | 223 | 320 | 307 | 278 | 268 |
| 2022 | 63 | 47 | 38 | 75 | 76 | 78 | 72 |
| 2023 | 310 | 244 | 213 | 191 | 245 | 209 | 206 |
| 2024 | 118 | 79 | 63 | 95 | 88 | 90 | 95 |
| 2025 | 267 | 193 | 150 | 330 | 347 | 384 | 337 |
| 2026 | 283 | 150 | 103 | 216 | 278 | 226 | 207 |

- **Hiçbir senaryoda negatif yıl yok.**
- TP olmadan 2022 ve 2025 DAHA iyi: o yıllarda TP, süren yükselişleri erken kesti.

**Senaryo tanımları ve sınırları [VARSAYIM]:**
- **F:** Yalnız TP / kademe kontrolünde fitil kırpılır; fiyat yolu, stoplar ve tutuş P&L'i gerçek kalır. "Fitilleri kısa bir dünya"nın
  hasat tarafını modeller. Gerçekte kapanışlar da değişirdi.
- **G:** Gecikme dilim yaşı ile sayılır. Fırsat gecikince seviye hâlâ geçiliyorsa ilk izinli barda dolar; geçilmiyorsa kaybolur.

## 3. TP fırsatı gelmeyen pozisyonların sermaye maliyeti

**[ÖLÇÜM]**
- TP'siz pozisyon süresi ortalama 5,5 gün, %95 dilimi 14,0 gün, maks 153,7 gün. TP'lilerde ortalama 6,4 gün.
- **Bağlı sermaye:** TP'siz pozisyonlarda toplam 1.293 özkaynak-gün (yılda ~209); bütün pozisyon sermayesinin **%78**'i.
- **Bu sermayenin getirisi:** yılda **−%137**. TP'li pozisyonlarda yılda +%1.344.
- **Brüt maruziyet:** ortalama 0,72 özkaynak (%5 dilimi 0,55, %95 dilimi 0,87); 7 günden yaşlı pozisyonların payıyla korelasyonu +0,14.
- **Yaş dağılımı:** açık ağırlığın ortalama %33'ü 7 günden, %15'i 14 günden yaşlı (%95 dilimi %54).
- **Coin yoğunlaşması:** ilk 5 coin brütün ortalama %50'si (%95 dilimi %61), ilk 10 coin %77'si.
- **Sektör yoğunlaşması:** ölçülemedi; depoda coin → sektör eşlemesi yok.
- **Uzayan pozisyonlar ve yeni girişler:**
  - 7 günden yaşlı pozisyonların payı arttıkça sonraki 5 günde açılan yeni pozisyon sayısı azalıyor (korelasyon −0,30); aynı günkü coin
    sayısıyla korelasyon −0,52.
  - 7 günden uzun pozisyonlar yeniden seçilerek uzuyor (bacak sayısı medyanı 39). Motor dilim yenilemesinde kapasiteyi kilitlemiyor;
    uzun pozisyon, seçim kuralı coini hâlâ seçtiği için sürüyor.

**Ölçülemeyen [VARSAYIM / HİPOTEZ]:**
- "Aynı sermayeyle kaçırılan fırsat" doğrudan ölçülemez: karşı-olgusal seçim gerekir.
- −0,30 korelasyonu eşzamanlı bir ilişki. Yaşlı pozisyonların yeni girişi engellediğini mi, yoksa aynı rejimde ikisinin birlikte mi
  oluştuğunu ayırt etmiyor.
- −%137 yıllık rakam, sonradan (TP'siz olarak) seçilmiş pozisyonların getirisi. Bu pozisyonların önceden bilinebileceği anlamına gelmez:
  her pozisyon açılırken TP şansı taşıyor.

## 4. Yıldız coinlerin kaybolması (gelecek bilgisi yok)

**Yöntem:**
- 2021-02'den itibaren her ay başında, yalnız o güne kadarki 180 ya da 365 günlük veriyle TP'ye veya net katkıya göre ilk N coin
  "yıldız" seçildi. O ay boyunca bu coinlerin günlük net katkısı seriden düşüldü (statik; madde 691'de statik ≈ motor).
- Evrene yeni giren ve evrenden çıkan coinler kendiliğinden hesaba katılıyor: seçim yalnız geçmişte işlem görmüş coinlerden.
- **Rastgele taban:** her ay geçmiş 180 günde işlem görmüş coinlerden rastgele N coin çıkarıldı; 200 tekrar.

**[ÖLÇÜM]** Baz (2021-02 sonrası): CAGR %228,9 · Sharpe 3,95 · maks DD −13,3.

| Geçmiş penceresi | Ölçüt | N=1 | N=3 | N=5 | N=10 |
|---|---|---|---|---|---|
| 180 g | TP | %225,0 | %207,6 | %182,4 | %176,1 |
| 180 g | net | %217,1 | %201,7 | %200,9 | %169,7 |
| 365 g | TP | %218,6 | %213,5 | %206,8 | %196,7 |
| 365 g | net | %217,0 | %191,7 | %184,6 | %181,3 |

- **Rastgele çıkarmaya karşı (180 g, TP ölçütü):**
  - Rastgele 5 coin: CAGR medyan %217,9 [%5 dilimi %200,6 – %95 dilimi %230,4]; yıldız 5 coin %182,4 → rastgeleden kötü (200 tekrarın
    hiçbiri bu kadar kötü değil).
  - Rastgele 10 coin: medyan %205,4 [%187,1 – %224,9]; yıldız 10 coin %176,1 → olasılık %1.
- **TP sırası kalıcı değil:**
  - Geçmiş 180 günün TP ilk 10'u sonraki ayın TP'sinin %13'ünü, sonraki çeyreğin %11'ini veriyor. Rastgele 10 coinin beklenen payı
    yaklaşık %18.
  - Sıra korelasyonu (çeyrek) +0,15. Sonraki çeyreğin TP ilk 10'unun ortalama yalnız 2,1'i geçmiş ilk 20'deydi.
- **Genç coinler:** 365 günden genç coinler 2024'te TP'nin %61'ini, 2025'te %69'unu, 2026'da %64'ünü; net kârın %60 / %91 / %81'ini
  verdi. 2022-23'te bu pay düşüktü (TP'nin %17-24'ü).

**Yorum:**
- [ÖLÇÜM] Yıldızlar dönüyor: geçmiş TP yıldızları sonraki ayın TP'sini rastgele bir 10 coinden fazla vermiyor. Sistemin kârı her dönem
  yeni coinlerden geliyor; son üç yılda çoğunlukla 1 yaşından genç coinlerden.
- [ÖLÇÜM] Ama "şu anki" yıldızlar o ay ortalamanın üstünde net katkı vermeye devam ediyor (rastgele çıkarmadan kötü). Bu katkı TP'den
  değil, tutuş ve funding toplamından geliyor.
- [HİPOTEZ] Kâr, yeni listelenen coinlerin akışına bağlı. Binance'in yeni vadeli listelemeleri azalırsa ya da genç coinlerin davranışı
  değişirse, bu yalnız backtestte yaşanmamış bir risk olur.

## 5. Erken uyarı göstergesi araştırması

**Yöntem:**
- **Hedef:** sonraki 30 gün kitap getirisi < 0.
- **Göstergeler** (yalnız o güne kadar bilinenler):
  - 30 / 60 / 90 günlük TP;
  - kitap oynaklığı;
  - son 30 günde gerçekleşen TP olaylarının pozisyon yaşı (TP'ye ulaşma süresi);
  - son 30 günde kapanan pozisyonlarda TP'siz oranı;
  - açık pozisyon yaşı (ortalama, 7 günden yaşlı pay);
  - 30 günlük funding;
  - ilk 5 ve 10 coinin brüt payı.
- **Model:** her göstergeye tek değişkenli lojistik regresyon, artı hepsiyle birlikte bir model.
- **Kronolojik ayrım:** eğitim 2020-11 – 2023-05 (hedef penceresi eğitim sınırını aşmasın diye 30 gün ambargo), test 2023-07-31 – 2026-08.
- **Alarm eşiği:** eğitimdeki risk tahminlerinin en yüksek %20'si; testte sabit tutuldu.
- **Anlamlılık:** dairesel kaydırma (hedef en az 45 gün kaydırıldı, 2.000 tekrar).
- **Rastgele taban:** AUC 0,50; testte her gün alarm vermek %10,9 isabet (yanlış alarm %89,1) ve lift 1,0 verir.

**[ÖLÇÜM]** Test kötü oranı %10,9; bağımsız 30 günlük blok sayısı yaklaşık 32.

| Gösterge | AUC eğitim | AUC test | p | Alarm günü | İsabet | Yanlış alarm | Yakalama | Lift | Alarm sonrası 30 g |
|---|---|---|---|---|---|---|---|---|---|
| TP 30 g | 0,57 | 0,36 | 0,94 | %34 | %4,7 | %95 | %15 | 0,43 | +%15,7 |
| TP 60 g | 0,53 | 0,62 | 0,11 | %0,7 | %0 | %100 | %0 | 0 | +%5,9 |
| TP 90 g | 0,58 | 0,63 | 0,06 | %1,7 | %0 | %100 | %0 | 0 | +%12,8 |
| Funding 30 g | 0,59 | 0,69 | 0,08 | %6,0 | %3,4 | %97 | %2 | 0,31 | +%6,2 |
| Kitap oynaklığı | 0,54 | 0,64 | 0,10 | %13,5 | %7,5 | %93 | %9 | 0,68 | +%13,9 |
| TP'ye ulaşma süresi | 0,46 | 0,67 | 0,03 | %1,1 | %9,1 | %91 | %1 | 0,83 | +%3,5 |
| TP'siz oranı | 0,59 | 0,64 | 0,09 | %11,4 | %17,7 | %82 | %19 | 1,62 | +%7,4 |
| **Pozisyon yaşı (ort.)** | 0,55 | **0,69** | **<0,001** | %55 | %15,6 | %84 | %78 | 1,42 | +%9,4 |
| **7 g'den yaşlı pay** | 0,52 | 0,62 | **0,004** | %41 | %15,5 | %85 | %57 | 1,42 | +%9,3 |
| İlk 5 coin payı | 0,56 | 0,57 | 0,15 | %49 | %12,5 | %88 | %56 | 1,15 | +%10,4 |
| İlk 10 coin payı | 0,54 | 0,58 | 0,09 | %57 | %12,4 | %88 | %65 | 1,14 | +%10,7 |
| Hepsi (çok değişkenli) | **0,78** | 0,68 | 0,10 | %13 | %8,9 | %91 | %10 | 0,81 | +%7,3 |

Test dönemi ileri 30 günlük getirinin ortalaması +%11,8.

**Değerlendirme:**
- **[ÖLÇÜM] Çoklu test:** 12 test yapıldı; Bonferroni eşiği 0,0042. Yalnız pozisyon yaşı (p < 0,001) ve 7 günden yaşlı pay (p = 0,004)
  istatistik olarak geçiyor.
- **[ÖLÇÜM] İşaret hipotezin TERSİ.** Zarardan önce açık pozisyonlar DAHA GENÇ (test: kötü dönemde ortalama yaş 5,2 gün, iyi dönemde 6,3);
  eğitimde de aynı yön (8,2'ye karşı 8,9). "TP'siz pozisyonlar yaşlanıp birikirse zarar gelir" beklentisi desteklenmedi.
- **[ÖLÇÜM] Ekonomik değeri zayıf.**
  - Alarm günlerin %41-55'inde açık; isabet %15,5 (taban %10,9); yanlış alarm %84-85.
  - Alarm sonrası 30 günün getirisi yine +%9,3 (ortalama +%11,8).
  - Eğitimdeki ayırt edicilik çok düşük (AUC 0,52-0,55); test dönemindeki güç bir rejim kayması olabilir: ortalama yaş 8,9 günden
    6,3'e indi.
- **[ÖLÇÜM]** TP 30 günlük göstergesinin işareti eğitimle test arasında ters döndü (test AUC 0,36).
- **[ÖLÇÜM]** Çok değişkenli model aşırı uyuyor: eğitimde 0,78, testte 0,68; lift 0,81.
- **[ÖLÇÜM] Sınırlama:** Dairesel kaydırma örnekler arası bağımlılığı kısmen koruyor; 32 bağımsız blokla p değerleri iyimser olabilir.

## 6. Beş sorunun cevabı

**1. TP fırsatının 7-14 gün gecikmesi stratejiyi ne kadar etkiliyor?**
- [ÖLÇÜM] Gerçekleşen TP olaylarının %91'i ilk 7 günde, %97'si ilk 14 günde geliyor; pozisyonlar zaten 5-10 günde kapanıyor.
- [ÖLÇÜM; senaryo VARSAYIM] 7 günlük gecikme: CAGR %247 → %209, Sharpe 4,14 → 2,66, maks DD −13 → −21. 14 günlük gecikme: %198 /
  2,52 / −23.
- Bu fiilen "TP'siz strateji" (%203). Getiri %15-20 düşüyor, risk ~1,6 kat artıyor; hiçbir yıl negatife dönmüyor.

**2. Uzun süre düşük oynaklık strateji için gerçekten tehlikeli mi?**
- [ÖLÇÜM] Tehlikeli değil, **verimsiz.** Düşük oynaklıkta TP %65 düşüyor, getiri yarıya iniyor, zararlı 30 günlük pencere %16,5'e çıkıyor
  (%7,5'e karşı).
- Ama tutuş kaybı yok (pozitif), günlük oynaklık ve en kötü gün daha hafif; 90 günlük düşük oynaklık pencerelerinin yalnız %4'ü zararlı.
- [HİPOTEZ] Asıl tehlike düşük oynaklık değil, **fitilsiz yükselişler**: sentetik fitilsiz dünyada CAGR %135, TP'siz durumdan bile kötü.

**3. Funding, TP fırsatı gelmeyen dönemlerde yeterli koruma sağlıyor mu?**
- [ÖLÇÜM] Pozisyon düzeyinde **hayır.** TP'siz pozisyonlarda funding +142 puan, fiyat kaybı −628 puan; kaybın yalnız %23'ü telafi ediliyor.
- 14 günden uzun TP'siz pozisyonlarda funding fiyatı geçiyor (+71 net).
- Kitap düzeyinde: düşük oynaklık dönemlerinde tutuş zaten pozitif. Orta ve yüksek oynaklıkta funding tutuş kaybının %58-144'ünü karşılıyor.
- TP tamamen kapalıyken kitabın %203 CAGR'si funding'den değil, tutulan pozisyonların fiyat hareketinden geliyor.

**4. Gelecekteki yıldız coinler değişirse sistem yeni coinlerde aynı avantajı bulabiliyor mu?**
- [ÖLÇÜM] Evet, tarihsel olarak buldu.
  - TP yıldızları kalıcı değil (sıra korelasyonu +0,15; geçmiş ilk 10, sonraki ayın TP'sini rastgele 10 coinden fazla vermiyor).
  - Kârın çoğu her dönem yeni coinlerden geliyor (2024-26'da TP'nin %61-69'u 1 yaşından genç coinlerden).
- Geçmiş bilgiyle her ay "şu anki" ilk 10 yıldız çıkarılsa bile CAGR %176-197 (baz %229).
- [HİPOTEZ] Bu avantaj yeni listeleme akışına bağlı; akış kurursa ya da değişirse backtestte olmayan bir risk doğar.

**5. Göstergelerden biri sonraki 30 günlük zararı rastgele tahminden daha iyi öngörebiliyor mu?**
- [ÖLÇÜM] Kullanışlı biçimde **hayır.** Yalnız açık pozisyon yaşı istatistik olarak geçiyor (test AUC 0,62-0,69, lift 1,4).
- İşareti hipotezin tersi (genç kitap → zarar), eğitimde neredeyse güçsüz, alarm günlerin yarısında açık, yanlış alarm %84, alarm sonrası
  getiri yine +%9.
- TP, oynaklık, funding ve yoğunlaşma göstergeleri rastgeleden ayırt edilemiyor.
- **Kapı önerilmez.** Pozisyon yaşı yalnız izleme amaçlı ve yeni veriyle yeniden sınanmalı.

---
### Yeniden üretim
```bash
python3 arastirma_m692_sicrama.py kos       # parite (2) + 6 senaryo × 2 hiza, tek işçi (~30 dk)
python3 arastirma_m692_sicrama.py analiz    # -> /tmp/m692/*.csv + ekran raporu (~20 dk; rastgele taban dahil)
```
Önkoşul: madde 690 (`kos`, `analiz`) ve madde 691 (`kos_seviye`, `analiz`) çıktıları.
