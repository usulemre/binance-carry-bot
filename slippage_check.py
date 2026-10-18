"""Emir defteri derinliğinden SLIPPAGE tahmini - emir GÖNDERMEDEN.

NEDEN GEREKLİ:
Paper trading slippage'ı hiç göstermez - fiyatı listeden okur ve "aldın"
der. Gerçekte emriniz emir defterini yukarı/aşağı süpürür ve ortalama
dolum fiyatınız ekrandaki fiyattan farklı olur. Bu fark, yüksek
frekanslı bir stratejide komisyondan ÇOK daha büyük bir maliyet kalemi
olabilir.

ÖRNEK (gerçek risk):
  63 günde 65 cycle × 2 işlem (giriş+çıkış) = 130 işlem
  İşlem başına %1.5 slippage  ->  toplam ~%195 maliyet
  Bu, +%90'lık bir kârı fazlasıyla siler.

ÖZELLİKLE ÖNEMLİ: "aşırı hareket edeni seç" tipi stratejiler doğası
gereği küçük piyasa değerli, İNCE emir defterli coinlere yönelir.
Yani slippage riski tesadüf değil, stratejinin yapısında vardır.

BU ARAÇ NE YAPAR:
Binance'in public /fapi/v1/depth endpoint'inden emir defterini çeker ve
"şu büyüklükte piyasa emri göndersem ortalama dolum fiyatım ne olurdu"
sorusunu hesaplar. HİÇBİR EMİR GÖNDERMEZ, API anahtarı GEREKTİRMEZ.

KULLANIM:
    python slippage_check.py --symbols BTCUSDT,ETHUSDT --notional 960
    python slippage_check.py --top 20 --notional 960      # en hacimli 20 coin
    python slippage_check.py --symbols LABUSDT --notional 100,500,960,5000
"""

import argparse
import sys

import requests

# scanner_public'teki fallback mantığının aynısı: mainnet engelliyse testnet
BASE_URL_CANDIDATES = [
    "https://fapi.binance.com",
    "https://testnet.binancefuture.com",
]
_working_base = None


def _get(path: str, params: dict = None, timeout: int = 10):
    global _working_base
    candidates = [_working_base] if _working_base else BASE_URL_CANDIDATES
    last = None
    for base in candidates:
        try:
            r = requests.get(f"{base}{path}", params=params, timeout=timeout)
            if r.status_code == 200:
                if _working_base is None:
                    _working_base = base
                    if base != BASE_URL_CANDIDATES[0]:
                        print(f"[uyarı] mainnet erişilemedi, {base} kullanılıyor. "
                              f"Testnet emir defteri GERÇEK piyasayı yansıtmaz - "
                              f"bu sonuçlar sadece mekanizmayı gösterir.\n")
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
    raise RuntimeError(f"Binance'e ulaşılamadı: {last}")


def get_order_book(symbol: str, limit: int = 500) -> dict:
    """Emir defterini çeker. limit: 5,10,20,50,100,500,1000"""
    r = _get("/fapi/v1/depth", {"symbol": symbol, "limit": limit})
    return r.json()


def simulate_market_order(book_side: list, notional_usdt: float) -> dict:
    """Bir piyasa emrinin emir defterini süpürmesini simüle eder.

    book_side : [[fiyat, miktar], ...] - alım için 'asks', satım için 'bids'
    notional_usdt : emrin dolar büyüklüğü

    Döner: ortalama dolum fiyatı, en iyi fiyat, slippage %, doldurulabilen oran
    """
    if not book_side:
        return None
    best_price = float(book_side[0][0])
    remaining = notional_usdt
    cost = 0.0
    qty_filled = 0.0
    levels_used = 0

    for price_str, qty_str in book_side:
        price, qty = float(price_str), float(qty_str)
        level_notional = price * qty
        levels_used += 1
        if level_notional >= remaining:
            take_qty = remaining / price
            cost += take_qty * price
            qty_filled += take_qty
            remaining = 0.0
            break
        cost += level_notional
        qty_filled += qty
        remaining -= level_notional

    filled_notional = notional_usdt - remaining
    if qty_filled <= 0:
        return None
    avg_price = cost / qty_filled
    slippage_pct = abs(avg_price - best_price) / best_price * 100
    return {
        "best_price": best_price,
        "avg_fill_price": avg_price,
        "slippage_pct": slippage_pct,
        "filled_pct": filled_notional / notional_usdt * 100,
        "levels_used": levels_used,
        "unfilled_usdt": remaining,
    }


def book_depth_usdt(book_side: list, n_levels: int = 20) -> float:
    """İlk N seviyedeki toplam dolar hacmi - defterin 'kalınlığı'."""
    return sum(float(p) * float(q) for p, q in book_side[:n_levels])


def analyze_symbol(symbol: str, notionals: list, book_limit: int = 500) -> dict:
    try:
        book = get_order_book(symbol, book_limit)
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    asks, bids = book.get("asks", []), book.get("bids", [])
    if not asks or not bids:
        return {"symbol": symbol, "error": "emir defteri boş"}

    best_ask, best_bid = float(asks[0][0]), float(bids[0][0])
    spread_pct = (best_ask - best_bid) / best_bid * 100

    results = {}
    for n in notionals:
        buy = simulate_market_order(asks, n)    # alım asks'i süpürür
        sell = simulate_market_order(bids, n)   # satım bids'i süpürür
        if buy and sell:
            # Gidiş-dönüş (giriş + çıkış) toplam maliyet
            results[n] = {
                "buy_slip": buy["slippage_pct"],
                "sell_slip": sell["slippage_pct"],
                "round_trip": buy["slippage_pct"] + sell["slippage_pct"] + spread_pct,
                "buy_filled": buy["filled_pct"],
                "levels": buy["levels_used"],
            }
    return {
        "symbol": symbol,
        "spread_pct": spread_pct,
        "depth20_ask": book_depth_usdt(asks, 20),
        "depth20_bid": book_depth_usdt(bids, 20),
        "results": results,
    }


