# BAŞLANGIÇ — Bu Projede Ne Var?

## GÜNCEL RAKAMLAR (tüm düzeltmeler sonrası)

Temiz 10 coin, 2022-2026, tüm maliyetler + uygulama gecikmesi dahil.
(Bu rakamlar `python test_doc_accuracy.py` ile doğrulanabilir.)

| | Kesitsel bot | Sinyal bot |
|---|---|---|
| Getiri | +65.9%/yıl | +954R / 4.6 yıl |
| Sharpe | 1.54 | - |
| Max düşüş | -26.1% | -28.6R |
| İşlem | ~2/gün | 6400 (kazanma %67) |

Kesitsel botta **faz aralığı +35% .. +109%** — botu hangi saatte
başlattığınıza bağlı, kontrol edilemez (madde 100/105).

**Karışım (%30 kesitsel + %70 sinyal):** Sharpe ~6.6 normalize,
max düşüş ~-37.

## GERÇEKÇİ BEKLENTİ

Backtest rakamı ham haliyle alınmamalı. Katman katman düzeltme:

| Katman | Sonuç |
|---|---|
| Backtest ham (karışım) | ~%200/yıl |
| Çoklu test düzeltmesi (-%25) | ~%150/yıl |
| Canlıya geçiş kayıpları (-%30) | ~%105/yıl |
| Faz/zamanlama şansı (-%20) | ~%84/yıl |

**ORTA SENARYO: yıllık %50-100**
**KÖTÜ SENARYO: yıllık %0-30**
**2 yılda 1 negatif yıl beklenmeli** (2022 ve 2026 öyleydi)

Ayrıca kazanç birkaç patlama dönemine yoğunlaşıyor (aşağıya bakın) -
tipik deneyim ortalamadan çok daha sönük olacak.

---

## İKİ BOT VAR

### 1. `main.py` — Sinyal botu (ÖNERİLEN, ağırlık %70)

Coinleri tek tek inceler, aşırı hareket sonrası geri dönüş arar.
Borsa tarafında SL/TP emri koyar.

```
strateji  : extreme_reversal
eşik      : %10 hareket, ATR stop 1.0x
pozisyon  : en fazla 5, her biri sermayenin %1 riski
kaldıraç  : 2x (likidasyon ~%50 uzakta)
korumalar : kademeli küçülme 30R, max tutma 10 gün,
            korelasyon filtresi, günlük zarar limiti %5
```

**Neden önerilen:** Walk-forward'da 6/7 dönem pozitif, kazanç
dağınık (en iyi 3 dönem çıkarılsa bile pozitif), faz riski yok.

### 2. `crosssec_bot.py` — Kesitsel bot (ağırlık %30)

Coinleri birbirine göre sıralar: en çok düşen 4'ü LONG, en çok
yükselen 4'ü SHORT. Piyasa nötr - genel yönden bağımsız.

```
ufuklar   : 5 ve 10 günlük getirilerin z-skor ortalaması
bacak     : 4 long + 4 short (kaldıraçsız)
rebalance : günde bir
kâr alma  : pozisyon +%4'e ulaşınca kapat
korumalar : kademeli küçülme %30, acil stop -%25,
            devre kesici -%35, likidite ve dispersiyon filtresi
```

**Zayıf yanı:** Faz riski (hangi saatte dengelediği sonucu %40+
değiştiriyor, çözülemiyor) ve kazanç 3 döneme yoğunlaşmış.

**DİKKAT:** Bu bot borsa tarafında SL/TP emri KULLANMAZ - korumalar
her turda bot tarafından uygulanır. **Bot durursa pozisyonlar
korumasız kalır.** Kesintisiz çalışacak bir ortamda başlatın.

### Birlikte çalıştırma

Korelasyon +0.146 - neredeyse bağımsız. Karışım her ikisinden iyi.
**Ayrı alt hesaplarda** çalıştırın; aynı hesapta pozisyonlar çakışır
(`check_bot_conflict.py` ile kontrol edin).

---

## İLK ÇALIŞTIRMA SIRASI

```bash
pip install -r requirements.txt
cp .env.example .env          # API anahtarlarınızı girin

python preflight.py           # 1. Ayar/bağlantı kontrolü - HATA varsa düzeltin
python crosssec_bot.py --dry-run   # 2. Ne yapacağını görün (emir göndermez)
python crosssec_bot.py --loop      # 3. Demo hesapta çalıştırın
python dashboard.py                # 4. Ayrı terminalde: izleme paneli
```

