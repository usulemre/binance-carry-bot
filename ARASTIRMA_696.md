# Araştırma 696 — Listeleme kuraklığında sermaye koruma (1 Kasım 2026)

> Soru (kullanıcı): "Binance'in yeni coin listeleme hızının düştüğü bir yılda da sermayeyi koruyabilen bir sistem."

## Değişmeyenler ve kontroller
Ana strateji kodu, parametreler, motor dosyaları ve canlı sistem **DEĞİŞMEDİ**. Filtre ya da kapı eklenmedi.

- **Araç:** `arastirma_m696_kuraklik.py`.
  - `analiz`: ön kayıtlı test.
  - `ek`: ön kayıt dışı tarama.
- **Ön kayıt:** KAR_HARITASI "Madde 696 ÖN KAYIT". Savunma sonuçları görülmeden yazıldı ve gönderildi (commit f9d34d4).
- **Yeni motor koşusu yok.** Kuraklık dünyaları, madde 694 ve 695'te koşulmuş motor çıktıları:
  - Her biri iki hizada.
  - O raporlarda parite bayt bayt doğrulanmıştı.
  - Hepsi tamamlanmış koşular.
- **Kontrol:** DUR25 (694) ile A_DUR180 (695) aynı coinleri çıkarıyor; günlük serileri birebir aynı (fark 0).
- **Dönem:** 2021-01-01 → 2026-09-30. 2026 dokuz aylık.
- **Git:** strateji ve motor dosyalarında diff yok.

**Yöntem:**
- Savunmalar kitap düzeyinde bir örtü olarak uygulandı: günlük getiri × ölçek s.
- s yalnız bir önceki güne kadarki veriyle hesaplanıyor.
- Ölçek değişiminin maliyeti 10 bp × |Δs|; ölçek ancak |Δs| ≥ 0,05 ise değişiyor.
- **VARSAYIM:** boşalan sermaye %0 getiri. Duyarlılık olarak %5 de hesaplandı.
- Örtü, motorun içindeki etkileşimi (ör. küçük pozisyonda kademe davranışı) modellemiyor; bu nedenle yaklaşık.

Etiketler: **ÖLÇÜM** veriden ya da motordan · **VARSAYIM** senaryo veya model varsayımı · **HİPOTEZ** doğrulanmamış açıklama.

---

## Kısa cevap
1. **Mevcut strateji kuraklık dünyalarının hiçbirinde takvim yılı bazında zarar etmiyor [ÖLÇÜM].**
   - En kötü yıl %18,5: Y365K 2025; Y365K = hiç genç coin olmayan, en uç dünya.
   - Asıl sorun düşüşün derinleşmesi:
     - Maks düşüş −%13'ten −%16..−22'ye çıkıyor.
     - Su altında kalma süresi 306 güne kadar uzuyor.
     - En uç dünyada en kötü 365 gün −%9,7.
2. **Ön kayıtlı dört savunmanın hiçbiri şartları geçmedi.**
   - Hiçbiri yedi kuraklık dünyasının hepsinde aynı anda şunları sağlayamadı: maks DD ≥ −%15, en kötü 365 gün ≥ 0 ve 1 yılda zarar olasılığı ≤ %1.
3. **Yapısal sınır [ÖLÇÜM]:**
   - Doz kısmak düşüşün derinliğini küçültüyor, kazanılan yılın işaretini değiştirmiyor.
   - En uç dünyada 1 yıllık zarar olasılığı her dozda ~%1,4-1,9.
   - En kötü 365 gün her dozda negatif: 1,0x'te −%9,7, 0,5x'te −%4,3.
   - "Hiç zarar etmeyen yıl" garantisi, kuralla değil ancak eski coinlerdeki kenarın kendisini iyileştirerek alınabilir.
4. **Gerçek dünyada bugünkü durum [ÖLÇÜM]:**
   - Botun işlem yapabileceği genç coin sayısı (60-365 gün, 70M hacim) 30 günlük ortalamada **5,1**. Bu 2022'den beri en düşük düzey.
   - 2024-25'te bu sayı 15-27 arasıydı.
   - Toplam listeleme sayısı yüksek (694: ~160 / yıl), ama hacim eşiğine ulaşan genç coin azalmış.

