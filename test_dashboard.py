"""dashboard.py testleri - canli izleme araci calisiyor mu?"""
import sys, os, json; sys.path.insert(0,'.')
import config
# anahtarsiz mod test edilsin
config.API_KEY=''; config.API_SECRET=''
import importlib, dashboard
importlib.reload(dashboard)

print("=== 1) Anahtarsiz modda /api/status calisiyor mu ===")
c=dashboard.app.test_client()
r=c.get('/api/status')
print(f"  HTTP {r.status_code}")
assert r.status_code==200, "endpoint cokdu!"
d=r.get_json()
assert d['has_keys'] is False
print(f"  has_keys={d['has_keys']}, signals={len(d['signals'])}: OK")

print("\n=== 2) Ana sayfa render ediliyor mu ===")
r2=c.get('/')
assert r2.status_code==200
html=r2.get_data(as_text=True)
assert 'csPanel' in html, "kesitsel bot paneli HTML'de yok!"
assert 'Bakiye' in html or 'balance' in html
print("  HTML render + kesitsel panel mevcut: OK")

print("\n=== 3) Kesitsel bot durum okuma ===")
import crosssec_bot as cb
json.dump({'peak_balance':12000.0}, open(cb.STATE_FILE,'w'))
d3=dashboard._crosssec_durum()
print(f"  okunan: {d3}")
assert d3 and d3['peak_balance']==12000.0
os.remove(cb.STATE_FILE)

print("\n=== 4) Durum dosyasi YOKSA None donmeli (cokme yok) ===")
assert dashboard._crosssec_durum() is None
print("  OK")

print("\n=== 5) BOZUK durum dosyasi -> cokme yok ===")
open(cb.STATE_FILE,'w').write('{bozuk!!')
assert dashboard._crosssec_durum() is None
os.remove(cb.STATE_FILE)
print("  OK")

print("\n=== 6) Dusus -> olcek/durum mantigi ===")
for dd,bek in [(0,'NORMAL'),(15,'KUCULTULDU'),(30,'ACILMIYOR'),(40,'DEVRE')]:
    o=cb.compute_exposure_scale(dd)
    print(f"  dusus %{dd:>2} -> exposure %{o*100:>3.0f}")
assert cb.compute_exposure_scale(0)==1.0
assert cb.compute_exposure_scale(30)==0.0

print("\nDASHBOARD TESTLERI GECTI")
