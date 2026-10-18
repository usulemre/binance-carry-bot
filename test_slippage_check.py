"""slippage_check.py'nin hesaplama mantiginin dogrulugu."""
import sys; sys.path.insert(0,'.')
from slippage_check import simulate_market_order, book_depth_usdt, risk_label

print("=== 1) Tek seviye yeterliyse slippage SIFIR olmali ===")
# 100 fiyattan 1000 adet var = $100.000 derinlik. $960 emri ilk seviyede doler.
book=[["100","1000"],["101","1000"]]
r=simulate_market_order(book, 960)
print(f"  ort.dolum={r['avg_fill_price']:.4f} (100 olmali), slippage=%{r['slippage_pct']:.4f}")
assert abs(r['avg_fill_price']-100)<1e-9, "tek seviyede slippage olmamali!"
assert r['filled_pct']==100

print("\n=== 2) Ince defter: birden fazla seviye suprulmeli ===")
# her seviyede sadece $100 var -> $960 emri 10 seviye yer
book=[[str(100+i), str(100/(100+i))] for i in range(20)]  # her seviye ~$100
r=simulate_market_order(book, 960)
print(f"  en iyi={r['best_price']:.2f}, ort.dolum={r['avg_fill_price']:.2f}, "
      f"slippage=%{r['slippage_pct']:.2f}, seviye={r['levels_used']}")
assert r['avg_fill_price']>r['best_price'], "ince defterde ortalama fiyat kotulesmeli!"
assert r['levels_used']>1, "birden fazla seviye kullanilmali!"

print("\n=== 3) Defter YETERSIZ: emrin tamami dolmamali ===")
book=[["100","1"],["101","1"]]   # toplam ~$201
r=simulate_market_order(book, 5000)
print(f"  dolabilen=%{r['filled_pct']:.1f}, dolmayan=${r['unfilled_usdt']:.0f}")
assert r['filled_pct']<100, "yetersiz defterde tamami dolmamali!"
assert r['unfilled_usdt']>0

print("\n=== 4) Buyuk emir, kucuk emirden DAHA KOTU dolmali ===")
book=[[str(100+i*0.1), "5"] for i in range(50)]
small=simulate_market_order(book, 500)
big=simulate_market_order(book, 10000)
print(f"  $500 slippage=%{small['slippage_pct']:.3f} | $10000 slippage=%{big['slippage_pct']:.3f}")
assert big['slippage_pct']>small['slippage_pct'], "buyuk emir daha kotu dolmali!"

print("\n=== 5) Derinlik hesabi ===")
book=[["100","10"],["101","10"],["102","10"]]   # 1000+1010+1020=3030
d=book_depth_usdt(book,3)
print(f"  3 seviye derinlik=${d:.0f} (3030 olmali)")
assert abs(d-3030)<1

print("\n=== 6) Risk etiketleri ===")
for v,exp in [(0.05,'ÇOK İYİ'),(0.3,'İYİ'),(0.7,'DİKKAT'),(2.0,'RİSKLİ'),(5.0,'ÇOK RİSKLİ')]:
    got=risk_label(v)
    print(f"  %{v} -> {got}")
    assert got==exp, f"yanlis etiket: {got}"

print("\nSLIPPAGE HESAP TESTLERI GECTI")
