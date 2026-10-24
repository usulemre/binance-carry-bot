# CANLIYA ÇIKIŞ — ilk çeyrek için adım adım plan

> **Bu belge madde 217'de BAŞTAN YAZILDI.** Önceki hâli madde 182'nin
> rakamlarını taşıyordu (+%91,8 / Sharpe 2,76) — yani **madde 209'un
> çürüttüğü ölçümü**. Bacak formülü 3 kat yanlıştı (`bakiye/75`, doğrusu
> `bakiye/225`), "günde bir tur / 5 dilim" diyordu (doğrusu 8 saatte bir
> tur / 15 dilim), "12+12 bacak" diyordu (doğrusu 6+6), düşüş eşikleri
> eski p5/p1'den geliyordu (−%20/−%25 yerine −%16/−%19,5) ve gelirin
> "%94'ü funding'den" diyordu — **madde 214 bunu çürüttü**.
>
> Bayat bir talimat, bayat bir ayardan daha tehlikelidir: ayarı kod
> denetler, talimatı kimse denetlemez. Bu yüzden artık
> `carry_preflight.py` bu belgedeki sayıların kodla aynı olduğunu
> **makine olarak** kontrol ediyor.

Bu belgenin tek amacı: beklentinin canlıda gerçekleşip gerçekleşmediğini
**para kaybetmeden önce** anlamak.

**Bugünkü beklenti** (madde 209 + 222: 48sa pencere, 5+5 bacak, kaldıraçsız):

| ölçü | değer |
|---|---|
| yıllık getiri | **+%112,5** |
| Sharpe | **3,12** |
| ortalama maksimum düşüş | **−%14,5** |
| 1 yıl düşüş p5 / p1 (bootstrap, madde 222/231) | **−%16,8 / −%20,7** |
| **1 yıl düşüş p5 / p1 (SIRALAMA testi, madde 243)** | **−%20,6 / −%25,3** |
| 1 yıl getiri p5 | +%41,4 |

> **MADDE 262 — BU TABLONUN TEK KAYNAĞI.** Yukarıdaki sayıların hepsi
> depodaki `referans_getiri.csv`'den (1.504 gün) üretilir; `/tmp`'deki
> hiçbir dosyaya bağlı değildir (madde 258'in sabitlediği
> `/tmp/kontrol_E*.pkl` bugün bakıldığında SİLİNMİŞTİ). Yeniden üretmek
> için: `python arastirma_yayinlanan_sayilar.py`. Getiri p5 belgelerde
> üç farklı değerle (+%41,1 / +%41,4 / +%41,5) geçiyordu; yayınlanan
> düşüş çiftini üreten koşu (blok 21, B=20.000) **+%41,4** veriyor, tablo
> ona bağlandı. Tarihsel araştırma tabloları o günün ölçümünün kaydıdır,
> değiştirilmedi.
>
> **VE KUYRUĞUN BELİRSİZLİĞİ TOHUMDAN DEĞİL BLOK UZUNLUĞUNDAN GELİYOR:**
> tohum ±0,4 puan, blok uzunluğu ±9,7 puan. Blok uzadıkça getiri kuyruğu
> kötüleşir (+%41,4 → +%31,7) ama düşüş kuyruğu iyileşir (−%19,1 →
> −%14,7) — **iki eksende birden ihtiyatlı tek bir blok seçimi yoktur.**
> Dürüst zarf çaprazdır: **getiri p5 +%34,8** (blok 90) ·
> **düşüş p5 −%19,1 / p1 −%23,9** (blok 5). Aşağıdaki −%18/−%23 alarm
> eşikleri üç bağımsız yöntemin (blok 21: −%20,7 · blok 5: −%23,9 ·
> madde 243 sıralama: −%25,6) arasında kalıyor; eşikler değişmedi.

> **MADDE 243 — DÜŞÜŞ BEKLENTİSİNİN DÜRÜST HÂLİ.** Yukarıdaki iki satır
> aynı kitabı iki farklı yöntemle ölçüyor ve İKİNCİSİ DAHA KÖTÜMSER.
> Bootstrap blokları gerçek sıralamayı kısmen korur; madde 243 sıralamayı
> TAMAMEN rastgeleleştirdi (20.000 örnek, aynı günlük getiriler) ve
> gerçekleşen −%14,54'ün karıştırılmış dağılımın **%84'lük** yüzdeliğinde
> olduğunu buldu — yani yayınlanan düşüş **şanslı bir sıralama.**
> **Canlıda −%20 civarı bir yıl beklenmelidir; bu bir arıza değildir.**
> Alarm eşikleri bu dağılımda sağlıklı botu yılda %11,1 (İNCELE) ve
> %2,2 (DURDUR) olasılıkla boşa tetikler — ikisi de kabul edilebilir.

