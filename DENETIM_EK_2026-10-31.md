# Denetim ek testleri — tek coin kuyruk riski ve funding iyimserliği (31 Ekim 2026)

Önceki denetimin (DENETIM_2026-10-31.md) devamı. Kaynak kod, strateji ve parametreler DEĞİŞTİRİLMEDİ; KAR_HARITASI'na yalnız ekleme
yapıldı. Ölçümler iki yeni araştırma betiğiyle yeniden üretilebilir (en sonda komutlar).
Etiketler: **[gerçek]** geçmiş veride gözlendi · **[varsayımsal]** gözlenmedi, senaryo · **[varsayım]** kanıtlanamayan girdi.

---

## TEST 1 — Tek coin kuyruk riski (`arastirma_m689_tek_coin_stres.py`)

**Girdi:** önerilen ayarın gerçek pozisyon defteri (`/tmp/m621/pozKS_{0,1}.pkl`), iki hiza, 27.173 portföy durumu, 2020-07 → 2026-09.
Ağırlıklar özkaynak payı; önerilen doz için ×1,15. Bakiye 2.000 $.

**Varsayımlar [varsayım]:**
- Bakım teminatı oranı (MMR): altcoinlerde %2,5, çöken coinde %5 (Binance'in küçük notional kademeleri ~%1-5).
- Teminat modu: çapraz teminat.
- Tasfiye: özkaynak ≤ Σ|notional| × MMR olduğunda.
- Şoklar anlık; gün içi toparlanma yok.

### 1.1 Gerçek portföy yoğunlaşması [gerçek]
- **En büyük tek long, özkaynağın:** medyan %9,8 · %99 dilim %16,4 · en fazla %21,4.
- **Brüt:** medyan 0,84x.

(Önceki raporun "brütün %34'ü" ifadesi brüte göreydi; özkaynağa göre en fazla %21,4.)

### 1.2 Geçmişte gerçekleşmiş tek coin çöküşleri [gerçek]
- **Sayım:** tutulan long'larda 24 saat içinde ≥ %50 düşüş 289 kez görüldü. 34 farklı coin, ör. ANC, FTT, BAN, BANK, LAB, POWER, REEF, SIREN.
- **Ağırlık 24 saat SABİT tutulsaydı en kötü durumlar** (kâr al / kademe / stop yok sayılarak):

| Tarih | Coin | Pay | Coin 24 sa | Piyasa 24 sa | Özkaynak |
|---|---|---|---|---|---|
| 2026-03-02 | POWER | %15,9 | −%86 | −%2,1 | −%13,7 |
| 2024-10-14 | REEF | %13,8 | −%63 | −%1,8 | −%8,7 |
| 2026-03-31 | SIREN | %7,7 | −%82 | +%2,7 | −%6,3 |

- **Defterdeki gerçek ağırlıklarla GERÇEKLEŞEN en kötü tek coin, 24 saat:**
  - IOTX (2021-11-09): −%12,3
  - REEF: −%8,7
  - AIOT: −%8,1
  - BTW: −%7,6
  - SIREN: −%7,5
- **POWER olayının ayrıntısı:** coin önce +%47 yükseldi. Kademe kâr al pozisyonun %80'ini çökmeden ÖNCE sattı (pay %13,8 → %2,9). Kitap
  o gün +%8-9 kazandı, ertesi gün −%4 kaybetti. Yani sabit ağırlık varsayımı abartılı; kademe gerçek bir koruma.
- **Gerçekleşen çöküşlerin çoğu piyasa yatayken oldu** (evren medyanı −%2 … +%3). Koşullu 24 saat stop (piyasa ≤ −%3 şartı) bu olayların
  hiçbirinde tetiklenmezdi.

### 1.3 Senaryolar
- **Durumlar:** en büyük long'u en yüksek 5 gerçek durum (BLZ %21,4 · TRB %20,5 · OGN %19,5 · ENSO %19,2 · BEL %18,8), %99'luk dilim
  (CKB %16,4) ve medyan (HOME %9,8).
- **Piyasa çöküş girdisi [gerçek]:** BTC'nin en kötü günlerinde (2021-01-11, 2021-12-04, 2022-06-13) likit evrenin medyan 24 saatlik
  getirisi −%20,2 / −%26,8 / −%16,2; ortalama **−%21**. 2020 Mart günlerinde evren filtresi boş olduğu için hesap dışı.

Özkaynak kaybı, 7 durumda en az / en çok:

| Senaryo | Kayıp % (min – maks) | Bakım / özkaynak (maks) | Tasfiye | Etiket |
|---|---|---|---|---|
| A1 coin −%50, piyasa yatay | 4,9 – 10,7 | %2,9 | hayır | coin hareketi gerçek, anlık şok varsayımsal |
| A2 coin −%80, piyasa yatay | 7,9 – 17,1 | %2,8 | hayır | coin hareketi gerçek, anlık şok varsayımsal |
| A3 coin −%95, piyasa yatay | 9,3 – 20,3 | %2,7 | hayır | varsayımsal |
| B1 −%50 + BTC çöküş günü (diğerleri −%21) | 5,3 – 10,6 | %2,4 | hayır | piyasa girdisi gerçek, birleşim varsayımsal |
| B2 −%80 + çöküş, koşullu stop çalışır (−%45 + %5 kayma) | 5,3 – 10,6 | %1,9 | hayır | varsayımsal |
| B3 −%80 + çöküş, stop çalışmaz | 8,2 – 16,7 | %2,2 | hayır | varsayımsal |
| B4 −%95 + çöküş, stop çalışmaz | 9,7 – 19,8 | %2,1 | hayır | varsayımsal |
| C1 likidite kaybı: stop tetiklenir, dolum −%70 | 7,2 – 14,7 | %1,9 | hayır | varsayımsal |
| D1 −%80 + 2. büyük long −%50, piyasa yatay | 10,9 – 23,2 | %3,0 | hayır | varsayımsal |
| D2 −%80 + diğer longlar −%20, shortlar −%5 (ayrışma) | 12,3 – 22,3 | %2,6 | hayır | varsayımsal |
| D3 −%95 + diğer longlar −%30, shortlar 0 | 18,1 – 31,0 | %2,7 | hayır | varsayımsal |

**En kötü durumda (BLZ, %21,4) 2.000 $ için:**
- **A2:** gün sonu 1.658 $, toparlanma için +%20,6 gerekir.
- **D1:** gün sonu 1.535 $, +%30,3 gerekir.
- **D3:** gün sonu 1.381 $, +%44,8 gerekir.

Brüt pozisyon şoktan sonra 0,97x'ten en fazla 1,04x'e çıkıyor (D1). Bakım teminatı / özkaynak en fazla %3; tasfiye **hiçbir senaryoda
yok**. Tasfiye için tek günde ~%95'in üzerinde kayıp gerekir.

### 1.4 Test 1 hükmü
- **Tasfiye:** risk değil.
- **Asıl risk:** tek günde **−%10 ile −%20** (tek coin), iki coin ya da ayrışmalı piyasada **−%20 ile −%31** kayıp.
  - Bunun yarısı gerçekleşmiş: geçmişte tek coinden −%12,3.
  - Diğer yarısı (−%95 çöküş, iki coin birden, kalabalık shortların düşmediği çöküş) varsayımsal.
- **Ayrışma senaryosu (D2 / D3) en tehlikelisi:** BTC çöküşünde shortlar long'lar kadar düşerse kitap korunuyor (B1). Long'lar çöküp
  shortlar yerinde kalırsa korunmuyor. Bu kombinasyon defterde görülmedi, ama mekanizma olarak mümkün.
- **Geçmiş en kötü gün (−%8,5)** bu dağılımın iyimser ucunda.

---

## TEST 2 — Funding iyimserliği (`arastirma_m688_funding_notr.py`)

**Yöntem:** `g33.py` DEĞİŞMEDİ. `/tmp/g33_m688.py` kopyasında yalnız funding satırı ortam değişkenine (FUND_MOD) bağlandı. Üç koşu:
- **A:** mevcut yöntem.
- **B:** istenen nötr koşu. O barda yeni açılan / büyütülen kısım, bar açılışında TAM damgalı ödemeyi almaz. Bar içi çıkan pozisyona
  ödeme hâlâ yazılmaz, yani en kötümser.
- **C:** zaman damgası doğru. T anındaki ödemeyi T'den önce açık olan kısım alır (bar içinde TP / stop ile çıkan dahil), yeni kısım almaz.
  Bar arasına düşen 1 / 4 saatlik ödemeler bar boyunca tutulana yazılır.

**Parite:** A koşusu her iki profil ve iki hizada mevcut sonuçlarla **BAYT BAYT AYNI**. Yöntem doğrulandı.

### 2.1 Tüm dönem (2020-07 → 2026-09, 2.000 $, 1,0x, iki hiza ortalaması)
| Koşu | P3T2 CAGR | Sharpe | maks DD | T4 CAGR | T4 Sharpe | P3T2 − T4 |
|---|---|---|---|---|---|---|
| A mevcut | +%247,5 | 4,14 | −%13,3 | +%244,3 | 3,84 | +3,1 |
| B nötr (istenen) | +%240,3 | 4,07 | −%13,4 | +%236,8 | 3,78 | +3,5 |
| C zaman damgası doğru | +%241,2 | 4,08 | −%13,4 | +%238,2 | 3,79 | +3,0 |

**Funding katkısı**, yıllık puanların toplamı:
- A: +763,6
- B: +725,9 (−37,8; −%4,9)
- C: +730,8 (−32,9)

### 2.2 Yıl yıl (P3T2)
Kısaltmalar: **f** = funding katkısı, **fiyat** = fiyat katkısı, **tp** = kâr al katkısı (yıllık puan). T4 farkı, P3T2 ile T4'ün CAGR farkı.

| Yıl | CAGR A / B / C | Sharpe A / B / C | f A / B / C | fiyat (A) | tp (A) | T4 farkı A / B / C |
|---|---|---|---|---|---|---|
| 2020* | +322 / +317 / +317 | 5,22 / 5,17 / 5,17 | 27,0 / 25,7 / 25,8 | +138,8 | +47,8 | +26 / +25 / +25 |
| 2021 | +472 / +464 / +465 | 6,06 / 6,01 / 6,02 | 52,5 / 48,6 / 49,1 | +378,4 | +143,7 | −48 / −46 / −46 |
| 2022 | +63 / +62 / +62 | 1,78 / 1,75 / 1,75 | 52,0 / 49,0 / 49,2 | +41,8 | +90,7 | +12 / +12 / +12 |
| 2023 | +310 / +302 / +304 | 4,74 / 4,68 / 4,69 | 131,7 / 126,2 / 127,6 | +238,2 | +90,9 | −13 / −12 / −13 |
| 2024 | +118 / +115 / +115 | 3,02 / 2,97 / 2,98 | 51,0 / 47,0 / 47,2 | +113,5 | +114,7 | −14 / −13 / −13 |
| 2025 | +268 / +255 / +256 | 4,03 / 3,92 / 3,93 | 210,4 / 199,4 / 200,6 | +59,3 | +174,7 | +43 / +42 / +42 |
| 2026* | +503 / +479 / +482 | 4,90 / 4,79 / 4,80 | 238,9 / 229,9 / 231,2 | +16,3 | +201,7 | −2 / 0 / −4 |

*2020 ve 2026 eksik yıl; CAGR yıllıklaştırılmış. Değerler 1,0x doz ve takvim yılı; önerilen 1,15x ile yapılan eski hesaplardan
(ör. madde 655) bu yüzden farklı.

### 2.3 Giriş anındaki ödeme canlıda alınabilir mi?
- **Binance kuralı:** USDⓈ-M sözleşmelerde funding, 8 saatlik coinlerde 00:00 / 08:00 / 16:00 UTC'de, o anda AÇIK pozisyona ödenir.
  4 / 1 saatlik coinlerde ödeme daha sık. Ödeme anından sonra açılan pozisyon o ödemeyi almaz.
- **Motor (A):** girişi bar kapanışında yapıyor. Hizalardan birinde bu an ödeme anıyla aynı; o ödemeyi pozisyona yazıyor, çıkış anındaki
  ödemeyi yazmıyor. 5 günlük tutuşta ödeme SAYISI doğru (15), ama hangi ödemelerin sayıldığı kaymış: seçim gereği uç olan giriş ödemesi
  sayılıyor, sönmüş çıkış ödemesi sayılmıyor.
- **Canlı bot:** turdan sonra sabit 8 saat bekliyor (`carry_bot.py:4829`, `time.sleep(REBALANCE_HOURS*3600/N_DILIM)`). Tur süresi her
  döngüde eklendiği için tur anı ödeme anlarına göre kayıyor, yani girişler günün her saatine dağılıyor.
  - Böyle bir girişte ilk ödeme 0-8 saat sonra gelir. 5 gün tutulan pozisyon yine ~15 ödeme alır; çıkıştan önceki son ödeme de dahil.
  - Bu yüzden **B ve C bir ödeme EKSİK sayıyor** (giriş ödemesini düşürüp çıkış ödemesini eklemiyorlar) ve kötümser. **A ise uç giriş
    ödemesini sayıp sönmüş çıkış ödemesini atladığı için iyimser.**
- **Sonuç:** gerçek değer A ile B / C arasında. Fark tüm dönemde ~6-7 CAGR puanı (+%247,5 → +%240-241), Sharpe −0,06. T4'e göre fark
  değişmiyor.
- Önceki raporun "%2-4 / yıl" tahmini yönde doğru, büyüklükte düşük kalmış: üst sınır ~%7 / yıl (1,0x).
- **[Kanıtlanmamış]:** canlıda maker emirlerin ödeme anının hemen öncesinde mi sonrasında mı dolduğu. Demo kaydıyla ölçülmeli.

### 2.4 Test 2 hükmü
Funding iyimserliği gerçek ama **küçük ve stratejinin sonucunu değiştirmiyor**: CAGR ~−%2,8 (göreli), Sharpe −0,06, düşüş aynı, T4 farkı
aynı. Yıl yıl tutarlı (her yıl −%1-5 göreli). Asıl öğretici olan ayrıştırma:
- **2020-2024:** kârın çoğu fiyat ve kâr al (TP).
- **2025-2026:** funding ve kâr al baskın, fiyat katkısı neredeyse sıfır (2026: fiyat +16, kâr al +202, funding +239).

Kâr al emirlerinin kârı yine fiyattan geliyor (sıçramada satış). Strateji son iki yılda "funding + sıçramalarda kâr al"a dönüşmüş.

---

## Yan bulgu — bellek (Test 2 koşuları sırasında) [gerçek]
- **Ne oldu:** 7 GB'lık araştırma ortamında iki P3T2 koşusu aynı anda çalışınca işletim sistemi koşuları öldürdü (dönüş kodu −9, bellek
  yetersiz).
