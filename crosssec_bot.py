"""Kesitsel (cross-sectional) ortalamaya dönüş botu - CANLI ÇALIŞTIRICI.

Bu, main.py'daki ana bottan TAMAMEN FARKLI bir stratejidir:

| | main.py (mean_reversion) | crosssec_bot.py (bu dosya) |
|---|---|---|
| Mantık | Her coini tek tek incele, sinyal ara | Tüm coinleri göreceli sırala |
| Pozisyon | SL/TP ile aç-kapa | Sürekli açık, periyodik dengele |
| Yön | Sinyale göre | Long ve short eşit (piyasa nötr) |
| Kâr kaynağı | Coinin kendi ortalamasına dönmesi | Coinlerin BİRBİRİNE yakınsaması |
| Stop-loss | Her pozisyonda var | YOK (portföy seviyesi risk yönetimi) |

BACKTEST SONUÇLARI (2022-2026, 14 coin, 4h, sabit nominal, tüm maliyetler
dahil - detay README madde 34/36):

  yıl    kâr      Sharpe   max düşüş
  2022   +66.7%    1.60     -14.0%
  2023  +176.9%    2.61     -17.8%
  2024  +352.6%    4.21     -29.8%
  2025  +105.4%    2.00     -26.6%
  2026    +3.9%    0.33     -17.6%

Walk-forward: 9 OOS diliminin 8'i pozitif, parametre seçimi tutarlı.
Ters sinyal testi: normal Sharpe +5.01, ters çevrilince -3.45 (gerçek edge).

=== ÖNEMLİ UYARILAR ===

1. STOP-LOSS YOKTUR. Risk, portföy seviyesinde yönetilir (piyasa nötr
   olmak + çeşitlendirme + max düşüş limiti). Tek bir coin patlarsa
   karşı bacak dengelemeyi amaçlar ama GARANTİ DEĞİLDİR.

2. Max düşüş backtest'te -%30'a kadar çıktı. Bu NORMAL kabul edilmeli,
   panikle kapatmak stratejiyi bozar.

3. Backtest'te modellenmemiş: emir defteri derinliği, rebalance araları
   ağırlık kayması, short bacağının borç maliyeti, yüksek işlem hacminin
   piyasa etkisi.

4. 2026 performansı zayıf (+3.9%). Strateji hâlâ kârlı ama eski
   yıllardaki gücünde değil.

KULLANIM:
    python crosssec_bot.py --dry-run     # sadece göster, emir gönderme
    python crosssec_bot.py               # gerçekten çalıştır
"""

import argparse
import json
import os
import logging
import time

import numpy as np
import pandas as pd

import config
from exchange_client import ExchangeClient
from slippage_check import simulate_market_order

logger = logging.getLogger("crosssec")

# --- Strateji parametreleri ---
# 504 kombinasyonluk tarama + out-of-sample doğrulama sonucu (README madde 38).
# Tarama 1 BAR UYGULAMA GECİKMESİ dahil yapıldı: gerçekte sinyali bar
# kapanışında görüp emri bir sonraki barda doldurursunuz. Gecikmesiz
# backtest Sharpe 12.6 gösteriyordu, gecikmeli 2.6 - yani o rakamın
# %80'i yanılsamaydı.
LOOKBACK_DAYS = 10       # göreceli performans penceresi (tek ufuk - eski yöntem)
REBALANCE_DAYS = 1       # GÜNDE BİR dengele (aşağıdaki slippage notuna bakın)

# --- FAZ DİLİMLEME (dengeleme saati riskini ortadan kaldırır) ---
# SORUN: Bot günde bir kez dengeliyor. Günün HANGİ SAATİNDE dengelediği
# sonucu çok değiştiriyor (ölçüldü: Sharpe 1.12 - 2.08 arası, madde 100).
# Hangi saatin iyi olacağı ÖNCEDEN BİLİNEMEZ.
#
# ÇÖZÜM: Sermayeyi dilimlere böl, her dilimi farklı saatte dengele.
# Her dilim bağımsız bir portföy gibi çalışır; fazlar arası korelasyon
# 0.405 olduğu için gerçek çeşitlendirme sağlıyor.
#
# ÖLÇÜLDÜ (tüm faz kombinasyonlarının ortalaması - dürüst karşılaştırma):
#   dilim   ort Sharpe   en kötü durum   pozisyon
#     1        1.54          1.12            8     (mevcut - şansa bağlı)
#     2        1.86          1.47           16
#     3        2.01          1.70           24     <- SEÇİLEN
#     6        2.20          2.20           48     (en iyi ama çok pozisyon)
#
# 3 dilim: Sharpe %30 artıyor, EN KÖTÜ durum %52 iyileşiyor.
# 6 dilim biraz daha iyi ama 48 pozisyon slippage ve API yükü demek.
#
# UYGULAMA: her turda SADECE sıradaki dilimin hedefi yeniden hesaplanır,
# diğerleri korunur. Toplam hedef hepsinin birleşimidir. Dilim durumları
# crosssec_state.json içinde "phase_targets" altında tutulur.
#     tek faz (günlük)   : Sharpe 1.54  (en kötü faz 1.12)
#     3 dilim            : Sharpe 2.01  ortalama, en kötü 1.70
#
# POZİSYON SAYISI: her dilim N_LEGS*2 coin seçer ama dilimler ÇAKIŞABİLİR
# (aynı coin birden fazla dilimde). Pratikte toplam benzersiz pozisyon
# 8-24 arasında değişir; ters yönler netleşir.
#
# DİKKAT - SLIPPAGE: 8 saatlik dengeleme günlükten 3 kat fazla devir
# demek. Madde 58'de 4 saatlik dengeleme kötü slippage senaryosunda
# ZARARA dönmüştü. 8 saatlik ara noktadır; demo hesapta gerçek
# slippage ölçüldükten sonra değerlendirin. Riskli bulursanız
# USE_PHASE_SPLIT=False ile günlüğe dönün.
#
# MİNİMUM SERMAYE: mevcut uygulamada değişmiyor (8 pozisyon).
# !!! KAPATILDI - ÖLÇÜM HATASI DÜZELTİLDİ (madde 104) !!!
# İlk ölçüm fazların GETİRİ SERİLERİNİ ortalıyordu; bu, dilimlerin
# AYRI HESAPLARDA çalıştığını varsayar. Gerçek uygulamada dilimler
# AYNI hesapta toplanıyor ve NETLEŞİYOR: bir dilimde long olan coin
# başka dilimde short oluyor.
#
# Ölçüldü: 3 dilimde net exposure %19.3 kayboluyor (brüt 0.999 ->
# net 0.807). Sermayenin beşte biri boşa yatıyor.
#
# GERÇEK DİLİM MANTIĞIYLA BACKTEST:
#   dilim   Sharpe   yıllık
#     1      1.78    +87.7%   <- en iyi (dilimleme YOK)
#     2      1.09    +32.4%
#     3      0.87    +21.7%
#     6      0.37     +6.7%
# Dilimleme ZARARLI. Kapatıldı.
#
# Faz riski (madde 100) hâlâ gerçek bir sorun ama bu çözüm işe
# yaramıyor. Alternatif: iki botu AYRI ALT HESAPLARDA farklı
# saatlerde çalıştırmak (netleşme olmaz) - ama bu sermaye bölmeyi
# gerektirir ve karışım oranıyla (madde 102) çakışır.
USE_PHASE_SPLIT = False
PHASE_COUNT = 3          # dengeleme 24/PHASE_COUNT saatte bir yapılır
N_LEGS = 4               # her tarafta kaç coin (4+4 = 8 pozisyon)
# BACKTEST ile CANLI arasında EVREN FARKI var - bacak sayısını doğrudan
# aktarmayın:
#   backtest evreni : 10 coin (temiz) -> 4+4 = evrenin %80'i
#   canlı evren     : 30 coin         -> 4+4 = evrenin %27'si
# Madde 79: optimum bacak ~ evrenin 1/3'ü.
#   10 coin için  -> ~2+2
#   30 coin için  -> ~5+5
# Yani backtestte "3+3 en iyi" sonucu, 30 coinlik canlı evrende ~5+5'e
# denk gelir. 4+4 ikisinin arasında, muhafazakâr bir orta nokta.
# Evreni genişletirseniz (historical_fetch.py --extended) bacağı da
# artırmayı değerlendirin.
# Bacak sayısı, çok ufuklu sıralamayla birlikte yeniden ölçüldü. Az bacak
# = daha yoğun = daha çok getiri + daha çok risk. Yıl yıl ortalamalar:
#   3+3: +154.0%  en kötü yıl -18.3%  OOS Sharpe 2.72  düşüş -21.7%
#   4+4: +144.1%  en kötü yıl -12.9%  OOS Sharpe 2.88  düşüş -17.2%  <- seçilen
#   5+5: +130.3%  en kötü yıl -12.4%  OOS Sharpe 2.81  düşüş -15.9%
#   6+6: +114.6%  en kötü yıl  -9.1%  OOS Sharpe 2.77  düşüş -12.8%
# 4+4 en iyi OOS Sharpe'ı veriyor; 5+5'e göre %11 daha çok getiri ve
# en kötü yıl neredeyse aynı. 3+3 daha çok kazandırıyor ama 2026'da
# -%18.3 ile çok riskli.