> **MADDE 260 — CANLI KARAR ARTIK KOD.** Bu belgedeki eşikleri *okumak*
> zorunda değilsiniz: `canli_karar.py` ön kayıtlı canlı karar kuralıdır ve
> `carry_izleme.py` artık onu çağırıp **çıkış kodu** veriyor
> (0 DEVAM · 1 İNCELE · 2 DURDUR). Yani 14. gün kontrolü gözetimsiz
> koşabilir. Kuralın en önemli maddesi: **toplam getiri hiçbir zaman karar
> ölçütü değildir** (madde 151: 30 günde %15 güç) — insanın ilk bakacağı şey
> tam olarak odur. Ve her ölçüt ancak **gücü %80'i geçtiği günden** itibaren
> durdurma verdirir: funding 14. günden, TP long 30., TP short 60.; düşüş
> koruması 1. günden (o bir performans ölçütü değil, risk korumasıdır).
>
> `python canli_karar.py --ornek` sekiz senaryoyu yazar — "getiri −%40 ama
> funding tam" senaryosu **DEVAM** verir, ve bunu görmek bu belgeyi okumaktan
> daha öğreticidir.

216 maddenin en pahalı dersi: *backtest'in göremediği şeyler icrada
saklanır.* Madde 204-211'de bulunan **on iki** hatanın hiçbiri backtest'te
görünmüyordu. İlk çeyreğin işi **kâr etmek değil, ölçmek**.

---

## 0. Başlamadan önce — GÜVENLİK (pazarlık yok)

- API anahtarında **Futures AÇIK**, **Para Çekme KAPALI**, **IP kısıtı VAR**.
- Anahtar hiçbir dosyaya yazılmaz; `config.py` **ortam değişkeninden**
  okur. Projede `.env` yoktur ve olmamalıdır.
