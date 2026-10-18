"""risk_manager.py - pozisyon boyutu ve gunluk zarar limiti.
En guvenlik kritik modul, hic test edilmemisti."""
import sys, os, json; sys.path.insert(0,'.')
import logging; logging.disable(logging.CRITICAL)
import config
from risk_manager import RiskManager

SF='/tmp/rm_test.json'
def temiz():
    if os.path.exists(SF): os.remove(SF)

temiz()
rm=RiskManager(config.RISK, SF)

print("=== 1) Pozisyon boyutu = risk / SL mesafesi ===")
# 10000 bakiye, %1 risk = 100 USDT risk. SL 5 birim uzakta -> 20 adet
q=rm.calculate_position_size(10000, 100.0, 95.0)
print(f"   bakiye=10000 risk=%{config.RISK.risk_per_trade_pct} SL=5 birim -> miktar={q}")
beklenen = 10000*(config.RISK.risk_per_trade_pct/100)/5
assert abs(q-min(beklenen, 10000*config.RISK.leverage*(config.RISK.max_position_notional_pct/100)/100))<1e-9

print("\n=== 2) SL YAKIN olunca miktar BUYUMELI (ama sinirli) ===")
yakin=rm.calculate_position_size(10000, 100.0, 99.9)   # 0.1 birim
uzak =rm.calculate_position_size(10000, 100.0, 90.0)   # 10 birim
print(f"   SL 0.1 birim -> {yakin:.2f} | SL 10 birim -> {uzak:.2f}")
assert yakin > uzak, "yakin SL'de miktar buyuk olmali"
# ama notional siniri devrede olmali
max_q = 10000*config.RISK.leverage*(config.RISK.max_position_notional_pct/100)/100
print(f"   notional siniri: {max_q:.2f} -> yakin SL bu siniri asmamali")
assert yakin <= max_q + 1e-9, "notional siniri calismadi - ASIRI POZISYON!"

print("\n=== 3) SL = giris fiyati (sifir mesafe) -> 0 donmeli ===")
assert rm.calculate_position_size(10000, 100.0, 100.0) == 0.0
print("   OK (sifira bolme yok)")

print("\n=== 4) Negatif/sifir bakiye -> 0 ===")
assert rm.calculate_position_size(0, 100.0, 95.0) == 0.0
assert rm.calculate_position_size(-500, 100.0, 95.0) == 0.0
print("   OK")

print("\n=== 5) scale siniri (0-1 disina tasmamali) ===")
tam=rm.calculate_position_size(10000,100.0,95.0,scale=1.0)
assert rm.calculate_position_size(10000,100.0,95.0,scale=5.0)==tam, "scale>1 kabul edildi!"
assert rm.calculate_position_size(10000,100.0,95.0,scale=-1)==0.0
print("   OK")

print("\n=== 6) Es zamanli pozisyon siniri ===")
mx=config.RISK.max_concurrent_positions
assert rm.can_open_new_position(mx-1) is True
assert rm.can_open_new_position(mx) is False
assert rm.can_open_new_position(mx+5) is False
print(f"   limit={mx}: OK")

print("\n=== 7) Gunluk zarar limiti ===")
temiz(); rm2=RiskManager(config.RISK, SF)
lim=config.RISK.max_daily_loss_pct
kucuk = -10000*(lim/100)*0.5    # limitin yarisi
buyuk = -10000*(lim/100)*1.5    # limitin 1.5 kati
print(f"   limit=%{lim}")
assert rm2.is_daily_loss_limit_hit(10000, kucuk) is False, "limit altinda tetiklendi"
assert rm2.is_daily_loss_limit_hit(10000, buyuk) is True, "limit asildi ama tetiklenmedi!"
print("   OK")

print("\n=== 8) KAR varken limit tetiklenmemeli ===")
assert rm2.is_daily_loss_limit_hit(10000, +5000) is False
print("   OK")

print("\n=== 9) BOZUK durum dosyasi -> cokme YOK ===")
temiz()
open(SF,'w').write('{bozuk json')
try:
    rm3=RiskManager(config.RISK, SF)
    rm3.calculate_position_size(10000,100.0,95.0)
    print("   OK (cokme yok)")
    bozuk_ok=True
except Exception as e:
    print(f"   !! COKTU: {type(e).__name__}: {e}")
    bozuk_ok=False

temiz()
if not bozuk_ok:
    sys.exit(1)
print("\nRISK YONETICI TESTLERI GECTI")

print("\n=== 10) ATOMIK YAZMA: yarim dosya birakmiyor mu ===")
temiz()
rm4=RiskManager(config.RISK, SF)
rm4.state={'date':'2026-01-01','daily_pnl':-50.0,'starting_balance':10000.0}
rm4._save_state()
# gecici dosya temizlenmis olmali
assert not os.path.exists(SF+'.tmp'), "gecici dosya kaldi!"
# icerik dogru okunmali
with open(SF) as f: st=json.load(f)
assert st['daily_pnl']==-50.0
print("   yazma sonrasi .tmp yok, icerik dogru: OK")

print("\n=== 11) DIGER durum dosyalari da atomik mi ===")
import crosssec_bot as cb, main as M, position_manager as pm
import inspect
for ad, fn in [('crosssec_bot._save_state', cb._save_state),
               ('main._save_bot_state', M._save_bot_state),
               ('position_manager.save_trades', pm.save_trades)]:
    kaynak=inspect.getsource(fn)
    atomik = 'os.replace' in kaynak
    print(f"   {ad:<32} atomik={atomik}")
    assert atomik, f"{ad} atomik degil - yarim dosya botu durdurabilir!"

print("\n=== 12) position_manager BOZUK dosyada cokmuyor mu ===")
eski=pm.TRADES_FILE
pm.TRADES_FILE='/tmp/pm_bozuk.json'
open(pm.TRADES_FILE,'w').write('{yarim kalmis')
r=pm.load_trades()
print(f"   bozuk dosyada load_trades() -> {r} (bos sozluk olmali)")
assert r=={}, "bozuk dosyada cokmeli degil, bos donmeli"
os.remove(pm.TRADES_FILE); pm.TRADES_FILE=eski

temiz()
print("\nDAYANIKLILIK TESTLERI GECTI")