---

## 1. Teşhis: kuraklıkta ne bozuluyor [ÖLÇÜM]

| Dünya | CAGR | Sharpe | Maks DD | En kötü ay | En kötü 365 g | 365 g pencerelerinde zarar % | En uzun su altı (g) | Yıllık 2021 / 22 / 23 / 24 / 25 / 26 |
|---|---|---|---|---|---|---|---|---|
| BAZ | 242 | 4,06 | −13,3 | −6,6 | +46,5 | 0 | 131 | 472 / 63 / 310 / 118 / 267 / 283 |
| L25_a (hafif) | 201 | 3,78 | −14,9 | −5,3 | +35,4 | 0 | 116 | 438 / 69 / 246 / 118 / 226 / 153 |
| L50_a | 150 | 3,41 | −16,8 | −8,0 | +19,5 | 0 | 123 | 474 / 67 / 184 / 167 / 115 / 24 |
| L50_b | 158 | 3,59 | −19,5 | −8,0 | +21,2 | 0 | 240 | 465 / 47 / 278 / 103 / 52 / 140 |
| L75_a | 126 | 3,11 | −16,9 | −11,9 | +6,7 | 0 | 134 | 454 / 68 / 175 / 61 / 19 / 122 |
| L75_b | 102 | 2,73 | −22,3 | −8,5 | +6,1 | 0 | 199 | 360 / 28 / 143 / 65 / 27 / 91 |
| DUR24 | 240 | 4,07 | −13,3 | −6,6 | +46,5 | 0 | 131 | 472 / 63 / 310 / 103 / 278 / 284 |
| DUR25 | 190 | 3,66 | −15,9 | −7,8 | +46,5 | 0 | 179 | 472 / 63 / 310 / 118 / 80 / 203 |
| **Y365K** | 81 | 2,39 | −21,2 | −11,4 | **−9,7** | 1,7 | 306 | 146 / 50 / 168 / 94 / 19 / 34 |

Dünya tanımları (694 / 695):
- **L25 / L50 / L75:** 2021+ listelenen coinlerin %25 / 50 / 75'i rastgele evrenden çıkarıldı; a ve b iki ayrı çekiliş.
- **DUR24 / DUR25:** 2024-H1 / 2025-H1'de listelenen bütün coinler çıkarıldı.
- **Y365K:** evrene giriş için asgari yaş 365 gün; yani hiç genç coin yok.

**Kaybın kaynağı (Y365K, puan, iki hiza ortalaması):**
- Long fiyat bacağı 2025'te −41, 2026'da −38. Long funding'i +28 / +45 ile kısmen kapatıyor.
- Short iki yılda da pozitif: +40 / +31.
- Derin düşüşler 2025 yazında toplanıyor:
  - L50_b, L75_b, DUR25 ve L75_a'da tepe 2025-03 ile 2025-07 arasında, dip 2025-09'da.
  - Y365K'nın düşüşü 2026-07 → 2026-08.
- **HİPOTEZ:** alt piyasa düşüşünde eski coinlerin long tarafı değer kaybediyor. Genç coinlerin TP hasadı olmadığında bunu telafi eden bir şey
  kalmıyor.

**"Eski coinde long kapat" neden koşulmadı:**
- Eski coin (> 2 yıl) long bacağı 2024-26'da baz dünyada −28 fiyat / +27 funding ile yaklaşık sıfır.
- Ama 2021-23'te +57 fiyat / +37 funding ile güçlü pozitif.
- Bu kural geçmişin yalnız bir yarısına uyar, yapısal değil.
- Ayrıştırmadan sonucu belli: 2021-23'te ~−100, 2024-26'da ~+5 puan. Ön kayıtta koşulmayacağı yazıldı.

---

## 2. Gösterge: botun işlem yapabileceği genç coin sayısı [ÖLÇÜM]