# --- ÇOK UFUKLU SIRALAMA ---
# Tek bir pencere (10 gün) gürültüye duyarlı. Birden fazla pencerenin
# z-skorunu ortalamak daha sağlam bir sinyal veriyor.
#
# ÖLÇÜLDÜ (OOS 2025-2026, gecikme + TP + kademeli azaltma dahil):
#   tek 10g ufuk    : Sharpe 1.75, yıllık +53.6%
#   5g + 10g        : Sharpe 2.69, yıllık +86.3%
#   5g + 10g + 15g  : Sharpe 2.81, yıllık +90.4%   <- seçilen
#
# YIL YIL: 5/5 yılda daha iyi (2022 ve 2026 dahil, istisnasız).
# Duyarlılık: denenen 8 kombinasyonun TÜMÜ tek-ufuktan iyi
# (OOS Sharpe 1.81-2.81 vs 1.75) - tek bir sihirli sayıya bağlı değil.
#
# Üç ufuk seçildi (iki yerine): en iyi OOS Sharpe'ı veriyor ve daha fazla
# pencere ortalaması doğal olarak gürültüye daha dayanıklıdır.
USE_MULTI_HORIZON = True
HORIZON_DAYS = [5, 10]       # bu pencerelerin z-skor ortalaması kullanılır
# GÜNCELLEME (madde 101): 5/10/15g'den 5/10g'ye çevrildi.
# Önceki seçim TEK FAZDA (offset 0) yapılmıştı; faz ortalamasıyla
# (dürüst ölçüm, bkz. madde 100) tablo değişti:
#   ufuklar        IS Sharpe   OOS Sharpe   OOS yıllık
#   5/10/15g          1.40        1.49        +65.2%   (eski)
#   5/10g             1.50        1.84        +92.4%   <- SEÇİLEN
#   10g tek           1.14        1.32        +54.6%
#   3/6/10g           1.30        1.85        +96.7%   (IS zayıf, tutarsız)
# Yıl yıl: 5/10g 5/5 yılda daha iyi - istisnasız.

# --- NEDEN 4 SAATLİK DEĞİL DE GÜNLÜK? ---
# Ham backtest 4 saatlik rebalance'ı daha iyi gösteriyor (yıllık +159% vs
# +77%). AMA slippage'a karşı kırılganlık tamamen farklı - çünkü aynı kârı
# 6 kat fazla işlemle üretiyor:
#
#   ayar              cycle başına kâr   ince defterli coinlerde ek maliyet
#   4 saatlik 5+5          %0.073                  %0.025   -> marj çok dar
#   GÜNLÜK 5+5            %0.211                  %0.120   -> marj rahat
#
# 4 saatlik ayarda kârın üçte biri slippage'a gidiyor ve gerçek slippage
# tahminden biraz kötü çıkarsa strateji ZARARA döner. Günlük rebalance
# aynı riske karşı 3 kat daha geniş marj bırakır.
# Ölçüm aracı: slippage_check.py (README madde 43).
#
# Bacak sayısı seçimi (günlük rebalance, OOS 2025-2026):
#   2+2: Sharpe 1.70, yıllık +84.1%, düşüş -20.6%
#   5+5: Sharpe 2.38, yıllık +76.9%, düşüş -14.3%   <- seçilen
#   7+7: Sharpe 1.95, yıllık +53.6%, düşüş -13.4%
# 5+5 en yüksek Sharpe ve en düşük düşüşü veriyor, getiri 2+2'ye yakın.
TIMEFRAME = "4h"
GROSS_EXPOSURE = 1.0     # toplam pozisyon / sermaye. 1.0 = kaldıraçsız
# Kaldıraç test edildi: Sharpe hemen hemen sabit kalıyor (2.91-3.03),
# yani yeni bir edge yaratmıyor - sadece getiri ve riski orantılı büyütüyor.
#   gross 1.0: yıllık  +99.9%, max düşüş -19.0%
#   gross 2.0: yıllık +183.8%, max düşüş -27.2%
#   gross 3.0: yıllık +248.7%, max düşüş -29.5%
# DİKKAT: MAX_DRAWDOWN_PCT (devre kesici) %35. Kaldıraç 2.0'da max düşüş
# zaten -%27.2; tek kötü dönem botu tamamen durdurabilir. Kaldıracı
# artırırsanız devre kesici eşiğini de gözden geçirin, yoksa bot normal
# bir dalgalanmada kapanıp manuel müdahale bekler.
UNIVERSE_SIZE = 30       # kaç coin taranacak (en hacimliler)
# EVREN GENİŞLİĞİ EN ÖNEMLİ KALDIRAÇ NOKTASI.
# Kesitsel strateji coinlerin BİRBİRİNE göre sıralanmasından kazanır -
# evren ne kadar genişse ayrışma o kadar zengin olur. Temiz veriyle
# ölçüldü (2022+):
#     4 coin  -> Sharpe 0.93      8 coin  -> Sharpe 1.76
#     6 coin  -> Sharpe 1.47     10 coin  -> Sharpe 2.13
# Her ek coin ~0.2 Sharpe ekliyor (doyma noktasına kadar).
#
# DİKKAT - BACKTEST İLE CANLI ARASINDA FARK VAR:
# Canlı bot burada 30 coin tarıyor ama backtest sadece 14 coinlik yerel
# veriyle yapılıyor (donuk olanlar çıkınca 10). Yani CANLI BOT,
# BACKTEST'TEN DAHA GENİŞ BİR EVRENDE ÇALIŞACAK - bu, backtest
# sonuçlarının muhafazakâr olabileceği nadir bir durumdur.
# Backtest'i canlıya yaklaştırmak için:
#     python historical_fetch.py --extended --start 2021-01-01
# (evreni 14'ten 34'e çıkarır)
# NOT: 5+5 bacak için 10 coin gerekir, ama likidite filtresi bir kısmını
# eler. 30 taranırsa filtre yarısını elese bile yeterli coin kalır.
# Backtest 14 coinle yapıldı; daha geniş evren kesitsel ayrışmayı
# zenginleştirdiği için sonucu iyileştirmesi beklenir, ama bu test
# EDİLMEDİ (mainnet verisi bu ortamdan indirilemedi).