**Demo hesapta HAFTALARCA çalıştırın.** Kod hiç canlı test edilmedi -
bu ortamdan Binance'e erişilemediği için gerçek emir dolumu, API
gecikmesi ve slippage ölçülemedi.

---

## EN ÖNEMLİ GERÇEK: KAZANÇ BİRKAÇ DÖNEME YOĞUNLAŞIYOR

Tam sistem walk-forward testi (9 adet 6 aylık dönem, parametreler
sadece geçmişten seçilerek):

| | Bileşik getiri |
|---|---|
| Tüm 9 dönem | **+5.540%** |
| En iyi 1 dönem hariç | +747% |
| En iyi 2 dönem hariç | +110% |
| **En iyi 3 dönem hariç** | **-8.7%** |

**Kazancın neredeyse tamamı 3 dönemden geliyor.** Kalan 6 dönem
birlikte zarar ediyor. 9 dönemin 4'ü negatifti.

Bunun pratik anlamı:
- **Uzun sessiz/kayıp dönemler normal.** 2022'nin tamamı, 2026'nın
  tamamı negatifti.
- **Botu kesintisiz çalıştırmak kritik** - patlama dönemini kaçırmamak için
- **6 aylık kayıp, strateji değiştirmek için sebep değil**
- **Zamanlama şansı büyük rol oynuyor** - 2024 başında başlayan ile
  2026 başında başlayan tamamen farklı sonuç görür

**AMA SİNYAL BOTU DAHA SAĞLAM:**

| | Sinyal botu | Kesitsel bot |
|---|---|---|
| Pozitif dönem | **6/7 (%86)** | 5/9 (%56) |
| En iyi 3 dönem hariç | **+94.7R (pozitif)** | -8.7% (zarar) |

Sinyal botunda kazanç çok daha dağınık - birkaç patlama dönemine
bağlı değil. Karışımda ağırlığının yüksek olmasının sebebi bu.

Kontrol araçları:
- `python full_walkforward.py`   (kesitsel bot)
- `python signal_walkforward.py` (sinyal botu)

---

## ÖLÇÜLMESİ GEREKEN İKİ ŞEY

**1. Funding** - stratejinin en hassas olduğu maliyet. Backtest
%0.01/8sa varsayıyor. Gerçek %0.05 çıkarsa Sharpe 2.96 → 2.35,
%0.10 çıkarsa 1.92. Bot her dengelemede gerçek oranı logluyor -
**o logu takip edin.**

**2. Slippage** - `slippage_check.py` ile ölçün:
```bash
python slippage_check.py --top 20 --notional 960
```
Bu ortamdan mainnet engelli olduğu için gerçek rakam alınamadı.
Strateji slippage'a dayanıklı çıktı (15 kat artışta %12 kayıp) ama
doğrulanmalı.

---

## YARDIMCI ARAÇLAR

| Araç | Ne yapar |
|---|---|
| `preflight.py` | Canlıya geçiş öncesi 15+ kontrol |
| `slippage_check.py` | Emir defterinden slippage tahmini (emir göndermez) |
| `check_bot_conflict.py` | İki bot aynı hesapta çakışır mı |
| `robustness_check.py` | Sonuçların istatistiksel güvenilirliği |
| `dashboard.py` | Canlı izleme paneli (tarayıcı) |
| `crosssec_backtest.py` | Kesitsel strateji backtest'i |
| `portfolio_backtest.py` | Sinyal botu backtest'i |

**Testler:** 13 paket, `python test_*.py` ile çalıştırılır.

---

## BİLİNEN SINIRLAMALAR

- **Hiç canlı çalışmadı** - tüm doğrulama backtest ve mock testlerle
- **14 coinle test edildi** - canlı bot 30 tarıyor, mainnet verisi
  indirilemedi (daha fazla coin muhtemelen daha iyi)
- **Funding sabit varsayıldı** - muhafazakâr yönde (gerçek maliyet
  daha düşük olmalı, çünkü piyasa nötr portföyde long/short netleşir)
- **Makro takvim boş** - `macro_calendar.py` içindeki `MACRO_EVENTS`
  listesini doldurmazsanız o filtre hiçbir şey yapmaz
- **2026 zor bir yıl** - her iki bot da bu dönemde zayıf

---

---

## BULUNAN BÜYÜK HATALAR

Backtest sonuçlarını şişiren veya gizli risk taşıyan hatalar:

