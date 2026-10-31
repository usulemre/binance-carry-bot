# Araştırma 691 — TP motoru dayanıklılık ve kırılganlık analizi (1 Kasım 2026)

Ana strateji kodu, parametreler ve canlı sistem DEĞİŞMEDİ. Canlıya gösterge ya da kapı eklenmedi. Optimizasyon yapılmadı.

Araç: `arastirma_m691_tp_motoru.py` (ayrı betik).
- Stres koşuları motorun kopyalarıyla yapıldı (`/tmp/g33_m691.py`, `/tmp/g33_m691s.py`).
- Düğmeler kapalıyken iki kopyanın E dosyası da `g33.py` ile **bayt bayt aynı** (3 parite kontrolü).

Etiketler: **[ölçüm]** veriden hesaplandı · **[varsayım]** kanıtlanamayan girdi · **[hipotez]** test edilmemiş yorum.

**Ortak veri ve dönem:**
- Önerilen ayar P3T2 (T7K + koşullu stop), 2.000 $, 1,0x, gerçekçi model (TEK_GIRIS, KOM %0,05, MERD_SIRA).
- İki hiza ortalaması; Temmuz 2020 – Eylül 2026.
- Kaynaklar: madde 690 bileşen defterleri (`/tmp/m690`), 4 saatlik OHLC (`/tmp/zemin.pkl`, `/tmp/hlo.pkl`), seviye kayıtlı çıkış defteri
  (`/tmp/m691/cikis_S_*.pkl`).
- 21.933 TP / kademe olayı (iki hiza toplamı): TP 9.602, kademe 12.331.

**Birimler:**
- Puan = özkaynak oranı × 100, bileşik değil.
- CAGR = yıllık bileşik getiri.
- "İşlem getirisi" = çıkış fiyatı / referans giriş (TEK_GIRIS ortalama girişi) − 1.

> **Madde 690'a not:** 690'ın TP bileşeninde, seviyesi olmayan çıkışların (ör. azami tutma süresi) yanlışlıkla "TP" sayılmış olabileceği
> şüphesi vardı. Kontrol edildi: motorun kaydettiği limit seviyesiyle bakıldığında **TP / kademe etiketli bütün olayların seviyesi var
> (0 istisna)**. 690'ın TP bileşeni (717 puan) doğru.
>
> Bu çalışmanın ilk denemesinde "olayların %26'sı seviyeyi < 5 bp geçti" sonucu çıkmıştı. O sonuç yanlış referanstan geliyordu: dilimin
> kendi girişi kullanılmıştı, motor ise coinin bütün dilimlerdeki ortalama girişini kullanıyor. Düzeltilmiş değerler §2'de.

---

## 1. TP ve oynaklık ilişkisi

**Veri ve yöntem:**
- Günlük TP bileşeni (madde 690), örtüşmeyen 74 takvim ayı ve 30 / 60 / 90 günlük hareketli toplamlar.
- Dört oynaklık ölçüsü (30 günlük gerçekleşen, yıllık %):
  - **kitap_vol:** kitabın tuttuğu coinlerin |ağırlık| ağırlıklı ortalaması;
  - **evren_vol:** bütün coinlerin medyanı;
  - **btc_vol:** BTC;
  - **bar aralığı:** evrenin 4 saatlik (yüksek / düşük − 1) medyanı.
- Terciller aylar üzerinden; esneklik log TP ile log kitap_vol arasındaki doğrusal eğim.

| Ölçü (aylık) | Korelasyon: TP | Korelasyon: TP sayısı | Korelasyon: getiri |
|---|---|---|---|
| kitap_vol | **+0,69** | **+0,77** | +0,22 |
| evren_vol | +0,18 | +0,50 | +0,03 |
| btc_vol | +0,11 | +0,32 | +0,14 |
| bar aralığı | +0,30 | +0,62 | +0,16 |

Hareketli pencerede TP ile kitap_vol korelasyonu: 30 g +0,64 · 60 g +0,73 · 90 g +0,75 [ölçüm].

**Kitap oynaklığı tercilleri (aylık ortalama) [ölçüm]:**

