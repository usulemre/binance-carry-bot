# Araştırma 709 — Genç short sayı sınırı (madde 704 H2) · 2 Kasım 2026

Ana strateji kodu, parametreler, motorun orijinal dosyaları ve canlı sistem **DEĞİŞMEDİ**.
- **Ön kayıt:** KAR_HARITASI "Madde 709 ÖN KAYIT" (commit b2dff44).
- **Zemin:** Ekim dahil.
- **Parite:** iki hizada, düğme kapalıyken EK_T7KKS ile **bayt bayt aynı**.
- **Koşular:** 6 koşu, tek işçiyle, hepsi rc 0.
- **Git:** strateji ve motor dosyalarında diff yok.

**Kural:**
- Dengelemede short adayları içinde < 365 g olanlardan yalnız en yüksek sinyalli k tanesi kalır; diğerleri elenir, yerine sıradaki (eski) aday girer.
- **Etkili olduğunun kontrolü:** elenen aday sayısı (hiza 0 / 1) K2 için ~117 bin, K3 için ~99 bin.

## Sonuç [ÖLÇÜM] — iki kol da RED

| Kol | Ham CAGR | Maks DD | En kötü gün | −%5 altı | Sharpe ≤2024 | Sharpe 2025+ | 1 yıl p1 | Eşit risk | Ekim (bilgi) | Karar |
|---|---|---|---|---|---|---|---|---|---|---|
| P3T2 | 247,4 | −13,3 | −7,41 | 4 | 4,03 | 4,42 | −19,7 | 315,2 | −4,27 | — |
| K2 | 202,9 | **−15,0** | −6,86 | 5 | 3,81 | **3,84** | −21,3 | 202,9 | −6,34 | RED |
| K3 | 227,2 | **−15,1** | −6,81 | 3 | 4,05 | 4,07 | −21,2 | 227,2 | −4,46 | RED |

**Yıllık fark (kol − P3T2, puan):**

| Kol | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| K2 | −33 | −81 | +1 | −35 | −1 | −44 | −98 |
| K3 | −14 | −14 | +7 | −20 | +2 | −23 | −71 |

## Yorum
- Sınır **en kötü günü biraz iyileştiriyor** (−7,41 → −6,8), ama **maks DD'yi kötüleştiriyor** (−13,3 → −15,0) ve getiriyi ağır kesiyor.
- Bu yüzden eşit risk kaldıracı bile 1,15'ten 1,00'a iniyor.
- Ekim'i de iyileştirmiyor: K2 −6,34, K3 −4,46, taban −4,27.
- **HİPOTEZ:**
  - Genç short'ların yerine giren eski short'lar daha az kazanıyor.
  - Genç short'lar kitabın long tarafına karşı daha iyi bir denge kuruyor; eski short'lar alt çöküşlerinde yeterince düşmüyor. Bu yüzden DD derinleşiyor.
  - Sonuç 664 (genç short dışlama RED) ve 697 T4 (genç short'lar en kârlı short grubu) ile tutarlı.
- **Karar:** bota girmez. Madde 704'ün beş hipotezinden H1 ve H2 test edildi, ikisi de RED. Kalanlar: H3 veri zayıf (ertelendi), H4 ve H5'in önsel değeri düşük.