def risk_label(round_trip_pct: float) -> str:
    if round_trip_pct < 0.15:
        return "ÇOK İYİ"
    if round_trip_pct < 0.40:
        return "İYİ"
    if round_trip_pct < 1.00:
        return "DİKKAT"
    if round_trip_pct < 3.00:
        return "RİSKLİ"
    return "ÇOK RİSKLİ"


def get_top_symbols(n: int) -> list:
    r = _get("/fapi/v1/ticker/24hr")
    tickers = [t for t in r.json() if t["symbol"].endswith("USDT")]
    tickers.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    return [t["symbol"] for t in tickers[:n]]


def main():
    ap = argparse.ArgumentParser(
        description="Emir defterinden slippage tahmini (emir GÖNDERMEZ, anahtar GEREKTİRMEZ)")
    ap.add_argument("--symbols", type=str, default=None,
                    help="Virgülle ayrılmış semboller: BTCUSDT,ETHUSDT")
    ap.add_argument("--top", type=int, default=None,
                    help="En hacimli N coini analiz et")
    ap.add_argument("--notional", type=str, default="960",
                    help="Emir büyüklüğü USDT (virgülle çoklu: 100,960,5000)")
    args = ap.parse_args()

    notionals = [float(x) for x in args.notional.split(",")]

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    elif args.top:
        symbols = get_top_symbols(args.top)
    else:
        print("--symbols veya --top vermelisiniz.\n")
        ap.print_help()
        return 1

    print(f"{len(symbols)} sembol, emir büyüklüğü: "
          f"{', '.join(f'${n:,.0f}' for n in notionals)} USDT")
    print("(gidiş-dönüş = alım slippage + satım slippage + spread)\n")

    rows = []
    for sym in symbols:
        a = analyze_symbol(sym, notionals)
        if "error" in a:
            print(f"{sym:<14} HATA: {a['error']}")
            continue
        rows.append(a)

    if not rows:
        return 1

    # Ana tablo: ilk notional için sıralı özet
    main_n = notionals[0]
    rows.sort(key=lambda r: r["results"].get(main_n, {}).get("round_trip", 9e9))

    print(f"{'sembol':<14} {'spread':>8} {'defter20(alış)':>15} "
          f"{'gidiş-dönüş':>12} {'değerlendirme':>14}")
    print("-" * 70)
    for r in rows:
        res = r["results"].get(main_n)
        if not res:
            continue
        rt = res["round_trip"]
        print(f"{r['symbol']:<14} {r['spread_pct']:>7.3f}% "
              f"${r['depth20_ask']:>13,.0f} {rt:>11.3f}% {risk_label(rt):>14}")
        if res["buy_filled"] < 99.9:
            print(f"{'':14} !! emrin sadece %{res['buy_filled']:.0f}'i dolabilir - "
                  f"defter yetersiz!")

    # Büyüklüğe göre kırılım (birden fazla notional verildiyse)
    if len(notionals) > 1:
        print(f"\n{'sembol':<14}", end="")
        for n in notionals:
            print(f"{'$'+format(n,',.0f'):>12}", end="")
        print()
        print("-" * (14 + 12 * len(notionals)))
        for r in rows:
            print(f"{r['symbol']:<14}", end="")
            for n in notionals:
                res = r["results"].get(n)
                print(f"{res['round_trip']:>11.3f}%" if res else f"{'--':>12}", end="")
            print()

    # Strateji maliyeti tahmini
    print(f"\n--- STRATEJİ MALİYETİ TAHMİNİ (${main_n:,.0f} pozisyon) ---")
    valid = [r["results"][main_n]["round_trip"] for r in rows if main_n in r["results"]]
    if valid:
        med = sorted(valid)[len(valid) // 2]
        worst = max(valid)
        print(f"Medyan gidiş-dönüş slippage : %{med:.3f}")
        print(f"En kötü sembol               : %{worst:.3f}")
        print()
        for cycles, label in [(6 * 30, "günde 6 dengeleme, 30 gün"),
                              (30, "günde 1 dengeleme, 30 gün"),
                              (65, "63 günde 65 cycle")]:
            print(f"  {label:<28}: medyan %{med*cycles:>7.1f} | "
                  f"en kötü %{worst*cycles:>7.1f} toplam maliyet")
        print("\nNOT: Bu, pozisyonun HER dengelemede tamamen değiştiği")
        print("varsayımıdır (üst sınır). Gerçekte bot sadece FARKI işler,")
        print("yani gerçek maliyet bunun altındadır. Yine de komisyondan")
        print("kat kat büyük olabilir - bu yüzden ölçmek gerekir.")

    if _working_base != BASE_URL_CANDIDATES[0]:
        print("\n" + "=" * 68)
        print("!!! UYARI: Bu sonuçlar TESTNET emir defterinden hesaplandı.")
        print("Testnet defterleri yapay olarak kalındır ve GERÇEK likiditeyi")
        print("YANSITMAZ. Buradaki 'ÇOK İYİ' değerlendirmeleri gerçek piyasada")
        print("çok daha kötü olabilir - özellikle küçük piyasa değerli")
        print("coinlerde. Gerçek ölçüm için bu aracı mainnet'e erişebilen")
        print("bir ağdan (kendi bilgisayarınızdan) çalıştırın.")
        print("=" * 68)

    return 0


if __name__ == "__main__":
    sys.exit(main())