| Tercil | Ay | Oynaklık | TP puan / ay | TP olayı / ay | Ort. işlem getirisi | İşlem başı katkı | Funding | Tutuş fiyatı | Getiri | Zarar ayı |
|---|---|---|---|---|---|---|---|---|---|---|
| düşük | 25 | %104 | 5,0 | 142 | %27,7 | 7,7 bp | 2,4 | +1,1 | 8,0 | %12 |
| orta | 24 | %140 | 7,7 | 274 | %27,2 | 7,3 bp | 2,6 | +0,3 | 9,8 | %17 |
| yüksek | 25 | %182 | 16,2 | 470 | %27,4 | 7,3 bp | 5,4 | −5,9 | 14,6 | %8 |

**Sonuç [ölçüm]:**
- Esneklik: TP katkısı **+1,89**, TP sayısı +2,25. Kitap oynaklığı %10 düşerse TP yaklaşık **%18** azalıyor.
- En düşük oynaklık çeyreğindeki aylarda (n = 19) TP 5,3 / ay; medyan bantta 7,6 (**−%30**). Toplam getiri ise 10,1'e karşı 9,8,
  yani düşmüyor.
- **Oynaklık TP'nin sayısını belirliyor, kalitesini değil.** İşlem başı katkı ve ortalama işlem getirisi tercillerde neredeyse sabit:
  7,3-7,7 bp ve %27.
