# Araştırma 698 — Yaş eğimi: seçilen genç bacaklara daha çok ağırlık (1 Kasım 2026)

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**.
- **Ön kayıt:** KAR_HARITASI "Madde 698 ÖN KAYIT", sonuçlar görülmeden (commit 4c5798a).
- **Araç:** `arastirma_m698_yas_egimi.py`.
- **Motor kopyası:** `/tmp/g33_m698.py` = g33.py + `YAS_EGIM` / `YAS_EGIM_GUN` / `YAS_EGIM_TARAF` düğmeleri.
- **Parite:** düğme kapalıyken iki hizada ana motorla **bayt bayt aynı**. Beş kolun her biri tabandan farklı, yani düğme etkili.
- **Koşular:** 14 koşu, tek işçiyle, hepsi rc 0.
- **Git:** strateji ve motor dosyalarında diff yok.

**Yöntem:**
- Seçim değişmiyor.
- Dengelemede eşit ağırlık hesaplandıktan sonra, bir tarafta hem genç hem eski bacak varsa genç bacakların ağırlığı × a.
- Taraf toplamı korunuyor: brüt ve dolar nötrlüğü aynı.
- Genç = o barda bilinen yaşı < g gün.

**Değerlendirme (madde 685 / 596):**
- Eşit risk: T4 1,0x'in maks DD'si, en kötü günü ve 1 yıllık bootstrap p1'i aşılmadan ulaşılabilen en büyük k ile yıllık getiri.
- **ADAY:** eşit-risk ≥ P3T2 + 8 **VE** Sharpe ≤2024 ve 2025+ tabandan düşük değil.

## Sonuç [ÖLÇÜM] — beş kol da RED

| Kol | Ham CAGR | Maks DD | En kötü gün | −%5 altı gün | Sharpe ≤2024 | Sharpe 2025+ | 1 yıl p1 | k | Eşit risk | Karar |
|---|---|---|---|---|---|---|---|---|---|---|
| P3T2 | 247,4 | −13,3 | −7,41 | 4 | 4,03 | 4,42 | −19,7 | 1,15 | 315,2 | — |
| A15 (×1,5, iki taraf) | 254,7 | −13,0 | −7,58 | 4 | **3,94** | 4,57 | −20,3 | 1,15 | 325,1 | RED (≤2024 Sharpe düştü) |
| A20 (×2, iki taraf) | 262,1 | −13,1 | −6,88 | 4 | **3,92** | **4,62** | −20,3 | 1,15 | **335,2** | RED (≤2024 Sharpe düştü) |
| L20 (×2, yalnız long) | 258,7 | −13,5 | −6,94 | 2 | 3,95 | 4,51 | −20,4 | 1,10 | 305,2 | RED |
| S20 (×2, yalnız short) | 249,8 | −13,7 | −7,40 | 5 | 3,98 | 4,52 | −19,9 | 1,10 | 294,2 | RED |
| A20G (×2, genç = 180 g) | 265,4 | −14,8 | −7,48 | 5 | 4,03 | 4,53 | −21,2 | 1,00 | 265,4 | RED |

**Yıllık fark (kol − P3T2, puan):**

| Kol | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|
| A15 | −33 | −8 | +4 | +1 | +41 | +48 |
| A20 | **−54** | −11 | +8 | +12 | **+69** | **+77** |
| L20 | −22 | −10 | −3 | +17 | +33 | +61 |
| S20 | −33 | −5 | +10 | −4 | +33 | +15 |
| A20G | +27 | −4 | +13 | +2 | +61 | +36 |

**Kuraklık dünyası** (L75_a, 2021+; karar dışı):
- Baz: CAGR 125,8, Sharpe 3,11, DD −16,9, en kötü gün −5,6.
- A20: CAGR 127,1, Sharpe **2,93**, DD **−18,1**, en kötü gün **−7,3**.
- Genç coin azken eğim getiri katmıyor, riski artırıyor.

## Yorum
- **Eğim, son dönemin rejimini büyütüyor.**
  - 2025-26'da yılda +40..+77 puan kazandırıyor.
  - 2021-22'de −8..−54 puan kaybettiriyor.
- A20 eşit riskte +20 puanla getiri şartını geçti. Ama 2024 öncesinde Sharpe düştüğü için iki dönem şartını geçemedi. Bu tam olarak ön kaydın
  yakalamak istediği şey: kazanç zamana yayılmıyor, son döneme yığılıyor.
- **Neden riskli [HİPOTEZ]:**
  - Genç coin avantajı 2024-26'ya özgü olabilir. 694'te 2021-23'te maruziyet başı genç %250 vs eski %139 iken, 2024-26'da %375 vs %62.
  - Kripto listeleme hızı 2026'da ~%60 düştü (697).
  - Eğim, tam da azalan kaynağa daha çok yaslanıyor.
  - Kuraklık dünyasında getiri katmadan riski artırıyor.
- **Short tarafında eğim (S20) zayıf.** 697'deki genç short kuyruğuyla tutarlı: getiri sınırlı, −%5 altı gün sayısı 4 → 5.
- **Karar:** ön kayıt gereği **bota girmez**. Beş kol çoklu deneme olduğu için ileriye dönük izleme önerisi de yok.
- **Bilgi notu:** A20, 2025+ için en güçlü kol (Sharpe 4,62). Genç coin akışı 2025 düzeyine dönerse yeniden ön kayıtla sınanabilir.
