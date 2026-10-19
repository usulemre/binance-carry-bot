# MADDE 343 — ELDEKİ TEK GERÇEK CANLI KAYIT (ve neden arşivlendi)

`canli_kayit_2026-09-12_10-03_ikinci_bot.log` — 71 KB, **21 günlük
gerçek canlı koşu**, kullanıcının **ikinci** botundan (ortalamaya
dönüş / ATR stop'lu, carry botu DEĞİL).

`.gitignore` `bot.log`'u dışlıyor ve canlı churn için bu doğru. Ama bu
dosya churn değil: **bu projede eldeki tek canlı icra kaydı** ve
konteynerle birlikte gidecekti. Bu yüzden ayrı bir adla arşivlendi.

## NİYE ÖNEMLİ

Carry kitabının en büyük ölçülmemiş riski belgenin kendi ifadesiyle:
*"uygulanabilirlik güveni MEDIUM (maker doluluğu simülasyonda %97;
**canlıda ölçülmedi**)"*. Bu kayıt o boşluğa bakan tek veri.

Sayılan olaylar (192 ERROR, 96 WARNING, 311 INFO):

| olay | adet |
|---|---|
| `emir DOLMADI` | **48** |
| `TP emri reddedildi` | **48** |
| `SÜRE DOLDU` → `kapatılıyor` | 71 |

## NE DER, NE DEMEZ — DİKKAT

**DEMEZ:** "carry botunun maker doluluğu şu kadar." Bu başka bir bot,
başka emir tipi, başka evren. Ölçülmüş bir sabiti başka yapılandırmaya
taşımak onu ölçülmemiş bir tahmine çevirir (madde 305'in yasası).

**DER:** borsa düzeyinde iki olgu var ve ikisi de carry botunu
ilgilendirir — (1) emirler fiilen dolmayabiliyor, (2) dolmayan emrin
ardından TP kurulamıyor ve pozisyon korumasız/yarım kalıyor. 48/48
eşitliği bunların **aynı 48 olay** olduğunu düşündürüyor: emir dolmaz →
TP kurulamaz. Carry botu GTX post-only maker giriş kullanıyor, yani
dolmama riski ona DAHA çok ait.

## AÇIK EKSEN (ölçülmedi)

Bu kayıttan şunlar çıkarılabilir ama ÇIKARILMADI: dolmama oranı
(payda: toplam emir denemesi), reddin saat/oynaklık dağılımı, ve
carry'nin `DOLUM_BEKLEME_SN=180` / `DOLUM_DENEME=2` ayarlarının bu
gerçeklikte ne verdiği. Payda log'da açıkça yok; çıkarmak için
`carry_izleme.py`'nin okuduğu biçime dönüştürmek gerekir.
