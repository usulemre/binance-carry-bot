"""CANLIYA GEÇİŞ ÖNCESİ KONTROL (preflight).

Bu proje boyunca her şey backtest'te doğrulandı ama HİÇ CANLI
ÇALIŞMADI. Bu araç, gerçek para riske atılmadan önce çalışması
gereken her şeyi tek tek kontrol eder.

HİÇBİR EMİR GÖNDERMEZ. Sadece okur ve raporlar.

KULLANIM:
    python preflight.py              # kesitsel bot için
    python preflight.py --signal     # sinyal botu için

Her kontrol şu üç sonuçtan birini verir:
    TAMAM    - sorun yok
    UYARI    - çalışır ama dikkat edilmeli
    HATA     - canlıya geçmeden önce düzeltilmeli
"""

import argparse
import sys

import numpy as np

import config

TAMAM, UYARI, HATA = "TAMAM", "UYARI", "HATA "
sonuclar = []


def kontrol(ad: str, durum: str, mesaj: str = ""):
    sonuclar.append((durum, ad, mesaj))
    isaret = {TAMAM: "  ✓", UYARI: "  !", HATA: "  ✗"}[durum]
    print(f"{isaret} [{durum}] {ad}")
    if mesaj:
        for satir in mesaj.split("\n"):
            print(f"        {satir}")