- **Ölçüm:** tek koşunun tepe belleği eski motorda 2.872 MB, hızlandırılmış motorda (madde 681) 3.078 MB (+206 MB).
- **Önceki etkisi:** madde 681'in parite koşusunda 4 T7KKS dosyasının eksik kalmasının sebebi bu (o koşuda sessizce düştü).
- **Ekim kontrolüne etkisi:** 2 Kasım'daki Ekim kontrolü 2 işçiyle koşarsa önerilen ayarın kolu düşebilir. O koşu tek işçiyle yapılmalı ve
  çıktıların eksiksizliği kontrol edilmeli.
- **Kapsam:** bu rapor kapsamında kod değiştirilmedi.

---

## Soru: sürdürülebilirlik açısından en büyük risk hangisi?
**Kârın kaynağının değişkenliği. Tek coin kuyruğu ya da funding hesabı değil.** Kanıtlar:
1. **Funding iyimserliği küçük:** −6-7 CAGR puanı (Test 2). Stratejiyi taşıyan bu değil.
2. **Tek coin kuyruğu sınırlı ve hayatta kalınabilir:** tasfiye yok; en kötü gerçekçi tek gün −%10-20, varsayımsal uç −%31 (Test 1).
   Acı verir ama hesabı bitirmez. Toparlanma için +%12-45 gerekir; tarihsel en uzun toparlanma 132 gün.
