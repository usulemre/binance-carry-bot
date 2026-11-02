# RESEARCH 699 — HYPOTHESIS REPORT (Alpha Discovery Program) · KAR_HARITASI'nda madde 704 (2 Kasım 2026)

> **Numara notu:** 699 numarası bugün "TP'siz uzun short'u kes" araştırmasına verildi. Bu rapor çakışma olmasın diye KAR_HARITASI'nda
> **madde 704** olarak kayıtlı.

**Kapsam:**
- Yalnız hipotez raporu. **Hiçbir strateji, parametre ya da motor değişikliği yapılmadı. Test koşusu yok.**
- Bu raporda yapılan tek veri işlemi, hipotezlerin **veri yeterliliği** kontrolü: kapsam, dönem, sağkalım. Sonuç (getiri) verisine bakılmadı,
  böylece ön kayıt kirlenmedi.

---

## 1. Geçmiş araştırmaların taraması: elenmiş ya da kapanmış eksenler

KAR_HARITASI taranırken (~7.900 satır, 389 başlıklı madde + tablolar) kullanıcının listesindeki her alanın durumu kontrol edildi.

| Alan (kullanıcı listesi) | Durum | Kanıt (madde) |
|---|---|---|
| Coin yaşına göre davranış | Çok derin ölçüldü. Yaş eşiği (60 g) her iki tarafta yerinde; yaşa göre ağırlık eğimi RED; genç coine ayrı hacim eşiği RED | 226 / 228, 461, 652, 664, 693, 694, 697, **698**, **703** |
| Long ve short ayrı alpha | Long kârı pompa + funding, short kârı tazelik + TP; taraf payı, taraf başına yaş / kademe / TP ölçüldü | 194, 214, 494, 566, 639, 664 |
| Funding değişim hızı / yönü | Funding eğimi (yeni artan öne) **güçlü negatif**; kalıcı funding plato yok; funding solması (çıkış) kapandı | **556 / 557**, 167 / 191 |
| Aşırı pozisyonlanma / kalabalık | Kalabalık (long/short oranı) seçimin değeri; top-trader kitabı ayrı kitap olarak RED; çeşitlendirme RED | 627, 649, 667 / 669 |
| Göreli performans / momentum | Kesitsel momentum ikinci motor bulundu ama getiri korelasyonu yüzünden eklemiyor; ML kesitsel tahmin RED | **237**, 389, 411, 579 |
| Volatilite genişleme / daralma | Oynaklık sıkışması kırılımı RED; oynaklığa göre TP (TPKAT) kapalı eksen; kitap oynaklık hedefi RED | **384**, 221, 555 / 685 |
| Fiyat sürekliliği / dönüş | Rejim analizi: tek yönlü süreklilik en iyi rejim; erken uyarı göstergesi yok | 692, **693** |
| Likidite / hacim | Hacim eşiği 70 M yerinde; Amihud ve anormal hacim RED; genç coine düşük eşik RED | 226, 507 / 508, 649, **703** |
| TP gerçekleşme / kâr realizasyonu | TP ana kâr kaynağı; seviye, kademe sayısı, kademe payı, TP sonrası yeniden giriş, koşucu, geri alım ölçüldü | 290, 417, 475, 476, 491, 639, 666, 691 / 692 |
| Pozisyon yaşı / tutma süresi | Tutma süresi bir doz düğmesi; TP'siz uzun short'u kesmek RED | 215, 264, 522, 679, **699** |
| Piyasa koşuluna göre sermaye dağılımı | Dinamik doz (oynaklık / momentum / düşüş) RED; prim ölçekli brüt mevcut; kuraklık savunması RED; eski coin kısma (E50) ölçüldü, izleme önerisi | 239 / 288, 685, **696**, **697** |
| Ortak davranış | Beta-nötr kitap, BTC / ETH trend kolu, korelasyonla çeşitlendirme RED; faktör korelasyonu ~0 | 686, 667, 695 F |
| Yeni veri | Prim endeksi, OI, taker, MEXC funding, USDC çiftleri, spot listeleme olayı, funding ödeme anı fiyatı: hepsi RED / kapandı | 550, 649, 676 / 683, 387, 394, 647 |