BARS_PER_DAY = 24 / int(TIMEFRAME.replace("h", ""))
LOOKBACK_BARS = int(LOOKBACK_DAYS * BARS_PER_DAY)
# Çekilmesi gereken bar sayısı: en uzun ufku karşılamalı. Çok ufuklu mod
# açıkken LOOKBACK_BARS yetmez (ör. 15 günlük ufuk 90 bar ister).
REQUIRED_BARS = (int(max(HORIZON_DAYS) * BARS_PER_DAY) if USE_MULTI_HORIZON
                 else LOOKBACK_BARS) + 5

# --- Portföy seviyesi risk koruması ---
# Bu stratejide pozisyon bazlı stop-loss YOKTUR (piyasa nötr yapı ve
# çeşitlendirme risk yönetimini üstlenir). Ama bu, sınırsız kayıp
# kabul edildiği anlamına gelmez. Backtest'te max düşüş -%30'a kadar
# çıktı; canlıda bunun ötesi, modelin öngörmediği bir şeyin olduğunu
# (rejim kırılması, veri sorunu, likidite krizi) gösterir.
#
# MAX_DRAWDOWN_PCT aşılırsa bot TÜM pozisyonları kapatır ve durur.
# Bu bir "stop-loss" değil, bir DEVRE KESİCİDİR: amacı kaybı sınırlamak
# değil, insan müdahalesi gerektiren bir durumu yakalamaktır.
MAX_DRAWDOWN_PCT = 35.0      # tepe bakiyeden bu kadar düşerse dur
STATE_FILE = "crosssec_state.json"

# --- KÂR GERİ VERME KORUMASI (kademeli exposure azaltma) ---
# Problem: strateji zirveye çıkıp sonra kârın büyük kısmını geri verebiliyor
# (gerçek kullanıcı deneyimi: 60 günde +%180, sonra +%96'ya geriledi).
#
# Çözüm: tepe bakiyeden uzaklaştıkça pozisyon büyüklüğünü KADEMELİ azalt.
# Kayıp büyüdükçe bot kendini küçültür, toparlanınca büyür. Bu, sert bir
# "dur" emrinden farklıdır - piyasadan tamamen çıkmaz, sadece küçülür.
#
# ÖLÇÜLEN ETKİ (2+2 coin, günlük rebalance, 2022-2026):
#   koruma yok           : yıllık +152.5%, Sharpe 1.67, max düşüş -74.5%
#   kademeli azaltma     : yıllık +105.6%, Sharpe 1.83, max düşüş -29.4%
# Getiri düşüyor AMA risk yarıdan fazla azalıyor ve Sharpe YÜKSELİYOR.
#
# 60 günlük pencerelerde en kötü geri verme: %33.3 -> %20.8
#
# NEDEN SERT STOP DEĞİL: "tepeden -%15 düşünce her şeyi kapat" denendi,
# DAHA KÖTÜ sonuç verdi (max düşüş -93.5%) - kötü anda kapatıp
# toparlanmayı kaçırıyor. Kademeli azaltma bu tuzağa düşmez.
USE_DRAWDOWN_SCALING = True
DRAWDOWN_SCALE_FULL_PCT = 30.0   # tepeden bu kadar düşünce exposure sıfırlanır
                                 # (aradaki her seviyede orantılı azalır)

# --- POZİSYON BAZLI KÂR ALMA ---
# Kullanıcı gözlemi: "zirvede kârı almak gerekmez mi?" - test edildi, EVET.
# Bir pozisyon girişinden %X kâra ulaşınca kapatılır; bir sonraki
# dengelemeye kadar o slot boş kalır.
#
# ÖLÇÜLEN ETKİ (2+2 coin, günlük rebalance, 2022-2026, 1 bar çıkış gecikmesi
# dahil - detay README madde 42):
#   koruma yok                    : yıllık +152.5%, Sharpe 1.67, düşüş -74.5%
#   sadece kademeli azaltma       : yıllık +105.6%, Sharpe 1.83, düşüş -29.4%
#   TP %10 + kademeli azaltma     : yıllık +135.1%, Sharpe 2.34, düşüş -29.6%
#
# İKİSİ BİRLİKTE gerekli: TP tek başına max düşüşü -%84'e ÇIKARIYOR
# (kazananları erken kapatıp kaybedenleri tutmaya yol açıyor).
# Kademeli azaltma ile birleşince hem getiri hem Sharpe artıyor.
#
# Eşik duyarlılığı: %4-%15 arası tüm değerler TP'siz halden iyi
# (OOS Sharpe 1.37-1.70 vs TP'siz 1.22) - tek bir sayıya bağlı değil.
USE_POSITION_TAKE_PROFIT = True
POSITION_TP_PCT = 4.0            # pozisyon bu kadar kâra ulaşınca kapat
# NOT: Eşik %8'den %4'e düşürüldü. %8 TEK UFUKLU sıralamayla ayarlanmıştı;
# çok ufuklu sıralamaya (HORIZON_DAYS) geçince optimum kaydı - daha iyi
# sinyal, daha hızlı kâr. Yeniden ölçüldü (OOS 2025-26):
#   TP yok : Sharpe 2.33, yıllık  +85.2%
#   +%8    : Sharpe 2.88, yıllık +102.1%
#   +%4    : Sharpe 3.23, yıllık +110.7%   <- seçilen
#   +%3    : Sharpe 3.33, yıllık +115.3%
# Yıl yıl (%4): ortalama +155.1%, en kötü yıl -7.3% (+%8'de -12.9%),
# sadece 1 negatif yıl. Her açıdan daha iyi.
# Plato geniş: %2.5-%5 arası tüm eşikler iyi çalışıyor - tek bir sayıya
# bağlı değil. %4 seçildi (platonun ortası, %3'ten daha az işlem üretir).
# Slippage kontrolü: %0.20 gibi kötü bir senaryoda bile %4 TP (+%101.8)
# %8 TP'den (+%98.2) iyi - düşük eşik orantısız slippage riski yaratmıyor.

