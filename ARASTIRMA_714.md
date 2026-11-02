# ARAŞTIRMA 714 — SHORT POZİSYON YAŞI VE KÂRLILIK PROFİLİ

**Karar: yeni test yapılmadı.** Gözlem yaşa bağlı bir alpha değil. Uygulanabilir hâli (short'u daha sık yenilemek) 493–513, 545–546, 553 ve 568'de defalarca test edildi; 40 saatlik yenileme önerilen ayarın içinde zaten var.

- Strateji, parametre ve canlı bot değişmedi. Motor çalıştırılmadı.
- **Araç:** `arastirma_m714_short_yas.py`, rc 0.
- **Veri:** madde 711 defteri (önerilen ayarın resmi çalıştırması EK_T7KKS ile birebir aynı). Pozisyon tanımı 712 / 713'tekiyle aynı.
- **Gruplama yalnız girişte bilinen özelliklerle yapıldı:** coin yaşı, giriş carry'si (giriş gününden önceki günün ödemeleri) ve yıl.
- **Birim:** "sy" sermaye-yıl başına demek, değerler % puan ve 1,0x doz.

## 1. Aşama 1 — Geçmiş araştırmalarla çakışma (içerik okunarak)

**Madde 493–501: short ara dengelemesi (S_REB).**
- **Ne test edildi:** Short dilimleri tam dengeleme (5 g) beklenmeden her 1 / 2 / 3 günde yeniden seçildi. T1 tabanında yapıldı; 2022–26, sonra uzun zemin 2020-07 → 2026-09.
- **Gerçekçilik kontrolü (494):** canlı bot gibi giriş fiyatı (TEK_GIRIS) ve 5 bp maliyetle tekrarlandı.
- **Sonuçlar:**
  - Kazanç short fiyatından ve short TP'sinden geliyor; funding hemen hemen aynı (493).
  - 496'nın notu: "short kârı tazelikten, long kârı pompadan".
  - Kazanç önce yalnız 2025–26 rejimi sanıldı. Uzun zeminde üç bağımsız dönemin üçünde de önde (497).
  - Ama protokolde RED: Sharpe her dönemde artıyor, en büyük düşüş 3–8 puan derinleşiyor (2020-11 dar evren olayı; 498 / 499).
  - Short coin tavanı %8 ile kuyruk kapandı. Dört şartın dördü tuttu, yalnız bootstrap P %68–82'de kaldı: RED, kullanıcı kararına bırakıldı (500 / 501).

**Madde 511–513 ve 545–546: T4 tabanında yenileme sıklığı** (1 g / 1,5 g / 3 g; 32 / 36 / 40 sa).
- 36–40 saatte bir plato var, 32 saat kötü.
- 48 saatten 40 saate geçiş protokolde RED: "bir doz farkı, kanıt değil" (513, 546).
- **Madde 553 / 568:** short 40 sa, T5 / T6 paketlerinin içinde yeniden test edildi.
- **Önerilen ayar (T7K) bugün `S_REB=10` kullanıyor** (10 bar = 40 sa). Yani "taze short daha kârlı" fikri zaten üretimde.

**Madde 521: T4 tabanında short yapısı.**
- **Ne test edildi:** short kademesi kapalıyken ve 5 / 6 short bacakla.
- **Sonuç:** Short kademesi gerekli; kapatılınca yıllık −40. Daha çok bacak en kötü günü iyileştiriyor ama getiriyi ve Sharpe'ı düşürüyor. 4+4 ve −%15 yerinde.
- Pozisyon yaşı test edilmedi, ama kademe ve TP short kârının çekirdeği.

**Diğer ilgili maddeler:**
- 215: taraf bazlı tutma süresi, RED.
- 493 / 499: sert piyasada short yenilemeyi durdurmak (S_REB_DUR); geçmedi.
- 611: kayıp veren short'u eleme (KAYIP_HAF), RED.
- 690–693: TP motoru, fitil ve gecikme.
- 713: long tarafta yaş.

**Çakışma değerlendirmesi:** 714'ün sorusu ("short'un ilk günleri daha mı değerli?") ölçüm olarak yeni. Ama eyleme dönük her hâli (short'u daha sık yenilemek, daha kısa tutmak) S_REB ekseninde, tutma süresi ekseninde (215) ve kademe ekseninde (521) test edildi. Bu yüzden önce bunun gerçek bir yaş etkisi mi, yoksa seçilim ya da TP zamanlaması mı olduğunu ölçtüm.

## 2. Aşama 2 — Ölçüm

**[ÖLÇÜM] Genel tablo.** 8.538 short pozisyon. Süre medyan 3 gün, ortalama 5,1, p90 10. Short sermayesinin %41'i yaş 0–2'de.

| Yaş (gün) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7–9 | 10–14 | 15+ |
|---|---|---|---|---|---|---|---|---|---|---|
| TP / sy | 255 | 217 | 171 | 150 | 198 | 168 | 171 | 128 | 142 | 141 |
| TP hariç fiyat / sy | −155 | +12 | −10 | −1 | −10 | −16 | −101 | −17 | −89 | −78 |
| Funding / sy | 18 | 20 | 21 | 21 | 19 | 23 | 24 | 23 | 23 | 21 |
| Net / sy | 79 | 237 | 164 | 156 | 193 | 161 | 80 | 121 | 65 | 73 |
| TP olan gün payı % | 4,0 | 7,1 | 5,3 | 5,3 | 5,2 | 4,8 | 4,5 | 3,8 | 3,9 | 3,9 |

**[ÖLÇÜM] Erken (0–2 g) ve geç (≥ 3 g) net / sy, gruplara göre:**

| Grup | Erken | Geç | Fark | TP erken / geç | Fiyat erken / geç | Funding erken / geç |
|---|---|---|---|---|---|---|
| Tümü | 183 | 117 | +65 | 209 / 152 | −27 / −44 | 20 / 22 |
| Genç coin (girişte ≤ 365 g) | 321 | 224 | +97 | 366 / 279 | −61 / −84 | 36 / 41 |
| Eski coin | 102 | 49 | +54 | 117 / 71 | −7 / −19 | 11 / 9 |
| Carry düşük | 17 | 34 | −18 | 81 / 38 | −49 / +4 | 3 / 5 |
| Carry orta | 215 | 56 | +160 | 124 / 83 | +102 / −25 | 8 / 11 |
| Carry yüksek | 302 | 270 | +32 | 403 / 348 | −128 / −117 | 47 / 52 |

**[ÖLÇÜM] Yıl yıl erken − geç farkı:** 2020 −92 · 2021 −116 · 2022 +49 · 2023 +107 · 2024 +49 · 2025 +129 · 2026 +226. Erken avantajı yalnız 2022–26'da var; 2020–21'de tersi.

**[ÖLÇÜM] Seçilim kontrolü (kilit test).** Yalnız en az 5 gün tutulan short'lar alındı (2.946 pozisyon) ve aynı pozisyonların içinde yaş 0–2 ile yaş 3–4 karşılaştırıldı:
- Tümü: yaş 0–2 net / sy 134, yaş 3–4 153.
- Yaş 3–4, 7 yılın 6'sında daha iyi: 2020, 2021, 2022, 2023, 2025, 2026. Yalnız 2024'te tersi (134 / −82).
- Aynı pozisyon yaşlandıkça değer kaybetmiyor.
- Erken avantajının kaynağı farklı: kısa süren pozisyonların ilk günleri çok kârlı. En fazla 3 gün süren short'larda yaş 0–2 net / sy 296, en az 5 gün sürenlerde 134. Short TP'ye değince pozisyon kapanıyor, kazancı da "genç yaş" hanesine yazılıyor.
- Pozisyonun ömrü sonradan bilinir; bu yüzden karar için kullanılamaz.

**[ÖLÇÜM] Yoğunlaşma.**
- Erken net'e en çok katkı yapan 3 coin: GALA 8,4, CHZ 5,3, REN 4,9. İlk 3 coinin payı %12, ilk 10'un %30.
- Bu 3 coin çıkarılınca fark +65'ten +52'ye iniyor.
- Yıllar aynı desende kalıyor: 2020 −92 · 2021 −183 · 2022 +35 · 2023 +120 · 2024 +21 · 2025 +140 · 2026 +223.

**[ÖLÇÜM] Yaşa göre en büyük ters hareket** (girişten o yaşa kadar en yüksek yükseliş; 4 saatlik kapanışlardan):

| Yaş (gün) | 0 | 1 | 2 | 3 | 5 | 7 |
|---|---|---|---|---|---|---|
| Medyan % | −2,0 | −3,2 | −4,0 | −4,9 | −5,9 | −6,3 |
| p10 % | −11,3 | −15,4 | −18,0 | −20,3 | −22,5 | −23,6 |

Ters hareket zamanla doğal olarak birikiyor; ilk günlerde ani bir sıçrama yok.

## 3. Yorum: gözlem mi, nedensel sonuç mu

- **[ÖLÇÜM]** Toplamdaki "erken yaş daha kârlı" deseninin iki kaynağı var:
  - **TP zamanlaması:** TP'ye değen short'lar kısa ömürlü olduğu için kazançları genç yaşa yazılıyor.
  - **Rejim:** desen yalnız 2022–26'da var, 2020–21'de tersi.
- **[ÖLÇÜM]** Aynı pozisyonlar içinde yaşlanma değeri düşürmüyor (yaş 3–4 > yaş 0–2, 7 yılın 6'sında). Bu yüzden "short yaşlandıkça alpha kaybeder" diye nedensel bir sonuç desteklenmiyor.
- **[VARSAYIM]** Taze short'ların gerçek avantajı, yeniden seçimle sermayenin yeni aşırı funding'li adaylara gitmesi ve TP'nin yeniden kurulması. Bu, S_REB'in mekanizması; zaten ölçüldü ve 40 saatle üretimde.

## 4. Aşama 3 — Araştırma kararı

**Yeni test önerilmiyor.**
- Yaşa bağlı alpha seçilim kontrolünde kayboluyor.
- Eyleme dönük her hâli test edildi:
  - short daha sık yenileme: 493–501, 511–513, 545–546, 553, 568
  - tutma süresi: 215
  - kademe ve TP yapısı: 521, 691–693
- Bunlara ek bir kol açmak, ön kayıt ölçütlerini görmüş bir parametre taraması olur.

## 5. Sınıflandırma

| Soru | Sonuç | Sınıf |
|---|---|---|
| Short'un ilk 0–2 günü yaşa bağlı gerçek bir alpha mı? | Aynı pozisyonlar içinde tersi (6 / 7 yıl); toplam desen TP zamanlaması ve 2022–26 rejimi | **RED** |
| Erken avantaj tek coine mi bağlı? | Hayır; ilk 3 coin hariç +52, ilk 10 coin payı %30 | Tek coine bağlı değil, ama yaş etkisi değil |
| Uygulanabilir hâli (sık yenileme) | 493–568'de test edildi; 40 sa önerilen ayarda | Yeni test yok (çakışma) |

## 6. Sınırlamalar

- **Pozisyon günlük çözünürlükte, kesintisiz günlerden kuruldu.** S_REB yenilemesinde aynı coin yeniden seçilirse pozisyon "devam" sayılıyor. Canlı gibi girişte (TEK_GIRIS=1) giriş fiyatı da korunuyor, bu yüzden tanım tutarlı.
- **En büyük ters hareket kapanış bazlı.** Gerçek fitiller daha derin olabilir.
- **Ömür grubu sonradan bilinir.** Yalnız betimsel kullanıldı; seçilim kontrolü aynı pozisyonların içinde yapıldı.
