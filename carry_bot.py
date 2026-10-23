"""FUNDING CARRY BOT — piyasa nötr funding toplayıcı.

MANTIK (README madde 113):
  Binance perpetual sözleşmelerde 8 saatte bir funding ödemesi yapılır.
  Funding POZİTİFSE long'lar short'lara öder, NEGATİFSE tersi.
  Bu, kaldıraçlı long talebinin ödediği bir kiradır - medyan yıllık %11.

  Bot o kirayı TOPLAYAN taraf olur:
    - funding'i EN YÜKSEK olan N coini SHORT'lar  (funding ALIR)
    - funding'i EN DÜŞÜK/NEGATİF olan N coini LONG'lar (funding ALIR)
    - iki taraf eşit büyüklükte -> piyasa nötr

  Fiyatın nereye gideceğini TAHMİN ETMEZ. Kâr fiyat hareketinden değil,
  8 saatte bir cebe giren funding ödemelerinden gelir.

YAPININ PARÇALARI:
  1. funding carry, 12+12 bacak       - çekirdek sinyal
  2. evren: hacim >= $100M, yaş >= 90g - tam evrende eksiden artıya (madde 133)
  3. + emir akışı %20 harman          - temiz panelde küçük ama tutarlı (madde 139)
  4. + 5 dilim faz çeşitlendirmesi    - KAPATMAYIN (madde 134.7, 137)
  5. + maker emir                     - maliyet
  6. + edge sağlık kapısı             - edge ölürse durdurur (madde 139)

GÜNCEL BEKLENTİ (847 sembollük temiz panel, sızıntısız motor, 5 dilim,
kaldıraçsız - madde 134, 137, 139):

  yıllık ~+%30, Sharpe ~1.25, max düşüş ~-%28
  bootstrap %95 aralık (yıllık): +%4.8 ile +%94.5

  ESKİ BAŞLIKTAKİ "Sharpe 2.07, düşüş -%10.9" RAKAMLARI 183 sembollük
  HAYATTA KALAN panelden geliyordu ve geçersizdir (madde 133-134).

RİSKLER:
  - Gelirin %94'ü LONG bacaktan (negatif funding, kalabalık short'lar).
    Delist riski tam bu bacakta; arşivde delist kapsamı zayıf
    (survivorship güveni DÜŞÜK, madde 136.13).
  - Kâr uç funding olaylarına bağlı: simetrik %5 kırpma net'in
    %79'unu siliyor (madde 136.8). Uç, zehir değil ürünün kendisi.
  - Piyasa nötr (BTC betası -0.04) ama fiyat gürültüsü büyük.
  - HİÇBİRİ CANLI DOĞRULANMADI. Kayma, limit emir doluluğu ve
    funding'in fiilen tahsil edildiği carry_izleme.py ile ölçülmeli.

KULLANIM:
    python carry_bot.py --dry-run     # emir göndermez, ne yapacağını yazar
    python carry_bot.py               # canlı (config'teki mod neyse)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time

import numpy as np
import pandas as pd

import carry_saglik
import config
from exchange_client import ExchangeClient

logger = logging.getLogger("carry_bot")

# ----------------------------------------------------------------- AYARLAR
# Bu değerler backtest'te doğrulandı (madde 113). Değiştirmeden önce
# crosssec_backtest tarzı bir A/B ölçümü yapın.

N_LEGS = int(os.getenv("CARRY_N_LEGS", "5"))
"""MADDE 230 — İKİ TARAF İÇİN AYRI BACAK SAYISI DENENDİ, REDDEDİLDİ.

Önce ölçüldü: iki tarafın sinyal yapısı taban tabana zıt. Seçilen
bacakların GÜNLÜK funding oranı, medyan (3.261 tur):

  bacak    LONG      SHORT
   1.     −%0,733   +%0,056
   2.     −%0,236   +%0,030
   3.     −%0,119   +%0,030
   4.     −%0,069   +%0,030
   5.     −%0,045   +%0,030

LONG tarafta 1.'den 5.'ye **16 KAT sönüm**; SHORT tarafta sönüm YOK
çünkü beş bacak da **%0,030/gün = standart funding oranında** oturuyor
(8 saatte %0,01). Yani short tarafta toplanacak bir funding ucu yok -
madde 214'ün "SHORT bacak kârının %86'sı fiyat+TP" bulgusunun SEBEBİ bu.

Buradan "az LONG, çok SHORT" yapısı denendi (eşit riskte, kontrolün
düşüşüne getirilmiş):

  L/S      yıllık   Sharpe   düşüş   22-24   25-26   EŞİT-RİSK
  3L/5S   +143.9%   3.108   −18.8   2.870   3.443    +107.2%
  4L/5S   +124.2%   3.100   −15.9   2.978   3.289    +110.1%
 *5L/5S* *+112.6%* *3.128* *−14.6* *2.984* *3.342*  *+112.5%*  <- kalan
  7L/5S    +90.1%   3.004   −13.2   2.893   3.174    +103.2%
  5L/8S   +100.9%   2.956   −14.4   2.906   3.053    +102.4%
  5L/10S   +95.6%   2.886   −14.9   2.845   2.977     +92.9%
  3L/8S   +130.0%   2.954   −19.0   2.796   3.187     +96.6%

**HİÇBİRİ EŞİT RİSKTE KONTROLÜ GEÇMİYOR.** 3L/5S'in +%143,9'u tamamen
KALDIRAÇ: aynı düşüşe getirildiğinde +%107,2, yani 5,4 puan DAHA KÖTÜ.
Bootstrap: Δeşit-risk −11,0 puan, P(>0) %22,8 (4L için −3,8, %30,6).

MEKANİZMA DÜZELTMESİ: "short funding düz, demek ki bacaklar birbirinin
yerine geçer, o yüzden daha çok short bacağı bedava çeşitlendirme"
diye tahmin ettim. Yanlış - 5L/8S ve 5L/10S açıkça kötü. Sebep: short
tarafın seçicisi funding DEĞİL, **kalabalık** (madde 148/228). Funding'in
düz olması, bilginin de düz olduğu anlamına gelmiyor; kalabalık ölçütü de
sırayla sönüyor. İki taraf da yoğunlaşmayı seviyor, sadece farklı
sinyaller üzerinden."""
"""Her tarafta kaç coin. 5+5 = 10 pozisyon.

DEĞİŞTİ: 30 -> 12 (madde 133). Yeni likidite+yaş filtresiyle evren
~35-45 sembole indi; 30+30 zaten kurulamıyordu (bot sessizce 20+20'ye
düşerdi). Tam evrende ölçüm, seyrelmenin pahalı olduğunu gösteriyor -
funding geliri en uç bacaklarda toplanmış durumda:

  bacak   yıllık   Sharpe   max düşüş   funding katkısı
   8+8    +26.3%    0.80      -41.1%        +178.5%
  10+10   +21.8%    0.77      -36.4%        +146.2%
  12+12   +16.7%    0.69      -34.0%        +119.0%   <- seçilen
  15+15    +5.3%    0.34      -36.2%         +84.1%
  20+20    +1.5%    0.18      -31.9%         +39.5%

8+8 daha kârlı ama -41% düşüş ve 16 pozisyonluk çeşitlendirme ince.
12+12, getirinin çoğunu koruyup düşüşü 7 puan azaltıyor.

DEĞİŞTİ: 12 -> 6 (MADDE 177). Yukarıdaki tablo ESKİ motorda ölçüldü
(kalabalık seçimi, fırsat rezervi, kâr al ve faz çeşitlendirmesi
YOKKEN) ve 8+8'in ALTINI hiç denemedi. Tam yapılandırmada, altı saat
fazının ORTALAMASIYLA yeniden ölçüldü:

  bacak   yıllık   Sharpe   maks düşüş   22-24 Sh   25-26 Sh
   1+1   +290.1%    2.20      -46.3%
   2+2   +197.4%    2.38      -32.3%
   4+4   +116.3%    2.40      -22.0%      2.47       2.50
   6+6    +92.0%   *2.44*     -20.0%      2.33       2.69   <- SEÇİLEN
   8+8    +68.9%    2.24      -20.7%
  12+12   +52.2%    2.15      -17.4%      2.07       2.39   (eski)

DEĞİŞTİ: 6 -> 5 (MADDE 222). Yukarıdaki madde 177 tablosu da artık
BAYAT: o ölçüm 48 saatlik funding penceresinden (madde 209), uç hareket
elemesinden (196), asimetrik kâr aldan (189) ve 15 dilimden (184) ÖNCE
yapıldı. Dört kabul edilen değişiklik yüzeyi altımızdan kaydırdı.

Bugünkü yapılandırmada yeniden ölçüldü (2 faz ortalaması, canlı
tahmincili 48sa sinyal):

  bacak   yıllık    Sharpe   22-24   25-26   maks düşüş
   3+3   +148.6%    3.06     2.94    3.25     -17.4%   (tek faz)
   4+4   +122.5%    3.02     2.92    3.17     -17.0%   (tek faz)
   5+5   +112.5%   *3.12*    2.794   3.147    -14.5%   <- SEÇİLEN
   6+6    +96.8%    3.02     2.786   2.922    -13.7%   (eski)

Ön kayıtlı kuralın üçü de geçti: 22-24 +0,008 · 25-26 +0,225 · düşüş
0,84 puan kötü (tolerans 3) · EŞİT RİSKTE +%103,6 vs +%96,8 (kaldıraç
0,94x). Bootstrap eşit riskte: getiri p5 +%37,5 vs +%34,7, ortanca
+%100,2 vs +%93,7, düşüş p5 -%15,9 vs -%15,8 ve p1 -%19,1 vs -%19,3 —
AYNI kuyruk, daha çok getiri.

DÜRÜST UYARI: 22-24'teki iyileşme +0,008, yani PRATİKTE BERABERLİK.
Kazanç 25-26'da. Sağlamlık: 5 bacak 5 yılın 4'ünde daha çok getiri,
Sharpe'la 3'ünde, 6 aylık pencerelerin %67'sinde kazanıyor. Yön madde
221'in yasasından ÖNCEDEN tahmin edildi (uçlar gelirin kendisi ->
yoğunlaşmak iyi), bu yüzden veri madenciliği değil.

MALİYET: daha az bacak = daha çok tek-isim riski. Madde 208'in yarım-tur
dengesizliği 1/n ile büyür. Ve 3+3/4+4 ön kayıtlı kuralın 1. şartından
düştü (22-24 Sharpe geriliyor), yani yoğunlaşmanın sınırı 5.

YAN FAYDA: bacak = bakiye/187,5 (6 bacakta /225), yani teknik alt sınır
2.250$ -> 1.875$'a iniyor.

Sharpe 4-6 bacakta TEPE yapıyor; 12+12 sadece daha az kâr değil, daha
KÖTÜ risk-ayarlı sonuç veriyordu. Sebebi madde 176'nın aynası: gelirin
%94'ü en uç bacaklardan geliyor, bacak sayısını artırmak seçimin
uçluğunu seyreltiyor.

DOĞRULAMALAR (hepsi geçti):
  - iki dönemde de Sharpe artıyor (2.07->2.33 ve 2.39->2.69)
  - ALTI saat fazının hepsinde (4+4 için Sharpe 2.17-2.41 aralığı)
  - sembol düşürme testinde de önde (4+4 ort +%85 vs 12+12 +%36)
  - AYNI RİSKE ölçeklendiğinde: 4+4 %0.6 brütle yılda ortanca +%60.3
    ve düşüş p1 -%23.8; 12+12 tam brütle +%50.6 ve p1 -%25.9. Yani
    az bacak, eşit riskte HEM daha çok kazandırıyor HEM daha sığ
    düşüyor.

DÜŞÜŞ ARTIYOR: -%17.4 -> -%20.0. Eski riski korumak isteyen
`CARRY_GROSS=0.75` ile 6+6 kullanabilir; beklenti yine 12+12'nin
üstünde kalır.

YAN FAYDA (madde 176): bacak sayısı yarıya inince bacak BÜYÜKLÜĞÜ
iki katına çıkıyor, yani minNotional yüzünden elenen sembol azalıyor.
Küçük sermayede evren daralması sorunu hafifliyor.

ESKİ ÖLÇÜM (183 sembollük hayatta-kalan panel, madde 114) bunun
TERSİNİ söylüyordu - aşağıdaki tablo o panelden, artık geçerli
değil, karşılaştırma için duruyor:
  15+15 -> +17.0% Sharpe 1.18 düşüş -17.6%
  20+20 -> +15.9% Sharpe 1.27 düşüş -15.7%
  30+30 -> +15.1% Sharpe 1.47 düşüş -12.1%   <- seçilen
  35+35 -> +14.1% Sharpe 1.50 düşüş -11.6%
Az bacak daha çok getirir ama daha çok oynar. 30+30 seçildi çünkü
KALDIRAÇLA ölçeklenebilir: Sharpe yüksek olan, aynı riskte daha çok
getirir. 30+30 @1.5x (+22.7%, düşüş -17.7%) > 15+15 @1x (+17.0%,
düşüş -17.6%)."""

FUNDING_WINDOW_HOURS = float(os.getenv("CARRY_FUNDING_WINDOW_H", "60"))
"""MADDE 442: VARSAYILAN 60 sa (T60 kitabı, sinyal paneli sk_bar60; madde
429-438). carry_parite.REFERANS_PENCERE_SAAT da 60. Eski kitap 48 ile
ölçülmüştü; aşağıdaki tarih o kitabındır.

Funding kaç SAATLİK ortalamayla sıralansın. 48 saat = 2 gün.

MADDE 209 - 8 SAATE GERİ DÖNMEYİN. Bu değer madde 182'de 72 -> 8
yapılmıştı; o karar **yanlış etiketlenmiş bir kontrole** dayanıyordu.

Deney motorunda (`g28.py`) `SINYAL_GUN=0` satırının yorumu "en son
ödeme; backtest'in bugünkü davranışı" diyordu. Gerçekte panelin sinyali
`sk = SIN.rolling(18 bar, min_periods=6).mean()`, yani **3 GÜNLÜK
ortalama**; `SINYAL_GUN` rolling'i onun ÜSTÜNE biniyor. Yani madde
182'nin tablosundaki satırlar şunlardı:

  etiket           gerçek pencere      Sharpe
  "en son ödeme"   3 gün (panelin hâli)  2.76   <- aslında 72 SAAT
  "1 gün"          3 gün (x) 1 gün ~4 gün 2.66
  "3 gün"          3 gün (x) 3 gün ~6 gün 2.59
  "24 gün"         3 gün (x) 24 gün       1.87

Tablo tutarlıydı - 3 günün ÖTESİ kötüleşiyor - ama en iyi satır "8
saat" değil, **72 saat**ti. Canlı bot 8 saate çekilince HİÇ ÖLÇÜLMEMİŞ
bir pencereyle çalışmaya başladı.

Madde 209'da pencere doğrudan tarandı - hem panel sinyaliyle hem de
CANLI BOTUN TAHMİNCİSİYLE (kısa pencere medyanı + 4sa tabanı, her BAR'da
hesaplanır; panel sinyaliyle kesitsel korelasyon 0.96). Karar tablosu
canlı tahminciyle, 2 ayrı faz ortalamasıyla, diğer her şey sabit:

  pencere    yıllık   Sharpe   22-24   25-26   maks düşüş
   8 saat    +78.6%    2.71     2.80    2.63     -13.1%   <- canlının hâliydi
  24 saat    +89.1%    2.89     2.91    2.91     -12.6%
  36 saat    +94.4%    3.00     2.91    3.14     -12.9%
  48 saat    +96.8%    3.02     2.97    3.11     -13.7%   <- SEÇİLEN
  60 saat    +95.8%    2.99     2.86    3.18     -14.1%
  72 saat    +93.7%    2.94     2.81    3.13     -14.7%

8 saat ailenin EN KÖTÜSÜ. 48 saat ön kayıtlı kuralı canlının FİİLÎ hâline
(8 saat) karşı iki dönemde de geçiyor (+0.17 ve +0.49), düşüş 0.65 puan
kötüleşiyor (tolerans 3 puan). Tepe SİVRİ DEĞİL YAYLA: 36/48/60 saat
0.03 Sharpe içinde, 24 saatten sonra düşüş pencereyle birlikte düzenli
artıyor. 72 saat (backtest panelinin kendi penceresi) da kuralı geçiyor
ama 22-24'te iyileşme sıfıra yakın (+0.005) ve düşüşü 1 puan daha derin.

Yeni beklenti: +%96.8 / Sharpe 3.02 / maks düşüş -%13.7 / 1 yıl p5
-%15.7 / p1 -%19.4. Eskisi (+%93.0 / 2.908 / -%16.2 / -%19.2 / -%23.9)
HER EKSENDE geçildi; eşit riskte +%114.5.

DİKKAT: bu ayar ZAMAN penceresidir, kayıt sayısı değil (madde 182).
Pencere sınırı DIŞLAYICI'dır (madde 209): tam pencere yaşındaki ödeme
sayılmaz, yoksa 8sa'lik bir sembolde "8 saat" son İKİ ödemeyi ortalar
ve pencere fiilen 16 saat olur.

MADDE 240 — YENİDEN AÇILDI, 48 SAAT KALDI VE TEPE SİVRİLEŞTİ. Madde
209'un taraması +%96,8 / Sharpe 3,02'lik bir yüzeydeydi; aradan 222
(bacak 6→5), 223, 224, 226, 227, 228, 230, 236 geçti. Aynı canlı
tahminci panelleriyle (`sk_bar08..72`), güncel yapılandırma, iki faz:

  pencere   yıllık   Sharpe   22-24   25-26   düşüş   eşit-risk
   8 saat   +%90,5   2,629   2,720   2,540  −14,54*   +%105,3
  24 saat  +%100,6   2,773   2,787   2,777  −13,48    +%111,5
  36 saat  +%104,3   2,821   2,697   2,995  −14,12    +%108,6
  **48 saat** +%112,5 **2,942** 2,794 3,147 −14,54   +%112,5  <- kalan
  60 saat  +%109,6   2,873   2,682   3,134  −14,48    +%110,2
  72 saat  +%105,7   2,798   2,623   3,035  −15,04    +%100,8
  (*8 saat satırının düşüşü −12,98)

Beş alternatifin HEPSİ iki dönemde de Sharpe kaybediyor; eksen tek
yönlü (8 < 24 < 36 < **48** > 60 > 72). Madde 209 bunu "36/48/60, 0,03
Sharpe içinde YAYLA" diye kaydetmişti; bugün 48, 60'ı **0,069** ve
36'yı **0,121** Sharpe geçiyor. **Kitabın geri kalanı iyileştikçe
optimum belirsizleşmedi, keskinleşti** — yani bu parametre artık
"plato içinde herhangi bir yer" değil, gerçek bir tepe.

Araç: `arastirma_madde240.py`."""

REBALANCE_HOURS = float(os.getenv("CARRY_REBALANCE_H", "120"))
"""Kaç saatte bir yeniden dengelensin. 120sa = 5 gün.