| # | Hata | Etkisi |
|---|---|---|
| 20 | Strateji sentetik veriyle seçilmiş | `adaptive` gerçekte 6/6 fold negatif |
| 21 | Portföy kısıtı yok (çakışan işlemler) | +1400R → +1006R |
| 27 | 2020-21 verisi bozuk (ETH 90.000$) | 623 sahte işlem, 221R |
| 38 | Uygulama gecikmesi modellenmemiş | Sharpe 12.6 → **2.6** |
| 49 | Kâr kilitleme zararlıymış | -123R (eski strateji için ayarlıydı) |
| 56 | Bot 15m'de, backtest 4h | Tüm sonuçlar geçersiz olurdu |
| 63 | **Likidasyon modellenmemiş** | Sinyallerin %9.6'sı riskli (kaldıraç 5x) |
| 64 | **Short'ta sınırsız kayıp** | Tek olay sermayenin %23'ü (XLM -%184) |

### "Var sanılan ama çalışmayan" şeyler (madde 66, 68, 69)
- `testnet` parametresi hiç kullanılmıyordu (ölü parametre)
- Likidite önbelleği rebalance'tan kısaydı (hiç işe yaramıyordu)
- Makro haber takvimi boştu (filtre sessizce devre dışı)

Hiçbiri hata vermiyor, sadece sessizce hiçbir şey yapmıyor.
Madde 70'te 10 ayar bayrağı sistematik test edildi - hepsi temiz çıktı.

---


---

## DENENİP REDDEDİLEN FİKİRLER

Tekrar denenmesin diye:

| Fikir | Sonuç | Madde |
|---|---|---|
| Minimum tutma süresi ("2-3 gün bekle") | Kazanma %57 → %42 | 51 |
| Giriş saati filtresi | Hiçbir saat referanstan iyi değil | 39, 51 |
| Trend stratejileri (MA, momentum) | Hepsi negatif, IS-OOS korelasyon **-0.55** | 52 |
| Portföy vol hedeflemesi | Sharpe düşüyor, risk artıyor | 47 |
| Korelasyon nötrlüğü | Sadece 2/5 yılda iyi | 47 |
| Taker akış sinyali | Klasik overfitting deseni | 48 |
| Dispersiyon filtresi | %74 boş zaman, marjinal kazanç | 46 |
| Histerezis (pozisyon koruma) | Getiri kaybı > slippage tasarrufu | 57 |
| Sıra ağırlıklı boyutlandırma | Sharpe 2.81 → 2.22 | 54 |
| Min z-skor eşiği | Her eşikte kötüleşti | 54 |
| Asimetrik bacak (3L+7S) | Tutarsız, piyasa nötrlüğü kaybolur | 54 |
| Pozisyon stop-loss (dar) | Marjinal | 55 |
| "Son günü atla" (momentum tekniği) | Sharpe 1.75 → **0.54** | 53 |
| 4 saatlik rebalance | Gerçek maliyetle **zarara** dönüyor | 44, 58 |

---


---

## KABUL EDİLEN İYİLEŞTİRMELER

| İyileştirme | Etki | Madde |
|---|---|---|
| **Çok ufuklu sıralama** (5/10/15g) | Sharpe 1.75 → **2.81**, 5/5 yıl | 53 |
| Kâr alma (%4) | Sharpe 2.33 → 3.23 | 42, 55 |
| Kademeli exposure azaltma | Max düşüş -74% → **-29%** | 40 |
| Likidite filtresi | Slippage sorununu kaynağında çözer | 45 |
| Acil stop (-%25) | Maliyetsiz sigorta (XLM olayı) | 64 |
| Güvenlik filtreleri (ATR/SL) | Likidasyon riski %19.5 → **%0** | 63 |
| Max tutma süresi (10 gün) | +391R → +435R | 51 |

---

---

## PROJEDEN ÇIKAN ÜÇ DERS

**1. Backtest'in ölçmediği şeyler en tehlikelisi.** Likidasyon riski
(madde 63) ve sınırsız short kaybı (madde 64) rakamlarda hiç
görünmüyordu ama gerçek hesapta ciddi zarar üretebilirdi.

**2. "Var sanılan ama çalışmayan" kod.** Ölü parametre, işe yaramayan
önbellek, boş makro listesi - hiçbiri hata vermiyor, sessizce hiçbir
şey yapmıyor (madde 66, 68, 69, 70).

**3. Test kendi doğruluğunu da kanıtlamalı.** İki kez yanlış kurulmuş
bir test, olmayan bir hatayı varmış gibi gösterdi (madde 62, 70).
"Hata var" diyen bir test önce kendisi doğrulanmalı.
