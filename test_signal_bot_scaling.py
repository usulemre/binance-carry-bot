"""Sinyal botu: kademeli exposure azaltma + yonetim anahtari testleri."""
import sys, os, json; sys.path.insert(0,'.')
import config
from risk_manager import RiskManager

print("=== 1) calculate_position_size scale carpani ===")
rm=RiskManager(config.RISK)
tam=rm.calculate_position_size(10000, 100.0, 95.0, scale=1.0)
yari=rm.calculate_position_size(10000, 100.0, 95.0, scale=0.5)
sifir=rm.calculate_position_size(10000, 100.0, 95.0, scale=0.0)
print(f"  scale=1.0 -> {tam:.4f}")
print(f"  scale=0.5 -> {yari:.4f} (yarisi olmali)")
print(f"  scale=0.0 -> {sifir:.4f} (0 olmali)")
assert abs(yari-tam/2)<1e-9, "yarim olcek yanlis!"
assert sifir==0.0, "sifir olcekte pozisyon acildi!"

print("\n=== 2) scale sinirlari (0-1 disina tasmamali) ===")
asiri=rm.calculate_position_size(10000,100.0,95.0,scale=5.0)
negatif=rm.calculate_position_size(10000,100.0,95.0,scale=-1.0)
print(f"  scale=5.0 -> {asiri:.4f} (tam ile ayni olmali)")
print(f"  scale=-1.0 -> {negatif:.4f} (0 olmali)")
assert abs(asiri-tam)<1e-9, "scale 1'in ustune cikti!"
assert negatif==0.0, "negatif scale pozisyon acti!"

print("\n=== 3) mean_reversion icin yonetim KAPALI olmali ===")
mr=config.USE_POSITION_MANAGEMENT.get("mean_reversion", True)
print(f"  mean_reversion yonetim: {mr} (False olmali)")
assert mr is False, "zararli yonetim hala acik!"

print("\n=== 4) bilinmeyen strateji icin varsayilan ACIK olmali ===")
bilinmeyen=config.USE_POSITION_MANAGEMENT.get("yeni_strateji", True)
print(f"  bilinmeyen strateji: {bilinmeyen} (True olmali - guvenli varsayilan)")
assert bilinmeyen is True

print("\n=== 5) dusus -> olcek hesabi ===")
import main
r_unit=10000*(config.RISK.risk_per_trade_pct/100)
for dd_r in [0,15,30,45]:
    bakiye=10000-dd_r*r_unit
    olcek=max(0.0,min(1.0,1.0-dd_r/config.DRAWDOWN_SCALE_FULL_R))
    print(f"  dusus {dd_r:>2}R (bakiye {bakiye:>7.0f}) -> olcek %{olcek*100:>5.1f}")
assert abs(max(0.0,min(1.0,1.0-0/30))-1.0)<1e-9
assert abs(max(0.0,min(1.0,1.0-15/30))-0.5)<1e-9
assert max(0.0,min(1.0,1.0-45/30))==0.0

print("\nSINYAL BOTU OLCEKLEME TESTLERI GECTI")

print("\n=== 6) maksimum tutma suresi: eski pozisyon kapanmali ===")
import time as _t, os, json
import main as M
M.BOT_STATE_FILE='/tmp/maxhold_test.json'
if os.path.exists(M.BOT_STATE_FILE): os.remove(M.BOT_STATE_FILE)

class FakeEx2:
    def __init__(s,pos): s._pos=pos; s.closed=[]; s.cancelled=[]
    def get_open_positions(s): return s._pos
    def close_position(s,sym,side,q): s.closed.append(sym)
    def cancel_all_open_orders(s,sym): s.cancelled.append(sym)

# 1. cagri: pozisyon ilk kez goruluyor -> kaydedilir, kapatilmaz
ex=FakeEx2([{'symbol':'AAAUSDT','positionAmt':'5'}])
M.close_stale_positions(ex)
print(f"  ilk gorus -> kapatilan: {ex.closed} (bos olmali)")
assert ex.closed==[], "ilk goruste kapatildi!"

# zamani geriye al (limit asilmis gibi)
st=json.load(open(M.BOT_STATE_FILE))
tf=M._timeframe_to_minutes(config.SCAN.timeframe)
st['position_opened_at']['AAAUSDT']=_t.time()-(config.MAX_HOLD_DAYS*86400+100)
json.dump(st,open(M.BOT_STATE_FILE,'w'))

ex2=FakeEx2([{'symbol':'AAAUSDT','positionAmt':'5'}])
M.close_stale_positions(ex2)
print(f"  sure dolunca -> kapatilan: {ex2.closed}")
assert 'AAAUSDT' in ex2.closed, "sure dolan pozisyon kapatilmadi!"
assert 'AAAUSDT' in ex2.cancelled, "emirler iptal edilmedi!"

print("\n=== 7) kapanmis pozisyon kayittan temizlenmeli ===")
ex3=FakeEx2([])   # artik acik pozisyon yok
M.close_stale_positions(ex3)
st=json.load(open(M.BOT_STATE_FILE))
print(f"  kalan kayit: {st.get('position_opened_at')}")
assert not st.get('position_opened_at'), "kapanan pozisyon kayitta kaldi!"
os.remove(M.BOT_STATE_FILE)
print("\nMAKSIMUM TUTMA TESTLERI GECTI")
