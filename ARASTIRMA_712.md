# ARAŞTIRMA 712 — FUNDING ALPHA KAYNAĞI VE YOĞUNLAŞMA

Bu çalışma yalnız ölçümdür. Strateji, parametre, filtre, pozisyon yönetimi ve canlı bot değiştirilmedi. Ön kayıt KAR_HARITASI madde 712'de, sonuçlar görülmeden yazıldı ve depoya gönderildi.

- **Araç:** `arastirma_m712_funding_kaynak.py`. `kos` motor karşı-olgularını, `analiz` A–D analizlerini çalıştırır. Tam çıktı her çalıştırmada yeniden üretilir.
- **Veri:** madde 711 tam geçmiş defteri (2020-07-19 → 2026-10-31). P3T2, iki hizanın ortalaması, 1,0x doz.
  - Defter, önerilen ayarın resmi çalıştırmasıyla (EK_T7KKS) birebir aynı. Değişiklik yokken byte-parity sağlandı.
  - Defter 110.669 satır içeriyor: (gün, sembol, hiza) başına fiyat, TP, stop, funding, komisyon ve pozisyon değerleri.
- **Motor:** 8 koşu (3 çıkarma senaryosu ve 1 arz durması senaryosu, her biri 2 hiza). Tek işçi, seri çalıştırıldı. Hepsi rc 0 ve TAMAM; eksik koşu yok.
- **Birim:** bütün % puanlar 1,0x dozda ve iki hiza ortalaması.
  - "sy" sermaye-yıl başına demek: kalemin, o kaleme ayrılan ortalama sermayeye göre yıllık getirisi.
  - Yıllık kitap getirisi bileşiktir. Kalemler günlük katkıların basit toplamıdır.

## 1. Funding gelirinin gerçek kaynakları

**[ÖLÇÜM] Toplam funding:** 2020–26'da 259,7 puan. Bunun 214,9'u long, 44,8'i short tarafından.

**[ÖLÇÜM] Gelir, long tarafta funding'i aşırı negatif olan az sayıda coinden geliyor.**
- Kitap, ödeme yapılan günlerin yalnız %36–41'inde funding ödüyor (2025–26).
- Ödenen funding çok küçük: 2025'te −1,5, 2026'da −1,7 puan. Alınan funding ise 69,0 ve 83,4 puan.

**Long funding / sermaye-yıl yıl yıl:**

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Long funding (puan) | 3,2 | −2,1 | 16,0 | 40,0 | 8,6 | 67,5 | 81,7 |
| Long funding / sy (%) | 18 | −6 | 39 | 104 | 22 | 171 | 291 |
| Evren medyan funding (yıllık %) | 25 | 45 | 4 | 12 | 17 | 8 | 9 |
| Funding ödenen gün payı (%) | 67 | 70 | 39 | 58 | 73 | 41 | 36 |

**[ÖLÇÜM] Yaş grubu:** funding / sy gençten yaşlıya düzenli azalıyor.
- 2020–26 ortalaması: 60–180 g %90, 181–365 g %68, 1–2 yıl %40, > 2 yıl %47.
- 2026: 368 / 288 / 161 / 64.

**Üç soru:**

- **2021'de 25 genç coine rağmen funding neden −2,1?**
  - [ÖLÇÜM] Boğa piyasasında evren medyan funding yıllık %45'ti.
  - Long tarafın seçtiği "en düşük funding'li" coinler bile çoğunlukla pozitif funding ödüyordu. Ödeme yapılan gün payı %70, ödenen −9,7, alınan 7,6.
  - [VARSAYIM] Genç coin bolluğu, piyasa geneli pozitif funding'deyken long'a funding geliri getirmiyor. O yılın kârı fiyattan geldi: long fiyat +91, TP +134.

