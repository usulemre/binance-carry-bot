# Araştırma 708 — Ekim 2026 zararının teşhisi ve önleme denemesi (2 Kasım 2026)

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**.
- **Ön kayıt:** KAR_HARITASI "Madde 708 ÖN KAYIT" (commit 1c02bf5).
- **Zemin:** Ekim dahil (madde 706 / 707).
- **Parite:** düğme kapalıyken iki hizada, Ekim dahil zeminde önerilen ayarla (EK_T7KKS) **bayt bayt aynı**.
- **Koşular:** 6 koşu, tek işçiyle, hepsi rc 0.
- **Git:** strateji ve motor dosyalarında diff yok.

## 1. Teşhis [ÖLÇÜM] — Ekim'in kaybı nereden geldi
Önerilen ayar, 1,0x, iki hiza ortalaması: Ekim **−%4,27** (×1,15 dozda −%4,99). Bileşik hesaplandı; basit toplam −%3,76.

**Coin bazında (komisyon hariç):** toplam −3,2 puan.

| Grup | Katkı (puan) |
|---|---|
| En kötü 5 coin | **−10,1** |
| Kalan 116 coin | **+6,9** |

121 coinin 64'ü zararda. Kayıp birkaç aşırı oynak coinde yoğunlaştı:

| Coin | Katkı | Olay |
|---|---|---|
| **BTW** (150 g, 24 sa hacim 58 M $) | **−3,7** | 1-14 Ekim SHORT: fiyat 1,0 → 2,4 (13 Ekim −1,1 puan). 15 Ekim funding dönünce LONG: fiyat 2,4 → 1,08 (26 Ekim −2,3, 30 Ekim −2,6). Günlük ±%20-45 hareketler; iki yönde de yanlış tarafta. |
| TIA | −2,2 | Short; 10 Ekim +%27, 16 Ekim +%16,5 |
| ARIA | −1,7 | Short; 20 Ekim +%41 (o gün kitabın en kötü bacağı) |
| APR | −1,35 | Short sıkışması; 28 Ekim'de kitabın %13,9'u tek coinde (fiyat kayması) |
| 龙虾 | −1,1 | Short |
| Q | (−2,0 tek gün) | +%111 pompadan sonra LONG; 24-25 Ekim −%30 / −%26 |

**Taraf ve piyasa:**
- LONG fiyat −12,5 / funding +5,0; SHORT fiyat +4,1 / funding +0,2.
- BTC −%7,2; alt evren medyanı −%16,2.

**Koşullu stop:** tetiklenmedi. Tasarım gereği (madde 622): yalnız piyasa çöküşüyle birlikte gelen 24 sa düşüşte çalışır. Ekim kayıpları tek coin hareketleriydi.

**Geçmişteki yeri:** 76 ayın 3. en kötüsü (2022-05 −6,6 ve 2023-02 −5,7'den sonra). Ay içi düşüş −%10,7; düşüş ay sonunda açık.

## 2. Önceden denenmiş savunmalar (tekrar edilmedi)

| Savunma | Madde | Sonuç |
|---|---|---|
| Long coin tavanı (dağıtımlı / dağıtımsız) | 542 / 543 | RED (kâr kaynağı da yoğun long'lar) |
| Uç hareket elemesi (UCELE) | GE2 | kapatmak +6 → kapalı |
| Oynaklığa göre ağırlık | 251 / 257 | kapalı (eşit ağırlık doğru) |
| Short 24 sa stop | 646 | RED |
| Long giriş stop'u | 651 | RED |
| Stop sonrası soğuma | 665 | RED |
| Kayıp hafızası | 611 | RED |
| Düşüş freni DDA2 (izleme kolu) | 685 | Ekim'de **−%5,93** (taban −%4,99, aynı risk dozunda) → işe yaramadı |

## 3. Denenen yeni savunma: taraf değişim soğuması [ÖLÇÜM] — RED
- **Kural:** son N gün içinde bu dilimde short tutulan coin long adayı, long tutulan coin short adayı olamaz.
- **Etkili olduğunun kontrolü:** elenen aday sayısı (hiza 0 / 1) N7 için ~47 bin, N14 için ~82 bin.

| Kol | Ham CAGR | Maks DD | En kötü gün | Sharpe ≤2024 | Sharpe 2025+ | Eşit risk | Ekim (bilgi) | Karar |
|---|---|---|---|---|---|---|---|---|
| P3T2 | 247,4 | −13,3 | −7,41 | 4,03 | 4,42 | 315,2 | −4,27 | — |
| N7 | 240,2 | −13,5 | −7,76 | 4,01 | 4,27 | 282,5 | −4,55 | RED |
| N14 | 230,3 | −13,3 | −7,45 | 3,95 | 4,11 | 291,7 | −4,75 | RED |

**Yıllık fark:**
- N7: 2023 −8,7, 2026 −26,8.
- N14: 2023 −16,7, 2026 −55,3.

**Önemli:** kural, ilham aldığı Ekim'i bile iyileştirmiyor (−4,55 / −4,75 vs −4,27).
- **HİPOTEZ:** taraf değiştiren coinler (BTW gibi) ortalamada hâlâ kârlı (madde 708 teşhisi: +13 / +55 puan).
- Bunları dışlamak sermayeyi sıradaki daha zayıf adaylara kaydırıyor.
- BTW'nin Ekim kaybını yerine gelen adaylar da telafi etmiyor.

## 4. Sonuç
- **Ekim kaybı bir hata değil, stratejinin bilinen kuyruğu.**
  - Kâr, aşırı oynak genç / orta yaşlı coinlerin iki yönlü hareketinden geliyor.
  - Aynı oynaklık bazı aylarda birkaç coinde ters yöne vurup kaybettiriyor: BTW, short'tayken pompa, long'dayken çöküş.
- 690-708 boyunca bu kuyruğu kesmeye çalışan bütün kurallar (stop, tavan, eleme, soğuma, fren) **kârı kuyruktan daha çok kesti**.
- **Kayıp büyüklüğünü kontrol etmenin ölçülmüş tek yolu doz** (madde 684): ×1,15 yerine 1,0x Ekim'i −%5,0 → −%4,3 yapar, getiriyi de orantılı azaltır. Bu kullanıcı kararı.
- **Kasım'da madde 650 kuralı tekrar ölçülecek.** Ard arda zayıf aylar gelirse 696 / 697'deki kuraklık bulgusu (genç coin havuzu 5'e indi) yeniden değerlendirilmeli.