def kontrol_ayarlar(signal_mode: bool):
    print("\n--- AYAR TUTARLILIĞI ---")

    if not config.API_KEY or not config.API_SECRET:
        kontrol("API anahtarları", HATA, ".env dosyasında BINANCE_API_KEY/SECRET yok")
        return False
    kontrol("API anahtarları", TAMAM, f"mod: {config.BINANCE_MODE}")

    if config.BINANCE_MODE == "live":
        kontrol("Çalışma modu", UYARI,
                "GERÇEK PARA modu! Önce 'demo' ile haftalarca test edin.")
    else:
        kontrol("Çalışma modu", TAMAM, f"{config.BINANCE_MODE} (sahte para)")

    # Zaman dilimi backtest ile aynı mı?
    if signal_mode:
        tf = config.SCAN.timeframe
    else:
        import crosssec_bot as cb
        tf = cb.TIMEFRAME
    if tf != "4h":
        kontrol("Zaman dilimi", HATA,
                f"Bot {tf} kullanıyor ama TÜM backtest'ler 4h ile yapıldı.\n"
                f"Parametreler (ATR, lookback, TP/SL) 4h için ayarlı - "
                f"başka dilimde backtest sonuçları GEÇERSİZ.")
    else:
        kontrol("Zaman dilimi", TAMAM, "4h (backtest ile aynı)")

    if signal_mode:
        # Kaldıraç / stop-loss tutarlılığı
        from strategy import MAX_SL_DISTANCE_PCT
        lik = 100 / config.RISK.leverage
        if MAX_SL_DISTANCE_PCT >= lik * 0.8:
            kontrol("Kaldıraç / SL tutarlılığı", HATA,
                    f"SL sınırı %{MAX_SL_DISTANCE_PCT} ama kaldıraç "
                    f"{config.RISK.leverage}x'te likidasyon ~%{lik:.0f}.\n"
                    f"Pozisyonlar SL'e ulaşmadan likide olabilir!")
        else:
            kontrol("Kaldıraç / SL tutarlılığı", TAMAM,
                    f"kaldıraç {config.RISK.leverage}x, likidasyon ~%{lik:.0f}, "
                    f"SL sınırı %{MAX_SL_DISTANCE_PCT}")

        # Makro takvim dolduruldu mu?
        try:
            import macro_calendar as mc
            mc.gecmis_olaylari_temizle()
            if not mc.is_configured():
                kontrol("Makro haber takvimi", UYARI,
                        "BOŞ - filtre hiçbir şey yapmayacak.\n"
                        "FOMC/CPI/NFP saatlerinde işlem açılmasını engellemek "
                        "için macro_calendar.py -> MACRO_EVENTS doldurun.")
            else:
                kontrol("Makro haber takvimi", TAMAM,
                        f"{len(mc.MACRO_EVENTS)} gelecek olay kayıtlı")
        except Exception as e:
            kontrol("Makro haber takvimi", UYARI, str(e))

        # Rejim filtresi bu strateji için doğru ayarda mı?
        rf = config.USE_REGIME_FILTER_BY_STRATEGY.get(
            config.ACTIVE_STRATEGY, config.RISK.use_regime_filter)
        if config.ACTIVE_STRATEGY == "extreme_reversal" and rf:
            kontrol("Rejim filtresi", UYARI,
                    "extreme_reversal için AÇIK - ölçümde 148.8R "
                    "kaybettiriyor (2025'te +162R'lik yılı engellerdi).")
        else:
            kontrol("Rejim filtresi", TAMAM, f"{config.ACTIVE_STRATEGY}: {rf}")

        yonetim = config.USE_POSITION_MANAGEMENT.get(config.ACTIVE_STRATEGY, True)
        if config.ACTIVE_STRATEGY in ("mean_reversion", "extreme_reversal") and yonetim:
            kontrol("Kâr kilitleme", UYARI,
                    f"{config.ACTIVE_STRATEGY} için AÇIK - ölçümde faydasız/zararlı "
                    f"çıkmıştı. Kapatmanız önerilir.")
        else:
            kontrol("Kâr kilitleme", TAMAM, f"{config.ACTIVE_STRATEGY}: {yonetim}")
    else:
        import crosssec_bot as cb
        # Önbellek / rebalance tutarlılığı
        rb_saat = cb.REBALANCE_DAYS * 24
        if cb.LIQUIDITY_CACHE_HOURS <= rb_saat:
            kontrol("Likidite önbelleği", UYARI,
                    f"Önbellek {cb.LIQUIDITY_CACHE_HOURS}sa, rebalance {rb_saat:.0f}sa - "
                    f"önbellek her turda dolar, işe yaramaz.")
        else:
            kontrol("Likidite önbelleği", TAMAM,
                    f"{cb.LIQUIDITY_CACHE_HOURS}sa ({cb.LIQUIDITY_CACHE_HOURS/rb_saat:.1f} turda bir yenilenir)")

        # Bacak / evren oranı
        oran = cb.N_LEGS * 2 / cb.UNIVERSE_SIZE
        if oran < 0.15:
            kontrol("Bacak / evren oranı", UYARI,
                    f"{cb.N_LEGS}+{cb.N_LEGS} pozisyon, {cb.UNIVERSE_SIZE} coinlik evrenin "
                    f"sadece %{oran*100:.0f}'i. Çok seçici - optimum ~%33 "
                    f"(yaklaşık {cb.UNIVERSE_SIZE//6}+{cb.UNIVERSE_SIZE//6}).")
        elif oran > 0.60:
            kontrol("Bacak / evren oranı", UYARI,
                    f"{cb.N_LEGS}+{cb.N_LEGS} pozisyon, evrenin %{oran*100:.0f}'i. "
                    f"Çok geniş - sıralamanın ayırt ediciliği azalır.")
        else:
            kontrol("Bacak / evren oranı", TAMAM,
                    f"evrenin %{oran*100:.0f}'i (optimum ~%33)")

        # Evren yeterli mi?
        if cb.UNIVERSE_SIZE < cb.N_LEGS * 2 * 2:
            kontrol("Coin evreni", UYARI,
                    f"{cb.UNIVERSE_SIZE} coin taranıyor, {cb.N_LEGS*2} pozisyon gerekiyor. "
                    f"Likidite filtresi elerse yetersiz kalabilir.")
        else:
            kontrol("Coin evreni", TAMAM,
                    f"{cb.UNIVERSE_SIZE} coin -> {cb.N_LEGS}+{cb.N_LEGS} pozisyon")

        # Faz dilimleme uyarısı
        if getattr(cb, "USE_PHASE_SPLIT", False) and cb.PHASE_COUNT > 1:
            kontrol("Faz dilimleme", UYARI,
                    f"AÇIK ({cb.PHASE_COUNT} dilim) - ölçümde ZARARLI çıktı.\n"
                    f"Dilimler aynı hesapta netleşiyor: net exposure %19 kayıp,\n"
                    f"Sharpe 1.78 -> 0.87 (madde 104).\n"
                    f"USE_PHASE_SPLIT=False önerilir. Ayrı alt hesap "
                    f"kullanıyorsanız açık kalabilir.")
        else:
            kontrol("Faz dilimleme", TAMAM, "kapalı (doğru ayar)")

        # Borsa SL'i yok uyarısı
        kontrol("Pozisyon koruması", UYARI,
                "Bu bot borsa tarafında SL/TP emri KULLANMAZ - korumalar\n"
                "her turda bot tarafından uygulanır.\n"
                "BOT DURURSA POZİSYONLAR KORUMASIZ KALIR.\n"
                "Kesintisiz çalışacak bir ortamda (VPS/sunucu) başlatın;\n"
                "uzun süre durduracaksanız önce pozisyonları kapatın.")

        # Devre kesici / kaldıraç
        if cb.GROSS_EXPOSURE > 1.5 and cb.MAX_DRAWDOWN_PCT < 40:
            kontrol("Devre kesici / kaldıraç", UYARI,
                    f"Kaldıraç {cb.GROSS_EXPOSURE}x'te max düşüş -%27'ye çıkabilir, "
                    f"devre kesici %{cb.MAX_DRAWDOWN_PCT}. Normal dalgalanmada durabilir.")
        else:
            kontrol("Devre kesici / kaldıraç", TAMAM,
                    f"gross {cb.GROSS_EXPOSURE}x, devre kesici %{cb.MAX_DRAWDOWN_PCT}")
    return True