- **2026'da 8,5 genç coin ortalamasına rağmen funding nasıl +81,7?**
  - [ÖLÇÜM] Long funding / sy tüm zamanların en yükseği (%291). Long sermayesi daha düşük olduğu halde (102 sermaye-gün; 2025'te 144) gelir arttı.
  - Gelir, her ay aşırı negatif funding'li 1–3 coinden geliyor. 2026'da aylık ilk 3 coinin long funding payı %37–88.
  - Yıl toplamında: LAB 9,0, RIVER 7,3, HOME 3,9, PIPPIN 3,0, SENT 2,9.
  - 2 yaşından büyük coinlerde de funding / sy 2025'teki %33'ten %64'e çıktı. Yani artış yalnız gençlerden değil, bütün yaşlarda.

- **Mayıs 2026'da funding neden yalnız +1,2?**
  - [ÖLÇÜM] Long sermayesi normaldi (10,0 sermaye-gün; diğer aylar 8–12), evren medyanı da normaldi (%9,7).
  - Ama o ay kitapta aşırı negatif funding'li coin yoktu. En çok funding getiren ORCA 0,4 puan; ödeme yapılan gün payı %42.
  - Haziran'da yalnız LAB 6,4 puan getirdi.
  - [VARSAYIM] Aylık funding geliri, kitabın o ay "aşırı negatif funding" coini bulup bulamamasına bağlı.

## 2. Coin ve yaş grubu yoğunlaşması

**[ÖLÇÜM] İlk N coinin funding payı:**

| Dönem | Kalem | İlk 3 | İlk 5 | İlk 10 | İlk 20 | Coin |
|---|---|---|---|---|---|---|
| 2020–26 | long | %15 | %22 | %32 | %44 | 525 |
| 2020–26 | toplam | %13 | %19 | %27 | %37 | 608 |
| 2025 | long | %20 | %29 | %41 | %58 | 297 |
| 2026 | long | %25 | %32 | %45 | %63 | 288 |

**[ÖLÇÜM] Yıllık toplam funding'de ilk 3 / ilk 10 coin payı:**
- 2020: %41 / %78
- 2021: %28 / %62
- 2022: %21 / %52
- 2023: %59 / %78 (TRB)
- 2024: %23 / %57
- 2025: %19 / %39
- 2026: %24 / %44

Yıllık yoğunlaşma 2025–26'da azaldı. Buna karşın aylık yoğunlaşma yüksek (bölüm 1): her ay öne çıkan coin değişiyor.

**[ÖLÇÜM] 2020–26 en çok funding getiren coinler:** TRB 13,7 · BLZ 9,5 · PIPPIN 9,3 · LAB 9,0 · RIVER 7,5 · AXS 5,3 · HOME 3,9 · LPT 3,9 · ALPACA 3,7 · FUN 3,7. En çok ödenen coin yalnız −0,2 puan (UNI).

**[ÖLÇÜM] Genç (≤ 365 g) coinlerin toplam funding payı:**
- 2021 %83 · 2022 %18 · 2023 %10 · 2024 %57 · 2025 %72 · 2026 %58.
- Yaş grubuna göre funding payı / maruziyet payı:
  - 2025: 60–180 g %41 / %25; > 2 yıl %14 / %39.
  - 2026: 60–180 g %29 / %12; > 2 yıl %23 / %55.

**[ÖLÇÜM] Delist edilen coinler dahil.** Panelde 31, defterde 27 delist coin var. Bunların funding katkısı 6,5 puan, net katkısı 11,4 puan. Hayatta kalan coinlere bakma yanlılığı (survivorship) funding sonucunu belirgin biçimde değiştirmiyor.

## 3. Funding sürekliliği

**Pozisyon tanımı:** aynı hiza, sembol ve yönde kesintisiz günler. 15.456 pozisyon var: 6.918 long, 8.538 short.
- Long pozisyon süresi: medyan 7 gün, ortalama 9,7, p90 17.
- Giriş oranı, giriş gününden önceki günün gerçek ödemelerinden alındı (gelecek bilgisi yok).

**[ÖLÇÜM] Gerçekleşen ve teorik funding:**
- Toplam: gerçekleşen 259,7, teorik (giriş oranı × süre) 246,6.
- Long en uç beşte birlikte: gerçekleşen 109,0, teorik 193,7. Funding girişten sonra normale dönüyor.
- Long en az uç dilimlerde gerçekleşen, teorikten yüksek (Q1 1,8 / −12,4; Q2 32,6 / −3,4). Normal funding ile giren coinlerin bir kısmının funding'i sonradan negatife dönüyor.

**[ÖLÇÜM] Avantaj kaç gün sürüyor?**
- Ölçü: tutulan long'larda (coin − evren medyanı) farkının, giriş anındaki farka oranı (medyan, n ≈ 3.800).
- Seyir: +1 gün 0,91 · +3 gün 0,27 · +7 gün 0,16 · +14 gün 0,08 · +30 gün 0,03.
- Yarı ömür yaklaşık 2–3 gün.
- Her yıl +7 günde oran 0,5'in altında: 2020 0,24 · 2021 0,18 · 2022 0,16 · 2023 0,06 · 2024 0,03 · 2025 0,20 · 2026 0,25.

**[ÖLÇÜM] Yüksek funding ile açılan pozisyonlar daha çok net gelir üretiyor mu?**
- **Long:** Hayır.
  - Q5 (en uç) net / sy %256, Q1 %249.
  - Q5'te funding / sy +232, fiyat / sy −211. Funding'i fiyat kaybı yiyor.
  - Q5'in en çok net getiren 3 coini (PIPPIN, WAVES, FUN) çıkarılınca Q5 − Q1 farkı +6'dan −111'e düşüyor.
  - Yıllar karışık: 2021, 2023, 2024 ve 2026'da Q5 kötü.
- **Short:** Evet, ama gelir funding'den değil.
  - Q5 net / sy %333, Q1 %4. Q5'te TP / sy 475, funding / sy yalnız 67.
  - İlk 3 coin (BIGTIME, GOAT, LAB) hariç fark 329'dan 289'a iniyor (−%12).
  - Fark 2022–2026'nın her yılında pozitif; 2020–21'de negatif.

## 4. Funding ile fiyat riski ilişkisi

**[ÖLÇÜM] Coin düzeyi** (en az 0,5 sermaye-gün tutulan coinler; long 283, short 149):
- Long'da funding / sy ile TP hariç fiyat / sy arasındaki Spearman korelasyonu −0,21 (p 0,0004). Short'ta −0,10 (p 0,20).
- Long yıl bazında: 2020 +0,24 · 2021 −0,43 · 2022 −0,01 · 2023 −0,09 · 2024 −0,18 · 2025 +0,03 · 2026 −0,23. Toplamda eşikte, yıllarda tutarsız.

**[ÖLÇÜM] Long coin beşte birlikleri (funding / sy'ye göre):**

| | Funding / sy (medyan) | Fiyat / sy (medyan) | Net / sy (medyan) | Zararlı coin payı | Medyan MAE | En kötü MAE (medyan) |
|---|---|---|---|---|---|---|
| Q1 en az | −7 | −25 | 19 | %47 | −8,5 | −30,6 |
| Q3 | 36 | −213 | −2 | %51 | −10,2 | −34,6 |
| Q5 en çok | 405 | −227 | 342 | %28 | −13,0 | −34,9 |

En yüksek funding'li coinler fiyatta daha çok kaybediyor ve ters hareketleri daha derin. Yine de net olarak en iyi grup bunlar; zararlı coin payı en düşük. Burada sınıflama gerçekleşen değere göre, yani olay sonrası bir ölçü.

**[ÖLÇÜM] Yüksek funding / sy olup net zararlı long coinler (üst %20):**
- SOON: funding +1,6, fiyat −7,4, net −4,7, MAE −81
- MYX: +3,2 / −6,6 / −3,4, MAE −72
- BTW: +1,9 / −4,5 / −2,7, MAE −55
- XEM: −1,9 net
- ME: −1,8 net
- NOM: −1,6 net
- H: −1,1 net, MAE −91

**[ÖLÇÜM] En çok funding getiren long'larda en büyük ters hareket:**
- LAB −93
- RIVER −64
- AXS −62
- HOME −67
- PIPPIN −52
- BLZ −49
- TRB −37

**[ÖLÇÜM] Pozisyon düzeyi, gerçekleşen funding / sy beşte birliği:**
- MAE p10: Q1 −25,1, Q5 −39,3.
- Net / sy: Q1 388, Q5 473.

**[ÖLÇÜM] Yıl bazında MAE** (long coinler, medyan; Q5 / Q1):
- 2021 −13,7 / −7,8
- 2022 −8,8 / −8,7
- 2023 −6,1 / −5,7
- 2024 −7,7 / −10,9
- 2025 −11,4 / −8,4
- 2026 −14,6 / −9,8

## 5. Coin çıkarma ve arz daralması stres testleri

Bunlar tarihsel karşı-olgulardır, gelecek tahmini değildir. Çıkarılacak coinler TÜM dönemin funding sıralamasına göre seçildi; yani bilerek gelecek bilgisi içeren bir stres testi.

**[ÖLÇÜM] Motor testi.** Coin evrenden çıkarılıyor, sermaye kalan coinlere dağılıyor.

| | CAGR | Sharpe | Maks DD | En kötü ay | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Taban P3T2 | 239,3 | 4,1 | −13,3 | −6,6 | 92 | 472 | 63 | 310 | 118 | 267 | 267 |
| İlk 3 funding coini çıkar | 193,8 | 3,7 | −13,4 | −6,0 | 94 | 465 | 65 | 123 | 111 | 200 | 242 |
| İlk 5 çıkar | 176,3 | 3,5 | −13,9 | −6,0 | 94 | 465 | 65 | 123 | 111 | 187 | 143 |
| İlk 10 çıkar | 156,5 | 3,3 | −13,5 | −5,7 | 94 | 401 | 67 | 105 | 112 | 132 | 128 |
| 2025-01'den 180 g listeleme durması | 190,9 | 3,7 | −15,9 | −7,8 | 92 | 472 | 63 | 310 | 118 | 80 | 185 |

- Hiçbir senaryoda hiçbir takvim yılı negatif değil.
- 2023 neredeyse tamamen TRB'ye bağlı (%310 → %123).
- 2026, ilk 5 coin çıkınca %267'den %143'e iniyor (LAB, RIVER, HOME).
- Arz durması 2025 funding'ini 70,1'den 45,8'e indiriyor (−%35). Toplam getiri ise çok daha fazla düşüyor (%267 → %80): genç coin kaybı funding'den çok TP ve fiyat üzerinden. Bu, 695 A_DUR180 sonucunu doğruluyor; funding kalemi ilk kez ayrıca ölçüldü.

**[ÖLÇÜM] Muhasebe testi.** Motor çalıştırılmadı; yalnız o coinlerin defter katkısı çıkarıldı, sermaye yeniden dağıtılmadı. Net katkı, % puan:

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Taban | 178,5 | 52,3 | 144,6 | 81,7 | 136,3 | 135,7 |
| Her yılın ilk 3 funding coini o yıl çıkar | 166,0 | 35,9 | 75,8 | 78,3 | 87,5 | 99,6 |
| Her yılın ilk 5'i o yıl çıkar | 175,7 | 28,0 | 61,3 | 77,3 | 85,7 | 94,1 |
| Genç funding −%25 | 174,8 | 51,5 | 143,6 | 79,2 | 123,7 | 123,3 |
| Genç funding −%50 | 171,2 | 50,7 | 142,5 | 76,8 | 111,1 | 110,9 |
| Genç funding −%75 | 167,5 | 49,9 | 141,5 | 74,3 | 98,5 | 98,6 |

Genç coinlerin funding'i %75 kesilse bile 2025–26 net katkısı hâlâ yaklaşık 100 puan. Funding kesintisi tek başına yılları zarara çevirmiyor. Asıl kırılganlık, genç coinlerin TP ve fiyat katkısının da kaybolması (arz durması satırı).

## 6. Veri kalitesi ve sınırlamalar

- **Pozisyon çözünürlüğü günlük.** Gün içinde kapatılıp yeniden açılan pozisyon tek pozisyon sayılıyor. Dilim (faz) bazında giriş ve çıkış saati defterde yok. Motor faz ortalamasını yazıyor.
- **Gerçekleşen funding = motorun hesapladığı funding.** Motor gerçek Binance ödeme zaman damgalarını kullanıyor; her ödeme bara bir kez yazılıyor, açılış barında ve çıkış barında sayılmıyor (madde 268 denetimi). Hesap ekstresi değil. Canlı funding kaydı yalnız madde 701'den beri tutuluyor ve henüz çok kısa.
- **Funding aralığı.** 135 funding dosyasında aralık sütunu yok. Bu dosyalarda aralık, ödemeler arası süreden çıkarıldı (1/2/4/8 sa); bulunamazsa 8 sa varsayıldı.
- **Yaş ölçüsü.** Panelin YAS ölçüsü 2020-01'den sayıyor; o tarihten önce listelenen coinlerde yaş az görünüyor. 2020'de bütün coinler "genç" görünüyor, bu yüzden 2020 yaş analizi anlamsız. 94 satırda yaş yok.
- **MAE kapanış bazlı (4 sa).** Gerçek fitil dahil en büyük ters hareket daha derin olabilir.
- **Beşte birlik sınırları tüm dönemden.** Ticarette gelecek bilgisi yok, ama gruplama tüm örnekle yapıldı. Coin düzeyi sınıflama (bölüm 4) gerçekleşen değere göre, yani olay sonrası.
- **Spread ve derinlik ölçülmedi.** Aşırı funding'li genç coinlerde ölçülemedi.

## 7. Sınıflandırma (ön kayıt ölçütleriyle)

| Hipotez | Sonuç | Sınıf |
|---|---|---|
| H-A1 long funding yoğun (2020–26 ilk 10 > %50) | %32 (long); yıllık toplam funding'de 2021–24 %52–78, 2025–26 %39–44 | **RED** |
| H-A2 2024–26 funding'in çoğunluğu genç coinlerden | 2024 %57 · 2025 %72 · 2026 %58; ama 2022–23'te %10–18 | **PROMISING** (rejime bağlı) |
| H-B1 en uç girişli pozisyonlar daha çok net (long) | Q5 ≈ Q1; ilk 3 coin hariç ters; yıllar karışık | **RED** |
| H-B1 aynı soru (short) | 2021–26'nın 5'inde ve 2025–2026'da tutuyor; ilk 3 hariç −%12; gelir TP / fiyattan | **ROBUST** (geçmiş içinde; strateji pozisyonlarına koşullu) |
| H-B2 avantaj 7 günde > %50 kaybolur | Her yıl +7 günde oran 0,03–0,25 | **ROBUST** |
| H-B3 yüksek funding = yüksek fiyat kaybı (Spearman < −0,2) | Toplam −0,21; yıllarda 2 / 6, 2025'te +0,03 | **RED** (sistematik ilişki yok; üst grupta fiyat kaybı var ama net en iyi) |
| H-C ilk 3 / 5 / 10 funding coini çıkınca hiçbir yıl negatif değil | Hepsi pozitif; CAGR 239 → 194 / 176 / 157 | **ROBUST** (yıl pozitifliği; getiri düzeyi ilk 5–10 coine duyarlı) |
| H-D yüksek funding'li coinlerde MAE daha derin | 2021–26'nın 5'inde; 2022–23'te fark küçük; ilk 3 coin testi yapılmadı | **PROMISING** |

## 8. Yeni alpha araştırma fırsatları

Bunlar yalnız hipotezdir; hiçbiri uygulanmadı. Her biri ayrı ön kayıt, tek eksen ve en çok 2 kol ister.

1. **Funding yarı ömrü ile tutma süresi uyuşmuyor.** Funding avantajının yarı ömrü 2–3 gün, long pozisyonun medyan süresi 7 gün. Funding avantajı söndükten sonra long pozisyonun beklenen değeri ne?
   - Önce madde 520 ("SOLAN LONG DEĞİŞİMİ") ve madde 692'deki gecikme sonuçları okunmalı; tekrar edilmemeli.
2. **Short tarafta aşırı pozitif funding.** Bu pozisyonlar 2022–26'nın her yılında sermaye başına en iyi grup, ama kazanç TP'den geliyor.
   - Madde 603 (short rezerv) bunu daha önce denedi. Ondan farklı bir eksen bulunursa (ör. süre ya da TP seviyesi), ayrı ön kayıtla test edilmeli.
3. **Aylık "aşırı negatif funding coin" sayısı.** Mayıs 2026'da bu tür coin yoktu ve funding 1,2'ye düştü. Bunu ileriye dönük izleme göstergesi olarak tutmak öneriliyor; kapı ya da filtre olarak değil.
   - Madde 690 ve 694, gerçek zamanlı göstergelerin öngörü gücünü daha önce kanıtlayamamıştı.
4. **Arz durmasında funding kaybı toplam kaybın küçük bir kısmı.** Kuraklık savunması funding'e değil, genç coinlerin TP ve fiyat katkısına odaklanmalı. Madde 696–697 bu yönde: E50 ileriye dönük izleme önerisi açık.