**Tanım:**
- n = evrende (70M hacim, 60 gün yaş, donukluk filtresi, TradFi / D8 hariç, o dünyanın çıkardıkları hariç) 60-365 gün yaşında coin sayısı.
- 30 günlük ortalaması, bir gün gecikmeli; o gün bilinen bir değer.

| Çeyrek sonu | 21-Q2 | 21-Q4 | 22-Q2 | 22-Q4 | 23-Q2 | 23-Q4 | 24-Q2 | 24-Q4 | 25-Q2 | 25-Q4 | 26-Q1 | 26-Q2 | 26-Q3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n30 (gerçek dünya) | 19,1 | 19,9 | 6,8 | 4,0 | 9,2 | 14,6 | 16,9 | 23,8 | 15,0 | 14,3 | 10,4 | 8,4 | **5,1** |

- **Gerçek dünyada son aylar:**

  | Ay | Baz aylık getiri | n30 |
  |---|---|---|
  | 2026-07 | +%0,8 | 5,2 |
  | 2026-08 | +%9,0 | 5,8 |
  | 2026-09 | +%7,3 | 5,1 |
  | 2026 H1 aylık aralığı | +%8 … +%37 | — |

  - Düşük n dönemlerinde (K1 kısıkken) kitabın günlük ortalaması 20 bp; diğer günlerde 37 bp.
  - Yani getiri düşüyor ama negatif değil.
  - **694'ün uyarısı geçerli:** zaman eğilimi çıkarılınca n getiriyi öngörmüyordu. Burada da nedensellik iddiası yok.

---

## 3. Ön kayıtlı savunmalar ve sonuç

**Kollar:**

| Kol | Ölçek s |
|---|---|
| K1 KURAK | clip(n30 / 6, 0,5, 1). Genç coin azalınca doz kısılır; 6 ≈ baz dünyada 2021-23 %10'luğu |
| K2 DDA2 | max(0,5 ; 1 + 3 × dd). Zirveden düşüşte doz kısılır (madde 685 kolu) |
| K3 V60K | clip(σ* / σ60, 0,5, 1). Oynaklık artınca kısılır, yalnız azaltır |
| K4 | K1 × K2, taban 0,25 |

**Ön kayıt şartları:**
- Yedi kuraklık dünyasının hepsinde en kötü 365 gün ≥ 0, maks DD ≥ −%15 ve bootstrap 1 yılda zarar olasılığı ≤ %1.
- **VE** normal dünyada CAGR bazın %90'ından az değil ve maks DD bazdan kötü değil.

| Kol | Kuraklık: en kötü 365 g (min) | 365 g şartı | Kuraklık: maks DD (min) | DD şartı | Bootstrap zarar maks | Bootstrap şartı | Kuraklık CAGR medyan | BAZ CAGR (oran) | BAZ DD | Sonuç |
|---|---|---|---|---|---|---|---|---|---|---|
| K0 baz | −9,7 | 6 / 7 | −22,3 | 1 / 7 | %1,6 | 6 / 7 | 150 | 242 (1,00) | −13,3 | — |
| K1 KURAK | −4,3 | 6 / 7 | −20,1 | 4 / 7 | %1,0 | 7 / 7 | 132 | 238 (0,98) | −13,3 | **RED** |
| K2 DDA2 | −15,0 | 5 / 7 | −17,3 | 4 / 7 | %1,7 | 6 / 7 | 131 | 210 (0,87) | −11,9 | **RED** |
| K3 V60K | −8,2 | 6 / 7 | −21,4 | 2 / 7 | %1,2 | 6 / 7 | 132 | 193 (0,80) | −10,7 | **RED** |
| K4 K1×K2 | −6,8 | 5 / 7 | −16,6 | 5 / 7 | %1,6 | 6 / 7 | 117 | 207 (0,85) | −11,9 | **RED** |

**Ayrıntılar [ÖLÇÜM]:**
- **K1, normal dünyada en ucuz kol:** −4 puan; baz dünyada günlerin %9,6'sında kısık (2022'de %29, 2026'da %27).
- **K1 kuraklık dünyalarında Sharpe'ı hafifçe artırıyor:**
  - L50_a 3,41 → 3,56.
  - L75_a 3,11 → 3,32.
  - L75_b 2,73 → 2,81.
  - Gösterge bir miktar bilgi taşıyor.