def kontrol_risk_tutarliligi():
    """Ayarlar BİRLİKTE tutarlı mı? (test_risk_coherence.py ile aynı mantık)

    Tek tek makul görünen ayarlar birlikte tehlikeli olabilir - örneğin
    4 pozisyon × %25 nominal × 5x kaldıraç marjı aşar.
    """
    print("\n--- RİSK AYARLARI TUTARLILIĞI ---")
    import crosssec_bot as cb
    from strategy import MAX_SL_DISTANCE_PCT
    r = config.RISK

    marj = r.max_position_notional_pct * r.max_concurrent_positions / r.leverage
    if marj > 100:
        kontrol("Marj yeterliliği", HATA,
                f"{r.max_concurrent_positions} pozisyon %{marj:.0f} marj ister - "
                f"hepsi açılamaz.")
    elif marj > 80:
        kontrol("Marj yeterliliği", UYARI,
                f"%{marj:.0f} marj kullanımı - ani harekette marj çağrısı riski")
    else:
        kontrol("Marj yeterliliği", TAMAM, f"%{marj:.0f} kullanım")

    tek_tur = r.risk_per_trade_pct * r.max_concurrent_positions
    if tek_tur > r.max_daily_loss_pct:
        kontrol("Günlük zarar limiti", HATA,
                f"Tek turda %{tek_tur} kayıp mümkün ama limit %{r.max_daily_loss_pct} - "
                f"limit koruma sağlamaz.")
    else:
        kontrol("Günlük zarar limiti", TAMAM,
                f"tek tur riski %{tek_tur} < limit %{r.max_daily_loss_pct}")

    if cb.DRAWDOWN_SCALE_FULL_PCT >= cb.MAX_DRAWDOWN_PCT:
        kontrol("Koruma sırası", HATA,
                f"Kademeli azaltma (%{cb.DRAWDOWN_SCALE_FULL_PCT}) devre kesiciden "
                f"(%{cb.MAX_DRAWDOWN_PCT}) sonra - kademeli koruma hiç devreye girmez.")
    else:
        kontrol("Koruma sırası", TAMAM,
                f"önce küçülme (%{cb.DRAWDOWN_SCALE_FULL_PCT}), sonra durma (%{cb.MAX_DRAWDOWN_PCT})")

    if cb.EMERGENCY_STOP_PCT <= cb.POSITION_TP_PCT * 2:
        kontrol("Acil stop eşiği", UYARI,
                f"Acil stop (%{cb.EMERGENCY_STOP_PCT}) kâr alma eşiğine "
                f"(%{cb.POSITION_TP_PCT}) çok yakın - normal dalgalanmada tetiklenebilir.")
    else:
        kontrol("Acil stop eşiği", TAMAM,
                f"%{cb.EMERGENCY_STOP_PCT} ({cb.EMERGENCY_STOP_PCT/cb.POSITION_TP_PCT:.1f}x TP)")


