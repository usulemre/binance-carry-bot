# Araştırma 690 — Kâr kaynağı sürdürülebilirlik analizi (1 Kasım 2026)

Kaynak kod, strateji ve parametreler DEĞİŞMEDİ. Hiçbir gösterge canlı stratejiye bağlanmadı. Önerilen ayar (P3T2 = T7K + koşullu stop,
2.000 $, 1,0x doz, gerçekçi model, iki hiza ortalaması) motorun KOPYASIYLA koşuldu (`/tmp/g33_m690.py`; yalnız mevcut günlük defter
çıktısına sütun eklendi). E dosyaları `g33.py` ile **bayt bayt aynı**.

Etiketler: **[ölçüm]** veriden hesaplandı · **[varsayım]** kanıtlanamayan girdi · **[hipotez]** test edilmemiş yorum / öneri.

**Tanımlar:**
- **Funding:** −poz × ödeme.
- **Fiyat:** çıkış olmayan barlarda poz × getiri; long / short ayrı.
- **TP:** kâr al ve kademe barlarında poz × getiri. Sıçramada satışın kendisi + kademe sonrası kalan.
- **Stop:** SL / S24K / diğer çıkış barları.
- **Komisyon:** KOM × işlem gören ağırlık (motorun kesintisinin yaklaşığı).
- **Gerçekleşmiş:** funding (anında nakit) + kapanan bacakların fiyat P&L'i.
- **Gerçekleşmemiş:** açık bacakların değişimi.
- **Birim:** getiri puanı (özkaynak oranı × 100), bileşik değil.

**Doğrulama [ölçüm]:** bileşenlerin toplamı, motorun günlük getirisiyle korelasyon **0,998**; ortalama mutlak fark 6,6 bp / gün.