- Düşük oynaklıkta tutuş fiyatı daha az kaybettiriyor (+1,1'e karşı yüksek tercilde −5,9). Kitap getirisi bu yüzden oynaklıktan çok
  daha az etkileniyor (korelasyon +0,22).
- Piyasa geneli ve BTC oynaklığı TP'yi açıklamıyor. Belirleyici olan, kitabın SEÇTİĞİ coinlerin oynaklığı.

**Varsayımlar ve sınırlamalar:**
- kitap_vol aynı günün ağırlıklarıyla hesaplandı: eşzamanlı bir ilişki, öngörü değil.
- 74 ay küçük örnek; terciller arası farkların güven aralığı geniş.
- Seçim kuralı yüksek oynaklıklı coinleri tercih ettiği için kitap_vol stratejinin kendi çıktısı.

## 2. TP gerçekleşme kalitesi

**Gerçek dolum verisi YOK.** Bot hiç canlı işlem yapmadı. Maker dolum oranı, kısmi dolum ve emir bekleme süresi **ölçülemedi**.
- Canlı kod TP ve kademeyi pozisyon açılınca borsaya GTC reduceOnly LIMIT emir olarak koyar (`carry_bot.py` kâr al kurulumu).
- Madde 267 bu varsayımı daha önce dakika verisiyle sınamıştı: gerçek TP vakasında seviyenin ötesinde ilk saatte medyan 15,3 M$ hacim
  geçiyor, fiyat orada medyan 30 dakika kalıyor; 10-100 bin $ bakiyede ıska %0-0,5.
- Bu çalışma onu tekrarlamadı; mevcut ayar için 4 saatlik bar ölçüsü ve stres testi ekledi.

### 2a. Model dolum fiyatı ile seviye arasındaki fark (4 saatlik bar) [ölçüm]
**Yöntem:**
- Motorun kaydettiği limit seviyesi kullanıldı.
- Delme = barın yükseği / max(seviye, açılış) − 1 (short için simetriği): fiyatın seviyenin ne kadar ötesine geçtiği.

**Sonuç:**
- Olayların %2,7'sinde seviye bar açılışında zaten geçilmişti. Model bu durumda açılış fiyatından dolduruyor, yani seviyeden daha iyi
  fiyattan (canlıda limit de öyle dolar).
- Model dolumu seviyeye göre medyan 0 bp, ortalama 169 bp daha iyi (boşluk açılışları yüzünden).

| Seviyeyi şundan az geçen olay | Olay payı | Katkı payı |
|---|---|---|
| < 5 bp | %1,2 | %1,1 |
| < 10 bp | %2,4 | %2,1 |
| < 20 bp | %4,7 | %3,5 |
| < 50 bp | %10,7 | %8,0 |
| < 100 bp | %21,3 | %17,5 |

Delme medyanı **290 bp** (%10 dilimi 47 bp, %25 dilimi 118 bp). Seviyeye "değip dönen" kenar vakaların payı küçük.

**Sınırlama:** 4 saatlik bar fiyatın seviyenin ötesinde ne kadar KALDIĞINI göstermez; bunun için dakika verisi gerekir (madde 267).

### 2b. Ek maliyet ve dolum stresi (motor kopyası, tam bileşik backtest) [ölçüm; senaryo girdisi varsayım]
**Senaryolar:**
- **K** (ek icra maliyeti): TP / kademe dolum fiyatı x bp kötüleşir.
- **D** (dokunma iyimserliği): limit, fiyat seviyeyi x bp geçmedikçe dolmaz; o bar değip dönerse pozisyon açık kalır.

| Senaryo | CAGR | Fark | Sharpe | Maks DD | Toplam puan | Fark |
|---|---|---|---|---|---|---|
| Baz (model) | %247,5 | — | 4,14 | −13,3 | 803,7 | — |
| K5: dolum 5 bp kötü | %246,0 | −1,4 | 4,13 | −13,3 | 801,1 | −2,6 |
| K10: 10 bp | %244,5 | −3,0 | 4,12 | −13,3 | 798,3 | −5,4 |
| K15: 15 bp | %243,0 | −4,5 | 4,10 | −13,3 | 795,5 | −8,2 |
| K20: 20 bp | %241,7 | −5,8 | 4,09 | −13,4 | 793,1 | −10,6 |
| D5: 5 bp delinmeden dolmaz | %245,9 | −1,5 | 4,13 | −13,3 | 800,9 | −2,8 |
| D10: 10 bp | %244,7 | −2,7 | 4,12 | −13,3 | 798,8 | −4,9 |
| D20: 20 bp | %243,3 | −4,1 | 4,10 | −13,3 | 796,2 | −7,5 |

- **Analitik kontrol:** TP / kademede işlem gören kitap ağırlığı toplam 55,6 (yılda ≈ 9 × özkaynak). 20 bp → −11,1 puan; motorun
  −10,6 puanıyla uyumlu.
- **Ne kadar TP kârı maliyete gidebilir? [ölçüm]**
  - TP olaylarının girişe göre katkısı 1.454 puan; 20 bp ek maliyet bunun **%0,8'i**.
  - Toplam kârın %1,3'ü. Her yıl hâlâ çok pozitif (yıl yıl tablo `/tmp/m691/stres_yillik.csv`).
- **Varsayım:** Senaryo büyüklükleri (5-20 bp) seçilmiş değerler, ölçülmüş kayma değil. Gerçek kayma ve ıska oranı ancak canlı / demo
  dolum kayıtlarıyla ölçülür.
- **Sınırlama:** Kapasite ayrı bir risk. Madde 267: 1 M$ bakiyede TP ıskası %5,5-7; bu çalışma 2.000 $ içindir.

## 3. Coin yoğunlaşması

**Veri ve yöntem:**
- Coin bazında TP bileşeni (madde 690) ve TP olay defteri (§2).
- Çıkarma iki yolla yapıldı:
  - **statik:** coinin günlük net katkısı seriden düşülür; yeri boş kalır;
  - **motor:** coin evrenden çıkarılır (yalnız SEMBOL_HARIC genişletildi); boşalan yer diğer coinlere gider.
- Çıkarılacak coinler 6 yıllık TP sıralamasına göre (geriye bakan / hindsight) seçildi.

**[ölçüm] TP yoğunlaşması:**
- 400 coin TP üretti; toplam 717 puan.

  | İlk N coin | TP payı | Net kâr payı |
  |---|---|---|
  | 1 | %2,1 | %−0,5 |
  | 3 | %6,0 | %8,3 |
  | 5 | %9,2 | %13,7 |
  | 10 | %15,9 | %22,8 |
  | 20 | %26,1 | %32,1 |

- Herfindahl 0,0066 → etkin coin sayısı **151**.
- **TP, net kâra göre daha az yoğun.**

**[ölçüm] En büyük TP coinleri:**

| Coin | TP olayı | TP puan | Ort. işlem getirisi | İşlem başı katkı | Net puan |
|---|---|---|---|---|---|
| BTW | 250 | 15,2 | %16,1 | 4,3 bp | **−4,1** |
| PIPPIN | 222 | 15,2 | %37,1 | 12,9 bp | 30,0 |
| TRB | 284 | 12,3 | %43,5 | 13,4 bp | 41,3 |
| SOL | 318 | 12,1 | %25,6 | 7,1 bp | 34,9 |
| DOGE | 287 | 11,1 | %28,3 | 6,9 bp | 8,5 |

İlk 20'nin tamamı: `/tmp/m691/coin_tp.csv`.

**[ölçüm] Çıkarma sonuçları:**

| Senaryo | Yöntem | CAGR | Sharpe | Maks DD | Toplam puan |
|---|---|---|---|---|---|
| Baz | — | %247,5 | 4,14 | −13,3 | 803,7 |
| İlk 1 (BTW) çıkar | statik / motor | %249,9 / %247,6 | 4,18 / 4,16 | −13,3 / −13,3 | 807,8 / 803,6 |
| İlk 3 (+PIPPIN, TRB) | statik / motor | %212,9 / %210,8 | 3,93 / 3,87 | −13,3 / −13,4 | 736,5 / 732,9 |
| İlk 5 (+SOL, DOGE) | statik / motor | %192,2 / %200,5 | 3,75 / 3,75 | −14,6 / −13,5 | 693,1 / 712,2 |

**Yıl yıl (motor, %):**
- İlk 3 coin yokken 2023'te getiri %310 → %166 (TRB'nin 2023'ü); 2025'te %267 → %200.
- İlk 5 yokken 2021'de %472 → %391.
- Hiçbir yıl negatife dönmüyor.

**Yorum:**
- [ölçüm] En büyük TP coini (BTW) net zararlı: TP'si yüksek ama tutuşta kaybettiriyor. TP'yi tek başına okumak yanıltıcı.
- [ölçüm] İlk 3-5 coin kaybı CAGR'yi 37-47 puan, Sharpe'ı 0,27-0,39 düşürüyor; maks DD değişmiyor.
- [hipotez] Kâr sağ kuyruklu: 2023 tek bir coinin (TRB) yılı. Gelecekte böyle 1-2 "yıldız" çıkmazsa yıllık getiri ölçülü biçimde düşer,
  sistem zarara geçmez.
- **Sınırlama:** Geriye bakan seçim en kötü durumu abartır. Önceden hangi coinin yıldız olacağı bilinmez.

## 4. TP başarısızlık dönemleri

**Veri ve yöntem:**
- Hareketli 30 / 60 / 90 günlük toplamlar; birbiriyle örtüşmeyen en düşük 5 TP penceresi.
- Aylık seride TP(t) ile getiri(t+k) arasında gecikmeli korelasyon.
- TP alt çeyrek aylarından sonraki getiri.
- Permütasyon testi (5.000 karıştırma).
- **Nedensellik iddiası yok.**

**[ölçüm] En düşük TP'li 30 günlük pencereler (puan):**
- Bütün pencerelerin medyanı: TP 7,3 · funding 1,8 · tutuş −1,4 · getiri 8,6 · TP olayı 258 · kitap_vol %141.

| Pencere | TP | Funding | Tutuş | Getiri | TP olayı | kitap_vol |
|---|---|---|---|---|---|---|
| 2022-09-20 – 10-19 | 0,0 | 1,2 | +3,8 | +4,7 | 0 | %93 |
| 2024-01-10 – 02-08 | 0,4 | 1,7 | −5,2 | −2,7 | 10 | %135 |
| 2022-01-25 – 02-23 | 0,5 | 1,1 | +1,8 | +2,4 | 56 | %123 |
| 2024-08-13 – 09-11 | 0,7 | 0,8 | −4,9 | −4,6 | 38 | %117 |
| 2022-12-02 – 12-31 | 0,7 | 2,9 | −0,7 | +2,1 | 23 | %101 |

**60 ve 90 günlük pencereler** (dosyalar `/tmp/m691/tp_dusuk_{30,60,90}g.csv`):
- En kötüsü 2022-06-24 – 08-22: TP 3,7 · tutuş −15,1 · getiri −10,9.
- 90 günlükte 2022-07-23 – 10-20: getiri −0,3.

**Ortak özellikler:**
- TP olay sayısı çok düşük (medyanın 0-%20'si).
- Kitap oynaklığı genelde medyanın altında (%93-135).
- Funding normal ya da biraz düşük.
- Getiri, tutuş fiyatının işaretine göre −5 ile +5 arası.

**[ölçüm] Zaman sıralaması (aylık):**

| Gecikme k (ay) | −2 | −1 | 0 | +1 | +2 | +3 |
|---|---|---|---|---|---|---|
| Korelasyon: TP(t) ile getiri(t+k) | +0,28 | +0,24 | **+0,53** | +0,23 | +0,22 | +0,08 |
| TP'nin kendi otokorelasyonu | +0,32 | +0,39 | 1 | +0,39 | +0,32 | +0,26 |

- **Aynı ay:** TP alt çeyrek aylarında getiri +3,9'a karşı diğer aylarda +13,2; zarar ayı oranı %21'e karşı %9.
- **Sonraki ay:** getiri +8,1'e karşı +11,8; zarar ayı oranı **%11'e karşı %13**.
  - Permütasyon farkı −2,4 puan, p = 0,73: **anlamlı ilişki yok.**
- 2 ve 3 ay sonrasında da fark yok (zarar ayı oranı %11 / %16'ya karşı %13 / %11).
- **Zarar aylarından önce TP:**
  - 9 zarar ayının 3'ünde TP önceki ay medyanın açıkça üstündeydi (bir ayda medyana eşit).
  - Düşük TP genelde zarar ayının KENDİSİNDE (2022-07: 1,1 · 2024-05: 1,6 · 2023-02: 2,5).

**Sonuç [ölçüm]:**
- Düşük TP ile zarar **aynı ayda** birlikte görülüyor.
- **TP düşüşü sonraki ayların kaybını önceden göstermiyor.**
- Aylık TP'nin otokorelasyonu 0,39: düşük TP'li bir ayı genelde ılımlı bir ay izliyor.

**Sınırlama:**
- Örtüşen pencereler bağımsız değil.
- 74 ay ve 9 zarar ayı küçük örnek.
- Permütasyon aylık otokorelasyonu korumuyor (blok karıştırma yapılmadı).

## 5. Özet

| Soru | Sonuç | Sınıf |
|---|---|---|
| TP oynaklığa ne kadar bağlı? | Kitabın tuttuğu coinlerin oynaklığına güçlü (r 0,69, esneklik 1,9); piyasa / BTC oynaklığına zayıf. Oynaklık TP'nin sayısını belirliyor; işlem başı kalitesi sabit (~7,5 bp, ~%27). | ölçüm |
| Oynaklık düşünce kitap ne yaşar? | En düşük oynaklık çeyreğinde TP −%30, ama toplam getiri değişmiyor (tutuş daha az kaybettiriyor). | ölçüm |
| İcra maliyeti TP'yi yer mi? | 20 bp ek maliyet veya 20 bp delme şartı → CAGR −4..−6 puan, toplam kârın ~%1'i. Gerçek dolum verisi yok. | ölçüm (senaryo girdisi varsayım) |
| Coin yoğunlaşması | TP etkin 151 coine yayılı; ilk 3 / 5 TP coini yokken CAGR %248 → %211 / %201, hiçbir yıl negatif değil. | ölçüm (geriye bakan seçim) |
| TP düşüşü kaybı önceden haber verir mi? | Hayır. Aynı ayda birlikte (zarar ayı %21'e karşı %9); sonraki ayda fark yok (p = 0,73). | ölçüm |
| TP motorunun asıl kırılganlığı | İcra değil; kitabın tuttuğu coinlerde uzun süre düşük oynaklık (sıçrama yok) ve birkaç yıldız coinin bulunmaması. | hipotez |

**Açık kalan [varsayım]:**
- Maker dolum oranı, kısmi dolum ve emir bekleme süresi ancak demo veya canlı dolum kayıtlarıyla ölçülebilir.
- `carry_gunluk_defter` / panel bu veriyi kaydedecek durumda; ilk canlı aydan sonra ölçülmeli.

---
### Yeniden üretim
```bash
python3 arastirma_m691_tp_motoru.py kos          # parite + 10 senaryo × 2 hiza (tek işçi, ~70 dk)
python3 arastirma_m691_tp_motoru.py kos_seviye   # seviye kayıtlı çıkış defteri (2 koşu, parite kontrollü)
python3 arastirma_m691_tp_motoru.py analiz       # -> /tmp/m691/*.csv + ekran raporu
```
Önkoşul: madde 690 çıktıları (`python3 arastirma_m690_kar_kaynagi.py kos && ... analiz`).