def kontrol_baglanti(signal_mode: bool):
    print("\n--- BORSA BAĞLANTISI ---")
    from exchange_client import ExchangeClient
    try:
        ex = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    except Exception as e:
        kontrol("İstemci oluşturma", HATA, str(e))
        return None

    try:
        bakiye = ex.get_account_balance_usdt()
        if bakiye <= 0:
            kontrol("Bakiye", HATA, "Bakiye sıfır - işlem yapılamaz")
        elif bakiye < 100:
            kontrol("Bakiye", UYARI,
                    f"{bakiye:.2f} USDT - minimum emir büyüklüğü (5 USDT) "
                    f"nedeniyle bazı pozisyonlar açılamayabilir")
        else:
            kontrol("Bakiye", TAMAM, f"{bakiye:.2f} USDT")
    except Exception as e:
        msg = str(e)
        if "restricted location" in msg or "451" in msg:
            kontrol("Bakiye", HATA,
                    "Bu ağdan Binance'e erişilemiyor (coğrafi kısıtlama).\n"
                    "API anahtarlarıyla ilgili DEĞİL - başka bir ağdan deneyin.")
        else:
            kontrol("Bakiye", HATA, msg)
        return None

    # Pozisyon modu
    try:
        mode = ex.client.futures_get_position_mode()
        hedge = mode.get("dualSidePosition", False)
        if hedge:
            kontrol("Pozisyon modu", TAMAM, "HEDGE (iki bot aynı hesapta çalışabilir)")
        else:
            kontrol("Pozisyon modu", UYARI,
                    "ONE-WAY (tek yön). İki botu aynı hesapta çalıştırırsanız "
                    "birbirlerinin pozisyonlarını bozarlar.\n"
                    "Tek bot çalıştırın veya ayrı alt hesap kullanın.")
    except Exception as e:
        kontrol("Pozisyon modu", UYARI, f"okunamadı: {e}")

    # Açık pozisyonlar
    try:
        acik = [p for p in ex.get_open_positions() if float(p.get("positionAmt", 0)) != 0]
        if acik:
            detay = "\n".join(f"{p['symbol']}: {p['positionAmt']}" for p in acik[:5])
            kontrol("Açık pozisyonlar", UYARI,
                    f"{len(acik)} açık pozisyon var. Bot bunları KENDİ pozisyonu "
                    f"sanıp yönetmeye çalışır:\n{detay}")
        else:
            kontrol("Açık pozisyonlar", TAMAM, "yok (temiz başlangıç)")
    except Exception as e:
        kontrol("Açık pozisyonlar", UYARI, str(e))

    return ex