3. **Kârın bileşimi yıldan yıla kökten değişiyor** (Test 2'nin ayrıştırması):
   - 2021'de kârın %66'sı fiyat, %25'i kâr al, %9'u funding'di.
   - 2026'da fiyat katkısı ~0; kâr funding ve kâr al emirlerinden.

   Yani "kenar" tek bir sabit mekanizma değil. Hangi bileşenin gelecekte çalışacağı bilinmiyor, ve sağlık kapısı yalnız funding'i izliyor.
   Fiyat / kâr al bileşeni (tarihsel kârın %50-90'ı) sessizce ölürse sistem bunu ancak düşüş olarak görür. Bu da 2022 tipi bir yılda
   (+%62, Sharpe 1,75) ya da daha kötüsünde fark edilir.

Sırada ikinci büyük risk olarak **icra**: maker dolum / ters seçim / kayma hiç ölçülmedi ve kâr al bileşeni bu kaliteye doğrudan bağlı.
Bu ve birinci risk ancak canlı / demo veriyle ve aylık örnek dışı kontrolle ölçülebilir.

---

## Yeniden üretim
```bash
cd binance-carry-bot      # zemin /tmp'de olmalı (VERI.md; yeniden_kur.py VERI_EK=uzun BAS_YIL=2020)
python3 arastirma_m689_tek_coin_stres.py            # Test 1 -> /tmp/m689/{durumlar,senaryolar,gercek_en_kotu_coin_24s,sabit_agirlik_en_kotu_long_24s}.csv
python3 arastirma_m688_funding_notr.py hazirla      # /tmp/fv_tam.pkl + /tmp/g33_m688.py (g33.py'nin kopyası)
python3 arastirma_m688_funding_notr.py kos          # 12 koşu, tek işçi (~25 dk); A koşusunun paritesini kontrol eder
python3 arastirma_m688_funding_notr.py analiz       # Test 2 tabloları
```
Girdi defterleri: `/tmp/m621/pozKS_{0,1}.pkl` ve `/tmp/m622`, `/tmp/m_ekim_kuru` E dosyaları — mevcut motorla (parite doğrulandı)
yeniden üretilebilir.