# --- LİKİDİTE FİLTRESİ ---
# Bu strateji "aşırı hareket edeni seç" mantığıyla çalıştığı için doğası
# gereği küçük piyasa değerli, İNCE emir defterli coinlere yönelir. Böyle
# bir coinde $960'lık emir defteri süpürüp kötü fiyattan dolabilir -
# paper trading'de bu HİÇ görünmez.
#
# Hesap (günlük rebalance, 5+5):
#   cycle başına kâr             : %0.211
#   ince defterli coinde maliyet : ~%0.19  -> marj neredeyse yok
#   likit coinde maliyet         : ~%0.03  -> marj rahat
#
# Bu filtre, emir defteri yeterince derin olmayan coinleri EVRENDEN
# çıkarır. Böylece sorun kaynağında çözülür ve rebalance sıklığını
# kısıtlamak gerekmez.
#
# MIN_DEPTH_USDT: ilk 20 seviyedeki toplam dolar hacmi bunun altındaysa
# coin atlanır. Varsayılan, tipik pozisyon büyüklüğünün ~50 katı olacak
# şekilde seçildi - emriniz defterin küçük bir kısmını yemeli.
# MAX_SLIPPAGE_PCT: tahmini gidiş-dönüş slippage bunu aşarsa coin atlanır.
# --- ACİL STOP-LOSS (kuyruk riski koruması) ---
# Bu stratejide normal stop-loss YOKTUR (piyasa nötr yapı risk yönetimini
# üstlenir). Ama SHORT tarafında kayıp teorik olarak sınırsızdır ve
# gerçek örnekler var:
#   XLMUSDT 2024-11: 0.186 -> 0.528 (18 günde) = short pozisyonda -%184
#   ETCUSDT 2022-07: 15.08 -> 37.74            = -%150
#   BCHUSDT 2023-06: 113.1 -> 260.0            = -%130
# Her pozisyon sermayenin %12.5'i olduğundan, XLM benzeri tek bir olay
# sermayenin %23'ünü götürür.
#
# Bu eşik ÇOK GENİŞ tutuldu - normal işleyişe karışmaz, sadece felaket
# senaryosunda devreye girer. 4.6 yılda sadece 6 kez tetikleniyor.
#
# ÖLÇÜLDÜ: performansı değiştirmiyor (OOS Sharpe 3.23 -> 3.25), yani
# MALİYETSİZ BİR SİGORTA. XLM olayının olduğu dönemde (2024-10/2025-01)
# hem getiriyi artırdı (+%133 -> +%143) hem düşüşü azalttı (-%16.2 -> -%14.5).
USE_EMERGENCY_STOP = True
EMERGENCY_STOP_PCT = 25.0        # pozisyon bu kadar zarara girerse kapat

# !!! ÖNEMLİ MİMARİ FARK (sinyal botuna göre) !!!
# Bu bot borsa tarafında SL/TP EMRİ KULLANMAZ. Kâr alma ve acil stop,
# her dengeleme turunda bot tarafından KONTROL EDİLİR ve pozisyon
# gerekirse kapatılır.
#
# SONUÇ: BOT DURURSA POZİSYONLAR KORUMASIZ KALIR. Borsada bekleyen bir
# stop emri yoktur; fiyat aleyhe giderse kimse kapatmaz.
#
# Bu yüzden:
#   - Botu kesintisiz çalışacak bir ortamda başlatın (sunucu/VPS,
#     kapanmayan bilgisayar). Dizüstü bilgisayarda "kapat-aç" yapmayın.
#   - Botu uzun süre durduracaksanız ÖNCE pozisyonları kapatın.
#   - dashboard.py ile çalıştığını düzenli kontrol edin.
#
# Neden borsa SL'i kullanılmıyor: strateji piyasa nötr ve pozisyonlar
# günlük olarak tamamen değişiyor. Her turda SL emirlerini iptal edip
# yeniden kurmak hem karmaşık hem de ek API yükü demek. Ayrıca sabit
# bir SL, kesitsel stratejinin mantığına (göreceli yakınsama) uymuyor.

# --- DİSPERSİYON FİLTRESİ (kötü rejim koruması) ---
# Bu strateji coinlerin BİRBİRİNDEN ayrışmasından kazanır. Ayrışma
# (dispersiyon) düşükse işlenecek hammadde yoktur - hangi yöne oynanırsa
# oynansın kazanılmaz.
#
# 2026 bunun örneği: dispersiyon 0.56% (2024'ün YEDİDE BİRİ), otokorelasyon
# +0.025 (ortalamaya dönüş yok). Strateji o yıl -%2.8 kaybetti.
#
# "Kötü rejimde tersini yap (momentum)" denendi, DAHA KÖTÜ:
#   2026: ortalamaya dönüş -%3.7  |  momentum -%13.6
# Çünkü sorun YÖN değil, ayrışmanın hiç olmaması.
#
# ÇÖZÜM: ayrışma eşiğin altındayken işlem yapma.
# ÖLÇÜLDÜ (temiz 10 coin, yıl yıl):
#   filtresiz : 2022 -17.2%  2023 +21.5%  2024 +129.6%  2025 +143.0%  2026 -2.8%
#   eşik 0.005: 2022 -17.2%  2023 +21.5%  2024 +129.6%  2025 +143.0%  2026 +0.9%
# Hiçbir yılı bozmuyor, 2026'yı pozitife çeviriyor, sadece %3 zaman boş.
#
# IS/OOS doğrulaması: eğitim döneminde etkisiz (Sharpe 2.25 sabit),
# test döneminde iyileştiriyor (2.20 -> 2.24). 0.004-0.010 aralığının
# tamamı çalışıyor - tek bir sayıya bağlı değil.
#
# NOT: Bu fikir madde 46'da REDDEDİLMİŞTİ, ama o test 14 coin (donuk
# dahil) ve eski parametrelerle yapılmıştı. Temiz evren + güncel
# ayarlarla sonuç değişti.
USE_DISPERSION_FILTER = True
MIN_DISPERSION = 0.005           # coinler arası getiri std'si bu değerin altındaysa dur
# EŞİK KALİBRASYONU EVRENE BAĞLI - dikkat:
#   14 coin (donuk dahil): dispersiyon medyanı 0.0209, eşiğin altında %0.0 zaman
#   10 coin (temiz)      : dispersiyon medyanı 0.0162, eşiğin altında %2.1 zaman
# Donuk coinler (fiyatı hiç değişmeyenler) dispersiyonu YAPAY OLARAK
# YÜKSELTİYOR - hareketsiz bir seri diğerlerinden "ayrışmış" görünüyor.
#
# Canlı bot 30 coin tarıyor ve likidite filtresi ölü coinleri eliyor,
# yani gerçek dispersiyon temiz-10 senaryosuna daha yakın olmalı.
# Filtre canlıda backtest'tekinden DAHA SIK devreye girebilir.
# Loglarda "Dispersiyon düşük" mesajının sıklığını izleyin: %10'u
# geçiyorsa eşik düşürülmeli (0.004 veya 0.003).
DISPERSION_WINDOW_BARS = 180     # kaç barlık geçmişten ölçülecek (~30 gün @4h)

USE_LIQUIDITY_FILTER = True
MIN_DEPTH_USDT = 200_000.0       # ilk 20 seviyede en az bu kadar hacim
MAX_SLIPPAGE_PCT = 0.25          # tahmini gidiş-dönüş slippage üst sınırı
# Likidite hızlı değişmez (bir coinin emir defteri derinliği saatler
# içinde kategori değiştirmez), bu yüzden sonuç önbelleğe alınır.
# Faydası: 30 coin x 5 ağırlık = 150 API ağırlığı ve 30 x 0.1sn = 3sn
# bekleme her turda tekrarlanmıyor. Rate limit kullanımı %12'den
# ~%6'ya iniyor ve dengeleme belirgin hızlanıyor.
# DİKKAT: Bu süre rebalance aralığından UZUN olmalı, yoksa önbellek her
# turda zaten dolmuş olur ve hiç işe yaramaz. Rebalance günlük (24sa)
# olduğu için 72 saat seçildi - önbellek ~3 turda bir yenilenir.
# Likidite bu sürede kategori değiştirmez (bir coin 3 günde likitten
# ilikit hale gelmez; gelirse de MIN_DEPTH eşiği zaten yakalar).
LIQUIDITY_CACHE_HOURS = 72.0
_liquidity_cache = {}            # {sembol: (zaman, uygun_mu, sebep)}


