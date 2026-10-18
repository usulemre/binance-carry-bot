"""RISK AYARLARI TUTARLILIGI.

Ayarlar tek tek makul gorunse de BIRLIKTE tehlikeli bir kombinasyon
olusturabilir. Ornegin:
  - 4 pozisyon x %25 notional x 5x kaldirac -> marj yetmez
  - tek turda %8 kayip riski ama gunluk limit %5 -> limit koruma saglamaz

Bu test, ayarlardan biri degistirildiginde tutarsizligi yakalar.
"""
import sys; sys.path.insert(0,'.')
import config, crosssec_bot as cb
from strategy import MAX_SL_DISTANCE_PCT

r = config.RISK
print("SINYAL BOTU AYARLARI")
print(f"  risk/islem=%{r.risk_per_trade_pct} | pozisyon={r.max_concurrent_positions} | "
      f"notional=%{r.max_position_notional_pct} | kaldirac={r.leverage}x | "
      f"gunluk limit=%{r.max_daily_loss_pct}")
print()

print("=== 1) Marj yeterli mi? ===")
toplam_notional = r.max_position_notional_pct * r.max_concurrent_positions
marj = toplam_notional / r.leverage
print(f"   toplam nominal=%{toplam_notional} / kaldirac {r.leverage}x -> marj=%{marj:.0f}")
assert marj <= 100, (
    f"MARJ YETMEZ: {r.max_concurrent_positions} pozisyon x "
    f"%{r.max_position_notional_pct} nominal, {r.leverage}x kaldiracla "
    f"%{marj:.0f} marj ister. Pozisyonlar acilamaz.")
if marj > 80:
    print(f"   ! UYARI: marj kullanimi yuksek (%{marj:.0f}) - ani harekette marj cagrisi riski")
else:
    print(f"   guvenli (%{marj:.0f})")

print("\n=== 2) Gunluk limit anlamli mi? ===")
tek_tur_risk = r.risk_per_trade_pct * r.max_concurrent_positions
print(f"   tum pozisyonlar SL yerse: %{tek_tur_risk} kayip")
print(f"   gunluk limit: %{r.max_daily_loss_pct}")
assert tek_tur_risk <= r.max_daily_loss_pct, (
    f"TEK TUR bile gunluk limiti asiyor (%{tek_tur_risk} > %{r.max_daily_loss_pct}). "
    f"Limit koruma saglamaz - bot zaten limiti asmis olarak durur.")
print(f"   tutarli")

print("\n=== 3) Kaldirac / stop-loss mesafesi ===")
likidasyon = 100 / r.leverage
print(f"   kaldirac {r.leverage}x -> likidasyon ~%{likidasyon:.0f}")
print(f"   SL ust siniri: %{MAX_SL_DISTANCE_PCT}")
assert MAX_SL_DISTANCE_PCT < likidasyon * 0.8, (
    f"SL siniri (%{MAX_SL_DISTANCE_PCT}) likidasyona (%{likidasyon:.0f}) cok yakin. "
    f"Fiyat SL'e ULASMADAN pozisyon likide olabilir.")
print(f"   guvenli tampon: SL %{MAX_SL_DISTANCE_PCT} < likidasyonun %80'i (%{likidasyon*0.8:.0f})")

print("\n" + "="*50)
print("KESITSEL BOT AYARLARI")
print(f"  bacak={cb.N_LEGS}+{cb.N_LEGS} | gross={cb.GROSS_EXPOSURE}x | "
      f"TP=%{cb.POSITION_TP_PCT} | acil stop=%{cb.EMERGENCY_STOP_PCT}")
print()

print("=== 4) Acil stop TP'den buyuk olmali ===")
print(f"   TP=%{cb.POSITION_TP_PCT}  acil stop=%{cb.EMERGENCY_STOP_PCT}")
assert cb.EMERGENCY_STOP_PCT > cb.POSITION_TP_PCT * 2, (
    f"Acil stop (%{cb.EMERGENCY_STOP_PCT}) TP'ye (%{cb.POSITION_TP_PCT}) cok yakin - "
    f"normal dalgalanmada tetiklenir, sigorta olmaktan cikar.")
print(f"   oran {cb.EMERGENCY_STOP_PCT/cb.POSITION_TP_PCT:.1f}x - normal dalgalanmada tetiklenmez")

print("\n=== 5) Kademeli azaltma < devre kesici ===")
print(f"   kademeli sifirlanma=%{cb.DRAWDOWN_SCALE_FULL_PCT}  devre kesici=%{cb.MAX_DRAWDOWN_PCT}")
assert cb.DRAWDOWN_SCALE_FULL_PCT < cb.MAX_DRAWDOWN_PCT, (
    "Kademeli azaltma devre kesiciden SONRA sifirlaniyor - "
    "bot once tamamen durur, kademeli koruma hic devreye girmez.")
print(f"   dogru sira: once kuculme (%{cb.DRAWDOWN_SCALE_FULL_PCT}), sonra durma (%{cb.MAX_DRAWDOWN_PCT})")

print("\n=== 6) Evren bacaklari karsilayabiliyor mu? ===")
gereken = cb.N_LEGS * 2
print(f"   evren={cb.UNIVERSE_SIZE} coin, gereken={gereken} pozisyon")
assert cb.UNIVERSE_SIZE >= gereken * 2, (
    f"Evren ({cb.UNIVERSE_SIZE}) gereken pozisyonun ({gereken}) 2 katindan az. "
    f"Likidite filtresi birkac coin elerse bacaklar dolmaz.")
print(f"   pay: {cb.UNIVERSE_SIZE/gereken:.1f}x (likidite filtresi eleyebilir)")

print("\n=== 7) Onbellek / rebalance ===")
rb=cb.REBALANCE_DAYS*24
assert cb.LIQUIDITY_CACHE_HOURS > rb, "onbellek rebalance'tan kisa - ise yaramaz"
print(f"   onbellek {cb.LIQUIDITY_CACHE_HOURS}sa > rebalance {rb:.0f}sa: OK")

print("\n=== 8) Veri yeterliligi ===")
gereken_bar = int(max(cb.HORIZON_DAYS)*cb.BARS_PER_DAY)
print(f"   en uzun ufuk {max(cb.HORIZON_DAYS)}g = {gereken_bar} bar, cekilen={cb.REQUIRED_BARS}")
assert cb.REQUIRED_BARS > gereken_bar, (
    "Cekilen bar sayisi en uzun ufku karsilamiyor - siralama sessizce bozulur!")
print(f"   yeterli (+{cb.REQUIRED_BARS-gereken_bar} bar pay)")

print("\nRISK TUTARLILIK TESTLERI GECTI")
