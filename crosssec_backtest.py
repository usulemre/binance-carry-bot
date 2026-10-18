"""Kesitsel (cross-sectional) ortalamaya dönüş + periyodik yeniden dengeleme.

BU, BOTUN ANA STRATEJİSİNDEN TAMAMEN FARKLI BİR MEKANİZMADIR.

Ana bot: her coini tek tek inceler, sinyal arar, SL/TP ile pozisyon açar.
Bu strateji: TÜM coinleri aynı anda tutar, göreceli performansa göre
ağırlıklandırır, periyodik olarak yeniden dengeler.

MANTIK:
  - Son N günde EN ÇOK YÜKSELENLERİ short'la
  - Son N günde EN ÇOK DÜŞENLERİ long'la
  - Long ve short tarafını EŞİT büyüklükte tut (piyasa nötr)
  - Her K günde bir yeniden dengele

NEDEN ÇALIŞABİLİR:
  1) Kesitsel ortalamaya dönüş: kripto coinleri birbirine göre salınır;
     aşırı ayrışanlar genelde geri yakınsar.
  2) Yeniden dengeleme primi ("Shannon's demon"): oynak ama trendsiz
     varlıklarda, periyodik olarak kazananı satıp kaybedeni almak
     volatiliteden kâr üretir - yön tahmini gerekmeden.
  3) Piyasa nötr: toplam piyasa yönünden bağımsız, yani ayı piyasasında
     da çalışabilir.

Bu, ana botun zayıf olduğu noktayı (yön tahmini, tek tek sinyal) tamamen
atlar. ANA BOT İÇİN BİR ÖNERİ DEĞİLDİR - ayrı bir fikrin dürüst testidir.

KULLANIM:
    python crosssec_backtest.py --lookback 30 --rebalance 3 --n-legs 4
"""

import argparse
import numpy as np
import pandas as pd

from backtest_yearly import load_all_csvs

# Maliyetler - ana backtest ile aynı varsayımlar
COMMISSION_PCT_PER_SIDE = 0.04   # taker %0.04
SLIPPAGE_PCT = 0.02              # her işlemde aleyhte kayma
# FUNDING MODELİ HAKKINDA ÖNEMLİ NOT:
# Aşağıdaki hesap `gross * funding` şeklinde - yani TÜM pozisyonlar
# (long VE short) maliyet ödüyor varsayılıyor. Bu GERÇEKÇİ DEĞİL ama
# bilinçli olarak MUHAFAZAKÂR bırakıldı:
#
# Gerçekte funding pozitifken long ÖDER, short ALIR. Piyasa nötr bir
# portföyde (4 long + 4 short, eşit büyüklükte) bu büyük ölçüde
# birbirini götürür - net funding maliyeti buradaki varsayımdan
# belirgin şekilde DÜŞÜK olmalıdır.
#
# Neden düzeltilmedi: long ve short bacakları FARKLI coinlerde ve
# bunların funding oranları farklıdır. Tam modelleme için coin bazında
# tarihsel funding verisi gerekir; bu veri elimizde yok (historical_data
# CSV'lerinde funding sütunu yok, testnet API'si sadece güncel veri
# veriyor). Eksik yönde hata yapmaktansa fazla yönde hata yapmak
# tercih edildi.
#
# DUYARLILIK (OOS 2025-26, kesitsel bot):
#   funding %0.00/8sa -> yıllık +108.0%, Sharpe 3.15
#   funding %0.01     -> yıllık  +99.9%, Sharpe 2.96  <- varsayılan
#   funding %0.05     -> yıllık  +75.8%, Sharpe 2.35
#   funding %0.10     -> yıllık  +58.8%, Sharpe 1.92
# Funding, stratejinin EN HASSAS olduğu maliyet kalemi. Gerçek net
# funding (long/short netleşmesi dahil) demo hesapta ölçülmeli.
AVG_FUNDING_PCT_PER_8H = 0.01    # ortalama funding (tek yönlü, muhafazakâr)


def build_price_panel(data: dict, timeframe_hours: int = 4) -> pd.DataFrame:
    """Tüm coinlerin kapanış fiyatlarını ortak zaman eksenine hizalar."""
    frames = {}
    for sym, df in data.items():
        s = df.set_index(pd.DatetimeIndex(df["date"]))["close"].astype(float)
        frames[sym] = s[~s.index.duplicated(keep="last")]
    panel = pd.DataFrame(frames).sort_index()
    # Tüm coinlerin veri verdiği barlar (yeni listelenen coinler başta eksik)
    panel = panel.dropna(how="any")
    return panel


