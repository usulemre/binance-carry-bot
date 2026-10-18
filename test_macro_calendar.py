"""macro_calendar.py testleri - canli botta karar veriyor, testi yoktu."""
import sys; sys.path.insert(0,'.')
from datetime import datetime, timezone, timedelta
import macro_calendar as mc

orig = list(mc.MACRO_EVENTS)

print("=== 1) Pencere mantigi (2sa once - 4sa sonra) ===")
mc.MACRO_EVENTS = ['2026-09-17T18:00:00']
senaryolar = [('2026-09-17T15:00:00', False, '3sa once - disarida'),
              ('2026-09-17T16:30:00', True,  '1.5sa once - icinde'),
              ('2026-09-17T18:00:00', True,  'tam saatinde'),
              ('2026-09-17T21:30:00', True,  '3.5sa sonra - icinde'),
              ('2026-09-17T23:00:00', False, '5sa sonra - disarida')]
for t, bek, ad in senaryolar:
    now = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
    r, _ = mc.is_near_macro_event(now)
    print(f"  {ad:<24} engelli={r} (beklenen {bek})")
    assert r == bek, f"pencere mantigi hatali: {ad}"

print("\n=== 2) BOS liste -> hicbir sey engellenmemeli ===")
mc.MACRO_EVENTS = []
assert mc.is_near_macro_event()[0] is False
assert mc.is_configured() is False
print("  bos liste: engelleme yok, is_configured=False (gorunur): OK")

print("\n=== 3) BOZUK tarih -> cokme YOK, digerleri calismali ===")
mc.MACRO_EVENTS = ['bozuk-tarih', '2026-09-17T18:00:00', '']
now = datetime.fromisoformat('2026-09-17T18:00:00').replace(tzinfo=timezone.utc)
r, sebep = mc.is_near_macro_event(now)
print(f"  bozuk girdiyle birlikte: engelli={r}")
assert r is True, "bozuk tarih digerlerini de bozdu!"

print("\n=== 4) Gecmis olaylar temizleniyor mu ===")
simdi = datetime.now(timezone.utc)
mc.MACRO_EVENTS = [
    (simdi - timedelta(days=30)).isoformat(),   # gecmis
    (simdi - timedelta(days=1)).isoformat(),    # gecmis
    (simdi + timedelta(days=10)).isoformat(),   # gelecek
]
silinen = mc.gecmis_olaylari_temizle()
print(f"  silinen: {silinen} (2 olmali), kalan: {len(mc.MACRO_EVENTS)} (1 olmali)")
assert silinen == 2 and len(mc.MACRO_EVENTS) == 1

print("\n=== 5) Naive datetime (tz yok) kabul edilmeli ===")
mc.MACRO_EVENTS = ['2026-09-17T18:00:00']
naive = datetime.fromisoformat('2026-09-17T18:00:00')   # tzinfo YOK
r, _ = mc.is_near_macro_event(naive)
assert r is True, "naive datetime islenemedi!"
print("  OK")

mc.MACRO_EVENTS = orig
print("\nMAKRO TAKVIM TESTLERI GECTI")