**Son 7 araştırmadan dersler (690-703):**
- **Kâr motoru:** TP / kademe hasadı, genç ve oynak coinlerde iki yönlü fiyat keşfi.
- **Kenarın yapısı:** kenar evren kuralının (yaş 60, hacim 70 M) içinde yaşıyor. Kural gevşedikçe kuyruk büyüyor (652, 703); yaşa göre ağırlık son
  rejimi büyütüyor (698).
- **Yöntem uyarısı:** coin-gün defterindeki koşullu getiri, serbest kalan sermayenin alternatif getirisi ölçülmeden aday sayılmamalı (699).
- **Ölçüt yükü:** eşit riskte +8 puan ve iki dönemde Sharpe şartı çok seçici. Ayar içi ince ayarlar bu yüzden hep RED çıkıyor.

**Sonuç:** Mevcut verilerle "yeni ve bağımsız" kalan alan dar. Aşağıdaki 5 hipotez, taramada **daha önce test edilmediği doğrulanan** eksenler.

---

## 2. Beş yeni hipotez

### H1 — "Gerçek yaş": tokenin spot geçmişine göre yaş eşiği
1. **Ek kâr nereden:**
   - Yaş eşiği (60 g), yeni listelenen coinin fiyat keşfi riskini (çöküş / sıkışma) dışarıda tutuyor.
   - Ama perp'ten **çok önce Binance spot'ta işlem gören** bir token gerçekte "yeni" değil: fiyat keşfini spotta tamamlamış.
   - Bu tokenler 60 günden önce evrene alınırsa, genç-perp avantajının (yüksek funding, oynaklık, TP) bir kısmı, yeni-token kuyruğu olmadan alınabilir.
   - Tersine, **hiç spotu olmayan** perp-only tokenlerde kuyruk daha kalın (SPOT_SART'ın gerekçesi, madde 389 civarı) ve bunlar için eşik uzatılabilir.
2. **Öncekilerden farkı:**
   - 652 / 664 yaş eşiğini **herkes için** gevşetti ya da sıkılaştırdı.
   - 461 genç coinleri kısmi ağırlıkla aldı.
   - SPOT_SART yalnız "spotu var / yok" filtresiydi; 394 ise spot listeleme **olayını** test etti.
   - **Yaşın kendisini tokenin gerçek piyasa geçmişiyle yeniden tanımlamak** denenmedi.
3. **Veri:**
   - `data_spot_ilk_gun.json`: 850 perp'in ilk Binance spot günü (delist olanlar dahil).
   - 2021+ listelenen 622 perp'in 156'sının spotu perp'ten 60 günden fazla önce, 240'ının yakın ya da sonra; 226'sının spotu yok.
   - Panel YAS.
4. **Look-ahead:** düşük. Spot ilk günü, perp listelendiğinde zaten geçmişte; kural o barda bilinen bilgiyle çalışır.
5. **Survivorship:** düşük. Spot verisi 850 sembolü kapsıyor, delist olanlar dahil. Sınır: yalnız Binance spot; başka borsalardaki geçmiş görülmez [VARSAYIM].
6. **Dönem:** 2021-01 → 2026-09, iki dönem (≤2024 / 2025+), iki hiza.
7. **Long / short:** iki tarafı da etkiler. Spot geçmişli tokenlerde short sıkışması daha az beklenir [HİPOTEZ].
8. **Kuyruk:** spot geçmişliler için erken giriş kuyruğu artırabilir (652'nin uyarısı). Spot'suzlar için geç giriş kuyruğu azaltır.
9. **Ret:** eşit-risk < P3T2 + 8, ya da iki dönemden birinde Sharpe düşerse, ya da kazanç tek coinden / tek yıldan gelirse.
10. **Başarı:** eşit-risk ≥ +8 **ve** iki dönemde Sharpe ≥ taban **ve** en kötü gün / maks DD bozulmuyor **ve** ilk 3 coin çıkarılınca da artı.

**Kollar (tek eksen, en çok 2):**

| Kol | Kural |
|---|---|
| A | Spotu perp'ten ≥ 365 g önce açılmış tokenlerde perp yaş eşiği 60 → 14 g |
| B | Spotu olmayan tokenlerde 60 → 90 g |

### H2 — Genç short yoğunlaşma sınırı (kuyruk kırpma, aynı getiri)
1. **Ek kâr nereden:**
   - 697 T4: genç (60-180 g) short'larda +%100 sıçrama riski eski coinlerin ~10 katı; en kötü coin-gün −%8,7.
   - Genç short'lar aynı gün kümeleniyor: ≥ 2 genç short'un aynı gün kaybettiği 55 gün var.
   - Bir dilimde aynı anda en çok k genç short (kalan yer sıradaki short adayına) kuyruğu kırpabilir.
   - Eşit risk kaldıraç sınırını gevşetirse getiri eşit riskte artar.
2. **Öncekilerden farkı:**
   - 664 genç short'u **tamamen dışladı** (RED: en kârlı grup).
   - CAP_ORTAK **coin başına** tavan.
   - 667 korelasyonla çeşitlendirme (short'ta felaket).
   - **Sayı sınırı** (yaş grubu başına) denenmedi.
3. **Veri:** mevcut panel ve YAS. Yeni veri gerekmiyor.
4. **Look-ahead:** yok; yaş o barda bilinen.
5. **Survivorship:** düşük (aynı zemin).
6. **Dönem:** 2021-01 → 2026-09.
7. **Long / short:** yalnız short tarafı. Long değişmez.
8. **Kuyruk:** azaltması bekleniyor. Ama 699 / 611 dersi geçerli: sıkışan short'u kesmek ortalamada kaybettiriyor; burada kesme değil, **giriş sınırı** test ediliyor.
9. **Ret:** eşit-risk < +8, ya da 2025+ Sharpe düşerse (genç coinlerin yoğun olduğu dönem).
10. **Başarı:** H1 ile aynı ölçüt; ek olarak en kötü gün ve 1 yıl p1 iyileşmeli (hipotezin mekanizması).

**Kollar:** k = 2 / 3 genç short (dilim başına).

### H3 — Kalabalığın çözülme hızı (long/short oranının değişimi)
1. **Ek kâr nereden:** Kalabalığın **seviyesi** (627) seçimin değerini taşıyor. Kalabalık hızla çözülürken (long oranı sert düşerken) short'a girmek
   geç kalmak olabilir; çözülme henüz başlamamış adayı tercih etmek fayda sağlayabilir.
2. **Öncekilerden farkı:**
   - 627 / 649 seviye kullandı.
   - 389'da "ls" ve "OI değişimi" ML'in 18 özelliğinden ikisiydi, ama ayrı bir kitap olarak, carry'nin içinde değil.
   - Carry'nin aday seçiminde **değişim** denenmedi.
3. **Veri:** `metrik_panel` long/short oranı. **Zayıf:** ilk geçerli değer 2022-02, 2023'te kapsam yalnız %19.
4. **Look-ahead:** düşük (4 sa gecikmeli metrik). Metrik zaman damgası doğrulanmalı [VARSAYIM].
5. **Survivorship:** orta. Metrik verisi eksik coinler sistematik olabilir.
6. **Dönem:** 2022-06 → 2026-09 (metrik kapsamı); IS ≤2024, OOS 2025+.
7. **Long / short:** iki taraf.
8. **Kuyruk:** belirsiz.
9. **Ret:** eşit-risk < +8 ya da kapsam %50 altı coinlerde sonuç farklıysa.
10. **Başarı:** standart ölçüt + kapsam yeterliliği.

### H4 — Alt piyasa oynaklığıyla orantılı doz (TP esnekliği)
1. **Ek kâr nereden:**
   - 691: TP kârı tutulan coinlerin oynaklığıyla yükseliyor (r 0,69, esneklik **1,89**).
   - Esneklik > 1 ise kitabın getiri / risk oranı oynaklık arttıkça artmalı.
   - Dozu alt evrenin gerçekleşen oynaklığına göre artırıp azaltmak Sharpe'ı artırabilir.
2. **Öncekilerden farkı:** 685 dozu **kitabın kendi** oynaklığına göre **ters yönde** ölçekledi (V20 / V60; 2025+'da kâr kesti). Evrenin oynaklığına göre
   **aynı yönde** ölçekleme denenmedi.
3. **Veri:** panel (fiyat). Örtü: günlük seri × ölçek.
4. **Look-ahead:** düşük; t günü ölçeği t−1'e kadarki oynaklıkla. Normalizasyon kayan medyanla (tam örnek değil).
5. **Survivorship:** düşük.
6. **Dönem:** 2020-07 → 2026-09.
7. **Long / short:** iki taraf eşit.
8. **Kuyruk:** **artırma riski yüksek.** Oynaklık çöküşlerde de yükselir; en kötü günler büyüyebilir.
9. **Ret:** eşit-risk < +8 ya da en kötü gün kötüleşirse.
10. **Başarı:** standart ölçüt.

**Not:** 685'te ters yön (V60) eşit riskte +351 ama Sharpe şartı RED'di. Bu bilgi aynı yönün de büyük ihtimalle başarısız olacağını düşündürüyor.
Önceden değeri düşük.

### H5 — Fırsat yoğunluğuna göre eski coin payı (697 E50), motorda doğrulama
1. **Ek kâr nereden:** Genç coin azken (n30 < 6) eski coin kolunu yarıya indirmek, genç coinlere dokunmadan kuraklık DD'sini sığlaştırıyordu (örtü).
2. **Öncekilerden farkı:** yeni değil. 697'nin **örtü** sonucunun motor içinde (sermaye yeniden dağılımı, TP davranışı) doğrulanması. "Yeterince derin
   incelenmemiş" sınıfında.
3. **Veri:** mevcut.
4. **Look-ahead:** düşük (n30 gecikmeli). Eşik 6 697'de ön kayıtlıydı; eşik 10 sonradan seçildi.
5. **Survivorship:** düşük.
6. **Dönem:** 2021-01 → 2026-09 + kuraklık dünyaları.
7. **Long / short:** eski coin bacakları (iki taraf).
8. **Kuyruk:** kuraklıkta azaltır; normal dönemde etkisi az.
9. **Ret:** eşit-risk < +8. 697 örtüsünde BAZ −4 puan ve DD biraz kötüleşmişti; büyük ihtimalle RED.
10. **Başarı:** standart ölçüt. Başarısız olsa bile kuraklık sigortası olarak bilgi değeri var.

---

## 3. Puanlama (1 = kötü, 5 = iyi; risk ve overfitting'de 5 = düşük risk)

| Hipotez | Potansiyel getiri | Risk artışı (5 = az) | Bağımsızlık | Veri güvenilirliği | Overfitting (5 = az) | Test maliyeti (5 = ucuz) | **Toplam / 30** |
|---|---|---|---|---|---|---|---|
| **H1 Gerçek yaş (spot geçmişi)** | 3 | 3 | **5** | 4 | 4 | 4 (6 motor koşusu) | **23** |
| H2 Genç short sayı sınırı | 3 | **4** | 4 | 5 | 4 | 4 (6 koşu) | **24** |
| H3 Kalabalık çözülme hızı | 3 | 3 | 4 | **2** | 3 | 3 | 18 |
| H4 Alt oynaklığa orantılı doz | 2 | **2** | 3 | 5 | 3 | **5** (örtü) | 20 |
| H5 E50 motor doğrulaması | 2 | 4 | **1** | 5 | 3 | 4 | 19 |

**Seçim:**
- **H2** puanda bir adım önde, ama mekanizması tamamen önceki araştırmanın (697 T4) tanı bulgusuna dayanıyor ve 664 / 611 / 699 aynı aileden üç RED.
- **H1** tek gerçekten **yeni veri boyutu**: tokenin spot geçmişi, yaşın yeniden tanımı. Kullanıcının "yaşa göre getiri davranışı" alanında,
  denenmemiş bir yönden geliyor. Veri tam (delist dahil 850 sembol); kural basit, en çok 2 kol.
- **Önerilen ilk test: H1.** İkinci sırada H2. H3 veri yetersizliği yüzünden şimdilik ertelendi. H4 ve H5'in önceden değeri düşük.

---

## 4. Disiplin (bütün hipotezler için)
- Orijinal strateji ve motor dosyalarına dokunulmaz; ayrı motor kopyası kullanılır, düğme kapalıyken iki hizada bayt bayt parite şart.
- Hipotez, kollar ve kabul ölçütleri **sonuçlardan önce** KAR_HARITASI'na ön kayıt olarak yazılır.
- Tek eksen, en çok 2 kol; varyant taraması yok.
- Eksik ya da başarısız koşu geçerli sayılmaz. RED de raporlanır.
- Kabul ölçütü: eşit-risk ≥ P3T2 + 8 **ve** Sharpe ≤2024 ve 2025+ düşmüyor **ve** maks DD / en kötü gün kabul edilebilir **ve** kazanç ilk 3 coin çıkarılınca
  ve tek yıl çıkarılınca da artı.
- ADAY çıksa bile Ekim+ verisiyle ileriye dönük doğrulama olmadan bota girmez.