def hesapla_dispersiyon(closes_by_symbol: dict, window: int) -> float:
    """Coinlerin BİRBİRİNDEN ayrışma miktarı (kesitsel getiri std'si).

    Bu stratejinin yakıtı bu. Düşükse işlenecek hammadde yok - hangi
    yöne oynanırsa oynansın kazanılmaz (momentum de denendi, daha kötü).
    """
    seriler = []
    for c in closes_by_symbol.values():
        s = pd.Series(c, dtype="float64")
        if len(s) < window + 1:
            continue
        r = s.pct_change().replace([np.inf, -np.inf], np.nan).tail(window)
        seriler.append(r.values)
    if len(seriler) < 4:
        return float("nan")
    n = min(len(x) for x in seriler)
    M = np.array([x[-n:] for x in seriler])
    # her bar için coinler ARASI std, sonra ortalama
    with np.errstate(invalid="ignore"):
        return float(np.nanmean(np.nanstd(M, axis=0)))


def compute_target_weights(closes_by_symbol: dict, n_legs: int,
                           gross_exposure: float) -> dict:
    """Hedef ağırlıkları hesaplar: {sembol: ağırlık}. Pozitif=long, negatif=short.

    En çok DÜŞENLER long, en çok YÜKSELENLER short (kesitsel ortalamaya dönüş).
    Long ve short tarafı eşit büyüklükte (piyasa nötr).

    USE_MULTI_HORIZON açıksa, tek bir pencere yerine HORIZON_DAYS içindeki
    her pencerenin z-skoru hesaplanıp ortalanır. Tek pencere gürültüye
    duyarlı; çoklu ortalama daha sağlam (ölçüldü: OOS Sharpe 1.75 -> 2.81,
    5/5 yılda daha iyi).
    """
    horizons = [int(h * BARS_PER_DAY) for h in HORIZON_DAYS] if USE_MULTI_HORIZON \
        else [LOOKBACK_BARS]
    need = max(horizons) + 1

    # Yeterli veriye sahip semboller
    usable = {s: c for s, c in closes_by_symbol.items() if len(c) >= need}
    if len(usable) < n_legs * 2:
        logger.warning(f"Yetersiz coin ({len(usable)}), en az {n_legs*2} gerekli "
                       f"(her biri {need} bar veriyle).")
        return {}

    syms = sorted(usable)
    z_sum = np.zeros(len(syms))
    for hb in horizons:
        perf = np.array([
            (float(usable[s][-1]) - float(usable[s][-hb - 1])) / float(usable[s][-hb - 1])
            if float(usable[s][-hb - 1]) > 0 else 0.0
            for s in syms
        ])
        sd = perf.std()
        z_sum += (perf - perf.mean()) / (sd + 1e-9)
    score = z_sum / len(horizons)

    order = np.argsort(score)
    losers = [syms[i] for i in order[:n_legs]]      # en düşük skor -> LONG
    winners = [syms[i] for i in order[-n_legs:]]    # en yüksek skor -> SHORT

    leg_size = (gross_exposure / 2) / n_legs
    weights = {}
    for s in losers:
        weights[s] = leg_size
    for s in winners:
        weights[s] = -leg_size
    return weights


def get_current_weights(exchange: ExchangeClient, balance: float) -> dict:
    """Mevcut açık pozisyonları ağırlık cinsinden döner."""
    current = {}
    if balance <= 0:
        return current
    for p in exchange.get_open_positions():
        amt = float(p.get("positionAmt", 0))
        if amt == 0:
            continue
        mark = float(p.get("markPrice") or p.get("entryPrice") or 0)
        if mark <= 0:
            continue
        current[p["symbol"]] = (amt * mark) / balance
    return current


