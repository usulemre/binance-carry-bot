# Araştırma 703 — Genç coine ayrı hacim eşiği (2 Kasım 2026)

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**.
- **Ön kayıt:** KAR_HARITASI "Madde 703 ÖN KAYIT" (commit 7d8f7d2).
- **Araç:** `arastirma_m703_genc_hacim.py`.
- **Motor kopyası:** `/tmp/g33_m703.py` = g33.py + `GENC_HACIM` düğmesi.
- **Parite:** düğme kapalıyken iki hizada ana motorla **bayt bayt aynı**.
- **Koşular:** 6 koşu, tek işçiyle, hepsi rc 0.
- **Git:** strateji ve motor dosyalarında diff yok.

**Kural:**
- Yaşı 60-365 g arası, donuk değil, TradFi / D8 değil ve 24 saatlik hacmi ≥ eşik olan coinler, 70 M $ ana eşiğin altında kalsalar da evrene girer.
- **Etkili olduğunun kontrolü** (coin × bar hücresi; taban 675.808):
  - G50: +53.655 (%8).
  - G30: +155.853 (%23).

## Sonuç [ÖLÇÜM] — iki kol da RED

| Kol | Ham CAGR | Maks DD | En kötü gün | −%5 altı gün | Sharpe ≤2024 | Sharpe 2025+ | 1 yıl p1 | k | Eşit risk | Karar |
|---|---|---|---|---|---|---|---|---|---|---|
| P3T2 | 247,4 | −13,3 | −7,41 | 4 | 4,03 | 4,42 | −19,7 | 1,15 | 315,2 | — |
| G50 (genç: 50 M $) | 245,9 | −13,8 | −6,39 | 5 | 3,97 | 4,30 | −22,2 | 1,10 | 289,4 | RED |
| G30 (genç: 30 M $) | 220,3 | **−18,7** | −8,41 | 8 | 3,97 | **3,38** | −24,8 | 0,80 | 156,0 | RED |

**Yıllık fark (kol − P3T2, puan):**

| Kol | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|
| G50 | −20 | −1 | +16 | −17 | +22 | −5 |
| G30 | −13 | +4 | +8 | **−35** | **−46** | **−84** |

## Yorum
- **Düşük hacimli genç coinler kazandırmıyor, kaybettiriyor.** En çok da kuralın yardım etmesi beklenen dönemde: 2024-26'da G30 −35 / −46 / −84 puan.
- **G30'un riski belirgin büyüyor:** DD −13,3 → −18,7, −%5 altı gün 4 → 8, 2025+ Sharpe 4,42 → 3,38.
- **Bulgu:** 697'deki "genç coin ~6× kazanıyor" ölçümü, hacim eşiğini GEÇEN genç coinler içindi.
- **HİPOTEZ:** hacim filtresi genç coin kenarının bir parçası.
  - Düşük hacimli genç coinlerde sıkışma / çöküş kuyruğu kalın (689 / 697).
  - Bu coinlerde funding sinyali gürültülü.
  - Bu sonuç madde 226 / 652 ile aynı yönde: evren kuralı ne kadar gevşerse kuyruk o kadar büyüyor.
- **Maliyet notu:** motor sabit 5 bp yazıyor. Düşük hacimde gerçek kayma daha yüksek olacağından, gerçek sonuç tablodan da kötü olur. Yani RED
  kararı maliyet varsayımından bağımsız.
- **Ek tanı (karar dışı):** gk defterinde, o gün 24 sa hacmi 70 M altında olan coinlerin brüt payı G50'de %30, G30'da %39.
  - Bu pay tabanda zaten tutulan, hacmi sonradan düşen coinleri de içeriyor; yalnız eklenen coinleri göstermiyor. Bu yüzden ayrıştırma amaçlı kullanılmadı.
- **Karar:** bota girmez. 70 M $ eşiği genç coinler için de yerinde.