> **ÖNEMLİ DÜZELTME (madde 687 / 688'e).** Önceki raporlardaki "fiyat payı %66 (2021) / funding payı %52 (2026)" ayrıştırması g33'ün
> yıllık tablosundan alınmıştı. O tabloda **kademe kâr almaları "fiyat" sütununa düşüyor** (kademe barı çıkış sayılmıyor). Kademe
> TP'ye konunca tablo değişiyor: kârın ana motoru **her yıl TP / kademe** (sıçramada satış). Tutuş fiyatı (çıkışsız barlar) net olarak
> sıfır civarı ya da negatif. "Kalabalığa karşı fiyat dönüşü" ifadesinin doğrusu: **dönüş, tutarak değil sıçramada satarak
> kazanılıyor.**

---

## 1. Kâr kaynakları ayrıştırması

### 1.1 Yıllık [ölçüm] (getiri puanı, 1,0x)
| Yıl | Funding | Long fiyat | Short fiyat | TP / kademe | Stop | Komisyon | Gerçek getiri |
|---|---|---|---|---|---|---|---|
| 2020* | 9,0 | 44,3 | −19,8 | 36,6 | 0,0 | −2,9 | 67,4 |
| 2021 | 17,6 | 92,8 | −57,4 | **135,6** | −0,1 | −6,7 | 179,1 |
| 2022 | 17,5 | −70,8 | 43,7 | **71,8** | −2,4 | −7,7 | 53,5 |
| 2023 | 44,0 | 60,0 | −25,6 | **70,5** | 0,0 | −7,6 | 145,9 |
| 2024 | 17,2 | 16,1 | −35,3 | **92,9** | −0,1 | −8,7 | 81,8 |
| 2025 | 71,0 | −84,5 | 22,8 | **142,6** | −0,9 | −9,1 | 136,0 |
| 2026* | 80,8 | −90,6 | −8,0 | **166,7** | −3,3 | −6,3 | 140,0 |

\*2020 Temmuz'dan, 2026 Eylül'e kadar (yıllıklaştırılmamış).

- **Long ve short fiyat birbirini kısmen dengeliyor** (bir yıl biri, ertesi yıl diğeri kaybediyor). İkisinin toplamı:
  2020 +24 · 2021 +35 · 2022 −27 · 2023 +34 · 2024 −19 · 2025 −62 · 2026 −99.
- **Son iki yılda tutuş fiyatı net negatif.** Kâr tamamen TP / kademe ve funding'den.

### 1.2 Coin bazında [ölçüm] (`/tmp/m690/coin_bilesen.csv`)
- 604 coin işlem gördü.
- Net kârın **%33'ü ilk 10 coinden**, %63'ü ilk 30'dan geliyor.
- 281 coin net zararlı.
- En kârlı: TRB +41,3 · SOL +34,9 · PIPPIN +30,0 · RIVER +29,8 · BNB +26,2 (puan, 6 yıl).
- En zararlı: KNC −9,7 · 1000SHIB −6,9 · LINA −6,5 · IOTX −6,1 · EGLD −5,5.
- **Kâr sağ kuyruklu:** birkaç coinin büyük sıçramaları taşıyor.

### 1.3 Pozisyon (bacak) defteri [ölçüm] (`/tmp/m690/pozisyon_defteri.csv`)
305.691 dilim bacağı:

| Kapanış türü | Bacak sayısı | Ortalama P&L | Toplam |
|---|---|---|---|
| TP ile kapanan | 10.246 | +1,85 (fiyat +1,81) | 189,3 |
| Devreden / yeniden dengelenen | 295.445 | +0,024 (fiyat ~0, funding +0,025) | 72,1 |

- **Gerçekleşmiş / gerçekleşmemiş:** gerçekleşmiş fiyat kârının neredeyse tamamı TP kapanışlarında.
- Devreden bacakların fiyatı toplamda −0,25 puan; yani gerçekleşmemiş fiyat P&L'i uzun vadede ~0'a yakınsıyor.
- Funding her bacakta gerçekleşmiş (anında nakit).
- Gün ve coin bazında bütün bileşenler: `/tmp/m690/gun_coin_bilesen.csv`.

## 2. 30 / 60 / 90 günlük hareketli pencereler [ölçüm]
Yıllıklaştırılmış puan; medyan [%5, %95]. Dosyalar: `/tmp/m690/hareketli_{30,60,90}g.csv`.

| Pencere | Funding | Long fiyat | Short fiyat | TP | Sharpe | Maks DD |
|---|---|---|---|---|---|---|
| 30 g | +22 [+6, +142] | −17 [−220, +254] | +2 [−191, +126] | +89 [+16, +280] | 4 [−2, 11] | −4 [−10, −2] |
| 60 g | +23 [+8, +138] | −16 [−185, +205] | −4 [−132, +101] | +91 [+38, +253] | 4 [0, 9] | −6 [−12, −3] |
| 90 g | +22 [+10, +126] | −14 [−155, +194] | −7 [−120, +80] | +87 [+41, +240] | 4 [1, 8] | −7 [−13, −4] |

**Negatif pencere oranı:**
- Funding **%0** (hiçbir 30 günlük pencerede negatif değil).
- TP **%0**.
- Long fiyat ~%55, short fiyat ~%50.

**Aylık:**
- Ortalama / standart sapma: funding 3,4 / 3,7 · TP 9,6 / 7,1 · long fiyat −0,4 / 12,3 · short fiyat −1,1 / 7,7.
- Bir sonraki aya taşınma (otokorelasyon): funding 0,67 · TP 0,39 · long fiyat 0,25 · short fiyat 0,07.

**İşlem başına beklenen getiri** (dilim bacağı): 30 günlük medyan +6,8 bp [%5 −1,5 · %95 +24,3]; 90 günlük +7,2 bp [+1,9 · +21,5].

## 3. Kötü rejimler (2021-2024)
Çeyreklik dosya: `/tmp/m690/ceyrek_bilesen.csv`. Kitabın en kötü ayları [ölçüm]:

| Ay | Funding | Long fiyat | Short fiyat | TP | Getiri |
|---|---|---|---|---|---|
| 2022-05 (LUNA) | 1,2 | −25,6 | 4,8 | 14,2 | −6,4 |
| 2023-02 | 0,3 | −5,7 | −3,2 | 2,5 | −5,8 |
| 2022-07 | 0,8 | 7,4 | −12,7 | 1,1 | −3,4 |
| 2022-08 | 0,7 | −6,6 | 1,0 | 3,2 | −2,9 |
| 2024-10 | 1,8 | −10,8 | 1,7 | 6,7 | −1,8 |
| 2024-08 | 1,6 | −11,4 | 3,5 | 6,1 | −1,5 |

- **Fiyat dönüşü (tutuş) hangi dönemde çalışmadı? [ölçüm]**
  - Long tarafı: 2022 tümü (−70,8; Q2 tek başına −50,5), 2025-26 (−84 / −91).
  - Short tarafı: 2021 (−57), 2023 (−26), 2024 (−35).
  - Tutuş fiyatı hiçbir dönemde güvenilir bir kâr kaynağı değil; aylık işareti yazı-tura.
- **Funding hangi dönemde ayakta tuttu? [ölçüm]** Hiçbir dönemde tek başına değil: 2021-2024 aylık 0,3-2,5 puan, çok küçük.
  - Tek istisna 2023 Q3: funding +29,7, o çeyreğin getirisinin %38'i.
  - 2025-26'da funding büyüdü (yılda 71-81). Son iki yılın ikinci ayağı funding.
- **TP getirinin önemli bölümü ne zaman? [ölçüm]** Her zaman. 2021 Q1-Q2 (59 / 40), 2022 Q2 (34; LUNA ayında long kaybının yarısını kapattı),
  2024 Q1 ve Q4, 2025-26 (yılda 143-167).
- **Hangi bileşen önce bozuldu? [ölçüm + hipotez]**
  - Kötü ayların ortak işareti, **TP'nin çok düşük olduğu ayda fiyatın da negatif olması**: 2022-07 TP 1,1 · 2023-02 TP 2,5 ·
    2022-08 TP 3,2.
  - 2021-10 / 2021-11'de TP 4,7-10 ve short fiyatı −13 / −10 ile getiri 0-1,4'e indi; ama 2022 Mart'ta +25 ile döndü.
  - 2022 Haziran-Ağustos'ta TP 14 → 1 → 3'e düştü. Funding bu sırada değişmedi (0,7-2,5).
  - [hipotez] Önce TP zayıflıyor (sıçrama yok / oynaklık düşük), sonra tutuş fiyatı belirleyici oluyor. Funding bozulmanın öncüsü değil.

## 4. Erken uyarı araştırması
**Kötü dönem tanımı (önceden):** sonraki 30 gün kitap getirisi < 0. Taban oran **%13,2**; 63 kötü bölüm. Göstergeler önceden tanımlandı,
eşik optimize edilmedi. Tablo: `/tmp/m690/erken_uyari.csv`.

| Gösterge | Alarm günü % | İsabet % | Lift | Yakalama % | Yanlış alarm % | Alarm sonrası 30 g getiri | Önceden yakalanan bölüm |
|---|---|---|---|---|---|---|---|
| Funding 30 g ≤ 0 (mevcut kapının F kuralı) | **0,0** | — | — | 0 | — | — | 0 / 63 |
| Funding 60 g ≤ 0 | 0,0 | — | — | 0 | — | — | 0 / 63 |
| Fiyat (long + short) 60 g < 0 | 57,4 | 13,2 | 1,0 | 57 | 87 | +%10,1 | 49 / 63 |
| Long fiyat 60 g < 0 | 53,3 | 10,3 | 0,8 | 42 | 90 | +%10,8 | 42 / 63 |
| Short fiyat 60 g < 0 | 49,7 | 14,7 | 1,1 | 56 | 85 | +%10,3 | 49 / 63 |
| TP 60 g < genişleyen medyanının yarısı | 7,7 | 14,4 | 1,1 | 8 | 86 | +%8,9 | 15 / 63 |
| Toplam getiri 60 g < 0 | 3,9 | 9,0 | 0,7 | 3 | 91 | +%7,0 | 9 / 63 |
| Fiyat 60 g < 0 VE funding 30 g düşük | 4,8 | 6,5 | 0,5 | 2 | 94 | +%9,7 | 5 / 63 |

**[ölçüm] Sonuç:**
- **Mevcut funding kuralı (F) 6 yılda hiç alarm vermedi.** Funding 30 günlük toplamı hiçbir zaman ≤ 0 olmadı. Edge'in tamamen ölmesi için
  tasarlanmış; kötü ayları yakalamıyor ve yakalaması da beklenmez.
- **Hiçbir bileşen göstergesi gelecek ayın zararını öngörmüyor** (lift 0,5-1,1 = rastgele ya da daha kötü).
- **Alarm günlerinden sonraki 30 günün getirisi yine +%7-11.** Bu göstergelerle bir kapı kurulsaydı iyi dönemleri kapatırdı; maliyet
  `iyi_dönem_kaybı_puan` sütununda (fiyat göstergesi için ~450 puan).
- **Yapısal kırılma denemesi:** 90 günlük funding VE TP birlikte tarihsel %10'un altında.
  - 63 gün alarm verdi: 2021-10, 2022-04, 2022-09 / 11.
  - Sonraki 90 günün ortalama getirisi +%14 (genel ortalama +%32): daha zayıf ama pozitif.
  - Eşik tarihsel dağılımdan seçildiği için [ölçüm, ama eşik örnek içi].

## 5. Nihai sonuçlar

**1. En istikrarlı kâr kaynağı: FUNDING [ölçüm].**
- Hiçbir 30 günlük pencerede negatif değil; aya taşınma 0,67; oynaklığı en düşük.
- Ama küçük: 2021-24'te yılda 17-44 puan.
- 2025-26'da büyüdü (71-81) ve sürüyor.

**2. En büyük ve en rejime bağımlı ikinci kaynak: TP / kademe [ölçüm].**
- Toplam kârın çoğu; hiçbir pencerede negatif değil, ama büyüklüğü 30 günde +16 ile +280 arası oynuyor (aya taşınma 0,39).
- Sıçrama ve oynaklık rejimine bağlı.
- [hipotez] Oynaklık uzun süre düşük kalırsa (sıçrama yok) TP söner ve kitap tutuş fiyatına kalır.

**3. En rejime bağımlı: TUTUŞ FİYATI (long / short) [ölçüm].**
- Aylık işareti yazı-tura (%41-57 negatif), aya taşınma ~0, uzun vadede net ~0 ya da negatif.
- Kötü ayları bu bileşen yapıyor, ama önceden bilinmiyor.

**4. Alarm hangi bileşende verilmeli? [hipotez; canlıya bağlanmadı]**
- Ölçüm yanıtı: hiçbir bileşen kötü ayı önceden göstermiyor; o yüzden **ay seviyesinde otomatik kapı önerilmez.**
- Yapısal kırılma için yalnız şu birleşik koşul anlamlı bir uyarı adayı: **funding 90 günlük VE TP 90 günlük ikisi birden tarihsel
  alt dilimde, ve ikisi de sürüyor.** Tarihte bu durum yalnız 2022 ikinci yarısında oldu; kitap o dönemde de pozitifti.
- Uyarı anlamı "kenar zayıflıyor, dozu ve beklentiyi gözden geçir" olmalı; "kapat" değil.

**5. Yalnız izleme amaçlı (karar vermeyen) göstergeler [hipotez]:**
- 30 / 60 / 90 günlük funding, TP, long ve short fiyat katkıları
- İşlem başına beklenen getiri
- Coin yoğunlaşması (ilk 10 coinin payı)
- TP kapanış sayısı

Bunlar panelde gösterilmeli. Long / short fiyat göstergesi tek başına asla kapı olmamalı (lift ≤ 1,1, alarm günlerinin %50'sinden fazlası).

**6. Kapının iyi dönemleri yanlışlıkla kapatma riski [ölçüm].**
- Ölçülen her bileşen göstergesinde alarm sonrası 30 günün getirisi pozitif (+%7-11 / ay).
- Fiyat temelli bir kapı zamanın ~%50-57'sinde kapalı kalır ve 6 yılda ~400-450 puanlık kârı kaçırırdı.
- Mevcut funding kapısının yanlış kapatma riski ise ölçüldüğü kadarıyla sıfır (hiç tetiklenmedi). Karşılığında erken uyarı değeri de sıfır.

**Varsayımlar [varsayım]:**
- Komisyon dağılımı yaklaşık; motorun gerçek kesintisi bileşen toplamıyla günde ~6,6 bp farklı.
- Bütün ölçümler backtest; canlı icra (TP dolumları, maker kalitesi) TP bileşenini doğrudan etkiler ve henüz ölçülmedi.
- 2025-26 funding artışının kalıcı olup olmadığı bilinmiyor.

---
### Yeniden üretim
```bash
python3 arastirma_m690_kar_kaynagi.py kos       # motor kopyası + 2 koşu (tek işçi, ~6 dk); parite kontrolü
python3 arastirma_m690_kar_kaynagi.py analiz    # tablolar -> /tmp/m690/*.csv
```