MADDE 223 — YENİDEN AÇILDI VE YİNE 5 GÜN ÇIKTI. Bu parametre madde
120'de taranmıştı; madde 222'nin kuralı ("bir parametre taranmış ve
optimumda ise, o taramadan BERİ kabul edilen her değişiklik onu
yeniden açar") onu yeniden açtı, çünkü aradan 184/189/196/209/222
geçti. Güncel yapılandırma (5+5 bacak, 15 dilim, 48sa pencere,
TPL 0,40 / TPS 0,20), tur aralığı 8 saatte SABİT, iki faz ortalaması:

  tutma   dilim    yıllık   Sharpe   düşüş   Sh 22-24   Sh 25-26   eşit-risk
  3 gün      9   +132.1%    3.054   −17.8      2.877      3.320     +116.5%
  4 gün     12   +118.9%    3.052   −16.8      2.916      3.262     +116.3%
  5 gün     15   +112.6%   *3.128*  −14.6     *2.984*    *3.342*    +112.6%  <- kalan
  6 gün     18    +99.8%    3.036   −14.4      2.884      3.257     +101.4%
  7 gün     21    +88.4%    2.913   −14.0      2.817      3.061      +92.5%

DÖRDÜ DE ÖN KAYITLI KURALDA REDDEDİLDİ (madde 212/218):
  3 gün: Sharpe iki dönemde de düşük, düşüş +3,26 puan (tolerans 3,0)
  4 gün: Sharpe iki dönemde de düşük (−0,068 / −0,080)
  6-7 gün: Sharpe düşük VE eşit riskte getiri −11,1 / −20,1 puan

3 ve 4 gün eşit riskte +3,9 / +3,7 puan DAHA getiriyordu - kural
onları yalnızca Sharpe şartından reddetti. Eşli blok bootstrap (1.504
gün, 21 günlük blok, 2.000 örnek, aynı günler) o kazancın GÜRÜLTÜ
olduğunu gösterdi:

  aday    ΔSharpe  [p5, p95]   P(ΔSh>0)   Δeşit-risk  [p5, p95]   P(>0)
  3 gün   −0.087 [−0.31,+0.12]   26,6%     −5,7  [−43,6, +37,8]   37,5%
  4 gün   −0.066 [−0.19,+0.04]   15,9%     −5,0  [−28,8, +16,9]   33,8%
  6 gün   −0.098 [−0.18,−0.01]  **2,7%**   −7,0  [−22,5,  +7,5]   20,9%
  7 gün   −0.204 [−0.36,−0.04]  **1,9%**  −15,3  [−39,6,  +7,8]   12,9%

Yani kısa tutma "daha iyi değil, sadece ayırt edilemez"; UZUN tutma
(6-7 gün) ise GERÇEKTEN kötü (p < %3). 5 gün korunur.

MADDE 239 — AYNI ANDA İKİ UFUK ("vade merdiveni") de denendi: tek bir
tutma süresi yerine 2 günlük ve 5 günlük kitapları birlikte tutmak (her
biri kendi içinde piyasa-nötr; madde 215'in kapattığı TARAF asimetrisi
değil, KİTAPLAR arası asimetri). Tam örnekte DÖRT ŞARTI DA geçiyor ve
kaldıraçsız üstün:

  harman          yıllık   Sharpe   22-24   25-26   düşüş   eşit-risk
  %25 2g + %75 5g +%121,5   2,980   2,829   3,194  −13,55    +%130,4
  %33 2g + %67 5g +%124,5   2,978   2,832   3,189  −13,77    +%131,4
  %50 2g + %50 5g +%130,6   2,958   2,827   3,157  −14,23    +%133,4

AMA BOOTSTRAP ÇÖKERTİYOR: Δeşit-risk +22,5 puan → **+3,9 puan**,
P(>0) %59,7; ΔSharpe P %70,2. Ve doz-yanıt TERS: 2 gün payı arttıkça
güven azalıyor (%70,2 → %64,3 → %53,5). 2 gün TEK başına açıkça kötü
(Δeşit-risk −14,6 puan, P %27,0). **RED.** Bu madde 227'nin AYNASI:
orada kuralı geçen bir aday bootstrap'ta çökmüştü; burada aynısı bir
YAPI için oldu. Araç: `arastirma_vade_merdiveni.py`.

Yan bulgu (madde 237'yi rafine eder): 2g ve 5g kitaplarının GÜNLÜK
GETİRİ korelasyonu **+0,875** - momentumun +0,718'inden daha YÜKSEK -
ve yine eklemiyor. Yani korelasyon eşiği tek başına ne kabul ne red
gerekçesidir; "aynı piyasa duvarı" bir eşikten daha derin.

MEKANİZMA (madde 223'ün asıl bulgusu): getiri farkı dilim
sayısından DEĞİL, tutma süresinden geliyor. Dilim sayısı 18'de
SABİTLENİP tutma süresi değiştirildiğinde:
  3 gün, 18 dilim (4sa aralık): +131.8%  Sharpe 3.06  düşüş −17.8
  3 gün,  9 dilim (8sa aralık): +132.1%  Sharpe 3.05  düşüş −17.8
  6 gün, 18 dilim (8sa aralık):  +99.8%  Sharpe 3.04  düşüş −14.4
Dilim sayısı faz ORTALAMASINI hiç oynatmıyor (+131,8 vs +132,1).
Bu madde 184'le çelişmez, onu açıklar: 184'ün kazancı da getiri
değildi (+%91,5 → +%91,6), faz YAYILIMIydı (22,6 → 2,5 puan).
N_DILIM bir risk parametresi değil, bir BELİRLİLİK parametresidir.

Tutma süresi ise bir KALDIRAÇ kolu gibi davranıyor: kısaldıkça
getiri ve düşüş birlikte büyüyor, Sharpe neredeyse sabit kalıyor.
Daha fazla getiri isteniyorsa doğru kol CARRY_GROSS'tur (orada
ölçülmüş), tutma süresini kısaltmak değil - aynı riski daha kötü
Sharpe'la satın alır."""

GROSS_EXPOSURE = float(os.getenv("CARRY_GROSS", "1.0"))
"""Toplam pozisyon / sermaye. 1.0 = kaldıraçsız (long %50 + short %50).

Güncel ölçüm (madde 149; 12+12, kalabalık seçimi, %70 kâr al, maker,
2022-01 -> 2026-08):

  gross   yıllık    Sharpe   max düşüş   en kötü ay
  1.0x   +53.4%     2.03     -18.4%      -6.7%
  1.5x   +86.6%     2.03     -26.6%     -10.0%
  2.0x  +124.4%     2.03     -34.1%     -13.3%

Sabit kaldıraç, oynaklık hedefli profillerden (CARRY_RISK) daha iyi
ya da eşit: hedefleme Sharpe'ı artırmıyor (1.88-2.02).

Backtest düşüşü iyimser: rastgele seçim denemelerinde kaldıraçsız
düşüş -%18 ile -%30 arasında değişti (madde 148.2). 2x'te -%40 ile
-%60 arası bir düşüş gerçekçi bir kötü senaryodur. Kaldıraç
kullanılacaksa önce 1x'te canlı ölçüm yapın.

MADDE 276 — YUKARIDAKİ MADDE 149 TABLOSU BAYAT; DOZ KARARI VERİLDİ.
O tablo 12+12 / %70 kâr al kitabından (1x'te +%53,4). Bugünkü kitap
1x'te **+%111,7** (madde 265'in icra düzeltmesiyle), max düşüş −%14,54.
Dozu artık tablo değil, kullanıcının TOLERANSI belirliyor (madde
261/243'ün karıştırma p95'i):

  tolerans (1 yıl p95 düşüş)   brüt     net yıllık
    −%20                      0,955x     +%104,9
    −%25                      1,219x     +%147,3
   *−%30  <- karar*          *1,254x*   *+%153,4*   (p5; medyan 1,497x)
    −%35                      1,786x     +%263,9

**Çözülen brüt TEK BİR SAYI DEĞİL:** blok bootstrap'ta −%30 toleransı
p5 1,254x · medyan 1,497x · p95 1,921x istiyor (Monte Carlo yayılımı
yalnız 0,015; örnekleme yayılımı **0,667**). Karar **ihtiyatlı uçtan**
verildi: 1,25x.

Likidasyon bağlayıcı değil: madde 266'nın gün içi kuyruğu (1x'te
−%41,41) ile duvar mmr %1'de 2,358x; 1,25x duvarın %53'ünde, 46,8 puan
pay var.

AMA EKRANDA GÖRÜLECEK SAYI −%30 DEĞİL: tolerans günlük KAPANIŞ
serisinde tanımlı, madde 266 gün içi yolun medyanda 1,488 kat derin
olduğunu ölçtü -> gün içi karşılığı **~−%45**, ölçülen kuyruk −%52.

**VARSAYILAN YİNE DE 1,0:** bot hiç canlı çalışmadı ve üç icra
varsayımı (madde 265/266/267) yalnız 2 aylık dakika verisinde
doğrulandı. Doz, madde 216'nın takvimi tamamlandıktan sonra tek satırla
açılır: `CARRY_GROSS=1.25`. Borsa kaldıracını `gerekli_kaldirac()`
kendisi hesaplar (1,5 kat pay + ÇAPRAZ teminat).

MADDE 239 — BRÜTÜ ZAMANA GÖRE DEĞİŞTİRMENİN BİR YOLU VAR VE ÖLÇÜLDÜ
(kabul EDİLMEDİ). Madde 165 "değişken kaldıraç, aynı ortalamada sabit
kaldıraçtan 14-24 puan kötü" demişti - ama orada koşullayıcı OYNAKLIK'tı.
Madde 239 koşullayıcıyı değiştirdi: **kesitsel funding dağılımı**
(uygun sembollerde p90-p10, 30 günlük ortalama, kendi 180 günlük YEREL
medyanına göre, 1 bar gecikmeli). Önce bütçe ölçüldü - bu ölçü kitabın
KENDİ ileriye dönük getirisini tek yönlü sıralıyor:

  prim çeyreği   yıllık   Sharpe   oynaklık   (tam örnek)
  Q1 (en dar)    +%49,7    1,67      %26,1
  Q2             +%84,6    2,34      %27,9
  Q3            +%117,0    3,29      %24,5
  Q4 (en geniş) +%239,9    4,42      %28,7

**Oynaklık çeyrekler arasında DÜZ.** Yani ölçü bir oynaklık vekili
değil, EDGE YOĞUNLUĞU ölçüsü: funding kesiti genişken her dolar daha
çok kazanıyor. Fiyat tahmini yok - bu yüzden botun kimliğini bozmuyor.

Yapı (`g33.py`: `BRUT_PRIM/BRUT_ALT/BRUT_UST/BRUT_REF`), iki faz:

  varyant        yıllık   Sharpe   22-24   25-26   düşüş   eşit-risk  ort brüt
  kontrol       +%112,5   2,942   2,794   3,147   −14,54    +%112,5    1,000x
  e0,5 ref180   +%137,3   3,061   3,069   3,115   −13,31    +%150,0    1,058x
  e1,0 ref180   +%137,3   3,067   3,143   3,065   −13,55    +%147,4    1,031x
  e1,5 ref180   +%134,4   3,052   3,129   3,062   −13,89    +%140,7    1,005x
  PLASEBO ters  +%116,4   2,807   2,735   2,909   −18,29     +%92,5    1,036x
  yalnız nakit  +%93,6    2,985   2,960   3,050   −12,49    +%109,0    0,848x

Getiri 25 puan artıyor, düşüş 1,2 puan SIĞLAŞIYOR, ortalama brüt
1,06x - ve **plasebo (aynı çarpan dağılımı, zamanda ters) yapıyı yok
ediyor** (+%92,5). Yani taşıyan şey doz değil ZAMANLAMA. Bootstrap:
ΔSharpe +0,117 (P %83,9), Δeşit-risk +22,2 puan (P %79,0).

**RED - tek sebep ŞART 1:** 25-26 Sharpe'ı 3,147 → 3,115 (−0,032). Alt
dönem bootstrap'i (4.000 örnek) o reddin tabanını gösteriyor: 22-24'te
ΔSharpe +0,269 ile **P %95,6**, 25-26'da −0,008 ile **P %48,2** (yazı
tura). Yani yapı bir dönemde yüksek güvenle iyileştiriyor, ötekinde
sıfırdan ayırt edilemiyor. Kural "her iki dönemde de iyileşme" istiyor
ve **kural DEĞİŞTİRİLMEDİ**: aday eldeyken kuralı gevşetmek madde
212'nin kapattığı deliğin ta kendisi.

İKİ UYARI: (1) kazanç yalnızca nakde çekmeden GELMİYOR - üst sınır
1,0'da tutulunca eşit riskte +3,6 puan kalıyor ve o da 1,17x kaldıraç
istiyor; yapı primin geniş olduğu dönemde brütü 1,5x'e kadar ARTIRMAYA
dayanıyor, yani kısmen bir KALDIRAÇ kararıdır (madde 227'nin bekleyen
kararı) ve motor likidasyonu modellemez. (2) ölçü 2025-26'da tek yönlü
DEĞİL; bütçe analizi ile şart 1 aynı şeyi söylüyor.

Araçlar: `arastirma_prim_butce.py`, `arastirma_prim_karar.py`.

MADDE 288 — DOZ TARANDI, KURALI GEÇEN BİR NOKTA VAR, YAPI ARTIK BOTTA
KURULU (varsayılan KAPALI). Madde 239 bu yapıyı tek bir dozda (e0,5)
ölçtü. Madde 288 (e, ref) ızgarasını taradı (25 hücre) ve 25-26 Sharpe
açığının e ile monoton büyüdüğünü gördü: e0,10 **+0,003** · e0,15
−0,001 · e0,25 −0,013 · e0,50 −0,020 · e0,75 −0,033 · e1,00 −0,028.
e0,10'da şart 1 ARTIYA geçiyor. Geçen band ref 120-180 (ref 90 −0,021
ve ref 270 −0,006 DÜŞÜYOR), bandın ortası ve en iyisi **ref150**:

  e0,10 ref150, faz ortalaması, `gecer_mi()` = GEÇER
    22-24 2,871 vs 2,789 (+0,082) · 25-26 3,159 vs 3,147 (+0,012)
    düşüş −14,27 vs −14,54 · eşit-risk +%120,9 (+8,6 puan) · kald. 1,02x
    doz ölçütü +12,15 puan · ortalama çarpan ~1,005x

İKİNCİ ELEK (kuralın geçmesi YETMEZ, bkz. aşağıdaki yasa): doz
ölçütünde eşli blok bootstrap **P(>0) %95,0** (e0,10 ref120'de ölçüldü;
bar %80), 22-24 ΔSharpe P %98,0, 25-26 ΔSharpe +0,0165 P %66,6 (zarar
YOK), madde 284'ün bahis fiyatı: **bahis DEĞİL** - 22-24 +17,06 ve
25-26 +0,81, iki rejimde de kazanıyor.

MADDE 288'İN ÜÇÜNCÜ YASASI — DÖRT ŞART KURALI HİÇBİR ŞEY YAPMAYAN BİR
ADAYI GEÇİRİR. `BRUT_PLASEBO=2` (aynı çarpan dağılımı, zamanda
KARIŞTIRILMIŞ, yani saf gürültü) `gecer_mi()`'den **GEÇTİ**: 22-24
+0,004 · 25-26 +0,005 · eşit-risk +2,3. Sebep mekanik: ±%0,5'lik
rastgele bir modülasyon iki Sharpe farkını iki bağımsız yazı-turaya
çevirir (~%25 geçme şansı) ve kalan üç şart otomatik geçer. Yani
"dört şartı da geçti" bir KANIT cümlesi değil, bir ELEME cümlesidir.
Ayıran ölçüt doz ölçütü + bootstrap: aday %95,0, karıştırılmış plasebo
**%71,0**, zamanda ters plasebo şart 1 ve şart 3'ten DÜŞÜYOR
(eşit-risk −2,7, düşüş kötüleşiyor). Sicilde plasebolar hep getiriyle
kıyaslanmış, hiç `gecer_mi()`'ye verilmemişti.

VARSAYILAN NEDEN YİNE DE KAPALI (madde 277'nin yasası: belgeye uyarı
yazmak varsayılanı güvenli kılmaz, o yüzden burada varsayılanın KENDİSİ
kapalı): bot hiç canlı çalışmadı, doz ölçütü icra varsayımları yalnız
2 aylık dakika verisinde doğrulanmış bir geri testte ölçülüyor ve
üçüncü yasa gereği kuralın geçmesi tek başına bir kabul gerekçesi
değil. Ayrıca çarpan ilk ~75 günde zaten 1,0 döner (kayan medyan için
geçmiş birikmesi gerekir), yani ilk çeyrekte hiçbir etkisi olamaz.
Madde 216'nın takvimi bittikten sonra tek satırla açılır:
`CARRY_PRIM_E=0.10` (ref varsayılanı zaten 150).

Araçlar: `arastirma_prim_doz.py`."""

PRIM_E = float(os.getenv("CARRY_PRIM_E", "0.0"))
"""Prim-ölçekli brütün duyarlılık üssü. **0 = KAPALI (varsayılan).**
Madde 288'in kuralı geçen noktası 0,10. Üs büyüdükçe 22-24 kazancı
büyüyor ama 25-26 şart 1'den düşüyor (yukarıdaki monoton tablo)."""

PRIM_REF_GUN = int(os.getenv("CARRY_PRIM_REF", "150"))
"""Primin kendi normunu ölçtüğü KAYAN medyan penceresi (gün).

MADDE 288: geçen band 120-180 (ref 90 −0,021 ve ref 270 −0,006 şart
1'den düşüyor), 150 bandın ORTASI ve aynı zamanda en iyisi. Hücre
bandın ortasından alındı, en iyisinden değil (madde 276'nın yöntemi).
GENİŞLEYEN değil KAYAN medyan: madde 239'un notu - genişleyen medyan
yapıyı "2025 sonrası kaldıraç artır"a çevirir, o TEK bir gerçekleşme."""

PRIM_OLC_GUN = int(os.getenv("CARRY_PRIM_OLC", "30"))
"""Prim ölçüm penceresi (gün) - motorun BRUT_OLC'si.
MADDE 288: madde 239'un ölçtüğü yapıdan birebir devralındı, taranmadı
(taranan eksen üs ve referans penceresiydi)."""

PRIM_ALT = float(os.getenv("CARRY_PRIM_ALT", "0.5"))
"""Çarpanın TABANI. MADDE 288: motorun BRUT_ALT'ından birebir;
e=0,10'da gerçekleşen aralık ~0,99-1,05, yani taban hiç dolmuyor."""

PRIM_UST = float(os.getenv("CARRY_PRIM_UST", "1.5"))
"""Çarpanın TAVANI. MADDE 288: motorun BRUT_UST'undan birebir. Tavan
ancak prim kendi medyanının 57 katına çıkarsa dolar (1,5^10) - ama
`gerekli_kaldirac()` payı yine bu tavanla büyütüyor, çünkü yanlış taraf
borsa emrinin reddi olurdu."""

PRIM_DOSYA = os.getenv("CARRY_PRIM_DOSYA", "carry_prim.csv")
"""Kesitsel prim geçmişi (zaman,değer). MADDE 288: her turda bir satır -
EK API İSTEĞİ YOK, ölçü zaten toplanan funding serisinden çıkıyor.
Dosya silinirse çarpan 1,0'a döner (zararsız yön), kazanç gider."""

MIN_DAILY_VOLUME_USD = float(os.getenv("CARRY_MIN_VOLUME", "70000000"))
"""MADDE 442: VARSAYILAN 70M (T60 kitabı; madde 401-403 "geniş evren", 429-438).
Eski kitap 100M ile ölçülmüştü; aşağıdaki tarih o kitabındır.

Bu hacmin altındaki coinler elenir.

DEĞİŞTİ: 5.000.000 -> 100.000.000 (madde 133).

Eski değer 183 sembollük panelde ölçülmüştü ve o panelde "evreni
daraltmak kârı öldürür" çıkıyordu. O panel HAYATTA KALANLARDAN
oluşuyordu - yani düşük hacimli kuyruğun ölen kısmı hiç yoktu.
847 sembollük tam evrende (delist edilmişler dahil) ölçüm TERSİNE
döndü; eşik tek başına en büyük kâr kaldıracı:

  hacim eşiği   yıllık   Sharpe   max düşüş   evren
  filtresiz     -25.2%    -1.25     -78.9%     212
  $30M           +4.7%    +0.36     -26.3%      72
  $50M           +5.4%    +0.39     -25.7%      54
  $100M         +14.5%    +0.73     -28.1%      34
  $200M (evren 19 sembol - bacak kurmaya yetmiyor)

Monoton bir ilişki; tek bir hücrenin tesadüfü değil.

MADDE 226 — YENİDEN AÇILDI, 100M KALDI; TEPE HER İKİ YANDAN DOĞRULANDI.
Yukarıdaki tarama Sharpe 0,73'lük bir yüzeyde yapılmıştı (bugün 3,13) ve
200M'i "evren 19 sembol, 12+12 bacak kurmaya yetmiyor" diye reddetmişti.
Bacak 5+5 olduğu için kısıt gevşemiş görünüyordu - GEVŞEMEMİŞ:

  madde 133'te: havuz yok      -> taraf başına 12 aday gerekiyordu
  bugün:        havuz 3,0 x 5  -> taraf başına **15** aday gerekiyor

Madde 179 havuzu getirdi, madde 222 bacağı indirdi; ikisi TERS yönde
hareket etti ve net gereksinim 12'den 15'e ÇIKTI. Evren ölçümü:

  eşik    ortalama evren   medyan   min   15+15 adayın çıktığı gün oranı
  100M         38.4          36      9              %72.4
  150M         27.8          26      5              %35.0
  200M         21.7          20      4              %15.9
  300M         14.9          13      2               %4.5

Yani 150M'de günlerin üçte ikisinde kitap eksik bacakla kuruluyor.
Tarama (iki faz ortalaması):

  eşik    yıllık   Sharpe   düşüş   22-24   25-26   eşit-risk
   50M   +107.8    2.972   −15.9   2.980   3.007    +95.3%
  100M  *+112.6*  *3.128*  −14.6  *2.984* *3.342*  +112.6%  <- kalan
  150M    +89.2    2.756   −15.3   2.615   2.968    +89.2%
  200M    +74.7    2.533   −18.2   2.680   2.388    +56.2%

Üçü de RED. 100M **her iki yandan** tepe: gevşetmek de sıkmak da
kötüleştiriyor. Madde 133'ün monoton "sıktıkça iyi" ilişkisi artık
geçerli değil - o ilişki bir TEPEYE dönüşmüş ve tepe tam burada.

Mekanizma tek cümlede: eşik iki şeyi birden yapıyor - kaliteyi
yükseltiyor VE evreni daraltıyor. Madde 133'ün yüzeyinde birincisi
baskındı; kitap 5+5 bacağa ve 3,0 havuza geçtikten sonra ikincisi
bağlayıcı hâle geldi.

ÖLÇÜM ARACI DOĞRULANDI: 100.000.001$ (yeniden kurma yolunu tetikler,
eşik fiilen aynı) kontrolle birebir aynı çıktı (+%112,3 / 3,10 /
−%14,5). Eşik taraması bu paritenin üstünde okunmalıdır."""

MIN_LISTELEME_GUN = int(os.getenv("CARRY_MIN_LISTING_DAYS", "60"))
"""MADDE 442: VARSAYILAN 60 gün (T60 kitabı; madde 396-397, 429-433). 60 gün
ALTINA İNİLMEZ: madde 427'de 45 gün MYX/AIA short sıkışmalarıyla hesabı
sıfırladı; 90 günün altı short felaket stop'u (CARRY_SHORT_STOP) olmadan
çalıştırılmaz (preflight HATA). Eski kitap 90 gün ile ölçülmüştü.

Listelendikten sonra en az bu kadar gün geçmiş olmalı.

Yeni listelenen coinler carry için ZEHİRDİR: funding oranları uç
değerler alır (bu yüzden sıralamada hep en üste çıkarlar) ama fiyat
hareketi funding gelirinin kat kat üstünde zarar yazar. Ölçüm
($100M hacim eşiğiyle birlikte, madde 133):

  yaş eşiği   yıllık   Sharpe   max düşüş
  yok          +6.1%    +0.37     -37.5%
  30 gün      +10.7%    +0.56     -31.6%
  90 gün      +14.5%    +0.73     -28.1%
  180 gün     +16.1%    +0.78     -30.7%

90 gün seçildi: 180'in getirisi biraz daha yüksek ama evreni 30
sembole indiriyor ve bu bacak kurmak için fazla dar.
0 = kapalı.

MADDE 228 — YENİDEN AÇILDI, 90 GÜN KALDI VE TABLO TERSİNE DÖNDÜ.
Yukarıdaki ölçüm madde 133'ün yüzeyinden (Sharpe 0,73). Motora bu
madde için `YAS_GUN` kolu eklendi (eskiden dışarı verilmiyordu; parite
ile doğrulandı: aynı eşikte taban birebir aynı çıkıyor).

  yaş eşiği   yıllık   Sharpe   düşüş   22-24   25-26   eşit-risk   evren
   30 gün    +106.1   2.840   −17.8   2.888   2.840     +85.1%    41.7
  *90 gün*  *+112.6* *3.128*  −14.6  *2.984* *3.342*   +112.6%    38.4  <- kalan
  180 gün     +94.8   2.890   −14.8   2.692   3.169     +92.6%    35.4
  270 gün     +72.6   2.589   −20.6   2.736   2.411     +47.2%    31.3

Madde 133'te 180 gün 90'dan DAHA İYİ görünüyordu (+%16,1 vs +%14,5) ve
yalnızca "evren 30 sembole iniyor" diye reddedilmişti. Bugün 180 gün
AÇIKÇA kötü: bootstrap P(ΔSharpe>0) = **%5,3**, eşit riskte −18,0
puan. Üstelik red gerekçesi de yanlışmış - güncel panelde 180 günün
evren maliyeti ortalama 38,4 → 35,4, yani "30 sembole inmek" değil.
**Doğru karar, yanlış gerekçeyle verilmişti; doğruluğu bugün gerçek
gerekçesiyle ölçüldü.**"""

MAX_SYMBOLS = int(os.getenv("CARRY_MAX_SYMBOLS", "95"))
"""Evren üst sınırı. Yeni eşiklerle evren zaten ~35-45 sembol, yani
bu sınır artık bağlayıcı değil - güvenlik amaçlı duruyor."""

LEVERAGE = int(os.getenv("CARRY_LEVERAGE", "1"))
"""Borsa tarafı kaldıraç için ALT SINIR. Pozisyon boyutunu GROSS_EXPOSURE
belirler; bu sadece teminat gereksinimini belirler. Bot en az
`gerekli_kaldirac()` kadarını ayarlar (madde 149): 1'de bırakılırsa
emirler "Margin is insufficient" ile reddedilirdi. Semboller ÇAPRAZ
teminata alınır; çapraz modda bu sayı likidasyon riskini artırmaz."""

def gerekli_kaldirac() -> int:
    """Borsa tarafında ayarlanacak kaldıraç (madde 149).

    Binance'te açılabilecek toplam pozisyon ~ teminat x borsa kaldıracı.
    Bot brüt GROSS_EXPOSURE x ölçek (oynaklık hedefiyle 3.0'a kadar)
    pozisyon açar. Borsa kaldıracı 1'de kalırsa emirler "Margin is
    insufficient" ile reddedilir. 1.5 kat pay bırakılır (gerçekleşmemiş
    zarar teminatı düşürür, rebalance'ta eski ve yeni emir üst üste binebilir).

    ÇAPRAZ teminatta bu sayı RİSKİ ARTIRMAZ: pozisyon büyüklüğünü
    GROSS_EXPOSURE belirler, likidasyon hesap düzeyindedir. Bu yüzden
    teminat modu her sembolde CROSSED'a çekilir."""
    import math
    olcek_max = 3.0 if VOL_HEDEF else 1.0
    # MADDE 288: prim-ölçekli brüt açıksa çarpanın TAVANI da paya girer.
    # İHTİYATLI: gerçekleşen tavan e=0,10'da ~1,05, ama burada kırpma
    # tavanı (1,5) kullanılıyor - yanlış taraf borsa emrinin reddi olurdu.
    if PRIM_E > 0:
        olcek_max *= PRIM_UST
    return max(LEVERAGE, int(math.ceil(GROSS_EXPOSURE * olcek_max * 1.5)))


_KALDIRAC_AYARLI: set = set()


def kaldirac_hazirla(client, sembol: str) -> bool:
    """Sembolü ÇAPRAZ teminata ve gerekli kaldıraca alır (süreç başına bir kez).

    İzole teminatta yüksek borsa kaldıracı her pozisyonu ayrı likidasyona
    açar - bu stratejide ölümcül (short bacakta +%20 sık görülür). Çapraz
    teminata alınamazsa (ör. o sembolde izole pozisyon açık) False döner
    ve kaldıraç YÜKSELTİLMEZ."""
    if sembol in _KALDIRAC_AYARLI:
        return True
    capraz = True
    try:
        client.client.futures_change_margin_type(symbol=sembol, marginType="CROSSED")
    except Exception as e:
        # -4046: zaten CROSSED (Binance "No need to change margin type")
        if "4046" not in str(e) and "No need" not in str(e):
            capraz = False
            logger.error("%s ÇAPRAZ teminata alınamadı (%s) - kaldıraç "
                         "yükseltilmedi; izole teminat bu strateji için tehlikeli", sembol, e)
    if capraz:
        try:
            client.set_leverage(sembol, gerekli_kaldirac())
        except Exception as e:
            logger.warning("%s kaldıraç ayarlanamadı: %s", sembol, e)
        _KALDIRAC_AYARLI.add(sembol)
    return capraz


# --------------------------------------------- MADDE 211: ELLE AYAR DEĞİŞİMİ
POZ_MODU_KONTROL = os.getenv("CARRY_POZ_MODU_KONTROL", "1") not in ("0", "false", "False")
"""Her turda pozisyon modunun TEK YÖNLÜ olduğu doğrulansın mı (madde 211)."""

IZOLE_KAPAT = os.getenv("CARRY_IZOLE_KAPAT", "1") not in ("0", "false", "False")
"""İzole teminatta bulunan sembol KAPATILSIN mı (madde 211)."""

IZOLE_OLCUM = {2: (3.3, 23.0), 3: (7.2, 34.0), 5: (19.3, 54.0), 10: (45.3, 64.0)}
"""Borsa kaldıracı -> (izole likidasyon eşiğini delen bacak-tutma yüzdesi,
hepsi izole olsa yıllık yanan teminat yüzdesi). Madde 211'de 3.860
bacak-tutma üzerinde ölçüldü; eşik ~1/kaldıraç. Sadece uyarı metnini
doğru rakamla yazmak için var."""


def tek_yonlu_mu(client) -> bool | None:
    """Hesap TEK YÖNLÜ (one-way) pozisyon modunda mı? None = bilinmiyor.

    MADDE 211. Hedge (çift yönlü) modda Binance her emirde `positionSide`
    ister; bot göndermediği için emirler `-4061` ile REDDEDİLİR ve
    `reduceOnly` (kâr al) hiç kabul edilmez. Yani bot HİÇ İŞLEM AÇAMAZ.

    Bu, projedeki en kötü hata sınıfı: bot çalışıyor görünür ama
    `_emirleri_gonder` "bacak AÇILAMADI" deyip kullanıcıyı
    "bakiye/minimum emir büyüklüğü veya API izinleri"ne yönlendirir -
    YANLIŞ SEBEBE. Bir kullanıcı günlerce bakiye kovalayabilir.

    Bilinmiyorsa (API hatası) True kabul edilir: dedektörün arızası botu
    durdurmamalı (madde 123).
    """
    try:
        m = client.client.futures_get_position_mode()
    except Exception as e:
        logger.warning("pozisyon modu okunamadı (%s) - tek yönlü varsayılıyor", e)
        return None
    try:
        return not bool(m.get("dualSidePosition"))
    except AttributeError:
        return None


def pozisyon_modu_hazirla(client, mevcut: dict) -> bool:
    """Hedge modda ise düzeltmeyi dener; tur devam edebilir mi onu döner.

    Pozisyon YOKSA tek yönlüye geçilir (Binance bunu ancak pozisyon
    kapalıyken kabul eder). Pozisyon VARSA geçilemez; tur atlanır ve ne
    yapılacağı tam olarak söylenir - sessiz duruş bırakılmaz.
    """
    if not POZ_MODU_KONTROL:
        return True
    tek = tek_yonlu_mu(client)
    if tek or tek is None:
        return True
    if not mevcut:
        try:
            client.client.futures_change_position_mode(dualSidePosition="false")
            logger.error("HESAP HEDGE (ÇİFT YÖNLÜ) MODDAYDI - pozisyon olmadığı "
                         "için TEK YÖNLÜ moda alındı. Bu modda bot hiç işlem "
                         "açamıyordu (emirler -4061 ile reddedilir).")
            return True
        except Exception as e:
            logger.error("hedge modundan çıkılamadı: %s", e)
    logger.error(
        "HESAP HEDGE (ÇİFT YÖNLÜ) POZİSYON MODUNDA - bot bu modda HİÇ İŞLEM "
        "AÇAMAZ: her emir `positionSide` ister, reduce-only kâr al emri hiç "
        "kabul edilmez. Emirler -4061 ile reddedilir ve hata mesajı sizi "
        "YANLIŞ SEBEBE (bakiye/izin) yönlendirir. ÇÖZÜM: Binance Futures "
        "arayüzünde tüm pozisyonları kapatıp Ayarlar > Pozisyon Modu'nu "
        "'Tek Yönlü'ye alın (%d pozisyon açık). Tur ATLANDI.", len(mevcut))
    return False


def izole_teminatlilar(client) -> list[str]:
    """İZOLE teminatta açık pozisyonu olan semboller (madde 211).

    `kaldirac_hazirla` süreç başına CACHE'liyor (`_KALDIRAC_AYARLI`): bir
    sembol bir kez ÇAPRAZ'a alındıktan sonra bir daha KONTROL EDİLMİYOR.
    Kullanıcı o sembolü elle izoleye çekerse bot orada işlem yapmaya
    devam eder. Docstring'in "ölümcül" dediği şey ölçüldü:

      kaldıraç  likidasyon  tetiklenen bacak  yılda  yanan teminat/yıl
        2x         ~%50         %3.3            28      ~%23 sermaye
        3x         ~%33         %7.2            61      ~%34 sermaye
        5x         ~%20        %19.3           163      ~%54 sermaye
       10x         ~%10        %45.3           382      ~%64 sermaye

    (3.860 bacak-tutma, 4,6 yıl, seçilen kitabın gerçek bacakları; yanan
    teminat = nominal/kaldıraç, artı kaybolan bacağın kirası ve nötrlüğün
    bozulması. Varsayılan ayarda kaldıraç 2x - yine de getirinin dörtte
    birinden fazlası.)

    Tespit BEDAVA: `futures_position_information` zaten çekiliyor ve
    `marginType` alanını veriyor. Bu yüzden cache'e güvenilmiyor,
    borsanın kendi cevabı okunuyor.
    """
    out = []
    try:
        poz = client.get_open_positions()
    except Exception as e:
        logger.warning("izole teminat kontrolü yapılamadı: %s", e)
        return out
    for p in poz:
        try:
            if abs(float(p["positionAmt"])) < 1e-12:
                continue
            if str(p.get("marginType", "cross")).lower().startswith("isolated"):
                out.append(p["symbol"])
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(set(out))


def izole_ele(hedef: dict, izole: list[str]) -> list[str]:
    """İzole sembolleri hedeften ÇIKARIR (yani kapatılmalarını sağlar).

    Hedefte kalsalar bot onları büyütmeye devam ederdi. Çıkarıldığında
    `emirleri_hesapla` kapatma emri üretir; kapandıktan sonra
    `kaldirac_hazirla` yeniden ÇAPRAZ'a alabilir (Binance teminat modunu
    ancak pozisyon kapalıyken değiştiriyor), bu yüzden cache'ten de
    düşürülür.
    """
    if not izole:
        return []
    atilan = []
    for s in izole:
        if s in hedef:
            hedef.pop(s, None)
            atilan.append(s)
        _KALDIRAC_AYARLI.discard(s)     # kapanınca ÇAPRAZ yeniden denenebilsin
    kal = max(1, gerekli_kaldirac())
    pay, yil_maliyet = IZOLE_OLCUM.get(kal, IZOLE_OLCUM[max(IZOLE_OLCUM)])
    logger.error(
        "İZOLE TEMİNATTA %d SEMBOL: %s. Bu strateji izole teminatta "
        "ÖLÜMCÜL: borsa kaldıracı %dx ile likidasyon ~%%%.0f'te ve seçilen "
        "kitapta bacak-tutmaların %%%.1f'i 5 gün içinde bu eşiği deliyor "
        "(hepsi izole olsa yanan teminat yıllık ~%%%.0f sermaye). "
        "Pozisyonlar KAPATILIYOR; kapandıktan sonra bot onları yeniden "
        "ÇAPRAZ'a alacak. Elle izoleye çektiyseniz geri alın "
        "(CARRY_IZOLE_KAPAT=0 ile bu koruma kapatılabilir).",
        len(izole), ", ".join(izole[:8]), kal, 100.0 / kal, pay, yil_maliyet)
    return atilan


MIN_NOTIONAL_USD = 5.0
"""Binance minimum emir büyüklüğü. Altındaki bacaklar atlanır."""

OTOMATIK_BACAK = os.getenv("CARRY_OTO_BACAK", "1") not in ("0", "false", "False")
"""Bacak sayısı bakiyeye göre otomatik ayarlansın mı? Varsayılan: EVET.

KÜÇÜK BAKİYE SORUNU (madde 130): 30+30 bacak ve 5 dilimde pozisyon
başına düşen tutar = bakiye x ölçek / 5 / 60. 2.000 USDT'de bu
sadece 6.7 USDT (ölçek 1.0) - Binance minimumu 5 USDT'nin hemen
üstünde. Minimumun altına düşen bacaklar ATLANIR, yani portföy
eksik ve DENGESİZ kurulur.

Ölçüldü (2.000 USDT, dengeli profil):
  ayar            bacak $   yıllık   Sharpe   1 yıl sonra
  30+30, 5 dilim    12.7$   +47.9%    2.16       2.958$
  20+20, 5 dilim    19.0$   +34.9%    1.56       2.698$
  15+15, 5 dilim    25.3$   +27.5%    1.21       2.550$
  10+10, 3 dilim    63.3$   +22.9%    0.98       2.457$

Bacak azaltmak PAHALI (Sharpe 2.16 -> 0.98) ama eksik kurulmuş
portföyden iyidir. Otomatik seçim, bacak başına en az
MIN_BACAK_USD kalacak en YÜKSEK bacak sayısını bulur."""

MIN_BACAK_USD = float(os.getenv("CARRY_MIN_BACAK_USD", "15"))
"""Bacak başına hedeflenen en az tutar (USDT).

Binance minimumu 5 USDT ama 15 seçildi çünkü:
  - ölçek ilk 20 tur 1.0'dır, sonra büyür; 15$ tampon bırakır
  - bazı sembollerde miktar hassasiyeti yüzünden gerçek minimum
    daha yüksektir (BTC ~100$, SOL ~150$)
  - minimuma çok yakın bacaklar yuvarlama sonrası altına düşebilir"""

BACAK_TAVAN = int(os.getenv("CARRY_BACAK_TAVAN", "4"))
"""MADDE 341 — bacak sayısının ÜST tavanı; bakiye büyüse de aşılmaz.

NEDEN VAR: `uygun_bacak_sayisi()` bakiyeyle bacak sayısını büyütüyordu.
Bu İKİ kanalı birden oynatır (madde 326'nın yasası): bacak sayısı artar
VE bacak büyüklüğü küçülür, yani ELENEN EVREN büyür. Kanallar ayrı
ölçüldü (doğrulanmış zemin, iki hizalama sınıfı, ön kayıtlı kural):

  kanal A — bacak 4 SABİT, evren D8 -> D2 (bacak 20,00 $)
      hiza 0: şart1 +0,100/+0,090 · şart2 −1,70 · eşit risk **+21,3**
      hiza 1: şart1 +0,100/+0,140 · şart2 −2,90 · eşit risk **+38,1**
      DÖRT ŞART DA GEÇTİ, kaldıraç gerekmiyor (aday kaldıraçsız üstün)
  kanal B — evren D8 SABİT, bacak 4 -> 5
      şart 1 DÜŞTÜ (25-26 Sharpe −0,050), eşit risk için **1,36x** ister

Ve 5 bacak her evren basamağını ~%25 daha fazla sermayeye iter:
      evren   4 bacak tavanı   5 bacak (eski kural)
      D7         2.576 $          3.219 $
      D2         3.000 $          3.750 $   <- kazancın ~%95'i bu basamakta
      D1         3.564 $          4.455 $
2.812 $'da eski kural 5'e çıkıyor, bacak 15,00 $'a düşüyor ve evren
D8'de KALIYOR — yani D2 basamağı hiç gelmiyor.

ÖLÇÜLEN BASAMAKLAR (4 bacak, hiza 0 / eşit-risk puanı):
      D7 @2.576 $  +2,7   · D2 @3.000 $  +21,3 · D1 @3.564 $  +0,0
AAVE'nin katkısı +0,9 puan, QNT'nin katkısı SIFIR (madde 296 da öyle
yazmış); kazanç beş majorün (ETH·LINK·LTC·BCH·ETC) 20,00 $ eşiğinde
dönmesinden geliyor.

2.000 $'da DAVRANIŞ DEĞİŞMEZ (zaten 4 bacak). Tavan sermaye gelince
işler. Eski davranışa dönmek için: CARRY_BACAK_TAVAN=5.
"""

MIN_LEGS = int(os.getenv("CARRY_MIN_LEGS", "4"))
"""Bacak sayısı bu değerin altına düşerse tur atlanır.

Sembol sayısı N_LEGS*2'ye yetmediğinde bot bacak sayısını KÜÇÜLTEREK
devam eder (tamamen durmak yerine). Ama çok az bacak = yoğunlaşmış
portföy = yüksek risk; 8+8'in altında işlem yapmaya değmez.

MADDE 177: N_LEGS 6 olduğu için bu eşik de 8 -> 4 yapıldı;
aksi halde her tur atlanırdı.

Ölçüldü (madde 114): 15+15 Sharpe 1.18, 30+30 Sharpe 1.47. Az bacak
belirgin şekilde daha oynak - bu yüzden küçülme bir ÇARE değil,
geçici bir tedbirdir; log'da uyarı verilir."""

LIMIT_EMIR = os.getenv("CARRY_LIMIT_EMIR", "1") not in ("0", "false", "False")
"""Emirler LIMIT (maker) olarak mı gönderilsin? Varsayılan: EVET.

Market emir TAKER'dır (%0.04). Limit emir defterin kendi tarafına
konursa MAKER'dır (%0.02) - komisyon yarıya iner. Ölçüldü (madde 121):

  senaryo                            yıllık   Sharpe
  taker + yüksek kayma (kötümser)    +22.6%    1.61
  taker %0.04 + kayma %0.02          +30.4%    2.07
  taker + BNB indirimi %10           +32.4%    2.19
  maker %0.02 + kayma %0.01          +34.4%    2.30
  maker + VIP1                       +35.8%    2.38
  maliyetsiz (üst sınır)             +38.6%    2.53

Maker'a geçmek yılda ~4 puan kazandırıyor - hiçbir risk almadan.

NEDEN BU STRATEJİDE GÜVENLİ: carry sinyali YAVAŞ. Emri 24 saat geç
göndermek bile sonucu +30.4%'ten ~+20%'ye düşürüyor, sıfırlamıyor
(madde 113). Yani limit emir dolmazsa acele etmeye gerek yok -
bir sonraki turda tekrar denenir. Hızlı stratejilerde bu geçerli
DEĞİLDİR.

Dolmayan emirler tur başında iptal edilir (bayat emir kalmasın).

AYRICA BEDAVA: hesapta BNB tutmak komisyonu %10 indirir (+2 puan).
Bu bir kod ayarı değil - Binance hesabından 'BNB ile komisyon öde'
seçeneğini açmanız yeterli."""

ISLEM_TOLERANSI = float(os.getenv("CARRY_TOLERANS", "0.50"))
"""Hedeften bu ORANDAN az sapan pozisyonlara dokunulmaz (bacak büyüklüğüne
göre). Gereksiz işlem maliyetini önler.

Ölçüldü (madde 124, dengeli profil):

  tolerans   yıllık   Sharpe   düşüş    işlem sayısı
  %0        +45.1%    2.09    -15.1%      15.802
  %10       +45.4%    2.10    -15.2%      11.949
  %20       +44.9%    2.07    -15.8%      11.193
  %30       +44.2%    2.04    -16.4%      10.877
  %50       +47.9%    2.16    -14.7%      10.667   <- seçilen
  %70       +46.5%    2.11    -15.4%      10.145

GETİRİ farkı GÜRÜLTÜ seviyesinde (monoton değil - %30'da düşüp
%50'de yükseliyor). Seçim getiriye göre değil OPERASYONEL fayda
için yapıldı: %32 daha az işlem demek daha az API çağrısı, daha az
kayma riski ve limit emirlere dolmak için daha çok zaman demek.

PARİTE NOTU: bot bu toleransı en baştan beri kullanıyordu (%25) ama
BACKTEST kullanmıyordu (tolerans=0). Yani backtest, botun gerçek
davranışını tam yansıtmıyordu. Ölçüldü: fark getiri açısından
ihmal edilebilir (+45.1% vs +45.4%) - yani eski sonuçlar geçerli.
Bu, projedeki 7. backtest/canlı parite kontrolüdür."""

GTX_DENEME_CARPANLARI = (1.0, 2.0, 4.0)
"""Madde 160: GTX emri reddedilirse limit fiyat bu çarpanlarla UZAKLAŞTIRILIP
yeniden denenir. Reddin en sık sebebi, fiyatın emir gönderilene kadar
kayıp limitin karşı tarafa geçmesidir."""

PIYASA_YEDEK = os.getenv("CARRY_PIYASA_YEDEK", "1") not in ("0", "false", "False")
"""Limit emir hiç geçmezse PİYASA emriyle açılsın mı? Varsayılan EVET.
Piyasa emrinin ek maliyeti ~4bp; açılmayan bacağın maliyeti yıllık ~3 puan
(madde 160), yani yaklaşık 75 kat daha pahalı.

MADDE 213 - DOLUM KOVALAMADA PİYASAYA DÜŞMEK YENİDEN ÖLÇÜLDÜ. Şüphe
şuydu: dolmayan emirler RASTGELE değil (fiyat pasif limitten kaçtığı için
dolmuyor - ters seçilim), yani genel gecikme ortalamasıyla karar
verilemez. 54.120 bacak-girişi üzerinde koşullu ölçüm:

  4 saatte dolmayan bacak oranı            %2,4  (madde 145 ile uyumlu)
  dolmayanlarda giriş fiyatı referanstan   %+2,55 KÖTÜ (ters seçilim büyük)
  piyasa - bekle farkı                     %-0,049 (piyasa hafif iyi)
  ama medyan                               %+0,080 (bekleme iyi)
  beklemenin daha iyi olduğu oran          %93,8

Yani beklemek VAKALARIN %94'ünde kazanıyor ama ORTALAMADA kaybediyor:
kuyruk, fiyatın kaçmaya devam ettiği nadir vakalar. Yıllık etki
%+0,37 (piyasa lehine) ama **t = -0,96, %95 aralık [-0,38, +1,11]** -
sıfırdan ayırt EDİLEMİYOR. Bootstrap aralığı da sıfırı içeriyor.

KARAR: DEĞİŞİKLİK YOK. Ne bir sızıntı bulundu ne bir kazanç; ölçüm
mevcut davranışı çürütmüyor. (4 saatlik bar çözünürlüğü, botun gerçek 6
dakikalık eşiğinden DAHA SERT bir ters seçilim ölçüyor - yani bu sonuç
gerçekte daha da nötr.)"""

DOLUM_BEKLEME_SN = float(os.getenv("CARRY_DOLUM_BEKLEME", "180"))
"""GTX emri konduktan sonra dolup dolmadığı kaç saniye sonra kontrol
edilsin (madde 193). 0 = kontrol yok (eski davranış).

NEDEN: GTX emri REDDEDİLİRSE saniyeler içinde piyasa emrine düşülüyor
(madde 160). Ama emir KABUL EDİLİP DOLMAZSA, bacak bir sonraki tura
(8 saate) kadar eksik kalıyordu. Madde 193'te giriş gecikmesinin
maliyeti ölçüldü:

  giriş gecikmesi   yıllık   Sharpe
  4 saat (ideal)   +96.8%    2.840
  8 saat           +94.7%    2.808
  12 saat          +91.6%    2.753
  24 saat          +82.8%    2.595

**Her 4 saatlik gecikme ~2 puan.** Buna karşılık maker/taker farkının
TÜM bütçesi 2.3 puan (madde 172). Yani bir maker dolumu için 4-5
saatten fazla beklemek, maker indiriminin tamamından daha pahalı.

Sonuç: dolum sabırla değil AGRESİF kovalanmalı. 3 dakika, emrin
dolması için bolca zaman; dolmadıysa fiyat kaçmış demektir."""

DOLUM_DENEME = int(os.getenv("CARRY_DOLUM_DENEME", "2"))
"""Dolmayan emir kaç kez daha denenir. Her denemede limit ofseti
GTX_DENEME_CARPANLARI ile açılır; son denemede PIYASA_YEDEK açıksa
piyasa emrine düşülür."""

LIMIT_OFSET = float(os.getenv("CARRY_LIMIT_OFSET", "0.0005"))
"""Limit fiyat, piyasadan bu kadar UZAĞA konur (0.0005 = %0.05).
Alışta aşağı, satışta yukarı. Maker olma olasılığını artırır ama
çok uzak olursa emir hiç dolmaz."""

# ------------------------------------------------- MADDE 213: İCRA BÜTÇESİ
DEVIR_YILLIK = 312.6
"""Yıllık DEVİR HIZI: |Δpozisyon| toplamı / sermaye. Ölçüldü (madde 213,
4,12 yıl, seçilen kitabın gerçek dilim döngüsü). 15 dilim x 8 saatlik tur
bu kadar işlem üretiyor; aylık devir sermayenin ~26 katı."""

PUAN_BASINA_BP = 1.65
"""Komisyondaki 1 BAZ PUAN, yıllık kaç PUAN getiriye mal oluyor.
Ölçüldü (madde 213): 2bp +%94,7 · 3bp +%93,0 · 4bp +%91,4 · 5bp +%89,7;
Sharpe baz puan başına -0,037.

İCRA EKSENİNİN ÜST SINIRI: komisyon SIFIR olsaydı +%98,0 (Sharpe 3,04).
Yani 2bp'de toplam komisyon yükü **3,3 puan**. İcrada yapılabilecek HER
iyileştirmenin toplamı bununla sınırlı - ve harmanlanmış gerçek oran
2,072bp olduğu için tabandan sadece **0,12 puan** uzaktayız (madde 213).
Bu eksende aranacak para YOK.

Pratik tek kaldıraç: komisyonu BNB ile ödemek (%10 indirim, 2,0 -> 1,8bp)
= ~+0,33 puan/yıl. VIP kademeleri erişilemez: aylık 26x devirle VIP1'in
15M$ eşiği ~577.000$ özsermaye gerektiriyor. (Borsa ücret tablosu
değişir - güncel oranları Binance'in ücret sayfasından doğrulayın.)"""

REZERV_PAY = float(os.getenv("CARRY_REZERV", "0.10"))
"""MADDE 442: VARSAYILAN 0.10 (T60 kitabı; madde 429-438). Taban pay
0,40 -> 0,45 (bacak = bakiye / 166,7). Eski kitap 0.20 ile ölçülmüştü.

Madde 156: sermayenin bu kadarı normalde BOŞ bekler ve sadece funding
UÇ seviyeye gelince devreye girer. 0 = kapalı (eski davranış).

Uç fırsat = günlük funding <= -%1.5 (yıllık -%547) olan LONG aday.
Rezerv o adaylara eklenir, eşiti short bacaklara dağıtılır (dolar
nötrlüğü korunur). Uç aday yoksa brüt pozisyon 1.0 yerine 0.8 kalır.

Backtest (12+12, kalabalık seçimi, maker): +53.8% Sh 2.10 düşüş -18.4%
-> +55.9% Sh 2.24 düşüş -14.7%. İki dönemde de iyileşme; rastgele bacağa
verilen rezerv Sh 2.05'te kalıyor (yani sinyalden geliyor).

MADDE 225 — YENİDEN AÇILDI. 0,20 KALDI, AMA SEBEBİ KURAL DEĞİL.
Yukarıdaki ölçüm 12+12 ile yapılmıştı - kalan en bayat tarama. Güncel
yapılandırmayla (5+5, havuz 3,0, 48sa pencere), iki faz ortalaması:

  rezerv   yıllık   Sharpe   düşüş   22-24   25-26   eşit-risk  gereken kaldıraç
  0 (kapalı) +127.9  3.007  −17.5   2.900   3.168    +103.3%     0.85x
  0.10      +125.0   3.084  −16.2   2.929   3.311    +107.8%     0.90x
  0.20     *+112.6* *3.128* −14.6  *2.984* *3.342*   +112.6%     1.00x  <- kalan
  0.30      +96.6    3.139  −13.0   2.988   3.363    +113.5%     1.13x
  0.40      +81.3    3.152  −11.3   2.998   3.382    +114.6%     1.30x

Sharpe 0,20-0,40 arasında PRATİKTE SABİT (3.128 / 3.139 / 3.152) ama
getiri ve düşüş birlikte küçülüyor. Bu bir KENAR değil, bir NAKİT
KADRANI imzasıdır: rezerv büyüdükçe kitabın gücü değil ÖLÇEĞİ düşüyor.

**0,30 ve 0,40 eski ÜÇ ŞARTIN ÜÇÜNÜ DE GEÇTİ** - projede ilk kez bir
yeniden açma adayı kuralı geçti. Bootstrap da destekledi: Δeşit-risk
+1,1 / +2,4 puan, P(>0) %83,6 / %83,0 (ΔSharpe ise yazı-tura: %52 /
%56). Yani gürültü DEĞİL.

REDDEDİLDİ - ve gerekçe kuralın kendisinde yoktu, bu yüzden kurala
DÖRDÜNCÜ ŞART eklendi (`karar_kurali.py`): **eşit riskteki üstünlük
kaldıraç gerektirmemeli.** 0,30'un üstünlüğünü toplamak için brüt
pozisyonu 1,13x'e, 0,40'ınkini 1,30x'e çıkarmak gerekiyor. Kitap şu an
KALDIRAÇSIZ (brüt 1,0). Motor likidasyonu hiç modellemez, yani kıyas
modellenen bir getiriyi modellenmeyen bir tehlikeye karşı fiyatlıyor.
Bu bir parametre iyileştirmesi değil, madde 149'un tablosuna karşı ayrı
verilecek bir KALDIRAÇ kararıdır.

Büyüklük de kararı destekliyor: 1 yıllık pencere bootstrap'ında (eşit
riske getirilmiş, gerçek kaldıraçlı seriler) ortalama getiri +%118,0 →
+%119,2 / +%119,4; getiri p5 +%41,1 → +%42,8 / +%41,7; düşüş p1 −%21,4
→ −%19,4 / −%20,8. Yani ~%1 göreli kazanç için kitaba marj sokulacaktı.

**BUNUN YERİNE KULLANILABİLİR BİR BULGU:** daha DÜŞÜK riskli bir kitap
isteniyorsa, rezervi büyütmek brüt pozisyonu kısmaktan biraz daha iyi -
ve kaldıraç gerektirmiyor:

  hedef düşüş   rezerv büyüt      brüt kıs          fark
  −%12,9        rezerv 0,30 → +%96,5   brüt 0,886 → +%95,6   +0,9 puan
  −%11,3        rezerv 0,40 → +%81,3   brüt 0,770 → +%79,8   +1,5 puan

Üçünde de Sharpe aynı (2,942). Yani `CARRY_REZERV`, `CARRY_GROSS`u
kısmaya kıyasla biraz daha verimli bir RİSK AZALTMA kadranıdır."""

REZERV_ESIK_YILLIK = float(os.getenv("CARRY_REZERV_ESIK", "5.475"))
"""Rezervi tetikleyen YILLIK funding eşiği (5.475 = -%547/yıl = günlük -%1.5).
Eşik taraması: günlük %1.2-%1.8 arası kuralı geçiyor, %1.0 ve %2.5 geçmiyor.

MADDE 240 — YENİDEN AÇILDI, %1,5 KALDI; VE BU BİR KÂR DIAL'İ DEĞİL.
Bu parametre, madde 240'ın **yeniden açma defteri**
(`arastirma_yeniden_acma_defteri.py`) tarafından bulundu: docstring'inde
hiçbir madde atfı yoktu, yani 240 tur boyunca bir kez taranıp hiç
yeniden açılmamıştı — ve sermaye dağıtımını belirliyor. Güncel
yapılandırma, iki faz ortalaması:

  günlük eşik   yıllık   Sharpe   22-24   25-26   düşüş   eşit-risk  kald.
  %1,0         +%115,3   2,915   2,762   3,129  −15,03    +%110,0   0,97x
  %1,2         +%114,3   2,932   2,780   3,144  −14,82    +%111,2   0,98x
  **%1,5**     +%112,5   2,942   2,794   3,147  −14,54    +%112,5   1,00x
  %1,8         +%111,3   2,966   2,823   3,165  −14,40    +%112,8   1,01x
  %2,0         +%110,2   2,977   2,831   3,180  −14,30    +%112,8   1,02x
  %2,2         +%109,1  *2,979*  2,836   3,177  −14,20    +%112,8   1,02x
  %2,5         +%105,5   2,955   2,823   3,139  −13,96    +%111,7   1,04x
  %3,0         +%103,8   2,968   2,835   3,153  −13,73    +%112,4   1,06x

**Eksen eşit riskte DÜZ**: %1,0'dan %3,0'a kadar +%110,0 ile +%112,8
arasında. Getiri tek yönlü DÜŞÜYOR, düşüş tek yönlü SIĞLAŞIYOR. Yani
eşik bir kâr dial'i değil, bir **pürüzsüzlük dial'i**.

%1,8-%2,2 iki dönemde de Sharpe'ı yükseltiyor (tepe %2,2) ve düşüşü
sığlaştırıyor — ama eşit riskte kazanç **+0,3 puan** ve 1,02x kaldıraç
istiyor, bu yüzden şart 4 reddediyor (madde 225/227). **Ölçülmüş bir
seçenek olarak duruyor:** daha pürüzsüz bir biniş isteyen %2,0'a
çekebilir, bedeli ~2,3 puan getiri."""

REZERV_COIN_KAP = float(os.getenv("CARRY_REZERV_KAP", "0.05"))
"""Bir coine EK olarak verilebilecek en yüksek pay. Sınırsız bırakılırsa
tek coin kitabın %15'ine çıkıyor (delist riski en yüksek coinler!).
%5 sınırla en yüksek tek coin ~%9, düşüş -17.6% -> -14.7%.

MADDE 240 — YENİDEN AÇILDI, %5 KALDI; KAPI BİR **DOZ** DIAL'İDİR.
Bu da defterin bulgusu (docstring'inde madde atfı yoktu). İki faz:

  kapı   yıllık   Sharpe   22-24   25-26   düşüş   eşit-risk  kald.
  %3    +%105,3   2,925   2,781   3,124  −14,21    +%108,6   1,02x
  **%5** +%112,5  2,942   2,794   3,147  −14,54    +%112,5   1,00x
  %8    +%118,0   2,932   2,764   3,166  −15,02    +%112,7   0,97x
  %15   +%121,8   2,922   2,743   3,171  −15,34    +%112,8   0,95x

Kapı açıldıkça ham getiri artıyor (+105,3 → +121,8) **ama düşüş aynı
oranda derinleşiyor** (−14,21 → −15,34); eşit-risk %5'in üzerinde
+112,7/+112,8'de sabit kalıyor ve 22-24 Sharpe'ı monoton kötüleşiyor
(2,794 → 2,743). Yani kapıyı açmak alfa satın almıyor, **doz** satın
alıyor — madde 225/229'un yasası (yoğunlaşma = doz) bir kez daha. %3
ise açıkça kötü: eşit riskte −3,9 puan."""

KALABALIK_HAVUZ = float(os.getenv("CARRY_KALABALIK_HAVUZ", "4.0"))
"""Madde 148: her tarafta skora göre HAVUZ x n aday alınır, içlerinden
KALABALIK olanlar seçilir - long tarafta en çok SHORT hesabı olanlar,
short tarafta en çok LONG hesabı olanlar (Binance globalLongShortAccountRatio).
Backtest 12+12: Sharpe 1.83 -> 2.10, düşüş -31.1% -> -18.4%; iki dönemde
de iyileşme; ters yön Sharpe 0.92; 12 rastgele seçimin hiçbiri geçemedi.
<= 1 verilirse kapalı (eski seçim: en uç n).

DEĞİŞTİ: 2.0 -> 3.0 (MADDE 179). Yukarıdaki ölçüm 12+12 ile yapılmıştı.
6+6 ve kâr al %40 ile, altı saat fazının ortalamasıyla yeniden ölçüldü:

  havuz   yıllık   Sharpe   maks düşüş   22-24 Sh   25-26 Sh
  kapalı  +76.3%    2.10      -25.5%
   1.5    +82.9%    2.41      -20.7%
   2.0    +88.3%    2.66      -21.2%      2.54       2.88   (eski)
   3.0    +91.8%   *2.76*     -16.9%      2.65       2.98   <- seçilen
   4.0    +91.6%    2.71      -15.5%   (tek faz)

3.0 her ölçütte 2.0'ı geçiyor: getiri +3.5 puan, Sharpe +0.10, düşüş
**4.3 puan DAHA SIĞ**, iki dönemde de iyi. Altı fazın düşüş aralığı da
tamamen daha iyi (-19.5..-14.9 vs -23.3..-17.7).

DİKKAT: tek faz taramasında 3.0'ın 25-26 Sharpe'ı 2.86 ile 2.0'ın
2.92'sinin ALTINDA görünüyordu; faz ortalaması alınınca 2.98 vs 2.88
oldu. Madde 175'in dersi: tek fazla karar verilmiyor.

Mekanizma: havuz genişledikçe "uç funding" şartını korurken kalabalık
boyutunda daha çok seçenek çıkıyor - yani aynı kirayı daha az sıkışmış
coinden toplamak mümkün oluyor.

MADDE 224 — YENİDEN AÇILDI, 3,0 YİNE ÇIKTI. Yukarıdaki ölçüm 6+6 bacak
ve eski yüzeyle yapılmıştı; aradan 184/189/196/209/222 geçti. Güncel
yapılandırmayla (5+5, 15 dilim, 48sa pencere, TPL 0,40 / TPS 0,20,
UCELE 0,40), iki faz ortalaması:

  havuz   yıllık   Sharpe   düşüş   22-24    25-26   eşit-risk   faz yayılımı
  kapalı  +74.8%   2.148   −22.0    2.441    1.930    +47.2%      6.3 puan
   1.5    +98.7%   2.751   −18.3    2.640    2.944    +75.5%      1.2 puan
   2.0   +105.4%   2.959   −18.5    2.796    3.199    +80.8%      0.9 puan
   3.0   +112.6%   3.128   −14.6    2.984    3.342   +112.6%    0.1 puan  (madde 224'te seçilen)
   4.0   +111.6%   3.115   −14.2    2.985    3.309   +115.8%      3.2 puan
   5.0   +108.5%   3.059   −16.0    2.912    3.276   +111.4%      2.1 puan

Dördü de ön kayıtlı kuralda RED. 4,0 pratikte BERABERLİK (Sharpe farkı
−0,013; 22-24 +0,002, 25-26 −0,033) ve eşit riskte +3,2 puan DAHA
getiriyor - yani madde 223'ün tarif ettiği tuzağın aynısı. Eşli blok
bootstrap kararı verdi: Δeşit-risk ortalaması **−0,4 puan, P(>0) %50,9**
- tam yazı-tura. Δ Sharpe P(>0) %29,9. 4,0 daha iyi değil, AYIRT
EDİLEMEZ; madde 223'ün kuralı gereği şart 3 tek başına kabul ettirmez.

2,0 (madde 179 öncesi değer) artık AÇIKÇA kötü: Δ Sharpe P(>0) %9,9,
eşit riskte −21,3 puan. Madde 179'un kararı doğrulandı ve güçlendi.

**ASIL BULGU - DEĞER KAYAR, ARGMAX KAYMAZ:** madde 179'da kalabalık
seçiminin değeri (kapalı → 3,0) +15,5 puan ve +0,66 Sharpe'dı; şimdi
**+37,8 puan ve +0,98 Sharpe**. Yani yüzeyin YÜKSEKLİĞİ neredeyse iki
katına çıktı ama TEPE NOKTASI hiç oynamadı. Bayat bir tarama iki farklı
şekilde bayat olabilir ve ayarı yalnızca ikincisi ilgilendirir.

**YANLIŞ ÇIKAN TAHMİN (kayda geçirildi):** tarama öncesi "madde 196
(UCELE) adayları eliyor, geniş havuzda eleme daha az ısırır, o yüzden
optimum YUKARI kaymıştır" diye tahmin ettim. Yanlış çıktı. Mekanizmanın
var olup olmadığı ayrıca ölçüldü - UCELE kapatılıp havuz 3 vs 4 sırası
yeniden bakıldı:

  UCELE=0,40:  havuz 3 +112.6% / 3.128   havuz 4 +111.6% / 3.115  (fark +1,0)
  UCELE=0   :  havuz 3 +116.2% / 3.017   havuz 4 +115.5% / 3.012  (fark +0,7)

Sıra değişmiyor, fark da değişmiyor: **adlandırdığım etkileşim yok.**
Tahmin de yanlıştı, gerekçesi de. (Yan gözlem: UCELE getiriyi 3,6 puan
DÜŞÜRÜP Sharpe'ı 0,11 yükseltiyor - madde 196 bir getiri değil risk
takasıydı; bu maddede yeniden açılmadı.)

DEĞİŞTİ: 3.0 -> 4.0 (MADDE 350/352). Madde 224'ün taraması 5+5 bacakta
yapılmıştı; madde 341'den beri bot 2.000-20.000 $ aralığında 15x4 koşuyor
ve havuz = HAVUZ x bacak olduğu için 4 bacakta 3,0 yalnız 12 aday demek
(5 bacakta 15'ti). 15x4'te, iki hizalamada, kontrole göre FARK
(yıllık puan / Sharpe / düşüş puanı / eşit-risk; P = eşli bootstrap):

  havuz  bakiye  hz   yıllık    22-24   25-26   düşüş   eşit-risk  P
   3.0    (kontrol)
   4.0  *2.000*   0   *+7,4*  +0,17   +0,02   −2,3    +33,5   *%92,6*
          2.000   1    +8,8   +0,22   +0,02   −4,3    +65,0    %94,3
          3.500   0    +5,7   +0,11   +0,04   −2,2    +34,4    %83,3
          3.500   1    +1,3   +0,05   −0,05   −2,3    +29,6    %58,7
   5.0    2.000   0/1  +3,0/+5,2  P %79,9/%89,2 (h0 şart 1: 25-26 −0,03)
          3.500   0/1  +5,5/+3,9  P %78,9/%75,2
   6.0    2.000   0/1  +0,7/+4,4  P %62,9/%82,1
          3.500   0/1  +2,0/+1,1  P %47,6/%53,3

Ön kayıtlı kural (arastirma_m352_havuz_plato.py): 2.000 $'da iki hizada
da geçen değerlerin bandı ve seçilen değerin 3.500 $'da en az bir hizada
geçip hiçbir hizada eşit riskte negatif olmaması. Band yalnız {4} (5,0
h0'da %79,9 ile kıl payı dışarıda) -> öneri kuralın kendi etiketiyle
ZAYIF. Kaldıraç başlığı DEĞİL: 4,0 kaldıraçsız hâliyle hem daha çok
kazanıyor hem daha sığ düşüyor. Yüzey 4-5'te plato, 6'da sönüyor.
Madde 224'te 4,0 beraberlikti (5 bacak, havuz 20); burada ayrışıyor —
madde 222'nin yasası: kitap değişince taranmış optimum kayar.
Geri almak için: CARRY_KALABALIK_HAVUZ=3."""

AKIS_AGIRLIK = float(os.getenv("CARRY_AKIS_AGIRLIK", "0.20"))
"""Sıralamanın ne kadarı EMİR AKIŞI sinyalinden gelsin (0 = sadece funding).

Emir akışı = agresif alıcı baskısı x hacim artışı. Tek başına işe
YARAMIYOR (+2.3% / -0.4%, Sharpe 0.25 / 0.01) ama funding ile
karıştırıldığında ikisi de iyileşiyor - gerçek çeşitlendirme.

Ölçüldü (madde 117), İKİ AYRI PANELDE doğrulandı:

  karışım      panel A (91c, 2022+)      panel B (137c, 2023-06+)
  %100 funding +10.1%  Sharpe 0.86       +16.9%  Sharpe 1.47
  %85/%15      +16.0%  Sharpe 1.29       +20.1%  Sharpe 1.68
  %80/%20      <- seçilen (iki panelin optimumlarının ortası)
  %75/%25      +16.2%  Sharpe 1.30       +19.5%  Sharpe 1.62
  %60/%40      +14.5%  Sharpe 1.19       +17.7%  Sharpe 1.50
  %100 akış     +2.3%  Sharpe 0.25        -0.4%  Sharpe 0.01

İki panelde de aynı yön - risk paritesinin (madde 116) aksine
TUTARLI. Tek panelde doğrulanan bir fikre güvenmeyin.

MADDE 228 — YENİDEN AÇILDI. %20 KALDI, AMA ARTIK YÜK TAŞIMIYOR.
Yukarıdaki tablo Sharpe 0,86-1,68'lik panellerden ve madde 148'in
KALABALIK SEÇİMİNDEN ÖNCE ölçülmüştü. Güncel yapılandırma, iki faz:

  akış payı   yıllık   Sharpe   düşüş   22-24   25-26   eşit-risk
    %0       +109.7   3.088   −14.6   2.981   3.257    +109.5%
    %10      +110.3   3.091   −14.6   2.956   3.293    +110.8%
   *%20*    *+112.6* *3.128*  −14.6  *2.984* *3.342*   +112.6%  <- kalan
    %30      +105.8   3.004   −16.0   2.852   3.225    +108.2%
    %40      +100.6   2.932   −19.6   2.619   3.349     +78.6%

Optimum yerinde. Ama KATKISI çökmüş - ve sebebi ölçüldü:

  kalabalık seçimi KAPALI (HAVUZ=1): akış %0 → %20
      +%59,2 / Sharpe 1,74  →  +%74,8 / Sharpe 2,135   (+15,6 puan, +0,40)
  kalabalık seçimi AÇIK  (HAVUZ=3): akış %0 → %20
     +%109,7 / Sharpe 3,088 → +%112,6 / Sharpe 3,128   ( +2,9 puan, +0,04)

Emir akışının değeri **%90 buharlaşıyor**. İkisi de KONUMLANMA
sinyali: kalabalık seçimi (madde 148, bu tablodan SONRA geldi) akışın
taşıdığı bilginin neredeyse tamamını zaten topluyor. Eşli blok
bootstrap: akışı tamamen kapatmak eşit riskte **−0,1 puan, P(>0)
%41,4** - yani getiri tarafında SIFIRDAN AYIRT EDİLEMEZ (Sharpe
tarafında zayıf biçimde aleyhte: P(ΔSh>0) %20,5).

**PRATİK SONUÇ:** %20 korunuyor (argmax orası ve hesaplaması bedava),
ama bu bileşen artık YÜK TAŞIMIYOR. Emir akışı verisi canlıda
bozulursa, kapatmanın bedeli ~2,9 puan ± gürültüdür; yukarıdaki eski
tablonun düşündürdüğü gibi kitabın yarısı değil. Kararı o rakama göre
verin."""

AKIS_KISA_BAR = 30    # 5 gün  - güncel akış
AKIS_UZUN_BAR = 180   # 30 gün - kıyas tabanı

RISK_PROFILI = os.getenv("CARRY_RISK", "kaldiracsiz").strip().lower()
"""Hazır risk profili = oynaklık hedefi = otomatik kaldıraç.

DEĞİŞTİ (madde 140): varsayılan "dengeli" -> "kaldiracsiz".

Eski tablo (madde 122) 183 sembollük hayatta-kalan panelden geliyordu;
orada stratejinin oynaklığı ~%10 olduğu için "dengeli %40" ılımlı bir
kaldıraçtı (düşüş -%15). Temiz panelde stratejinin kendi oynaklığı
~%24; aynı %40 hedefi ~2x kaldıraç ve -%54 düşüş demek. Ayrıca oynaklık
hesabında iki hata vardı (bkz. _vol_olcek_hesapla).

Temiz panel, 5 dilim, düzeltilmiş hesap (90 gün pencere, kaldıraçsız
oynaklık ölçümü), 2022-07 -> 2026-08:

  profil         hedef   yıllık  Sharpe  max düşüş  ort. kald.  en kötü ay
  kaldiracsiz      -     +30.3%   1.21     -27.6%     1.00x       -8.4%   <- varsayılan
  guvenli        %20     +26.2%   1.17     -31.8%     1.03x      -10.3%
  dengeli        %40     +51.0%   1.16     -54.2%     2.04x      -19.9%
  agresif        %60     +72.2%   1.22     -63.3%     2.58x      -23.9%
  cok_agresif    %80     +84.3%   1.24     -63.3%     2.81x      -23.9%

OKUMA:
- Sharpe her satırda ~1.2 - kaldıraç kâr YARATMAZ, getiriyi de düşüşü
  de aynı oranda büyütür. Daha fazla kâr isteyen, daha derin düşüşü
  bilerek kabul eder.
- "guvenli" kaldıraçsızdan KÖTÜ: stratejinin oynaklığı zaten ~%24,
  %20 hedef neredeyse hiç kaldıraç değiştirmiyor, sadece gürültü ekliyor.
- Ayların yaklaşık YARISI zararda kapanıyor (5 dilimde %49); medyan ay
  ~-%0.2, ortalama ay +%2.5. Yıllık kâr birkaç büyük aydan gelir.
- Düşüşler GEÇMİŞ ölçümdür; gelecekte daha derin olabilir. -%63
  düşüşte hesabın üçte ikisi erir; agresif profiller likidasyona
  yaklaşma riski taşır.

Bilinmeyen bir profil adı yazılırsa KALDIRAÇSIZ çalışır (güvenli taraf)."""

_PROFILLER = {"kaldiracsiz": 0.0, "kaldıraçsız": 0.0,
              "guvenli": 0.20, "güvenli": 0.20, "dengeli": 0.40,
              "agresif": 0.60, "cok_agresif": 0.80, "çok_agresif": 0.80}

VOL_HEDEF = float(os.getenv("CARRY_VOL_HEDEF",
                            str(_PROFILLER.get(RISK_PROFILI, 0.0))))
"""Yıllık portföy oynaklığı hedefi. 0 = kapalı (sabit büyüklük).

Portföy son dönemde hedeften SAKİN seyrediyorsa pozisyonlar büyütülür,
OYNAK seyrediyorsa küçültülür. Ölçek [0.3x, 3.0x] ile sınırlı.

Ölçüldü (madde 116, 137 coin, 30+30, faz ortalamalı):

  (5 dilim + %80 funding/%20 akış yapısıyla, madde 120/122)
  hedef    yıllık   Sharpe   max düşüş   brüt
  kapalı   +22.4%    2.07       -8.9%   1.00x
  %20      +30.4%    2.07      -10.9%   1.34x
  %30      +38.7%    2.11      -12.8%   1.64x
  %40      +45.1%    2.09      -15.1%   1.89x   <- varsayılan (dengeli)
  %50      +50.1%    2.06      -17.7%   2.10x
  %60      +54.6%    2.03      -20.0%   2.30x
  %80      +63.5%    2.03      -22.8%   2.61x

  RISK_PROFILI ile de seçilebilir (güvenli/dengeli/agresif/çok_agresif).

DÜRÜST OKUMA: Sharpe her seviyede ~1.50 sabit - bu bir ALFA
iyileştirmesi DEĞİL, otomatik kaldıraç ayarıdır. Sabit kaldıraçtan
farkı, sakin dönemde büyüyüp oynak dönemde küçülmesi. Getiri de
düşüş de aynı oranda büyür.

MADDE 165 - BU ÖZELLİK ZARARLI, AÇMAYIN. Kabul edilen getiri
serisinde AYNI ortalama kaldıraçta sabit kaldıraçla karşılaştırıldı:

  hedef   ort.kald.   vol-hedefi        aynı kald. SABİT      fark
  %20       1.16x    +51.8%  −18.0%    +66.1%  −16.8%     −14.3 puan
  %30       1.71x    +83.2%  −26.0%   +106.7%  −24.1%     −23.4 puan
  %40       2.14x   +118.9%  −33.5%   +142.7%  −29.4%     −23.8 puan
  %60       2.58x   +174.5%  −39.2%   +184.4%  −34.6%      −9.8 puan

Her satırda HEM getiri düşük HEM düşüş derin - yani tam anlamıyla
domine ediliyor. SEBEBİ ölçüldü: ölçek ile SONRAKİ 30 günün getirisi
NEGATİF korelasyonlu (−0.14). Ölçek yüksekken (sakin dönem) sonraki
30 gün ortalama %+2.1; ölçek düşükken (oynak dönem) %+5.6. Carry en
çok stresten HEMEN SONRA öder; sakin dönemde funding zaten incedir.
Yani oynaklık hedefi tam yanlış anda büyütüp tam yanlış anda
küçültüyor. Daha fazla getiri isteniyorsa CARRY_GROSS ile sabit
kaldıraç kullanılmalı."""

N_DILIM = int(os.getenv("CARRY_N_DILIM", "15"))
"""Sermaye kaç alt portföye bölünsün (faz çeşitlendirmesi, madde 120/184).

MADDE 184 — 5'TEN 15'E ÇIKARILDI. Tutma süresi 120 saat sabit; 15
dilim demek her dilimin **8 saatte bir** (funding aralığıyla aynı)
yenilenmesi demek. Ölçüm, 6 başlangıç fazının ortalaması, tam
yapılandırma:

  dilim (aralık)   yıllık   Sharpe   düşüş(ort)  en kötü  faz yayılımı
  3  (40 saat)    +97.3%    2.688     −18.3%     −25.6%     19.8 puan
  5  (24 saat)    +91.5%    2.682     −17.6%     −19.5%     22.6 puan
  6  (20 saat)    +91.9%    2.712     −16.9%     −18.9%     19.4 puan
  10 (12 saat)    +91.7%    2.740     −17.0%     −18.2%     14.4 puan
  15 ( 8 saat)    +91.6%    2.755     −17.0%     −18.1%    **2.5 puan**  <- seçilen

"Faz yayılımı" = botun hangi saatte başlatıldığına bağlı yıllık getiri
farkı. 5 dilimde **22,6 puan** — yani botu sabah mı akşam mı
başlattığınız, bir yılın getirisinden daha çok fark ediyordu. 15
dilimde bu **2,5 puana** iniyor. Kumar ortadan kalkıyor.

Getiri DEĞİŞMİYOR (+%91,5 → +%91,6). Değişen risk: Sharpe 2,682 →
2,755, en kötü düşüş −%19,5 → −%18,1. İki alt dönemde de Sharpe
iyileşiyor (22-24: 2,602 → 2,652; 25-26: 2,873 → 2,970) — ön
kayıtlı kuralı geçiyor.

YÖN TESTİ: 3 dilim (ters yön) Sharpe'ı 2,688'e, en kötü düşüşü
−%25,6'ya götürüyor. Etki gerçek, gürültü değil.

DEVİR HIZI ARTMIYOR: pozisyon yine 5 gün tutuluyor, sadece giriş
anları inceliyor. Ek komisyon YOK. Canlının %50 toleransıyla da
ölçüldü: sonuç aynı (+%91,5 / Sharpe 2,753).

**SERMAYE MALİYETİ (madde 223'te GÜNCELLENDİ - madde 222'den beri
bayattı):** bacak = `bakiye x GROSS x taban_pay / (N_DILIM x N_LEGS)`,
yani şu an `bakiye / 166,7` (madde 442: rezerv 0,20 -> 0,10, taban pay
0,40 -> 0,45; eski kitapta `bakiye / 187,5`, 1.875$). Tam 5+5 bacak
**1.667$** üstünde kurulur.
Bu paragraf madde 222'ye kadar `(15 x 6)` ve "~3.400$" diyordu; bacak
sayısı 6'dan 5'e inince yanlışlaştı ve bir tur boyunca öyle kaldı -
`test_carry_preflight.py` yalnızca `CANLIYA_CIKIS.md` belgesini
denetliyordu, KOD İÇİ docstring'i kimse denetlemiyordu. Madde 223'te
bu sayı da testle koda bağlandı.

  N_DILIM    bacak       tam 5+5 için asgari bakiye (rezerv 0,10)
     5     bakiye/55,6              556$
     6     bakiye/66,7              667$
    10     bakiye/111,1           1.111$
    15     bakiye/166,7           1.667$   <- seçilen

Altındaysa `uygun_bacak_sayisi` bacak sayısını kendiliğinden düşürür.
**1.667$ altındaki hesaplarda `CARRY_N_DILIM` düşürülebilir** - madde
223 ölçtü: dilim sayısı faz ORTALAMASINI hiç oynatmıyor, sadece faz
YAYILIMINI (başlangıç saatinin kumarı) büyütür. Yani bu bir getiri
fedası değil, belirlilik fedasıdır.

ESKİ ÖLÇÜM (madde 120) 10 dilimin "ek fayda vermediğini" söylüyordu;
o ölçüm TEK başlangıç fazında yapılmıştı, yani kazancın geldiği yeri
(faz kumarını) göremiyordu. Dördüncü kez: motor değişince yeniden ölç.

--- madde 120'nin özgün ölçümü (eski motor, tek faz) ---

SORUN: tek bir rebalance zamanlamasıyla çalışmak KUMAR. Ölçüldü -
aynı strateji, sadece hangi gün dengelendiğine göre:
  en kötü faz: +22.4% yıllık, Sharpe 1.43
  en iyi faz : +37.3% yıllık, Sharpe 2.21
Hangisine denk geleceğiniz şans.

ÇÖZÜM: sermayeyi N dilime böl, her dilimi FARKLI gün dengele.
Bot her gün çalışır ama sadece sırası gelen dilimi yeniler.

Ölçüldü (vol hedefi %20 açık):
  tek faz    : +29.8%  Sharpe 1.82  düşüş -13.6%   <- şans faktörü var
  2 dilim    : +33.2%  Sharpe 2.16  düşüş  -8.9%
  3 dilim    : +29.0%  Sharpe 1.97  düşüş -12.7%
  5 dilim    : +30.4%  Sharpe 2.07  düşüş -10.9%   <- seçilen
  10 dilim   : +30.1%  Sharpe 2.07  düşüş -10.6%

5 seçildi: 10'a çıkmak ek fayda vermiyor, 2'nin yüksek Sharpe'ı
ise sadece 2 örnekten geldiği için güvenilmez. Aynı getiri, daha
yüksek Sharpe, daha sığ düşüş - ve faz şansı tamamen ortadan kalkar.

YAN FAYDA: işlemler 5 güne yayılır, tek seferde büyük emir
gönderilmez (piyasa etkisi ve kayma azalır)."""

DILIM_DURUM_DOSYA = os.getenv("CARRY_DILIM_LOG", "carry_dilimler.json")
"""Her dilimin hedef portföyü burada tutulur. Bot yeniden başlasa
bile dilim sırası ve hedefleri kaybolmaz."""

VOL_GECMIS_DOSYA = os.getenv("CARRY_VOL_LOG", "carry_equity.csv")
"""Oynaklık hedefi için bakiye geçmişi. Bot her turda buraya yazar;
yeterli geçmiş birikene kadar ölçek 1.0 kalır (sessizce yanlış
ölçek uygulamaz)."""

VOL_MIN_KAYIT = 20
"""Oynaklık tahmini için gereken en az tur sayısı. Altındaysa ölçek 1.0."""

VOL_PENCERE = 90
"""Oynaklık son kaç örnekten (turdan, ~gün) ölçülsün (madde 140).

Eskiden TÜM geçmiş kullanılıyordu. Stratejinin oynaklığı 2022-24'te
düşük, 2025-26'da çok yüksek; tüm geçmişe bakan tahmin sakin yıllara
takılı kalıp oynak dönemde fazla kaldıraç açıyordu (%40 hedefte
gerçekleşen %60). Pencere GETİRİYE göre değil, gerçekleşen oynaklığın
hedefe yakınlığına göre seçildi:

  pencere      %40 hedefte yıllara göre gerçekleşen     sapma
  tüm geçmiş   43  39  47  60  61                       13.6 puan
  180 gün      43  41  45  46  43                        4.0
  90 gün       42  41  44  46  42                        3.6   <- seçilen
  60 gün       42  41  44  46  43                        3.6
  30 gün       40  42  44  48  45                        4.6"""

SAGLIK_MODU = os.getenv("CARRY_SAGLIK_MODU", "durdur").strip().lower()
"""Edge sağlık dedektörü (madde 139): "durdur" | "uyar" | "kapali".

Carry primi ölürse (funding kalıcılığı kaybolur, prim sıkışır) bunu
FİYAT kaybını beklemeden, doğrudan funding verisinden yakalar. Funding
metrikleri fiyattan ~9 kat daha az gürültülü olduğu için bu çok daha
hızlı ve az yanlış alarmlıdır.

Ölçüldü (eşikler 2022-2024'te sabitlendi, sonra test edildi):
  yanlış alarm, gerçek 2025-26 verisi      : 0 / 120 rebalance
  yanlış alarm, 5 farklı başlangıç tarihi  : 0
  kalıcılık ölümünü yakalama (40 tohum)    : 40/40, medyan 36 gün
  keskin prim sıkışması (x0.1)             : 23-39 gün
  yavaş erime (180 günde sıfıra)           : 138-183 gün

DÜRÜST OKUMA: bu bir SİGORTA, kâr artırıcı değil. Simülasyonlarda
ortalama getiriyi artırmadı (kalıcılık ölümünde fark -1.5 puan,
t=-0.55, anlamsız); kazandırdığı şey düşüş: ort. max düşüş
-27.0% -> -20.6%. Prim sıkışması senaryosunda fiyat tarafından gelen
getiriyi de kaçırdı (+22.9% -> +3.5%).

"durdur": kapı kapanınca tüm pozisyonlar kapatılır, dilimler
          sıfırlanır; 10 gün kesintisiz sağlıklı görünce dilimler
          günde bir yeniden dolar.
"uyar"  : sadece log'a UYARI yazar, işlem akışına dokunmaz.
"kapali": dedektör hiç çalışmaz (API çağrısı da yapılmaz)."""

SAGLIK_DOSYA = os.getenv("CARRY_SAGLIK_LOG", "carry_saglik.json")
"""Sadece kapının durumu (açık/kapalı, ne zamandan beri temiz)
saklanır. Metrikler her turda Binance'ten DURUMSUZ yeniden hesaplanır,
bu yüzden bot ilk günden silahlıdır ve bozuk bir durum dosyası
metrikleri bozamaz."""

KAR_AL_ORAN = float(os.getenv("CARRY_KAR_AL", "0.60"))
"""MADDE 442: VARSAYILAN long 0,60 / short 0,20 (T60 kitabı; madde 435-436:
TPL 0,50 / 0,60 / 0,70 dd'yi bozmadan plato, IS ve OOS'ta aynı yönde).
Eski kitap long 0,40 ile ölçülmüştü; aşağıdaki tarih o kitabındır.

Pozisyon başına KÂR AL seviyesi (madde 143). 0 = kapalı.

Long: giriş x (1 + oran), short: giriş x (1 - oran) seviyesine borsada
bekleyen, yalnızca KAPATAN (reduce-only) limit emir konur. Limit emir
olduğu için fiyat oraya gelince maker olarak dolar.

Ölçüldü (canlı ayar, 5 dilim, bar içi yüksek/düşükle, 2022-07 -> 2026-08):

  seviye    12+12 Sharpe (tam / 22-24 / 25-26)   6+6 Sharpe (tam / 22-24 / 25-26)
  yok         1.42 / 1.08 / 1.81                   1.67 / 1.87 / 1.68
  %30         1.39 / 1.44 / 1.36                   1.70 / 2.10 / 1.34   <- fazla sıkı
  %40         1.65 / 1.41 / 1.96                   1.96 / 2.18 / 1.86
  %50         1.56 / 1.22 / 1.97                   1.90 / 2.04 / 1.89
  %70         1.68 / 1.26 / 2.17                   1.96 / 2.07 / 2.01   <- seçilen
  %100        1.68 / 1.26 / 2.17                   2.01 / 2.12 / 2.07

%40-%100 arası PLATO; ortası seçildi, en iyisi değil. 12+12'de 5 yılın
5'inde, 6+6'da 5'in 4'ünde iyileştiriyor. Mekanizma: 5 günlük tutma
içinde +%70 (long'da squeeze) ya da -%70 (short'ta çöküş) yapan coin
çoğunlukla geri dönüyor; kâr al o dönüşten önce kilitliyor.

MADDE 227 — YENİDEN AÇILDI, HER İKİ TARAF DA OPTİMUMDA ÇIKTI. Yukarıdaki
tablo madde 143'ün yüzeyinden (Sharpe 1,67-2,01; bugün 3,13) ve madde
222'den (bacak 6→5) BERİ hiç yeniden ölçülmemişti. Madde 222'deki deneme
`env` sırası hatasıyla sessizce kontrolü tekrarlamıştı; bu yüzden TP,
madde 222'nin yeniden-açma listesine hiç GİRMEDİ - listenin kendisi
eksikti ve eksik olan, madde 214'e göre kârın TAMAMINI taşıyan
mekanizmaydı. (Madde 290: "tamamı" düzeltildi - hasadın gerçek katkısı
+18,9 CAGR puanı / +0,77 Sharpe / −6,1 düşüş, yani kârın %16,8'i;
ayrıntı `carry_tp.csv`'nin docstring'inde.)

Güncel yapılandırmayla, iki faz ortalaması:

  TPL / TPS   yıllık   Sharpe   düşüş   22-24    25-26   eşit-risk
  0,25 / 0,20  +86.7   2.836   −14.9   2.721    3.006     +83.7%
  0,30 / 0,20  +95.8   2.945   −15.2   2.832    3.114     +90.2%
  0,40 / 0,20 *+112.6* *3.128* −14.6  *2.984*  *3.342*   +112.6%  <- kalan
  0,50 / 0,20 +117.7   3.109   −14.3   2.969    3.320     +121.5%
  0,60 / 0,20 +121.2   3.077   −14.2   2.948    3.277     +126.3%
  0,40 / 0,10 +105.0   2.914   −18.1   2.972    2.868      +78.1%
  0,40 / 0,15 +108.4   3.032   −16.8   2.903    3.225      +88.9%
  0,40 / 0,30 +108.8   3.064   −16.5   3.021    3.159      +98.4%

Her iki taraf da tepe noktasında: LONG 0,40'ta, SHORT 0,20'de.

TEHLİKELİ GÖRÜNEN ADAYLAR: 0,50 ve 0,60, eşit riskte +8,9 / +13,8 puan
DAHA getiriyordu VE düşüşleri kontrolden daha SIĞDI (−14,25 / −14,15 vs
−14,58) - yani kaldıraçsız hâlleriyle "üstün" görünüyorlardı. Eşli blok
bootstrap ikisini de çürüttü:

  aday        Δ eşit-risk (ort)  P(>0)   P(düşüş daha SIĞ)
  0,50 / 0,20      +2,2 puan    %64,1        %35,5
  0,60 / 0,20      −1,1 puan    %50,8        %23,9

Tam örneklemdeki +8,9/+13,8 puan +2,2/−1,1'e çöküyor, ve asıl önemlisi
"daha sığ düşüş" yeniden örneklemelerin yalnızca %35/%24'ünde
tekrarlıyor - yani ÜSTÜNLÜK TEK BİR GERÇEKLEŞMENİN ESERİ. 0,30 ise
gerçekten kötü: P(ΔSharpe>0) = %0,15.

Madde 178'in "eşiği düşür" yönünün bir TABANI var ve tam burada.

MADDE 235 — ÇIKIŞIN ŞEKLİ (seviyesi değil) denendi. Proje bugüne kadar
TP'nin yalnızca SEVİYESİNİ taradı; şekli hep "tek eşik, hep ya hiç"
kaldı. Üç şekil ölçüldü. Önce bütçe (32.250 bacak, tutma süresi içinde
en iyi lehte hareket):

  eşik     LONG değme   SHORT değme
  +%10       %42,9        %50,4
  +%20       %21,4        %20,9
  +%40       %8,3         %10,6*     <- mevcut LONG eşiği
  +%60       %4,1         %0,8
  p99 kuyruk  +%116        +%56
  (*SHORT'un mevcut eşiği +%20; gerçekleşen oranlar madde 216:
   LONG %8,8 / SHORT %18,1 - ölçüm aracı doğrulandı)

  şekil                     yıllık   Sharpe   düşüş   eşit-risk   kaldıraç
  tek eşik (kalan)         +112.6%   3.128   −14.6    +112.6%     1.00x
  YARIM (TP'de yarısı)     +103.8%   2.819   −16.3     +95.3%     0.94x
  takip %20 / geri %10      −31.1%  −1.658   −80.1      −3.6%     0.10x
  takip %30 / geri %15      +16.2%   0.761   −25.5      +9.8%     0.57x
  takip %50 / geri %20      +77.9%   2.456   −15.4     +72.4%     0.94x
  merdiven %20 x1/2        +106.5%  *3.202* −14.2     +118.6%     1.08x
  merdiven %20 x1/3        +108.5%   3.183   −14.3    +116.4%     1.05x
  merdiven %10 x1/3         +98.2%   3.157   −13.0    +116.3%     1.13x

TAKİP EDEN ÇIKIŞ KİTABI YIKIYOR ve sebebi bu docstring'in hemen
altında zaten yazılıydı: **takip eden çıkış, kılık değiştirmiş bir
STOP'tur.** Bu coinler ~%100 oynak, %10'luk bir geri çekilme sürekli
oluyor; ve çıkış, funding tahsil eden pozisyonu tam yanlış anda
kapatıyor. Doz-yanıt tek yönlü: gevşettikçe kontrole yaklaşıyor, yani
**en iyi takip, takip olmamasıdır.**

MERDİVEN GERÇEK AMA RİSK BOYUTUNDA. Eşli blok bootstrap (2.000 örnek):

  aday            ΔSharpe   P(ΔSh>0)    Δeşit-risk    P(>0)
  merdiven %20x1/2  +0,099   **%93,9**     +3,3 puan   %58,5
  merdiven %20x1/3  +0,069     %94,1       +2,7 puan   %62,2
  merdiven %10x1/3  +0,061     %79,0       +3,0 puan   %59,0

**Sharpe'ı %94 güvenle yükseltiyor** (bu arayışın en güçlü istatistiksel
sonucu) VE her iki rejimde de (düşük prim 2,794→2,839; yüksek prim
3,147→3,314, yani madde 231'in rejim endişesi geçerli değil). AMA eşit
riskteki getiri yazı-tura (%58,5). Çelişki değil: merdiven OYNAKLIĞI,
maksimum DÜŞÜŞTEN daha çok azaltıyor. Sharpe oynaklığı kullanır, eşit
risk ise düşüşü eşitler - merdiven kazananları erken kırpıyor, kötü
kuyruğa dokunmuyor.

**KABUL EDİLMEDİ.** Ön kayıtlı kural iki şarttan düşürüyor: 22-24
Sharpe'ı düz (−0,000..−0,018) ve üstünlük 1,05-1,13x kaldıraç istiyor
(madde 225'in 4. şartı; merdiven kısmen bir nakde çekme aracı). Ve
kullanıcının sorduğu şey KÂR: merdiven ~6 puan getiri FEDA ediyor,
eşit riskte kazancı ise sıfırdan ayırt edilemiyor.

**AMA ÖLÇÜLMÜŞ BİR SEÇENEK OLARAK DURUYOR:** daha pürüzsüz bir binişe
~6 puan getiri ödemeye razıysanız, merdiven %20 x1/2 bunu %94 güvenle
veriyor. Canlı botta uygulanmadı - bacak başına ikinci bir reduce-only
emir gerektirir.

KARŞILAŞTIRMA: aynı testte STOP-LOSS'lar ağır zarar verdi (12+12:
stop %10 -> -%1.7/yıl, %20 -> +%8.5, %30 -> +%18.6, stopsuz +%36).
Bu coinler ~%100 oynak; stop gürültüyle tetikleniyor ve funding
kirası ödenen pozisyonu tam yanlış anda kapatıyor. Stop YOKTUR.

Kâr al dolan coin, eski dilimlerden çıkarılır - yoksa ertesi tur bot
onu hedefte görüp hemen yeniden açardı (backtest'te koltuk o dilimin
bir sonraki rebalance'ına kadar boş kalıyor).

MADDE 229 — O BOŞ KOLTUK BİR KUSUR DEĞİL, BİR ÖZELLİK. Ölçüldü:
brütün **%5,01'i** her an boş duruyor. Eksenin tavanı ~+5,6 puan.
Üç doldurma yolu da denendi (iki faz ortalaması):

  koltuk          konuşlandırma   yıllık   Sharpe   düşüş   eşit-risk
  BOŞ (kalan)         %95,0     +112.6%   3.128   −14.6    +112.6%
  yedekle DOLDUR      %100,8    +101.2%   2.972   −15.3    +104.5%
  AYNI yönde gir      %95,4     +112.1%   2.971   −16.7    +100.3%
  TERS yöne dön       %99,6     +105.1%   2.511   −22.6     +59.1%

Boşluğu doldurmak **11,4 puan yakıyor** - tavanın iki katı. Yani 6.
sıradaki aday 5.'den kötü olmakla kalmıyor, **hiç yoktan da kötü.**
Bootstrap: AYNI P(ΔSharpe>0)=%1,4, TERS %1,6 (kesin red); DOLDUR'un
bandı geniş ama tavanı +5,6 iken nokta tahmini −11,4, yani en iyimser
okumada bile kazanç yok.

**BU BİR YASA VE İKİ BAĞIMSIZ ÖLÇÜMÜ VAR:** madde 225 (rezervdeki %20
boş sermaye, konuşlandırılmışından iyi) ve madde 229 (hasat edilen
koltuk boş, doluymuş halinden 11,4 puan iyi). Bu, madde 177'den beri
yoğunlaşma yönünün (bacak 12→6→5, havuz 2→3, hacim eşiği yukarı) neden
hep işlediğini açıklıyor: hepsi marjinal adayı kitaptan atıyordu.

TERS ayrıca madde 214 hakkında bir şey söylüyor: SHORT bacak "geri
dönüş hasadı" ise de, **TP dolduğunda geri dönüş ZATEN olmuştur** -
ters girmek hareketten sonra girmektir. Sharpe 3,128 → 2,511.

MADDE 238 — KÂR AL, KİTABIN EN BÜYÜK TEK KATMANI. Proje her katmanı tam
yapılandırmadan TEK TEK ÇIKARARAK ölçmüştü; hiç kimse ÇIPLAK seçiciden
başlayıp katmanları EKLEMEMİŞTİ. Eşit-risk sütunu her şeyi tam kitabın
−%14,5 düşüşünde karşılaştırır:

  katman                       yıllık   Sharpe   düşüş   eşit-risk     Δ
  A çıplak kesitsel seçici     +72.5%   1.389   −34.8     +26.1%      —
  B + kalabalık havuzu        +107.1%   2.058   −20.4     +68.9%   +42,8
  C + emir akışı %20          +109.8%   2.095   −23.0     +59.8%    −9,1
  D + uç hareket elemesi      +103.1%   2.238   −23.6     +54.0%    −5,8
  E + fırsat rezervi           +92.8%   2.200   −19.8     +61.8%    +7,8
  F + KÂR AL (tam kitap)      +112.5%   2.942   −14.5    +112.5%   +50,7

Çıplak seçici TEK BAŞINA KÂRLI (+%72,5, Sharpe 1,39) ama eşit riskte tam
kitabın dörtte birini veriyor; −%34,8 düşüşle de taşınabilir değil. En
büyük iki katman: **KÂR AL hasadı (+50,7 puan)** ve kalabalık havuzu
(+42,8). Bu, madde 214'ün "funding gelir değil seçici" çerçevesinin
üçüncü bağımsız ölçümü.

KATMANLAR TOPLAMSAL DEĞİL: emir akışı (−9,1) ve uç hareket elemesi
(−5,8) merdivenin BU noktasında negatif, oysa tam yapılandırmadan
ÇIKARILINCA ikisi de kitabı kötüleştiriyor (madde 228/236). Bir
katmanın işareti, YANINDA NE DURDUĞUNA bağlı - bu yüzden "şu katman
kaç puan getiriyor" sorusunun tek bir doğru cevabı yoktur ve
yeniden-açma her zaman TAM yapılandırmada yapılmalıdır (madde 177).
Araç: `arastirma_katman.py`.

DEĞİŞTİ: %70 -> %40 (MADDE 178). Yukarıdaki tablo, kalabalık seçimi ve
fırsat rezervi DEVREDE DEĞİLKEN ölçülmüştü (Sharpe seviyeleri ~1.9-2.0,
bugün 2.4-2.7). Madde 177'nin dersi uygulandı: parametre, TAM
yapılandırmada ve ALTI saat fazının ortalamasıyla yeniden ölçüldü.

  6+6, faz ortalamalı:
  seviye   yıllık   Sharpe   maks düşüş   22-24 Sh   25-26 Sh   faz aralığı
   %70     +89.1%    2.41      -20.1%       2.43       2.55     2.18-2.44
   %40     +88.3%   *2.66*     -21.2%       2.54       2.88     2.44-2.69

Getiri aynı (0.8 puan fark), Sharpe 2.41 -> 2.66. İki dönemde de
iyileşiyor ve ALTI FAZIN HEPSİNDE daha iyi: %40'ın EN KÖTÜ fazı (2.44),
%70'in EN İYİ fazına (2.44) eşit. Düşüş 1.1 puan kötüleşiyor (sınır 3).

Mekanizma aynı, sadece daha erken: squeeze geri dönüşünü %70 yerine
%40'ta kilitlemek, dönüşten önce daha sık yakalıyor.

Tek faz taramasında (6+6) Sharpe tepesi: %25 2.37 | %30 2.47 |
**%40 2.63** | %50 2.53 | %70 2.44 | %100 2.42 | kapalı 1.99."""

KAR_AL_SHORT = float(os.getenv("CARRY_KAR_AL_SHORT", "0.20"))
"""SHORT bacaklar için AYRI kâr al eşiği (madde 189).

Madde 189'da kâr kaynakları ayrıştırıldı ve şu çıktı: kârın üçte ikisi
LONG taraftan geliyor, SHORT bacakların funding katkısı ise yıllık
sadece +11 puan. Yani short bacak esasen bir HEDGE'dir - ve hedge'in
kârı, shortlanan coin çöktüğünde alınır.

Simetrik %40 eşiği bu çöküşleri çok geç yakalıyordu. Short eşiği
taranınca (long %40 sabit, 6 faz ortalaması):

  short TP   yıllık   Sharpe   düşüş   22-24 Sh   25-26 Sh
  kapalı    +79.1%    2.505   -16.5%    2.505     2.310
  %10       +91.0%    2.657   -17.9%    2.742     2.600
  %15       +93.5%    2.758   -16.9%    2.658     2.935
  **%20**   +96.8%   **2.840** -15.1%  **2.717**  **3.045**  <- seçilen
  %25       +96.4%    2.838   -16.3%    2.763     2.990
  %30       +94.9%    2.815   -16.6%    2.758     2.950
  %40       +91.6%    2.755   -17.0%    2.652     2.970   (eski)
  %60       +83.6%    2.540   -16.9%    2.540     2.470

Geniş, düzgün bir plato (%20-%30 arası hepsi >=2.815) - uçurum kenarı
DEĞİL. En kötü durumda (%15'e kayarsa) bugünkü seviyeye dönülür.

DOĞRULAMA (madde 188'in dersi): tarihsel düşüş değil BOOTSTRAP düşüşü
kullanıldı. 1 yıllık p5 düşüşü −%20.7 → −%20.4 (iyileşiyor), p1
−%26.6 → −%25.5. Aynı p5 riskine ölçeklendiğinde getiri **+%91.4 →
+%103.8**.

Long eşiği %40'ta KALIYOR: %50/%25 kombinasyonu ham getiride daha
yüksek (+%101.9) ama aynı riskte daha az (+%100.3), çünkü p5 düşüşü
kötüleşiyor.

MADDE 227'DE YENİDEN AÇILDI VE %20 YİNE ÇIKTI. Tarama `KAR_AL_ORAN`
docstring'inde (TPL/TPS birlikte tarandığı için): 0,40/0,10 +%105,0 ·
0,40/0,15 +%108,4 · **0,40/0,20 +%112,6 (kalan)** · 0,40/0,30 +%108,8.
Her iki taraf da tepe noktasında.

MADDE 240 — BU ÇAPRAZ ATIF BİR DENETİM BULGUSUDUR. Madde 240'ın
yeniden-açma defteri (`arastirma_yeniden_acma_defteri.py`) docstring'leri
okuyarak "en son hangi maddede ölçüldü" tablosunu kuruyor; bu parametre
orada **madde 189** görünüyordu, çünkü 227'deki ölçümü BAŞKA bir
parametrenin docstring'inde duruyordu. Defterin yapısal sınırı bu:
birlikte taranan parametrelerde ölçümü taşıyan docstring tek olunca
öteki BAYAT görünür. Çözüm çapraz atıf - bu paragraf onun kendisi."""

SHORT_FELAKET = float(os.getenv("CARRY_SHORT_STOP", "2.0"))
"""SHORT FELAKET STOP'U (madde 428-436). Short bacak girişten +%X aleyhe
giderse borsada bekleyen STOP_MARKET (reduceOnly, MARK fiyatı) kapatır.
0 kapatır. Varsayılan 2,0 = +%200.

Bu bir getiri ayarı DEĞİL, kuyruk sigortasıdır. Madde 427: yaş 45
evreninde MYX (6 Ağu 2025, tek gün −%63) ve AIA (7 Kas 2025, −%165) short
sıkışmaları gerçekçi ağırlık kaymalı modelde hesabı SIFIRLADI. Madde 428:
yaş 90 kitapta +%300 stop 4 yılda hiç tetiklenmedi (maliyet ≈0), +%200
yılda ~1 puan; yaş 45 kombinasyonunda dd −%191 -> −%21,7. Eski "stop
YOKTUR" kuralı (madde 143/191) DAR stoplar (%10-30) içindir: onlar
gürültüyle tetiklenip kirayı öldürüyordu; +%200 gürültüye takılmaz.
Yaş eşiği 60'a indirilirse (CARRY_MIN_LISTING_DAYS=60) bu stop ŞARTTIR.

Dolan stop, dolan kâr al gibi işlenir: sembol tüm dilim hedeflerinden
çıkar (aynı turda yeniden açılmasın)."""

BUGUN_PROFIL = {"FUNDING_WINDOW_HOURS": 48.0, "KAR_AL_ORAN": 0.40, "UC_HAREKET_ELE": 0.40,
                "REZERV_PAY": 0.20, "MIN_DAILY_VOLUME_USD": 1e8, "MIN_LISTELEME_GUN": 90}
"""Madde 442'den ÖNCEKİ varsayılanlar (eski kitap). Tarihsel maddelerin
"ayar DEĞİŞMEDİ" denetimleri bu sözlüğe bakar: o maddeler bu kitabı ölçtü."""

LONG_FELAKET = float(os.getenv("CARRY_LONG_STOP", "0"))
"""LONG FELAKET STOP'U (madde 443-445). Long bacak girişten −%X düşerse borsada
bekleyen STOP_MARKET (SELL, reduceOnly, MARK fiyatı) kapatır. 0 = KAPALI (varsayılan).

Bir KÂR ayarı değil, kullanıcının risk tercihine bırakılan DÜĞME. T60'ın en kötü
günleri piyasa çöküşü değil, TEK küçük coinin long'ta tek günde %80-90 çökmesi
(POWER, REEF, SIREN). Backtest (2.000 $, kaymalı model):
  CARRY_LONG_STOP   yıllık    en kötü gün   −%5 altı gün
  0 (kapalı)        +%222       −%8,6           9
  0.45              +%210       −%6,5           7
  0.40              +%208       −%5,9           6
  0.35              +%203       −%5,5           5
Aynı en kötü güne sabit doz düşürmeyle (0,69x) inmek yıllık ~+%127 bırakırdı;
stop aynı korumayı çok daha ucuza verir. Maliyetin çoğu 2025'te (V dönüşleri).
Saatlik veride çöküşlerin çoğu stop seviyesinden geçerek iniyor; tek saatte
uçurum yapanlarda (POWER −%48/saat) dolum seviyenin altında olur."""

LONG_24S = float(os.getenv("CARRY_LONG_24S", "0.45"))
"""24 SA DÜŞÜŞ STOP'U (madde 449-453). Long bacak, coinin 24 sa önceki kapanışından
−%X düşerse borsada bekleyen STOP_MARKET (SELL, reduceOnly, MARK) ile kapanır;
seviye her turda (8 sa) yenilenir. 0 = kapalı. VARSAYILAN 0,45.

Girişten bağımsızdır: normal dalgalanmada (yavaş düşüş) çalışmaz, yalnız gerçek
çöküşte (pompala-boşalt, madde 446) devreye girer. Backtest (T60, 2.000 $, kaymalı,
seviye 8 sa'te bir yenilenerek - madde 452):
  CARRY_LONG_24S   yıllık    en kötü gün   −%5 altı gün
  0 (kapalı)       +%222       −%8,6           9
  0.40             +%217       −%5,5           6
  0.45             +%216       −%5,5           7     <- varsayılan
  0.50             +%217       −%5,9           7
  0.55             +%214       −%6,5           7
3.500 $'da da aynı (−%8,6 → −%5,5, 5 puan). Girişten stop'la (CARRY_LONG_STOP)
BİRLİKTE kullanmak daha kötü (madde 452: 15 puan, en kötü gün −%5,9)."""

# MADDE 442 — VARSAYILAN PROFİL T60. Madde 429-438'in vardığı ayar varsayılan
# yapıldı: hacim 70M (CARRY_MIN_VOLUME), yaş 60 (CARRY_MIN_LISTING_DAYS),
# rezerv 0,10 (CARRY_REZERV), uç hareket eleme kapalı (CARRY_UC_HAREKET=0),
# funding penceresi 60 sa (CARRY_FUNDING_WINDOW_H), long kâr al 0,60
# (CARRY_KAR_AL), short felaket stop'u +%200 (CARRY_SHORT_STOP). Backtest
# (gerçekçi ağırlık kayması, 2.000 $): yıllık +%222 / dd −%20,8; eski
# varsayılanlar +%128 / −%21,0. Eski kitap CARRY_PROFIL=BUGUN + eski
# değerlerle hâlâ kurulabilir (carry_preflight.py iki profili de tanır).

TEMINAT_MODU = os.getenv("CARRY_TEMINAT_MODU", "usdt").strip().lower()
"""Sermaye nasıl okunsun: "usdt" (varsayılan) | "coklu" (madde 141).

"coklu": Binance çoklu varlık modunda BFUSD / LDUSDT gibi getiri
taşıyan teminat kullanılıyorsa. Bot toplam teminat değerini
(`totalMarginBalance`) okur.

"usdt": sadece USDT satırı okunur. Hesapta USDT dışı teminat tespit
edilirse bot turu ATLAR ve HATA yazar - aksi halde bakiyeyi ~0 görüp
sessizce işlem yapmayı bırakırdı (projedeki sessiz no-op sınıfı).

UYARI: BFUSD'nin getirisi de funding ücretlerinden gelir (Binance'in
kendi delta-nötr stratejisi). Yani bu botun edge'iyle AYNI primden
beslenir: funding çökerse ikisi birlikte düşer. Çeşitlendirme değildir."""

SAGLIK_GOLGE_BACAK = 12
"""Gölge kitabın bacak sayısı. Eşikler 12+12 ile kalibre edildi;
N_LEGS değişse bile dedektör 12 ile ölçer ki eşikler anlamlı kalsın."""


# ------------------------------------------------------------------ VERİ
def yillik_funding(kayitlar: list, saat: float = None) -> float | None:
    """Funding geçmişinden YILLIKLAŞTIRILMIŞ oranı hesaplar.

    KRİTİK: her sembol 8 saatte bir ödemez. Ölçüldü (madde 114):
    122 sembolün 24'ü 4 SAATTE bir, 1'i SAATTE bir öder. Ham oranı
    karşılaştırmak yanlış sıralama yaptırır - 4 saatlik bir coinin
    ham oranı yarı görünür ama yıllık getirisi 2 KATIDIR.

    Aralık, ardışık ödeme zaman damgalarının MEDYANINDAN çıkarılır;
    sabit varsayılmaz. Bu, backtest ile canlı bot arasındaki paritenin
    can alıcı noktası.
    """
    if len(kayitlar) < 2:
        return None
    zaman = sorted(int(k["fundingTime"]) for k in kayitlar)
    farklar = [(zaman[i + 1] - zaman[i]) / 3600000.0
               for i in range(len(zaman) - 1)]
    farklar = [f for f in farklar if 0.5 <= f <= 24]
    if not farklar:
        return None
    aralik = sorted(farklar)[len(farklar) // 2]        # medyan saat
    # ARALIK ALT SINIRI (madde 138): Binance bazı sembollerde ödeme
    # aralığını geçici olarak kısaltıyor (4sa -> 1sa). Medyan 1 çıkarsa
    # sinyal x24 ile çarpılır, 4 saatlikte x6 - yani sinyal 4 KAT şişer
    # ve sembol sıralamada uca fırlar. Ölçüldü: bu 4 sembol backtest'te
    # -379 USD (net P&L'nin -%1.2'si) götürüyordu.
    # Binance'in kalıcı en kısa aralığı 4 saattir; altı geçici bir
    # durumdur ve kalıcı oran olarak yıllıklaştırılmamalıdır.
    aralik = max(aralik, 4.0)
    # MADDE 182: SADECE pencere içindeki ödemeler ortalanır.
    # Eskiden gelen TÜM kayıtlar ortalanıyordu; `funding_topla` 73 kayıt
    # istediği için 8 saatlik bir sembolde bu 24 GÜNLÜK ortalama demekti
    # (4 saatlikte 12 gün, 1 saatlikte 3 gün). Yani hem ISTENEN pencere
    # (72 saat) tutmuyordu hem de her sembol FARKLI uzunlukta bir
    # pencereyle sıralanıyordu.
    sec = kayitlar
    if saat and saat > 0:
        try:
            son = max(int(k["fundingTime"]) for k in kayitlar)
            kes = son - int(saat * 3600000)
            # MADDE 209: SINIR DIŞLAYICI. Eskiden `>=` idi; ödeme aralığı
            # tam pencere boyuna eşit olan sembolde (8sa pencere, 8sa
            # sembol) pencerenin İKİ ucundaki ödeme de sayılıyor, yani
            # "8 saat" fiilen 16 saat oluyordu. 72 saatte de aynı hata
            # 9 ödemeyi 10 yapıyor; panelin 18 barlık ortalaması TAM 9
            # ödemeye denk düştüğü için parite ancak dışlayıcı sınırla
            # kuruluyor.
            icinde = [k for k in kayitlar if int(k["fundingTime"]) > kes]
            if icinde:
                sec = icinde
        except (KeyError, TypeError, ValueError):
            pass
    ort = sum(float(k["fundingRate"]) for k in sec) / len(sec)
    return ort * (24.0 / aralik) * 365.0


def funding_topla(client: ExchangeClient, semboller: list[str],
                  saat: float) -> pd.Series:
    """Her sembol için YILLIKLAŞTIRILMIŞ ortalama funding oranını döner.

    Binance funding geçmişi endpoint'i sembol başına ayrı istek ister.
    Hız sınırına takılmamak için aralarda kısa bekleme var.
    """
    # Aralık tespiti için birkaç kayıt yeterli; pencere filtresini
    # `yillik_funding` ZAMAN damgasından uyguluyor (madde 182).
    # Fazla kayıt istemek artık zararsız - çünkü ortalamaya girmiyor.
    # MADDE 209: kayıt sayısı EN SIK ödeyene göre hesaplanır. Eski
    # formül `saat/2 + 4` idi; 72 saatlik pencerede 40 kayıt verir ve
    # SAATLİK ödeyen bir sembolde pencere 72 saat yerine ~40 saate
    # kırpılırdı (sessizce, sembole göre FARKLI pencere - madde 182'nin
    # düzelttiği hatanın aynısı). En kısa aralık 1 saat kabul edilir.
    n = max(4, min(400, int(saat) + 4))
    out = {}
    for i, s in enumerate(semboller):
        try:
            h = client.client.futures_funding_rate(symbol=s, limit=n)
            y = yillik_funding(h, saat)
            if y is not None:
                out[s] = y
        except Exception as e:
            logger.warning("%s funding alınamadı: %s", s, e)
        if i % 20 == 19:
            time.sleep(0.5)
    return pd.Series(out, dtype=float)


def _bakiye_yaz(yol: str, bakiye: float, olcek: float) -> None:
    """Bakiye geçmişine bir satır: zaman, bakiye, o turda uygulanan ölçek."""
    try:
        with open(yol, "a", encoding="utf-8") as fh:
            fh.write(f"{time.time():.0f},{bakiye:.4f},{olcek:.6f}\n")
    except OSError as e:
        logger.warning("bakiye geçmişi yazılamadı: %s", e)


def vol_olcek(bakiye: float, dosya: str = None,
              olcme_yap: bool = True) -> float:
    """Bakiye geçmişinden oynaklık hedefi ölçeğini hesaplar.

    Yeterli geçmiş yoksa 1.0 döner - yani ölçek uygulanmaz. Sessizce
    yanlış bir ölçek uygulamaktansa hiç uygulamamak tercih edildi.
    """
    yol = dosya or VOL_GECMIS_DOSYA
    if not VOL_HEDEF:
        # Oynaklık hedefi kapalı olsa bile bakiye KAYDEDİLİR (madde 151):
        # canlı/backtest karşılaştırması (carry_sapma.py) bu dosyayı okur,
        # ve profil sonradan açılırsa geçmiş hazır olur.
        if olcme_yap:
            _bakiye_yaz(yol, bakiye, 1.0)
        return 1.0
    gecmis, zamanlar, olcekler = [], [], []
    try:
        if os.path.exists(yol):
            with open(yol, encoding="utf-8") as fh:
                for satir in fh:
                    parca = satir.strip().split(",")
                    if len(parca) >= 2:
                        try:
                            z = float(parca[0])
                            b = float(parca[1])
                            # 3. sütun: o turda UYGULANAN ölçek. Eski
                            # dosyalarda yok -> 1.0 varsayılır.
                            o = float(parca[2]) if len(parca) >= 3 else 1.0
                        except ValueError:
                            continue
                        if b <= 0 or o <= 0:
                            continue
                        gecmis.append(b)
                        zamanlar.append(z)
                        olcekler.append(o)
    except OSError as e:
        logger.warning("bakiye geçmişi okunamadı: %s", e)
        return 1.0

    olcek = _vol_olcek_hesapla(gecmis + [bakiye], zamanlar, olcekler)

    if olcme_yap:
        # Kayıt SADECE gerçek turda yapılır. Ön kontrol (bacak sayısı
        # hesabı) aynı turda ikinci bir satır yazarsa oynaklık tahmini
        # bozulurdu - sessiz bir hata olurdu. Uygulanan ölçek de yazılır
        # ki sonraki turlar KALDIRAÇSIZ oynaklığı geri hesaplayabilsin.
        _bakiye_yaz(yol, bakiye, olcek)
    return olcek


def _vol_olcek_hesapla(bakiyeler: list, zamanlar: list, olcekler: list) -> float:
    """Ölçeği hesaplar. bakiyeler = geçmiş + şimdiki bakiye (son eleman).

    İKİ HATA DÜZELTMESİ (madde 140):

    1) YILLIKLAŞTIRMA: eskiden `365.25*24/REBALANCE_HOURS` = 73 örnek/yıl
       varsayılıyordu. Bot günde bir tur atıp bakiye yazıyor; günlük veriyi
       73 ile yıllıklaştırmak oynaklığı sqrt(5)=2.24 kat DÜŞÜK ölçüp
       kaldıracı 2.24 kat şişiriyordu (temiz veride ort. 2.18x, max
       düşüş -%54). Artık gerçek aralık zaman damgalarından alınır.

    2) KENDİ KALDIRACINI ÖLÇMEK: eskiden oynaklık botun KALDIRAÇLI
       bakiyesinden ölçülüp ölçek sıfırdan `hedef / ölçülen` diye
       konuyordu. Ölçek 1.5x iken ölçülen oynaklık zaten 1.5 kat şişik;
       sistem hedefe değil sqrt(hedef/oynaklık)'a yakınsıyordu - yani
       "güvenli %20" pratikte kaldıraçsızdan RİSKLİ, "agresif %60"
       hedefine hiç ulaşmıyordu. Artık her dönemin getirisi o dönemde
       uygulanan ölçeğe bölünür: KALDIRAÇSIZ oynaklık ölçülür.
    """
    if len(bakiyeler) < VOL_MIN_KAYIT:
        logger.info("oynaklık hedefi: yeterli geçmiş yok (%d/%d) - ölçek 1.0",
                    len(bakiyeler), VOL_MIN_KAYIT)
        return 1.0
    b = np.array(bakiyeler, dtype=float)
    g = b[1:] / b[:-1] - 1.0
    # dönem t'nin getirisi, t-1 anında konan ölçekle kazanıldı
    o = np.array((olcekler + [1.0])[:len(g)], dtype=float)
    o = np.where(o > 0, o, 1.0)
    u = g / o
    u = u[np.isfinite(u)][-VOL_PENCERE:]
    if len(u) < 5 or u.std() <= 1e-9:
        return 1.0
    aralik_sn = None
    if len(zamanlar) >= 3:
        dz = np.diff(np.array(zamanlar, dtype=float))
        dz = dz[dz > 0]
        if len(dz):
            aralik_sn = float(np.median(dz))
    if not aralik_sn:
        aralik_sn = REBALANCE_HOURS / max(1, N_DILIM) * 3600.0   # tur aralığı
    tur_yil = 365.25 * 86400.0 / aralik_sn
    yillik_vol = float(u.std() * np.sqrt(tur_yil))
    olcek = float(np.clip(VOL_HEDEF / yillik_vol, 0.3, 3.0))
    logger.info("oynaklık hedefi: kaldıraçsız %%%.1f/yıl, hedef %%%.1f -> ölçek %.2fx",
                yillik_vol * 100, VOL_HEDEF * 100, olcek)
    return olcek


# --- MADDE 288: PRİM-ÖLÇEKLİ BRÜT ------------------------------------
# Yapı madde 239'da motora yazıldı (`g33.py`: BRUT_PRIM/REF/ALT/UST),
# orada ŞART 1'den düştü ve CANLI BOTA HİÇ GİRMEDİ. Madde 288 dozu
# taradı: e0,10 / ref150 dört şartı da geçiyor (geçen band ref 120-180,
# ref 90 ve 270 düşüyor) ve doz ölçütünde +12,15 puan, eşli blok
# bootstrap P(>0) %95,0 - plasebolar %71,0 ve altında kalıyor.
#
# Ölçü FİYAT TAHMİNİ DEĞİL: uygun sembollerin yıllık funding'inde
# kesitsel p90-p10 (madde 239'un bütçesi: bu ölçü kitabın KENDİ ileriye
# dönük getirisini tek yönlü sıralıyor, oynaklık çeyrekler arasında
# DÜZ -> edge yoğunluğu ölçüsü).

def prim_olc(funding: "pd.Series") -> float:
    """Kesitsel funding primi: p90 - p10 (yıllıklaştırılmış oran)."""
    f = pd.Series(funding, dtype=float).dropna()
    if len(f) < 5:
        return float("nan")
    return float(f.quantile(0.9) - f.quantile(0.1))


def prim_kaydet(deger: float, yol: str = None, yaz: bool = True) -> None:
    """Bir prim ölçümünü geçmişe ekler (zaman, değer). Kuru çalışma YAZMAZ."""
    if not yaz or deger != deger:
        return
    yol = yol or PRIM_DOSYA
    try:
        with open(yol, "a", encoding="utf-8") as fh:
            fh.write("%.0f,%.8f\n" % (time.time(), deger))
    except OSError as e:
        logger.warning("prim geçmişi yazılamadı: %s", e)


def _prim_gecmis_oku(yol: str = None) -> list:
    yol = yol or PRIM_DOSYA
    out = []
    try:
        with open(yol, "r", encoding="utf-8") as fh:
            for satir in fh:
                p = satir.strip().split(",")
                if len(p) == 2:
                    try:
                        out.append((float(p[0]), float(p[1])))
                    except ValueError:
                        continue
    except OSError:
        return []
    out.sort()
    return out


def prim_carpani(yol: str = None, simdi: float = None) -> float:
    """Brüte uygulanacak çarpan. Geçmiş yetmezse 1,0 (yani KAPALI gibi).

    (30 günlük prim ortalaması / kendi PRIM_REF_GUN günlük medyanı) ** e,
    [PRIM_ALT, PRIM_UST] aralığına kırpılır. Bugünün ölçümü çağrı
    sırasında henüz yazılmadığı için **1 tur gecikme** doğaldır (motorun
    `.shift(1)`'i).

    GERİYE DÖNÜK MEDYAN DEĞİL, KAYAN MEDYAN: madde 239'un notu -
    genişleyen medyan kullanılırsa yapı "2025 sonrası kaldıraç artır"a
    döner ve bu TEK bir gerçekleşmedir.
    """
    if PRIM_E <= 0:
        return 1.0
    g = _prim_gecmis_oku(yol)
    if not g:
        return 1.0
    simdi = time.time() if simdi is None else simdi
    gun = 86400.0
    olc = [v for t, v in g if simdi - t <= PRIM_OLC_GUN * gun]
    ref = [v for t, v in g if simdi - t <= PRIM_REF_GUN * gun]
    # Motorun min_periods'u: ölçüm penceresinin 2/3'ü, referansın 1/2'si.
    if len(olc) < 2 or (simdi - g[0][0]) < PRIM_REF_GUN * gun * 0.5:
        return 1.0
    if len(ref) < 3:
        return 1.0
    o = float(np.mean(olc))
    r = float(np.median(ref))
    if not (o > 0 and r > 0):
        return 1.0
    m = float(np.clip((o / r) ** PRIM_E, PRIM_ALT, PRIM_UST))
    logger.info("prim-ölçekli brüt: 30g ort %.5f / %dg medyan %.5f -> çarpan %.4f",
                o, PRIM_REF_GUN, r, m)
    return m


def kalabalik_topla(client: ExchangeClient, semboller: list[str]) -> pd.Series:
    """Sembol -> hesap bazında long/short oranı (son 5 dk değeri).
    >1: long hesap çok, <1: short hesap çok. Alınamayan sembol atlanır."""
    out = {}
    for i, s in enumerate(semboller):
        try:
            r = client.client.futures_global_longshort_ratio(symbol=s, period="5m", limit=1)
            if r:
                v = float(r[-1]["longShortRatio"])
                if v > 0 and np.isfinite(v):
                    out[s] = v
        except Exception as e:
            logger.warning("%s long/short oranı alınamadı: %s", s, e)
        if i % 20 == 19:
            time.sleep(0.5)
    return pd.Series(out, dtype=float)


KALABALIK_ONBELLEK_DOSYA = os.getenv(
    "CARRY_KALABALIK_ONBELLEK",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "carry_kalabalik.json"))
"""Son alınan long/short oranları, zaman damgasıyla (madde 363)."""

KALABALIK_BAYAT_SAAT = float(os.getenv("CARRY_KALABALIK_BAYAT_SAAT", "24"))
"""Oran API'si cevap vermezse son bilinen oran en fazla kaç saat eski olabilir.

MADDE 361/362/363. Kalabalık seçimi kitabın yük taşıyan parçası: havuzdan
rastgele seçim `ls`'nin yılda 77-91 puan ALTINDA (madde 358). Oran API'si
adayların yarısından azına cevap verirse bot eskiden doğrudan "en uç n"e
düşüyordu; HAVUZ 4 kitabında bu yedeğin fiyatı ölçüldü ve bayat oranla
karşılaştırıldı (2.000 $ / 3.500 $, iki hiza, kontrole göre yıllık puan):

  yedek                yıllık          düşüş      eşit-risk
  en uç n (eski)      −38 .. −47     +5,6 .. +9,0   −72 .. −82
  24 sa bayat oran     −5 .. −10     +0,6 .. +0,9   −11 .. −19   <- seçilen
  48 sa bayat oran    −15 .. −23     +3,2 .. +4,0   −39 .. −49
  144 sa bayat oran   −34 .. −43     +6,7 .. +9,2   −71 .. −80  (= en uç n)

Oranın bilgisi hızla eriyor; 6 günde sıfırlanıyor. 24 saat dört hücrede
de en uç n'den açık ara iyi. 0 verilirse önbellek kullanılmaz (eski
davranış). Bu bir kâr kaldıracı değil, bir ARIZA MODUNUN maliyetini
~%80 küçülten sigorta."""


def _kalabalik_onbellek_oku(dosya: str = None) -> dict:
    dosya = dosya or KALABALIK_ONBELLEK_DOSYA
    try:
        with open(dosya, encoding="utf-8") as fh:
            d = json.load(fh)
        return {k: (float(v[0]), float(v[1])) for k, v in d.items()
                if isinstance(v, (list, tuple)) and len(v) == 2}
    except (OSError, ValueError, TypeError):
        return {}


def _kalabalik_onbellek_yaz(taze: pd.Series, simdi: float, dosya: str = None) -> None:
    dosya = dosya or KALABALIK_ONBELLEK_DOSYA
    d = _kalabalik_onbellek_oku(dosya)
    for s, v in taze.items():
        d[s] = (float(v), float(simdi))
    tmp = dosya + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({k: list(v) for k, v in sorted(d.items())}, fh)
        os.replace(tmp, dosya)          # atomik (madde 72)
    except OSError as e:
        logger.warning("kalabalık önbelleği yazılamadı: %s", e)


def kalabalik_onbellekle_tamamla(taze: pd.Series, adaylar: list, simdi: float = None,
                                 dosya: str = None) -> tuple[pd.Series, int]:
    """Taze oranı olmayan adayları, KALABALIK_BAYAT_SAAT içindeki son
    bilinen oranla doldurur. Taze oranları önbelleğe yazar.
    Döner: (birleşik seri, önbellekten gelen aday sayısı)."""
    simdi = time.time() if simdi is None else simdi
    if len(taze):
        _kalabalik_onbellek_yaz(taze, simdi, dosya)
    if KALABALIK_BAYAT_SAAT <= 0:
        return taze, 0
    ob = _kalabalik_onbellek_oku(dosya)
    ek = {}
    for s in adaylar:
        if s in taze.index or s not in ob:
            continue
        v, t = ob[s]
        if v > 0 and np.isfinite(v) and 0 <= simdi - t <= KALABALIK_BAYAT_SAAT * 3600:
            ek[s] = v
    if not ek:
        return taze, 0
    return pd.concat([taze, pd.Series(ek, dtype=float)]), len(ek)


def kalabalik_adaylar(skor: pd.Series, n: int, havuz: float = None) -> tuple[list, list]:
    """Her taraf için aday havuzu (skor sırasına göre, en uç önce)."""
    havuz = KALABALIK_HAVUZ if havuz is None else havuz
    f = skor.dropna().sort_values()
    m = min(max(n, int(havuz * n)), len(f) // 2)
    return list(f.index[:m]), list(f.index[::-1][:m])


def kalabalik_sec(adaylar: list, oran: pd.Series, n: int, taraf: int) -> list:
    """Adaylar EN UÇTAN başlayarak sıralı. taraf=+1 long, -1 short.
    Long: oranı EN DÜŞÜK (en çok short hesap) olanlar; short: EN YÜKSEK.
    Oranı olmayan aday, uç sırasına göre puanlanır (backtest ile birebir)."""
    if not adaylar:
        return []
    m = len(adaylar)
    olc = np.array([-taraf * np.log(oran[a]) if (a in oran.index and oran[a] > 0)
                    else np.nan for a in adaylar], float)
    p = pd.Series(olc).rank(pct=True).values
    yedek = np.linspace(1, 0, m)
    p = np.where(np.isfinite(olc), p, yedek)
    sira = np.argsort(-p, kind="stable")[:n]
    return [adaylar[j] for j in sira]


UC_HAREKET_ELE = float(os.getenv("CARRY_UC_HAREKET", "0"))
"""MADDE 442: VARSAYILAN 0 = KAPALI (T60 kitabı; madde 429-433: UCELE 0 komşusu
+56,7 puanla kontrolü geçiyor, 0,40 ise T60'tan 2 puan dd kötü). Eski kitap
0,40 ile ölçülmüştü; aşağıdaki tarih o kitabındır.

MADDE 236 — YENİDEN AÇILDI (hiç açılmamıştı) VE 0,40 OPTİMUMDA ÇIKTI.

Bu eşik madde 196'da kondu ve 222'nin yeniden-açma listesine HİÇ
girmedi. Madde 236'nın bacak bazında katkı defteri ona işaret etti: en
kötü 250 bacağın ayırt edici niteliği, girişten önceki 6 barlık yukarı
hareket (medyan +%2,12; tüm bacaklarda +%0,08).

  eşik      yıllık   Sharpe   düşüş   22-24   25-26   eşit-risk
  kapalı   +116.2%   3.017   −14.2   2.929   3.182    +120.9%
  0,20      +95.1%   2.967   −15.2   3.000   2.942     +89.8%
  0,30     +107.9%   3.114   −14.5   3.017   3.266    +108.3%
 *0,40*   *+112.6%* *3.128* −14.6  *2.984* *3.342*   +112.6%  <- kalan
  0,60     +112.1%   3.044   −14.6   2.928   3.228    +118.6%

Dördü de RED. Tarama TEK YÖNLÜ DEĞİL: 0,20 hem kapalıdan hem 0,40'tan
kötü, yani aşırı filtreleme kazananları da kesiyor.

**NEDEN SIKMAK İŞE YARAMIYOR - VE BU PROJENİN GENEL CEVABI:** önceki
hareket bir ZARAR seçicisi değil, bir KUYRUK seçicisi. Katkı defteri
(44.961 bacak) en kötü 250 ile en iyi 250'yi yan yana koyuyor:

  nitelik (medyan)      en kötü 250   en iyi 250    tümü
  funding sinyali         −0,0025      −0,0253    +0,0001
  oynaklık                +0,0669      +0,0699    +0,0215
  önceki 6 bar hareket    +0,0212      +0,0076    +0,0008
  LONG oranı                 %68        **%100**      %50

Oynaklık ve önceki hareket İKİ KUYRUKTA DA yüksek. Yani bu niteliklere
dayanan her filtre, zararı keserken kârı da kesiyor - madde 221'in
oynaklığa göre ölçeklenmiş TP'sinin, madde 236'nın UCELE sıkmasının ve
genel olarak madde 196'dan beri hiçbir yeni filtrenin işe yaramamasının
TEK sebebi bu.

Ayırt eden tek nitelik **funding sinyalinin ucluğu** (en iyi 250'de
−0,0253 vs tümünde +0,0001, yani 250 kat) - ve kitap onu zaten
kullanıyor. Madde 222'nin yoğunlaşma yasası tam olarak bu.

MADDE 241 — AYNI %40 EŞİĞİNİN TERS İŞARETİ ÖLÇÜLDÜ: "pump olanı SHORT,
dump olanı LONG" ayrı bir kol olarak. Bu filtre pump'ı long adaylığından
ÇIKARIYOR; kullanıcının sorduğu şey onu AKTİF OLARAK SHORT'lamaktı.

  olay (3 gün)      N      ort      medyan   kazanan      p1    en kötü
  pump -> SHORT   3.999   +%4,06   +%12,07    %68,6    −%145,7   −%743
  dump -> LONG      752   +%2,81   −%10,33    %35,2     −%81,7   −%100

**Gözlem gerçek** (%68,6 kazanan, medyan +%12,07) ama beklenti kuyrukta
eriyor. Sebep bu docstring'in akrabası olan madde 191: kitabın LONG
bacağı yıllık −108,5 puan kanama ödeyip **+141,6 puanlık sıkışma
opsiyonunu SATIN ALIYOR**; pump'ı short'lamak o opsiyonu **SATMAK**tır.

Dump tarafının ARZI YOK: ±%40'ta günde 0,79 pump ama **0,17 dump**,
günlerin **%87'sinde hiç dump yok**. Yani kol yapısal olarak net short
kalır (madde 215: eşleşmeyen bacak nötrlüğü bozar).

Sermaye payı HER PAYDA RED (en iyi varyant, 04 UTC): %5 eşit-risk
+%110,5 · %10 +%89,3 · %20 +%62,4. Ölçeklenebilir hâli (sıralama bazlı
geri dönüş) tek yönlü kötü: %100'de +%18,0. Araç:
`arastirma_olay_kolu.py`."""
"""Son 24 saatte bu ORANDAN fazla hareket eden coin, hareketin KARŞI
tarafında aday OLAMAZ (madde 196). 0 = kapalı.

+%40 pump olmuş coin LONG adayı olamaz (tepeden alma), −%40 dump olmuş
coin SHORT adayı olamaz (dipten satma). Sıralamayı değiştirmez, sadece
adayı havuzdan çıkarır.

Madde 195'te bulunan şey bu fikri doğurdu: pump olmuş coinde funding
NEGATİF oluyor - yani böyle bir coin bizim LONG adayı listesine
girebiliyor. Ama o anda long açmak, sıkışmanın tepesinden almaktır.

Ölçüldü (6 faz, tam yapılandırma):

  eşik      yıllık   Sharpe   22-24 Sh   25-26 Sh   1yıl p5 dd   p1 dd
  kapalı   +96.8%    2.840     2.717      3.045      -20.7%     -26.6%
  %20      +80.5%    2.787     2.723      2.897         -          -
  %30      +89.1%    2.878     2.752      3.070      -18.9%     -23.0%
  **%40**  +93.0%   **2.908**  **2.738**  **3.160**  **-19.2%** **-23.9%**
  %60      +93.2%    2.850     2.715      3.055         -          -

Doz-tepki tepe yapıyor (%20 kontrolden KÖTÜ, %40 en iyi, %60 geri
düşüyor) - eşik gürültü değil. İki alt dönemde de Sharpe artıyor.

DOĞRULAMA (madde 188'in ölçüsü): bootstrap 1 yıllık p5 düşüşü
−%20.4 → **−%19.2**, p1 −%25.5 → **−%23.9**. Yani KUYRUK RİSKİ
azalıyor. Aynı p5 riskine ölçeklendiğinde getiri
**+%96.2 → +%102.1.**

DÜRÜST UYARI: kaldıraçsız (GROSS=1.0) çalışırken bu değişiklik
getiriyi +%96.8'den +%93.0'a DÜŞÜRÜR. Kazanç, iyileşen riski
kaldıraçla getiriye çevirdiğinizde ortaya çıkıyor (+5.9 puan). Yani
bu, doz kararından ÖNCE alınan bir verimlilik iyileştirmesi.

Veri: `futures_ticker` zaten `priceChangePercent` veriyor - EK API
ÇAĞRISI YOK."""


DONUK_ESIK = float(os.getenv("CARRY_DONUK_ESIK", "0.10"))
"""Son 30 günün bu ORANINDAN fazla barında fiyatı HİÇ değişmeyen sembol
evrenden atılır (madde 183).

Backtest bu filtreyi en baştan beri kullanıyordu (`uygunluk()` içinde
`DONUK < 0.10`); CANLI BOT KULLANMIYORDU. 8. parite kontrolünde bulundu
ve ölçüldü (6 saat fazının ortalaması, tam yapılandırma):

  donuk filtresi   yıllık   Sharpe   düşüş(ort)   düşüş(en kötü)
  VAR  (%10)      +91.5%    2.68      -17.6%        -19.5%
  YOK             +90.0%    2.64      -18.6%        -20.0%

Getiri farkı küçük ama 6 fazın 5'inde aynı yönde; asıl fayda DÜŞÜŞTE.
Donuk seri = fiyatı güncellenmeyen, gerçekte işlem görmeyen sembol:
funding sıralamasında uç görünür, ama çıkmak istediğinizde karşı taraf
yoktur. Hacim filtresi bunları yakalamıyor (hacim raporlanıyor ama
fiyat kıpırdamıyor).

0 = kapalı. Veri alınamayan sembol CEZALANDIRILMAZ (filtreden geçer).

MADDE 240 — YENİDEN AÇILDI, 0,10 TEPEDE. Son tarama madde 183'teydi,
yani **57 tur önce** ve Sharpe 2,68'lik bir yüzeyde. Güncel
yapılandırma, iki faz ortalaması:

  eşik   yıllık   Sharpe   22-24   25-26   düşüş   eşit-risk
  0,05  +%112,0   2,951   2,784   3,181  −14,54    +%112,0
  **0,10** +%112,5 2,942  2,794   3,147  −14,54    +%112,5  <- kalan
  0,20  +%108,5   2,857   2,765   2,995  −14,54    +%108,5
  0,30  +%109,1   2,872   2,768   3,024  −15,13    +%103,1

Sıkılaştırmak 4 ila 9 puan yakıyor (filtre gerçek sembolleri eliyor),
gevşetmek nötr (0,05 pratikte beraberlik, eşit riskte −0,5 puan).
Madde 183'ün "asıl fayda düşüşte" tespiti bugün de geçerli: 0,05/0,10/
0,20 üçünün düşüşü AYNI (−14,54), fark getiride. Araç:
`arastirma_madde240.py`."""


def akis_topla(client: ExchangeClient, semboller: list[str],
               donuk_out: dict | None = None) -> pd.Series:
    """Emir akışı sinyali: agresif alıcı baskısı x hacim artışı.

    donuk_out verilirse, AYNI kline'lardan hesaplanan donukluk oranı
    (fiyatı değişmeyen bar payı) bu sözlüğe yazılır - ek API çağrısı yok.

    Binance kline'ları `taker_buy_quote_asset_volume` alanını verir -
    yani hacmin ne kadarı AGRESİF ALIM (piyasa emriyle alan) idi.
    0.5 = dengeli. Ölçülen medyan 0.4895.

    Sinyal = (son 5g alıcı payı - 0.5) x (son 5g hacim / son 30g hacim)
    YÜKSEK = alıcı baskısı artıyor VE hacim artıyor -> LONG adayı.
    """
    out = {}
    for i, s in enumerate(semboller):
        try:
            k = client.client.futures_klines(symbol=s, interval="4h",
                                             limit=AKIS_UZUN_BAR + 5)
            if len(k) < AKIS_UZUN_BAR:
                continue
            qv = np.array([float(x[7]) for x in k])      # quote_volume
            tb = np.array([float(x[10]) for x in k])     # taker_buy_quote
            if donuk_out is not None:
                kap = np.array([float(x[4]) for x in k])  # close
                if len(kap) > 1:
                    donuk_out[s] = float(np.mean(np.diff(kap) == 0))
            oran = np.divide(tb, qv, out=np.full_like(qv, np.nan), where=qv > 0)
            kisa = np.nanmean(oran[-AKIS_KISA_BAR:])
            hac_k = np.nanmean(qv[-AKIS_KISA_BAR:])
            hac_u = np.nanmean(qv[-AKIS_UZUN_BAR:])
            if not np.isfinite(kisa) or hac_u <= 0:
                continue
            out[s] = (kisa - 0.5) * (hac_k / hac_u)
        except Exception as e:
            logger.warning("%s akış alınamadı: %s", s, e)
        if i % 20 == 19:
            time.sleep(0.5)
    return pd.Series(out, dtype=float)


def birlesik_skor(funding: pd.Series, akis: pd.Series) -> pd.Series:
    """Funding ve emir akışını YÜZDELİK SIRAYA çevirip harmanlar.

    Ham değerleri toplamak yanlış olurdu - farklı birimler, farklı
    ölçekler. Yüzdelik sıra ikisini de [0,1] aralığına getirir.

    Sonuç DÜŞÜK olan LONG'lanır:
      - funding düşük/negatif  -> funding alırız
      - akış yüksek            -> alıcı baskısı var
    Bu yüzden akışın sırası TERSLENİR.
    """
    f = funding.dropna()
    if AKIS_AGIRLIK <= 0 or akis is None or akis.empty:
        return f
    ortak = f.index.intersection(akis.dropna().index)
    if len(ortak) < len(f) * 0.5:
        logger.warning("akış verisi yetersiz (%d/%d) - sadece funding kullanılıyor",
                       len(ortak), len(f))
        return f
    # PARİTE (madde 183): akış verisi OLMAYAN sembol evrenden ATILMAZ,
    # akış sırası nötr (0.5) sayılır - backtest de böyle yapıyor. Eskiden
    # kesişim alınıyordu: tek bir API hatası sembolü o tur seçimden
    # tamamen düşürüyordu.
    fr = f.rank(pct=True)
    ar = (-akis.reindex(f.index)).rank(pct=True).fillna(0.5)
    return (1 - AKIS_AGIRLIK) * fr + AKIS_AGIRLIK * ar


def limit_fiyat(fiyat: float, yon: str, hassasiyet: int, ofset: float = None) -> str:
    """Maker olması için limit fiyatı piyasadan uzağa koyar.

    ALIŞ -> piyasanın ALTINA (alıcı tarafında bekler)
    SATIŞ -> piyasanın ÜSTÜNE (satıcı tarafında bekler)

    GTX (post-only) ile gönderilir: emir taker olacaksa Binance onu
    kabul etmez, iptal eder. Böylece YANLIŞLIKLA taker olunmaz -
    maliyet avantajı garanti altına alınır.
    """
    o = LIMIT_OFSET if ofset is None else ofset
    if yon == "BUY":
        p = fiyat * (1 - o)
    else:
        p = fiyat * (1 + o)
    return f"{p:.{max(0, int(hassasiyet))}f}"


def taban_pay() -> float:
    """Bir bacağın kitap payı çarpanı: rezerv ayrıldıktan sonra kalan taban
    (madde 156/161). Rezerv kapalıysa 0.5 (klasik long %50 / short %50)."""
    return max(0.05, 0.5 - (REZERV_PAY / 2 if REZERV_PAY > 0 else 0.0))


def uygun_bacak_sayisi(bakiye: float, olcek: float = 1.0) -> int:
    """Bakiyeye göre bacak başına MIN_BACAK_USD kalacak en yüksek bacak sayısı.

    Sessizce eksik portföy kurmaktansa daha az ama DOLU bacak tercih
    edilir. N_LEGS'i asla AŞMAZ - sadece küçültür.
    """
    if not OTOMATIK_BACAK:
        return N_LEGS
    dilim = bakiye * olcek / max(1, N_DILIM)
    if dilim <= 0:
        return N_LEGS
    # bacak_usd = dilim * GROSS * (0.5 - REZERV/2) / n  >=  MIN_BACAK_USD
    # madde 161: rezerv ayrılınca TABAN bacak küçülür; hesaba katılmazsa
    # bot bacakları %25 büyük sanar ve minimum emir sınırına takılan
    # bacaklar SESSİZCE açılmaz (her eksik bacak yıllık ~3 puan, madde 160).
    n = int(dilim * GROSS_EXPOSURE * taban_pay() / max(MIN_BACAK_USD, 1e-9))
    # MADDE 341: BACAK TAVANI. Bacak sayısını bakiyeyle büyütmek İKİ şeyi
    # birden yapar (madde 326'nın iki-kanal yasası): bacak sayısı artar VE
    # bacak büyüklüğü küçülür, yani EVREN daralır. İki kanal ayrı ölçüldü:
    #   kanal A (bacak 4 sabit, evren D8->D2): DÖRT ŞART DA GEÇTİ,
    #           eşit risk +21,3 (hiza 0) / +38,1 (hiza 1) puan, kaldıraç YOK
    #   kanal B (evren D8 sabit, bacak 4->5): şart 1 DÜŞTÜ (25-26 -0,050)
    #           ve eşit risk için 1,36x kaldıraç ister
    # Üstüne 5 bacak her evren basamağını ~%25 daha fazla sermayeye iter:
    #   evren   4 bacak tavanı   5 bacak (eski)
    #   D7         2.576 $          3.219 $
    #   D2         3.000 $          3.750 $     <- kazancın %95'i burada
    #   D1         3.564 $          4.455 $
    # 2.812 $'da eski kural 5'e çıkıyor ve bacak 15,00 $'a düşüp evren
    # D8'de KALIYOR - yani D2 hiç gelmiyor. Tavan bunu engeller.
    # 2.000 $'da davranış DEĞİŞMEZ (zaten 4); tavan sermaye gelince işler.
    return min(N_LEGS, BACAK_TAVAN, max(MIN_LEGS, n))


ASGARI_BACAK_CARPANI = float(os.getenv("CARRY_ASGARI_CARPAN", "2.0"))
"""Bacak, borsanın minimum emrinin (MIN_NOTIONAL_USD) kaç katı olmalı ki
tur çalıştırılsın (madde 204). Fiyat hareketi ve miktar yuvarlaması için
güvenlik payı."""


def bakiye_yeterli_mi(bakiye: float, n_legs: int, olcek: float = 1.0) -> tuple[bool, float]:
    """Bakiye, `n_legs` bacaklı bir dilim kurmaya yetiyor mu? (madde 204)

    Döner: (yeterli_mi, hesaplanan_bacak_usd)

    NEDEN: `uygun_bacak_sayisi` bacak sayısını MIN_LEGS'in altına
    indirmiyor. Bakiye çok küçükse bacak MIN_NOTIONAL_USD'nin altında
    kalıyor, borsa emri reddediyor ve bot SESSİZCE hiç işlem açmıyordu.
    Bu kontrol o durumu turun başında yakalar.
    """
    dilim = max(0.0, bakiye) * max(0.0, olcek) / max(1, N_DILIM)
    bacak = dilim * GROSS_EXPOSURE * taban_pay() / max(1, n_legs)
    return bacak >= MIN_NOTIONAL_USD * ASGARI_BACAK_CARPANI, bacak


def islem_yapilabilir(client: ExchangeClient, semboller: list,
                      bacak_usd: float) -> list:
    """Bacak büyüklüğüyle GERÇEKTEN emir açılabilecek sembolleri süzer.

    İki sınır var ve ikisi de sessizce portföyü bozar:
      1. minNotional  - emrin USD değeri bu değerin altındaysa reddedilir
      2. stepSize     - miktar bu adımın katı olmalı; yüksek fiyatlı
                        coinlerde en küçük adım büyük bir USD tutarına
                        denk gelir (BTC ~100$, SOL ~150$)

    Bu süzme SEÇİM aşamasında yapılır, emir aşamasında değil - böylece
    portföy eksik değil, sadece daha dar bir evrenle DENGELİ kurulur.
    """
    try:
        bilgi = client.client.futures_exchange_info()
    except Exception as e:
        logger.warning("exchange_info alınamadı (%s) - süzme atlanıyor", e)
        return semboller
    fiyatlar = {}
    try:
        for t in client.client.futures_ticker():
            fiyatlar[t["symbol"]] = float(t.get("lastPrice") or 0)
    except Exception:
        pass
    uygun, elenen = [], []
    for s in bilgi.get("symbols", []):
        ad = s.get("symbol")
        if ad not in semboller:
            continue
        min_notional, step = 5.0, 0.0
        for f in s.get("filters", []):
            if f.get("filterType") == "MIN_NOTIONAL":
                min_notional = float(f.get("notional", f.get("minNotional", 5)))
            elif f.get("filterType") == "LOT_SIZE":
                step = float(f.get("stepSize", 0))
        fiyat = fiyatlar.get(ad, 0.0)
        adim_usd = step * fiyat if (step > 0 and fiyat > 0) else 0.0
        gerekli = max(min_notional, adim_usd)
        if bacak_usd >= gerekli > 0:
            uygun.append(ad)
        elif gerekli > 0:
            elenen.append((ad, gerekli))
    if elenen:
        elenen.sort(key=lambda x: -x[1])
        ornek = ", ".join(f"{a}({g:.0f}$)" for a, g in elenen[:5])
        logger.info("bacak %.1f$ ile açılamayan %d sembol elendi: %s%s",
                    bacak_usd, len(elenen), ornek,
                    " ..." if len(elenen) > 5 else "")
    return uygun if uygun else semboller


def yetim_dilimleri_ele(durum: dict) -> list[str]:
    """`N_DILIM`den BÜYÜK numaralı dilimleri durumdan çıkarır (madde 206).

    NEDEN: dilim sırası `sira % N_DILIM` ile döner. Kullanıcı N_DILIM'i
    DÜŞÜRÜRSE (örneğin madde 204'ün önerisiyle 15 → 5), eski durumdaki
    5..14 numaralı dilimlerin sırası BİR DAHA ASLA gelmez. Hedefleri
    `toplam_hedef` tarafından sonsuza kadar toplanmaya devam eder:
    kitabın 10/15'i (=%67) donmuş, aylar önceki sinyalle kurulmuş
    pozisyonda kalır - yenilenmez, çıkılmaz, yeniden sıralanmaz.

    Çözüm: yetim dilimi durumdan SİL. Hedefi kaybolduğu için bot bir
    sonraki turda o pozisyonları normal yolla KAPATIR (mevcut var,
    hedef yok -> kapatma emri).

    Döner: elenen dilim anahtarları.
    """
    dilimler = durum.get("dilimler") or {}
    yetim = []
    for k in list(dilimler):
        try:
            n = int(k)
        except (TypeError, ValueError):
            yetim.append(k); continue
        if n >= N_DILIM or n < 0:
            yetim.append(k)
    if not yetim:
        return []
    atilan_sembol = set()
    for k in yetim:
        atilan_sembol.update((dilimler.pop(k, {}) or {}).keys())
        (durum.get("dilim_bakiye") or {}).pop(k, None)
    # giriş funding kaydı: başka dilimde de duran sembolü SİLME
    kalan = set()
    for h in dilimler.values():
        kalan.update(h.keys())
    gf = durum.get("giris_funding") or {}
    for sem in atilan_sembol - kalan:
        gf.pop(sem, None)
    durum["sira"] = int(durum.get("sira", 0)) % max(1, N_DILIM)
    logger.warning(
        "YETİM DİLİM temizliği: %d dilim (%s) N_DILIM=%d'in üstünde kaldığı "
        "için silindi - sırası bir daha gelmeyecekti ve pozisyonları "
        "sonsuza kadar donmuş kalacaktı (madde 206). Bu dilimlerin "
        "pozisyonları bu turda KAPATILACAK: %s",
        len(yetim), ", ".join(sorted(yetim, key=lambda x: str(x))), N_DILIM,
        ", ".join(sorted(atilan_sembol - kalan)[:8]) or "(yok)")
    return yetim


def dilim_durum_oku(dosya: str = None) -> dict:
    """Dilimlerin son hedeflerini ve sıradaki dilim numarasını okur."""
    yol = dosya or DILIM_DURUM_DOSYA
    try:
        if os.path.exists(yol):
            with open(yol, encoding="utf-8") as fh:
                d = json.load(fh)
            if isinstance(d, dict) and "dilimler" in d:
                yetim_dilimleri_ele(d)     # madde 206
                return d
    except (OSError, ValueError) as e:
        logger.warning("dilim durumu okunamadı (%s) - sıfırdan başlanıyor", e)
    return {"sira": 0, "dilimler": {}}


DURUM_KURTAR = os.getenv("CARRY_DURUM_KURTAR", "1") not in ("0", "false", "False")
"""Durum dosyası kaybolduğunda borsadaki pozisyonları SAHİPLEN (madde 207).

0 yapılırsa eski davranış: hedef boş olduğu için bot ilk turda kitabın
neredeyse tamamını TASFİYE eder."""


def durum_kurtar(durum: dict, mevcut: dict, bakiye: float) -> int:
    """Durum kaybolmuşsa borsadaki pozisyonları dilimlere DAĞITIR (madde 207).

    SORUN: durum dosyası silinirse (sunucu taşıma, disk temizliği, volume'suz
    konteyner yeniden başlatma) `dilimler` boş gelir. Bot o turda bir tek
    yeni dilim yazar; `toplam_hedef` sadece onu içerir; borsadaki diğer
    14 dilimlik pozisyon "hedefte yok" sayılıp **tek turda kapatılır.**
    Kitabın ~%93'ü tasfiye edilir, 5 günde yeniden kurulur: hem komisyon
    hem de 5 gün eksik maruziyet.

    ÇÖZÜM: mevcut pozisyonları BOŞ dilim slotlarına dağıt. Hedef =
    pozisyonun kendisi olduğu için o turda İŞLEM OLMAZ; her slot sırası
    geldikçe (5 gün içinde) normal yolla taze sinyalle değişir. Yani
    bilinmeyen yaşlı bir kitap, bir devir içinde normale döner.

    Döner: kurtarılan pozisyon sayısı.
    """
    if not DURUM_KURTAR or not mevcut:
        return 0
    if durum.get("dilimler"):
        return 0                      # durum yerinde, kurtarmaya gerek yok
    sira = int(durum.get("sira", 0)) % max(1, N_DILIM)
    # sıradaki slot TAZE dilime ayrılır; kalan slotlara dağıtılır
    slotlar = [str((sira + 1 + k) % max(1, N_DILIM))
               for k in range(max(1, N_DILIM) - 1)]
    if not slotlar:
        return 0
    kalem = sorted(mevcut.items(), key=lambda kv: -abs(kv[1]))
    dilimler = durum.setdefault("dilimler", {})
    bak = durum.setdefault("dilim_bakiye", {})
    for i, (sem, usd) in enumerate(kalem):
        if abs(usd) < MIN_NOTIONAL_USD:
            continue
        slot = slotlar[i % len(slotlar)]
        dilimler.setdefault(slot, {})[sem] = float(usd)
        bak[slot] = float(bakiye)
    logger.error(
        "DURUM DOSYASI KAYIP ama borsada %d pozisyon var. Bunlar %d dilim "
        "slotuna DAĞITILDI (madde 207) - bu turda işlem yapılmayacak, her "
        "slot sırası geldikçe 5 gün içinde taze sinyalle yenilenecek. "
        "Eski davranış kitabın ~%%%d'ini tek turda tasfiye ederdi. "
        "Durum dosyasının neden kaybolduğunu KONTROL EDİN (%s).",
        len(kalem), len(slotlar), int(100 * (N_DILIM - 1) / max(1, N_DILIM)),
        DILIM_DURUM_DOSYA)
    return len(kalem)


def dilim_durum_yaz(durum: dict, dosya: str = None) -> None:
    yol = dosya or DILIM_DURUM_DOSYA
    try:
        with open(yol, "w", encoding="utf-8") as fh:
            json.dump(durum, fh)
    except OSError as e:
        logger.warning("dilim durumu yazılamadı: %s", e)


DILIM_OLCEK_TAVAN = float(os.getenv("CARRY_DILIM_OLCEK_TAVAN", "1.5"))
"""Bayat dilim hedefi en fazla bu katsayıyla ölçeklenir (madde 205).
Bakiye çok hızlı düşerse ölçek patlamasın diye güvenlik sınırı."""


def toplam_hedef(durum: dict, bakiye: float | None = None) -> dict:
    """Tüm dilimlerin hedeflerini toplayarak portföy hedefini üretir.

    Aynı sembol birden fazla dilimde olabilir - USD tutarları toplanır.
    Zıt yönler birbirini götürür (bir dilim long, diğeri short ise net
    pozisyon küçülür) - bu DOĞRU davranıştır, fazla işlem yapılmaz.

    MADDE 205 — BAYAT HEDEF ÖLÇEKLEMESİ: dilim hedefleri MUTLAK USD
    olarak saklanıyor ve sadece sırası gelince (5 günde bir) yenileniyor.
    `bakiye` verilirse her dilimin hedefi, kurulduğu andaki bakiyeye göre
    ÖLÇEKLENİR - yani hedef, sermayenin sabit bir ORANI olarak korunur.

    NEDEN ÖNEMLİ: ölçeklemesiz hâlde bakiye düşerken 14 dilimin hedefi
    eski (yüksek) bakiyeden kalıyor, yani **brüt maruziyet düşüşte
    ARTIYOR** - negatif konvekslik. KÂR HARİTASI'nın "yapılmaması
    gerekenler" listesindeki "düşüşte kaldıraç artırmak" maddesinin
    sessiz hâli. Backtest ise ağırlığı sabit tutuyor, yani bu sapmayı
    hiç modellemiyor (madde 183 ailesinden bir parite farkı).

    `bakiye` verilmezse eski davranış (ölçeksiz) korunur.
    """
    top = {}
    kayit = durum.get("dilim_bakiye", {}) or {}
    for anahtar, hedef in durum.get("dilimler", {}).items():
        olcek = 1.0
        if bakiye is not None and bakiye > 0:
            eski = kayit.get(str(anahtar))
            try:
                eski = float(eski) if eski else 0.0
            except (TypeError, ValueError):
                eski = 0.0
            if eski > 0:
                olcek = min(DILIM_OLCEK_TAVAN, max(1.0 / DILIM_OLCEK_TAVAN,
                                                   bakiye / eski))
        for sembol, usd in hedef.items():
            top[sembol] = top.get(sembol, 0.0) + usd * olcek
    return {s: v for s, v in top.items() if abs(v) >= MIN_NOTIONAL_USD}


SOLMA_ORAN = float(os.getenv("CARRY_SOLMA", "0"))
"""Funding SOLDUĞUNDA erken çık: bacağın funding'i giriş seviyesinin bu
katının ALTINA inerse (ya da işaret değiştirirse) 5 günü beklemeden
kapatılır. 0 = kapalı.

MANTIK: bu strateji funding KİRASI toplar. Kira kesildiğinde elde
kalan sadece FİYAT RİSKİDİR - yani ödemesi bitmiş bir pozisyonu
taşımak, bedava risk taşımaktır.

Ölçüldü (madde 167, 12+12, 4s motor, maker):

  eşik      yıllık   Sharpe   düşüş    22-24 Sh   25-26 Sh
  kapalı    +46.8%    1.83    −31.1      1.44       2.30
  0.60      +51.2%    2.02    −33.3      1.39       2.77
  0.70      +48.2%    2.02    −32.0      1.47       2.70   <- varsayılan
  0.80      +45.2%    2.03    −32.1      1.38       2.85
  0.90      +39.0%    1.98    −28.4      1.25       2.90

DOĞRULAMALAR:
  - PLASEBO (aynı sıklıkta RASTGELE erken çıkış): Sharpe 1.78, +%29.3.
    Yani kazanç "daha kısa tutmak"tan değil, DOĞRU bacağı bırakmaktan
    geliyor.
  - TERS KURAL (funding GÜÇLENİNCE çık): −%1.8/yıl, Sharpe −0.58.
    Kural bilgi taşıyor.
  - Genel Sharpe 0.60-0.90 aralığının TAMAMINDA ~2.02 - sağlam.

VARSAYILAN 0 = KAPALI. ÇÜNKÜ TAM YAPILANDIRMADA GEÇERSİZ ÇIKTI:

Yukarıdaki tablo İNDİRGENMİŞ motorda (kalabalık seçimi ve fırsat
rezervi OLMADAN) ölçülmüştü. Kabul edilen TAM yapılandırmada tekrar
ölçüldü ve sonuç TERSİNE döndü:

  SOLMA     yıllık   Sharpe   düşüş    22-24 Sh   25-26 Sh
  0 (kapalı) +55.9%   2.24    −14.7      2.13       2.51
  0.60       +45.7%   2.13    −16.0      1.77       2.58
  0.70       +40.9%   2.07    −16.9      1.83       2.42
  0.80       +37.3%   2.05    −16.2      1.83       2.37

Her eşikte HEM getiri HEM Sharpe düşüyor, düşüş derinleşiyor.

SEBEBİ: indirgenmiş motorda kazandırmasının nedeni, o motorun zaten
zayıf olan bacak seçimini telafi etmesiydi. Kalabalık seçimi + fırsat
rezervi devredeyken portföy zaten doğru bacakları tutuyor; erken çıkış
sadece KÂRLI pozisyonları vaktinden önce kesiyor.

DERS: bir fikri indirgenmiş motorda ölçüp kabul etmek YETMİYOR. Kabul
kararı, canlıda çalışacak TAM yapılandırmada verilmeli. Bu madde 167'de
neredeyse yapılan hataydı; beklenti güncellenmediği için yakalandı.

Kod ve testler duruyor (kapalı bir seçenek olarak, bulguyu belgelemek
için). AÇMAYIN."""


def funding_soldu(durum: dict, funding: pd.Series) -> list:
    """Funding'i solmuş bacakları dilim hedeflerinden ÇIKARIR (madde 167).

    Giriş anındaki funding `durum["giris_funding"]` içinde tutulur.
    Çıkarılan sembollerin listesi döner; hedeften düştükleri için
    normal emir mekanizması onları KAPATIR.
    """
    if SOLMA_ORAN <= 0 or funding is None or funding.empty:
        return []
    giris = durum.get("giris_funding", {})
    solan = []
    for ad, hedef in durum.get("dilimler", {}).items():
        for sembol in list(hedef):
            g0 = giris.get(sembol)
            simdi = funding.get(sembol)
            if g0 is None or simdi is None or not np.isfinite(simdi) or not g0:
                continue          # bilgi yoksa DOKUNMA (sessizce kapatma yok)
            if abs(simdi) < SOLMA_ORAN * abs(g0) or (simdi > 0) != (g0 > 0):
                hedef.pop(sembol, None)
                solan.append(sembol)
    for s in solan:
        if not any(s in h for h in durum.get("dilimler", {}).values()):
            durum.get("giris_funding", {}).pop(s, None)
    return solan


def giris_funding_yaz(durum: dict, yeni_dilim: dict, funding: pd.Series) -> None:
    """Yeni açılan bacakların GİRİŞ funding'ini kaydeder (madde 167)."""
    if SOLMA_ORAN <= 0 or funding is None:
        return
    g = durum.setdefault("giris_funding", {})
    for sembol in yeni_dilim:
        v = funding.get(sembol)
        if v is not None and np.isfinite(v):
            g[sembol] = float(v)


TRADFI_HARIC = os.getenv("CARRY_TRADFI_HARIC", "1") not in ("0", "false", "False")
"""Hisse / ETF / emtia perp'leri evrenden çıkarılsın mı? (madde 142)

Binance Aralık 2025'ten itibaren yüzlerce TradFi perp listeledi (altın,
petrol, Tesla, Nvidia, S&P, Kore/HK hisseleri...). Bunlarda kriptodaki
gibi kalabalık kaldıraçlı spekülatör yok, dolayısıyla FUNDING PRİMİ YOK:
backtest'te işlem gören 17 TradFi sembolün toplam funding katkısı
+198 USD (net -1.812 USD). Bot yine de 12 koltuğu doldurmak için onları
seçiyordu - son rebalance'ta long bacağın YARISI hisseydi.

Ölçüldü (5 dilim, temiz panel):
                        TradFi dahil            TradFi hariç
  tüm dönem           +30.3%  Sh 1.25  -27.7%   +34.1%  Sh 1.36  -27.7%
  2026 (var oldukları) +64.5%  Sh 1.57  -19.1%   +95.2%  Sh 2.00  -17.6%

Tespit: exchange_info'da contractType == "TRADIFI_PERPETUAL" ya da
underlyingType EQUITY / COMMODITY / ... (bkz. _TRADFI_TIPLERI). Bilgi
alınamazsa aşağıdaki YEDEK isim listesi kullanılır."""

_TRADFI_TIPLERI = {"EQUITY", "CN_EQUITY", "KR_EQUITY", "HK_EQUITY",
                   "PREMARKET", "COMMODITY"}

_TRADFI_YEDEK = set(s + "USDT" for s in """
AAOI AAPL ADBE ALAB AMAT AMD AMZN ANTHROPIC APP ARM ASML ASTS AVGO
AXTI BABA BE BITO BMNR BRKB BX BZ CAT CBRS CIEN CL COHR COIN COPPER
COST CRCL CRDO CRM CRWD CRWV CSCO CSOPSAMSUNG2L CSOPSKHYNIX2L CXMT
DELL DIS DKNG DRAM EBAY EWJ EWT EWY EWZ FLEX FLNC GDX GEV GLW GME
GOOGL GS HANMI HD HIMS HK0700 HK1810 HOOD HPE HYUNDAI IBM INTC IREN
IWM JPM KLAC KO KODEX200 KORU KUAISHOU LGELECTRONICS LITE LLY LRCX
MEITUAN META MINIMAX MRVL MSFT MSTR MU NATGAS NAVER NBIS NET NFLX
NOK NOW NVDA NVO ONDS OPENAI ORCL PANW PAYP PLTR POPMART PYPL QCOM
QQQ RDDT RIVN RKLB SAMSUNG SAMSUNGEM SHOP SKHY SKHYNIX SMCI SMH
SNDK SNOW SOFI SONY SOXL SOXS SPCX SPY SQQQ STRC TBT TENCENT TER
TMF TQQQ TSLA TSM TTWO TXN TZA UBER UNITREE URNM UVXY VRT VST WDC
WMT XAG XAU XAUT XBI XLE XPD XPT ZHIPU ZM
""".split())
"""exchange_info alınamadığında kullanılan yedek liste (2026-08 itibarıyla
arşivde görülen TradFi perp'ler). Yeni listelemeleri KAPSAMAZ - asıl
tespit exchange_info alanlarıyla yapılır."""


def tradfi_mi(sembol: str, bilgi: dict | None) -> bool:
    """Sembol bir hisse/ETF/emtia perp'i mi? bilgi = exchange_info satırı."""
    if bilgi:
        if bilgi.get("contractType") == "TRADIFI_PERPETUAL":
            return True
        if str(bilgi.get("underlyingType", "")).upper() in _TRADFI_TIPLERI:
            return True
        if bilgi.get("underlyingType") or bilgi.get("contractType"):
            return False          # alanlar var ve kripto diyor
    return sembol in _TRADFI_YEDEK


# madde 146: delisti DUYURULMUŞ sembol yeni seçime girmez. Binance
# duyuruda perp'in deliveryDate alanını (normalde 2100 yılı) delist
# zamanına çeker; status de TRADING'den çıkar. Açık pozisyon ZORLA
# KAPATILMAZ - backtest'te duyuruda kapatmak Sharpe'ı düşürdü
# (delist olan coinlerde long bacak yüksek funding topluyor). Filtre
# sadece reddedilecek açılış emirlerini ve boş kalan bacağı önler.
DELIST_UFUK_GUN = float(os.getenv("CARRY_DELIST_UFUK_GUN", "30"))


def delist_mi(bilgi: dict | None, simdi_ms: float = None) -> bool:
    """exchange_info satırına göre sembol kapanıyor/kapanacak mı?
    Bilgi yoksa False (veri eksikliği cezalandırılmaz)."""
    if not bilgi:
        return False
    st = str(bilgi.get("status", "TRADING") or "TRADING").upper()
    if st != "TRADING":
        return True
    dd = bilgi.get("deliveryDate")
    if dd and str(bilgi.get("contractType", "PERPETUAL")).upper() in ("PERPETUAL", "TRADIFI_PERPETUAL"):
        try:
            dd = float(dd)
        except (TypeError, ValueError):
            return False
        if simdi_ms is None:
            simdi_ms = time.time() * 1000.0
        if dd - simdi_ms < DELIST_UFUK_GUN * 86400000.0:
            return True
    return False


def sembol_bilgisi(client: ExchangeClient) -> dict[str, dict]:
    """exchange_info'yu TEK sefer çekip sembol -> satır sözlüğü döner."""
    try:
        bilgi = client.client.futures_exchange_info()
    except Exception as e:
        logger.warning("exchange_info alınamadı (%s) - yaş filtresi "
                       "UYGULANAMIYOR, TradFi tespiti YEDEK listeyle", e)
        return {}
    return {s["symbol"]: s for s in bilgi.get("symbols", []) if "symbol" in s}


def listeleme_yaslari(client: ExchangeClient, bilgi: dict = None) -> dict[str, float]:
    """Sembol -> listelemeden bu yana geçen GÜN sayısı.

    Binance `futures_exchange_info` içinde `onboardDate` verir (ms).
    Alınamazsa boş sözlük döner ve yaş filtresi sessizce DEVRE DIŞI
    kalır - bu bilinçli bir seçim: filtre uygulanamıyorsa botu
    durdurmak yerine eski davranışa düşer, ama uyarı yazar."""
    if bilgi is None:
        bilgi = sembol_bilgisi(client)
    simdi = time.time() * 1000.0
    out = {}
    for s in bilgi.values():
        ob = s.get("onboardDate")
        if not ob:
            continue
        try:
            out[s["symbol"]] = (simdi - float(ob)) / 86400000.0
        except (TypeError, ValueError):
            continue
    return out


SON_24S_DEGISIM: dict[str, float] = {}
"""Madde 196: `evren_sec` her çağrıldığında `futures_ticker`'dan gelen
24 saatlik yüzde değişim buraya yazılır (sembol -> oran)."""


def evren_sec(client: ExchangeClient) -> list[str]:
    """Likidite VE listelenme yaşı filtresinden geçen evreni kurar.

    İki filtre de madde 133'te ölçüldü; tam evrende (delist edilmişler
    dahil) carry'yi eksiden artıya geçiren şey bu ikisidir."""
    try:
        tickers = client.client.futures_ticker()
    except Exception as e:
        logger.error("ticker listesi alınamadı: %s", e)
        return []
    bilgi = sembol_bilgisi(client)
    yaslar = listeleme_yaslari(client, bilgi) if MIN_LISTELEME_GUN > 0 else {}
    uygun = []
    elenen_hacim = elenen_yas = elenen_tradfi = elenen_delist = 0
    for t in tickers:
        s = t["symbol"]
        if not s.endswith("USDT") or "_" in s:
            continue
        if s in ("BTCDOMUSDT", "BTCSTUSDT"):
            continue
        try:
            hacim = float(t["quoteVolume"])
        except (KeyError, ValueError):
            continue
        try:    # madde 196: 24 saatlik degisim - ayni cagridan, bedava
            SON_24S_DEGISIM[s] = float(t["priceChangePercent"]) / 100.0
        except (KeyError, TypeError, ValueError):
            SON_24S_DEGISIM.pop(s, None)
        if hacim < MIN_DAILY_VOLUME_USD:
            elenen_hacim += 1
            continue
        if delist_mi(bilgi.get(s)):
            elenen_delist += 1
            continue
        if TRADFI_HARIC and tradfi_mi(s, bilgi.get(s)):
            elenen_tradfi += 1
            continue
        # yaş bilgisi YOKSA eleme - veri eksikliği cezalandırılmaz
        if MIN_LISTELEME_GUN > 0 and s in yaslar and yaslar[s] < MIN_LISTELEME_GUN:
            elenen_yas += 1
            continue
        uygun.append((s, hacim))
    uygun.sort(key=lambda x: x[1], reverse=True)
    logger.info("evren: %d sembol (hacim filtresi %d eledi, yaş %d, TradFi %d, delist %d)",
                len(uygun), elenen_hacim, elenen_yas, elenen_tradfi, elenen_delist)
    if len(uygun) < 2 * MIN_LEGS:
        logger.warning("evren çok dar (%d sembol) - CARRY_MIN_VOLUME "
                       "düşürülmeli mi kontrol edin", len(uygun))
    return [s for s, _ in uygun[:MAX_SYMBOLS]]


# ------------------------------------------------------------- HEDEF PORTFÖY
def rezerv_agirlik(uzun: list, kisa: list, ham_funding: pd.Series) -> tuple[dict, dict]:
    """Uç funding'li long adaylara EK pay, karşılığı short bacaklara (madde 156).

    Döner: (ek_long, ek_short) - sembol -> kitap payı (brüt 1.0 üzerinden).
    Uç aday yoksa boş sözlükler döner: rezerv kullanılmaz, sermaye boş kalır."""
    if REZERV_PAY <= 0 or ham_funding is None or not uzun or not kisa:
        return {}, {}
    uc = [s for s in uzun
          if s in ham_funding.index and np.isfinite(ham_funding[s])
          and ham_funding[s] <= -REZERV_ESIK_YILLIK]
    if not uc:
        return {}, {}
    pay = (REZERV_PAY / 2) / len(uc)
    if REZERV_COIN_KAP > 0:
        pay = min(pay, REZERV_COIN_KAP)
    toplam = pay * len(uc)
    return ({s: pay for s in uc}, {s: toplam / len(kisa) for s in kisa})


def hedef_portfoy(funding: pd.Series, bakiye: float,
                  n_legs: int = None, kalabalik: pd.Series = None,
                  ham_funding: pd.Series = None) -> dict[str, float]:
    """Funding sıralamasından hedef pozisyonları (USD, işaretli) üretir.

    funding YÜKSEK -> SHORT (funding alırız)
    funding DÜŞÜK/NEGATİF -> LONG (funding alırız)
    """
    f = funding.dropna()
    # DAYANIKLILIK (madde 123): sembol sayısı yetersizse tamamen durmak
    # yerine bacak sayısını küçült. Canlıda bazı sembollerin funding
    # verisi gelmeyebilir veya likidite filtresinden az sembol geçebilir;
    # o durumda bot HİÇ işlem yapmazdı - sessiz bir duruş.
    n = N_LEGS if n_legs is None else min(N_LEGS, max(MIN_LEGS, int(n_legs)))
    if len(f) < 2 * n:
        n = len(f) // 2
        if n < MIN_LEGS:
            logger.warning("yeterli sembol yok (%d) - %d+%d bacak bile "
                           "kurulamıyor, tur atlanıyor", len(f), MIN_LEGS, MIN_LEGS)
            return {}
        logger.warning("sadece %d sembol var - bacak sayısı %d'ye "
                       "düşürüldü (portföy daha yoğun, risk daha yüksek)",
                       len(f), n)
    sirali = f.sort_values()
    bacak_usd = (bakiye * GROSS_EXPOSURE / 2) / n
    if kalabalik is not None and KALABALIK_HAVUZ > 1 and len(kalabalik) > 0:
        # madde 148: aday havuzundan kalabalık olanları seç
        la, sa = kalabalik_adaylar(f, n)
        uzun = kalabalik_sec(la, kalabalik, n, +1)
        kisa = kalabalik_sec(sa, kalabalik, n, -1)
    else:
        uzun = list(sirali.index[:n])          # en düşük funding -> LONG
        kisa = list(sirali.index[-n:])         # en yüksek funding -> SHORT
    ek_l, ek_s = rezerv_agirlik(uzun, kisa, ham_funding)
    # rezerv ayrılınca taban bacaklar küçülür; uç adaylara EK pay eklenir
    taban = taban_pay()
    kitap = bakiye * GROSS_EXPOSURE
    hedef = {}
    for s in uzun:
        hedef[s] = kitap * (taban / n + ek_l.get(s, 0.0))
    for s in kisa:
        hedef[s] = -kitap * (taban / n + ek_s.get(s, 0.0))
    if ek_l:
        logger.info("REZERV devrede: %d uç coin (%s), coin başına +%%%.1f",
                    len(ek_l), ", ".join(sorted(ek_l)), 100 * next(iter(ek_l.values())))
    return hedef


TP_DEFTER_DOSYA = os.getenv("CARRY_TP_DEFTER",
                            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "carry_tp.csv"))
"""Kâr al DOLUMLARININ defteri (madde 216). Satır: zaman,sembol,taraf.

NEDEN: madde 214 kârın TAMAMININ kâr-al hasadından geldiğini gösterdi
(funding +109,8 ve ham fiyat -108,0 birbirini götürüyor, TP +210,5). Yani
TP ULAŞMA ORANI, kâr motorunun en doğrudan canlı göstergesi - ve hiç
izlenmiyordu.

MADDE 290 — YUKARIDAKİ "TAMAMI" YANLIŞ, AMA BU DEFTER YİNE GEREKLİ.
Hasat GERÇEKTEN kapatıldığında (`TP=0 TPL=0 TPS=0`; bileşen muhasebesinde
"SHORT/LONG kar-al fiyat +0.0" ile doğrulandı) kitap **+%93,4 / Sharpe
2,33 / düşüş −20,6** kazanıyor ve **ham fiyat −98,7 yerine +64,9** oluyor.
Yani götürme bir MUHASEBE ARTEFAKTI: kâr-al lehte hareketleri erken
çıkarıp kendi kovasına yazıyor, 5 günlük normal çıkışa SADECE aleyhte
olanlar kalıyor - "bacak fiyat" kovasının negatifliği bir SEÇİLİM
sonucudur, ekonomik bir maliyet değil. Hasadın GERÇEK katkısı: **+18,9
CAGR puanı, +0,77 Sharpe, −6,1 puan düşüş** = kârın %16,8'i ve Sharpe'ın
dörtte biri. Madde 214'ün "funding bir SEÇİCİdir" kısmı AYAKTA.

Bu defterin gerekçesi değişmiyor, sadece ağırlığı: TP ulaşma oranı kârın
TAMAMINI değil altıda birini ve Sharpe'ın dörtte birini izliyor. Düşüşün
−6,1 puanı da ona bağlı olduğu için hâlâ en doğrudan göstergelerden biri.
YASA (madde 290): bir bileşen muhasebesi, bileşeni KAPATMADAN
yorumlanamaz - kovalar arasındaki işaretler çıkış zamanlamasının seçilim
etkisini taşır.

Madde 216'da gücü ölçüldü (plaseboya karşı, %5 seviyesinde):

  gözlem              etki/std   14 gün  30 gün  60 gün
  funding tahsilatı     0,891     %100    %100    %100
  TP oranı LONG         0,344      %72     %95    %100
  TP oranı SHORT        0,224      %42     %68     %91
  (toplam getiri)         —         —      %15      —     <- madde 151

BEKLENEN ORANLAR (madde 214, 54.000 bacak-tutması): LONG %8,8 (eşik %40),
SHORT %18,1 (eşik %20). `carry_izleme.py` bu defteri okuyup karşılaştırır."""

BEKLENEN_TP_LONG = 0.088
BEKLENEN_TP_SHORT = 0.181
"""Madde 214'te ölçülen TP ulaşma oranları - `carry_izleme` kıyası için."""


TP_KURULUM_DOSYA = os.getenv(
    "CARRY_TP_KURULUM",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "carry_tp_kurulum.csv"))
"""Kâr al emirlerinin KONULMA defteri (madde 292). Satır:
zaman,hedeflenen,kurulan,basarisiz.

NEDEN — MADDE 292'NİN TEK GERÇEK BULGUSU. `carry_tp.csv` TP'lerin
DOLDUĞUNU sayıyor; hiç kimse KONULDUĞUNU saymıyordu. `kar_al_kur`
tek tek emir hatalarını yalnızca `logger.warning` ile geçiyor, dönüş
değeri (`kurulan`) çağrıldığı yerde ATILIYOR ve açık pozisyon sayısıyla
hiç kıyaslanmıyordu. Yani 50 pozisyonun 10'una TP konulamazsa bot
sessizce devam ediyordu.

BEDELİ ÖLÇÜLÜ: madde 290'a göre kâr-al hasadı **+18,9 CAGR puanı ve
−6,1 puan düşüş** değerinde. Konulamayan her TP, o bacağın hasat
payını götürür.

VE DAHA KÖTÜSÜ YANLIŞ TEŞHİS: `carry_izleme.py` düşük TP dolumunu
görünce "**kâr motoru çalışmıyor olabilir**" diyor - yani 291 maddelik
stratejiyi şüpheli ilan ediyor. Oysa aynı belirtiyi hiç KONULMAMIŞ
emirler de üretir. Madde 286'nın yasası ("ölçemedim ile ölçtüm-şüpheli
AYRI kodlar olmalı") canlı yüzeyde ihlal ediliyordu: bir API hatası,
bir piyasa bulgusu gibi görünüyordu. Bu defter iki sebebi ayırır."""


def _tp_kurulum_kaydet(hedeflenen: int, kurulan: int, basarisiz: int) -> None:
    """Kâr al KONMA sonucunu deftere yazar (madde 292).

    Hata sessizce geçilir - defter bir ölçüm aracı, botu durdurmamalı."""
    try:
        with open(TP_KURULUM_DOSYA, "a", encoding="utf-8") as fh:
            fh.write(f"{time.time():.0f},{hedeflenen},{kurulan},{basarisiz}\n")
    except OSError as e:
        logger.warning("TP kurulum defterine yazılamadı: %s", e)


def tp_kurulum_oku(dosya: str = None, gun: float = 30.0) -> dict:
    """Son `gun` gündeki TP KONMA istatistiği (madde 292).

    Döner: {"tur": ÖLÇÜLEBİLEN tur sayısı, "hedeflenen": ..., "kurulan": ...,
            "olculemedi": pozisyonların hiç okunamadığı tur sayısı,
            "oran": kurulan/hedeflenen (hedef 0 ise nan)}

    MADDE 286'NIN AYRIMI BURADA DA: `hedeflenen = -1` yazılan satır
    "pozisyonlar OKUNAMADI" demektir, "sıfır pozisyon vardı" demez. O
    satırlar orana KATILMAZ, ayrıca sayılır - yoksa toplamı bozar ve
    oran 1'in üstüne çıkabilirdi.
    """
    yol = dosya or TP_KURULUM_DOSYA
    esik = time.time() - gun * 86400.0
    tur = hedef = kurulan = olculemedi = 0
    try:
        with open(yol, "r", encoding="utf-8") as fh:
            for satir in fh:
                p = satir.strip().split(",")
                if len(p) < 3:
                    continue
                try:
                    t = float(p[0])
                    h = int(float(p[1]))
                    k = int(float(p[2]))
                except ValueError:
                    continue
                if t < esik:
                    continue
                if h < 0:
                    olculemedi += 1
                    continue
                tur += 1
                hedef += h
                kurulan += k
    except OSError:
        pass
    return {"tur": tur, "hedeflenen": hedef, "kurulan": kurulan,
            "olculemedi": olculemedi,
            "oran": (kurulan / hedef) if hedef > 0 else float("nan")}


def _tp_kaydet(sembol: str, emir_yonu: str) -> None:
    """Dolan kâr al emrini deftere yazar (madde 216).

    `emir_yonu` KÂR AL emrinin yönü: long pozisyonun TP'si SELL, short'un
    BUY. Yani bacağın tarafı TERSİ. Hata sessizce geçilir - defter bir
    ölçüm aracı, botu durdurmamalı."""
    try:
        taraf = "LONG" if emir_yonu == "SELL" else "SHORT"
        with open(TP_DEFTER_DOSYA, "a", encoding="utf-8") as fh:
            fh.write(f"{time.time():.0f},{sembol},{taraf}\n")
    except OSError as e:
        logger.warning("TP defterine yazılamadı: %s", e)


def tp_defteri_oku(dosya: str = None, gun: float = 30.0) -> dict:
    """Son `gun` gündeki TP dolumlarını sayar. {'LONG': n, 'SHORT': n}."""
    dosya = dosya or TP_DEFTER_DOSYA
    out = {"LONG": 0, "SHORT": 0}
    kes = time.time() - gun * 86400.0
    try:
        with open(dosya, encoding="utf-8") as fh:
            for satir in fh:
                p = satir.strip().split(",")
                if len(p) < 3:
                    continue
                try:
                    if float(p[0]) < kes:
                        continue
                except ValueError:
                    continue
                if p[2] in out:
                    out[p[2]] += 1
    except OSError:
        pass
    return out


def felaket_emri_gonder(client: ExchangeClient, sem: str, adet: float, tetik: str,
                        yon: str = "BUY"):
    """Koruyucu STOP_MARKET (short için BUY +%X, long için SELL −%X). algoId döner.

    Binance 2025-12-09'dan beri koşullu emirleri (STOP_MARKET vb.) normal
    `/fapi/v1/order` uç noktasında REDDEDİYOR (-4120); `/fapi/v1/algoOrder`
    (algoType=CONDITIONAL, triggerPrice) kullanılmalı. python-binance
    >= 1.0.37 `futures_create_algo_order` sağlar; yoksa açık hata verilir
    (sessizce sigortasız kalmak yerine)."""
    f = getattr(client.client, "futures_create_algo_order", None)
    if f is None:
        raise RuntimeError("python-binance eski: futures_create_algo_order yok "
                           "(pip install -U python-binance)")
    e = f(algoType="CONDITIONAL", symbol=sem, side=yon, type="STOP_MARKET",
          triggerPrice=tetik, quantity=adet, reduceOnly="true",
          workingType="MARK_PRICE")
    return e.get("algoId")


def long_24s_referans(client: ExchangeClient, sem: str) -> float | None:
    """24 sa önceki 4 sa kapanış (madde 453). Son kline açık bar; son kapanmış
    bar [-2]; motorun cv[i-5]'i ile aynı hiza için [-7]. Okunamazsa None."""
    try:
        k = client.client.futures_klines(symbol=sem, interval="4h", limit=8)
        if len(k) >= 7:
            v = float(k[-7][4])
            return v if v > 0 else None
    except Exception as ex:
        logger.warning("24 sa referans fiyatı okunamadı %s: %s", sem, ex)
    return None


def felaket_simdi_kapat(client: ExchangeClient, durum: dict, sem: str, adet: float) -> None:
    """Fiyat stop seviyesini turlar arasında geçmişse long'u hemen kapatır ve
    sembolü dilimlerden çıkarır (yeniden açılmasın)."""
    try:
        client.close_position(sem, "SELL", adet)
        for hedef in durum.get("dilimler", {}).values():
            hedef.pop(sem, None)
        logger.error("24 SA DÜŞÜŞ STOP'U: %s seviyenin altında bulundu - long piyasa "
                     "emriyle kapatıldı, dilimlerden çıkarıldı", sem)
    except Exception as ex:
        logger.error("24 SA DÜŞÜŞ STOP'U: %s seviyenin altında ama KAPATILAMADI (%s)", sem, ex)


def felaket_tetiklendi_mi(e: dict) -> bool:
    """Algo emri tetiklendi mi: tetiklenince `actualOrderId` dolar (piyasa
    emri olduğu için tetik = dolum)."""
    if str(e.get("actualOrderId") or "").strip() not in ("", "0"):
        return True
    return str(e.get("algoStatus", "")).upper() in ("TRIGGERED", "FINISHED", "FILLED")


def koruma_acik() -> bool:
    """Kâr al veya short felaket stop'undan biri açık mı."""
    return KAR_AL_ORAN > 0 or KAR_AL_SHORT > 0 or SHORT_FELAKET > 0 or LONG_FELAKET > 0 or LONG_24S > 0


def kar_al_kontrol(client: ExchangeClient, durum: dict) -> list[str]:
    """Önceki turda konan kâr al emirlerinden DOLANLARI bulur ve o
    sembolleri tüm dilim hedeflerinden çıkarır. Dolan sembolleri döner.

    Emir durumu alınamazsa sembol dokunulmadan bırakılır (yanlışlıkla
    pozisyon silmektense bir tur beklemek güvenli)."""
    dolan = []
    for sem, oid in list(durum.get("kar_al", {}).items()):
        try:
            e = client.client.futures_get_order(symbol=sem, orderId=oid)
        except Exception as ex:
            logger.warning("kâr al durumu alınamadı %s: %s", sem, ex)
            continue
        if str(e.get("status", "")).upper() in ("FILLED", "PARTIALLY_FILLED"):
            dolan.append(sem)
            _tp_kaydet(sem, str(e.get("side", "")).upper())
            for hedef in durum.get("dilimler", {}).values():
                hedef.pop(sem, None)
    if dolan:
        logger.info("KÂR AL doldu: %s - eski dilimlerden çıkarıldı", ", ".join(dolan))
    felaket = []
    for sem, oid in list(durum.get("felaket", {}).items()):
        try:
            e = client.client.futures_get_algo_order(symbol=sem, algoId=oid)
        except Exception as ex:
            logger.warning("felaket stop durumu alınamadı %s: %s", sem, ex)
            continue
        if felaket_tetiklendi_mi(e):
            felaket.append(sem)
            for hedef in durum.get("dilimler", {}).values():
                hedef.pop(sem, None)
    if felaket:
        logger.error("FELAKET STOP'U DOLDU: %s - pozisyon kapandı, eski dilimlerden "
                     "çıkarıldı (short +%%%.0f / long −%%%.0f)", ", ".join(felaket),
                     SHORT_FELAKET * 100, LONG_FELAKET * 100)
    return dolan + felaket


def kar_al_iptal(client: ExchangeClient, durum: dict) -> None:
    """Kayıtlı tüm kâr al emirlerini iptal eder (hata sessizce geçilir:
    emir zaten dolmuş/iptal olmuş olabilir)."""
    for sem, oid in list(durum.get("kar_al", {}).items()):
        try:
            client.client.futures_cancel_order(symbol=sem, orderId=oid)
        except Exception:
            pass
    durum["kar_al"] = {}
    for sem, oid in list(durum.get("felaket", {}).items()):
        try:
            client.client.futures_cancel_algo_order(symbol=sem, algoId=oid)
        except Exception:
            pass
    durum["felaket"] = {}


def kar_al_kur(client: ExchangeClient, durum: dict) -> int:
    """Açık her pozisyona reduce-only kâr al limit emri koyar. Konan
    emir sayısını döner. Emir kimlikleri durum["kar_al"]'a yazılır.

    MADDE 292 — SESSİZ BAŞARISIZLIK KAPATILDI. Eskiden tek tek emir
    hataları yalnızca `logger.warning` ile geçiliyordu, dönüş değeri
    çağrıldığı yerde ATILIYORDU ve hiç kimse konan emir sayısını açık
    pozisyon sayısıyla kıyaslamıyordu. 50 pozisyonun 10'una TP
    konulamazsa bot sessizce devam ediyordu - oysa hasat madde 290'a
    göre **+18,9 CAGR puanı ve −6,1 puan düşüş** değerinde.

    Artık: başarısızlar BİR KEZ yeniden denenir, sonuç
    `carry_tp_kurulum.csv`'ye yazılır ve eksik kalırsa **ERROR**
    seviyesinde, sembol adlarıyla raporlanır."""
    if not koruma_acik():
        return 0
    kar_al_iptal(client, durum)
    try:
        pozisyonlar = list(client.get_open_positions())
    except Exception as ex:
        logger.error("kâr al: açık pozisyonlar OKUNAMADI (%s) - hiçbir TP "
                     "konulamadı, pozisyonlar korumasız", ex)
        _tp_kurulum_kaydet(-1, 0, -1)
        return 0

    def _felaket_koy(sem, giris, adet, pr, long_mu=False) -> None:
        """Felaket STOP_MARKET (reduceOnly, MARK). Hata kâr al'ı bozmaz ama
        ERROR olarak raporlanır: sigortasız pozisyon demektir.

        Long tetiği (madde 453): girişten −LONG_FELAKET ve/veya 24 sa önceki
        kapanıştan −LONG_24S; ikisi de açıksa YÜKSEK olan (önce vuran)."""
        try:
            if long_mu:
                _adaylar = []
                if LONG_FELAKET > 0:
                    _adaylar.append(giris * (1 - LONG_FELAKET))
                if LONG_24S > 0:
                    _ref = long_24s_referans(client, sem)
                    if _ref:
                        _adaylar.append(_ref * (1 - LONG_24S))
                if not _adaylar:
                    return
                _tetik = max(_adaylar)
                try:
                    _fiyat = float(client.client.futures_symbol_ticker(symbol=sem)["price"])
                except Exception:
                    _fiyat = None
                if _fiyat is not None and _fiyat <= _tetik:
                    # Çöküş turlar arasında seviyeyi zaten geçmiş: bekleyen stop
                    # hemen tetiklenir/reddedilir (-2021). Motor bu barda çıkardı.
                    felaket_simdi_kapat(client, durum, sem, adet)
                    return
            else:
                _tetik = giris * (1 + SHORT_FELAKET)
            durum.setdefault("felaket", {})[sem] = felaket_emri_gonder(
                client, sem, adet, f"{_tetik:.{pr.get('price_precision', 2)}f}",
                yon="SELL" if long_mu else "BUY")
        except Exception as ex:
            felaket_basarisiz[sem] = str(ex)[:80]

    felaket_basarisiz: dict = {}

    def _koy(p) -> tuple:
        """(sembol, kondu_mu, sebep). Hedef dışıysa sembol None döner."""
        try:
            sem = p["symbol"]
            miktar = float(p["positionAmt"])
            giris = float(p.get("entryPrice") or 0)
        except (KeyError, ValueError, TypeError):
            return (None, False, "pozisyon satırı okunamadı")
        if abs(miktar) < 1e-12 or giris <= 0:
            return (None, False, "boş pozisyon")
        if miktar > 0:
            yon, fiyat = "SELL", giris * (1 + KAR_AL_ORAN)
        else:
            yon, fiyat = "BUY", giris * (1 - KAR_AL_SHORT)
        try:
            pr = client.get_symbol_precision(sem)
            adet = round(abs(miktar), pr["quantity_precision"])
            if adet <= 0:
                return (None, False, "miktar hassasiyete yuvarlanınca 0")
            if miktar < 0 and SHORT_FELAKET > 0 and sem not in durum.get("felaket", {}):
                _felaket_koy(sem, giris, adet, pr)
            if miktar > 0 and (LONG_FELAKET > 0 or LONG_24S > 0) and sem not in durum.get("felaket", {}):
                _felaket_koy(sem, giris, adet, pr, long_mu=True)
            if (KAR_AL_ORAN if miktar > 0 else KAR_AL_SHORT) <= 0:
                return (sem, True, "")
            e = client.client.futures_create_order(
                symbol=sem, side=yon, type="LIMIT", timeInForce="GTC",
                quantity=adet, price=f"{fiyat:.{pr.get('price_precision', 2)}f}",
                reduceOnly=True)
            durum.setdefault("kar_al", {})[sem] = e.get("orderId")
            return (sem, True, "")
        except Exception as ex:
            return (sem, False, str(ex)[:80])

    kurulan = 0
    hedeflenen = 0
    basarisiz: dict = {}
    kalan = []
    for p in pozisyonlar:
        sem, ok, sebep = _koy(p)
        if sem is None:
            continue
        hedeflenen += 1
        if ok:
            kurulan += 1
        else:
            basarisiz[sem] = sebep
            kalan.append(p)
    # MADDE 292: TEK SEFERLİK YENİDEN DENEME. Hız sınırı, geçici 5xx ve
    # anlık hassasiyet hataları bir denemede geçer; kalıcı olanı görmek
    # için ikinciyi de kaydediyoruz.
    if kalan:
        time.sleep(0.5)
        for p in kalan:
            sem, ok, sebep = _koy(p)
            if sem is None:
                continue
            if ok:
                kurulan += 1
                basarisiz.pop(sem, None)
            else:
                basarisiz[sem] = sebep
    for sem in list(felaket_basarisiz):
        if sem in durum.get("felaket", {}):
            felaket_basarisiz.pop(sem)
    if felaket_basarisiz:
        logger.error("FELAKET STOP'U KONULAMADI: %d pozisyon SİGORTASIZ (%s). Sebep: %s",
                     len(felaket_basarisiz), ", ".join(sorted(felaket_basarisiz)[:8]),
                     "; ".join(f"{s}: {r}" for s, r in sorted(felaket_basarisiz.items())[:3]))
    if SHORT_FELAKET > 0 or LONG_FELAKET > 0:
        logger.info("%d pozisyona felaket stop'u kondu (short +%%%.0f / long %s)",
                    len(durum.get("felaket", {})), SHORT_FELAKET * 100,
                    f"−%{LONG_FELAKET * 100:.0f}" if LONG_FELAKET > 0 else "kapalı")
    _tp_kurulum_kaydet(hedeflenen, kurulan, len(basarisiz))
    if basarisiz:
        logger.error(
            "KÂR AL EMRİ KONULAMADI: %d/%d pozisyon KORUMASIZ (%s). Hasat "
            "madde 290'a göre +18,9 CAGR puanı ve −6,1 düşüş değerinde; bu "
            "bacaklar bu turda hasat ŞANSINI KAYBEDER. Sebepler: %s",
            len(basarisiz), hedeflenen, ", ".join(sorted(basarisiz)[:8]),
            "; ".join(f"{s}: {r}" for s, r in sorted(basarisiz.items())[:3]))
    logger.info("%d/%d pozisyona kâr al emri kondu (long %%%.0f / short %%%.0f)",
                kurulan, hedeflenen, KAR_AL_ORAN * 100, KAR_AL_SHORT * 100)
    return kurulan


def mevcut_portfoy(client: ExchangeClient) -> dict[str, float]:
    """Açık pozisyonları {sembol: işaretli USD} olarak döner.

    MADDE 164 - GÜNCEL DEĞER, giriş değeri DEĞİL. Eski kod pozisyonu
    `positionAmt * entryPrice` ile ölçüyordu; bu, pozisyonun AÇILDIĞI
    ANDAKİ dolar değeridir ve fiyat hareket ettikçe DEĞİŞMEZ.

    Sonucu şuydu: fiyat hareketiyle büyüyen bir bacağı bot hâlâ eski
    boyutunda sanıyor, hedefle farkı göremiyor ve KIRPMIYOR. Yükselen
    bir SHORT bacak sınırsız büyüyebiliyor (kâr al sadece kazananı
    kapatır, kaybedeni değil). Ölçüldü (indirgenmiş motor, 12+12):
    medyan brüt 0.99x ile normal görünürken TEK bir bacak özsermayenin
    %774'üne ulaşıyor ve hesap sıfırlanıyor (-%99.4).

    Backtest'te bu yok: orada pozisyon her bar sermayenin sabit oranı
    olarak tutulur. Güncel değer okunduğunda günlük tur bütün kitabı
    hedefe çeker ve parite geri gelir (+%46.8 Sh 1.82 vs backtest
    +%43.8 Sh 1.75).

    Öncelik: borsanın verdiği `notional` (işaretli) > markPrice ile
    hesap > son çare entryPrice.

    MADDE 211 - AYNI SEMBOLÜN SATIRLARI TOPLANIR, ÜZERİNE YAZILMAZ.
    Eskiden `out[sembol] = deger` idi. HEDGE (çift yönlü) pozisyon
    modunda Binance her sembol için İKİ satır döner (LONG ve SHORT);
    ikinci satır birincisini siliyordu, yani bot maruziyetini 2 kata
    kadar YANLIŞ ölçebiliyordu. Toplama, tek yönlü modda hiçbir şeyi
    değiştirmez (sembol başına tek satır).
    """
    out: dict[str, float] = {}
    for p in client.get_open_positions():
        try:
            miktar = float(p["positionAmt"])
            if abs(miktar) < 1e-12:
                continue
            sem = p["symbol"]
            nominal = p.get("notional")
            deger = None
            if nominal not in (None, "", 0, "0"):
                d = float(nominal)
                if d and (d > 0) == (miktar > 0):
                    deger = d
            if deger is None:
                fiyat = (float(p.get("markPrice") or 0)
                         or float(p.get("entryPrice") or 0))
                deger = miktar * fiyat
            out[sem] = out.get(sem, 0.0) + deger
        except (KeyError, ValueError, TypeError):
            continue
    return {s: v for s, v in out.items() if abs(v) > 1e-12}


def emirleri_hesapla(hedef: dict[str, float], mevcut: dict[str, float],
                     tolerans_usd: float) -> list[tuple[str, str, float]]:
    """(sembol, yön, usd_farkı) listesi. Küçük farklar atlanır.

    tolerans: gereksiz işlem maliyeti oluşturmamak için, hedeften bu
    kadar USD'den az sapan pozisyonlara dokunulmaz.

    MADDE 208 - AÇILIŞLAR TARAF DOKUMASIYLA SIRALANIR. Emirler tek tek,
    araya 0.2s uyku koyularak gönderilir; borsa bakımı ya da API hatası
    listenin ORTASINDA vurursa geri kalanı hiç gönderilmez ve eksik
    bacaklar 8 saat (120sa/15 dilim) öyle kalır. Eski sıralamada yeni
    açılışların hepsinde `mevcut=0` olduğu için iç sıra set-hash sırasıydı
    - yani tarafa göre KEYFİ. Ölçüldü (335 rebalance barı x 40 çekiliş,
    rastgele kesme noktası):

        sıralama            |net| ort   |net| max   8sa K/Z p1   en kötü
        keyfi (eski)          %2.01      %10.00      -%0.618    -%1.641
        dokuma (yeni)         %0.91       %2.50      -%0.520    -%0.868

    Dokumada liste NEREDE kesilirse kesilsin |net| en fazla BİR bacak
    kalır (max %2.50 = nn=4 olduğu barlardaki tek bacak). Piyasa nötrlüğü
    yarım turda da korunur. Kapanışlar önce kalır (marj boşalsın).
    """
    # MADDE 301: SIRA ARTIK BELIRLENIMLI.
    # Eskiden `set(...)` uzerinde donuluyor ve sonra YALNIZ buyukluge gore
    # siralaniyordu. Ama bu kitabin acilis bacaklari ESIT BUYUKLUKTE, yani
    # siralama tumuyle beraberlik: sira, Python'un SUREC BASINA rastgele
    # string hash tohumuna kaliyordu. Olculdu - ayni girdi, bes ayri
    # PYTHONHASHSEED, bes ayri sira:
    #     0 -> C0,C7,C2,C1,...   1 -> C4,C3,C2,C5,...   2 -> C8,C1,C2,C9,...
    # Canlida sonucu: tur yarida kesilirse (API hatasi, oran limiti, zaman
    # asimi) HANGI bacaklarin acildigi KEYFI olur; kitap madde 208'in
    # dokumasi sayesinde NOTR kalir ama sembol bilesimi her kosuda degisir,
    # yani canli davranis yeniden uretilemez ve bir arizanin ayni kosullarda
    # tekrarlanmasi imkansizdir. Entegrasyon takimi da bu yuzden ARA ARA
    # dusuyordu (madde 300'un kosusunda 11e/11f'teki uc test).
    # Cozum: her siralamaya SEMBOL ADI ikincil anahtar olarak eklendi.
    # Buyukluk sirasi DEGISMEDI (birincil anahtar ayni), yalniz beraberlikler
    # artik alfabetik kiriliyor.
    emirler = []
    for s in sorted(set(hedef) | set(mevcut)):
        h = hedef.get(s, 0.0)
        m = mevcut.get(s, 0.0)
        fark = h - m
        if abs(fark) < max(tolerans_usd, MIN_NOTIONAL_USD):
            continue
        emirler.append((s, "BUY" if fark > 0 else "SELL", abs(fark)))
    # Önce kapanışlar (marj boşalsın), sonra açılışlar
    kapanis = [e for e in emirler if abs(mevcut.get(e[0], 0.0)) > 0]
    acilis = [e for e in emirler if abs(mevcut.get(e[0], 0.0)) <= 0]
    kapanis.sort(key=lambda e: (-abs(mevcut.get(e[0], 0.0)), e[0]))
    # madde 208: açılışları taraflara ayır, büyükten küçüğe, sonra DOKU
    al = sorted([e for e in acilis if e[1] == "BUY"], key=lambda e: (-e[2], e[0]))
    sat = sorted([e for e in acilis if e[1] == "SELL"], key=lambda e: (-e[2], e[0]))
    dokuma = []
    for i in range(max(len(al), len(sat))):
        if i < len(al):
            dokuma.append(al[i])
        if i < len(sat):
            dokuma.append(sat[i])
    return kapanis + dokuma


# ----------------------------------------------------------------- ÇALIŞTIR
def sermaye_oku(client: ExchangeClient) -> float | None:
    """Botun sermayesi. None = güvenli değil, tur atlanmalı (madde 141)."""
    usdt = client.get_account_balance_usdt()
    if TEMINAT_MODU == "coklu":
        return client.get_account_equity_usd()
    try:
        toplam = client.get_account_equity_usd()
    except Exception:
        return usdt
    if toplam > 50.0 and usdt < 0.5 * toplam:
        logger.error("HESAPTA USDT DIŞI TEMİNAT VAR: USDT %.2f, toplam teminat "
                     "%.2f. Bot USDT modunda bu sermayeyi göremez ve pozisyonları "
                     "yanlış boyutlar. BFUSD/LDUSDT kullanıyorsanız "
                     "CARRY_TEMINAT_MODU=coklu ayarlayın. Tur ATLANIYOR.",
                     usdt, toplam)
        return None
    # madde 162: USDT modunda da ÖZSERMAYE (totalMarginBalance) kullanılır.
    # Cüzdan bakiyesi gerçekleşmemiş K/Z'yi İÇERMEZ: kârdayken bot olması
    # gerekenden küçük, ZARARDAYKEN büyük pozisyon açardı - yani düşüşte
    # riski artırırdı. Backtest her gün özsermaye üzerinden büyütüyor;
    # bu, canlı/backtest paritesinin bir parçası.
    if toplam > 0:
        if abs(toplam - usdt) > 0.02 * max(usdt, 1.0):
            logger.info("sermaye: cüzdan %.2f USDT, özsermaye %.2f USD "
                        "(gerçekleşmemiş K/Z dahil) - özsermaye kullanılıyor",
                        usdt, toplam)
        return toplam
    return usdt


def saglik_kontrol(client: ExchangeClient, semboller: list[str],
                   simdi_ms: int = None, dosya: str = None,
                   yaz: bool = True) -> tuple:
    """Edge sağlığını ölçer, kapı durumunu günceller (madde 139).

    Döner: (kapi_acik: bool, durum: str, gerekce: str)

    HATA DURUMUNDA AÇIK KALIR ve UYARI yazar. Bilinçli seçim: dedektörün
    kendi arızası botu sessizce durdurmamalı (madde 123 dersi). Ama bu,
    API hatalarında dedektörün devre dışı kalabileceği demektir - log'daki
    "sağlık ölçülemedi" satırları izlenmeli.
    """
    if SAGLIK_MODU == "kapali":
        return True, "KAPALI", "dedektör kapalı"
    yol = dosya or SAGLIK_DOSYA
    simdi = int(simdi_ms if simdi_ms is not None else time.time() * 1000)
    blok = REBALANCE_HOURS
    # MADDE 182: dedektörün sinyal penceresi botunkinden GENİŞ tutulur.
    # Bot 8 saatlik pencereyle SON ödemeyi seçiyor; ama dedektör GEÇMİŞ
    # blok zamanlarında aynı pencereyi uygularsa, ızgara hizalanmadığında
    # pencereye HİÇ ödeme düşmeyebilir ve dedektör "ISINMA"da takılır.
    # 12 saat, 8 saatlik bir sembolde her zaman >=1 ödeme içerir.
    # MADDE 185 DÜZELTMESİ: 12 saat YETMİYOR. `carry_saglik._yillik`
    # aralığı ölçebilmek için EN AZ İKİ ödeme ister; 8 saatlik ızgarada
    # 12 saatlik pencereye hizalamaya göre bazen tek ödeme düşüyordu ve
    # dedektör günün üçte birinde sessizce "ISINMA"da kalıyordu (kapı
    # açık, koruma YOK). 24 saat her hizalamada >=3 ödeme içerir.
    _sag_pencere = max(FUNDING_WINDOW_HOURS, 24.0)
    geri_saat = blok * (carry_saglik.PENCERE + 1) + max(_sag_pencere, 72.0) + 24
    bas = simdi - int(geri_saat * 3600000)
    gecmis = {}
    for i, s in enumerate(semboller):
        try:
            h = client.client.futures_funding_rate(symbol=s, startTime=bas,
                                                    endTime=simdi, limit=1000)
            gecmis[s] = [(int(k["fundingTime"]), float(k["fundingRate"]))
                         for k in h]
        except Exception as e:
            logger.warning("sağlık: %s funding geçmişi alınamadı: %s", s, e)
        if i % 20 == 19:
            time.sleep(0.5)
    try:
        ic, f, disp = carry_saglik.metrikleri_hesapla(
            gecmis, simdi, SAGLIK_GOLGE_BACAK, blok_saat=blok,
            sinyal_saat=_sag_pencere)
        durum, gerekce = carry_saglik.saglik_durumu(ic, f, disp)
    except Exception as e:
        logger.warning("sağlık ölçülemedi (%s) - kapı AÇIK varsayılıyor", e)
        return True, "HATA", str(e)

    try:
        with open(yol, encoding="utf-8") as fh:
            kapi = json.load(fh)
    except (OSError, ValueError):
        kapi = {}
    kapi = carry_saglik.kapi_guncelle_zamanli(kapi, durum, simdi, blok_saat=blok)
    if yaz:   # kuru çalışma kapıyı DEĞİŞTİRMEZ - test canlıyı etkilemesin
        try:
            with open(yol, "w", encoding="utf-8") as fh:
                json.dump(kapi, fh)
        except OSError as e:
            logger.warning("sağlık durumu yazılamadı: %s", e)

    if durum == "BOZUK":
        logger.warning("EDGE SAĞLIĞI BOZUK: %s", gerekce)
    elif durum == "ISINMA":
        logger.warning("sağlık ölçümü için geçmiş yetersiz: %s", gerekce)
    else:
        logger.info("edge sağlığı: %s", gerekce)
    if not kapi["acik"] and durum == "SAGLIKLI":
        kalan = (carry_saglik.TOPARLANMA * blok * 3600000.0
                 - (simdi - kapi["temiz_bas_ms"])) / 86400000.0
        logger.info("sağlık düzeldi - yeniden açılmaya %.1f gün", kalan)
    return bool(kapi["acik"]), durum, gerekce


def _olay_kilidi_var() -> bool:
    """Olay modülünün (carry_olay.py) pozisyonu açık mı? Madde 166.

    Açıksa ana tur ATLANIR: o birkaç dakika boyunca kitapta modülün
    geçici bacakları var; ana bot onları kendi pozisyonu sanıp kırpardı.
    Bayat kilit (süreç çökmüşse) yok sayılır, aksi halde ana bot
    sonsuza kadar bloke olurdu."""
    try:
        from carry_olay import kilit_var
        return kilit_var()
    except Exception:
        return False


def uc_hareket_ele(funding: pd.Series) -> pd.Series:
    """Son 24 saatte uç hareket etmiş coini KARŞI tarafta adaylıktan
    çıkarır (madde 196).

    +%40 pump olmuş coin LONG adayı olamaz, −%40 dump olmuş coin SHORT
    adayı olamaz. Taraf, funding'in evren MEDYANINA göre belirlenir -
    backtest'le birebir aynı kural.

    Sıralamayı DEĞİŞTİRMEZ; sadece adayı havuzdan çıkarır. Veri
    yoksa eleme yok (veri eksikliği cezalandırılmaz).
    """
    if UC_HAREKET_ELE <= 0 or funding is None or funding.empty:
        return funding
    if not SON_24S_DEGISIM:
        return funding
    med = float(funding.median())
    at = []
    for s in funding.index:
        d = SON_24S_DEGISIM.get(s)
        if d is None or not np.isfinite(d):
            continue
        uzun_aday = funding[s] < med          # düşük funding -> LONG adayı
        if d >= UC_HAREKET_ELE and uzun_aday:
            at.append(s)
        elif d <= -UC_HAREKET_ELE and not uzun_aday:
            at.append(s)
    if not at:
        return funding
    kalan = funding.drop(index=at)
    if len(kalan) < 2 * MIN_LEGS:
        logger.warning("uç hareket elemesi evreni %d sembole düşürüyordu - "
                       "eleme bu tur UYGULANMADI", len(kalan))
        return funding
    logger.info("uç hareket elemesi %d sembol çıkardı: %s",
                len(at), ", ".join(sorted(at)[:8]))
    return kalan


def bir_tur(client: ExchangeClient, dry_run: bool = False) -> dict:
    if not dry_run and _olay_kilidi_var():
        logger.info("olay modülünün penceresi açık - bu tur ATLANDI "
                    "(birkaç dakika sonra tekrar denenmeli)")
        return {"atlandi": "olay_kilidi"}
    semboller = evren_sec(client)
    if not semboller:
        logger.error("evren boş - tur atlanıyor")
        return {}

    # EDGE SAĞLIĞI (madde 139): kalibrasyonla aynı evren (hacim + yaş
    # filtresi) üzerinde, işlem yapılabilirlik filtresinden ÖNCE ölçülür.
    kapi_acik, s_durum, s_gerekce = saglik_kontrol(client, list(semboller),
                                                   yaz=not dry_run)
    if SAGLIK_MODU == "durdur" and not kapi_acik:
        logger.warning("SAĞLIK KAPISI KAPALI (%s) - tüm pozisyonlar "
                       "kapatılıyor, dilimler sıfırlanıyor", s_gerekce)
        durum = dilim_durum_oku()
        durum["dilimler"] = {}
        if not dry_run:
            kar_al_iptal(client, durum)
        mevcut = mevcut_portfoy(client)
        emirler = emirleri_hesapla({}, mevcut, tolerans_usd=0.0)
        if dry_run:
            for s, yon, usd in emirler:
                logger.info("  [DRY] KAPAT %-14s %-4s %8.2f USD", s, yon, usd)
            return {"emir": len(emirler), "hedef": {}, "saglik": s_durum,
                    "kapi": "KAPALI"}
        # madde 211: sağlık kapısı kolunda HER emir kapanış - teminat
        # hazırlığı bunları engellememeli (izole pozisyon da kapanabilsin).
        basarili = _emirleri_gonder(client, emirler, mevcut)
        dilim_durum_yaz(durum)
        return {"emir": len(emirler), "basarili": basarili,
                "saglik": s_durum, "kapi": "KAPALI"}
    if SAGLIK_MODU == "uyar" and not kapi_acik:
        logger.warning("SAĞLIK KAPISI KAPALI ama mod=uyar - işlem akışı "
                       "DEĞİŞTİRİLMEDİ (%s)", s_gerekce)

    # Bakiyeye göre bacak sayısını ve işlem yapılabilir evreni belirle
    # (madde 130). Bu, emir aşamasında sessizce atlanan bacakları önler.
    _bakiye_on = sermaye_oku(client)
    if _bakiye_on is None:
        return {"atlandi": "teminat"}
    _olcek_on = vol_olcek(_bakiye_on, olcme_yap=False)
    n_legs = uygun_bacak_sayisi(_bakiye_on, _olcek_on)
    # MADDE 204: bakiye bu bacak sayısına yetmiyorsa tur ATLANIR. Yoksa
    # her emir MIN_NOTIONAL'ın altında kalıp SESSİZCE reddedilirdi.
    _yeter, _b_usd = bakiye_yeterli_mi(_bakiye_on, n_legs, _olcek_on)
    if not _yeter:
        logger.error(
            "BAKİYE YETERSİZ: %.0f$ ile %d bacaklı dilim kurulunca bacak "
            "%.1f$ olur; borsanın minimumu %.0f$ (güvenlik payıyla %.0f$). "
            "Bot bu bakiyede SESSİZCE hiç işlem açmaz. Çözüm: bakiyeyi "
            "~%.0f$'a çıkarın ya da CARRY_N_DILIM'i düşürün (5 dilimde "
            "aynı bakiye 3 kat büyük bacak verir).",
            _bakiye_on, n_legs, _b_usd, MIN_NOTIONAL_USD,
            MIN_NOTIONAL_USD * ASGARI_BACAK_CARPANI,
            MIN_NOTIONAL_USD * ASGARI_BACAK_CARPANI * N_DILIM * n_legs
            / max(1e-9, GROSS_EXPOSURE * taban_pay()))
        return {"atlandi": "bakiye_yetersiz", "bacak_usd": _b_usd}
    _dilim_on = _bakiye_on * _olcek_on / max(1, N_DILIM)
    _bacak_on = _dilim_on * GROSS_EXPOSURE * taban_pay() / max(1, n_legs)
    semboller = islem_yapilabilir(client, semboller, _bacak_on)
    logger.info("evren: %d sembol | bacak %d+%d (~%.1f$/pozisyon)",
                len(semboller), n_legs, n_legs, _bacak_on)
    if n_legs < N_LEGS:
        logger.warning("bakiye %.0f$ için bacak %d'den %d'ye düşürüldü - "
                       "daha az çeşitlendirme, daha yüksek oynaklık",
                       _bakiye_on, N_LEGS, n_legs)

    funding = funding_topla(client, semboller, FUNDING_WINDOW_HOURS)
    logger.info("funding alınan sembol: %d", len(funding))

    _donuk: dict = {}
    # MADDE 228 - GİZLİ BAĞ KOPARILDI. `akis_topla` iki işi birden yapar:
    # emir akışı skorunu üretir VE donuk seri filtresinin (madde 183)
    # verisini doldurur. Eskiden çağrı yalnızca `AKIS_AGIRLIK > 0` iken
    # yapılıyordu; yani akış ağırlığını 0'a çeken biri, hiçbir uyarı
    # almadan DONUK FİLTRESİNİ de kapatıyordu. Madde 228 akışın katkısını
    # +0,04 Sharpe'a kadar düşürdüğü için "kapatayım" artık akla gelebilir
    # bir seçenek - bu yüzden bağ koparıldı: veri, İKİSİNDEN BİRİ
    # gerekiyorsa toplanır.
    if AKIS_AGIRLIK > 0 or DONUK_ESIK > 0:
        akis = akis_topla(client, semboller,
                          donuk_out=_donuk if DONUK_ESIK > 0 else None)
        if AKIS_AGIRLIK > 0:
            logger.info("emir akışı alınan sembol: %d", len(akis))
        else:
            logger.info("emir akışı ağırlığı 0; veri YALNIZCA donuk seri "
                        "filtresi (madde 183) için toplandı: %d sembol",
                        len(akis))
            akis = pd.Series(dtype=float)
    else:
        akis = pd.Series(dtype=float)
    # DONUK SERİ FİLTRESİ (madde 183): fiyatı kıpırdamayan sembol elenir.
    # Veri yoksa eleme yok - veri eksikliği cezalandırılmaz.
    if DONUK_ESIK > 0 and _donuk:
        _at = [s for s in funding.index
               if s in _donuk and _donuk[s] >= DONUK_ESIK]
        if _at:
            logger.info("donuk seri filtresi %d sembol eledi: %s",
                        len(_at), ", ".join(sorted(_at)[:8]))
            funding = funding.drop(index=_at)
    funding = uc_hareket_ele(funding)
    skor = birlesik_skor(funding, akis)

    bakiye = sermaye_oku(client)
    if bakiye is None:
        return {"atlandi": "teminat"}
    # Kuru çalışma bakiye geçmişine YAZMAZ - yoksa test çalıştırmaları
    # oynaklık tahminini (ve dolayısıyla kaldıracı) bozardı.
    olcek = vol_olcek(bakiye, olcme_yap=not dry_run)
    # MADDE 288: prim-ölçekli brüt. Çarpan ÖNCE okunur (bugünün ölçümü
    # henüz yazılmadığı için 1 tur gecikme doğal - motorun .shift(1)'i),
    # ölçüm SONRA yazılır. PRIM_E=0 iken ikisi de etkisiz.
    if PRIM_E > 0:
        olcek *= prim_carpani()
        prim_kaydet(prim_olc(funding), yaz=not dry_run)

    # FAZ ÇEŞİTLENDİRMESİ (madde 120): sermaye N dilime bölünür, her
    # turda SADECE sırası gelen dilim yenilenir. Diğer dilimler önceki
    # hedeflerini korur. Böylece tek bir rebalance zamanlamasına
    # bağımlılık (ve onun şans faktörü) ortadan kalkar.
    durum = dilim_durum_oku()
    # MADDE 207: durum kayıpsa borsadaki pozisyonları sahiplen - yoksa
    # kitabın ~%93'ü bu turda tasfiye edilirdi.
    if not durum.get("dilimler"):
        durum_kurtar(durum, mevcut_portfoy(client), bakiye)
    # Kâr al dolanları, YENİ dilim yazılmadan ÖNCE eski dilimlerden çıkar
    # (kuru çalışmada durum değiştirilmez).
    if not dry_run and koruma_acik():
        kar_al_kontrol(client, durum)
    sira = int(durum.get("sira", 0)) % max(1, N_DILIM)
    dilim_sermaye = (bakiye * olcek) / max(1, N_DILIM)
    kalabalik = None
    if KALABALIK_HAVUZ > 1:
        _n = min(N_LEGS, max(MIN_LEGS, int(n_legs))) if n_legs else N_LEGS
        _la, _sa = kalabalik_adaylar(skor, _n)
        kalabalik = kalabalik_topla(client, _la + _sa)
        logger.info("kalabalık oranı alınan aday: %d / %d", len(kalabalik), len(_la) + len(_sa))
        # MADDE 363: API eksik cevap verirse son bilinen oranla tamamla
        kalabalik, _ob_n = kalabalik_onbellekle_tamamla(kalabalik, _la + _sa)
        if _ob_n:
            logger.warning("%d adayın oranı önbellekten (en fazla %.0f sa eski) alındı",
                           _ob_n, KALABALIK_BAYAT_SAAT)
        if len(kalabalik) < 0.5 * max(1, len(_la) + len(_sa)):
            logger.warning("long/short oranı adayların yarısından azında var - "
                           "bu tur kalabalık seçimi KAPALI (en uç n)")
            kalabalik = None
    yeni_dilim = hedef_portfoy(skor, dilim_sermaye, n_legs=n_legs, kalabalik=kalabalik,
                               ham_funding=funding)
    if not yeni_dilim:
        return {}
    durum.setdefault("dilimler", {})[str(sira)] = yeni_dilim
    # madde 205: bu dilimin hangi bakiyeyle kurulduğunu KAYDET
    durum.setdefault("dilim_bakiye", {})[str(sira)] = float(bakiye)
    durum["sira"] = (sira + 1) % max(1, N_DILIM)
    giris_funding_yaz(durum, yeni_dilim, funding)
    # MADDE 167: kirası kesilmiş bacaklar 5 günü beklemeden bırakılır.
    # Bu SADECE eski dilimleri etkiler; yeni dilim az önce yazıldı ve
    # giriş funding'i kendisiyle aynı olduğu için elenmez.
    _solan = funding_soldu(durum, funding)
    if _solan:
        logger.info("funding SOLDU, %d bacak erken kapatılıyor: %s",
                    len(_solan), ", ".join(_solan[:6]))

    hedef = toplam_hedef(durum, bakiye)
    if not hedef:
        return {}
    mevcut = mevcut_portfoy(client)
    # MADDE 211: ELLE DEĞİŞTİRİLEN AYARLAR. İkisi de backtest'te yok ve
    # ikisi de botun kendi hata mesajlarını YANILTICI hâle getiriyor.
    if not dry_run and not pozisyon_modu_hazirla(client, mevcut):
        return {"atlandi": "hedge_modu"}
    _izole = izole_teminatlilar(client) if IZOLE_KAPAT else []
    if _izole:
        izole_ele(hedef, _izole)

    yillik = funding * 100   # funding_topla zaten yıllıklaştırıyor
    _l = [s for s, v in hedef.items() if v > 0 and s in yillik.index]
    _s = [s for s, v in hedef.items() if v < 0 and s in yillik.index]
    logger.info("bakiye %.2f USDT | dilim %d/%d yenilendi | %d pozisyon | "
                "LONG funding ort %%%.1f/yıl | SHORT %%%.1f/yıl",
                bakiye, sira + 1, N_DILIM, len(hedef),
                yillik[_l].mean() if _l else float("nan"),
                yillik[_s].mean() if _s else float("nan"))

    bacak_usd = dilim_sermaye * GROSS_EXPOSURE * taban_pay() / max(1, n_legs)
    emirler = emirleri_hesapla(hedef, mevcut,
                               tolerans_usd=bacak_usd * ISLEM_TOLERANSI)
    logger.info("%d emir gerekiyor", len(emirler))

    if dry_run:
        for s, yon, usd in emirler:
            logger.info("  [DRY] %-14s %-4s %8.2f USD   funding %%%+.1f/yıl%s",
                        s, yon, usd, yillik.get(s, float("nan")),
                        "  <- funding ALIYORUZ"
                        if (hedef.get(s, 0) > 0) == (yillik.get(s, 0) < 0)
                        else "")
        logger.info("  [DRY] dilim durumu KAYDEDİLMEDİ (kuru çalışma)")
        return {"bakiye": bakiye, "emir": len(emirler), "hedef": hedef,
                "dilim": sira, "saglik": s_durum}

    basarili = _emirleri_gonder(client, emirler, mevcut)
    logger.info("%d/%d emir gönderildi", basarili, len(emirler))
    # MADDE 208: KÂR AL, DİLİM DEFTERİNİ REHİN ALAMAZ. Eskiden sıra
    # `kar_al_kur` -> `dilim_durum_yaz` idi. `kar_al_kur` içindeki
    # `get_open_positions()` (ve `kar_al_iptal`) borsa bakımında hata
    # fırlatır; o hata `bir_tur`'dan dışarı çıkar ve `dilim_durum_yaz`
    # HİÇ ÇALIŞMAZ. Sonuç: pozisyonlar borsada AÇIK, defterde YOK ->
    # bir sonraki tur onları hiçbir dilimde bulamaz ve KAPATIR (gidiş
    # dönüş komisyon + dilim boşa gitti + `sira` ilerlemediği için eski
    # dilim 8 saat fazla tutulur). Artık defter ÖNCE yazılır; kâr al
    # bir süstür, kendi hatası defteri bozmaz.
    dilim_durum_yaz(durum)
    if koruma_acik():
        try:
            kar_al_kur(client, durum)
        except Exception as e:
            logger.error("kâr al emirleri KURULAMADI (%s) - pozisyonlar "
                         "korumasız, dilim defteri yazıldı. Bir sonraki tur "
                         "yeniden denenecek.", e)
        else:
            dilim_durum_yaz(durum)   # kâr al emir kimlikleri de kalıcı olsun
    return {"bakiye": bakiye, "emir": len(emirler), "basarili": basarili,
            "dilim": sira, "saglik": s_durum}


def _olay_emri_mi(emir: dict) -> bool:
    """Emir, olay modülüne (carry_olay.py) mi ait? Madde 166.

    Modül kurulu değilse her şey eskisi gibi çalışır (hepsi False)."""
    try:
        from carry_olay import olay_emri_mi
        return olay_emri_mi(emir)
    except Exception:
        return False


def bayat_emirleri_temizle(client: ExchangeClient, emirler: list) -> int:
    """TÜM açık emirleri siler, sadece bu turda işlem görecekleri değil (madde 163).

    SIZINTI: eski kod yalnızca `emirler` listesindeki sembollerde iptal
    yapıyordu. Dolmayan bir GTX emri, sembol portföyden ÇIKTIĞINDA hiçbir
    zaman emir listesine girmez - kitapta BAYAT fiyatla asılı kalır ve
    günler sonra dolabilir. Sonuç: bot'un haberi olmayan, karşı bacağı
    OLMAYAN yönlü bir pozisyon. Aynısı kısmi dolan bir bacağın artığı
    tolerans altında kaldığında da olur (delta < tolerans -> emir yok ->
    iptal yok -> kalan GTX sonra dolar, pozisyon hedefi AŞAR).

    Backtest'te böyle bir kavram yok: orada emir ya dolar ya dolmaz.
    Bu yüzden zarar backtest'te GÖRÜNMEZ ve kuyruğu sınırsızdır.

    Kâr al emirleri de silinir; tur sonunda kar_al_kur() hepsini güncel
    pozisyon boyutuyla yeniden kurar (eski davranışın aynısı).

    Tüm açık emirleri tek çağrıda listeleyemezsek (API hatası) eski
    davranışa düşeriz - temizlik hiç yapmamaktan iyidir.
    """
    islem = {s for s, _, _ in emirler}
    korunan: dict = {}
    acik: list = []
    try:
        acik = client.client.futures_get_open_orders()
        kitap = {o["symbol"] for o in acik if o.get("symbol")}
        # BİRLEŞİM: listeleme gecikmeli/eksik olabilir, işlem görecekleri
        # her hâlükârda temizleriz (eski davranışın garantisi korunur).
        semboller = sorted(kitap | islem)
        fazla = sorted(kitap - islem)
        if fazla:
            logger.info("bayat emir: %d sembolde emir listesi DIŞINDA açık emir "
                        "var, iptal ediliyor: %s", len(fazla), ", ".join(fazla[:5]))
        # MADDE 166: olay modülünün (carry_olay.py) emirleri KORUNUR.
        # O emirler dakikalık bir pencerede yaşar; buradan silinirlerse
        # modül sessizce çalışamaz hâle gelirdi. Olay emri BULUNAN
        # sembollerde toplu iptal yerine TEK TEK iptal yapılır.
        for o in acik:
            if _olay_emri_mi(o) and o.get("symbol"):
                korunan.setdefault(o["symbol"], set()).add(o.get("orderId"))
        if korunan:
            logger.info("bayat emir: %d sembolde olay modülünün emri var, "
                        "onlara dokunulmuyor", len(korunan))
    except Exception as e:
        logger.warning("açık emirler listelenemedi (%s) - sadece işlem görecek "
                       "sembollerde iptal yapılıyor", e)
        semboller = sorted(islem)
    silinen = 0
    for s in semboller:
        try:
            if s in korunan:
                # toplu iptal olay emrini de silerdi - tek tek iptal
                for o in acik:
                    if o.get("symbol") == s and o.get("orderId") not in korunan[s]:
                        try:
                            client.client.futures_cancel_order(
                                symbol=s, orderId=o["orderId"])
                        except Exception:
                            pass
            else:
                client.cancel_all_open_orders(s)
            silinen += 1
        except Exception:
            pass
    return silinen


def dolumu_kovala(client: ExchangeClient, bekleyen: list[dict]) -> int:
    """Konan GTX emirlerinden DOLMAYANLARI kovalar (madde 193).

    Emir kabul edildi ama dolmadıysa, bacak bir sonraki tura kadar eksik
    kalırdı. Giriş gecikmesinin maliyeti ölçüldü: her 4 saat ~2 puan
    (DOLUM_BEKLEME_SN belgesine bakın). Bu yüzden dolum beklenmez,
    kovalanır: kalan miktar iptal edilip daha uzak limitle, son denemede
    piyasa emriyle kapatılır.

    KISMİ DOLUM: borsadan `executedQty` okunur, sadece KALAN miktar
    yeniden gönderilir - yoksa pozisyon iki katına çıkardı.

    Döner: kovalanıp tamamlanan emir sayısı.
    """
    tamamlanan = 0
    for tur in range(max(1, DOLUM_DENEME)):
        time.sleep(DOLUM_BEKLEME_SN)
        kalanlar = []
        for b in bekleyen:
            try:
                e = client.client.futures_get_order(symbol=b["sembol"],
                                                    orderId=b["id"])
            except Exception as ex:
                logger.warning("%s dolum durumu okunamadı: %s", b["sembol"], ex)
                continue
            durum = str(e.get("status", "")).upper()
            if durum == "FILLED":
                continue
            try:
                dolan = float(e.get("executedQty") or 0)
            except (TypeError, ValueError):
                dolan = 0.0
            kalan = max(0.0, float(b["miktar"]) - dolan)
            if durum in ("CANCELED", "EXPIRED", "REJECTED"):
                pass                      # emir yok; kalan varsa yeniden gönder
            else:
                try:
                    client.client.futures_cancel_order(symbol=b["sembol"],
                                                       orderId=b["id"])
                except Exception:
                    pass                  # bu arada dolmuş olabilir
                try:                      # iptalden sonra gerçek dolumu TEKRAR oku
                    e2 = client.client.futures_get_order(symbol=b["sembol"],
                                                         orderId=b["id"])
                    dolan = max(dolan, float(e2.get("executedQty") or 0))
                    kalan = max(0.0, float(b["miktar"]) - dolan)
                except Exception:
                    pass
            if kalan <= 0:
                continue
            kalanlar.append(dict(b, miktar=kalan))
        if not kalanlar:
            if tur == 0:
                logger.info("dolum kontrolü: konan emirlerin HEPSİ doldu")
            break
        son = (tur >= max(1, DOLUM_DENEME) - 1)
        logger.warning("dolum kontrolü %d: %d emir dolmadı - %s",
                       tur + 1, len(kalanlar),
                       "PİYASA emrine düşülüyor" if son and PIYASA_YEDEK
                       else "limit uzaklaştırılıp yeniden deneniyor")
        yeni_bekleyen = []
        for b in kalanlar:
            try:
                p = client.get_symbol_precision(b["sembol"])
                fiyat = float(client.client.futures_symbol_ticker(
                    symbol=b["sembol"])["price"])
                miktar = round(float(b["miktar"]), p["quantity_precision"])
                if miktar <= 0 or miktar * fiyat < MIN_NOTIONAL_USD:
                    continue
                if son and PIYASA_YEDEK:
                    client.open_market_position(b["sembol"], b["yon"], miktar)
                    tamamlanan += 1
                else:
                    carpan = GTX_DENEME_CARPANLARI[
                        min(tur + 1, len(GTX_DENEME_CARPANLARI) - 1)]
                    limit = limit_fiyat(fiyat, b["yon"],
                                        p.get("price_precision", 2),
                                        ofset=LIMIT_OFSET * carpan)
                    e = client.client.futures_create_order(
                        symbol=b["sembol"], side=b["yon"], type="LIMIT",
                        timeInForce="GTX", quantity=miktar, price=limit)
                    if e and e.get("orderId") is not None:
                        yeni_bekleyen.append(dict(b, miktar=miktar,
                                                  id=e.get("orderId")))
                    tamamlanan += 1
            except Exception as ex:
                logger.error("%s dolum kovalama başarısız: %s", b["sembol"], ex)
            time.sleep(0.2)
        bekleyen = yeni_bekleyen
        if not bekleyen:
            break
    return tamamlanan


def _kuculten_mi(sembol: str, yon: str, usd: float, mevcut: dict | None) -> bool:
    """Bu emir mevcut pozisyonu KÜÇÜLTÜYOR mu (kapatma/kırpma)?

    MADDE 211: `kaldirac_hazirla` teminat modunu ÇAPRAZ'a çekmeyi dener;
    sembolde AÇIK POZİSYON varsa Binance bunu `-4048` ile reddediyor
    ("Margin type cannot be changed if there exists position") ve fonksiyon
    False dönüyor. `_emirleri_gonder` da False görünce emri ATLIYORDU.

    Sonuç: elle izoleye çekilmiş bir sembolün pozisyonu **hiç
    kapatılamıyordu**. Madde 211'in kendi düzeltmesi (izole sembolü
    hedeften çıkarmak) kapatma emrini üretiyor, ama bu kontrol onu
    engelliyordu - yani izole pozisyon sonsuza kadar yönetilmeden
    kalırdı. Teminat hazırlığı AÇILIŞ için var; küçülten emir ne kaldıraç
    ne teminat modu ister.
    """
    if not mevcut:
        return False
    m = mevcut.get(sembol, 0.0)
    if abs(m) < 1e-12:
        return False
    # Pozisyonun tersine giden emir küçültür (fazlası yön çevirir, o da
    # önce küçültme içerir - yine engellenmemeli).
    return (m > 0 and yon == "SELL") or (m < 0 and yon == "BUY")


def _emirleri_gonder(client: ExchangeClient, emirler: list,
                     mevcut: dict | None = None) -> int:
    """Emirleri gönderir, başarılı sayısını döner. Önceki turdan kalan
    dolmamış limit emirleri önce temizlenir - bayat fiyattan dolmasınlar.

    `mevcut`: pozisyonlar (madde 211). Verilirse KÜÇÜLTEN emirler teminat
    hazırlığından muaf tutulur - yoksa açık pozisyonlu bir sembol hiç
    kapatılamaz."""
    bayat_emirleri_temizle(client, emirler)

    basarili = 0
    kucuk: list[str] = []         # madde 204: MIN_NOTIONAL altında kalanlar
    bekleyen: list[dict] = []     # madde 193: konan GTX emirleri
    acilamayan = []
    for s, yon, usd in emirler:
        try:
            if (not _kuculten_mi(s, yon, usd, mevcut)
                    and not kaldirac_hazirla(client, s)):
                continue          # çapraz teminat doğrulanamadı - bu turda dokunma
            p = client.get_symbol_precision(s)
            fiyat = float(client.client.futures_symbol_ticker(symbol=s)["price"])
            miktar = round(usd / fiyat, p["quantity_precision"])
            if miktar <= 0 or miktar * fiyat < MIN_NOTIONAL_USD:
                # MADDE 204: bu atlama eskiden SESSİZDİ. Bakiye küçükse her
                # bacak buradan dönüyor, bot hiç işlem açmıyor ve hiçbir
                # uyarı çıkmıyordu - madde 123'ün "sessiz duruş" hatası.
                kucuk.append(s)
                continue
            if not LIMIT_EMIR:
                client.open_market_position(s, yon, miktar)
                basarili += 1
                time.sleep(0.2)
                continue
            # madde 160: GTX (post-only) emri reddedilirse bacak 24 saat AÇIK
            # KALMAZ. Backtest'te her eksik bacak yıllık ~3 puana mal oluyor.
            # Önce limit daha uzağa konur, son çare piyasa emri (+4bp).
            son_hata = None
            for deneme, carpan in enumerate(GTX_DENEME_CARPANLARI):
                try:
                    limit = limit_fiyat(fiyat, yon, p.get("price_precision", 2),
                                        ofset=LIMIT_OFSET * carpan)
                    _e = client.client.futures_create_order(
                        symbol=s, side=yon, type="LIMIT", timeInForce="GTX",
                        quantity=miktar, price=limit)
                    if _e and _e.get("orderId") is not None:
                        bekleyen.append({"sembol": s, "yon": yon,
                                         "miktar": miktar,
                                         "id": _e.get("orderId")})
                    if deneme:
                        logger.info("%s %s: GTX %d. denemede geçti (ofset x%.0f)",
                                    s, yon, deneme + 1, carpan)
                    basarili += 1
                    son_hata = None
                    break
                except Exception as e:
                    son_hata = e
            if son_hata is not None:
                if PIYASA_YEDEK:
                    try:
                        client.open_market_position(s, yon, miktar)
                        logger.warning("%s %s: limit emir geçmedi (%s) - PİYASA "
                                       "emriyle açıldı (+4bp)", s, yon, son_hata)
                        basarili += 1
                    except Exception as e2:
                        acilamayan.append(s)
                        logger.error("%s %s emri hiç açılamadı: %s", s, yon, e2)
                else:
                    acilamayan.append(s)
                    logger.error("%s %s emri açılamadı: %s", s, yon, son_hata)
        except Exception as e:
            acilamayan.append(s)
            logger.error("%s %s emri başarısız: %s", yon, s, e)
        time.sleep(0.2)
    if acilamayan:
        oran = len(acilamayan) / max(1, len(emirler))
        logger.error("%d/%d bacak AÇILAMADI (%s). Her eksik bacak yıllık ~3 "
                     "puana mal oluyor (madde 160); portföy de tam nötr değil.",
                     len(acilamayan), len(emirler), ", ".join(acilamayan[:8]))
        if oran > 0.25:
            logger.error("Emirlerin dörtte birinden fazlası açılamadı - "
                         "bakiye/minimum emir büyüklüğü veya API izinlerini kontrol edin.")
    if kucuk:
        logger.error("%d/%d bacak MİNİMUM EMİR BÜYÜKLÜĞÜNÜN ALTINDA kaldı "
                     "(%s) - bakiye bu bacak sayısı için yetersiz. "
                     "CARRY_N_DILIM'i düşürün veya bakiye ekleyin; "
                     "madde 204'e bakın.",
                     len(kucuk), len(emirler), ", ".join(sorted(set(kucuk))[:8]))
    if DOLUM_BEKLEME_SN > 0 and bekleyen:
        dolumu_kovala(client, bekleyen)
    return basarili


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="emir GÖNDERMEZ, ne yapacağını yazar")
    ap.add_argument("--once", action="store_true",
                    help="tek tur çalışıp çıkar (varsayılan: döngü)")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler("carry_bot.log", encoding="utf-8")])

    client = ExchangeClient(config.API_KEY, config.API_SECRET,
                            mode=getattr(config, "MODE", "demo"))
    logger.info("carry_bot başladı | mod=%s | %d+%d bacak | %d dilim | "
                "her dilim %.0fsa'te bir (tur: %.0fsa) | gross %.1fx | "
                "akış %.0f%% | risk: %s (vol hedefi %.0f%%)",
                client.mode, N_LEGS, N_LEGS, N_DILIM, REBALANCE_HOURS,
                REBALANCE_HOURS / max(1, N_DILIM), GROSS_EXPOSURE,
                AKIS_AGIRLIK * 100, RISK_PROFILI, VOL_HEDEF * 100)

    while True:
        try:
            bir_tur(client, dry_run=args.dry_run)
        except KeyboardInterrupt:
            logger.info("durduruldu")
            break
        except Exception as e:
            logger.exception("tur başarısız: %s", e)
        if args.once:
            break
        # Her dilim REBALANCE_HOURS'ta bir yenilenir; N dilim varsa
        # bot bunun 1/N'i kadar sıklıkta çalışır.
        time.sleep(REBALANCE_HOURS * 3600 / max(1, N_DILIM))


if __name__ == "__main__":
    main()