def _load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict):
    """ATOMİK yazma: önce geçici dosya, sonra os.replace.
    Doğrudan yazarken kesinti olursa (elektrik, kill, disk dolu) dosya
    yarım kalır ve bot bir daha başlamaz. Bu yöntemde dosya ya eski ya
    yeni halidir, asla yarım değil."""
    tmp = STATE_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        logger.warning(f"Durum kaydedilemedi: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def check_drawdown(balance: float) -> tuple:
    """Tepe bakiyeye göre düşüşü kontrol eder. (devam_et, düşüş_yüzdesi) döner.

    Durum dosyası bozuksa (elle düzenlenmiş, disk hatası, yarım yazılmış)
    tepe bakiye mevcut bakiyeden başlatılır. Bot çökmez - en kötü ihtimalle
    düşüş koruması bir süre için sıfırlanır, ki bu güvenli taraftır.
    """
    state = _load_state()
    try:
        onceki_peak = float(state.get("peak_balance", 0.0))
        if not np.isfinite(onceki_peak) or onceki_peak < 0:
            onceki_peak = 0.0
    except (TypeError, ValueError):
        logger.warning("Durum dosyasındaki tepe bakiye okunamadı, sıfırlanıyor.")
        onceki_peak = 0.0
    peak = max(onceki_peak, balance)
    state["peak_balance"] = peak
    _save_state(state)
    if peak <= 0:
        return True, 0.0
    dd = (peak - balance) / peak * 100
    return dd < MAX_DRAWDOWN_PCT, dd


def close_all(exchange: ExchangeClient, dry_run: bool = False):
    """Tüm açık pozisyonları kapatır (devre kesici tetiklendiğinde)."""
    for p in exchange.get_open_positions():
        amt = float(p.get("positionAmt", 0))
        if amt == 0:
            continue
        sym = p["symbol"]
        logger.warning(f"  KAPAT {sym} ({amt})")
        if not dry_run:
            _close_symbol(exchange, sym)
            time.sleep(0.5)


def compute_exposure_scale(drawdown_pct: float) -> float:
    """Tepe bakiyeden düşüşe göre pozisyon büyüklüğü çarpanı (0.0 - 1.0).

    Düşüş 0 ise 1.0 (tam büyüklük), DRAWDOWN_SCALE_FULL_PCT'e ulaşınca 0.0.
    Aradaki her seviyede doğrusal azalır. Toparlandıkça kendiliğinden büyür.
    """
    if not USE_DRAWDOWN_SCALING or DRAWDOWN_SCALE_FULL_PCT <= 0:
        return 1.0
    scale = 1.0 - (drawdown_pct / DRAWDOWN_SCALE_FULL_PCT)
    return float(max(0.0, min(1.0, scale)))


def take_profits(exchange: ExchangeClient, dry_run: bool = False) -> list:
    """Hedefine ulaşan pozisyonları kapatır. Kapatılan sembolleri döner.

    Binance açık pozisyonda gerçekleşmemiş kâr yüzdesini doğrudan verir
    (unRealizedProfit / pozisyon nominali), bu yüzden giriş fiyatını ayrıca
    saklamaya gerek yok - bot yeniden başlasa bile doğru çalışır.
    """
    if not USE_POSITION_TAKE_PROFIT:
        return []
    closed = []
    for p in exchange.get_open_positions():
        amt = float(p.get("positionAmt", 0))
        if amt == 0:
            continue
        entry = float(p.get("entryPrice", 0) or 0)
        mark = float(p.get("markPrice", 0) or 0)
        if entry <= 0 or mark <= 0:
            continue
        # LONG'da fiyat artışı, SHORT'ta düşüşü kârdır
        change_pct = (mark - entry) / entry * 100
        gain_pct = change_pct if amt > 0 else -change_pct
        sym = p["symbol"]
        if gain_pct >= POSITION_TP_PCT:
            logger.info(f"KÂR AL {sym}: +%{gain_pct:.1f} "
                        f"(hedef +%{POSITION_TP_PCT}) - kapatılıyor")
        elif USE_EMERGENCY_STOP and gain_pct <= -EMERGENCY_STOP_PCT:
            # Kuyruk riski koruması - normal işleyişte nadiren tetiklenir
            logger.warning(f"ACİL STOP {sym}: %{gain_pct:.1f} zarar "
                           f"(sınır -%{EMERGENCY_STOP_PCT}) - kapatılıyor")
        else:
            continue
        if not dry_run:
            _close_symbol(exchange, sym)
            time.sleep(0.5)
        closed.append(sym)
    return closed


def log_funding_durumu(exchange: ExchangeClient, target: dict):
    """Açılacak pozisyonların funding oranlarını loglar ve NET etkiyi hesaplar.

    NEDEN ÖNEMLİ: Backtest funding'i sabit %0.01/8sa varsayıyor ve tüm
    pozisyonların maliyet ödediğini kabul ediyor (muhafazakâr). Gerçekte
    funding pozitifken LONG öder, SHORT alır - piyasa nötr portföyde
    büyük ölçüde netleşir.

    Funding, stratejinin en hassas olduğu maliyet kalemi (duyarlılık:
    %0.01 -> Sharpe 2.96, %0.10 -> Sharpe 1.92). Gerçek değerin
    ölçülmesi için bu log tutuluyor. Sadece BİLGİ amaçlı - karar
    vermiyor.
    """
    try:
        toplam_net = 0.0
        satirlar = []
        for sym, w in target.items():
            if abs(w) < 1e-9:
                continue
            try:
                info = exchange.client.futures_mark_price(symbol=sym)
                fr = float(info.get("lastFundingRate", 0)) * 100  # %
            except Exception:
                continue
            # LONG pozisyon funding pozitifse ÖDER (negatif etki),
            # SHORT pozisyon funding pozitifse ALIR (pozitif etki)
            etki = -fr if w > 0 else fr
            toplam_net += etki * abs(w)
            satirlar.append(f"{sym} {'L' if w > 0 else 'S'} %{fr:+.4f}")
        if satirlar:
            yillik = toplam_net * 3 * 365
            logger.info(f"Funding (8sa): net %{toplam_net:+.4f} -> yıllık ~%{yillik:+.1f}")
            logger.info(f"  {' | '.join(satirlar)}")
    except Exception as e:
        logger.debug(f"Funding bilgisi alınamadı: {e}")

def check_liquidity(exchange: ExchangeClient, symbol: str,
                    position_notional: float) -> tuple:
    """Coin bu pozisyon büyüklüğü için yeterince likit mi?

    (uygun_mu, sebep) döner. Emir defterine bakar, emir GÖNDERMEZ.
    Veri alınamazsa GÜVENLİ tarafta kalır: coini ATLAR (aksi halde
    likiditesi bilinmeyen bir coine körlemesine girilirdi).
    """
    if not USE_LIQUIDITY_FILTER:
        return True, ""

    # Önbellek kontrolü - likidite saatler içinde kategori değiştirmez
    simdi = time.time()
    onbellek = _liquidity_cache.get(symbol)
    if onbellek and (simdi - onbellek[0]) < LIQUIDITY_CACHE_HOURS * 3600:
        return onbellek[1], onbellek[2] + " [önbellek]"

    def _kaydet(ok, sebep):
        _liquidity_cache[symbol] = (simdi, ok, sebep)
        return ok, sebep

    try:
        book = exchange.client.futures_order_book(symbol=symbol, limit=100)
    except Exception as e:
        # Hatayı ÖNBELLEĞE ALMA - geçici olabilir, sonraki turda tekrar dene
        return False, f"emir defteri alınamadı ({e})"

    asks, bids = book.get("asks", []), book.get("bids", [])
    if not asks or not bids:
        return False, "emir defteri boş"

    depth_ask = sum(float(p) * float(q) for p, q in asks[:20])
    depth_bid = sum(float(p) * float(q) for p, q in bids[:20])
    depth = min(depth_ask, depth_bid)
    if depth < MIN_DEPTH_USDT:
        return _kaydet(False, f"defter sığ (${depth:,.0f} < ${MIN_DEPTH_USDT:,.0f})")

    buy = simulate_market_order(asks, position_notional)
    sell = simulate_market_order(bids, position_notional)
    if not buy or not sell:
        return _kaydet(False, "dolum simüle edilemedi")
    if buy["filled_pct"] < 99.5 or sell["filled_pct"] < 99.5:
        return _kaydet(False, f"emrin tamamı dolmaz (%{min(buy['filled_pct'], sell['filled_pct']):.0f})")

    best_ask, best_bid = float(asks[0][0]), float(bids[0][0])
    spread_pct = (best_ask - best_bid) / best_bid * 100
    round_trip = buy["slippage_pct"] + sell["slippage_pct"] + spread_pct
    if round_trip > MAX_SLIPPAGE_PCT:
        return _kaydet(False, f"slippage yüksek (%{round_trip:.3f} > %{MAX_SLIPPAGE_PCT})")
    return _kaydet(True, f"likit (defter ${depth:,.0f}, slippage %{round_trip:.3f})")


def rebalance(exchange: ExchangeClient, dry_run: bool = False):
    # Borsa API'si geçici olarak cevap vermeyebilir (ağ, rate limit, bakım).
    # Bu durumda ÇÖKMEK yerine bu turu atlamak gerekir - aksi halde --loop
    # modunda tek bir geçici hata botu tamamen durdurur ve açık pozisyonlar
    # yönetimsiz kalır.
    try:
        balance = exchange.get_account_balance_usdt()
    except Exception as e:
        logger.error(f"Bakiye alınamadı, bu tur atlanıyor: {e}")
        return
    logger.info(f"Bakiye: {balance:.2f} USDT")
    if balance <= 0:
        logger.error("Bakiye sıfır, işlem yapılmıyor.")
        return

    # DEVRE KESİCİ: beklenenin ötesinde düşüş varsa her şeyi kapat ve dur.
    ok, dd = check_drawdown(balance)
    logger.info(f"Tepe bakiyeden düşüş: %{dd:.1f} (limit: %{MAX_DRAWDOWN_PCT})")
    if not ok:
        logger.error(f"DEVRE KESİCİ TETİKLENDİ: düşüş %{dd:.1f} > %{MAX_DRAWDOWN_PCT}. "
                     f"Tüm pozisyonlar kapatılıyor. Bot durduruldu - "
                     f"devam etmek için {STATE_FILE} dosyasını silin ve "
                     f"durumu MANUEL inceleyin.")
        close_all(exchange, dry_run)
        raise SystemExit(1)

    # KÂR ALMA: hedefine ulaşan pozisyonları kapat. Bu, dengelemeden ÖNCE
    # yapılır ki kapatılan pozisyonlar aynı turda yeniden açılmasın.
    tp_closed = take_profits(exchange, dry_run)

    symbols = exchange.get_top_symbols(
        config.SCAN.quote_asset, UNIVERSE_SIZE, config.SCAN.excluded_symbols
    )
    closes = {}
    for sym in symbols:
        try:
            df = exchange.get_klines(sym, TIMEFRAME, REQUIRED_BARS)
            closes[sym] = df["close"].values
        except Exception as e:
            logger.warning(f"{sym} verisi alınamadı: {e}")

    # LİKİDİTE FİLTRESİ: sıralamadan ÖNCE uygulanır. Sonra uygulanırsa
    # elenen coinler yüzünden bacaklar eksik kalırdı; önce eleyince
    # sıralama sadece işlem yapılabilir coinler arasında yapılır.
    if USE_LIQUIDITY_FILTER and closes:
        # Her pozisyon, toplam sermayenin (gross/2)/N_LEGS kadarı
        position_notional = balance * (GROSS_EXPOSURE / 2) / N_LEGS
        liquid = {}
        elenen = []
        for sym in list(closes):
            ok, sebep = check_liquidity(exchange, sym, position_notional)
            if ok:
                liquid[sym] = closes[sym]
            else:
                elenen.append(f"{sym} ({sebep})")
            time.sleep(0.1)  # rate limit koruması
        if elenen:
            logger.info(f"Likidite filtresi {len(elenen)} coin eledi "
                        f"(pozisyon ~${position_notional:,.0f}):")
            for e in elenen:
                logger.info(f"    {e}")
        if len(liquid) < N_LEGS * 2:
            logger.warning(
                f"Likidite filtresinden sonra sadece {len(liquid)} coin kaldı, "
                f"en az {N_LEGS*2} gerekli. Bu turda işlem yapılmıyor. "
                f"MIN_DEPTH_USDT/MAX_SLIPPAGE_PCT gevşetilebilir veya "
                f"UNIVERSE_SIZE artırılabilir.")
            return
        closes = liquid

    # DİSPERSİYON KONTROLÜ: coinler birbirinden ayrışmıyorsa bu stratejinin
    # kazanacağı bir şey yok. Mevcut pozisyonlar normal yönetilmeye devam
    # eder (TP/acil stop çalışır), sadece YENİ pozisyon açılmaz.
    if USE_DISPERSION_FILTER and closes:
        disp = hesapla_dispersiyon(closes, DISPERSION_WINDOW_BARS)
        if np.isfinite(disp):
            if disp < MIN_DISPERSION:
                logger.info(
                    f"Dispersiyon düşük ({disp:.5f} < {MIN_DISPERSION}) - coinler "
                    f"birbirinden ayrışmıyor, yeni pozisyon açılmayacak. "
                    f"Mevcut pozisyonlar yönetilmeye devam ediyor.")
                # Kâr alma / acil stop bu turda ZATEN yapıldı (yukarıda,
                # take_profits çağrısı). Tekrar çağırmak aynı pozisyonu iki
                # kez kapatmaya çalışır.
                return
            logger.info(f"Dispersiyon: {disp:.5f} (eşik {MIN_DISPERSION}) - uygun")
        else:
            logger.warning("Dispersiyon ölçülemedi (veri yetersiz) - filtre atlandı.")

    # --- FAZ DİLİMLEME ---
    # Sermaye PHASE_COUNT dilime bölünür. Her turda SADECE SIRADAKİ dilim
    # yeniden hesaplanır; diğer dilimler önceki hedeflerini korur.
    # Toplam hedef = tüm dilimlerin toplamı.
    #
    # Neden: bot günde bir dengelediğinde HANGİ SAATTE dengelediği sonucu
    # çok değiştiriyor (Sharpe 1.12-2.08, madde 100). Dilimler farklı
    # saatlerde dengelenince bu risk dağılır ve fazlar arası korelasyon
    # 0.405 olduğu için gerçek çeşitlendirme sağlanır.
    # Ölçüldü: tek faz 1.54 -> 3 dilim 2.01 ortalama Sharpe.
    if USE_PHASE_SPLIT and PHASE_COUNT > 1:
        state = _load_state()
        dilimler = state.get("phase_targets", {})     # {"0": {sym: w}, ...}
        sira = int(state.get("next_phase", 0)) % PHASE_COUNT

        # Sıradaki dilimin hedefini yeniden hesapla (sermayenin 1/PHASE_COUNT'i)
        yeni = compute_target_weights(closes, N_LEGS, GROSS_EXPOSURE / PHASE_COUNT)
        if not yeni:
            return
        dilimler[str(sira)] = yeni
        state["phase_targets"] = dilimler
        state["next_phase"] = (sira + 1) % PHASE_COUNT
        _save_state(state)
        logger.info(f"Faz dilimleme: dilim {sira+1}/{PHASE_COUNT} yenilendi "
                    f"(diğer dilimler korunuyor)")

        # Toplam hedef: tüm dilimlerin ağırlıkları toplanır. Aynı coin
        # birden fazla dilimde olabilir - ağırlıkları toplanır, ters
        # yönlerde ise netleşir (borsada zaten tek pozisyon tutulur).
        target = {}
        for d in dilimler.values():
            for sym, w in d.items():
                target[sym] = target.get(sym, 0.0) + w
        # Netleşme sonucu sıfıra çok yakın kalanları ele
        target = {k: v for k, v in target.items() if abs(v) > 1e-6}
    else:
        target = compute_target_weights(closes, N_LEGS, GROSS_EXPOSURE)

    if not target:
        return

    # Kâr geri verme koruması: tepeden uzaklaştıkça küçül, toparlandıkça büyü.
    scale = compute_exposure_scale(dd)
    if scale < 1.0:
        logger.info(f"Düşüş nedeniyle pozisyon büyüklüğü %{scale*100:.0f}'e "
                    f"ölçekleniyor (koruma aktif)")
        target = {sym: w * scale for sym, w in target.items()}
        if scale <= 0.01:
            logger.warning("Ölçek sıfıra yakın - tüm pozisyonlar kapatılacak, "
                           "toparlanma beklenecek.")

    current = get_current_weights(exchange, balance)

    log_funding_durumu(exchange, target)

    logger.info("--- HEDEF PORTFÖY ---")
    for sym, w in sorted(target.items(), key=lambda kv: -kv[1]):
        yon = "LONG " if w > 0 else "SHORT"
        logger.info(f"  {yon} {sym:<12} ağırlık={abs(w)*100:5.1f}%")

    # Hedefte olmayan VEYA hedef ağırlığı sıfırlanmış pozisyonları kapat.
    # İkinci durum, düşüş koruması exposure'ı sıfıra çektiğinde oluşur:
    # sembol hâlâ "hedef" sözlüğünde ama ağırlığı 0. Bunu fark
    # hesabına bırakmak yetmez (piyasa emriyle ters yön açmaya çalışırdı),
    # pozisyonun düpedüz kapatılması gerekir.
    for sym, w in current.items():
        if abs(w) <= 0.001:
            continue
        target_w = target.get(sym, 0.0)
        if sym not in target or abs(target_w) < 1e-9:
            sebep = "artık hedefte değil" if sym not in target else "koruma nedeniyle sıfırlandı"
            logger.info(f"KAPAT {sym} ({sebep}, mevcut ağırlık {w*100:+.1f}%)")
            if not dry_run:
                _close_symbol(exchange, sym)
                time.sleep(0.5)

    # Hedef ağırlıklara getir
    for sym, tw in target.items():
        if abs(tw) < 1e-9:
            continue  # yukarıda kapatıldı
        if sym in tp_closed:
            # Bu tur kâr alınan sembolü hemen geri açma - yoksa kâr alma
            # anlamsız olur (kapat-hemen aç döngüsü, sadece komisyon öder).
            # Bir sonraki dengelemede hâlâ hedefteyse normal açılır.
            logger.info(f"  {sym}: bu tur kâr alındı, yeniden açılmıyor")
            continue
        cw = current.get(sym, 0.0)
        diff = tw - cw
        # Küçük sapmalar için işlem yapma (komisyon yer)
        if abs(diff) < 0.01:
            logger.info(f"  {sym}: sapma küçük ({diff*100:+.1f}%), dokunulmuyor")
            continue
        notional = abs(diff) * balance
        side = "BUY" if diff > 0 else "SELL"
        logger.info(f"  {sym}: {cw*100:+.1f}% -> {tw*100:+.1f}% | {side} ~{notional:.2f} USDT")
        if not dry_run:
            _adjust_symbol(exchange, sym, side, notional)
            time.sleep(0.5)


def _close_symbol(exchange: ExchangeClient, symbol: str):
    for p in exchange.get_open_positions():
        if p["symbol"] != symbol:
            continue
        amt = float(p.get("positionAmt", 0))
        if amt == 0:
            continue
        side = "SELL" if amt > 0 else "BUY"
        try:
            exchange.cancel_all_open_orders(symbol)
            exchange.close_position(symbol, side, abs(amt))
            logger.info(f"    {symbol} kapatıldı.")
        except Exception as e:
            logger.error(f"    {symbol} kapatılamadı: {e}")


def _adjust_symbol(exchange: ExchangeClient, symbol: str, side: str, notional: float):
    # Binance Futures'ta emirlerin minimum nominal değeri vardır (genelde
    # 5 USDT). Altında kalan emirler borsa tarafından reddedilir, bu yüzden
    # hiç göndermiyoruz - aksi halde her dengelemede hata logu birikir.
    MIN_NOTIONAL_USDT = 5.0
    if notional < MIN_NOTIONAL_USDT:
        logger.info(f"    {symbol}: nominal çok küçük ({notional:.2f} USDT "
                    f"< {MIN_NOTIONAL_USDT}), atlanıyor")
        return
    try:
        df = exchange.get_klines(symbol, TIMEFRAME, 2)
        price = float(df["close"].iloc[-1])
        if price <= 0:
            logger.warning(f"    {symbol}: geçersiz fiyat, atlanıyor")
            return
        prec = exchange.get_symbol_precision(symbol)
        qty_prec = int(prec.get("quantity_precision", 3))
        qty = round(notional / price, qty_prec)
        if qty <= 0:
            logger.info(f"    {symbol}: yuvarlama sonrası miktar sıfır, atlanıyor")
            return
        exchange.open_market_position(symbol, side, qty)
        logger.info(f"    {symbol} {side} {qty} gerçekleşti.")
    except Exception as e:
        logger.error(f"    {symbol} emri başarısız: {e}")


def main():
    ap = argparse.ArgumentParser(description="Kesitsel ortalamaya dönüş botu")
    ap.add_argument("--dry-run", action="store_true",
                    help="Hiç emir gönderme, sadece ne yapacağını göster")
    ap.add_argument("--loop", action="store_true",
                    help=f"Sürekli çalış (her {REBALANCE_DAYS*24:.0f} saatte bir dengele)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if not config.API_KEY or not config.API_SECRET:
        logger.error("API anahtarları eksik. .env dosyasını kontrol edin.")
        return

    exchange = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    logger.info(f"Mod: {config.BINANCE_MODE} | Strateji: kesitsel ortalamaya dönüş")
    logger.info(f"Ayar: {LOOKBACK_DAYS}g lookback, {REBALANCE_DAYS*24:.1f} saatte bir "
                f"rebalance, {N_LEGS}+{N_LEGS} coin, gross={GROSS_EXPOSURE}x")
    if args.dry_run:
        logger.info(">>> DRY-RUN: hiçbir emir gönderilmeyecek <<<")

    # Bağlantıyı erkenden doğrula ki, anlaşılmaz bir yığın izi yerine
    # ne olduğunu söyleyen bir mesaj görülsün.
    try:
        exchange.get_account_balance_usdt()
    except Exception as e:
        msg = str(e)
        if "restricted location" in msg or "451" in msg:
            logger.error(
                "Binance API'ye bu ağdan erişilemiyor (coğrafi/yasal kısıtlama). "
                "Bu, API anahtarlarınızla ilgili DEĞİL - sunucunun bulunduğu "
                "bölgeyle ilgili. Botu kendi bilgisayarınızdan çalıştırmayı deneyin."
            )
        elif "API-key" in msg or "signature" in msg.lower():
            logger.error(f"API anahtarı reddedildi: {e}\n"
                         f"BINANCE_MODE={config.BINANCE_MODE} ayarının anahtarların "
                         f"alındığı ortamla eşleştiğinden emin olun.")
        else:
            logger.error(f"Borsaya bağlanılamadı: {e}")
        return

    if args.loop:
        # FAZ DİLİMLEME: sermayeyi PHASE_COUNT dilime böl, her dilimi
        # farklı saatte dengele. Dengeleme saati riskini ortadan kaldırır
        # (bkz. USE_PHASE_SPLIT açıklaması).
        #
        # UYGULAMA: her turda SADECE sıradaki dilimin hedefi yeniden
        # hesaplanır (bkz. rebalance içindeki faz dilimleme bloğu).
        # Diğer dilimler önceki hedeflerini korur; toplam hedef hepsinin
        # birleşimidir. Böylece pozisyonlar zaman içine yayılır.
        if USE_PHASE_SPLIT and PHASE_COUNT > 1:
            interval = REBALANCE_DAYS * 24 * 3600 / PHASE_COUNT
            logger.info(
                f"FAZ DİLİMLEME AKTİF: {PHASE_COUNT} dilim, "
                f"{24/PHASE_COUNT:.0f} saatte bir dengeleme. "
                f"Her turda sermayenin ~1/{PHASE_COUNT}'i yeniden konumlanır - "
                f"dengeleme saati riski dağıtılır.")
        else:
            interval = REBALANCE_DAYS * 24 * 3600
        ardisik_hata = 0
        MAX_ARDISIK_HATA = 5
        while True:
            try:
                rebalance(exchange, args.dry_run)
                ardisik_hata = 0
            except SystemExit:
                # Devre kesici tetiklendi - bu KASITLI bir duruş, yutulmamalı.
                raise
            except KeyboardInterrupt:
                logger.info("Kullanıcı durdurdu.")
                raise
            except Exception as e:
                ardisik_hata += 1
                logger.error(f"Dengeleme hatası ({ardisik_hata}/{MAX_ARDISIK_HATA}): {e}")
                # Üst üste hata alıyorsak ortada yapısal bir sorun var
                # (API anahtarı iptal edilmiş, borsa erişimi kesilmiş vb.).
                # Sonsuza kadar denemek yerine durup insana haber ver.
                if ardisik_hata >= MAX_ARDISIK_HATA:
                    logger.error(
                        f"{MAX_ARDISIK_HATA} kez üst üste hata alındı - bot durduruluyor. "
                        f"AÇIK POZİSYONLAR VARSA MANUEL KONTROL EDİN.")
                    raise SystemExit(1)
            logger.info(f"Sonraki dengeleme {REBALANCE_DAYS*24:.1f} saat sonra.")
            time.sleep(interval)
    else:
        rebalance(exchange, args.dry_run)


if __name__ == "__main__":
    main()