- **K1 en uç dünyada DD'yi yarıya indiriyor:** Y365K −21,2 → −11,1.
- **Ama L50_b, L75_b ve DUR25'te 2025 yazı düşüşünü kaçırıyor;** o aralıkta ortalama s 0,94-1,00. Nedeni şu:
  - Kuraklık başladığında önceki yılın coinleri hâlâ "genç".
  - Bu yüzden gösterge ~6-12 ay gecikiyor.
  - Rastgele çekilişlerde de sayı 6'nın üstünde kalıyor.
- **K2 (düşüş freni):** Y365K'da en kötü 365 günü −9,7'den −15,0'e **kötüleştiriyor**. Dipte doz kısıp toparlanmayı kaçırıyor; 539 / 685
  bulgularıyla aynı. Normal dünyada da −32 puan.
- **K3 (oynaklık hedefi):** normal dünyada en pahalısı (−49 puan). Kuraklık DD'sine neredeyse etkisi yok, çünkü kuraklık düşüşleri yüksek
  oynaklıkla gelmiyor.
- **Nakit %5 duyarlılığı:** sıralamayı değiştirmiyor. Örneğin K1'de kuraklık medyanı CAGR 132 → 134; şart sonuçları aynı.

**Sınıf:** dört kol **RED**. Ön kayıt gereği bota girmez.

---

## 4. Ön kayıt dışı (sonuçlar görüldükten sonra): ailenin sınırı
Bu bölüm seçim değildir. Doz kısma ailesinin şartlara ulaşıp ulaşamayacağını görmek için tarama yapıldı. Sonradan görüldüğü için **HİPOTEZ**.

**K1 eşiği (N_REF) taraması:**

| N_REF | BAZ CAGR | BAZ DD | Kuraklık CAGR med | Kuraklık DD min | DD ≥ −15 | En kötü 365 g min | Bootstrap zarar maks |
|---|---|---|---|---|---|---|---|
| 4 | 242 | −13,3 | 144 | −22,1 | 4 / 7 | −4,3 | %1,6 |
| 6 (ön kayıt) | 238 | −13,3 | 132 | −20,1 | 4 / 7 | −4,3 | %1,7 |
| 8 | 221 | −12,1 | 117 | −17,0 | 5 / 7 | −4,3 | %1,0 |
| **10** | **206** | −12,1 | 105 | **−14,5** | **7 / 7** | −4,3 | %1,4 |
| 12 | 193 | −12,2 | 99 | −13,0 | 7 / 7 | −4,3 | %1,5 |
| 15 | 171 | −11,9 | 92 | −12,0 | 7 / 7 | −4,3 | %1,5 |

**Sabit doz (kural değil, aritmetik):**

| Doz | BAZ CAGR | BAZ DD | Kuraklık CAGR med | Kuraklık DD min | DD ≥ −15 | En kötü 365 g min | Bootstrap zarar maks |
|---|---|---|---|---|---|---|---|
| 1,00 | 242 | −13,3 | 150 | −22,3 | 1 / 7 | −9,7 | %1,7 |
| 0,85 | 186 | −11,4 | 119 | −19,3 | 4 / 7 | −8,0 | %2,2 |
| 0,75 | 154 | −10,1 | 100 | −17,2 | 5 / 7 | −6,9 | %1,4 |
| 0,67 | 131 | −9,0 | 86 | −15,5 | 6 / 7 | −6,0 | %1,9 |
| **0,60** | **112** | −8,1 | 75 | **−14,0** | **7 / 7** | −5,3 | %1,5 |
| 0,50 | 87 | −6,8 | 60 | −11,8 | 7 / 7 | −4,3 | %1,4 |

(Bootstrap 2.000 simülasyon; zarar olasılığındaki ±0,3 puanlık oynama örnekleme gürültüsü.)