def _reversal_corr(prices, i: int, horizon: int, window: int):
    """Kesitsel ortalamaya dönüş gücünü ölç (SADECE geçmiş veriyle).

    t anındaki h-barlık getirinin kesitsel sapması ile, t'den t+h'ye olan
    getirinin kesitsel sapması arasındaki korelasyonun ortalaması.
    NEGATİF = çok düşen sonra yükseliyor = strateji çalışır.
    SIFIRA YAKIN = etki yok = strateji kazanamaz.

    Sadece t + horizon <= i olan örnekler kullanılır, yani ileriye bakmaz.
    Yeterli örnek yoksa None döner (filtre uygulanmaz).
    """
    son = i - horizon                      # en son tamamlanmış örnek
    ilk = max(horizon, i - window)
    if son - ilk < horizon:
        return None
    adim = max(1, horizon // 5)
    cors = []
    for t in range(ilk, son + 1, adim):
        gecmis = (prices[t] - prices[t - horizon]) / prices[t - horizon]
        ileri = (prices[t + horizon] - prices[t]) / prices[t]
        if not (np.isfinite(gecmis).all() and np.isfinite(ileri).all()):
            continue
        a = gecmis - gecmis.mean()
        b = ileri - ileri.mean()
        sa, sb = a.std(), b.std()
        if sa < 1e-12 or sb < 1e-12:
            continue
        cors.append(float(np.dot(a, b) / (len(a) * sa * sb)))
    if len(cors) < 5:
        return None
    return float(np.mean(cors))


def run_crosssectional(panel: pd.DataFrame, lookback_bars: int, rebalance_bars: int,
                       n_legs: int, market_neutral: bool = True,
                       gross_exposure: float = 1.0,
                       compound: bool = True,
                       horizons_bars=None, pos_tp=None, trail_scale=None,
                       exec_lag: int = 1,
                       min_dispersion=None, dispersion_window: int = 180,
                       max_reversal_corr=None, reversal_window: int = 540,
                       reversal_full=None, signal_sign: int = -1,
                       adaptive_sign: bool = False, adaptive_horizon: int = 360,
                       pos_sl=None):
    """Kesitsel ortalamaya dönüş backtest'i.

    lookback_bars   : göreceli performans kaç barlık geçmişten ölçülür
    rebalance_bars  : kaç barda bir yeniden dengelenir
    n_legs          : her tarafta kaç coin tutulur (n_legs long + n_legs short)
    market_neutral  : True ise long ve short tarafı eşit büyüklükte
    gross_exposure  : toplam pozisyon büyüklüğü / sermaye. 1.0 = kaldıraçsız
                      (long %50 + short %50). 2.0 = 2x kaldıraç.
    horizons_bars   : ÇOK UFUKLU sıralama - birden fazla pencerenin z-skoru
                      ortalanır. None ise tek lookback_bars kullanılır.
                      Canlı bot varsayılanı: [30, 60, 90] (5g/10g/15g @4h).
    pos_tp          : pozisyon bu orana (0.04 = %4) ulaşınca kapatılır.
                      Canlı bot varsayılanı: 0.04
    trail_scale     : kademeli exposure azaltma - tepeden bu kadar (0.30 =
                      30 puan) düşünce pozisyon sıfırlanır, arada orantılı.
                      Canlı bot varsayılanı: 0.30
    pos_sl          : ACİL STOP - pozisyon bu orana (0.25 = %25) zarar
                      ederse kapatılır. Canlı bottaki EMERGENCY_STOP_PCT
                      karşılığı (madde 64: kuyruk riski koruması).
                      None = kapalı.
    min_dispersion  : coinler arası getiri std'si bu değerin altındaysa
                      YENİ POZİSYON AÇILMAZ (mevcutlar yönetilmeye devam
                      eder). Canlı bottaki MIN_DISPERSION karşılığı.
                      None = filtre kapalı.
    dispersion_window: dispersiyon kaç barlık geçmişten ölçülsün.
    max_reversal_corr: TERSİNE DÖNÜŞ FİLTRESİ (madde 109). Geçmiş penceredeki
                     kesitsel otokorelasyon (düşenin sonra yükselme eğilimi)
                     bu değerden BÜYÜKSE yeni pozisyon açılmaz. Negatif bir
                     sayı verilir (örn. -0.05): korelasyon ne kadar negatifse
                     ortalamaya dönüş o kadar güçlü demektir. Ölçüldü: 2024'te
                     -0.30 (bot +2475%), 2026'da -0.01 (bot -11%).
                     SADECE geçmiş veri kullanır - look-ahead yoktur.
    reversal_window : otokorelasyon kaç barlık geçmişten ölçülsün.
    exec_lag        : uygulama gecikmesi (bar). GERÇEKÇİ DEĞER 1: sinyali
                      bar kapanışında görüp emri sonraki barda doldurursunuz.
                      0 yaparsanız sonuç CİDDİ ŞEKİLDE ŞİŞER (ölçüldü:
                      Sharpe 12.6 vs 2.6).
    compound        : True ise kâr yeniden yatırılır (bileşik).

                      CANLI BOT ZATEN BİLEŞİK ÇALIŞIYOR - pozisyonları her
                      turda güncel bakiyeye göre hesaplıyor
                      (balance * GROSS_EXPOSURE). Yani backtest'i bileşik
                      çalıştırmak canlı davranışı DAHA DOĞRU yansıtır.

                      Eskiden varsayılan False'tu ("emir defteri derinliği
                      sınırsız büyümeye izin vermez" gerekçesiyle). Bu kaygı
                      BÜYÜK FONLAR için geçerli, küçük hesaplar için değil:
                        sermaye      pozisyon başına
                          2.000 USDT       333 USDT
                         10.000 USDT     1.667 USDT
                        100.000 USDT    16.667 USDT
                      Likidite filtresi 200.000 USDT derinlik istiyor, yani
                      ~1.2 MİLYON USDT sermayeye kadar bileşik gerçekçi.

                      ETKİ (temiz veri, 2022-2026, 2000 USDT başlangıç):
                        sabit nominal : yıllık  +92.5%  ->  10.597 USDT
                        bileşik       : yıllık +130.1%  ->  96.234 USDT
                      Sharpe aynı (2.13), max düşüş aynı (-%28) - yani
                      bedava kazanç değil, kârı yeniden yatırmanın doğal
                      sonucu.

                      Büyük sermayeyle çalışıyorsanız compound=False ile
                      muhafazakâr tahmin alın.

    Döner: (equity_serisi, metrikler)
    """
    prices = panel.values
    dates = panel.index
    n_bars, n_sym = prices.shape

    hors = horizons_bars or [lookback_bars]
    warm = max(hors) + 5
    if n_bars < warm + 10:
        raise ValueError(f"Yetersiz veri: {n_bars} bar, en az {warm+10} gerekli")

    equity = [0.0 if not compound else 1.0]
    eq_dates = [dates[warm]]
    positions = np.zeros(n_sym)
    entry_px = np.zeros(n_sym)
    n_trades = 0
    turnover_total = 0.0
    pending = None          # (uygulama_bari, hedef_pozisyonlar)
    exit_pending = []       # TP tetiklenen indeksler (sonraki barda kapanır)
    peak = equity[0]

    for i in range(warm, n_bars - 1):
        # Önceki barda TP tetiklenenleri şimdi kapat (gecikme)
        for j in exit_pending:
            if positions[j] != 0.0:
                cost = abs(positions[j]) * (COMMISSION_PCT_PER_SIDE + SLIPPAGE_PCT) / 100
                equity[-1] = equity[-1] * (1 - cost) if compound else equity[-1] - cost
                positions[j] = 0.0
        exit_pending = []

        cur = equity[-1]
        peak = max(peak, cur)
        # Kademeli exposure azaltma.
        # DİKKAT: düşüş ORANSAL ölçülmeli, mutlak puan cinsinden değil.
        # Sabit nominal modda equity = kümülatif kâr (0'dan başlar), bileşik
        # modda = sermaye katı (1'den başlar). Puan cinsinden ölçmek bileşik
        # modda hatalıydı: sermaye büyüdükçe aynı YÜZDE düşüş çok daha fazla
        # PUAN ediyor, koruma kalıcı olarak sıfırda kilitleniyordu.
        # (Ölçüldü: bileşik modda bot 2024'ten sonra tamamen durmuştu.)
        scale = 1.0
        if trail_scale:
            if compound:
                # peak ve cur sermaye katı -> oransal düşüş
                dusus = (peak - cur) / peak if peak > 0 else 0.0
            else:
                # kümülatif kâr -> puan cinsinden (başlangıç sermayesine göre)
                dusus = peak - cur
            scale = max(0.0, min(1.0, 1.0 - dusus / trail_scale))

        # Gecikmeli dengeleme emrini uygula
        if pending is not None and pending[0] == i:
            new_pos = pending[1] * scale
            turnover = np.abs(new_pos - positions).sum()
            cost = turnover * (COMMISSION_PCT_PER_SIDE + SLIPPAGE_PCT) / 100
            equity[-1] = equity[-1] * (1 - cost) if compound else equity[-1] - cost
            n_trades += int((np.abs(new_pos - positions) > 1e-9).sum())
            turnover_total += turnover
            positions = new_pos
            entry_px = np.where(np.abs(new_pos) > 0, prices[i], 0.0)
            pending = None

        # Kâr alma / acil stop kontrolü (çıkış bir sonraki barda - look-ahead
        # olmasın). Canlı bot her turda aynı kontrolü yapıyor.
        if pos_tp is not None or pos_sl is not None:
            for j in np.nonzero(positions)[0]:
                if entry_px[j] <= 0:
                    continue
                chg = float((prices[i][j] - entry_px[j]) / entry_px[j])
                gain = chg if positions[j] > 0 else -chg
                if pos_tp is not None and gain >= pos_tp:
                    exit_pending.append(j)
                elif pos_sl is not None and gain <= -pos_sl:
                    exit_pending.append(j)

        # Yeniden dengeleme sinyali
        if (i - warm) % rebalance_bars == 0:
            # DİSPERSİYON FİLTRESİ: coinler birbirinden ayrışmıyorsa bu
            # stratejinin kazanacağı bir şey yok (madde 81). Mevcut
            # pozisyonlar yönetilmeye devam eder, sadece yeni açılmaz.
            _skip = False
            if min_dispersion is not None:
                _w = np.diff(prices[max(0, i - dispersion_window):i], axis=0) / \
                     prices[max(0, i - dispersion_window):i - 1]
                if _w.size and np.nanmean(np.nanstd(_w, axis=1)) < min_dispersion:
                    _skip = True
            # TERSİNE DÖNÜŞ FİLTRESİ: ortalamaya dönüş etkisi zayıfladıysa
            # ayrışma yüksek olsa bile bu stratejinin kazanacağı şey yok.
            _rev_scale = 1.0
            if (not _skip) and max_reversal_corr is not None:
                _rc = _reversal_corr(prices, i, hors[0], reversal_window)
                if _rc is not None:
                    if reversal_full is None:
                        # SERT mod: eşiğin üstündeyse hiç pozisyon açma
                        if _rc > max_reversal_corr:
                            _skip = True
                    else:
                        # KADEMELİ mod: dönüş gücü zayıfladıkça pozisyonu
                        # orantılı küçült. reversal_full'da tam güç,
                        # max_reversal_corr'da sıfır.
                        _span = max_reversal_corr - reversal_full
                        _rev_scale = ((max_reversal_corr - _rc) / _span
                                      if _span > 1e-12 else 1.0)
                        _rev_scale = float(min(1.0, max(0.0, _rev_scale)))
                        if _rev_scale <= 1e-9:
                            _skip = True
            if _skip:
                    pending = (i + exec_lag, np.zeros(n_sym))
                    bar_ret = (prices[i + 1] - prices[i]) / prices[i]
                    port_ret = float(np.clip(np.dot(positions, bar_ret), -0.5, 0.5))
                    gross_ = np.abs(positions).sum()
                    funding = gross_ * (AVG_FUNDING_PCT_PER_8H / 100) * (4 / 8)
                    if compound:
                        equity.append(equity[-1] * (1 + port_ret) - funding * equity[-1])
                    else:
                        equity.append(equity[-1] + port_ret - funding)
                    eq_dates.append(dates[i + 1])
                    continue
            z_sum = np.zeros(n_sym)
            for hb in hors:
                perf = (prices[i] - prices[i - hb]) / prices[i - hb]
                z_sum += (perf - perf.mean()) / (perf.std() + 1e-9)
            score = z_sum / len(hors)

            # signal_sign: -1 = ortalamaya dönüş (düşeni al), +1 = momentum
            # (yükseleni al). adaptive_sign açıksa geçmiş penceredeki
            # otokorelasyonun İŞARETİNE göre otomatik seçilir (madde 110).
            _sign = signal_sign
            if adaptive_sign:
                _ac = _reversal_corr(prices, i, adaptive_horizon, reversal_window)
                if _ac is not None:
                    _sign = 1 if _ac > 0 else -1
            score = score * (-_sign)
            order = np.argsort(score)
            new_pos = np.zeros(n_sym)
            new_pos[order[:n_legs]] = (gross_exposure / 2) / n_legs
            new_pos[order[-n_legs:]] = -(gross_exposure / 2) / n_legs

            if market_neutral:
                lsum = new_pos[new_pos > 0].sum()
                ssum = -new_pos[new_pos < 0].sum()
                if lsum > 0 and ssum > 0:
                    new_pos[new_pos > 0] *= (gross_exposure / 2) / lsum
                    new_pos[new_pos < 0] *= (gross_exposure / 2) / ssum

            # Kademeli tersine dönüş ölçeği (piyasa nötrlüğü bozulmaz -
            # her iki bacak aynı oranda küçülür)
            if _rev_scale < 1.0:
                new_pos = new_pos * _rev_scale

            if exec_lag <= 0:
                # GECİKMESİZ mod: emri HEMEN uygula. Bu bloğun üstündeki
                # "pending uygula" kontrolü bu bardan önce çalıştığı için
                # pending=(i, ...) yazmak emri SONSUZA KADAR bekletirdi -
                # bot hiç işlem yapmaz, hata da vermezdi (ölçüldü: 0 emir,
                # %100 boş zaman). Gerçekçi değer 1'dir; 0 sadece
                # karşılaştırma amaçlı kullanılır ama doğru çalışmalı.
                new_pos = new_pos * scale
                turnover = np.abs(new_pos - positions).sum()
                cost = turnover * (COMMISSION_PCT_PER_SIDE + SLIPPAGE_PCT) / 100
                equity[-1] = equity[-1] * (1 - cost) if compound else equity[-1] - cost
                n_trades += int((np.abs(new_pos - positions) > 1e-9).sum())
                turnover_total += turnover
                positions = new_pos
                entry_px = np.where(np.abs(new_pos) > 0, prices[i], 0.0)
                pending = None
            else:
                pending = (i + exec_lag, new_pos)

        bar_ret = (prices[i + 1] - prices[i]) / prices[i]
        port_ret = float(np.clip(np.dot(positions, bar_ret), -0.5, 0.5))
        gross = np.abs(positions).sum()
        funding = gross * (AVG_FUNDING_PCT_PER_8H / 100) * (4 / 8)

        if compound:
            new_eq = equity[-1] * (1 + port_ret) - funding * equity[-1]
            if new_eq <= 0.01:
                equity.append(0.0)
                eq_dates.append(dates[i + 1])
                break
        else:
            new_eq = equity[-1] + port_ret - funding
        equity.append(new_eq)
        eq_dates.append(dates[i + 1])

    eq = pd.Series(equity, index=eq_dates)
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    if compound:
        rets = eq.pct_change().dropna()
        total_return = eq.iloc[-1] - 1
        cagr = (eq.iloc[-1] ** (1 / years) - 1) if years > 0 and eq.iloc[-1] > 0 else float("nan")
        peak = eq.cummax()
        max_dd = ((eq - peak) / peak).min()
    else:
        # Sabit nominal: eq = kümülatif kâr (başlangıç sermayesinin katı).
        # Getiriler zaten sermaye oranı olduğu için fark alınır, bölünmez.
        rets = eq.diff().dropna()
        total_return = eq.iloc[-1]
        cagr = (eq.iloc[-1] / years) if years > 0 else float("nan")  # basit yıllık
        max_dd = (eq - eq.cummax()).min()
    sharpe = (rets.mean() / rets.std() * np.sqrt(365.25 * 6)) if rets.std() > 0 else float("nan")

    years_ = years if years > 0 else 1.0
    flat_frac = float((pd.Series(equity).diff().abs() < 1e-12).mean())
    return eq, {
        "turnover_per_year": turnover_total / years_,
        "flat_pct": flat_frac * 100,
        "total_return_pct": total_return * 100,
        "cagr_pct": cagr * 100,
        "sharpe": sharpe,
        "max_drawdown_pct": max_dd * 100,
        "n_rebalance_trades": n_trades,
        "avg_turnover": turnover_total / max(1, n_trades),
        "years": years,
    }


def main():
    ap = argparse.ArgumentParser(description="Kesitsel ortalamaya dönüş / piyasa nötr rebalance testi")
    ap.add_argument("--timeframe", default="4h")
    ap.add_argument("--lookback-days", type=float, default=10, help="Tek ufuk modu için pencere (gün)")
    ap.add_argument("--rebalance-days", type=float, default=1, help="Kaç günde bir yeniden dengelensin")
    ap.add_argument("--n-legs", type=int, default=4, help="Her tarafta kaç coin")
    ap.add_argument("--horizons", type=str, default=None,
                    help="Çok ufuklu sıralama pencereleri, gün (boş bırakılırsa tek ufuk)")
    ap.add_argument("--tp", type=float, default=4.0, help="Kâr alma eşiği %% (0=kapalı)")
    ap.add_argument("--trail-scale", type=float, default=30.0,
                    help="Kademeli azaltma: tepeden bu kadar puan düşüşte sıfırlanır (0=kapalı)")
    ap.add_argument("--all-phases", action="store_true",
                    help="TÜM rebalance fazlarını çalıştırıp ORTALAMA al. "
                         "Tek faz sonucu yanıltıcıdır: botun günün hangi "
                         "saatinde dengelediği sonucu %%40+ değiştirebilir "
                         "(bkz. README madde 100).")
    ap.add_argument("--min-dispersion", type=float, default=None,
                    help="Dispersiyon filtresi eşiği (boş bırakılırsa "
                         "crosssec_bot.py'deki ayar kullanılır, 0 ile kapatılır)")
    ap.add_argument("--max-reversal-corr", type=float, default=None,
                    help="Tersine dönüş filtresi eşiği (negatif sayı, örn. "
                         "-0.05). Geçmiş penceredeki ortalamaya dönüş gücü "
                         "bu değerden zayıfsa yeni pozisyon açılmaz. "
                         "0 ile kapatılır.")
    ap.add_argument("--reversal-window", type=int, default=540,
                    help="Tersine dönüş ölçüm penceresi (bar)")
    ap.add_argument("--no-lag", action="store_true",
                    help="Uygulama gecikmesini KAPAT (gerçekçi DEĞİL, sonucu şişirir)")
    ap.add_argument("--no-neutral", action="store_true", help="Piyasa nötr olmasın")
    ap.add_argument("--gross", type=float, default=1.0, help="Toplam pozisyon/sermaye (1.0=kaldıraçsız)")
    ap.add_argument("--no-compound", action="store_true",
                    help="Kârı yeniden YATIRMA (sabit nominal - büyük sermaye "
                         "için muhafazakâr tahmin)")
    ap.add_argument("--year", type=int, default=None, help="Sadece bu yılı test et")
    ap.add_argument("--from-year", type=int, default=None, help="Bu yıldan itibaren test et")
    args = ap.parse_args()

    bars_per_day = 24 / int(args.timeframe.replace("h", ""))
    lookback = int(args.lookback_days * bars_per_day)
    rebalance = max(1, int(args.rebalance_days * bars_per_day))

    data = load_all_csvs(args.timeframe)
    panel = build_price_panel(data)
    if args.year:
        panel = panel[panel.index.year == args.year]
    if args.from_year:
        panel = panel[panel.index.year >= args.from_year]
    print(f"{panel.shape[1]} coin, {panel.shape[0]} bar "
          f"({panel.index[0].date()} - {panel.index[-1].date()})")
    print(f"lookback={lookback} bar (~{args.lookback_days}g), "
          f"rebalance={rebalance} bar (~{args.rebalance_days}g), her tarafta {args.n_legs} coin\n")

    # Varsayılan: crosssec_bot.py'deki ayar (tek kaynak - parite için)
    import crosssec_bot as _cb0
    _hor_str = args.horizons if args.horizons is not None \
        else ",".join(str(h) for h in _cb0.HORIZON_DAYS)
    hors = [int(float(x) * bars_per_day) for x in _hor_str.split(",")] \
        if _hor_str.strip() else None

    # Dispersiyon filtresi: CLI > crosssec_bot.py ayarı
    import crosssec_bot as _cb
    if args.min_dispersion is not None:
        _min_disp = args.min_dispersion if args.min_dispersion > 0 else None
    else:
        _min_disp = _cb.MIN_DISPERSION if _cb.USE_DISPERSION_FILTER else None
    _disp_win = _cb.DISPERSION_WINDOW_BARS
    _max_rev = args.max_reversal_corr
    if _max_rev is not None and _max_rev == 0:
        _max_rev = None
    _rev_win = args.reversal_window
    if args.all_phases:
        import numpy as _np
        _fazlar = []
        for _off in range(rebalance):
            try:
                _, _mm = run_crosssectional(
                    panel.iloc[_off:], lookback, rebalance, args.n_legs,
                    market_neutral=not args.no_neutral, gross_exposure=args.gross,
                    compound=not args.no_compound, horizons_bars=hors,
                    pos_tp=(args.tp / 100 if args.tp > 0 else None),
                    trail_scale=(args.trail_scale / 100 if args.trail_scale > 0 else None),
                    exec_lag=(0 if args.no_lag else 1),
                    min_dispersion=_min_disp, dispersion_window=_disp_win,
                    max_reversal_corr=_max_rev, reversal_window=_rev_win,
                    pos_sl=(_cb.EMERGENCY_STOP_PCT / 100 if _cb.USE_EMERGENCY_STOP else None))
                _fazlar.append(_mm)
            except Exception:
                pass
        if _fazlar:
            print(f"TÜM FAZLAR ({len(_fazlar)} adet) - dengeleme saati etkisi:")
            _c = _np.array([x["cagr_pct"] for x in _fazlar])
            _s = _np.array([x["sharpe"] for x in _fazlar])
            _d = _np.array([x["max_drawdown_pct"] for x in _fazlar])
            for _i, _x in enumerate(_fazlar):
                print(f"  faz {_i} (saat {_i*4:>2}:00): yıllık {_x['cagr_pct']:>+8.1f}%  "
                      f"Sharpe {_x['sharpe']:.2f}")
            print()
            print(f"  ORTALAMA  : yıllık {_c.mean():>+8.1f}%  Sharpe {_s.mean():.2f}  "
                  f"düşüş {_d.mean():.1f}%")
            print(f"  aralık    : {_c.min():+.0f}% .. {_c.max():+.0f}%  "
                  f"(std {_c.std():.1f}%)")
            print()
            print("  NOT: gerçekçi beklenti ORTALAMA'dır, en iyi faz değil.")
            return

    eq, m = run_crosssectional(panel, lookback, rebalance, args.n_legs,
                               market_neutral=not args.no_neutral, gross_exposure=args.gross,
                               compound=not args.no_compound,
                               horizons_bars=hors,
                               pos_tp=(args.tp / 100 if args.tp > 0 else None),
                               trail_scale=(args.trail_scale / 100 if args.trail_scale > 0 else None),
                               exec_lag=(0 if args.no_lag else 1),
                               min_dispersion=_min_disp,
                               dispersion_window=_disp_win,
                               max_reversal_corr=_max_rev,
                               reversal_window=_rev_win,
                               pos_sl=(_cb.EMERGENCY_STOP_PCT / 100
                                       if _cb.USE_EMERGENCY_STOP else None))
    if hors:
        print(f"çok ufuklu sıralama: {_hor_str} gün | TP +%{args.tp} | "
              f"kademeli azaltma {args.trail_scale} puan | gecikme {'YOK' if args.no_lag else '1 bar'}\n")
    mod = "SABİT NOMİNAL (kâr yeniden yatırılmıyor)" if args.no_compound \
        else "BİLEŞİK (canlı bot davranışı)"
    print(f"Mod               : {mod}")
    print(f"Toplam kâr        : {m['total_return_pct']:+.1f}% (başlangıç sermayesinin katı, {m['years']:.1f} yıl)")
    print(f"Yıllık ortalama   : {m['cagr_pct']:+.1f}%")
    print(f"Sharpe            : {m['sharpe']:.2f}")
    print(f"Maksimum düşüş    : {m['max_drawdown_pct']:.1f}%")
    print(f"Yeniden dengeleme : {m['n_rebalance_trades']} emir")
    print(f"Yıllık devir      : {m['turnover_per_year']:.0f}x  "
          f"(yüksek devir = slippage'a hassas)")
    print(f"Boş geçen zaman   : %{m['flat_pct']:.1f}  "
          f"(yüksek ise koruma devrede, bot işlem yapmıyor demektir)")


if __name__ == "__main__":
    main()
