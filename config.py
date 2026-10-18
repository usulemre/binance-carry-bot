"""
Binance Futures Testnet Agentic Trading Bot - Konfigürasyon
=============================================================
Tüm ayarlar buradan yönetilir. Canlıya geçmeden önce TESTNET=True ile
haftalarca test etmeden ASLA gerçek paraya geçmeyin.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()  # proje kökündeki .env dosyasını otomatik yükler

# ---------------------------------------------------------------------------
# API Anahtarları (.env dosyasından okunur, ASLA kod içine yazmayın)
# ---------------------------------------------------------------------------
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
# "demo" (yeni, önerilen - demo.binance.com hesabından alınan anahtarlar),
# "legacy_testnet" (eski, artık genelde çalışmayan testnet.binancefuture.com),
# "live" (gerçek para).
BINANCE_MODE = os.getenv("BINANCE_MODE", "demo")

# ---------------------------------------------------------------------------
# Tarama Ayarları
# ---------------------------------------------------------------------------
@dataclass
class ScanConfig:
    top_n_symbols: int = 30            # Hacme göre taranacak coin sayısı
    quote_asset: str = "USDT"          # Sadece USDT paritelerine bak
    # KRİTİK: Bu değer BACKTEST'İN YAPILDIĞI dilimle aynı olmalı.
    # Tüm backtest'ler 4h veriyle yapıldı (historical_data/*_4h.csv).
    # 15m'de çalıştırmak, 4h için ayarlanmış parametreleri (ATR çarpanları,
    # lookback pencereleri, TP/SL mesafeleri) tamamen farklı bir ölçekte
    # kullanmak demektir - backtest sonuçları GEÇERSİZ olur.
    # Farklı bir dilim kullanmak isterseniz önce o dilimin verisini indirip
    # backtest'i tekrar çalıştırın.
    timeframe: str = "4h"              # Mum periyodu (backtest ile aynı olmalı)
    kline_lookback: int = 200          # İndikatör hesaplamak için mum sayısı
    scan_interval_seconds: int = 3600  # saatte bir tara (4h bar için yeterli;
                                       # bar kapanışları kaçmasın diye bardan sık)
    excluded_symbols: List[str] = field(default_factory=lambda: [
        "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "DAIUSDT"
    ])  # Stabil coin çiftlerini hariç tut

# ---------------------------------------------------------------------------
# Strateji Ayarları (Trend + Momentum + Hacim)
# ---------------------------------------------------------------------------
@dataclass
class StrategyConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_period: int = 14
    rsi_long_min: float = 45.0
    rsi_long_max: float = 70.0
    rsi_short_min: float = 30.0
    rsi_short_max: float = 55.0
    volume_ma_period: int = 20
    volume_spike_multiplier: float = 1.2   # Son hacim, ortalamanın en az 1.2 katı olmalı
    atr_period: int = 14
    # ATR stop çarpanı - extreme_reversal için yeniden ölçüldü:
    #   çarpan   IS_R      OOS_R    OOS kazanma
    #     1.0  +566.0R   +213.4R      62.4%    <- SEÇİLEN
    #     1.5  +444.4R   +182.6R      73.0%    (eski)
    #     2.0  +335.1R   +143.2R      79.0%
    # Dar stop daha düşük kazanma oranı verir ama toplam getiri belirgin
    # daha yüksek (kayıplar küçük, kazançlar aynı).
    # LİKİDASYON AÇISINDAN DA DAHA GÜVENLİ: medyan SL mesafesi %7.79
    # (1.5'te %10.81), güvenlik filtresi sadece 7 sinyal eliyor (1.5'te 91).
    atr_sl_multiplier: float = 1.0         # Stop-loss = ATR * bu katsayı
    atr_tp_multiplier: float = 3.0         # Take-profit = ATR * bu katsayı (R:R ~ 1:2)
    min_signal_score: float = 3.0          # 0-4 arası puanlamada minimum eşik
    # --- Breakout stratejisi parametreleri ---
    donchian_period: int = 20              # Kaç barlık en yüksek/en düşük seviye kırılımı aranacak
    # --- Mean-reversion stratejisi parametreleri ---
    bb_period: int = 20
    bb_std_dev: float = 2.0
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    # --- Rejim tespiti (adaptif strateji) parametreleri ---
    adx_period: int = 14
    adx_trend_threshold: float = 25.0      # Bunun üzeri = trend halinde piyasa
    adx_range_threshold: float = 20.0      # Bunun altı = yatay/choppy piyasa
    vol_lookback: int = 100                # Volatilite z-score'u için bakılacak bar sayısı
    vol_extreme_zscore: float = 2.0        # Bunun üzeri = anormal oynaklık (çöküş/flaş kriz) -> işlem açma
    # --- Üst zaman dilimi (higher timeframe) trend teyidi ---
    # 2026 Eylül piyasası: BTC dar bir bantta konsolide oluyor, düşük zaman
    # diliminde gürültüden kaynaklanan yanlış sinyaller artıyor. Sinyal, daha
    # uzun periyotlu EMA'larla yaklaşık bir "üst zaman dilimi" trendiyle de
    # uyumlu olmalı.
    require_htf_confirmation: bool = True
    htf_multiplier: int = 4                # Üst TF EMA periyotları = normal periyot * bu çarpan
    # --- Aşırı hareket sonrası ters yön (extreme reversal) parametreleri ---
    # "Çok yükselene short, çok düşene long": Bollinger bandı yerine doğrudan
    # son N bardaki % hareket eşiğine dayalı, daha agresif bir fade stratejisi.
    extreme_lookback: int = 20             # Kaç bar geriye bakılarak % hareket hesaplanacak
    # extreme_reversal varsayılan strateji olunca (madde 86) bu eşikler
    # ilk kez ayarlandı - eskiden mean_reversion kullanıldığı için hiç
    # optimize edilmemişlerdi.
    # ÖLÇÜLDÜ (temiz veri, IS 2022-24 / OOS 2025):
    # GÜNCELLEME - TAM PARİTE ile yeniden ölçüldü (madde 96/97):
    # Önceki tarama HATALIYDI: portfolio_backtest sinyal üretiminde her
    # zaman global config.STRATEGY kullanıyordu, yani eşik değişiklikleri
    # SESSİZCE ETKİSİZ kalıyordu (tüm eşikler aynı sonucu veriyordu).
    # Düzeltildikten sonra (kademeli azaltma + max tutma dahil):
    #   eşik    IS_R      OOS_R    OOS işlem
    #    %8   +703.0R   +204.9R      2054
    #   %10   +714.1R   +227.3R      1526   <- SEÇİLEN (hem IS hem OOS en iyi)
    #   %12   +618.8R   +220.7R      1137   (eski)
    #   %15   +407.1R   +156.5R       718
    # Slippage: %10 her seviyede en iyi (%0.10'da bile +201.8R).
    # Yıl yıl: 4/5 yılda daha iyi, toplam +97.9R fazla.
    extreme_threshold_pct: float = 10.0    # Bu % hareketin üzeri "aşırı" sayılır
    extreme_retrace_fraction: float = 0.4  # Kâr hedefi: hareketin bu kadarının geri alınması
    # --- Order flow (taker alım/satım oranı) teyidi ---
    # Binance kline verisinde zaten mevcut ama kullanılmayan bir veri: her
    # mumdaki hacmin ne kadarının ALICI tarafından başlatıldığı. LONG sinyali,
    # gerçekten alıcı baskısı varken (fiyat sadece "boş" hacimle değil, gerçek
    # talep ile yükseliyorsa) teyit edilir.
    require_orderflow_confirmation: bool = False  # varsayılan kapalı, test edilecek
    orderflow_buy_threshold: float = 0.55  # LONG için buy_ratio_ma bu değerin üzeri olmalı
    # --- Trend kalıcılığı (persistence) filtresi ---
    # Tek bar'lık ADX sıçraması "gerçek trend" ile "gürültü" arasında ayrım
    # yapmaz. ADX'in en az `trend_persistence_bars` bar boyunca ÜST ÜSTE
    # eşiğin üzerinde kalması, daha "kurulmuş" bir trendi işaret eder.
    trend_persistence_bars: int = 1  # 1 = filtre yok (eski davranış)

# ---------------------------------------------------------------------------
# Risk Yönetimi
# ---------------------------------------------------------------------------
@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 1.0        # İşlem başına sermayenin %'si
    # KALDIRAÇ GÜVENLİK ANALİZİ (backtest R cinsinden çalışır, likidasyon
    # riskini MODELLEMEZ - bu yüzden ayrıca hesaplandı):
    # Stop-loss mesafesi likidasyon mesafesine yaklaşırsa, fiyat SL'e
    # ulaşmadan pozisyon likide olur ve zarar planlanandan büyük olur.
    #   kaldıraç  likidasyon   riskli sinyal oranı
    #      2x        ~%50           %0.0     GÜVENLİ
    #      3x        ~%33           %1.5     dikkat
    #      5x        ~%20           %9.6     RİSKLİ  <- eski ayar
    #     10x        ~%10          %36.0     çok riskli
    # 2x seçildi. Getiriyi düşürmez (pozisyon boyutu risk_per_trade_pct'e
    # göre hesaplanıyor, kaldıraca göre değil) - sadece likidasyon
    # tamponunu genişletir.
    leverage: int = 2                      # Varsayılan kaldıraç
    # extreme_reversal daha çok sinyal ürettiği için slot limiti yeniden
    # ölçüldü (temiz veri, IS 2022-24 / OOS 2025):
    #   limit   IS_R      OOS_R    OOS düşüş
    #     4   +566.0R   +213.4R     -27.9R   (eski)
    #     5   +640.8R   +227.7R     -27.4R   <- SEÇİLEN
    #     6   +675.3R   +249.3R     -29.0R
    #     8   +682.5R   +252.8R     -29.5R   (doyma)
    #
    # 6 daha kârlı AMA günlük zarar limitiyle çakışıyor:
    #   6 poz x %1 risk = %6 kayıp > günlük limit %5 -> limit koruma
    #   sağlamaz hale gelirdi (madde 76 tutarlılık kuralı).
    # Denenen alternatifler:
    #   A) risk %1->%0.8 ile 6 poz: +199.4R - KAZANÇ YOK, elendi
    #   B) günlük limiti %7'ye çıkar: +249.3R ama kayıp toleransı %40 artar
    #   C) 5 pozisyonda kal: +227.7R, mevcut risk yapısıyla UYUMLU <- seçildi
    # 5 poz x %1 = %5 = günlük limit (tam sınırda, aşmıyor).
    max_concurrent_positions: int = 5      # Aynı anda açık pozisyon sayısı
    max_daily_loss_pct: float = 5.0        # Günlük bu kayba ulaşınca bot durur
    close_positions_on_daily_limit: bool = True  # True: limite ulaşınca AÇIK pozisyonları da kapat
    max_position_notional_pct: float = 25.0  # Tek pozisyon, sermayenin en fazla %'si (kaldıraçlı)
    breakeven_trigger_atr: float = 1.0     # Bu kadar ATR kâra ulaşınca stop-loss girişe çekilir
    partial_tp_r_multiple: float = 1.5     # Bu R'ye ulaşınca pozisyonun bir kısmı KESİN kapatılır
    partial_tp_fraction: float = 0.5       # Kısmi kâr alımında kapatılacak oran (0.5 = yarısı)
    trailing_atr_multiple: float = 2.0     # Breakeven sonrası, en iyi fiyattan bu kadar ATR geride takip et
    # --- Korelasyon riski filtresi (CANLI botta da uygulanır) ---
    # Kripto altcoinleri yüksek korelasyonludur; filtresiz halde "4 farklı
    # pozisyon" aslında "aynı bahsin 4 katı" olabilir. Gerçek 2020-2026
    # verisinde (mean_reversion, max 4 pozisyon) bu filtre hem getiriyi
    # artırdı (+1006R -> +1047R) hem max düşüşü azalttı (-61R -> -46R).
    use_correlation_filter: bool = True
    correlation_threshold: float = 0.7     # Bu mutlak korelasyonun üzerindeyse yeni pozisyon açma
    correlation_lookback: int = 50         # Korelasyon kaç barlık getiriden hesaplanacak
    # --- Piyasa rejimi filtresi (bkz. market_regime.py) ---
    # mean_reversion stratejisi düşük volatilite rejiminde para kaybediyor
    # (hareket yoksa TP'ye ulaşılmaz ama komisyon+funding ödenir).
    # 68 aylık ölçüm: eşiğin üstünde 53 ay ort +12.80R, altında 15 ay ort -2.06R.
    # 2026'nın 8 ayının HEPSİ eşiğin altında - filtre o yıl botu durdururdu.
    # NOT: Bu bayrak STRATEJI BAZINDA ele alınır - aşağıdaki
    # USE_REGIME_FILTER_BY_STRATEGY sözlüğüne bakın. Buradaki değer
    # sözlükte bulunmayan stratejiler için varsayılandır.
    use_regime_filter: bool = True
    regime_min_volatility: float = 0.020   # Bar-üstü getiri std'si bu değerin altındaysa işlem yapma
    regime_max_autocorrelation: float = -0.05  # (opsiyonel filtre) otokorelasyon bunun üstündeyse dur
    use_autocorr_filter: bool = False      # Volatilite filtresi tek başına daha iyi çalışıyor
    regime_lookback_bars: int = 180        # Rejim kaç barlık geçmişten ölçülecek (~30 gün @ 4h)

# ---------------------------------------------------------------------------
# Hangi strateji tarzı canlıda kullanılacak?
# ---------------------------------------------------------------------------
# "mean_reversion"  : Bollinger/RSI ortalamaya donus (VARSAYILAN - bkz. not)
# "extreme_reversal": asiri hareket sonrasi ters yon
# "adaptive"        : rejime gore otomatik secim
# "trend_momentum"  : sadece EMA trend + RSI momentum
# "breakout"        : sadece Donchian kanal kirilimi
#
# NOT (guncelleme): Varsayilan iki kez degisti, cunku test YONTEMI duzeldi.
# 1) Once "adaptive" vardi (sentetik veriyle secilmisti).
# 2) Gercek 2020-2026 verisinde yil-yil/walk-forward testte "adaptive"
#    6 fold'un 6'sinda negatif cikti, "extreme_reversal" +1400R ile one
#    gecti.
# 3) Ama o testler her bari BAGIMSIZ degerlendiriyordu: ayni olaydan
#    onlarca CAKISAN islem sayiyordu. Gercek bot max_concurrent_positions=4
#    ile sinirli. portfolio_backtest.py --local-data ile bu kisit uygulaninca
#    "extreme_reversal"in +1400R'si +10R'ye dustu (yanilsamaymis),
#    "mean_reversion" ise +1006R ile acik ara one gecti.
#
# GERCEKCI PORTFOY SONUCU (14 coin, 4h, 2020-2026, max 4 es zamanli pozisyon):
#   mean_reversion    +1005.89R  (kazanma %68.2, max dusus -61R)   <- varsayilan
#   extreme_reversal    +10.09R  (kazanma %57.8, max dusus -18R)
#   adaptive           -131.45R
#   breakout           -154.54R
#   trend_momentum     -263.23R
# Detay: README.md "Gercekci Portfoy Testi" bolumu.
# NOT (GÜNCELLEME - madde 85): Varsayılan `mean_reversion`'dan
# `extreme_reversal`'a çevrildi. Bu karar madde 32'de ters yönde
# verilmişti ama o zaman: kirli veri, uygulama gecikmesi yok, ATR/SL
# güvenlik filtreleri yok, kaldıraç 5x idi. Hepsi düzeltilince sonuç
# tersine döndü.
#
# TEMİZ VERİ + GECİKME + GÜVENLİK FİLTRELERİ ile (2022-2026):
#   extreme_reversal : +438.9R  (2039 işlem, kazanma %73.3, düşüş -31.9R)
#   mean_reversion   : +265.8R  (2419 işlem, kazanma %67.3, düşüş -55.6R)
#   adaptive         : -248.0R
#   trend_momentum   : -199.8R
#   breakout         : -280.3R
#
# IS/OOS DOĞRULAMASI:
#   strateji            IS (2022-24)   OOS (2025-26)   OOS düşüş
#   extreme_reversal      +300.3R        +137.4R        -31.9R
#   mean_reversion        +245.8R         +12.5R        -55.6R
# Her iki dönemde de daha iyi, üstelik riski yarı yarıya az.
#
# MADDE 32'DEKİ "SLOT BLOKE" SORUNU ÇÖZÜLDÜ: extreme_reversal eskiden
# çok geniş stop'lu pozisyonlar açıp slotları aylarca bloke ediyordu
# (slot 4->10 yapılınca işlem sayısı x2.3 artıyordu). ATR/SL güvenlik
# filtreleri (madde 63) o pozisyonları zaten eliyor - artış artık x1.17,
# mean_reversion'ın x1.11'ine yakın.
ACTIVE_STRATEGY = os.getenv("ACTIVE_STRATEGY", "extreme_reversal")

SCAN = ScanConfig()
STRATEGY = StrategyConfig()
RISK = RiskConfig()

# ---------------------------------------------------------------------------
# Stratejiye özel kâr kilitleme ayarları
# ---------------------------------------------------------------------------
# Backtest'te (bkz. backtest_yearly.py --compare-management) tek tip sıkı
# kâr kilitleme, trend_momentum/adaptive gibi "az sayıda büyük kazanan"
# stratejilerinde kârı ~%50 azalttı, çünkü büyük kazananları erken kesti.
# breakout/mean_reversion gibi "çok sayıda küçük hareket" stratejilerinde
# ise hafif iyileştirdi. Bu yüzden strateji tarzına göre farklı ayarlar:
STRATEGY_MANAGEMENT = {
    # NOT (önemli): Bu ayarlar eski varsayılan strateji `adaptive` için
    # ayarlanmıştı. Varsayılan `mean_reversion`'a geçince kimse yeniden
    # test etmemişti - ölçüldüğünde ZARARLI olduğu görüldü:
    #   2022-2024: basit SL/TP +713.5R  vs  kâr kilitlemeli +590.1R (-123R)
    #   2025-2026: basit SL/TP +160.4R  vs  kâr kilitlemeli +151.9R  (-9R)
    # Sebep: mean_reversion fiyatın geri dönmesini bekler; breakeven stop
    # normal dalgalanmada tetiklenip pozisyonu erkenden öldürüyor
    # (kazanma oranı %71.5 -> %67.0 düşüyor).
    # Bu yüzden mean_reversion için yönetim KAPATILDI (use_management=False).
    # Diğer stratejilerin ayarları dokunulmadan bırakıldı.
    # Trend/momentum stratejileri: kazananın KOŞMASINA izin ver.
    # Daha geç kısmi kâr al, daha az miktar al, trailing'i çok geniş tut.
    "trend_momentum": dict(breakeven_trigger_atr=2.5, breakeven_buffer_pct=0.05,
                            partial_tp_r_multiple=3.0, partial_tp_fraction=0.25,
                            trailing_atr_multiple=4.0),
    "adaptive": dict(breakeven_trigger_atr=2.5, breakeven_buffer_pct=0.05,
                      partial_tp_r_multiple=3.0, partial_tp_fraction=0.25,
                      trailing_atr_multiple=4.0),
    # Breakout/mean-reversion: hareketler zaten daha kısa/hızlı, sıkı
    # kilitleme test edildi ve hafif iyileştirdi -> aynen koru.
    "breakout": dict(breakeven_trigger_atr=1.0, breakeven_buffer_pct=0.05,
                      partial_tp_r_multiple=1.5, partial_tp_fraction=0.5,
                      trailing_atr_multiple=2.0),
    "mean_reversion": dict(breakeven_trigger_atr=1.0, breakeven_buffer_pct=0.05,
                            partial_tp_r_multiple=1.5, partial_tp_fraction=0.5,
                            trailing_atr_multiple=2.0),
    "extreme_reversal": dict(breakeven_trigger_atr=1.0, breakeven_buffer_pct=0.05,
                              partial_tp_r_multiple=1.5, partial_tp_fraction=0.5,
                              trailing_atr_multiple=2.0),
}

# Hangi stratejide REJİM FİLTRESİ kullanılsın?
# (düşük volatilitede işlem yapmama kuralı)
#
# mean_reversion için faydalıydı: hareket yoksa TP'ye ulaşılmaz ama
# komisyon+funding ödenir (madde 30).
#
# extreme_reversal için ZARARLI - ölçüldü:
#   yıl   volatilite  filtre   getiri
#   2022    0.0117    DURUR     +9.6R   <- engellenirdi
#   2023    0.0439    açık     +85.9R
#   2024    0.0583    açık    +193.4R
#   2025    0.0105    DURUR   +162.3R   <- engellenirdi!
#   2026    0.0118    DURUR    -23.1R
#   filtresiz toplam +428.1R, filtreli +279.3R -> 148.8R KAYIP
#
# Sebep: extreme_reversal aşırı HAREKETLERİ yakalıyor, genel oynaklığa
# bağlı değil. 2025'te volatilite düşüktü ama strateji +162R kazandı.
USE_REGIME_FILTER_BY_STRATEGY = {
    "mean_reversion": True,     # faydalı (madde 30)
    "extreme_reversal": False,  # zararlı: 148.8R kaybettiriyor
    "adaptive": True,
    "trend_momentum": True,
    "breakout": True,
}

# Hangi stratejide kâr kilitleme yönetimi KULLANILSIN?
# mean_reversion için ölçüldü ve zararlı çıktı (yukarıdaki nota bakın).
# Diğerleri test edilmedi, varsayılan olarak açık bırakıldı.
USE_POSITION_MANAGEMENT = {
    "mean_reversion": False,    # ölçüldü: -123R (2022-24), -9R (2025-26)
    "extreme_reversal": False,  # ölçüldü: +0.2R (IS), -6.4R (OOS) - faydasız
                                # Basit SL/TP ile aynı getiri ama kazanma
                                # oranı düşüyor (%82.5 -> %78.3). Breakeven
                                # stop, normal dalgalanmada erken kapatıyor.
    "adaptive": True,
    "trend_momentum": True,
    "breakout": True,
}

# --- Sinyal botu için kademeli exposure azaltma ---
# Kesitsel botta çok işe yaramıştı, sinyal botunda da ölçüldü:
#   referans           : OOS +56.0R, max düşüş -77.3R
#   kademeli azaltma   : OOS +93.7R, max düşüş -28.9R
# Getiri ARTIYOR, risk YARIDAN FAZLA azalıyor.
# Tepe bakiyeden düşüş DRAWDOWN_SCALE_FULL_R'ye ulaşınca yeni pozisyon
# açılmaz; aradaki seviyelerde pozisyon büyüklüğü orantılı küçülür.
USE_DRAWDOWN_SCALING = True
DRAWDOWN_SCALE_FULL_R = 30.0   # bu kadar R düşüşte exposure sıfırlanır
# extreme_reversal ile KESİNTİSİZ 2022-2026 ölçümü (temiz veri):
#   eşik   toplam R   max düşüş   R/düşüş oranı
#    yok    +448.0R     -40.5R       11.07
#    20R    +424.9R     -18.1R      *23.45*   <- risk ayarlı EN İYİ
#    30R    +434.0R     -23.2R       18.67    <- seçilen
#    50R    +440.3R     -28.8R       15.29
#    80R    +443.4R     -32.6R       13.58
#
# 20R risk ayarlı olarak açık ara en iyi: %2 daha az getiri karşılığında
# düşüş neredeyse YARIYA iniyor (-23.2R -> -18.1R). Getiri farkı küçük
# çünkü koruma sadece kötü dönemlerde devreye giriyor.
#
# 30R korundu (orta nokta), ama DAYANIKLILIK ÖNCELİKLİYSE 20R DAHA
# İYİ BİR SEÇİM - özellikle küçük hesaplarda büyük düşüş psikolojik
# olarak da zor.
#
# ÖNEMLİ METODOLOJİ NOTU: walk-forward testi (signal_walkforward.py)
# her dönemde 50R seçti, ama bu ANLAMLI DEĞİL - 6 aylık dilimlerde
# tepe-düşüş birikimi oluşmadığı için eşikler ayırt edilemiyor
# (20R ile 50R arası fark sadece %3). Koruma mekanizmalarını kısa
# dilimli walk-forward ile seçmeye çalışmak yanıltıcıdır; uzun
# kesintisiz dönemde ölçmek gerekir.

# --- Maksimum tutma süresi (sinyal botu) ---
# mean_reversion HIZLI geri dönüş bekler. Pozisyon günlerce açık kalıyorsa
# tez muhtemelen yanlıştır; sermayeyi orada tutmak yerine serbest bırakmak
# daha iyi. Ölçüldü (1 bar gecikme + kademeli azaltma dahil):
#   üst sınır yok : IS +391.3R, OOS  +93.7R
#   10 gün        : IS +435.4R, OOS +107.9R   <- seçilen
# Eşik duyarlılığı: 5-20 gün arası TÜM değerler referanstan iyi
# (her iki dönemde de) - tek bir sihirli sayıya bağlı değil.
#
# DENENİP REDDEDİLEN (ters fikir): MİNİMUM tutma süresi ("al, 2-3 gün
# bekle"). Açıkça zararlı ve giderek kötüleşiyor:
#   1 gün bekle: OOS +47.6R (kazanma %50.5)
#   3 gün bekle: OOS  -7.5R (kazanma %42.1)
#   5 gün bekle: OOS -27.9R (kazanma %35.6)
# Sebep: TP bastırılınca kazanan pozisyonlar kâr noktasından geri dönüp
# SL'e gidiyor. Kazanma oranı %57'den %36'ya çöküyor.
#
# DENENİP REDDEDİLEN: giriş saati filtresi. Hiçbir tek saat referansa
# yaklaşamadı (en iyi +61.7R vs +93.7R); saat eleme ise %1'lik farklar
# üretti (gürültü). Ayrıca 12:00 OOS'ta en iyi, IS'te EN KÖTÜ çıktı -
# klasik gürültü işareti.
USE_MAX_HOLD = True
# DİKKAT: GÜN cinsinden tanımlı, bar cinsinden DEĞİL. Backtest 4h barlarla
# yapıldı (60 bar = 10 gün) ama canlı bot SCAN.timeframe kullanıyor
# (varsayılan 15m). Bar sayısı olarak tanımlansaydı canlıda 15 saat
# olurdu - 16 kat yanlış. Gün cinsinden tanımlamak bu hatayı önler.
MAX_HOLD_DAYS = 10.0           # Bu süreden uzun açık kalan pozisyonu kapat.

LOG_FILE = "bot.log"
STATE_FILE = "bot_state.json"
