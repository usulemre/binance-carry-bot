# ARAŞTIRMA 717 — V3 kuralının Hyperliquid ile bağımsız sınaması

**Sonuç: V3 DESTEKLENMEZ** (ön kayıtlı ölçüt, bağımsız pencere 2023-06 → 2025-05). Strateji, parametre ve canlı bot değişmedi. 677'nin Aralık kuralı aynen geçerli; bu sonuç ek kanıt olarak raporlanıyor.

## Kurulum

- **Ön kayıt:** KAR_HARITASI madde 717. Veri indirilmeden yazıldı ve depoya gönderildi.
- **Araç:** `arastirma_m717_hyperliquid.py`, dört adım: indir / panel / koş / analiz.
- **Veri:** Hyperliquid fundingHistory, saatlik ödemeler, 2023-05 → 2026-10.
  - Meta evreninde 235 perp var, 56'sı delist işaretli.
  - 215'i Binance sembolleriyle eşleşti. Eşleşmeyen 20 coin Binance'te yok: HPOS, RLB, UNIBOT, OX, FRIEND, SHIA, CANTO, REQ, NFTI, PANDORA, MNT, BLAST, PURR, JELLY, LAUNCHCOIN, YZY, APEX, CASHCAT, PONS, XTEN.
- **Kapsam:** Binance sinyal hücrelerinin %36,6'sında (2023-06 → 2025-05), %33,9'unda (2025-06 → 2026-09) ve %27,7'sinde (2026-10) Hyperliquid verisi var.
- **Benzerlik:** Hyperliquid ile Binance arasında coinlerin funding sırasına göre korelasyon (panel 60 / 96) +0,47 / +0,48. MEXC'te bu +0,93 / +0,94'tü.
- **Kural:** V3H = B + 0,5 × (B − HL), yalnız Hyperliquid verisi olan hücrelerde. Long panel sk_bar60, short panel sk_bar96. Taban P3T2, iki hiza, 2.000 $.
- **Koşular:** 2 motor koşusu, tek işçi, ikisi de rc 0 ve TAMAM.
- **Parite:** Hyperliquid sinyalinin ilk barı 2023-05-14. Seriler o gün ayrışmaya başlıyor; öncesinde tabanla fark 0.

## Sonuçlar (1,0x, iki hiza ortalaması)

| Pencere | V3H getiri | Taban getiri | V3H Sharpe | Taban Sharpe | V3H en kötü gün | Taban en kötü gün | V3H maks DD | Taban maks DD |
|---|---|---|---|---|---|---|---|---|
| **BİRİNCİL 2023-06 → 2025-05** | **%673** | **%780** | **3,40** | **3,62** | −6,16 | −7,41 | −11,7 | −12,4 |
| 2023-H2 | %138 | %156 | 4,34 | 4,94 | −4,33 | −3,68 | −10,4 | −8,1 |
| 2024 | %109 | %118 | 2,99 | 3,02 | −6,16 | −7,41 | −10,9 | −9,9 |
| 2025-H1 | %55 | %58 | 3,03 | 3,12 | −4,75 | −3,90 | −11,7 | −12,4 |
| 676 penceresi 2025-06 → 2026-09 (bilgi) | %917 | %793 | 5,16 | 4,85 | −5,76 | −5,25 | −12,5 | −12,5 |
| 2026-10, 677 OOS ayı (bilgi) | −3,61 | −4,27 | −0,98 | −1,16 | −3,31 | −3,52 | −7,7 | −9,3 |

**Ön kayıtlı ölçüt (birincil pencere):**
- getiri: X
- Sharpe: X
- en kötü gün: Y

→ **V3 DESTEKLENMEZ.**

V3H üç alt dönemin üçünde de getiri ve Sharpe'ta geride. Aylık fark (basit, puan) en çok 2023-12 (+13,4), 2024-01 (+9,9) ve 2024-11 (−13,2) aylarında oynuyor.

## Yorum

- **[ÖLÇÜM] Bağımsız dönem kuralı desteklemiyor.** Kuralın hiç görülmediği dönemde, ikinci bir borsanın verisiyle V3 tabandan kötü.
- **[ÖLÇÜM] İki dış borsa aynı pencerede ters sonuç veriyor.** 676 penceresinde (2025-06 → 2026-09):
  - MEXC ile V3: %373, taban %793 (madde 716).
  - Hyperliquid ile V3: %917, taban %793.
- **[VARSAYIM] Kural sağlam bir kenar değil.** Aynı fikir, aynı dönemde, dış borsaya göre çok kötü ya da çok iyi çıkabiliyor. Bu, kuralın dış borsa verisinin gürültüsüne bağlı olduğunu gösteriyor.
- **[ÖLÇÜM] Ekim'de üç seri birbirine çok yakın:** Hyperliquid V3 −3,61, MEXC V3 −3,65, taban −4,27. Tek ay; karar için anlamı yok.

## Karar

- 677'nin Aralık kuralı (Ekim–Aralık, MEXC V3, üç şart) değişmedi.
- Aralık'ta MEXC V3 şartları tutsa bile, iki ek kanıt da kuralın aleyhinde raporlanmak zorunda: 676 penceresi (madde 716) ve 717'nin bağımsız penceresi.
- Bota giriş için kullanıcı kararı gerekir.

## Sınırlamalar

- **Hyperliquid'in funding yapısı farklı:** Saatlik ödeniyor, faiz ve prim bileşeni Binance'ten farklı hesaplanıyor. Fark, kalabalık kadar borsa mekaniğini de yansıtıyor olabilir.
- **Kapsam ~%35:** Hyperliquid'de olmayan genç Binance coinlerinde (kârın büyük kaynağı) kural etkisiz.
- **Meta'dan silinmiş eski coinler indirilemedi:** Bu yalnız kapsamı daraltıyor; Binance evrenini etkilemiyor.
