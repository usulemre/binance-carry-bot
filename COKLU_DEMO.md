# ÇOKLU DEMO — profilleri AYNI ANDA, ayrı ayrı çalıştırıp gün gün karşılaştırmak

Amaç: T4, T4 + koşullu stop, T7K 1,15x + koşullu stop, T6 + koşullu stop … aynı günlerde, aynı piyasada, şu anki kâr al /
kademe / stop seviyeleriyle çalışsın; her biri için PDF'teki gibi **gün gün ne tuttu, ne açtı / kapattı, % kaç kazandı** raporu çıksın.

## ŞART: her bot AYRI demo hesabı
Binance tek hesapta bir coinde tek pozisyon tutar (one-way). İki bot aynı hesapta aynı coine dokunursa birbirinin pozisyonunu
kapatır / büyütür ve iki defter de bozulur (`check_bot_conflict.py`). Bu yüzden **her profil için ayrı demo hesabı ve ayrı API anahtarı**
gerekir (her demo hesabı ayrı bir Binance girişine bağlıdır). Aynı hesabı iki bota VERMEYİN.

## Kitap büyüklüğü (CARRY_SERMAYE_OLCEK)
Demo hesaplar genelde büyük sanal bakiye verir. Bot, kitabı bakiyeye göre kurar (evren, bacak büyüklüğü, doz). 2.000 $'lık kitabı
denemek için: `CARRY_SERMAYE_OLCEK = 2000 / demo özkaynağı` (ör. 10.000 USDT → 0.2). Bot özkaynağın yalnız bu kadarını kullanır,
bileşik büyüme korunur; rapor getiriyi bu kullanılan sermayeye göre hesaplar. Gerçek hesapta 1,0 dışı değer preflight'ta HATA.

## Madde 656: hepsi önerilende
Kullanıcı kararı (2026-10-29): bütün botlar önerilen ayarda — `sudo ./deploy/onerilen_kur.sh --hepsi` ya da yeni bot için
`sudo ./deploy/coklu_demo_kur.sh AD ONERILEN "" "" <ölçek>`. Aşağıdaki tablo profiller arası KARŞILAŞTIRMA isteğe bağlı kalırsa geçerlidir.

## Önerilen dört bot (karşılaştırma için) (bugünkü kanıta göre; KAR_HARITASI 596, 622-623, 629, 638)
| AD | komut | ne | backtest beklentisi (2.000 $, yıllık) |
|---|---|---|---|
| T4 | `sudo ./deploy/coklu_demo_kur.sh T4 T4 1.0 0 <ölçek>` | kod varsayılanı | +%244 |
| T4KS | `sudo ./deploy/coklu_demo_kur.sh T4KS T4 1.0 0.03 <ölçek>` | T4 + koşullu stop | +%254 (−%5 günü daha sık) |
| T7KKS | `sudo ./deploy/coklu_demo_kur.sh T7KKS T7K 1.15 0.03 <ölçek>` | **önerilen** | +%315 |
| T6KS | `sudo ./deploy/coklu_demo_kur.sh T6KS T6 1.0 0.03 <ölçek>` | bilgi (1x) | +%329 (dd daha derin) |
Büyük bakiye (≳ 12.500 $ kitap) denemek isterseniz T6 için GROSS 1.10 (KURULUM_BUYUK_BAKIYE.md).

## Kurulum (sunucuda; ana kurulum /opt/carry)
```bash
cd /opt/carry && git pull
sudo ./deploy/coklu_demo_kur.sh T7KKS T7K 1.15 0.03 0.2     # her bot için bir kez (yukarıdaki tablo)
sudo nano /opt/carry-T7KKS/.env                              # O hesabın BINANCE_API_KEY / SECRET'ı
(cd /opt/carry-T7KKS && python3 carry_preflight.py)          # HATA 0 (ölçek satırı UYARI olarak görünür — normal)
sudo systemctl enable --now carry@T7KKS carry-defter@T7KKS.timer carry-rapor.timer
journalctl -u carry@T7KKS -f
```
Eski tek bot (`carry` servisi) çalışıyorsa ve aynı demo hesabını kullanıyorsa onu durdurun: `sudo systemctl disable --now carry`.
Kod güncellemesi: `cd /opt/carry && git pull && for d in /opt/carry-*/; do [ -f $d/carry_bot.py ] && git -C $d pull; done`
ve `sudo systemctl restart 'carry@*'`.

## Rapor
- Her bot her gün 00:05 UTC'de `defter/gunluk.jsonl`'a bir satır yazar (`carry_gunluk_defter.py topla`): kitap sermayesi, gün
  getirisi, açık pozisyonlar (coin, long/short, $, kâr %), son 24 saatin funding / gerçekleşen kâr / komisyonu, dünden bu yana
  açılan / kapanan / büyüyen / küçülen pozisyonlar.
- 00:15 UTC'de `/opt/carry-rapor/demo_defteri.html` ve `.pdf`: özet (her botun toplam getirisi, en iyi / en kötü gün, funding,
  komisyon), **gün gün yan yana getiri tablosu**, ve her bot için gün gün sayfalar (o gün ne tutuyordu, ne açtı / kapattı).
- Elle: `python3 /opt/carry/carry_gunluk_defter.py rapor --klasor /opt/carry-T4 --klasor /opt/carry-T7KKS --pdf`
- Raporu bana (bu sohbete / GitHub'a) yüklerseniz backtest beklentisiyle karşılaştırırım (madde 617 kuralı + dolum maliyeti).

## Ne ölçülecek
1. Profiller arası FARK backtest'teki sırayı tutuyor mu (T7KKS > T4KS > T4)? Tek ay gürültülüdür; 4-8 hafta bakın.
2. Gerçek dolum maliyeti (komisyon toplamı / işlem hacmi) — madde 519: 15 bp altı rahat, ~29 bp'de T4 avantajı sıfır.
3. Koşullu stop logları: `KOŞULLU 24 SA STOP: ... -> tutuluyor / kapatılıyor`.
