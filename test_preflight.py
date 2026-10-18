"""preflight.py kontrollerinin gercekten hata yakaladigini dogrular."""
import sys, importlib; sys.path.insert(0,'.')
import config, preflight

# Test ortamdan BAGIMSIZ olmali: .env yoksa da calismali.
# (Aksi halde test "gecti/kaldi" sonucu, kimin makinesinde
# calistigina gore degisir.)
if not config.API_KEY:
    config.API_KEY = "test_anahtar"
    config.API_SECRET = "test_secret"

def calistir(signal_mode=False):
    preflight.sonuclar.clear()
    preflight.kontrol_ayarlar(signal_mode)
    return {ad: d for d, ad, _ in preflight.sonuclar}

print("=== 1) Dogru ayarlarla: hata olmamali ===")
r=calistir(False)
hatalar=[k for k,v in r.items() if v==preflight.HATA]
print(f"  hata: {hatalar} (bos olmali)")
assert not hatalar, f"dogru ayarda hata: {hatalar}"

print("\n=== 2) YANLIS zaman dilimi -> HATA vermeli ===")
import crosssec_bot as cb
eski=cb.TIMEFRAME; cb.TIMEFRAME='15m'
r=calistir(False)
print(f"  Zaman dilimi -> {r.get('Zaman dilimi')}")
assert r.get('Zaman dilimi')==preflight.HATA, "yanlis timeframe yakalanmadi!"
cb.TIMEFRAME=eski

print("\n=== 3) Onbellek rebalance'tan KISA -> UYARI vermeli ===")
eski_c=cb.LIQUIDITY_CACHE_HOURS; cb.LIQUIDITY_CACHE_HOURS=1.0
r=calistir(False)
print(f"  Likidite onbellegi -> {r.get('Likidite önbelleği')}")
assert r.get('Likidite önbelleği')==preflight.UYARI, "onbellek uyumsuzlugu yakalanmadi!"
cb.LIQUIDITY_CACHE_HOURS=eski_c

print("\n=== 4) TEHLIKELI kaldirac/SL kombinasyonu -> HATA ===")
import strategy
eski_lev=config.RISK.leverage; config.RISK.leverage=10   # likidasyon ~%10
r=calistir(True)
print(f"  Kaldirac/SL -> {r.get('Kaldıraç / SL tutarlılığı')}")
assert r.get('Kaldıraç / SL tutarlılığı')==preflight.HATA, "likidasyon riski yakalanmadi!"
config.RISK.leverage=eski_lev

print("\n=== 5) Zararli kar kilitleme ACIK -> UYARI ===")
eski_m=dict(config.USE_POSITION_MANAGEMENT)
config.USE_POSITION_MANAGEMENT[config.ACTIVE_STRATEGY]=True
r=calistir(True)
print(f"  Kar kilitleme -> {r.get('Kâr kilitleme')}")
assert r.get('Kâr kilitleme')==preflight.UYARI, "zararli yonetim yakalanmadi!"
config.USE_POSITION_MANAGEMENT.update(eski_m)

print("\n=== 6) LIVE mod -> UYARI vermeli ===")
eski_mode=config.BINANCE_MODE; config.BINANCE_MODE='live'
r=calistir(False)
print(f"  Calisma modu -> {r.get('Çalışma modu')}")
assert r.get('Çalışma modu')==preflight.UYARI, "live mod uyarisi yok!"
config.BINANCE_MODE=eski_mode

print("\nPREFLIGHT TESTLERI GECTI")