def kontrol_piyasa(ex, signal_mode: bool):
    print("\n--- PİYASA DURUMU ---")
    if signal_mode:
        from market_regime import compute_market_regime, is_regime_tradeable
        try:
            syms = ex.get_top_symbols(config.SCAN.quote_asset, 14,
                                      config.SCAN.excluded_symbols)
            closes = {}
            for s in syms[:14]:
                try:
                    df = ex.get_klines(s, config.SCAN.timeframe,
                                       config.RISK.regime_lookback_bars + 5)
                    closes[s] = df["close"].values
                except Exception:
                    pass
            if closes:
                r = compute_market_regime(closes, config.RISK.regime_lookback_bars)
                ok, sebep = is_regime_tradeable(
                    r, config.RISK.regime_min_volatility,
                    config.RISK.regime_max_autocorrelation,
                    config.RISK.use_autocorr_filter)
                if ok:
                    kontrol("Piyasa rejimi", TAMAM, sebep)
                else:
                    kontrol("Piyasa rejimi", UYARI,
                            f"{sebep}\nBot çalışacak ama İŞLEM AÇMAYACAK.")
        except Exception as e:
            kontrol("Piyasa rejimi", UYARI, str(e))
    else:
        import crosssec_bot as cb
        try:
            bakiye = ex.get_account_balance_usdt()
            poz_buyuklugu = bakiye * (cb.GROSS_EXPOSURE / 2) / cb.N_LEGS
            syms = ex.get_top_symbols(config.SCAN.quote_asset, cb.UNIVERSE_SIZE,
                                      config.SCAN.excluded_symbols)
            cb._liquidity_cache.clear()
            gecen, elenen = [], []
            for s in syms:
                ok, _ = cb.check_liquidity(ex, s, poz_buyuklugu)
                (gecen if ok else elenen).append(s)
            if len(gecen) < cb.N_LEGS * 2:
                kontrol("Likidite filtresi", HATA,
                        f"Sadece {len(gecen)} coin geçti, {cb.N_LEGS*2} gerekli.\n"
                        f"MIN_DEPTH_USDT düşürün veya UNIVERSE_SIZE artırın.")
            else:
                kontrol("Likidite filtresi", TAMAM,
                        f"{len(gecen)}/{len(syms)} coin geçti "
                        f"(pozisyon ~${poz_buyuklugu:,.0f})")

            # Funding - en hassas maliyet kalemi
            oranlar = []
            for s in gecen[:10]:
                try:
                    info = ex.client.futures_mark_price(symbol=s)
                    oranlar.append(float(info.get("lastFundingRate", 0)) * 100)
                except Exception:
                    pass
            if oranlar:
                ort = float(np.mean(np.abs(oranlar)))
                yillik = ort * 3 * 365
                if ort > 0.05:
                    kontrol("Funding oranları", UYARI,
                            f"ortalama |%{ort:.4f}|/8sa -> yıllık ~%{yillik:.0f}\n"
                            f"Backtest %0.01 varsayıyor. Yüksek funding "
                            f"getiriyi ciddi düşürür (Sharpe 2.96 -> 1.92).")
                else:
                    kontrol("Funding oranları", TAMAM,
                            f"ortalama |%{ort:.4f}|/8sa -> yıllık ~%{yillik:.0f} "
                            f"(backtest varsayımı %0.01)")
        except Exception as e:
            kontrol("Piyasa kontrolleri", UYARI, str(e))


def main():
    ap = argparse.ArgumentParser(description="Canlıya geçiş öncesi kontrol")
    ap.add_argument("--signal", action="store_true",
                    help="Sinyal botu (main.py) için kontrol et")
    args = ap.parse_args()

    bot = "SİNYAL BOTU (main.py)" if args.signal else "KESİTSEL BOT (crosssec_bot.py)"
    print("=" * 62)
    print(f"CANLIYA GEÇİŞ ÖNCESİ KONTROL — {bot}")
    print("=" * 62)
    print("Hiçbir emir gönderilmez, sadece okuma yapılır.")

    if kontrol_ayarlar(args.signal):
        kontrol_risk_tutarliligi()
        ex = kontrol_baglanti(args.signal)
        if ex is not None:
            kontrol_piyasa(ex, args.signal)

    print("\n" + "=" * 62)
    h = sum(1 for d, _, _ in sonuclar if d == HATA)
    u = sum(1 for d, _, _ in sonuclar if d == UYARI)
    t = sum(1 for d, _, _ in sonuclar if d == TAMAM)
    print(f"SONUÇ: {t} tamam, {u} uyarı, {h} hata")
    if h:
        print("\nHATALAR düzeltilmeden canlıya geçmeyin:")
        for d, ad, m in sonuclar:
            if d == HATA:
                print(f"  - {ad}")
        return 1
    if u:
        print("\nUYARILAR (çalışır ama okuyun):")
        for d, ad, m in sonuclar:
            if d == UYARI:
                print(f"  - {ad}")
    print("\nSONRAKİ ADIM:")
    print("  1. python crosssec_bot.py --dry-run   (ne yapacağını gör)")
    print("  2. Demo hesapta --loop ile HAFTALARCA çalıştır")
    print("  3. Gerçek slippage ve funding'i logdan ölç")
    print("  4. Sonuçlar backtest'e yakınsa gerçek paraya geç")
    print("\nHATIRLATMA: backtest Sharpe'ı ~1216 konfigürasyon denendiği")
    print("için şişkindir. Gerçekçi beklenti 1.5-2.5 (bkz. README madde 61).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