- Daha önce herhangi bir yere yapıştırılmış bir anahtar varsa **iptal
  edilir**, yenisi üretilir.

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
```

## 1. Sermaye — ne kadarla başlanır

Bacak büyüklüğü, koddan doğrulanmış formül:

```
bacak = bakiye / 166,7     # 15 dilim x 5+5 bacak x %45 taban payı (rezerv 0,10)
```

| bakiye | bacak | durum |
|---|---|---|
| 1.600 $ | 9,6 $ | **YETERSİZ** — bot sessizce hiç işlem açmaz (madde 204 bunu yakalar ve turu atlar) |
| **1.667 $** | **10,0 $** | teknik alt sınır (borsa minimumu 5$ × 2 güvenlik payı) |
| 5.000 $ | 30,0 $ | rahat aralığın başı |
| **15.000 $** | **90,0 $** | eleme minimal, **beklenti tam** |
| 50.000 $ | 300 $ | kapasite hâlâ sorun değil (madde 204) |

(Madde 222 bacak sayısını 6'dan 5'e indirdi; aynı bakiyede bacak %20
büyüdüğü için teknik alt sınır 2.250$'dan 1.875$'a indi. Madde 442 rezervi
0,20'den 0,10'a indirdi; taban pay %40 -> %45, alt sınır **1.667$**.)

**MADDE 176 — bunu hafife almayın.** Küçük bacak, pahalı sembolleri
evrenden eler. Ölçüldü: evrenin %20'si elendiğinde getiri +%55,9'dan
+%35,6'ya düşüyor. Sebep bacak SAYISI değil **seçimin uçluğu**: 60 aday
arasından en uç 6 ile 48 aday arasından en uç 6 aynı şey değil.

Yani küçük sermaye "daha az para" değil, **daha düşük getiri ORANI**
demektir. `carry_preflight.py` eleme oranını ölçüp %20'yi geçerse HATA
verir.

**İlk çeyrekte kaybetmeyi göze alabileceğin parayla başla.**

## 2. Ayarlar — varsayılanlar DOĞRU, elleme

Varsayılanlar ölçülen yapılandırmanın kendisi. Hiçbirini set etmeniz
gerekmiyor; `carry_preflight.py` sapma olursa **HATA** verir:

| ayar | değer | madde |
|---|---|---|
| `CARRY_PROFIL` | **T60** | **442** |
| `CARRY_N_LEGS` | **5** | **222** |
| `CARRY_N_DILIM` | 15 | 184 |
| `CARRY_FUNDING_WINDOW_H` | **60** | **429** |
| `CARRY_REBALANCE_H` | 120 (5 gün) | 120 |
| `CARRY_GROSS` | 1.0 (kaldıraçsız) | — |
| `CARRY_KAR_AL` | **0.60** | **435-436** |
| `CARRY_KAR_AL_SHORT` | 0.20 | 189 |
| `CARRY_UC_HAREKET` | **0** (kapalı) | **429** |
| `CARRY_HAVUZ` | 3.0 | 179 |
| `CARRY_REZERV` | **0.10** | **429** |
| `CARRY_MIN_VOLUME` | **70000000** (70M $) | **429** |
| `CARRY_MIN_LISTING_DAYS` | **60** | **429/433** |
| `CARRY_SHORT_STOP` | **2.0** (+%200) | **428/437** |
| `CARRY_LONG_24S` | **0.45** (24 sa'te −%45 düşen long kapanır) | **449-453** |
| `CARRY_MERDIVEN` | **0.45** (long'un ⅔'ü +%45'te satılır, kalanı +%60'ta) | **463-469** |
| `CARRY_MERDIVEN_SHORT` | **0.15** (short'un ⅔'ü −%15'te kapanır, kalanı −%20'de) | **466-469** |
| `CARRY_SHORT_ARA_SAAT` | 0 = kapalı (aday: **48** — short tarafı 2 günde bir yeniden seçilir; ADAYLAR.md, kullanıcı kararı) | **493-502** |
| `CARRY_SHORT_TAVAN` | 0 = kapalı (aday: **0.08** — coin başına toplam short ≤ sermayenin %8'i; 48 ile birlikte) | **455-456, 500-502** |
| `CARRY_EVREN_MIN` | 0 = kapalı (aday: **30** — 70M eşiği 30'dan az coin bırakırsa hacim sırasıyla 30'a tamamla, 20M taban; sigorta) | **507-508** |
| `CARRY_MERDIVEN_PAY` | **0.667** | **468-469** |
| `CARRY_LONG_STOP` | 0 (kapalı) — 24 sa stop'u varken AÇMAYIN | **443-445, 452** |

**MADDE 469 — İKİ TARAFLI MERDİVEN (varsayılan).** Long'un ⅔'ü +%45'te, short'un ⅔'ü −%15'te
kapanır; kalanlar +%60 / −%20'de. Backtest: yıllık +%249, Sharpe 3,83, en kötü düşüş −%17,4,
−%5'ten kötü gün 3; protokolde 4/4 P %98-99 (madde 468). Kapatmak: `CARRY_MERDIVEN=0
CARRY_MERDIVEN_SHORT=0`.

**MADDE 465 — MERDİVEN KÂR ALMA (varsayılan açık).** Long pozisyonun yarısı girişten
+%45'te satılır, kalanı +%60'ta. Backtest: yıllık +%216 → +%233, Sharpe 3,44 → 3,66,
−%5'ten kötü gün 7 → 5; protokolde dört hücrenin dördü P %99+ (madde 464).
Kapatmak: `CARRY_MERDIVEN=0`.

**MADDE 453 — 24 SA DÜŞÜŞ STOP'U (varsayılan açık, 0.45).** Long bacak, coinin 24 saat
önceki fiyatından %45 düşerse kapanır; seviye her turda yenilenir. Backtest: en kötü gün
−%8,6 → −%5,5, yıllık maliyet ~5 puan (+%222 → +%216). Kapatmak: `CARRY_LONG_24S=0`.

**MADDE 445 — LONG FELAKET STOP'U (isteğe bağlı düğme).** `CARRY_LONG_STOP=0.40`
long bacağı girişten −%40'ta kapatır. Backtest: en kötü gün −%8,6 → −%5,9, −%5'ten kötü
gün 9 → 6, yıllık getiri +%222 → +%208. Daha sıkı (0.35) daha az kötü gün / daha çok
maliyet; daha gevşek (0.45) tersi. Varsayılan kapalı; açmak kullanıcının risk tercihidir.

**MADDE 442 — VARSAYILAN T60.** Madde 429-438 araştırmasının vardığı ayar
artık kodun varsayılanı; `.env`'de bu satırlardan HİÇBİRİNİ yazmayın (eski
bir `.env` eski değerleri taşıyorsa `carry_preflight.py` SAPMA diye HATA
verir — o satırları silin). Backtest (gerçekçi ağırlık kayması, 2.000 $,
1x): yıllık **+%222**, tam dönem düşüş **−%20,8** (eski kitap +%128 / −%21,0).
Yıllar: 2023 +%308 · 2024 +%125 · 2025 +%253 · 2026 (Oca-Eyl) +%286.
Eski kitaba dönmek için: `CARRY_PROFIL=BUGUN CARRY_FUNDING_WINDOW_H=48
CARRY_KAR_AL=0.40 CARRY_UC_HAREKET=0.40 CARRY_REZERV=0.20
CARRY_MIN_VOLUME=100000000 CARRY_MIN_LISTING_DAYS=90`.
Yaş eşiği 60'ın altına İNDİRİLMEZ ve short stop'u (yaş < 90 iken) KAPATILMAZ:
preflight ikisinde de HATA verir (madde 427: yaş 45 hesabı sıfırladı).

**AÇMA listesi** — ölçülmüş, zarar veriyor:

- `CARRY_VOL_HEDEF` / `CARRY_RISK=dengeli|agresif` → madde 165: aynı
  ortalama kaldıraçta sabit kaldıraça **14-24 puan** kaybediyor.
- `CARRY_SOLMA` → madde 167.3: +%55,9 → +%40,9.
- `CARRY_FUNDING_WINDOW_H=8` → **madde 209: ailenin en kötüsü**
  (Sharpe 2,71 vs 3,02). Eski belgeler 8 diyorsa onlar bayat.
- `CARRY_N_LEGS=6` (veya 12) → **madde 222**: 6 bacak artık varsayılan
  DEĞİL. 5 bacak eşit riskte +%103,6 vs +%96,8. 3-4 bacak daha çok
  getiri verir ama ön kayıtlı kuralın 1. şartından düşer.
- `CARRY_POZ_MODU_KONTROL=0` veya `CARRY_IZOLE_KAPAT=0` → madde 211:
  ikisi de gerçek para koruması.

**AÇILMASI iyi olan tek şey:** Binance'de komisyonu **BNB ile ödemek**
(%10 indirim). Madde 213: yıllık devir 312× olduğu için 0,2 baz puan
indirim ≈ **+0,33 puan/yıl**, bedava.

## 3. Sıfırıncı gün — emirsiz kontroller

```bash
python carry_preflight.py       # HİÇBİR EMİR GÖNDERMEZ, sadece okur
python carry_bot.py --dry-run   # ne yapacağını yazar, emir YOK
```

> **`preflight.py`'yi (eski, carry'siz olan) ÇALIŞTIRMAYIN.** O araç bu
> projenin eski botları için yazıldı; `.env` arar ve carry botunda
> olmayan ayarları kontrol eder, yanlış HATA verir. Doğru araç
> `carry_preflight.py`.

`carry_preflight.py` şunları kontrol eder — hepsi madde 204-216'da
bulunan **gerçek** canlı arızaları:

| kontrol | madde | neyi yakalar |
|---|---|---|
| ayarlar ölçülenle aynı mı | 209 | beklenti geçersiz olur |
| sinyal tanımı paritesi | 210 | canlı ile backtest farklı sinyal |
| referans seri / rapor tutarlılığı | 216 | yanlış ölçütle kıyas |
| defterler yazılabiliyor mu | 216 | ölçüm sessizce kaybolur |
| pozisyon modu TEK YÖNLÜ mü | 211 | bot HİÇ işlem açamaz |
| izole teminatta pozisyon | 211 | yıllık ~%23 sermaye yanar |
| bakiye bacak başına yeterli mi | 204 | bot sessizce hiç işlem açmaz |
| bacak yüzünden eleme oranı | 176 | getiri ORANI düşer |
| sağlık kapısı açık mı | 139 | bot pozisyon açmaz |

**HATA varsa canlıya geçmeyin.** Araç ne yapılacağını satır satır yazar.

Beklenen dry-run çıktısı: evren ~60-95 sembol, **5+5 bacak**, sağlık
kapısı AÇIK, 10 emir.

## 4. Çalıştırma

```bash
python carry_bot.py
```

**8 saatte bir** tur atar ve 15 dilimden sırası geleni yeniler (madde
184: 5 dilim yerine 15, başlangıç saati kumarını bitirdi). Her dilim 5
günde bir yenilenir. İlk **5 gün** kitap kurulum aşamasıdır; bu dönemde
getiri okuması anlamsızdır.

### 4b. Sürecin AYAKTA kalması

En tehlikeli hâl çökmüş bot değil, **çöktüğünü bilmediğin** bottur.
Pozisyonlar açık kalır ama dilimler yenilenmez, kâr al tazelenmez, bayat
emirler temizlenmez.

`carry_rapor.py` bunu ayrı bir alarm olarak ölçer: son turun üzerinden
**36 saat** geçerse İNCELE, **72 saat** geçerse DURDUR. Bu alarm ilk 5
gün muafiyetini bile ezer.

```ini
# /etc/systemd/system/carry.service
[Unit]
Description=Carry bot
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/carry
Environment=BINANCE_API_KEY=...
Environment=BINANCE_API_SECRET=...
ExecStart=/usr/bin/python3 carry_bot.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now carry
journalctl -u carry -f
```

`Restart=always` şart. `RestartSec=60` çökme döngüsünde rate-limit
yemeyi önler.

**Çökme sonrası:**

1. `python carry_rapor.py` — son tur kaç saat önce?
2. Borsada açık emir kaldı mı? Bir sonraki tur `bayat_emirleri_temizle`
   hepsini siler.
3. `carry_dilimler.json` duruyor mu? **Silmeyin** — ama silinirse artık
   felaket değil: madde 207'nin `durum_kurtar()`'ı borsadaki pozisyonları
   sahiplenip defteri yeniden kurar ve o turda **işlem yapmaz**. (Eskiden
   kitabın %93'ü tasfiye ediliyordu.)

## 5. Neyi NE ZAMAN kontrol edeceksin — madde 216'nın takvimi

Bu takvim ölçüldü. Gözlemlerin ölü bir edge'i yakalama gücü:

| gözlem | 14 gün | 30 gün | 60 gün |
|---|---|---|---|
| **funding tahsilatı** | **%100** | %100 | %100 |
| TP ulaşma oranı (LONG) | %72 | **%95** | %100 |
| TP ulaşma oranı (SHORT) | %42 | %68 | %91 |
| toplam getiri | — | **%15** | — |

**Yanlış gözleme bakmak bir yıl beklemek demektir.**

### MADDE 286 — ÇIKIŞ KODLARI: "ÖLÇEMEDİM" ≠ "ÖLÇTÜM, ŞÜPHELİ"

`carry_izleme.py` ön kayıtlı canlı kararı **çıkış koduyla** verir
(madde 260). Kodlar:

| kod | anlam | ne yapmalı |
|---|---|---|
| **0** | DEVAM | devam |
| **1** | İNCELE | ölçüm şüpheli — `carry_sapma.py` + `carry_defter.py` |
| **2** | DURDUR | botu durdur |
| **3** | **ÖLÇÜLEMEDİ** | **verdikt DEĞİL** — anahtar yok / borsaya ulaşılamadı; düzelt ve TEKRAR çalıştır |

**Madde 286 bir kusur düzeltti:** bu araç anahtar yokken `rapor()`
içinde ham `AssertionError` ile çöküyor ve Python'un **1** kodunu
veriyordu — yani *"İNCELE"* verdiktiyle **birebir aynı**. Gözetimsiz
bir 14. gün kontrolünde bu, *"funding tahsil edilmiyor"* ile
*"anahtarı export etmeyi unuttum"*u ayırt edemez demekti (madde 211'in
sessiz-yanlış-sinyal sınıfı). Artık ikisi ayrı kod.

**Kod 3 görürsen hiçbir karar vermemişsindir.** Takvim durmaz, ölçüm
tekrarlanır.

| gün | komut | ne söyler |
|---|---|---|
| **her gün** | `carry_rapor.py` | tek sayfa karar: DEVAM / İNCELE / DURDUR (ölü bot alarmı dahil) |
| **gün 1-5** | log | sadece emirlerin AÇILDIĞINI doğrula; getiri okuması anlamsız |
| **gün 14** | `carry_izleme.py --gun 14` | **KARAR NOKTASI**: funding tahsilatı. Burada %100 güç var — beklentinin %80'inin altındaysa "şanssızlık" geçerli açıklama DEĞİL |
| **gün 30** | `carry_izleme.py --gun 30` | TP dolum sayısı (kâr motoru). Beklenenin yarısından azsa dur |
| **gün 90+** | `carry_sapma.py` | ancak burada toplam getiri kıyası anlamlı olur |
| otomatik | sağlık kapısı | piyasada prim ölürse bot kendi durur |

**Dört arıza, dört dedektör** (madde 216):

| arıza | dedektör |
|---|---|
| seçim bozuldu / bot yanlış işlem açıyor | funding tahsilatı (14 gün) |
| kâr motoru durdu | TP ulaşma oranı (30 gün) |
| piyasada funding primi öldü | sağlık dedektörü (madde 139) |
| hepsi birlikte | toplam getiri (90 gün) |

## 6. Normal nedir — panik eşikleri

Ölçüldü (1.504 günlük referans seri, 50 ay, 48sa pencere, 5+5 bacak):

| olay | sıklık | anlamı |
|---|---|---|
| zararlı gün | **%46** | tamamen normal |
| zararlı ay | **%14** | normal |
| üst üste 3 zararlı ay | görüldü | **normal**, tarihte var |
| 118 gün düşüşten çıkamama | görüldü | **normal**, tarihte var |

> **İki hafta eksideysen bu bir bilgi değildir.** Karar ölçütü getiri
> değil, gün 14'teki funding tahsilatıdır.

### Hangi beklentiyi kullanacaksınız (MADDE 231)

Funding primi 2025Q1'de **seviye atladı** — bir trend değil, bir rejim
(Mann-Whitney p=0,0005; seviye modeli doğrusal trendden iyi uyuyor). En
uç long adayının funding medyanı −%0,49/gün → −%1,86/gün, **3,8 kat**.
Rejimler geri döner, o yüzden üç ayrı sayı var ve hangisini
kullandığınızı bilmeniz gerekiyor:

| rejim | yıllık | Sharpe | 1 yıl getiri p5 | 1 yıl düşüş p1 |
|---|---|---|---|---|
| **tüm örnek — YAYINLANAN** | **+%112,5** | 2,942 | +%41,1 | −%21,4 |
| düşük prim (örneğin %60'ı, 2022H2-2024Q4) | +%95,0 | 2,794 | **+%24,2** | **−%22,3** |
| yüksek prim (2025Q1+, **şu an buradayız**) | +%141,0 | 3,147 | +%71,6 | −%18,0 |

**Yayınlanan +%112,5 bir harmandır** (%60 düşük prim + %40 yüksek prim),
yani şu anki rejimden kasten DÜŞÜK. 2026'nın +%202'sini veya son rejimin
+%141'ini beklenti yapmayın — o rakam, devam edeceğini varsaymanızı
gerektirir ve bunun hiçbir dayanağı yok.

**İyi haber:** kenar her iki rejimde de var (Sharpe 2,79 ve 3,15).
Prim gerilerse risk "kenar kayboldu" değil, "getiri +%95'e indi".

**GERÇEK alarm eşikleri** (bootstrap p5/p1'den, madde 209; eşik madde
231'de DÜŞÜK PRİM rejimine göre gevşetildi):

| durum | ne yap |
|---|---|
| düşüş **−%18'i** geçti | dur, `carry_izleme.py` + `carry_defter.py` çalıştır. Normal yılın p5 düşüşü −%16,8, düşük prim rejiminde −%17,9 |
| düşüş **−%23'ü** geçti | 1x'te bu 100 yılda 1 olay (p1 −%21,4; düşük prim rejiminde −%22,3). **Durdur.** Ya beklenti yanlış ya icra bozuk |
| `carry_sapma.py` → **CİDDİ SAPMA** | durdur; **asla kaldıraç artırma** |
| funding tahsilatı **düşük prim tabanının %80'inin** altında (gün 14+) | dur, sebebini bul — bu noktada istatistiksel güç %100. Taban **%0,0653/gün** (madde 232) |
| funding tahsilatı tabanın **%50'sinin** altında | durdur, API/hesap tarafında sorun ara |

> **MADDE 232 — BU ÖLÇÜT ÖNCEDEN YANLIŞ KURULMUŞTU.** Rapor beklenen
> funding'i `günlük toplam getiri × 0,94` diye türetiyordu; o 0,94, madde
> 136'nın *"funding gelirinin %94'ü LONG bacaktan gelir"* cümlesinden
> alınıp *"gelirin %94'ü funding'den gelir"* diye yanlış etiketlenmişti.
> Beklenti **1,93 kat** yüksek çıkıyordu ve SAĞLIKLI bir bot şöyle
> görünüyordu: yüksek prim rejiminde oran 0,81 (temiz), harmanda 0,52
> (İNCELE), **düşük primde 0,32 (DURDUR)**. Yani hata şu an içinde
> olduğumuz yüksek prim rejimi tarafından maskeleniyordu. Artık beklenti
> motorla ölçülüyor (%0,1055/gün harman) ve alarm **en kötü rejimin**
> tabanına göre veriliyor.

> **MADDE 233 — BELGE İLE KOD AYRIŞMIŞTI.** Bu iki eşiği belge
> −%17/−%21 diye yazarken `carry_rapor.py` −%20/−%25 kullanıyordu; yani
> birkaç madde boyunca belge ile botun gerçekten uyguladığı eşikler
> FARKLIYDI ve hiçbir test bunu denetlemiyordu (madde 217 belgeyi koda
> bağlamıştı ama bu iki sabiti kapsamıyordu). Kodun değerleri de madde
> 175'ten beri bayattı: o ölçüm p5 −%20,0 / p1 −%26,1 diyordu, oysa
> madde 222'de yeniden üretilen seri p5 −%16,8 / p1 −%20,7, madde
> 231'in en kötü rejimi ise p5 −%17,9 / p1 −%22,3 veriyor. Kod **−%18 /
> −%23**'e çekildi (en kötü rejime göre) ve belgedeki bu iki satır artık
> **doğrudan kod sabitlerinden türetilerek** test ediliyor.

**Günlük raporda artık REJİM satırı var** (madde 232): tahsil edilen
funding'den hangi rejimde olduğunuzu ve dolayısıyla hangi beklentinin
geçerli olduğunu (+%95 / +%112,5 / +%141) yazar. Gerçekleşen getiriyi
harman beklentiye kıyaslamadan önce o satıra bakın.
| `carry_rapor.py` → **SİNYAL TANIMI PARİTESİ BOZUK** | durdur. Beklenti o ayarla ölçülmedi, bütün kıyaslar geçersiz (madde 210) |
| sağlık kapısı kapandı | bot pozisyonları kapattı; sebebini oku, kendi açılmasını bekle |

## 7. Çeyrek sonu — kaldıraç kararı

Üç şart birden sağlanıyorsa kaldıraç konuşulabilir:

1. `carry_izleme.py`: funding tahsilatı beklentinin **≥%80'i**
2. `carry_sapma.py`: durum **NORMAL** (veya üstü)
3. `carry_defter.py`: muhasebe özdeşliği her gün tuttu

**Doz kararı bootstrap p5/p1 ile verilir, tarihsel maksimumla değil**
(madde 188). Bugünkü dağılım (kaldıraçsız, 1 yıl):

| ayar | beklenen yıllık | ortalama düşüş | p5 düşüş | p1 düşüş |
|---|---|---|---|---|
| `CARRY_GROSS=1.0` | +%112,5 | −%14,5 | −%16,8 | −%20,7 |

### MADDE 276 — DOZ KARARI VERİLDİ: `CARRY_GROSS=1.25`, AMA KAPISI BU BELGE

Kullanıcı toleransını verdi: **bir yıllık p95 düşüşte −%30.** Madde
261/243'ün karıştırma ölçütüyle çözülen brüt:

| tolerans (1 yıl p95 düşüş) | brüt | net yıllık (icra düşülmüş) |
|---|---|---|
| −%20 | 0,955x | +%104,9 |
| −%25 | 1,219x | +%147,3 |
| **−%30 ← karar** | **1,254x** | **+%153,4** |
| −%35 | 1,786x | +%263,9 |

**Çözülen brüt tek bir sayı değil.** Blok bootstrap'ta aynı −%30
toleransı **p5 1,254x · medyan 1,497x · p95 1,921x** istiyor. Monte
Carlo yayılımı yalnız 0,015, örnekleme yayılımı **0,667** — yani
tekrarlanabilirlik doğruluk değil. Karar **ihtiyatlı uçtan** verildi:
**1,25x**.

**Likidasyon bağlayıcı değil.** Madde 266'nın gün içi kuyruğu 1x'te
−%41,41; duvar mmr %1'de 2,358x. 1,25x duvarın **%53'ünde**, 46,8 puan
pay var. Borsa kaldıracını bot kendi hesaplar
(`gerekli_kaldirac()` → 1,5 kat pay + ÇAPRAZ teminat).

**AMA EKRANDA GÖRÜLECEK SAYI −%30 DEĞİL.** Tolerans günlük KAPANIŞ
serisinde tanımlı; madde 266 gün içi yolun medyanda **1,488 kat** derin
olduğunu dakika verisinde ölçtü → gün içi karşılığı **~−%45**, ölçülen
en kötü kuyruk **−%52**. Bu, dozu kabul etmeden önce bilinmesi gereken
sayıdır.

**Doz BUGÜN AÇILMIYOR. `CARRY_GROSS` varsayılanı 1,0'da kaldı.** Sebep
kodun kendi talimatı (madde 149) ve bu belgenin konusu: bot **hiç canlı
çalışmadı** ve üç icra varsayımı (madde 265 giriş dolumu / 266 gün içi
düşüş / 267 TP dolumu) yalnız 2 aylık dakika verisinde doğrulandı.
1,25x, ölçülmemiş her canlı sapmayı 1,25 ile çarpar. Sıra:

1. 1x'te canlı başla, madde 216'nın takvimini koştur
   (gün 14 funding kapısı → gün 30 long TP → gün 60 short TP).
2. Yukarıdaki üç "doz açma şartı" (funding tahsilatı ≥%80, sapma
   NORMAL, muhasebe özdeşliği) tuttuysa tek satır: `CARRY_GROSS=1.25`.

**Kaldıraç kâr yaratmaz, dozu büyütür.** Kararı düşüşe tahammülüne göre
ver, getiriye bakarak değil.

### MADDE 288 — İKİNCİ BİR TEK SATIR: `CARRY_PRIM_E=0.10`

Prim-ölçekli brüt (brütü kesitsel funding priminin kendi normuna
oranıyla ölçekle) **botta kurulu ama KAPALI**. Dört şartı da geçen ilk
aday (275-288) ve doz ölçütünde +12,15 puan / **P %95,3** — ama:

- Kuralın geçmesi **kanıt değil**: karıştırılmış plasebo da geçti
  (madde 288'in üçüncü yasası). Kararı taşıyan şey bootstrap ve
  plasebodan ayrışma.
- 25-26'daki +0,012 **gürültüdür** (P %66,6).
- Her şey, icra varsayımları yalnız 2 aylık dakika verisinde
  doğrulanmış bir geri testte ölçüldü.

**Sıra aynı:** 1x'te canlı başla → madde 216'nın takvimi → üç doz açma
şartı tuttuysa `CARRY_GROSS=1.25`. `CARRY_PRIM_E=0.10` **ondan sonra**,
ve ayrı bir karar olarak. Aceleye gerek yok: çarpan ilk **~75 günde
zaten 1,0** döner, çünkü kayan medyan için `carry_prim.csv`'de geçmiş
birikmesi gerekir. Yani ilk çeyrekte açsan da kapalıysa da fark yok —
bu da onu açmak için beklemenin bedava olduğu anlamına gelir.

Açtıktan sonra kontrol: logda `prim-ölçekli brüt: ... -> çarpan X`
satırı. Çarpan 1,10'un üstüne çıkıyorsa **dur ve bana sor** — e=0,10'da
beklenen aralık 0,99-1,05; daha büyüğü ya prim verisinde bir kırılma ya
`carry_prim.csv`'de bozuk satır demektir.

**Kaldıracı ASLA düşüş sırasında artırma.** Madde 164 ve 205'te bulunan
iki ayrı sızıntı tam olarak buydu — ikincisi botun bunu **sessizce**
yapmasıydı (dilim hedefleri mutlak USD saklandığı için).

### MADDE 372 — 2.000 $ İÇİN GÜNCELLEME (madde 344-371'in canlıya etkisi)

Yukarıdaki tablolar 5+5 bacaklı, HAVUZ 3'lü eski kitaba ait. Bot bugün
2.000-20.000 $ aralığında **15 dilim × 4 bacak, HAVUZ 4** koşuyor ve iki
yeni koruma taşıyor. Kapı DEĞİŞMEDİ: önce 1x canlı çeyrek, sonra doz.

**Değişen üç şey:**

1. **HAVUZ 3 → 4 (madde 352).** 2.000 $'da kaldıraçsız yaklaşık +7..+9
   puan, düşüş 2..4 puan sığ. Ayar gerekmiyor (varsayılan).
2. **Oran önbelleği (madde 361-363).** Kalabalık seçimi kitabın yük
   taşıyan parçası; oran API'si susarsa bot eskiden yılda ~−43 puanlık
   yedeğe düşüyordu. Artık 24 saate kadar son bilinen oranı kullanıyor
   (~−8 puan). Ayar gerekmiyor.
3. **2.000 $'da doz kararının evren kanalı (madde 368-369).** Kaldıraç
   bacağı da büyütür: bacak = bakiye × brüt × 0,4 / 60. 2.000 $'da:

| ayar | bacak | evren | yıllık | 1y p5 düşüş | 1y p1 düşüş | gün içi p1~ |
|---|---|---|---|---|---|---|
| 1,0x | 13,3 $ | 8 major hariç | +%124..+131 | −%19..−20 | −%22..−24 | −%32..−36 |
| 1,25x | 16,7 $ | 8 major hariç | ~+%180 | −%23..−25 | −%27..−30 | −%40..−44 |
| **1,55x** | **20,7 $** | **yalnız BTC/QNT hariç** | **+%228..+245** | **−%27** | **−%31..−%33** | **−%45..−%47** |

(1y = blok bootstrap, kapanış bazında; gün içi = p1 × 1,458, madde 291.)
1,5x'te bacak TAM 20,00 $ = ETH grubunun asgari emri; bakiye ya da
düşüş ölçeği biraz inince grup her turda girip çıkar. Bu yüzden 1,5 değil
**en az 1,55**. Kullanıcı toleransı −%30: 1,25x içinde; 1,55x'te p5
içinde, p1 sınırın hemen dışında.

**Doz açma sırası (değişmedi, yalnız seçenek eklendi):** 1x canlı çeyrek →
yukarıdaki üç şart → `CARRY_GROSS=1.25` *veya*, düşüş tahammülü kötü %1
yılda −%33'ü kaldırıyorsa, `CARRY_GROSS=1.55`. Prim çarpanı
(`CARRY_PRIM_E=0.10`) iki dozda da ~+6 puan ekler ama kanıt eşiğinin
0,7 puan altında (madde 357).

**Ön uçuş (madde 374):** kaldıraç sessizce açılamaz. Ölçülmüş bir dozu
açmak için iki satır birlikte gerekir, ikisi AYNI değer:
`CARRY_GROSS=1.55` ve `CARRY_DOZ_ONAY=1.55` (ya da 1.25). Onaysız, 1,50-1,54
aralığında ya da ölçülmemiş bir dozda `carry_preflight.py` HATA verir.

**Canlıda izlenecek iki yeni log satırı:**
- `"... adayın oranı önbellekten ... alındı"` — oran API'si eksik cevap
  veriyor. Ara sıra normal; her turda görülüyorsa API sorunu var.
- `"... bu tur kalabalık seçimi KAPALI (en uç n)"` — önbellek de yetmedi.
  Her görüldüğü tur, yıllık ~−43 puan hızında kayıp demek; birkaç tur üst
  üste görülürse botu durdurup API erişimini düzeltin.

**Yoğunlaşma (madde 371):** en çok tutulan coin özsermayenin ~%10'u (1x),
1,55x'te ~%15-23. Bot STOP-LOSS kullanmıyor. Tarihte en büyük yoğunlaşma
(TRB 2023) botun lehine işledi; yine de tek coinde ters yönde +%100
hareket 1,55x'te özsermayenin ~%15-23'ü demektir.

## 8. Üç ay sonra ne öğrenmiş olacaksın

- **Funding gerçekten tahsil ediliyor mu.** Dikkat: madde 214 gelirin
  "%94'ü funding" ifadesini **çürüttü** — funding (+109,8) ile ham fiyat
  (−108,0) birbirini götürüyor, kârın tamamı **kâr-al hasadı** (+210,5).
  Funding gelir değil **seçici**. Yine de en güçlü canlı gösterge o,
  çünkü seçimin çalıştığını 14 günde kanıtlıyor.
- **TP ulaşma oranı beklentiye uyuyor mu** (LONG %8,8 / SHORT %18,1) —
  kâr motorunun doğrudan ölçüsü.
- **GTX emirleri doluyor mu** (madde 213: 4 saatte dolmayan pay %2,4,
  harmanlanmış komisyon 2,072bp — varsayım 2bp).
- **Beklenti ile gerçek arasındaki fark.**

Bu dördü, on üç tur backtest araştırmasının veremediği bilgidir — ve
madde 213-216 artık **neden** veremediğini de ölçtü: icra ekseni toplam
3,3 puan (tabandan 0,12 uzakta), funding öngörüsü ekseninin bütçesi
**negatif**, fiyat öngörüsü ulaşılamaz.