**Okuma:**
- **Kuraklık DD şartı** (yedi dünyada DD ≥ −%15) iki yoldan sağlanabiliyor:
  - Sabit dozla: 0,6x gerekiyor ve normal dünya getirisi %242 → %112 (−%54).
  - Genç coin göstergesine bağlı dozla (N_REF 10): normal dünya %242 → %206 (−%15).
  - **Göstergeye bağlı doz, sabit doza göre ~3-4 kat daha verimli bir sigorta.**
- **Ama iki şart hiçbir dozda sağlanmıyor:**
  - En kötü 365 gün ≥ 0 (Y365K'da her dozda negatif).
  - Zarar olasılığı ≤ %1 (Y365K'da ~%1,4-1,9).
  - Kenar zayıfladığında doz kaybı küçültür, yok etmez.
- **N_REF 10 bugün ne yapardı [ÖLÇÜM]:**
  - Bugün ölçek 0,54 olurdu: n30 5,1.
  - Gerçek dünyada 2023 %310 → %178 ve 2026 %283 → %239 olurdu.
  - 2026-Q3'te çeyrek %17,9 → %10,2 olurdu.
  - Sigortanın bedeli, kuraklık yaşanmayan yıllarda ödeniyor.

---

## 5. Sonuç ve öneri

**Ölçülen:**
- Strateji listeleme kuraklığında sermayeyi takvim yılı bazında koruyor.
- Getiri yarıya ya da üçte birine düşüyor; düşüş −%22'ye, su altı 10 aya kadar uzayabiliyor.
- Hiç genç coin olmayan uç dünyada 12 aylık bir dönem −%10'a kadar zararda kalabiliyor.

**Bulunamayan:**
- Normal yıllarda bedava, kuraklıkta ise sermayeyi tam koruyan bir kural.
- Ön kayıtlı dört kol RED.

**En umut veren yön (HİPOTEZ, sonradan):**
- Doz, botun işlem yapabileceği genç coin sayısına bağlanabilir (eşik ~10).
- Kuraklık düşüşünü 7 / 7 dünyada −%15'in içinde tutuyor; normal dünyada %15 getiriye mal oluyor.
- Sonradan seçildiği için **bota girmez**.
- Ön kayıtla ileriye dönük izlenebilir (madde 685 DDA2 gibi): Ekim-Aralık verisinde n30 ve "K1 @10 olsaydı" getirisi raporlanır.
- Bu izlemeyi başlatmak kullanıcı kararı.

**Yapısal çözüm başka yerde:**
- Kuraklıkta zarar ihtimalini sıfıra yaklaştırmak için eski coin kitabının kenarını iyileştirmek gerekiyor.
- 2024-26'da eski coin long'u fiyatta kaybediyor.
- Bu ayrı bir araştırma konusu: neden kaybettiği, rejime mi bağlı.

**Demo izleme metriği (ekle):**
- n30 (botun evreninde 60-365 gün yaşında coin sayısı, 30 günlük ortalama).
- Bugün 5,1. 2022'deki dip 4,0.
- Bu sayı ~6'nın altında kalırken aylık getiri ve DD özellikle izlenmeli.
- Otomatik kapı DEĞİL.

---

## Sınırlar
- Kuraklık dünyaları karşı-olgu.
  - Gerçek bir kuraklıkta piyasanın kendisi de değişebilir: hacim, funding, oynaklık.
  - Burada yalnız o coinlerin hiç gelmediği varsayıldı [VARSAYIM].
- Savunmalar kitap düzeyinde örtü; motor içi etkileşim modellenmedi.
- Histerezis yüzünden ölçek 1'in hemen altında (0,95-0,999) takılı kalabiliyor. Bu nedenle sonradan taramada "kısık gün payı" raporlanmadı;
  getiri etkisi bu kalıntıyı içeriyor.
- K3'ün σ* sabiti tam örnek medyanı (madde 685 ile aynı yaklaşım); seviye için hafif gelecek bilgisi.
- Delist geçmişinin veri setinde eksiksiz olduğu doğrulanamadı (694 ile aynı) [VARSAYIM].
