# Araştırma 705 — "Gerçek yaş": yaş eşiği tokenin spot geçmişine göre (madde 704 H1) · 2 Kasım 2026

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**.
- **Ön kayıt:** KAR_HARITASI "Madde 705 ÖN KAYIT" (commit 2036bbb).
- **Araç:** `arastirma_m705_gercek_yas.py`.
- **Motor kopyası:** `/tmp/g33_m705.py`.
- **Parite:** düğme kapalıyken iki hizada ana motorla **bayt bayt aynı**.
- **Başarısız deneme:** ilk deneme, motor kopyası spot dosyasını yanlış klasörde aradığı için çöktü (rc 1, FileNotFoundError). **Sayılmadı**,
  çıktıları silindi; yol düzeltilip baştan koşuldu (commit d36b43f).
- **Koşular:** 10 koşu, hepsi rc 0: parite 2 + kollar 4 + ön kayıtlı ilk-3-coin kontrolü 4.
- **Git:** strateji ve motor dosyalarında diff yok.

**Kollar:**

| Kol | Kural | Evren değişimi (coin × bar) |
|---|---|---|
| A | Spotu perp'ten ≥ 365 g önce açılan tokenler 14 g perp yaşından uygun | +6.153 (+%0,9) |
| B | O barda spotu olmayan tokenler 90 g yaşa kadar uygun değil | −5.440 (−%0,8) |

## Sonuç [ÖLÇÜM]

| Kol | Ham CAGR | Maks DD | En kötü gün | Sharpe ≤2024 | Sharpe 2025+ | Eşit risk | İlk elek | Ek kontroller | **Karar** |
|---|---|---|---|---|---|---|---|---|---|
| P3T2 | 247,4 | −13,3 | −7,41 | 4,03 | 4,42 | 315,2 | — | — | — |
| A | 257,0 | −13,3 | −7,37 | 4,13 | 4,46 | **328,4** (+13,1) | ADAY | **en iyi yıl hariç −0,1 · ilk 3 coin hariç +4,7** | **RED** |
| B | 218,4 | −13,3 | −7,41 | 4,02 | **3,73** | 275,7 | RED | — | **RED** |

**Yıllık fark (kol − P3T2, puan):**

| Kol | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| A | −0,6 | **+105,8** | −2,8 | +1,9 | −2,1 | +9,0 | 0,0 |
| B | −0,8 | −0,8 | +0,4 | −6,3 | −3,1 | **−96,6** | **−70,6** |

**Ön kayıtlı ek kontroller (A):**

| Kontrol | P3T2 | A | Fark | Sonuç |
|---|---|---|---|---|
| 2021 hariç CAGR | 215,7 | 215,6 | **−0,1** | Sharpe 3,798 / 3,799 → **geçmedi** |
| Etkilenen coinlerden net katkısı en büyük 3'ü (DENT, BTT, HOT) evrenden çıkarılınca, eşit risk | 312,2 | 316,9 | **+4,7** (< +8) | **geçmedi** |

İlk 3 coin hariç yıllık farkın da büyük kısmı 2021'de: +38,1.

**Tanı (karar dışı):**

| Kol | Etkilenen pencere | Brüt payı | Katkı (maliyet hariç) | Coin sayısı | En büyük katkılar |
|---|---|---|---|---|---|
| A | Spot-önce coinlerin 14-60 g penceresi | %1,1 | +15,1 puan | 65 | DENT, BTT, HOT (2021'in eski "spot dinozorları") |
| B | Spotsuz coinlerin 60-90 g penceresi | %4,3 | **+60,6 puan** | 196 | CRV, SUSHI, KAITO |

## Yorum
- **A:**
  - İlk eleği geçti, ama kazanç **tek bir yılın** ürünü. 2021 boğasında, eski spot tokenlerin perp'e yeni geldiği dalga (DENT / BTT / HOT gibi)
    bu kazancı üretiyor.
  - 2021 çıkınca fark sıfır.
  - Ön kayıt tam bu durumu yakalamak için yazılmıştı → **RED**.
  - Mekanizma gerçek olabilir [HİPOTEZ] ama tekrarlanabilir kanıt yok. Bugün perp'e gelen tokenlerin çoğu spot'la aynı anda listeleniyor
    (2021+ 622 perp'in yalnız 156'sı spot-önce).
- **B:**
  - Hipotezin tersi çıktı: spotu olmayan genç coinler (60-90 g) riskli değil, **değerli**.
  - Dışlanınca 2025-26'da −97 / −71 puan kaybettiriyor.
  - "Perp-only token daha riskli" varsayımı bu kitapta yanlış. SPOT_SART yalnız short tarafında bir gerekçeydi; genel kuralda geçerli değil.
- **Genel:** yaş eşiğini kişiselleştirmek (spot geçmişine göre) tekrarlanabilir kâr getirmiyor. 60 g eşik bu eksende de yerinde (652 / 664 / 698 /
  703 ile tutarlı).
- **Karar:** bota girmez. Madde 704'teki sıraya göre sıradaki hipotez H2 (genç short sayı sınırı).
