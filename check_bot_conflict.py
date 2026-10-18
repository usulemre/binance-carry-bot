"""İki botu aynı hesapta çalıştırmadan önce ÇAKIŞMA kontrolü.

SORUN: `main.py` (sinyal botu) ve `crosssec_bot.py` (kesitsel bot) aynı
coinlerde TERS yönde pozisyon açabilir. Örneğin sinyal botu BTCUSDT long
açarken kesitsel bot BTCUSDT short tutuyor olabilir.

Binance'te iki pozisyon modu var:
  - ONE-WAY (tek yön, varsayılan): Bir sembolde tek pozisyon olur.
    İkinci bot ters yönde emir gönderirse, ilkinin pozisyonunu KAPATIR
    veya azaltır. İki bot birbirinin işlemlerini bozar.
  - HEDGE (çift yön): Aynı sembolde hem long hem short tutulabilir.
    İki bot birbirini bozmaz.

Bu araç mevcut modu kontrol eder ve iki botun evrenlerinin ne kadar
örtüştüğünü gösterir.

EN TEMİZ ÇÖZÜM: Ayrı Binance alt hesapları (sub-account) kullanmak.
Her botun kendi bakiyesi, kendi pozisyonları olur, hiç karışmaz.

KULLANIM:
    python check_bot_conflict.py
"""

import sys

import config
from exchange_client import ExchangeClient
import crosssec_bot as cs


def main():
    if not config.API_KEY or not config.API_SECRET:
        print("API anahtarları eksik (.env dosyasını kontrol edin).")
        return 1

    ex = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)

    print("=== POZİSYON MODU ===")
    try:
        mode = ex.client.futures_get_position_mode()
        hedge = mode.get("dualSidePosition", False)
        if hedge:
            print("  HEDGE modu AÇIK - iki bot aynı hesapta çalışabilir.")
            print("  (Aynı sembolde hem long hem short tutulabilir.)")
        else:
            print("  ONE-WAY modu (tek yön) - İKİ BOT AYNI HESAPTA ÇAKIŞIR!")
            print()
            print("  Sinyal botu BTCUSDT long açarken kesitsel bot BTCUSDT short")
            print("  açmak isterse, ikincisi birincinin pozisyonunu kapatır.")
            print()
            print("  Seçenekler:")
            print("    1) AYRI ALT HESAPLAR kullanın (en temizi)")
            print("    2) Hedge moduna geçin (Binance arayüzünden)")
            print("    3) Tek bir bot çalıştırın")
    except Exception as e:
        print(f"  Pozisyon modu okunamadı: {e}")

    print()
    print("=== EVREN ÖRTÜŞMESİ ===")
    try:
        signal_syms = set(ex.get_top_symbols(
            config.SCAN.quote_asset, config.SCAN.top_n_symbols,
            config.SCAN.excluded_symbols))
        cs_syms = set(ex.get_top_symbols(
            config.SCAN.quote_asset, cs.UNIVERSE_SIZE,
            config.SCAN.excluded_symbols))
        ortak = signal_syms & cs_syms
        print(f"  Sinyal botu evreni  : {len(signal_syms)} coin")
        print(f"  Kesitsel bot evreni : {len(cs_syms)} coin")
        print(f"  ORTAK               : {len(ortak)} coin")
        if ortak:
            orn = sorted(ortak)[:8]
            print(f"    örnek: {', '.join(orn)}{'...' if len(ortak) > 8 else ''}")
            print()
            print(f"  Bu {len(ortak)} coinde iki bot aynı anda ters yönde")
            print(f"  pozisyon almak isteyebilir.")
    except Exception as e:
        print(f"  Evren karşılaştırılamadı: {e}")

    print()
    print("=== AÇIK POZİSYONLAR ===")
    try:
        pos = [p for p in ex.get_open_positions()
               if float(p.get("positionAmt", 0)) != 0]
        if not pos:
            print("  Açık pozisyon yok.")
        else:
            for p in pos:
                amt = float(p["positionAmt"])
                yon = "LONG " if amt > 0 else "SHORT"
                print(f"  {yon} {p['symbol']:<14} {abs(amt)}")
            print()
            print("  NOT: Bu pozisyonların hangi bota ait olduğu borsa")
            print("  tarafından ayırt EDİLEMEZ. İki bot aynı hesapta")
            print("  çalışıyorsa birbirinin pozisyonlarını kendininmiş gibi")
            print("  görür ve yönetmeye çalışır.")
    except Exception as e:
        print(f"  Pozisyonlar okunamadı: {e}")

    print()
    print("=== ÖNERİ ===")
    print("  Sermaye bölüşümü (backtest'te en iyi Sharpe veren):")
    print("    %40 kesitsel bot + %60 sinyal botu")
    print("  Ama AYRI ALT HESAPLARDA çalıştırın - aynı hesapta")
    print("  pozisyonlar ve bakiye hesapları karışır.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
