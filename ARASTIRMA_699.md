# Araştırma 699 — TP'siz uzun short'u kesmek (1 Kasım 2026)

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**.
- **Ön kayıt:** KAR_HARITASI "Madde 699 ÖN KAYIT" (commit 534f4e1).
- **Araç:** `arastirma_m699_tpsiz_short.py`.
- **Motor kopyası:** `/tmp/g33_m699.py` = g33.py + `STP_GUN` / `STP_SOGUMA` düğmeleri.
- **Parite:** düğme kapalıyken iki hizada ana motorla **bayt bayt aynı**.
- **Koşular:** 8 koşu, tek işçiyle, hepsi rc 0.
- **Git:** strateji ve motor dosyalarında diff yok.

**Kural:**
- Bir dilimde, TP ya da kademe olmadan d gün tutulan short dengelemede aday listesinden çıkar; pozisyon kapanır.
- O coin 5 gün o dilimde aday olmaz. Yerine sıradaki aday gelir.
- **Etkili olduğunun kontrolü:** kesilen coin-dengeleme sayısı (hiza 0 / 1):
  - D7: 1.432 / 1.538.
  - D10: 397 / 418.
  - D14: 131 / 127.

**Teşhis (aynı veriden, ön kayıtta yazıldı):** TP'siz geçen her günden sonra short'un kalan katkısı düşüyordu.

| Kesintisiz tutulan short | Maruziyet başı yıllık getiri |
|---|---|
| 10 günden sonra | %4,5 |
| 15 günden sonra | −%10 |
| Short ortalaması | %149 |

## Sonuç [ÖLÇÜM] — üç kol da RED

| Kol | Ham CAGR | Maks DD | En kötü gün | Sharpe ≤2024 | Sharpe 2025+ | k | Eşit risk | Karar |
|---|---|---|---|---|---|---|---|---|
| P3T2 | 247,4 | −13,3 | −7,41 | 4,03 | 4,42 | 1,15 | 315,2 | — |
| D7 | 245,1 | −14,2 | −7,46 | 4,00 | 4,42 | 1,05 | 266,1 | RED |
| D10 | 245,9 | −13,3 | −7,47 | 4,01 | 4,42 | 1,15 | 313,1 | RED |
| D14 | 247,3 | −13,4 | −7,41 | 4,03 | 4,43 | 1,10 | 291,3 | RED |

**Yıllık fark (kol − P3T2, puan):**

| Kol | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|
| D7 | −24 | +2 | +2 | −2 | −3 | +7 |
| D10 | −11 | 0 | +1 | −1 | +2 | −1 |
| D14 | −4 | 0 | +1 | +1 | −1 | +2 |

## Yorum
- **Kural etkili ama getiri nötr ya da biraz negatif.** Teşhisteki "boşa bağlanan sermaye" serbest kalınca yerine gelen short'lar da daha
  iyisini yapmıyor [HİPOTEZ].
- Uzun süren short'lar düşük getirili olsa da kitapta hedge işi görüyor. Kesmek DD'yi biraz derinleştiriyor (D7 −14,2) ve eşit riskte kaybettiriyor.
- **Ders:** coin-gün defterindeki koşullu getiri tek başına yeterli değil; serbest kalan sermayenin alternatif getirisi de ölçülmeli. Madde
  611 / 665'teki "sıkışan short'a devam etmek doğru" bulgusuyla tutarlı: kayba göre de süreye göre de kesmek kazandırmıyor.
- **Karar:** bota girmez, izleme önerisi yok.
